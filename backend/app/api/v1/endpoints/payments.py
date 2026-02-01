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
            "success": result.get("success", False),
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


@router.get("/test-credentials")
async def test_toyyibpay_credentials():
    """
    Test ToyyibPay credentials and configuration
    Returns detailed configuration info and attempts to create a test bill
    """
    try:
        logger.info("🔍 Testing ToyyibPay credentials...")

        result = toyyibpay_service.test_connection()

        return {
            "success": result.get("success", False),
            "sandbox": settings.TOYYIBPAY_SANDBOX,
            "base_url": toyyibpay_service.base_url,
            "config": result.get("config", {}),
            "bill_code": result.get("bill_code"),
            "payment_url": result.get("payment_url"),
            "error": result.get("error"),
            "details": result.get("details")
        }

    except Exception as e:
        logger.error(f"ToyyibPay credentials test failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "sandbox": settings.TOYYIBPAY_SANDBOX,
            "base_url": toyyibpay_service.base_url
        }


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
    This is called by ToyyibPay after payment is processed.

    Processes payments for:
    - Subscription upgrades/renewals
    - Addon purchases
    """
    try:
        # Get form data from callback
        form_data = await request.form()
        data = dict(form_data)

        logger.info(f"📥 ToyyibPay callback received: {data}")

        result = toyyibpay_service.verify_callback(data)

        if result.get("success") and result.get("status") == "paid":
            bill_code = result.get("bill_code")
            tp_transaction_id = result.get("transaction_id")
            reference = result.get("reference")
            amount = result.get("amount")

            logger.info(f"✅ Payment successful for bill: {bill_code}")
            logger.info(f"   ToyyibPay Transaction ID: {tp_transaction_id}")
            logger.info(f"   Reference: {reference}")
            logger.info(f"   Amount: {amount}")

            # Process the payment using the new subscription system tables
            await _process_successful_payment(bill_code, tp_transaction_id)

        elif result.get("status") == "pending":
            logger.info(f"⏳ Payment pending for bill: {result.get('bill_code')}")

        else:
            logger.warning(f"❌ Payment failed or unknown status: {result}")
            # Update transaction status to failed if we can find it
            bill_code = result.get("bill_code")
            if bill_code:
                await _update_transaction_status(bill_code, "failed")

        return {"status": "OK"}

    except Exception as e:
        logger.error(f"ToyyibPay callback error: {e}", exc_info=True)
        return {"status": "ERROR", "message": str(e)}


async def _process_successful_payment(bill_code: str, tp_transaction_id: str = None):
    """
    Process a successful payment by updating the appropriate tables.

    Handles:
    - Subscription payments (new subscriptions, upgrades, renewals)
    - Addon purchases
    """
    from datetime import datetime, timedelta

    try:
        # Find the transaction by bill_code in the transactions table
        url = f"{settings.SUPABASE_URL}/rest/v1/transactions"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={"toyyibpay_bill_code": f"eq.{bill_code}"}
            )

        if response.status_code != 200:
            logger.error(f"Failed to find transaction for bill_code {bill_code}")
            return

        transactions = response.json()

        if not transactions:
            logger.warning(f"⚠️ No transaction found for bill_code: {bill_code}")
            # Try legacy payments table as fallback
            await _process_legacy_payment(bill_code, tp_transaction_id)
            return

        transaction = transactions[0]
        transaction_id = transaction.get("transaction_id")
        user_id = transaction.get("user_id")
        transaction_type = transaction.get("transaction_type")
        metadata = transaction.get("metadata", {})
        amount = transaction.get("amount")
        invoice_number = transaction.get("invoice_number")

        logger.info(f"📝 Found transaction: {transaction_id}")
        logger.info(f"   User: {user_id}")
        logger.info(f"   Type: {transaction_type}")
        logger.info(f"   Metadata: {metadata}")

        # Update transaction status to success (and ensure invoice number exists)
        patch_data = {
            "payment_status": "success",
            "toyyibpay_transaction_id": tp_transaction_id,
            "payment_date": datetime.utcnow().isoformat()
        }

        if not invoice_number:
            try:
                from app.services.subscription_service import subscription_service
                patch_data["invoice_number"] = await subscription_service.generate_invoice_number()
            except Exception as inv_err:
                logger.warning(f"Could not generate invoice number: {inv_err}")

        async with httpx.AsyncClient() as client:
            await client.patch(
                url,
                headers={**headers, "Prefer": "return=minimal"},
                params={"transaction_id": f"eq.{transaction_id}"},
                json=patch_data
            )

        logger.info(f"✅ Transaction {transaction_id} marked as success")

        # Process based on transaction type
        if transaction_type in ["subscription", "renewal"]:
            await _process_subscription_payment(user_id, metadata, bill_code)
        elif transaction_type == "addon":
            await _process_addon_payment(user_id, transaction_id, metadata)

    except Exception as e:
        logger.error(f"Error processing payment for bill_code {bill_code}: {e}", exc_info=True)


async def _process_subscription_payment(user_id: str, metadata: dict, bill_code: str):
    """Process a subscription or renewal payment."""
    from datetime import datetime, timedelta

    plan = metadata.get("plan", "starter")
    price = TIER_PRICES.get(plan, 5.00)

    logger.info(f"📝 Processing subscription payment for user {user_id}, plan: {plan}")

    try:
        url = f"{settings.SUPABASE_URL}/rest/v1/subscriptions"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        import httpx

        # Get current subscription
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={"user_id": f"eq.{user_id}"}
            )

        existing_sub = response.json() if response.status_code == 200 else []

        now = datetime.utcnow()

        # Calculate new end date
        if existing_sub:
            current_end = existing_sub[0].get("end_date")
            if current_end:
                try:
                    end_dt = datetime.fromisoformat(current_end.replace("Z", "+00:00"))
                    # If current subscription is still valid, extend from end date
                    if end_dt > now.replace(tzinfo=end_dt.tzinfo):
                        now = end_dt.replace(tzinfo=None)
                except:
                    pass

        new_end_date = now + timedelta(days=30)

        subscription_data = {
            "tier": plan,
            "status": "active",
            "start_date": datetime.utcnow().isoformat(),
            "end_date": new_end_date.isoformat(),
            "price": price,
            "toyyibpay_bill_code": bill_code,
            "auto_renew": True
        }

        async with httpx.AsyncClient() as client:
            if existing_sub:
                # Update existing subscription
                response = await client.patch(
                    url,
                    headers={**headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}"},
                    json=subscription_data
                )
            else:
                # Create new subscription
                subscription_data["user_id"] = user_id
                response = await client.post(
                    url,
                    headers={**headers, "Prefer": "return=minimal"},
                    json=subscription_data
                )

        if response.status_code in [200, 201, 204]:
            logger.info(f"✅ Subscription updated for user {user_id}: {plan} until {new_end_date}")

            # Reset monthly usage counters for the new billing period
            billing_period = datetime.utcnow().strftime("%Y-%m")
            usage_url = f"{settings.SUPABASE_URL}/rest/v1/usage_tracking"

            async with httpx.AsyncClient() as client:
                # Check if usage tracking exists for this period
                response = await client.get(
                    usage_url,
                    headers=headers,
                    params={
                        "user_id": f"eq.{user_id}",
                        "billing_period": f"eq.{billing_period}"
                    }
                )

                if response.status_code == 200 and not response.json():
                    # Create new usage tracking for this period
                    await client.post(
                        usage_url,
                        headers={**headers, "Prefer": "return=minimal"},
                        json={
                            "user_id": user_id,
                            "billing_period": billing_period,
                            "websites_count": 0,
                            "menu_items_count": 0,
                            "ai_hero_used": 0,
                            "ai_images_used": 0,
                            "delivery_zones_count": 0,
                            "riders_count": 0
                        }
                    )
                    logger.info(f"✅ Created new usage tracking for billing period {billing_period}")

            # Re-enable suspended websites if any
            websites_url = f"{settings.SUPABASE_URL}/rest/v1/websites"
            async with httpx.AsyncClient() as client:
                await client.patch(
                    websites_url,
                    headers={**headers, "Prefer": "return=minimal"},
                    params={
                        "user_id": f"eq.{user_id}",
                        "status": "eq.suspended"
                    },
                    json={"status": "published"}
                )
            logger.info(f"✅ Re-enabled suspended websites for user {user_id}")
        else:
            logger.error(f"❌ Failed to update subscription: {response.status_code}")

    except Exception as e:
        logger.error(f"Error processing subscription payment: {e}", exc_info=True)


async def _process_addon_payment(user_id: str, transaction_id: str, metadata: dict):
    """Process an addon purchase payment."""

    addon_type = metadata.get("addon_type")
    quantity = metadata.get("quantity", 1)
    unit_price = metadata.get("unit_price", ADDON_PRICES.get(addon_type, 0))
    total_price = unit_price * quantity

    logger.info(f"📝 Processing addon payment for user {user_id}: {addon_type} x{quantity}")

    try:
        url = f"{settings.SUPABASE_URL}/rest/v1/addon_purchases"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={**headers, "Prefer": "return=representation"},
                json={
                    "user_id": user_id,
                    "transaction_id": transaction_id,
                    "addon_type": addon_type,
                    "quantity": quantity,
                    "quantity_used": 0,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "status": "active"
                }
            )

        if response.status_code in [200, 201]:
            addon_record = response.json()
            logger.info(f"✅ Addon credits added for user {user_id}: {addon_type} x{quantity}")
            logger.info(f"   Addon ID: {addon_record[0].get('addon_id') if addon_record else 'N/A'}")
        else:
            logger.error(f"❌ Failed to create addon purchase: {response.status_code}")
            logger.error(f"   Response: {response.text}")

    except Exception as e:
        logger.error(f"Error processing addon payment: {e}", exc_info=True)


async def _update_transaction_status(bill_code: str, status: str):
    """Update transaction status by bill code."""
    try:
        url = f"{settings.SUPABASE_URL}/rest/v1/transactions"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        import httpx
        async with httpx.AsyncClient() as client:
            await client.patch(
                url,
                headers=headers,
                params={"toyyibpay_bill_code": f"eq.{bill_code}"},
                json={"payment_status": status}
            )

        logger.info(f"Updated transaction status for {bill_code} to {status}")
    except Exception as e:
        logger.error(f"Error updating transaction status: {e}")


async def _process_legacy_payment(bill_code: str, tp_transaction_id: str = None):
    """Fallback to process payment using legacy payments table."""
    try:
        # Query payments table by bill_code
        payment_records = await supabase_service.select_records("payments", {"bill_code": bill_code})

        if payment_records and len(payment_records) > 0:
            payment = payment_records[0]
            user_id = payment.get("user_id")
            tier = payment.get("tier")

            logger.info(f"📝 Found legacy payment record: user_id={user_id}, tier={tier}")

            if user_id and tier:
                # Update the payment record status
                await supabase_service.update_payment_status(payment.get("id"), "successful")

                # Upgrade user's subscription
                tier_price = TIER_PRICES.get(tier, 0)
                upgrade_success = await supabase_service.update_user_subscription(user_id, {
                    "tier": tier,
                    "status": "active",
                    "price": tier_price,
                    "toyyibpay_bill_code": bill_code
                })

                if upgrade_success:
                    logger.info(f"✅ Subscription upgraded for user {user_id} to {tier}")
                else:
                    logger.error(f"❌ Failed to upgrade subscription for user {user_id}")

                # Update usage limits based on tier
                await _update_usage_limits(user_id, tier)

        else:
            logger.warning(f"⚠️ No payment record found in legacy table for bill_code: {bill_code}")
            # Try addon_purchases table as a last resort (for old records with bill_code field)
            await _process_legacy_addon_payment(bill_code, tp_transaction_id)
    except Exception as db_error:
        logger.error(f"❌ Database error processing legacy payment: {db_error}")


async def _process_legacy_addon_payment(bill_code: str, tp_transaction_id: str = None):
    """
    Fallback to process addon payment from legacy addon_purchases records.
    These records were created with bill_code field instead of proper transaction records.
    """
    try:
        import httpx
        url = f"{settings.SUPABASE_URL}/rest/v1/addon_purchases"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

        # Look for addon_purchases with this bill_code that are still pending
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={
                    "bill_code": f"eq.{bill_code}",
                    "status": "eq.pending"
                }
            )

        if response.status_code != 200:
            logger.warning(f"⚠️ Failed to query addon_purchases for bill_code: {bill_code}")
            return

        records = response.json()

        if records and len(records) > 0:
            addon_record = records[0]
            addon_id = addon_record.get("addon_id") or addon_record.get("id")
            user_id = addon_record.get("user_id")
            addon_type = addon_record.get("addon_type")
            quantity = addon_record.get("quantity", 1)

            logger.info(f"📝 Found legacy addon_purchase record: addon_id={addon_id}, user={user_id}, type={addon_type}")

            # Update the addon_purchase status to active
            async with httpx.AsyncClient() as client:
                update_response = await client.patch(
                    url,
                    headers={**headers, "Prefer": "return=minimal"},
                    params={"bill_code": f"eq.{bill_code}"},
                    json={
                        "status": "active",
                        "quantity_used": 0
                    }
                )

            if update_response.status_code in [200, 204]:
                logger.info(f"✅ Legacy addon_purchase activated for user {user_id}: {addon_type} x{quantity}")
            else:
                logger.error(f"❌ Failed to update legacy addon_purchase: {update_response.status_code}")
        else:
            logger.warning(f"⚠️ No addon_purchase record found for bill_code: {bill_code}")

    except Exception as e:
        logger.error(f"❌ Error processing legacy addon payment: {e}", exc_info=True)


async def _update_usage_limits(user_id: str, tier: str):
    """Update user's usage limits based on their subscription tier"""
    try:
        # Define limits for each tier
        tier_limits = {
            "starter": {
                "websites_limit": 1,
                "menu_items_limit": 20,
                "ai_hero_limit": 1,
                "ai_menu_limit": 5,
                "delivery_zones_limit": 1,
                "riders_limit": 0
            },
            "basic": {
                "websites_limit": 5,
                "menu_items_limit": None,  # Unlimited
                "ai_hero_limit": 10,
                "ai_menu_limit": 30,
                "delivery_zones_limit": 5,
                "riders_limit": 0
            },
            "pro": {
                "websites_limit": None,  # Unlimited
                "menu_items_limit": None,
                "ai_hero_limit": None,
                "ai_menu_limit": None,
                "delivery_zones_limit": None,
                "riders_limit": 10
            }
        }

        limits = tier_limits.get(tier, tier_limits["starter"])

        # Try to update usage_limits table
        try:
            # First check if record exists
            existing = await supabase_service.select_records("usage_limits", {"user_id": user_id})

            if existing and len(existing) > 0:
                # Update existing record
                url = f"{supabase_service.url}/rest/v1/usage_limits"
                params = {"user_id": f"eq.{user_id}"}

                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.patch(
                        url,
                        headers={**supabase_service.service_headers, "Prefer": "return=minimal"},
                        params=params,
                        json=limits
                    )

                if response.status_code in [200, 204]:
                    logger.info(f"✅ Updated usage limits for user {user_id}")
                else:
                    logger.warning(f"⚠️ Failed to update usage limits: {response.status_code}")
            else:
                # Create new record
                limits["user_id"] = user_id
                await supabase_service.insert_record("usage_limits", limits)
                logger.info(f"✅ Created usage limits for user {user_id}")

        except Exception as limits_error:
            logger.warning(f"⚠️ Could not update usage_limits table: {limits_error}")

    except Exception as e:
        logger.error(f"❌ Error updating usage limits: {e}")


@router.get("/toyyibpay/verify/{bill_code}")
async def verify_toyyibpay_payment(bill_code: str):
    """
    Verify payment status for a ToyyibPay bill
    Also processes the payment if successful but not yet processed
    """
    try:
        logger.info(f"🔍 Verifying payment for bill_code: {bill_code}")

        # Get transactions from ToyyibPay
        result = toyyibpay_service.get_bill_transactions(bill_code)

        if not result.get("success"):
            return result

        transactions = result.get("transactions", [])

        # Check if any transaction is successful (status == "1")
        payment_successful = False
        transaction_details = None

        for txn in transactions:
            if txn.get("billpaymentStatus") == "1":
                payment_successful = True
                transaction_details = txn
                break

        if payment_successful:
            logger.info(f"✅ Payment verified as successful for bill: {bill_code}")

            # Try to process the payment using new transactions table
            import httpx
            try:
                url = f"{settings.SUPABASE_URL}/rest/v1/transactions"
                headers = {
                    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json"
                }

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers=headers,
                        params={"toyyibpay_bill_code": f"eq.{bill_code}"}
                    )

                if response.status_code == 200:
                    tx_records = response.json()

                    if tx_records and len(tx_records) > 0:
                        tx = tx_records[0]

                        # If transaction is still pending, process it now
                        if tx.get("payment_status") == "pending":
                            logger.info(f"📝 Processing pending transaction: {tx.get('transaction_id')}")

                            # Process the successful payment
                            await _process_successful_payment(
                                bill_code,
                                transaction_details.get("billpaymentInvoiceNo")
                            )

                        return {
                            "success": True,
                            "status": "paid",
                            "bill_code": bill_code,
                            "transaction_type": tx.get("transaction_type"),
                            "amount": float(tx.get("amount", 0)),
                            "metadata": tx.get("metadata"),
                            "transaction": transaction_details
                        }

            except Exception as tx_error:
                logger.warning(f"⚠️ Could not check transactions table: {tx_error}")

            # Fallback to legacy payments table
            try:
                payment_records = await supabase_service.select_records("payments", {"bill_code": bill_code})

                if payment_records and len(payment_records) > 0:
                    payment = payment_records[0]

                    # If payment is still pending, process it now
                    if payment.get("status") == "pending":
                        user_id = payment.get("user_id")
                        tier = payment.get("tier")

                        logger.info(f"📝 Processing pending legacy payment: user_id={user_id}, tier={tier}")

                        if user_id and tier:
                            # Update payment status
                            await supabase_service.update_payment_status(payment.get("id"), "successful")

                            # Upgrade subscription
                            tier_price = TIER_PRICES.get(tier, 0)
                            await supabase_service.update_user_subscription(user_id, {
                                "tier": tier,
                                "status": "active",
                                "price": tier_price,
                                "toyyibpay_bill_code": bill_code
                            })

                            # Update usage limits
                            await _update_usage_limits(user_id, tier)

                            logger.info(f"✅ Late payment processing completed for user {user_id}")

                    return {
                        "success": True,
                        "status": "paid",
                        "bill_code": bill_code,
                        "tier": payment.get("tier"),
                        "amount": float(payment.get("amount", 0)),
                        "transaction": transaction_details
                    }

            except Exception as db_error:
                logger.warning(f"⚠️ Could not check/update legacy payment record: {db_error}")

            return {
                "success": True,
                "status": "paid",
                "bill_code": bill_code,
                "transaction": transaction_details
            }

        else:
            # Check for pending transactions
            has_pending = any(txn.get("billpaymentStatus") == "2" for txn in transactions)

            return {
                "success": True,
                "status": "pending" if has_pending else "unpaid",
                "bill_code": bill_code,
                "transactions": transactions
            }

    except Exception as e:
        logger.error(f"Error verifying ToyyibPay payment: {e}", exc_info=True)
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
    "ai_image": 1.00,
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

        # Get user phone from database or use default
        user_phone = '0123456789'  # Default Malaysian phone format
        customer_name = email.split('@')[0] if email else 'Customer'

        if user_data:
            if user_data.get('phone'):
                user_phone = user_data.get('phone')
            if user_data.get('name'):
                customer_name = user_data.get('name')
            elif user_data.get('full_name'):
                customer_name = user_data.get('full_name')

        logger.info(f"📝 Creating subscription payment:")
        logger.info(f"   Tier: {tier}")
        logger.info(f"   Price: RM{price}")
        logger.info(f"   Email: {email}")
        logger.info(f"   Phone: {user_phone}")
        logger.info(f"   Name: {customer_name}")
        logger.info(f"   Ref: {external_ref}")

        # Create ToyyibPay bill
        result = toyyibpay_service.create_bill(
            bill_name=f"BinaApp {tier.upper()} Plan",
            bill_description=f"Langganan bulanan BinaApp {tier.upper()}",
            bill_amount=price,
            bill_email=email,
            bill_phone=user_phone,
            bill_name_customer=customer_name,
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

        # Get user phone from database or use default
        user_phone = '0123456789'  # Default Malaysian phone format
        customer_name = email.split('@')[0] if email else 'Customer'

        if user_data:
            if user_data.get('phone'):
                user_phone = user_data.get('phone')
            if user_data.get('name'):
                customer_name = user_data.get('name')
            elif user_data.get('full_name'):
                customer_name = user_data.get('full_name')

        logger.info(f"📝 Creating addon purchase:")
        logger.info(f"   Addon: {addon_type} x{quantity}")
        logger.info(f"   Price: RM{total_price}")
        logger.info(f"   Email: {email}")
        logger.info(f"   Phone: {user_phone}")

        # Create ToyyibPay bill
        result = toyyibpay_service.create_bill(
            bill_name=f"BinaApp Addon {addon_type}",
            bill_description=f"Pembelian {quantity}x {addon_type}",
            bill_amount=total_price,
            bill_email=email,
            bill_phone=user_phone,
            bill_name_customer=customer_name,
            bill_external_reference_no=external_ref
        )

        if result.get("success"):
            bill_code = result.get("bill_code")
            logger.info(f"ToyyibPay addon bill created: {bill_code}")

            # CRITICAL: Create transaction record so callback handler can find it
            # The callback handler looks for transactions by toyyibpay_bill_code
            transaction_id = None
            try:
                from app.services.subscription_service import subscription_service
                invoice_number = await subscription_service.generate_invoice_number()

                transaction_records = await supabase_service.insert_record("transactions", {
                    "user_id": str(user_id),
                    "transaction_type": "addon",
                    "item_description": f"{addon_type} x{quantity}",
                    "amount": total_price,
                    "toyyibpay_bill_code": bill_code,
                    "payment_status": "pending",
                    "invoice_number": invoice_number,
                    "metadata": {
                        "addon_type": addon_type,
                        "quantity": quantity,
                        "unit_price": unit_price
                    }
                })
                if transaction_records and len(transaction_records) > 0:
                    transaction_id = transaction_records[0].get("transaction_id")
                    logger.info(f"✅ Transaction record created: {transaction_id}")
            except Exception as db_error:
                logger.error(f"❌ Failed to create transaction record: {db_error}")
                # Still continue - the payment might work via legacy fallback

            logger.info(f"Addon purchase created for user {user_id[:8]}: {addon_type} x{quantity}")

            return {
                "success": True,
                "transaction_id": transaction_id,
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
