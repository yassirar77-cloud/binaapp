"""Mascot Video — pure rules, the DashScope video-edit request shape, the
job driver and the routes. No network."""

import struct
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import mascot_videos as ep
from app.core.security import get_current_user
from app.services import image_moderation_service as moderation
from app.services import mascot_video as mv
from app.services import zai_video_service as svc
from tests.test_zai_video_service import FakeResponse

MERCHANT = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def _box(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(body), kind) + body


def make_mp4(seconds: float, timescale: int = 1000, version: int = 0) -> bytes:
    """The smallest thing with a readable moov/mvhd."""
    duration = int(seconds * timescale)
    if version == 1:
        mvhd = bytes([1, 0, 0, 0]) + bytes(16) + struct.pack(">IQ", timescale, duration)
    else:
        mvhd = bytes(4) + bytes(8) + struct.pack(">II", timescale, duration)
    return _box(b"ftyp", b"isom" + bytes(4)) + _box(b"mdat", bytes(32)) + _box(b"moov", _box(b"mvhd", mvhd + bytes(80)))


# --------------------------------------------------------------------------
# pure rules
# --------------------------------------------------------------------------

class TestRules:
    def test_flag_is_off_by_default(self, monkeypatch):
        monkeypatch.delenv("MASCOT_VIDEO_ENABLED", raising=False)
        assert mv.mascot_video_enabled() is False
        monkeypatch.setenv("MASCOT_VIDEO_ENABLED", "true")
        assert mv.mascot_video_enabled() is True

    def test_duration_is_read_from_mvhd(self):
        assert mv.mp4_duration_seconds(make_mp4(7.5)) == 7.5
        assert mv.mp4_duration_seconds(make_mp4(9, timescale=600, version=1)) == 9
        assert mv.mp4_duration_seconds(b"not a video at all") is None
        assert mv.mp4_duration_seconds(b"") is None

    def test_clip_limits(self, monkeypatch):
        monkeypatch.delenv("MASCOT_VIDEO_MAX_MB", raising=False)
        assert mv.validate_clip(make_mp4(10.2), "video/mp4") == {"ext": "mp4", "seconds": 10.2}
        assert mv.validate_clip(make_mp4(5), "video/quicktime")["ext"] == "mov"
        for data, mime, code in [
            (make_mp4(11), "video/mp4", "clip_too_long"),
            (make_mp4(1), "video/mp4", "clip_too_short"),
            (make_mp4(5), "video/webm", "unsupported_clip"),
            (b"junk" * 10, "video/mp4", "unreadable_clip"),
            (b"", "video/mp4", "empty_clip"),
        ]:
            with pytest.raises(mv.ClipRejected) as exc:
                mv.validate_clip(data, mime)
            assert exc.value.code == code

    def test_clip_size_limit(self, monkeypatch):
        monkeypatch.setenv("MASCOT_VIDEO_MAX_MB", "1")
        with pytest.raises(mv.ClipRejected) as exc:
            mv.validate_clip(make_mp4(5) + bytes(1024 * 1024), "video/mp4")
        assert exc.value.code == "clip_too_large"
        monkeypatch.setenv("MASCOT_VIDEO_MAX_MB", "5000")
        assert mv.max_clip_bytes() == 100 * 1024 * 1024  # the provider's own ceiling

    def test_mascot_limits(self):
        assert mv.validate_mascot(b"x", "image/png") == "png"
        with pytest.raises(mv.ClipRejected):
            mv.validate_mascot(b"x", "image/gif")
        with pytest.raises(mv.ClipRejected):
            mv.validate_mascot(bytes(mv.MASCOT_MAX_BYTES + 1), "image/png")

    def test_cost_counts_input_and_output_seconds(self, monkeypatch):
        monkeypatch.delenv("WAN_COST_USD_PER_SEC_720P", raising=False)
        assert mv.estimate_cost_usd(10, "720P") == 2.0
        assert mv.estimate_cost_usd(5.2, "1080P") == 2.08

    def test_daily_cap(self, monkeypatch):
        monkeypatch.delenv("MASCOT_VIDEO_DAILY_LIMIT", raising=False)
        assert mv.daily_limit() == 3
        monkeypatch.setenv("MASCOT_VIDEO_DAILY_LIMIT", "nonsense")
        assert mv.daily_limit() == 3
        assert mv.cap_reached(2, 3) is False
        assert mv.cap_reached(3, 3) is True
        assert mv.cap_reached(0, 0) is True  # 0 disables

    def test_prompt_keeps_the_real_scene_and_bounds_the_merchant_text(self):
        prompt = mv.build_edit_prompt("  menari  sambil pegang teh tarik ")
        assert prompt.startswith("Edit Video 1: add the cartoon mascot character from Image 1")
        assert "What the mascot does: menari sambil pegang teh tarik." in prompt
        assert "Keep everything else in Video 1 unchanged" in prompt
        assert mv.DEFAULT_ACTION in mv.build_edit_prompt("")
        assert len(mv.build_edit_prompt("x" * 5000)) < 1200

    def test_public_view_labels_output_as_ai_and_hides_the_ledger(self):
        view = mv.public_view({"id": "1", "status": "ready", "cost": 2.08, "task_id": "t", "merchant_id": MERCHANT})
        assert view["ai_generated"] is True
        assert not {"cost", "task_id", "merchant_id", "clip_key"} & set(view)


# --------------------------------------------------------------------------
# DashScope request shape
# --------------------------------------------------------------------------

def recording_client(responses):
    """An httpx.AsyncClient stand-in that replays ``responses`` in order."""
    calls = []
    queue = list(responses)

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def _next(self, method, url, **kwargs):
            calls.append({"method": method, "url": str(url), **kwargs})
            return queue.pop(0)

        async def get(self, url, **kwargs):
            return await self._next("GET", url, **kwargs)

        async def post(self, url, **kwargs):
            return await self._next("POST", url, **kwargs)

    return _Client, calls


@pytest.fixture
def dashscope_env(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-key")
    monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "wan3.0-video")
    monkeypatch.delenv("DASHSCOPE_API_URL", raising=False)


class TestVideoEditRequest:
    async def test_submit_sends_reference_video_and_image(self, dashscope_env):
        client, calls = recording_client([FakeResponse(200, {"output": {"task_id": "task-1"}})])
        with patch.object(svc.httpx, "AsyncClient", client):
            task_id = await svc.zai_video_service.submit_video_edit(
                "p" * 900, video_url="oss://bucket/clip.mp4",
                reference_image_urls=["data:image/png;base64,AAAA"], resolution="720P", watermark=True,
            )
        assert task_id == "task-1"
        call = calls[0]
        assert call["url"].endswith("/services/aigc/video-generation/video-synthesis")
        assert call["headers"]["X-DashScope-Async"] == "enable"
        assert call["headers"]["X-DashScope-OssResourceResolve"] == "enable"
        body = call["json"]
        assert body["model"] == "wan3.0-video"
        assert body["input"]["media"] == [
            {"type": "reference_image", "url": "data:image/png;base64,AAAA"},
            {"type": "reference_video", "url": "oss://bucket/clip.mp4"},
        ]
        assert len(body["input"]["prompt"]) == 900  # an edit prompt is not cut to 512
        assert body["parameters"] == {
            "resolution": "720P", "ratio": "adaptive", "duration": -1, "audio": False, "watermark": True,
        }

    async def test_submit_refuses_a_model_that_cannot_edit(self, dashscope_env, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_VIDEO_MODEL", "happyhorse-1.1-t2v")
        with pytest.raises(svc.ZaiVideoError):
            await svc.zai_video_service.submit_video_edit("p", video_url="https://x/clip.mp4")

    async def test_temp_upload_returns_an_oss_url(self, dashscope_env):
        policy = {"data": {
            "upload_dir": "dashscope-instant/abc", "upload_host": "https://oss.example.com",
            "oss_access_key_id": "id", "signature": "sig", "policy": "pol",
            "x_oss_object_acl": "private", "x_oss_forbid_overwrite": "true",
        }}
        client, calls = recording_client([FakeResponse(200, policy), FakeResponse(200)])
        with patch.object(svc.httpx, "AsyncClient", client):
            url = await svc.zai_video_service.upload_temp_file(b"clip", "c.mp4", model="wan3.0-video")
        assert url == "oss://dashscope-instant/abc/c.mp4"
        assert calls[0]["params"] == {"action": "getPolicy", "model": "wan3.0-video"}
        assert calls[1]["url"] == "https://oss.example.com"
        assert calls[1]["data"]["key"] == "dashscope-instant/abc/c.mp4"

    async def test_temp_upload_failure_is_a_video_error(self, dashscope_env):
        client, _ = recording_client([FakeResponse(403)])
        with patch.object(svc.httpx, "AsyncClient", client):
            with pytest.raises(svc.ZaiVideoError):
                await svc.zai_video_service.upload_temp_file(b"clip", "c.mp4", model="wan3.0-video")


# --------------------------------------------------------------------------
# video moderation fails closed
# --------------------------------------------------------------------------

class TestVideoModeration:
    async def test_no_key_is_not_allowed(self, monkeypatch):
        monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
        monkeypatch.delenv("QWEN_API_KEY", raising=False)
        verdict = await moderation.check_video_safety("oss://x/clip.mp4")
        assert verdict["is_safe"] is False and verdict["unavailable"] is True

    async def test_api_error_is_not_allowed(self, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-key")
        client, _ = recording_client([FakeResponse(404)])
        with patch.object(moderation.httpx, "AsyncClient", client):
            verdict = await moderation.check_video_safety("oss://x/clip.mp4")
        assert verdict["is_safe"] is False and verdict["unavailable"] is True

    async def test_verdict_is_parsed_and_the_clip_is_sent_as_video(self, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-key")
        monkeypatch.delenv("QWEN_VL_VIDEO_MODEL", raising=False)
        text = '{"is_safe": false, "reason": "x", "confidence": 90, "detected_categories": ["violence"]}'
        body = {"output": {"choices": [{"message": {"content": [{"text": text}]}}]}}
        client, calls = recording_client([FakeResponse(200, body)])
        with patch.object(moderation.httpx, "AsyncClient", client):
            verdict = await moderation.check_video_safety("oss://x/clip.mp4")
        assert verdict["is_safe"] is False and not verdict.get("unavailable")
        assert verdict["detected_categories"] == ["violence"]
        sent = calls[0]
        assert sent["json"]["model"] == "qwen3-vl-plus"
        assert sent["json"]["input"]["messages"][0]["content"][0] == {"video": "oss://x/clip.mp4"}
        assert sent["headers"]["X-DashScope-OssResourceResolve"] == "enable"


# --------------------------------------------------------------------------
# the job driver, on an in-memory table and bucket
# --------------------------------------------------------------------------

@pytest.fixture
def store(monkeypatch, dashscope_env):
    rows, objects = {}, {}

    async def db_insert(table, row, **_):
        row = {**row, "id": f"00000000-0000-4000-8000-{len(rows):012d}", "created_at": mv._iso_now()}
        rows[row["id"]] = row
        return row

    async def db_select(table, *, filters=None, extra=None, select="*"):
        found = [r for r in rows.values() if all(str(r.get(k)) == str(v) for k, v in (filters or {}).items())]
        extra = extra or {}
        if extra.get("task_id") == "not.is.null":
            found = [r for r in found if r.get("task_id")]
        if "status" in extra:
            allowed = extra["status"][4:-1].split(",")
            found = [r for r in found if r.get("status") in allowed]
        return found

    async def db_update(table, filters, patch_):
        rows[filters["id"]].update(patch_)
        return []

    async def store_bytes(data, ext):
        key = f"{len(objects):032x}.{ext}"
        objects[key] = data
        return key

    async def fetch_bytes(key):
        return objects.get(key)

    for name, fn in [("db_insert", db_insert), ("db_select", db_select), ("db_update", db_update),
                     ("store_bytes", store_bytes), ("fetch_bytes", fetch_bytes)]:
        monkeypatch.setattr(mv, name, fn)
    monkeypatch.setattr(mv, "POLL_INTERVAL_SECONDS", 0)
    return rows, objects


def provider(monkeypatch, *, verdict, poll=None, found=True):
    monkeypatch.setattr(mv, "check_mascot_in_result", AsyncMock(return_value=(
        None if found is None else {"mascot_visible": found, "visible_at_end": found, "reason": ""}
    )))
    monkeypatch.setattr(mv, "burn_ai_label", lambda data: b"LABELLED:" + data)
    service = svc.zai_video_service
    upload = AsyncMock(return_value="oss://tmp/clip.mp4")
    submit = AsyncMock(return_value="task-9")
    monkeypatch.setattr(service, "upload_temp_file", upload)
    monkeypatch.setattr(service, "submit_video_edit", submit)
    monkeypatch.setattr(service, "fetch_result", AsyncMock(return_value=poll or {
        "status": "success", "video_url": "https://provider/out.mp4", "raw_status": "SUCCEEDED",
    }))
    monkeypatch.setattr(service, "download", AsyncMock(return_value=b"RESULT"))
    monkeypatch.setattr(service, "fetch_dashscope_usage", AsyncMock(return_value={"duration": 10.4, "SR": 720}))
    monkeypatch.setattr(moderation, "check_video_safety", AsyncMock(return_value=verdict))
    return upload, submit


async def run_job(prompt="lambai"):
    row = await mv.create_job(
        merchant_id=MERCHANT, clip=make_mp4(5.2), clip_ext="mp4", clip_seconds=5.2,
        mascot=b"PNG", mascot_ext="png", prompt=prompt,
    )
    await mv._running[row["id"]]
    return row["id"]


class TestDriver:
    async def test_safe_clip_is_rendered_stored_and_costed(self, store, monkeypatch):
        rows, objects = store
        monkeypatch.setenv("MASCOT_VIDEO_WATERMARK", "true")
        upload, submit = provider(monkeypatch, verdict={"is_safe": True})
        row = rows[await run_job()]
        assert row["status"] == "ready"
        assert objects[row["result_key"]] == b"LABELLED:RESULT"  # the stored file carries the AI label
        assert row["mascot_found"] is True
        assert row["result_url"].endswith(f"/api/v1/mascot-videos/media/{row['result_key']}")
        assert row["cost"] == 1.04  # metered: 10.4 billed seconds at 720P
        assert row["consent_at"]
        # one temp upload per model: moderation, then the render
        assert [c.kwargs["model"] for c in upload.await_args_list] == ["qwen3-vl-plus", "wan3.0-video"]
        kwargs = submit.await_args.kwargs
        assert kwargs["video_url"] == "oss://tmp/clip.mp4"
        assert kwargs["reference_image_urls"][0].startswith("data:image/png;base64,")
        assert kwargs["watermark"] is True

    async def test_unsafe_clip_is_rejected_and_never_rendered(self, store, monkeypatch):
        rows, _ = store
        _, submit = provider(monkeypatch, verdict={"is_safe": False, "reason": "violence"})
        row = rows[await run_job()]
        assert row["status"] == "rejected" and not row.get("task_id")
        submit.assert_not_awaited()
        assert await mv.renders_today(MERCHANT) == 0  # a refused clip does not use the cap

    async def test_moderation_outage_fails_the_job_without_rendering(self, store, monkeypatch):
        rows, _ = store
        _, submit = provider(monkeypatch, verdict={"is_safe": False, "unavailable": True})
        row = rows[await run_job()]
        assert row["status"] == "failed"
        submit.assert_not_awaited()

    async def test_provider_failure_ends_the_job_and_still_counts(self, store, monkeypatch):
        rows, _ = store
        provider(monkeypatch, verdict={"is_safe": True},
                 poll={"status": "fail", "raw_status": "FAILED", "code": "X", "message": "internal detail"})
        row = rows[await run_job()]
        assert row["status"] == "failed"
        assert "internal detail" not in row["error"]
        assert await mv.renders_today(MERCHANT) == 1  # it reached the provider
        assert await mv.active_jobs(MERCHANT) == 0

    async def test_render_without_a_mascot_is_not_delivered_and_not_counted(self, store, monkeypatch):
        rows, objects = store
        provider(monkeypatch, verdict={"is_safe": True}, found=False)
        row = rows[await run_job()]
        assert row["status"] == "failed" and row["mascot_found"] is False
        assert row["error"] == mv.NO_MASCOT_MESSAGE
        assert not row.get("result_key") and b"LABELLED:RESULT" not in objects.values()
        assert row["cost"] == 1.04  # it was still paid for
        usage = await mv.usage_today(MERCHANT)
        assert usage["used"] == 0 and usage["attempts"] == 1

    async def test_render_is_delivered_when_the_mascot_check_cannot_run(self, store, monkeypatch):
        rows, _ = store
        provider(monkeypatch, verdict={"is_safe": True}, found=None)
        row = rows[await run_job()]
        assert row["status"] == "ready" and row["mascot_found"] is None
        assert await mv.renders_today(MERCHANT) == 1

    async def test_a_clip_that_cannot_be_labelled_is_not_delivered(self, store, monkeypatch):
        rows, _ = store
        provider(monkeypatch, verdict={"is_safe": True})

        def broken(_data):
            raise mv.LabelError("no ffmpeg")

        monkeypatch.setattr(mv, "burn_ai_label", broken)
        row = rows[await run_job()]
        assert row["status"] == "failed" and not row.get("result_key")

    async def test_a_merchant_cannot_read_another_merchants_job(self, store, monkeypatch):
        provider(monkeypatch, verdict={"is_safe": True})
        job_id = await run_job()
        assert (await mv.get_job(job_id, MERCHANT))["id"] == job_id
        assert await mv.get_job(job_id, OTHER) is None
        assert await mv.get_job("not-a-uuid", MERCHANT) is None


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch, store):
    app = FastAPI()
    app.include_router(ep.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: {"sub": MERCHANT}
    monkeypatch.setenv("MASCOT_VIDEO_ENABLED", "true")
    monkeypatch.delenv("MASCOT_VIDEO_DAILY_LIMIT", raising=False)
    provider(monkeypatch, verdict={"is_safe": True})
    monkeypatch.setattr(mv, "_spawn", lambda job_id: None)  # routes only; the driver is tested above
    monkeypatch.setattr(moderation, "moderate_uploaded_image", AsyncMock(return_value={"allowed": True, "message": ""}))
    return TestClient(app)


def post_job(client, *, seconds=5.0, consent="true", mascot=True, **data):
    files = {"clip": ("clip.mp4", make_mp4(seconds), "video/mp4")}
    if mascot:
        files["mascot"] = ("m.png", b"PNG", "image/png")
    return client.post("/api/v1/mascot-videos/jobs", files=files, data={"consent": consent, "prompt": "lambai", **data})


class TestRoutes:
    def test_every_route_404s_with_the_flag_off(self, client, monkeypatch):
        monkeypatch.setenv("MASCOT_VIDEO_ENABLED", "false")
        assert client.get("/api/v1/mascot-videos/config").status_code == 404
        assert client.get("/api/v1/mascot-videos/jobs").status_code == 404
        assert post_job(client).status_code == 404
        assert client.get("/api/v1/mascot-videos/media/" + "a" * 32 + ".mp4").status_code == 404

    def test_config_reports_limits_and_usage(self, client):
        body = client.get("/api/v1/mascot-videos/config").json()
        assert body["max_clip_seconds"] == 10
        assert body["daily"] == {"used": 0, "limit": 3, "remaining": 3, "attempts": 0, "attempt_limit": 6}

    def test_create_requires_consent(self, client):
        response = post_job(client, consent="false")
        assert response.status_code == 422
        assert response.json()["detail"]["error"] == "consent_required"

    def test_create_refuses_a_long_clip_and_a_missing_mascot(self, client):
        assert post_job(client, seconds=14).json()["detail"]["error"] == "clip_too_long"
        assert post_job(client, mascot=False).json()["detail"]["error"] == "mascot_required"

    def test_create_refuses_a_mascot_url_off_the_allowlist(self, client):
        response = post_job(client, mascot=False, mascot_url="https://169.254.169.254/latest/meta-data")
        assert response.status_code == 422
        assert response.json()["detail"]["error"] == "bad_mascot_url"

    def test_create_then_poll(self, client, store):
        rows, _ = store
        response = post_job(client)
        assert response.status_code == 202
        job = response.json()["job"]
        assert job["status"] == "queued" and job["ai_generated"] is True
        assert rows[job["id"]]["merchant_id"] == MERCHANT
        assert client.get(f"/api/v1/mascot-videos/jobs/{job['id']}").json()["job"]["id"] == job["id"]
        assert len(client.get("/api/v1/mascot-videos/jobs").json()["jobs"]) == 1

    def test_one_job_at_a_time(self, client):
        assert post_job(client).status_code == 202
        second = post_job(client)
        assert second.status_code == 409
        assert second.json()["detail"]["error"] == "job_in_progress"

    def test_daily_cap(self, client, store, monkeypatch):
        rows, _ = store
        monkeypatch.setenv("MASCOT_VIDEO_DAILY_LIMIT", "1")
        job_id = post_job(client).json()["job"]["id"]
        rows[job_id].update({"status": "ready", "task_id": "task-9"})
        capped = post_job(client)
        assert capped.status_code == 429
        assert capped.json()["detail"]["error"] == "daily_limit_reached"

    def test_no_mascot_renders_do_not_use_the_cap_but_hit_the_attempt_ceiling(self, client, store, monkeypatch):
        rows, _ = store
        monkeypatch.setenv("MASCOT_VIDEO_DAILY_LIMIT", "1")
        for _ in range(2):  # attempt ceiling defaults to twice the limit
            response = post_job(client)
            assert response.status_code == 202
            rows[response.json()["job"]["id"]].update({"status": "failed", "task_id": "t", "mascot_found": False})
        blocked = post_job(client)
        assert blocked.status_code == 429
        assert blocked.json()["detail"]["error"] == "daily_attempts_reached"

    def test_another_merchants_job_is_not_found(self, client, store):
        job_id = post_job(client).json()["job"]["id"]
        client.app.dependency_overrides[get_current_user] = lambda: {"sub": OTHER}
        assert client.get(f"/api/v1/mascot-videos/jobs/{job_id}").status_code == 404
        assert client.get("/api/v1/mascot-videos/jobs").json()["jobs"] == []

    def test_media_serves_only_well_formed_keys(self, client, store):
        _, objects = store
        key = "0" * 32 + ".mp4"
        objects[key] = b"VIDEO"
        ok = client.get(f"/api/v1/mascot-videos/media/{key}")
        assert ok.status_code == 200 and ok.content == b"VIDEO" and ok.headers["content-type"] == "video/mp4"
        assert client.get("/api/v1/mascot-videos/media/..%2Fsecret.mp4").status_code == 404


# --------------------------------------------------------------------------
# the burned-in label
# --------------------------------------------------------------------------

class TestLabel:
    def test_label_image_is_a_transparent_png(self):
        from io import BytesIO

        from PIL import Image

        image = Image.open(BytesIO(mv.ai_label_png()))
        assert image.mode == "RGBA" and image.width > image.height
        assert image.getpixel((0, 0))[3] == 0  # rounded corner is transparent

    def test_missing_ffmpeg_is_a_label_error(self, monkeypatch):
        monkeypatch.setattr(mv, "ffmpeg_path", lambda: None)
        with pytest.raises(mv.LabelError):
            mv.burn_ai_label(b"clip")

    def test_ffmpeg_failure_is_a_label_error(self):
        if not mv.ffmpeg_path():
            pytest.skip("no ffmpeg in this environment")
        with pytest.raises(mv.LabelError):
            mv.burn_ai_label(b"this is not a video")

    def test_usage_counts(self):
        rows = [{"mascot_found": True}, {"mascot_found": None}, {"mascot_found": False}]
        assert mv.count_usage(rows) == {"renders": 2, "attempts": 3}
