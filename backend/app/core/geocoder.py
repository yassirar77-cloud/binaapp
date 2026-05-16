"""Shared Nominatim geocoder helpers.

Both owner-facing routes (in delivery_zones.py) and the public customer
route (in delivery.py) call into here. Keeping the cache + Nominatim
client in one place means a single shared User-Agent + in-process cache
across the whole process — friendlier to Nominatim's per-IP rate limit
than letting browsers hit the API directly.

Behavior is lifted as-is from the previous in-route implementation:
  - In-process dict cache, 7-day TTL, 5000-entry cap, oldest-10% evict.
  - 5-digit postcode regex pre-check before hitting Nominatim.
  - 10s timeout, surfaces 504 on timeout / 502 on other errors.
"""
from __future__ import annotations

import re
import time
from typing import Dict, Optional

import httpx
from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel


# =====================================================
# Pydantic shape returned by every geocode call.
# =====================================================
class GeocodeResult(BaseModel):
    found: bool
    lat: float | None = None
    lng: float | None = None
    display_name: str | None = None


# =====================================================
# Nominatim config
# =====================================================
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "BinaApp/1.0 (admin@binaapp.my)"
_HTTP_TIMEOUT_SEC = 10.0

# 5-digit Malaysian postcode pattern. Other countries can be supported later
# by relaxing this regex per-country.
_MY_POSTCODE_RE = re.compile(r"^\d{5}$")

ADDRESS_MIN_LEN = 4
ADDRESS_MAX_LEN = 300


# =====================================================
# In-process cache. Process-wide; resets on restart. Adequate for our
# scale and avoids the operational cost of adding Redis just for this.
# =====================================================
_GEOCODE_CACHE: Dict[str, tuple[float, dict]] = {}
_GEOCODE_TTL = 60 * 60 * 24 * 7  # 7 days
_GEOCODE_CACHE_MAX = 5000


def _cache_get(key: str) -> Optional[dict]:
    entry = _GEOCODE_CACHE.get(key)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts >= _GEOCODE_TTL:
        _GEOCODE_CACHE.pop(key, None)
        return None
    return data


def _cache_put(key: str, data: dict) -> None:
    if len(_GEOCODE_CACHE) >= _GEOCODE_CACHE_MAX:
        # Evict oldest 10% to keep amortized cost low.
        items = sorted(_GEOCODE_CACHE.items(), key=lambda kv: kv[1][0])
        for k, _ in items[: max(1, _GEOCODE_CACHE_MAX // 10)]:
            _GEOCODE_CACHE.pop(k, None)
    _GEOCODE_CACHE[key] = (time.time(), data)


async def _nominatim_fetch(params: Dict[str, str]) -> list:
    """Call Nominatim and return its JSON array (possibly empty).

    Raises HTTPException(504) on timeout, HTTPException(502) on any other
    transport / response error — mirroring the prior in-route behavior.
    """
    headers = {"User-Agent": _USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SEC) as http:
            resp = await http.get(_NOMINATIM_URL, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Geocoder masa tamat")
    except Exception as e:
        logger.error(f"Nominatim error: {e}")
        raise HTTPException(status_code=502, detail="Geocoder unavailable")


def _to_result(data: list) -> dict:
    if not data:
        return {"found": False, "lat": None, "lng": None, "display_name": None}
    first = data[0]
    return {
        "found": True,
        "lat": float(first["lat"]),
        "lng": float(first["lon"]),
        "display_name": first.get("display_name"),
    }


# =====================================================
# Public helpers used by route handlers
# =====================================================
async def geocode_postcode(postcode: str, country: str = "MY") -> GeocodeResult:
    """Resolve a 5-digit postcode → lat/lng. Cached for 7 days.

    Postcode format is validated against /^\\d{5}$/ before hitting Nominatim
    to defend the User-Agent's IP against rate-limiting from spammy / nonsense
    inputs (e.g. ?postcode=KFC).
    """
    pc = postcode.strip()
    if not _MY_POSTCODE_RE.match(pc):
        raise HTTPException(status_code=400, detail="Postcode mesti 5 digit")

    key = f"PC:{country.upper()}:{pc}"
    cached = _cache_get(key)
    if cached is not None:
        return GeocodeResult(**cached)

    data = await _nominatim_fetch(
        {"postalcode": pc, "country": country, "format": "json", "limit": "1"}
    )
    result = _to_result(data)
    _cache_put(key, result)
    return GeocodeResult(**result)


async def geocode_address(q: str, country: str = "MY") -> GeocodeResult:
    """Resolve a free-text address → lat/lng. Cached for 7 days."""
    query = q.strip()
    if len(query) < ADDRESS_MIN_LEN:
        raise HTTPException(status_code=400, detail="Alamat terlalu pendek")

    key = f"ADDR:{country.upper()}:{query.lower()}"
    cached = _cache_get(key)
    if cached is not None:
        return GeocodeResult(**cached)

    data = await _nominatim_fetch(
        {
            "q": query,
            "countrycodes": country.lower(),
            "format": "json",
            "limit": "1",
        }
    )
    result = _to_result(data)
    _cache_put(key, result)
    return GeocodeResult(**result)
