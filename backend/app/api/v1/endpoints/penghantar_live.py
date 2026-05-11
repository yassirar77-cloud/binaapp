"""
Penghantar Live API — owner-side live monitoring endpoints for
/dashboard/penghantar-live.

Auth pattern is the same as delivery_zones.py: custom-JWT verified via
get_current_user, Supabase queried via the service-role client, ownership
checked in Python (and again inside mutating RPCs because they accept
p_user_id explicitly).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from supabase import Client

from app.core.security import get_current_user
from app.core.supabase import get_supabase_client

router = APIRouter(prefix="/live", tags=["Penghantar Live (Owner)"])


# =====================================================
# Ownership helper — duplicated from delivery_zones.py to keep this PR small.
# TODO: lift to app/core/ownership.py in a future refactor PR.
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


# =====================================================
# RPC error → HTTP status mapping
# =====================================================
def _map_rpc_error(exc: Exception, op_label: str) -> HTTPException:
    """Translate a Postgrest/supabase-py RPC exception into an HTTPException.

    The mutating RPCs (reassign_order_rider, cancel_delivery_order) raise
    typed text exceptions from Postgres. supabase-py surfaces these via the
    exception's str() — there is no stable exception class across versions,
    so we match on the message text just like delivery_zones.py does.
    """
    msg = str(exc).lower()

    if "forbidden" in msg:
        return HTTPException(
            status_code=403, detail="Anda tiada kebenaran untuk pesanan ini"
        )
    if "rider not in this outlet" in msg:
        return HTTPException(
            status_code=400, detail="Rider ini bukan dari outlet anda"
        )
    if "cannot cancel order in status" in msg:
        return HTTPException(
            status_code=400,
            detail="Pesanan ini tidak boleh dibatalkan dalam status semasa",
        )
    if "cannot reassign rider on order in status" in msg:
        return HTTPException(
            status_code=400,
            detail="Pesanan dalam status ini tidak boleh ditukar rider",
        )
    if "cancellation reason must be at least" in msg or "minimum" in msg:
        return HTTPException(
            status_code=400, detail="Sebab pembatalan terlalu pendek"
        )

    logger.error(f"{op_label} failed: {exc}")
    return HTTPException(status_code=500, detail="Ralat sistem. Sila cuba lagi.")


# =====================================================
# Pydantic schemas
# =====================================================
class OrderItemOut(BaseModel):
    id: Optional[str] = None
    menu_item_id: Optional[str] = None
    item_name: str
    quantity: int
    unit_price: float
    total_price: float
    options: Any | None = None
    notes: Optional[str] = None


class ActiveOrderOut(BaseModel):
    id: str
    order_number: str
    customer_name: str
    customer_phone: str
    delivery_address: str
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    items: List[OrderItemOut] = Field(default_factory=list)
    subtotal: float
    delivery_fee: float
    total_amount: float
    status: str
    created_at: str
    picked_up_at: Optional[str] = None
    estimated_delivery_time: Optional[int] = None
    eta_at: Optional[str] = None
    rider_id: Optional[str] = None
    rider_name: Optional[str] = None
    rider_phone: Optional[str] = None
    rider_vehicle_plate: Optional[str] = None
    rider_current_latitude: Optional[float] = None
    rider_current_longitude: Optional[float] = None
    rider_last_location_update: Optional[str] = None
    rider_is_online: Optional[bool] = None
    delivery_zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    zone_color: Optional[str] = None
    zone_outer_radius_m: Optional[int] = None


class LiveRiderOut(BaseModel):
    id: str
    name: str
    phone: str
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_model: Optional[str] = None
    is_active: bool
    is_online: bool
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    last_location_update: Optional[str] = None
    active_order_id: Optional[str] = None
    active_order_number: Optional[str] = None
    active_order_eta_at: Optional[str] = None
    active_order_status: Optional[str] = None
    today_deliveries: int = 0


class ReassignBody(BaseModel):
    new_rider_id: Optional[str] = None  # null → unassign


class CancelBody(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def _strip_and_min_length(cls, v: str) -> str:
        stripped = (v or "").strip()
        if len(stripped) < 10:
            raise ValueError(
                "Sebab pembatalan mesti sekurang-kurangnya 10 aksara"
            )
        if len(stripped) > 500:
            raise ValueError("Sebab pembatalan terlalu panjang (maksimum 500 aksara)")
        return stripped


# =====================================================
# Row mappers — Supabase returns dicts; coerce to Pydantic models.
# Numeric fields come back as Decimal/str sometimes; cast defensively.
# =====================================================
def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _as_str(v: Any) -> Optional[str]:
    return None if v is None else str(v)


def _row_to_active_order(r: Dict[str, Any]) -> ActiveOrderOut:
    items_raw = r.get("items") or []
    items = [
        OrderItemOut(
            id=_as_str(i.get("id")),
            menu_item_id=_as_str(i.get("menu_item_id")),
            item_name=i.get("item_name") or "",
            quantity=_as_int(i.get("quantity")) or 0,
            unit_price=_as_float(i.get("unit_price")) or 0.0,
            total_price=_as_float(i.get("total_price")) or 0.0,
            options=i.get("options"),
            notes=i.get("notes"),
        )
        for i in items_raw
    ]
    return ActiveOrderOut(
        id=str(r["id"]),
        order_number=r["order_number"],
        customer_name=r["customer_name"],
        customer_phone=r["customer_phone"],
        delivery_address=r["delivery_address"],
        delivery_latitude=_as_float(r.get("delivery_latitude")),
        delivery_longitude=_as_float(r.get("delivery_longitude")),
        items=items,
        subtotal=_as_float(r.get("subtotal")) or 0.0,
        delivery_fee=_as_float(r.get("delivery_fee")) or 0.0,
        total_amount=_as_float(r.get("total_amount")) or 0.0,
        status=r["status"],
        created_at=r["created_at"],
        picked_up_at=_as_str(r.get("picked_up_at")),
        estimated_delivery_time=_as_int(r.get("estimated_delivery_time")),
        eta_at=_as_str(r.get("eta_at")),
        rider_id=_as_str(r.get("rider_id")),
        rider_name=r.get("rider_name"),
        rider_phone=r.get("rider_phone"),
        rider_vehicle_plate=r.get("rider_vehicle_plate"),
        rider_current_latitude=_as_float(r.get("rider_current_latitude")),
        rider_current_longitude=_as_float(r.get("rider_current_longitude")),
        rider_last_location_update=_as_str(r.get("rider_last_location_update")),
        rider_is_online=r.get("rider_is_online"),
        delivery_zone_id=_as_str(r.get("delivery_zone_id")),
        zone_name=r.get("zone_name"),
        zone_color=r.get("zone_color"),
        zone_outer_radius_m=_as_int(r.get("zone_outer_radius_m")),
    )


def _row_to_live_rider(r: Dict[str, Any]) -> LiveRiderOut:
    return LiveRiderOut(
        id=str(r["id"]),
        name=r["name"],
        phone=r["phone"],
        vehicle_plate=r.get("vehicle_plate"),
        vehicle_type=r.get("vehicle_type"),
        vehicle_model=r.get("vehicle_model"),
        is_active=bool(r.get("is_active")),
        is_online=bool(r.get("is_online")),
        current_latitude=_as_float(r.get("current_latitude")),
        current_longitude=_as_float(r.get("current_longitude")),
        last_location_update=_as_str(r.get("last_location_update")),
        active_order_id=_as_str(r.get("active_order_id")),
        active_order_number=r.get("active_order_number"),
        active_order_eta_at=_as_str(r.get("active_order_eta_at")),
        active_order_status=r.get("active_order_status"),
        today_deliveries=_as_int(r.get("today_deliveries")) or 0,
    )


# =====================================================
# Endpoints
# =====================================================
@router.get(
    "/website/{website_id}/orders", response_model=List[ActiveOrderOut]
)
async def list_active_orders_endpoint(
    website_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """List active orders (status in pending/confirmed/preparing/ready/picked_up/delivering)
    for a website, with denormalized rider + zone info and aggregated items."""
    _verify_website_ownership(supabase, website_id, current_user["sub"])
    try:
        res = supabase.rpc(
            "list_active_orders", {"p_website_id": website_id}
        ).execute()
        rows = res.data or []
        return [_row_to_active_order(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"list_active_orders failed: {e}")
        raise HTTPException(
            status_code=500, detail="Gagal memuatkan pesanan aktif"
        )


@router.get(
    "/website/{website_id}/riders", response_model=List[LiveRiderOut]
)
async def list_live_riders_endpoint(
    website_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """List riders for a website with current GPS + most-recent active order
    info and today's delivered count."""
    _verify_website_ownership(supabase, website_id, current_user["sub"])
    try:
        res = supabase.rpc(
            "list_riders_with_orders", {"p_website_id": website_id}
        ).execute()
        rows = res.data or []
        return [_row_to_live_rider(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"list_riders_with_orders failed: {e}")
        raise HTTPException(status_code=500, detail="Gagal memuatkan rider")


@router.patch("/orders/{order_id}/rider", status_code=204)
async def reassign_order_rider_endpoint(
    order_id: str,
    body: ReassignBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Reassign (or unassign with new_rider_id=null) the rider on an order.

    Ownership and same-website-rider checks are enforced inside the RPC.
    Errors are mapped to 403 / 400 / 500 by _map_rpc_error.
    """
    user_id = current_user["sub"]
    try:
        supabase.rpc(
            "reassign_order_rider",
            {
                "p_user_id": user_id,
                "p_order_id": order_id,
                "p_new_rider_id": body.new_rider_id,
            },
        ).execute()
    except HTTPException:
        raise
    except Exception as e:
        raise _map_rpc_error(e, "reassign_order_rider")
    return Response(status_code=204)


@router.post("/orders/{order_id}/cancel", status_code=204)
async def cancel_order_endpoint(
    order_id: str,
    body: CancelBody,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Cancel an order. Status change only — refund is handled manually by
    the owner. The RPC refuses orders already delivered/completed/cancelled
    and requires reason >= 10 chars (frontend validates first via Pydantic)."""
    user_id = current_user["sub"]
    try:
        supabase.rpc(
            "cancel_delivery_order",
            {
                "p_user_id": user_id,
                "p_order_id": order_id,
                "p_reason": body.reason,
            },
        ).execute()
    except HTTPException:
        raise
    except Exception as e:
        raise _map_rpc_error(e, "cancel_delivery_order")
    return Response(status_code=204)
