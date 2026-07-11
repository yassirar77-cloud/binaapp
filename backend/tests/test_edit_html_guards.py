"""
Tests for the editor AI-edit guard pipeline (app.services.edit_guards) and
its wiring into POST /api/edit-html.

Production gap being closed: the sensitive-claim sanitizer (and the other
post-generation guards) ran on every FULL generation path but not on the
editor's AI Assistant quick-edit path, so an edit could introduce — or leave
standing — an invented "Est. 2024 · Pengusaha Muslim" badge, an empty image
slot, or AOS-hidden content.

Covers:
- apply_edit_guards(): unverified sensitive claim stripped, merchant-stated
  claim kept, empty-src image slots fixed, PHOTO_SLOT tokens handled,
  layout/AOS safety CSS injected, idempotency (running twice == once)
- claim_sources_for_website(): website-row sources vs pre-edit-HTML fallback
- Endpoint wiring: POST /api/edit-html runs the guards on the DeepSeek
  result, verifies against the owner's stored business data, and refuses a
  website_id owned by someone else

All HTTP calls are mocked — no live API usage.
"""

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_service import AIService
from app.services.edit_guards import apply_edit_guards, claim_sources_for_website


@pytest.fixture(scope="module")
def ai_service():
    return AIService()


def make_page(body: str) -> str:
    return (
        "<!DOCTYPE html><html><head><title>Kedai</title></head>"
        f"<body>{body}</body></html>"
    )


BADGE = '<span class="badge">Est. 2024 · Pengusaha Muslim</span>'


# ── apply_edit_guards ────────────────────────────────────────────────────────

class TestApplyEditGuards:
    def test_unverified_pengusaha_muslim_badge_stripped(self, ai_service):
        html = make_page(f"<h1>Kedai Kopi Ali</h1>{BADGE}")
        website = {
            "business_name": "Kedai Kopi Ali",
            "description": "Kedai kopi biasa di Ipoh",
            "location_address": "Ipoh, Perak",
        }
        out = apply_edit_guards(html, ai_service, website=website)
        assert "Pengusaha Muslim" not in out
        assert "Est. 2024" not in out
        assert "Kedai Kopi Ali" in out

    def test_merchant_stated_halal_survives(self, ai_service):
        html = make_page(
            "<h1>Restoran Aminah</h1>"
            '<span class="pill">100% Halal</span>'
        )
        website = {
            "business_name": "Restoran Aminah",
            "description": "Restoran masakan kampung, dijamin halal",
            "location_address": "Shah Alam",
        }
        out = apply_edit_guards(html, ai_service, website=website)
        assert "Halal" in out

    def test_unverified_halal_stripped_when_not_in_business_data(self, ai_service):
        html = make_page('<h1>Kedai Barat</h1><span class="pill">Halal</span>')
        website = {
            "business_name": "Kedai Barat",
            "description": "Western food restaurant",
            "location_address": "",
        }
        out = apply_edit_guards(html, ai_service, website=website)
        assert "Halal" not in out

    def test_empty_image_slot_gets_image_safety_treatment(self, ai_service):
        html = make_page('<h1>Kedai</h1><img src="" alt="hero">')
        out = apply_edit_guards(
            html, ai_service, website={"description": "Kedai makan"}
        )
        # No <img> tag is left with an empty src (the guard CSS's
        # img[src=""] SELECTORS are allowed to contain the literal).
        assert not re.search(r'<img[^>]*src=""', out)
        # A real fallback URL was substituted in.
        assert '<img src="http' in out

    def test_photo_slot_token_emptied_then_filled(self, ai_service):
        html = make_page('<img src="PHOTO_SLOT_1" alt="hero">')
        out = apply_edit_guards(
            html, ai_service, website={"description": "Kedai makan"}
        )
        assert "PHOTO_SLOT" not in out
        # broken-image fixer filled the emptied slot
        assert not re.search(r'<img[^>]*src=""', out)

    def test_layout_safety_css_injected(self, ai_service):
        html = make_page("<h1>Kedai</h1>")
        out = apply_edit_guards(html, ai_service, website={"description": "Kedai"})
        assert 'id="binaapp-layout-safety"' in out
        # AOS visibility rescue is part of the guard CSS.
        assert "data-aos" in out

    def test_idempotent_running_twice_same_output(self, ai_service):
        html = make_page(
            f"<h1>Kedai Kopi Ali</h1>{BADGE}"
            '<img src="" alt="x"><div data-aos="fade-up">Info</div>'
        )
        website = {
            "business_name": "Kedai Kopi Ali",
            "description": "Kedai kopi biasa",
            "location_address": "Ipoh",
        }
        once = apply_edit_guards(html, ai_service, website=website)
        twice = apply_edit_guards(once, ai_service, website=website)
        assert once == twice

    def test_empty_html_passthrough(self, ai_service):
        assert apply_edit_guards("", ai_service, website=None) == ""

    def test_fallback_no_website_new_claim_stripped(self, ai_service):
        previous = make_page("<h1>Kedai Kopi Ali</h1>")
        edited = make_page(f"<h1>Kedai Kopi Ali</h1>{BADGE}")
        out = apply_edit_guards(
            edited, ai_service, website=None, previous_html=previous
        )
        assert "Pengusaha Muslim" not in out

    def test_fallback_no_website_existing_claim_survives(self, ai_service):
        previous = make_page(
            '<h1>Restoran Aminah</h1><span class="pill">Halal</span>'
        )
        edited = make_page(
            '<h1>Restoran Aminah Baru</h1><span class="pill">Halal</span>'
        )
        out = apply_edit_guards(
            edited, ai_service, website=None, previous_html=previous
        )
        assert "Halal" in out


# ── claim_sources_for_website ────────────────────────────────────────────────

class TestClaimSources:
    def test_website_row_fields(self):
        sources = claim_sources_for_website(
            {
                "business_name": "Kedai A",
                "description": "Nasi lemak sedap",
                "location_address": "KL",
            }
        )
        assert sources == ["Kedai A", "Nasi lemak sedap", "KL"]

    def test_missing_fields_skipped(self):
        assert claim_sources_for_website({"business_name": "Kedai A"}) == ["Kedai A"]

    def test_fallback_strips_tags(self):
        sources = claim_sources_for_website(None, "<p>Dijamin halal</p>")
        assert len(sources) == 1
        assert "halal" in sources[0]
        assert "<p>" not in sources[0]

    def test_no_data_at_all(self):
        assert claim_sources_for_website(None, "") == []


# ── POST /api/edit-html wiring ───────────────────────────────────────────────

EDITED_PAGE = (
    "<!DOCTYPE html><html><head><title>Kedai Kopi Ali</title></head><body>"
    "<h1>Kedai Kopi Ali</h1>"
    '<span class="badge">Est. 2024 · Pengusaha Muslim</span>'
    '<span class="pill">Halal</span>'
    "<p>" + "Kopi terbaik di pekan. " * 10 + "</p>"
    "</body></html>"
)


def _deepseek_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": html}}]}
    return resp


def _post_edit(client, auth_headers, payload):
    return client.post("/api/edit-html", json=payload, headers=auth_headers)


class TestEditHtmlEndpoint:
    @pytest.fixture
    def deepseek_mock(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
        client_mock = MagicMock()
        client_mock.__aenter__ = AsyncMock(return_value=client_mock)
        client_mock.__aexit__ = AsyncMock(return_value=False)
        client_mock.post = AsyncMock(return_value=_deepseek_response(EDITED_PAGE))
        with patch("app.main.httpx.AsyncClient", return_value=client_mock):
            yield client_mock

    def test_guards_run_with_website_business_data(
        self, client, auth_headers, deepseek_mock, test_user_id
    ):
        website = {
            "id": "site-1",
            "user_id": test_user_id,
            "business_name": "Kedai Kopi Ali",
            "description": "Kedai kopi halal di Ipoh",
            "location_address": "Ipoh",
        }
        with patch(
            "app.main.supabase_service.get_website",
            new=AsyncMock(return_value=website),
        ):
            resp = _post_edit(
                client,
                auth_headers,
                {
                    "html": "<html><body>old</body></html>",
                    "instruction": "tukar warna",
                    "website_id": "site-1",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # Invented badge stripped, merchant-stated claim kept.
        assert "Pengusaha Muslim" not in data["html"]
        assert "Est. 2024" not in data["html"]
        assert "Halal" in data["html"]
        # Layout/AOS guard applied to the edit result.
        assert 'id="binaapp-layout-safety"' in data["html"]

    def test_foreign_website_id_rejected(
        self, client, auth_headers, deepseek_mock
    ):
        website = {"id": "site-2", "user_id": "someone-else"}
        with patch(
            "app.main.supabase_service.get_website",
            new=AsyncMock(return_value=website),
        ):
            resp = _post_edit(
                client,
                auth_headers,
                {
                    "html": "<html><body>old</body></html>",
                    "instruction": "tukar warna",
                    "website_id": "site-2",
                },
            )
        assert resp.status_code == 403
        assert resp.json()["success"] is False

    def test_no_website_id_still_guards_via_previous_html(
        self, client, auth_headers, deepseek_mock
    ):
        # Legacy caller without website_id: the pre-edit HTML is the claim
        # source, so the newly-introduced badge is still stripped.
        get_website = AsyncMock()
        with patch("app.main.supabase_service.get_website", new=get_website):
            resp = _post_edit(
                client,
                auth_headers,
                {
                    "html": "<html><body><h1>Kedai Kopi Ali</h1></body></html>",
                    "instruction": "tukar warna",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Pengusaha Muslim" not in data["html"]
        get_website.assert_not_awaited()

    def test_website_lookup_failure_falls_back(
        self, client, auth_headers, deepseek_mock
    ):
        with patch(
            "app.main.supabase_service.get_website",
            new=AsyncMock(side_effect=RuntimeError("supabase down")),
        ):
            resp = _post_edit(
                client,
                auth_headers,
                {
                    "html": "<html><body><h1>Kedai Kopi Ali</h1></body></html>",
                    "instruction": "tukar warna",
                    "website_id": "site-1",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        # Fallback source = pre-edit HTML → invented badge still stripped.
        assert "Pengusaha Muslim" not in data["html"]

    def test_requires_auth(self, client):
        resp = client.post(
            "/api/edit-html",
            json={"html": "<html></html>", "instruction": "x"},
        )
        assert resp.status_code in (401, 403)
