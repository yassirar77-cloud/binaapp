"""The four things a merchant can do with a clip beyond generate / tweak /
remove, and the vertical clip they can make from the same inputs.

    speed + effect       credit-free playback rate and CSS colour look (patcher, PATCH)
    prompt ideas         GET /hero-video/ideas — static, per business type
    clip library         GET /{id}/hero-video/library, POST /{id}/hero-video/apply
    download link        state.download_url, library[].download_url (fl_attachment)
    social clip          POST /hero-video/social — 9:16, stored, never applied

Reuses the API fixtures of test_hero_video_api (same patches, same pages).
"""

from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints import hero_video as ep
from app.services import zai_video_service as svc
from app.services.hero_video_ideas import ideas_for
from app.services.hero_video_patcher import (
    BLOCK_START,
    DEFAULT_EFFECT,
    DEFAULT_SPEED,
    STYLE_ID,
    VIDEO_EFFECTS,
    apply_hero_video,
    build_settings,
    clamp_speed,
    clean_effect,
    detect_hero_video,
    hero_video_download_url,
    needs_style_upgrade,
    remove_hero_video,
)
from app.services.zai_video_service import (
    ASPECT_HERO,
    ASPECT_SOCIAL,
    PURPOSE_SOCIAL,
    build_hero_video_prompt,
    clean_aspect,
    purpose_of,
)
from tests.test_hero_video_api import (  # noqa: F401 — fixtures
    CLOUD_POSTER,
    CLOUD_VIDEO,
    LIVE_HTML,
    WITH_VIDEO_HTML,
    _access,
    _drive_to_done,
    _published_html,
    _row,
    enabled,
    patches,
)
from tests.test_zai_video_service import FakeResponse, fake_client

PAGE = (
    "<!DOCTYPE html><html><head><title>x</title></head><body>"
    '<section id="home"><h1>Kedai Ali</h1></section><footer>f</footer></body></html>'
)
RAW = "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-1-ab.mp4"


def _style(html):
    i = html.index(f'<style id="{STYLE_ID}">')
    return html[i:html.index("</style>", i)]


# ---------------------------------------------------------------------------
# Patcher: speed and effect
# ---------------------------------------------------------------------------

class TestSpeedAndEffect:
    def test_defaults_write_nothing_new(self):
        html = apply_hero_video(PAGE, build_settings(video_url=RAW)).html
        assert 'data-binaapp-speed="' not in html
        assert 'data-binaapp-effect="' not in html
        assert "filter:" not in _style(html)
        state = detect_hero_video(html)
        assert state["speed"] == DEFAULT_SPEED and state["effect"] == DEFAULT_EFFECT

    def test_speed_and_effect_round_trip(self):
        html = apply_hero_video(PAGE, build_settings(video_url=RAW, speed=0.5, effect="warm")).html
        assert 'data-binaapp-speed="0.5"' in html and 'data-binaapp-effect="warm"' in html
        state = detect_hero_video(html)
        assert state["speed"] == 0.5 and state["effect"] == "warm"
        # Re-applying what was read back is a no-op: no upgrade loop.
        assert needs_style_upgrade(html) is False

    def test_effect_is_a_css_filter_on_the_video_element(self):
        html = apply_hero_video(PAGE, build_settings(video_url=RAW, effect="mono")).html
        style = _style(html)
        assert ".binaapp-hero-video{filter:grayscale(1) contrast(1.05);}" in style

    def test_blurring_effect_overscans_to_hide_the_fringe(self):
        style = _style(apply_hero_video(PAGE, build_settings(video_url=RAW, effect="dreamy")).html)
        assert "filter:blur(2px)" in style and "transform:scale(1.05)" in style

    def test_speed_is_applied_by_the_bootstrap(self):
        html = apply_hero_video(PAGE, build_settings(video_url=RAW, speed=1.5)).html
        assert "data-binaapp-speed" in html and "v.playbackRate=sp" in html

    def test_unknown_effect_and_bad_speed_fall_back(self):
        s = build_settings(video_url=RAW, speed="fast", effect="<script>")
        assert s.speed == DEFAULT_SPEED and s.effect == DEFAULT_EFFECT
        assert clamp_speed(0) == DEFAULT_SPEED and clamp_speed(-2) == DEFAULT_SPEED
        assert clamp_speed(9) == 2.0 and clamp_speed(0.1) == 0.25
        assert clean_effect(" WARM ") == "warm"

    def test_every_effect_applies_and_removes_cleanly(self):
        for key in VIDEO_EFFECTS:
            html = apply_hero_video(PAGE, build_settings(video_url=RAW, effect=key, speed=0.75)).html
            assert detect_hero_video(html)["effect"] == key
            assert remove_hero_video(html).html == PAGE


class TestDownloadUrl:
    def test_adds_the_attachment_flag_to_the_delivery_transform(self):
        assert hero_video_download_url(CLOUD_VIDEO) == (
            "https://res.cloudinary.com/demo/video/upload/"
            "fl_attachment,q_auto:good,w_1920,c_limit,ac_none/v1/binaapp/hero-videos/ws-1-ab.mp4"
        )

    def test_raw_asset_gets_its_own_segment(self):
        assert hero_video_download_url(RAW) == (
            "https://res.cloudinary.com/demo/video/upload/fl_attachment/v1/binaapp/hero-videos/ws-1-ab.mp4"
        )

    def test_idempotent_and_leaves_foreign_urls_alone(self):
        once = hero_video_download_url(CLOUD_VIDEO)
        assert hero_video_download_url(once) == once
        assert hero_video_download_url("https://cdn.example.com/a.mp4") == "https://cdn.example.com/a.mp4"
        assert hero_video_download_url(None) is None


# ---------------------------------------------------------------------------
# Service: aspect, social prompt, purpose
# ---------------------------------------------------------------------------

class TestAspect:
    def test_clean_aspect(self):
        assert clean_aspect("9:16") == ASPECT_SOCIAL
        assert clean_aspect("1:1") == ASPECT_HERO and clean_aspect(None) == ASPECT_HERO

    def test_social_prompt_uses_the_vertical_suffix(self):
        p = build_hero_video_prompt(business_name="Kedai Ali", custom_prompt="asap naik", aspect=ASPECT_SOCIAL)
        assert p.startswith("asap naik. ")
        assert "vertical 9:16" in p and "website hero" not in p and len(p) <= 512

    def test_hero_prompt_is_unchanged(self):
        p = build_hero_video_prompt(business_name="Kedai Ali")
        assert p.endswith("16:9.") and "vertical" not in p

    @pytest.mark.asyncio
    async def test_dashscope_social_clip_asks_for_a_tall_ratio(self, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "k")
        monkeypatch.setenv("HERO_VIDEO_PROVIDER", "dashscope")
        client, calls = fake_client(post_response=FakeResponse(200, {"output": {"task_id": "t1", "task_status": "PENDING"}}))
        monkeypatch.setattr(svc.httpx, "AsyncClient", client)
        service = svc.ZaiVideoService()
        assert await service.submit("p", aspect=ASPECT_SOCIAL) == "t1"
        assert calls["post"][0]["json"]["parameters"]["ratio"] == "9:16"
        # And a hero clip keeps the operator's landscape default.
        await service.submit("p")
        assert calls["post"][1]["json"]["parameters"]["ratio"] == "16:9"

    @pytest.mark.asyncio
    async def test_zai_social_clip_uses_the_portrait_size(self, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "k")
        monkeypatch.setenv("HERO_VIDEO_PROVIDER", "zai")
        client, calls = fake_client(post_response=FakeResponse(200, {"id": "z1", "task_status": "PROCESSING"}))
        monkeypatch.setattr(svc.httpx, "AsyncClient", client)
        service = svc.ZaiVideoService()
        await service.submit("p", aspect=ASPECT_SOCIAL)
        assert calls["post"][0]["json"]["size"] == "720x1280"


class TestPurpose:
    def test_register_job_records_the_purpose_in_settings(self):
        job = svc.zai_video_service.register_job(
            task_id="t", website_id="", user_id="u", prompt="p", settings={"overlay": "auto"},
            purpose=PURPOSE_SOCIAL,
        )
        assert job.purpose == PURPOSE_SOCIAL and job.settings["purpose"] == PURPOSE_SOCIAL
        assert job.to_dict()["purpose"] == PURPOSE_SOCIAL
        assert purpose_of(job.settings) == PURPOSE_SOCIAL
        assert purpose_of({}) == "hero" and purpose_of({"purpose": "weird"}) == "hero"

    def test_a_hero_job_adds_nothing_to_its_settings(self):
        job = svc.zai_video_service.register_job(
            task_id="t", website_id="ws", user_id="u", prompt="p", settings={"overlay": "auto"}
        )
        assert "purpose" not in job.settings and job.purpose == "hero"


# ---------------------------------------------------------------------------
# Ideas
# ---------------------------------------------------------------------------

class TestIdeas:
    def test_food_ideas_lead_with_food(self):
        ideas = ideas_for("restaurant")
        assert ideas and ideas[0]["key"].startswith("food-")
        assert {"key", "ms", "en"} <= set(ideas[0])

    def test_unknown_type_gets_general_ideas(self):
        assert all(i["key"].startswith("gen-") for i in ideas_for("zzz"))
        assert ideas_for("", limit=2) == ideas_for("general", limit=2)

    def test_endpoint_is_public_and_static(self, client, patches):
        body = client.get("/api/v1/websites/hero-video/ideas?business_type=bakery&limit=3").json()
        assert body["success"] and len(body["ideas"]) == 3
        assert body["ideas"][0]["key"].startswith("bakery-")

    def test_endpoint_is_gated(self, client, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_ENABLED", "false")
        assert client.get("/api/v1/websites/hero-video/ideas").status_code == 404


# ---------------------------------------------------------------------------
# API: options, PATCH, state
# ---------------------------------------------------------------------------

class TestOptionsAndPatch:
    def test_options_list_the_new_controls(self, client):
        body = client.get("/api/v1/websites/hero-video/options").json()
        assert body["speeds"] == [0.5, 0.75, 1.0, 1.25, 1.5]
        assert [e["key"] for e in body["effects"]][:2] == ["none", "warm"]
        assert body["aspects"] == ["16:9", "9:16"]

    def test_patch_speed_and_effect_is_credit_free(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        resp = client.patch(
            "/api/v1/websites/ws-1/hero-video",
            json={"speed": 0.5, "effect": "vintage"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["changed"] and body["settings"]["speed"] == 0.5 and body["settings"]["effect"] == "vintage"
        assert body["settings"]["overlay"] == "dark"  # the rest of the look is kept
        html = _published_html(patches)
        assert 'data-binaapp-speed="0.5"' in html and 'data-binaapp-effect="vintage"' in html
        assert html.count(BLOCK_START) == 1
        patches["submit"].assert_not_called()

    def test_patch_rejects_an_out_of_range_speed(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        assert client.patch("/api/v1/websites/ws-1/hero-video", json={"speed": 5}, headers=auth_headers).status_code == 422

    def test_generate_remembers_speed_and_effect_for_the_landing(self, client, auth_headers, patches):
        resp = client.post(
            "/api/v1/websites/ws-1/hero-video/generate",
            json={"speed": 0.75, "effect": "cool"},
            headers=auth_headers,
        )
        assert resp.status_code == 202
        job = svc.zai_video_service.get_job(resp.json()["job_id"])
        assert job.settings["speed"] == 0.75 and job.settings["effect"] == "cool"
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://zai/clip.mp4", "cover_image_url": None, "raw_status": "SUCCEEDED",
        }
        body = _drive_to_done(client, auth_headers, job.job_id).json()
        assert body["status"] == "completed"
        assert 'data-binaapp-effect="cool"' in body["html_content"]
        assert 'data-binaapp-speed="0.75"' in body["html_content"]

    def test_state_carries_a_download_link_and_business_type(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        body = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers).json()
        assert body["download_url"] == hero_video_download_url(CLOUD_VIDEO)
        assert "fl_attachment" in body["download_url"]
        assert body["business_type"] == "restaurant"
        assert body["settings"]["speed"] == 1.0 and body["settings"]["effect"] == "none"

    def test_state_without_video_has_no_download_link(self, client, auth_headers, patches):
        body = client.get("/api/v1/websites/ws-1/hero-video", headers=auth_headers).json()
        assert body["download_url"] is None


# ---------------------------------------------------------------------------
# API: library and apply
# ---------------------------------------------------------------------------

OTHER_VIDEO = "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-9-cd.mp4"
OTHER_POSTER = "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-9-cd.jpg"


def _ledger_row(**over):
    row = {
        "job_id": "job-lib-1",
        "user_id": "test-user-id-12345",
        "website_id": "ws-9",
        "status": "completed",
        "prompt": "asap naik dari wok. warm light.",
        "video_url": OTHER_VIDEO,
        "poster_url": OTHER_POSTER,
        "settings": {"overlay": "auto", "poster_luminance": 0.2},
        "created_at": "2026-09-17T10:00:00+00:00",
    }
    row.update(over)
    return row


@pytest.fixture
def library(patches, monkeypatch):
    load_stored = AsyncMock(return_value=[])
    monkeypatch.setattr(ep.ledger, "load_stored_for_user", load_stored)
    return load_stored


class TestLibrary:
    def test_lists_stored_clips_newest_first_with_download_links(self, client, auth_headers, patches, library):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        library.return_value = [
            _ledger_row(),
            _ledger_row(job_id="job-cur", video_url=CLOUD_VIDEO, poster_url=CLOUD_POSTER, website_id="ws-1"),
            _ledger_row(job_id="job-soc", settings={"purpose": "social"}),
            _ledger_row(job_id="job-bad", video_url="http://insecure/x.mp4"),
            _ledger_row(job_id="job-none", video_url=None),
        ]
        body = client.get("/api/v1/websites/ws-1/hero-video/library", headers=auth_headers).json()
        assert body["count"] == 3
        by_id = {c["job_id"]: c for c in body["clips"]}
        assert by_id["job-lib-1"]["can_apply"] and not by_id["job-lib-1"]["is_current"]
        assert "fl_attachment" in by_id["job-lib-1"]["download_url"]
        # The raw stored URL is normalised to the delivery URL for embedding.
        assert by_id["job-lib-1"]["video_url"].startswith("https://res.cloudinary.com/demo/video/upload/q_auto")
        assert by_id["job-cur"]["is_current"] is True
        assert by_id["job-soc"]["purpose"] == "social" and by_id["job-soc"]["aspect"] == "9:16"
        assert by_id["job-soc"]["can_apply"] is False

    def test_library_requires_ownership(self, client, auth_headers, patches, library):
        patches["get_website"].return_value = _row(user_id="someone-else")
        assert client.get("/api/v1/websites/ws-1/hero-video/library", headers=auth_headers).status_code in (403, 404)

    def test_apply_puts_a_library_clip_on_the_hero_credit_free(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        patches["ledger_load"].return_value = _ledger_row()
        resp = client.post(
            "/api/v1/websites/ws-1/hero-video/apply",
            json={"job_id": "job-lib-1", "effect": "warm"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["changed"] and body["live_site_updated"]
        settings = body["settings"]
        assert settings["video_url"].endswith("ws-9-cd.mp4") and settings["poster_url"] == OTHER_POSTER
        assert settings["effect"] == "warm"
        assert settings["overlay"] == "dark"  # the look already on the page is kept
        assert settings["poster_luminance"] == 0.2  # measured when the clip was stored
        html = _published_html(patches)
        assert html.count(BLOCK_START) == 1 and "ws-9-cd.mp4" in html and "ws-1-ab.mp4" not in html
        patches["submit"].assert_not_called()
        patches["use_credit"].assert_not_called()
        patches["store"].assert_not_called()
        # The websites row records the swap.
        row_payload = patches["update_website"].call_args_list[0].args[1]
        assert row_payload["hero_video_url"].endswith("ws-9-cd.mp4")

    def test_apply_on_a_page_without_a_video_uses_the_body_look(self, client, auth_headers, patches):
        patches["ledger_load"].return_value = _ledger_row()
        resp = client.post(
            "/api/v1/websites/ws-1/hero-video/apply",
            json={"job_id": "job-lib-1", "overlay": "light", "speed": 0.5},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["settings"]["overlay"] == "light" and resp.json()["settings"]["speed"] == 0.5

    def test_apply_refuses_another_users_clip(self, client, auth_headers, patches):
        patches["ledger_load"].return_value = _ledger_row(user_id="someone-else")
        resp = client.post("/api/v1/websites/ws-1/hero-video/apply", json={"job_id": "job-lib-1"}, headers=auth_headers)
        assert resp.status_code == 404 and resp.json()["detail"]["error"] == "clip_not_found"
        patches["publish_website"].assert_not_called()

    def test_apply_refuses_a_social_clip(self, client, auth_headers, patches):
        patches["ledger_load"].return_value = _ledger_row(settings={"purpose": "social"})
        resp = client.post("/api/v1/websites/ws-1/hero-video/apply", json={"job_id": "job-lib-1"}, headers=auth_headers)
        assert resp.status_code == 422 and resp.json()["detail"]["error"] == "clip_not_for_hero"

    def test_apply_of_the_current_clip_is_a_noop(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content=WITH_VIDEO_HTML)
        patches["ledger_load"].return_value = _ledger_row(
            video_url=CLOUD_VIDEO, poster_url=CLOUD_POSTER, settings={"overlay": "dark"},
        )
        body = client.post("/api/v1/websites/ws-1/hero-video/apply", json={"job_id": "job-lib-1"}, headers=auth_headers).json()
        assert body["changed"] is False
        patches["publish_website"].assert_not_called()

    def test_apply_needs_a_hero(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(html_content="<html><head></head><body><p>hi</p></body></html>")
        patches["ledger_load"].return_value = _ledger_row()
        resp = client.post("/api/v1/websites/ws-1/hero-video/apply", json={"job_id": "job-lib-1"}, headers=auth_headers)
        assert resp.status_code == 422 and resp.json()["detail"]["error"] == "hero_not_found"


# ---------------------------------------------------------------------------
# API: social clip
# ---------------------------------------------------------------------------

def _start_social(client, auth_headers, body=None):
    resp = client.post("/api/v1/websites/hero-video/social", json=body or {}, headers=auth_headers)
    assert resp.status_code == 202, resp.text
    return resp.json()


class TestSocialClip:
    def test_starts_a_vertical_job_with_the_sites_context(self, client, auth_headers, patches):
        body = _start_social(client, auth_headers, {"website_id": "ws-1", "style": "energetic", "prompt": "sate dibakar"})
        assert body["purpose"] == "social" and body["aspect"] == "9:16"
        assert body["prompt"].startswith("sate dibakar. ") and "vertical 9:16" in body["prompt"]
        assert "vibrant lively" in body["prompt"]  # the preset's tone
        assert patches["submit"].call_args.kwargs["aspect"] == "9:16"
        job = svc.zai_video_service.get_job(body["job_id"])
        assert job.purpose == "social" and job.website_id == "" and job.settings["purpose"] == "social"
        patches["ledger_create"].assert_called_once()

    def test_works_without_a_site(self, client, auth_headers, patches):
        body = _start_social(client, auth_headers, {"business_name": "Warung Mak", "business_type": "food"})
        assert "Warung Mak" in body["prompt"] and "vertical 9:16" in body["prompt"]
        patches["get_website"].assert_not_called()

    def test_completes_on_storage_and_never_touches_a_page(self, client, auth_headers, patches):
        job_id = _start_social(client, auth_headers, {"website_id": "ws-1"})["job_id"]
        patches["fetch_result"].return_value = {
            "status": "success", "video_url": "https://zai/tall.mp4", "cover_image_url": None, "raw_status": "SUCCEEDED",
        }
        resp = client.get(f"/api/v1/websites/hero-video/jobs/{job_id}", headers=auth_headers)
        assert resp.json()["status"] == "processing"
        # Drive it like the server does.
        from tests.test_hero_video_api import _drive_once
        for _ in range(5):
            job = _drive_once(job_id)
            if job.status not in ("processing", "storing"):
                break
        assert job.status == "completed" and job.applied is False
        # The purpose survives the store step into the ledger row, so a
        # restart (and the library) still know this clip is tall.
        from app.services.hero_video_jobs import row_from_job
        assert job.settings["purpose"] == "social"
        assert row_from_job(job)["settings"]["purpose"] == "social"
        patches["luminance"].assert_not_called()
        body = client.get(f"/api/v1/websites/hero-video/jobs/{job_id}", headers=auth_headers).json()
        assert body["status"] == "completed" and body["purpose"] == "social"
        assert body["video_url"] == CLOUD_VIDEO and body["aspect"] == "9:16"
        assert body["download_url"] == hero_video_download_url(CLOUD_VIDEO)
        assert "html_content" not in body
        # Stored under the job's own id, no page written, no site published.
        assert patches["store"].call_args.kwargs["website_id"] == job_id
        patches["publish_website"].assert_not_called()
        patches["update_website"].assert_not_called()
        # It is not an active job for the site, so a hero clip can start.
        assert svc.zai_video_service.active_job_for_website("ws-1") is None

    def test_is_paid_like_a_hero_clip(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=1)
        job_id = _start_social(client, auth_headers)["job_id"]
        patches["use_credit"].assert_called_once()
        assert svc.zai_video_service.get_job(job_id).charged is True

    def test_plan_gate_blocks_before_spending(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=0)
        resp = client.post("/api/v1/websites/hero-video/social", json={}, headers=auth_headers)
        assert resp.status_code == 402
        patches["submit"].assert_not_called()

    def test_failed_generation_refunds(self, client, auth_headers, patches):
        patches["plan_gate"].return_value = _access(free=False, credits=1)
        job_id = _start_social(client, auth_headers)["job_id"]
        patches["fetch_result"].return_value = {"status": "fail", "video_url": None, "cover_image_url": None, "raw_status": "FAILED"}
        from tests.test_hero_video_api import _drive_once
        job = _drive_once(job_id)
        assert job.status == "failed" and job.refunded is True
        patches["refund_credit"].assert_called_once()

    def test_a_resumed_stored_social_job_completes_instead_of_parking(self, patches):
        from datetime import datetime, timezone

        from app.services import hero_video_jobs as ledger
        row = _ledger_row(
            job_id="job-resume", status="storing", website_id="", settings={"purpose": "social"},
            # Minutes old, not a day: a completed job older than the registry
            # TTL is swept on the next read, which is right but not this test.
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        job = ledger.job_from_row(row)
        assert job.purpose == "social"
        import asyncio as _a

        async def _adopt():
            job_id = ep._adopt_row(row)
            adopted = svc.zai_video_service.get_job(job_id)
            if adopted.finalize_task is not None:
                await adopted.finalize_task
            return adopted

        adopted = _a.run(_adopt())
        assert adopted.status == "completed" and adopted.result_payload["aspect"] == "9:16"
        assert adopted.result_payload["download_url"].startswith("https://res.cloudinary.com/")
