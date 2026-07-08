"""
Tests for the GLM (Z.ai) primary HTML generation path.

Covers:
- _call_glm(): thinking-disabled request body, preamble stripping,
  empty-content failure, truncation flag tracking, missing-key short-circuit
- _replace_photo_slots(): slot→URL binding, out-of-range slots, no-URL case
- Fallback chain: GLM failure falls through to DeepSeek; GLM success skips it

All HTTP calls are mocked — no live API usage.
"""

import asyncio
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import app.services.ai_service as ai_service_module
from app.services.ai_service import AIService


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_httpx_response(content: str, finish_reason: str = "stop",
                         completion_tokens: int = 1000, status_code: int = 200):
    """Build a MagicMock mimicking httpx.Response for a chat completion."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = "error body"
    resp.json.return_value = {
        "choices": [{
            "message": {"content": content},
            "finish_reason": finish_reason,
        }],
        "usage": {"completion_tokens": completion_tokens},
    }
    return resp


def _patch_async_client(mock_response):
    """Patch httpx.AsyncClient so client.post() returns mock_response.
    Returns the mock post function for request-body assertions."""
    mock_post = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.post = mock_post
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    return patch.object(ai_service_module.httpx, "AsyncClient",
                        return_value=mock_ctx), mock_post


@pytest.fixture
def glm_service():
    service = AIService()
    service.zai_api_key = "test-zai-key"
    service.zai_base_url = "https://api.z.ai/api/paas/v4"
    service.zai_model = "glm-5.2"
    return service


# ── _call_glm ────────────────────────────────────────────────────────────────

class TestCallGlm:

    @pytest.mark.asyncio
    async def test_request_disables_thinking(self, glm_service):
        """The request body MUST carry thinking.type=disabled — without it
        glm-5.2 burns the whole output budget on reasoning."""
        patcher, mock_post = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            await glm_service._call_glm("make a website")

        body = mock_post.call_args.kwargs["json"]
        assert body["thinking"] == {"type": "disabled"}
        assert body["model"] == "glm-5.2"
        assert body["max_tokens"] == ai_service_module.AI_GLM_MAX_TOKENS
        # Posted to the Z.ai chat-completions endpoint with the bearer key
        url = mock_post.call_args.args[0]
        assert url == "https://api.z.ai/api/paas/v4/chat/completions"
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-zai-key"

    @pytest.mark.asyncio
    async def test_system_prompt_carries_photo_slot_contract(self, glm_service):
        patcher, mock_post = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            await glm_service._call_glm("make a website")

        system_msg = mock_post.call_args.kwargs["json"]["messages"][0]
        assert system_msg["role"] == "system"
        assert "PHOTO_SLOT_1" in system_msg["content"]
        assert "Output ONLY HTML" in system_msg["content"]
        assert "RM" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_system_prompt_requires_core_sections(self, glm_service):
        """The required-sections clause: minimum section set, order CTA last,
        design freedom otherwise."""
        patcher, mock_post = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            await glm_service._call_glm("make a website")

        content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
        assert "Include at minimum these sections" in content
        for section in ("hero", "menu highlights", "about", "location", "order CTA"):
            assert section in content
        assert "Always end the page with the order CTA" in content
        assert "never omit the required sections" in content
        # Design freedom stays explicit alongside the hard requirements
        assert "may add tasteful extra sections" in content

    @pytest.mark.asyncio
    async def test_has_images_true_uses_photo_slot_contract(self, glm_service):
        """Explicit has_images=True → PHOTO_SLOT contract, no no-photo clause."""
        patcher, mock_post = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            await glm_service._call_glm("make a website", has_images=True)

        content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
        assert "PHOTO_SLOT_1" in content
        assert "No photographs are available" not in content

    @pytest.mark.asyncio
    async def test_has_images_false_uses_no_photo_mode(self, glm_service):
        """has_images=False → no-photo design instruction, and the request
        body carries NO PHOTO_SLOT mention anywhere."""
        patcher, mock_post = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            await glm_service._call_glm("make a website", has_images=False)

        body = mock_post.call_args.kwargs["json"]
        content = body["messages"][0]["content"]
        assert "No photographs are available" in content
        assert "typography-led" in content
        assert "Do NOT use any <img> tags" in content
        # The literal token name must never reach the model in this mode —
        # checked across the ENTIRE request body, not just the system message.
        assert "PHOTO_SLOT" not in json.dumps(body)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("has_images", [True, False])
    async def test_both_image_modes_keep_voice_and_sections(self, glm_service, has_images):
        """Malay/Manglish voice, RM pricing, and required-sections clauses are
        identical in both image modes."""
        patcher, mock_post = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            await glm_service._call_glm("make a website", has_images=has_images)

        content = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
        assert "Malay/Manglish" in content
        assert "Prices in RM" in content
        assert "Include at minimum these sections" in content
        assert "Always end the page with the order CTA" in content
        assert "may add tasteful extra sections" in content
        assert "Output ONLY HTML" in content

    @pytest.mark.asyncio
    async def test_strips_preamble_before_first_angle_bracket(self, glm_service):
        raw = "Sure! Here is your website:\n\n<!DOCTYPE html><html><body>hi</body></html>"
        patcher, _ = _patch_async_client(_mock_httpx_response(raw))
        with patcher:
            result = await glm_service._call_glm("make a website")

        assert result is not None
        assert result.startswith("<!DOCTYPE html>")

    @pytest.mark.asyncio
    async def test_empty_content_returns_none(self, glm_service):
        patcher, _ = _patch_async_client(_mock_httpx_response("   \n  "))
        with patcher:
            result = await glm_service._call_glm("make a website")
        assert result is None

    @pytest.mark.asyncio
    async def test_truncated_finish_reason_sets_flag(self, glm_service):
        patcher, _ = _patch_async_client(
            _mock_httpx_response("<html><body>partial", finish_reason="length")
        )
        with patcher:
            result = await glm_service._call_glm("make a website")

        assert result is not None  # content returned; caller decides to discard
        assert glm_service._last_api_call == {
            "provider": "glm",
            "finish_reason": "length",
            "truncated": True,
        }

    @pytest.mark.asyncio
    async def test_clean_stop_leaves_truncated_false(self, glm_service):
        patcher, _ = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            await glm_service._call_glm("make a website")
        assert glm_service._last_api_call["truncated"] is False
        assert glm_service._last_api_call["provider"] == "glm"

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_none_without_http(self, glm_service):
        glm_service.zai_api_key = None
        patcher, mock_post = _patch_async_client(_mock_httpx_response("<html></html>"))
        with patcher:
            result = await glm_service._call_glm("make a website")
        assert result is None
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self, glm_service):
        patcher, _ = _patch_async_client(_mock_httpx_response("", status_code=429))
        with patcher:
            result = await glm_service._call_glm("make a website")
        assert result is None


# ── _replace_photo_slots ─────────────────────────────────────────────────────

class TestReplacePhotoSlots:

    def test_binds_slots_in_order(self, glm_service):
        html = (
            '<img src="PHOTO_SLOT_1"><img src=\'PHOTO_SLOT_2\'>'
            '<img src="PHOTO_SLOT_3">'
        )
        urls = ["https://cdn/hero.jpg", "https://cdn/g1.jpg", "https://cdn/g2.jpg"]
        out = glm_service._replace_photo_slots(html, urls)
        assert 'src="https://cdn/hero.jpg"' in out
        assert "src='https://cdn/g1.jpg'" in out
        assert 'src="https://cdn/g2.jpg"' in out
        assert "PHOTO_SLOT" not in out

    def test_out_of_range_slot_reuses_last_url(self, glm_service):
        html = '<img src="PHOTO_SLOT_9">'
        out = glm_service._replace_photo_slots(html, ["https://cdn/a.jpg", "https://cdn/b.jpg"])
        assert 'src="https://cdn/b.jpg"' in out

    def test_no_urls_empties_src_for_safety_net(self, glm_service):
        """With no real URLs, slots become src='' so _fix_broken_image_urls
        (the existing final safety net) fills them with fallbacks."""
        html = '<img src="PHOTO_SLOT_1" alt="x">'
        out = glm_service._replace_photo_slots(html, [])
        assert 'src=""' in out
        assert "PHOTO_SLOT" not in out

    def test_bare_token_in_css_url_is_bound(self, glm_service):
        html = "<div style=\"background-image:url(PHOTO_SLOT_1)\"></div>"
        out = glm_service._replace_photo_slots(html, ["https://cdn/hero.jpg"])
        assert "url(https://cdn/hero.jpg)" in out

    def test_noop_when_no_tokens(self, glm_service):
        html = '<img src="https://cdn/real.jpg">'
        assert glm_service._replace_photo_slots(html, ["https://cdn/x.jpg"]) == html

    def test_ordered_prompt_image_urls_hero_first(self, glm_service):
        image_urls = {
            "gallery2": "https://cdn/g2.jpg",
            "hero": "https://cdn/hero.jpg",
            "gallery1": "https://cdn/g1.jpg",
            "gallery1_name": "Nasi Lemak",  # name keys must be ignored
        }
        assert glm_service._ordered_prompt_image_urls(image_urls) == [
            "https://cdn/hero.jpg", "https://cdn/g1.jpg", "https://cdn/g2.jpg",
        ]


# ── fallback chain (generate_website) ────────────────────────────────────────

VALID_HTML = (
    "<!DOCTYPE html><html><head><title>t</title></head>"
    "<body><h1>Kedai Test</h1><p>" + ("x" * 200) + "</p></body></html>"
)


def _make_request():
    from app.models.schemas import WebsiteGenerationRequest
    return WebsiteGenerationRequest(
        business_name="Kedai Test",
        description="Kedai makan mamak di KL",
        whatsapp_number="0123456789",
        subdomain="kedai-test",
    )


def _neutralize_post_processing(service):
    """Stub the deterministic post-HTML steps so chain tests stay fast and
    assert only the provider-ordering behaviour."""
    service._validate_generated_html = MagicMock(return_value=[])
    service._improve_with_qwen = AsyncMock(side_effect=lambda html, desc: html)
    service._fix_placeholders = MagicMock(side_effect=lambda html, *a, **k: html)
    service._fix_menu_item_images = MagicMock(side_effect=lambda html, *a, **k: html)
    service._generate_ai_food_images = AsyncMock(side_effect=lambda html, **k: (html, 0))
    service._fix_broken_image_urls = MagicMock(side_effect=lambda html, *a, **k: html)


class TestGlmFallbackChain:

    @pytest.mark.asyncio
    async def test_glm_failure_falls_back_to_deepseek(self, glm_service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", True)
        glm_service._call_glm = AsyncMock(return_value=None)
        glm_service._call_deepseek = AsyncMock(return_value=VALID_HTML)
        _neutralize_post_processing(glm_service)

        result = await glm_service.generate_website(_make_request(), image_choice="none")

        glm_service._call_glm.assert_awaited_once()
        glm_service._call_deepseek.assert_awaited()  # fallback fired
        assert "<h1>Kedai Test</h1>" in result.html_content

    @pytest.mark.asyncio
    async def test_glm_success_skips_deepseek(self, glm_service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", True)
        glm_service._call_glm = AsyncMock(return_value=VALID_HTML)
        glm_service._call_deepseek = AsyncMock(return_value="<html>deepseek</html>")
        _neutralize_post_processing(glm_service)

        result = await glm_service.generate_website(_make_request(), image_choice="none")

        glm_service._call_glm.assert_awaited_once()
        glm_service._call_deepseek.assert_not_awaited()
        assert "<h1>Kedai Test</h1>" in result.html_content

    @pytest.mark.asyncio
    async def test_flag_off_never_touches_glm(self, glm_service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
        glm_service._call_glm = AsyncMock(return_value=VALID_HTML)
        glm_service._call_deepseek = AsyncMock(return_value=VALID_HTML)
        _neutralize_post_processing(glm_service)

        await glm_service.generate_website(_make_request(), image_choice="none")

        glm_service._call_glm.assert_not_awaited()
        glm_service._call_deepseek.assert_awaited()

    @pytest.mark.asyncio
    async def test_glm_wait_for_uses_tight_glm_timeout(self, glm_service, monkeypatch):
        """The GLM primary call must be bounded by AI_GLM_TIMEOUT_SECONDS,
        not the loose 300s AI_PRIMARY_TIMEOUT_SECONDS — a hung Z.ai must not
        double total latency before the DeepSeek fallback runs."""
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", True)
        glm_service._call_glm = AsyncMock(return_value=VALID_HTML)
        glm_service._call_deepseek = AsyncMock(return_value=VALID_HTML)
        _neutralize_post_processing(glm_service)

        recorded_timeouts = []
        real_wait_for = asyncio.wait_for

        async def _recording_wait_for(coro, timeout=None):
            recorded_timeouts.append(timeout)
            return await real_wait_for(coro, timeout=timeout)

        monkeypatch.setattr(ai_service_module.asyncio, "wait_for", _recording_wait_for)

        await glm_service.generate_website(_make_request(), image_choice="none")

        # The first wait_for in the pipeline wraps the GLM primary call.
        assert recorded_timeouts[0] == ai_service_module.AI_GLM_TIMEOUT_SECONDS
        assert recorded_timeouts[0] < ai_service_module.AI_PRIMARY_TIMEOUT_SECONDS

    @pytest.mark.asyncio
    async def test_truncated_glm_output_is_discarded(self, glm_service, monkeypatch):
        """GLM returns content but hit its output cap → discard, use DeepSeek."""
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", True)

        async def _truncated_glm(prompt, *a, **k):
            glm_service._last_api_call = {
                "provider": "glm", "finish_reason": "length", "truncated": True,
            }
            return "<html><body>partial"

        glm_service._call_glm = AsyncMock(side_effect=_truncated_glm)

        async def _clean_deepseek(prompt, *a, **k):
            glm_service._last_api_call = {
                "provider": "deepseek", "finish_reason": "stop", "truncated": False,
            }
            return VALID_HTML

        glm_service._call_deepseek = AsyncMock(side_effect=_clean_deepseek)
        _neutralize_post_processing(glm_service)

        result = await glm_service.generate_website(_make_request(), image_choice="none")

        glm_service._call_deepseek.assert_awaited()
        assert "<h1>Kedai Test</h1>" in result.html_content
        assert result.was_truncated is False
