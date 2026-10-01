"""AI promo clips for TikTok (Wan 3.0 reference-to-video) — pure rules, the
DashScope request shape, and the admin routes. No network."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services import zai_video_service as svc
from app.services.social import tiktok_ai_video as ai
from app.services.social import tiktok_media
from tests.test_zai_video_service import FakeResponse, fake_client


# --------------------------------------------------------------------------
# pure rules
# --------------------------------------------------------------------------

class TestRules:
    def test_cost_estimate_uses_list_price_and_fx(self, monkeypatch):
        monkeypatch.delenv("WAN_COST_USD_PER_SEC_720P", raising=False)
        monkeypatch.setenv("WAN_USD_TO_MYR", "4.50")
        assert ai.estimate_cost("720P", 10) == {"usd": 1.0, "rm": 4.5}
        assert ai.estimate_cost("1080P", 15) == {"usd": 3.0, "rm": 13.5}

    def test_cost_override_per_resolution(self, monkeypatch):
        monkeypatch.setenv("WAN_COST_USD_PER_SEC_720P", "0.08")
        monkeypatch.setenv("WAN_USD_TO_MYR", "4.00")
        assert ai.estimate_cost("720P", 10) == {"usd": 0.8, "rm": 3.2}

    def test_unknown_resolution_or_duration_fall_back_to_defaults(self):
        assert ai.clean_resolution("4K") == "720P"
        assert ai.clean_resolution("1080p") == "1080P"
        assert ai.clean_duration(7) == 10
        assert ai.clean_duration(15) == 15
        assert ai.clean_duration("x") == 10

    def test_daily_cap(self, monkeypatch):
        monkeypatch.setenv("WAN_DAILY_VIDEO_LIMIT", "3")
        assert ai.daily_limit() == 3
        assert ai.cap_reached(2, 3) is False
        assert ai.cap_reached(3, 3) is True
        monkeypatch.setenv("WAN_DAILY_VIDEO_LIMIT", "nonsense")
        assert ai.daily_limit() == 10
        assert ai.cap_reached(0, 0) is True  # 0 disables

    def test_prompt_names_every_photo_and_fits_the_provider_limit(self):
        p = ai.build_promo_prompt("promo nasi kandar RM12, Khulafa Seksyen 7", 3)
        assert "Image 1, Image 2, Image 3" in p
        assert "promo nasi kandar RM12, Khulafa Seksyen 7." in p
        assert "9:16" in p and "no text" in p
        assert len(p) <= svc.ZAI_PROMPT_MAX_CHARS
        one = ai.build_promo_prompt("", 1)
        assert "Image 1" in one and "Image 2" not in one
        long = ai.build_promo_prompt("x" * 2000, 2)
        assert len(long) <= svc.ZAI_PROMPT_MAX_CHARS and long.endswith(ai._SOCIAL_SUFFIX)

    def test_enabled_requires_dashscope_and_a_wan3_model(self, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-key")
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan3.0-video")
        assert ai.is_enabled() is True
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "happyhorse-1.1-t2v")
        assert ai.is_enabled() is False
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan3.0-video")
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        monkeypatch.delenv("DASHSCOPE_API_KEY_INTL", raising=False)
        assert ai.is_enabled() is False

    def test_public_view_has_no_internal_fields_and_flags_submitted(self):
        v = ai.public_view({"id": "j1", "status": "ready", "video_key": "a" * 32 + ".mp4", "task_id": "t",
                            "estimated_cost_usd": "1.0000", "estimated_cost_rm": "4.40", "created_by": "u"})
        assert v["submitted"] is True and v["video_key"].endswith(".mp4")
        assert v["estimated_cost_rm"] == 4.4
        assert "created_by" not in v
        assert ai.public_view({"id": "j2", "status": "failed"})["submitted"] is False

    def test_media_key_regex_accepts_mp4_only_with_hex_key(self):
        assert tiktok_media.MEDIA_KEY_RE.match("a" * 32 + ".mp4")
        assert tiktok_media.MEDIA_KEY_RE.match("0" * 32 + ".webp")
        assert not tiktok_media.MEDIA_KEY_RE.match("A" * 32 + ".mp4")
        assert not tiktok_media.MEDIA_KEY_RE.match("a" * 32 + ".mov")


# --------------------------------------------------------------------------
# DashScope request shape for reference-to-video
# --------------------------------------------------------------------------

@pytest.fixture
def dashscope_ref_env(monkeypatch):
    monkeypatch.setenv("HERO_VIDEO_PROVIDER", "dashscope")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-key")
    monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan3.0-video")
    monkeypatch.delenv("DASHSCOPE_VIDEO_RESOLUTION", raising=False)


class TestDashScopeReferenceRequest:
    async def test_reference_images_resolution_and_15s(self, dashscope_ref_env):
        client, calls = fake_client(
            post_response=FakeResponse(200, {"output": {"task_id": "t-1", "task_status": "PENDING"}})
        )
        with patch.object(svc.httpx, "AsyncClient", client):
            task = await svc.ZaiVideoService().submit(
                "Promo. Image 1, Image 2.",
                duration=15,
                provider=svc.PROVIDER_DASHSCOPE,
                aspect=svc.ASPECT_SOCIAL,
                reference_image_urls=["https://www.binaapp.my/api/tiktok/media/a.jpg", "https://www.binaapp.my/api/tiktok/media/b.jpg"],
                resolution="720P",
            )
        assert task == "t-1"
        body = calls["post"][0]["json"]
        assert body["model"] == "wan3.0-video"
        assert body["input"]["media"] == [
            {"type": "reference_image", "url": "https://www.binaapp.my/api/tiktok/media/a.jpg"},
            {"type": "reference_image", "url": "https://www.binaapp.my/api/tiktok/media/b.jpg"},
        ]
        assert body["parameters"]["resolution"] == "720P"
        assert body["parameters"]["ratio"] == "9:16"
        assert body["parameters"]["duration"] == 15
        assert body["parameters"]["audio"] is False
        assert calls["post"][0]["headers"]["X-DashScope-Async"] == "enable"

    async def test_hero_path_unchanged_first_frame_and_env_resolution(self, dashscope_ref_env, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_VIDEO_RESOLUTION", "1080P")
        client, calls = fake_client(
            post_response=FakeResponse(200, {"output": {"task_id": "t-2", "task_status": "PENDING"}})
        )
        with patch.object(svc.httpx, "AsyncClient", client):
            await svc.ZaiVideoService().submit(
                "Hero", duration=5, provider=svc.PROVIDER_DASHSCOPE, image_url="https://x/hero.jpg"
            )
        body = calls["post"][0]["json"]
        assert body["input"]["media"] == [{"type": "first_frame", "url": "https://x/hero.jpg"}]
        assert body["parameters"]["resolution"] == "1080P"
        assert body["parameters"]["ratio"] == "adaptive"
        assert body["parameters"]["duration"] == 5

    async def test_duration_outside_the_unified_range_falls_back(self, dashscope_ref_env):
        client, calls = fake_client(
            post_response=FakeResponse(200, {"output": {"task_id": "t-3", "task_status": "PENDING"}})
        )
        with patch.object(svc.httpx, "AsyncClient", client):
            await svc.ZaiVideoService().submit("x", duration=45, provider=svc.PROVIDER_DASHSCOPE)
        assert calls["post"][0]["json"]["parameters"]["duration"] == svc.zai_video_duration()

    async def test_reference_images_refused_on_a_non_wan3_model(self, dashscope_ref_env, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "happyhorse-1.1-t2v")
        with pytest.raises(svc.ZaiVideoError):
            await svc.ZaiVideoService().submit(
                "x", provider=svc.PROVIDER_DASHSCOPE, reference_image_urls=["https://x/a.jpg"]
            )


# --------------------------------------------------------------------------
# start_generation + driver
# --------------------------------------------------------------------------

class TestStartGeneration:
    async def test_submit_refusal_marks_the_row_failed(self, dashscope_ref_env, monkeypatch):
        monkeypatch.setenv("WAN_DAILY_VIDEO_LIMIT", "10")
        rows = {}

        async def insert(table, row, **_):
            rows["row"] = {**row, "id": "job-1"}
            return rows["row"]

        async def update(table, filters, patch_):
            rows["row"].update(patch_)
            return [rows["row"]]

        async def select(table, filters=None, extra=None, select="*"):
            if filters and filters.get("id") == "job-1":
                return [rows["row"]]
            return []

        with patch.object(ai, "db_insert", insert), patch.object(ai, "db_update", update), \
             patch.object(ai, "db_select", select), \
             patch.object(svc.zai_video_service, "submit", AsyncMock(side_effect=svc.ZaiVideoError("rate limit"))):
            row = await ai.start_generation(
                user_id="admin", brief="promo", photo_keys=["a" * 32 + ".jpg"], resolution="720P", duration_sec=10
            )
        assert row["status"] == "failed"
        assert "rate limit" in row["error"]
        assert row["estimated_cost_rm"] > 0
        assert "task_id" not in row  # never submitted → does not count against the cap

    async def test_cap_blocks_before_submit(self, dashscope_ref_env, monkeypatch):
        monkeypatch.setenv("WAN_DAILY_VIDEO_LIMIT", "1")
        with patch.object(ai, "submitted_today", AsyncMock(return_value=1)), \
             patch.object(svc.zai_video_service, "submit", AsyncMock()) as submit:
            with pytest.raises(ai.DailyCapReached):
                await ai.start_generation(user_id="a", brief="", photo_keys=["k"], resolution="720P", duration_sec=10)
            submit.assert_not_called()

    async def test_driver_stores_the_clip_in_the_bucket(self, dashscope_ref_env):
        patches = {}

        async def update(table, filters, patch_):
            patches.update(patch_)
            return [patch_]

        with patch.object(ai, "db_update", update), \
             patch.object(ai, "POLL_INTERVAL_SECONDS", 0), \
             patch.object(svc.zai_video_service, "fetch_result", AsyncMock(side_effect=[
                 {"status": "processing", "raw_status": "RUNNING"},
                 {"status": "success", "video_url": "https://cdn/x.mp4", "raw_status": "SUCCEEDED"},
             ])), \
             patch.object(svc.zai_video_service, "download", AsyncMock(return_value=b"mp4bytes")), \
             patch.object(tiktok_media, "store_bytes", AsyncMock(return_value="f" * 32 + ".mp4")) as store:
            await ai._drive("job-9", "task-9")
        store.assert_awaited_once_with(b"mp4bytes", "mp4")
        assert patches["status"] == "ready"
        assert patches["video_key"].endswith(".mp4")
        assert patches["video_bytes"] == 8

    async def test_driver_marks_provider_failure(self, dashscope_ref_env):
        patches = {}

        async def update(table, filters, patch_):
            patches.update(patch_)
            return [patch_]

        with patch.object(ai, "db_update", update), patch.object(ai, "POLL_INTERVAL_SECONDS", 0), \
             patch.object(svc.zai_video_service, "fetch_result", AsyncMock(return_value={
                 "status": "fail", "raw_status": "FAILED", "message": "content policy"})):
            await ai._drive("job-8", "task-8")
        assert patches["status"] == "failed"
        assert "content policy" in patches["error"]


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

class TestRoutes:
    def test_config_requires_admin(self, client, auth_headers):
        with patch("app.services.subscription_service.subscription_service._is_admin", new=AsyncMock(return_value=False)), \
             patch("app.core.admin.admin_emails", return_value=set()):
            assert client.get("/api/v1/social/tiktok/ai-video/config", headers=auth_headers).status_code == 403

    def test_config_reports_cost_table_and_usage(self, client, auth_headers, test_user_email, monkeypatch):
        monkeypatch.setenv("WAN_DAILY_VIDEO_LIMIT", "10")
        monkeypatch.setenv("WAN_USD_TO_MYR", "4.40")
        monkeypatch.delenv("WAN_COST_USD_PER_SEC_720P", raising=False)
        with patch("app.core.admin.admin_emails", return_value={test_user_email}), \
             patch.object(ai, "submitted_today", AsyncMock(return_value=3)):
            resp = client.get("/api/v1/social/tiktok/ai-video/config", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["resolutions"] == ["720P", "1080P"] and body["default_resolution"] == "720P"
        assert body["durations"] == [10, 15]
        assert body["cost_table"]["720P"]["10"] == {"usd": 1.0, "rm": 4.4}
        assert body["daily"] == {"used": 3, "limit": 10, "remaining": 7}

    def test_create_rejects_too_many_photos(self, client, auth_headers, test_user_email, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "ds")
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan3.0-video")
        files = [("files", (f"p{i}.jpg", b"\xff\xd8\xff", "image/jpeg")) for i in range(4)]
        with patch("app.core.admin.admin_emails", return_value={test_user_email}), \
             patch.object(ai, "submitted_today", AsyncMock(return_value=0)):
            resp = client.post("/api/v1/social/tiktok/ai-video/jobs", headers=auth_headers,
                               data={"brief": "x", "resolution": "720P", "duration_sec": "10"}, files=files)
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "too_many_photos"

    def test_create_refused_at_the_daily_cap_stores_nothing(self, client, auth_headers, test_user_email, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "ds")
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan3.0-video")
        monkeypatch.setenv("WAN_DAILY_VIDEO_LIMIT", "2")
        with patch("app.core.admin.admin_emails", return_value={test_user_email}), \
             patch.object(ai, "submitted_today", AsyncMock(return_value=2)), \
             patch.object(tiktok_media, "store_bytes", AsyncMock()) as store:
            resp = client.post("/api/v1/social/tiktok/ai-video/jobs", headers=auth_headers,
                               data={"brief": "x", "resolution": "720P", "duration_sec": "10"},
                               files=[("files", ("p.jpg", b"\xff\xd8\xff", "image/jpeg"))])
        assert resp.status_code == 429
        assert resp.json()["detail"]["error"] == "daily_limit"
        store.assert_not_called()

    def test_create_unavailable_without_dashscope(self, client, auth_headers, test_user_email, monkeypatch):
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        monkeypatch.delenv("DASHSCOPE_API_KEY_INTL", raising=False)
        with patch("app.core.admin.admin_emails", return_value={test_user_email}):
            resp = client.post("/api/v1/social/tiktok/ai-video/jobs", headers=auth_headers,
                               data={"brief": "x"}, files=[("files", ("p.jpg", b"\xff\xd8\xff", "image/jpeg"))])
        assert resp.status_code == 503

    def test_create_happy_path_returns_202_job(self, client, auth_headers, test_user_email, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "ds")
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan3.0-video")
        job = {"id": "j", "status": "processing", "task_id": "t", "resolution": "1080P", "duration_sec": 15,
               "estimated_cost_usd": 3.0, "estimated_cost_rm": 13.2, "photo_keys": ["k"]}
        with patch("app.core.admin.admin_emails", return_value={test_user_email}), \
             patch.object(ai, "submitted_today", AsyncMock(return_value=0)), \
             patch.object(tiktok_media, "store_bytes", AsyncMock(return_value="k" * 32 + ".jpg")), \
             patch.object(ai, "start_generation", AsyncMock(return_value=job)) as start:
            resp = client.post("/api/v1/social/tiktok/ai-video/jobs", headers=auth_headers,
                               data={"brief": "promo", "resolution": "1080P", "duration_sec": "15"},
                               files=[("files", ("p.jpg", b"\xff\xd8\xff", "image/jpeg"))])
        assert resp.status_code == 202
        assert resp.json()["job"]["status"] == "processing"
        assert resp.json()["job"]["estimated_cost_rm"] == 13.2
        kwargs = start.await_args.kwargs
        assert kwargs["resolution"] == "1080P" and kwargs["duration_sec"] == 15 and kwargs["brief"] == "promo"

    def test_media_serves_mp4(self, client):
        resp_obj = FakeResponse(200, content=b"\x00\x00\x00\x18ftyp")
        with patch.object(tiktok_media, "fetch_object", AsyncMock(return_value=resp_obj)):
            resp = client.get("/api/v1/social/tiktok/media/" + "a" * 32 + ".mp4")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("video/mp4")
        assert client.get("/api/v1/social/tiktok/media/" + "a" * 32 + ".mov").status_code == 404
