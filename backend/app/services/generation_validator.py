"""Post-generation validator — the blocking gate before publish/preview.

Why this exists
---------------
Every degradation path in the generation pipeline was written as "silently
substitute something plausible and continue": five silent fallbacks on item
names, stock images on generation failure, a placeholder phone default, icon
glyph replacement, and a large CSS block patching layout failures. Nothing
failed loudly and nothing ever compared the OUTPUT against the INPUT — so a
brief with 25 priced items shipped a live site with four invented dishes and
no prices, and nobody found out until a human read the page.

This module is the missing comparison. It is a PURE FUNCTION of
(html, brief) -> ValidationResult. No I/O, no network, no globals, no
side effects, so it is trivially unit-testable and safe to call from any
generation path — GLM, DeepSeek, Qwen, or the pre-built template pipeline.

Severity contract
-----------------
ERROR   — the page is wrong in a way that damages the merchant (fabricated
          items, missing prices they supplied, a fake phone number). Callers
          MUST fail closed: block publish and surface the messages.
WARNING — the page is publishable but degraded (missing OG tags, mixed
          language, an empty container). Never blocks.

Checks that compare against merchant input only ERROR when the input actually
had the data. The validator never demands content the merchant never gave —
that would just push the generator back toward inventing it, which is the
defect this module exists to stop.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from app.services.reviews_policy import normalize_supplied_reviews
from app.utils.text_escapes import find_escape_leaks

# ---------------------------------------------------------------------------
# Phone helpers — shared with ai_service so the "what is a fake number"
# definition lives in exactly one place.
# ---------------------------------------------------------------------------

#: Known dummy/example numbers that must never reach a published page.
#: "60123456789" was the pipeline's own default and shipped on live sites.
PLACEHOLDER_PHONE_DIGITS = frozenset({
    "60123456789", "0123456789", "123456789", "601234567890",
    "60111111111", "60000000000", "1234567890", "60123456780",
    "60112345678", "60198765432", "60123456788",
})

_SEQUENTIAL_RUNS = ("0123456789", "9876543210")


def normalize_my_phone_digits(raw: Optional[str]) -> str:
    """Malaysian phone → digits-only, or '' when unusable.

    Returns '' for missing, too-short/too-long, repeated-digit, sequential
    and known-placeholder input. Callers MUST treat '' as "no usable number"
    and omit contact CTAs — never substitute an example number.
    """
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("0"):
        digits = "6" + digits
    elif digits.startswith("1"):
        digits = "60" + digits
    if len(digits) < 10 or len(digits) > 15:
        return ""
    if digits in PLACEHOLDER_PHONE_DIGITS:
        return ""
    body = digits[2:] if digits.startswith("60") else digits
    if len(set(body)) <= 1:
        return ""
    if any(body and body in run for run in _SEQUENTIAL_RUNS):
        return ""
    return digits


def is_placeholder_phone(raw: Optional[str]) -> bool:
    """True when this number must never be published."""
    digits = re.sub(r"\D", "", str(raw or ""))
    return bool(digits) and not normalize_my_phone_digits(digits)


# ---------------------------------------------------------------------------
# Inputs / outputs
# ---------------------------------------------------------------------------

#: Generic qualifiers the generator has been observed appending to a business
#: name to manufacture menu items ("Kak Ropiah A0" -> "Set Kak Ropiah A0").
GENERIC_ITEM_SUFFIXES = (
    "set", "combo", "istimewa", "special", "spesial", "pakej", "package",
    "deluxe", "premium", "classic", "original", "signature",
)

#: Shop-type / legal-entity nouns carrying no product identity — ignored when
#: testing whether an item name is "the business name plus a suffix".
BUSINESS_NAME_TYPE_WORDS = frozenset({
    "warung", "kedai", "restoran", "restaurant", "cafe", "kafe", "gerai",
    "stall", "bakery", "bakeri", "catering", "katering", "enterprise",
    "trading", "resources", "sdn", "bhd", "the", "shop", "store", "house",
    "and", "dan", "&",
})

#: The marker shipped when a merchant never supplied a business name.
#:
#: A missing name used to be filled with the first word of the description,
#: which for "Kedai makan di Shah Alam…" produced the brand "Kedai" across the
#: header, footer, copyright and <title> — a plausible-looking fake the
#: merchant never chose and might not notice. A placeholder that is obviously
#: unfilled in the page's own language is the honest substitute, and
#: `business_name_placeholder` below turns it into a publish blocker so it can
#: never go live.
BUSINESS_NAME_PLACEHOLDERS: Dict[str, str] = {
    "ms": "NAMA PERNIAGAAN ANDA",
    "en": "YOUR BUSINESS NAME",
}


def business_name_placeholder(language: Optional[str] = "ms") -> str:
    """The unfilled-business-name marker for `language` (default Malay)."""
    return BUSINESS_NAME_PLACEHOLDERS.get(
        (language or "ms").lower(), BUSINESS_NAME_PLACEHOLDERS["ms"]
    )


def is_business_name_placeholder(name: Optional[str]) -> bool:
    """True when `name` is an unfilled placeholder rather than a real name."""
    candidate = _norm(name)
    return bool(candidate) and any(
        candidate == _norm(marker) for marker in BUSINESS_NAME_PLACEHOLDERS.values()
    )


#: Bare section labels from a source brief (A0, B12) — never a product name.
_SECTION_LABEL_RE = re.compile(r"\b[a-z]\d{1,2}\b", re.IGNORECASE)

#: Clock times in supplied operating hours ("6:30", "7.00", "9 pagi", "5pm").
_TIME_RE = re.compile(
    r"\b\d{1,2}[:.]\d{2}\b|\b\d{1,2}\s*(?:am|pm|pagi|petang|malam|tgh)\b",
    re.IGNORECASE,
)

_EN_CTA_STRINGS = (
    "order now", "contact us", "read more", "learn more", "book now",
    "view menu", "get started", "our services", "about us", "send message",
    "shop now", "find us", "opening hours",
)
_MS_CTA_STRINGS = (
    "pesan sekarang", "hubungi kami", "lihat menu", "tempah sekarang",
    "laman utama", "tentang kami", "hantar mesej", "waktu operasi",
    "beli sekarang", "ketahui lebih",
)


@dataclass
class SanitizerRemoval:
    """One sensitive-claim removal and what replaced it (if anything)."""
    claim: str
    substitution: str = ""


@dataclass
class GenerationBrief:
    """The merchant-supplied ground truth a generation is checked against.

    Only fields the validator reads. Build one with brief_from_request().
    """
    business_name: str = ""
    description: str = ""
    language: str = "ms"
    whatsapp_number: Optional[str] = None
    location_address: Optional[str] = None
    operating_hours: Optional[str] = None
    menu_items: List[Dict[str, str]] = field(default_factory=list)
    #: Reviews the MERCHANT supplied. Empty means the page may not show a
    #: review at all — see _check_fabricated_reviews.
    reviews: List[Dict[str, Any]] = field(default_factory=list)
    sanitizer_removals: List[SanitizerRemoval] = field(default_factory=list)
    #: Which model produced the HTML — logged with the result so the fallback
    #: ordering can be tuned on real data rather than intuition.
    model: str = ""


@dataclass
class ValidationIssue:
    code: str
    message: str
    detail: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message, "detail": self.detail}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}" + (f" ({self.detail})" if self.detail else "")


@dataclass
class ValidationResult:
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    model: str = ""

    @property
    def ok(self) -> bool:
        """True when nothing blocks publish. Warnings do not block."""
        return not self.errors

    def error_messages(self) -> List[str]:
        return [str(e) for e in self.errors]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "model": self.model,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
        }


# ---------------------------------------------------------------------------
# HTML helpers — regex-based on purpose: the validator must never fail to run
# because of a parser dependency or malformed markup.
# ---------------------------------------------------------------------------

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", re.IGNORECASE | re.DOTALL)


def _strip_scripts(html: str) -> str:
    return _SCRIPT_STYLE_RE.sub(" ", html or "")


def visible_text(html: str) -> str:
    """Rendered text only — script/style contents excluded."""
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", _strip_scripts(html))).strip()


def _norm(s: str) -> str:
    """Lowercase, collapse whitespace — for tolerant containment checks."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _tokens(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (s or "").lower())


def heading_texts(html: str) -> List[str]:
    """Every heading's visible text — the generator renders card titles as
    <h3> (mandated by the prompt), so this is where fabricated item names
    surface."""
    out = []
    for raw in _HEADING_RE.findall(_strip_scripts(html)):
        text = re.sub(r"\s+", " ", _TAG_RE.sub(" ", raw)).strip()
        if text:
            out.append(text)
    return out


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_placeholder_contacts(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """1. Placeholder contacts — ERROR.

    A published site whose WhatsApp link points at a dummy number is a dead
    business, so any placeholder-looking wa.me/tel: number blocks publish.
    """
    issues: List[ValidationIssue] = []
    seen: set = set()

    for match in re.finditer(r"wa\.me/\+?([0-9\s\-()]{6,20})", html or "", re.IGNORECASE):
        raw = match.group(1)
        digits = re.sub(r"\D", "", raw)
        if not digits or digits in seen:
            continue
        seen.add(digits)
        if is_placeholder_phone(digits) or not digits:
            issues.append(ValidationIssue(
                "placeholder_whatsapp",
                "WhatsApp link uses a placeholder or unusable number",
                f"wa.me/{digits}",
            ))

    for match in re.finditer(r"tel:\+?([0-9\s\-()]{6,20})", html or "", re.IGNORECASE):
        digits = re.sub(r"\D", "", match.group(1))
        if not digits or digits in seen:
            continue
        seen.add(digits)
        if is_placeholder_phone(digits):
            issues.append(ValidationIssue(
                "placeholder_phone",
                "Telephone link uses a placeholder number",
                f"tel:{digits}",
            ))

    # An empty href is just as broken as a fake one.
    if re.search(r"wa\.me/[\"'\s>]", html or "", re.IGNORECASE):
        issues.append(ValidationIssue(
            "empty_whatsapp_link", "WhatsApp link has no number", "wa.me/"
        ))
    return issues


def _check_derived_item_names(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """2. Derived item names — ERROR.

    Catches the Warung Kak Ropiah class directly: headings that are the
    business name plus a generic qualifier ("Set Kak Ropiah A0"), and any
    heading carrying a source-brief section label ("A0").

    Names the merchant actually supplied are always allowed, however odd —
    if they list an item called "Set A", that is their data, not fabrication.
    """
    issues: List[ValidationIssue] = []
    supplied = {_norm(i.get("name", "")) for i in (brief.menu_items or []) if i.get("name")}

    biz_tokens = {
        t for t in _tokens(brief.business_name)
        if t not in BUSINESS_NAME_TYPE_WORDS and len(t) > 1
    }

    for heading in heading_texts(html):
        key = _norm(heading)
        if not key or key in supplied:
            continue
        h_tokens = set(_tokens(heading))

        # (a) business name + generic suffix
        if biz_tokens and biz_tokens.issubset(h_tokens):
            extra = h_tokens - biz_tokens
            if extra and any(s in extra for s in GENERIC_ITEM_SUFFIXES):
                issues.append(ValidationIssue(
                    "fabricated_item_name",
                    "Item name is the business name plus a generic qualifier",
                    heading,
                ))
                continue

        # (b) source-brief artefact (bare section label)
        label = _SECTION_LABEL_RE.search(heading)
        if label and not re.fullmatch(r"[a-z]\d{1,2}", key):
            # Ignore genuine product codes the merchant supplied (handled by
            # the `supplied` check above) — anything else is brief residue.
            issues.append(ValidationIssue(
                "section_label_in_item_name",
                "Item name contains a source-brief section label",
                f"{heading} (label: {label.group(0)})",
            ))
    return issues


def _check_price_integrity(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """3. Price integrity — ERROR.

    Compares against the INPUT, never a regex for "RM": the failure mode was
    a page full of confident prose with every supplied price silently gone.
    """
    issues: List[ValidationIssue] = []
    text = _norm(visible_text(html))
    # Tags stripped BEFORE collapsing, so a price split across elements
    # (RM<span>7.00</span>) still counts as present.
    compact = re.sub(r"\s+", "", text)

    for item in (brief.menu_items or []):
        price = (item.get("price") or "").strip()
        if not price:
            continue
        needle = _norm(price)
        if needle in text or re.sub(r"\s+", "", needle) in compact:
            continue
        issues.append(ValidationIssue(
            "missing_price",
            "A supplied price is missing from the page",
            f"{item.get('name', '?')}: {price}",
        ))
    return issues


def _check_required_fields(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """4. Required fields — ERROR.

    Location and hours are only required when the merchant supplied them:
    demanding content that was never provided would push the generator back
    toward inventing an address, which is the defect this module prevents.
    """
    issues: List[ValidationIssue] = []
    text = _norm(visible_text(html))
    raw = _norm(html)

    if brief.business_name and _norm(brief.business_name) not in text:
        issues.append(ValidationIssue(
            "missing_business_name",
            "Business name does not appear on the page",
            brief.business_name,
        ))

    has_contact = any((
        "wa.me/" in raw,
        "tel:" in raw,
        "mailto:" in raw,
        "<form" in raw,
        "binaapp-contact-slot" in raw,
    ))
    if not has_contact:
        issues.append(ValidationIssue(
            "no_contact_method",
            "Page offers no way to contact the business",
            "expected a wa.me/tel:/mailto: link or a contact form",
        ))

    if brief.location_address:
        # Match on the most distinctive tokens rather than the whole string —
        # the generator legitimately reformats an address across lines.
        addr_tokens = [t for t in _tokens(brief.location_address) if len(t) > 3]
        hits = sum(1 for t in addr_tokens if t in text)
        if addr_tokens and hits < max(1, len(addr_tokens) // 2):
            issues.append(ValidationIssue(
                "missing_location",
                "Supplied address does not appear on the page",
                brief.location_address,
            ))

    if brief.operating_hours:
        # Match on the TIMES, not the surrounding words: "Cawangan Jalan Ipoh
        # 6:30-15:00" shares "jalan"/"ipoh" with the address, so a word-level
        # check passed even when every opening time had been dropped.
        times = _TIME_RE.findall(brief.operating_hours)
        if times:
            present = sum(1 for t in times if _norm(t).replace(" ", "") in
                          re.sub(r"\s+", "", text))
            missing = len(times) - present
            if present < max(1, len(times) // 2):
                issues.append(ValidationIssue(
                    "missing_operating_hours",
                    "Supplied operating hours do not appear on the page",
                    f"{missing} of {len(times)} time(s) missing: {brief.operating_hours}",
                ))
        else:
            hour_tokens = [t for t in _tokens(brief.operating_hours) if len(t) > 2]
            if hour_tokens and not any(t in text for t in hour_tokens):
                issues.append(ValidationIssue(
                    "missing_operating_hours",
                    "Supplied operating hours do not appear on the page",
                    brief.operating_hours,
                ))
    return issues


def _check_empty_containers(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """5. Empty containers — WARNING."""
    issues: List[ValidationIssue] = []
    body = _strip_scripts(html or "")

    empty_imgs = len(re.findall(r"<img\b(?![^>]*\bsrc\s*=\s*[\"'][^\"'\s]+)[^>]*>", body, re.IGNORECASE))
    if empty_imgs:
        issues.append(ValidationIssue(
            "empty_image", f"{empty_imgs} <img> tag(s) with no usable src", ""
        ))

    if re.search(r"url\(\s*[\"']?\s*[\"']?\s*\)", body, re.IGNORECASE):
        issues.append(ValidationIssue(
            "empty_background_url", "A CSS background url() is empty", ""
        ))

    # Injection slots that render as a blank box when the widget never loads.
    for slot in re.finditer(
        r"<(\w+)[^>]*id=[\"']([\w-]*slot[\w-]*)[\"'][^>]*>(.*?)</\1>",
        body, re.IGNORECASE | re.DOTALL,
    ):
        if not visible_text(slot.group(3)):
            issues.append(ValidationIssue(
                "empty_injection_slot",
                "Injection slot has no fallback content",
                f"#{slot.group(2)}",
            ))
    return issues


_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r"""([a-zA-Z_:][-\w:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")


def meta_content(html: str, name: str) -> Optional[str]:
    """The `content` of the first <meta name="..."> tag, or None.

    Attribute-order agnostic on purpose: the publish path runs the HTML
    through html5lib first, which re-emits `<meta content="…" name="…">`, and
    an order-sensitive regex reported a description that was plainly there as
    missing.
    """
    target = name.lower()
    for tag in _META_TAG_RE.finditer(html or ""):
        attrs = {
            m.group(1).lower(): (m.group(2) or m.group(3) or m.group(4) or "")
            for m in _ATTR_RE.finditer(tag.group())
        }
        if attrs.get("name", "").strip().lower() == target:
            return attrs.get("content", "")
    return None


def _check_required_metadata(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """6a. Title and meta description must EXIST and be non-empty — ERROR.

    These were warnings, which is how a site shipped with an empty <title>:
    the tab reads as the bare URL and the WhatsApp share preview has no name.
    Neither needs merchant data to be certain — the page either has them or it
    does not — so both also block at publish.
    """
    issues: List[ValidationIssue] = []
    head = html or ""

    title = _TITLE_RE.search(head)
    if not title or not title.group(1).strip():
        issues.append(ValidationIssue("missing_title", "Page has no <title>", ""))

    desc = meta_content(head, "description")
    if not (desc or "").strip():
        issues.append(ValidationIssue(
            "missing_meta_description", "No meta description", ""
        ))
    return issues


def _check_metadata(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """6b. Discoverability metadata — WARNING. Malaysian SMEs share via
    WhatsApp; without OG tags the link previews as a bare URL."""
    issues: List[ValidationIssue] = []
    head = html or ""

    desc = (meta_content(head, "description") or "").strip()
    if len(desc) > 160:
        issues.append(ValidationIssue(
            "long_meta_description",
            "Meta description exceeds 160 characters",
            f"{len(desc)} chars",
        ))

    for prop in ("og:title", "og:description", "og:image", "og:url"):
        if not re.search(
            rf"<meta\b[^>]*(?:property|name)=[\"']{re.escape(prop)}[\"']",
            head, re.IGNORECASE,
        ):
            issues.append(ValidationIssue("missing_og_tag", f"Missing {prop}", prop))

    ld = re.findall(
        r"<script\b[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        head, re.IGNORECASE | re.DOTALL,
    )
    if not ld:
        issues.append(ValidationIssue("missing_json_ld", "No JSON-LD structured data", ""))
    else:
        for block in ld:
            try:
                json.loads(block.strip())
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    "invalid_json_ld", "JSON-LD block is not parseable", block.strip()[:80]
                ))
                break
    return issues


def _check_language_consistency(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """7. Language consistency — WARNING."""
    issues: List[ValidationIssue] = []
    lang_attr = re.search(r"<html\b[^>]*\blang=[\"']([^\"']+)[\"']", html or "", re.IGNORECASE)
    lang = (lang_attr.group(1) if lang_attr else brief.language or "ms").lower()
    text = _norm(visible_text(html))

    if lang.startswith("ms"):
        found = sorted({s for s in _EN_CTA_STRINGS if s in text})
        if found:
            issues.append(ValidationIssue(
                "mixed_language_cta",
                "English CTA text on a Bahasa Malaysia page",
                ", ".join(found[:5]),
            ))
    elif lang.startswith("en"):
        found = sorted({s for s in _MS_CTA_STRINGS if s in text})
        if found:
            issues.append(ValidationIssue(
                "mixed_language_cta",
                "Bahasa Malaysia CTA text on an English page",
                ", ".join(found[:5]),
            ))
    return issues


#: Quantified trust claims the generator invents to fill fixed-slot layouts.
#: Each pattern captures the number so it can be checked against the brief.
_INVENTED_METRIC_PATTERNS = (
    # No trailing lookahead here: an adjacent stat cell ("15+ Tahun 1000+
    # Pelanggan") made a (?!\s*\d) guard reject the very case it must catch.
    ("years_in_business",
     re.compile(r"\b(\d{1,3})\s*\+\s*(?:tahun|years?)\b"
                r"|\b(\d{1,3})\s+(?:tahun|years?)\s+(?:pengalaman|experience|beroperasi)\b",
                re.IGNORECASE)),
    ("customer_count",
     re.compile(r"\b(\d[\d,\.]{1,9})\s*\+?\s*(?:pelanggan|customers?|clients?|"
                r"pesanan|orders?|jualan)\b", re.IGNORECASE)),
    ("rating",
     re.compile(r"\b([0-5][.,]\d)\s*(?:★|\/\s*5|bintang|stars?|rating)\b", re.IGNORECASE)),
    ("review_count",
     re.compile(r"\b(\d[\d,\.]{1,9})\s*\+?\s*(?:ulasan|reviews?|testimoni)\b", re.IGNORECASE)),
)


def _check_invented_metrics(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """Quantified claims not present in the brief — WARNING.

    The generator pads 3-up stat rows with numbers it made up ("15+ Tahun" on
    a business that never stated a founding year). These are trust claims a
    customer will read as fact.

    WARNING rather than ERROR on purpose: a number can legitimately reach the
    page through a supplied menu item or address, and the brief this runs
    against at publish time is weak. It flags for review without blocking a
    merchant whose data genuinely contains the figure.
    """
    issues: List[ValidationIssue] = []
    text = visible_text(html)
    source = " ".join(filter(None, [
        brief.description or "",
        brief.business_name or "",
        brief.operating_hours or "",
        brief.location_address or "",
        " ".join(f"{i.get('name','')} {i.get('price','')}" for i in (brief.menu_items or [])),
    ]))
    source_numbers = set(re.findall(r"\d[\d,\.]*", source))

    for code, pattern in _INVENTED_METRIC_PATTERNS:
        for match in pattern.finditer(text):
            # Patterns may have alternate capture groups; take whichever fired.
            number = next((g for g in match.groups() if g), "")
            if not number or number in source_numbers:
                continue
            issues.append(ValidationIssue(
                "invented_metric",
                f"Quantified claim ({code.replace('_', ' ')}) not present in the brief",
                match.group(0).strip(),
            ))
    return issues


def _check_sanitizer_trace(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """8. Sanitizer trace — ERROR on bare deletion.

    Stripping an unverified halal/certification claim is correct; deleting it
    and leaving nothing is not. For a Malay F&B site that trust signal is the
    highest-value element on the page, so a removal must always leave
    approved wording behind.
    """
    issues: List[ValidationIssue] = []
    for removal in (brief.sanitizer_removals or []):
        if not (removal.substitution or "").strip():
            issues.append(ValidationIssue(
                "sanitizer_bare_deletion",
                "Sanitizer removed a claim without substituting approved wording",
                removal.claim,
            ))
    return issues


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _check_escape_leaks(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """10. No backslash character escapes in the rendered page — ERROR.

    A site shipped with 17 literal `\\u2014` and `\\U0001f4f1` sequences in its
    visible text, including the <title> and the meta description. Contents of
    <script>/<style> are exempt: an escape there is legitimate source code.
    """
    leaks = find_escape_leaks(html or "")
    return [
        ValidationIssue(
            "unicode_escape_leak",
            "Backslash escape sequence rendered as visible text",
            snippet,
        )
        for snippet in leaks
    ]


#: Template tokens that must never survive into a rendered page. `{{name}}`
#: (the deterministic renderer), `[BUSINESS_NAME]` and `HERO_IMAGE_URL` (the
#: LLM prompt skeletons), `${...}` (a JS template literal that never ran).
_PLACEHOLDER_TOKEN_RES = (
    re.compile(r"\{\{\s*[a-z0-9_.\-]+\s*\}\}", re.IGNORECASE),
    re.compile(r"\[[A-Z][A-Z0-9_]{3,}\]"),
    re.compile(r"\b(?:HERO|GALLERY|PHOTO)_(?:IMAGE_URL|SLOT_\d+)\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]*_(?:PLACEHOLDER|ALT_TEXT|URL)\b"),
    re.compile(r"\$\{\s*[a-z0-9_.\-]+\s*\}", re.IGNORECASE),
    re.compile(r"\blorem ipsum\b", re.IGNORECASE),
)

#: Developer-facing captions that describe a feature instead of providing it.
#: The contact section shipped a dead grey box reading "Peta lokasi akan
#: dipaparkan di sini" — a note to the implementer rendered to the customer.
_DEAD_PLACEHOLDER_TEXT_RES = (
    re.compile(r"akan dipaparkan di sini", re.IGNORECASE),
    re.compile(r"akan (?:datang|ditambah) (?:di sini|kemudian)", re.IGNORECASE),
    re.compile(r"will be (?:displayed|shown|added) here", re.IGNORECASE),
    re.compile(r"\bmap (?:placeholder|goes here)\b", re.IGNORECASE),
    re.compile(r"\b(?:image|content|text) goes here\b", re.IGNORECASE),
)
# NOTE: "coming soon" / "akan datang" on their own are deliberately NOT here.
# Real merchants write them about real things ("menu baru akan datang"), and
# this list blocks a publish — every entry has to be a caption only a
# developer would write.


def _check_unresolved_placeholders(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """11. No unresolved template tokens or dead placeholder copy — ERROR.

    Both failure modes reach the customer as visible text, and neither needs
    merchant data to recognise, so both block at publish too.
    """
    issues: List[ValidationIssue] = []
    markup = _strip_scripts(html or "")
    text = visible_text(html or "")

    for pattern in _PLACEHOLDER_TOKEN_RES:
        match = pattern.search(markup)
        if match:
            issues.append(ValidationIssue(
                "unresolved_placeholder",
                "Unresolved template placeholder in page",
                match.group()[:80],
            ))

    for pattern in _DEAD_PLACEHOLDER_TEXT_RES:
        match = pattern.search(text)
        if match:
            lo = max(0, match.start() - 40)
            issues.append(ValidationIssue(
                "dead_placeholder_text",
                "Placeholder caption rendered instead of real content",
                text[lo:match.end() + 40].strip()[:120],
            ))
    return issues


def _check_business_name_placeholder(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """12. The unfilled-business-name marker must not be published — ERROR.

    Deliberately a blocker rather than a silent substitution: a merchant who
    never gave us a name gets an obviously-unfilled page they must complete,
    not a page branded with a generic word we picked for them.
    """
    if not any(
        _norm(marker) in _norm(visible_text(html or ""))
        for marker in BUSINESS_NAME_PLACEHOLDERS.values()
    ):
        return []
    return [ValidationIssue(
        "business_name_placeholder",
        "Business name was never supplied — the page still shows the placeholder",
        "Set the business name before publishing",
    )]


#: Section wrappers that hold customer reviews, by id/class.
_REVIEW_SECTION_RE = re.compile(
    r"<(section|div)\b[^>]*(?:id|class)=[\"'][^\"']*"
    r"(?:testimoni|testimonial|review|ulasan|kata-pelanggan)"
    r"[^\"']*[\"'][^>]*>(.*?)</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)

#: A quoted sentence long enough to be a review rather than a label. Matches
#: the three ways the generators render one: HTML entities (&ldquo;…&rdquo;),
#: typographic quotes, and straight quotes.
_QUOTED_ATTRIBUTION_RE = re.compile(
    r"&ldquo;[^<]{25,}?&rdquo;"
    r"|&quot;[^<]{25,}?&quot;"
    r"|[\u201c\u2018][^<\u201d\u2019]{25,}?[\u201d\u2019]"
    r"|\"[^<\"]{25,}?\"",
    re.DOTALL,
)


def _check_fabricated_reviews(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """13. No invented customer reviews — ERROR (generation time only).

    The generator was writing three named customers with quotes onto every
    site, for merchants who supplied none. A fabricated endorsement on a real
    business's page is a trust problem and, published as-is, a potential legal
    one — so with no supplied reviews, a review-shaped block is a defect.

    NOT enforced at publish: there the brief is unknown, and a merchant who
    has since pasted in their real reviews must not be blocked by them.
    """
    if brief.reviews:
        return []

    issues: List[ValidationIssue] = []
    for match in _REVIEW_SECTION_RE.finditer(_strip_scripts(html or "")):
        body = match.group(2)
        # The quote search runs on the RENDERED TEXT, never the markup: a
        # long class list or href inside a quoted attribute is not a customer
        # saying something. Star markup is a class, so that one reads the tags.
        quote = _QUOTED_ATTRIBUTION_RE.search(visible_text(body))
        has_stars = bool(re.search(r"fa-star|★|&#9733;", body, re.IGNORECASE))
        if quote or has_stars:
            issues.append(ValidationIssue(
                "fabricated_testimonial",
                "Testimonial section contains reviews the merchant never supplied",
                re.sub(r"\s+", " ", visible_text(body))[:160],
            ))
            break
    return issues


_ERROR_CHECKS = (
    _check_placeholder_contacts,
    _check_derived_item_names,
    _check_price_integrity,
    _check_required_fields,
    _check_sanitizer_trace,
    _check_escape_leaks,
    _check_required_metadata,
    _check_unresolved_placeholders,
    _check_business_name_placeholder,
    _check_fabricated_reviews,
)
_WARNING_CHECKS = (
    _check_empty_containers,
    _check_metadata,
    _check_language_consistency,
    _check_invented_metrics,
)


def validate_generated_site(html: str, brief: GenerationBrief) -> ValidationResult:
    """Validate generated HTML against the merchant's own brief.

    Pure function — no I/O, no globals, no mutation of its arguments.

    An individual check that raises is downgraded to a warning rather than
    taking the generation down: a bug in the validator must never become an
    outage, and a check that cannot run is a check that found nothing.
    """
    result = ValidationResult(model=brief.model or "")

    if not (html or "").strip():
        result.errors.append(ValidationIssue("empty_html", "Generated HTML is empty", ""))
        return result

    for check in _ERROR_CHECKS:
        try:
            result.errors.extend(check(html, brief))
        except Exception as err:  # pragma: no cover - defensive
            result.warnings.append(ValidationIssue(
                "check_failed", f"Validator check {check.__name__} failed", str(err)
            ))
    for check in _WARNING_CHECKS:
        try:
            result.warnings.extend(check(html, brief))
        except Exception as err:  # pragma: no cover - defensive
            result.warnings.append(ValidationIssue(
                "check_failed", f"Validator check {check.__name__} failed", str(err)
            ))
    return result


#: Error codes safe to enforce when only a WEAK brief is available.
#:
#: The validator's power scales with how much ground truth it is given. At
#: generation time we have the full request (menu items, prices, phone,
#: address) and every check is meaningful. At publish time the payload is
#: arbitrary — possibly hand-edited — HTML plus a project name, so checks
#: like "business name must appear" or "must have a contact method" would
#: block legitimate pages (a logo image instead of text, a renamed site).
#:
#: These codes need no merchant data to be certain: the page itself contains
#: something demonstrably fake.
PUBLISH_ENFORCED_CODES = frozenset({
    "placeholder_whatsapp",
    "placeholder_phone",
    "empty_whatsapp_link",
    "fabricated_item_name",
    "section_label_in_item_name",
    # The page itself is demonstrably unfinished, whatever the brief said:
    # a backslash escape rendered as text, a template token that never
    # resolved, a developer caption, a missing <title>/description, or the
    # business-name placeholder the merchant still has to fill in.
    "unicode_escape_leak",
    "unresolved_placeholder",
    "dead_placeholder_text",
    "missing_title",
    "missing_meta_description",
    "business_name_placeholder",
})


def blocking_errors(result: ValidationResult, enforced: Optional[frozenset] = None) -> List[ValidationIssue]:
    """Errors that should block, filtered to `enforced` codes.

    Pass PUBLISH_ENFORCED_CODES on the publish path; omit `enforced` at
    generation time, where the full brief makes every check trustworthy.
    """
    if enforced is None:
        return list(result.errors)
    return [e for e in result.errors if e.code in enforced]


def brief_from_request(
    request: Any,
    sanitizer_removals: Optional[Iterable[Any]] = None,
    model: str = "",
    operating_hours: Optional[str] = None,
) -> GenerationBrief:
    """Build a GenerationBrief from a WebsiteGenerationRequest.

    Tolerant by design: accepts anything with the expected attributes, and
    normalises MenuItemInput models or plain dicts. Never raises — a brief
    that cannot be built fully still validates what it can.
    """
    def _attr(name, default=None):
        return getattr(request, name, default)

    items: List[Dict[str, str]] = []
    for raw in (_attr("menu_items") or []):
        try:
            if hasattr(raw, "model_dump"):
                d = raw.model_dump()
            elif hasattr(raw, "dict"):
                d = raw.dict()
            elif isinstance(raw, dict):
                d = raw
            elif isinstance(raw, str):
                d = {"name": raw}
            else:
                continue
            name = str(d.get("name") or "").strip()
            if not name:
                continue
            items.append({
                "name": name,
                "price": str(d.get("price") or "").strip(),
                "category": str(d.get("category") or "").strip(),
            })
        except Exception:
            continue

    removals: List[SanitizerRemoval] = []
    for raw in (sanitizer_removals or []):
        if isinstance(raw, SanitizerRemoval):
            removals.append(raw)
        elif isinstance(raw, dict):
            removals.append(SanitizerRemoval(
                claim=str(raw.get("claim", "")),
                substitution=str(raw.get("substitution", "")),
            ))
        elif isinstance(raw, str):
            # Legacy trace format: a bare claim string means bare deletion.
            removals.append(SanitizerRemoval(claim=raw, substitution=""))

    language = _attr("language", "ms")
    language = getattr(language, "value", language) or "ms"

    return GenerationBrief(
        business_name=str(_attr("business_name", "") or ""),
        description=str(_attr("description", "") or ""),
        language=str(language),
        whatsapp_number=_attr("whatsapp_number"),
        location_address=_attr("location_address"),
        operating_hours=operating_hours,
        menu_items=items,
        reviews=normalize_supplied_reviews(_attr("testimonials")),
        sanitizer_removals=removals,
        model=model,
    )
