"""
BinaApp Delivery System API Endpoints
Handles real-time food delivery and order tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from typing import List, Optional
from loguru import logger
from decimal import Decimal
from datetime import datetime

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
    RiderInfoResponse,
    RiderLocationResponse,
)

router = APIRouter(prefix="/delivery", tags=["Delivery System"])


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

        # 2. Get delivery zone for fee
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

        # Check minimum order
        if subtotal < Decimal(str(zone['minimum_order'])):
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
            "estimated_delivery_time": zone['estimated_time_min']
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

        supabase.table("order_items").insert(order_items_data).execute()

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
        rider = None
        rider_location = None
        eta_minutes = None

        if order.get('rider_id'):
            rider_response = supabase.table("riders").select(
                "id, name, phone, photo_url, vehicle_type, vehicle_plate, rating, current_latitude, current_longitude"
            ).eq("id", order['rider_id']).execute()

            if rider_response.data:
                rider = convert_db_row_to_dict(rider_response.data[0])

                # Get latest rider location
                location_response = supabase.table("rider_locations").select("*").eq(
                    "order_id", order_id
                ).order("recorded_at", desc=True).limit(1).execute()

                if location_response.data:
                    rider_location = convert_db_row_to_dict(location_response.data[0])

                # TODO: Calculate ETA using Google Maps API
                eta_minutes = order.get('estimated_delivery_time', 30)

        return {
            "order": order,
            "items": items,
            "status_history": status_history,
            "rider": rider,
            "rider_location": rider_location,
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
# HEALTH CHECK
# =====================================================

@router.get("/health")
async def health_check():
    """Check if delivery system is operational"""
    return {
        "status": "healthy",
        "service": "BinaApp Delivery System",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
