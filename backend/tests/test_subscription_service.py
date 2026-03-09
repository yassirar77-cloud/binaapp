"""
Tests for subscription_service.py — tier limits, pricing, billing period, invoice generation.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime


class TestTierConfiguration:
    def test_tier_prices_defined(self):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        assert service.TIER_PRICES["free"] == 0.00
        assert service.TIER_PRICES["starter"] == 5.00
        assert service.TIER_PRICES["basic"] == 29.00
        assert service.TIER_PRICES["pro"] == 49.00

    def test_addon_prices_defined(self):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        assert "ai_image" in service.ADDON_PRICES
        assert "website" in service.ADDON_PRICES
        assert all(p > 0 for p in service.ADDON_PRICES.values())

    def test_starter_tier_limits(self):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        starter = service.TIER_LIMITS["starter"]
        assert starter["websites_limit"] == 1
        assert starter["menu_items_limit"] == 20
        assert starter["riders_limit"] == 0

    def test_basic_tier_has_more_than_starter(self):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        starter = service.TIER_LIMITS["starter"]
        basic = service.TIER_LIMITS["basic"]
        assert basic["websites_limit"] > starter["websites_limit"]
        assert basic["delivery_zones_limit"] > starter["delivery_zones_limit"]

    def test_pro_tier_unlimited_websites(self):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        pro = service.TIER_LIMITS["pro"]
        assert pro["websites_limit"] is None  # Unlimited

    def test_pro_tier_has_riders(self):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        pro = service.TIER_LIMITS["pro"]
        assert pro["riders_limit"] == 10


class TestBillingPeriod:
    def test_current_billing_period_format(self):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        period = service.get_current_billing_period()
        # Should match YYYY-MM format
        assert len(period) == 7
        assert period[4] == "-"
        year, month = period.split("-")
        assert 2020 <= int(year) <= 2100
        assert 1 <= int(month) <= 12


class TestInvoiceGeneration:
    @pytest.mark.asyncio
    async def test_fallback_invoice_format(self):
        """When RPC is unavailable, fallback generates INV-YYYYMMDD-XXXX."""
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        # Mock httpx to simulate RPC failure
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=MagicMock(status_code=500))
            mock_client_cls.return_value = mock_client

            invoice = await service.generate_invoice_number()

        assert invoice.startswith("INV-")
        parts = invoice.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 4  # XXXX

    @pytest.mark.asyncio
    async def test_rpc_invoice_when_available(self):
        """When RPC succeeds, use the DB-generated invoice number."""
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService()
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_resp = MagicMock(status_code=200)
            mock_resp.json.return_value = "INV-20260309-0001"

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            invoice = await service.generate_invoice_number()

        assert invoice == "INV-20260309-0001"
