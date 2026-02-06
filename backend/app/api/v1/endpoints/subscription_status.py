"""
Subscription Status Endpoint
GET /api/v1/subscription/status

Returns detailed subscription status including:
- Current status (active, expired, grace, locked)
- Days remaining until expiry
- Grace period days remaining
- Lock information
- Feature access permissions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.core.security import get_current_user
from app.middleware.subscription_guard import (
    get_subscription_status_from_db,
    SubscriptionStatus,
)
from app.services.subscription_service import subscription_service


router = APIRouter(prefix="/subscription", tags=["Subscription Status"])


# =============================================================================
# SUBSCRIPTION STATUS ENDPOINT
# =============================================================================

@router.get("/status")
async def get_subscription_status(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user's subscription status.

    Returns:
        - status: Current subscription status (active, expired, grace, locked)
        - tier: Subscription tier (starter, basic, pro)
        - days_remaining: Days until subscription expires
        - grace_days_remaining: Days remaining in grace period (if applicable)
        - is_locked: Whether the subscription is locked
        - lock_reason: Reason for lock (if locked)
        - can_use_dashboard: Whether user can access dashboard features
        - can_use_website: Whether user can manage websites
        - end_date: Subscription end date
        - grace_period_end: Grace period end date (if applicable)
        - payment_url: URL to make payment
    """
    user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak sah"
        )

    # Get detailed subscription status
    sub_status = await get_subscription_status_from_db(user_id)

    # Add payment URL
    sub_status["payment_url"] = "/dashboard/billing"

    # Add human-readable status message
    status_messages = {
        "active": {
            "message": "Langganan anda aktif",
            "message_en": "Your subscription is active"
        },
        "expired": {
            "message": "Langganan anda telah tamat. Sila perbaharui dalam masa 5 hari.",
            "message_en": "Your subscription has expired. Please renew within 5 days."
        },
        "grace": {
            "message": f"Anda dalam tempoh tangguh. Baki {sub_status.get('grace_days_remaining', 0)} hari sebelum akaun dikunci.",
            "message_en": f"You are in grace period. {sub_status.get('grace_days_remaining', 0)} days remaining before account lock."
        },
        "locked": {
            "message": "Akaun anda telah dikunci. Sila buat pembayaran untuk meneruskan.",
            "message_en": "Your account has been locked. Please make a payment to continue."
        },
    }

    current_status = sub_status.get("status", "active")
    if current_status in status_messages:
        sub_status["status_message"] = status_messages[current_status]["message"]
        sub_status["status_message_en"] = status_messages[current_status]["message_en"]

    # Add urgency level for UI
    # Active subscriptions with auto-renew should never show urgency
    auto_renew = sub_status.get("auto_renew", False)
    if current_status == "active" and auto_renew:
        sub_status["urgency"] = "none"
    elif current_status == "locked":
        sub_status["urgency"] = "critical"
    elif current_status == "grace":
        sub_status["urgency"] = "high"
    elif current_status == "expired":
        sub_status["urgency"] = "medium"
    elif sub_status.get("days_remaining") is not None and sub_status["days_remaining"] <= 5:
        sub_status["urgency"] = "low"
    else:
        sub_status["urgency"] = "none"

    return sub_status


@router.get("/lock-info")
async def get_lock_info(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get detailed lock information for the current user.

    Returns lock reason, lock time, and what actions are blocked.
    """
    user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak sah"
        )

    sub_status = await get_subscription_status_from_db(user_id)

    if not sub_status.get("is_locked"):
        return {
            "is_locked": False,
            "message": "Akaun anda tidak dikunci",
            "message_en": "Your account is not locked"
        }

    return {
        "is_locked": True,
        "locked_at": sub_status.get("locked_at"),
        "lock_reason": sub_status.get("lock_reason"),
        "blocked_actions": [
            "create_website",
            "edit_website",
            "delete_website",
            "manage_menu",
            "manage_orders",
            "manage_riders",
            "view_analytics",
        ],
        "allowed_actions": [
            "view_subscription",
            "make_payment",
            "view_billing",
            "contact_support",
        ],
        "payment_url": "/dashboard/billing",
        "message": "Akaun anda telah dikunci kerana langganan tamat. Sila buat pembayaran untuk membuka kunci.",
        "message_en": "Your account has been locked due to expired subscription. Please make a payment to unlock."
    }


@router.get("/can-access/{feature}")
async def check_feature_access(
    feature: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check if user can access a specific feature.

    Features:
        - dashboard: Access to main dashboard
        - websites: Create/edit websites
        - menu: Manage menu items
        - orders: Manage orders
        - analytics: View analytics
        - riders: Manage riders
        - delivery: Manage delivery settings
    """
    user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak sah"
        )

    sub_status = await get_subscription_status_from_db(user_id)

    # Features blocked when locked
    locked_features = [
        "dashboard", "websites", "menu", "orders",
        "analytics", "riders", "delivery", "zones"
    ]

    is_locked = sub_status.get("is_locked", False)
    can_access = not is_locked or feature not in locked_features

    # Special case: billing and subscription always accessible
    if feature in ["billing", "subscription", "payment", "profile"]:
        can_access = True

    return {
        "feature": feature,
        "can_access": can_access,
        "subscription_status": sub_status.get("status"),
        "is_locked": is_locked,
        "reason": "subscription_locked" if is_locked and not can_access else None,
        "payment_url": "/dashboard/billing" if not can_access else None,
    }


@router.get("/websites-lock-status")
async def get_websites_lock_status(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get lock status for all websites owned by the user.

    Returns list of websites with their individual lock status.
    """
    user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak sah"
        )

    try:
        from app.core.config import settings
        import httpx

        # Get all websites for user with their lock status
        url = f"{settings.SUPABASE_URL}/rest/v1/websites"
        params = {
            "user_id": f"eq.{user_id}",
            "select": "id,name,subdomain,website_lock_status(is_locked,locked_at,lock_reason)"
        }
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logger.error(f"Failed to get websites: {response.status_code}")
            return {"websites": [], "error": "fetch_failed"}

        websites = response.json()

        # Format response
        result = []
        for website in websites:
            lock_status = website.get("website_lock_status", [])
            is_locked = False
            locked_at = None
            lock_reason = None

            if lock_status and len(lock_status) > 0:
                is_locked = lock_status[0].get("is_locked", False)
                locked_at = lock_status[0].get("locked_at")
                lock_reason = lock_status[0].get("lock_reason")

            result.append({
                "website_id": website.get("id"),
                "name": website.get("name"),
                "subdomain": website.get("subdomain"),
                "is_locked": is_locked,
                "locked_at": locked_at,
                "lock_reason": lock_reason,
            })

        return {"websites": result}

    except Exception as e:
        logger.error(f"Error getting websites lock status: {e}")
        return {"websites": [], "error": str(e)}


@router.get("/expiry-warning")
async def get_expiry_warning(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get expiry warning information if subscription is expiring soon.

    Returns warning level and message based on days remaining.
    """
    user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak sah"
        )

    sub_status = await get_subscription_status_from_db(user_id)

    days_remaining = sub_status.get("days_remaining")
    grace_days_remaining = sub_status.get("grace_days_remaining")
    status_value = sub_status.get("status")
    auto_renew = sub_status.get("auto_renew", False)

    # Active subscription with auto-renew enabled should not show expiry warnings
    # The subscription will renew automatically when the billing cycle ends
    if status_value == "active" and auto_renew:
        return {
            "show_warning": False,
            "warning_level": "none",
            "days_remaining": days_remaining,
        }

    # Determine warning level
    if status_value == "locked":
        return {
            "show_warning": True,
            "warning_level": "critical",
            "title": "Akaun Dikunci",
            "title_en": "Account Locked",
            "message": "Akaun anda telah dikunci. Sila buat pembayaran segera.",
            "message_en": "Your account has been locked. Please make payment immediately.",
            "days_remaining": 0,
            "action": "pay_now",
            "action_url": "/dashboard/billing",
        }

    if status_value == "grace":
        return {
            "show_warning": True,
            "warning_level": "high",
            "title": "Tempoh Tangguh",
            "title_en": "Grace Period",
            "message": f"Baki {grace_days_remaining} hari sebelum akaun dikunci.",
            "message_en": f"{grace_days_remaining} days remaining before account lock.",
            "days_remaining": grace_days_remaining,
            "action": "pay_now",
            "action_url": "/dashboard/billing",
        }

    if status_value == "expired":
        return {
            "show_warning": True,
            "warning_level": "medium",
            "title": "Langganan Tamat",
            "title_en": "Subscription Expired",
            "message": "Langganan anda telah tamat. Sila perbaharui segera.",
            "message_en": "Your subscription has expired. Please renew immediately.",
            "days_remaining": 0,
            "action": "renew",
            "action_url": "/dashboard/billing",
        }

    if days_remaining is not None:
        if days_remaining <= 3:
            return {
                "show_warning": True,
                "warning_level": "medium",
                "title": "Langganan Hampir Tamat",
                "title_en": "Subscription Expiring Soon",
                "message": f"Langganan anda akan tamat dalam {days_remaining} hari.",
                "message_en": f"Your subscription will expire in {days_remaining} days.",
                "days_remaining": days_remaining,
                "action": "renew",
                "action_url": "/dashboard/billing",
            }

        if days_remaining <= 5:
            return {
                "show_warning": True,
                "warning_level": "low",
                "title": "Peringatan Langganan",
                "title_en": "Subscription Reminder",
                "message": f"Langganan anda akan tamat dalam {days_remaining} hari.",
                "message_en": f"Your subscription will expire in {days_remaining} days.",
                "days_remaining": days_remaining,
                "action": "renew",
                "action_url": "/dashboard/billing",
            }

    # No warning needed
    return {
        "show_warning": False,
        "warning_level": "none",
        "days_remaining": days_remaining,
    }
