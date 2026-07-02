"""
Payment Service - Stripe Integration
Handles subscriptions and payments
"""

import stripe
from typing import Dict
from loguru import logger

from app.core.config import settings
from app.models.schemas import SubscriptionTier


class PaymentService:
    """Service for Stripe payment operations"""

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        logger.info("Stripe payment service initialized")

    # Subscription Plans Configuration
    PLANS = {
        SubscriptionTier.FREE: {
            "name": "Free",
            "price_monthly": 0,
            "price_yearly": 0,
            "features": [
                "1 website",
                "Basic templates",
                "AI generation",
                "Subdomain hosting",
                "WhatsApp integration",
                "Contact forms"
            ],
            "max_websites": 1,
            "stripe_price_id_monthly": None,
            "stripe_price_id_yearly": None
        },
        SubscriptionTier.BASIC: {
            "name": "Basic",
            "price_monthly": 29.00,
            "price_yearly": 290.00,
            "features": [
                "5 websites",
                "All templates",
                "Priority AI generation",
                "Custom subdomain",
                "All integrations",
                "Email support",
                "Analytics"
            ],
            "max_websites": 5,
            "stripe_price_id_monthly": "price_basic_monthly",  # Replace with actual Stripe price ID
            "stripe_price_id_yearly": "price_basic_yearly"
        },
        SubscriptionTier.PRO: {
            "name": "Pro",
            "price_monthly": 49.00,
            "price_yearly": 490.00,
            "features": [
                "Unlimited websites",
                "Premium templates",
                "Advanced AI features",
                "Priority support",
                "Advanced analytics",
                "10 rider GPS tracking",
                "Custom subdomain"
            ],
            "max_websites": -1,  # Unlimited
            "stripe_price_id_monthly": "price_pro_monthly",
            "stripe_price_id_yearly": "price_pro_yearly"
        }
    }

    async def create_checkout_session(
        self,
        user_id: str,
        email: str,
        tier: SubscriptionTier,
        billing_period: str
    ) -> Dict:
        """
        Create Stripe checkout session for subscription
        """
        try:
            if tier == SubscriptionTier.FREE:
                raise ValueError("Cannot create checkout session for free tier")

            plan = self.PLANS[tier]

            # Select price ID based on billing period
            price_id = (
                plan["stripe_price_id_monthly"]
                if billing_period == "monthly"
                else plan["stripe_price_id_yearly"]
            )

            # Create checkout session
            session = stripe.checkout.Session.create(
                customer_email=email,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{settings.BASE_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.BASE_URL}/pricing",
                metadata={
                    'user_id': user_id,
                    'tier': tier,
                    'billing_period': billing_period
                }
            )

            logger.info(f"Checkout session created for user {user_id}: {session.id}")

            return {
                'session_id': session.id,
                'checkout_url': session.url
            }

        except Exception as e:
            logger.error(f"Error creating checkout session: {e}")
            raise

    async def handle_webhook(self, payload: bytes, sig_header: str) -> Dict:
        """
        DISABLED (audit C2). Stripe webhooks are not used — BinaApp bills via
        ToyyibPay. This method previously called stripe.Webhook.construct_event
        with STRIPE_WEBHOOK_SECRET, which defaults to "" and therefore accepted a
        forged signature, letting anyone grant a free subscription via
        metadata.user_id/tier. The HTTP route has been removed; this method is
        kept only so nothing that still imports it crashes, and hard-fails
        instead of granting anything.
        """
        logger.error("Stripe webhook handling is disabled (ToyyibPay is the only gateway).")
        raise RuntimeError("Stripe webhooks are disabled")

    async def _handle_checkout_completed(self, session: Dict):
        """Handle successful checkout"""
        user_id = session['metadata']['user_id']
        tier = session['metadata']['tier']

        logger.info(f"Checkout completed for user {user_id}, tier: {tier}")

        # Update user subscription in database
        # This would be handled by supabase_service
        from app.services.supabase_client import supabase_service

        await supabase_service.update_subscription(user_id, {
            'tier': tier,
            'stripe_customer_id': session.get('customer'),
            'stripe_subscription_id': session.get('subscription'),
            'status': 'active'
        })

    async def _handle_subscription_updated(self, subscription: Dict):
        """Handle subscription updates"""
        logger.info(f"Subscription updated: {subscription['id']}")
        # Update subscription status in database

    async def _handle_subscription_cancelled(self, subscription: Dict):
        """Handle subscription cancellation"""
        logger.info(f"Subscription cancelled: {subscription['id']}")
        # Update subscription status to cancelled

    async def _handle_payment_failed(self, invoice: Dict):
        """Handle failed payment"""
        logger.warning(f"Payment failed for invoice: {invoice['id']}")
        # Notify user about failed payment

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancel a subscription
        """
        try:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"Subscription cancelled: {subscription_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False

    async def get_subscription_plans(self) -> Dict:
        """
        Get all available subscription plans
        """
        return self.PLANS

    async def verify_subscription(self, user_id: str, tier: SubscriptionTier) -> bool:
        """
        Verify if user has active subscription for given tier
        """
        # This would check database and Stripe
        # For now, return True for free tier
        if tier == SubscriptionTier.FREE:
            return True

        # Check with Supabase
        from app.services.supabase_client import supabase_service
        subscription = await supabase_service.get_user_subscription(user_id)

        return subscription and subscription.get('status') == 'active' and subscription.get('tier') == tier


# Create singleton instance
payment_service = PaymentService()
