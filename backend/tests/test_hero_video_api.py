"""Tests for the hero video background endpoints.

    GET    /api/v1/websites/hero-video/options
    GET    /api/v1/websites/{id}/hero-video
    POST   /api/v1/websites/{id}/hero-video/generate
    GET    /api/v1/websites/{id}/hero-video/jobs/{job_id}
    PATCH  /api/v1/websites/{id}/hero-video
    DELETE /api/v1/websites/{id}/hero-video

What matters beyond "does it add a video":

  1. Flag-gated: HERO_VIDEO_ENABLED off → 404 everywhere.
  2. The only AI call is the Z.ai submit/poll; apply, tweak and remove are
     credit-free HTML patches (no quota counters are ever imported here).
  3. Publish safety, inherited from the theme/contact paths: patch the live
     snapshot, never publish an unbalanced base, be honest when the live site
     did not change.
  4. Cost guards: plan gate, one job per site, per-site daily cap.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.endpoints import hero_video as ep
from app.services import zai_video_service as svc
from app.services.hero_video_patcher import (
    BLOCK_START,
    HERO_MARKER_ATTR,
    LEGACY_CHILD_RULE,
    STYLE_ID,
    apply_hero_video,
    build_settings,
    needs_style_upgrade,
)

LIVE_HTML = (
    "<!DOCTYPE html><html><head><title>Kedai Ali</title></head>"
    "<body>"
    '<header><nav><a href="#home">Utama</a></nav></header>'
    '<section id="home" class="min-h-screen"><div><h1>Kedai Ali</h1><p>Nasi lemak</p></div></section>'
    '<section id="menu"><h2>Menu</h2></section>'
    "<footer>foot</footer></body></html>"
)

NO_HERO_HTML = "<!DOCTYPE html><html><head></head><body><p>hi</p></body></html>"

# Truncated mid-tag: no </body>, no </html>. The mimba failure shape.
TRUNCATED_HTML = '<!DOCTYPE html><html><head></head><body><img src="https://x'

CLOUD_VIDEO = "https://res.cloudinary.com/demo/video/upload/q_auto:eco,w_1280,c_limit,ac_none/v1/binaapp/hero-videos/ws-1-ab.mp4"
CLOUD_POSTER = "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-1-ab.jpg"

WITH_VIDEO_HTML = apply_hero_video(
    LIVE_HTML, build_settings(video_url=CLOUD_VIDEO, poster_url=CLOUD_POSTER)
).html


def _access(free=False, credits=0):
    return {
        "free": free,
        "credits": credits,
        "allowed": free or credits > 0,
        "price_rm": 5.0,
        "addon_type": "hero_video",
    }


def _row(**overrides):
    row = {
        "id": "ws-1",
        "user_id": "test-user-id-12345",
        "business_name": "Kedai Ali",
        "business_type": "restaurant",
        "description": "Nasi lemak sambal sotong",
        "subdomain": "kedaiali",
        "status": "published",
        "html_content": LIVE_HTML,
    }
    row.update(overrides)
    return row


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("HERO_VIDEO_ENABLED", "true")
    monkeypatch.setenv("ZAI_API_KEY", "zai-test-key")
    ep._reset_submit_counters()
    svc.zai_video_service._jobs.clear()
    yield
    svc.zai_video_service._jobs.clear()


@pytest.fixture
def patches():
    with (
        patch.object(ep.supabase_service, "get_website", new=AsyncMock(return_value=_row())) as get_website,
        patch.object(ep.supabase_service, "update_website", new=AsyncMock(return_value=True)) as update_website,
        patch.object(
            ep.storage_service, "publish_website",
            new=AsyncMock(return_value="https://kedaiali.binaapp.my"),
        ) as publish_website,
        patch.object(ep, "_fetch_serving_snapshot", new=AsyncMock(return_value=None)) as fetch_snapshot,
        patch.object(ep, "hero_video_access", new=AsyncMock(return_value=_access(free=True))) as plan_gate,
        patch.object(ep.subscription_service, "use_addon_credit", new=AsyncMock(return_value=True)) as use_credit,
        patch.object(ep.subscription_service, "refund_addon_credit", new=AsyncMock(return_value=True)) as refund_credit,
        patch.object(
            svc.zai_video_service, "submit_with_fallback",
            new=AsyncMock(return_value=("task-1", "dashscope")),
        ) as submit,
        patch.object(
            svc.zai_video_service, "fetch_result",
            new=AsyncMock(return_value={"status": "processing", "video_url": None, "cover_image_url": None}),
        ) as fetch_result,
        patch.object(
            svc.zai_video_service, "store",
            new=AsyncMock(return_value={"video_url": CLOUD_VIDEO, "poster_url": CLOUD_POSTER}),
        ) as store,
        # Overlay auto-selection reads the poster over HTTP; pin it here and
        # let the luminance tests below override it.
        patch.object(ep, "auto_overlay_opacity", new=AsyncMock(return_value=0.45)) as auto_opacity,
        # The durable ledger and the timeout alert talk to Supabase / SMTP.
        patch.object(ep.ledger, "save", new=AsyncMock(return_value="ok")) as ledger_save,
        patch.object(ep.ledger, "create", new=AsyncMock(return_value=True)) as ledger_create,
        patch.object(ep.ledger, "mark_refunded", new=AsyncMock(return_value=True)) as ledger_mark_refunded,
        patch.object(ep.ledger, "load", new=AsyncMock(return_value=None)) as ledger_load,
        patch.object(ep.ledger, "load_claimable", new=AsyncMock(return_value=[])) as ledger_claimable,
        patch.object(ep.ledger, "load_stale", new=AsyncMock(return_value=[])) as ledger_stale,
        patch.object(ep.ledger, "claim", new=AsyncMock(return_value=True)) as ledger_claim,
        patch(
            "app.services.email_service.email_service.send_admin_notification",
            new=AsyncMock(return_value=True),
        ) as admin_email,
    ):
        yield {
            "auto_opacity": auto_opacity,
            "ledger_save": ledger_save,
            "ledger_create": ledger_create,
            "ledger_mark_refunded": ledger_mark_refunded,
            "ledger_load": ledger_load,
            "ledger_claimable": ledger_claimable,
            "ledger_stale": ledger_stale,
            "ledger_claim": ledger_claim,
            "admin_email": admin_email,
            "get_website": get_website,
            "update_website": update_website,
            "publish_website": publish_website,
            "fetch_snapshot": fetch_snapshot,
            "plan_gate": plan_gate,
            "use_credit": use_credit,
            "refund_credit": refund_credit,
            "submit": submit,
            "fetch_result": fetch_result,
            "store": store,
        }


def _published_html(patches):
    assert patches["publish_website"].called
    return patches["publish_website"].call_args.kwargs["html_content"]


def _drive_once(job_id):
    """One step of the server driver, on its own loop. The poll endpoint is
    read-only, so tests advance the job the way the driver does."""
    import asyncio as _a

    job = svc.zai_video_service.get_job(job_id)

    async def _step():
        await ep._advance_hero_video_job(job, job.website_id, job.user_id)
        if job.finalize_task is not None:
            await job.finalize_task

    _a.run(_step())
    return job


def _drive_to_done(client, auth_headers, job_id, steps=20):
    """Run the driver until the job is terminal, then read it back through
    the (read-only) poll endpoint exactly as the dashboard would."""
    for _ in range(steps):
        job = _drive_once(job_id)
        if job.status not in ("processing", "storing"):
            break
    else:
        raise AssertionError(f"job never finished: {job.to_dict()}")
    return client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers)


def _start_job(client, auth_headers, body=None):
    resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json=body or {}, headers=auth_headers)
    assert resp.status_code == 202, resp.text
    return resp.json()["job_id"]


class TestFlag:
    def test_everything_404s_when_off(self, client, auth_headers, patches, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_ENABLED", "false")
        assert client.get("/api/v1/websites/hero-video/options").status_code == 404
        assert client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers).status_code == 404
        assert client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers).status_code == 404
        assert client.delete("/api/v1/websites/ws-1/hero-video", headers=auth_headers).status_code == 404
        patches["submit"].assert_not_called()


class TestOptions:
    def test_catalogue_is_public(self, client):
        body = client.get("/api/v1/websites/hero-video/options").json()
        # DashScope running the unified wan3.0-video model is the default.
        assert body["success"] and body["model"] == "wan3.0-video"
        assert body["provider"] == "dashscope"
        assert {s["key"] for s in body["styles"]} >= {"cinematic", "ambient", "elegant"}
        assert all(s["label_ms"] for s in body["styles"])
        assert body["overlays"] == ["dark", "light", "none"]

    def test_catalogue_follows_the_provider_switch(self, client, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_PROVIDER", "zai")
        body = client.get("/api/v1/websites/hero-video/options").json()
        assert body["model"] == "cogvideox-3" and body["provider"] == "zai"


class TestReadState:
    def test_clean_page(self, client, auth_headers, patches):
        body = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers).json()
        assert body["has_video"] is False and body["settings"] is None
        assert body["hero_found"] is True and body["hero_match"] == "id"
        assert body["job"] is None and body["allowed"] is True
        assert body["source"] == "db"

    def test_reads_the_live_snapshot_first(self, client, auth_headers, patches):
        patches["fetch_snapshot"].return_value = WITH_VIDEO_HTML
        body = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers).json()
        assert body["source"] == "storage"
        assert body["has_video"] is True
        assert body["settings"]["video_url"] == CLOUD_VIDEO

    def test_requires_ownership(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(user_id="someone-else")
        assert client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers).status_code == 403

    def test_requires_auth(self, client, patches):
        assert client.get("/api/v1/websites/ws-1/hero-video").status_code in (401, 403)


class TestGenerate:
    def test_starts_a_job_with_a_business_aware_prompt(self, client, auth_headers, patches):
        resp = client.post(
            "/api/v1/websites/ws-1/hero-video/generate",
            json={"style": "ambient", "overlay": "light", "overlay_opacity": 0.3},
            headers=auth_headers,
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "processing" and body["job_id"]
        assert "Kedai Ali" in body["prompt"] and "calm ambient" in body["prompt"]
        prompt_arg = patches["submit"].call_args.args[0]
        assert prompt_arg == body["prompt"]
        # The look is remembered on the job, applied when the clip lands.
        job = svc.zai_video_service.get_job(body["job_id"])
        assert job.settings["overlay"] == "light" and job.settings["overlay_opacity"] == 0.3
        # Nothing is written until the video exists.
        patches["update_website"].assert_not_called()
        patches["publish_website"].assert_not_called()

    def test_custom_prompt_is_forwarded(self, client, auth_headers, patches):
        _start_job(client, auth_headers, {"prompt": "asap naik dari wok"})
        # Leads the prompt, closed with a full stop so the ambience and the
        # boilerplate that follow read as their own sentences (this used to
        # join with a bare space and run straight into "Background video...").
        assert patches["submit"].call_args.args[0].startswith("asap naik dari wok. ")

    def test_plan_gate_blocks_before_spending(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=0)
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 402
        assert resp.json()["detail"]["error"] == "payment_required"
        assert resp.json()["detail"]["price_rm"] == 5.0
        patches["submit"].assert_not_called()

    def test_no_hero_blocks_before_spending(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=NO_HERO_HTML)
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "hero_not_found"
        patches["submit"].assert_not_called()

    def test_unbalanced_base_blocks_before_spending(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=TRUNCATED_HTML)
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "no_balanced_html_base"
        patches["submit"].assert_not_called()

    def test_one_job_per_site(self, client, auth_headers, patches):
        _start_job(client, auth_headers)
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "job_in_progress"
        assert patches["submit"].call_count == 1

    def test_daily_cap(self, client, auth_headers, patches, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_MAX_PER_SITE_PER_DAY", "2")
        for _ in range(2):
            job_id = _start_job(client, auth_headers)
            svc.zai_video_service.get_job(job_id).status = svc.JOB_STATUS_FAILED
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 429
        assert resp.json()["detail"]["error"] == "daily_limit_reached"

    def test_zai_submit_failure_is_a_502_and_not_counted(self, client, auth_headers, patches):
        patches["submit"].side_effect = svc.ZaiVideoError("boom")
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 502
        assert svc.zai_video_service.active_job_for_website("ws-1") is None
        assert ep._count_recent_submits("ws-1") == 0

    def test_non_https_image_url_is_dropped(self, client, auth_headers, patches):
        _start_job(client, auth_headers, {"image_url": "http://x/hero.jpg"})
        assert patches["submit"].call_args.kwargs["image_url"] is None
        svc.zai_video_service._jobs.clear()
        _start_job(client, auth_headers, {"image_url": "https://x/hero.jpg"})
        assert patches["submit"].call_args.kwargs["image_url"] == "https://x/hero.jpg"


class TestPoll:
    def test_still_processing(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "processing" and body["applied"] is False
        patches["store"].assert_not_called()
        patches["publish_website"].assert_not_called()

    def test_success_stores_applies_and_publishes(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers, {"overlay": "light"})
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        resp = _drive_to_done(client, auth_headers, job_id)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed" and body["applied"] is True
        assert body["live_site_updated"] is True
        assert body["video_url"] == CLOUD_VIDEO and body["poster_url"] == CLOUD_POSTER
        assert body["settings"]["overlay"] == "light"
        patches["store"].assert_awaited_once_with("https://cdn.z.ai/v.mp4", website_id="ws-1")

        html = _published_html(patches)
        assert f'{HERO_MARKER_ATTR}="1"' in html and BLOCK_START in html
        assert CLOUD_VIDEO in html and f'id="{STYLE_ID}"' in html
        assert "<h1>Kedai Ali</h1>" in html  # copy untouched
        assert body["html_content"] == html
        assert patches["update_website"].call_args.args[1]["html_content"] == html

    def test_success_patches_the_live_snapshot_not_the_stale_db(self, client, auth_headers, patches):
        live = LIVE_HTML.replace("Nasi lemak", "Nasi lemak LIVE")
        patches["fetch_snapshot"].return_value = live
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["base_source"] == "storage"
        assert "Nasi lemak LIVE" in _published_html(patches)

    def test_second_poll_after_completion_is_cheap(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        _drive_to_done(client, auth_headers, job_id)
        again = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert again["status"] == "completed"
        assert again["html_content"]  # the payload survives on the job for later polls
        assert patches["store"].await_count == 1
        assert patches["publish_website"].await_count == 1

    def test_generation_failure(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "fail", "video_url": None, "cover_image_url": None}
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["status"] == "failed" and body["error"] == "generation_failed"
        # The site can start a new one straight away.
        assert svc.zai_video_service.active_job_for_website("ws-1") is None

    def test_storage_failure(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        patches["store"].side_effect = svc.ZaiVideoError("cloudinary down")
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["status"] == "failed" and body["error"] == "storage_failed"
        patches["publish_website"].assert_not_called()

    def test_transient_poll_error_is_still_processing(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].side_effect = svc.ZaiVideoError("DashScope video poll failed (403)", status_code=403)
        _drive_once(job_id)
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "processing"
        # ...and the job says what the provider actually answered.
        assert body["provider_status"] == "http_403"

    def test_timeout_marks_failed(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        svc.zai_video_service.get_job(job_id).created_at -= svc.zai_video_max_wait_seconds() + 1
        _drive_once(job_id)
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "failed" and body["error"] == "timeout"
        patches["fetch_result"].assert_not_called()

    def test_storage_refresh_failure_is_reported_honestly(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        patches["publish_website"].side_effect = RuntimeError("storage down")
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["status"] == "completed"
        assert body["live_site_updated"] is False
        assert body["warning"] == "storage_refresh_failed"
        assert "belum dikemas kini" in body["message"]
        html_writes = [c for c in patches["update_website"].await_args_list if "html_content" in c.args[1]]
        assert len(html_writes) == 1

    def test_the_poll_endpoint_never_talks_to_the_provider(self, client, auth_headers, patches):
        """The browser poll is read-only. It used to poll the provider as
        well as the server driver (two pollers per job, one on a request
        path a phone fires every 8 s) and read the website row each time."""
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        reads_before = patches["get_website"].await_count
        for _ in range(3):
            body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
            assert body["status"] == "processing" and body["applied"] is False
        patches["fetch_result"].assert_not_called()
        patches["store"].assert_not_called()
        assert patches["get_website"].await_count == reads_before
        # A poll during 'storing' reports progress, nothing more.
        svc.zai_video_service.get_job(job_id).status = svc.JOB_STATUS_STORING
        storing = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert storing["status"] == "storing" and "html_content" not in storing
        assert "dipasang" in storing["message"]
        svc.zai_video_service.get_job(job_id).status = svc.JOB_STATUS_PROCESSING
        done = _drive_to_done(client, auth_headers, job_id).json()
        assert done["status"] == "completed" and done["html_content"]

    def test_overlay_opacity_follows_the_posters_luminance_when_not_set(self, client, auth_headers, patches):
        """Bug 5: the old fixed 0.45 was unreadable over a bright clip."""
        patches["auto_opacity"].return_value = 0.7
        job_id = _start_job(client, auth_headers, {"overlay": "dark"})  # no overlay_opacity
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["settings"]["overlay_opacity"] == 0.7
        patches["auto_opacity"].assert_awaited_once_with(CLOUD_POSTER)
        assert "rgba(0,0,0,0.7)" in _published_html(patches)

    def test_an_explicit_overlay_opacity_is_the_merchants_and_is_kept(self, client, auth_headers, patches):
        patches["auto_opacity"].return_value = 0.7
        job_id = _start_job(client, auth_headers, {"overlay": "dark", "overlay_opacity": 0.3})
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["settings"]["overlay_opacity"] == 0.3
        patches["auto_opacity"].assert_not_called()

    def test_no_overlay_means_no_luminance_lookup(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers, {"overlay": "none"})
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        _drive_to_done(client, auth_headers, job_id)
        patches["auto_opacity"].assert_not_called()

    def test_unknown_or_foreign_job_404s(self, client, auth_headers, patches):
        assert client.get("/api/v1/websites/ws-1/hero-video/jobs/nope", headers=auth_headers).status_code == 404
        job = svc.zai_video_service.register_job(
            task_id="t", website_id="ws-other", user_id="test-user-id-12345", prompt="p", settings={}
        )
        assert client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job.job_id}", headers=auth_headers).status_code == 404


class TestPatchLook:
    def test_changes_overlay_without_ai(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        resp = client.patch(
            "/api/v1/websites/ws-1/hero-video",
            json={"overlay": "none", "show_on_mobile": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["changed"] is True and body["live_site_updated"] is True
        assert body["settings"]["overlay"] == "none" and body["settings"]["show_on_mobile"] is False
        assert body["settings"]["video_url"] == CLOUD_VIDEO  # clip reused
        html = _published_html(patches)
        assert 'data-binaapp-overlay="none"' in html and html.count(BLOCK_START) == 1
        patches["submit"].assert_not_called()
        patches["store"].assert_not_called()

    def test_same_settings_is_a_noop(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        body = client.patch("/api/v1/websites/ws-1/hero-video", json={"overlay": "dark"}, headers=auth_headers).json()
        assert body["changed"] is False
        patches["publish_website"].assert_not_called()

    def test_404_when_no_video(self, client, auth_headers, patches):
        resp = client.patch("/api/v1/websites/ws-1/hero-video", json={"overlay": "none"}, headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "no_hero_video"

    def test_rejects_out_of_range_opacity(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        resp = client.patch("/api/v1/websites/ws-1/hero-video", json={"overlay_opacity": 1.5}, headers=auth_headers)
        assert resp.status_code == 422


class TestRemove:
    def test_restores_the_original_page(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        resp = client.delete("/api/v1/websites/ws-1/hero-video", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["changed"] is True and body["live_site_updated"] is True
        assert _published_html(patches) == LIVE_HTML
        assert body["html_content"] == LIVE_HTML

    def test_noop_when_nothing_to_remove(self, client, auth_headers, patches):
        body = client.delete("/api/v1/websites/ws-1/hero-video", headers=auth_headers).json()
        assert body["changed"] is False
        patches["publish_website"].assert_not_called()
        patches["update_website"].assert_not_called()

    def test_unpublished_site_updates_db_only(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(status="draft", html_content=WITH_VIDEO_HTML)
        body = client.delete("/api/v1/websites/ws-1/hero-video", headers=auth_headers).json()
        assert body["changed"] is True and body["live_site_updated"] is False
        patches["publish_website"].assert_not_called()
        # Two DB writes, in order: the row forgets the clip, then the page.
        writes = [c.args[1] for c in patches["update_website"].await_args_list]
        assert len(writes) == 2
        assert writes[0]["hero_video_url"] is None and writes[0]["hero_video_settings"] is None
        assert "html_content" in writes[1] and BLOCK_START not in writes[1]["html_content"]

    def test_unbalanced_base_is_refused(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=TRUNCATED_HTML)
        resp = client.delete("/api/v1/websites/ws-1/hero-video", headers=auth_headers)
        assert resp.status_code == 422
        patches["publish_website"].assert_not_called()


# ---------------------------------------------------------------------------
# Self-heal: pages patched by the first release get the current CSS
# ---------------------------------------------------------------------------

# WITH_VIDEO_HTML with the first release's child-restyling rule spliced into
# the page's own style block — exactly what a site patched before the fix
# carries in storage.
LEGACY_CSS_HTML = WITH_VIDEO_HTML.replace("</style>", LEGACY_CHILD_RULE + "</style>", 1)
assert needs_style_upgrade(LEGACY_CSS_HTML)


class TestLegacyCssSelfHeal:
    def test_state_read_reapplies_current_css_and_republishes(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=LEGACY_CSS_HTML)

        resp = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["upgraded_css"] is True
        assert body["has_video"] is True
        assert body["settings"]["video_url"] == CLOUD_VIDEO

        published = _published_html(patches)
        assert LEGACY_CHILD_RULE not in published
        assert needs_style_upgrade(published) is False
        assert "z-index:-1;" in published
        # The clip and its settings survive the rewrite untouched.
        assert CLOUD_VIDEO in published and CLOUD_POSTER in published
        assert patches["update_website"].called

    def test_state_read_on_current_css_is_read_only(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)

        resp = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["upgraded_css"] is False
        assert not patches["publish_website"].called
        assert not patches["update_website"].called

    def test_state_read_without_video_is_read_only(self, client, auth_headers, patches):
        resp = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["upgraded_css"] is False
        assert resp.json()["has_video"] is False
        assert not patches["publish_website"].called

    def test_persist_failure_never_breaks_the_read(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=LEGACY_CSS_HTML)
        patches["update_website"].side_effect = RuntimeError("db down")

        resp = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["upgraded_css"] is False
        # Still reports the video the page has — from the unmodified HTML.
        assert body["has_video"] is True


class TestProviderConfigurationErrors:
    def test_rejected_key_is_reported_as_configuration(self, client, auth_headers, patches):
        patches["submit"].side_effect = svc.ZaiVideoError("DashScope video submit failed (401)")
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail["error"] == "provider_not_configured"
        assert "kunci API" in detail["message"]

    def test_transient_submit_failure_keeps_the_retry_message(self, client, auth_headers, patches):
        patches["submit"].side_effect = svc.ZaiVideoError("DashScope video submit timed out")
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 502
        assert resp.json()["detail"]["error"] == "video_submit_failed"

    def test_job_polls_the_provider_it_was_submitted_to(self, client, auth_headers, patches):
        patches["submit"].return_value = ("zai-task-9", "zai")
        job_id = _start_job(client, auth_headers)
        _drive_once(job_id)
        assert patches["fetch_result"].call_args.kwargs.get("provider") == "zai"


# ---------------------------------------------------------------------------
# Paid per clip: RM5 add-on credit, charged on accept, refunded on failure
# ---------------------------------------------------------------------------

class TestPaidCredits:
    def test_free_access_never_consumes_a_credit(self, client, auth_headers, patches):
        _start_job(client, auth_headers)
        assert not patches["use_credit"].called

    def test_credit_is_consumed_once_the_provider_accepts(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=2)
        job_id = _start_job(client, auth_headers)
        patches["use_credit"].assert_awaited_once_with("test-user-id-12345", "hero_video")
        job = svc.zai_video_service.get_job(job_id)
        assert job.charged is True

    def test_rejected_submit_costs_nothing(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=1)
        patches["submit"].side_effect = svc.ZaiVideoError("DashScope video submit failed (500)")
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", headers=auth_headers, json={})
        assert resp.status_code == 502
        assert not patches["use_credit"].called

    def test_failed_generation_refunds_the_credit(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=1)
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "fail", "video_url": None, "cover_image_url": None}
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["status"] == "failed" and body["error"] == "generation_failed"
        patches["refund_credit"].assert_awaited_once_with("test-user-id-12345", "hero_video")
        assert body["refunded"] is True
        # A second poll of the same failed job never refunds twice.
        client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers)
        assert patches["refund_credit"].await_count == 1

    def test_storage_failure_refunds_too(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=1)
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://p/v.mp4", "cover_image_url": None}
        patches["store"].side_effect = svc.ZaiVideoError("storage failed")
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["error"] == "storage_failed"
        assert patches["refund_credit"].await_count == 1

    def test_successful_job_keeps_the_charge(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=1)
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://p/v.mp4", "cover_image_url": None}
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["status"] == "completed" and body["charged"] is True and body["refunded"] is False
        assert not patches["refund_credit"].called

    def test_state_and_options_expose_price_and_credits(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=3)
        state = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers).json()
        assert state["allowed"] is True and state["free_access"] is False and state["credits"] == 3
        assert state["price_rm"] == 5.0 and state["addon_type"] == "hero_video"
        options = client.get("/api/v1/websites/hero-video/options").json()
        assert options["price_rm"] == 5.0 and options["addon_type"] == "hero_video"

    def test_access_endpoint(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=0)
        body = client.get("/api/v1/websites/hero-video/access", headers=auth_headers).json()
        assert body["allowed"] is False and body["credits"] == 0 and body["price_rm"] == 5.0



class TestPhotoIsTheStill:
    """When the job was asked to animate the merchant's hero photo, that
    photo — not the clip's generic first frame — is the poster: the still
    shown while the clip loads, on data-saver phones and under
    prefers-reduced-motion. The scrim is still measured from the clip's own
    frame, because that is what it sits over while playing."""

    def test_poster_is_the_merchant_photo_and_scrim_reads_the_clip(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers, {"image_url": "https://res.cloudinary.com/x/shop.jpg"})
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["status"] == "completed"
        assert body["poster_url"] == "https://res.cloudinary.com/x/shop.jpg"
        assert body["image_url"] == "https://res.cloudinary.com/x/shop.jpg"
        # Overlay opacity was unset → measured, and from the CLIP's frame.
        patches["auto_opacity"].assert_awaited_once_with(CLOUD_POSTER)
        html = _published_html(patches)
        assert 'poster="https://res.cloudinary.com/x/shop.jpg"' in html
        assert CLOUD_POSTER not in html

    def test_text_job_keeps_the_clip_frame_as_poster(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        body = _drive_to_done(client, auth_headers, job_id).json()
        assert body["poster_url"] == CLOUD_POSTER and body["image_url"] is None


class TestServerDrivesTheJob:
    """The server polls the provider itself. Before this, the browser's
    poll was the only thing that advanced a job: website malan's merchant
    went back to the dashboard 56 seconds in, DashScope finished the clip,
    and nobody ever collected it.

    These run the driver on a real event loop rather than through the
    sync TestClient: that fixture opens a fresh portal per request and
    tears it down with the response, cancelling any timer-driven task —
    a browser that has left, in miniature, and exactly the situation in
    which the clip must still land. Nothing here ever polls the job."""

    def _job(self, user_id, **kw):
        return svc.zai_video_service.register_job(
            task_id="task-1", website_id="ws-1", user_id=user_id, prompt="p",
            settings=ep.HeroVideoLook().model_dump(), provider="dashscope", **kw,
        )

    def test_generate_starts_the_driver(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        assert svc.zai_video_service.get_job(job_id).driver_task is not None

    async def test_clip_lands_with_nobody_polling(self, patches, test_user_id, monkeypatch):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        job = self._job(test_user_id)
        await ep._drive_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "storing" and job.finalize_task is not None
        await job.finalize_task
        assert job.status == "completed" and job.applied is True and job.live_site_updated is True
        patches["store"].assert_awaited_once_with("https://cdn.z.ai/v.mp4", website_id="ws-1")
        assert CLOUD_VIDEO in _published_html(patches)

    async def test_failure_refunds_with_nobody_polling(self, patches, test_user_id, monkeypatch):
        """A paid clip the provider fails must give the credit back even
        though no browser is there to observe the failure."""
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        patches["fetch_result"].return_value = {
            "status": "fail", "video_url": None, "cover_image_url": None,
        }
        job = self._job(test_user_id, charged=True)
        await ep._drive_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "failed" and job.error == "generation_failed"
        assert patches["refund_credit"].called
        patches["store"].assert_not_called()

    async def test_timeout_refunds_with_nobody_polling(self, patches, test_user_id, monkeypatch):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        monkeypatch.setenv("ZAI_VIDEO_MAX_WAIT_SECONDS", "0")
        job = self._job(test_user_id, charged=True)
        await ep._drive_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "failed" and job.error == "timeout"
        assert patches["refund_credit"].called
        patches["fetch_result"].assert_not_called()

    async def test_driver_stops_when_the_job_is_purged(self, patches, test_user_id, monkeypatch):
        """A registry sweep (TTL) or reset must not leave a driver acting on
        a job nobody can see."""
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        job = self._job(test_user_id)
        svc.zai_video_service._jobs.clear()
        await ep._drive_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "processing"
        patches["fetch_result"].assert_not_called()

    async def test_two_drivers_hand_off_exactly_once(self, patches, test_user_id, monkeypatch):
        """The driver and the sweep may both observe SUCCESS; only one may
        store the clip."""
        import asyncio
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        job = self._job(test_user_id)
        await asyncio.gather(
            ep._drive_hero_video_job(job, "ws-1", test_user_id),
            ep._advance_hero_video_job(job, "ws-1", test_user_id),
        )
        await job.finalize_task
        assert job.status == "completed"
        patches["store"].assert_awaited_once()
        patches["publish_website"].assert_called_once()


class TestPreparedAheadOfPublish:
    """The clip is made while the page is still being generated, so the
    publish that follows goes live WITH its video.

    Every site the merchant checked right after publishing was static for
    the two or three minutes a post-publish job took, and read as "again
    no video". The hero photo, style and description are all known when
    they press Generate; the page takes minutes to build. So: prepare the
    clip then (no site yet), park it as `ready`, and let /api/publish
    stage it into the page it is about to upload."""

    PREPARE = "/api/v1/websites/hero-video/prepare"

    def _body(self, **extra):
        body = {
            "style": "cinematic",
            "prompt": "the whale glides past",
            "image_url": "https://res.cloudinary.com/demo/image/upload/whale.jpg",
            "business_name": "Kedai Ikan",
            "business_type": "food",
            "description": "Kedai ikan unik di Kota Damansara",
        }
        body.update(extra)
        return body

    def _prepared(self, user_id, **kw):
        job = svc.zai_video_service.register_job(
            task_id="task-p", website_id="", user_id=user_id, prompt="p",
            settings=ep.HeroVideoLook().model_dump(), provider="dashscope",
            image_url="https://res.cloudinary.com/demo/image/upload/whale.jpg", **kw,
        )
        return job

    def _ready(self, user_id, **kw):
        job = self._prepared(user_id, **kw)
        job.status = svc.JOB_STATUS_READY
        job.video_url = CLOUD_VIDEO
        job.poster_url = job.image_url
        return job

    # -- prepare ------------------------------------------------------------

    def test_prepare_starts_a_job_with_no_site(self, client, auth_headers, patches, test_user_id):
        resp = client.post(self.PREPARE, json=self._body(), headers=auth_headers)
        assert resp.status_code == 202, resp.text
        data = resp.json()
        job = svc.zai_video_service.get_job(data["job_id"])
        assert job is not None and job.website_id == "" and job.user_id == test_user_id
        assert job.driver_task is not None
        assert data["status"] == "processing"
        # The form's context reaches the prompt the way the row's would.
        prompt = patches["submit"].call_args.args[0]
        assert "the whale glides past" in prompt
        assert patches["submit"].call_args.kwargs["image_url"].endswith("whale.jpg")
        # No site was read or written.
        patches["get_website"].assert_not_called()
        patches["publish_website"].assert_not_called()

    def test_prepare_is_gated_like_generate(self, client, auth_headers, patches, test_user_id):
        patches["plan_gate"].return_value = _access(free=False, credits=0)
        assert client.post(self.PREPARE, json=self._body(), headers=auth_headers).status_code == 402
        patches["submit"].assert_not_called()

        patches["plan_gate"].return_value = _access(free=True)
        for _ in range(ep.MAX_ACTIVE_JOBS_PER_USER):
            self._prepared(test_user_id)
        resp = client.post(self.PREPARE, json=self._body(), headers=auth_headers)
        assert resp.status_code == 429 and resp.json()["detail"]["error"] == "too_many_jobs"

    def test_prepare_charges_a_paid_account_once_accepted(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=2)
        resp = client.post(self.PREPARE, json=self._body(), headers=auth_headers)
        assert resp.status_code == 202
        patches["use_credit"].assert_awaited_once()
        assert svc.zai_video_service.get_job(resp.json()["job_id"]).charged is True

    def test_prepare_requires_the_flag(self, client, auth_headers, patches, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_ENABLED", "false")
        assert client.post(self.PREPARE, json=self._body(), headers=auth_headers).status_code == 404

    # -- the clip lands before any site exists ---------------------------------

    async def test_clip_parks_as_ready_when_no_site_has_claimed_it(self, patches, test_user_id):
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        job = self._prepared(test_user_id)
        handed = await ep._advance_hero_video_job(job, "", test_user_id)
        assert handed and job.status == "storing"
        await job.finalize_task
        assert job.status == "ready"
        assert job.video_url == CLOUD_VIDEO
        # Stored under the job's own id — there is no site to file it under.
        patches["store"].assert_awaited_once_with("https://cdn.z.ai/v.mp4", website_id=job.job_id)
        # The merchant's photo is the still, as for any image job.
        assert job.poster_url == job.image_url
        patches["get_website"].assert_not_called()
        patches["publish_website"].assert_not_called()
        assert job.refunded is False

    async def test_unclaimed_clip_is_refunded_after_the_window(self, patches, test_user_id, monkeypatch):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        monkeypatch.setattr(ep, "PREPARED_CLAIM_WINDOW_SECONDS", 0.01)
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        job = self._prepared(test_user_id, charged=True)
        await ep._drive_hero_video_job(job, "", test_user_id)
        assert job.status == "failed" and job.error == "unclaimed"
        patches["refund_credit"].assert_awaited_once()

    async def test_a_claimed_clip_is_never_expired(self, patches, test_user_id, monkeypatch):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        monkeypatch.setattr(ep, "PREPARED_CLAIM_WINDOW_SECONDS", 0.5)
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        job = self._prepared(test_user_id, charged=True)
        import asyncio
        driver = asyncio.create_task(ep._drive_hero_video_job(job, "", test_user_id))
        while job.status != "ready":
            await asyncio.sleep(0.005)
        # The publish claims it inside the window.
        html, staged = ep.stage_prepared_hero_video(job.job_id, test_user_id, LIVE_HTML)
        await ep.settle_prepared_hero_video(job.job_id, test_user_id, _row(), staged)
        await driver
        assert job.status == "completed"
        patches["refund_credit"].assert_not_called()

    # -- polling a prepared job -------------------------------------------------

    def test_pending_poll_reports_the_prepared_job(self, client, auth_headers, patches, test_user_id):
        job = self._prepared(test_user_id)
        resp = client.get(f"/api/v1/websites/hero-video/jobs/{job.job_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing" and resp.json()["website_id"] == ""
        job.status = svc.JOB_STATUS_READY
        job.result_payload = {"message": "Video sedia"}
        data = client.get(f"/api/v1/websites/hero-video/jobs/{job.job_id}", headers=auth_headers).json()
        assert data["status"] == "ready" and data["message"] == "Video sedia"

    def test_pending_poll_is_owner_only(self, client, auth_headers, patches):
        job = self._prepared("someone-else")
        assert client.get(f"/api/v1/websites/hero-video/jobs/{job.job_id}", headers=auth_headers).status_code == 404
        assert client.get("/api/v1/websites/hero-video/jobs/nope", headers=auth_headers).status_code == 404

    # -- the publish claims the clip -----------------------------------------------

    def test_stage_puts_a_ready_clip_on_the_page_without_touching_the_job(self, patches, test_user_id):
        job = self._ready(test_user_id)
        html, info = ep.stage_prepared_hero_video(job.job_id, test_user_id, LIVE_HTML)
        assert info["status"] == "staged" and info["hero_match"] == "id"
        assert BLOCK_START in html and CLOUD_VIDEO in html
        assert f'img[src="{job.image_url}"]' in html
        # Nothing consumed yet: a publish that fails after this can stage again.
        assert job.status == "ready" and job.website_id == ""

    async def test_settle_confirms_a_staged_clip(self, patches, test_user_id):
        job = self._ready(test_user_id)
        html, staged = ep.stage_prepared_hero_video(job.job_id, test_user_id, LIVE_HTML)
        info = await ep.settle_prepared_hero_video(job.job_id, test_user_id, _row(), staged)
        assert info["status"] == "applied"
        assert job.status == "completed" and job.applied and job.live_site_updated
        assert job.website_id == "ws-1"
        # The publish wrote the page itself; the page is not written twice —
        # only the row's hero_video_* columns are brought in step.
        patches["publish_website"].assert_not_called()
        patches["update_website"].assert_awaited_once()
        row = patches["update_website"].await_args.args[1]
        assert row["hero_video_url"] == CLOUD_VIDEO and "html_content" not in row
        assert patches["ledger_save"].await_args.args[0] is job

    def test_stage_ignores_missing_foreign_or_finished_jobs(self, patches, test_user_id):
        assert ep.stage_prepared_hero_video(None, test_user_id, LIVE_HTML)[1]["status"] == "none"
        assert ep.stage_prepared_hero_video("nope", test_user_id, LIVE_HTML)[1]["status"] == "none"
        foreign = self._ready("someone-else")
        html, info = ep.stage_prepared_hero_video(foreign.job_id, test_user_id, LIVE_HTML)
        assert info["status"] == "none" and html == LIVE_HTML
        failed = self._prepared(test_user_id)
        failed.status = "failed"
        failed.error = "generation_failed"
        assert ep.stage_prepared_hero_video(failed.job_id, test_user_id, LIVE_HTML)[1] == {
            "status": "none", "job_id": failed.job_id, "reason": "generation_failed",
        }

    def test_stage_leaves_a_page_without_a_hero_alone(self, patches, test_user_id):
        job = self._ready(test_user_id)
        html, info = ep.stage_prepared_hero_video(job.job_id, test_user_id, NO_HERO_HTML)
        assert html == NO_HERO_HTML and info["reason"] == "hero_not_found"

    async def test_publish_before_the_clip_lands_attaches_the_site(self, patches, test_user_id):
        """The provider is still rendering when the merchant publishes:
        the site is attached to the job and the server applies the clip
        the moment it lands, with nobody polling."""
        job = self._prepared(test_user_id)
        html, staged = ep.stage_prepared_hero_video(job.job_id, test_user_id, LIVE_HTML)
        assert html == LIVE_HTML and staged["status"] == "pending"
        info = await ep.settle_prepared_hero_video(job.job_id, test_user_id, _row(), staged)
        assert info["status"] == "pending" and job.website_id == "ws-1"

        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://cdn.z.ai/v.mp4", "cover_image_url": None,
        }
        await ep._advance_hero_video_job(job, "", test_user_id)
        await job.finalize_task
        assert job.status == "completed" and job.live_site_updated is True
        patches["store"].assert_awaited_once_with("https://cdn.z.ai/v.mp4", website_id="ws-1")
        assert CLOUD_VIDEO in _published_html(patches)

    async def test_clip_ready_between_staging_and_upload_is_applied_at_settle(self, patches, test_user_id):
        job = self._prepared(test_user_id)
        html, staged = ep.stage_prepared_hero_video(job.job_id, test_user_id, LIVE_HTML)
        assert staged["status"] == "pending"
        # ...the clip lands while the upload is in flight...
        job.status = svc.JOB_STATUS_READY
        job.video_url = CLOUD_VIDEO
        job.poster_url = job.image_url
        info = await ep.settle_prepared_hero_video(job.job_id, test_user_id, _row(), staged)
        # Applied in the background, never inside the publish request; the
        # create page follows the job and gets the page from its poll.
        assert info["status"] == "pending" and job.website_id == "ws-1"
        assert job.status == "storing" and job.finalize_task is not None
        patches["publish_website"].assert_not_called()
        await job.finalize_task
        assert job.status == "completed" and BLOCK_START in job.result_payload["html_content"]
        assert CLOUD_VIDEO in _published_html(patches)

    async def test_settle_never_steals_a_job_attached_elsewhere(self, patches, test_user_id):
        job = self._prepared(test_user_id)
        job.website_id = "ws-other"
        info = await ep.settle_prepared_hero_video(job.job_id, test_user_id, _row(), {"status": "pending"})
        assert info["status"] == "none" and job.website_id == "ws-other"

    def test_generate_on_the_site_still_works_after_a_claim(self, client, auth_headers, patches, test_user_id):
        # A completed prepared job is not "active" — the merchant can make
        # another clip for the same site from the editor as before.
        job = self._ready(test_user_id)
        job.status = "completed"
        job.website_id = "ws-1"
        assert client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers).status_code == 202
