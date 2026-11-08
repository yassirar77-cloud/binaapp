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
    for key in list(out):
        if re.fullmatch(r"(?:gallery[1-4]|menuphoto\d+)", key) and out.get(key):
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
    _h, light, sat = colorsys.rgb_to_hls(r, g, b)
    return 0.12 <= light <= 0.88 and sat >= 0.25


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


def _dish_phrases(item_names: Sequence[str], limit: int = 3) -> List[str]:
    """The merchant's items as plain dish descriptions ("Set B – Ayam Gepuk
    Tauhu Tempe" → "smashed crispy fried chicken with fried tofu and
    tempeh"): an image model letters a menu label into the picture, and
    "Set A – Ayam Gepuk" came back as a sign reading "Set A Aman Gepok"."""
    from app.services import image_subjects
    out: List[str] = []
    for name in item_names:
        if not (name and str(name).strip()):
            continue
        dish = image_subjects.plain_dish_prompt(str(name)).split(", top-down")[0].strip()
        if dish and dish not in out:
            out.append(dish)
        if len(out) >= limit:
            break
    return out


def _and(xs: Sequence[str]) -> str:
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _spread(dishes: Sequence[str]) -> str:
    """"a generous spread of smashed crispy fried chicken with fried tofu,
    tempeh and stir-fried cabbage" — main dishes once, sides once."""
    heads: List[str] = []
    sides: List[str] = []
    for d in dishes:
        head, _, rest = d.partition(" with ")
        if head and head not in heads:
            heads.append(head)
        for side in re.split(r",\s*|\s+and\s+", rest):
            side = side.strip()
            if side and side not in sides and side not in heads:
                sides.append(side)
    text = _and(heads) if heads else "the shop's dishes"
    if sides:
        text += " with " + _and(sides[:4])
    return ("a generous spread of " if len(dishes) > 1 else "") + text


def direction_hero_cue(
    *,
    image_cue: str,
    vertical: str,
    theme: str,
    item_names: Sequence[str] = (),
    merchant_prompt: Optional[str] = None,
    business_text: str = "",
    cue_keywords: Sequence[str] = (),
) -> str:
    """The hero image prompt Pass 1 writes: the merchant's own dishes, the
    light of the direction and the theme, merged with the merchant's own
    words (which lead when present).

    A direction's ``image_cue`` opens with an EXAMPLE subject for the
    shops it was written for ("a stacked burger and fries on kraft paper"
    for Halal Street). That subject is used only when the merchant listed
    no items AND the business matches the direction's keywords; otherwise
    only its light and mood are kept. agp (ayam gepuk, styled "bold") got
    Halal Street, and its hero was a burger."""
    items = [n.strip() for n in item_names if n and n.strip()][:3]
    clauses = [c.strip() for c in str(image_cue or "").split(",") if c.strip()]
    cue_subject, cue_style = (clauses[0], clauses[1:]) if clauses else ("", [])
    text = f" {str(business_text or '').lower()} "
    subject_fits = not cue_keywords or any(str(k).lower() in text for k in cue_keywords)
    parts: List[str] = []
    if merchant_prompt and merchant_prompt.strip():
        parts.append(merchant_prompt.strip())
    food = vertical in ("food", "bakery")
    if items and food:
        parts.append(_spread(_dish_phrases(items)))
    elif items:
        parts.append("showing " + ", ".join(items))
        if cue_subject and subject_fits and cue_keywords:
            parts.append(cue_subject)
    elif cue_subject and subject_fits:
        parts.append(cue_subject)
    elif food and not (merchant_prompt and merchant_prompt.strip()):
        parts.append("freshly baked cakes and pastries" if vertical == "bakery" else "a generous spread of the shop's freshly cooked dishes")
    parts.extend(cue_style)
    parts.append("warm evening light, deep shadows" if theme == "dark" else ("bright natural daylight, appetising and warm" if food else "bright natural daylight"))
    if food:
        parts.append("the dish is the subject, no people, no text")
    cue = ", ".join(parts)
    lowered = cue.lower()
    for banned in _GENERIC_BANNED:
        if banned in lowered and not (merchant_prompt and banned in merchant_prompt.lower()):
            cue = re.sub(re.escape(banned), "the dish close-up", cue, flags=re.IGNORECASE)
    return cue
