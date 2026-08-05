"""Tests for the Design Studio endpoints.

    GET   /api/v1/websites/design/options
    GET   /api/v1/websites/{id}/theme
    PATCH /api/v1/websites/{id}/theme

Two things matter beyond "does it change the colour":

  1. It is a CREDIT-FREE path. It must never reach the AI or the quota
     counters — that is the entire reason it exists.
  2. It republishes over a live site, so it inherits the mimba publish-safety
     rules: rewrite against the live snapshot, never publish an unbalanced
     base, and be honest when the live site did not actually change.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.design_system import get_named_palette


LIVE_HTML = (
    "<!DOCTYPE html><html><head><title>Kedai Ali</title>"
    '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700'
    '&family=DM+Sans:wght@400;700&display=swap" rel="stylesheet">'
    "<style>:root{--primary-color:#EA580C;--secondary-color:#9A3412;"
    "--bg-color:#FFFBF5;--text-color:#1C1917;}</style></head>"
    "<body>"
    '<a href="https://wa.me/60195551234">Chat</a>'
    '<div style="background:#EA580C">Pesan Sekarang</div>'
    "<footer>foot</footer>"
    "</body></html>"
)

# Truncated mid-tag: no </body>, no </html>. The mimba failure shape.
TRUNCATED_HTML = (
    "<!DOCTYPE html><html><head><title>Kedai Ali</title></head><body>"
    '<img src="https://res.cloudinary.com/x/image/upload'
)


def _row(**overrides):
    row = {
        "id": "ws-1",
        "user_id": "test-user-id-12345",
        "name": "Kedai Ali",
        "subdomain": "kedaiali",
        "status": "published",
        "html_content": LIVE_HTML,
    }
    row.update(overrides)
    return row


@pytest.fixture
def patches():
    with (
        patch(
            "app.api.v1.endpoints.design_studio.supabase_service.get_website",
            new=AsyncMock(return_value=_row()),
        ) as get_website,
        patch(
            "app.api.v1.endpoints.design_studio.supabase_service.update_website",
            new=AsyncMock(return_value=True),
        ) as update_website,
        patch(
            "app.api.v1.endpoints.design_studio.storage_service.publish_website",
            new=AsyncMock(return_value="https://kedaiali.binaapp.my"),
        ) as publish_website,
        patch(
            "app.api.v1.endpoints.design_studio._fetch_serving_snapshot",
            new=AsyncMock(return_value=None),
        ) as fetch_snapshot,
    ):
        yield {
            "get_website": get_website,
            "update_website": update_website,
            "publish_website": publish_website,
            "fetch_snapshot": fetch_snapshot,
        }


def _published_html(patches):
    assert patches["publish_website"].called
    return patches["publish_website"].call_args.kwargs["html_content"]


def _update_payload(patches):
    args, kwargs = patches["update_website"].call_args
    return args[1] if len(args) > 1 else kwargs.get("data", args[-1])


class TestDesignOptions:
    def test_catalogue_is_public_and_complete(self, client):
        resp = client.get("/api/v1/websites/design/options")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["palettes"]) >= 12
        assert len(body["fonts"]) >= 10
        # 5 original personalities + the opt-in Doodle Cartoon style.
        assert len(body["styles"]) == 6
        assert {s["key"] for s in body["styles"]} >= {
            "elegant", "minimal", "playful", "bold", "classic", "doodle"
        }

    def test_every_palette_carries_a_full_swatch_and_malay_label(self, client):
        body = client.get("/api/v1/websites/design/options").json()
        for palette in body["palettes"]:
            assert palette["label_ms"], "the dashboard is in Bahasa Melayu"
            for role in ("primary", "secondary", "accent", "background", "surface", "text"):
                assert palette["colors"][role].startswith("#")

    def test_dark_mode_returns_the_dark_variants(self, client):
        light = client.get("/api/v1/websites/design/options?color_mode=light").json()
        dark = client.get("/api/v1/websites/design/options?color_mode=dark").json()
        light_blue = next(p for p in light["palettes"] if p["key"] == "blue")
        dark_blue = next(p for p in dark["palettes"] if p["key"] == "blue")
        assert light_blue["colors"]["background"] != dark_blue["colors"]["background"]

    def test_font_keys_are_unique(self, client):
        fonts = client.get("/api/v1/websites/design/options").json()["fonts"]
        keys = [f["key"] for f in fonts]
        assert len(keys) == len(set(keys))

    def test_business_type_filter_narrows_the_font_list(self, client):
        everything = client.get("/api/v1/websites/design/options").json()["fonts"]
        gym_only = client.get(
            "/api/v1/websites/design/options?business_type=gym"
        ).json()["fonts"]
        assert 0 < len(gym_only) < len(everything)


class TestReadCurrentTheme:
    def test_reports_the_live_palette_and_matched_key(self, client, auth_headers, patches):
        resp = client.get("/api/v1/websites/ws-1/theme", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["palette"]["primary"] == "#EA580C"
        assert body["palette_key"] == "orange"
        assert body["fonts"]["heading"] == "Playfair Display"
        assert body["source"] == "db"

    def test_prefers_the_live_storage_snapshot_over_the_db_blob(
        self, client, auth_headers, patches
    ):
        patches["fetch_snapshot"].return_value = LIVE_HTML.replace("#EA580C", "#2563EB")
        body = client.get("/api/v1/websites/ws-1/theme", headers=auth_headers).json()
        assert body["source"] == "storage"
        assert body["palette"]["primary"] == "#2563EB"

    def test_requires_auth(self, client):
        assert client.get("/api/v1/websites/ws-1/theme").status_code in (401, 403)

    def test_rejects_a_site_owned_by_someone_else(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(user_id="someone-else")
        resp = client.get("/api/v1/websites/ws-1/theme", headers=auth_headers)
        assert resp.status_code == 403

    def test_missing_site_is_404(self, client, auth_headers, patches):
        patches["get_website"].return_value = None
        resp = client.get("/api/v1/websites/ws-1/theme", headers=auth_headers)
        assert resp.status_code == 404


class TestRepaintByNamedPalette:
    def test_applies_the_palette_and_republishes(self, client, auth_headers, patches):
        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"palette": "blue"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["changed"] is True
        assert body["palette_key"] == "blue"
        assert body["live_site_updated"] is True

        published = _published_html(patches)
        assert "--primary-color:#2563EB" in published
        assert "#EA580C" not in published
        # The DB blob is kept in sync with what went live.
        assert _update_payload(patches)["html_content"] == published

    def test_copy_and_links_are_untouched(self, client, auth_headers, patches):
        client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"palette": "blue"},
        )
        published = _published_html(patches)
        assert "Pesan Sekarang" in published
        assert 'href="https://wa.me/60195551234"' in published

    def test_unknown_palette_is_rejected(self, client, auth_headers, patches):
        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"palette": "chartreuse"},
        )
        assert resp.status_code == 400
        patches["publish_website"].assert_not_called()

    def test_dark_mode_palette_is_honoured(self, client, auth_headers, patches):
        client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"palette": "blue", "color_mode": "dark"},
        )
        dark_blue = get_named_palette("blue", "dark")
        assert f"--primary-color:{dark_blue['primary']}" in _published_html(patches)

    def test_applying_the_same_palette_twice_is_a_reported_no_op(
        self, client, auth_headers, patches
    ):
        # Round-trip: repaint once, feed the published result back in, and the
        # second call must recognise there is nothing left to do rather than
        # churning a fresh copy through storage.
        client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"palette": "blue"},
        )
        patches["get_website"].return_value = _row(
            html_content=_published_html(patches)
        )
        patches["publish_website"].reset_mock()

        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"palette": "blue"},
        )
        assert resp.status_code == 200
        assert resp.json()["changed"] is False
        patches["publish_website"].assert_not_called()


class TestRepaintByBrandColours:
    def test_explicit_hexes_win(self, client, auth_headers, patches):
        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"palette": "blue", "colors": {"primary": "#123456"}},
        )
        assert resp.status_code == 200
        published = _published_html(patches)
        assert "--primary-color:#123456" in published
        # The rest of the requested palette still applies.
        assert "--secondary-color:#1E40AF" in published

    def test_a_lone_brand_colour_keeps_the_rest_of_the_page(
        self, client, auth_headers, patches
    ):
        client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"colors": {"primary": "#123456"}},
        )
        published = _published_html(patches)
        assert "--primary-color:#123456" in published
        assert "--secondary-color:#9A3412" in published, "untouched role survives"

    def test_invalid_hex_is_a_422(self, client, auth_headers, patches):
        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"colors": {"primary": "royal blue"}},
        )
        assert resp.status_code == 422
        patches["publish_website"].assert_not_called()

    def test_shorthand_hex_is_accepted_and_expanded(self, client, auth_headers, patches):
        client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"colors": {"primary": "#abc"}},
        )
        assert "--primary-color:#AABBCC" in _published_html(patches)


class TestShuffle:
    def test_shuffle_advances_from_the_page_s_current_palette(
        self, client, auth_headers, patches
    ):
        # The page is orange; the next palette in display order is red.
        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"shuffle": True},
        )
        assert resp.status_code == 200
        assert resp.json()["palette_key"] == "red"

    def test_shuffle_is_reproducible(self, client, auth_headers, patches):
        first = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"shuffle": True}
        ).json()["palette_key"]
        second = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"shuffle": True}
        ).json()["palette_key"]
        assert first == second, "same input page -> same next palette"

    def test_shuffle_step_skips_further_ahead(self, client, auth_headers, patches):
        one = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"shuffle": True}
        ).json()["palette_key"]
        three = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"shuffle": True, "shuffle_step": 3},
        ).json()["palette_key"]
        assert one != three


class TestTypographySwap:
    def test_font_key_swaps_the_pairing(self, client, auth_headers, patches):
        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"font_key": "bebas-neue__barlow"},
        )
        assert resp.status_code == 200
        published = _published_html(patches)
        assert "family=Bebas+Neue" in published
        assert "Playfair Display" not in published

    def test_unknown_font_key_is_rejected(self, client, auth_headers, patches):
        resp = client.patch(
            "/api/v1/websites/ws-1/theme",
            headers=auth_headers,
            json={"font_key": "comic-sans__comic-sans"},
        )
        assert resp.status_code == 400
        patches["publish_website"].assert_not_called()


class TestPublishSafety:
    def test_rewrites_against_the_live_snapshot_not_the_db_blob(
        self, client, auth_headers, patches
    ):
        # DB blob is stale (missing the CTA); the live snapshot has it.
        patches["get_website"].return_value = _row(
            html_content=LIVE_HTML.replace("<div style=\"background:#EA580C\">Pesan Sekarang</div>", "")
        )
        patches["fetch_snapshot"].return_value = LIVE_HTML

        resp = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"palette": "blue"}
        )
        assert resp.json()["base_source"] == "storage"
        assert "Pesan Sekarang" in _published_html(patches)

    def test_truncated_base_with_no_snapshot_refuses_to_publish(
        self, client, auth_headers, patches
    ):
        patches["get_website"].return_value = _row(html_content=TRUNCATED_HTML)
        patches["fetch_snapshot"].return_value = None

        resp = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"palette": "blue"}
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "no_balanced_html_base"
        patches["publish_website"].assert_not_called()
        patches["update_website"].assert_not_called()

    def test_a_draft_site_is_updated_without_touching_storage(
        self, client, auth_headers, patches
    ):
        patches["get_website"].return_value = _row(status="draft")
        resp = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"palette": "blue"}
        )
        assert resp.status_code == 200
        assert resp.json()["live_site_updated"] is False
        patches["publish_website"].assert_not_called()
        assert "#2563EB" in _update_payload(patches)["html_content"]

    def test_storage_failure_is_reported_honestly(self, client, auth_headers, patches):
        patches["publish_website"].side_effect = RuntimeError("bucket down")
        resp = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"palette": "blue"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["live_site_updated"] is False
        assert body["warning"] == "storage_refresh_failed"
        assert "belum dikemas kini" in body["message"]

    def test_empty_body_is_rejected(self, client, auth_headers, patches):
        resp = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={}
        )
        assert resp.status_code == 400
        patches["publish_website"].assert_not_called()

    def test_not_the_owner_is_403(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(user_id="someone-else")
        resp = client.patch(
            "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"palette": "blue"}
        )
        assert resp.status_code == 403
        patches["publish_website"].assert_not_called()

    def test_requires_auth(self, client):
        resp = client.patch("/api/v1/websites/ws-1/theme", json={"palette": "blue"})
        assert resp.status_code in (401, 403)


class TestCreditFree:
    """The whole point: a recolour must never cost a generation."""

    def test_no_ai_call_and_no_quota_touch(self, client, auth_headers, patches):
        with (
            patch("app.services.ai_service.ai_service.generate_website") as gen,
            patch(
                "app.services.subscription_service.subscription_service"
                ".increment_usage"
            ) as increment,
        ):
            resp = client.patch(
                "/api/v1/websites/ws-1/theme",
                headers=auth_headers,
                json={"palette": "blue"},
            )
        assert resp.status_code == 200
        gen.assert_not_called()
        increment.assert_not_called()
