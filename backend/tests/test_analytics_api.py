"""
Tests for the merchant analytics API (/api/v1/analytics/*).

Covers auth, cross-tenant ownership, server-side tier clamping, the
pro-only CSV export, and the pure aggregation helpers.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.endpoints.analytics import (
    MYT,
    aggregate_top_items,
    build_daily_series,
    build_heatmap,
    clamp_days,
    pct_change,
    parse_ts_myt,
)

WEBSITE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OWNER_ID = "test-user-id-12345"  # matches conftest's test_user_id
OTHER_ID = "someone-else-9999"

ANALYTICS_MODULE = "app.api.v1.endpoints.analytics"


def _db_query_factory(website_owner=OWNER_ID, orders=None, extra=None):
    """Fake _db_query keyed by table name."""
    orders = orders or []
    extra = extra or {}

    async def _fake(table, params):
        if table == "websites":
            return [{"id": WEBSITE_ID, "user_id": website_owner, "subdomain": "mybistro"}]
        if table == "delivery_orders":
            return orders
        return extra.get(table, [])

    return _fake


def _iso_hours_ago(hours):
    return (datetime.now(MYT) - timedelta(hours=hours)).isoformat()


# ---------------------------------------------------------------------------
# Auth + ownership
# ---------------------------------------------------------------------------

class TestAuthAndOwnership:
    def test_requires_auth(self, client):
        resp = client.get(f"/api/v1/analytics/summary?website_id={WEBSITE_ID}")
        assert resp.status_code in (401, 403)

    def test_cross_tenant_is_denied(self, client, auth_headers):
        with patch(
            f"{ANALYTICS_MODULE}._db_query",
            new=AsyncMock(side_effect=_db_query_factory(website_owner=OTHER_ID)),
        ), patch(f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value="pro")):
            resp = client.get(
                f"/api/v1/analytics/revenue-daily?website_id={WEBSITE_ID}",
                headers=auth_headers,
            )
        assert resp.status_code == 403

    def test_missing_website_is_404(self, client, auth_headers):
        async def _empty(table, params):
            return []

        with patch(f"{ANALYTICS_MODULE}._db_query", new=AsyncMock(side_effect=_empty)), patch(
            f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value="pro")
        ):
            resp = client.get(
                f"/api/v1/analytics/revenue-daily?website_id={WEBSITE_ID}",
                headers=auth_headers,
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Server-side tier clamping
# ---------------------------------------------------------------------------

class TestTierClamping:
    @pytest.mark.parametrize(
        "tier,requested,expected_days,expected_clamped",
        [
            ("free", 90, 7, True),
            ("starter", 90, 7, True),
            ("basic", 90, 30, True),
            ("pro", 90, 90, False),
            ("basic", 14, 14, False),
        ],
    )
    def test_days_clamped_by_tier(
        self, client, auth_headers, tier, requested, expected_days, expected_clamped
    ):
        with patch(
            f"{ANALYTICS_MODULE}._db_query",
            new=AsyncMock(side_effect=_db_query_factory()),
        ), patch(f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value=tier)):
            resp = client.get(
                f"/api/v1/analytics/revenue-daily?website_id={WEBSITE_ID}&days={requested}",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == expected_days
        assert body["clamped"] is expected_clamped
        assert body["tier"] == tier
        # The series itself must honour the clamp, not just the metadata
        assert len(body["series"]) == expected_days

    def test_summary_locks_30d_block_for_starter(self, client, auth_headers):
        with patch(
            f"{ANALYTICS_MODULE}._db_query",
            new=AsyncMock(side_effect=_db_query_factory()),
        ), patch(f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value="starter")), patch(
            f"{ANALYTICS_MODULE}._db_count", new=AsyncMock(return_value=0)
        ):
            resp = client.get(
                f"/api/v1/analytics/summary?website_id={WEBSITE_ID}",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["summary"]["last_30d"] == {"locked": True}
        assert "revenue" in body["summary"]["last_7d"]


# ---------------------------------------------------------------------------
# CSV export gating
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_denied_below_pro(self, client, auth_headers):
        with patch(
            f"{ANALYTICS_MODULE}._db_query",
            new=AsyncMock(side_effect=_db_query_factory()),
        ), patch(f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value="basic")):
            resp = client.get(
                f"/api/v1/analytics/export?website_id={WEBSITE_ID}",
                headers=auth_headers,
            )
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "tier_required"

    def test_export_streams_csv_for_pro(self, client, auth_headers):
        orders = [
            {
                "order_number": "ORD-001",
                "created_at": _iso_hours_ago(2),
                "status": "delivered",
                "payment_method": "cod",
                "payment_status": "paid",
                "delivery_zone": "Zon A",
                "subtotal": 20.0,
                "delivery_fee": 5.0,
                "total_amount": 25.0,
            }
        ]
        with patch(
            f"{ANALYTICS_MODULE}._db_query",
            new=AsyncMock(side_effect=_db_query_factory(orders=orders)),
        ), patch(f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value="pro")):
            resp = client.get(
                f"/api/v1/analytics/export?website_id={WEBSITE_ID}&dataset=orders",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment" in resp.headers["content-disposition"]
        body = resp.text
        assert "ORD-001" in body
        # PII-light export: no customer columns
        assert "customer" not in body.split("\n")[0]


# ---------------------------------------------------------------------------
# Endpoint aggregation smoke tests
# ---------------------------------------------------------------------------

class TestAggregationEndpoints:
    def test_revenue_daily_excludes_cancelled(self, client, auth_headers):
        orders = [
            {"total_amount": 50.0, "status": "delivered", "created_at": _iso_hours_ago(1)},
            {"total_amount": 30.0, "status": "pending", "created_at": _iso_hours_ago(2)},
            {"total_amount": 99.0, "status": "cancelled", "created_at": _iso_hours_ago(3)},
        ]
        with patch(
            f"{ANALYTICS_MODULE}._db_query",
            new=AsyncMock(side_effect=_db_query_factory(orders=orders)),
        ), patch(f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value="pro")):
            resp = client.get(
                f"/api/v1/analytics/revenue-daily?website_id={WEBSITE_ID}&days=7",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        today_row = resp.json()["series"][-1]
        assert today_row["revenue"] == 80.0
        assert today_row["orders"] == 2

    def test_visitors_reads_rollups_only(self, client, auth_headers):
        extra = {
            "site_analytics_daily": [
                {
                    "date": datetime.now(MYT).date().isoformat(),
                    "total_views": 12,
                    "unique_visitors": 7,
                    "mobile_views": 9,
                    "tablet_views": 1,
                    "desktop_views": 2,
                }
            ],
            "site_analytics_pages_daily": [
                {"page_path": "/", "views": 10},
                {"page_path": "/menu", "views": 2},
            ],
            "site_analytics_referrers_daily": [{"referrer_source": "google.com", "views": 5}],
        }
        with patch(
            f"{ANALYTICS_MODULE}._db_query",
            new=AsyncMock(side_effect=_db_query_factory(extra=extra)),
        ), patch(f"{ANALYTICS_MODULE}._get_tier", new=AsyncMock(return_value="basic")):
            resp = client.get(
                f"/api/v1/analytics/visitors?website_id={WEBSITE_ID}&days=7",
                headers=auth_headers,
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["totals"] == {"total_views": 12, "unique_visitors": 7}
        assert body["devices"] == {"mobile": 9, "tablet": 1, "desktop": 2}
        assert body["top_pages"][0] == {"page_path": "/", "views": 10}
        assert body["top_referrers"][0] == {"source": "google.com", "views": 5}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_clamp_days(self):
        assert clamp_days(90, "free") == (7, True)
        assert clamp_days(90, "basic") == (30, True)
        assert clamp_days(90, "pro") == (90, False)
        assert clamp_days(0, "pro") == (1, False)
        assert clamp_days(30, None) == (7, True)
        assert clamp_days(30, "unknown-tier") == (7, True)

    def test_pct_change(self):
        assert pct_change(150, 100) == 50.0
        assert pct_change(50, 100) == -50.0
        assert pct_change(10, 0) is None
        assert pct_change(0, 0) is None

    def test_build_daily_series_zero_fills(self):
        series = build_daily_series([], days=7)
        assert len(series) == 7
        assert all(row["revenue"] == 0.0 and row["orders"] == 0 for row in series)
        # Chronological, ending today (MYT)
        assert series[-1]["date"] == datetime.now(MYT).date().isoformat()
        assert series[0]["date"] < series[-1]["date"]

    def test_build_heatmap_buckets_in_myt(self):
        # 02:30 UTC == 10:30 MYT — the hour bucket must be the MYT one
        orders = [{"status": "delivered", "created_at": "2026-06-29T02:30:00+00:00"}]
        expected_dow = datetime(2026, 6, 29).weekday()
        cells = build_heatmap(orders)
        assert len(cells) == 7 * 24
        hit = [c for c in cells if c["count"] > 0]
        assert hit == [{"dow": expected_dow, "hour": 10, "count": 1}]

    def test_aggregate_top_items_orders_by_quantity(self):
        items = [
            {"item_name": "Nasi Lemak", "quantity": 5, "total_price": 40.0},
            {"item_name": "Teh Tarik", "quantity": 9, "total_price": 27.0},
            {"item_name": "Nasi Lemak", "quantity": 3, "total_price": 24.0},
        ]
        top = aggregate_top_items(items)
        assert top[0] == {"item_name": "Teh Tarik", "quantity": 9, "revenue": 27.0}
        assert top[1] == {"item_name": "Nasi Lemak", "quantity": 8, "revenue": 64.0}

    def test_parse_ts_myt(self):
        ts = parse_ts_myt("2026-07-03T00:00:00Z")
        assert ts is not None
        assert ts.utcoffset() == timedelta(hours=8)
        assert parse_ts_myt(None) is None
        assert parse_ts_myt("garbage") is None
