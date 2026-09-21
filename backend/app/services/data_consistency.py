"""
Generate-time data consistency (Round 2, §B) — the checks that run on the
merchant's own inputs before Pass 1, so the page can never contradict
itself.

- **Location tokens.** The story said "Seksyen 18", the address field said
  "Seksyen 7", and the site printed both. ``location_conflicts`` extracts
  place tokens (Seksyen N, Taman X, Bandar X, city names) from the story and
  the address and reports every disagreement as a question the create page
  can put to the merchant. Generation is refused until the merchant picks.
- **Hours.** ``hours_are_24h`` recognises "00:00–23:59", "24 jam", "24/7",
  "setiap hari 24 jam"; ``normalize_hours`` turns the structured field into
  one canonical string. The open-now badge and the page copy both read the
  structured value — never prose.
- **Prices.** ``parse_price`` accepts what a merchant types ("RM6", "6.5",
  "RM 12,50") and rejects what a formatter cannot honour ("RM25.oo");
  ``format_price`` is the single renderer (``RM6.00``); ``find_bad_prices``
  is the HTML lint for ``RM\\d+\\.[^\\d]``.
- **Address.** ``normalize_address`` title-cases the lines, fixes the
  letter-digit/letter-digit typo (``l7/l`` → ``L7/1``), and keeps postcodes
  and state names as they are.

Pure module — no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Location tokens
# ---------------------------------------------------------------------------

_SEKSYEN_RE = re.compile(r"\b(?:seksyen|section|sek\.?|sec\.?)\s*(\d{1,3}[a-z]?)\b", re.IGNORECASE)
_NAMED_AREA_RE = re.compile(
    r"\b(taman|bandar|kampung|kg\.?|desa|pekan|jalan|lorong|persiaran|presint|precinct|bukit|kota|puncak|alam)\s+"
    r"([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,3})",
)
_CITIES = (
    "shah alam", "petaling jaya", "subang jaya", "kuala lumpur", "klang", "kajang", "bangi", "puchong",
    "cheras", "ampang", "gombak", "rawang", "sepang", "cyberjaya", "putrajaya", "seremban", "nilai",
    "melaka", "johor bahru", "skudai", "ipoh", "taiping", "penang", "george town", "bayan lepas",
    "butterworth", "alor setar", "sungai petani", "kota bharu", "kuala terengganu", "kuantan",
    "kuching", "kota kinabalu", "sandakan", "tawau", "miri", "sibu", "bintulu", "labuan", "langkawi",
    "seri kembangan", "batu caves", "selayang", "sungai buloh", "kepong", "wangsa maju", "setapak",
    "bukit jalil", "damansara", "mont kiara", "bangsar", "sri petaling", "kelana jaya", "ara damansara",
)


@dataclass(frozen=True)
class LocationToken:
    kind: str  # seksyen | area | city
    value: str  # canonical, lower-case ("18", "taman melawati", "shah alam")

    def label(self) -> str:
        if self.kind == "seksyen":
            return f"Seksyen {self.value.upper()}"
        return " ".join(w.capitalize() for w in self.value.split())


def location_tokens(text: Optional[str]) -> List[LocationToken]:
    """Every place token in ``text``, in order of appearance, de-duplicated."""
    out: List[LocationToken] = []
    if not text:
        return out
    seen = set()

    def _add(tok: LocationToken) -> None:
        if tok not in seen:
            seen.add(tok)
            out.append(tok)

    for m in _SEKSYEN_RE.finditer(text):
        _add(LocationToken("seksyen", m.group(1).lower()))
    for m in _NAMED_AREA_RE.finditer(text):
        kind_word = m.group(1).lower().rstrip(".")
        if kind_word in ("jalan", "lorong", "persiaran"):
            continue  # a street is not an area claim
        name = re.sub(r"\s+", " ", m.group(2)).strip().lower()
        # "Taman X" followed by a city on the same line: keep the first 1–3 words only.
        _add(LocationToken("area", f"{kind_word} {name}"))
    lowered = text.lower()
    for city in _CITIES:
        if re.search(r"\b" + re.escape(city) + r"\b", lowered):
            _add(LocationToken("city", city))
    return out


@dataclass
class LocationConflict:
    kind: str
    story_value: str
    address_value: str
    question_ms: str
    question_en: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "kind": self.kind,
            "story": self.story_value,
            "address": self.address_value,
            "question": self.question_ms,
            "question_en": self.question_en,
        }


def location_conflicts(story: Optional[str], address: Optional[str]) -> List[LocationConflict]:
    """Where the story and the address name different places of the same
    kind (a different Seksyen, a different Taman, a different city)."""
    story_tokens = location_tokens(story)
    address_tokens = location_tokens(address)
    if not story_tokens or not address_tokens:
        return []
    conflicts: List[LocationConflict] = []
    for kind in ("seksyen", "city", "area"):
        s_vals = [t for t in story_tokens if t.kind == kind]
        a_vals = [t for t in address_tokens if t.kind == kind]
        if not s_vals or not a_vals:
            continue
        a_set = {t.value for t in a_vals}
        for s in s_vals:
            if s.value in a_set:
                continue
            if kind == "area" and any(s.value in a or a in s.value for a in a_set):
                continue
            a = a_vals[0]
            conflicts.append(LocationConflict(
                kind=kind,
                story_value=s.label(),
                address_value=a.label(),
                question_ms=f"Cerita sebut {s.label()} tapi alamat {a.label()} — yang mana betul?",
                question_en=f"The story says {s.label()} but the address says {a.label()} — which is correct?",
            ))
            break  # one question per kind is enough
    return conflicts


def apply_location_resolution(
    story: str,
    address: str,
    resolution: Optional[Dict[str, str]],
) -> Tuple[str, str]:
    """``resolution`` = {kind: "story" | "address"} from the merchant. The
    losing side's token is rewritten to the winning value so the site can
    never carry both."""
    if not resolution:
        return story, address
    for conflict in location_conflicts(story, address):
        choice = str(resolution.get(conflict.kind) or "").lower()
        if choice == "story":
            address = _replace_token(address, conflict.address_value, conflict.story_value)
        elif choice == "address":
            story = _replace_token(story, conflict.story_value, conflict.address_value)
    return story, address


def scrub_location_tokens(html: str, fixups: Dict[str, str]) -> Tuple[str, int]:
    """Rewrite every losing location label (``{"Seksyen 7": "Seksyen 18"}``)
    in the page's visible text and attributes. Returns (html, count)."""
    out = html or ""
    total = 0
    for old_label, new_label in (fixups or {}).items():
        before = out
        out = _replace_token(out, old_label, new_label)
        if out != before:
            total += len(re.findall(re.escape(new_label), out, flags=re.IGNORECASE)) - len(re.findall(re.escape(new_label), before, flags=re.IGNORECASE))
    return out, max(total, 0)


def _replace_token(text: str, old_label: str, new_label: str) -> str:
    if old_label.lower().startswith("seksyen "):
        number = old_label.split(" ", 1)[1]
        pattern = re.compile(r"\b(seksyen|section|sek\.?)\s*" + re.escape(number) + r"\b", re.IGNORECASE)
        return pattern.sub(lambda m: f"{m.group(1)} {new_label.split(' ', 1)[1]}", text)
    return re.sub(re.escape(old_label), new_label, text, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# Hours
# ---------------------------------------------------------------------------

_ALWAYS_OPEN_RE = re.compile(
    r"\b24\s*(?:jam|hours?|hrs?)\b|\b24\s*/\s*7\b|\bopen\s+24\b|\bbuka\s+24\b|\bsepanjang\s+masa\b|\b24-?hour\b",
    re.IGNORECASE,
)
_RANGE_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|pagi|petang|malam)?\s*(?:-|–|—|hingga|to|sampai)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|pagi|petang|malam)?", re.IGNORECASE)


def _to_minutes(hour: str, minute: Optional[str], marker: Optional[str]) -> Optional[int]:
    h, m = int(hour), int(minute or 0)
    mk = (marker or "").lower()
    if h > 24 or m > 59:
        return None
    if mk in ("pm", "petang", "malam") and h < 12:
        h += 12
    elif mk in ("am", "pagi") and h == 12:
        h = 0
    return h * 60 + m


def hours_are_24h(*sources: Optional[str]) -> bool:
    """True when the structured hours or the story say the place never
    closes: 00:00–23:59 / 00:00–00:00 / 24 jam / 24/7."""
    for text in sources:
        if not text:
            continue
        if _ALWAYS_OPEN_RE.search(text):
            return True
        for m in _RANGE_RE.finditer(text):
            opens = _to_minutes(m.group(1), m.group(2), m.group(3))
            closes = _to_minutes(m.group(4), m.group(5), m.group(6))
            if opens is None or closes is None:
                continue
            if opens == 0 and closes in (0, 24 * 60, 23 * 60 + 59):
                return True
            if opens == closes:
                return True
    return False


_HOURS_2359_RE = re.compile(
    r"(?:buka\s+sekarang\s*[·\-–—]?\s*)?(?:tutup|closes?)\s*(?:pada\s+)?23[:.]59"
    r"|00[:.]00\s*(?:-|–|—|hingga|to|sampai)\s*(?:23[:.]59|00[:.]00|24[:.]00)"
    r"|12[:.]00\s*am\s*(?:-|–|—|to)\s*11[:.]59\s*pm",
    re.IGNORECASE,
)


def enforce_24h_copy(html: str, language: str = "ms") -> Tuple[str, int]:
    """A 24-hour business never reads "tutup 23:59" or "00:00 - 23:59" on
    the page: every such string in visible text becomes "Buka 24 jam"."""
    label = "Buka 24 jam" if not str(language or "ms").lower().startswith("en") else "Open 24 hours"
    count = 0

    def _text(segment: str) -> str:
        nonlocal count
        new, n = _HOURS_2359_RE.subn(label, segment)
        count += n
        return new

    parts = re.split(r"(<[^>]+>)", html or "")
    return "".join(p if p.startswith("<") else _text(p) for p in parts), count


@dataclass
class HoursInfo:
    is_24h: bool
    text: Optional[str]  # canonical hours text for the page (None = never render hours)
    source: str  # structured | story | none

    def as_dict(self) -> Dict[str, Any]:
        return {"is_24h": self.is_24h, "text": self.text, "source": self.source}


def normalize_hours(structured: Optional[str], story: Optional[str] = None, language: str = "ms") -> HoursInfo:
    """The one hours value the page may show. A structured field wins; the
    story can only contribute an explicit 24-hour claim."""
    ms = not str(language or "ms").lower().startswith("en")
    label_24 = "Buka 24 jam" if ms else "Open 24 hours"
    structured = (structured or "").strip()
    if structured:
        if hours_are_24h(structured):
            return HoursInfo(True, label_24, "structured")
        return HoursInfo(False, structured, "structured")
    if hours_are_24h(story):
        return HoursInfo(True, label_24, "story")
    return HoursInfo(False, None, "none")


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------

#: "RM6", "6.5", "RM 12,50", and a decimal with a unit ("RM18/pax", "12 / kg").
#: Either side of the separator may be empty — "24." is 24.00 and ".90" is
#: 0.90 — but not both: a lone "." is no price. The create page's field lets
#: a trailing or leading dot through (it only strips letters), and a merchant
#: who typed "24." was refused with "invalid_price" for a number any human
#: reads without hesitation.
_PRICE_INPUT_RE = re.compile(r"^\s*(?:rm)?\s*(\d{0,6})(?:[.,](\d{0,2}))?\s*(?:/\s*([a-z]{1,12}))?\s*$", re.IGNORECASE)
#: A price whose decimal part is not digits: "RM25.oo", "RM6.", "RM12.5x".
#: Same word-boundary guard as _PRICE_IN_TEXT_RE below: the "RM" at the end
#: of "transfoRM" is not a currency prefix.
BAD_PRICE_RE = re.compile(r"(?<![A-Za-z0-9])RM\s?\d+\.(?!\d)[^\s<,;]*")
#: Text that must never be substituted for a missing price.
PRICE_PLACEHOLDER_RE = re.compile(r"atas permintaan|price on request|hubungi (?:kami )?untuk harga|\bTBA\b", re.IGNORECASE)


def split_price(raw: Any) -> Optional[Tuple[Decimal, Optional[str]]]:
    """Merchant input → (Decimal, unit), or None when it is not a number.
    Never coerces letters to digits: "RM25.oo" is rejected, not read as
    25.00. A unit after a slash ("RM18/pax") is kept as the unit."""
    if raw is None:
        return None
    if isinstance(raw, (int, float, Decimal)):
        try:
            value = Decimal(str(raw))
        except InvalidOperation:
            return None
        return (value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), None) if value >= 0 else None
    m = _PRICE_INPUT_RE.match(str(raw))
    if not m:
        return None
    whole, frac, unit = m.group(1), m.group(2), m.group(3)
    if not whole and not frac:
        return None  # "", "RM", "." — nothing to read
    whole, frac = whole or "0", frac or "0"
    try:
        return Decimal(f"{whole}.{frac}").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), (unit.lower() if unit else None)
    except InvalidOperation:
        return None


def parse_price(raw: Any) -> Optional[Decimal]:
    """Merchant input → Decimal (unit dropped), or None when not a number."""
    parts = split_price(raw)
    return parts[0] if parts else None


def format_price(value: Any) -> Optional[str]:
    """The single renderer: ``RM6.00``, ``RM12.50``, ``RM18.00/pax``. None for no price."""
    if isinstance(value, Decimal):
        return f"RM{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
    parts = split_price(value)
    if parts is None:
        return None
    dec, unit = parts
    return f"RM{dec}" + (f"/{unit}" if unit else "")


def find_bad_prices(html: str) -> List[str]:
    """Every ``RM<digits>.<not a digit>`` in the page — the ``RM25.oo`` class of typo."""
    return [m.group(0) for m in BAD_PRICE_RE.finditer(html or "")]


#: An RM amount in visible copy. Two guards, both learned the hard way:
#:
#: ``(?<![A-Za-z0-9])`` — the match is case-insensitive, so the "rm" at the
#: end of ``transform`` matched, and ``transition: ... transform 0.2s ease``
#: was rewritten to ``transfoRM0.20s ease`` in the page's own <style> block.
#: Twice, on a live site. "RM" is a currency prefix, not a substring.
#:
#: ``(?![\d.])`` — don't take half of a longer number.
_PRICE_IN_TEXT_RE = re.compile(
    r"(?<![A-Za-z0-9])RM\s?\d{1,6}(?:[.,]\d{1,2})?(?:\s*/\s*[a-z]{1,12})?(?![\d.])",
    re.IGNORECASE,
)

#: Elements whose CONTENT is not prose. It sits between tags like any other
#: text, so a tag-splitting pass walks straight into it — which is how a
#: currency rule got to reach CSS at all.
_NON_PROSE_ELEMENTS = ("style", "script", "template", "textarea", "pre", "code", "svg")
_NON_PROSE_OPEN_RE = re.compile(
    r"^<\s*(" + "|".join(_NON_PROSE_ELEMENTS) + r")\b", re.IGNORECASE
)
_NON_PROSE_CLOSE_RE = re.compile(
    r"^<\s*/\s*(" + "|".join(_NON_PROSE_ELEMENTS) + r")\b", re.IGNORECASE
)


def reformat_prices(html: str) -> Tuple[str, int]:
    """Rewrite every RM amount in visible text through ``format_price``:
    ``RM6`` → ``RM6.00``, ``RM12,5`` → ``RM12.50``.

    Only prose is touched. Attribute values and URLs are left alone (the
    split keeps whole tags intact), and so is everything inside <style>,
    <script> and the other non-prose elements below — a currency pass has
    no business inside a stylesheet.
    """
    count = 0

    def _text(segment: str) -> str:
        nonlocal count

        def _sub(m: "re.Match") -> str:
            nonlocal count
            formatted = format_price(m.group(0))
            if formatted and formatted != m.group(0):
                count += 1
                return formatted
            return m.group(0)

        return _PRICE_IN_TEXT_RE.sub(_sub, segment)

    parts = re.split(r"(<[^>]+>)", html or "")
    out = []
    # Depth rather than a flag: <svg> nests, and a stray close tag must not
    # hand the rest of the document back to the rewriter.
    non_prose = 0
    for part in parts:
        if part.startswith("<"):
            if _NON_PROSE_CLOSE_RE.match(part):
                non_prose = max(0, non_prose - 1)
            elif _NON_PROSE_OPEN_RE.match(part) and not part.rstrip().endswith("/>"):
                non_prose += 1
            out.append(part)
            continue
        out.append(part if non_prose else _text(part))
    return "".join(out), count


# ---------------------------------------------------------------------------
# Address
# ---------------------------------------------------------------------------

_LOWER_WORDS = {"dan", "di", "off", "of", "the", "bin", "binti", "al"}
_UPPER_WORDS = {"kl", "pj", "usj", "ss", "sri", "ttdi", "ioi", "pkns", "mrr2", "ldp", "nkve", "plus", "jb", "kb"}
_STATE_WORDS = {
    "selangor", "kuala lumpur", "johor", "kedah", "kelantan", "melaka", "negeri sembilan", "pahang",
    "perak", "perlis", "pulau pinang", "penang", "sabah", "sarawak", "terengganu", "putrajaya", "labuan",
}
# "l7/l" and "Ll/l2" — a lot number typed with a lower-case L for a 1.
_LOT_TYPO_RE = re.compile(r"\b([A-Za-z])(\d+)/([lL])(\d*)\b")
_LOT_TYPO_RE_2 = re.compile(r"\b([lL])(\d+)/([lLA-Za-z])(\d*)\b")
_UNIT_RE = re.compile(r"^(?:no\.?|lot|unit|tingkat|blok|block)\s*[a-z0-9-]+", re.IGNORECASE)


def _title_word(word: str) -> str:
    lw = word.lower()
    if lw in _UPPER_WORDS:
        return word.upper()
    if lw in _LOWER_WORDS:
        return lw
    if re.fullmatch(r"\d+[a-z]?", lw):
        return lw.upper()
    if re.fullmatch(r"[a-z]{1,3}\d+[a-z]?(?:/[a-z0-9]+)?", lw):  # L7/1, B2, SS2, USJ9, J3/4
        return word.upper()
    if "-" in word:
        return "-".join(_title_word(p) for p in word.split("-"))
    if "/" in word:
        return "/".join(_title_word(p) for p in word.split("/"))
    return word[:1].upper() + word[1:].lower()


def normalize_address(raw: Optional[str]) -> str:
    """Title-cased, typo-fixed address text (still one string, commas kept)."""
    if not raw:
        return ""
    text = re.sub(r"\s+", " ", str(raw)).strip().strip(",")
    # Lot-number typos: a lower-case l where a 1 belongs after the slash.
    text = _LOT_TYPO_RE.sub(lambda m: f"{m.group(1).upper()}{m.group(2)}/1{m.group(4)}", text)
    text = _LOT_TYPO_RE_2.sub(lambda m: f"L{m.group(2)}/{('1' if m.group(3).lower() == 'l' else m.group(3).upper())}{m.group(4)}", text)
    pieces = [p.strip() for p in text.split(",")]
    out: List[str] = []
    for piece in pieces:
        if not piece:
            continue
        words = piece.split(" ")
        out.append(" ".join(_title_word(w) if w else w for w in words))
    return ", ".join(out)


def address_lines(raw: Optional[str]) -> List[str]:
    """Normalised address split into display lines (unit/street, area, postcode + city, state)."""
    normalized = normalize_address(raw)
    return [p for p in (s.strip() for s in normalized.split(",")) if p]
