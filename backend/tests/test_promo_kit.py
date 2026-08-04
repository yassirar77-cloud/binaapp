"""Tests for the Promo Kit — share/story images, vCard QR, Wi-Fi QR.

The properties that matter mirror the QR toolkit's:

  1. Everything renders OFFLINE (Pillow + segno) — no network, no AI call.
  2. What goes on a poster or into a QR is the merchant's own data — the
     phone number must come from their published page, the palette from
     the page they are serving, and Wi-Fi credentials must never be stored.
  3. The public share card exists for crawlers, so it must be reachable
     without auth on the subdomain host, but 404 for locked/gated sites.
"""

import io
from unittest.mock import AsyncMock, patch

import pytest

from app.services.promo_kit import (
    build_vcard,
    build_vcard_poster_html,
    build_wifi_payload,
    build_wifi_poster_html,
    extract_email,
    extract_phone,
    extract_tagline,
)
from app.services.share_card import (
    PIL_AVAILABLE,
    SHARE_CARD_SIZE,
    STORY_CARD_SIZE,
    render_share_card,
    render_story_card,
)

pytestmark = pytest.mark.skipif(
    not PIL_AVAILABLE, reason="Pillow (image renderer) not installed"
)

PALETTE = {
    "primary": "#2563EB",
    "surface": "#FFFFFF",
    "background": "#F8FAFF",
    "text": "#0F172A",
    "text_muted": "#64748B",
}


def _png_size(png: bytes):
    from PIL import Image

    return Image.open(io.BytesIO(png)).size


# ---------------------------------------------------------------------------
# Image renderers
# ---------------------------------------------------------------------------

class TestShareCard:
    def test_renders_a_png_at_og_dimensions(self):
        png = render_share_card("Kedai Ali", "https://kedaiali.binaapp.my", PALETTE)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert _png_size(png) == SHARE_CARD_SIZE

    def test_renders_offline_without_any_network_call(self):
        with patch("httpx.Client", side_effect=AssertionError("network!")), patch(
            "httpx.AsyncClient", side_effect=AssertionError("network!")
        ):
            assert render_share_card("Kedai Ali", "https://a.binaapp.my", PALETTE)

    def test_survives_missing_palette_and_name(self):
        assert render_share_card("", "https://a.binaapp.my", None)
        assert render_share_card("Kedai", "https://a.binaapp.my", {})

    def test_survives_an_absurdly_long_name_and_tagline(self):
        png = render_share_card(
            "Restoran Selera Kampung Warisan Bonda Sri Menanti dan Anak-Anak Sdn Bhd",
            "https://selerakampungwarisanbonda.binaapp.my",
            PALETTE,
            tagline="Masakan kampung asli " * 20,
        )
        assert _png_size(png) == SHARE_CARD_SIZE

    def test_hostile_palette_values_fall_back_instead_of_crashing(self):
        png = render_share_card(
            "Kedai",
            "https://a.binaapp.my",
            {"primary": "<script>", "background": "javascript:", "text": "zzz"},
        )
        assert _png_size(png) == SHARE_CARD_SIZE

    def test_different_palettes_produce_different_cards(self):
        a = render_share_card("Kedai", "https://a.binaapp.my", PALETTE)
        b = render_share_card(
            "Kedai", "https://a.binaapp.my", {**PALETTE, "primary": "#DC2626"}
        )
        assert a != b


class TestStoryCard:
    def test_renders_a_png_at_story_dimensions(self):
        png = render_story_card("Kedai Ali", "https://kedaiali.binaapp.my", PALETTE)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert _png_size(png) == STORY_CARD_SIZE

    def test_language_changes_the_copy_but_not_the_size(self):
        ms = render_story_card("K", "https://a.binaapp.my", PALETTE, language="ms")
        en = render_story_card("K", "https://a.binaapp.my", PALETTE, language="en")
        assert ms != en
        assert _png_size(ms) == _png_size(en) == STORY_CARD_SIZE


# ---------------------------------------------------------------------------
# Contact extraction — only what the page itself advertises
# ---------------------------------------------------------------------------

class TestExtraction:
    def test_wa_me_number_wins(self):
        html = (
            '<a href="tel:03-1234567">call</a>'
            '<a href="https://wa.me/60123456789?text=hi">order</a>'
        )
        assert extract_phone(html) == "+60123456789"

    def test_whatsapp_api_link_is_understood(self):
        html = '<a href="https://api.whatsapp.com/send?phone=60198765432">w</a>'
        assert extract_phone(html) == "+60198765432"

    def test_tel_link_is_the_fallback(self):
        assert extract_phone('<a href="tel:+603-2168 8888">call</a>') == "+60321688888"

    def test_no_number_means_none_not_an_invented_one(self):
        assert extract_phone("<p>no contact here</p>") is None
        assert extract_phone("") is None

    def test_email_from_mailto(self):
        assert extract_email('<a href="mailto:ali@kedai.my">e</a>') == "ali@kedai.my"

    def test_tagline_is_the_pages_own_meta_description(self):
        html = '<meta name="description" content="Kopi tarik legenda Melaka">'
        assert extract_tagline(html) == "Kopi tarik legenda Melaka"

    def test_reversed_attribute_order_still_matches(self):
        html = '<meta content="Nasi ayam Hainan asli di Shah Alam" name="description">'
        assert extract_tagline(html) == "Nasi ayam Hainan asli di Shah Alam"


# ---------------------------------------------------------------------------
# QR payloads — must scan correctly on real phones
# ---------------------------------------------------------------------------

class TestVcard:
    def test_minimal_shape(self):
        v = build_vcard("Kedai Ali", "+60123456789", "https://kedaiali.binaapp.my")
        assert v.startswith("BEGIN:VCARD\r\nVERSION:3.0")
        assert "FN:Kedai Ali" in v
        assert "TEL;TYPE=CELL:+60123456789" in v
        assert "URL:https://kedaiali.binaapp.my" in v
        assert v.rstrip().endswith("END:VCARD")

    def test_separators_in_the_name_are_escaped(self):
        v = build_vcard("Kedai; Ali, Anak")
        assert "FN:Kedai\\; Ali\\, Anak" in v

    def test_newlines_cannot_smuggle_extra_vcard_fields(self):
        v = build_vcard("Kedai\nNOTE:injected")
        assert "\nNOTE:" not in v
        assert "\\nNOTE:injected" in v

    def test_optional_fields_are_simply_absent(self):
        v = build_vcard("Kedai")
        assert "TEL" not in v and "EMAIL" not in v and "URL" not in v


class TestWifiPayload:
    def test_wpa_shape(self):
        assert (
            build_wifi_payload("KedaiAli", "rahsia123")
            == "WIFI:T:WPA;S:KedaiAli;P:rahsia123;;"
        )

    def test_special_characters_are_escaped(self):
        payload = build_wifi_payload("Kedai;Ali", 'p@ss:word,1"2\\3')
        assert "S:Kedai\\;Ali;" in payload
        assert 'P:p@ss\\:word\\,1\\"2\\\\3;' in payload

    def test_empty_password_forces_nopass(self):
        assert build_wifi_payload("OpenNet", "") == "WIFI:T:nopass;S:OpenNet;;"
        assert build_wifi_payload("OpenNet", "", "WPA") == "WIFI:T:nopass;S:OpenNet;;"

    def test_unknown_security_falls_back_to_wpa(self):
        assert build_wifi_payload("X", "pw", "TELNET").startswith("WIFI:T:WPA;")


# ---------------------------------------------------------------------------
# Posters
# ---------------------------------------------------------------------------

class TestPosters:
    def test_vcard_poster_wears_the_site_palette(self):
        vcard = build_vcard("Kedai Ali", "+60123456789")
        html = build_vcard_poster_html("Kedai Ali", vcard, "+60123456789", PALETTE)
        assert "#2563EB" in html
        assert "Kedai Ali" in html
        assert "<svg" in html, "QR must be rendered inline, not remote"
        assert "+60123456789" in html

    def test_wifi_poster_shows_credentials_for_printing(self):
        html = build_wifi_poster_html("Kedai Ali", "KedaiAli_5G", "rahsia123")
        assert "KedaiAli_5G" in html
        assert "rahsia123" in html
        assert "<svg" in html

    def test_wifi_poster_can_hide_the_password_text(self):
        html = build_wifi_poster_html(
            "Kedai Ali", "KedaiAli_5G", "rahsia123", show_password=False
        )
        assert "rahsia123" not in html

    def test_poster_escapes_hostile_ssid(self):
        html = build_wifi_poster_html("K", '<script>alert(1)</script>', "pw")
        assert "<script>alert(1)</script>" not in html

    def test_language_toggle(self):
        ms = build_wifi_poster_html("K", "Net", "pw", language="ms")
        en = build_wifi_poster_html("K", "Net", "pw", language="en")
        assert "Wi-Fi Percuma" in ms
        assert "Free Wi-Fi" in en


# ---------------------------------------------------------------------------
# Endpoints — same gate discipline as the QR toolkit
# ---------------------------------------------------------------------------

def _row(**overrides):
    row = {
        "id": "ws-1",
        "user_id": "test-user-id-12345",
        "name": "Kedai Ali",
        "subdomain": "kedaiali",
        "status": "published",
        "html_content": (
            "<html><head>"
            '<meta name="description" content="Kopi tarik legenda Melaka">'
            "<style>:root{--primary-color:#2563EB;--bg-color:#F8FAFF;}</style>"
            '</head><body><a href="https://wa.me/60123456789">order</a></body></html>'
        ),
    }
    row.update(overrides)
    return row


@pytest.fixture
def kit_patches():
    # promo_kit endpoints reuse site_qr's owner+published gate, so the
    # supabase call to patch lives in the site_qr module.
    with patch(
        "app.api.v1.endpoints.site_qr.supabase_service.get_website",
        new=AsyncMock(return_value=_row()),
    ) as get_website:
        yield {"get_website": get_website}


class TestEndpoints:
    def test_share_card_endpoint_serves_a_png(self, client, auth_headers, kit_patches):
        resp = client.get("/api/v1/websites/ws-1/share-card.png", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert _png_size(resp.content) == SHARE_CARD_SIZE

    def test_story_endpoint_serves_a_png(self, client, auth_headers, kit_patches):
        resp = client.get("/api/v1/websites/ws-1/story.png", headers=auth_headers)
        assert resp.status_code == 200
        assert _png_size(resp.content) == STORY_CARD_SIZE

    def test_vcard_qr_uses_the_pages_own_number(
        self, client, auth_headers, kit_patches
    ):
        from app.services.qr_service import qr_svg
        from app.services.qr_service import build_site_url
        from app.core.config import settings

        resp = client.get("/api/v1/websites/ws-1/vcard-qr.svg", headers=auth_headers)
        assert resp.status_code == 200
        expected_vcard = build_vcard(
            "Kedai Ali",
            phone="+60123456789",
            url=build_site_url("kedaiali", settings.MAIN_DOMAIN),
        )
        assert resp.text == qr_svg(expected_vcard, scale=8, border=2)

    def test_vcard_without_a_number_anywhere_is_a_clear_409(
        self, client, auth_headers, kit_patches
    ):
        kit_patches["get_website"].return_value = _row(
            html_content="<html><head></head><body>no contact</body></html>"
        )
        resp = client.get("/api/v1/websites/ws-1/vcard-qr.svg", headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "no_phone_found"

    def test_vcard_phone_override(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(
            html_content="<html><head></head><body>no contact</body></html>"
        )
        resp = client.get(
            "/api/v1/websites/ws-1/vcard-poster.html?phone=%2B60111222333",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "+60111222333" in resp.text

    def test_wifi_poster_round_trip(self, client, auth_headers, kit_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/wifi-poster.html?ssid=KedaiAli_5G&password=rahsia123",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "KedaiAli_5G" in resp.text
        assert "rahsia123" in resp.text
        assert resp.headers["cache-control"] == "private, no-store", (
            "a page carrying Wi-Fi credentials must never enter a shared cache"
        )

    def test_wifi_ssid_is_required_and_bounded(self, client, auth_headers, kit_patches):
        assert (
            client.get(
                "/api/v1/websites/ws-1/wifi-poster.html", headers=auth_headers
            ).status_code
            == 422
        )
        assert (
            client.get(
                "/api/v1/websites/ws-1/wifi-poster.html?ssid=" + "x" * 33,
                headers=auth_headers,
            ).status_code
            == 422
        )

    def test_all_surfaces_require_auth(self, client):
        for path in (
            "share-card.png",
            "story.png",
            "vcard-qr.svg",
            "vcard-poster.html",
            "wifi-poster.html?ssid=x",
        ):
            assert client.get(f"/api/v1/websites/ws-1/{path}").status_code in (401, 403)

    def test_other_peoples_sites_are_403(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(user_id="someone-else")
        resp = client.get("/api/v1/websites/ws-1/share-card.png", headers=auth_headers)
        assert resp.status_code == 403

    def test_unpublished_site_is_a_clear_409(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(subdomain=None)
        resp = client.get("/api/v1/websites/ws-1/story.png", headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "not_published"


# ---------------------------------------------------------------------------
# Serve path — the public share card and the injected meta tags
# ---------------------------------------------------------------------------

class TestServePath:
    HTML = (
        "<html><head><title>Kedai Ali</title>"
        '<meta name="description" content="Kopi tarik legenda Melaka">'
        "<style>:root{--primary-color:#2563EB;}</style>"
        "</head><body>hi</body></html>"
    )

    def setup_method(self):
        from app.middleware import subdomain as m

        m._share_card_cache.clear()

    def test_share_card_response_is_a_png(self):
        from app.middleware.subdomain import _share_card_response

        resp = _share_card_response("kedaiali", "Kedai Ali", self.HTML)
        assert resp.status_code == 200
        assert resp.media_type == "image/png"
        assert _png_size(resp.body) == SHARE_CARD_SIZE

    def test_share_card_is_cached_per_subdomain(self):
        from app.middleware import subdomain as m

        first = m._share_card_response("kedaiali", "Kedai Ali", self.HTML)
        with patch(
            "app.services.share_card.render_share_card",
            side_effect=AssertionError("re-rendered despite cache"),
        ):
            second = m._share_card_response("kedaiali", "Kedai Ali", self.HTML)
        assert first.body == second.body

    def test_render_failure_is_a_404_never_a_crash(self):
        from app.middleware import subdomain as m

        with patch(
            "app.services.share_card.render_share_card", return_value=b""
        ):
            resp = m._share_card_response("kedaiali", "Kedai Ali", self.HTML)
        assert resp.status_code == 404

    def test_meta_injection_points_at_the_share_card(self):
        from app.middleware.subdomain import _inject_social_meta

        out = _inject_social_meta(self.HTML, "kedaiali")
        assert 'property="og:image"' in out
        assert "kedaiali" in out and "/share-card.png" in out
        assert 'name="twitter:card" content="summary_large_image"' in out

    def test_meta_injection_is_idempotent(self):
        from app.middleware.subdomain import _inject_social_meta

        once = _inject_social_meta(self.HTML, "kedaiali")
        twice = _inject_social_meta(once, "kedaiali")
        assert once.count("og:image") == twice.count("og:image")

    def test_an_existing_og_image_is_never_overridden(self):
        from app.middleware.subdomain import _inject_social_meta

        html = (
            "<html><head>"
            '<meta property="og:image" content="https://cdn.example/hero.jpg">'
            "</head><body></body></html>"
        )
        out = _inject_social_meta(html, "kedaiali")
        assert "share-card.png" not in out
        assert "hero.jpg" in out

    def test_page_without_head_is_left_alone(self):
        from app.middleware.subdomain import _inject_social_meta

        assert _inject_social_meta("<body>x</body>", "kedaiali") == "<body>x</body>"
