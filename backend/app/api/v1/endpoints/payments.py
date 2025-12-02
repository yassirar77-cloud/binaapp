"""
Payment Endpoints
Handles Stripe payments and subscriptions
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request, Header
from typing import Optional
from loguru import logger

from app.models.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SubscriptionPlan,
    SubscriptionTier
)
from app.services.payment_service import payment_service
from app.services.supabase_client import supabase_service
from app.core.security import get_current_user

router = APIRouter()


@router.get("/plans", response_model=dict)
async def get_subscription_plans():
    """
    Get all available subscription plans
    """
    try:
        plans = await payment_service.get_subscription_plans()

        return {
            "plans": [
                {
                    "tier": tier,
                    "name": plan["name"],
                    "price_monthly": plan["price_monthly"],
                    "price_yearly": plan["price_yearly"],
                    "features": plan["features"],
                    "max_websites": plan["max_websites"],
                    "custom_domain": tier == SubscriptionTier.PRO
                }
                for tier, plan in plans.items()
            ]
        }

    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription plans"
        )


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create Stripe checkout session for subscription
    """
    try:
        user_id = current_user.get("sub")
        email = current_user.get("email")

        # Create checkout session
        session = await payment_service.create_checkout_session(
            user_id=user_id,
            email=email,
            tier=request.tier,
            billing_period=request.billing_period
        )

        return CheckoutSessionResponse(
            session_id=session["session_id"],
            checkout_url=session["checkout_url"]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """
    Handle Stripe webhook events
    """
    try:
        if not stripe_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header"
            )

        payload = await request.body()

        # Process webhook
        result = await payment_service.handle_webhook(payload, stripe_signature)

        return result

    except ValueError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.get("/subscription", response_model=dict)
async def get_subscription(current_user: dict = Depends(get_current_user)):
    """
    Get current user's subscription
    """
    try:
        user_id = current_user.get("sub")

        subscription = await supabase_service.get_user_subscription(user_id)

        if not subscription:
            return {
                "tier": SubscriptionTier.FREE,
                "status": "active",
                "max_websites": 1,
                "features": payment_service.PLANS[SubscriptionTier.FREE]["features"]
            }

        tier = subscription.get("tier", SubscriptionTier.FREE)
        plan = payment_service.PLANS.get(tier)

        return {
            "tier": tier,
            "status": subscription.get("status"),
            "max_websites": plan["max_websites"],
            "features": plan["features"],
            "stripe_customer_id": subscription.get("stripe_customer_id"),
            "stripe_subscription_id": subscription.get("stripe_subscription_id")
        }

    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription"
        )


@router.post("/cancel-subscription")
async def cancel_subscription(current_user: dict = Depends(get_current_user)):
    """
    Cancel current subscription
    """
    try:
        user_id = current_user.get("sub")

        subscription = await supabase_service.get_user_subscription(user_id)

        if not subscription or subscription.get("tier") == SubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription to cancel"
            )

        stripe_subscription_id = subscription.get("stripe_subscription_id")
        if not stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe subscription found"
            )

        # Cancel in Stripe
        success = await payment_service.cancel_subscription(stripe_subscription_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel subscription"
            )

        # Update database
        await supabase_service.update_subscription(user_id, {
            "status": "cancelled",
            "tier": SubscriptionTier.FREE
        })

        logger.info(f"Subscription cancelled for user: {user_id}")

        return {
            "message": "Subscription cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )
