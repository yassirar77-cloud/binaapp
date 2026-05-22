"""
Tests for the regenerate endpoint at PATCH /api/v1/websites/{id}/regenerate.

Focus is on the request shaping + access control logic (auth, ownership,
quota, validation) — the background AI generation is mocked out, so these
tests run instantly and have no external dependencies.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.schemas import WebsiteRegenerateRequest


class TestRegenerateRequestSchema:
    """Pydantic model — the first line of defence against bad input."""

    def test_empty_body_is_valid(self):
        # Body is optional; when omitted, the endpoint reuses the stored
        # description on the website row.
        req = WebsiteRegenerateRequest()
        assert req.description is None

    def test_description_min_length_enforced(self):
        # Same 10-char floor as the create endpoint. A 5-char prompt is
        # never useful and indicates a frontend bug.
        with pytest.raises(Exception):
            WebsiteRegenerateRequest(description="short")

    def test_description_max_length_enforced(self):
        # 5000 chars matches the create endpoint. Anything larger is
        # almost certainly the user pasting the AI's previous output back
        # into the box.
        with pytest.raises(Exception):
            WebsiteRegenerateRequest(description="x" * 5001)

    def test_valid_description_passes(self):
        req = WebsiteRegenerateRequest(description="a kedai bakery in shah alam")
        assert req.description == "a kedai bakery in shah alam"


class TestRegenerateEndpointAccess:
    """Auth, ownership, conflict — these gates must hold even if the
    AI pipeline behind them changes."""

    @pytest.fixture
    def patches(self):
        """Patches for every external call the regenerate endpoint makes,
        in one place so the tests stay readable."""
        with (
            patch(
                "app.api.v1.endpoints.websites.supabase_service.get_website",
                new=AsyncMock(),
            ) as get_website,
            patch(
                "app.api.v1.endpoints.websites.supabase_service.update_website",
                new=AsyncMock(return_value=True),
            ) as update_website,
            patch(
                "app.api.v1.endpoints.websites.subscription_service.check_limit",
                new=AsyncMock(return_value={"allowed": True}),
            ) as check_limit,
        ):
            yield {
                "get_website": get_website,
                "update_website": update_website,
                "check_limit": check_limit,
            }

    def _website_row(
        self,
        owner_id: str,
        *,
        status: str = "draft",
        description: str = "stored description from create flow",
        generation_count: int = 1,
    ) -> dict:
        return {
            "id": "ws-1",
            "user_id": owner_id,
            "business_name": "Test Cafe",
            "business_type": "restaurant",
            "subdomain": "testcafe",
            "language": "ms",
            "status": status,
            "include_whatsapp": True,
            "whatsapp_number": "+60123456789",
            "include_maps": False,
            "include_ecommerce": True,
            "description": description,
            "generation_count": generation_count,
            "created_at": "2026-05-22T00:00:00",
            "updated_at": "2026-05-22T00:00:00",
            "published_at": None,
        }

    def test_404_when_website_missing(
        self, client, auth_headers, test_user_id, patches
    ):
        patches["get_website"].return_value = None
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 404

    def test_403_when_owned_by_someone_else(
        self, client, auth_headers, test_user_id, patches
    ):
        patches["get_website"].return_value = self._website_row(
            owner_id="some-other-user"
        )
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate",
            headers=auth_headers,
            json={"description": "a brand new description for the cafe"},
        )
        assert resp.status_code == 403
        # The check_limit call must NOT happen before the ownership check
        # — that would leak the existence of the row + waste a quota
        # check on someone who has no right to regenerate it.
        patches["check_limit"].assert_not_called()

    def test_409_when_already_generating(
        self, client, auth_headers, test_user_id, patches
    ):
        patches["get_website"].return_value = self._website_row(
            owner_id=test_user_id, status="generating"
        )
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 409
        # Double-billing protection — quota must not be consumed for a
        # request that is rejected.
        patches["check_limit"].assert_not_called()

    def test_400_when_no_description_anywhere(
        self, client, auth_headers, test_user_id, patches
    ):
        # Legacy row from before migration 039 — no stored description.
        patches["get_website"].return_value = self._website_row(
            owner_id=test_user_id, description=None
        )
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "description_required"

    def test_403_when_quota_exceeded(
        self, client, auth_headers, test_user_id, patches
    ):
        patches["get_website"].return_value = self._website_row(
            owner_id=test_user_id
        )
        patches["check_limit"].return_value = {
            "allowed": False,
            "message": "Had AI hero tercapai (5/5).",
            "can_buy_addon": True,
            "current_usage": 5,
            "limit": 5,
        }
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate",
            headers=auth_headers,
            json={"description": "a new description for the cafe"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["detail"]["error"] == "LIMIT_REACHED"
        # The write must NOT have happened — important because the same
        # field we'd update (generation_count) is what we use to bill
        # later. Bumping it on a quota-failed request is a revenue leak.
        patches["update_website"].assert_not_called()

    def test_quota_check_runs_for_owner_with_valid_description(
        self, client, auth_headers, test_user_id, patches
    ):
        patches["get_website"].return_value = self._website_row(
            owner_id=test_user_id
        )
        with patch(
            "app.api.v1.endpoints.websites.generate_website_content",
            new=AsyncMock(),
        ):
            resp = client.patch(
                "/api/v1/websites/ws-1/regenerate",
                headers=auth_headers,
                json={"description": "completely new vibe — modern minimalist"},
            )
        # 200 OK with the GENERATING status — frontend polls GET /:id.
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "generating"
        # Quota was consumed via check_limit (same path as create).
        patches["check_limit"].assert_awaited_once()
        # Persisted description + bumped counter.
        patches["update_website"].assert_awaited()
        update_call_kwargs = patches["update_website"].await_args.args[1]
        assert (
            update_call_kwargs["description"]
            == "completely new vibe — modern minimalist"
        )
        assert update_call_kwargs["generation_count"] == 2  # prev was 1

    def test_stored_description_reused_when_body_empty(
        self, client, auth_headers, test_user_id, patches
    ):
        patches["get_website"].return_value = self._website_row(
            owner_id=test_user_id,
            description="the original prompt from create",
            generation_count=3,
        )
        with patch(
            "app.api.v1.endpoints.websites.generate_website_content",
            new=AsyncMock(),
        ):
            resp = client.patch(
                "/api/v1/websites/ws-1/regenerate",
                headers=auth_headers,
                json={},
            )
        assert resp.status_code == 200, resp.text
        update_payload = patches["update_website"].await_args.args[1]
        assert update_payload["description"] == "the original prompt from create"
        assert update_payload["generation_count"] == 4
