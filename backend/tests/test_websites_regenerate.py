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
        # Persisted description, but generation_count is NOT bumped here
        # anymore — that move-on-success is the whole point of the
        # post-PR665 hardening fix. The background task does the bump.
        patches["update_website"].assert_awaited()
        update_call_kwargs = patches["update_website"].await_args.args[1]
        assert (
            update_call_kwargs["description"]
            == "completely new vibe — modern minimalist"
        )
        assert "generation_count" not in update_call_kwargs

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
        # Same rule: counter only bumps inside the background task on
        # success, never in the synchronous PATCH.
        assert "generation_count" not in update_payload


class TestGenerationCountIncrementsOnlyOnSuccess:
    """The background task — generate_website_content — owns the
    generation_count bump. These tests pin that contract: the counter
    moves on success and stays put on failure (timeout or otherwise),
    so a flaky AI provider can't burn the user's quota."""

    @pytest.fixture
    def patched_supabase(self):
        """Patch supabase_service so we can inspect every update_website call
        the background task makes."""
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
                "app.api.v1.endpoints.websites.subscription_service.increment_usage",
                new=AsyncMock(),
            ),
        ):
            yield {"get_website": get_website, "update_website": update_website}

    def _build_request(self):
        from app.models.schemas import WebsiteGenerationRequest, Language

        return WebsiteGenerationRequest(
            description="a kedai bakery in shah alam selling kek lapis and roti",
            language=Language.MALAY,
            business_name="Kek Lapis Sarawak",
            business_type="bakery",
            subdomain="keklapis",
            include_whatsapp=True,
            whatsapp_number="+60123456789",
            include_maps=False,
            include_ecommerce=False,
        )

    @pytest.mark.asyncio
    async def test_success_bumps_generation_count_by_one(self, patched_supabase):
        from app.api.v1.endpoints import websites as websites_module
        from app.models.schemas import AIGenerationResponse

        patched_supabase["get_website"].return_value = {
            "id": "ws-1",
            "generation_count": 4,
        }
        fake_response = AIGenerationResponse(
            html_content="<html><body>generated</body></html>",
            css_content=None,
            js_content=None,
            meta_title="Kek Lapis Sarawak",
            meta_description="Kek lapis traditional",
            sections=["Header", "Hero"],
            integrations_included=["WhatsApp"],
            ai_images_count=0,
        )
        with patch.object(
            websites_module.ai_service,
            "generate_website",
            new=AsyncMock(return_value=fake_response),
        ):
            await websites_module.generate_website_content(
                "ws-1", self._build_request(), user_id="user-1"
            )

        # The success update must include generation_count = prev + 1.
        success_calls = [
            call.args[1]
            for call in patched_supabase["update_website"].await_args_list
            if call.args[1].get("status") == "draft"
        ]
        assert success_calls, "expected at least one success update"
        assert success_calls[-1]["generation_count"] == 5
        assert success_calls[-1].get("error_message") is None

    @pytest.mark.asyncio
    async def test_timeout_does_not_bump_generation_count(self, patched_supabase):
        import asyncio
        from app.api.v1.endpoints import websites as websites_module

        # Background task hits the endpoint-level wait_for ceiling. The
        # except block must mark status=failed WITHOUT touching the
        # counter — the user gets a free retry, not a billed failure.
        with patch.object(
            websites_module.ai_service,
            "generate_website",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            await websites_module.generate_website_content(
                "ws-1", self._build_request(), user_id="user-1"
            )

        all_payloads = [
            call.args[1] for call in patched_supabase["update_website"].await_args_list
        ]
        # Every update made during the failure path must omit generation_count.
        for payload in all_payloads:
            assert "generation_count" not in payload, (
                f"failure path must not bump generation_count, got {payload}"
            )
        # And at least one update must have flipped status to failed.
        statuses = [p.get("status") for p in all_payloads]
        assert "failed" in statuses

    @pytest.mark.asyncio
    async def test_generic_exception_does_not_bump_generation_count(
        self, patched_supabase
    ):
        from app.api.v1.endpoints import websites as websites_module

        with patch.object(
            websites_module.ai_service,
            "generate_website",
            new=AsyncMock(side_effect=Exception("provider 500")),
        ):
            await websites_module.generate_website_content(
                "ws-1", self._build_request(), user_id="user-1"
            )

        all_payloads = [
            call.args[1] for call in patched_supabase["update_website"].await_args_list
        ]
        for payload in all_payloads:
            assert "generation_count" not in payload


class TestAITimeoutRetry:
    """generate_website's bounded-retry path: primary times out → fall
    back to Qwen on a shorter budget → succeed or surface TimeoutError."""

    @pytest.mark.asyncio
    async def test_primary_timeout_falls_back_to_qwen(self, monkeypatch):
        import asyncio
        from app.services import ai_service as ai_service_module
        from app.models.schemas import WebsiteGenerationRequest, Language

        monkeypatch.setenv("AI_TIMEOUT_RETRY_ENABLED", "true")

        svc = ai_service_module.AIService()

        # Primary hangs forever; the wait_for budget makes it raise
        # TimeoutError. Fallback returns valid HTML inside the budget.
        async def slow_deepseek(*args, **kwargs):
            await asyncio.sleep(10)
            return "should never reach here"

        async def quick_qwen(prompt, *args, **kwargs):
            return "<html><body>fallback ok</body></html>", {
                "was_truncated": False,
                "truncation_retries": 0,
                "needs_manual_review": False,
                "unclosed_tags": [],
            }

        # Shrink budgets so the test doesn't actually wait 120s.
        monkeypatch.setattr(
            ai_service_module, "AI_PRIMARY_TIMEOUT_SECONDS", 0.05
        )
        monkeypatch.setattr(
            ai_service_module, "AI_FALLBACK_TIMEOUT_SECONDS", 5.0
        )

        with (
            patch.object(svc, "_call_deepseek", side_effect=slow_deepseek),
            patch.object(
                svc, "_call_qwen_with_truncation_retry", side_effect=quick_qwen
            ),
            # Stub the rest of the pipeline so the test stays focused on
            # the timeout retry contract.
            patch.object(
                svc, "_build_strict_prompt", return_value="<prompt>"
            ),
            patch.object(svc, "_fix_placeholders", side_effect=lambda h, *a, **k: h),
            patch.object(svc, "_fix_menu_item_images", side_effect=lambda h, *a, **k: h),
            patch.object(svc, "_fix_broken_image_urls", side_effect=lambda h, *a, **k: h),
            patch.object(
                svc, "_validate_generated_html", return_value=[]
            ),
        ):
            request = WebsiteGenerationRequest(
                description="a kedai roti in shah alam",
                language=Language.MALAY,
                business_name="Kedai Roti",
                business_type="bakery",
                subdomain="kedairoti",
                include_whatsapp=False,
                include_maps=False,
                include_ecommerce=False,
            )
            response = await svc.generate_website(request, image_choice="none")

        assert response.html_content
        assert "fallback ok" in response.html_content

    @pytest.mark.asyncio
    async def test_disabled_flag_skips_wait_for_wrapper(self, monkeypatch):
        # When AI_TIMEOUT_RETRY_ENABLED=false, the primary call runs
        # without a wait_for ceiling — same behaviour as before the
        # post-PR665 hardening. Rollback safety net.
        from app.services import ai_service as ai_service_module

        monkeypatch.setenv("AI_TIMEOUT_RETRY_ENABLED", "false")
        assert ai_service_module._ai_timeout_retry_enabled() is False
        monkeypatch.setenv("AI_TIMEOUT_RETRY_ENABLED", "true")
        assert ai_service_module._ai_timeout_retry_enabled() is True
        monkeypatch.setenv("AI_TIMEOUT_RETRY_ENABLED", "FALSE")
        assert ai_service_module._ai_timeout_retry_enabled() is False

    @pytest.mark.asyncio
    async def test_both_models_timeout_raises_timeout_error(self, monkeypatch):
        import asyncio
        from app.services import ai_service as ai_service_module
        from app.models.schemas import WebsiteGenerationRequest, Language

        monkeypatch.setenv("AI_TIMEOUT_RETRY_ENABLED", "true")
        monkeypatch.setattr(
            ai_service_module, "AI_PRIMARY_TIMEOUT_SECONDS", 0.05
        )
        monkeypatch.setattr(
            ai_service_module, "AI_FALLBACK_TIMEOUT_SECONDS", 0.05
        )

        svc = ai_service_module.AIService()

        async def hang(*args, **kwargs):
            await asyncio.sleep(10)

        with (
            patch.object(svc, "_call_deepseek", side_effect=hang),
            patch.object(svc, "_call_qwen_with_truncation_retry", side_effect=hang),
            patch.object(svc, "_build_strict_prompt", return_value="<prompt>"),
        ):
            request = WebsiteGenerationRequest(
                description="a kedai roti in shah alam",
                language=Language.MALAY,
                business_name="Kedai Roti",
                business_type="bakery",
                subdomain="kedairoti",
                include_whatsapp=False,
                include_maps=False,
                include_ecommerce=False,
            )
            with pytest.raises(asyncio.TimeoutError):
                await svc.generate_website(request, image_choice="none")
