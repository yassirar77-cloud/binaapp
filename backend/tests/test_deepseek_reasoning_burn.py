"""
Tests for the DeepSeek reasoning-budget guard in _call_deepseek.

Regression context — production job c1c93d8a failed at progress 55% with the
opaque error "Failed to generate website" after burning 252s. The API had
returned:

    DeepSeek ✅ Generated 0 chars (finish_reason=length, completion_tokens=24001)
    DeepSeek output usage: 24001/24000 tokens (100% of cap)

i.e. deepseek-v4-pro is a reasoning model, max_tokens bounds reasoning +
content together, and a long reasoning pass consumed the entire budget leaving
`content` empty. `reasoning_content` was never read, empty content was falsy,
and the caller raised a generic failure.

Covers:
- thinking-disabled request body (the root-cause fix)
- 400-on-`thinking` retry without the field
- reasoning-burn detection and the _last_api_call signals
- salvaging a real HTML document out of reasoning_content
- refusing to salvage reasoning prose that has no document root

All HTTP calls are mocked — no live API usage.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import app.services.ai_service as ai_service_module
from app.services.ai_service import AIService


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_response(content="", reasoning_content=None, finish_reason="stop",
                   completion_tokens=1000, status_code=200):
    """Build a MagicMock mimicking an httpx chat-completion response."""
    message = {"content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = "error body"
    resp.json.return_value = {
        "choices": [{"message": message, "finish_reason": finish_reason}],
        "usage": {"completion_tokens": completion_tokens},
    }
    return resp


def _patch_client(*responses):
    """Patch httpx.AsyncClient so successive post() calls return `responses`."""
    mock_post = AsyncMock(side_effect=list(responses))
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
    svc.deepseek_model = "deepseek-v4-flash"
    svc.deepseek_model_pro = "deepseek-v4-pro"
    return svc


# ── root cause: thinking must be disabled ────────────────────────────────────

class TestThinkingDisabled:

    @pytest.mark.asyncio
    async def test_request_disables_thinking(self, service):
        """The request body MUST carry thinking.type=disabled. Without it the
        deepseek-v4 reasoning models spend the whole max_tokens budget on
        reasoning and return empty content."""
        patcher, mock_post = _patch_client(_mock_response("<html>ok</html>"))
        with patcher:
            out = await service._call_deepseek("build a site")

        body = mock_post.call_args.kwargs["json"]
        assert body["thinking"] == {"type": "disabled"}
        assert out == "<html>ok</html>"

    @pytest.mark.asyncio
    async def test_retries_without_thinking_on_400(self, service):
        """A deployment that rejects the `thinking` field must not turn every
        generation into a hard failure — retry once without it."""
        patcher, mock_post = _patch_client(
            _mock_response(status_code=400),
            _mock_response("<html>recovered</html>"),
        )
        with patcher:
            out = await service._call_deepseek("build a site")

        assert mock_post.call_count == 2
        assert "thinking" not in mock_post.call_args.kwargs["json"]
        assert out == "<html>recovered</html>"

    @pytest.mark.asyncio
    async def test_non_400_error_does_not_retry(self, service):
        """A 500 is not a `thinking` contract problem — one attempt, then None."""
        patcher, mock_post = _patch_client(_mock_response(status_code=500))
        with patcher:
            out = await service._call_deepseek("build a site")

        assert mock_post.call_count == 1
        assert out is None


# ── reasoning burn detection + salvage ───────────────────────────────────────

class TestReasoningBurn:

    @pytest.mark.asyncio
    async def test_salvages_html_document_from_reasoning(self, service):
        """The exact production shape: whole budget on reasoning, content
        empty. A real document in reasoning_content is recovered rather than
        throwing away a multi-minute call."""
        reasoning = "Let me plan the layout.\n<!DOCTYPE html><html>hero</html>"
        patcher, _ = _patch_client(_mock_response(
            content="", reasoning_content=reasoning,
            finish_reason="length", completion_tokens=24001,
        ))
        with patcher:
            out = await service._call_deepseek("build a site")

        assert out == reasoning
        assert service._last_api_call["reasoning_burn"] is True
        assert service._last_api_call["empty_content"] is True
        # finish_reason=length must still mark the result truncated so the
        # salvaged page is flagged for review, not shipped as clean.
        assert service._last_api_call["truncated"] is True

    @pytest.mark.asyncio
    async def test_refuses_to_salvage_reasoning_without_document_root(self, service):
        """Reasoning prose with stray fragments but no <!DOCTYPE/<html must NOT
        be returned — _extract_html would pass the model's deliberation through
        as the merchant's website. Failing is the better outcome."""
        patcher, _ = _patch_client(_mock_response(
            content="",
            reasoning_content="I should use a <div> here and maybe a nav bar.",
            finish_reason="length", completion_tokens=24001,
        ))
        with patcher:
            out = await service._call_deepseek("build a site")

        assert out == ""
        assert service._last_api_call["reasoning_burn"] is True

    @pytest.mark.asyncio
    async def test_salvages_bare_html_tag(self, service):
        """A document opening with <html (no doctype) is still a real page."""
        reasoning = "thinking...\n<html><body>shop</body></html>"
        patcher, _ = _patch_client(_mock_response(
            content="", reasoning_content=reasoning,
            finish_reason="length", completion_tokens=24001,
        ))
        with patcher:
            out = await service._call_deepseek("build a site")

        assert out == reasoning

    @pytest.mark.asyncio
    async def test_no_reasoning_burn_flag_on_healthy_response(self, service):
        """Normal response: no burn flags, content returned untouched."""
        patcher, _ = _patch_client(_mock_response(
            "<html>fine</html>", finish_reason="stop", completion_tokens=900,
        ))
        with patcher:
            out = await service._call_deepseek("build a site")

        assert out == "<html>fine</html>"
        assert service._last_api_call["reasoning_burn"] is False
        assert service._last_api_call["empty_content"] is False
        assert service._last_api_call["truncated"] is False

    @pytest.mark.asyncio
    async def test_content_preferred_over_reasoning(self, service):
        """When the model emits real content, reasoning_content is ignored."""
        patcher, _ = _patch_client(_mock_response(
            content="<html>real</html>",
            reasoning_content="<html>draft</html>",
        ))
        with patcher:
            out = await service._call_deepseek("build a site")

        assert out == "<html>real</html>"
        assert service._last_api_call["reasoning_burn"] is False

    @pytest.mark.asyncio
    async def test_empty_content_without_reasoning_is_not_a_burn(self, service):
        """Empty content and no reasoning_content at all: flagged empty, but
        not a reasoning burn — the cause is different and reported as such."""
        patcher, _ = _patch_client(_mock_response(content="", finish_reason="stop"))
        with patcher:
            out = await service._call_deepseek("build a site")

        assert out == ""
        assert service._last_api_call["empty_content"] is True
        assert service._last_api_call["reasoning_burn"] is False

    @pytest.mark.asyncio
    async def test_missing_api_key_short_circuits(self, service):
        """No key: no HTTP call, and the burn signals stay falsy for callers."""
        service.deepseek_api_key = ""
        out = await service._call_deepseek("build a site")
        assert out is None
        assert not service._last_api_call.get("reasoning_burn")
