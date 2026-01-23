"""
Subscription Guard Middleware
Protects routes based on subscription status and limits
"""

from fastapi import HTTPException, status, Depends
from functools import wraps
from typing import Callable, Optional
from loguru import logger

from app.services.subscription_service import subscription_service
from app.core.security import get_current_user


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
