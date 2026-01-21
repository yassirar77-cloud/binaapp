"""
Payment Service - Stripe Integration
Handles subscriptions and payments
"""

import stripe
from typing import Dict, Optional
from loguru import logger

from app.core.config import settings
from app.models.schemas import SubscriptionTier


class PaymentService:
    """Service for Stripe payment operations"""

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        logger.info("Stripe payment service initialized")

    # Subscription Plans Configuration (BinaApp pricing)
    PLANS = {
        SubscriptionTier.STARTER: {
            "name": "Starter",
            "price_monthly": 5.00,
            "price_yearly": 50.00,  # 2 months free
            "features": [
                "1 website",
                "20 menu items",
                "1 AI hero generation (lifetime)",
                "5 AI menu images (lifetime)",
                "1 delivery zone",
                "Subdomain hosting",
                "WhatsApp integration"
            ],
            "max_websites": 1,
            "stripe_price_id_monthly": None,  # Using ToyyibPay instead
            "stripe_price_id_yearly": None
        },
        SubscriptionTier.BASIC: {
            "name": "Basic",
            "price_monthly": 29.00,
            "price_yearly": 290.00,  # 2 months free
            "features": [
                "5 websites",
                "Unlimited menu items",
                "10 AI hero generations/month",
                "30 AI menu images/month",
                "5 delivery zones",
                "Priority support",
                "Analytics"
            ],
            "max_websites": 5,
            "stripe_price_id_monthly": "price_basic_monthly",
            "stripe_price_id_yearly": "price_basic_yearly"
        },
        SubscriptionTier.PRO: {
            "name": "Pro",
            "price_monthly": 49.00,
            "price_yearly": 490.00,  # 2 months free
            "features": [
                "Unlimited websites",
                "Unlimited menu items",
                "Unlimited AI hero generations",
                "Unlimited AI menu images",
                "Unlimited delivery zones",
                "10 riders",
                "Priority support",
                "Advanced analytics",
                "Custom domain support"
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
            if tier == SubscriptionTier.STARTER:
                raise ValueError("Cannot create checkout session for starter tier")

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
        Handle Stripe webhook events
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )

            logger.info(f"Received Stripe webhook: {event['type']}")

            # Handle different event types
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                await self._handle_checkout_completed(session)

            elif event['type'] == 'customer.subscription.updated':
                subscription = event['data']['object']
                await self._handle_subscription_updated(subscription)

            elif event['type'] == 'customer.subscription.deleted':
                subscription = event['data']['object']
                await self._handle_subscription_cancelled(subscription)

            elif event['type'] == 'invoice.payment_failed':
                invoice = event['data']['object']
                await self._handle_payment_failed(invoice)

            return {'status': 'success'}

        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise

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
        # For now, return True for starter tier
        if tier == SubscriptionTier.STARTER:
            return True

        # Check with Supabase
        from app.services.supabase_client import supabase_service
        subscription = await supabase_service.get_user_subscription(user_id)

        return subscription and subscription.get('status') == 'active' and subscription.get('tier') == tier


# Create singleton instance
payment_service = PaymentService()
