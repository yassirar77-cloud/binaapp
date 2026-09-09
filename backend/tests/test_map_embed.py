"""Bug 3: the embedded map spanned Klang to Subang Jaya with no pin.

The page embedded the keyless search form — maps?q=<address text> — with
the raw "13/2" unencoded. When Google can't resolve the text to one place it
renders a wide region and no marker. The fix geocodes once at publish, keeps
lat/lng on the row, and points the iframe at coordinates with zoom 16; when
geocoding fails the embed becomes an *encoded* address search, never the
wide-area frame.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.map_embed import (
    MARKER_ZOOM, build_map_embed_src, extract_map_address, has_map_embed, rewrite_map_embeds,
)

ADDRESS = "No 12-1, Jalan Bunga Raya 13/2, Seksyen 13, 40100 Shah Alam, Selangor"
PAGE = (
    '<html><body><section><iframe allowfullscreen="" class="w-full h-[400px]" loading="lazy" '
    'src="https://www.google.com/maps?q=No+12-1,+Jalan+Bunga+Raya+13/2,+Seksyen+13,+40100+Shah+Alam,+Selangor&amp;output=embed" '
    'title="Peta"></iframe></section></body></html>'
)


class TestExtract:
    def test_reads_the_address_the_page_is_searching_for(self):
        assert extract_map_address(PAGE) == ADDRESS

    def test_no_map_means_none(self):
        assert extract_map_address("<html><body>no map</body></html>") is None
        assert has_map_embed("<html></html>") is False

    def test_coordinates_are_not_an_address(self):
        html = '<iframe src="https://maps.google.com/maps?q=3.07,101.51&z=16&output=embed"></iframe>'
        assert extract_map_address(html) is None


class TestBuild:
    def test_coordinates_pin_at_zoom_16(self):
        src = build_map_embed_src(lat=3.0733, lng=101.5185, address=ADDRESS)
        assert src == f"https://maps.google.com/maps?q=3.073300,101.518500&z={MARKER_ZOOM}&output=embed"

    def test_no_coordinates_falls_back_to_an_encoded_search_never_the_raw_string(self):
        src = build_map_embed_src(lat=None, lng=None, address=ADDRESS)
        assert src.startswith("https://maps.google.com/maps?q=")
        assert "13%2F2" in src          # the slash that broke the original
        assert "13/2" not in src
        assert "&z=16" in src

    def test_nothing_to_work_with_leaves_the_page_alone(self):
        assert build_map_embed_src(lat=None, lng=None, address="") is None


class TestRewrite:
    def test_every_map_iframe_is_repointed_and_attribute_safe(self):
        src = build_map_embed_src(lat=3.0733, lng=101.5185, address=ADDRESS)
        out = rewrite_map_embeds(PAGE + PAGE, src)
        assert out.count("q=3.073300,101.518500&amp;z=16&amp;output=embed") == 2
        assert "Jalan+Bunga" not in out
        assert 'title="Peta"' in out  # other attributes untouched

    def test_non_map_iframes_are_untouched(self):
        html = '<iframe src="https://www.youtube.com/embed/x"></iframe>'
        assert rewrite_map_embeds(html, "https://maps.google.com/maps?q=1,2&z=16&output=embed") == html


class TestPublishPersistsCoordinates:
    """Cross-layer: POST /api/publish geocodes, pins the map in the stored
    HTML, and writes lat/lng/location_address on the websites row."""

    def _publish(self, client, auth_headers, geo_result, body_extra=None):
        supabase_mock = MagicMock()
        table_mock = MagicMock()
        for m in ("select", "insert", "update", "upsert", "delete", "eq", "neq", "limit", "single", "order"):
            getattr(table_mock, m).return_value = table_mock
        rsp = MagicMock()
        rsp.data = []
        table_mock.execute.return_value = rsp
        supabase_mock.table.return_value = table_mock

        storage_response = MagicMock()
        storage_response.status_code = 201
        storage_response.text = ""
        fake_http = MagicMock()
        fake_http.__aenter__ = AsyncMock(return_value=fake_http)
        fake_http.__aexit__ = AsyncMock(return_value=False)
        fake_http.post = AsyncMock(return_value=storage_response)

        with (
            patch("app.main.supabase", supabase_mock),
            patch("app.main.sub_service.check_limit", new=AsyncMock(return_value={"allowed": True})),
            patch("app.main.sub_service.increment_usage", new=AsyncMock(return_value=True)),
            patch("app.services.plan_features.can_publish_subdomain", new=AsyncMock(return_value=True)),
            patch("app.main.supabase_service.is_email_verified", new=AsyncMock(return_value=True)),
            patch("app.main.httpx.AsyncClient", return_value=fake_http),
            patch("app.core.geocoder.geocode_address", new=AsyncMock(return_value=geo_result)),
        ):
            resp = client.post("/api/publish", headers=auth_headers, json={
                "html_content": PAGE,
                "subdomain": "nadirasalon",
                "project_name": "Nadira",
                "website_id": "ws-map-1",
                "description": "Salon rambut di Shah Alam.",
                **(body_extra or {}),
            })
        payload = next(
            (c.args[0] for c in table_mock.upsert.call_args_list if c.args and isinstance(c.args[0], dict)),
            None,
        )
        return resp, payload

    def test_geocode_hit_pins_the_map_and_stores_coordinates(self, client, auth_headers):
        geo = MagicMock(found=True, lat=3.0733, lng=101.5185, display_name="Shah Alam")
        resp, payload = self._publish(client, auth_headers, geo)
        assert resp.status_code == 200, resp.text
        assert payload["lat"] == 3.0733 and payload["lng"] == 101.5185
        assert payload["location_address"] == ADDRESS
        assert "q=3.073300,101.518500&amp;z=16&amp;output=embed" in payload["html_content"]

    def test_explicit_address_in_the_body_wins_over_the_page(self, client, auth_headers):
        geo = MagicMock(found=True, lat=1.0, lng=2.0, display_name="x")
        resp, payload = self._publish(client, auth_headers, geo, {"address": "Jalan Lain 5, Klang"})
        assert payload["location_address"] == "Jalan Lain 5, Klang"

    def test_geocode_miss_still_encodes_the_search_and_never_stores_null_island(self, client, auth_headers):
        geo = MagicMock(found=False, lat=None, lng=None, display_name=None)
        resp, payload = self._publish(client, auth_headers, geo)
        assert resp.status_code == 200, resp.text
        assert "lat" not in payload and "lng" not in payload
        assert "13%2F2" in payload["html_content"]
        assert "Jalan+Bunga+Raya+13/2" not in payload["html_content"]

    def test_geocoder_blowing_up_never_blocks_the_publish(self, client, auth_headers):
        with patch("app.core.geocoder.geocode_address", new=AsyncMock(side_effect=RuntimeError("nominatim down"))):
            geo = MagicMock(found=False, lat=None, lng=None)
            resp, payload = self._publish(client, auth_headers, geo)
        assert resp.status_code == 200, resp.text
        assert payload is not None
