"""Tests for the Counter Kit — loyalty stamp cards, business cards,
voucher sheets and the holiday-closure notice.

What matters:

  1. Everything printed is the merchant's own data, escaped — offer text,
     reward lines and dates are printed verbatim but can never smuggle
     markup onto a page the merchant will open and print.
  2. The stamp count is clamped to something a physical card can hold, and
     the reward stamp is always the last one.
  3. The endpoints share the family gate exactly: 401 unauthenticated,
     403 not-yours, 409 unpublished, and required params (voucher offer,
     reopen date) are enforced by FastAPI's own 422.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.counter_kit import (
    build_business_cards_html,
    build_closure_poster_html,
    build_loyalty_card_html,
    build_voucher_sheet_html,
)

PALETTE = {
    "primary": "#2563EB",
    "surface": "#FFFFFF",
    "background": "#F8FAFF",
    "text": "#0F172A",
    "text_muted": "#64748B",
}

URL = "https://kedaiali.binaapp.my"


# ---------------------------------------------------------------------------
# Loyalty cards
# ---------------------------------------------------------------------------

class TestLoyaltyCards:
    def test_sheet_carries_eight_cards_with_the_requested_stamps(self):
        html = build_loyalty_card_html("Kedai Ali", URL, stamps=8, palette=PALETTE)
        assert html.count('class="card"') == 8
        # 7 numbered stamps + 1 gift stamp per card.
        assert html.count('class="stamp gift"') == 8
        assert html.count('class="stamp"') == 8 * 7

    def test_stamp_count_is_clamped_to_a_printable_range(self):
        assert build_loyalty_card_html("K", URL, stamps=999).count("stamp gift") == 8
        html_small = build_loyalty_card_html("K", URL, stamps=1)
        # Clamped up to 4: 3 numbered + the gift.
        assert html_small.count('class="stamp"') == 8 * 3

    def test_default_reward_names_the_free_purchase(self):
        assert "ke-10 PERCUMA" in build_loyalty_card_html("K", URL, stamps=10)
        assert "10th purchase is FREE" in build_loyalty_card_html(
            "K", URL, stamps=10, language="en"
        )

    def test_custom_reward_is_printed_escaped(self):
        html = build_loyalty_card_html(
            "K", URL, reward='Teh <script>alert("x")</script> percuma'
        )
        assert "<script>" not in html
        assert "Teh &lt;script&gt;" in html

    def test_carries_palette_and_site_url(self):
        html = build_loyalty_card_html("Kedai Ali", URL, palette=PALETTE)
        assert "#2563EB" in html
        assert "kedaiali.binaapp.my" in html


# ---------------------------------------------------------------------------
# Business cards
# ---------------------------------------------------------------------------

class TestBusinessCards:
    def test_sheet_carries_ten_cards_with_contact_and_qr(self):
        html = build_business_cards_html(
            "Kedai Ali", URL, phone="+60123456789", tagline="Nasi lemak legend",
            palette=PALETTE,
        )
        assert html.count('class="card"') == 10
        assert html.count("+60123456789") == 10
        assert "Nasi lemak legend" in html
        assert "<svg" in html or "<img" in html

    def test_phone_and_tagline_are_optional(self):
        html = build_business_cards_html("Kedai Ali", URL)
        assert 'class="contact"' not in html
        assert 'class="tagline"' not in html
        assert html.count('class="card"') == 10

    def test_hostile_tagline_is_escaped(self):
        html = build_business_cards_html("K", URL, tagline='<img onerror="x">')
        assert "<img onerror" not in html
        assert "&lt;img" in html


# ---------------------------------------------------------------------------
# Voucher sheet
# ---------------------------------------------------------------------------

class TestVoucherSheet:
    def test_sheet_carries_six_vouchers_with_the_offer(self):
        html = build_voucher_sheet_html(
            "Kedai Ali", URL, offer="10% OFF", code="raya10", expiry="30 Jun 2026",
            palette=PALETTE,
        )
        assert html.count('class="voucher"') == 6
        assert html.count("10% OFF") == 6
        assert "RAYA10" in html, "codes print uppercased"
        assert "Sah sehingga 30 Jun 2026" in html

    def test_code_and_expiry_are_optional(self):
        html = build_voucher_sheet_html("K", URL, offer="Teh tarik percuma")
        assert 'class="code"' not in html
        assert "Sah sehingga" not in html
        assert "Satu baucar untuk satu pelanggan" in html

    def test_english_copy(self):
        html = build_voucher_sheet_html(
            "K", URL, offer="Free drink", expiry="30 Jun", language="en"
        )
        assert "Valid until 30 Jun" in html
        assert "One voucher per customer" in html

    def test_hostile_offer_is_escaped(self):
        html = build_voucher_sheet_html("K", URL, offer='<b onclick="x">50%</b>')
        assert "<b onclick" not in html
        assert "&lt;b onclick" in html


# ---------------------------------------------------------------------------
# Closure notice
# ---------------------------------------------------------------------------

class TestClosurePoster:
    def test_carries_dates_note_and_site_qr(self):
        html = build_closure_poster_html(
            "Kedai Ali", URL, reopen="5 Jun", closed_from="1 Jun",
            note="Selamat Hari Raya Aidilfitri", palette=PALETTE,
        )
        assert "Tutup mulai" in html and "1 Jun" in html
        assert "Buka semula" in html and "5 Jun" in html
        assert "Selamat Hari Raya Aidilfitri" in html
        assert "kedaiali.binaapp.my" in html
        assert "#2563EB" in html

    def test_closed_from_is_optional_and_default_note_kicks_in(self):
        html = build_closure_poster_html("K", URL, reopen="selepas Raya")
        assert "Tutup mulai" not in html
        assert "selepas Raya" in html
        assert "Terima kasih atas sokongan anda" in html

    def test_english_copy(self):
        html = build_closure_poster_html("K", URL, reopen="June 5", language="en")
        assert "Holiday Notice" in html
        assert "Reopening" in html
        assert "We're still online" in html

    def test_dates_are_escaped_not_interpreted(self):
        html = build_closure_poster_html("K", URL, reopen='<script>x</script>')
        assert "<script>x</script>" not in html
        assert "&lt;script&gt;" in html


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
            "<html><head>"
            '<meta name="description" content="Nasi lemak paling sedap di Melaka">'
            '<a href="https://wa.me/60123456789">w</a>'
            "<style>:root{--primary-color:#2563EB;}</style>"
            "</head><body>hi</body></html>"
        ),
    }
    row.update(overrides)
    return row


@pytest.fixture
def kit_patches():
    with patch(
        "app.api.v1.endpoints.site_qr.supabase_service.get_website",
        new=AsyncMock(return_value=_row()),
    ) as get_website:
        yield {"get_website": get_website}


class TestEndpoints:
    def test_loyalty_cards_round_trip(self, client, auth_headers, kit_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/loyalty-cards.html?stamps=8", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "Kad Setia" in resp.text
        assert resp.text.count('class="stamp gift"') == 8
        assert "#2563EB" in resp.text, "sheet inherits the site's own primary"

    def test_loyalty_stamps_out_of_range_is_422(self, client, auth_headers, kit_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/loyalty-cards.html?stamps=99", headers=auth_headers
        )
        assert resp.status_code == 422

    def test_business_cards_read_phone_and_tagline_from_the_page(
        self, client, auth_headers, kit_patches
    ):
        resp = client.get(
            "/api/v1/websites/ws-1/business-cards.html", headers=auth_headers
        )
        assert resp.status_code == 200
        assert "+60123456789" in resp.text
        assert "Nasi lemak paling sedap di Melaka" in resp.text

    def test_business_cards_tagline_override_wins(
        self, client, auth_headers, kit_patches
    ):
        resp = client.get(
            "/api/v1/websites/ws-1/business-cards.html?tagline=Custom+line",
            headers=auth_headers,
        )
        assert "Custom line" in resp.text
        assert "Nasi lemak paling sedap" not in resp.text

    def test_voucher_sheet_round_trip(self, client, auth_headers, kit_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/voucher-sheet.html?offer=10%25+OFF&code=raya10",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "10% OFF" in resp.text and "RAYA10" in resp.text

    def test_voucher_sheet_without_an_offer_is_422(
        self, client, auth_headers, kit_patches
    ):
        resp = client.get(
            "/api/v1/websites/ws-1/voucher-sheet.html", headers=auth_headers
        )
        assert resp.status_code == 422

    def test_closure_poster_round_trip(self, client, auth_headers, kit_patches):
        resp = client.get(
            "/api/v1/websites/ws-1/closure-poster.html?reopen=5+Jun&closed_from=1+Jun",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "Notis Cuti" in resp.text
        assert "5 Jun" in resp.text and "1 Jun" in resp.text

    def test_closure_poster_without_reopen_is_422(
        self, client, auth_headers, kit_patches
    ):
        resp = client.get(
            "/api/v1/websites/ws-1/closure-poster.html", headers=auth_headers
        )
        assert resp.status_code == 422

    def test_all_surfaces_require_auth(self, client):
        for path in (
            "loyalty-cards.html",
            "business-cards.html",
            "voucher-sheet.html?offer=x",
            "closure-poster.html?reopen=x",
        ):
            assert client.get(f"/api/v1/websites/ws-1/{path}").status_code in (401, 403)

    def test_other_peoples_sites_are_403(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(user_id="someone-else")
        resp = client.get(
            "/api/v1/websites/ws-1/loyalty-cards.html", headers=auth_headers
        )
        assert resp.status_code == 403

    def test_unpublished_site_is_a_clear_409(self, client, auth_headers, kit_patches):
        kit_patches["get_website"].return_value = _row(subdomain=None)
        resp = client.get(
            "/api/v1/websites/ws-1/business-cards.html", headers=auth_headers
        )
        assert resp.status_code == 409
