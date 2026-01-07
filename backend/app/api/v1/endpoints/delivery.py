"""
BinaApp Delivery System API Endpoints
Handles real-time food delivery and order tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from typing import List, Optional
from loguru import logger
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel
import os
from supabase import create_client

from app.core.supabase import get_supabase_client
from app.models.delivery_schemas import (
    # Zones
    DeliveryZoneResponse,
    ZonesWithSettingsResponse,
    CoverageCheckRequest,
    CoverageCheckResponse,
    # Menu
    MenuResponse,
    MenuItemResponse,
    MenuCategoryResponse,
    # Orders
    OrderCreate,
    OrderResponse,
    OrderTrackingResponse,
    OrderItemResponse,
    OrderStatusHistoryResponse,
    OrderStatusUpdate,
    RiderInfoResponse,
    RiderLocationResponse,
    RiderResponse,
    RiderCreateBusiness,
    AssignRiderRequest,
    DeliverySettingsResponse,
    DeliverySettingsUpdate,
)

router = APIRouter(prefix="/delivery", tags=["Delivery System"])
bearer_scheme = HTTPBearer()


# =====================================================
# AUTHENTICATED (RLS) SUPABASE CLIENT
# =====================================================

def get_supabase_rls_client(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Client:
    """
    Create a Supabase client that uses the caller's Supabase JWT for RLS.

    This is required for business/admin operations so we do NOT bypass Row Level Security.
    """
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_KEY")  # fallback (some envs reuse this name)
        or ""
    )

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase not configured for authenticated requests (missing SUPABASE_URL / SUPABASE_ANON_KEY)",
        )

    client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    # Apply JWT for PostgREST calls (enforces RLS)
    client.postgrest.auth(credentials.credentials)
    return client


# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def convert_db_row_to_dict(row: dict) -> dict:
    """Convert database row to dict, handling decimal types"""
    result = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, datetime):
            result[key] = value
        else:
            result[key] = value
    return result


# =====================================================
# ZONE & COVERAGE ENDPOINTS
# =====================================================

@router.get("/zones/{website_id}", response_model=ZonesWithSettingsResponse)
async def get_delivery_zones(
    website_id: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get all delivery zones for a website with delivery settings

    **Public endpoint** - Used by customer ordering widget
    """
    try:
        # Get active delivery zones
        zones_response = supabase.table("delivery_zones").select("*").eq(
            "website_id", website_id
        ).eq("is_active", True).order("sort_order").execute()

        # Get delivery settings
        settings_response = supabase.table("delivery_settings").select("*").eq(
            "website_id", website_id
        ).execute()

        zones = [convert_db_row_to_dict(z) for z in zones_response.data]
        settings = convert_db_row_to_dict(settings_response.data[0]) if settings_response.data else None

        return {
            "zones": zones,
            "settings": settings
        }

    except Exception as e:
        logger.error(f"Error fetching delivery zones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch delivery zones: {str(e)}"
        )


@router.post("/check-coverage", response_model=CoverageCheckResponse)
async def check_delivery_coverage(
    request: CoverageCheckRequest,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Check if a location is within delivery coverage

    **Note:** Currently returns the first active zone.
    In production, implement proper geofencing using PostGIS.
    """
    try:
        # Get all active zones for this website
        response = supabase.table("delivery_zones").select("*").eq(
            "website_id", request.website_id
        ).eq("is_active", True).execute()

        if not response.data:
            return {
                "covered": False,
                "message": "No delivery zones available for this location"
            }

        # TODO: Implement proper geofencing with PostGIS
        # For MVP, just return the first zone as covered
        zone = convert_db_row_to_dict(response.data[0])

        return {
            "covered": True,
            "zone": zone,
            "fee": zone['delivery_fee'],
            "estimated_time": f"{zone['estimated_time_min']}-{zone['estimated_time_max']} min",
            "message": f"Delivery available to {zone['zone_name']}"
        }

    except Exception as e:
        logger.error(f"Error checking coverage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check coverage: {str(e)}"
        )


# =====================================================
# MENU ENDPOINTS
# =====================================================

@router.get("/menu/{website_id}", response_model=MenuResponse)
async def get_menu(
    website_id: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get complete menu with categories and items

    **Public endpoint** - Used by customer ordering widget
    """
    try:
        # Get categories
        categories_response = supabase.table("menu_categories").select("*").eq(
            "website_id", website_id
        ).eq("is_active", True).order("sort_order").execute()

        # Get menu items with options
        items_response = supabase.table("menu_items").select(
            "*"
        ).eq("website_id", website_id).eq("is_available", True).order("sort_order").execute()

        categories = [convert_db_row_to_dict(c) for c in categories_response.data]
        items = [convert_db_row_to_dict(i) for i in items_response.data]

        # For each item, get its options
        for item in items:
            options_response = supabase.table("menu_item_options").select("*").eq(
                "menu_item_id", item['id']
            ).order("sort_order").execute()
            item['options'] = [convert_db_row_to_dict(o) for o in options_response.data]

        return {
            "categories": categories,
            "items": items
        }

    except Exception as e:
        logger.error(f"Error fetching menu: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch menu: {str(e)}"
        )


@router.get("/menu/{website_id}/item/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    website_id: str,
    item_id: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get single menu item with options
    """
    try:
        # Get menu item
        item_response = supabase.table("menu_items").select("*").eq(
            "id", item_id
        ).eq("website_id", website_id).execute()

        if not item_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )

        item = convert_db_row_to_dict(item_response.data[0])

        # Get options
        options_response = supabase.table("menu_item_options").select("*").eq(
            "menu_item_id", item_id
        ).order("sort_order").execute()

        item['options'] = [convert_db_row_to_dict(o) for o in options_response.data]

        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching menu item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch menu item: {str(e)}"
        )


# =====================================================
# ORDER ENDPOINTS
# =====================================================

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Create a new delivery order

    **Public endpoint** - Customers can place orders without authentication
    """
    try:
        # 1. Fetch menu items to calculate prices
        menu_item_ids = [item.menu_item_id for item in order.items]
        items_response = supabase.table("menu_items").select("*").in_(
            "id", menu_item_ids
        ).execute()

        if len(items_response.data) != len(menu_item_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some menu items not found"
            )

        # Create menu items lookup
        menu_items_map = {item['id']: item for item in items_response.data}

        # 2. Get delivery zone for fee (optional for pickup orders)
        zone = None
        delivery_fee = 0.0

        if order.delivery_zone_id:
            zone_response = supabase.table("delivery_zones").select("*").eq(
                "id", order.delivery_zone_id
            ).execute()

            if not zone_response.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid delivery zone"
                )

            zone = zone_response.data[0]
            delivery_fee = float(zone['delivery_fee'])

        # 3. Calculate order totals
        subtotal = Decimal("0")
        order_items_data = []

        for item_create in order.items:
            menu_item = menu_items_map[item_create.menu_item_id]
            unit_price = Decimal(str(menu_item['price']))

            # TODO: Add price modifiers from options
            total_price = unit_price * item_create.quantity
            subtotal += total_price

            order_items_data.append({
                "menu_item_id": item_create.menu_item_id,
                "item_name": menu_item['name'],
                "quantity": item_create.quantity,
                "unit_price": float(unit_price),
                "total_price": float(total_price),
                "options": item_create.options,
                "notes": item_create.notes
            })

        # Check minimum order (only when delivery zone is provided)
        if zone and subtotal < Decimal(str(zone.get('minimum_order', 0))):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Minimum order is RM{zone['minimum_order']}"
            )

        total_amount = subtotal + Decimal(str(delivery_fee))

        # 4. Create order record (order_number auto-generated by trigger)
        order_data = {
            "website_id": order.website_id,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "customer_email": order.customer_email,
            "delivery_address": order.delivery_address,
            "delivery_latitude": float(order.delivery_latitude) if order.delivery_latitude else None,
            "delivery_longitude": float(order.delivery_longitude) if order.delivery_longitude else None,
            "delivery_notes": order.delivery_notes,
            "delivery_zone_id": order.delivery_zone_id,
            "delivery_fee": delivery_fee,
            "subtotal": float(subtotal),
            "total_amount": float(total_amount),
            "payment_method": order.payment_method.value,
            "payment_status": "pending",
            "status": "pending",
            "estimated_prep_time": 30,  # Default 30 minutes
            "estimated_delivery_time": zone['estimated_time_min'] if zone else None
        }

        order_response = supabase.table("delivery_orders").insert(order_data).execute()

        if not order_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create order"
            )

        created_order = order_response.data[0]
        order_id = created_order['id']

        # 5. Create order items
        for item_data in order_items_data:
            item_data['order_id'] = order_id

        try:
            items_result = supabase.table("order_items").insert(order_items_data).execute()
            if not items_result.data:
                logger.error(f"❌ Failed to insert order items for order {order_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save order items. Please try again."
                )
            logger.info(f"✅ Saved {len(items_result.data)} order items")
        except HTTPException:
            raise
        except Exception as items_error:
            logger.error(f"❌ Error inserting order items: {items_error}")
            # Try to rollback - delete the order if items failed
            try:
                supabase.table("delivery_orders").delete().eq("id", order_id).execute()
                logger.info(f"🔄 Rolled back order {order_id} due to items failure")
            except Exception as rollback_error:
                logger.error(f"❌ Rollback failed: {rollback_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save order items: {str(items_error)}"
            )

        # 6. TODO: Send notifications (WhatsApp, Email)
        logger.info(f"✅ Order created: {created_order['order_number']} - Total: RM{total_amount}")

        # 7. Return created order
        return convert_db_row_to_dict(created_order)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


@router.get("/orders/{order_number}/track", response_model=OrderTrackingResponse)
async def track_order(
    order_number: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get order status and tracking information

    **Public endpoint** - Anyone with order number can track
    """
    try:
        # 1. Get order
        order_response = supabase.table("delivery_orders").select("*").eq(
            "order_number", order_number
        ).execute()

        if not order_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        order = convert_db_row_to_dict(order_response.data[0])
        order_id = order['id']

        # 2. Get order items
        items_response = supabase.table("order_items").select("*").eq(
            "order_id", order_id
        ).execute()

        items = [convert_db_row_to_dict(i) for i in items_response.data]

        # 3. Get status history
        history_response = supabase.table("order_status_history").select("*").eq(
            "order_id", order_id
        ).order("created_at").execute()

        status_history = [convert_db_row_to_dict(h) for h in history_response.data]

        # 4. Get rider info if assigned
        #
        # Phase 1 requirement:
        # - Do NOT expose rider GPS / realtime tracking data publicly.
        # - Only return basic rider info once assigned.
        rider = None
        rider_location = None
        eta_minutes = None

        if order.get('rider_id'):
            rider_response = supabase.table("riders").select(
                "id, name, phone, photo_url, vehicle_type, vehicle_plate, rating, current_latitude, current_longitude"
            ).eq("id", order['rider_id']).execute()

            if rider_response.data:
                rider = convert_db_row_to_dict(rider_response.data[0])
                # Phase 1: explicitly do not expose GPS fields publicly
                rider["current_latitude"] = None
                rider["current_longitude"] = None

                # TODO: Calculate ETA using Google Maps API
                eta_minutes = order.get('estimated_delivery_time', 30)

        return {
            "order": order,
            "items": items,
            "status_history": status_history,
            "rider": rider,
            "rider_location": rider_location,  # Always None in Phase 1
            "eta_minutes": eta_minutes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track order: {str(e)}"
        )


# =====================================================
# BUSINESS ORDER MANAGEMENT ENDPOINTS
# =====================================================

@router.get("/admin/orders", response_model=List[OrderResponse])
async def get_my_business_orders(
    status_filter: Optional[str] = None,
    supabase: Client = Depends(get_supabase_rls_client),
):
    """
    Get orders for the authenticated user's websites (RLS enforced).
    """
    try:
        query = supabase.table("delivery_orders").select("*").order("created_at", desc=True)
        if status_filter:
            query = query.eq("status", status_filter)
        orders_response = query.execute()
        return [convert_db_row_to_dict(o) for o in (orders_response.data or [])]
    except Exception as e:
        logger.error(f"Error fetching authenticated business orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orders: {str(e)}",
        )


@router.get("/orders/business/{user_id}", response_model=List[OrderResponse])
async def get_business_orders(
    user_id: str,
    status_filter: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get all orders for websites owned by a user

    **Authenticated endpoint** - Business owners can view their orders
    """
    try:
        # 1. Get all websites owned by this user
        websites_response = supabase.table("websites").select("id").eq(
            "user_id", user_id
        ).execute()

        if not websites_response.data:
            return []

        website_ids = [w['id'] for w in websites_response.data]

        # 2. Get all orders for these websites
        query = supabase.table("delivery_orders").select("*").in_(
            "website_id", website_ids
        ).order("created_at", desc=True)

        if status_filter:
            query = query.eq("status", status_filter)

        orders_response = query.execute()

        orders = [convert_db_row_to_dict(o) for o in orders_response.data]

        return orders

    except Exception as e:
        logger.error(f"Error fetching business orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orders: {str(e)}"
        )


@router.put("/admin/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status_admin(
    order_id: str,
    status_update: OrderStatusUpdate,
    supabase: Client = Depends(get_supabase_rls_client),
):
    """
    Update order status (RLS enforced).
    """
    try:
        # 1. Get current order (RLS will restrict)
        order_response = supabase.table("delivery_orders").select("*").eq("id", order_id).execute()
        if not order_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        current_order = order_response.data[0]
        new_status = status_update.status.value

        # 2. Prepare update data with timestamp
        update_data = {"status": new_status}
        timestamp_field = f"{new_status}_at"
        if timestamp_field in [
            "confirmed_at",
            "preparing_at",
            "ready_at",
            "picked_up_at",
            "delivered_at",
            "completed_at",
            "cancelled_at",
        ]:
            update_data[timestamp_field] = datetime.utcnow().isoformat()

        updated_response = supabase.table("delivery_orders").update(update_data).eq("id", order_id).execute()
        if not updated_response.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update order status")

        # Also insert explicit history row (in addition to DB trigger), so Phase 1 admin UI works
        # even if triggers are disabled in some environments.
        try:
            supabase.table("order_status_history").insert(
                {
                    "order_id": order_id,
                    "status": new_status,
                    "notes": status_update.notes,
                    "updated_by": "business",
                }
            ).execute()
        except Exception as history_err:
            logger.warning(f"⚠️ Could not insert order_status_history (continuing): {history_err}")

        logger.info(
            f"✅ Order {current_order.get('order_number')} status updated: {current_order.get('status')} → {new_status}"
        )
        return convert_db_row_to_dict(updated_response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}",
        )


@router.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Update order status

    **Authenticated endpoint** - Business owners can update order status

    Status flow: pending → confirmed → preparing → ready → delivered
    """
    try:
        # 1. Get current order
        order_response = supabase.table("delivery_orders").select("*").eq(
            "id", order_id
        ).execute()

        if not order_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        current_order = order_response.data[0]
        new_status = status_update.status.value

        # 2. Prepare update data with timestamp
        update_data = {"status": new_status}
        timestamp_field = f"{new_status}_at"
        if timestamp_field in ['confirmed_at', 'preparing_at', 'ready_at', 'picked_up_at', 'delivered_at', 'completed_at', 'cancelled_at']:
            update_data[timestamp_field] = datetime.utcnow().isoformat()

        # 3. Update order status
        updated_response = supabase.table("delivery_orders").update(
            update_data
        ).eq("id", order_id).execute()

        if not updated_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order status"
            )

        # 4. Add to status history
        history_data = {
            "order_id": order_id,
            "status": new_status,
            "notes": status_update.notes,
            "updated_by": "business"
        }
        supabase.table("order_status_history").insert(history_data).execute()

        logger.info(f"✅ Order {current_order['order_number']} status updated: {current_order['status']} → {new_status}")

        return convert_db_row_to_dict(updated_response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
        )


@router.put("/admin/orders/{order_id}/assign-rider", response_model=OrderResponse)
async def assign_rider_to_order(
    order_id: str,
    payload: AssignRiderRequest,
    supabase: Client = Depends(get_supabase_rls_client),
):
    """
    Assign (or unassign) a rider to an order (RLS enforced).
    Phase 1: supports "Own Riders" only (rider.website_id must match order.website_id).
    """
    try:
        order_resp = supabase.table("delivery_orders").select("id, order_number, website_id").eq("id", order_id).execute()
        if not order_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        order = order_resp.data[0]

        rider_id = payload.rider_id
        if rider_id:
            rider_resp = supabase.table("riders").select("id, website_id, is_active").eq("id", rider_id).execute()
            if not rider_resp.data:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid rider")
            rider = rider_resp.data[0]
            if not rider.get("is_active", True):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rider is inactive")
            if str(rider.get("website_id")) != str(order.get("website_id")):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rider does not belong to this website")

        updated = supabase.table("delivery_orders").update({"rider_id": rider_id}).eq("id", order_id).execute()
        if not updated.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign rider")

        # Optional history note
        try:
            supabase.table("order_status_history").insert(
                {
                    "order_id": order_id,
                    "status": updated.data[0].get("status", "pending"),
                    "notes": "Rider assigned" if rider_id else "Rider unassigned",
                    "updated_by": "business",
                }
            ).execute()
        except Exception as history_err:
            logger.warning(f"⚠️ Could not insert order_status_history for rider assignment (continuing): {history_err}")

        logger.info(f"✅ Rider assignment updated for order {order.get('order_number')}: rider_id={rider_id}")
        return convert_db_row_to_dict(updated.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign rider: {str(e)}",
        )


@router.get("/admin/websites/{website_id}/riders", response_model=List[RiderResponse])
async def list_riders(
    website_id: str,
    supabase: Client = Depends(get_supabase_rls_client),
):
    """List riders for a website (RLS enforced)."""
    try:
        resp = supabase.table("riders").select("*").eq("website_id", website_id).order("created_at", desc=True).execute()
        return [convert_db_row_to_dict(r) for r in (resp.data or [])]
    except Exception as e:
        logger.error(f"Error listing riders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list riders: {str(e)}",
        )


@router.post("/admin/websites/{website_id}/riders", response_model=RiderResponse)
async def create_rider(
    website_id: str,
    rider: RiderCreateBusiness,
    supabase: Client = Depends(get_supabase_rls_client),
):
    """Create a rider for a website (Phase 1: no rider app auth)."""
    try:
        data = rider.dict()
        data["website_id"] = website_id
        resp = supabase.table("riders").insert(data).execute()
        if not resp.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create rider")
        return convert_db_row_to_dict(resp.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rider: {str(e)}",
        )


@router.get("/admin/websites/{website_id}/settings", response_model=DeliverySettingsResponse)
async def get_delivery_settings_admin(
    website_id: str,
    supabase: Client = Depends(get_supabase_rls_client),
):
    """Get delivery settings for a website (RLS enforced). Creates defaults if missing."""
    try:
        resp = supabase.table("delivery_settings").select("*").eq("website_id", website_id).execute()
        if resp.data:
            return convert_db_row_to_dict(resp.data[0])

        # Create defaults
        inserted = supabase.table("delivery_settings").insert({"website_id": website_id}).execute()
        if not inserted.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initialize delivery settings")
        return convert_db_row_to_dict(inserted.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching delivery settings (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch delivery settings: {str(e)}",
        )


@router.put("/admin/websites/{website_id}/settings", response_model=DeliverySettingsResponse)
async def update_delivery_settings_admin(
    website_id: str,
    update: DeliverySettingsUpdate,
    supabase: Client = Depends(get_supabase_rls_client),
):
    """Update delivery settings for a website (RLS enforced)."""
    try:
        # Ensure row exists
        existing = supabase.table("delivery_settings").select("id").eq("website_id", website_id).execute()
        if not existing.data:
            supabase.table("delivery_settings").insert({"website_id": website_id}).execute()

        payload = update.dict(exclude_unset=True)
        updated = supabase.table("delivery_settings").update(payload).eq("website_id", website_id).execute()
        if not updated.data:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update delivery settings")
        return convert_db_row_to_dict(updated.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating delivery settings (admin): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update delivery settings: {str(e)}",
        )


# =====================================================
# WIDGET CONFIGURATION ENDPOINT
# =====================================================

@router.get("/config/{website_id}")
async def get_widget_config(
    website_id: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get widget configuration for a website.

    Returns:
    - businessType: detected from website's business_type or description
    - payment: { cod, qr, qr_image }
    - fulfillment: { delivery, pickup, delivery_fee, min_order, delivery_area, pickup_address }
    - whatsapp_number
    - business_name
    - primary_color
    - categories (based on business type)

    **Public endpoint** - Used by customer ordering widget
    """
    from app.services.business_types import (
        detect_business_type,
        get_business_config,
        get_categories_for_business_type
    )

    try:
        # 1. Get website info
        website_response = supabase.table("websites").select(
            "id, name, business_type, whatsapp_number, description, language, location_address"
        ).eq("id", website_id).execute()

        website = None
        if website_response.data:
            website = website_response.data[0]

        # 2. Get delivery settings
        settings_response = supabase.table("delivery_settings").select("*").eq(
            "website_id", website_id
        ).execute()

        settings = settings_response.data[0] if settings_response.data else None

        # 3. Get first active delivery zone for default fee
        zone_response = supabase.table("delivery_zones").select(
            "zone_name, delivery_fee, minimum_order"
        ).eq("website_id", website_id).eq("is_active", True).order("sort_order").limit(1).execute()

        first_zone = zone_response.data[0] if zone_response.data else None

        # 4. Determine business type
        business_type = "general"
        if website:
            if website.get("business_type"):
                business_type = website["business_type"]
            elif website.get("description"):
                business_type = detect_business_type(website["description"])
            elif website.get("name"):
                business_type = detect_business_type(website["name"])

        # 5. Get business config for categories and colors
        biz_config = get_business_config(business_type)

        # 6. Build response with all configuration needed by widget
        config = {
            "website_id": website_id,
            "business_type": business_type,
            "business_name": website.get("name", "Kedai") if website else "Kedai",
            "whatsapp_number": (
                settings.get("whatsapp_number") if settings else None
            ) or (
                website.get("whatsapp_number") if website else None
            ) or "",
            "language": website.get("language", "ms") if website else "ms",
            "primary_color": biz_config.get("primary_color", "#ea580c"),

            # Payment options
            "payment": {
                "cod": settings.get("accept_cod", True) if settings else True,
                "qr": settings.get("accept_online", False) if settings else False,
                "qr_image": settings.get("qr_payment_image") if settings else None
            },

            # Fulfillment options
            "fulfillment": {
                "delivery": settings.get("delivery_enabled", True) if settings else True,
                "delivery_fee": float(first_zone.get("delivery_fee", 5)) if first_zone else (
                    float(settings.get("default_delivery_fee", 5)) if settings else 5.0
                ),
                "min_order": float(first_zone.get("minimum_order", 20)) if first_zone else (
                    float(settings.get("minimum_order", 20)) if settings else 20.0
                ),
                "delivery_area": first_zone.get("zone_name", "") if first_zone else "",
                "pickup": settings.get("pickup_enabled", True) if settings else True,
                "pickup_address": settings.get("pickup_address") or (
                    website.get("location_address") if website else ""
                ) or ""
            },

            # Categories for this business type
            "categories": biz_config.get("categories", []),

            # Features for this business type
            "features": biz_config.get("features", {})
        }

        logger.info(f"✅ Widget config loaded for {website_id}: type={business_type}")
        return config

    except Exception as e:
        logger.error(f"Error fetching widget config: {e}")
        # Return defaults instead of failing
        return {
            "website_id": website_id,
            "business_type": "food",
            "business_name": "Kedai",
            "whatsapp_number": "",
            "language": "ms",
            "primary_color": "#ea580c",
            "payment": {"cod": True, "qr": False, "qr_image": None},
            "fulfillment": {
                "delivery": True,
                "delivery_fee": 5.0,
                "min_order": 20.0,
                "delivery_area": "",
                "pickup": True,
                "pickup_address": ""
            },
            "categories": [
                {"id": "nasi", "name": "🍚 Nasi", "icon": "🍚"},
                {"id": "lauk", "name": "🍗 Lauk", "icon": "🍗"},
                {"id": "minuman", "name": "🥤 Minuman", "icon": "🥤"}
            ],
            "features": {
                "delivery_zones": True,
                "time_slots": True,
                "special_instructions": True
            }
        }


# =====================================================
# PUBLIC ORDER MANAGEMENT (for simple business dashboards)
# =====================================================

@router.get("/website/{website_id}/orders", response_model=List[OrderResponse])
async def get_website_orders(
    website_id: str,
    status_filter: Optional[str] = None,
    limit: int = 50,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Get all orders for a website (public endpoint for simple dashboards).

    **Note:** This is a public endpoint to enable simple business dashboards.
    For production, consider adding an API key or basic auth.
    """
    try:
        query = supabase.table("delivery_orders").select("*").eq(
            "website_id", website_id
        ).order("created_at", desc=True).limit(limit)

        if status_filter:
            query = query.eq("status", status_filter)

        orders_response = query.execute()
        return [convert_db_row_to_dict(o) for o in (orders_response.data or [])]
    except Exception as e:
        logger.error(f"Error fetching website orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch orders: {str(e)}",
        )


@router.get("/website/{website_id}/riders", response_model=List[RiderResponse])
async def get_website_riders(
    website_id: str,
    online_only: bool = False,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Get all riders for a website (public endpoint for business dashboards).

    Phase 1: Returns basic rider info (no GPS).
    """
    try:
        query = supabase.table("riders").select("*").eq(
            "website_id", website_id
        ).eq("is_active", True).order("name")

        if online_only:
            query = query.eq("is_online", True)

        riders_response = query.execute()
        riders = [convert_db_row_to_dict(r) for r in (riders_response.data or [])]

        # Phase 1: Hide GPS coordinates
        for rider in riders:
            rider["current_latitude"] = None
            rider["current_longitude"] = None

        return riders
    except Exception as e:
        logger.error(f"Error fetching website riders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch riders: {str(e)}",
        )


@router.post("/website/{website_id}/riders", response_model=RiderResponse)
async def create_website_rider(
    website_id: str,
    rider: RiderCreateBusiness,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Create a rider for a website (public endpoint for simple integration).

    Phase 1: No rider app auth required.
    """
    try:
        data = rider.dict()
        data["website_id"] = website_id
        resp = supabase.table("riders").insert(data).execute()
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create rider"
            )
        return convert_db_row_to_dict(resp.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rider: {str(e)}",
        )


@router.put("/website/{website_id}/riders/{rider_id}", response_model=RiderResponse)
async def update_website_rider(
    website_id: str,
    rider_id: str,
    update_data: dict,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Update a rider for a website (public endpoint).

    Allowed fields: name, phone, vehicle_type, vehicle_plate, is_active, is_online.
    """
    try:
        # Validate allowed fields
        allowed_fields = {"name", "phone", "email", "photo_url", "vehicle_type", "vehicle_plate", "vehicle_model", "is_active", "is_online"}
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

        if not filtered_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        resp = supabase.table("riders").update(filtered_data).eq(
            "id", rider_id
        ).eq("website_id", website_id).execute()

        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider not found"
            )
        return convert_db_row_to_dict(resp.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rider: {str(e)}",
        )


@router.put("/orders/{order_id}/assign-rider", response_model=OrderResponse)
async def assign_rider_to_order_public(
    order_id: str,
    payload: AssignRiderRequest,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Assign (or unassign) a rider to an order (public endpoint for simple dashboards).

    Phase 1: supports "Own Riders" only (rider.website_id must match order.website_id).
    """
    try:
        order_resp = supabase.table("delivery_orders").select(
            "id, order_number, website_id, status"
        ).eq("id", order_id).execute()

        if not order_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        order = order_resp.data[0]

        rider_id = payload.rider_id
        new_status = order.get("status")

        if rider_id:
            rider_resp = supabase.table("riders").select(
                "id, name, website_id, is_active"
            ).eq("id", rider_id).execute()

            if not rider_resp.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid rider"
                )
            rider = rider_resp.data[0]

            if not rider.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rider is inactive"
                )
            if str(rider.get("website_id")) != str(order.get("website_id")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Rider does not belong to this website"
                )

            # Auto-advance status to "ready" or "picked_up" if still preparing
            if new_status in ("pending", "confirmed", "preparing"):
                new_status = "ready"

            logger.info(f"✅ Assigning rider {rider.get('name')} to order {order.get('order_number')}")

        update_data = {"rider_id": rider_id}
        if new_status != order.get("status"):
            update_data["status"] = new_status

        updated = supabase.table("delivery_orders").update(update_data).eq(
            "id", order_id
        ).execute()

        if not updated.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign rider"
            )

        # Add to status history
        try:
            note = f"Rider assigned: {rider.get('name')}" if rider_id else "Rider unassigned"
            supabase.table("order_status_history").insert({
                "order_id": order_id,
                "status": updated.data[0].get("status", "pending"),
                "notes": note,
                "updated_by": "business",
            }).execute()
        except Exception as history_err:
            logger.warning(f"⚠️ Could not insert order_status_history: {history_err}")

        logger.info(f"✅ Rider assignment updated for order {order.get('order_number')}")
        return convert_db_row_to_dict(updated.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign rider: {str(e)}",
        )


@router.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status_public(
    order_id: str,
    status_update: OrderStatusUpdate,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Update order status (public endpoint for simple dashboards).

    Status flow: pending → confirmed → preparing → ready → picked_up → delivering → delivered → completed
    """
    try:
        # Get current order
        order_response = supabase.table("delivery_orders").select("*").eq(
            "id", order_id
        ).execute()

        if not order_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        current_order = order_response.data[0]
        new_status = status_update.status.value

        # Prepare update data with timestamp
        update_data = {"status": new_status}
        timestamp_field = f"{new_status}_at"
        if timestamp_field in [
            "confirmed_at", "preparing_at", "ready_at", "picked_up_at",
            "delivered_at", "completed_at", "cancelled_at"
        ]:
            update_data[timestamp_field] = datetime.utcnow().isoformat()

        # Update order status
        updated_response = supabase.table("delivery_orders").update(
            update_data
        ).eq("id", order_id).execute()

        if not updated_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update order status"
            )

        # Add to status history
        history_data = {
            "order_id": order_id,
            "status": new_status,
            "notes": status_update.notes,
            "updated_by": "business"
        }
        supabase.table("order_status_history").insert(history_data).execute()

        logger.info(
            f"✅ Order {current_order['order_number']} status updated: "
            f"{current_order['status']} → {new_status}"
        )

        return convert_db_row_to_dict(updated_response.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
        )


# =====================================================
# ENHANCED TRACKING WITH RIDER STATUS
# =====================================================

@router.get("/orders/{order_number}/status")
async def get_order_status_simple(
    order_number: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Get simplified order status for quick checks.

    Returns essential tracking info including rider assignment status.
    """
    try:
        order_response = supabase.table("delivery_orders").select(
            "id, order_number, status, rider_id, customer_name, total_amount, "
            "created_at, estimated_delivery_time"
        ).eq("order_number", order_number).execute()

        if not order_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        order = order_response.data[0]

        # Get rider info if assigned
        rider_info = None
        if order.get("rider_id"):
            rider_response = supabase.table("riders").select(
                "id, name, phone, vehicle_type, vehicle_plate"
            ).eq("id", order["rider_id"]).execute()

            if rider_response.data:
                rider_info = rider_response.data[0]

        return {
            "order_number": order["order_number"],
            "status": order["status"],
            "has_rider": order.get("rider_id") is not None,
            "rider": rider_info,
            "total_amount": float(order["total_amount"]) if order.get("total_amount") else None,
            "estimated_delivery_time": order.get("estimated_delivery_time"),
            "created_at": order["created_at"],
            "status_message": get_status_message(order["status"], rider_info is not None)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order status: {str(e)}"
        )


def get_status_message(status: str, has_rider: bool) -> str:
    """Get human-readable status message in Malay"""
    messages = {
        "pending": "Pesanan anda sedang menunggu pengesahan",
        "confirmed": "Pesanan disahkan! Sedang diproses",
        "preparing": "Makanan sedang disediakan",
        "ready": "Pesanan siap! Menunggu rider" if not has_rider else "Pesanan siap untuk diambil rider",
        "picked_up": "Rider sudah ambil pesanan anda",
        "delivering": "Pesanan dalam perjalanan ke lokasi anda",
        "delivered": "Pesanan telah dihantar! Selamat menikmati",
        "completed": "Pesanan selesai. Terima kasih!",
        "cancelled": "Pesanan dibatalkan",
        "rejected": "Pesanan tidak dapat diproses"
    }
    return messages.get(status, "Status tidak diketahui")


# =====================================================
# HEALTH CHECK
# =====================================================

@router.get("/health")
async def health_check():
    """Check if delivery system is operational"""
    return {
        "status": "healthy",
        "service": "BinaApp Delivery System",
        "version": "1.1.0",  # Updated version
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "rider_system": True,
            "order_tracking": True,
            "phase_1_complete": True,
            "phase_2_gps_tracking": False  # Not yet enabled
        }
    }
