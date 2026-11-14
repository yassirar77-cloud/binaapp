"""Booking engine API — real appointment slots for service businesses.

Merchant (login + website ownership):

    GET    /api/v1/bookings/admin/{website_id}/settings
    PUT    /api/v1/bookings/admin/{website_id}/settings
    GET    /api/v1/bookings/admin/{website_id}/services
    POST   /api/v1/bookings/admin/{website_id}/services
    PUT    /api/v1/bookings/admin/{website_id}/services/{service_id}
    DELETE /api/v1/bookings/admin/{website_id}/services/{service_id}
    GET    /api/v1/bookings/admin/{website_id}/bookings?date_from=&date_to=&status=
    PUT    /api/v1/bookings/admin/{website_id}/bookings/{booking_id}/status

Customer (no login; per-IP rate limits):

    GET    /api/v1/bookings/public/{website_id}                 services + what is bookable
    GET    /api/v1/bookings/public/{website_id}/slots?service_id=&date=
    POST   /api/v1/bookings/public/{website_id}                 make a booking
    GET    /api/v1/bookings/public/{website_id}/lookup?reference=&phone=
    POST   /api/v1/bookings/public/{website_id}/cancel

The rules (what a slot is, when it is bookable) are in
``services/booking_engine.py``. The final say on capacity belongs to the
database: bookings are inserted through ``create_booking()`` (migration
065), which counts and inserts under a lock.

A customer proves a booking is theirs with the reference code AND the
phone number it was made with — the reference alone is not enough.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from datetime import timedelta
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from app.core.security import get_current_user
from app.services import booking_engine as engine
from app.services import booking_store as store

router = APIRouter()

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)

MAX_SERVICES = 40

# ---------------------------------------------------------------------------
# Rate limits (process memory, per IP) — the public half has no login.
# ---------------------------------------------------------------------------

_WINDOW_SECONDS = 3600.0
_LIMITS = {"create": 10, "lookup": 40, "cancel": 15}
_hits: Dict[str, Dict[str, Deque[float]]] = {k: defaultdict(deque) for k in _LIMITS}


def reset_rate_limits() -> None:
    for bucket in _hits.values():
        bucket.clear()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limit(kind: str, request: Request) -> None:
    now = time.monotonic()
    hits = _hits[kind][_client_ip(request)]
    while hits and now - hits[0] > _WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= _LIMITS[kind]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "RATE_LIMITED", "message": "Terlalu banyak cubaan. Sila cuba lagi nanti."},
        )
    hits.append(now)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _bad(exc: engine.BookingError, code: int = status.HTTP_400_BAD_REQUEST) -> HTTPException:
    return HTTPException(status_code=code, detail={"error": exc.code, "message": exc.message})


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"error": "UNAVAILABLE", "message": "Sistem tempahan tidak dapat dihubungi. Sila cuba lagi."},
    )


def _check_uuid(value: str, what: str = "ID") -> str:
    if not _UUID_RE.match((value or "").strip()):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": f"{what} tidak dijumpai"},
        )
    return value.strip().lower()


async def _site_or_404(website_id: str) -> Dict[str, Any]:
    website_id = _check_uuid(website_id, "Website")
    site = await store.get_site(website_id)
    if site is None:
        raise _unavailable()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Website tidak dijumpai"},
        )
    return site


async def _owned_site(website_id: str, current_user: dict) -> Dict[str, Any]:
    site = await _site_or_404(website_id)
    if str(site.get("user_id")) != str(current_user.get("sub")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bukan website anda")
    return site


async def _settings(website_id: str) -> Dict[str, Any]:
    row = await store.get_settings(website_id)
    if row is None:
        raise _unavailable()
    return engine.normalize_settings(row)


def _service_view(row: Dict[str, Any], *, public: bool = False) -> Dict[str, Any]:
    view = {
        "id": row.get("id"),
        "name": row.get("name"),
        "description": row.get("description") or "",
        "duration_min": row.get("duration_min"),
        "price": float(row["price"]) if row.get("price") is not None else None,
    }
    if not public:
        view["active"] = bool(row.get("active", True))
        view["sort_order"] = row.get("sort_order", 0)
    return view


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class SettingsUpdate(BaseModel):
    enabled: bool = False
    slot_interval_min: int = Field(30, ge=5, le=240)
    capacity_per_slot: int = Field(1, ge=1, le=50)
    lead_time_min: int = Field(60, ge=0, le=10080)
    max_days_ahead: int = Field(30, ge=1, le=180)
    weekly_hours: Dict[str, List[Dict[str, str]]] = Field(default_factory=dict)
    closed_dates: List[str] = Field(default_factory=list)
    note: str = Field("", max_length=engine.MAX_NOTE_LEN)


class ServiceBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)
    duration_min: int = Field(30, ge=5, le=600)
    price: Optional[float] = Field(None, ge=0, le=100000)
    active: bool = True
    sort_order: int = Field(0, ge=0, le=1000)

    @field_validator("name", "description", mode="before")
    @classmethod
    def _strip(cls, v):
        return "" if v is None else str(v).strip()


class StatusBody(BaseModel):
    status: str


class BookingCreate(BaseModel):
    service_id: str
    date: str
    time: str
    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_phone: str = Field(..., min_length=7, max_length=20)
    notes: str = Field("", max_length=500)

    @field_validator("customer_name", "notes", mode="before")
    @classmethod
    def _strip(cls, v):
        return "" if v is None else str(v).strip()


class CancelBody(BaseModel):
    reference: str
    phone: str


# ---------------------------------------------------------------------------
# Merchant: settings
# ---------------------------------------------------------------------------

@router.get("/bookings/admin/{website_id}/settings")
async def get_booking_settings(website_id: str, current_user: dict = Depends(get_current_user)):
    site = await _owned_site(website_id, current_user)
    return {"website_id": site["id"], "settings": await _settings(site["id"])}


@router.put("/bookings/admin/{website_id}/settings")
async def update_booking_settings(
    website_id: str, body: SettingsUpdate, current_user: dict = Depends(get_current_user)
):
    site = await _owned_site(website_id, current_user)
    try:
        cleaned = engine.normalize_settings(body.model_dump(), strict=True)
    except engine.BookingError as exc:
        raise _bad(exc, 422)
    if cleaned["enabled"] and not engine.open_weekdays(cleaned):
        raise _bad(
            engine.BookingError("INVALID_HOURS", "Tetapkan sekurang-kurangnya satu hari operasi"),
            422,
        )
    saved = await store.save_settings(site["id"], cleaned)
    if saved is None:
        raise _unavailable()
    return {"website_id": site["id"], "settings": engine.normalize_settings(saved)}


# ---------------------------------------------------------------------------
# Merchant: services
# ---------------------------------------------------------------------------

@router.get("/bookings/admin/{website_id}/services")
async def list_booking_services(website_id: str, current_user: dict = Depends(get_current_user)):
    site = await _owned_site(website_id, current_user)
    rows = await store.list_services(site["id"])
    if rows is None:
        raise _unavailable()
    return {"services": [_service_view(r) for r in rows]}


@router.post("/bookings/admin/{website_id}/services", status_code=status.HTTP_201_CREATED)
async def create_booking_service(
    website_id: str, body: ServiceBody, current_user: dict = Depends(get_current_user)
):
    site = await _owned_site(website_id, current_user)
    existing = await store.list_services(site["id"])
    if existing is None:
        raise _unavailable()
    if len(existing) >= MAX_SERVICES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "TOO_MANY_SERVICES", "message": f"Maksimum {MAX_SERVICES} servis"},
        )
    row = await store.create_service(site["id"], body.model_dump())
    if row is None:
        raise _unavailable()
    return _service_view(row)


@router.put("/bookings/admin/{website_id}/services/{service_id}")
async def update_booking_service(
    website_id: str, service_id: str, body: ServiceBody,
    current_user: dict = Depends(get_current_user),
):
    site = await _owned_site(website_id, current_user)
    service_id = _check_uuid(service_id, "Servis")
    row = await store.update_service(site["id"], service_id, body.model_dump())
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Servis tidak dijumpai"},
        )
    return _service_view(row)


@router.delete("/bookings/admin/{website_id}/services/{service_id}")
async def delete_booking_service(
    website_id: str, service_id: str, current_user: dict = Depends(get_current_user)
):
    """Existing bookings keep the service's name, duration and price —
    those were copied onto each booking when it was made."""
    site = await _owned_site(website_id, current_user)
    service_id = _check_uuid(service_id, "Servis")
    if not await store.delete_service(site["id"], service_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Servis tidak dijumpai"},
        )
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Merchant: bookings
# ---------------------------------------------------------------------------

@router.get("/bookings/admin/{website_id}/bookings")
async def list_site_bookings(
    website_id: str,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
):
    site = await _owned_site(website_id, current_user)
    try:
        start = engine.parse_date(date_from) if date_from else engine.now_myt().date()
        end = engine.parse_date(date_to) if date_to else start + timedelta(days=30)
    except engine.BookingError as exc:
        raise _bad(exc, 422)
    if status_filter and status_filter not in engine.ALL_STATUSES:
        raise HTTPException(status_code=422, detail="Status tidak sah")
    rows = await store.list_bookings(
        site["id"], date_from=start.isoformat(), date_to=end.isoformat(), status=status_filter
    )
    if rows is None:
        raise _unavailable()
    return {
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "bookings": [_owner_booking_view(r) for r in rows],
    }


def _owner_booking_view(row: Dict[str, Any]) -> Dict[str, Any]:
    view = engine.public_booking_view(row)
    view.pop("customer_phone_masked", None)
    view.pop("can_cancel", None)
    view.update({
        "id": row.get("id"),
        "customer_phone": row.get("customer_phone"),
        "cancelled_by": row.get("cancelled_by"),
        "created_at": row.get("created_at"),
        "next_statuses": sorted(engine.STATUS_TRANSITIONS.get(row.get("status"), ())),
    })
    return view


@router.put("/bookings/admin/{website_id}/bookings/{booking_id}/status")
async def update_booking_status(
    website_id: str, booking_id: str, body: StatusBody,
    current_user: dict = Depends(get_current_user),
):
    site = await _owned_site(website_id, current_user)
    booking_id = _check_uuid(booking_id, "Tempahan")
    if body.status not in engine.ALL_STATUSES:
        raise HTTPException(status_code=422, detail="Status tidak sah")
    booking = await store.get_booking(site["id"], booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Tempahan tidak dijumpai"},
        )
    current = booking.get("status")
    if not engine.can_transition(current, body.status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "INVALID_TRANSITION",
                "message": f"Tempahan berstatus '{current}' tidak boleh ditukar kepada '{body.status}'",
            },
        )
    updated = await store.set_booking_status(
        site["id"], booking_id, from_status=current, to_status=body.status,
        cancelled_by="owner" if body.status == "cancelled" else None,
    )
    if not updated:
        # Someone else (the customer cancelling, another tab) got there first.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "STALE", "message": "Tempahan ini telah berubah. Sila muat semula."},
        )
    return _owner_booking_view(updated)


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

@router.get("/bookings/public/{website_id}")
async def public_booking_info(website_id: str):
    site = await _site_or_404(website_id)
    settings = await _settings(site["id"])
    services: List[Dict[str, Any]] = []
    if settings["enabled"]:
        rows = await store.list_services(site["id"], active_only=True)
        if rows is None:
            raise _unavailable()
        services = [_service_view(r, public=True) for r in rows]
    return {
        "website_id": site["id"],
        "business_name": site.get("business_name") or "",
        "enabled": bool(settings["enabled"] and services),
        "services": services,
        "open_weekdays": engine.open_weekdays(settings),
        "closed_dates": settings["closed_dates"],
        "max_days_ahead": settings["max_days_ahead"],
        "note": settings["note"],
        "today": engine.now_myt().date().isoformat(),
    }


async def _bookable_service(website_id: str, service_id: str) -> Dict[str, Any]:
    service = await store.get_service(website_id, _check_uuid(service_id, "Servis"))
    if not service or not service.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SERVICE_NOT_FOUND", "message": "Servis tidak dijumpai"},
        )
    return service


@router.get("/bookings/public/{website_id}/slots")
async def public_slots(website_id: str, service_id: str = Query(...), date: str = Query(...)):
    site = await _site_or_404(website_id)
    settings = await _settings(site["id"])
    if not settings["enabled"]:
        raise _bad(engine.BookingError("BOOKING_DISABLED", "Tempahan dalam talian belum dibuka"), 409)
    try:
        day = engine.parse_date(date)
    except engine.BookingError as exc:
        raise _bad(exc, 422)
    service = await _bookable_service(site["id"], service_id)
    problem = engine.date_problem(settings, day)
    if problem:
        return {"date": day.isoformat(), "slots": [], "reason": problem.code, "message": problem.message}
    existing = await store.list_bookings_for_date(site["id"], day.isoformat())
    if existing is None:
        raise _unavailable()
    slots = engine.generate_slots(settings, service["duration_min"], day, existing)
    return {
        "date": day.isoformat(),
        # Counts stay server-side: how busy a shop is, is the shop's business.
        "slots": [{"time": s["time"], "available": s["available"]} for s in slots],
        "reason": None,
        "message": None,
    }


@router.post("/bookings/public/{website_id}", status_code=status.HTTP_201_CREATED)
async def public_create_booking(website_id: str, body: BookingCreate, request: Request):
    _rate_limit("create", request)
    site = await _site_or_404(website_id)
    settings = await _settings(site["id"])
    try:
        phone = engine.normalize_phone(body.customer_phone)
        day = engine.parse_date(body.date)
    except engine.BookingError as exc:
        raise _bad(exc, 422)
    if not settings["enabled"]:
        raise _bad(engine.BookingError("BOOKING_DISABLED", "Tempahan dalam talian belum dibuka"), 409)
    service = await _bookable_service(site["id"], body.service_id)

    existing = await store.list_bookings_for_date(site["id"], day.isoformat())
    if existing is None:
        raise _unavailable()
    try:
        slot = engine.resolve_slot(settings, service["duration_min"], day, body.time, existing)
    except engine.BookingError as exc:
        raise _bad(exc, 409 if exc.code in ("SLOT_FULL", "SLOT_TOO_SOON") else 400)

    args = {
        "p_website_id": site["id"],
        "p_service_id": service["id"],
        "p_service_name": service["name"],
        "p_duration_min": service["duration_min"],
        "p_price": service.get("price"),
        "p_booking_date": day.isoformat(),
        "p_start_at": slot["start_at"],
        "p_end_at": slot["end_at"],
        "p_customer_name": body.customer_name,
        "p_customer_phone": phone,
        "p_notes": body.notes,
        "p_capacity": settings["capacity_per_slot"],
    }
    booking = None
    for _ in range(4):
        try:
            booking = await store.insert_booking({**args, "p_reference": engine.make_reference()})
            break
        except store.DuplicateReference:
            continue
        except store.SlotFull:
            raise _bad(
                engine.BookingError("SLOT_FULL", "Maaf, slot ini baru sahaja penuh. Sila pilih masa lain."),
                409,
            )
        except store.DuplicateBooking:
            raise _bad(
                engine.BookingError(
                    "DUPLICATE_BOOKING", "Nombor ini sudah ada tempahan pada masa tersebut."
                ),
                409,
            )
    if not booking:
        raise _unavailable()

    await _notify_owner(site, booking)
    logger.info(f"📅 Booking {booking.get('reference')} created for website {site['id']}")
    return engine.public_booking_view(booking)


async def _notify_owner(site: Dict[str, Any], booking: Dict[str, Any]) -> None:
    """Bell + WhatsApp, both best-effort."""
    owner_id = site.get("user_id")
    if not owner_id:
        return
    view = engine.public_booking_view(booking)
    summary = f"{view['service_name']} · {view['date']} {view['time']}"
    try:
        await store.notify_owner(
            str(owner_id), site["id"], "Tempahan Baru!",
            f"{booking.get('customer_name')} - {summary}",
            {"booking_id": booking.get("id"), "reference": booking.get("reference")},
        )
        phone = await store.get_owner_phone(str(owner_id))
        if phone:
            from fastapi.concurrency import run_in_threadpool
            from app.utils.whatsapp import send_whatsapp_message

            await run_in_threadpool(
                send_whatsapp_message,
                phone,
                f"Tempahan baru ({booking.get('reference')})\n"
                f"{booking.get('customer_name')} · {booking.get('customer_phone')}\n{summary}",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"📅 owner notification for booking failed: {exc}")


async def _customer_booking(website_id: str, reference: str, phone: str) -> Dict[str, Any]:
    """The booking, only if reference AND phone both match. A wrong phone
    answers exactly like a wrong reference."""
    not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "NOT_FOUND", "message": "Tempahan tidak dijumpai. Semak kod rujukan dan nombor telefon."},
    )
    try:
        ref = engine.clean_reference(reference)
        digits = engine.normalize_phone(phone)
    except engine.BookingError:
        raise not_found
    booking = await store.get_booking_by_reference(website_id, ref)
    if not booking or booking.get("customer_phone") != digits:
        raise not_found
    return booking


@router.get("/bookings/public/{website_id}/lookup")
async def public_lookup(
    website_id: str, request: Request, reference: str = Query(...), phone: str = Query(...)
):
    _rate_limit("lookup", request)
    site = await _site_or_404(website_id)
    return engine.public_booking_view(await _customer_booking(site["id"], reference, phone))


@router.post("/bookings/public/{website_id}/cancel")
async def public_cancel(website_id: str, body: CancelBody, request: Request):
    _rate_limit("cancel", request)
    site = await _site_or_404(website_id)
    booking = await _customer_booking(site["id"], body.reference, body.phone)
    if not engine.customer_can_cancel(booking):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CANNOT_CANCEL", "message": "Tempahan ini tidak boleh dibatalkan lagi."},
        )
    updated = await store.set_booking_status(
        site["id"], booking["id"], from_status=booking["status"],
        to_status="cancelled", cancelled_by="customer",
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "STALE", "message": "Tempahan ini telah berubah. Sila semak semula."},
        )
    return engine.public_booking_view(updated)
