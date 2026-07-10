"""
Tests for the "Report Issue → Free Regeneration" make-good flow.

Covers:
- Feature flag (ISSUE_REPORT_ENABLED) gating — flag off means 404 everywhere.
- POST /api/v1/websites/{id}/report-issue: ownership, auto-grant vs
  escalation, duplicate collapsing, rate limits.
- The free-regeneration path: quota check bypassed but NOT charged, image
  usage NOT incremented, report resolved only on success.
- Regression: a normal regeneration still checks + charges quota as before.

All external calls (Supabase REST, AI generation) are mocked — these tests
run instantly with no network access.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.models.schemas import AIGenerationResponse, WebsiteGenerationRequest, Language


def _website_row(
    owner_id: str,
    *,
    status: str = "draft",
    free_regens_granted: int = 0,
    generation_count: int = 1,
    html_content: str = "<html><body>site</body></html>",
    description: str = "stored description from create flow",
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
        "include_ecommerce": False,
        "description": description,
        "generation_count": generation_count,
        "html_content": html_content,
        "free_regens_granted": free_regens_granted,
        "created_at": "2026-07-01T00:00:00",
        "updated_at": "2026-07-01T00:00:00",
        "published_at": None,
    }


def _report_row(report_id="rep-1", status="auto_regen_granted", **overrides) -> dict:
    row = {
        "id": report_id,
        "website_id": "ws-1",
        "user_id": "test-user-id-12345",
        "category": "images_wrong",
        "description": None,
        "status": status,
        "regen_used": False,
        "created_at": "2026-07-10T00:00:00",
    }
    row.update(overrides)
    return row


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ISSUE_REPORT_ENABLED", "true")


@pytest.fixture
def report_patches():
    """Every external call the report endpoint makes, mocked in one place."""
    svc = "app.api.v1.endpoints.issue_reports.issue_report_service"
    with (
        patch(
            "app.api.v1.endpoints.issue_reports.supabase_service.get_website",
            new=AsyncMock(),
        ) as get_website,
        patch(f"{svc}.find_existing_open_report", new=AsyncMock(return_value=None)) as find_existing,
        patch(f"{svc}.count_recent_reports", new=AsyncMock(return_value=0)) as count_recent,
        patch(f"{svc}.create_report", new=AsyncMock()) as create_report,
        patch(f"{svc}.increment_free_regens_granted", new=AsyncMock(return_value=True)) as increment,
        patch(f"{svc}.update_report", new=AsyncMock(return_value=True)) as update_report,
    ):
        # create_report echoes back whatever it was given, plus an id.
        async def _echo(data):
            return {**data, "id": "rep-new"}

        create_report.side_effect = _echo
        yield {
            "get_website": get_website,
            "find_existing": find_existing,
            "count_recent": count_recent,
            "create_report": create_report,
            "increment": increment,
            "update_report": update_report,
        }


class TestFeatureFlag:
    """Flag off → the feature does not exist. Zero behavior change elsewhere."""

    def test_report_endpoint_404_when_flag_off(self, client, auth_headers, monkeypatch):
        monkeypatch.delenv("ISSUE_REPORT_ENABLED", raising=False)
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "images_wrong"},
        )
        assert resp.status_code == 404

    def test_report_endpoint_404_when_flag_false(self, client, auth_headers, monkeypatch):
        monkeypatch.setenv("ISSUE_REPORT_ENABLED", "false")
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "images_wrong"},
        )
        assert resp.status_code == 404

    def test_admin_endpoints_404_when_flag_off(self, client, auth_headers, monkeypatch):
        monkeypatch.delenv("ISSUE_REPORT_ENABLED", raising=False)
        assert (
            client.get("/api/v1/admin/issue-reports", headers=auth_headers).status_code
            == 404
        )
        assert (
            client.patch(
                "/api/v1/admin/issue-reports/rep-1",
                headers=auth_headers,
                json={"status": "resolved"},
            ).status_code
            == 404
        )

    def test_flag_off_regenerate_never_consults_reports(
        self, client, auth_headers, test_user_id, monkeypatch
    ):
        """Zero behavior change: with the flag off, the regenerate endpoint
        must not even look for granted reports and must hit the normal
        quota path."""
        monkeypatch.delenv("ISSUE_REPORT_ENABLED", raising=False)
        with (
            patch(
                "app.api.v1.endpoints.websites.supabase_service.get_website",
                new=AsyncMock(return_value=_website_row(test_user_id)),
            ),
            patch(
                "app.api.v1.endpoints.websites.supabase_service.update_website",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "app.api.v1.endpoints.websites.subscription_service.check_limit",
                new=AsyncMock(return_value={"allowed": True}),
            ) as check_limit,
            patch(
                "app.services.issue_report_service.issue_report_service.get_unused_granted_report",
                new=AsyncMock(),
            ) as get_granted,
            patch(
                "app.api.v1.endpoints.websites.generate_website_content",
                new=AsyncMock(),
            ),
        ):
            resp = client.patch(
                "/api/v1/websites/ws-1/regenerate", headers=auth_headers, json={}
            )
        assert resp.status_code == 200, resp.text
        check_limit.assert_awaited_once()
        get_granted.assert_not_called()


class TestReportIssueEndpoint:
    def test_requires_auth(self, client, flag_on):
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue", json={"category": "other"}
        )
        assert resp.status_code in (401, 403)

    def test_404_when_website_missing(
        self, client, auth_headers, flag_on, report_patches
    ):
        report_patches["get_website"].return_value = None
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "images_wrong"},
        )
        assert resp.status_code == 404

    def test_403_when_not_owner(self, client, auth_headers, flag_on, report_patches):
        report_patches["get_website"].return_value = _website_row("someone-else")
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "images_wrong"},
        )
        assert resp.status_code == 403
        report_patches["create_report"].assert_not_called()

    def test_400_when_no_completed_generation(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        report_patches["get_website"].return_value = _website_row(
            test_user_id, generation_count=0, html_content=""
        )
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "page_broken"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "no_completed_generation"

    def test_invalid_category_rejected(
        self, client, auth_headers, flag_on, report_patches
    ):
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "i_dont_like_it"},
        )
        assert resp.status_code == 422

    def test_description_over_500_chars_rejected(
        self, client, auth_headers, flag_on, report_patches
    ):
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "other", "description": "x" * 501},
        )
        assert resp.status_code == 422

    def test_first_report_grants_free_regen_and_increments_counter(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        report_patches["get_website"].return_value = _website_row(
            test_user_id, free_regens_granted=0
        )
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "images_wrong", "description": "hero image is a car, not food"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "regen_granted"
        # Cap default is 2: one grant just used → one remaining.
        assert body["regens_remaining"] == 1
        # The report row was created as a grant...
        created = report_patches["create_report"].await_args.args[0]
        assert created["status"] == "auto_regen_granted"
        assert created["regen_used"] is False
        # ...and the per-site counter was bumped from its current value.
        report_patches["increment"].assert_awaited_once_with("ws-1", 0)

    def test_cap_reached_escalates(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        report_patches["get_website"].return_value = _website_row(
            test_user_id, free_regens_granted=2
        )
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "text_wrong"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "escalated"
        created = report_patches["create_report"].await_args.args[0]
        assert created["status"] == "escalated"
        # No grant → counter untouched.
        report_patches["increment"].assert_not_called()

    def test_duplicate_open_report_returns_existing_without_new_row(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        report_patches["get_website"].return_value = _website_row(
            test_user_id, free_regens_granted=1
        )
        report_patches["find_existing"].return_value = _report_row(
            report_id="rep-existing"
        )
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "images_wrong"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["report_id"] == "rep-existing"
        assert body["duplicate"] is True
        report_patches["create_report"].assert_not_called()
        report_patches["increment"].assert_not_called()

    def test_site_rate_limit_enforced(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        report_patches["get_website"].return_value = _website_row(test_user_id)

        async def counts(website_id=None, user_id=None):
            return 3 if website_id else 0  # site at the 3/24h cap

        report_patches["count_recent"].side_effect = counts
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "other"},
        )
        assert resp.status_code == 429
        report_patches["create_report"].assert_not_called()

    def test_user_rate_limit_enforced(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        report_patches["get_website"].return_value = _website_row(test_user_id)

        async def counts(website_id=None, user_id=None):
            return 10 if user_id else 0  # user at the 10/24h cap

        report_patches["count_recent"].side_effect = counts
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "other"},
        )
        assert resp.status_code == 429
        report_patches["create_report"].assert_not_called()

    def test_grant_counter_bump_failure_demotes_to_escalated(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        """An untracked grant must never be handed out: if the counter bump
        fails, the report is demoted to escalated."""
        report_patches["get_website"].return_value = _website_row(test_user_id)
        report_patches["increment"].return_value = False
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "page_broken"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "escalated"
        report_patches["update_report"].assert_awaited_once_with(
            "rep-new", {"status": "escalated"}
        )

    def test_diagnostics_snapshot_is_lightweight_metadata(
        self, client, auth_headers, test_user_id, flag_on, report_patches
    ):
        html = "<html><body>" + "x" * 5000 + "</body></html>"
        report_patches["get_website"].return_value = _website_row(
            test_user_id, html_content=html
        )
        resp = client.post(
            "/api/v1/websites/ws-1/report-issue",
            headers=auth_headers,
            json={"category": "images_wrong"},
        )
        assert resp.status_code == 200, resp.text
        diagnostics = report_patches["create_report"].await_args.args[0]["diagnostics"]
        assert diagnostics["html_sha256"] is not None
        assert diagnostics["html_length"] == len(html)
        assert diagnostics["generation_provider"] in ("glm", "deepseek")
        assert diagnostics["image_provider"] in ("zai", "stability")
        # The radar stores hashes and metadata — never the HTML itself.
        assert html not in str(diagnostics)


class TestFreeRegenerationPath:
    """The quota-bypass mechanism — the part that must never leak revenue."""

    @pytest.fixture
    def regen_patches(self, test_user_id):
        with (
            patch(
                "app.api.v1.endpoints.websites.supabase_service.get_website",
                new=AsyncMock(return_value=_website_row(test_user_id)),
            ) as get_website,
            patch(
                "app.api.v1.endpoints.websites.supabase_service.update_website",
                new=AsyncMock(return_value=True),
            ) as update_website,
            patch(
                "app.api.v1.endpoints.websites.subscription_service.check_limit",
                new=AsyncMock(return_value={"allowed": True}),
            ) as check_limit,
            patch(
                "app.services.issue_report_service.issue_report_service.get_unused_granted_report",
                new=AsyncMock(return_value=None),
            ) as get_granted,
            patch(
                "app.api.v1.endpoints.websites.generate_website_content",
                new=AsyncMock(),
            ) as background,
        ):
            yield {
                "get_website": get_website,
                "update_website": update_website,
                "check_limit": check_limit,
                "get_granted": get_granted,
                "background": background,
            }

    def test_granted_report_bypasses_quota_check(
        self, client, auth_headers, flag_on, regen_patches
    ):
        regen_patches["get_granted"].return_value = _report_row()
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate", headers=auth_headers, json={}
        )
        assert resp.status_code == 200, resp.text
        # The whole point: quota is neither checked nor blocked-on.
        regen_patches["check_limit"].assert_not_called()
        # The report id is threaded to the background task.
        args = regen_patches["background"].call_args.args
        assert args[3] == "rep-1"

    def test_quota_exhausted_user_can_still_use_grant(
        self, client, auth_headers, flag_on, regen_patches
    ):
        regen_patches["get_granted"].return_value = _report_row()
        regen_patches["check_limit"].return_value = {"allowed": False}
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate", headers=auth_headers, json={}
        )
        assert resp.status_code == 200, resp.text

    def test_no_grant_falls_through_to_normal_quota(
        self, client, auth_headers, flag_on, regen_patches
    ):
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate", headers=auth_headers, json={}
        )
        assert resp.status_code == 200, resp.text
        regen_patches["check_limit"].assert_awaited_once()
        assert regen_patches["background"].call_args.args[3] is None

    def test_regression_normal_regen_blocked_when_quota_exhausted(
        self, client, auth_headers, flag_on, regen_patches
    ):
        """No grant + exhausted quota → 403, exactly as today."""
        regen_patches["check_limit"].return_value = {
            "allowed": False,
            "message": "Had AI hero tercapai (1/1).",
        }
        resp = client.patch(
            "/api/v1/websites/ws-1/regenerate", headers=auth_headers, json={}
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "LIMIT_REACHED"


class TestFreeRegenBackgroundTask:
    """generate_website_content with free_regen_report_id set: no usage
    charged, report resolved on success, grant preserved on failure."""

    @pytest.fixture
    def task_patches(self):
        with (
            patch(
                "app.api.v1.endpoints.websites.supabase_service.get_website",
                new=AsyncMock(return_value={"id": "ws-1", "generation_count": 1}),
            ),
            patch(
                "app.api.v1.endpoints.websites.supabase_service.update_website",
                new=AsyncMock(return_value=True),
            ) as update_website,
            patch(
                "app.api.v1.endpoints.websites.subscription_service.increment_usage",
                new=AsyncMock(),
            ) as increment_usage,
            patch(
                "app.api.v1.endpoints.websites.subscription_service.check_limit",
                new=AsyncMock(return_value={"allowed": True, "remaining": 5}),
            ) as check_limit,
            patch(
                "app.services.issue_report_service.issue_report_service.mark_regen_completed",
                new=AsyncMock(return_value=True),
            ) as mark_completed,
        ):
            yield {
                "update_website": update_website,
                "increment_usage": increment_usage,
                "check_limit": check_limit,
                "mark_completed": mark_completed,
            }

    def _build_request(self):
        return WebsiteGenerationRequest(
            description="a kedai bakery in shah alam selling kek lapis",
            language=Language.MALAY,
            business_name="Kek Lapis",
            business_type="bakery",
            subdomain="keklapis",
            include_whatsapp=False,
            include_maps=False,
            include_ecommerce=False,
        )

    def _ai_response(self, ai_images_count=3):
        return AIGenerationResponse(
            html_content="<html><body>regenerated</body></html>",
            meta_title="t",
            meta_description="d",
            sections=["Hero"],
            integrations_included=[],
            ai_images_count=ai_images_count,
        )

    @pytest.mark.asyncio
    async def test_free_regen_charges_nothing_and_resolves_report(self, task_patches):
        from app.api.v1.endpoints import websites as websites_module

        with patch.object(
            websites_module.ai_service,
            "generate_website",
            new=AsyncMock(return_value=self._ai_response(ai_images_count=3)),
        ):
            await websites_module.generate_website_content(
                "ws-1",
                self._build_request(),
                user_id="user-1",
                free_regen_report_id="rep-1",
            )

        # Quota NOT decremented — not for the hero, not for the 3 images.
        task_patches["increment_usage"].assert_not_called()
        # No per-user image-quota lookup either — the free budget applies.
        task_patches["check_limit"].assert_not_called()
        # Report consumed exactly once, only after success.
        task_patches["mark_completed"].assert_awaited_once_with("rep-1")
        # And the site itself was updated to draft with a bumped counter.
        success_payloads = [
            call.args[1]
            for call in task_patches["update_website"].await_args_list
            if call.args[1].get("status") == "draft"
        ]
        assert success_payloads and success_payloads[-1]["generation_count"] == 2

    @pytest.mark.asyncio
    async def test_free_regen_failure_leaves_grant_intact(self, task_patches):
        from app.api.v1.endpoints import websites as websites_module

        with patch.object(
            websites_module.ai_service,
            "generate_website",
            new=AsyncMock(side_effect=Exception("provider 500")),
        ):
            await websites_module.generate_website_content(
                "ws-1",
                self._build_request(),
                user_id="user-1",
                free_regen_report_id="rep-1",
            )

        # Grant NOT consumed — the user retries without losing it.
        task_patches["mark_completed"].assert_not_called()
        task_patches["increment_usage"].assert_not_called()
        # Site flipped to failed as usual.
        statuses = [
            call.args[1].get("status")
            for call in task_patches["update_website"].await_args_list
        ]
        assert "failed" in statuses

    @pytest.mark.asyncio
    async def test_free_regen_uses_bounded_free_image_budget(self, task_patches):
        """The image cap is the explicit FREE_AI_IMAGES_PER_SITE budget —
        bounded, never None/unlimited."""
        from app.api.v1.endpoints import websites as websites_module

        captured = {}

        async def capture_generate(request, max_ai_images=None, **kwargs):
            captured["max_ai_images"] = max_ai_images
            return self._ai_response()

        with patch.object(
            websites_module.ai_service, "generate_website", new=capture_generate
        ):
            await websites_module.generate_website_content(
                "ws-1",
                self._build_request(),
                user_id="user-1",
                free_regen_report_id="rep-1",
            )

        from app.services.ai_service import free_ai_images_per_site

        assert captured["max_ai_images"] == free_ai_images_per_site()
        assert captured["max_ai_images"] is not None

    @pytest.mark.asyncio
    async def test_regression_normal_regen_still_charges_quota(self, task_patches):
        """No report id → identical to today's behavior: hero + image
        usage incremented after success, report machinery never touched."""
        from app.api.v1.endpoints import websites as websites_module

        with patch.object(
            websites_module.ai_service,
            "generate_website",
            new=AsyncMock(return_value=self._ai_response(ai_images_count=2)),
        ):
            await websites_module.generate_website_content(
                "ws-1", self._build_request(), user_id="user-1"
            )

        charged_actions = [
            call.args[1] for call in task_patches["increment_usage"].await_args_list
        ]
        assert "generate_ai_hero" in charged_actions
        assert "generate_ai_image" in charged_actions
        task_patches["mark_completed"].assert_not_called()


class TestAdminEndpoints:
    @pytest.fixture
    def admin_patches(self):
        svc = "app.api.v1.endpoints.issue_reports.issue_report_service"
        with (
            patch(
                "app.api.v1.endpoints.issue_reports.subscription_service._is_admin",
                new=AsyncMock(return_value=True),
            ) as is_admin,
            patch(f"{svc}.list_reports", new=AsyncMock(return_value=[])) as list_reports,
            patch(f"{svc}.get_report", new=AsyncMock(return_value=_report_row())) as get_report,
            patch(f"{svc}.update_report", new=AsyncMock(return_value=True)) as update_report,
        ):
            yield {
                "is_admin": is_admin,
                "list_reports": list_reports,
                "get_report": get_report,
                "update_report": update_report,
            }

    def test_non_admin_gets_403(self, client, auth_headers, flag_on, admin_patches):
        admin_patches["is_admin"].return_value = False
        resp = client.get(
            "/api/v1/admin/issue-reports?status=escalated", headers=auth_headers
        )
        assert resp.status_code == 403

    def test_list_filters_by_status(self, client, auth_headers, flag_on, admin_patches):
        admin_patches["list_reports"].return_value = [
            _report_row(status="escalated")
        ]
        resp = client.get(
            "/api/v1/admin/issue-reports?status=escalated", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["reports"][0]["status"] == "escalated"
        kwargs = admin_patches["list_reports"].await_args.kwargs
        assert kwargs["status_filter"] == "escalated"

    def test_patch_sets_status_and_note(
        self, client, auth_headers, flag_on, admin_patches
    ):
        resp = client.patch(
            "/api/v1/admin/issue-reports/rep-1",
            headers=auth_headers,
            json={"status": "rejected", "admin_note": "user deleted the hero image themselves"},
        )
        assert resp.status_code == 200, resp.text
        payload = admin_patches["update_report"].await_args.args[1]
        assert payload["status"] == "rejected"
        assert payload["admin_note"] == "user deleted the hero image themselves"
        assert payload["resolved_at"] is not None

    def test_patch_rejects_invalid_status(
        self, client, auth_headers, flag_on, admin_patches
    ):
        resp = client.patch(
            "/api/v1/admin/issue-reports/rep-1",
            headers=auth_headers,
            json={"status": "auto_regen_granted"},
        )
        assert resp.status_code == 422

    def test_patch_404_when_report_missing(
        self, client, auth_headers, flag_on, admin_patches
    ):
        admin_patches["get_report"].return_value = None
        resp = client.patch(
            "/api/v1/admin/issue-reports/rep-missing",
            headers=auth_headers,
            json={"status": "resolved"},
        )
        assert resp.status_code == 404


class TestFlagAndCapHelpers:
    def test_flag_default_off(self, monkeypatch):
        from app.services.issue_report_service import issue_report_enabled

        monkeypatch.delenv("ISSUE_REPORT_ENABLED", raising=False)
        assert issue_report_enabled() is False

    def test_flag_read_at_call_time(self, monkeypatch):
        from app.services.issue_report_service import issue_report_enabled

        monkeypatch.setenv("ISSUE_REPORT_ENABLED", "true")
        assert issue_report_enabled() is True
        monkeypatch.setenv("ISSUE_REPORT_ENABLED", "false")
        assert issue_report_enabled() is False

    def test_cap_default_and_env_override(self, monkeypatch):
        from app.services.issue_report_service import issue_free_regen_cap

        monkeypatch.delenv("ISSUE_FREE_REGEN_CAP", raising=False)
        assert issue_free_regen_cap() == 2
        monkeypatch.setenv("ISSUE_FREE_REGEN_CAP", "5")
        assert issue_free_regen_cap() == 5
        monkeypatch.setenv("ISSUE_FREE_REGEN_CAP", "not-a-number")
        assert issue_free_regen_cap() == 2
        monkeypatch.setenv("ISSUE_FREE_REGEN_CAP", "-3")
        assert issue_free_regen_cap() == 0
