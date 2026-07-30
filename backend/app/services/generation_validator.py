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


def _check_metadata(html: str, brief: GenerationBrief) -> List[ValidationIssue]:
    """6. Metadata — WARNING. Malaysian SMEs share via WhatsApp; without OG
    tags the link previews as a bare URL."""
    issues: List[ValidationIssue] = []
    head = html or ""

    title = re.search(r"<title\b[^>]*>(.*?)</title>", head, re.IGNORECASE | re.DOTALL)
    if not title or not title.group(1).strip():
        issues.append(ValidationIssue("missing_title", "Page has no <title>", ""))

    desc = re.search(
        r"<meta\b[^>]*name=[\"']description[\"'][^>]*content=[\"']([^\"']*)[\"']",
        head, re.IGNORECASE,
    )
    if not desc or not desc.group(1).strip():
        issues.append(ValidationIssue("missing_meta_description", "No meta description", ""))
    elif len(desc.group(1).strip()) > 160:
        issues.append(ValidationIssue(
            "long_meta_description",
            "Meta description exceeds 160 characters",
            f"{len(desc.group(1).strip())} chars",
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

_ERROR_CHECKS = (
    _check_placeholder_contacts,
    _check_derived_item_names,
    _check_price_integrity,
    _check_required_fields,
    _check_sanitizer_trace,
)
_WARNING_CHECKS = (
    _check_empty_containers,
    _check_metadata,
    _check_language_consistency,
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
        sanitizer_removals=removals,
        model=model,
    )
