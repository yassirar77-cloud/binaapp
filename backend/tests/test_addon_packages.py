"""
Tests for AI image / AI hero addon pricing packages.

Covers:
1. Catalog integrity (ADDON_PACKAGES in subscription_service): every package
   type has a matching per-unit ADDON_PRICES entry, the 1-unit package price
   equals the single-credit price (so the legacy quantity path and the package
   path can never disagree), unit prices decrease with volume, and ids are
   unique.
2. resolve_addon_package / get_addon_packages helpers.
3. The purchase endpoints are server-authoritative: when a package_id is sent,
   quantity and price come from the catalog and the client's quantity/total is
   ignored; unknown or mismatched packages are rejected with 400.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import HTTPException

from app.services.subscription_service import SubscriptionService, subscription_service


class TestCatalogIntegrity:
    def test_package_types_have_unit_prices(self):
        for addon_type in SubscriptionService.ADDON_PACKAGES:
            assert addon_type in SubscriptionService.ADDON_PRICES

    def test_single_package_price_matches_addon_price(self):
        """The 1-unit package MUST cost exactly the per-unit addon price."""
        for addon_type, packages in SubscriptionService.ADDON_PACKAGES.items():
            singles = [p for p in packages if p["quantity"] == 1]
            assert singles, f"{addon_type} has no 1-unit package"
            assert singles[0]["price"] == SubscriptionService.ADDON_PRICES[addon_type]

    def test_unit_price_decreases_with_volume(self):
        """Bigger bundles must never cost more per credit than smaller ones."""
        for addon_type, packages in SubscriptionService.ADDON_PACKAGES.items():
            ordered = sorted(packages, key=lambda p: p["quantity"])
            unit_prices = [p["price"] / p["quantity"] for p in ordered]
            assert unit_prices == sorted(unit_prices, reverse=True), (
                f"{addon_type}: unit price should be non-increasing, got {unit_prices}"
            )

    def test_no_package_exceeds_linear_price(self):
        """A bundle must never cost more than buying singles."""
        for addon_type, packages in SubscriptionService.ADDON_PACKAGES.items():
            unit = SubscriptionService.ADDON_PRICES[addon_type]
            for pkg in packages:
                assert pkg["price"] <= unit * pkg["quantity"]

    def test_package_ids_unique(self):
        ids = [
            p["package_id"]
            for packages in SubscriptionService.ADDON_PACKAGES.values()
            for p in packages
        ]
        assert len(ids) == len(set(ids))

    def test_package_unit_prices_are_exact_2dp(self):
        """The callback recomputes total as unit_price * quantity, so every
        package's effective unit price must round-trip exactly at 2 decimals."""
        for packages in SubscriptionService.ADDON_PACKAGES.values():
            for pkg in packages:
                unit = round(pkg["price"] / pkg["quantity"], 2)
                assert round(unit * pkg["quantity"], 2) == pkg["price"]

    def test_ai_image_packages_exist(self):
        quantities = {p["quantity"] for p in SubscriptionService.ADDON_PACKAGES["ai_image"]}
        assert 1 in quantities
        assert any(q >= 10 for q in quantities)


class TestCatalogHelpers:
    def test_resolve_known_package(self):
        pkg = subscription_service.resolve_addon_package("ai_image_10")
        assert pkg == {"addon_type": "ai_image", "quantity": 10, "price": 8.00}

    def test_resolve_unknown_package_returns_none(self):
        assert subscription_service.resolve_addon_package("nope_999") is None

    def test_get_addon_packages_filter(self):
        all_packages = subscription_service.get_addon_packages()
        ai_only = subscription_service.get_addon_packages("ai_image")
        assert all(p["addon_type"] == "ai_image" for p in ai_only)
        assert len(all_packages) > len(ai_only)

    def test_get_addon_packages_savings_math(self):
        ten = next(
            p for p in subscription_service.get_addon_packages("ai_image")
            if p["package_id"] == "ai_image_10"
        )
        # 10 singles = RM10, package = RM8 → save RM2 = 20%
        assert ten["unit_price"] == 0.80
        assert ten["savings"] == 2.00
        assert ten["savings_pct"] == 20


FAKE_USER = {"sub": "user-abc-123", "email": "buyer@example.com"}


def _bill_success():
    return {"success": True, "bill_code": "BILL123", "payment_url": "https://toyyibpay.test/BILL123"}


def _subscription_endpoint_patches(insert_record: AsyncMock):
    """Patch out network calls made by subscription.purchase_addon."""
    base = "app.api.v1.endpoints.subscription"
    return [
        patch(f"{base}.toyyibpay_service.create_bill", MagicMock(return_value=_bill_success())),
        patch(f"{base}.supabase_service.get_user_by_id", AsyncMock(return_value={"full_name": "Buyer", "phone": "0123"})),
        patch(f"{base}.supabase_service.insert_record", insert_record),
        patch(f"{base}.subscription_service.generate_invoice_number", AsyncMock(return_value="INV-20260716-0001")),
    ]


class TestSubscriptionPurchaseEndpoint:
    @pytest.mark.asyncio
    async def test_package_purchase_uses_server_price_and_quantity(self):
        """package_id wins: client quantity 999 is ignored, RM8 for 10 credits."""
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        insert_record = AsyncMock(return_value={"transaction_id": "tx-1"})
        patches = _subscription_endpoint_patches(insert_record)
        with patches[0] as create_bill, patches[1], patches[2], patches[3]:
            result = await purchase_addon(
                AddonPurchaseRequest(addon_type="ai_image", quantity=999, package_id="ai_image_10"),
                FAKE_USER,
            )

        assert result["success"] is True
        assert result["quantity"] == 10
        assert result["package_id"] == "ai_image_10"
        assert result["total_amount"] == 8.00

        # The ToyyibPay bill is created for the package price, not 999 x RM1.
        assert create_bill.call_args.kwargs["bill_amount"] == 8.00

        # The transaction record carries the package metadata the payment
        # callback uses to grant credits.
        tx = insert_record.call_args.args[1]
        assert tx["amount"] == 8.00
        assert tx["metadata"]["quantity"] == 10
        assert tx["metadata"]["unit_price"] == 0.80
        assert tx["metadata"]["package_id"] == "ai_image_10"

    @pytest.mark.asyncio
    async def test_unknown_package_rejected(self):
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        with pytest.raises(HTTPException) as exc:
            await purchase_addon(
                AddonPurchaseRequest(addon_type="ai_image", package_id="ai_image_9999"),
                FAKE_USER,
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_mismatched_addon_type_rejected(self):
        """An ai_hero package can't be bought under addon_type ai_image."""
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        with pytest.raises(HTTPException) as exc:
            await purchase_addon(
                AddonPurchaseRequest(addon_type="ai_image", package_id="ai_hero_5"),
                FAKE_USER,
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_legacy_quantity_purchase_unchanged(self):
        """No package_id → linear per-unit pricing exactly as before."""
        from app.api.v1.endpoints.subscription import purchase_addon, AddonPurchaseRequest

        insert_record = AsyncMock(return_value={"transaction_id": "tx-2"})
        patches = _subscription_endpoint_patches(insert_record)
        with patches[0] as create_bill, patches[1], patches[2], patches[3]:
            result = await purchase_addon(
                AddonPurchaseRequest(addon_type="ai_image", quantity=3),
                FAKE_USER,
            )

        assert result["success"] is True
        assert result["quantity"] == 3
        assert result["package_id"] is None
        assert result["total_amount"] == 3.00
        assert create_bill.call_args.kwargs["bill_amount"] == 3.00


class TestPackagesListingEndpoint:
    @pytest.mark.asyncio
    async def test_lists_packages_with_savings(self):
        from app.api.v1.endpoints.subscription import get_addon_packages

        result = await get_addon_packages()
        packages = result["packages"]
        assert any(p["package_id"] == "ai_image_10" for p in packages)
        ten = next(p for p in packages if p["package_id"] == "ai_image_10")
        assert ten["savings_pct"] == 20

    @pytest.mark.asyncio
    async def test_filter_by_addon_type(self):
        from app.api.v1.endpoints.subscription import get_addon_packages

        result = await get_addon_packages(addon_type="ai_hero")
        assert result["packages"]
        assert all(p["addon_type"] == "ai_hero" for p in result["packages"])


class TestPaymentsPurchaseEndpoint:
    """The legacy /api/v1/payments/addon/purchase path gets the same
    server-authoritative package handling."""

    @pytest.mark.asyncio
    async def test_package_purchase_uses_server_price(self):
        from app.api.v1.endpoints.payments import purchase_addon, AddonPurchaseRequest

        base = "app.api.v1.endpoints.payments"
        insert_record = AsyncMock(return_value={"transaction_id": "tx-3"})
        create_bill = MagicMock(return_value=_bill_success())

        with patch(f"{base}.settings") as mock_settings, \
             patch(f"{base}.supabase_service.get_user_by_id", AsyncMock(return_value={"email": "buyer@example.com"})), \
             patch(f"{base}.supabase_service.insert_record", insert_record), \
             patch(f"{base}.toyyibpay_service.create_bill", create_bill), \
             patch("app.services.subscription_service.subscription_service.generate_invoice_number", AsyncMock(return_value="INV-20260716-0002")):
            mock_settings.EMAIL_VERIFICATION_ENABLED = False
            result = await purchase_addon(
                AddonPurchaseRequest(user_id="user-abc-123", addon_type="ai_image", quantity=1, package_id="ai_image_30")
            )

        assert result["success"] is True
        assert result["quantity"] == 30
        assert result["package_id"] == "ai_image_30"
        assert result["amount"] == 21.00
        assert create_bill.call_args.kwargs["bill_amount"] == 21.00

    @pytest.mark.asyncio
    async def test_unknown_package_rejected(self):
        from app.api.v1.endpoints.payments import purchase_addon, AddonPurchaseRequest

        base = "app.api.v1.endpoints.payments"
        with patch(f"{base}.settings") as mock_settings:
            mock_settings.EMAIL_VERIFICATION_ENABLED = False
            with pytest.raises(HTTPException) as exc:
                await purchase_addon(
                    AddonPurchaseRequest(user_id="user-abc-123", addon_type="ai_image", package_id="bogus")
                )
        assert exc.value.status_code == 400
