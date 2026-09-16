"""Round 6 (mimk.binaapp.my — Barbershop Abang Din, 2026-09-16).

Four failures on one hero, each with its own cause:

1. A finished clip never reached the page. Job 14d4c4f1 SUCCEEDED at the
   provider, was stored on Cloudinary with its poster, and sat at
   ``ready``/``applied=false`` for the rest of the day. It was PREPARED —
   made before the site existed — and the only thing that could ever move
   it on was a publish holding its job id in the browser's memory and in
   the registry of the instance that made it. The merchant paid, came back
   41 minutes later and published; the id was gone with the page reload,
   the site went live static, and the create page generated a SECOND clip.

2. ``auto`` chose a light scrim on a dark hero. The page writes its colours
   in a ``<style>`` block (``h1 { color: var(--text-color) }``), which the
   tone reader could not see, so the most explicit hero on the page read as
   "no opinion" and a muted paragraph decided it.

3. The mood suffix argued with the merchant's own motion text.

4. The clip was delivered at ``q_auto:eco,w_1280``.

5. The clip went full-bleed instead of into the hero's media column,
   because the ``<img>`` was five levels down and the walk looked two.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.endpoints import hero_video as ep
from app.services import zai_video_service as svc
from app.services.hero_video_patcher import (
    BLOCK_START,
    HERO_MEDIA_ATTR,
    STYLE_ID,
    apply_hero_video,
    build_settings,
    detect_hero_tone,
    find_hero_media,
    find_hero_open_tag,
    hero_copy_tone,
    remove_hero_video,
)

from tests.test_hero_video_api import CLOUD_POSTER, CLOUD_VIDEO, LIVE_HTML, _row

enabled = pytest.importorskip("tests.test_hero_video_api").enabled
patches = pytest.importorskip("tests.test_hero_video_api").patches

USER = "test-user-id-12345"


@pytest.fixture
def loglines():
    """Capture loguru output as '<LEVEL> <message>' lines."""
    from loguru import logger

    lines = []
    sink = logger.add(
        lambda m: lines.append(f"{m.record['level'].name} {m.record['message']}"),
        level="DEBUG",
    )
    try:
        yield lines
    finally:
        logger.remove(sink)


# ---------------------------------------------------------------------------
# The page, as mimk actually shipped it
# ---------------------------------------------------------------------------

#: A dark page whose colours live in a stylesheet, and a split hero whose
#: photo is two wrappers below the column. Nothing here is inline and
#: nothing carries a Tailwind colour class — which is the whole point.
MIMK = (
    "<!DOCTYPE html><html><head><style>"
    ":root{--bg-color:#141518;--text-color:#F5F3EE;--text-muted-color:#9A948B}"
    "body{background-color:var(--bg-color);color:var(--text-color)}"
    "h1{color:var(--text-color)}"
    "p,li{color:var(--text-muted-color)}"
    "</style></head><body>"
    '<section class="pt-32 md:pt-40 pb-16" id="hero">'
    '<div class="max-w-7xl mx-auto px-4">'
    '<div class="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">'
    '<div class="order-2 md:order-1">'
    '<h1 class="text-4xl leading-[1.05] mb-6">Fade, Gunting Klasik</h1>'
    '<p class="text-lg text-[#9A948B] mb-8">Barbershop lelaki di Seksyen 24.</p>'
    "</div>"
    '<div class="order-1 md:order-2 relative">'
    '<div class="hero-photo-anim relative rounded-2xl overflow-hidden shadow-2xl">'
    '<img class="w-full aspect-[16/9] object-cover" src="https://res.cloudinary.com/d/image/upload/v1/binaapp/user_uploads/a2bc44d4.jpg" alt="dalam kedai">'
    "</div>"
    '<div class="absolute bottom-4 right-4 flex flex-col gap-2 items-end z-10">'
    '<span class="badge-pill">Walk-in Welcome</span>'
    '<span class="badge-pill">Buka 11 pagi</span>'
    "</div></div></div></div></section>"
    '<section id="servis"><h2>Servis</h2></section></body></html>'
)

#: What the clip measured: a dark barbershop interior.
DARK_CLIP = 0.264


def _settings(**kw):
    base = {
        "video_url": CLOUD_VIDEO,
        "poster_url": "https://res.cloudinary.com/d/image/upload/v1/binaapp/user_uploads/a2bc44d4.jpg",
        "poster_luminance": DARK_CLIP,
    }
    base.update(kw)
    return build_settings(**base)


def _style(html):
    i = html.index(f'<style id="{STYLE_ID}">')
    return html[i:html.index("</style>", i)]


# ---------------------------------------------------------------------------
# 2. The scrim
# ---------------------------------------------------------------------------

class TestTheHeroIsReadFromItsOwnStylesheet:
    def test_the_headline_colour_is_seen_even_though_it_is_in_a_style_block(self):
        # `h1 { color: var(--text-color) }` -> #F5F3EE -> light copy -> dark hero.
        assert hero_copy_tone(MIMK) == "light"
        assert detect_hero_tone(MIMK) == "dark"

    def test_a_muted_paragraph_no_longer_speaks_for_the_headline(self):
        # #9A948B is a mid grey that reads "dark" by luminance alone. It used
        # to be the ONLY copy with a readable colour, so it decided the hero.
        assert "#9A948B" in MIMK
        assert detect_hero_tone(MIMK) == "dark"

    def test_the_scrim_is_dark_and_no_white_is_painted(self):
        settings = _settings()
        assert settings.resolved_overlay(MIMK) == "dark"
        assert "rgba(255,255,255," not in _style(apply_hero_video(MIMK, settings).html)

    def test_the_near_white_copy_is_left_alone(self):
        assert _settings().resolved_text_mode(MIMK) == "keep"

    def test_a_page_that_inherits_its_copy_colour_from_body_still_reads(self):
        # Nothing in the hero states a colour — no class, no inline style, no
        # rule for h1 or p. `body { color: var(--text-color) }` is what the
        # copy actually renders in, so it is what the hero is read from.
        page = (
            MIMK.replace("h1{color:var(--text-color)}", "")
            .replace("p,li{color:var(--text-muted-color)}", "")
            .replace(" text-[#9A948B]", "")
        )
        assert hero_copy_tone(page) == "light"
        assert detect_hero_tone(page) == "dark"

    def test_the_headline_outranks_a_muted_paragraph(self):
        # The order matters: p/li are muted by design on both dark and light
        # pages, and #9A948B is a mid grey that only just reads as dark. The
        # headline is the signal; the paragraph is the fallback.
        assert hero_copy_tone(MIMK) == "light"
        assert detect_hero_tone(MIMK.replace("h1{color:var(--text-color)}", "")) == "light"


class TestTheClipsOwnLuminance:
    PLAIN = (
        "<html><head></head><body>"
        '<section id="home"><div><h1>Kedai</h1></div></section></body></html>"'
    )

    def test_a_dark_clip_decides_when_nothing_else_does(self):
        assert _settings(poster_luminance=0.2).clip_tone() == "dark"
        assert _settings(poster_luminance=0.2).resolved_overlay(self.PLAIN) == "dark"

    def test_a_bright_clip_decides_the_other_way(self):
        assert _settings(poster_luminance=0.85).resolved_overlay(self.PLAIN) == "light"

    def test_a_mid_tone_clip_states_nothing(self):
        assert _settings(poster_luminance=0.5).clip_tone() == ""
        assert _settings(poster_luminance=None).clip_tone() == ""

    def test_the_page_still_outranks_the_clip(self):
        # A dark clip on a genuinely light page keeps the light scrim: that
        # is what makes the page's dark copy readable over the footage.
        light = (
            "<html><head><style>:root{--bg-color:#FFFFFF}"
            "body{color:#1C1917}</style></head><body>"
            '<section id="home"><div><h1>Kedai</h1></div></section></body></html>'
        )
        assert _settings(poster_luminance=0.2).resolved_overlay(light) == "light"


class TestTheScrimNeverHidesTheCopy:
    def test_a_light_scrim_under_light_copy_is_refused(self):
        settings = _settings(overlay="auto")
        # Force the contradiction: the hero's backdrop says light, its copy
        # says light too (the shape that shipped a white veil under white text).
        page = MIMK.replace("h1{color:var(--text-color)}", "h1{color:#F5F3EE}").replace(
            '<section class="pt-32 md:pt-40 pb-16" id="hero">',
            '<section class="pt-32 bg-white" id="hero">',
        )
        assert hero_copy_tone(page) == "light"
        assert settings.resolved_overlay(page) in ("dark", "none")
        assert settings.resolved_overlay(page) != "light"

    def test_an_explicit_choice_is_still_the_merchants_to_make(self):
        # Only `auto` is second-guessed.
        page = MIMK
        assert _settings(overlay="light").resolved_overlay(page) == "light"


# ---------------------------------------------------------------------------
# 5. The media column
# ---------------------------------------------------------------------------

class TestTheClipLandsInTheMediaColumn:
    def _found(self):
        match, _how = find_hero_open_tag(MIMK)
        return find_hero_media(MIMK, match.start())

    def test_media_five_levels_down_is_found(self):
        found = self._found()
        assert len(found) == 1

    def test_the_frame_around_the_photo_is_the_host(self):
        _start, _end, host = self._found()[0]
        assert host is not None
        assert MIMK[host[0]:].startswith('<div class="hero-photo-anim')

    def test_the_layer_is_injected_into_that_frame(self):
        result = apply_hero_video(MIMK, _settings())
        assert "layer_hosted_in_media_column" in result.notes
        frame = result.html.index('class="hero-photo-anim')
        layer = result.html.index(BLOCK_START)  # the injected markup, not the CSS
        headline = result.html.index("<h1")
        assert headline < frame < layer

    def test_the_photo_keeps_its_box_so_the_frame_keeps_its_height(self):
        html = apply_hero_video(MIMK, _settings()).html
        assert f'{HERO_MEDIA_ATTR}="replaced-hosted"' in html
        style = _style(html)
        assert f'[{HERO_MEDIA_ATTR}="replaced-hosted"]{{visibility:hidden !important;}}' in style

    def test_the_poster_url_net_does_not_hide_the_hosted_photo(self):
        # The merchant uploaded this photo, so it is ALSO the poster. The
        # URL net used to hide it outright, collapsing the frame.
        style = _style(apply_hero_video(MIMK, _settings()).html)
        assert 'img[src="' in style
        assert f'img[src="https://res.cloudinary.com/d/image/upload/v1/binaapp/user_uploads/a2bc44d4.jpg"]:not([{HERO_MEDIA_ATTR}])' in style

    def test_a_deep_picture_with_no_media_wrapper_is_left_alone(self):
        # A collage inside the layout is content, not the hero's backdrop.
        # Claiming it would hide it and paint a full-bleed clip in its place.
        collage = MIMK.replace(
            '<div class="hero-photo-anim relative rounded-2xl overflow-hidden shadow-2xl">',
            '<div class="grid grid-cols-2 gap-2"><p>Galeri</p>',
        )
        match, _how = find_hero_open_tag(collage)
        assert find_hero_media(collage, match.start()) == []
        result = apply_hero_video(collage, _settings())
        assert "layer_hosted_in_media_column" not in result.notes
        # Nothing in the body is stamped (the CSS always declares the rules).
        body = result.html[result.html.index("<body"):]
        assert HERO_MEDIA_ATTR not in body
        assert "Galeri" in body and "a2bc44d4.jpg" in body

    def test_the_badges_over_the_photo_are_untouched(self):
        html = apply_hero_video(MIMK, _settings()).html
        assert "Walk-in Welcome" in html and "Buka 11 pagi" in html

    def test_remove_restores_the_exact_original_bytes(self):
        assert remove_hero_video(apply_hero_video(MIMK, _settings()).html).html == MIMK

    def test_idempotent(self):
        once = apply_hero_video(MIMK, _settings()).html
        assert apply_hero_video(once, _settings()).html == once


# ---------------------------------------------------------------------------
# 1. A ready clip always reaches a page
# ---------------------------------------------------------------------------

def _ready_row(job_id="ready-1", website_id="", minutes_ago=45, user_id=USER):
    started = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return {
        "job_id": job_id,
        "task_id": "task-9",
        "provider": "dashscope",
        "website_id": website_id,
        "user_id": user_id,
        "status": "ready",
        "error": None,
        "provider_status": "SUCCEEDED",
        "prompt": "p",
        "settings": ep.HeroVideoLook().model_dump(),
        "video_url": CLOUD_VIDEO,
        "poster_url": CLOUD_POSTER,
        "charged": True,
        "refunded": False,
        "applied": False,
        "live_site_updated": False,
        "poll_errors": 0,
        "created_at": started.isoformat(),
        "updated_at": started.isoformat(),
        "lease_owner": None,
        "lease_until": None,
    }


class TestAPublishFindsItsPreparedClip:
    async def test_a_job_id_this_process_never_saw_is_claimed_from_the_ledger(self, patches):
        row = _ready_row()
        patches["ledger_load"].return_value = row
        resolved = await ep.resolve_prepared_hero_video("ready-1", USER)
        assert resolved == "ready-1"
        job = svc.zai_video_service.get_job("ready-1")
        assert job is not None and job.status == svc.JOB_STATUS_READY
        assert job.video_url == CLOUD_VIDEO

    async def test_a_publish_with_no_job_id_still_claims_the_merchants_clip(self, patches):
        # The create page lost the id across a payment redirect.
        patches["ledger_ready_for_user"].return_value = [_ready_row("orphan-1")]
        resolved = await ep.resolve_prepared_hero_video(None, USER)
        assert resolved == "orphan-1"
        assert svc.zai_video_service.get_job("orphan-1") is not None

    async def test_another_merchants_clip_is_never_claimed(self, patches):
        patches["ledger_load"].return_value = _ready_row(user_id="someone-else")
        patches["ledger_ready_for_user"].return_value = []
        assert await ep.resolve_prepared_hero_video("ready-1", USER) is None

    async def test_a_clip_already_attached_to_a_site_is_left_alone(self, patches):
        patches["ledger_ready_for_user"].return_value = [_ready_row(website_id="ws-other")]
        assert await ep.resolve_prepared_hero_video(None, USER) is None

    async def test_a_finished_job_id_claims_nothing(self, patches):
        row = _ready_row()
        row.update(status="failed", error="timeout")
        patches["ledger_load"].return_value = row
        patches["ledger_ready_for_user"].return_value = []
        assert await ep.resolve_prepared_hero_video("ready-1", USER) is None

    async def test_the_window_can_be_closed(self, patches, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_ADOPT_WINDOW_SECONDS", "0")
        patches["ledger_ready_for_user"].return_value = [_ready_row("orphan-1")]
        assert await ep.resolve_prepared_hero_video(None, USER) is None


class TestTheSweepRehomesAReadyClip:
    async def test_an_unclaimed_clip_is_applied_to_the_site_that_followed_it(self, patches):
        patches["ledger_ready_unapplied"].return_value = [_ready_row("orphan-2")]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value="ws-1")):
            result = await ep.rehome_ready_hero_video_jobs()
        assert result["applied"] == ["orphan-2"]
        job = svc.zai_video_service.get_job("orphan-2")
        assert job.applied is True and job.status == svc.JOB_STATUS_COMPLETED
        assert job.website_id == "ws-1"
        # The page the merchant is serving now carries the clip.
        patches["publish_website"].assert_awaited()

    async def test_the_ledger_row_is_closed_with_finished_at(self, patches):
        patches["ledger_ready_unapplied"].return_value = [_ready_row("orphan-3")]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value="ws-1")):
            await ep.rehome_ready_hero_video_jobs()
        saved = [c.args[0] for c in patches["ledger_save"].await_args_list]
        final = [j for j in saved if j.job_id == "orphan-3"][-1]
        row = ep.ledger.row_from_job(final)
        assert row["status"] == "completed" and row["applied"] is True
        assert row["finished_at"] is not None

    async def test_a_clip_with_no_site_to_go_to_is_left_for_the_claim_window(self, patches):
        patches["ledger_ready_unapplied"].return_value = [_ready_row("orphan-4")]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value=None)):
            result = await ep.rehome_ready_hero_video_jobs()
        assert result["applied"] == [] and result["no_site"] == 1
        assert result["expired"] == []
        assert svc.zai_video_service.get_job("orphan-4") is None

    async def test_a_row_another_process_is_driving_is_not_stolen(self, patches):
        row = _ready_row("orphan-5")
        row["lease_owner"] = "another-process"
        row["lease_until"] = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        patches["ledger_ready_unapplied"].return_value = [row]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value="ws-1")):
            result = await ep.rehome_ready_hero_video_jobs()
        assert result["applied"] == []

    async def test_the_stuck_sweep_runs_it(self, patches):
        patches["ledger_ready_unapplied"].return_value = [_ready_row("orphan-6")]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value="ws-1")):
            result = await ep.sweep_stuck_hero_video_jobs()
        assert result["rehomed"] == ["orphan-6"]


# ---------------------------------------------------------------------------
# Polling cost: a poll that changes nothing does not rewrite the row
# ---------------------------------------------------------------------------

class TestTheLedgerIsNotRewrittenOnEveryPoll:
    async def test_an_unchanged_poll_only_renews_the_lease_when_it_is_due(self, patches, test_user_id):
        patches["fetch_result"].return_value = {
            "status": "processing", "video_url": None, "cover_image_url": None,
            "raw_status": "PENDING",
        }
        job = svc.zai_video_service.register_job(
            task_id="task-1", website_id="ws-1", user_id=test_user_id, prompt="p",
            settings=ep.HeroVideoLook().model_dump(), provider="dashscope",
        )
        # First poll: PENDING is new, and the lease has never been written.
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert patches["ledger_save"].await_count == 1
        # Next polls say the same thing inside the renewal window.
        for _ in range(5):
            await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert patches["ledger_save"].await_count == 1
        # Once half the lease has gone, the row is written to keep it.
        job.last_ledger_save -= ep.ledger.lease_seconds_for(job.status)
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert patches["ledger_save"].await_count == 2

    async def test_a_state_change_always_writes(self, patches, test_user_id):
        patches["fetch_result"].return_value = {
            "status": "processing", "video_url": None, "cover_image_url": None,
            "raw_status": "PENDING",
        }
        job = svc.zai_video_service.register_job(
            task_id="task-1", website_id="ws-1", user_id=test_user_id, prompt="p",
            settings=ep.HeroVideoLook().model_dump(), provider="dashscope",
        )
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        before = patches["ledger_save"].await_count
        patches["fetch_result"].return_value = {
            "status": "processing", "video_url": None, "cover_image_url": None,
            "raw_status": "RUNNING",
        }
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert patches["ledger_save"].await_count == before + 1
        assert job.provider_status == "RUNNING"


# ---------------------------------------------------------------------------
# A ready clip is never silently held (round 7 / job 14d4c4f1)
# ---------------------------------------------------------------------------

class TestAStrandedClipIsLoudAndBounded:
    """14d4c4f1 sat at `ready` for 3h43m: lease renewed minutes earlier,
    poll_errors 0, no error, no log line, nothing to distinguish it from a
    healthy job. It was not stuck — a prepared clip waits for the publish
    that will carry it, and that window is a day on purpose — but "waiting"
    and "dead" looked identical, so nobody could tell which it was."""

    async def test_a_clip_with_no_site_is_reported_at_error(self, patches, loglines):
        patches["ledger_ready_unapplied"].return_value = [_ready_row("lonely-1", minutes_ago=200)]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value=None)):
            result = await ep.rehome_ready_hero_video_jobs()
        assert result["stranded"] == ["lonely-1"]
        assert any("HERO_VIDEO_STRANDED" in line and "lonely-1" in line for line in loglines)

    async def test_a_clip_inside_the_grace_is_not_shouted_about(self, patches, loglines):
        patches["ledger_ready_unapplied"].return_value = [_ready_row("young-1", minutes_ago=5)]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value=None)):
            result = await ep.rehome_ready_hero_video_jobs()
        assert result["stranded"] == []
        assert not any("HERO_VIDEO_STRANDED" in line for line in loglines)

    async def test_past_the_claim_window_the_sweep_ends_it(self, patches, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_CLAIM_WINDOW_SECONDS", "3600")
        patches["ledger_ready_unapplied"].return_value = [_ready_row("old-1", minutes_ago=90)]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value=None)):
            result = await ep.rehome_ready_hero_video_jobs()
        assert result["expired"] == ["old-1"]
        # Terminal in the ledger: failed, with the reason, and refunded.
        saved = [c.args[0] for c in patches["ledger_save"].await_args_list]
        final = [j for j in saved if j.job_id == "old-1"][-1]
        assert final.status == svc.JOB_STATUS_FAILED and final.error == "unclaimed"
        row = ep.ledger.row_from_job(final)
        assert row["finished_at"] is not None and row["lease_owner"] is None
        patches["refund_credit"].assert_awaited()

    async def test_a_row_another_process_holds_is_not_ended_here(self, patches, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_CLAIM_WINDOW_SECONDS", "3600")
        row = _ready_row("leased-1", minutes_ago=120)
        row["lease_owner"] = "another-process"
        row["lease_until"] = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        patches["ledger_ready_unapplied"].return_value = [row]
        result = await ep.rehome_ready_hero_video_jobs()
        assert result["expired"] == []

    async def test_a_clip_that_can_be_applied_is_applied_not_expired(self, patches, monkeypatch):
        monkeypatch.setenv("HERO_VIDEO_CLAIM_WINDOW_SECONDS", "36000")
        patches["ledger_ready_unapplied"].return_value = [_ready_row("home-1", minutes_ago=200)]
        with patch.object(ep, "_site_for_prepared_clip", new=AsyncMock(return_value="ws-1")):
            result = await ep.rehome_ready_hero_video_jobs()
        assert result["applied"] == ["home-1"] and result["expired"] == []
