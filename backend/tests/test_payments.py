"""
Tests for payment_service.py — Stripe integration.

All Stripe API calls are mocked. Tests verify:
- Plan configuration accuracy
- Checkout session creation logic
- Webhook handling (signature verification, event routing)
- Subscription lifecycle (complete, update, cancel, payment failure)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.models.schemas import SubscriptionTier


class TestPlanConfiguration:
    def test_free_plan_has_zero_price(self):
        from app.services.payment_service import PaymentService

        service = PaymentService()
        free = service.PLANS[SubscriptionTier.FREE]
        assert free["price_monthly"] == 0
        assert free["price_yearly"] == 0
        assert free["max_websites"] == 1

    def test_basic_plan_pricing(self):
        from app.services.payment_service import PaymentService

        service = PaymentService()
        basic = service.PLANS[SubscriptionTier.BASIC]
        assert basic["price_monthly"] == 29.00
        assert basic["price_yearly"] == 290.00
        assert basic["max_websites"] == 5

    def test_pro_plan_unlimited_websites(self):
        from app.services.payment_service import PaymentService

        service = PaymentService()
        pro = service.PLANS[SubscriptionTier.PRO]
        assert pro["max_websites"] == -1  # Unlimited

    def test_all_tiers_have_required_fields(self):
        from app.services.payment_service import PaymentService

        service = PaymentService()
        required_fields = {"name", "price_monthly", "price_yearly", "features", "max_websites"}
        for tier, plan in service.PLANS.items():
            for field in required_fields:
                assert field in plan, f"Plan {tier} missing field: {field}"

    def test_yearly_price_is_discount(self):
        """Yearly price should be less than 12x monthly (i.e., a discount)."""
        from app.services.payment_service import PaymentService

        service = PaymentService()
        for tier, plan in service.PLANS.items():
            if plan["price_monthly"] > 0:
                assert plan["price_yearly"] < plan["price_monthly"] * 12, (
                    f"Plan {tier} yearly is not cheaper than 12x monthly"
                )


class TestCheckoutSession:
    @pytest.mark.asyncio
    async def test_free_tier_raises_error(self):
        from app.services.payment_service import PaymentService

        service = PaymentService()
        with pytest.raises(ValueError, match="free tier"):
            await service.create_checkout_session(
                user_id="user-1",
                email="test@example.com",
                tier=SubscriptionTier.FREE,
                billing_period="monthly",
            )

    @pytest.mark.asyncio
    @patch("stripe.checkout.Session.create")
    async def test_basic_monthly_checkout(self, mock_stripe_create):
        from app.services.payment_service import PaymentService

        mock_stripe_create.return_value = MagicMock(
            id="cs_test_123",
            url="https://checkout.stripe.com/test",
        )

        service = PaymentService()
        result = await service.create_checkout_session(
            user_id="user-1",
            email="test@example.com",
            tier=SubscriptionTier.BASIC,
            billing_period="monthly",
        )

        assert result["session_id"] == "cs_test_123"
        assert result["checkout_url"] == "https://checkout.stripe.com/test"
        mock_stripe_create.assert_called_once()

        call_kwargs = mock_stripe_create.call_args
        assert call_kwargs.kwargs["metadata"]["user_id"] == "user-1"
        assert call_kwargs.kwargs["mode"] == "subscription"

    @pytest.mark.asyncio
    @patch("stripe.checkout.Session.create")
    async def test_pro_yearly_checkout(self, mock_stripe_create):
        from app.services.payment_service import PaymentService

        mock_stripe_create.return_value = MagicMock(
            id="cs_test_456",
            url="https://checkout.stripe.com/yearly",
        )

        service = PaymentService()
        result = await service.create_checkout_session(
            user_id="user-2",
            email="pro@example.com",
            tier=SubscriptionTier.PRO,
            billing_period="yearly",
        )

        assert result["session_id"] == "cs_test_456"
        call_kwargs = mock_stripe_create.call_args
        assert call_kwargs.kwargs["line_items"][0]["price"] == "price_pro_yearly"


class TestWebhookHandling:
    @pytest.mark.asyncio
    @patch("stripe.Webhook.construct_event")
    async def test_checkout_completed_event(self, mock_construct):
        from app.services.payment_service import PaymentService

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"user_id": "user-1", "tier": "basic"},
                    "customer": "cus_123",
                    "subscription": "sub_123",
                }
            },
        }

        service = PaymentService()
        with patch.object(service, "_handle_checkout_completed", new_callable=AsyncMock) as mock_handler:
            result = await service.handle_webhook(b"payload", "sig_header")
            assert result["status"] == "success"
            mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("stripe.Webhook.construct_event")
    async def test_subscription_deleted_event(self, mock_construct):
        from app.services.payment_service import PaymentService

        mock_construct.return_value = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_123"}},
        }

        service = PaymentService()
        with patch.object(service, "_handle_subscription_cancelled", new_callable=AsyncMock) as mock_handler:
            result = await service.handle_webhook(b"payload", "sig_header")
            assert result["status"] == "success"
            mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("stripe.Webhook.construct_event")
    async def test_payment_failed_event(self, mock_construct):
        from app.services.payment_service import PaymentService

        mock_construct.return_value = {
            "type": "invoice.payment_failed",
            "data": {"object": {"id": "inv_123"}},
        }

        service = PaymentService()
        with patch.object(service, "_handle_payment_failed", new_callable=AsyncMock) as mock_handler:
            result = await service.handle_webhook(b"payload", "sig_header")
            mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("stripe.Webhook.construct_event")
    async def test_invalid_signature_raises(self, mock_construct):
        import stripe

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "sig_header"
        )

        from app.services.payment_service import PaymentService

        service = PaymentService()
        with pytest.raises(stripe.error.SignatureVerificationError):
            await service.handle_webhook(b"bad_payload", "bad_sig")
