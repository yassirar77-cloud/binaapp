"""
Tests for the PDPA-safe visitor tracking pipeline.

Covers the pure hashing/normalization helpers, the fire-and-forget
/api/analytics/track endpoint (DNT, bots, 204 semantics), and the
no-PII-in-logs guarantee.
"""
from unittest.mock import AsyncMock, patch

import pytest
from loguru import logger

from app.services.analytics_tracking import (
    client_ip_from_headers,
    compute_visitor_hash,
    is_bot_user_agent,
    normalize_page_path,
    normalize_referrer_source,
    classify_device,
    process_pageview,
)

FAKE_IP = "203.0.113.42"
FAKE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
SITE_A = "11111111-1111-1111-1111-111111111111"
SITE_B = "22222222-2222-2222-2222-222222222222"


# ---------------------------------------------------------------------------
# compute_visitor_hash
# ---------------------------------------------------------------------------

class TestVisitorHash:
    def test_rotates_daily(self):
        h1 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01")
        h2 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-02")
        assert h1 != h2

    def test_stable_within_a_day(self):
        h1 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01")
        h2 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01")
        assert h1 == h2

    def test_differs_per_site(self):
        h1 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01")
        h2 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_B, date_str="2026-07-01")
        assert h1 != h2

    def test_differs_per_visitor(self):
        h1 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01")
        h2 = compute_visitor_hash("198.51.100.7", FAKE_UA, SITE_A, date_str="2026-07-01")
        assert h1 != h2

    def test_differs_per_salt(self):
        h1 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01", salt="a")
        h2 = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01", salt="b")
        assert h1 != h2

    def test_never_contains_ip(self):
        h = compute_visitor_hash(FAKE_IP, FAKE_UA, SITE_A, date_str="2026-07-01")
        assert FAKE_IP not in h
        assert len(h) == 32
        int(h, 16)  # hex digest


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

class TestNormalizers:
    def test_page_path_strips_query_and_fragment(self):
        assert normalize_page_path("/menu?utm_source=fb#top") == "/menu"

    def test_page_path_defaults_to_root(self):
        assert normalize_page_path(None) == "/"
        assert normalize_page_path("") == "/"
        assert normalize_page_path("?q=1") == "/"

    def test_page_path_clamps_length(self):
        assert len(normalize_page_path("/" + "a" * 500)) == 200

    def test_page_path_adds_leading_slash(self):
        assert normalize_page_path("menu") == "/menu"

    def test_referrer_domain_extracted(self):
        assert normalize_referrer_source("https://www.google.com/search?q=x") == "google.com"

    def test_referrer_empty_is_direct(self):
        assert normalize_referrer_source(None) == "direct"
        assert normalize_referrer_source("") == "direct"
        assert normalize_referrer_source("not a url") == "direct"

    def test_referrer_same_site_is_direct(self):
        assert (
            normalize_referrer_source("https://mybistro.binaapp.my/menu", own_hostname="mybistro.binaapp.my")
            == "direct"
        )

    def test_bot_detection(self):
        assert is_bot_user_agent("Googlebot/2.1 (+http://www.google.com/bot.html)")
        assert is_bot_user_agent("curl/8.0")
        assert not is_bot_user_agent(FAKE_UA)

    def test_device_classification(self):
        assert classify_device(FAKE_UA) == "mobile"
        assert (
            classify_device("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            == "desktop"
        )

    def test_client_ip_prefers_forwarded_headers(self):
        # Behind a proxy the first X-Forwarded-For entry is the real client.
        assert (
            client_ip_from_headers({"x-forwarded-for": "198.51.100.7, 10.0.0.1"})
            == "198.51.100.7"
        )
        assert client_ip_from_headers({"x-real-ip": "203.0.113.9"}) == "203.0.113.9"
        assert client_ip_from_headers({"cf-connecting-ip": "203.0.113.5"}) == "203.0.113.5"

    def test_client_ip_falls_back(self):
        assert client_ip_from_headers({}, fallback="127.0.0.1") == "127.0.0.1"
        assert client_ip_from_headers({}) == "unknown"


# ---------------------------------------------------------------------------
# process_pageview (background task)
# ---------------------------------------------------------------------------

class TestProcessPageview:
    async def test_unknown_hostname_is_noop(self):
        with patch(
            "app.services.analytics_tracking._resolve_website",
            new=AsyncMock(return_value=None),
        ):
            recorded = await process_pageview("ghost.binaapp.my", "/", None, FAKE_IP, FAKE_UA)
        assert recorded is False

    async def test_opted_out_website_is_noop(self):
        with patch(
            "app.services.analytics_tracking._resolve_website",
            new=AsyncMock(return_value={"id": SITE_A, "analytics_enabled": False}),
        ):
            recorded = await process_pageview("mybistro.binaapp.my", "/", None, FAKE_IP, FAKE_UA)
        assert recorded is False

    async def test_happy_path_calls_rollup_rpc(self):
        captured = {}

        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                pass

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, json=None, headers=None):
                captured["url"] = url
                captured["payload"] = json
                return FakeResponse()

        with patch(
            "app.services.analytics_tracking._resolve_website",
            new=AsyncMock(return_value={"id": SITE_A, "analytics_enabled": True}),
        ), patch("app.services.analytics_tracking.httpx.AsyncClient", FakeClient):
            recorded = await process_pageview(
                "mybistro.binaapp.my",
                "/menu?utm=x",
                "https://www.facebook.com/some/post",
                FAKE_IP,
                FAKE_UA,
            )

        assert recorded is True
        assert captured["url"].endswith("/rest/v1/rpc/track_site_pageview")
        payload = captured["payload"]
        assert payload["p_website_id"] == SITE_A
        assert payload["p_page_path"] == "/menu"
        assert payload["p_referrer_source"] == "facebook.com"
        assert payload["p_device"] == "mobile"
        # PDPA: the payload carries only the salted hash — never the raw IP/UA
        assert FAKE_IP not in str(payload)
        assert FAKE_UA not in str(payload)

    async def test_failure_logs_no_pii(self):
        messages = []
        sink_id = logger.add(lambda m: messages.append(str(m)), level="DEBUG")
        try:
            with patch(
                "app.services.analytics_tracking._resolve_website",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ):
                recorded = await process_pageview(
                    "mybistro.binaapp.my", "/", None, FAKE_IP, FAKE_UA
                )
        finally:
            logger.remove(sink_id)
        assert recorded is False
        joined = "\n".join(messages)
        assert FAKE_IP not in joined
        assert FAKE_UA not in joined


# ---------------------------------------------------------------------------
# POST /api/analytics/track endpoint
# ---------------------------------------------------------------------------

TRACK_PAYLOAD = {
    "project_id": "mybistro.binaapp.my",
    "referrer": "https://google.com",
    "page_path": "/menu",
}


class TestTrackEndpoint:
    def test_returns_204_and_schedules_work(self, client):
        with patch("app.main.process_pageview", new=AsyncMock(return_value=True)) as task:
            resp = client.post(
                "/api/analytics/track",
                json=TRACK_PAYLOAD,
                headers={"User-Agent": FAKE_UA},
            )
        assert resp.status_code == 204
        assert task.await_count == 1
        kwargs = task.await_args.kwargs
        assert kwargs["hostname"] == "mybistro.binaapp.my"
        assert kwargs["page_path"] == "/menu"

    def test_old_snippet_visitor_id_is_ignored(self, client):
        with patch("app.main.process_pageview", new=AsyncMock(return_value=True)) as task:
            resp = client.post(
                "/api/analytics/track",
                json={**TRACK_PAYLOAD, "visitor_id": "v_legacy123"},
                headers={"User-Agent": FAKE_UA},
            )
        assert resp.status_code == 204
        assert task.await_count == 1
        # The legacy client-side visitor id must not reach the pipeline
        assert "v_legacy123" not in str(task.await_args)

    @pytest.mark.parametrize("header", [{"DNT": "1"}, {"Sec-GPC": "1"}])
    def test_dnt_and_gpc_fully_opt_out(self, client, header):
        with patch("app.main.process_pageview", new=AsyncMock()) as task:
            resp = client.post(
                "/api/analytics/track",
                json=TRACK_PAYLOAD,
                headers={"User-Agent": FAKE_UA, **header},
            )
        assert resp.status_code == 204
        task.assert_not_awaited()

    def test_bots_are_dropped(self, client):
        with patch("app.main.process_pageview", new=AsyncMock()) as task:
            resp = client.post(
                "/api/analytics/track",
                json=TRACK_PAYLOAD,
                headers={"User-Agent": "Googlebot/2.1"},
            )
        assert resp.status_code == 204
        task.assert_not_awaited()
