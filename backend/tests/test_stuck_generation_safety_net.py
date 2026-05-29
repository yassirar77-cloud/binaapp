"""
Tests for the three-layer stuck-generation safety net.

Layer 1: heartbeat task next to the AI call
Layer 2: scheduler job that sweeps stuck rows
Layer 3: admin endpoint that manually unsticks a row

External calls (Supabase, AI) are mocked. These tests are fully offline
and finish in well under a second.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import generation_heartbeat as gh

# The endpoint modules transitively import python-jose / supabase which may
# not be installed in every test environment (CI installs them; some local
# containers don't). The pure-logic tests still run; endpoint tests skip
# rather than reporting a false negative for the safety-net behaviour.
try:
    from app.api.v1.endpoints import websites as websites_mod  # noqa: F401
    from app.api.admin import unstick_generation as unstick_endpoint  # noqa: F401

    ENDPOINT_IMPORTS_AVAILABLE = True
except Exception:
    websites_mod = None  # type: ignore
    unstick_endpoint = None  # type: ignore
    ENDPOINT_IMPORTS_AVAILABLE = False

requires_endpoints = pytest.mark.skipif(
    not ENDPOINT_IMPORTS_AVAILABLE,
    reason="endpoint modules' transitive deps (jose/supabase) not installed",
)


# ---------------------------------------------------------------------------
# Layer 1: heartbeat loop
# ---------------------------------------------------------------------------


class TestHeartbeatLoop:
    @pytest.mark.asyncio
    async def test_writes_timestamp_on_each_tick(self):
        """Heartbeat fires once immediately, then again after the interval."""
        with patch.object(
            gh.supabase_service,
            "update_website",
            new=AsyncMock(return_value=True),
        ) as mock_update:
            task = asyncio.create_task(
                gh.heartbeat_loop("ws-1", interval_seconds=0.05)
            )
            # Long enough for the immediate write + two interval ticks.
            await asyncio.sleep(0.18)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert mock_update.call_count >= 3
        # Every call must target the right row and only touch the
        # heartbeat column — nothing else.
        for call in mock_update.call_args_list:
            args, kwargs = call
            assert args[0] == "ws-1"
            assert set(args[1].keys()) == {"last_heartbeat_at"}
            assert args[1]["last_heartbeat_at"] is not None

    @pytest.mark.asyncio
    async def test_swallows_supabase_errors_without_crashing(self):
        """A failing heartbeat write must not kill the loop."""
        with patch.object(
            gh.supabase_service,
            "update_website",
            new=AsyncMock(side_effect=RuntimeError("supabase down")),
        ) as mock_update:
            task = asyncio.create_task(
                gh.heartbeat_loop("ws-2", interval_seconds=0.05)
            )
            await asyncio.sleep(0.12)
            assert not task.done()  # still ticking despite the error
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        assert mock_update.call_count >= 2

    @pytest.mark.asyncio
    async def test_clear_heartbeat_sets_null(self):
        with patch.object(
            gh.supabase_service,
            "update_website",
            new=AsyncMock(return_value=True),
        ) as mock_update:
            await gh.clear_heartbeat("ws-3")
        mock_update.assert_awaited_once_with(
            "ws-3", {"last_heartbeat_at": None}
        )


@requires_endpoints
class TestGenerationLifecycleClears:
    """Integration-flavoured: drive `generate_website_content` and prove
    the heartbeat is cancelled + cleared on both success and failure."""

    @pytest.mark.asyncio
    async def test_heartbeat_cleared_on_success(self):
        from app.api.v1.endpoints import websites as websites_mod

        fake_request = MagicMock()
        fake_request.business_name = "Kedai"
        fake_request.language = MagicMock(value="ms")
        fake_request.include_ecommerce = False
        fake_request.whatsapp_number = None
        fake_request.business_type = None
        fake_request.description = "desc"

        fake_ai_response = MagicMock()
        fake_ai_response.html_content = "<html></html>"
        fake_ai_response.ai_images_count = 0
        fake_ai_response.integrations_included = []
        fake_ai_response.meta_title = "t"
        fake_ai_response.meta_description = "d"
        fake_ai_response.sections = []

        with (
            patch.object(
                websites_mod.ai_service,
                "generate_website",
                new=AsyncMock(return_value=fake_ai_response),
            ),
            patch.object(
                websites_mod,
                "extract_theme_tokens",
                return_value={},
                create=True,
            ),
            patch.object(
                websites_mod,
                "TemplateService",
                return_value=MagicMock(
                    inject_chat_widget=MagicMock(
                        return_value="<html></html>"
                    ),
                ),
            ),
            patch.object(
                websites_mod.supabase_service,
                "get_website",
                new=AsyncMock(return_value={"generation_count": 0}),
            ),
            patch.object(
                websites_mod.supabase_service,
                "update_website",
                new=AsyncMock(return_value=True),
            ) as mock_update,
            patch.object(
                websites_mod.subscription_service,
                "increment_usage",
                new=AsyncMock(return_value=None),
            ),
        ):
            await websites_mod.generate_website_content(
                "ws-success", fake_request, user_id="u1"
            )

        clear_calls = [
            c for c in mock_update.call_args_list
            if c.args[1].get("last_heartbeat_at") is None
            and "status" not in c.args[1]
        ]
        assert clear_calls, "expected a heartbeat NULL write on success"

    @pytest.mark.asyncio
    async def test_heartbeat_cleared_on_failure(self):
        from app.api.v1.endpoints import websites as websites_mod

        fake_request = MagicMock()
        fake_request.business_name = "Kedai"
        fake_request.language = MagicMock(value="ms")
        fake_request.include_ecommerce = False
        fake_request.business_type = None
        fake_request.description = "desc"

        with (
            patch.object(
                websites_mod.ai_service,
                "generate_website",
                new=AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(
                websites_mod.supabase_service,
                "update_website",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            await websites_mod.generate_website_content(
                "ws-fail", fake_request, user_id="u1"
            )

        clear_calls = [
            c for c in mock_update.call_args_list
            if c.args[1].get("last_heartbeat_at") is None
            and "status" not in c.args[1]
        ]
        failed_calls = [
            c for c in mock_update.call_args_list
            if c.args[1].get("status") == "failed"
        ]
        assert failed_calls, "expected the failure status write"
        assert clear_calls, "expected a heartbeat NULL write on failure too"


# ---------------------------------------------------------------------------
# Layer 2: stuck-sweeper
# ---------------------------------------------------------------------------


class TestStuckSweeper:
    @pytest.mark.asyncio
    async def test_flips_stuck_rows_to_failed(self):
        stuck_rows = [
            {"id": "ws-stuck-1", "status": "generating"},
            {"id": "ws-stuck-2", "status": "generating"},
        ]
        with (
            patch.object(
                gh,
                "find_stuck_websites",
                new=AsyncMock(return_value=stuck_rows),
            ),
            patch.object(
                gh.supabase_service,
                "update_website",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            result = await gh.sweep_stuck_generations()

        assert result["count"] == 2
        assert set(result["ids"]) == {"ws-stuck-1", "ws-stuck-2"}
        for call in mock_update.call_args_list:
            payload = call.args[1]
            assert payload["status"] == "failed"
            assert payload["last_heartbeat_at"] is None
            assert "timeout" in payload["error_message"].lower()

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_stuck_rows(self):
        with (
            patch.object(
                gh, "find_stuck_websites", new=AsyncMock(return_value=[])
            ),
            patch.object(
                gh.supabase_service,
                "update_website",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            result = await gh.sweep_stuck_generations()

        assert result == {"checked": True, "count": 0, "ids": []}
        mock_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_find_stuck_filters_recent_heartbeat(self):
        """The PostgREST query must include the `lt.<cutoff>` clause that
        excludes rows whose heartbeat is fresher than the threshold."""
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.json = MagicMock(return_value=[])
        captured = {}

        class _FakeClient:
            def __init__(self, *a, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, headers=None, params=None):
                captured["params"] = params
                return fake_response

        with patch("app.services.generation_heartbeat.httpx.AsyncClient", _FakeClient):
            await gh.find_stuck_websites(threshold_minutes=5)

        params = captured["params"]
        assert params["status"] == "eq.generating"
        assert "last_heartbeat_at.is.null" in params["or"]
        assert "last_heartbeat_at.lt." in params["or"]
        assert params["updated_at"].startswith("lt.")


# ---------------------------------------------------------------------------
# Layer 3: admin unstick endpoint
# ---------------------------------------------------------------------------


@requires_endpoints
class TestAdminUnstickEndpoint:
    """Drive the endpoint coroutine directly — avoids spinning up the
    full FastAPI app, but exercises auth + status checks + DB updates."""

    @pytest.fixture
    def caller_admin(self):
        return {"sub": "admin-user"}

    @pytest.fixture
    def caller_normie(self):
        return {"sub": "regular-user"}

    @pytest.mark.asyncio
    async def test_non_admin_gets_403(self, caller_normie):
        from app.api.admin import unstick_generation as endpoint
        from fastapi import HTTPException

        with patch.object(
            endpoint.subscription_service,
            "_is_admin",
            new=AsyncMock(return_value=False),
        ):
            with pytest.raises(HTTPException) as exc:
                await endpoint.unstick_generation(
                    "ws-1", current_user=caller_normie
                )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_website_returns_404(self, caller_admin):
        from app.api.admin import unstick_generation as endpoint
        from fastapi import HTTPException

        with (
            patch.object(
                endpoint.subscription_service,
                "_is_admin",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                endpoint.supabase_service,
                "get_website",
                new=AsyncMock(return_value=None),
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await endpoint.unstick_generation(
                    "ws-missing", current_user=caller_admin
                )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_status_returns_400_with_current_status(
        self, caller_admin
    ):
        from app.api.admin import unstick_generation as endpoint
        from fastapi import HTTPException

        with (
            patch.object(
                endpoint.subscription_service,
                "_is_admin",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                endpoint.supabase_service,
                "get_website",
                new=AsyncMock(return_value={"id": "ws-1", "status": "draft"}),
            ),
            patch.object(
                endpoint.supabase_service,
                "update_website",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            with pytest.raises(HTTPException) as exc:
                await endpoint.unstick_generation(
                    "ws-1", current_user=caller_admin
                )
        assert exc.value.status_code == 400
        assert exc.value.detail["current_status"] == "draft"
        mock_update.assert_not_awaited()  # no side effect on no-op

    @pytest.mark.asyncio
    async def test_generating_status_flips_to_failed(self, caller_admin):
        from app.api.admin import unstick_generation as endpoint

        stuck_row = {
            "id": "ws-stuck",
            "status": "generating",
            "subdomain": "houok",
        }
        flipped_row = {
            "id": "ws-stuck",
            "status": "failed",
            "subdomain": "houok",
            "error_message": "manually unstuck",
            "updated_at": "2026-05-23T09:00:00+00:00",
        }
        with (
            patch.object(
                endpoint.subscription_service,
                "_is_admin",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                endpoint.supabase_service,
                "get_website",
                new=AsyncMock(side_effect=[stuck_row, flipped_row]),
            ),
            patch.object(
                endpoint.supabase_service,
                "update_website",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            result = await endpoint.unstick_generation(
                "ws-stuck", current_user=caller_admin
            )

        assert result["ok"] is True
        assert result["previous_status"] == "generating"
        assert result["new_status"] == "failed"
        payload = mock_update.call_args.args[1]
        assert payload["status"] == "failed"
        assert payload["last_heartbeat_at"] is None
        assert "admin" in payload["error_message"].lower()
