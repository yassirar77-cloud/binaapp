"""
Tests for the 2-tier pricing lineup and free AI images.

Product decisions covered:
1. Basic (RM29) is retired from sale: hidden from pricing UIs
   (is_public=False on /plans) and new purchases are rejected — but the tier
   itself stays defined so grandfathered subscribers keep their plan, price
   display, limits, and renewals.
2. AI images are free product-wide: ai_image / ai_hero addons are removed
   from the catalog and new purchases are rejected, while already-purchased
   credits remain consumable and check_limit stops advertising a purchase it
   would reject.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import HTTPException

from app.services.subscription_service import SubscriptionService, subscription_service

FAKE_USER = {"sub": "user-abc-123", "email": "buyer@example.com"}


class TestLineupConstants:
    def test_basic_not_purchasable_but_still_defined(self):
        assert "basic" not in SubscriptionService.PURCHASABLE_TIERS
        # Grandfathering: pricing/limits stay defined for existing subscribers.
        assert SubscriptionService.TIER_PRICES["basic"] == 29.00
        assert "basic" in SubscriptionService.TIER_LIMITS

    def test_starter_and_pro_purchasable(self):
        assert SubscriptionService.PURCHASABLE_TIERS == {"starter", "pro"}

    def test_ai_addons_discontinued_but_priced(self):
        assert SubscriptionService.DISCONTINUED_ADDONS == {"ai_image", "ai_hero"}
        # Prices stay so existing purchased credits keep their recorded value.
        assert "ai_image" in SubscriptionService.ADDON_PRICES
        assert "ai_hero" in SubscriptionService.ADDON_PRICES


class TestPlansEndpoint:
    @pytest.mark.asyncio
    async def test_basic_marked_not_public(self):
        """/plans still returns basic (grandfathered display) but flags it
        is_public=False so pricing UIs hide it."""
        from app.api.v1.endpoints.subscription import get_subscription_plans

        fallback = [
            {"plan_name": "starter", "display_name": "Starter", "price": 5.00},
            {"plan_name": "basic", "display_name": "Basic", "price": 29.00},
            {"plan_name": "pro", "display_name": "Pro", "price": 49.00},
        ]
        with patch(
            "app.api.v1.endpoints.subscription.subscription_service.get_subscription_plans",
            AsyncMock(return_value=fallback),
        ):
            result = await get_subscription_plans()

        by_name = {p["plan_name"]: p for p in result["plans"]}
        assert by_name["starter"]["is_public"] is True
        assert by_name["pro"]["is_public"] is True
        assert by_name["basic"]["is_public"] is False

    @pytest.mark.asyncio
    async def test_no_plan_advertises_paid_ai_images(self):
        """Feature lists say AI images are free — no '<N> imej AI' counts."""
        from app.api.v1.endpoints.subscription import get_subscription_plans

        fallback = [
            {"plan_name": "starter", "display_name": "Starter", "price": 5.00},
            {"plan_name": "basic", "display_name": "Basic", "price": 29.00},
            {"plan_name": "pro", "display_name": "Pro", "price": 49.00},
        ]
        with patch(
            "app.api.v1.endpoints.subscription.subscription_service.get_subscription_plans",
            AsyncMock(return_value=fallback),
        ):
            result = await get_subscription_plans()

        for plan in result["plans"]:
            features = " | ".join(plan["feature_list"]).lower()
            assert "imej ai percuma" in features
            for stale in ("5 imej ai", "30 imej ai", "imej ai/bulan"):
                assert stale not in features


class TestAddonCatalog:
    @pytest.mark.asyncio
    async def test_ai_addons_not_listed(self):
        from app.api.v1.endpoints.subscription import get_available_addons

        result = await get_available_addons()
        types = {a["type"] for a in result["addons"]}
        assert "ai_image" not in types
        assert "ai_hero" not in types
        # The operational addons are still sold.
        assert {"website", "rider", "zone"} <= types


def _purchase_patches():
    """Patch out network calls made by subscription.purchase_addon (only
    reached when validation passes)."""
    base = "app.api.v1.endpoints.subscription"
    bill = {"success": True, "bill_code": "B1", "payment_url": "https://pay.test/B1"}
    return [
        patch(f"{base}.toyyibpay_service.create_bill", MagicMock(return_value=bill)),
        patch(f"{base}.supabase_service.get_user_by_id", AsyncMock(return_value={})),
        patch(
            f"{base}.supabase_service.insert_record",
            AsyncMock(return_value={"transaction_id": "tx-1"}),
        ),
        patch(
            f"{base}.subscription_service.generate_invoice_number",
            AsyncMock(return_value="INV-20260716-0001"),
        ),
    ]


class TestAddonPurchaseRejection:
    @pytest.mark.asyncio
    async def test_subscription_endpoint_rejects_ai_image(self):
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        with pytest.raises(HTTPException) as exc:
            await purchase_addon(
                AddonPurchaseRequest(addon_type="ai_image", quantity=1), FAKE_USER
            )
        assert exc.value.status_code == 400
        assert "percuma" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_subscription_endpoint_rejects_ai_hero(self):
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        with pytest.raises(HTTPException) as exc:
            await purchase_addon(
                AddonPurchaseRequest(addon_type="ai_hero", quantity=1), FAKE_USER
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_subscription_endpoint_still_sells_rider(self):
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        patches = _purchase_patches()
        with patches[0] as create_bill, patches[1], patches[2], patches[3]:
            result = await purchase_addon(
                AddonPurchaseRequest(addon_type="rider", quantity=2), FAKE_USER
            )

        assert result["success"] is True
        assert create_bill.call_args.kwargs["bill_amount"] == 6.00  # 2 x RM3

    @pytest.mark.asyncio
    async def test_payments_endpoint_rejects_ai_image(self):
        from app.api.v1.endpoints.payments import purchase_addon, AddonPurchaseRequest

        with patch("app.api.v1.endpoints.payments.settings") as mock_settings:
            mock_settings.EMAIL_VERIFICATION_ENABLED = False
            with pytest.raises(HTTPException) as exc:
                await purchase_addon(
                    AddonPurchaseRequest(
                        user_id="user-abc-123", addon_type="ai_image", quantity=5
                    )
                )
        assert exc.value.status_code == 400


class TestBasicPurchaseRejection:
    @pytest.mark.asyncio
    async def test_upgrade_to_basic_rejected(self):
        from app.api.v1.endpoints.subscription import upgrade_subscription, UpgradeRequest

        # Current plan lookup must not matter — basic is rejected before any
        # network call.
        with patch(
            "app.api.v1.endpoints.subscription.subscription_service.get_subscription_status",
            AsyncMock(return_value={"plan_name": "starter"}),
        ):
            with pytest.raises(HTTPException) as exc:
                await upgrade_subscription(
                    UpgradeRequest(new_plan="basic", prorate=False), FAKE_USER
                )
        assert exc.value.status_code == 400
        assert "tidak lagi ditawarkan" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_upgrade_to_pro_still_allowed(self):
        """Pro upgrades pass validation and reach bill creation."""
        from app.api.v1.endpoints.subscription import upgrade_subscription, UpgradeRequest

        base = "app.api.v1.endpoints.subscription"
        bill = {"success": True, "bill_code": "B2", "payment_url": "https://pay.test/B2"}
        with patch(
            f"{base}.subscription_service.get_subscription_status",
            AsyncMock(return_value={"plan_name": "starter"}),
        ), patch(
            f"{base}.supabase_service.get_user_by_id", AsyncMock(return_value={})
        ), patch(
            f"{base}.toyyibpay_service.create_bill", MagicMock(return_value=bill)
        ) as create_bill, patch(
            f"{base}.supabase_service.insert_record",
            AsyncMock(return_value={"transaction_id": "tx-2"}),
        ), patch(
            f"{base}.subscription_service.generate_invoice_number",
            AsyncMock(return_value="INV-20260716-0002"),
        ):
            result = await upgrade_subscription(
                UpgradeRequest(new_plan="pro", prorate=False), FAKE_USER
            )

        assert result["success"] is True
        assert create_bill.call_args.kwargs["bill_amount"] == 49.00

    @pytest.mark.asyncio
    async def test_subscribe_endpoint_rejects_basic(self):
        from app.api.v1.endpoints.payments import create_subscription_payment, SubscriptionRequest

        with patch("app.api.v1.endpoints.payments.settings") as mock_settings:
            mock_settings.EMAIL_VERIFICATION_ENABLED = False
            with pytest.raises(HTTPException) as exc:
                await create_subscription_payment(
                    "basic", SubscriptionRequest(user_id="user-abc-123")
                )
        assert exc.value.status_code == 400
        assert "tidak lagi ditawarkan" in exc.value.detail.lower()


class TestCheckLimitFreeImages:
    """check_limit for AI images must never advertise a purchase the
    purchase endpoints would reject — but existing credits stay usable."""

    def _service(self):
        return subscription_service

    def _limit_patches(self, svc, limits, usage, credits):
        return [
            patch.object(svc, "_is_admin", AsyncMock(return_value=False)),
            patch.object(svc, "get_user_limits", AsyncMock(return_value=limits)),
            patch.object(svc, "get_or_create_usage_tracking", AsyncMock(return_value=usage)),
            patch.object(
                svc, "get_subscription_status",
                AsyncMock(return_value={"plan_name": "starter", "is_expired": False}),
            ),
            patch.object(svc, "get_available_addon_credits", AsyncMock(return_value=credits)),
        ]

    @pytest.mark.asyncio
    async def test_at_limit_no_addon_upsell(self):
        svc = self._service()
        patches = self._limit_patches(
            svc,
            limits={"ai_images_limit": 5},
            usage={"ai_images_used": 5},
            credits={"ai_image": 0},
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = await svc.check_limit("user-x", "generate_ai_image")

        assert result["allowed"] is False
        assert result["can_buy_addon"] is False
        assert "reset" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_existing_credits_still_consumable(self):
        """A user who bought ai_image credits before the retirement can still
        use them past the plan limit."""
        svc = self._service()
        patches = self._limit_patches(
            svc,
            limits={"ai_images_limit": 5},
            usage={"ai_images_used": 5},
            credits={"ai_image": 3},
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = await svc.check_limit("user-x", "generate_ai_image")

        assert result["allowed"] is True
        assert result["using_addon"] is True

    @pytest.mark.asyncio
    async def test_rider_limit_still_offers_addon(self):
        """Non-retired addons keep the buy-addon upsell."""
        svc = self._service()
        patches = self._limit_patches(
            svc,
            limits={"riders_limit": 10},
            usage={"riders_count": 10},
            credits={"rider": 0},
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = await svc.check_limit("user-x", "add_rider")

        assert result["allowed"] is False
        assert result["can_buy_addon"] is True
        assert result["addon_type"] == "rider"
