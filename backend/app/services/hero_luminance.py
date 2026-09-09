"""Pick a hero-video overlay strength from the clip's own first frame.

The overlay used to be a fixed dark/0.45. That reads fine over dark footage
and washes out over bright footage — the subtitle and the opening-hours line
on a bright clip were unreadable. The poster is a Cloudinary-derived first
frame of the same asset, so its mean luminance is a cheap, honest proxy for
how much scrim the copy needs.

Mapping (mean luminance 0..1 → dark-overlay opacity):

    ≤ 0.20  →  0.35   dark clip, keep the picture
       0.45 →  0.51
    ≥ 0.75  →  0.70   bright clip, protect the text

Only applies when the merchant did NOT set an opacity themselves (None).
"""

from __future__ import annotations

import io
from typing import Optional

import httpx
from loguru import logger

DARK_LUM, DARK_OPACITY = 0.20, 0.35
BRIGHT_LUM, BRIGHT_OPACITY = 0.75, 0.70
FALLBACK_OPACITY = 0.45


def opacity_for_luminance(luminance: Optional[float]) -> float:
    """Linear between the two anchors, clamped; fallback when unknown."""
    if luminance is None:
        return FALLBACK_OPACITY
    lum = min(max(float(luminance), 0.0), 1.0)
    if lum <= DARK_LUM:
        return DARK_OPACITY
    if lum >= BRIGHT_LUM:
        return BRIGHT_OPACITY
    t = (lum - DARK_LUM) / (BRIGHT_LUM - DARK_LUM)
    return round(DARK_OPACITY + t * (BRIGHT_OPACITY - DARK_OPACITY), 2)


def luminance_of_image_bytes(data: bytes) -> Optional[float]:
    """Mean luminance 0..1 of an encoded image, or None if unreadable."""
    try:
        from PIL import Image  # Pillow is already a backend dependency
        with Image.open(io.BytesIO(data)) as im:
            grey = im.convert("L").resize((64, 36))
            px = list(grey.getdata())
            return (sum(px) / len(px)) / 255.0 if px else None
    except Exception as exc:
        logger.warning(f"🎬 luminance: could not read poster ({exc})")
        return None


async def poster_luminance(url: Optional[str], timeout: float = 8.0) -> Optional[float]:
    """Download the poster and measure it. Any failure → None (fallback)."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            logger.warning(f"🎬 luminance: poster fetch {resp.status_code}")
            return None
        return luminance_of_image_bytes(resp.content)
    except Exception as exc:
        logger.warning(f"🎬 luminance: poster fetch failed ({exc})")
        return None


async def auto_overlay_opacity(poster_url: Optional[str]) -> float:
    lum = await poster_luminance(poster_url)
    opacity = opacity_for_luminance(lum)
    logger.info(
        f"🎬 Overlay opacity auto-selected: {opacity} "
        f"(poster luminance={'n/a' if lum is None else round(lum, 3)})"
    )
    return opacity
