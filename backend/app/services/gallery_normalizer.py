"""Deterministic post-pass for AI-generated gallery HTML.

The generation prompt asks the model to (a) give every gallery/menu card
image the same height and (b) never repeat a category tag, but a prompt is
guidance, not a guarantee. This module enforces both deterministically on
the final HTML so the result is consistent regardless of what the model
emitted.

Pure stdlib (regex) — adds no dependency and runs in any generation path.
Every transform is wrapped so it can never raise into the pipeline; on any
error the original HTML is returned unchanged.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1) Uniform gallery/menu card image heights
# ---------------------------------------------------------------------------
# Numeric Tailwind heights typical of a CARD image area (a tall block).
# Deliberately starts at 40 so small images — avatars, logos, icons
# (h-8..h-32) — are never touched.
_CARD_HEIGHTS = {40, 44, 48, 52, 56, 60, 64, 72, 80, 96}

# If an <img>'s class carries any of these, it is NOT a uniform card image
# (hero/full-bleed/arbitrary/already-aspect/avatar) — leave it alone.
_SKIP_HEIGHT_MARKERS = ("h-screen", "h-[", "min-h-", "aspect-", "rounded-full", "h-full")

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_CLASS_ATTR = re.compile(r"(\bclass\s*=\s*)(['\"])(.*?)\2", re.IGNORECASE | re.DOTALL)
_HEIGHT_TOKEN = re.compile(r"^(?:(?:sm|md|lg|xl|2xl):)?h-(\d+)$")


def _normalize_img_classes(class_value: str) -> str:
    low = class_value.lower()
    # Only normalize images that crop to fill (object-cover); normalizing a
    # contain/letterboxed image would distort it.
    if "object-cover" not in low:
        return class_value
    if any(marker in low for marker in _SKIP_HEIGHT_MARKERS):
        return class_value

    tokens = class_value.split()
    kept = []
    found_card_height = False
    for tok in tokens:
        m = _HEIGHT_TOKEN.match(tok)
        if m and int(m.group(1)) in _CARD_HEIGHTS:
            found_card_height = True
            continue  # drop this per-card height utility (base + responsive)
        kept.append(tok)

    if not found_card_height:
        return class_value

    if "aspect-[4/3]" not in kept:
        kept.append("aspect-[4/3]")
    if "w-full" not in kept:
        kept.insert(0, "w-full")
    return " ".join(kept)


def normalize_gallery_heights(html: str) -> str:
    """Replace per-card pixel heights on card images with a uniform aspect ratio."""
    def _img_sub(img_match):
        tag = img_match.group(0)

        def _class_sub(cm):
            new_cls = _normalize_img_classes(cm.group(3))
            return f"{cm.group(1)}{cm.group(2)}{new_cls}{cm.group(2)}"

        return _CLASS_ATTR.sub(_class_sub, tag, count=1)

    return _IMG_TAG.sub(_img_sub, html)


# ---------------------------------------------------------------------------
# 2) De-duplicate repeated gallery category tags
# ---------------------------------------------------------------------------
# A "tag" is a small badge/chip <span>, identified by badge-like classes.
_BADGE_HINTS = (
    "rounded-full", "uppercase", "tracking-", "text-xs",
    "text-[10px]", "text-[11px]", "badge", "chip",
)
# Short labels that legitimately repeat across cards (promo/status badges) and
# must NOT be de-duplicated. Matched case-insensitively.
_ALLOW_REPEAT = {
    "new", "baru", "popular", "populer", "terlaris", "best seller", "bestseller",
    "hot", "sale", "promo", "promosi", "diskaun", "discount", "halal", "viral",
    "signature", "recommended", "disyorkan", "sold out", "habis", "featured",
    "pilihan", "special", "istimewa", "trending", "limited",
}
_SPAN_BADGE = re.compile(
    r"<span\b([^>]*\bclass\s*=\s*['\"][^'\"]*['\"][^>]*)>([^<>]{1,24})</span>",
    re.IGNORECASE,
)


def dedupe_gallery_tags(html: str) -> str:
    """Remove a repeated non-promo category tag's later occurrences.

    Keeps the first instance; drops subsequent identical badge tags so the same
    label can't appear on two cards. Promo/status badges (NEW, HALAL, …) are
    allowed to repeat.
    """
    seen = set()

    def _sub(m):
        attrs_low = m.group(1).lower()
        if not any(hint in attrs_low for hint in _BADGE_HINTS):
            return m.group(0)  # not a badge — leave body text alone
        key = re.sub(r"\s+", " ", m.group(2).strip()).lower()
        if not key or key in _ALLOW_REPEAT:
            return m.group(0)
        if key in seen:
            return ""  # duplicate category tag — drop it
        seen.add(key)
        return m.group(0)

    return _SPAN_BADGE.sub(_sub, html)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def normalize_gallery_html(html: str) -> str:
    """Apply all deterministic gallery fixes. Never raises."""
    if not html or "<img" not in html.lower():
        return html
    try:
        html = normalize_gallery_heights(html)
    except Exception as e:  # pragma: no cover - safety net
        logger.warning(f"gallery height normalize skipped: {e}")
    try:
        html = dedupe_gallery_tags(html)
    except Exception as e:  # pragma: no cover - safety net
        logger.warning(f"gallery tag dedupe skipped: {e}")
    return html
