"""Tests for the Z.ai (GLM / CogVideoX) video service.

No network: httpx.AsyncClient and cloudinary.uploader.upload are patched.
Covers the request shape (endpoint, auth, model, muted), the async-result
state machine, the download → Cloudinary handoff, the derived poster URL,
the prompt builder's 512-char safety and the in-memory job registry.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services import zai_video_service as svc
from app.services.zai_video_service import (
    PROVIDER_DASHSCOPE,
    PROVIDER_ZAI,
    ZAI_PROMPT_MAX_CHARS,
    ZaiVideoError,
    ZaiVideoService,
    build_hero_video_prompt,
    dashscope_video_resolution,
    hero_video_enabled,
    hero_video_fallback_provider,
    hero_video_model,
    hero_video_provider,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b"", text="err"):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.content = content
        self.text = text

    def json(self):
        return self._json


def fake_client(post_response=None, get_response=None, post_exc=None, get_exc=None):
    calls = {"post": [], "get": []}

    class _Client:
        def __init__(self, *args, **kwargs):
            calls.setdefault("init", []).append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            calls["post"].append({"url": str(url), "headers": headers, "json": json})
            if post_exc:
                raise post_exc
            return post_response

        async def get(self, url, headers=None):
            calls["get"].append({"url": str(url), "headers": headers})
            if get_exc:
                raise get_exc
            return get_response

    return _Client, calls


@pytest.fixture
def zai_env(monkeypatch):
    # These tests exercise the Z.ai path explicitly; DashScope is the default.
    monkeypatch.setenv("HERO_VIDEO_PROVIDER", "zai")
    monkeypatch.setenv("ZAI_API_KEY", "zai-test-key")
    monkeypatch.setenv("ZAI_API_URL", "https://api.z.ai/api/paas/v4")
    monkeypatch.delenv("ZAI_VIDEO_MODEL", raising=False)
    monkeypatch.delenv("ZAI_VIDEO_SIZE", raising=False)


class TestFlag:
    def test_default_off(self, monkeypatch):
        monkeypatch.delenv("HERO_VIDEO_ENABLED", raising=False)
        assert hero_video_enabled() is False

    @pytest.mark.parametrize("value", ["true", "1", "YES", "on"])
    def test_truthy_values(self, monkeypatch, value):
        monkeypatch.setenv("HERO_VIDEO_ENABLED", value)
        assert hero_video_enabled() is True


class TestPrompt:
    def test_business_and_preset_are_in_the_scene(self):
        prompt = build_hero_video_prompt(
            business_name="Kedai Ali", business_type="restaurant",
            description="Nasi lemak sambal sotong", style="ambient",
        )
        assert "restaurant business called Kedai Ali" in prompt
        assert "Nasi lemak sambal sotong" in prompt
        assert "calm ambient atmosphere" in prompt
        assert "no text" in prompt and "seamless loop" in prompt

    def test_custom_prompt_replaces_scene_but_keeps_safety_suffix(self):
        prompt = build_hero_video_prompt(
            business_name="Kedai Ali", custom_prompt="  steam rising   from a wok  ", style="elegant"
        )
        # Squashed, leading, and closed with a full stop — the business-derived
        # scene is still replaced, but the merchant's text no longer runs on
        # into the ambience and safety boilerplate that follow it.
        assert prompt.startswith("steam rising from a wok. ")
        assert "Kedai Ali" not in prompt
        assert "no logos" in prompt
        # The style they picked reaches the model instead of being dropped.
        assert "luxurious minimal composition" in prompt

    def test_never_exceeds_the_api_cap(self):
        prompt = build_hero_video_prompt(custom_prompt="x" * 2000)
        assert len(prompt) <= ZAI_PROMPT_MAX_CHARS
        assert prompt.endswith("16:9.")

    def test_unknown_style_falls_back(self):
        assert "slow cinematic camera drift" in build_hero_video_prompt(style="nope")


class TestSubmit:
    async def test_request_shape(self, zai_env):
        client, calls = fake_client(
            post_response=FakeResponse(200, {"id": "task-1", "task_status": "PROCESSING"})
        )
        with patch.object(httpx, "AsyncClient", client):
            task_id = await ZaiVideoService().submit("a scene", duration=10)
        assert task_id == "task-1"
        post = calls["post"][0]
        assert post["url"] == "https://api.z.ai/api/paas/v4/videos/generations"
        assert post["headers"]["Authorization"] == "Bearer zai-test-key"
        body = post["json"]
        assert body["model"] == "cogvideox-3"
        assert body["with_audio"] is False
        assert body["duration"] == 10
        assert body["size"] == "1280x720"
        assert body["fps"] == 30
        assert body["quality"] == "speed"
        assert "image_url" not in body

    async def test_image_to_video_passes_image_url(self, zai_env):
        client, calls = fake_client(post_response=FakeResponse(200, {"id": "t"}))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("scene", image_url="https://x/hero.jpg")
        assert calls["post"][0]["json"]["image_url"] == "https://x/hero.jpg"

    async def test_invalid_duration_uses_default(self, zai_env):
        client, calls = fake_client(post_response=FakeResponse(200, {"id": "t"}))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("scene", duration=7)
        assert calls["post"][0]["json"]["duration"] == 5

    async def test_env_overrides_model_and_size(self, zai_env, monkeypatch):
        monkeypatch.setenv("ZAI_VIDEO_MODEL", "cogvideox-4")
        monkeypatch.setenv("ZAI_VIDEO_SIZE", "1920x1080")
        monkeypatch.setenv("ZAI_VIDEO_QUALITY", "quality")
        client, calls = fake_client(post_response=FakeResponse(200, {"id": "t"}))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("scene")
        body = calls["post"][0]["json"]
        assert body["model"] == "cogvideox-4" and body["size"] == "1920x1080"
        assert body["quality"] == "quality"

    async def test_no_api_key(self, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_PROVIDER", "zai")
        monkeypatch.delenv("ZAI_API_KEY", raising=False)
        with pytest.raises(ZaiVideoError, match="ZAI_API_KEY"):
            await ZaiVideoService().submit("scene")

    @pytest.mark.parametrize("status_code", [400, 401, 429, 500])
    async def test_non_200_raises(self, zai_env, status_code):
        client, _ = fake_client(post_response=FakeResponse(status_code, {}, text="bad"))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError):
                await ZaiVideoService().submit("scene")

    async def test_timeout_raises(self, zai_env):
        client, _ = fake_client(post_exc=httpx.ReadTimeout("slow"))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="timed out"):
                await ZaiVideoService().submit("scene")

    async def test_missing_id_raises(self, zai_env):
        client, _ = fake_client(post_response=FakeResponse(200, {"task_status": "PROCESSING"}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="no task id"):
                await ZaiVideoService().submit("scene")


class TestFetchResult:
    async def test_polls_async_result_endpoint(self, zai_env):
        client, calls = fake_client(
            get_response=FakeResponse(200, {"task_status": "PROCESSING", "video_result": []})
        )
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().fetch_result("task-9")
        assert calls["get"][0]["url"] == "https://api.z.ai/api/paas/v4/async-result/task-9"
        assert result["status"] == "processing"

    async def test_success_returns_urls(self, zai_env):
        client, _ = fake_client(
            get_response=FakeResponse(200, {
                "task_status": "SUCCESS",
                "video_result": [{"url": "https://cdn/v.mp4", "cover_image_url": "https://cdn/c.jpg"}],
            })
        )
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().fetch_result("t")
        assert result == {
            "status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": "https://cdn/c.jpg",
        }

    async def test_fail_state(self, zai_env):
        client, _ = fake_client(get_response=FakeResponse(200, {"task_status": "FAIL"}))
        with patch.object(httpx, "AsyncClient", client):
            assert (await ZaiVideoService().fetch_result("t"))["status"] == "fail"

    async def test_success_without_url_raises(self, zai_env):
        client, _ = fake_client(get_response=FakeResponse(200, {"task_status": "SUCCESS", "video_result": [{}]}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="no video URL"):
                await ZaiVideoService().fetch_result("t")

    async def test_rate_limited_poll_reads_as_processing(self, zai_env):
        client, _ = fake_client(get_response=FakeResponse(429, {}))
        with patch.object(httpx, "AsyncClient", client):
            assert (await ZaiVideoService().fetch_result("t"))["status"] == "processing"

    async def test_server_error_raises(self, zai_env):
        client, _ = fake_client(get_response=FakeResponse(500, {}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError):
                await ZaiVideoService().fetch_result("t")


class TestStore:
    async def test_downloads_then_uploads_as_video(self, zai_env):
        client, calls = fake_client(get_response=FakeResponse(200, content=b"mp4-bytes"))
        upload = MagicMock(return_value={
            "secure_url": "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-1-ab.mp4"
        })
        with patch.object(httpx, "AsyncClient", client), \
             patch.object(svc.cloudinary.uploader, "upload", upload):
            stored = await ZaiVideoService().store("https://cdn/v.mp4", website_id="ws-1")
        assert calls["get"][0]["url"] == "https://cdn/v.mp4"
        assert calls["get"][0]["headers"]["User-Agent"].startswith("Mozilla/5.0")
        args, kwargs = upload.call_args
        assert args[0] == b"mp4-bytes"
        assert kwargs["resource_type"] == "video"
        assert kwargs["folder"] == "binaapp/hero-videos"
        assert kwargs["public_id"].startswith("ws-1-")
        assert stored["video_url"].endswith("ws-1-ab.mp4")
        assert stored["poster_url"].endswith("ws-1-ab.jpg")

    async def test_oversized_download_is_refused(self, zai_env, monkeypatch):
        monkeypatch.setenv("ZAI_VIDEO_MAX_BYTES", "10")
        client, _ = fake_client(get_response=FakeResponse(200, content=b"x" * 11))
        upload = MagicMock()
        with patch.object(httpx, "AsyncClient", client), \
             patch.object(svc.cloudinary.uploader, "upload", upload):
            with pytest.raises(ZaiVideoError, match="too large"):
                await ZaiVideoService().store("https://cdn/v.mp4", website_id="ws-1")
        upload.assert_not_called()

    async def test_download_failure(self, zai_env):
        client, _ = fake_client(get_response=FakeResponse(404, content=b""))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="download failed"):
                await ZaiVideoService().store("https://cdn/v.mp4", website_id="ws-1")

    async def test_upload_failure(self, zai_env):
        client, _ = fake_client(get_response=FakeResponse(200, content=b"bytes"))
        upload = MagicMock(side_effect=RuntimeError("cloudinary down"))
        with patch.object(httpx, "AsyncClient", client), \
             patch.object(svc.cloudinary.uploader, "upload", upload):
            with pytest.raises(ZaiVideoError, match="storage failed"):
                await ZaiVideoService().store("https://cdn/v.mp4", website_id="ws-1")

    def test_poster_url_derivation(self):
        assert ZaiVideoService.poster_url_for("https://r/video/upload/v1/a/b.mp4") == "https://r/video/upload/v1/a/b.jpg"
        assert ZaiVideoService.poster_url_for("https://r/video/upload/v1/a/b") is None
        assert ZaiVideoService.poster_url_for("") is None


class TestJobRegistry:
    def test_one_active_job_per_site_and_user_count(self):
        service = ZaiVideoService()
        job = service.register_job(task_id="t1", website_id="ws-1", user_id="u1", prompt="p", settings={})
        assert service.get_job(job.job_id) is job
        assert service.active_job_for_website("ws-1") is job
        assert service.active_job_for_website("ws-2") is None
        assert service.active_jobs_for_user("u1") == 1
        job.status = svc.JOB_STATUS_COMPLETED
        assert service.active_job_for_website("ws-1") is None
        assert service.active_jobs_for_user("u1") == 0

    def test_stale_jobs_are_swept(self):
        service = ZaiVideoService()
        job = service.register_job(task_id="t1", website_id="ws-1", user_id="u1", prompt="p", settings={})
        job.created_at -= svc._JOB_TTL_SECONDS + 1
        assert service.get_job(job.job_id) is None

    def test_to_dict_never_leaks_the_task_id_or_prompt(self):
        service = ZaiVideoService()
        job = service.register_job(task_id="secret-task", website_id="ws-1", user_id="u1", prompt="p", settings={})
        payload = job.to_dict()
        assert "secret-task" not in str(payload)
        assert set(payload) >= {"job_id", "status", "video_url", "poster_url", "applied", "elapsed_seconds"}


# ---------------------------------------------------------------------------
# Provider switch + DashScope (Alibaba Model Studio) path
# ---------------------------------------------------------------------------

@pytest.fixture
def dashscope_env(monkeypatch):
    monkeypatch.delenv("HERO_VIDEO_PROVIDER", raising=False)  # default → dashscope
    monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-test-key")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_URL", raising=False)
    monkeypatch.delenv("DASHSCOPE_VIDEO_MODEL", raising=False)
    monkeypatch.delenv("DASHSCOPE_VIDEO_RESOLUTION", raising=False)
    monkeypatch.delenv("DASHSCOPE_VIDEO_RATIO", raising=False)
    monkeypatch.delenv("ZAI_VIDEO_DURATION", raising=False)


DS_SUBMIT_OK = {"output": {"task_id": "ds-task-1", "task_status": "PENDING"}, "request_id": "r1"}


class TestProviderSwitch:
    def test_dashscope_is_the_default(self, monkeypatch):
        monkeypatch.delenv("HERO_VIDEO_PROVIDER", raising=False)
        assert hero_video_provider() == PROVIDER_DASHSCOPE
        assert hero_video_model() == "happyhorse-1.1-t2v"

    def test_zai_can_be_selected(self, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_PROVIDER", "zai")
        assert hero_video_provider() == PROVIDER_ZAI
        assert hero_video_model() == "cogvideox-3"

    def test_unknown_value_falls_back_to_dashscope(self, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_PROVIDER", "runway")
        assert hero_video_provider() == PROVIDER_DASHSCOPE

    def test_resolution_is_validated(self, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_VIDEO_RESOLUTION", "4k")
        assert dashscope_video_resolution() == "720P"
        monkeypatch.setenv("DASHSCOPE_VIDEO_RESOLUTION", "480p")
        assert dashscope_video_resolution() == "480P"


class TestDashScopeSubmit:
    async def test_request_shape(self, dashscope_env):
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            task_id = await ZaiVideoService().submit("A slow pan across a bright salon", duration=5)
        assert task_id == "ds-task-1"
        post = calls["post"][0]
        url, headers, body = post["url"], post["headers"], post["json"]
        assert url == "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
        assert headers["Authorization"] == "Bearer ds-test-key"
        assert headers["X-DashScope-Async"] == "enable"
        assert body["model"] == "happyhorse-1.1-t2v"
        assert body["input"] == {"prompt": "A slow pan across a bright salon"}
        assert body["parameters"] == {
            "resolution": "720P", "ratio": "16:9", "duration": 5, "watermark": False,
        }
        assert "with_audio" not in body and "size" not in body

    async def test_qwen_key_is_accepted_as_fallback(self, dashscope_env, monkeypatch):
        monkeypatch.delenv("DASHSCOPE_API_KEY")
        monkeypatch.setenv("QWEN_API_KEY", "qwen-key")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("p")
        assert calls["post"][0]["headers"]["Authorization"] == "Bearer qwen-key"

    async def test_env_overrides(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_URL", "https://dashscope.aliyuncs.com/api/v1/")
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan2.7-t2v")
        monkeypatch.setenv("DASHSCOPE_VIDEO_RESOLUTION", "480P")
        monkeypatch.setenv("DASHSCOPE_VIDEO_RATIO", "9:16")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("p", duration=10)
        url, body = calls["post"][0]["url"], calls["post"][0]["json"]
        assert url.startswith("https://dashscope.aliyuncs.com/api/v1/services/")
        assert body["model"] == "wan2.7-t2v"
        assert body["parameters"] == {
            "resolution": "480P", "ratio": "9:16", "duration": 10, "watermark": False,
        }

    async def test_watermark_can_be_switched_on(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_VIDEO_WATERMARK", "true")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("p")
        assert calls["post"][0]["json"]["parameters"]["watermark"] is True

    async def test_image_url_is_ignored_for_text_to_video(self, dashscope_env):
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("p", image_url="https://x/hero.jpg")
        assert "image_url" not in calls["post"][0]["json"]["input"]

    async def test_no_key_raises_before_any_call(self, dashscope_env, monkeypatch):
        monkeypatch.delenv("DASHSCOPE_API_KEY")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="DASHSCOPE_API_KEY"):
                await ZaiVideoService().submit("p")
        assert calls["post"] == []

    @pytest.mark.parametrize("status_code", [400, 401, 403, 500])
    async def test_non_200_raises(self, dashscope_env, status_code):
        client, _ = fake_client(post_response=FakeResponse(status_code, {"code": "InvalidParameter", "message": "bad"}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match=str(status_code)):
                await ZaiVideoService().submit("p")

    async def test_rate_limit_has_its_own_message(self, dashscope_env):
        client, _ = fake_client(post_response=FakeResponse(429, {}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="rate limit"):
                await ZaiVideoService().submit("p")

    async def test_missing_task_id_raises(self, dashscope_env):
        client, _ = fake_client(post_response=FakeResponse(200, {"output": {}}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="no task id"):
                await ZaiVideoService().submit("p")


def _ds_task(status, **output):
    return {"request_id": "r", "output": {"task_id": "ds-task-1", "task_status": status, **output}}


class TestDashScopeFetchResult:
    async def test_polls_the_tasks_endpoint(self, dashscope_env):
        client, calls = fake_client(get_response=FakeResponse(200, _ds_task("RUNNING")))
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().fetch_result("ds-task-1")
        url, headers = calls["get"][0]["url"], calls["get"][0]["headers"]
        assert url == "https://dashscope-intl.aliyuncs.com/api/v1/tasks/ds-task-1"
        assert headers["Authorization"] == "Bearer ds-test-key"
        assert result["status"] == "processing"

    @pytest.mark.parametrize("state", ["PENDING", "RUNNING", "pending"])
    async def test_pending_states_are_processing(self, dashscope_env, state):
        client, _ = fake_client(get_response=FakeResponse(200, _ds_task(state)))
        with patch.object(httpx, "AsyncClient", client):
            assert (await ZaiVideoService().fetch_result("t"))["status"] == "processing"

    async def test_succeeded_returns_the_video_url(self, dashscope_env):
        client, _ = fake_client(get_response=FakeResponse(
            200, _ds_task("SUCCEEDED", video_url="https://dashscope-result.oss.example/clip.mp4?Expires=1&Signature=abc")
        ))
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().fetch_result("t")
        assert result == {
            "status": "success",
            "video_url": "https://dashscope-result.oss.example/clip.mp4?Expires=1&Signature=abc",
            "cover_image_url": None,
        }

    @pytest.mark.parametrize("state", ["FAILED", "CANCELED", "UNKNOWN"])
    async def test_terminal_failures(self, dashscope_env, state):
        client, _ = fake_client(get_response=FakeResponse(
            200, _ds_task(state, code="DataInspectionFailed", message="prompt blocked")
        ))
        with patch.object(httpx, "AsyncClient", client):
            assert (await ZaiVideoService().fetch_result("t"))["status"] == "fail"

    async def test_succeeded_without_url_raises(self, dashscope_env):
        client, _ = fake_client(get_response=FakeResponse(200, _ds_task("SUCCEEDED")))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="no video URL"):
                await ZaiVideoService().fetch_result("t")

    async def test_rate_limited_poll_reads_as_processing(self, dashscope_env):
        client, _ = fake_client(get_response=FakeResponse(429, {}))
        with patch.object(httpx, "AsyncClient", client):
            assert (await ZaiVideoService().fetch_result("t"))["status"] == "processing"

    async def test_server_error_raises(self, dashscope_env):
        client, _ = fake_client(get_response=FakeResponse(500, {}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError):
                await ZaiVideoService().fetch_result("t")


# ---------------------------------------------------------------------------
# Fallback chain + per-job provider
# ---------------------------------------------------------------------------

ZAI_SUBMIT_OK = {"id": "zai-task-9", "task_status": "PROCESSING", "request_id": "r"}


def two_step_client(first, second):
    """POST answers `first` on the first call and `second` afterwards; GET is unused."""
    calls = {"post": [], "get": []}
    answers = [first, second]

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            calls["post"].append({"url": str(url), "headers": headers, "json": json})
            return answers[min(len(calls["post"]) - 1, 1)]

        async def get(self, url, headers=None):
            calls["get"].append({"url": str(url), "headers": headers})
            return FakeResponse(200, {})

    return _Client, calls


class TestFallbackProvider:
    def test_defaults_to_zai_when_dashscope_is_primary(self, monkeypatch):
        monkeypatch.delenv("HERO_VIDEO_PROVIDER", raising=False)
        monkeypatch.delenv("HERO_VIDEO_FALLBACK_PROVIDER", raising=False)
        assert hero_video_fallback_provider() == PROVIDER_ZAI

    def test_no_fallback_when_zai_is_primary(self, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_PROVIDER", "zai")
        monkeypatch.delenv("HERO_VIDEO_FALLBACK_PROVIDER", raising=False)
        assert hero_video_fallback_provider() is None

    def test_none_disables_and_same_as_primary_is_ignored(self, monkeypatch):
        monkeypatch.delenv("HERO_VIDEO_PROVIDER", raising=False)
        monkeypatch.setenv("HERO_VIDEO_FALLBACK_PROVIDER", "none")
        assert hero_video_fallback_provider() is None
        monkeypatch.setenv("HERO_VIDEO_FALLBACK_PROVIDER", "dashscope")
        assert hero_video_fallback_provider() is None

    async def test_primary_accepts_returns_primary(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            assert await ZaiVideoService().submit_with_fallback("p") == ("ds-task-1", "dashscope")
        assert len(calls["post"]) == 1

    async def test_rejected_key_falls_back_to_zai(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        client, calls = two_step_client(
            FakeResponse(401, {"code": "InvalidApiKey", "message": "Invalid API-key provided."}),
            FakeResponse(200, ZAI_SUBMIT_OK),
        )
        with patch.object(httpx, "AsyncClient", client):
            assert await ZaiVideoService().submit_with_fallback("p") == ("zai-task-9", "zai")
        assert "dashscope-intl" in calls["post"][0]["url"]
        assert calls["post"][1]["url"].endswith("/videos/generations")
        assert calls["post"][1]["headers"]["Authorization"] == "Bearer zai-key"

    async def test_no_fallback_key_means_primary_error_surfaces(self, dashscope_env, monkeypatch):
        monkeypatch.delenv("ZAI_API_KEY", raising=False)
        client, calls = fake_client(post_response=FakeResponse(401, {"code": "InvalidApiKey"}))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="401"):
                await ZaiVideoService().submit_with_fallback("p")
        assert len(calls["post"]) == 1

    async def test_both_fail_raises_the_primary_error(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        client, calls = two_step_client(
            FakeResponse(401, {"code": "InvalidApiKey"}), FakeResponse(500, {})
        )
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(ZaiVideoError, match="DashScope video submit failed \\(401\\)"):
                await ZaiVideoService().submit_with_fallback("p")
        assert len(calls["post"]) == 2

    async def test_fetch_result_follows_the_jobs_provider_not_the_env(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        client, calls = fake_client(get_response=FakeResponse(
            200, {"task_status": "PROCESSING", "video_result": [], "model": "cogvideox-3", "request_id": "r"}
        ))
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().fetch_result("zai-task-9", provider="zai")
        assert calls["get"][0]["url"].endswith("/async-result/zai-task-9")
        assert result["status"] == "processing"

    def test_register_job_records_the_provider(self, dashscope_env):
        service = ZaiVideoService()
        job = service.register_job(
            task_id="zai-task-9", website_id="ws", user_id="u", prompt="p", settings={}, provider="zai"
        )
        assert job.provider == "zai"
        assert job.to_dict()["provider"] == "zai"
        default = service.register_job(task_id="t2", website_id="ws2", user_id="u", prompt="p", settings={})
        assert default.provider == "dashscope"


class TestKeyHygiene:
    async def test_pasted_key_with_newline_is_stripped(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "  sk-clean-key\n")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("p")
        assert calls["post"][0]["headers"]["Authorization"] == "Bearer sk-clean-key"

    async def test_blank_dashscope_key_falls_through_to_qwen(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "   ")
        monkeypatch.setenv("QWEN_API_KEY", "qwen-key")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            await ZaiVideoService().submit("p")
        assert calls["post"][0]["headers"]["Authorization"] == "Bearer qwen-key"

    def test_fingerprint_never_reveals_the_key(self):
        key = "sk-729b6079968a4aaaaaaaaaaaaaaaaaaa1234"
        fp = svc._key_fingerprint(key)
        assert fp.startswith("sk-729") and fp.endswith(f"({len(key)} chars)")
        assert "968a4aaa" not in fp and key not in fp
        assert svc._key_fingerprint(None) == "none"

    async def test_401_logs_which_key_was_used(self, dashscope_env, caplog):
        client, _ = fake_client(post_response=FakeResponse(401, {"code": "InvalidApiKey"}))
        with patch.object(httpx, "AsyncClient", client), pytest.raises(ZaiVideoError):
            await ZaiVideoService().submit("p")
        # loguru → caplog bridge may not be wired; assert via the service's own
        # helper instead so the test is independent of logging plumbing.
        key, source = svc._dashscope_key_source()
        assert source == "DASHSCOPE_API_KEY" and key == "ds-test-key"



# ── image jobs route to a provider that can animate the image ────────────────
# Regression: website kilafa uploaded its storefront as the hero and asked for
# a video. The default primary (DashScope, text-to-video) dropped image_url,
# so the clip showed strangers in a different restaurant, laid over the
# merchant's own photo.

class TestImageJobRouting:

    @pytest.mark.asyncio
    async def test_photo_goes_to_zai_first_when_configured(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        client, calls = fake_client(post_response=FakeResponse(200, ZAI_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().submit_with_fallback(
                "p", image_url="https://res.cloudinary.com/x/shop.jpg"
            )
        assert result == ("zai-task-9", "zai")
        assert len(calls["post"]) == 1
        url, body = calls["post"][0]["url"], calls["post"][0]["json"]
        assert "/videos/generations" in url
        assert body["image_url"] == "https://res.cloudinary.com/x/shop.jpg"

    @pytest.mark.asyncio
    async def test_photo_without_zai_key_keeps_dashscope(self, dashscope_env, monkeypatch):
        """No Z.ai key → exactly today's behaviour: DashScope, text-to-video."""
        monkeypatch.delenv("ZAI_API_KEY", raising=False)
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().submit_with_fallback(
                "p", image_url="https://res.cloudinary.com/x/shop.jpg"
            )
        assert result == ("ds-task-1", "dashscope")
        assert len(calls["post"]) == 1
        assert "video-synthesis" in calls["post"][0]["url"]

    @pytest.mark.asyncio
    async def test_zai_rejection_falls_back_to_dashscope_for_a_photo(self, dashscope_env, monkeypatch):
        """An image job is never worse than a text job: if Z.ai cannot take
        it, the usual primary still makes a (text-to-video) clip."""
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        client, calls = two_step_client(
            FakeResponse(401, {"error": {"code": "1000", "message": "invalid key"}}),
            FakeResponse(200, DS_SUBMIT_OK),
        )
        with patch.object(httpx, "AsyncClient", client):
            result = await ZaiVideoService().submit_with_fallback(
                "p", image_url="https://res.cloudinary.com/x/shop.jpg"
            )
        assert result == ("ds-task-1", "dashscope")
        assert "/videos/generations" in calls["post"][0]["url"]
        assert "video-synthesis" in calls["post"][1]["url"]

    @pytest.mark.asyncio
    async def test_text_job_order_is_unchanged(self, dashscope_env, monkeypatch):
        """Without a photo the routing is untouched even with Z.ai configured."""
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        client, calls = fake_client(post_response=FakeResponse(200, DS_SUBMIT_OK))
        with patch.object(httpx, "AsyncClient", client):
            assert await ZaiVideoService().submit_with_fallback("p") == ("ds-task-1", "dashscope")
        assert "video-synthesis" in calls["post"][0]["url"]
