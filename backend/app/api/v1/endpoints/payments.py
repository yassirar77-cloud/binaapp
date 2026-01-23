"""
Payment Endpoints
Handles Stripe payments and subscriptions
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request, Header
from typing import Optional
from pydantic import BaseModel
from loguru import logger

# Request models for payment endpoints
class SubscriptionRequest(BaseModel):
    user_id: str  # UUID string from Supabase

class AddonPurchaseRequest(BaseModel):
    user_id: str  # UUID string from Supabase
    addon_type: str
    quantity: int = 1

from app.models.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    SubscriptionPlan,
    SubscriptionTier
)
from app.services.payment_service import payment_service
from app.services.supabase_client import supabase_service
from app.services.toyyibpay_service import toyyibpay_service
from app.core.security import get_current_user
from app.core.config import settings

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


# ============================================
# ToyyibPay Endpoints
# ============================================

@router.get("/test")
async def test_toyyibpay():
    """
    Test ToyyibPay integration
    Creates a test bill to verify API connection
    """
    try:
        result = toyyibpay_service.test_connection()

        return {
            "success": True,
            "sandbox": settings.TOYYIBPAY_SANDBOX,
            "base_url": toyyibpay_service.base_url,
            "result": result
        }

    except Exception as e:
        logger.error(f"ToyyibPay test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ToyyibPay test failed: {str(e)}"
        )


@router.post("/toyyibpay/create-bill")
async def create_toyyibpay_bill(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a ToyyibPay bill for subscription payment
    """
    try:
        body = await request.json()

        user_id = current_user.get("sub")
        email = current_user.get("email")

        bill_name = body.get("bill_name", "BinaApp Subscription")
        bill_description = body.get("bill_description", "BinaApp subscription payment")
        bill_amount = float(body.get("amount", 29.00))
        bill_phone = body.get("phone", "")
        customer_name = body.get("customer_name", email)

        result = toyyibpay_service.create_bill(
            bill_name=bill_name,
            bill_description=bill_description,
            bill_amount=bill_amount,
            bill_email=email,
            bill_phone=bill_phone,
            bill_name_customer=customer_name,
            bill_external_reference_no=f"BINA_{user_id[:8]}"
        )

        if result.get("success"):
            logger.info(f"ToyyibPay bill created for user {user_id}: {result.get('bill_code')}")
            return {
                "success": True,
                "bill_code": result.get("bill_code"),
                "payment_url": result.get("payment_url")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to create bill")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ToyyibPay bill: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment bill"
        )


@router.post("/toyyibpay/callback")
async def toyyibpay_callback(request: Request):
    """
    Handle ToyyibPay payment callback
    This is called by ToyyibPay after payment is processed
    """
    try:
        # Get form data from callback
        form_data = await request.form()
        data = dict(form_data)

        logger.info(f"ToyyibPay callback received: {data}")

        result = toyyibpay_service.verify_callback(data)

        if result.get("success") and result.get("status") == "paid":
            # Payment successful - update user subscription
            bill_code = result.get("bill_code")
            logger.info(f"Payment successful for bill: {bill_code}")

            # TODO: Extract user_id from bill_external_reference_no and update subscription
            # For now, just log the success

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"ToyyibPay callback error: {e}")
        return {"status": "ERROR", "message": str(e)}


@router.get("/toyyibpay/verify/{bill_code}")
async def verify_toyyibpay_payment(bill_code: str):
    """
    Verify payment status for a ToyyibPay bill
    """
    try:
        result = toyyibpay_service.get_bill_transactions(bill_code)

        return result

    except Exception as e:
        logger.error(f"Error verifying ToyyibPay payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify payment"
        )


# ============================================
# Subscription & Addon Purchase Endpoints
# ============================================

# Subscription tier pricing (RM)
TIER_PRICES = {
    "starter": 5,
    "basic": 29,
    "pro": 49
}

# Addon pricing (RM)
ADDON_PRICES = {
    "ai_image": 0.50,
    "ai_hero": 2.00,
    "extra_website": 5.00,
    "extra_rider": 3.00,
    "extra_zone": 2.00
}


@router.post("/subscribe/{tier}")
async def create_subscription_payment(
    tier: str,
    request: SubscriptionRequest
):
    """
    Create a ToyyibPay bill for subscription upgrade
    """
    try:
        # Validate tier
        if tier not in TIER_PRICES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {tier}. Valid tiers: {list(TIER_PRICES.keys())}"
            )

        user_id = request.user_id

        # Validate user_id is not empty
        if not user_id or not user_id.strip():
            logger.error("Subscription payment failed: user_id is empty")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required. Please log in again."
            )

        user_id = user_id.strip()
        price = TIER_PRICES[tier]

        logger.info(f"Creating subscription payment: tier={tier}, user_id={user_id[:8]}...")

        # Get user email from database (try multiple sources)
        email = None

        # Try to get from users table
        user_data = await supabase_service.get_user_by_id(user_id)
        if user_data and user_data.get("email"):
            email = user_data.get("email")
            logger.info(f"Found email from users table: {email}")

        # Fallback: try to get from auth system
        if not email:
            auth_user = await supabase_service.get_user(user_id)
            if auth_user and hasattr(auth_user, 'email'):
                email = auth_user.email
                logger.info(f"Found email from auth: {email}")

        # Final fallback: generate email
        if not email:
            email = f"user{user_id[:8]}@binaapp.my"
            logger.warning(f"Using generated email for user {user_id[:8]}: {email}")

        # Truncate external reference to avoid ToyyibPay limits (max 50 chars)
        external_ref = f"SUB_{tier}_{user_id[:20]}"

        logger.info(f"Creating ToyyibPay bill: email={email}, ref={external_ref}")

        # Create ToyyibPay bill
        result = toyyibpay_service.create_bill(
            bill_name=f"BinaApp {tier.upper()} Subscription",
            bill_description=f"Monthly subscription to BinaApp {tier.upper()} plan",
            bill_amount=price,
            bill_email=email,
            bill_phone="",
            bill_name_customer=email,
            bill_external_reference_no=external_ref
        )

        if result.get("success"):
            bill_code = result.get("bill_code")
            logger.info(f"ToyyibPay bill created: {bill_code}")

            # Try to store payment record in database (optional - don't fail if table doesn't exist)
            payment_id = bill_code
            try:
                payment_record = await supabase_service.insert_record("payments", {
                    "user_id": str(user_id),
                    "bill_code": bill_code,
                    "amount": price,
                    "type": "subscription",
                    "tier": tier,
                    "status": "pending"
                })
                if payment_record and len(payment_record) > 0:
                    payment_id = payment_record[0].get("id", bill_code)
                    logger.info(f"Payment record stored: {payment_id}")
                else:
                    logger.warning("Payment record not stored (payments table may not exist)")
            except Exception as db_error:
                logger.warning(f"Could not store payment record: {db_error}")
                # Continue anyway - payment can still proceed

            logger.info(f"Subscription payment created for user {user_id[:8]}: {tier} - {bill_code}")

            return {
                "success": True,
                "payment_id": payment_id,
                "bill_code": bill_code,
                "payment_url": result.get("payment_url"),
                "tier": tier,
                "amount": price
            }
        else:
            error_msg = result.get("error", "Failed to create payment")
            error_details = result.get("details", "")
            logger.error(f"ToyyibPay bill creation failed: {error_msg} | Details: {error_details}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error_msg}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription payment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription payment: {str(e)}"
        )


@router.post("/addon/purchase")
async def purchase_addon(
    request: AddonPurchaseRequest
):
    """
    Create a ToyyibPay bill for addon purchase
    """
    try:
        user_id = request.user_id
        addon_type = request.addon_type
        quantity = request.quantity

        # Validate user_id
        if not user_id or not user_id.strip():
            logger.error("Addon purchase failed: user_id is empty")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required. Please log in again."
            )

        user_id = user_id.strip()

        if addon_type not in ADDON_PRICES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid addon type: {addon_type}"
            )

        logger.info(f"Creating addon purchase: type={addon_type}, qty={quantity}, user={user_id[:8]}...")

        # Get user email from database (try multiple sources)
        email = None

        user_data = await supabase_service.get_user_by_id(user_id)
        if user_data and user_data.get("email"):
            email = user_data.get("email")

        if not email:
            auth_user = await supabase_service.get_user(user_id)
            if auth_user and hasattr(auth_user, 'email'):
                email = auth_user.email

        if not email:
            email = f"user{user_id[:8]}@binaapp.my"
            logger.warning(f"Using generated email for addon purchase: {email}")

        unit_price = ADDON_PRICES[addon_type]
        total_price = unit_price * quantity

        # Truncate external reference
        external_ref = f"ADDON_{addon_type}_{user_id[:16]}"

        # Create ToyyibPay bill
        result = toyyibpay_service.create_bill(
            bill_name=f"BinaApp Addon - {addon_type}",
            bill_description=f"Purchase of {quantity}x {addon_type} addon",
            bill_amount=total_price,
            bill_email=email,
            bill_phone="",
            bill_name_customer=email,
            bill_external_reference_no=external_ref
        )

        if result.get("success"):
            bill_code = result.get("bill_code")
            logger.info(f"ToyyibPay addon bill created: {bill_code}")

            # Try to store addon purchase record (optional)
            addon_id = bill_code
            try:
                addon_record = await supabase_service.insert_record("addon_purchases", {
                    "user_id": str(user_id),
                    "bill_code": bill_code,
                    "addon_type": addon_type,
                    "quantity": quantity,
                    "amount": total_price,
                    "status": "pending"
                })
                if addon_record and len(addon_record) > 0:
                    addon_id = addon_record[0].get("id", bill_code)
            except Exception as db_error:
                logger.warning(f"Could not store addon purchase record: {db_error}")

            logger.info(f"Addon purchase created for user {user_id[:8]}: {addon_type} x{quantity}")

            return {
                "success": True,
                "addon_id": addon_id,
                "payment_id": bill_code,
                "bill_code": bill_code,
                "payment_url": result.get("payment_url"),
                "addon_type": addon_type,
                "quantity": quantity,
                "amount": total_price
            }
        else:
            error_msg = result.get("error", "Failed to create payment")
            error_details = result.get("details", "")
            logger.error(f"ToyyibPay addon bill creation failed: {error_msg} | Details: {error_details}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{error_msg}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating addon purchase: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create addon purchase: {str(e)}"
        )


@router.post("/subscriptions/upgrade/{tier}")
async def upgrade_subscription(
    tier: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Upgrade user subscription after successful payment
    """
    try:
        body = await request.json()
        payment_id = body.get("payment_id")

        if tier not in TIER_PRICES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {tier}"
            )

        user_id = current_user.get("sub")

        # Update user's subscription tier
        # First, try to update existing subscription
        update_result = await supabase_service.update_user_subscription(user_id, {
            "tier": tier,
            "status": "active",
            "price": TIER_PRICES[tier]
        })

        # Update payment status if payment_id provided
        if payment_id:
            await supabase_service.update_payment_status(payment_id, "successful")

        logger.info(f"Subscription upgraded for user {user_id} to {tier}")

        return {
            "success": True,
            "subscription": {
                "tier": tier,
                "status": "active",
                "price": TIER_PRICES[tier]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upgrading subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade subscription"
        )


@router.get("/subscriptions/current")
async def get_current_subscription(current_user: dict = Depends(get_current_user)):
    """
    Get user's current subscription details
    """
    try:
        user_id = current_user.get("sub")

        subscription = await supabase_service.get_user_subscription(user_id)

        if not subscription:
            return {
                "tier": "free",
                "price": 0,
                "status": "active",
                "limits": {
                    "websites": "1",
                    "menu_items": "20",
                    "ai_hero": "1",
                    "ai_images": "5",
                    "delivery_zones": "1"
                }
            }

        return {
            "tier": subscription.get("tier", "free"),
            "price": subscription.get("price", 0),
            "status": subscription.get("status", "active"),
            "valid_until": subscription.get("current_period_end")
        }

    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription"
        )
