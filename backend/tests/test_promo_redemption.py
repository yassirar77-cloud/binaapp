"""
Tests for the promo code redemption endpoint (app/api/v1/endpoints/subscription.py).

The atomic slot-cap and the one-redemption-per-user guard live in the
redeem_promo_code() Postgres function (advisory lock + UNIQUE(user_id)); the test
suite mocks the Supabase RPC so it can assert the endpoint correctly surfaces the
two business outcomes the function returns:

  1. slot cap reached  -> RPC status 'promo_full'      (THE SLOT CAP)
  2. user already used  -> RPC status 'already_redeemed' (NO DOUBLE-REDEEM)

plus the happy path and a no-RPC-needed empty-code rejection.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.api.v1.endpoints.subscription import redeem_promo, RedeemPromoRequest

FAKE_USER = {"sub": "user-123", "email": "promo@example.com"}


def _mock_rpc(json_body):
    """Patch httpx.AsyncClient so the RPC POST returns `json_body` with status 200."""
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = json_body
    mock_resp.text = str(json_body)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    patcher = patch("httpx.AsyncClient", return_value=mock_client)
    return patcher, mock_client


class TestSlotCap:
    @pytest.mark.asyncio
    async def test_promo_full_is_surfaced_to_caller(self):
        """When the DB function reports the cap is reached, the endpoint returns
        success=False with reason 'promo_full' so the frontend can fall back to
        normal checkout."""
        patcher, _ = _mock_rpc(
            {"success": False, "status": "promo_full", "max": 20, "used": 20}
        )
        with patcher:
            result = await redeem_promo(RedeemPromoRequest(code="BINA20"), FAKE_USER)

        assert result["success"] is False
        assert result["reason"] == "promo_full"
        assert "penuh" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_successful_redemption_returns_expiry(self):
        """Happy path: the 20th-or-earlier redeemer gets Starter with an expiry."""
        patcher, _ = _mock_rpc(
            {
                "success": True,
                "status": "redeemed",
                "tier": "starter",
                "expires_at": "2026-07-22T00:00:00+00:00",
                "slots_remaining": 5,
            }
        )
        with patcher:
            result = await redeem_promo(RedeemPromoRequest(code="bina20"), FAKE_USER)

        assert result["success"] is True
        assert result["tier"] == "starter"
        assert result["expires_at"].startswith("2026-07-22")
        # Confirmation message shows the date (frontend renders "Starter percuma sampai ...").
        assert "2026-07-22" in result["message"]


class TestNoDoubleRedeem:
    @pytest.mark.asyncio
    async def test_already_redeemed_is_rejected(self):
        """A user who already redeemed (RPC status 'already_redeemed') is blocked
        with a clear message and no second grant."""
        patcher, mock_client = _mock_rpc(
            {"success": False, "status": "already_redeemed"}
        )
        with patcher:
            result = await redeem_promo(RedeemPromoRequest(code="BINA20"), FAKE_USER)

        assert result["success"] is False
        assert result["reason"] == "already_redeemed"
        assert "telah" in result["message"].lower()
        # The RPC was the only call — the endpoint trusts the DB's atomic guard.
        assert mock_client.post.await_count == 1

    @pytest.mark.asyncio
    async def test_empty_code_rejected_without_rpc(self):
        """A blank code is rejected locally without hitting the database."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            result = await redeem_promo(RedeemPromoRequest(code="   "), FAKE_USER)
            mock_client_cls.assert_not_called()

        assert result["success"] is False
        assert result["reason"] == "invalid_code"
