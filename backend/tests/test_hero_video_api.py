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

CLOUD_VIDEO = "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-1-ab.mp4"
CLOUD_POSTER = "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-1-ab.jpg"

WITH_VIDEO_HTML = apply_hero_video(
    LIVE_HTML, build_settings(video_url=CLOUD_VIDEO, poster_url=CLOUD_POSTER)
).html


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
        patch.object(ep, "can_use_hero_video", new=AsyncMock(return_value=True)) as plan_gate,
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
    ):
        yield {
            "get_website": get_website,
            "update_website": update_website,
            "publish_website": publish_website,
            "fetch_snapshot": fetch_snapshot,
            "plan_gate": plan_gate,
            "submit": submit,
            "fetch_result": fetch_result,
            "store": store,
        }


def _published_html(patches):
    assert patches["publish_website"].called
    return patches["publish_website"].call_args.kwargs["html_content"]


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
        # DashScope HappyHorse is the default provider.
        assert body["success"] and body["model"] == "happyhorse-1.1-t2v"
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
        assert patches["submit"].call_args.args[0].startswith("asap naik dari wok ")

    def test_plan_gate_blocks_before_spending(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = False
        resp = client.post("/api/v1/websites/ws-1/hero-video/generate", json={}, headers=auth_headers)
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "plan_not_allowed"
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
        resp = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers)
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
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["base_source"] == "storage"
        assert "Nasi lemak LIVE" in _published_html(patches)

    def test_second_poll_after_completion_is_cheap(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers)
        again = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert again["status"] == "completed"
        assert patches["store"].await_count == 1
        assert patches["publish_website"].await_count == 1

    def test_generation_failure(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "fail", "video_url": None, "cover_image_url": None}
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "failed" and body["error"] == "generation_failed"
        # The site can start a new one straight away.
        assert svc.zai_video_service.active_job_for_website("ws-1") is None

    def test_storage_failure(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        patches["store"].side_effect = svc.ZaiVideoError("cloudinary down")
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "failed" and body["error"] == "storage_failed"
        patches["publish_website"].assert_not_called()

    def test_transient_poll_error_is_still_processing(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].side_effect = svc.ZaiVideoError("poll timed out")
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "processing"

    def test_timeout_marks_failed(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        svc.zai_video_service.get_job(job_id).created_at -= svc.zai_video_max_wait_seconds() + 1
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "failed" and body["error"] == "timeout"
        patches["fetch_result"].assert_not_called()

    def test_storage_refresh_failure_is_reported_honestly(self, client, auth_headers, patches):
        job_id = _start_job(client, auth_headers)
        patches["fetch_result"].return_value = {"status": "success", "video_url": "https://cdn/v.mp4", "cover_image_url": None}
        patches["publish_website"].side_effect = RuntimeError("storage down")
        body = client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "completed"
        assert body["live_site_updated"] is False
        assert body["warning"] == "storage_refresh_failed"
        assert "belum dikemas kini" in body["message"]
        patches["update_website"].assert_awaited_once()

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
        patches["update_website"].assert_awaited_once()

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
        client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers)
        assert patches["fetch_result"].call_args.kwargs.get("provider") == "zai"

