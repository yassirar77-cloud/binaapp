"""
Delivery Zones API — owner-side admin endpoints for /dashboard/penghantaran.

These endpoints power the per-website zone manager. They sit alongside the
legacy /delivery/zones/{website_id} endpoint, which is still used by the
public customer flow. New owner UI MUST use these (/zones/...) routes.

Auth pattern: this codebase issues custom JWTs (signed with the backend's
JWT_SECRET_KEY), so Supabase RLS via client.postgrest.auth(token) does not
work — Supabase rejects the signature with PGRST301. We instead verify the
JWT in FastAPI via get_current_user, query Supabase via the service-role
client (bypasses RLS), and check ownership in Python before each operation.
The 3 mutating RPCs accept p_user_id explicitly because auth.uid() returns
NULL when called via service-role.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field
from supabase import Client

from app.core.security import get_current_user
from app.core.supabase import get_supabase_client

router = APIRouter(prefix="/zones", tags=["Delivery Zones (Owner)"])

# 5-digit Malaysian postcode pattern. Other countries can be supported later
# by relaxing this regex per-country.
_MY_POSTCODE_RE = re.compile(r"^\d{5}$")


# =====================================================
# Ownership helpers — service-role queries can read anything, so we verify
# ownership in Python before mutations or info reads.
# =====================================================
def _verify_website_ownership(
    supabase: Client, website_id: str, user_id: str
) -> None:
    """Raise HTTPException(403) if the website does not belong to user_id."""
    res = (
        supabase.table("websites")
        .select("id")
        .eq("id", website_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=403, detail="Bukan website anda")


def _verify_zone_ownership(
    supabase: Client, zone_id: str, user_id: str
) -> str:
    """Verify ownership and return the zone's website_id.

    Raises 404 if the zone doesn't exist, 403 if it belongs to someone else.
    Two queries instead of a Postgrest join for compatibility across
    supabase-py versions.
    """
    z = (
        supabase.table("delivery_zones")
        .select("website_id")
        .eq("id", zone_id)
        .limit(1)
        .execute()
    )
    if not z.data:
        raise HTTPException(status_code=404, detail="Zon tidak dijumpai")
    website_id = z.data[0]["website_id"]
    _verify_website_ownership(supabase, website_id, user_id)
    return website_id


# =====================================================
# Pydantic schemas
# =====================================================
class ScheduleDay(BaseModel):
    open: str = "10:00"
    close: str = "22:00"
    active: bool = True


GeoJSONPolygon = Dict[str, Any]  # {"type": "Polygon", "coordinates": [[[lng, lat], ...]]}


class ZoneIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = "#C7FF3D"
    fee_cents: int = Field(ge=0, default=500)
    min_order_cents: int = Field(ge=0, default=2000)
    polygon: GeoJSONPolygon
    schedule_json: Dict[str, ScheduleDay] | None = None
    estimated_delivery_min: int = Field(ge=0, default=30)
    max_simultaneous_orders: int = Field(ge=0, default=10)
    customer_notes: str | None = None
    active: bool = True
    inner_radius_m: int | None = Field(default=None, ge=0)
    outer_radius_m: int | None = Field(default=None, ge=1)


class ZonePatch(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    fee_cents: Optional[int] = Field(default=None, ge=0)
    min_order_cents: Optional[int] = Field(default=None, ge=0)
    polygon: Optional[GeoJSONPolygon] = None
    schedule_json: Optional[Dict[str, ScheduleDay]] = None
    estimated_delivery_min: Optional[int] = Field(default=None, ge=0)
    max_simultaneous_orders: Optional[int] = Field(default=None, ge=0)
    customer_notes: Optional[str] = None
    active: Optional[bool] = None
    inner_radius_m: Optional[int] = Field(default=None, ge=0)
    outer_radius_m: Optional[int] = Field(default=None, ge=1)


class ZoneOut(BaseModel):
    id: str
    website_id: str
    name: str
    color: str
    fee_cents: int
    min_order_cents: int
    polygon: GeoJSONPolygon
    schedule_json: Dict[str, Any]
    estimated_delivery_min: int | None
    max_simultaneous_orders: int | None
    customer_notes: str | None
    active: bool
    area_m2: float | None
    inner_radius_m: int | None = None
    outer_radius_m: int | None = None
    created_at: str
    updated_at: str


def _row_to_zone_out(row: Dict[str, Any]) -> ZoneOut:
    return ZoneOut(
        id=str(row["id"]),
        website_id=str(row["website_id"]),
        name=row["name"],
        color=row["color"],
        fee_cents=row["fee_cents"],
        min_order_cents=row["min_order_cents"],
        polygon=row["polygon_geojson"],
        schedule_json=row["schedule_json"],
        estimated_delivery_min=row.get("estimated_delivery_min"),
        max_simultaneous_orders=row.get("max_simultaneous_orders"),
        customer_notes=row.get("customer_notes"),
        active=row["active"],
        area_m2=row.get("area_m2"),
        inner_radius_m=row.get("inner_radius_m"),
        outer_radius_m=row.get("outer_radius_m"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# =====================================================
# Endpoints
# =====================================================
@router.get("/website/{website_id}", response_model=List[ZoneOut])
async def list_zones(
    website_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """List all zones for a website. Ownership verified in Python."""
    _verify_website_ownership(supabase, website_id, current_user["sub"])
    try:
        res = supabase.rpc(
            "list_delivery_zones", {"p_website_id": website_id}
        ).execute()
        rows = res.data or []
        return [_row_to_zone_out(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"list_zones failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list zones: {e}")


@router.post("/website/{website_id}", response_model=ZoneOut, status_code=201)
async def create_zone(
    website_id: str,
    zone: ZoneIn,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Create a new zone (polygon as GeoJSON)."""
    user_id = current_user["sub"]
    _verify_website_ownership(supabase, website_id, user_id)
    try:
        schedule = zone.schedule_json or {}
        schedule_payload = {
            k: v.model_dump() if hasattr(v, "model_dump") else v
            for k, v in schedule.items()
        } or None

        rpc_args = {
            "p_user_id": user_id,
            "p_website_id": website_id,
            "p_name": zone.name,
            "p_color": zone.color,
            "p_fee_cents": zone.fee_cents,
            "p_min_order_cents": zone.min_order_cents,
            "p_polygon_geojson": json.dumps(zone.polygon),
            "p_schedule_json": schedule_payload,
            "p_estimated_delivery_min": zone.estimated_delivery_min,
            "p_max_simultaneous_orders": zone.max_simultaneous_orders,
            "p_customer_notes": zone.customer_notes,
            "p_active": zone.active,
            "p_inner_radius_m": zone.inner_radius_m,
            "p_outer_radius_m": zone.outer_radius_m,
        }
        res = supabase.rpc("insert_delivery_zone", rpc_args).execute()
        new_id = res.data
        if not new_id:
            raise HTTPException(status_code=500, detail="Insert returned no id")

        # Fetch back via list RPC, filter client-side
        rows = supabase.rpc(
            "list_delivery_zones", {"p_website_id": website_id}
        ).execute().data or []
        row = next((r for r in rows if str(r["id"]) == str(new_id)), None)
        if not row:
            raise HTTPException(status_code=500, detail="Inserted zone not visible")
        return _row_to_zone_out(row)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "forbidden" in msg.lower():
            raise HTTPException(status_code=403, detail="Not your website")
        logger.error(f"create_zone failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create zone: {e}")


@router.patch("/{zone_id}", response_model=ZoneOut)
async def update_zone(
    zone_id: str,
    patch: ZonePatch,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Partial update of a zone."""
    user_id = current_user["sub"]
    website_id = _verify_zone_ownership(supabase, zone_id, user_id)
    try:
        polygon_geojson = json.dumps(patch.polygon) if patch.polygon else None
        schedule_payload = None
        if patch.schedule_json:
            schedule_payload = {
                k: v.model_dump() if hasattr(v, "model_dump") else v
                for k, v in patch.schedule_json.items()
            }

        rpc_args = {
            "p_user_id": user_id,
            "p_zone_id": zone_id,
            "p_name": patch.name,
            "p_color": patch.color,
            "p_fee_cents": patch.fee_cents,
            "p_min_order_cents": patch.min_order_cents,
            "p_polygon_geojson": polygon_geojson,
            "p_schedule_json": schedule_payload,
            "p_estimated_delivery_min": patch.estimated_delivery_min,
            "p_max_simultaneous_orders": patch.max_simultaneous_orders,
            "p_customer_notes": patch.customer_notes,
            "p_active": patch.active,
            "p_inner_radius_m": patch.inner_radius_m,
            "p_outer_radius_m": patch.outer_radius_m,
        }
        supabase.rpc("update_delivery_zone", rpc_args).execute()

        rows = supabase.rpc(
            "list_delivery_zones", {"p_website_id": website_id}
        ).execute().data or []
        row = next((r for r in rows if str(r["id"]) == str(zone_id)), None)
        if not row:
            raise HTTPException(status_code=404, detail="Zone not found")
        return _row_to_zone_out(row)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "forbidden" in msg.lower():
            raise HTTPException(status_code=403, detail="Not your zone")
        logger.error(f"update_zone failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update zone: {e}")


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(
    zone_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Delete a zone after verifying ownership."""
    _verify_zone_ownership(supabase, zone_id, current_user["sub"])
    try:
        res = supabase.table("delivery_zones").delete().eq("id", zone_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=404, detail="Zon tidak dijumpai"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_zone failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete zone: {e}")


# =====================================================
# Postcode test (point-in-zone lookup)
# =====================================================
class ZoneTestResult(BaseModel):
    covered: bool
    zone_id: str | None = None
    name: str | None = None
    fee_cents: int | None = None
    min_order_cents: int | None = None
    color: str | None = None


@router.get("/website/{website_id}/test", response_model=ZoneTestResult)
async def test_point(
    website_id: str,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    include_inactive: bool = Query(False),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Return the smallest zone covering (lat,lng), or covered=false.

    By default only active zones are considered. Owner postcode test can pass
    include_inactive=true to preview against draft zones.
    """
    _verify_website_ownership(supabase, website_id, current_user["sub"])
    try:
        res = supabase.rpc(
            "find_zone_for_point",
            {
                "p_website_id": website_id,
                "p_lat": lat,
                "p_lng": lng,
                "p_only_active": not include_inactive,
            },
        ).execute()
        rows = res.data or []
        if not rows:
            return ZoneTestResult(covered=False)
        r = rows[0]
        return ZoneTestResult(
            covered=True,
            zone_id=str(r["id"]),
            name=r["name"],
            fee_cents=r["fee_cents"],
            min_order_cents=r["min_order_cents"],
            color=r["color"],
        )
    except Exception as e:
        logger.error(f"test_point failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test point: {e}")


# =====================================================
# Geocoder proxy (Nominatim) — server-side to obey TOS
# =====================================================
_GEOCODE_CACHE: Dict[str, tuple[float, dict]] = {}
_GEOCODE_TTL = 60 * 60 * 24 * 7  # 7 days
_GEOCODE_CACHE_MAX = 5000  # hard cap to prevent unbounded growth


class GeocodeResult(BaseModel):
    found: bool
    lat: float | None = None
    lng: float | None = None
    display_name: str | None = None


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


@router.get("/geocode", response_model=GeocodeResult)
async def geocode_postcode(
    postcode: str = Query(..., min_length=5, max_length=5),
    country: str = Query("MY", min_length=2, max_length=2),
    _user: Dict = Depends(get_current_user),
):
    """Resolve a 5-digit postcode → lat/lng via Nominatim. Caches in-process.

    Postcode format is validated against /^\\d{5}$/ before hitting Nominatim
    to defend the User-Agent's IP against rate-limiting from spammy / nonsense
    inputs (e.g. ?postcode=KFC).
    """
    pc = postcode.strip()
    if not _MY_POSTCODE_RE.match(pc):
        raise HTTPException(
            status_code=400, detail="Postcode mesti 5 digit"
        )

    key = f"{country.upper()}:{pc}"
    cached = _cache_get(key)
    if cached is not None:
        return GeocodeResult(**cached)

    headers = {"User-Agent": "BinaApp/1.0 (admin@binaapp.my)"}
    params = {
        "postalcode": pc,
        "country": country,
        "format": "json",
        "limit": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Geocoder masa tamat")
    except Exception as e:
        logger.error(f"Nominatim error: {e}")
        raise HTTPException(status_code=502, detail="Geocoder unavailable")

    if not data:
        result = {"found": False, "lat": None, "lng": None, "display_name": None}
    else:
        first = data[0]
        result = {
            "found": True,
            "lat": float(first["lat"]),
            "lng": float(first["lon"]),
            "display_name": first.get("display_name"),
        }
    _cache_put(key, result)
    return GeocodeResult(**result)


# =====================================================
# Free-text address geocoder — used for auto-locating outlets
# from registered location_address. Same Nominatim proxy + cache as
# postcode lookup, but accepts arbitrary text via Nominatim's `q=` param.
# =====================================================
_ADDRESS_MIN_LEN = 4
_ADDRESS_MAX_LEN = 300


@router.get("/geocode-address", response_model=GeocodeResult)
async def geocode_address(
    q: str = Query(..., min_length=_ADDRESS_MIN_LEN, max_length=_ADDRESS_MAX_LEN),
    country: str = Query("MY", min_length=2, max_length=2),
    _user: Dict = Depends(get_current_user),
):
    """Resolve a free-text address → lat/lng via Nominatim.

    Used by the penghantaran page to auto-locate the outlet from the
    registered location_address on first visit. Cached identically to
    geocode_postcode to stay within Nominatim's rate limits.
    """
    query = q.strip()
    if len(query) < _ADDRESS_MIN_LEN:
        raise HTTPException(status_code=400, detail="Alamat terlalu pendek")

    key = f"ADDR:{country.upper()}:{query.lower()}"
    cached = _cache_get(key)
    if cached is not None:
        return GeocodeResult(**cached)

    headers = {"User-Agent": "BinaApp/1.0 (admin@binaapp.my)"}
    params = {
        "q": query,
        "countrycodes": country.lower(),
        "format": "json",
        "limit": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Geocoder masa tamat")
    except Exception as e:
        logger.error(f"Nominatim address error: {e}")
        raise HTTPException(status_code=502, detail="Geocoder unavailable")

    if not data:
        result = {"found": False, "lat": None, "lng": None, "display_name": None}
    else:
        first = data[0]
        result = {
            "found": True,
            "lat": float(first["lat"]),
            "lng": float(first["lon"]),
            "display_name": first.get("display_name"),
        }
    _cache_put(key, result)
    return GeocodeResult(**result)


# =====================================================
# Website info + outlet location pin
# =====================================================
class WebsiteOut(BaseModel):
    id: str
    name: str | None = None
    business_name: str | None = None
    location_address: str | None = None
    lat: float | None = None
    lng: float | None = None


class WebsiteLocationIn(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class WebsiteLocationOut(BaseModel):
    website_id: str
    lat: float
    lng: float


@router.get("/website/{website_id}/info", response_model=WebsiteOut)
async def get_website_info(
    website_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Return basic website info needed by the penghantaran page
    (name, address, current outlet pin)."""
    _verify_website_ownership(supabase, website_id, current_user["sub"])
    try:
        res = (
            supabase.table("websites")
            .select("id,name,business_name,location_address,lat,lng")
            .eq("id", website_id)
            .single()
            .execute()
        )
        d = res.data
        if not d:
            raise HTTPException(status_code=404, detail="Website not found")
        return WebsiteOut(
            id=str(d["id"]),
            name=d.get("name"),
            business_name=d.get("business_name"),
            location_address=d.get("location_address"),
            lat=d.get("lat"),
            lng=d.get("lng"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_website_info failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load website")


@router.put("/website/{website_id}/location", response_model=WebsiteLocationOut)
async def set_website_location(
    website_id: str,
    body: WebsiteLocationIn,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Set the outlet pin location for the website. Used by penghantaran
    page on first-run setup and the 'Tukar lokasi' action."""
    user_id = current_user["sub"]
    _verify_website_ownership(supabase, website_id, user_id)
    try:
        supabase.rpc(
            "update_website_location",
            {
                "p_user_id": user_id,
                "p_website_id": website_id,
                "p_lat": body.lat,
                "p_lng": body.lng,
            },
        ).execute()
        return WebsiteLocationOut(website_id=website_id, lat=body.lat, lng=body.lng)
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "forbidden" in msg.lower():
            raise HTTPException(status_code=403, detail="Bukan website anda")
        logger.error(f"set_website_location failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to set location")
