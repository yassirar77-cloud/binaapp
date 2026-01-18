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
import bcrypt

from app.core.supabase import get_supabase_client
from app.core.security import get_current_user
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
    RiderLocationUpdate,
    RiderResponse,
    RiderCreateBusiness,
    RiderUpdate,
    AssignRiderRequest,
    DeliverySettingsResponse,
    DeliverySettingsUpdate,
)
from app.utils.whatsapp import (
    notify_owner_new_order,
    notify_rider_assigned,
    notify_customer_status_update,
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

    # Log authentication for debugging
    logger.info(f"[RLS Client] Created client with JWT token (length: {len(credentials.credentials)})")

    return client


def get_rider_admin_client(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Client:
    """
    Prefer service-role client for rider admin endpoints.
    Fallback to RLS client when service role is unavailable.
    """
    service_key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    )

    if service_key:
        logger.info("[Rider Admin] Using service role client for rider admin endpoints")
        return get_supabase_client()

    logger.warning("[Rider Admin] Service role key missing; falling back to RLS client")
    return get_supabase_rls_client(credentials)


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


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against bcrypt hash.

    SECURITY: Plain text password support has been REMOVED.
    All passwords must be properly hashed with bcrypt.
    """
    try:
        # Check if stored password is a bcrypt hash (starts with $2a$, $2b$, or $2y$)
        if hashed_password and hashed_password.startswith(('$2a$', '$2b$', '$2y$')):
            # It's a bcrypt hash - verify normally
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        else:
            # SECURITY FIX: Plain text passwords are NO LONGER SUPPORTED
            # If you see this error, the rider password needs to be rehashed
            logger.critical(
                f"SECURITY: Plain text password detected in database! "
                f"This rider account is BLOCKED until password is rehashed. "
                f"Run: UPDATE riders SET password_hash = bcrypt_hash(password_hash) WHERE ..."
            )
            # Return False - do not allow login with plain text passwords
            return False
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# =====================================================
# CUSTOMER & CONVERSATION HELPERS
# =====================================================

async def get_or_create_customer(supabase: Client, website_id: str, phone: str, name: str, address: str = "") -> dict:
    """Get existing customer or create new one for the website"""
    try:
        # Check if customer exists
        result = supabase.table("website_customers").select("*").eq(
            "website_id", website_id
        ).eq("phone", phone).execute()

        if result.data:
            # Update existing customer info
            customer = result.data[0]
            supabase.table("website_customers").update({
                "name": name,
                "address": address,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", customer["id"]).execute()
            logger.info(f"[Customer] Found existing customer: {customer['id']}")
            return customer
        else:
            # Create new customer - UUID MUST be generated server-side only
            import uuid
            new_customer_id = str(uuid.uuid4())
            logger.info(f"[Customer] SERVER-SIDE UUID generated for new customer: {new_customer_id}")
            logger.info(f"[Customer] Bound to website_id: {website_id}")

            customer_data = {
                "id": new_customer_id,
                "website_id": website_id,
                "phone": phone,
                "name": name,
                "address": address
            }
            insert_result = supabase.table("website_customers").insert(customer_data).execute()
            if insert_result.data:
                logger.info(f"[Customer] Created new customer: {customer_data['id']} for website {website_id}")
                return insert_result.data[0]
            return customer_data
    except Exception as e:
        logger.error(f"[Customer] Error: {e}")
        return None


async def create_order_conversation(supabase: Client, order_id: str, order_number: str, website_id: str,
                                     customer_id: str, customer_name: str, customer_phone: str) -> dict:
    """Create chat conversation for an order"""
    try:
        import uuid

        # CRITICAL: Generate conversation UUID server-side only
        new_conversation_id = str(uuid.uuid4())
        logger.info(f"[Chat] SERVER-SIDE UUID generated for conversation: {new_conversation_id}")
        logger.info(f"[Chat] Conversation bound to website_id: {website_id}, order: {order_number}")

        # Fetch website name for display in owner dashboard (optional)
        website_name = ""
        try:
            website_result = supabase.table("websites").select("business_name, name").eq("id", website_id).single().execute()
            if website_result.data:
                website_name = website_result.data.get("business_name") or website_result.data.get("name") or ""
        except Exception as website_error:
            logger.warning(f"[Chat] Could not load website name for {website_id}: {website_error}")

        # Build conversation data - ONLY use columns that exist in chat_conversations table
        # Actual schema: id, order_id, website_id, customer_name, customer_phone, status,
        #               unread_owner, unread_customer, unread_rider, created_at, updated_at
        # NOTE: customer_id column was REMOVED from the database
        conversation_data = {
            "id": new_conversation_id,
            "order_id": order_id,
            "website_id": website_id,
            "website_name": website_name,
            "customer_name": customer_name or "Customer",
            "customer_phone": customer_phone or "",
            "status": "active"
        }

        result = supabase.table("chat_conversations").insert(conversation_data).execute()

        # If insert failed due to missing column (e.g. website_name), retry without it
        if not result.data and getattr(result, "error", None):
            logger.warning(f"[Chat] Conversation insert failed: {result.error}")
            conversation_data.pop("website_name", None)
            result = supabase.table("chat_conversations").insert(conversation_data).execute()

        if result.data:
            conversation = result.data[0]
            logger.info(f"[Chat] Created conversation {conversation['id']} for order {order_number} (website: {website_id})")
            return conversation

        if getattr(result, "error", None):
            logger.error(f"[Chat] Conversation insert error: {result.error}")
        return conversation_data
    except Exception as e:
        logger.error(f"[Chat] Error creating conversation: {e}")
        return None


async def send_system_message(supabase: Client, conversation_id: str, content: str) -> None:
    """Send a system message to a conversation"""
    try:
        import uuid
        # Use canonical message_text for chat_messages
        supabase.table("chat_messages").insert({
            "id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "sender_type": "system",
            "message_text": content,
            "content": content,
            "is_read": False
        }).execute()
    except Exception as e:
        logger.error(f"[Chat] Error sending system message: {e}")


async def create_notification(supabase: Client, user_type: str, user_id: str, website_id: str = None,
                              order_id: str = None, conversation_id: str = None,
                              notif_type: str = "new_order", title: str = "", body: str = "") -> None:
    """Create a notification for a user"""
    try:
        import uuid
        supabase.table("notifications").insert({
            "id": str(uuid.uuid4()),
            "user_type": user_type,
            "user_id": user_id,
            "website_id": website_id,
            "order_id": order_id,
            "conversation_id": conversation_id,
            "type": notif_type,
            "title": title,
            "body": body
        }).execute()
        logger.info(f"[Notification] Created {notif_type} for {user_type}:{user_id}")
    except Exception as e:
        logger.error(f"[Notification] Error: {e}")


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
    import re

    try:
        # =====================================================
        # CRITICAL: VALIDATE WEBSITE ID (Single Source of Truth)
        # =====================================================
        # GUARD 1: Reject null/empty website IDs
        if not order.website_id or not order.website_id.strip():
            logger.warning(f"[Order] REJECTED: Order creation with empty website_id")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "MISSING_WEBSITE_ID",
                    "message": "Website ID is required for order creation"
                }
            )

        # GUARD 2: Validate UUID format (fail fast on malformed IDs)
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(order.website_id.strip()):
            logger.warning(f"[Order] REJECTED: Invalid UUID format for website_id: {order.website_id[:50]}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_UUID_FORMAT",
                    "message": "Website ID must be a valid UUID"
                }
            )

        # GUARD 3: Verify website exists in database (AUTHORITATIVE CHECK)
        website_check = supabase.table("websites").select("id, business_name, user_id").eq(
            "id", order.website_id.strip()
        ).execute()

        if not website_check.data:
            logger.warning(f"[Order] REJECTED: Website not found in database: {order.website_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "WEBSITE_NOT_FOUND",
                    "message": "No website found with this ID. Cannot create order for non-existent website."
                }
            )

        # Use the CANONICAL ID from database (not user-provided)
        canonical_website_id = website_check.data[0]["id"]
        website_owner_id = website_check.data[0].get("user_id")
        logger.info(f"[Order] Website validated: {canonical_website_id}")

        # Replace order website_id with canonical value
        # This ensures referential integrity even if client sent slightly different ID
        order.website_id = canonical_website_id

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

        # 6. Register/Get customer
        customer = await get_or_create_customer(
            supabase=supabase,
            website_id=order.website_id,
            phone=order.customer_phone,
            name=order.customer_name,
            address=order.delivery_address
        )
        customer_id = customer["id"] if customer else None

        # 7. Create chat conversation for this order
        conversation = None
        conversation_id = None
        if customer_id:
            conversation = await create_order_conversation(
                supabase=supabase,
                order_id=order_id,
                order_number=created_order['order_number'],
                website_id=order.website_id,
                customer_id=customer_id,
                customer_name=order.customer_name,
                customer_phone=order.customer_phone
            )
            conversation_id = conversation["id"] if conversation else None

            # Note: delivery_orders table does NOT have customer_id or conversation_id columns
            # These relationships are maintained through:
            # - website_customers table (customer by phone)
            # - chat_conversations table (conversation by order_id)
            # Skipping update as columns don't exist

            # Send system message to conversation
            await send_system_message(
                supabase=supabase,
                conversation_id=conversation_id,
                content=f"Pesanan baru #{created_order['order_number']}\n"
                        f"{order.customer_name}\n"
                        f"{order.delivery_address}\n"
                        f"RM{total_amount:.2f}"
            )

        # 8. Create notification for owner
        website_result = supabase.table("websites").select("user_id").eq("id", order.website_id).single().execute()
        if website_result.data:
            owner_id = website_result.data["user_id"]
            await create_notification(
                supabase=supabase,
                user_type="owner",
                user_id=owner_id,
                website_id=order.website_id,
                order_id=order_id,
                conversation_id=conversation_id,
                notif_type="new_order",
                title="Pesanan Baru!",
                body=f"{order.customer_name} - RM{total_amount:.2f}"
            )

            # NEW: Send WhatsApp notification to owner
            try:
                # Get owner's phone number
                owner_profile = supabase.table("profiles").select("phone").eq("id", owner_id).single().execute()
                if owner_profile.data and owner_profile.data.get("phone"):
                    notify_owner_new_order(
                        owner_phone=owner_profile.data["phone"],
                        order_number=created_order['order_number'],
                        customer_name=order.customer_name,
                        customer_phone=order.customer_phone,
                        total_amount=float(total_amount),
                        items=order_items_data,
                        delivery_address=order.delivery_address
                    )
                    logger.info(f"📱 WhatsApp notification sent to owner for order {created_order['order_number']}")
            except Exception as wa_error:
                logger.warning(f"⚠️ Failed to send WhatsApp to owner: {wa_error}")
                # Don't fail the order creation if WhatsApp fails

        logger.info(f"✅ Order created: {created_order['order_number']} - Total: RM{total_amount}")

        # 9. Return created order with conversation_id and customer_id
        result = convert_db_row_to_dict(created_order)
        result["conversation_id"] = conversation_id
        result["customer_id"] = customer_id
        return result

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

        # 4. Get rider info if assigned (Phase 2: now includes GPS)
        rider = None
        rider_location = None
        eta_minutes = None

        if order.get('rider_id'):
            rider_response = supabase.table("riders").select(
                "id, name, phone, photo_url, vehicle_type, vehicle_plate, rating, "
                "current_latitude, current_longitude, last_location_update"
            ).eq("id", order['rider_id']).execute()

            if rider_response.data:
                rider = convert_db_row_to_dict(rider_response.data[0])

                # Phase 2: Return GPS coordinates for real-time tracking
                # (GPS fields will be null if rider hasn't sent location yet)

                # Build rider_location object if GPS available
                if rider.get('current_latitude') and rider.get('current_longitude'):
                    rider_location = {
                        "latitude": rider['current_latitude'],
                        "longitude": rider['current_longitude'],
                        "recorded_at": rider.get('last_location_update')
                    }

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

        # NEW: Send WhatsApp notification to customer on status changes
        if new_status in ['confirmed', 'ready', 'picked_up', 'delivering', 'delivered']:
            try:
                # Get rider info if available
                rider_name = None
                rider_phone = None
                if current_order.get('rider_id'):
                    rider_resp = supabase.table("riders").select("name, phone").eq("id", current_order['rider_id']).single().execute()
                    if rider_resp.data:
                        rider_name = rider_resp.data.get('name')
                        rider_phone = rider_resp.data.get('phone')

                notify_customer_status_update(
                    customer_phone=current_order['customer_phone'],
                    order_number=current_order['order_number'],
                    status=new_status,
                    rider_name=rider_name,
                    rider_phone=rider_phone,
                    eta_minutes=15  # TODO: Calculate based on GPS distance
                )
                logger.info(f"📱 WhatsApp status update sent to customer for order {current_order['order_number']}")
            except Exception as wa_error:
                logger.warning(f"⚠️ Failed to send WhatsApp to customer: {wa_error}")
                # Don't fail the status update if WhatsApp fails

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
    Phase 2+: Sends WhatsApp notification to rider when assigned.
    """
    try:
        # Get full order details for WhatsApp notification
        order_resp = supabase.table("delivery_orders").select(
            "id, order_number, website_id, customer_name, customer_phone, "
            "delivery_address, total_amount"
        ).eq("id", order_id).execute()

        if not order_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        order = order_resp.data[0]

        rider_id = payload.rider_id
        rider_info = None

        if rider_id:
            # Get full rider details for notification
            rider_resp = supabase.table("riders").select(
                "id, website_id, is_active, name, phone"
            ).eq("id", rider_id).execute()

            if not rider_resp.data:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid rider")
            rider_info = rider_resp.data[0]

            if not rider_info.get("is_active", True):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rider is inactive")
            if str(rider_info.get("website_id")) != str(order.get("website_id")):
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

        # NEW: Send WhatsApp notification to rider
        if rider_id and rider_info:
            try:
                notify_rider_assigned(
                    rider_phone=rider_info['phone'],
                    rider_name=rider_info['name'],
                    order_number=order['order_number'],
                    customer_name=order['customer_name'],
                    customer_phone=order['customer_phone'],
                    delivery_address=order['delivery_address'],
                    total_amount=order['total_amount']
                )
                logger.info(f"📱 WhatsApp notification sent to rider {rider_info['name']} for order {order['order_number']}")
            except Exception as wa_error:
                logger.warning(f"⚠️ Failed to send WhatsApp to rider: {wa_error}")
                # Don't fail the assignment if WhatsApp fails

        # Return response with WhatsApp notification info
        response_data = convert_db_row_to_dict(updated.data[0])

        # Add WhatsApp notification details if rider was assigned
        if rider_id and rider_info:
            # Format phone number for WhatsApp (remove non-digits)
            rider_phone = rider_info.get('phone', '').replace('+', '').replace(' ', '').replace('-', '')

            # Create WhatsApp message
            message = (
                f"🛵 *Pesanan Baru!*\n\n"
                f"Order: #{order.get('order_number')}\n"
                f"Pelanggan: {order.get('customer_name')}\n"
                f"Telefon: {order.get('customer_phone')}\n"
                f"Alamat: {order.get('delivery_address')}\n"
                f"Jumlah: RM {order.get('total_amount', 0):.2f}\n\n"
                f"Buka rider app: https://binaapp.my/rider\n"
                f"Login dengan Rider ID anda untuk lihat pesanan."
            )

            # URL encode the message
            import urllib.parse
            encoded_message = urllib.parse.quote(message)

            # Add WhatsApp link to response
            response_data['whatsapp_notification'] = {
                'rider_name': rider_info.get('name'),
                'rider_phone': rider_phone,
                'whatsapp_link': f"https://wa.me/{rider_phone}?text={encoded_message}",
                'message_preview': message
            }

        return response_data

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
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_rider_admin_client),
):
    """
    List riders for a website (Admin endpoint).

    Uses service role when available and falls back to RLS with user JWT.
    This keeps riders visible even when the service role key is missing.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")

        website_check = supabase.table("websites").select("id").eq("id", website_id).eq("user_id", user_id).execute()
        if not website_check.data:
            logger.warning(f"[Rider LIST] User {user_id} attempted to access riders for unauthorized website: {website_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this website"
            )

        logger.info(f"[Rider LIST] user_id={user_id} website_id={website_id}")
        logger.info(f"[Rider LIST] Querying riders for website_id: {website_id}")

        resp = supabase.table("riders").select("*").eq("website_id", website_id).order("created_at", desc=True).execute()

        logger.info(f"[Rider LIST] Found {len(resp.data or [])} riders")
        if resp.data:
            logger.info(f"[Rider LIST] Rider IDs: {[r.get('id', 'unknown') for r in resp.data]}")
            logger.info(f"[Rider LIST] Rider names: {[r.get('name', 'unknown') for r in resp.data]}")

        return [convert_db_row_to_dict(r) for r in (resp.data or [])]
    except Exception as e:
        logger.error(f"[Rider LIST] Error listing riders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list riders: {str(e)}",
        )


@router.post("/admin/websites/{website_id}/riders", response_model=RiderResponse)
async def create_rider(
    website_id: str,
    rider: RiderCreateBusiness,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_rider_admin_client),
):
    """
    Create a rider for a website (Admin endpoint).

    Uses service role when available and falls back to RLS with user JWT.
    This keeps rider creation working even when the service role key is missing.
    """
    try:
        user_id = current_user.get("sub") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID not found in token")

        website_check = supabase.table("websites").select("id").eq("id", website_id).eq("user_id", user_id).execute()
        if not website_check.data:
            logger.warning(f"[Rider CREATE] User {user_id} attempted to create rider for unauthorized website: {website_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this website"
            )

        logger.info(f"[Rider CREATE] Creating rider for website_id: {website_id}")
        logger.info(f"[Rider CREATE] user_id={user_id} website_id={website_id}")
        logger.info(f"[Rider CREATE] Rider data: {rider.dict(exclude={'password'})}")

        data = rider.dict()
        data["website_id"] = website_id

        # Hash password before storing (SECURITY FIX)
        password = data.pop("password", None)
        if password:
            data["password_hash"] = hash_password(password)
            logger.info(f"[Rider CREATE] Creating rider with hashed password")

        resp = supabase.table("riders").insert(data).execute()

        if not resp.data:
            logger.error(f"[Rider CREATE] Failed - no data returned from insert")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create rider")

        created_rider = resp.data[0]
        logger.info(f"[Rider CREATE] ✅ Successfully created rider with ID: {created_rider.get('id', 'unknown')}")
        logger.info(f"[Rider CREATE] Created rider name: {created_rider.get('name', 'unknown')}")
        logger.info(f"[Rider CREATE] Created rider website_id: {created_rider.get('website_id', 'unknown')}")

        # Immediately verify the rider exists by querying it back
        verify_resp = supabase.table("riders").select("*").eq("id", created_rider.get('id')).execute()
        if verify_resp.data:
            logger.info(f"[Rider CREATE] ✅ Verification successful - rider exists in database")
        else:
            logger.warning(f"[Rider CREATE] ⚠️ Verification failed - rider not found immediately after creation")

        return convert_db_row_to_dict(created_rider)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Rider CREATE] ❌ Error creating rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rider: {str(e)}",
        )


@router.put("/riders/{rider_id}", response_model=RiderResponse)
async def update_rider(
    rider_id: str,
    update_data: RiderUpdate,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Update a rider (Admin endpoint - uses service role to bypass RLS).

    CRITICAL FIX: Changed from get_supabase_rls_client to get_supabase_client
    to match create_rider and list_riders endpoints.

    Supports updating all rider fields including password reset.
    Password will be hashed before storage.
    """
    try:
        # Convert to dict and filter out None values
        data = {k: v for k, v in update_data.dict().items() if v is not None}

        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        # Hash password if provided
        password = data.pop("password", None)
        if password:
            data["password_hash"] = hash_password(password)
            logger.info(f"Updating rider {rider_id} with new hashed password")

        resp = supabase.table("riders").update(data).eq("id", rider_id).execute()

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


@router.put("/riders/{rider_id}/status")
async def update_rider_status(
    rider_id: str,
    status_data: dict,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Update rider status (activate/deactivate).

    Body:
    - status: "active" or "inactive"

    This is a soft delete - rider remains in database but is marked inactive.
    """
    try:
        new_status = status_data.get("status", "inactive")

        # Validate status value
        if new_status not in ["active", "inactive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status mesti 'active' atau 'inactive'"
            )

        # Update rider status
        resp = supabase.table("riders").update({
            "is_active": new_status == "active"
        }).eq("id", rider_id).execute()

        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider tidak dijumpai"
            )

        action = "diaktifkan" if new_status == "active" else "dinyahaktifkan"
        logger.info(f"✅ Rider {rider_id} {action}")

        return {
            "success": True,
            "message": f"Rider berjaya {action}",
            "rider": convert_db_row_to_dict(resp.data[0])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rider status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengemas kini status rider: {str(e)}"
        )


@router.delete("/riders/{rider_id}")
async def delete_rider(
    rider_id: str,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Permanently delete a rider (hard delete).

    Warning: This cannot be undone. Use PUT /riders/{rider_id}/status
    for soft delete (deactivation) instead.
    """
    try:
        # First check if rider exists
        check_resp = supabase.table("riders").select("id, name").eq("id", rider_id).execute()

        if not check_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider tidak dijumpai"
            )

        rider_name = check_resp.data[0].get("name", "Unknown")

        # Delete the rider
        resp = supabase.table("riders").delete().eq("id", rider_id).execute()

        logger.info(f"✅ Rider {rider_name} ({rider_id}) deleted permanently")

        return {
            "success": True,
            "message": f"Rider {rider_name} berjaya dipadam"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memadam rider: {str(e)}"
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
# WIDGET ID VALIDATION ENDPOINT
# =====================================================

@router.get("/validate-widget/{website_id}")
async def validate_widget_id(
    website_id: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Validate website ID for widget initialization.

    This endpoint is the SINGLE SOURCE OF TRUTH for widget ID binding.
    It verifies that the provided website_id exists in the database
    and returns the canonical ID with validation status.

    **CRITICAL**: Widgets MUST call this endpoint before initializing
    to prevent client-side UUID drift and ensure referential integrity.

    Returns:
    - valid: boolean - whether the website_id exists in database
    - website_id: string - the canonical database website.id (NOT user-provided)
    - business_name: string - the website's business name
    - status: string - website publication status
    - error: string (only if invalid) - reason for rejection

    **Public endpoint** - Used by widget bootstrap
    """
    import re

    # GUARD 1: Reject null/empty IDs immediately
    if not website_id or website_id.strip() == '':
        logger.warning(f"[Widget Validation] REJECTED: Empty website_id provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "valid": False,
                "error": "MISSING_WEBSITE_ID",
                "message": "Website ID is required for widget initialization"
            }
        )

    # GUARD 2: Validate UUID format (prevents SQL injection and malformed IDs)
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    if not uuid_pattern.match(website_id.strip()):
        logger.warning(f"[Widget Validation] REJECTED: Invalid UUID format: {website_id[:50]}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "valid": False,
                "error": "INVALID_UUID_FORMAT",
                "message": "Website ID must be a valid UUID"
            }
        )

    try:
        # GUARD 3: Verify existence in database - this is the AUTHORITATIVE check
        website_response = supabase.table("websites").select(
            "id, business_name, name, status, subdomain"
        ).eq("id", website_id.strip()).execute()

        if not website_response.data:
            logger.warning(f"[Widget Validation] REJECTED: Website not found in database: {website_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "valid": False,
                    "error": "WEBSITE_NOT_FOUND",
                    "message": "No website found with this ID in database",
                    "website_id": website_id
                }
            )

        website = website_response.data[0]

        # SUCCESS: Return the CANONICAL database ID (not the user-provided one)
        # This ensures the widget always uses the database's source of truth
        canonical_id = website["id"]

        logger.info(f"[Widget Validation] APPROVED: {canonical_id} ({website.get('subdomain', 'unknown')})")

        return {
            "valid": True,
            "website_id": canonical_id,  # ALWAYS return canonical DB value
            "business_name": website.get("business_name") or website.get("name") or "Kedai",
            "subdomain": website.get("subdomain"),
            "status": website.get("status", "unknown"),
            "message": "Widget ID validated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Widget Validation] Database error validating {website_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "valid": False,
                "error": "DATABASE_ERROR",
                "message": "Failed to validate website ID"
            }
        )


@router.post("/purge-widget-cache/{website_id}")
async def purge_widget_cache(
    website_id: str,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Purge cached widget configuration for a website.

    This endpoint should be called when:
    - Website is regenerated/republished
    - Website settings are changed
    - Widget ID drift is detected

    Returns instructions for client-side cache purging.

    **Public endpoint** - Can be called by admin dashboard
    """
    import re

    # Validate UUID format
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    if not uuid_pattern.match(website_id.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid website ID format"
        )

    try:
        # Verify website exists
        website_response = supabase.table("websites").select("id, subdomain").eq(
            "id", website_id
        ).execute()

        if not website_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        website = website_response.data[0]

        logger.info(f"[Widget Cache] Purge requested for {website_id} ({website.get('subdomain')})")

        # Return cache purge instructions
        # Client-side caches that need clearing:
        return {
            "success": True,
            "website_id": website["id"],
            "subdomain": website.get("subdomain"),
            "cache_keys_to_clear": [
                f"binaapp_conv_{website_id}",
                f"binaapp_customer_id_{website_id}",
                "binaapp_customer_name",
                "binaapp_customer_phone",
                "binaapp_customer_id"
            ],
            "message": "Widget cache purge initiated. Clear localStorage keys on client."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Widget Cache] Error purging cache for {website_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge cache: {str(e)}"
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
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """
    Get all orders for a website (requires authentication and ownership).

    SECURITY: Only website owners can access their orders.
    """
    try:
        # SECURITY: Extract user_id from authenticated token
        user_id = current_user.get("sub") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # SECURITY: Verify user owns this website
        website_check = supabase.table("websites").select("id").eq("id", website_id).eq("user_id", user_id).execute()
        if not website_check.data:
            logger.warning(f"User {user_id} attempted to access orders for unauthorized website: {website_id}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: You don't own this website"
            )

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
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """
    Get all riders for a website (requires authentication and ownership).

    SECURITY: Only website owners can access their riders.
    Phase 1: Returns basic rider info (no GPS).
    """
    try:
        # SECURITY: Extract user_id from authenticated token
        user_id = current_user.get("sub") or current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")

        # SECURITY: Verify user owns this website
        website_check = supabase.table("websites").select("id").eq("id", website_id).eq("user_id", user_id).execute()
        if not website_check.data:
            logger.warning(f"User {user_id} attempted to access riders for unauthorized website: {website_id}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: You don't own this website"
            )

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

        # Hash password before storing (SECURITY FIX)
        password = data.pop("password", None)
        if password:
            data["password_hash"] = hash_password(password)
            logger.info(f"Creating rider with hashed password")

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


@router.put("/website/{website_id}/riders/{rider_id}/status")
async def update_website_rider_status(
    website_id: str,
    rider_id: str,
    status_data: dict,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Update rider status for a website (activate/deactivate).

    Body:
    - status: "active" or "inactive"
    """
    try:
        new_status = status_data.get("status", "inactive")

        if new_status not in ["active", "inactive"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status mesti 'active' atau 'inactive'"
            )

        resp = supabase.table("riders").update({
            "status": new_status,
            "is_active": new_status == "active"
        }).eq("id", rider_id).eq("website_id", website_id).execute()

        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider tidak dijumpai"
            )

        action = "diaktifkan" if new_status == "active" else "dinyahaktifkan"
        logger.info(f"✅ Rider {rider_id} {action}")

        return {
            "success": True,
            "message": f"Rider berjaya {action}",
            "rider": convert_db_row_to_dict(resp.data[0])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rider status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengemas kini status rider: {str(e)}"
        )


@router.delete("/website/{website_id}/riders/{rider_id}")
async def delete_website_rider(
    website_id: str,
    rider_id: str,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Permanently delete a rider for a website.
    """
    try:
        check_resp = supabase.table("riders").select("id, name").eq(
            "id", rider_id
        ).eq("website_id", website_id).execute()

        if not check_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider tidak dijumpai"
            )

        rider_name = check_resp.data[0].get("name", "Unknown")

        supabase.table("riders").delete().eq("id", rider_id).eq("website_id", website_id).execute()

        logger.info(f"✅ Rider {rider_name} ({rider_id}) deleted")

        return {
            "success": True,
            "message": f"Rider {rider_name} berjaya dipadam"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memadam rider: {str(e)}"
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

        # Get conversation_id by looking up chat_conversations via order_id
        # Note: delivery_orders does NOT have conversation_id column
        conv_lookup = supabase.table("chat_conversations").select("id").eq("order_id", order_id).execute()
        conversation_id = conv_lookup.data[0]["id"] if conv_lookup.data else None

        if conversation_id and rider_id:
            # Add rider to conversation
            try:
                supabase.table("chat_conversations").update({
                    "rider_id": rider_id
                }).eq("id", conversation_id).execute()
            except Exception as conv_err:
                logger.warning(f"⚠️ Could not update conversation with rider: {conv_err}")

            # Send system message
            await send_system_message(
                supabase=supabase,
                conversation_id=conversation_id,
                content=f"Rider ditugaskan: {rider.get('name')}\n{rider.get('phone', '')}"
            )

            # Notify rider
            await create_notification(
                supabase=supabase,
                user_type="rider",
                user_id=rider_id,
                website_id=order.get("website_id"),
                order_id=order_id,
                conversation_id=conversation_id,
                notif_type="order_assigned",
                title="Pesanan Baru Ditugaskan!",
                body=f"Hantar ke: #{order.get('order_number')}"
            )

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

        # Send status update to chat
        # Note: delivery_orders does NOT have conversation_id column, look up via order_id
        conv_result = supabase.table("chat_conversations").select("id").eq("order_id", order_id).execute()
        conversation_id = conv_result.data[0]["id"] if conv_result.data else None
        if conversation_id:
            status_messages = {
                "confirmed": "Pesanan disahkan! Sedang menyediakan pesanan anda.",
                "preparing": "Pesanan sedang disediakan",
                "ready": "Pesanan sedia untuk diambil",
                "picked_up": "Rider telah mengambil pesanan",
                "delivering": "Pesanan dalam perjalanan",
                "delivered": "Pesanan telah dihantar!",
                "completed": "Pesanan selesai. Terima kasih!",
                "cancelled": "Pesanan dibatalkan"
            }
            if new_status in status_messages:
                await send_system_message(
                    supabase=supabase,
                    conversation_id=conversation_id,
                    content=status_messages[new_status]
                )

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
# RIDER GPS LOCATION UPDATES (PHASE 2)
# =====================================================

@router.put("/riders/{rider_id}/location")
async def update_rider_location(
    rider_id: str,
    location: RiderLocationUpdate,
    order_id: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Update rider's GPS location (Phase 2).

    Called by rider mobile app to send GPS updates every 15 seconds.

    Updates:
    - riders.current_latitude
    - riders.current_longitude
    - riders.last_location_update

    Also logs to rider_locations table for tracking history.

    **Phase 2 Note:** Authentication will be added in Feature #3 (rider app).
    For now, this is a public endpoint to enable testing.
    """
    try:
        # Validate rider exists
        rider_response = supabase.table("riders").select("id, name, is_active").eq(
            "id", rider_id
        ).execute()

        if not rider_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider not found"
            )

        rider = rider_response.data[0]

        if not rider.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Rider account is inactive"
            )

        # Update rider's current location
        update_data = {
            "current_latitude": float(location.latitude),
            "current_longitude": float(location.longitude),
            "last_location_update": datetime.utcnow().isoformat()
        }

        updated_rider = supabase.table("riders").update(update_data).eq(
            "id", rider_id
        ).execute()

        if not updated_rider.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update rider location"
            )

        # Log to rider_locations history table
        location_history = {
            "rider_id": rider_id,
            "order_id": order_id,  # Optional: associate with specific order
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "recorded_at": datetime.utcnow().isoformat()
        }

        try:
            supabase.table("rider_locations").insert(location_history).execute()
        except Exception as history_error:
            # Log error but don't fail the request
            logger.warning(f"Failed to log rider location history: {history_error}")

        logger.info(
            f"✅ Rider {rider.get('name')} location updated: "
            f"{location.latitude}, {location.longitude}"
        )

        return {
            "success": True,
            "message": "Location updated successfully",
            "rider_id": rider_id,
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "updated_at": update_data["last_location_update"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rider location: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rider location: {str(e)}"
        )


@router.get("/riders/{rider_id}/location")
async def get_rider_location(
    rider_id: str,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Get rider's current GPS location (Phase 2).

    Returns current location from riders table.
    """
    try:
        rider_response = supabase.table("riders").select(
            "id, name, current_latitude, current_longitude, last_location_update, is_online"
        ).eq("id", rider_id).execute()

        if not rider_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider not found"
            )

        rider = rider_response.data[0]

        return {
            "rider_id": rider["id"],
            "rider_name": rider["name"],
            "latitude": rider.get("current_latitude"),
            "longitude": rider.get("current_longitude"),
            "last_update": rider.get("last_location_update"),
            "is_online": rider.get("is_online", False)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rider location: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rider location: {str(e)}"
        )


@router.get("/riders/{rider_id}/location/history")
async def get_rider_location_history(
    rider_id: str,
    limit: int = 50,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Get rider's GPS location history (Phase 2).

    Returns recent location updates from rider_locations table.
    Useful for debugging and analytics.
    """
    try:
        history_response = supabase.table("rider_locations").select(
            "latitude, longitude, recorded_at, order_id"
        ).eq("rider_id", rider_id).order(
            "recorded_at", desc=True
        ).limit(limit).execute()

        return {
            "rider_id": rider_id,
            "count": len(history_response.data or []),
            "history": [convert_db_row_to_dict(h) for h in (history_response.data or [])]
        }

    except Exception as e:
        logger.error(f"Error getting rider location history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rider location history: {str(e)}"
        )


@router.get("/riders/{rider_id}/orders")
async def get_rider_orders(
    rider_id: str,
    status_filter: Optional[str] = None,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Get orders assigned to a specific rider (Phase 2).

    Returns list of orders where rider_id matches.
    Used by rider mobile app to show assigned deliveries.

    Query Parameters:
    - status_filter: Filter by status (e.g., "ready", "picked_up", "delivering")
    """
    try:
        # Validate rider exists
        rider_response = supabase.table("riders").select("id, name").eq(
            "id", rider_id
        ).execute()

        if not rider_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rider not found"
            )

        # Build query
        query = supabase.table("delivery_orders").select(
            "id, order_number, customer_name, customer_phone, customer_email, "
            "delivery_address, delivery_latitude, delivery_longitude, "
            "subtotal, delivery_fee, total_amount, payment_method, payment_status, "
            "status, created_at, confirmed_at, ready_at, picked_up_at, delivered_at, "
            "estimated_prep_time, estimated_delivery_time"
        ).eq("rider_id", rider_id)

        # Apply status filter if provided
        if status_filter:
            query = query.eq("status", status_filter)

        # Order by created_at descending (newest first)
        query = query.order("created_at", desc=True).limit(50)

        orders_response = query.execute()

        orders = [convert_db_row_to_dict(o) for o in (orders_response.data or [])]

        return {
            "rider_id": rider_id,
            "rider_name": rider_response.data[0]["name"],
            "count": len(orders),
            "orders": orders
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rider orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rider orders: {str(e)}"
        )


@router.put("/riders/{rider_id}/orders/{order_id}/status")
async def update_order_status_by_rider(
    rider_id: str,
    order_id: str,
    status_update: dict,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Update order status by rider (Phase 2).

    Allows rider to update order status from rider mobile app.
    Validates that the order is assigned to the rider.

    Body:
    - status: New status (e.g., "picked_up", "delivering", "delivered")
    - notes: Optional notes
    """
    try:
        new_status = status_update.get("status")
        notes = status_update.get("notes", "")

        if not new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status field is required"
            )

        # Validate order belongs to this rider
        order_response = supabase.table("delivery_orders").select(
            "id, order_number, rider_id, status"
        ).eq("id", order_id).execute()

        if not order_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        order = order_response.data[0]

        if order.get("rider_id") != rider_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Order not assigned to this rider"
            )

        # Update order status
        update_data = {"status": new_status}

        # Update timestamp fields based on status
        now = datetime.utcnow().isoformat()
        if new_status == "picked_up":
            update_data["picked_up_at"] = now
        elif new_status == "delivering":
            update_data["picked_up_at"] = order.get("picked_up_at") or now
        elif new_status == "delivered":
            update_data["delivered_at"] = now
        elif new_status == "completed":
            update_data["completed_at"] = now

        updated_order = supabase.table("delivery_orders").update(update_data).eq(
            "id", order_id
        ).execute()

        # Log to order history
        history_entry = {
            "order_id": order_id,
            "status": new_status,
            "notes": notes or f"Updated by rider",
            "created_at": now
        }

        try:
            supabase.table("order_status_history").insert(history_entry).execute()
        except Exception as history_error:
            logger.warning(f"Failed to log order history: {history_error}")

        logger.info(f"✅ Rider {rider_id} updated order {order['order_number']} to {new_status}")

        return {
            "success": True,
            "message": "Order status updated",
            "order_id": order_id,
            "order_number": order["order_number"],
            "new_status": new_status,
            "updated_at": now
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
        )


# =====================================================
# RIDER AUTHENTICATION
# =====================================================

class RiderLoginRequest(BaseModel):
    phone: str
    password: str


@router.post("/riders/login")
async def rider_login(
    credentials: RiderLoginRequest,
    supabase: Client = Depends(get_supabase_client),
):
    """
    Authenticate rider using phone number and password.

    Body:
    - phone: Rider's phone number
    - password: Rider's password

    Returns rider info if authentication successful.
    """
    try:
        # Clean phone number (remove spaces, dashes, etc.)
        phone = credentials.phone.replace(" ", "").replace("-", "").strip()

        if not phone or not credentials.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number and password are required"
            )

        # Find rider by phone number
        rider_response = supabase.table("riders").select(
            "id, name, phone, password_hash, website_id, vehicle_type, vehicle_plate, is_active"
        ).eq("phone", phone).execute()

        if not rider_response.data or len(rider_response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nombor telefon atau kata laluan salah"
            )

        rider = rider_response.data[0]

        # Check if rider is active
        if rider.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akaun rider tidak aktif. Sila hubungi pentadbir."
            )

        # Verify password using bcrypt (SECURITY FIX)
        stored_password = rider.get("password_hash", "")
        if not verify_password(credentials.password, stored_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nombor telefon atau kata laluan salah"
            )

        # Remove password from response
        rider.pop("password_hash", None)

        logger.info(f"✅ Rider {rider['name']} ({phone}) logged in successfully")

        return {
            "success": True,
            "message": "Login berjaya",
            "rider": rider
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during rider login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login gagal: {str(e)}"
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
        "version": "2.0.0",  # Updated version for Phase 2
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "rider_system": True,
            "order_tracking": True,
            "phase_1_complete": True,
            "phase_2_gps_tracking": True,  # Now enabled!
            "phase_2_google_maps": True,
            "phase_2_gps_updates": True
        }
    }
