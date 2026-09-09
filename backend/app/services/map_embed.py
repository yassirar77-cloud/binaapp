"""Google Maps embeds that actually show where the business is.

The generated page embeds the keyless search form of the Maps embed —
``maps?q=<address text>&output=embed``. When Google cannot resolve that text
to one place (a Malaysian address with "13/2" in it, unencoded, is a good
way to guarantee it can't) the frame renders a wide region with no pin.

This module makes the embed deterministic: geocode the address once at
publish time, keep lat/lng on the website row, and point every map iframe at
the coordinates with an explicit zoom. When geocoding fails the fallback is a
properly URL-encoded search on the address string — still a search, but at
least the one Google can parse — and never the wide-area frame.
"""

from __future__ import annotations

import html as _html
import re
from typing import Optional
from urllib.parse import parse_qs, quote_plus, unquote_plus, urlsplit

from loguru import logger

MARKER_ZOOM = 16

_MAP_IFRAME_RE = re.compile(
    r"""(<iframe\b[^>]*?\bsrc\s*=\s*)(['"])([^'"]*(?:google\.[a-z.]+/maps|maps\.google\.[a-z.]+)[^'"]*)\2""",
    re.IGNORECASE,
)
_COORD_RE = re.compile(r"^\s*-?\d{1,2}(?:\.\d+)?\s*,\s*-?\d{1,3}(?:\.\d+)?\s*$")


def extract_map_address(html: str) -> Optional[str]:
    """The address text the page's first map iframe is searching for, or
    None when there is no map or it already points at coordinates."""
    m = _MAP_IFRAME_RE.search(html or "")
    if not m:
        return None
    src = _html.unescape(m.group(3))
    try:
        q = parse_qs(urlsplit(src).query).get("q", [""])[0]
    except Exception:
        return None
    q = unquote_plus(q).strip()
    if not q or _COORD_RE.match(q):
        return None
    return q


def build_map_embed_src(
    *, lat: Optional[float], lng: Optional[float], address: Optional[str], zoom: int = MARKER_ZOOM
) -> Optional[str]:
    """Coordinates → pinned embed at ``zoom``. No coordinates → encoded
    address search. Nothing at all → None (leave the page alone)."""
    if lat is not None and lng is not None:
        return f"https://maps.google.com/maps?q={lat:.6f},{lng:.6f}&z={zoom}&output=embed"
    addr = (address or "").strip()
    if addr:
        return f"https://maps.google.com/maps?q={quote_plus(addr)}&z={zoom}&output=embed"
    return None


def rewrite_map_embeds(html: str, new_src: str) -> str:
    """Point every Google Maps iframe in ``html`` at ``new_src``."""
    if not html or not new_src:
        return html
    escaped = _html.escape(new_src, quote=False)  # & → &amp; inside an attribute

    def _sub(m: "re.Match") -> str:
        return f"{m.group(1)}{m.group(2)}{escaped}{m.group(2)}"

    out, n = _MAP_IFRAME_RE.subn(_sub, html)
    if n:
        logger.info(f"🗺️ Rewrote {n} map embed(s) → {new_src}")
    return out


def has_map_embed(html: str) -> bool:
    return bool(_MAP_IFRAME_RE.search(html or ""))
