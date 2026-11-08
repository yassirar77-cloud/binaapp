"""The copy the AI writes for a composed page — and nothing else.

A small JSON object with hard length caps. Every field is plain text:
tags are stripped, whitespace collapsed, over-long values cut at a word.
Anything that looks invented (an RM amount or a phone number the brief
does not contain, a placeholder token) drops the field back to the
deterministic fallback, which is built from the merchant's own words.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.sections.spec import SiteSpec

LIMITS = {
    "kicker": 32,
    "headline": 64,
    "subheadline": 150,
    "menu_lead": 120,
    "about_title": 44,
    "about_paragraph": 340,
    "tagline": 90,
    "contact_lead": 120,
}
MAX_ABOUT_PARAGRAPHS = 3

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PLACEHOLDER_RE = re.compile(r"\{\{|\}\}|\[(?:ISI|INSERT|YOUR|NAMA)|lorem ipsum|contoh:", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"RM\s?\d[\d,]*(?:\.\d{1,2})?", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?6?0)?1\d[\s-]?\d{3,4}[\s-]?\d{4}(?!\d)")
_YEAR_RE = re.compile(r"\b(?:sejak|since|est\.?|established)\s*(?:tahun\s*)?(19|20)\d{2}\b", re.IGNORECASE)
_RATING_RE = re.compile(r"\b\d(?:[.,]\d)?\s*/\s*5\b|\b\d{2,}\s*%|\b\d[\d,]*\+?\s*(?:pelanggan|customers|reviews|ulasan)", re.IGNORECASE)


@dataclass
class Copy:
    kicker: str = ""
    headline: str = ""
    subheadline: str = ""
    menu_lead: str = ""
    about_title: str = ""
    about_paragraphs: List[str] = field(default_factory=list)
    tagline: str = ""
    contact_lead: str = ""
    source: str = "ai"          # ai | fallback | mixed
    rejected: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kicker": self.kicker, "headline": self.headline, "subheadline": self.subheadline,
            "menu_lead": self.menu_lead, "about_title": self.about_title,
            "about_paragraphs": list(self.about_paragraphs), "tagline": self.tagline,
            "contact_lead": self.contact_lead, "source": self.source, "rejected": list(self.rejected),
        }


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean_text(value: Any, limit: int) -> str:
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", str(value if value is not None else ""))).strip()
    text = text.strip("\"'“”‘’ ")
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut[limit // 2:]:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:-–—") + "…"


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", str(text or ""))
    return [p.strip() for p in parts if p and p.strip()]


def suspicious(text: str, spec: SiteSpec) -> Optional[str]:
    """Why ``text`` may not be shown: a placeholder, or a fact (price,
    phone, founding year, rating) the merchant never gave."""
    if not text:
        return None
    if _PLACEHOLDER_RE.search(text):
        return "placeholder"
    source = f"{spec.description}\n{' '.join(it.price for it in spec.items)}"
    for m in _AMOUNT_RE.finditer(text):
        amount = re.sub(r"[^\d.]", "", m.group(0))
        if amount and amount not in re.sub(r"[^\d.\s]", " ", source):
            return f"amount {m.group(0)}"
    for m in _PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))[-9:]
        if digits not in re.sub(r"\D", "", source + spec.wa_digits):
            return "phone"
    if _YEAR_RE.search(text) and not _YEAR_RE.search(spec.description):
        return "year"
    if _RATING_RE.search(text) and not _RATING_RE.search(spec.description):
        return "rating"
    return None


# ---------------------------------------------------------------------------
# Fallback copy (no model)
# ---------------------------------------------------------------------------

_VERTICAL_WORD = {
    "ms": {"food": "Restoran", "bakery": "Bakeri", "clothing": "Butik", "salon": "Salun", "services": "Perkhidmatan", "general": "Kedai"},
    "en": {"food": "Restaurant", "bakery": "Bakery", "clothing": "Boutique", "salon": "Salon", "services": "Services", "general": "Shop"},
}


_FACT_SENTENCE_RE = re.compile(
    r"\blevel\s*\d|\brefill\b|\bcaj\b|\bcharge\b|\bcoming\s+soon\b|\bakan\s+datang\b|\+\s*RM|\bRM\s?\d",
    re.IGNORECASE,
)


def fallback_copy(spec: SiteSpec) -> Copy:
    lang = spec.lang
    sents = _sentences(spec.description)
    # Facts the sections already render (levels, refill, charges, coming
    # soon, prices) are not repeated in the about text.
    about_sents = [s for s in sents if not _FACT_SENTENCE_RE.search(s)] or sents
    sub = clean_text(sents[0], LIMITS["subheadline"]) if sents else ""
    if not sub:
        sub = ("Order on WhatsApp, we reply fast." if spec.is_food else "Message us on WhatsApp.") if lang == "en" else (
            "Pesan terus di WhatsApp, kami balas segera." if spec.is_food else "Hubungi kami di WhatsApp."
        )
    paragraphs: List[str] = []
    buf = ""
    for s in about_sents[1:] if len(about_sents) > 1 else about_sents:
        if len(buf) + len(s) + 1 > LIMITS["about_paragraph"]:
            if buf:
                paragraphs.append(buf)
            buf = s
        else:
            buf = f"{buf} {s}".strip()
        if len(paragraphs) >= MAX_ABOUT_PARAGRAPHS:
            break
    if buf and len(paragraphs) < MAX_ABOUT_PARAGRAPHS:
        paragraphs.append(buf)
    paragraphs = [clean_text(p, LIMITS["about_paragraph"]) for p in paragraphs][:MAX_ABOUT_PARAGRAPHS]
    if not paragraphs:
        paragraphs = [sub]
    town = ""
    if spec.address:
        m = re.search(r"\b\d{5}\s+([A-Za-z][A-Za-z .]{2,30}?)(?:,|$)", spec.address)
        town = m.group(1).strip() if m else ""
    kicker = _VERTICAL_WORD[lang].get(spec.vertical, _VERTICAL_WORD[lang]["general"]) + (f" · {town}" if town else "")
    return Copy(
        kicker=clean_text(kicker, LIMITS["kicker"]),
        headline=clean_text(spec.business_name, LIMITS["headline"]),
        subheadline=sub,
        menu_lead=("Prices as listed, order straight on WhatsApp." if lang == "en" else "Harga seperti tertera, pesan terus di WhatsApp.") if spec.is_food else "",
        about_title=("About us" if lang == "en" else "Tentang Kami"),
        about_paragraphs=paragraphs,
        tagline=clean_text(sub, LIMITS["tagline"]),
        contact_lead=("Message or call us, we reply fast." if lang == "en" else "Hantar mesej atau telefon, kami balas segera."),
        source="fallback",
    )


# ---------------------------------------------------------------------------
# Prompt + parse
# ---------------------------------------------------------------------------

COPY_SYSTEM_PROMPT = (
    "You are a copywriter for Malaysian small-business websites. Write short, warm, specific copy "
    "in the requested language. Use ONLY facts in the brief: never invent prices, phone numbers, years, "
    "ratings, awards or claims. No emojis, no hashtags, no HTML. Respond with ONLY a JSON object."
)


def build_copy_prompt(spec: SiteSpec) -> str:
    lang_name = "English" if spec.lang == "en" else "Bahasa Malaysia (natural, everyday, not formal)"
    items = ", ".join(it.name for it in spec.items[:12]) or "(none supplied)"
    shape = {
        "kicker": f"≤{LIMITS['kicker']} chars, a tiny eyebrow above the headline, e.g. the type of business + town",
        "headline": f"≤{LIMITS['headline']} chars, the hero headline — may be the business name or a short promise",
        "subheadline": f"≤{LIMITS['subheadline']} chars, one sentence under the headline",
        "menu_lead": f"≤{LIMITS['menu_lead']} chars, one line under the menu/products heading (empty string if no items)",
        "about_title": f"≤{LIMITS['about_title']} chars",
        "about_paragraphs": f"1 to {MAX_ABOUT_PARAGRAPHS} paragraphs, each ≤{LIMITS['about_paragraph']} chars, in the merchant's voice",
        "tagline": f"≤{LIMITS['tagline']} chars, footer line",
        "contact_lead": f"≤{LIMITS['contact_lead']} chars, one line above the contact buttons",
    }
    return (
        f"Language: {lang_name}.\n"
        f"Business: {spec.business_name} ({spec.vertical}).\n"
        f"Town/address: {spec.address or '(not given)'}.\n"
        f"Menu/products (names only): {items}.\n"
        f"Merchant's brief (the only source of facts):\n\"\"\"\n{spec.description.strip()[:3000]}\n\"\"\"\n\n"
        "Write the copy as JSON with exactly these keys:\n" + json.dumps(shape, ensure_ascii=False, indent=1)
    )


def parse_copy(raw: Optional[str], spec: SiteSpec) -> Copy:
    """The model's JSON as a ``Copy``; every missing, empty or suspicious
    field takes the fallback value. Never raises."""
    fb = fallback_copy(spec)
    if not raw or not isinstance(raw, str):
        return fb
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return fb
    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        try:
            data = json.loads(re.sub(r",\s*([}\]])", r"\1", text[start:end + 1]))
        except (json.JSONDecodeError, ValueError):
            return fb
    if not isinstance(data, dict):
        return fb
    out = Copy(source="ai")
    used_fallback = False

    def pick(key: str, limit_key: str, fallback: str, required: bool = True) -> str:
        nonlocal used_fallback
        value = clean_text(data.get(key, ""), LIMITS[limit_key])
        why = suspicious(value, spec)
        if why:
            out.rejected.append(f"{key}: {why}")
            value = ""
        if not value and required:
            used_fallback = True
            return fallback
        return value

    out.kicker = pick("kicker", "kicker", fb.kicker, required=False)
    out.headline = pick("headline", "headline", fb.headline)
    out.subheadline = pick("subheadline", "subheadline", fb.subheadline)
    out.menu_lead = pick("menu_lead", "menu_lead", fb.menu_lead, required=False) if spec.has_menu else ""
    out.about_title = pick("about_title", "about_title", fb.about_title)
    out.tagline = pick("tagline", "tagline", fb.tagline)
    out.contact_lead = pick("contact_lead", "contact_lead", fb.contact_lead)
    raw_paras = data.get("about_paragraphs")
    if isinstance(raw_paras, str):
        raw_paras = [raw_paras]
    paras: List[str] = []
    for p in (raw_paras or [])[:MAX_ABOUT_PARAGRAPHS]:
        value = clean_text(p, LIMITS["about_paragraph"])
        why = suspicious(value, spec)
        if why:
            out.rejected.append(f"about_paragraphs: {why}")
            continue
        if value:
            paras.append(value)
    if not paras:
        used_fallback = True
        paras = list(fb.about_paragraphs)
    out.about_paragraphs = paras
    if used_fallback or out.rejected:
        out.source = "mixed"
    return out
