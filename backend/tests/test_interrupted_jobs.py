"""An interrupted generation is failed with a retry message, never left
'processing'. Job 7f29bbb4 sat at 55% after a Render redeploy restarted
the worker; nothing ever moved it."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services import generation_heartbeat as gh

NOW = datetime(2026, 11, 6, 11, 30, tzinfo=timezone.utc)


def _job(status="processing", ago=600, naive=False):
    ts = NOW - timedelta(seconds=ago)
    return {"job_id": "7f29bbb4-9a0f", "status": status, "updated_at": (ts.replace(tzinfo=None) if naive else ts).isoformat()}


class TestStaleness:
    def test_silent_processing_job_is_stale(self):
        assert gh.job_is_stale(_job(ago=600), now=NOW)
        assert gh.job_is_stale(_job(ago=600, naive=True), now=NOW)

    def test_recent_heartbeat_is_alive(self):
        assert not gh.job_is_stale(_job(ago=45), now=NOW)

    def test_finished_jobs_are_never_stale(self):
        assert not gh.job_is_stale(_job(status="completed", ago=99999), now=NOW)
        assert not gh.job_is_stale(_job(status="failed", ago=99999), now=NOW)
        assert not gh.job_is_stale(None, now=NOW)

    def test_message_is_malay_and_asks_to_retry(self):
        assert "Sila cuba lagi" in gh.JOB_INTERRUPTED_ERROR


class _Resp:
    def __init__(self, status, payload):
        self.status_code, self._p = status, payload
        self.content = json.dumps(payload).encode()
        self.text = json.dumps(payload)

    def json(self):
        return self._p


class _Client:
    def __init__(self, log, patch_rows, get_rows=()):
        self.log, self.patch_rows, self.get_rows = log, patch_rows, list(get_rows)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def patch(self, url, headers=None, params=None, json=None):
        self.log.append(("PATCH", params, json))
        return _Resp(200, self.patch_rows)

    async def get(self, url, headers=None, params=None):
        self.log.append(("GET", params, None))
        return _Resp(200, self.get_rows)


@pytest.mark.asyncio
async def test_fail_is_conditional_on_still_processing_and_still_stale(monkeypatch):
    log = []
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client(log, [{"job_id": "7f29bbb4"}]))
    assert await gh.fail_stale_job("7f29bbb4-9a0f")
    _, params, body = log[0]
    assert params["status"] == "eq.processing" and params["updated_at"].startswith("lt.")
    assert body["status"] == "failed" and body["error"] == gh.JOB_INTERRUPTED_ERROR


@pytest.mark.asyncio
async def test_a_heartbeat_that_lands_first_wins(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client([], []))
    assert not await gh.fail_stale_job("7f29bbb4-9a0f")


@pytest.mark.asyncio
async def test_sweep_fails_every_silent_job(monkeypatch):
    log = []
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client(log, [{"job_id": "x"}], [{"job_id": "a"}, {"job_id": "b"}]))
    res = await gh.sweep_stale_jobs()
    assert res["count"] == 2 and res["ids"] == ["a", "b"]


@pytest.mark.asyncio
async def test_status_endpoint_fails_a_dead_job(monkeypatch):
    import app.main as main_module

    async def fake_get(job_id):
        return _job(ago=900) | {"progress": 55, "html": None}

    async def fake_fail(job_id, **kw):
        return True

    monkeypatch.setattr(main_module, "get_job_from_supabase", fake_get)
    monkeypatch.setattr(gh, "fail_stale_job", fake_fail)
    res = await main_module.get_generation_status("7f29bbb4-9a0f")
    assert res["status"] == "failed" and "Sila cuba lagi" in res["error"]
