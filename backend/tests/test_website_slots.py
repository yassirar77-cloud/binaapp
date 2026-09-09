"""
Website slot accounting ("Laman Web Tambahan", RM5 per slot).

A purchased website slot is permanent capacity: the user may build on
plan limit + every slot bought, whether or not the slot is already marked
used (a used slot still holds a live site). The old check compared the
live site count against limit + *unused* credits, so once a slot was
consumed the site it funded kept counting but the slot no longer did —
buying another slot never unblocked the user, and a failed generation
also ate a paid slot. These tests pin the corrected model.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.services import plan_features
from app.services.subscription_service import (
    subscription_service,
    WEBSITE_QUOTA_STATUS_FILTER,
)


USER = "7feab79a-6937-4c59-a883-3a2f7609b734"


def _row(rid, qty=1, used=0, status="active"):
    return {
        "id": rid,
        "quantity": qty,
        "quantity_used": used,
        "status": status,
        "created_at": f"2026-01-0{rid}T00:00:00+00:00",
    }


class _FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ""

    def json(self):
        return self._payload


class _FakeClient:
    """Minimal httpx.AsyncClient stand-in recording GET params."""

    calls = []
    responses = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None, params=None):
        _FakeClient.calls.append({"url": url, "params": params or {}})
        if _FakeClient.responses:
            return _FakeClient.responses.pop(0)
        return _FakeResponse([])


@pytest.fixture
def fake_client():
    _FakeClient.calls = []
    _FakeClient.responses = []
    with patch("app.services.subscription_service.httpx.AsyncClient", _FakeClient):
        yield _FakeClient


class TestGetWebsiteSlotPurchases:
    @pytest.mark.asyncio
    async def test_counts_used_and_unused_slots(self, fake_client):
        fake_client.responses = [
            _FakeResponse([
                _row(1, qty=1, used=1, status="depleted"),
                _row(2, qty=1, used=0, status="active"),
                _row(3, qty=2, used=1, status="active"),
            ])
        ]
        slots = await subscription_service.get_website_slot_purchases(USER)

        assert slots["purchased"] == 4  # 1 + 1 + 2, used or not
        assert slots["available"] == 2  # row 2 (1) + row 3 (1 left)
        assert [r["id"] for r in slots["rows"]] == [2, 3]

        params = fake_client.calls[0]["params"]
        assert params["addon_type"] == "eq.website"
        assert params["status"] == "in.(active,depleted)"
        assert params["order"] == "created_at.asc"

    @pytest.mark.asyncio
    async def test_query_failure_is_zero_not_crash(self, fake_client):
        fake_client.responses = [_FakeResponse({"message": "boom"}, status_code=500)]
        slots = await subscription_service.get_website_slot_purchases(USER)
        assert slots == {"purchased": 0, "available": 0, "rows": []}


class TestCheckLimitWebsiteSlots:
    def _patches(self, *, limit, current, slots):
        svc = subscription_service
        return (
            patch.object(svc, "_is_admin", AsyncMock(return_value=False)),
            patch.object(svc, "get_user_limits", AsyncMock(return_value={"websites_limit": limit})),
            patch.object(
                svc, "get_or_create_usage_tracking",
                AsyncMock(return_value={"websites_count": current}),
            ),
            patch.object(
                svc, "get_subscription_status",
                AsyncMock(return_value={"plan_name": "starter", "is_expired": False}),
            ),
            patch.object(svc, "get_website_slot_purchases", AsyncMock(return_value=slots)),
            # The consumable-credit path must not be consulted for websites.
            patch.object(
                svc, "get_available_addon_credits",
                AsyncMock(side_effect=AssertionError("credit path used for websites")),
            ),
            # A paid plan: the blocked branch may offer the slot add-on.
            patch.object(plan_features, "can_publish_subdomain", AsyncMock(return_value=True)),
        )

    async def _check(self, **kw):
        p = self._patches(**kw)
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6]:
            return await subscription_service.check_limit(USER, "create_website")

    @pytest.mark.asyncio
    async def test_reported_case_two_unused_slots_two_sites(self):
        """STARTER (limit 1), 2 live sites, 2 slots bought and never marked
        used: the user still has a slot to build on."""
        result = await self._check(
            limit=1, current=2,
            slots={"purchased": 2, "available": 2, "rows": [_row(1), _row(2)]},
        )
        assert result["allowed"] is True
        assert result["using_addon"] is True
        assert result["total_allowed"] == 3
        assert result["remaining"] == 1

    @pytest.mark.asyncio
    async def test_used_slot_keeps_counting_after_new_purchase(self):
        """The regression: one slot already used (site #2 lives on it), a
        second slot just bought. Old maths: 2 < 1 + 1 unused → blocked."""
        result = await self._check(
            limit=1, current=2,
            slots={"purchased": 2, "available": 1, "rows": [_row(2)]},
        )
        assert result["allowed"] is True
        assert result["using_addon"] is True
        assert result["total_allowed"] == 3

    @pytest.mark.asyncio
    async def test_blocked_only_when_every_slot_holds_a_site(self):
        result = await self._check(
            limit=1, current=2,
            slots={"purchased": 1, "available": 0, "rows": []},
        )
        assert result["allowed"] is False
        assert result["can_buy_addon"] is True
        assert result["addon_type"] == "website"
        assert result["addon_price"] == 5.00
        assert result["total_allowed"] == 2
        assert result["limit"] == 1
        assert "2/2" in result["message"]

    @pytest.mark.asyncio
    async def test_deleted_site_frees_its_used_slot(self):
        """Slot marked used, its site later deleted: the slot is capacity
        again and nothing new needs to be consumed."""
        result = await self._check(
            limit=1, current=1,
            slots={"purchased": 1, "available": 0, "rows": []},
        )
        assert result["allowed"] is True
        assert result["using_addon"] is False
        assert result["total_allowed"] == 2

    @pytest.mark.asyncio
    async def test_within_plan_limit_never_touches_slots(self):
        result = await self._check(
            limit=1, current=0,
            slots={"purchased": 1, "available": 1, "rows": [_row(1)]},
        )
        assert result["allowed"] is True
        assert "using_addon" not in result
        assert result["remaining"] == 2

    @pytest.mark.asyncio
    async def test_unlimited_plan_short_circuits(self):
        result = await self._check(
            limit=None, current=50,
            slots={"purchased": 0, "available": 0, "rows": []},
        )
        assert result["allowed"] is True
        assert result["unlimited"] is True


class TestFailedSitesDoNotOccupySlots:
    def test_filter_constant(self):
        assert WEBSITE_QUOTA_STATUS_FILTER == "not.in.(pending_payment,failed)"

    @pytest.mark.asyncio
    async def test_actual_counts_exclude_failed_and_drafts(self, fake_client):
        fake_client.responses = [
            _FakeResponse([], headers={"content-range": "0-1/2"}),  # website count
            _FakeResponse([]),  # website ids for child resources
        ]
        counts = await subscription_service.get_actual_resource_counts(USER)
        assert counts["websites_count"] == 2
        website_calls = [c for c in fake_client.calls if c["url"].endswith("/rest/v1/websites")]
        assert website_calls, "websites table was not queried"
        for call in website_calls:
            assert call["params"]["status"] == WEBSITE_QUOTA_STATUS_FILTER


class TestUsageWithLimitsShowsOwnedSlots:
    @pytest.mark.asyncio
    async def test_dashboard_websites_row_uses_purchased_slots(self):
        svc = subscription_service
        with (
            patch.object(
                svc, "get_subscription_status",
                AsyncMock(return_value={
                    "plan_name": "starter", "status": "active", "days_remaining": 10,
                    "end_date": None, "is_expired": False,
                }),
            ),
            patch.object(svc, "get_user_limits", AsyncMock(return_value={"websites_limit": 1})),
            patch.object(
                svc, "get_or_create_usage_tracking",
                AsyncMock(return_value={"websites_count": 3}),
            ),
            # Only 0 unused credits — the old code would have shown 3/1.
            patch.object(svc, "get_available_addon_credits", AsyncMock(return_value={"website": 0})),
            patch.object(
                svc, "get_website_slot_purchases",
                AsyncMock(return_value={"purchased": 2, "available": 0, "rows": []}),
            ),
        ):
            usage = await svc.get_usage_with_limits(USER)

        websites = usage["usage"]["websites"]
        assert websites["used"] == 3
        assert websites["limit"] == 1
        assert websites["addon_credits"] == 2
        assert websites["percentage"] == 100
