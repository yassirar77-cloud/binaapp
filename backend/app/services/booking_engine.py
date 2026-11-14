"""Booking engine — the pure rules behind slot booking.

No database and no network in this module: everything takes plain dicts and
returns plain dicts, so the slot rules can be tested exhaustively. The
storage half is ``booking_store.py``; the HTTP half is
``api/v1/endpoints/bookings.py``.

THE RULES
---------
* The business keeps Malaysian time (UTC+8, no daylight saving). Opening
  hours, "today" and the date a customer picks are all in that zone;
  instants are stored and returned as UTC-aware timestamps.
* A day's slots start at each opening range's ``open`` and step by
  ``slot_interval_min``. A slot only exists if the whole service fits
  before that range's ``close``.
* A slot is bookable when it starts at least ``lead_time_min`` from now,
  its date is no more than ``max_days_ahead`` days away, the date is not a
  closed date, and fewer than ``capacity_per_slot`` active bookings overlap
  it. "Overlap" is conservative: any active booking touching the slot's
  time range counts against it, whichever service it is for.
* The database enforces the capacity rule again under a lock
  (``create_booking`` in migration 065) — this module decides what to
  *offer*; the database decides what is *accepted*.
"""

from __future__ import annotations

import re
import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

#: Malaysian time. A fixed offset is exact: Malaysia has no daylight saving.
MYT = timezone(timedelta(hours=8), name="MYT")

WEEKDAYS: Tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

ACTIVE_STATUSES = frozenset({"pending", "confirmed"})
ALL_STATUSES = frozenset({"pending", "confirmed", "cancelled", "completed", "no_show"})

#: What the merchant may move a booking to, from each status. Finished
#: states are final — a cancelled slot may already have been rebooked.
STATUS_TRANSITIONS: Dict[str, frozenset] = {
    "pending": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"completed", "no_show", "cancelled"}),
    "cancelled": frozenset(),
    "completed": frozenset(),
    "no_show": frozenset(),
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "slot_interval_min": 30,
    "capacity_per_slot": 1,
    "lead_time_min": 60,
    "max_days_ahead": 30,
    "weekly_hours": {
        "mon": [{"open": "09:00", "close": "18:00"}],
        "tue": [{"open": "09:00", "close": "18:00"}],
        "wed": [{"open": "09:00", "close": "18:00"}],
        "thu": [{"open": "09:00", "close": "18:00"}],
        "fri": [{"open": "09:00", "close": "18:00"}],
        "sat": [{"open": "09:00", "close": "18:00"}],
        "sun": [],
    },
    "closed_dates": [],
    "note": "",
}

LIMITS = {
    "slot_interval_min": (5, 240),
    "capacity_per_slot": (1, 50),
    "lead_time_min": (0, 10080),
    "max_days_ahead": (1, 180),
}

MAX_RANGES_PER_DAY = 4
MAX_CLOSED_DATES = 120
MAX_NOTE_LEN = 500

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# No 0/O/1/I/L: the code is read over the phone and typed back.
_REF_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_REF_RE = re.compile(r"^TP-[A-Z0-9]{6}$")


class BookingError(ValueError):
    """A rule was broken. ``code`` is stable for clients; the message is
    Malay copy that can be shown to the person as-is."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Small parsers
# ---------------------------------------------------------------------------

def parse_hhmm(value: Any) -> int:
    """'09:30' -> 570 minutes after midnight. '24:00' is accepted as the
    end of the day (1440) so a shop can close at midnight."""
    text = str(value or "").strip()
    if text == "24:00":
        return 1440
    match = _TIME_RE.match(text)
    if not match:
        raise BookingError("INVALID_TIME", f"Masa tidak sah: {text or '(kosong)'}")
    return int(match.group(1)) * 60 + int(match.group(2))


def format_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_date(value: Any) -> date:
    text = str(value or "").strip()
    if not _DATE_RE.match(text):
        raise BookingError("INVALID_DATE", "Tarikh tidak sah")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise BookingError("INVALID_DATE", "Tarikh tidak sah")


def parse_instant(value: Any) -> Optional[datetime]:
    """A stored timestamptz (ISO string or datetime) as an aware datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    # PostgREST may return "+00" style offsets or 5-digit fractions.
    text = re.sub(r"([+-]\d{2})$", r"\1:00", text)
    text = re.sub(r"\.(\d{1,6})\d*", lambda m: "." + m.group(1).ljust(6, "0"), text)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def now_myt() -> datetime:
    return datetime.now(MYT)


def normalize_phone(raw: Any) -> str:
    """Malaysian mobile/landline digits in one canonical form (60…), so the
    same person is recognised however they typed the number."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("600"):
        digits = "60" + digits[3:]
    elif digits.startswith("0"):
        digits = "6" + digits
    elif digits and not digits.startswith("60"):
        digits = "60" + digits
    if not 10 <= len(digits) <= 13:
        raise BookingError("INVALID_PHONE", "Nombor telefon tidak sah")
    return digits


def make_reference() -> str:
    return "TP-" + "".join(secrets.choice(_REF_ALPHABET) for _ in range(6))


def clean_reference(raw: Any) -> str:
    text = str(raw or "").strip().upper().replace(" ", "")
    if text and not text.startswith("TP-"):
        text = "TP-" + text.removeprefix("TP")
    if not _REF_RE.match(text):
        raise BookingError("INVALID_REFERENCE", "Kod rujukan tidak sah")
    return text


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def _clamp_int(value: Any, key: str, default: int) -> int:
    low, high = LIMITS[key]
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def clean_weekly_hours(raw: Any, *, strict: bool = False) -> Dict[str, List[Dict[str, str]]]:
    """Canonical weekly hours: every weekday present, ranges sorted,
    well-formed and non-overlapping.

    ``strict`` (merchant input) raises on anything wrong; the lenient mode
    (stored rows) drops what it cannot read so one bad range never takes
    the whole booking page down.
    """
    source = raw if isinstance(raw, dict) else {}
    cleaned: Dict[str, List[Dict[str, str]]] = {}
    for day in WEEKDAYS:
        ranges_in = source.get(day) or []
        if not isinstance(ranges_in, list):
            if strict:
                raise BookingError("INVALID_HOURS", "Format waktu operasi tidak sah")
            ranges_in = []
        if strict and len(ranges_in) > MAX_RANGES_PER_DAY:
            raise BookingError(
                "INVALID_HOURS", f"Maksimum {MAX_RANGES_PER_DAY} julat masa sehari"
            )
        ranges: List[Tuple[int, int]] = []
        for item in ranges_in[:MAX_RANGES_PER_DAY]:
            try:
                if not isinstance(item, dict):
                    raise BookingError("INVALID_HOURS", "Format waktu operasi tidak sah")
                start, end = parse_hhmm(item.get("open")), parse_hhmm(item.get("close"))
                if end <= start:
                    raise BookingError(
                        "INVALID_HOURS", "Waktu tutup mesti selepas waktu buka"
                    )
            except BookingError:
                if strict:
                    raise
                continue
            ranges.append((start, end))
        ranges.sort()
        kept: List[Tuple[int, int]] = []
        for start, end in ranges:
            if kept and start < kept[-1][1]:
                if strict:
                    raise BookingError("INVALID_HOURS", "Julat masa bertindih")
                continue
            kept.append((start, end))
        cleaned[day] = [
            {"open": format_hhmm(s), "close": format_hhmm(e)} for s, e in kept
        ]
    return cleaned


def clean_closed_dates(raw: Any, *, strict: bool = False) -> List[str]:
    out: List[str] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            out.append(parse_date(item).isoformat())
        except BookingError:
            if strict:
                raise
    out = sorted(set(out))
    if strict and len(out) > MAX_CLOSED_DATES:
        raise BookingError("INVALID_DATE", f"Maksimum {MAX_CLOSED_DATES} tarikh tutup")
    return out[:MAX_CLOSED_DATES]


def normalize_settings(row: Optional[Dict[str, Any]], *, strict: bool = False) -> Dict[str, Any]:
    """Settings as the rest of the engine expects them. A website with no
    row yet gets the defaults (booking off, Mon–Sat 9–6)."""
    if not row:
        return {**DEFAULT_SETTINGS, "weekly_hours": clean_weekly_hours(DEFAULT_SETTINGS["weekly_hours"])}
    hours_raw = row.get("weekly_hours")
    return {
        "enabled": bool(row.get("enabled", False)),
        "slot_interval_min": _clamp_int(row.get("slot_interval_min"), "slot_interval_min", 30),
        "capacity_per_slot": _clamp_int(row.get("capacity_per_slot"), "capacity_per_slot", 1),
        "lead_time_min": _clamp_int(row.get("lead_time_min"), "lead_time_min", 60),
        "max_days_ahead": _clamp_int(row.get("max_days_ahead"), "max_days_ahead", 30),
        "weekly_hours": clean_weekly_hours(hours_raw, strict=strict),
        "closed_dates": clean_closed_dates(row.get("closed_dates"), strict=strict),
        "note": str(row.get("note") or "")[:MAX_NOTE_LEN],
    }


def open_weekdays(settings: Dict[str, Any]) -> List[str]:
    return [d for d in WEEKDAYS if settings["weekly_hours"].get(d)]


# ---------------------------------------------------------------------------
# Slots
# ---------------------------------------------------------------------------

def _at(day: date, minutes: int) -> datetime:
    return datetime.combine(day, time(0, 0), tzinfo=MYT) + timedelta(minutes=minutes)


def _active_ranges(bookings: Iterable[Dict[str, Any]]) -> List[Tuple[datetime, datetime]]:
    ranges = []
    for booking in bookings or []:
        if booking.get("status") not in ACTIVE_STATUSES:
            continue
        start, end = parse_instant(booking.get("start_at")), parse_instant(booking.get("end_at"))
        if start and end:
            ranges.append((start, end))
    return ranges


def date_problem(settings: Dict[str, Any], day: date, now: Optional[datetime] = None) -> Optional[BookingError]:
    """Why nothing can be booked on ``day`` at all, or None."""
    today = (now or now_myt()).astimezone(MYT).date()
    if day < today:
        return BookingError("DATE_PAST", "Tarikh ini sudah berlalu")
    if (day - today).days > settings["max_days_ahead"]:
        return BookingError(
            "DATE_TOO_FAR",
            f"Tempahan hanya dibuka {settings['max_days_ahead']} hari ke hadapan",
        )
    if day.isoformat() in settings["closed_dates"]:
        return BookingError("DATE_CLOSED", "Kami tutup pada tarikh ini")
    if not settings["weekly_hours"].get(WEEKDAYS[day.weekday()]):
        return BookingError("DATE_CLOSED", "Kami tutup pada hari ini")
    return None


def generate_slots(
    settings: Dict[str, Any],
    duration_min: int,
    day: date,
    bookings: Iterable[Dict[str, Any]] = (),
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Every slot of ``day`` for a service of ``duration_min``.

    Returns ``[{"time": "09:00", "start_at": iso, "end_at": iso,
    "remaining": 2, "available": True}]`` — past and full slots are
    included with ``available: False`` so the page can show them greyed
    out. An empty list means the day is not bookable at all.
    """
    now = (now or now_myt()).astimezone(MYT)
    if date_problem(settings, day, now):
        return []
    duration = max(5, int(duration_min))
    interval = settings["slot_interval_min"]
    capacity = settings["capacity_per_slot"]
    earliest = now + timedelta(minutes=settings["lead_time_min"])
    taken = _active_ranges(bookings)

    slots: List[Dict[str, Any]] = []
    for rng in settings["weekly_hours"][WEEKDAYS[day.weekday()]]:
        cursor, close = parse_hhmm(rng["open"]), parse_hhmm(rng["close"])
        while cursor + duration <= close:
            start, end = _at(day, cursor), _at(day, cursor + duration)
            overlapping = sum(1 for s, e in taken if s < end and e > start)
            remaining = max(0, capacity - overlapping)
            slots.append({
                "time": format_hhmm(cursor),
                "start_at": start.astimezone(timezone.utc).isoformat(),
                "end_at": end.astimezone(timezone.utc).isoformat(),
                "remaining": remaining,
                "available": remaining > 0 and start >= earliest,
            })
            cursor += interval
    return slots


def resolve_slot(
    settings: Dict[str, Any],
    duration_min: int,
    day: date,
    time_hhmm: str,
    bookings: Iterable[Dict[str, Any]] = (),
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """The slot a customer asked for, or a BookingError saying why not.

    The requested time must be one the engine itself would offer — a
    customer cannot invent 09:07 or book outside opening hours.
    """
    now = (now or now_myt()).astimezone(MYT)
    if not settings["enabled"]:
        raise BookingError("BOOKING_DISABLED", "Tempahan dalam talian belum dibuka")
    problem = date_problem(settings, day, now)
    if problem:
        raise problem
    wanted = format_hhmm(parse_hhmm(time_hhmm))
    for slot in generate_slots(settings, duration_min, day, bookings, now):
        if slot["time"] != wanted:
            continue
        if slot["remaining"] <= 0:
            raise BookingError("SLOT_FULL", "Maaf, slot ini sudah penuh. Sila pilih masa lain.")
        if not slot["available"]:
            raise BookingError("SLOT_TOO_SOON", "Slot ini terlalu hampir. Sila pilih masa lain.")
        return slot
    raise BookingError("SLOT_INVALID", "Masa ini tiada dalam jadual. Sila pilih masa lain.")


def can_transition(current: str, target: str) -> bool:
    return target in STATUS_TRANSITIONS.get(current, frozenset())


def customer_can_cancel(booking: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """A customer may cancel an active booking that has not started yet."""
    if booking.get("status") not in ACTIVE_STATUSES:
        return False
    start = parse_instant(booking.get("start_at"))
    return bool(start and start > (now or now_myt()))


def public_booking_view(booking: Dict[str, Any]) -> Dict[str, Any]:
    """What a customer holding the reference may see — no internal ids
    beyond the reference itself, and the phone is masked."""
    phone = str(booking.get("customer_phone") or "")
    start = parse_instant(booking.get("start_at"))
    local = start.astimezone(MYT) if start else None
    return {
        "reference": booking.get("reference"),
        "service_name": booking.get("service_name"),
        "duration_min": booking.get("duration_min"),
        "price": booking.get("price"),
        "date": local.date().isoformat() if local else booking.get("booking_date"),
        "time": local.strftime("%H:%M") if local else None,
        "start_at": booking.get("start_at"),
        "end_at": booking.get("end_at"),
        "customer_name": booking.get("customer_name"),
        "customer_phone_masked": ("*" * max(0, len(phone) - 4)) + phone[-4:],
        "notes": booking.get("notes") or "",
        "status": booking.get("status"),
        "can_cancel": customer_can_cancel(booking),
    }
