"""
Free (preview-only) plan must not be sold add-ons it cannot use.

A founder on a Free-plan test account bought a RM5 website slot and a RM5
hero video credit, read the receipts as the RM5/month Starter plan, and
then hit the "Upgrade to Starter to publish" sheet. Website slots and hero
video clips only make sense on a plan that can publish to a subdomain, so:

- both add-on purchase endpoints refuse them on a plan without
  can_publish_subdomain and point at the Starter upgrade;
- check_limit("create_website") on such a plan says requires_upgrade
  instead of offering the add-on;
- hero_video_access reports requires_upgrade so the UI offers the upgrade
  instead of a credit purchase (existing credits stay usable).
"""

import pytest
from unittest.mock import patch, AsyncMock

from fastapi import HTTPException

from app.services import plan_features
from app.services.subscription_service import subscription_service

FAKE_USER = {"sub": "user-free-1", "email": "free@example.com"}


class TestAddonRequiresPaidPlan:
    @pytest.mark.asyncio
    async def test_website_and_hero_video_gated_on_free(self):
        with patch.object(plan_features, "can_publish_subdomain", AsyncMock(return_value=False)):
            assert await plan_features.addon_requires_paid_plan("u", "website") is True
            assert await plan_features.addon_requires_paid_plan("u", "hero_video") is True

    @pytest.mark.asyncio
    async def test_other_addons_never_consult_the_plan(self):
        with patch.object(
            plan_features, "can_publish_subdomain",
            AsyncMock(side_effect=AssertionError("plan looked up for a non-gated addon")),
        ):
            assert await plan_features.addon_requires_paid_plan("u", "zone") is False
            assert await plan_features.addon_requires_paid_plan("u", "rider") is False

    @pytest.mark.asyncio
    async def test_paid_plan_passes(self):
        with patch.object(plan_features, "can_publish_subdomain", AsyncMock(return_value=True)):
            assert await plan_features.addon_requires_paid_plan("u", "website") is False


class TestPurchaseEndpointsRefuseOnFree:
    @pytest.mark.asyncio
    async def test_subscription_endpoint_rejects_website_slot_on_free(self):
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        with patch.object(plan_features, "can_publish_subdomain", AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc:
                await purchase_addon(
                    AddonPurchaseRequest(addon_type="website", quantity=1), FAKE_USER
                )
        assert exc.value.status_code == 403
        assert "starter" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_subscription_endpoint_rejects_hero_video_on_free(self):
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        with patch.object(plan_features, "can_publish_subdomain", AsyncMock(return_value=False)):
            with pytest.raises(HTTPException) as exc:
                await purchase_addon(
                    AddonPurchaseRequest(addon_type="hero_video", quantity=1), FAKE_USER
                )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_payments_endpoint_rejects_website_slot_on_free(self):
        from app.api.v1.endpoints.payments import purchase_addon, AddonPurchaseRequest

        with patch("app.api.v1.endpoints.payments.settings") as mock_settings, patch.object(
            plan_features, "can_publish_subdomain", AsyncMock(return_value=False)
        ):
            mock_settings.EMAIL_VERIFICATION_ENABLED = False
            with pytest.raises(HTTPException) as exc:
                await purchase_addon(
                    AddonPurchaseRequest(user_id="user-free-1", addon_type="website", quantity=1)
                )
        assert exc.value.status_code == 403
        assert "starter" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_payments_endpoint_rejects_hero_video_on_free(self):
        from app.api.v1.endpoints.payments import purchase_addon, AddonPurchaseRequest

        with patch("app.api.v1.endpoints.payments.settings") as mock_settings, patch.object(
            plan_features, "can_publish_subdomain", AsyncMock(return_value=False)
        ):
            mock_settings.EMAIL_VERIFICATION_ENABLED = False
            with pytest.raises(HTTPException) as exc:
                await purchase_addon(
                    AddonPurchaseRequest(user_id="user-free-1", addon_type="hero_video", quantity=1)
                )
        assert exc.value.status_code == 403


class TestCheckLimitOnFreePlan:
    def _patches(self, can_publish: bool):
        svc = subscription_service
        return (
            patch.object(svc, "_is_admin", AsyncMock(return_value=False)),
            patch.object(svc, "get_user_limits", AsyncMock(return_value={"websites_limit": 1})),
            patch.object(
                svc, "get_or_create_usage_tracking",
                AsyncMock(return_value={"websites_count": 1}),
            ),
            patch.object(
                svc, "get_subscription_status",
                AsyncMock(return_value={"plan_name": "free", "is_expired": False}),
            ),
            patch.object(
                svc, "get_website_slot_purchases",
                AsyncMock(return_value={"purchased": 0, "available": 0, "rows": []}),
            ),
            patch.object(plan_features, "can_publish_subdomain", AsyncMock(return_value=can_publish)),
        )

    @pytest.mark.asyncio
    async def test_free_plan_at_limit_requires_upgrade_not_addon(self):
        p = self._patches(can_publish=False)
        with p[0], p[1], p[2], p[3], p[4], p[5]:
            result = await subscription_service.check_limit("user-free-1", "create_website")
        assert result["allowed"] is False
        assert result["can_buy_addon"] is False
        assert result["requires_upgrade"] is True
        assert "starter" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_paid_plan_at_limit_still_offers_slot(self):
        p = self._patches(can_publish=True)
        with p[0], p[1], p[2], p[3], p[4], p[5]:
            result = await subscription_service.check_limit("user-paid-1", "create_website")
        assert result["allowed"] is False
        assert result["can_buy_addon"] is True
        assert result["addon_type"] == "website"


class TestHeroVideoAccessOnFreePlan:
    @pytest.mark.asyncio
    async def test_reports_requires_upgrade_without_free_access(self):
        with patch.object(plan_features, "can_use_hero_video", AsyncMock(return_value=False)), patch.object(
            plan_features, "can_publish_subdomain", AsyncMock(return_value=False)
        ), patch.object(
            subscription_service, "get_available_addon_credits",
            AsyncMock(return_value={"hero_video": 1}),
        ):
            access = await plan_features.hero_video_access("user-free-1")
        assert access["requires_upgrade"] is True
        # A credit already bought stays usable.
        assert access["credits"] == 1
        assert access["allowed"] is True

    @pytest.mark.asyncio
    async def test_paid_plan_does_not_require_upgrade(self):
        with patch.object(plan_features, "can_use_hero_video", AsyncMock(return_value=False)), patch.object(
            plan_features, "can_publish_subdomain", AsyncMock(return_value=True)
        ), patch.object(
            subscription_service, "get_available_addon_credits",
            AsyncMock(return_value={}),
        ):
            access = await plan_features.hero_video_access("user-paid-1")
        assert access["requires_upgrade"] is False
        assert access["allowed"] is False

    @pytest.mark.asyncio
    async def test_free_access_never_requires_upgrade(self):
        with patch.object(plan_features, "can_use_hero_video", AsyncMock(return_value=True)), patch.object(
            plan_features, "can_publish_subdomain",
            AsyncMock(side_effect=AssertionError("plan looked up for a free-access account")),
        ):
            access = await plan_features.hero_video_access("admin-1")
        assert access["requires_upgrade"] is False
        assert access["allowed"] is True
