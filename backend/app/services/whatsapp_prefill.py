"""WhatsApp prefill text that fits the business.

The floating button on every generated page opened WhatsApp with "saya
berminat dengan perkhidmatan anda" — service wording — on an ayam gepuk
restaurant. The prefill now follows the vertical: a food business gets
"saya nak order". Per-item order links carry the ordering choices the brief
mentions (spice level, dine-in / take away) as blanks the customer fills in,
so the kitchen gets a complete order instead of a follow-up question.
Pure functions; no I/O.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from urllib.parse import quote, unquote

_FOOD_TYPES = {"food", "restaurant", "cafe", "bakery", "catering", "fnb", "f&b"}

#: Floating-button prefill by (vertical, language).
DEFAULT_PREFILL = {
    ("food", "ms"): "Assalamualaikum, saya nak order",
    ("food", "en"): "Hi, I would like to order",
    ("general", "ms"): "Assalamualaikum, saya berminat dengan perkhidmatan anda",
    ("general", "en"): "Hi, I'm interested in your services",
}

#: Ordering choices a brief can mention → the blank the customer fills in.
_OPTION_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(level|tahap)\s*(kepedasan|pedas)?\s*\d|\btahap\s+kepedasan\b|\bspice\s*level\b|\bspicy\s*level\b|\b(extra\s*hot|level\s*[123])\b", re.IGNORECASE), "Level: _", "Level: _"),
    (re.compile(r"\b(dine[\s-]*in|makan\s+di\s+(kedai|sini|restoran)|take[\s-]*away|bungkus|tapau|ta\s*pau)\b", re.IGNORECASE), "Dine-in/Take away: _", "Dine-in/Take away: _"),
]


def _lang(language: Optional[str]) -> str:
    return "en" if str(language or "ms").lower().startswith("en") else "ms"


def is_food_type(business_type: Optional[str]) -> bool:
    return str(business_type or "").strip().lower() in _FOOD_TYPES


def default_prefill(language: Optional[str], business_type: Optional[str] = None) -> str:
    """The floating button's message for this vertical and language."""
    vertical = "food" if is_food_type(business_type) else "general"
    return DEFAULT_PREFILL[(vertical, _lang(language))]


def order_options(description: Optional[str], language: Optional[str] = "ms") -> List[str]:
    """Blanks to append to an item order ("Level: _", "Dine-in/Take away: _")
    for every ordering choice the brief mentions, in a fixed order."""
    text = str(description or "")
    out: List[str] = []
    for pattern, ms_label, en_label in _OPTION_PATTERNS:
        if pattern.search(text):
            out.append(en_label if _lang(language) == "en" else ms_label)
    return out


def order_suffix(options: List[str]) -> str:
    return f" ({', '.join(options)})" if options else ""


def order_prefill_for(description: Optional[str], language: Optional[str] = "ms", business_type: Optional[str] = "food") -> str:
    """The text an item order link starts with; the item name follows it
    and ``order_suffix`` is appended by ``enrich_order_links``."""
    return default_prefill(language, business_type)


_WA_HREF_RE = re.compile(r"""(href=["'])(https?://(?:api\.)?(?:wa\.me|whatsapp\.com)/[^"'?]*\?[^"']*?\btext=)([^"'&]*)""", re.IGNORECASE)


def enrich_order_links(html: str, description: Optional[str], language: Optional[str] = "ms") -> Tuple[str, int]:
    """Append the ordering blanks to every per-item WhatsApp link.

    A per-item link is one whose prefilled text names an item after the
    order phrase (longer than the bare phrase). The floating button's bare
    phrase is left alone. Idempotent: a link that already carries a "("
    suffix is not touched. Returns (html, links changed)."""
    options = order_options(description, language)
    if not html or not options:
        return html, 0
    suffix = order_suffix(options)
    bare = {v.lower() for v in DEFAULT_PREFILL.values()} | {"assalamualaikum, saya nak pesan", "hi, i would like to order"}
    changed = 0

    def _sub(m: "re.Match") -> str:
        nonlocal changed
        raw = m.group(3)
        text = unquote(raw.replace("+", " ")).strip()
        low = text.lower()
        if not text or low in bare or "(" in text:
            return m.group(0)
        if not any(low.startswith(b) for b in bare) and not re.search(r"\b(order|pesan|tempah|nak)\b", low):
            return m.group(0)
        changed += 1
        return m.group(1) + m.group(2) + quote(text + suffix, safe="")

    out = _WA_HREF_RE.sub(_sub, html)
    return out, changed
