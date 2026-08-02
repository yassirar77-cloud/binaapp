"""Tests for the QR toolkit — offline codes and printable posters.

Two properties matter:

  1. The QR is rendered LOCALLY. Every published site used to load its footer
     QR from api.qrserver.com, putting a third party on the render path of a
     merchant's own page. Nothing here may reach out over the network.
  2. Whatever is printed must be scannable and must point at the real
     published URL — a poster with a wrong or unscannable code is worse than
     no poster, because it goes on a wall.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.qr_service import (
    SEGNO_AVAILABLE,
    build_poster_html,
    build_site_url,
    qr_data_uri,
    qr_svg,
    remote_qr_url,
    with_query,
)


pytestmark = pytest.mark.skipif(
    not SEGNO_AVAILABLE, reason="segno (QR encoder) not installed"
)


class TestUrlBuilding:
    def test_plain_site_url(self):
        assert build_site_url("kedaiali", "binaapp.my") == "https://kedaiali.binaapp.my"

    def test_table_marker_makes_each_table_a_distinct_url(self):
        five = build_site_url("kedaiali", "binaapp.my", table="5")
        six = build_site_url("kedaiali", "binaapp.my", table="6")
        assert five == "https://kedaiali.binaapp.my/?meja=5"
        assert five != six

    def test_campaign_marker(self):
        assert (
            build_site_url("kedaiali", "binaapp.my", campaign="raya")
            == "https://kedaiali.binaapp.my/?kempen=raya"
        )

    def test_no_subdomain_yields_nothing(self):
        assert build_site_url("", "binaapp.my") == ""

    def test_with_query_preserves_existing_params(self):
        assert with_query("https://x.my/?a=1", src="qr") == "https://x.my/?a=1&src=qr"


class TestSvgRendering:
    def test_renders_a_standalone_svg(self):
        svg = qr_svg("https://kedaiali.binaapp.my")
        assert svg.startswith("<svg")
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg
        assert svg.rstrip().endswith("</svg>")

    def test_inline_form_omits_the_xmlns(self):
        svg = qr_svg("https://kedaiali.binaapp.my", standalone=False)
        assert svg.startswith("<svg")
        assert "xmlns=" not in svg

    def test_renders_offline_without_any_network_call(self):
        # If the encoder ever reached for the network, this would blow up.
        with patch("httpx.Client", side_effect=AssertionError("network!")), patch(
            "httpx.AsyncClient", side_effect=AssertionError("network!")
        ):
            assert qr_svg("https://kedaiali.binaapp.my")

    def test_different_payloads_produce_different_codes(self):
        assert qr_svg("https://a.binaapp.my") != qr_svg("https://b.binaapp.my")

    def test_same_payload_is_byte_identical(self):
        assert qr_svg("https://a.binaapp.my") == qr_svg("https://a.binaapp.my")

    def test_empty_payload_renders_nothing(self):
        assert qr_svg("") == ""

    def test_colours_are_applied(self):
        svg = qr_svg("https://a.binaapp.my", dark="#2563EB")
        assert "#2563eb" in svg.lower()

    def test_a_bogus_colour_falls_back_instead_of_injecting(self):
        svg = qr_svg("https://a.binaapp.my", dark='"><script>alert(1)</script>')
        assert "<script>" not in svg
        assert "#111827" in svg.lower()

    def test_scale_is_clamped_so_a_caller_cannot_ask_for_a_100mb_svg(self):
        def width(svg):
            return int(svg.split('width="')[1].split('"')[0])

        assert width(qr_svg("https://a.binaapp.my", scale=0)) > 0
        assert width(qr_svg("https://a.binaapp.my", scale=9999)) == width(
            qr_svg("https://a.binaapp.my", scale=40)
        )

    def test_data_uri_is_base64_and_attribute_safe(self):
        uri = qr_data_uri("https://kedaiali.binaapp.my")
        assert uri.startswith("data:image/svg+xml;base64,")
        assert '"' not in uri and "<" not in uri

    def test_remote_url_is_only_a_fallback_shape(self):
        url = remote_qr_url("https://kedaiali.binaapp.my")
        assert url.startswith("https://api.qrserver.com/")
        assert "%3A%2F%2F" in url, "payload must be percent-encoded"


class TestPoster:
    PALETTE = {
        "primary": "#2563EB",
        "surface": "#FFFFFF",
        "background": "#F8FAFF",
        "text": "#0F172A",
        "text_muted": "#64748B",
    }

    def test_poster_is_a_complete_printable_document(self):
        html = build_poster_html("Kedai Ali", "https://kedaiali.binaapp.my", self.PALETTE)
        assert html.startswith("<!DOCTYPE html>")
        assert html.rstrip().endswith("</html>")
        assert "@page" in html and "A4" in html
        assert "@media print" in html

    def test_poster_carries_an_inline_qr_not_a_remote_image(self):
        html = build_poster_html("Kedai Ali", "https://kedaiali.binaapp.my", self.PALETTE)
        assert "<svg" in html
        assert "api.qrserver.com" not in html

    def test_poster_wears_the_site_palette(self):
        html = build_poster_html("Kedai Ali", "https://kedaiali.binaapp.my", self.PALETTE)
        assert "#2563EB" in html
        assert "#F8FAFF" in html

    def test_poster_shows_the_real_url_and_business_name(self):
        html = build_poster_html("Kedai Ali", "https://kedaiali.binaapp.my", self.PALETTE)
        assert "Kedai Ali" in html
        assert "kedaiali.binaapp.my" in html

    def test_table_mode_labels_the_table(self):
        html = build_poster_html(
            "Kedai Ali", "https://kedaiali.binaapp.my/?meja=5", self.PALETTE, table="5"
        )
        assert "Meja 5" in html

    def test_malay_is_the_default_language(self):
        html = build_poster_html("Kedai Ali", "https://kedaiali.binaapp.my", self.PALETTE)
        assert "Imbas" in html
        assert "Scan To Visit" not in html

    def test_english_variant(self):
        html = build_poster_html(
            "Kedai Ali", "https://kedaiali.binaapp.my", self.PALETTE, language="en"
        )
        assert "Scan To Visit" in html

    def test_business_name_is_escaped(self):
        html = build_poster_html(
            "<script>alert(1)</script>", "https://x.binaapp.my", self.PALETTE
        )
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html

    def test_custom_headline_is_escaped_too(self):
        html = build_poster_html(
            "Kedai Ali",
            "https://x.binaapp.my",
            self.PALETTE,
            headline='" onload="alert(1)',
        )
        assert 'onload="alert(1)' not in html

    def test_label_colour_stays_readable_on_a_pale_primary(self):
        html = build_poster_html(
            "Kedai Ali", "https://x.binaapp.my", {"primary": "#FDE047"}
        )
        # Yellow chip -> dark text, never white-on-yellow.
        assert "color: #111827" in html

    def test_poster_invents_nothing(self):
        html = build_poster_html("Kedai Ali", "https://x.binaapp.my", self.PALETTE)
        for fabrication in ("Est.", "★", "5.0", "Halal", "Best "):
            assert fabrication not in html

    def test_missing_palette_falls_back_to_defaults(self):
        html = build_poster_html("Kedai Ali", "https://x.binaapp.my", None)
        assert "<svg" in html and "#EA580C" in html


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
        "html_content": (
            "<html><head><style>:root{--primary-color:#2563EB;--bg-color:#F8FAFF;}"
            "</style></head><body>hi</body></html>"
        ),
    }
    row.update(overrides)
    return row


@pytest.fixture
def qr_patches():
    with patch(
        "app.api.v1.endpoints.site_qr.supabase_service.get_website",
        new=AsyncMock(return_value=_row()),
    ) as get_website:
        yield {"get_website": get_website}


class TestQrEndpoints:
    def test_svg_endpoint_serves_an_image(self, client, auth_headers, qr_patches):
        resp = client.get("/api/v1/websites/ws-1/qr.svg", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/svg+xml")
        assert resp.text.startswith("<svg")

    def test_it_encodes_the_real_published_url(self, client, auth_headers, qr_patches):
        from app.core.config import settings

        served = client.get("/api/v1/websites/ws-1/qr.svg", headers=auth_headers).text
        expected = qr_svg(
            build_site_url("kedaiali", settings.MAIN_DOMAIN), scale=8, border=2
        )
        assert served == expected

    def test_table_qr_encodes_the_table_url(self, client, auth_headers, qr_patches):
        from app.core.config import settings

        plain = client.get("/api/v1/websites/ws-1/qr.svg", headers=auth_headers).text
        table = client.get(
            "/api/v1/websites/ws-1/qr.svg?table=5", headers=auth_headers
        ).text
        assert plain != table
        assert table == qr_svg(
            build_site_url("kedaiali", settings.MAIN_DOMAIN, table="5"),
            scale=8,
            border=2,
        )

    def test_poster_endpoint_returns_html_in_the_site_palette(
        self, client, auth_headers, qr_patches
    ):
        resp = client.get("/api/v1/websites/ws-1/qr-poster.html", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/html")
        assert "#2563EB" in resp.text, "poster inherits the site's own primary"
        assert "Kedai Ali" in resp.text

    def test_unpublished_site_is_a_clear_409(self, client, auth_headers, qr_patches):
        qr_patches["get_website"].return_value = _row(subdomain=None)
        resp = client.get("/api/v1/websites/ws-1/qr.svg", headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "not_published"

    def test_other_peoples_sites_are_403(self, client, auth_headers, qr_patches):
        qr_patches["get_website"].return_value = _row(user_id="someone-else")
        resp = client.get("/api/v1/websites/ws-1/qr.svg", headers=auth_headers)
        assert resp.status_code == 403

    def test_missing_site_is_404(self, client, auth_headers, qr_patches):
        qr_patches["get_website"].return_value = None
        resp = client.get("/api/v1/websites/ws-1/qr.svg", headers=auth_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        assert client.get("/api/v1/websites/ws-1/qr.svg").status_code in (401, 403)

    def test_out_of_range_scale_is_rejected(self, client, auth_headers, qr_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/qr.svg?scale=999", headers=auth_headers
        )
        assert resp.status_code == 422

    def test_language_is_validated(self, client, auth_headers, qr_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/qr-poster.html?language=klingon", headers=auth_headers
        )
        assert resp.status_code == 422
