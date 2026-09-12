"""The content-integrity gate on the publish endpoint that is actually mounted.

`app/api/simple/publish.py` has run this gate for a while — but that module is
not included in the app, so the HTML that really goes live (POST /api/publish
in `app.main`) reached Supabase Storage having been checked for balanced tags
and nothing else. These tests pin the gate to the mounted route so the two
handlers cannot drift apart again.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

B = chr(92)
EM_DASH = B + "u2014"

GOOD_PAGE = (
    "<!DOCTYPE html><html lang=\"ms\"><head><title>Nadira Salon</title>"
    '<meta name="description" content="Salon rambut di Shah Alam.">'
    "</head><body><h1>Nadira Salon</h1>"
    "<p>Rawatan rambut — tempahan melalui WhatsApp.</p>"
    "</body></html>"
)


def _page(head: str = "", body: str = "") -> str:
    return (
        '<!DOCTYPE html><html lang="ms"><head><title>Nadira Salon</title>'
        '<meta name="description" content="Salon rambut di Shah Alam.">'
        f"{head}</head><body><h1>Nadira Salon</h1>{body}</body></html>"
    )


def _publish(client, auth_headers, html, query=""):
    supabase_mock = MagicMock()
    table_mock = MagicMock()
    for m in ("select", "insert", "update", "upsert", "delete", "eq",
              "neq", "limit", "single", "order"):
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
    ):
        return client.post(
            f"/api/publish{query}",
            headers=auth_headers,
            json={
                "html_content": html,
                "subdomain": "nadirasalon",
                "project_name": "Nadira Salon",
                "website_id": "ws-gate-1",
                "description": "Salon rambut di Shah Alam.",
            },
        )


class TestGatePassesGoodPages:
    def test_a_complete_page_publishes(self, client, auth_headers):
        assert _publish(client, auth_headers, GOOD_PAGE).status_code == 200


class TestGateBlocksUnfinishedPages:
    @pytest.mark.parametrize(
        "html, expected_code",
        [
            (_page(body=f"<p>Rawatan {EM_DASH} rambut</p>"), "unicode_escape_leak"),
            (_page(body="<p>{{business_name}}</p>"), "unresolved_placeholder"),
            (
                _page(body="<div>Peta lokasi akan dipaparkan di sini</div>"),
                "dead_placeholder_text",
            ),
            (
                _page(body="<footer>NAMA PERNIAGAAN ANDA</footer>"),
                "business_name_placeholder",
            ),
            (
                '<!DOCTYPE html><html lang="ms"><head>'
                '<meta name="description" content="Salon."></head>'
                "<body><h1>Nadira</h1></body></html>",
                "missing_title",
            ),
            (
                '<!DOCTYPE html><html lang="ms"><head><title>Nadira</title>'
                "</head><body><h1>Nadira</h1></body></html>",
                "missing_meta_description",
            ),
        ],
    )
    def test_blocked_with_422_naming_the_issue(self, client, auth_headers, html, expected_code):
        resp = _publish(client, auth_headers, html)
        assert resp.status_code == 422, resp.text
        payload = resp.json()
        assert payload["error"] == "content_validation_failed"
        assert any(expected_code in issue for issue in payload["issues"])

    def test_the_response_carries_the_offending_snippet(self, client, auth_headers):
        """Fail loudly: the caller must be able to see WHAT is wrong."""
        resp = _publish(client, auth_headers, _page(body=f"<p>Rawatan {EM_DASH} rambut</p>"))
        issue = next(i for i in resp.json()["issues"] if "unicode_escape_leak" in i)
        assert EM_DASH in issue
        assert "Rawatan" in issue


class TestGateOverrides:
    def test_force_query_param_overrides(self, client, auth_headers):
        resp = _publish(
            client, auth_headers, _page(body="<p>{{tagline}}</p>"), query="?force=true"
        )
        assert resp.status_code == 200, resp.text

    def test_ops_kill_switch_overrides(self, client, auth_headers, monkeypatch):
        monkeypatch.setenv("GENERATION_VALIDATOR_ENFORCE", "0")
        resp = _publish(client, auth_headers, _page(body="<p>{{tagline}}</p>"))
        assert resp.status_code == 200, resp.text
