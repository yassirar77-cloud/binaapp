"""
Delivery Zones API — owner-side admin endpoints for /dashboard/penghantaran.

These endpoints power the per-website zone manager. They sit alongside the
legacy /delivery/zones/{website_id} endpoint, which is still used by the
public customer flow. New owner UI MUST use these (/zones/...) routes.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel, Field
from supabase import Client, create_client

from app.core.security import get_current_user

router = APIRouter(prefix="/zones", tags=["Delivery Zones (Owner)"])
bearer_scheme = HTTPBearer()


# =====================================================
# RLS-aware Supabase client
# =====================================================
def _rls_client(token: str) -> Client:
    url = os.getenv("SUPABASE_URL", "")
    anon = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not anon:
        raise HTTPException(
            status_code=500,
            detail="Supabase not configured (SUPABASE_URL / SUPABASE_ANON_KEY)",
        )
    client = create_client(url, anon)
    client.postgrest.auth(token)
    return client


def get_rls_supabase(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Client:
    return _rls_client(credentials.credentials)


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
    created_at: str
    updated_at: str


# =====================================================
# Endpoints
# =====================================================
@router.get("/website/{website_id}", response_model=List[ZoneOut])
async def list_zones(
    website_id: str,
    supabase: Client = Depends(get_rls_supabase),
):
    """List all zones for a website (RLS restricts to owner)."""
    try:
        res = supabase.rpc(
            "list_delivery_zones", {"p_website_id": website_id}
        ).execute()
        rows = res.data or []
        return [
            ZoneOut(
                id=str(r["id"]),
                website_id=str(r["website_id"]),
                name=r["name"],
                color=r["color"],
                fee_cents=r["fee_cents"],
                min_order_cents=r["min_order_cents"],
                polygon=r["polygon_geojson"],
                schedule_json=r["schedule_json"],
                estimated_delivery_min=r.get("estimated_delivery_min"),
                max_simultaneous_orders=r.get("max_simultaneous_orders"),
                customer_notes=r.get("customer_notes"),
                active=r["active"],
                area_m2=r.get("area_m2"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"list_zones failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list zones: {e}")


@router.post("/website/{website_id}", response_model=ZoneOut, status_code=201)
async def create_zone(
    website_id: str,
    zone: ZoneIn,
    supabase: Client = Depends(get_rls_supabase),
):
    """Create a new zone (polygon as GeoJSON)."""
    try:
        schedule = zone.schedule_json or {}
        schedule_payload = {k: v.model_dump() if hasattr(v, "model_dump") else v
                            for k, v in schedule.items()} or None

        rpc_args = {
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
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
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
    supabase: Client = Depends(get_rls_supabase),
):
    """Partial update of a zone."""
    try:
        polygon_geojson = json.dumps(patch.polygon) if patch.polygon else None
        schedule_payload = None
        if patch.schedule_json:
            schedule_payload = {
                k: v.model_dump() if hasattr(v, "model_dump") else v
                for k, v in patch.schedule_json.items()
            }

        rpc_args = {
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
        }
        supabase.rpc("update_delivery_zone", rpc_args).execute()

        # Resolve website_id from the zone, then read back via list RPC
        meta = supabase.table("delivery_zones").select("website_id").eq("id", zone_id).single().execute()
        website_id = meta.data["website_id"]
        rows = supabase.rpc(
            "list_delivery_zones", {"p_website_id": website_id}
        ).execute().data or []
        row = next((r for r in rows if str(r["id"]) == str(zone_id)), None)
        if not row:
            raise HTTPException(status_code=404, detail="Zone not found")
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
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
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
    supabase: Client = Depends(get_rls_supabase),
):
    try:
        supabase.table("delivery_zones").delete().eq("id", zone_id).execute()
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
    supabase: Client = Depends(get_rls_supabase),
):
    """Return the smallest active zone covering (lat,lng), or covered=false."""
    try:
        res = supabase.rpc(
            "find_zone_for_point",
            {"p_website_id": website_id, "p_lat": lat, "p_lng": lng},
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


class GeocodeResult(BaseModel):
    found: bool
    lat: float | None = None
    lng: float | None = None
    display_name: str | None = None


@router.get("/geocode", response_model=GeocodeResult)
async def geocode_postcode(
    postcode: str = Query(..., min_length=3, max_length=10),
    country: str = Query("MY", min_length=2, max_length=2),
    _user: Dict = Depends(get_current_user),
):
    """Resolve postcode → lat/lng via Nominatim. Caches in-process."""
    key = f"{country.upper()}:{postcode.strip()}"
    now = time.time()
    cached = _GEOCODE_CACHE.get(key)
    if cached and now - cached[0] < _GEOCODE_TTL:
        return GeocodeResult(**cached[1])

    headers = {"User-Agent": "BinaApp/1.0 (admin@binaapp.my)"}
    params = {
        "postalcode": postcode,
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
    _GEOCODE_CACHE[key] = (now, result)
    return GeocodeResult(**result)
