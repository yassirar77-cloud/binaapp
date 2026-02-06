"""
Subscription Guard Middleware
Protects routes based on subscription status and limits

Includes:
- HTTP Middleware for checking subscription lock status on every request
- Dependency injection guards for route-level protection
- Subscription status enum and helper functions
"""

from fastapi import HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from functools import wraps
from typing import Callable, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timedelta
from loguru import logger
import httpx

from app.services.subscription_service import subscription_service
from app.core.security import get_current_user
from app.core.config import settings


# =============================================================================
# SUBSCRIPTION STATUS ENUM
# =============================================================================

class SubscriptionStatus(str, Enum):
    """Subscription status values matching database constraint"""
    ACTIVE = "active"      # Paid and valid
    EXPIRED = "expired"    # Past end_date, entering grace
    GRACE = "grace"        # 5-day warning period
    LOCKED = "locked"      # Full lock, must pay
    CANCELLED = "cancelled"
    PENDING = "pending"


# =============================================================================
# PROTECTED AND ALLOWED ROUTES CONFIGURATION
# =============================================================================

# Routes that should be BLOCKED when subscription is LOCKED
PROTECTED_ROUTE_PREFIXES = [
    "/api/v1/websites",      # Website management (create, update, delete)
    "/api/v1/menu",          # Menu management
    "/api/v1/orders",        # Order management for restaurant owners
    "/api/v1/riders",        # Rider management
    "/api/v1/delivery",      # Delivery management
    "/api/v1/zones",         # Zone management
    "/api/v1/analytics",     # Analytics access
    "/dashboard",            # Dashboard routes
]

# Routes that should ALWAYS be allowed (even when locked)
ALLOWED_ROUTE_PREFIXES = [
    "/api/v1/subscription",   # So they can check status and pay
    "/api/v1/payments",       # So they can pay
    "/api/v1/auth",           # Authentication
    "/api/v1/health",         # Health checks
    "/health",                # Health check
    "/static",                # Static files
    "/docs",                  # API docs
    "/openapi.json",          # OpenAPI spec
    "/api/upload",            # Allow uploads for payment proof
]

# HTTP methods that are always allowed (read-only operations)
ALLOWED_METHODS_WHEN_GRACE = ["GET", "HEAD", "OPTIONS"]


# =============================================================================
# SUBSCRIPTION STATUS CHECKER
# =============================================================================

async def get_subscription_status_from_db(user_id: str) -> Dict[str, Any]:
    """
    Get detailed subscription status from database including lock info.
    Returns status, days remaining, grace info, and lock details.
    """
    try:
        url = f"{settings.SUPABASE_URL}/rest/v1/subscriptions"
        params = {
            "user_id": f"eq.{user_id}",
            "select": "id,user_id,tier,status,end_date,grace_period_end,locked_at,lock_reason,last_payment_reminder,auto_renew"
        }
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logger.error(f"Failed to get subscription: {response.status_code}")
            return {"status": SubscriptionStatus.ACTIVE, "error": "fetch_failed"}

        records = response.json()
        if not records:
            # No subscription found - treat as active (free tier)
            return {
                "status": SubscriptionStatus.ACTIVE,
                "tier": "starter",
                "end_date": None,
                "is_locked": False,
                "days_remaining": None,
                "grace_days_remaining": None,
                "can_use_dashboard": True,
                "can_use_website": True,
            }

        sub = records[0]
        now = datetime.utcnow()

        # Parse dates
        end_date = None
        if sub.get("end_date"):
            end_date = datetime.fromisoformat(sub["end_date"].replace("Z", "+00:00")).replace(tzinfo=None)

        grace_period_end = None
        if sub.get("grace_period_end"):
            grace_period_end = datetime.fromisoformat(sub["grace_period_end"].replace("Z", "+00:00")).replace(tzinfo=None)

        # Calculate days remaining
        days_remaining = None
        if end_date:
            days_remaining = max(0, (end_date - now).days)

        grace_days_remaining = None
        if grace_period_end:
            grace_days_remaining = max(0, (grace_period_end - now).days)

        # Determine effective status
        db_status = sub.get("status", "active")
        is_locked = db_status == SubscriptionStatus.LOCKED
        is_grace = db_status == SubscriptionStatus.GRACE
        is_expired = db_status == SubscriptionStatus.EXPIRED

        # Determine permissions
        can_use_dashboard = not is_locked
        can_use_website = not is_locked  # Websites can still be viewed by customers

        return {
            "subscription_id": sub.get("id"),
            "user_id": user_id,
            "status": db_status,
            "tier": sub.get("tier", "starter"),
            "end_date": sub.get("end_date"),
            "grace_period_end": sub.get("grace_period_end"),
            "locked_at": sub.get("locked_at"),
            "lock_reason": sub.get("lock_reason"),
            "auto_renew": sub.get("auto_renew", False),
            "is_locked": is_locked,
            "is_grace": is_grace,
            "is_expired": is_expired,
            "days_remaining": days_remaining,
            "grace_days_remaining": grace_days_remaining,
            "can_use_dashboard": can_use_dashboard,
            "can_use_website": can_use_website,
        }

    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        # Fail open - allow access if we can't check
        return {
            "status": SubscriptionStatus.ACTIVE,
            "error": str(e),
            "is_locked": False,
            "can_use_dashboard": True,
            "can_use_website": True,
        }


def is_route_protected(path: str) -> bool:
    """Check if a route should be protected when subscription is locked"""
    for prefix in ALLOWED_ROUTE_PREFIXES:
        if path.startswith(prefix):
            return False

    for prefix in PROTECTED_ROUTE_PREFIXES:
        if path.startswith(prefix):
            return True

    return False


def is_route_allowed(path: str) -> bool:
    """Check if a route should always be allowed"""
    for prefix in ALLOWED_ROUTE_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


async def get_user_id_from_request(request: Request) -> Optional[str]:
    """Extract user ID from request authorization header"""
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.replace("Bearer ", "")
        if not token:
            return None

        # Verify token with Supabase
        url = f"{settings.SUPABASE_URL}/auth/v1/user"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            return user_data.get("id")

        return None

    except Exception as e:
        logger.debug(f"Could not extract user ID: {e}")
        return None


# =============================================================================
# HTTP MIDDLEWARE FOR SUBSCRIPTION CHECK
# =============================================================================

async def subscription_check_middleware(request: Request, call_next):
    """
    HTTP Middleware to check subscription status on protected routes.

    Flow:
    1. Allow all OPTIONS requests (CORS preflight)
    2. Allow all explicitly allowed routes (payment, auth, health)
    3. For protected routes, check if user is authenticated
    4. If authenticated, check subscription status
    5. If LOCKED, return 403 with payment URL
    6. If GRACE, allow GET but warn on mutating operations
    """
    path = request.url.path
    method = request.method

    # Always allow OPTIONS requests (CORS preflight)
    if method == "OPTIONS":
        return await call_next(request)

    # Always allow explicitly allowed routes
    if is_route_allowed(path):
        return await call_next(request)

    # Check if this is a protected route
    if not is_route_protected(path):
        return await call_next(request)

    # Protected route - check for authentication
    user_id = await get_user_id_from_request(request)

    if not user_id:
        # Not authenticated - let the route handler deal with it
        return await call_next(request)

    # Get subscription status
    sub_status = await get_subscription_status_from_db(user_id)

    # Check if locked
    if sub_status.get("is_locked"):
        logger.warning(f"Blocked locked user {user_id} from accessing {path}")
        return JSONResponse(
            status_code=403,
            content={
                "error": "subscription_locked",
                "code": "SUBSCRIPTION_LOCKED",
                "message": "Langganan anda telah dikunci. Sila buat pembayaran untuk meneruskan.",
                "message_en": "Your subscription has been locked. Please make a payment to continue.",
                "status": "locked",
                "lock_reason": sub_status.get("lock_reason"),
                "locked_at": sub_status.get("locked_at"),
                "payment_url": "/dashboard/billing",
                "can_use_dashboard": False,
                "can_use_website": False,
            }
        )

    # Check if in grace period and doing mutating operation
    if sub_status.get("is_grace") and method not in ALLOWED_METHODS_WHEN_GRACE:
        # In grace period - allow GET but warn on mutations
        logger.info(f"User {user_id} in grace period attempting {method} on {path}")
        # Still allow but add warning header
        response = await call_next(request)
        response.headers["X-Subscription-Warning"] = "grace_period"
        response.headers["X-Grace-Days-Remaining"] = str(sub_status.get("grace_days_remaining", 0))
        return response

    # Check if expired (transitioning to grace)
    if sub_status.get("is_expired"):
        # Add warning header
        response = await call_next(request)
        response.headers["X-Subscription-Warning"] = "expired"
        response.headers["X-Days-Remaining"] = str(sub_status.get("days_remaining", 0))
        return response

    # All good - proceed
    return await call_next(request)


class SubscriptionGuard:
    """
    Middleware for checking subscription status and limits

    Usage:
        # As a dependency
        @router.post("/create-website")
        async def create_website(
            ...,
            _sub_check: dict = Depends(SubscriptionGuard.require_active())
        ):
            ...

        # With limit check
        @router.post("/generate-image")
        async def generate_image(
            ...,
            _limit_check: dict = Depends(SubscriptionGuard.check_limit("generate_ai_image"))
        ):
            ...
    """

    @staticmethod
    def require_active():
        """
        Dependency that requires an active subscription
        Blocks if subscription is expired or suspended
        """
        async def dependency(current_user: dict = Depends(get_current_user)):
            user_id = current_user.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sila log masuk untuk meneruskan"
                )

            sub_status = await subscription_service.get_subscription_status(user_id)

            if sub_status.get("is_expired") or sub_status.get("status") in ["expired", "suspended"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "subscription_expired",
                        "message": "Langganan anda telah tamat. Sila perbaharui untuk meneruskan.",
                        "plan_name": sub_status.get("plan_name"),
                        "expired_at": sub_status.get("end_date"),
                        "renew_url": "/dashboard/billing"
                    }
                )

            return {
                "user_id": user_id,
                "subscription": sub_status
            }

        return dependency

    @staticmethod
    def check_limit(action: str):
        """
        Dependency that checks if user can perform a specific action

        Actions:
            - create_website
            - add_menu_item
            - generate_ai_hero
            - generate_ai_image
            - add_zone
            - add_rider
        """
        async def dependency(current_user: dict = Depends(get_current_user)):
            user_id = current_user.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sila log masuk untuk meneruskan"
                )

            # Check subscription status first
            sub_status = await subscription_service.get_subscription_status(user_id)

            if sub_status.get("is_expired") or sub_status.get("status") in ["expired", "suspended"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "subscription_expired",
                        "message": "Langganan anda telah tamat. Sila perbaharui untuk meneruskan.",
                        "renew_url": "/dashboard/billing"
                    }
                )

            # Check limit for the action
            limit_result = await subscription_service.check_limit(user_id, action)

            if not limit_result.get("allowed"):
                # Check if user has addon credits
                if limit_result.get("can_buy_addon"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "limit_reached",
                            "message": limit_result.get("message"),
                            "current_usage": limit_result.get("current_usage"),
                            "limit": limit_result.get("limit"),
                            "can_buy_addon": True,
                            "addon_type": limit_result.get("addon_type"),
                            "addon_price": limit_result.get("addon_price"),
                            "upgrade_url": "/dashboard/billing"
                        }
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "limit_reached",
                            "message": limit_result.get("message"),
                            "current_usage": limit_result.get("current_usage"),
                            "limit": limit_result.get("limit"),
                            "can_buy_addon": False,
                            "upgrade_url": "/dashboard/billing"
                        }
                    )

            return {
                "user_id": user_id,
                "limit_check": limit_result,
                "using_addon": limit_result.get("using_addon", False)
            }

        return dependency

    @staticmethod
    def require_feature(feature: str):
        """
        Dependency that requires a specific feature enabled in user's plan

        Features:
            - custom_domain
            - api_access
            - white_label
            - gps_tracking
            - priority_ai
            - analytics
            - qr_payment
        """
        async def dependency(current_user: dict = Depends(get_current_user)):
            user_id = current_user.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sila log masuk untuk meneruskan"
                )

            # Get subscription and check features
            subscription = await subscription_service.get_user_subscription(user_id)

            if not subscription:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "feature_not_available",
                        "message": f"Ciri '{feature}' tidak tersedia dalam pelan anda",
                        "required_plan": "basic atau pro",
                        "upgrade_url": "/dashboard/billing"
                    }
                )

            # Get plan features
            plans = await subscription_service.get_subscription_plans()
            tier = subscription.get("tier", "starter")

            plan = next((p for p in plans if p.get("plan_name") == tier), None)

            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "feature_not_available",
                        "message": f"Ciri '{feature}' tidak tersedia dalam pelan anda",
                        "upgrade_url": "/dashboard/billing"
                    }
                )

            features = plan.get("features", {})

            if not features.get(feature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "feature_not_available",
                        "message": f"Ciri '{feature}' tidak tersedia dalam pelan {tier}",
                        "current_plan": tier,
                        "upgrade_url": "/dashboard/billing"
                    }
                )

            return {
                "user_id": user_id,
                "feature": feature,
                "plan": tier
            }

        return dependency

    @staticmethod
    def require_tier(min_tier: str):
        """
        Dependency that requires a minimum subscription tier

        Tiers (in order):
            - starter
            - basic
            - pro
        """
        async def dependency(current_user: dict = Depends(get_current_user)):
            user_id = current_user.get("sub")

            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sila log masuk untuk meneruskan"
                )

            tier_order = {"starter": 1, "basic": 2, "pro": 3}
            min_tier_level = tier_order.get(min_tier.lower(), 1)

            # Get subscription
            sub_status = await subscription_service.get_subscription_status(user_id)
            current_tier = sub_status.get("plan_name", "starter")
            current_tier_level = tier_order.get(current_tier.lower(), 1)

            if current_tier_level < min_tier_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "tier_required",
                        "message": f"Ciri ini memerlukan pelan {min_tier.upper()} atau lebih tinggi",
                        "current_plan": current_tier,
                        "required_plan": min_tier,
                        "upgrade_url": "/dashboard/billing"
                    }
                )

            return {
                "user_id": user_id,
                "current_tier": current_tier
            }

        return dependency


# Helper functions for use in route handlers

async def check_and_increment_usage(user_id: str, action: str) -> dict:
    """
    Check limit and increment usage counter if allowed
    Returns the limit check result

    Usage in route handler:
        result = await check_and_increment_usage(user_id, "create_website")
        if not result["allowed"]:
            raise HTTPException(...)
        # Proceed with action
    """
    limit_result = await subscription_service.check_limit(user_id, action)

    if not limit_result.get("allowed"):
        return limit_result

    # If using addon, consume the addon credit
    if limit_result.get("using_addon"):
        addon_type_map = {
            "create_website": "website",
            "generate_ai_hero": "ai_hero",
            "generate_ai_image": "ai_image",
            "add_zone": "zone",
            "add_rider": "rider"
        }
        addon_type = addon_type_map.get(action)
        if addon_type:
            await subscription_service.use_addon_credit(user_id, addon_type)
        # Always increment usage counters so UI reflects total used
        await subscription_service.increment_usage(user_id, action)
    else:
        # Increment the usage counter
        await subscription_service.increment_usage(user_id, action)

    return limit_result


async def decrement_usage_on_delete(user_id: str, action: str) -> bool:
    """
    Decrement usage counter when user deletes something
    """
    delete_action_map = {
        "delete_website": "delete_website",
        "delete_menu_item": "delete_menu_item",
        "delete_zone": "delete_zone",
        "delete_rider": "delete_rider"
    }

    if action not in delete_action_map:
        return False

    return await subscription_service.decrement_usage(user_id, action)


# Subscription guard instance for convenience
subscription_guard = SubscriptionGuard()
