"""Tests for the Business Kit — menu poster, review QR, WhatsApp order QR,
and the serve-time open/closed badge.

What matters:

  1. A printed menu must show the merchant's REAL items and prices — from
     their menu table when it has rows, from the page's own baked
     ``deliveryMenuData`` otherwise, and a clear 409 when neither exists.
  2. A printed QR is trusted by whoever scans it, so the review poster only
     accepts Google-family URLs and the WhatsApp poster only prints a number
     the merchant's page (or an explicit override) provides.
  3. The open badge is gated on the page's own JSON-LD hours and must be
     idempotent — a cached page re-served twice may never stack scripts.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.business_kit import (
    build_menu_poster_html,
    build_review_poster_html,
    build_wa_link,
    build_whatsapp_poster_html,
    default_order_message,
    format_price,
    group_by_category,
    is_valid_review_url,
    normalize_db_menu,
    parse_menu_from_html,
)

PALETTE = {
    "primary": "#2563EB",
    "surface": "#FFFFFF",
    "background": "#F8FAFF",
    "text": "#0F172A",
    "text_muted": "#64748B",
}


def _page_with_menu(menu) -> str:
    return (
        "<html><head></head><body><script>"
        f"const deliveryMenuData = {json.dumps(menu)}; const deliveryCart = [];"
        "</script></body></html>"
    )


# ---------------------------------------------------------------------------
# Menu sources
# ---------------------------------------------------------------------------

class TestMenuParsing:
    def test_reads_the_baked_delivery_menu(self):
        items = parse_menu_from_html(
            _page_with_menu(
                [
                    {"name": "Nasi Lemak", "price": "8.50", "category": "Nasi"},
                    {"name": "Teh Tarik", "price": 3, "category": "Minuman"},
                ]
            )
        )
        assert [i["name"] for i in items] == ["Nasi Lemak", "Teh Tarik"]

    def test_brackets_inside_descriptions_do_not_truncate_the_array(self):
        items = parse_menu_from_html(
            _page_with_menu(
                [{"name": "Set A", "price": 5, "description": "nasi + ayam [pedas]"}]
            )
        )
        assert len(items) == 1
        assert "[pedas]" in items[0]["description"]

    def test_quotes_and_escapes_survive(self):
        items = parse_menu_from_html(
            _page_with_menu([{"name": 'Nasi "Special" \\ Ayam', "price": 9}])
        )
        assert items[0]["name"] == 'Nasi "Special" \\ Ayam'

    def test_no_menu_variable_means_no_items(self):
        assert parse_menu_from_html("<html><body>hi</body></html>") == []
        assert parse_menu_from_html("") == []

    def test_broken_json_returns_empty_not_a_crash(self):
        html = "const deliveryMenuData = [{'single': 'quotes'}];"
        assert parse_menu_from_html(html) == []

    def test_nameless_entries_are_dropped(self):
        items = parse_menu_from_html(
            _page_with_menu([{"price": 5}, {"name": "Real", "price": 6}])
        )
        assert [i["name"] for i in items] == ["Real"]


class TestDbMenu:
    def test_unavailable_items_never_reach_a_printed_menu(self):
        items = normalize_db_menu(
            [
                {"name": "Sold Out", "price": 5, "is_available": False},
                {"name": "Available", "price": 7.5, "is_popular": True},
            ]
        )
        assert [i["name"] for i in items] == ["Available"]
        assert items[0]["is_popular"] is True

    def test_category_name_wins_over_raw_category(self):
        items = normalize_db_menu(
            [{"name": "A", "price": 1, "category_name": "Minuman Panas"}]
        )
        assert items[0]["category"] == "Minuman Panas"

    def test_none_and_garbage_rows_are_skipped(self):
        assert normalize_db_menu(None) == []
        assert normalize_db_menu([None, "x", {"price": 1}]) == []


class TestFormatting:
    def test_price_shapes(self):
        assert format_price("8.50") == "RM 8.50"
        assert format_price(3) == "RM 3.00"
        assert format_price("RM 12") == "RM 12.00"
        assert format_price("12,50") == "RM 12.50"
        assert format_price(None) == ""
        assert format_price("ikut pasaran") == "ikut pasaran"

    def test_grouping_preserves_first_seen_category_order(self):
        groups = group_by_category(
            [
                {"name": "a", "category": "Nasi"},
                {"name": "b", "category": "Minuman"},
                {"name": "c", "category": "Nasi"},
            ]
        )
        assert [g[0] for g in groups] == ["Nasi", "Minuman"]
        assert [i["name"] for i in groups[0][1]] == ["a", "c"]


class TestMenuPoster:
    ITEMS = [
        {"name": "Nasi Lemak", "price": "8.50", "category": "Nasi", "is_popular": True},
        {"name": "Teh Tarik", "price": 3, "category": "Minuman", "description": "Panas / ais"},
    ]

    def test_carries_real_items_prices_and_palette(self):
        html = build_menu_poster_html(
            "Kedai Ali", self.ITEMS, "https://kedaiali.binaapp.my", PALETTE
        )
        assert "Nasi Lemak" in html and "RM 8.50" in html
        assert "Teh Tarik" in html and "RM 3.00" in html
        assert "#2563EB" in html
        assert "★" in html, "popular items are starred"
        assert "<svg" in html, "footer QR must be rendered offline"

    def test_escapes_hostile_item_names(self):
        html = build_menu_poster_html(
            "K",
            [{"name": "<script>alert(1)</script>", "price": 1}],
            "https://k.binaapp.my",
            PALETTE,
        )
        assert "<script>alert(1)</script>" not in html

    def test_language_toggle(self):
        en = build_menu_poster_html("K", self.ITEMS, "https://k.binaapp.my", PALETTE, "en")
        assert "Menu &amp; Prices" in en


# ---------------------------------------------------------------------------
# Review poster
# ---------------------------------------------------------------------------

class TestReviewUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://g.page/r/AbCdEf123/review",
            "https://google.com/maps/place/x",
            "https://www.google.com.my/search?q=kedai+ali",
            "https://maps.app.goo.gl/abc123",
            "https://search.google.com/local/writereview?placeid=X",
        ],
    )
    def test_google_family_urls_are_accepted(self, url):
        assert is_valid_review_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.com/phish",
            "http://google.com/maps",  # not https
            "https://notgoogle.com/g.page/",
            "https://google.evil.com/",
            "",
            "https://g.page/" + "x" * 500,  # over length cap
        ],
    )
    def test_everything_else_is_rejected(self, url):
        assert not is_valid_review_url(url)

    def test_poster_carries_the_ask(self):
        html = build_review_poster_html(
            "Kedai Ali", "https://g.page/r/x/review", PALETTE, "ms"
        )
        assert "Beri Kami 5 Bintang" in html
        assert "<svg" in html


# ---------------------------------------------------------------------------
# WhatsApp poster
# ---------------------------------------------------------------------------

class TestWhatsAppPoster:
    def test_wa_link_shape(self):
        link = build_wa_link("+60123456789", "Hai! (Meja 5)")
        assert link == "https://wa.me/60123456789?text=Hai%21%20%28Meja%205%29"

    def test_wa_link_without_message(self):
        assert build_wa_link("+60123456789", "") == "https://wa.me/60123456789"

    def test_no_digits_no_link(self):
        assert build_wa_link("", "x") == ""

    def test_default_message_carries_the_table(self):
        assert "(Meja 7)" in default_order_message("Kedai", "7", "ms")
        assert "(Table 7)" in default_order_message("Kedai", "7", "en")
        assert "Meja" not in default_order_message("Kedai", None, "ms")

    def test_poster_kicker_names_the_table(self):
        html = build_whatsapp_poster_html(
            "Kedai Ali", "+60123456789", PALETTE, "ms", table="5"
        )
        assert "Meja 5" in html
        assert "+60123456789" in html
        assert "<svg" in html


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _row(**overrides):
    row = {
        "id": "ws-1",
        "user_id": "test-user-id-12345",
        "name": "Kedai Ali",
        "subdomain": "kedaiali",
        "status": "published",
        "html_content": _page_with_menu(
            [{"name": "Nasi Lemak", "price": "8.50", "category": "Nasi"}]
        ).replace(
            "<head>",
            '<head><a href="https://wa.me/60123456789">w</a>'
            "<style>:root{--primary-color:#2563EB;}</style>",
        ),
    }
    row.update(overrides)
    return row


@pytest.fixture
def kit_patches():
    with patch(
        "app.api.v1.endpoints.site_qr.supabase_service.get_website",
        new=AsyncMock(return_value=_row()),
    ) as get_website, patch(
        "app.api.v1.endpoints.business_kit.supabase_service.select_records",
        new=AsyncMock(return_value=None),
    ) as select_records:
        yield {"get_website": get_website, "select_records": select_records}


class TestEndpoints:
    def test_menu_poster_from_the_baked_page_menu(
        self, client, auth_headers, kit_patches
    ):
        resp = client.get("/api/v1/websites/ws-1/menu-poster.html", headers=auth_headers)
        assert resp.status_code == 200
        assert "Nasi Lemak" in resp.text and "RM 8.50" in resp.text
        assert "#2563EB" in resp.text, "poster inherits the site's own primary"

    def test_menu_poster_prefers_db_rows_when_present(
        self, client, auth_headers, kit_patches
    ):
        def by_table(table, filters=None):
            if table == "menu_items":
                return [
                    {"name": "Laksa Johor", "price": 12, "category_id": "c1"},
                    {"name": "Off Menu", "price": 9, "is_available": False},
                ]
            return [{"id": "c1", "name": "Ikonik"}]

        kit_patches["select_records"].side_effect = by_table
        resp = client.get("/api/v1/websites/ws-1/menu-poster.html", headers=auth_headers)
        assert resp.status_code == 200
        assert "Laksa Johor" in resp.text and "Ikonik" in resp.text
        assert "Off Menu" not in resp.text
        assert "Nasi Lemak" not in resp.text, "DB menu replaces the baked one"

    def test_no_menu_anywhere_is_a_clear_409(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(
            html_content="<html><head></head><body>no menu</body></html>"
        )
        resp = client.get("/api/v1/websites/ws-1/menu-poster.html", headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "no_menu_found"

    def test_review_poster_round_trip(self, client, auth_headers, kit_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/review-poster.html"
            "?review_url=https%3A%2F%2Fg.page%2Fr%2FAbC%2Freview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "Beri Kami 5 Bintang" in resp.text

    def test_non_google_review_url_is_rejected(self, client, auth_headers, kit_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/review-poster.html"
            "?review_url=https%3A%2F%2Fevil.com%2Fx",
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "invalid_review_url"

    def test_whatsapp_poster_uses_the_pages_own_number(
        self, client, auth_headers, kit_patches
    ):
        resp = client.get(
            "/api/v1/websites/ws-1/whatsapp-poster.html?table=5", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "Meja 5" in resp.text
        assert "+60123456789" in resp.text

    def test_whatsapp_poster_without_a_number_is_a_clear_409(
        self, client, auth_headers, kit_patches
    ):
        kit_patches["get_website"].return_value = _row(
            html_content="<html><head></head><body>no contact</body></html>"
        )
        resp = client.get(
            "/api/v1/websites/ws-1/whatsapp-poster.html", headers=auth_headers
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "no_phone_found"

    def test_all_surfaces_require_auth(self, client):
        for path in (
            "menu-poster.html",
            "review-poster.html?review_url=https%3A%2F%2Fg.page%2Fx",
            "whatsapp-poster.html",
        ):
            assert client.get(f"/api/v1/websites/ws-1/{path}").status_code in (401, 403)

    def test_other_peoples_sites_are_403(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(user_id="someone-else")
        resp = client.get("/api/v1/websites/ws-1/menu-poster.html", headers=auth_headers)
        assert resp.status_code == 403

    def test_unpublished_site_is_a_clear_409(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(subdomain=None)
        resp = client.get("/api/v1/websites/ws-1/menu-poster.html", headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "not_published"


# ---------------------------------------------------------------------------
# Open badge — serve-time injection
# ---------------------------------------------------------------------------

class TestOpenBadge:
    HOURS_PAGE = (
        '<html lang="ms"><head><script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "Restaurant",
                "openingHoursSpecification": [
                    {
                        "@type": "OpeningHoursSpecification",
                        "dayOfWeek": ["Monday", "Tuesday"],
                        "opens": "09:00",
                        "closes": "22:00",
                    }
                ],
            }
        )
        + "</script></head><body>hi</body></html>"
    )

    def test_injected_only_when_the_page_carries_hours(self):
        from app.middleware.subdomain import _inject_open_badge

        out = _inject_open_badge(self.HOURS_PAGE)
        assert "BinaApp Open Badge" in out
        assert "binaapp-open-badge" in out

        plain = "<html><body>no hours here</body></html>"
        assert _inject_open_badge(plain) == plain

    def test_idempotent(self):
        from app.middleware.subdomain import _inject_open_badge

        once = _inject_open_badge(self.HOURS_PAGE)
        assert _inject_open_badge(once) == once

    def test_reads_hours_from_the_page_not_the_server(self):
        # The script must compute state client-side (Asia/Kuala_Lumpur) —
        # the injected block therefore carries the timezone and no baked
        # open/closed verdict.
        from app.middleware.subdomain import _OPEN_BADGE_SCRIPT

        assert "Asia/Kuala_Lumpur" in _OPEN_BADGE_SCRIPT
        assert "openingHoursSpecification" in _OPEN_BADGE_SCRIPT
        assert "Buka sekarang" in _OPEN_BADGE_SCRIPT and "Open now" in _OPEN_BADGE_SCRIPT
