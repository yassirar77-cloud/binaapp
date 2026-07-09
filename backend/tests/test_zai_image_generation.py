"""
Tests for the Z.ai image provider and the free-by-default image auto-fill.

Covers:
- _generate_image_zai: request shape (endpoint/auth/model/size), Cloudinary
  handoff, timeout/error handling.
- _generate_image dispatcher: provider selection by IMAGE_PROVIDER, Z.ai →
  Stability fallback, both-fail → None fallthrough.
- _resolve_autofill_image_cap: FREE_AI_IMAGES_PER_SITE default when no quota
  is supplied (None); explicit zero honoured as zero (quota-bypass guard);
  lower positive caller quota wins.
- _autofill_missing_images: zero uploads → hero + per-item generation up to the
  cap; lower caller quota respected; explicit-zero quota generates nothing;
  existing uploads reduce the generated count; prompts carry the real item
  names; total failure leaves image_urls empty so the no-photo branch still
  applies.

No network calls: httpx.AsyncClient and cloudinary.uploader.upload are patched.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.models.schemas import WebsiteGenerationRequest
from app.services import ai_service as ai_service_module
from app.services.ai_service import AIService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b"img-bytes", text="error-body"):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.content = content
        self.text = text

    def json(self):
        return self._json


def make_fake_async_client(post_response=None, get_response=None, post_exc=None, post_responses=None):
    """Build a stand-in for httpx.AsyncClient that records calls.

    post_responses: optional sequence returned call-by-call (the last entry
    repeats), for retry scenarios like 429 → 429 → 200.
    """
    queue = list(post_responses) if post_responses else None

    class FakeAsyncClient:
        init_kwargs = []
        post_calls = []
        get_calls = []

        def __init__(self, **kwargs):
            type(self).init_kwargs.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None, **kwargs):
            type(self).post_calls.append({"url": url, "headers": headers, "json": json})
            if post_exc is not None:
                raise post_exc
            if queue:
                return queue.pop(0) if len(queue) > 1 else queue[0]
            return post_response

        async def get(self, url, **kwargs):
            type(self).get_calls.append(url)
            return get_response

    return FakeAsyncClient


ZAI_OK_RESPONSE = FakeResponse(
    status_code=200,
    json_data={"data": [{"url": "https://zai-cdn.example/generated.png"}]},
)


@pytest.fixture
def zai_env(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    monkeypatch.delenv("ZAI_API_URL", raising=False)
    monkeypatch.delenv("ZAI_BASE_URL", raising=False)
    monkeypatch.delenv("ZAI_IMAGE_MODEL", raising=False)
    monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("FREE_AI_IMAGES_PER_SITE", raising=False)
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)


@pytest.fixture
def cloudinary_upload(monkeypatch):
    mock = MagicMock(return_value={"secure_url": "https://res.cloudinary.com/demo/binaapp/generated.png"})
    monkeypatch.setattr(ai_service_module.cloudinary.uploader, "upload", mock)
    return mock


def make_request(**overrides):
    defaults = dict(
        description="Restoran nasi kandar dengan ayam goreng berempah dan roti canai di Pulau Pinang",
        business_name="Restoran Uji",
        subdomain="restoranuji",
    )
    defaults.update(overrides)
    return WebsiteGenerationRequest(**defaults)


# ---------------------------------------------------------------------------
# Part 1a: _generate_image_zai — request shape + Cloudinary handoff
# ---------------------------------------------------------------------------

class TestZaiImageGeneration:
    async def test_request_shape(self, zai_env, cloudinary_upload, monkeypatch):
        fake_client = make_fake_async_client(
            post_response=ZAI_OK_RESPONSE,
            get_response=FakeResponse(content=b"png-bytes"),
        )
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        url = await service._generate_image_zai("a test prompt")

        assert url == "https://res.cloudinary.com/demo/binaapp/generated.png"
        assert len(fake_client.post_calls) == 1
        call = fake_client.post_calls[0]
        assert call["url"] == "https://api.z.ai/api/paas/v4/images/generations"
        assert call["headers"]["Authorization"] == "Bearer test-zai-key"
        # ZAI_IMAGE_MODEL default. Valid codes: glm-image, cogview-4-250304;
        # plain 'cogview-4' is rejected by the live API (error 1211).
        assert call["json"]["model"] == "glm-image"
        assert call["json"]["prompt"] == "a test prompt"
        assert call["json"]["size"] == "1024x1024"
        # Per-call cap: raised to 120s (glm-image can legitimately take >30s;
        # total build time is protected by the phase budget instead).
        assert fake_client.init_kwargs[0]["timeout"] == ai_service_module.ZAI_IMAGE_TIMEOUT_SECONDS
        assert ai_service_module.ZAI_IMAGE_TIMEOUT_SECONDS == 120.0

    async def test_zai_image_model_env_override(self, zai_env, cloudinary_upload, monkeypatch):
        monkeypatch.setenv("ZAI_IMAGE_MODEL", "cogview-4-250304")
        fake_client = make_fake_async_client(
            post_response=ZAI_OK_RESPONSE,
            get_response=FakeResponse(content=b"png-bytes"),
        )
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        await service._generate_image_zai("a test prompt")

        assert fake_client.post_calls[0]["json"]["model"] == "cogview-4-250304"

    async def test_zai_base_url_env_respected(self, zai_env, cloudinary_upload, monkeypatch):
        monkeypatch.setenv("ZAI_API_URL", "https://custom.z.ai/v4")
        fake_client = make_fake_async_client(
            post_response=ZAI_OK_RESPONSE,
            get_response=FakeResponse(content=b"png-bytes"),
        )
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        await service._generate_image_zai("a test prompt")

        assert fake_client.post_calls[0]["url"] == "https://custom.z.ai/v4/images/generations"

    async def test_cloudinary_handoff_downloads_returned_url(self, zai_env, cloudinary_upload, monkeypatch):
        fake_client = make_fake_async_client(
            post_response=ZAI_OK_RESPONSE,
            get_response=FakeResponse(content=b"downloaded-image-bytes"),
        )
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        url = await service._generate_image_zai("a test prompt")

        # Downloaded the URL from the Z.ai response...
        assert fake_client.get_calls == ["https://zai-cdn.example/generated.png"]
        # ...and pushed the bytes through the existing Cloudinary path.
        cloudinary_upload.assert_called_once_with(b"downloaded-image-bytes", folder="binaapp")
        assert url == "https://res.cloudinary.com/demo/binaapp/generated.png"

    async def test_no_api_key_returns_none(self, zai_env, cloudinary_upload, monkeypatch):
        monkeypatch.delenv("ZAI_API_KEY", raising=False)
        service = AIService()
        assert await service._generate_image_zai("a test prompt") is None
        cloudinary_upload.assert_not_called()

    async def test_http_error_returns_none(self, zai_env, cloudinary_upload, monkeypatch):
        fake_client = make_fake_async_client(post_response=FakeResponse(status_code=500))
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        assert await service._generate_image_zai("a test prompt") is None
        cloudinary_upload.assert_not_called()

    async def test_missing_url_in_response_returns_none(self, zai_env, cloudinary_upload, monkeypatch):
        fake_client = make_fake_async_client(
            post_response=FakeResponse(status_code=200, json_data={"data": []})
        )
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        assert await service._generate_image_zai("a test prompt") is None
        cloudinary_upload.assert_not_called()

    async def test_timeout_returns_none(self, zai_env, cloudinary_upload, monkeypatch):
        fake_client = make_fake_async_client(post_exc=httpx.TimeoutException("timed out"))
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        assert await service._generate_image_zai("a test prompt") is None
        cloudinary_upload.assert_not_called()

    async def test_download_failure_returns_none(self, zai_env, cloudinary_upload, monkeypatch):
        fake_client = make_fake_async_client(
            post_response=ZAI_OK_RESPONSE,
            get_response=FakeResponse(status_code=404),
        )
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        assert await service._generate_image_zai("a test prompt") is None
        cloudinary_upload.assert_not_called()


# ---------------------------------------------------------------------------
# Part 1a-bis: Z.ai rate limiting, serialization, and the phase budget
# ---------------------------------------------------------------------------

RATE_LIMIT_RESPONSE = FakeResponse(
    status_code=429,
    json_data={"code": "1302", "message": "Rate limit reached for requests"},
    text='{"code":"1302","message":"Rate limit reached for requests"}',
)


class TestZaiRateLimitAndSerialization:
    async def test_429_retry_then_success(self, zai_env, cloudinary_upload, monkeypatch):
        monkeypatch.setattr(ai_service_module, "ZAI_IMAGE_RETRY_BACKOFF_SECONDS", (0.0, 0.0))
        fake_client = make_fake_async_client(
            post_responses=[RATE_LIMIT_RESPONSE, ZAI_OK_RESPONSE],
            get_response=FakeResponse(content=b"png-bytes"),
        )
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        url = await service._generate_image_zai("a test prompt")

        assert url == "https://res.cloudinary.com/demo/binaapp/generated.png"
        assert len(fake_client.post_calls) == 2  # 429, then success on retry

    async def test_429_exhausted_returns_none(self, zai_env, cloudinary_upload, monkeypatch):
        monkeypatch.setattr(ai_service_module, "ZAI_IMAGE_RETRY_BACKOFF_SECONDS", (0.0, 0.0))
        fake_client = make_fake_async_client(post_responses=[RATE_LIMIT_RESPONSE])
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        assert await service._generate_image_zai("a test prompt") is None
        assert len(fake_client.post_calls) == 3  # initial + 2 retries
        cloudinary_upload.assert_not_called()

    async def test_429_exhausted_falls_back_to_stability(self, zai_env, cloudinary_upload, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        monkeypatch.setenv("ZAI_IMAGE_REQUEST_DELAY_SECONDS", "0")
        monkeypatch.setattr(ai_service_module, "ZAI_IMAGE_RETRY_BACKOFF_SECONDS", (0.0, 0.0))
        fake_client = make_fake_async_client(post_responses=[RATE_LIMIT_RESPONSE])
        monkeypatch.setattr(ai_service_module.httpx, "AsyncClient", fake_client)

        service = AIService()
        service.stability_api_key = "test-stability-key"
        service._generate_stability_image = AsyncMock(
            return_value="https://res.cloudinary.com/stability.png"
        )
        url = await service._generate_image("a test prompt", food=False)
        assert url == "https://res.cloudinary.com/stability.png"
        service._generate_stability_image.assert_awaited_once()

    async def test_zai_requests_are_serialized(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        monkeypatch.setenv("ZAI_IMAGE_REQUEST_DELAY_SECONDS", "0")
        service = AIService()

        state = {"active": 0, "max_active": 0, "order": []}

        async def fake_zai(prompt):
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
            state["order"].append(prompt)
            await asyncio.sleep(0.01)
            state["active"] -= 1
            return f"https://res.cloudinary.com/{len(state['order'])}.png"

        service._generate_image_zai = fake_zai

        prompts = [f"item {i}" for i in range(5)]
        results = await asyncio.gather(
            *[service._generate_image(p, food=False) for p in prompts]
        )

        assert all(results)
        assert state["max_active"] == 1  # concurrency 1: never overlapping
        assert state["order"] == prompts  # FIFO through the lock

    async def test_stability_path_keeps_parallelism(self, zai_env):
        service = AIService()  # IMAGE_PROVIDER unset → stability

        state = {"active": 0, "max_active": 0}

        async def fake_stability(prompt, food=True):
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
            await asyncio.sleep(0.02)
            state["active"] -= 1
            return "https://res.cloudinary.com/stability.png"

        service._generate_stability_image = fake_stability

        await asyncio.gather(*[service._generate_image(f"p{i}") for i in range(4)])
        assert state["max_active"] > 1  # unchanged: parallel generation

    async def test_request_spacing_delay(self, zai_env, monkeypatch):
        monkeypatch.setenv("ZAI_IMAGE_REQUEST_DELAY_SECONDS", "5")
        service = AIService()

        sleeps = []

        async def fake_sleep(seconds):
            sleeps.append(seconds)

        monkeypatch.setattr(ai_service_module.asyncio, "sleep", fake_sleep)
        service._zai_last_request_at = ai_service_module.time.monotonic()
        await service._pace_zai_image_request()

        assert sleeps and 4.5 < sleeps[0] <= 5.0

    async def test_phase_budget_cutover_to_stability(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        monkeypatch.setenv("ZAI_IMAGE_REQUEST_DELAY_SECONDS", "0")
        service = AIService()
        service.stability_api_key = "test-stability-key"

        async def slow_zai(prompt):
            await asyncio.sleep(0.05)
            return "https://res.cloudinary.com/zai.png"

        service._generate_image_zai = slow_zai
        service._generate_stability_image = AsyncMock(
            return_value="https://res.cloudinary.com/stability.png"
        )

        phase = {"spent": 0.0, "budget": 0.04, "exhausted": False}
        first = await service._generate_image("one", food=False, zai_phase=phase)
        second = await service._generate_image("two", food=False, zai_phase=phase)

        # First image spends the whole budget on Z.ai; the second goes
        # straight to Stability without touching Z.ai again.
        assert first == "https://res.cloudinary.com/zai.png"
        assert second == "https://res.cloudinary.com/stability.png"
        assert phase["exhausted"] is True
        service._generate_stability_image.assert_awaited_once()

    def test_phase_budget_default(self, zai_env):
        service = AIService()
        phase = service._new_zai_image_phase()
        assert phase == {"spent": 0.0, "budget": 300.0, "exhausted": False}

    def test_outer_timeout_extends_for_zai(self, zai_env, monkeypatch):
        assert ai_service_module.generation_outer_timeout_seconds() == 180.0
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        expected = (
            180.0
            + 300.0  # phase budget
            + 2 * ai_service_module.ZAI_IMAGE_TIMEOUT_SECONDS  # in-flight gen + download
            + sum(ai_service_module.ZAI_IMAGE_RETRY_BACKOFF_SECONDS)
        )
        assert ai_service_module.generation_outer_timeout_seconds() == expected


# ---------------------------------------------------------------------------
# Part 1b: _generate_image dispatcher — provider selection + fallback chain
# ---------------------------------------------------------------------------

class TestProviderSelection:
    def _service(self):
        service = AIService()
        service._generate_image_zai = AsyncMock(return_value="https://res.cloudinary.com/zai.png")
        service._generate_stability_image = AsyncMock(return_value="https://res.cloudinary.com/stability.png")
        return service

    async def test_default_provider_is_stability(self, zai_env):
        service = self._service()
        url = await service._generate_image("nasi lemak")
        assert url == "https://res.cloudinary.com/stability.png"
        service._generate_stability_image.assert_awaited_once_with("nasi lemak", food=True)
        service._generate_image_zai.assert_not_awaited()

    async def test_unknown_provider_value_falls_back_to_stability(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "something-else")
        service = self._service()
        url = await service._generate_image("nasi lemak")
        assert url == "https://res.cloudinary.com/stability.png"
        service._generate_image_zai.assert_not_awaited()

    async def test_zai_provider_selected_by_flag(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        service = self._service()
        url = await service._generate_image("nasi lemak")
        assert url == "https://res.cloudinary.com/zai.png"
        service._generate_image_zai.assert_awaited_once()
        service._generate_stability_image.assert_not_awaited()

    async def test_zai_food_prompt_gets_malaysian_mapping(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        service = self._service()
        await service._generate_image("nasi lemak", food=True)
        sent_prompt = service._generate_image_zai.await_args.args[0]
        assert sent_prompt == service._get_malaysian_prompt("nasi lemak")
        assert "nasi lemak" in sent_prompt.lower()

    async def test_zai_nonfood_prompt_used_verbatim(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        service = self._service()
        prompt = "Professional product photo of Keladi Tikus herbal supplement, studio lighting"
        await service._generate_image(prompt, food=False)
        assert service._generate_image_zai.await_args.args[0] == prompt

    async def test_zai_failure_falls_back_to_stability(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        monkeypatch.setenv("STABILITY_API_KEY", "test-stability-key")
        service = self._service()
        service._generate_image_zai = AsyncMock(return_value=None)  # Z.ai fails/times out
        url = await service._generate_image("nasi lemak")
        assert url == "https://res.cloudinary.com/stability.png"
        service._generate_stability_image.assert_awaited_once_with("nasi lemak", food=True)

    async def test_both_providers_fail_returns_none(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        monkeypatch.setenv("STABILITY_API_KEY", "test-stability-key")
        service = self._service()
        service._generate_image_zai = AsyncMock(return_value=None)
        service._generate_stability_image = AsyncMock(return_value=None)
        assert await service._generate_image("nasi lemak") is None

    async def test_zai_failure_without_stability_key_returns_none(self, zai_env, monkeypatch):
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        service = self._service()  # STABILITY_API_KEY not set (zai_env clears it)
        service._generate_image_zai = AsyncMock(return_value=None)
        assert await service._generate_image("nasi lemak") is None
        service._generate_stability_image.assert_not_awaited()

    async def test_availability_check_tracks_provider(self, zai_env, monkeypatch):
        service = AIService()
        # provider=stability, no key → unavailable
        assert service._image_generation_available() is False
        # provider=zai, zai key set → available even without Stability
        monkeypatch.setenv("IMAGE_PROVIDER", "zai")
        assert service._image_generation_available() is True


# ---------------------------------------------------------------------------
# Part 2a: cap resolution
# ---------------------------------------------------------------------------

class TestAutofillCap:
    def test_defaults(self, zai_env):
        service = AIService()
        # No quota supplied (None) → free-by-default budget applies.
        assert service._resolve_autofill_image_cap(None) == 6
        # EXPLICIT zero/negative means the plan system said no — never
        # overridden by the free default (quota-bypass guard).
        assert service._resolve_autofill_image_cap(0) == 0
        assert service._resolve_autofill_image_cap(-3) == 0
        assert service._resolve_autofill_image_cap(2) == 2  # lower caller quota wins
        assert service._resolve_autofill_image_cap(10) == 6  # free budget is the ceiling

    def test_env_override(self, zai_env, monkeypatch):
        monkeypatch.setenv("FREE_AI_IMAGES_PER_SITE", "3")
        service = AIService()
        assert service._resolve_autofill_image_cap(None) == 3
        assert service._resolve_autofill_image_cap(2) == 2
        monkeypatch.setenv("FREE_AI_IMAGES_PER_SITE", "0")
        assert service._resolve_autofill_image_cap(None) == 0

    def test_malformed_env_falls_back(self, zai_env, monkeypatch):
        monkeypatch.setenv("FREE_AI_IMAGES_PER_SITE", "not-a-number")
        service = AIService()
        assert service._resolve_autofill_image_cap(None) == 6


# ---------------------------------------------------------------------------
# Part 2b: per-business-type prompt templates
# ---------------------------------------------------------------------------

class TestAutofillPromptTemplates:
    def test_category_resolution(self, zai_env, monkeypatch):
        service = AIService()
        # Food wins first.
        monkeypatch.setattr(service, "_is_food_business", lambda d: True)
        assert service._autofill_prompt_category("Restoran nasi kandar") == "food"
        monkeypatch.setattr(service, "_is_food_business", lambda d: False)
        # Creative-services keywords (BM + EN).
        assert service._autofill_prompt_category("Jurugambar perkahwinan profesional") == "creative"
        assert service._autofill_prompt_category("Wedding photography and videography") == "creative"
        # Goods-selling / undetected types → retail product shots.
        monkeypatch.setattr(ai_service_module, "detect_business_type", lambda d: "clothing")
        assert service._autofill_prompt_category("Butik pakaian") == "retail"
        monkeypatch.setattr(ai_service_module, "detect_business_type", lambda d: "general")
        assert service._autofill_prompt_category("Kedai runcit") == "retail"
        # Non-creative service types → generic subject-first template.
        monkeypatch.setattr(ai_service_module, "detect_business_type", lambda d: "salon")
        assert service._autofill_prompt_category("Salon rambut wanita") == "generic"

    def test_item_naming_equipment_is_still_the_subject(self, zai_env):
        # Studios/equipment may only appear when the item itself names them —
        # the item name is the subject verbatim.
        service = AIService()
        prompt = service._autofill_item_prompt("retail", "Studio Lighting Kit", "camera shop")
        assert "Professional product photography of Studio Lighting Kit" in prompt


# ---------------------------------------------------------------------------
# Part 2c: auto-fill of missing image slots
# ---------------------------------------------------------------------------

MENU_ITEMS = ["Nasi Kandar", "Ayam Goreng Berempah", "Roti Canai", "Teh Tarik"]


@pytest.fixture
def autofill_service(zai_env, monkeypatch):
    service = AIService()
    monkeypatch.setattr(service, "_is_food_business", lambda description: True)
    service.extract_menu_item_names = AsyncMock(return_value=list(MENU_ITEMS))
    service.extract_product_category_names = AsyncMock(return_value=list(MENU_ITEMS))

    counter = {"n": 0}

    async def _fake_generate(prompt, food=True, zai_phase=None):
        counter["n"] += 1
        return f"https://res.cloudinary.com/gen{counter['n']}.png"

    service._generate_image = AsyncMock(side_effect=_fake_generate)
    return service


class TestAutofillMissingImages:
    async def test_zero_uploads_generates_hero_plus_items(self, autofill_service):
        image_urls = {}
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, None)

        # 1 hero + 4 items, under the default cap of 6
        assert count == 5
        assert autofill_service._generate_image.await_count == 5
        assert image_urls["hero"]
        for i, name in enumerate(MENU_ITEMS, start=1):
            assert image_urls[f"gallery{i}"]
            assert image_urls[f"gallery{i}_name"] == name
        # hero never carries an item name
        assert "hero_name" not in image_urls

    async def test_caller_quota_lower_than_default_is_respected(self, autofill_service):
        image_urls = {}
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, 2)

        assert count == 2
        assert autofill_service._generate_image.await_count == 2
        # Hero wins the budget, then the first item; later slots stay empty.
        assert image_urls["hero"]
        assert image_urls["gallery1"]
        assert "gallery2" not in image_urls

    async def test_explicit_zero_quota_generates_nothing(self, autofill_service):
        # Explicit 0 = plan exhausted / plan forbids AI images. The free
        # default must NOT override that decision.
        image_urls = {}
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, 0)
        assert count == 0
        assert image_urls == {}
        autofill_service._generate_image.assert_not_awaited()
        # No uploads + zero cap → no URLs → downstream has_images decision
        # takes the no-photo typography branch.
        assert autofill_service._ordered_prompt_image_urls(image_urls) == []

    async def test_free_env_cap_applies(self, autofill_service, monkeypatch):
        monkeypatch.setenv("FREE_AI_IMAGES_PER_SITE", "3")
        image_urls = {}
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, None)
        assert count == 3
        assert autofill_service._generate_image.await_count == 3

    async def test_free_cap_zero_disables_autofill(self, autofill_service, monkeypatch):
        monkeypatch.setenv("FREE_AI_IMAGES_PER_SITE", "0")
        image_urls = {}
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, None)
        assert count == 0
        assert image_urls == {}
        autofill_service._generate_image.assert_not_awaited()

    async def test_existing_uploads_reduce_generated_count(self, autofill_service):
        # Merchant uploaded 2 gallery photos, one of them Nasi Kandar.
        image_urls = {
            "gallery1": "https://res.cloudinary.com/upload1.png",
            "gallery1_name": "Nasi Kandar",
            "gallery2": "https://res.cloudinary.com/upload2.png",
        }
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, None)

        # hero + gallery3 + gallery4 — never regenerates the uploaded slots
        assert count == 3
        assert autofill_service._generate_image.await_count == 3
        assert image_urls["gallery1"] == "https://res.cloudinary.com/upload1.png"
        assert image_urls["gallery2"] == "https://res.cloudinary.com/upload2.png"
        assert image_urls["hero"]
        assert image_urls["gallery3"]
        assert image_urls["gallery4"]
        # "Nasi Kandar" is covered by the upload → not generated again
        generated_names = {image_urls["gallery3_name"], image_urls["gallery4_name"]}
        assert "Nasi Kandar" not in generated_names
        assert generated_names <= set(MENU_ITEMS)

    async def test_all_slots_covered_makes_no_calls(self, autofill_service):
        image_urls = {
            "hero": "h",
            "gallery1": "1", "gallery2": "2", "gallery3": "3", "gallery4": "4",
        }
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, None)
        assert count == 0
        autofill_service._generate_image.assert_not_awaited()
        autofill_service.extract_menu_item_names.assert_not_awaited()

    async def test_prompts_contain_real_item_names(self, autofill_service):
        image_urls = {}
        await autofill_service._autofill_missing_images(make_request(), image_urls, None)

        prompts = [c.args[0] for c in autofill_service._generate_image.await_args_list]
        # Slot 0 is the hero banner; slots 1..4 are the real menu items.
        for name, prompt in zip(MENU_ITEMS, prompts[1:]):
            assert name in prompt

    async def test_retail_prompts_put_product_on_clean_background(self, autofill_service, monkeypatch):
        monkeypatch.setattr(autofill_service, "_is_food_business", lambda description: False)
        monkeypatch.setattr(ai_service_module, "detect_business_type", lambda description: "general")
        autofill_service.extract_product_category_names = AsyncMock(
            return_value=["Keladi Tikus Herbal Supplement"]
        )
        image_urls = {}
        request = make_request(
            description="Kedai produk kesihatan menjual Keladi Tikus herbal supplement asli"
        )
        await autofill_service._autofill_missing_images(request, image_urls, None)

        calls = autofill_service._generate_image.await_args_list
        # hero + 1 real product (only items that exist — nothing invented)
        assert len(calls) == 2
        product_prompt = calls[1].args[0]
        # Retail template: the product itself on a clean background
        assert "Professional product photography of Keladi Tikus Herbal Supplement" in product_prompt
        assert "clean background" in product_prompt
        assert calls[1].kwargs.get("food") is False
        assert image_urls["gallery1_name"] == "Keladi Tikus Herbal Supplement"

    async def test_creative_prompts_show_the_work_not_the_premises(self, autofill_service, monkeypatch):
        monkeypatch.setattr(autofill_service, "_is_food_business", lambda description: False)
        autofill_service.extract_product_category_names = AsyncMock(
            return_value=["Wedding Photography", "Portrait Session"]
        )
        image_urls = {}
        request = make_request(
            description="Perkhidmatan jurugambar perkahwinan dan videografi majlis di Kuala Lumpur"
        )
        await autofill_service._autofill_missing_images(request, image_urls, None)

        prompts = [c.args[0] for c in autofill_service._generate_image.await_args_list]
        hero_prompt, item_prompts = prompts[0], prompts[1:]

        # The work itself is the subject, framed artistically (silhouettes/
        # details/venue) rather than close-up faces...
        assert "Wedding Photography" in item_prompts[0]
        assert "Portrait Session" in item_prompts[1]
        for p in item_prompts:
            assert "silhouette" in p.lower()
            assert "venue" in p.lower()
        assert "silhouette" in hero_prompt.lower()
        # ...and never the studio, equipment, or empty premises.
        for p in prompts:
            low = p.lower()
            assert "studio" not in low
            assert "equipment" not in low
            assert "storefront" not in low
            assert "interior" not in low

    async def test_generic_prompts_use_item_name_as_subject(self, autofill_service, monkeypatch):
        monkeypatch.setattr(autofill_service, "_is_food_business", lambda description: False)
        monkeypatch.setattr(ai_service_module, "detect_business_type", lambda description: "services")
        autofill_service.extract_product_category_names = AsyncMock(
            return_value=["Servis Penghawa Dingin"]
        )
        image_urls = {}
        request = make_request(description="Syarikat membaiki dan menyelenggara penghawa dingin")
        await autofill_service._autofill_missing_images(request, image_urls, None)

        calls = autofill_service._generate_image.await_args_list
        item_prompt = calls[1].args[0]
        assert item_prompt.startswith("Professional photography of Servis Penghawa Dingin")
        # Generic hero showcases the work in action — not empty premises.
        hero_prompt = calls[0].args[0]
        assert "work in action" in hero_prompt
        assert "storefront" not in hero_prompt.lower()

    async def test_generation_failure_uses_pool_fallback_without_counting(self, autofill_service, monkeypatch):
        autofill_service._generate_image = AsyncMock(return_value=None)
        monkeypatch.setattr(
            autofill_service, "get_matching_image",
            lambda *args, **kwargs: "https://images.unsplash.com/pool.png",
        )
        image_urls = {}
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, None)

        # Slots are pool-filled so nothing ships blank, but the AI-generated
        # count (usage accounting) stays 0.
        assert count == 0
        assert image_urls["hero"] == "https://images.unsplash.com/pool.png"
        assert image_urls["gallery1"] == "https://images.unsplash.com/pool.png"

    async def test_total_failure_leaves_no_photo_branch_intact(self, autofill_service, monkeypatch):
        autofill_service._generate_image = AsyncMock(return_value=None)

        def _pool_fails(*args, **kwargs):
            raise RuntimeError("pool unavailable")

        monkeypatch.setattr(autofill_service, "get_matching_image", _pool_fails)
        image_urls = {}
        count = await autofill_service._autofill_missing_images(make_request(), image_urls, None)

        assert count == 0
        assert image_urls == {}
        # Downstream has_images decision: no URLs → no-photo typography branch.
        assert autofill_service._ordered_prompt_image_urls(image_urls) == []
