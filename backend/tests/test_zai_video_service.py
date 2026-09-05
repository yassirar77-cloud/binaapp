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
    ZAI_PROMPT_MAX_CHARS,
    ZaiVideoError,
    ZaiVideoService,
    build_hero_video_prompt,
    hero_video_enabled,
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
        assert prompt.startswith("steam rising from a wok ")
        assert "Kedai Ali" not in prompt
        assert "no logos" in prompt

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
