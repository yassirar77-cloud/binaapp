"""
Imagery intelligence (§6) — what the pipeline learns from the merchant's
photos before it designs around them, and the crops it applies.

- ``hero_quality``   rejects a blurry/low-res (< 1200px wide) or portrait
                      hero for full-bleed use; the plan then falls back to
                      a split hero.
- ``dominant_colours`` two or three dominant, saturated colours from the
                      hero and item photos (tiny quantisation) so the plan
                      can harmonise its palette with the food.
- ``cloudinary_transform`` / ``apply_section_crops`` consistent crop
                      ratios per section (hero 16:9, menu 4:3, gallery 3:2)
                      applied as Cloudinary transforms — real crops, not
                      CSS.
- ``direction_hero_cue`` the dish-specific hero prompt cue for generated
                      images: the plan's direction cue merged with the
                      merchant's own words and their signature items, so a
                      generated hero is never a generic "person eating".

Network is confined to ``_fetch``; everything else is pure and tested on
in-memory images. Pillow is optional: without it the quality gate says
"unknown, allow full-bleed" and no colours are extracted.
"""

from __future__ import annotations

import asyncio
import colorsys
import io
import logging
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

MIN_HERO_WIDTH = 1200
FETCH_TIMEOUT_SECONDS = 8.0
MAX_FETCH_BYTES = 12 * 1024 * 1024

#: Crop ratio per image role, as Cloudinary ``ar_`` values.
SECTION_RATIOS: Dict[str, str] = {
    "hero": "16:9",
    "menu": "4:3",
    "product": "4:3",
    "gallery": "3:2",
    "about": "3:2",
}
SECTION_WIDTHS: Dict[str, int] = {"hero": 1600, "menu": 900, "product": 900, "gallery": 1200, "about": 1200}

_CLOUDINARY_UPLOAD_RE = re.compile(r"^(https?://res\.cloudinary\.com/[^/]+/image/upload/)(.*)$", re.IGNORECASE)
_TRANSFORM_SEGMENT_RE = re.compile(r"^(?:[a-z]{1,3}_[^/]+)(?:,[a-z]{1,3}_[^/]+)*$")


@dataclass
class HeroQuality:
    width: int = 0
    height: int = 0
    known: bool = False
    reason: str = ""

    @property
    def portrait(self) -> bool:
        return self.known and self.height > self.width

    @property
    def full_bleed_ok(self) -> bool:
        """Unknown quality allows full-bleed (never block on a fetch
        failure); a known small or portrait image does not."""
        if not self.known:
            return True
        return self.width >= MIN_HERO_WIDTH and not self.portrait


# ---------------------------------------------------------------------------
# Cloudinary crops
# ---------------------------------------------------------------------------

def cloudinary_transform(url: str, role: str) -> str:
    """Insert a crop transform for ``role`` into a Cloudinary upload URL.
    Non-Cloudinary URLs and URLs that already carry an ``ar_`` transform
    are returned unchanged."""
    if not url or not isinstance(url, str):
        return url
    m = _CLOUDINARY_UPLOAD_RE.match(url.strip())
    if not m:
        return url
    ratio = SECTION_RATIOS.get(role)
    if not ratio:
        return url
    rest = m.group(2)
    first = rest.split("/", 1)[0]
    if _TRANSFORM_SEGMENT_RE.match(first) and "ar_" in first:
        return url
    width = SECTION_WIDTHS.get(role, 1200)
    transform = f"c_fill,ar_{ratio},g_auto,w_{width},q_auto,f_auto"
    return f"{m.group(1)}{transform}/{rest}"


def apply_section_crops(image_urls: Dict[str, str], *, item_role: str = "menu") -> Dict[str, str]:
    """Crop the hero to 16:9 and every gallery slot to the item ratio."""
    out = dict(image_urls or {})
    if out.get("hero"):
        out["hero"] = cloudinary_transform(out["hero"], "hero")
    for i in range(1, 5):
        key = f"gallery{i}"
        if out.get(key):
            out[key] = cloudinary_transform(out[key], item_role)
    return out


def crop_uploaded_images(uploaded: Sequence, *, item_role: str = "menu") -> List:
    """Same crops on the request's uploaded_images list (dicts with url/name)."""
    out = []
    for img in uploaded or []:
        if isinstance(img, dict) and img.get("url"):
            name = str(img.get("name") or "").lower()
            role = "hero" if "hero" in name else item_role
            out.append({**img, "url": cloudinary_transform(img["url"], role)})
        elif isinstance(img, str):
            out.append(cloudinary_transform(img, item_role))
        else:
            out.append(img)
    return out


# ---------------------------------------------------------------------------
# Quality + colours
# ---------------------------------------------------------------------------

async def _fetch(url: str) -> Optional[bytes]:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
            r = await client.get(url)
        if r.status_code != 200:
            return None
        data = r.content
        return data if len(data) <= MAX_FETCH_BYTES else None
    except Exception as err:
        logger.info(f"🖼️ Image fetch failed ({url[:80]}): {err}")
        return None


def hero_quality_from_bytes(data: Optional[bytes]) -> HeroQuality:
    if not data:
        return HeroQuality(reason="no image data")
    try:
        from PIL import Image
    except Exception:
        return HeroQuality(reason="Pillow unavailable")
    try:
        with Image.open(io.BytesIO(data)) as img:
            w, h = img.size
    except Exception as err:
        return HeroQuality(reason=f"unreadable image: {err}")
    q = HeroQuality(width=w, height=h, known=True)
    if q.portrait:
        q.reason = "portrait orientation"
    elif w < MIN_HERO_WIDTH:
        q.reason = f"only {w}px wide (< {MIN_HERO_WIDTH})"
    return q


async def hero_quality(url: Optional[str]) -> HeroQuality:
    if not url:
        return HeroQuality(reason="no hero")
    # Cloudinary URLs already carry width in a transform when we cropped
    # them; still measure the source when we can.
    return hero_quality_from_bytes(await _fetch(url))


def _saturated_enough(rgb: Tuple[int, int, int]) -> bool:
    r, g, b = (c / 255 for c in rgb)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return 0.12 <= l <= 0.88 and s >= 0.25


def dominant_colours_from_bytes(data: Optional[bytes], n: int = 2) -> List[str]:
    """Up to ``n`` dominant saturated colours (#RRGGBB), most frequent first.
    Near-white, near-black and grey pixels are ignored — they are the
    plate, not the food."""
    if not data:
        return []
    try:
        from PIL import Image
    except Exception:
        return []
    try:
        with Image.open(io.BytesIO(data)) as img:
            small = img.convert("RGB")
            small.thumbnail((96, 96))
            quant = small.quantize(colors=12, method=Image.Quantize.MEDIANCUT if hasattr(Image, "Quantize") else 0)
            palette = quant.getpalette()
            counts = sorted(quant.getcolors() or [], reverse=True)
    except Exception as err:
        logger.info(f"🖼️ Colour extraction failed: {err}")
        return []
    out: List[str] = []
    for count, idx in counts:
        rgb = tuple(palette[idx * 3: idx * 3 + 3])
        if len(rgb) < 3 or not _saturated_enough(rgb):  # type: ignore[arg-type]
            continue
        hex_colour = "#%02X%02X%02X" % rgb  # type: ignore[str-format]
        if hex_colour not in out:
            out.append(hex_colour)
        if len(out) >= n:
            break
    return out


async def dominant_colours(urls: Iterable[Optional[str]], n: int = 3) -> List[str]:
    """Dominant colours across the hero and item photos (hero first)."""
    found: List[str] = []
    for url in [u for u in urls if u][:4]:
        data = await _fetch(url)
        for colour in dominant_colours_from_bytes(data, n=2):
            if colour not in found:
                found.append(colour)
        if len(found) >= n:
            break
    return found[:n]


# ---------------------------------------------------------------------------
# Hero prompt cue
# ---------------------------------------------------------------------------

_GENERIC_BANNED = ("person eating", "people eating", "customer smiling", "family enjoying", "stock photo")


def direction_hero_cue(
    *,
    image_cue: str,
    vertical: str,
    theme: str,
    item_names: Sequence[str] = (),
    merchant_prompt: Optional[str] = None,
) -> str:
    """The hero image prompt Pass 1 writes: the direction's dish-specific
    cue, the merchant's signature items, the light of the theme, merged
    with the merchant's own words (which lead when present)."""
    items = [n.strip() for n in item_names if n and n.strip()][:3]
    parts: List[str] = []
    if merchant_prompt and merchant_prompt.strip():
        parts.append(merchant_prompt.strip())
    if items and vertical in ("food", "bakery"):
        parts.append("featuring " + ", ".join(items))
    elif items:
        parts.append("showing " + ", ".join(items))
    if image_cue:
        parts.append(image_cue)
    parts.append("warm evening light, deep shadows" if theme == "dark" else "bright natural daylight, appetising and warm")
    if vertical in ("food", "bakery"):
        parts.append("the dish is the subject, no people, no text")
    cue = ", ".join(parts)
    lowered = cue.lower()
    for banned in _GENERIC_BANNED:
        if banned in lowered and not (merchant_prompt and banned in merchant_prompt.lower()):
            cue = re.sub(re.escape(banned), "the dish close-up", cue, flags=re.IGNORECASE)
    return cue
