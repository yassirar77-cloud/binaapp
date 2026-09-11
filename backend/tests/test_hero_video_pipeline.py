"""Regression suite for the hero-video pipeline's durability.

Written after 2026-09-11 (website moo / job cc6bc685 / task 74c0563a) and
the seven-day log reconciliation behind it. What it pins, in the order the
task listed them:

  * SUCCEEDED writes the URL — onto the websites row (hero_video_url)
    BEFORE the page is patched, then into the HTML and storage.
  * FAILED marks the job failed (and refunds).
  * Timeout marks the job failed with reason 'timeout', refunds, and
    fires the HERO_VIDEO_TIMEOUT alert (CRITICAL line + admin email).
  * A client that disconnects mid-job still gets its clip: the server
    driver is the only poller and needs no browser.
  * The published HTML carries <video> and the data-binaapp-hero-video
    marker on the hero tag.
  * The poll endpoint never polls the provider (no duplicate polling).
  * The stuck sweep fails overdue jobs regardless of the website's status,
    from the live registry and from the ledger.
  * A restart resumes unfinished jobs from the ledger with their real age.
  * /api/publish busts the served-page cache.
  * The provider's raw task_status is logged on every poll and the full
    body on any non-SUCCEEDED terminal state.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from loguru import logger

from app.api.v1.endpoints import hero_video as ep
from app.services import hero_video_jobs as ledger
from app.services import zai_video_service as svc
from app.services.hero_video_patcher import HERO_MARKER_ATTR

from tests import test_hero_video_api as api_tests
from tests.test_hero_video_api import (
    CLOUD_POSTER,
    CLOUD_VIDEO,
    LIVE_HTML,
    _published_html,
    _row,
    _start_job,
)
from tests.test_zai_video_service import FakeResponse, _ds_task, fake_client

# The endpoint suite's fixtures (feature flag + every external call mocked),
# registered under their own names so the tests below can request them.
enabled = api_tests.enabled
patches = api_tests.patches


@pytest.fixture
def loglines():
    """Capture loguru output as '<LEVEL> <message>' lines."""
    lines = []
    sink = logger.add(lambda m: lines.append(f"{m.record['level'].name} {m.record['message']}"), level="DEBUG")
    try:
        yield lines
    finally:
        logger.remove(sink)


def _job(user_id="test-user-id-12345", website_id="ws-1", **kw):
    return svc.zai_video_service.register_job(
        task_id="task-1", website_id=website_id, user_id=user_id, prompt="p",
        settings=ep.HeroVideoLook().model_dump(), provider="dashscope", **kw,
    )


SUCCESS = {"status": "success", "video_url": "https://cdn.provider/v.mp4", "cover_image_url": None, "raw_status": "SUCCEEDED"}
FAILED = {"status": "fail", "video_url": None, "cover_image_url": None, "raw_status": "FAILED",
          "code": "InternalError.Algo", "message": "generation failed"}


# ---------------------------------------------------------------------------
# 1. SUCCEEDED writes the URL
# ---------------------------------------------------------------------------

class TestSucceededWritesTheUrl:
    async def test_row_is_written_before_the_page(self, patches, test_user_id):
        patches["fetch_result"].return_value = SUCCESS
        job = _job()
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        await job.finalize_task
        assert job.status == "completed" and job.video_url == CLOUD_VIDEO

        writes = [c.args[1] for c in patches["update_website"].await_args_list]
        assert writes[0]["hero_video_url"] == CLOUD_VIDEO
        assert writes[0]["hero_video_poster_url"] == CLOUD_POSTER
        assert writes[0]["hero_video_settings"]["video_url"] == CLOUD_VIDEO
        assert "html_content" not in writes[0]
        assert "html_content" in writes[-1] and CLOUD_VIDEO in writes[-1]["html_content"]
        # Row first, page second: the order is the point.
        assert [("hero_video_url" in w, "html_content" in w) for w in writes] == [(True, False), (False, True)]
        # The ledger saw the terminal state.
        assert patches["ledger_save"].await_args.args[0].status == "completed"

    async def test_row_write_failure_is_loud_not_fatal(self, patches, test_user_id, loglines):
        patches["fetch_result"].return_value = SUCCESS
        patches["update_website"].side_effect = [False, True]  # columns fail, html succeeds
        job = _job()
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        await job.finalize_task
        assert job.status == "completed"
        assert job.result_payload["warning"] == "row_write_failed"
        assert any("hero_video_* write updated no row" in line and line.startswith("ERROR") for line in loglines)


# ---------------------------------------------------------------------------
# 2. FAILED marks failed
# ---------------------------------------------------------------------------

class TestFailedMarksFailed:
    async def test_provider_failure(self, patches, test_user_id, loglines):
        patches["fetch_result"].return_value = FAILED
        job = _job(charged=True)
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "failed" and job.error == "generation_failed"
        assert job.provider_status == "FAILED"
        assert job.provider_message == "InternalError.Algo generation failed"
        assert job.refunded is True
        patches["refund_credit"].assert_awaited_once()
        patches["store"].assert_not_called()
        assert patches["ledger_save"].await_args.args[0].status == "failed"
        assert any(f"job {job.job_id} FAILED error=generation_failed" in line for line in loglines)

    async def test_poll_errors_are_counted_not_fatal(self, patches, test_user_id):
        patches["fetch_result"].side_effect = svc.ZaiVideoError("DashScope video poll failed (403)", status_code=403)
        job = _job()
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "processing"
        assert job.poll_errors == 2 and job.provider_status == "http_403"
        patches["refund_credit"].assert_not_called()
        # The next good poll clears the count.
        patches["fetch_result"].side_effect = None
        patches["fetch_result"].return_value = {**SUCCESS, "status": "processing", "video_url": None, "raw_status": "RUNNING"}
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert job.poll_errors == 0 and job.provider_status == "RUNNING"


# ---------------------------------------------------------------------------
# 3. Timeout marks failed with a reason, and alerts
# ---------------------------------------------------------------------------

class TestTimeout:
    async def test_marks_failed_refunds_and_alerts(self, patches, test_user_id, loglines):
        job = _job(charged=True)
        job.created_at -= svc.zai_video_max_wait_seconds() + 1
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "failed" and job.error == "timeout"
        assert job.refunded is True
        patches["fetch_result"].assert_not_called()
        alert = [line for line in loglines if "HERO_VIDEO_TIMEOUT" in line and line.startswith("CRITICAL")]
        assert len(alert) == 1
        assert f"job={job.job_id}" in alert[0] and "website=ws-1" in alert[0] and "task=task-1" in alert[0]
        patches["admin_email"].assert_awaited_once()
        assert patches["admin_email"].await_args.kwargs["notification_type"] == "error"
        assert patches["admin_email"].await_args.kwargs["details"]["job_id"] == job.job_id

    async def test_alert_email_failure_never_hides_the_line(self, patches, test_user_id, loglines):
        patches["admin_email"].side_effect = RuntimeError("smtp down")
        job = _job()
        job.created_at -= svc.zai_video_max_wait_seconds() + 1
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        assert job.status == "failed" and job.error == "timeout"
        assert any("HERO_VIDEO_TIMEOUT job=" in line and line.startswith("CRITICAL") for line in loglines)
        assert any("admin email raised" in line for line in loglines)

    def test_the_limit_is_ten_minutes_by_default(self, monkeypatch):
        monkeypatch.delenv("ZAI_VIDEO_MAX_WAIT_SECONDS", raising=False)
        assert svc.zai_video_max_wait_seconds() == 600.0

    def test_prepared_clips_wait_a_day_for_their_publish(self):
        assert ep.PREPARED_CLAIM_WINDOW_SECONDS == 24 * 60 * 60


# ---------------------------------------------------------------------------
# 4. Client disconnect mid-job still completes
# ---------------------------------------------------------------------------

class TestClientDisconnect:
    async def test_job_started_over_http_completes_with_no_further_requests(
        self, client, auth_headers, patches, monkeypatch
    ):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        job_id = _start_job(client, auth_headers)  # the browser's only request
        job = svc.zai_video_service.get_job(job_id)
        patches["fetch_result"].side_effect = [
            {**SUCCESS, "status": "processing", "video_url": None, "raw_status": "PENDING"},
            {**SUCCESS, "status": "processing", "video_url": None, "raw_status": "RUNNING"},
            SUCCESS,
        ]
        # Nobody polls. The driver does the job's work on its own.
        await ep._drive_hero_video_job(job, "ws-1", job.user_id)
        await job.finalize_task
        assert job.status == "completed" and job.applied and job.live_site_updated
        assert patches["fetch_result"].await_count == 3
        assert CLOUD_VIDEO in _published_html(patches)

    async def test_driver_survives_an_unexpected_exception(self, patches, test_user_id, monkeypatch, loglines):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        patches["fetch_result"].side_effect = [RuntimeError("boom"), SUCCESS]
        job = _job()
        await ep._drive_hero_video_job(job, "ws-1", test_user_id)
        await job.finalize_task
        assert job.status == "completed"
        assert any("driver step for job" in line and "raised" in line for line in loglines)


# ---------------------------------------------------------------------------
# 5. Published HTML contains <video> + the marker
# ---------------------------------------------------------------------------

class TestPublishedHtml:
    async def test_hero_carries_the_marker_and_a_video_with_the_stored_source(self, patches, test_user_id):
        patches["fetch_result"].return_value = SUCCESS
        job = _job()
        await ep._advance_hero_video_job(job, "ws-1", test_user_id)
        await job.finalize_task
        html = _published_html(patches)
        hero = re.search(r"<section\b[^>]*>", html.split("<body>", 1)[1]).group(0)
        assert f'{HERO_MARKER_ATTR}="1"' in hero and 'id="home"' in hero
        video = re.search(r'<video\b[^>]*class="binaapp-hero-video"[^>]*>.*?</video>', html, re.S)
        assert video, html
        assert f'<source src="{CLOUD_VIDEO}" type="video/mp4">' in video.group(0)
        assert "autoplay" in video.group(0) and "muted" in video.group(0) and "playsinline" in video.group(0)
        # What the DB row and the storage snapshot get is the same page.
        assert patches["update_website"].await_args.args[1]["html_content"] == html


# ---------------------------------------------------------------------------
# 6. No duplicate polling
# ---------------------------------------------------------------------------

class TestSinglePoller:
    def test_site_poll_and_prepared_poll_are_read_only(self, client, auth_headers, patches, test_user_id):
        job_id = _start_job(client, auth_headers)
        prepared = svc.zai_video_service.register_job(
            task_id="task-p", website_id="", user_id=test_user_id, prompt="p", settings={}, provider="dashscope",
        )
        patches["fetch_result"].return_value = SUCCESS
        for _ in range(3):
            assert client.get(f"/api/v1/websites/ws-1/hero-video/jobs/{job_id}", headers=auth_headers).json()["status"] == "processing"
            assert client.get(f"/api/v1/websites/hero-video/jobs/{prepared.job_id}", headers=auth_headers).json()["status"] == "processing"
        patches["fetch_result"].assert_not_called()
        patches["store"].assert_not_called()
        assert "_advance_hero_video_job" not in _source_of(ep.poll_hero_video_job)
        assert "_advance_hero_video_job" not in _source_of(ep.poll_prepared_hero_video_job)


def _source_of(fn) -> str:
    import inspect
    return inspect.getsource(fn)


# ---------------------------------------------------------------------------
# 7. The sweep covers hero-video jobs regardless of website status
# ---------------------------------------------------------------------------

class TestSweep:
    async def test_overdue_live_job_on_a_published_site_is_failed(self, patches, test_user_id, loglines):
        patches["get_website"].return_value = _row(status="published")
        fresh = _job()
        stuck = _job(charged=True)
        stuck.created_at -= svc.zai_video_max_wait_seconds() + ep.HERO_VIDEO_SWEEP_GRACE_SECONDS + 1
        result = await ep.sweep_stuck_hero_video_jobs()
        assert result["count"] == 1 and result["ids"] == [stuck.job_id]
        assert stuck.status == "failed" and stuck.error == "timeout" and stuck.refunded is True
        assert fresh.status == "processing"
        assert any("HERO_VIDEO_TIMEOUT" in line for line in loglines)
        patches["admin_email"].assert_awaited_once()

    async def test_ledger_row_with_no_live_job_is_failed_and_refunded(self, patches, test_user_id):
        started = datetime.now(timezone.utc) - timedelta(seconds=svc.zai_video_max_wait_seconds() + 1000)
        patches["ledger_stale"].return_value = [{
            "job_id": "ghost-1", "task_id": "t-ghost", "provider": "dashscope", "website_id": "ws-1",
            "user_id": test_user_id, "status": "processing", "prompt": "p", "settings": {},
            "charged": True, "refunded": False, "created_at": started.isoformat(),
        }]
        result = await ep.sweep_stuck_hero_video_jobs()
        assert result["ids"] == ["ghost-1"]
        patches["refund_credit"].assert_awaited_once_with(test_user_id, "hero_video")
        saved = patches["ledger_save"].await_args.args[0]
        assert saved.job_id == "ghost-1" and saved.status == "failed" and saved.error == "timeout" and saved.refunded

    async def test_ledger_row_behind_a_finished_live_job_is_brought_up_to_date(self, patches, test_user_id):
        live = _job()
        live.status = "completed"
        patches["ledger_stale"].return_value = [{"job_id": live.job_id, "status": "processing", "user_id": test_user_id}]
        result = await ep.sweep_stuck_hero_video_jobs()
        assert result["count"] == 0
        assert patches["ledger_save"].await_args.args[0] is live
        patches["refund_credit"].assert_not_called()

    async def test_scheduler_runs_the_hero_video_sweep(self, monkeypatch):
        from app.core import scheduler as sched
        monkeypatch.setenv("HERO_VIDEO_ENABLED", "true")
        s = sched.StuckGenerationScheduler()
        with (
            patch("app.services.generation_heartbeat.sweep_stuck_generations", new=AsyncMock(return_value={"checked": True, "count": 0, "ids": []})),
            patch.object(ep, "sweep_stuck_hero_video_jobs", new=AsyncMock(return_value={"checked_rows": 2, "count": 1, "ids": ["j"]})) as sweep,
        ):
            await s._sweep_job()
        sweep.assert_awaited_once()
        assert s.get_status()["last_hero_video_count"] == 1


# ---------------------------------------------------------------------------
# 8. Restart recovery from the ledger
# ---------------------------------------------------------------------------

class TestResume:
    def test_row_roundtrip_keeps_the_real_age(self):
        job = _job(charged=True)
        job.provider_status = "RUNNING"
        job.created_wall = time.time() - 300
        job.created_at = time.monotonic() - 300
        row = ledger.row_from_job(job)
        assert row["status"] == "processing" and row["charged"] is True and row["finished_at"] is None
        back = ledger.job_from_row(row)
        assert back.job_id == job.job_id and back.provider_status == "RUNNING" and back.charged
        assert 299 <= back.age_seconds() <= 302

    async def test_unfinished_rows_are_adopted_and_driven(self, patches, test_user_id, monkeypatch):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        started = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
        base = {"provider": "dashscope", "user_id": test_user_id, "prompt": "p", "settings": {}, "created_at": started}
        patches["ledger_claimable"].return_value = [
            {**base, "job_id": "r-processing", "task_id": "t1", "website_id": "ws-1", "status": "processing"},
            {**base, "job_id": "r-storing-stored", "task_id": "t2", "website_id": "ws-1", "status": "storing",
             "video_url": CLOUD_VIDEO, "poster_url": CLOUD_POSTER},
            {**base, "job_id": "r-storing-unstored", "task_id": "t3", "website_id": "ws-1", "status": "storing"},
            {**base, "job_id": "r-ready", "task_id": "t4", "website_id": "", "status": "ready",
             "video_url": CLOUD_VIDEO, "poster_url": CLOUD_POSTER},
        ]
        patches["fetch_result"].return_value = SUCCESS
        resumed = await ep.resume_hero_video_jobs()
        ep._resume_recheck_task.cancel()
        assert resumed == 4
        assert patches["ledger_claim"].await_count == 4
        reg = svc.zai_video_service
        assert reg.get_job("r-processing").driver_task is not None
        assert 85 <= reg.get_job("r-processing").age_seconds() <= 95
        assert reg.get_job("r-storing-unstored").status == "processing"  # re-polled
        assert reg.get_job("r-ready").status == "ready" and reg.get_job("r-ready").driver_task is not None

        for job_id in ("r-processing", "r-storing-unstored"):
            await reg.get_job(job_id).driver_task
            await reg.get_job(job_id).finalize_task
            assert reg.get_job(job_id).status == "completed", job_id
        await reg.get_job("r-storing-stored").finalize_task
        assert reg.get_job("r-storing-stored").status == "completed"
        # The two that were never stored are stored now; the one that was
        # already on Cloudinary is applied as-is, not downloaded again.
        assert patches["store"].await_count == 2
        reg.get_job("r-ready").driver_task.cancel()

    async def test_resume_never_replaces_a_live_job(self, patches, test_user_id):
        live = _job()
        patches["ledger_claimable"].return_value = [{"job_id": live.job_id, "status": "processing", "user_id": test_user_id}]
        assert await ep.resume_hero_video_jobs() == 0
        ep._resume_recheck_task.cancel()
        assert svc.zai_video_service.get_job(live.job_id) is live
        patches["ledger_claim"].assert_not_called()

    async def test_a_row_another_process_claims_first_is_not_adopted(self, patches, test_user_id):
        """Two instances overlap during a deploy; the conditional PATCH in
        ledger.claim lets exactly one win. The loser must not drive it."""
        patches["ledger_claimable"].return_value = [
            {"job_id": "contested", "task_id": "t", "provider": "dashscope", "website_id": "ws-1",
             "user_id": test_user_id, "status": "processing", "prompt": "p", "settings": {}},
        ]
        patches["ledger_claim"].return_value = False
        assert await ep.adopt_unowned_jobs() == 0
        assert svc.zai_video_service.get_job("contested") is None


class TestOwnership:
    """A terminal write must belong to one process and happen once."""

    async def test_fail_job_defers_to_a_row_already_ended_elsewhere(self, patches, test_user_id):
        job = _job(charged=True)
        patches["ledger_load"].return_value = {"job_id": job.job_id, "status": "failed", "error": "timeout", "refunded": True}
        await ep._fail_job(job, "timeout")
        assert job.status == "failed" and job.error == "timeout" and job.refunded is True
        patches["refund_credit"].assert_not_called()
        patches["ledger_save"].assert_not_called()

    async def test_fail_job_leaves_a_row_leased_by_a_live_process_alone(self, patches, test_user_id):
        job = _job(charged=True)
        until = (datetime.now(timezone.utc) + timedelta(seconds=50)).isoformat()
        patches["ledger_load"].return_value = {"job_id": job.job_id, "status": "processing",
                                               "lease_owner": "someone-else", "lease_until": until}
        await ep._fail_job(job, "timeout")
        assert job.status == "processing"
        patches["refund_credit"].assert_not_called()

    async def test_one_refund_per_job_is_decided_by_the_ledger(self, patches, test_user_id):
        """The refund claim is a conditional PATCH on refunded=false. A job
        failed here and again after a restart is refunded once; a ledger
        that cannot answer does not block the merchant's money."""
        row = {"job_id": "ghost", "task_id": "t", "provider": "dashscope", "website_id": "ws-1",
               "user_id": test_user_id, "status": "processing", "prompt": "p", "settings": {},
               "charged": True, "refunded": False}
        patches["ledger_mark_refunded"].return_value = False  # already refunded elsewhere
        job = ledger.job_from_row(row)
        await ep._fail_job(job, "timeout")
        patches["refund_credit"].assert_not_called()
        assert job.refunded is True
        patches["ledger_mark_refunded"].return_value = None  # ledger unreachable
        await ep._fail_job(ledger.job_from_row(row), "timeout")
        patches["refund_credit"].assert_awaited_once()
        patches["ledger_mark_refunded"].return_value = True
        await ep._fail_job(ledger.job_from_row(row), "timeout")
        assert patches["refund_credit"].await_count == 2

    async def test_a_driver_that_lost_its_row_stops(self, patches, test_user_id, monkeypatch, loglines):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        patches["ledger_save"].return_value = ledger.SAVE_LOST
        patches["fetch_result"].return_value = {**SUCCESS, "status": "processing", "video_url": None, "raw_status": "RUNNING"}
        job = _job()
        await ep._drive_hero_video_job(job, "ws-1", test_user_id)
        assert job.ownership_lost and svc.zai_video_service.get_job(job.job_id) is None
        assert any("another process owns the row" in line for line in loglines)

    async def test_sweep_claims_a_stale_row_before_failing_it(self, patches, test_user_id):
        started = datetime.now(timezone.utc) - timedelta(seconds=svc.zai_video_max_wait_seconds() + 1000)
        row = {"job_id": "ghost-2", "task_id": "t", "provider": "dashscope", "website_id": "ws-1",
               "user_id": test_user_id, "status": "processing", "prompt": "p", "settings": {},
               "charged": True, "refunded": False, "created_at": started.isoformat()}
        patches["ledger_stale"].return_value = [row]
        patches["ledger_claim"].return_value = False  # another sweeper won
        result = await ep.sweep_stuck_hero_video_jobs()
        assert result["count"] == 0
        patches["refund_credit"].assert_not_called()
        patches["ledger_claim"].return_value = True
        result = await ep.sweep_stuck_hero_video_jobs()
        assert result["ids"] == ["ghost-2"]
        patches["refund_credit"].assert_awaited_once()

    async def test_sweep_adopts_an_orphan_inside_the_limit(self, patches, test_user_id, monkeypatch):
        monkeypatch.setattr(ep, "POLL_INTERVAL_SECONDS", 0.01)
        started = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        patches["ledger_claimable"].return_value = [
            {"job_id": "orphan", "task_id": "t", "provider": "dashscope", "website_id": "ws-1",
             "user_id": test_user_id, "status": "processing", "prompt": "p", "settings": {}, "created_at": started},
        ]
        patches["fetch_result"].return_value = SUCCESS
        result = await ep.sweep_stuck_hero_video_jobs()
        assert result["adopted"] == 1 and result["count"] == 0
        job = svc.zai_video_service.get_job("orphan")
        await job.driver_task
        await job.finalize_task
        assert job.status == "completed" and CLOUD_VIDEO in _published_html(patches)

    async def test_finaliser_stops_when_the_sweep_ended_the_job_mid_store(self, patches, test_user_id, loglines):
        job = _job()
        job.status = svc.JOB_STATUS_STORING

        async def slow_store(*a, **k):
            job.status = svc.JOB_STATUS_FAILED  # the sweep acted while we were downloading
            job.error = "timeout"
            return {"video_url": CLOUD_VIDEO, "poster_url": CLOUD_POSTER}

        patches["store"].side_effect = slow_store
        await ep._finalize_hero_video_job(job, _row(), test_user_id, "https://cdn.provider/v.mp4")
        assert job.status == "failed" and job.applied is False
        patches["publish_website"].assert_not_called()
        assert not any("html_content" in c.args[1] for c in patches["update_website"].await_args_list)
        assert any("stopping before" in line for line in loglines)

    async def test_settle_does_not_complete_a_job_the_window_already_ended(self, patches, test_user_id):
        job = svc.zai_video_service.register_job(
            task_id="t", website_id="", user_id=test_user_id, prompt="p", settings={}, provider="dashscope",
        )
        job.status = svc.JOB_STATUS_READY
        job.video_url = CLOUD_VIDEO
        html, staged = ep.stage_prepared_hero_video(job.job_id, test_user_id, LIVE_HTML)
        assert staged["status"] == "staged"
        job.status = svc.JOB_STATUS_FAILED  # 'unclaimed' landed between stage and settle
        job.error = "unclaimed"
        info = await ep.settle_prepared_hero_video(job.job_id, test_user_id, _row(), staged)
        assert info["status"] == "applied" and info["note"] == "job_failed"
        assert job.status == "failed" and job.applied is False
        patches["update_website"].assert_not_called()


# ---------------------------------------------------------------------------
# 9. /api/publish busts the served-page cache
# ---------------------------------------------------------------------------

class TestPublishBustsTheCache:
    def test_invalidate_is_called_after_a_successful_upload(self, client, auth_headers):
        from tests.test_publish_persistence import VALID_BALANCED_HTML, _empty_select_mock

        supabase_mock = MagicMock()
        supabase_mock.table.return_value = _empty_select_mock()
        storage_response = MagicMock(status_code=201, text="")
        fake = MagicMock()
        fake.__aenter__ = AsyncMock(return_value=fake)
        fake.__aexit__ = AsyncMock(return_value=False)
        fake.post = AsyncMock(return_value=storage_response)
        with (
            patch("app.main.supabase", supabase_mock),
            patch("app.main.sub_service.check_limit", new=AsyncMock(return_value={"allowed": True})),
            patch("app.main.sub_service.increment_usage", new=AsyncMock(return_value=True)),
            patch("app.services.plan_features.can_publish_subdomain", new=AsyncMock(return_value=True)),
            patch("app.main.supabase_service.is_email_verified", new=AsyncMock(return_value=True)),
            patch("app.main.httpx.AsyncClient", return_value=fake),
            patch("app.middleware.subdomain.invalidate_site_cache") as invalidate,
        ):
            resp = client.post(
                "/api/publish", headers=auth_headers,
                json={"html_content": VALID_BALANCED_HTML, "subdomain": "newshop",
                      "project_name": "New Shop", "website_id": "ws-new-1"},
            )
        assert resp.status_code == 200, resp.text
        invalidate.assert_called_once_with("newshop")


# ---------------------------------------------------------------------------
# 10. Raw provider state is logged on every poll; full body on failure
# ---------------------------------------------------------------------------

class TestProviderStateLogging:
    @pytest.fixture(autouse=True)
    def _dashscope(self, monkeypatch):
        monkeypatch.delenv("HERO_VIDEO_PROVIDER", raising=False)
        monkeypatch.setenv("DASHSCOPE_API_KEY", "ds-test-key")

    async def test_every_poll_logs_the_raw_task_status(self, loglines):
        client, _ = fake_client(get_response=FakeResponse(200, _ds_task("RUNNING")))
        with patch.object(httpx, "AsyncClient", client):
            result = await svc.ZaiVideoService().fetch_result("t-1")
        assert result["status"] == "processing" and result["raw_status"] == "RUNNING"
        assert any("DashScope task t-1 task_status=RUNNING" in line for line in loglines)

    @pytest.mark.parametrize("state", ["FAILED", "CANCELED", "UNKNOWN"])
    async def test_terminal_failure_logs_the_full_body(self, loglines, state):
        body = _ds_task(state)
        body["output"]["code"] = "DataInspectionFailed"
        body["output"]["message"] = "Input data may contain inappropriate content."
        client, _ = fake_client(get_response=FakeResponse(200, body, text=json.dumps(body)))
        with patch.object(httpx, "AsyncClient", client):
            result = await svc.ZaiVideoService().fetch_result("t-2")
        assert result["status"] == "fail" and result["raw_status"] == state
        assert result["code"] == "DataInspectionFailed"
        errors = [line for line in loglines if line.startswith("ERROR") and f"task t-2 {state}" in line]
        assert errors and "full body" in errors[0] and "DataInspectionFailed" in errors[0]

    async def test_unexpected_state_is_logged_with_the_body_and_kept_processing(self, loglines):
        client, _ = fake_client(get_response=FakeResponse(200, _ds_task("WEIRD_NEW_STATE")))
        with patch.object(httpx, "AsyncClient", client):
            result = await svc.ZaiVideoService().fetch_result("t-3")
        assert result["status"] == "processing" and result["raw_status"] == "WEIRD_NEW_STATE"
        assert any("UNEXPECTED task_status='WEIRD_NEW_STATE'" in line and "full body" in line for line in loglines)

    async def test_http_error_carries_its_status_and_body(self, loglines):
        client, _ = fake_client(get_response=FakeResponse(403, {}, text=""))
        with patch.object(httpx, "AsyncClient", client):
            with pytest.raises(svc.ZaiVideoError) as exc:
                await svc.ZaiVideoService().fetch_result("t-4")
        assert exc.value.status_code == 403
        assert any("poll failed: HTTP 403" in line and "(empty)" in line for line in loglines)


# ---------------------------------------------------------------------------
# 11. The ledger's HTTP layer
# ---------------------------------------------------------------------------

class TestLedgerHttp:
    @pytest.fixture(autouse=True)
    def _pooled(self, monkeypatch):
        # Route the pooled Supabase client through the fake for the test.
        from app.services.supabase_client import supabase_service
        monkeypatch.setattr(supabase_service, "_pooled_client", None)

    def _capture(self, status=200, body=None, text=""):
        from app.services.supabase_client import supabase_service
        supabase_service._pooled_client = None  # each fake is a fresh pool
        calls = {}

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def post(self, url, headers=None, json=None, params=None):
                calls["post"] = {"url": url, "headers": headers, "json": json}
                return FakeResponse(status, body, text=text)

            async def patch(self, url, headers=None, json=None, params=None):
                calls["patch"] = {"url": url, "headers": headers, "json": json, "params": params}
                return FakeResponse(status, body, text=text)

            async def get(self, url, headers=None, params=None):
                calls["get"] = {"url": url, "headers": headers, "params": params}
                return FakeResponse(status, body, text=text)

            @property
            def is_closed(self):
                return False

        return _Client, calls

    async def test_create_is_an_upsert_that_stamps_this_process_lease(self):
        client, calls = self._capture(201)
        with patch.object(httpx, "AsyncClient", client):
            assert await ledger.create(_job()) is True
        assert calls["post"]["url"].endswith("/rest/v1/hero_video_jobs")
        assert "resolution=merge-duplicates" in calls["post"]["headers"]["Prefer"]
        row = calls["post"]["json"]
        assert row["lease_owner"] == ledger.PROCESS_ID and row["lease_until"] > row["updated_at"]
        assert row["status"] == "processing" and row["finished_at"] is None

    async def test_save_only_writes_rows_this_process_owns(self):
        client, calls = self._capture(200, [{"job_id": "j"}], text="[{}]")
        with patch.object(httpx, "AsyncClient", client):
            assert await ledger.save(_job()) == ledger.SAVE_OK
        assert calls["patch"]["params"]["or"] == f"(lease_owner.is.null,lease_owner.eq.{ledger.PROCESS_ID})"
        # Zero rows and the row exists under another owner → lost.
        client, calls = self._capture(200, [], text="[]")
        with patch.object(httpx, "AsyncClient", client), \
             patch.object(ledger, "load", new=AsyncMock(return_value={"job_id": "j", "lease_owner": "other"})):
            assert await ledger.save(_job()) == ledger.SAVE_LOST
        # Zero rows and no row at all → re-created.
        client, calls = self._capture(200, [], text="[]")
        with patch.object(httpx, "AsyncClient", client), \
             patch.object(ledger, "load", new=AsyncMock(return_value=None)):
            assert await ledger.save(_job()) == ledger.SAVE_OK
        assert "post" in calls

    async def test_mark_refunded_is_won_once(self):
        client, calls = self._capture(200, [{"job_id": "j"}], text="[{}]")
        with patch.object(httpx, "AsyncClient", client):
            assert await ledger.mark_refunded("j") is True
        assert calls["patch"]["params"]["refunded"] == "eq.false" and calls["patch"]["json"]["refunded"] is True
        client, _ = self._capture(200, [], text="[]")
        with patch.object(httpx, "AsyncClient", client), \
             patch.object(ledger, "load", new=AsyncMock(return_value={"job_id": "j", "refunded": True})):
            assert await ledger.mark_refunded("j") is False

    async def test_terminal_rows_drop_the_lease(self):
        job = _job()
        job.status = "completed"
        row = ledger.row_from_job(job)
        assert row["lease_owner"] is None and row["lease_until"] is None and row["finished_at"]

    async def test_claim_wins_only_when_one_row_comes_back(self):
        client, calls = self._capture(200, [{"job_id": "j"}], text="[{}]")
        with patch.object(httpx, "AsyncClient", client):
            assert await ledger.claim("j", "processing") is True
        params = calls["patch"]["params"]
        assert params["job_id"] == "eq.j"
        assert params["status"].startswith("in.(") and "processing" in params["status"]
        assert params["or"].startswith("(lease_until.is.null,lease_until.lt.")
        assert calls["patch"]["json"]["lease_owner"] == ledger.PROCESS_ID
        client, _ = self._capture(200, [], text="[]")
        with patch.object(httpx, "AsyncClient", client):
            assert await ledger.claim("j", "processing") is False

    async def test_failures_are_loud_and_return_false(self, loglines):
        client, _ = self._capture(500, {}, text="boom")
        with patch.object(httpx, "AsyncClient", client):
            assert await ledger.save(_job()) == ledger.SAVE_ERROR
            assert await ledger.create(_job()) is False
            assert await ledger.claim("j", "processing") is False
            assert await ledger.load_claimable() == []
            assert await ledger.mark_refunded("j") is None
        assert sum(1 for line in loglines if line.startswith("ERROR") and "[hero-video-ledger]" in line) == 5

    def test_lease_is_live_semantics(self):
        future = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        past = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        assert ledger.lease_is_live({"lease_owner": "other", "lease_until": future}) is True
        assert ledger.lease_is_live({"lease_owner": "other", "lease_until": past}) is False
        assert ledger.lease_is_live({"lease_owner": ledger.PROCESS_ID, "lease_until": future}) is False
        assert ledger.lease_is_live({"lease_owner": None, "lease_until": future}) is False
        # Postgres' own timestamp spelling parses too.
        assert ledger.lease_is_live({"lease_owner": "other", "lease_until": "2099-01-01 00:00:00.123456+00"}) is True
