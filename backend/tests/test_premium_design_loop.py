"""
Tests for the premium design critique loop (PREMIUM_DESIGN_LOOP flag).

Covers:
- Critique JSON parsing (clean JSON, fenced JSON, prose-wrapped, garbage,
  improvements capped at 5)
- One-revision cap: exactly one DeepSeek review + at most one GLM revision
  per generation, even when the critique still reports issues
- Review failure (timeout / HTTP error / unparseable) falls through to the
  original HTML without calling GLM
- Flag off = zero extra calls (no review, no revision, no HTTP traffic)

All HTTP calls are mocked — no live API usage.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import app.services.ai_service as ai_service_module
from app.services.ai_service import AIService


ORIGINAL_HTML = "<!DOCTYPE html><html><body><h1>Nasi Lemak Pak Din</h1></body></html>"
REVISED_HTML = "<!DOCTYPE html><html><body><h1>Nasi Lemak Pak Din (revised)</h1></body></html>"

CRITIQUE_WITH_ISSUES = {
    "pass": False,
    "violations": ["rule 2: missing location section"],
    "improvements": ["Increase hero heading contrast", "Tighten menu card spacing"],
}
CRITIQUE_CLEAN = {"pass": True, "violations": [], "improvements": []}


def _mock_httpx_response(content: str, status_code: int = 200):
    """MagicMock mimicking httpx.Response for a chat completion."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = "error body"
    resp.json.return_value = {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"completion_tokens": 100},
    }
    return resp


def _patch_async_client(mock_response):
    """Patch httpx.AsyncClient so client.post() returns mock_response.
    Returns (patcher, mock_post) for request-body assertions."""
    mock_post = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.post = mock_post
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return patch.object(ai_service_module.httpx, "AsyncClient",
                        return_value=mock_ctx), mock_post


@pytest.fixture
def service():
    svc = AIService()
    svc.deepseek_api_key = "test-deepseek-key"
    svc.deepseek_base_url = "https://api.deepseek.com/v1"
    svc.zai_api_key = "test-zai-key"
    svc.zai_base_url = "https://api.z.ai/api/paas/v4"
    svc.zai_model = "glm-5.2"
    return svc


def _flag(value: bool):
    return patch.object(ai_service_module, "PREMIUM_DESIGN_LOOP", value)


# ── critique parsing ─────────────────────────────────────────────────────────

class TestCritiqueParsing:

    def test_clean_json_parsed(self):
        critique = AIService._parse_design_critique(json.dumps(CRITIQUE_WITH_ISSUES))
        assert critique == CRITIQUE_WITH_ISSUES

    def test_fenced_json_parsed(self):
        content = "```json\n" + json.dumps(CRITIQUE_CLEAN) + "\n```"
        critique = AIService._parse_design_critique(content)
        assert critique == CRITIQUE_CLEAN

    def test_prose_wrapped_json_parsed(self):
        content = "Here is my review:\n" + json.dumps(CRITIQUE_WITH_ISSUES) + "\nHope this helps!"
        critique = AIService._parse_design_critique(content)
        assert critique["pass"] is False
        assert critique["violations"] == CRITIQUE_WITH_ISSUES["violations"]

    def test_improvements_capped_at_five(self):
        raw = {"pass": True, "violations": [],
               "improvements": [f"fix {i}" for i in range(9)]}
        critique = AIService._parse_design_critique(json.dumps(raw))
        assert len(critique["improvements"]) == 5

    def test_garbage_returns_none(self):
        assert AIService._parse_design_critique("not json at all") is None
        assert AIService._parse_design_critique("") is None
        assert AIService._parse_design_critique(None) is None
        assert AIService._parse_design_critique("[1, 2, 3]") is None

    def test_missing_keys_normalised(self):
        critique = AIService._parse_design_critique('{"pass": false}')
        assert critique == {"pass": False, "violations": [], "improvements": []}

    @pytest.mark.asyncio
    async def test_review_call_parses_critique_end_to_end(self, service):
        """Full _review_design_with_deepseek: request shape + parsed result."""
        patcher, mock_post = _patch_async_client(
            _mock_httpx_response(json.dumps(CRITIQUE_WITH_ISSUES)))
        with patcher:
            critique = await service._review_design_with_deepseek(ORIGINAL_HTML)

        assert critique == CRITIQUE_WITH_ISSUES
        body = mock_post.call_args.kwargs["json"]
        assert body["model"] == ai_service_module.DESIGN_REVIEW_MODEL
        assert body["thinking"] == {"type": "disabled"}
        assert body["response_format"] == {"type": "json_object"}
        # Reviewer system prompt carries the hard rules; user message is the HTML
        assert "HARD RULES" in body["messages"][0]["content"]
        assert body["messages"][1]["content"] == ORIGINAL_HTML


# ── one-revision cap ─────────────────────────────────────────────────────────

class TestOneRevisionCap:

    @pytest.mark.asyncio
    async def test_exactly_one_review_and_one_revision(self, service):
        """Even when the critique reports issues, GLM is asked to revise
        exactly once and the reviewer is never consulted again."""
        review = AsyncMock(return_value=dict(CRITIQUE_WITH_ISSUES))
        revise = AsyncMock(return_value=REVISED_HTML)
        with _flag(True), \
             patch.object(service, "_review_design_with_deepseek", review), \
             patch.object(service, "_call_glm", revise):
            result = await service._run_premium_design_loop(ORIGINAL_HTML)

        assert result == REVISED_HTML
        assert review.await_count == 1
        assert revise.await_count == 1

    @pytest.mark.asyncio
    async def test_revision_prompt_carries_critique_and_own_html(self, service):
        review = AsyncMock(return_value=dict(CRITIQUE_WITH_ISSUES))
        revise = AsyncMock(return_value=REVISED_HTML)
        with _flag(True), \
             patch.object(service, "_review_design_with_deepseek", review), \
             patch.object(service, "_call_glm", revise):
            await service._run_premium_design_loop(ORIGINAL_HTML)

        prompt = revise.call_args.args[0]
        assert ORIGINAL_HTML in prompt
        assert "rule 2: missing location section" in prompt
        assert "Increase hero heading contrast" in prompt

    @pytest.mark.asyncio
    async def test_clean_review_skips_revision(self, service):
        review = AsyncMock(return_value=dict(CRITIQUE_CLEAN))
        revise = AsyncMock(return_value=REVISED_HTML)
        with _flag(True), \
             patch.object(service, "_review_design_with_deepseek", review), \
             patch.object(service, "_call_glm", revise):
            result = await service._run_premium_design_loop(ORIGINAL_HTML)

        assert result == ORIGINAL_HTML
        assert review.await_count == 1
        assert revise.await_count == 0

    @pytest.mark.asyncio
    async def test_bad_revision_ships_original(self, service):
        """A failed/empty/non-HTML revision never replaces the original."""
        for bad in (None, "", "sorry, I cannot do that"):
            review = AsyncMock(return_value=dict(CRITIQUE_WITH_ISSUES))
            revise = AsyncMock(return_value=bad)
            with _flag(True), \
                 patch.object(service, "_review_design_with_deepseek", review), \
                 patch.object(service, "_call_glm", revise):
                result = await service._run_premium_design_loop(ORIGINAL_HTML)
            assert result == ORIGINAL_HTML
            assert revise.await_count == 1  # still only ONE attempt

    @pytest.mark.asyncio
    async def test_truncated_revision_ships_original_and_restores_api_state(self, service):
        original_state = {"provider": "glm", "finish_reason": "stop", "truncated": False}
        service._last_api_call = dict(original_state)

        async def truncated_revision(*args, **kwargs):
            service._last_api_call = {"provider": "glm", "finish_reason": "length",
                                      "truncated": True}
            return REVISED_HTML

        review = AsyncMock(return_value=dict(CRITIQUE_WITH_ISSUES))
        with _flag(True), \
             patch.object(service, "_review_design_with_deepseek", review), \
             patch.object(service, "_call_glm", side_effect=truncated_revision):
            result = await service._run_premium_design_loop(ORIGINAL_HTML)

        assert result == ORIGINAL_HTML
        # Upstream truncation checks must reflect the shipped (original) HTML
        assert service._last_api_call == original_state


# ── review failure falls through ─────────────────────────────────────────────

class TestReviewFailureFallsThrough:

    @pytest.mark.asyncio
    async def test_review_returning_none_ships_original_without_revision(self, service):
        review = AsyncMock(return_value=None)
        revise = AsyncMock(return_value=REVISED_HTML)
        with _flag(True), \
             patch.object(service, "_review_design_with_deepseek", review), \
             patch.object(service, "_call_glm", revise):
            result = await service._run_premium_design_loop(ORIGINAL_HTML)

        assert result == ORIGINAL_HTML
        assert revise.await_count == 0

    @pytest.mark.asyncio
    async def test_review_timeout_returns_none(self, service):
        """A hung DeepSeek reviewer is bounded by the 30s cap and yields None."""
        import asyncio as _asyncio

        mock_post = AsyncMock(side_effect=_asyncio.TimeoutError())
        mock_client = MagicMock()
        mock_client.post = mock_post
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        with patch.object(ai_service_module.httpx, "AsyncClient", return_value=mock_ctx):
            critique = await service._review_design_with_deepseek(ORIGINAL_HTML)
        assert critique is None

    @pytest.mark.asyncio
    async def test_review_http_error_returns_none(self, service):
        patcher, _ = _patch_async_client(_mock_httpx_response("", status_code=500))
        with patcher:
            critique = await service._review_design_with_deepseek(ORIGINAL_HTML)
        assert critique is None

    @pytest.mark.asyncio
    async def test_review_unparseable_content_returns_none(self, service):
        patcher, _ = _patch_async_client(_mock_httpx_response("I liked it a lot!"))
        with patcher:
            critique = await service._review_design_with_deepseek(ORIGINAL_HTML)
        assert critique is None

    @pytest.mark.asyncio
    async def test_missing_deepseek_key_skips_review(self, service):
        service.deepseek_api_key = None
        patcher, mock_post = _patch_async_client(_mock_httpx_response("{}"))
        with patcher:
            critique = await service._review_design_with_deepseek(ORIGINAL_HTML)
        assert critique is None
        assert mock_post.await_count == 0


# ── flag off = zero extra calls ──────────────────────────────────────────────

class TestFlagOff:

    @pytest.mark.asyncio
    async def test_flag_off_makes_zero_calls(self, service):
        """With PREMIUM_DESIGN_LOOP off the loop is a pure pass-through:
        no reviewer call, no GLM call, no HTTP traffic at all."""
        patcher, mock_post = _patch_async_client(
            _mock_httpx_response(json.dumps(CRITIQUE_WITH_ISSUES)))
        review = AsyncMock(return_value=dict(CRITIQUE_WITH_ISSUES))
        revise = AsyncMock(return_value=REVISED_HTML)
        with _flag(False), patcher, \
             patch.object(service, "_review_design_with_deepseek", review), \
             patch.object(service, "_call_glm", revise):
            result = await service._run_premium_design_loop(ORIGINAL_HTML)

        assert result == ORIGINAL_HTML
        assert review.await_count == 0
        assert revise.await_count == 0
        assert mock_post.await_count == 0

    def test_flag_defaults_off(self):
        """The flag ships dark: env default parses to False."""
        assert ai_service_module.os.getenv("PREMIUM_DESIGN_LOOP", "false") \
            .strip().lower() in ("false", "0", "no", "off")


class TestPhotoSlotContract:

    @pytest.mark.asyncio
    async def test_revision_dropping_photo_slots_ships_original(self):
        """A revision that loses the PHOTO_SLOT tokens would break image
        binding downstream — the loop must reject it."""
        svc = AIService()
        svc.deepseek_api_key = "k"
        svc.zai_api_key = "k"
        original = "<!DOCTYPE html><html><img src='PHOTO_SLOT_1'></html>"
        revised_no_slots = "<!DOCTYPE html><html><img src='https://invented.example/x.jpg'></html>"
        review = AsyncMock(return_value=dict(CRITIQUE_WITH_ISSUES))
        revise = AsyncMock(return_value=revised_no_slots)
        with _flag(True), \
             patch.object(svc, "_review_design_with_deepseek", review), \
             patch.object(svc, "_call_glm", revise):
            result = await svc._run_premium_design_loop(original, has_images=True)
        assert result == original

    @pytest.mark.asyncio
    async def test_revision_keeping_photo_slots_accepted(self):
        svc = AIService()
        svc.deepseek_api_key = "k"
        svc.zai_api_key = "k"
        original = "<!DOCTYPE html><html><img src='PHOTO_SLOT_1'></html>"
        revised = "<!DOCTYPE html><html><header></header><img src='PHOTO_SLOT_1'></html>"
        review = AsyncMock(return_value=dict(CRITIQUE_WITH_ISSUES))
        revise = AsyncMock(return_value=revised)
        with _flag(True), \
             patch.object(svc, "_review_design_with_deepseek", review), \
             patch.object(svc, "_call_glm", revise):
            result = await svc._run_premium_design_loop(original, has_images=True)
        assert result == revised


class TestPassFlagInconsistency:

    def test_pass_true_with_violations_normalised_to_fail(self):
        critique = AIService._parse_design_critique(
            '{"pass": true, "violations": ["rule 3: no location section"], "improvements": []}'
        )
        assert critique["pass"] is False

    @pytest.mark.asyncio
    async def test_violations_trigger_revision_despite_pass_true(self, service):
        """A reviewer that claims pass=true while listing violations must
        still get its one revision."""
        review = AsyncMock(return_value={
            "pass": True, "violations": ["rule 3: no location section"], "improvements": [],
        })
        revise = AsyncMock(return_value=REVISED_HTML)
        with _flag(True), \
             patch.object(service, "_review_design_with_deepseek", review), \
             patch.object(service, "_call_glm", revise):
            result = await service._run_premium_design_loop(ORIGINAL_HTML)
        assert result == REVISED_HTML
        assert revise.await_count == 1


class TestGenerationOuterTimeout:
    """The outer wait_for guard around generate_website must not kill a
    healthy premium-loop generation mid-revision (worst case ~510s), while
    normal generations keep the tight 180s budget."""

    def test_default_budget_when_flags_off(self):
        with patch.object(ai_service_module, "USE_GLM_FOR_HTML", False), \
             patch.object(ai_service_module, "PREMIUM_DESIGN_LOOP", False):
            assert ai_service_module.generation_outer_timeout_seconds() == 180.0

    def test_premium_without_glm_keeps_default(self):
        """The loop only runs on the GLM path — premium alone doesn't
        justify a longer budget."""
        with patch.object(ai_service_module, "USE_GLM_FOR_HTML", False), \
             patch.object(ai_service_module, "PREMIUM_DESIGN_LOOP", True):
            assert ai_service_module.generation_outer_timeout_seconds() == 180.0

    def test_glm_without_premium_keeps_default(self):
        with patch.object(ai_service_module, "USE_GLM_FOR_HTML", True), \
             patch.object(ai_service_module, "PREMIUM_DESIGN_LOOP", False):
            assert ai_service_module.generation_outer_timeout_seconds() == 180.0

    def test_premium_glm_budget_covers_worst_case(self):
        with patch.object(ai_service_module, "USE_GLM_FOR_HTML", True), \
             patch.object(ai_service_module, "PREMIUM_DESIGN_LOOP", True):
            budget = ai_service_module.generation_outer_timeout_seconds()
        worst_case = (ai_service_module.AI_GLM_TIMEOUT_SECONDS * 2
                      + ai_service_module.DESIGN_REVIEW_TIMEOUT_SECONDS)
        assert budget >= worst_case
        assert budget >= 180.0
