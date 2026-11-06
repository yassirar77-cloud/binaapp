"""Heartbeat + stuck-sweep helpers for website generation.

A long AI generation runs inside a FastAPI BackgroundTask. If the Render
worker restarts mid-flight (deploy, OOM, network blip), the task dies
silently and the websites row stays at status='generating' forever — the
user sees an infinite spinner and the only way out is manual SQL.

This module is the safety net:

1. `heartbeat_loop(website_id)` — spawned as `asyncio.create_task` next
   to the AI call. Writes `last_heartbeat_at = NOW()` every
   HEARTBEAT_INTERVAL_SECONDS. Cancelling the task stops the writes.
2. `clear_heartbeat(website_id)` — best-effort NULL write on the way out
   of every generation path (success and failure).
3. `find_stuck_websites(...)` + `mark_stuck_website_failed(...)` —
   queries used by the scheduler job in `core/scheduler.py`.

Heartbeat writes are best-effort: a transient Supabase error must NOT
take down the AI generation (the heartbeat is here to recover stuck
state, not to add a new failure mode). Errors are logged and swallowed.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.services.supabase_client import supabase_service


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


HEARTBEAT_INTERVAL_SECONDS = _env_float("HEARTBEAT_INTERVAL_SECONDS", 30.0)
STUCK_GENERATION_THRESHOLD_MINUTES = _env_float(
    "STUCK_GENERATION_THRESHOLD_MINUTES", 5.0
)

STUCK_ERROR_MESSAGE = (
    "Generation timeout — worker may have restarted. Please try again."
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _write_heartbeat(website_id: str) -> None:
    """One heartbeat write. Best-effort — swallow errors after logging."""
    try:
        ok = await supabase_service.update_website(
            website_id, {"last_heartbeat_at": _utcnow_iso()}
        )
        if not ok:
            logger.warning(
                f"[heartbeat] update_website returned falsy for {website_id} "
                f"— row may have been deleted or RLS blocked the write"
            )
    except Exception as e:
        logger.warning(f"[heartbeat] write failed for {website_id}: {e}")


async def heartbeat_loop(
    website_id: str,
    interval_seconds: Optional[float] = None,
) -> None:
    """Periodically stamp `last_heartbeat_at` for the given website.

    Spawn with `asyncio.create_task(heartbeat_loop(id))`, and cancel the
    task in a `finally` block once the AI work is done. CancelledError is
    re-raised so the caller's task accounting stays accurate.
    """
    interval = interval_seconds or HEARTBEAT_INTERVAL_SECONDS
    try:
        # First heartbeat fires immediately so a worker that dies in
        # the first 30s still leaves a trail for the sweep.
        await _write_heartbeat(website_id)
        while True:
            await asyncio.sleep(interval)
            await _write_heartbeat(website_id)
    except asyncio.CancelledError:
        # Expected — the AI call finished. Don't log noisily.
        raise


async def clear_heartbeat(website_id: str) -> None:
    """Null the heartbeat at the end of generation. Best-effort."""
    try:
        await supabase_service.update_website(
            website_id, {"last_heartbeat_at": None}
        )
    except Exception as e:
        logger.warning(f"[heartbeat] clear failed for {website_id}: {e}")


async def find_stuck_websites(
    threshold_minutes: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Return websites that look stuck on status='generating'.

    A row is stuck when ALL of:
      - status = 'generating'
      - last_heartbeat_at IS NULL OR < NOW() - threshold
      - updated_at < NOW() - threshold

    The `updated_at` clause guards against transient races where the
    heartbeat hasn't fired yet on a brand-new row (the regenerate
    endpoint stamps updated_at when it flips status to 'generating').
    """
    minutes = threshold_minutes or STUCK_GENERATION_THRESHOLD_MINUTES
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=minutes)
    ).isoformat()

    url = f"{supabase_service.url}/rest/v1/websites"
    # PostgREST `or` syntax: heartbeat null OR heartbeat < cutoff.
    # `updated_at` is ANDed via a separate query param.
    params = {
        "status": "eq.generating",
        "or": f"(last_heartbeat_at.is.null,last_heartbeat_at.lt.{cutoff})",
        "updated_at": f"lt.{cutoff}",
        "select": "id,user_id,subdomain,status,updated_at,last_heartbeat_at",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                url, headers=supabase_service.headers, params=params
            )
        if resp.status_code != 200:
            logger.warning(
                f"[stuck-sweep] PostgREST returned {resp.status_code}: "
                f"{resp.text[:200]}"
            )
            return []
        rows = resp.json()
        return rows if isinstance(rows, list) else []
    except Exception as e:
        logger.error(f"[stuck-sweep] query failed: {e}")
        return []


async def mark_stuck_website_failed(website_id: str) -> bool:
    """Flip a stuck generating row to failed + clear the heartbeat."""
    ok = await supabase_service.update_website(
        website_id,
        {
            "status": "failed",
            "error_message": STUCK_ERROR_MESSAGE,
            "last_heartbeat_at": None,
            "updated_at": _utcnow_iso(),
        },
    )
    if ok:
        logger.warning(
            f"[stuck-sweep] marked website_id={website_id} as failed "
            f"(was stuck on 'generating')"
        )
    else:
        logger.error(
            f"[stuck-sweep] failed to update website_id={website_id} — "
            f"PostgREST returned no rows"
        )
    return ok


async def sweep_stuck_generations(
    threshold_minutes: Optional[float] = None,
) -> Dict[str, Any]:
    """Find every stuck row and mark it failed. Returns a summary dict."""
    stuck = await find_stuck_websites(threshold_minutes=threshold_minutes)
    if not stuck:
        return {"checked": True, "count": 0, "ids": []}

    flipped: List[str] = []
    for row in stuck:
        website_id = row.get("id")
        if not website_id:
            continue
        ok = await mark_stuck_website_failed(website_id)
        if ok:
            flipped.append(website_id)

    return {"checked": True, "count": len(flipped), "ids": flipped}


# ---------------------------------------------------------------------------
# generation_jobs: an interrupted job is failed, never left 'processing'
# ---------------------------------------------------------------------------
# A Render redeploy restarted the worker under job 7f29bbb4 at 55%; the row
# stayed 'processing' for good (the sweep above only watches `websites`).
# run_generation_task's heartbeat touches generation_jobs.updated_at every
# JOB_HEARTBEAT_SECONDS (30s), so a row silent for STALE_JOB_SECONDS has no
# worker. It is flipped to 'failed' with a retry message — by the status
# endpoint the moment the page polls it, and by the scheduler sweep.

STALE_JOB_SECONDS = _env_float("STALE_JOB_SECONDS", 180.0)
JOB_INTERRUPTED_ERROR = (
    "Penjanaan terganggu kerana pelayan dimulakan semula. Sila cuba lagi."
)


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        ts = datetime.fromisoformat(text)
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def job_is_stale(job: Optional[Dict[str, Any]], *, now: Optional[datetime] = None,
                 stale_seconds: Optional[float] = None) -> bool:
    """A 'processing' job whose row has not been touched for
    STALE_JOB_SECONDS: the worker that owned it is gone."""
    if not job or str(job.get("status") or "") != "processing":
        return False
    ts = _parse_ts(job.get("updated_at"))
    if ts is None:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - ts).total_seconds() >= (stale_seconds or STALE_JOB_SECONDS)


async def fail_stale_job(job_id: str, *, stale_seconds: Optional[float] = None) -> bool:
    """Flip one job to 'failed' — only while it is still 'processing' AND
    still stale, so a heartbeat that lands meanwhile wins. True when this
    call changed the row."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds or STALE_JOB_SECONDS)).isoformat()
    url = f"{supabase_service.url}/rest/v1/generation_jobs"
    params = {"job_id": f"eq.{job_id}", "status": "eq.processing", "updated_at": f"lt.{cutoff}"}
    headers = {**supabase_service.headers, "Prefer": "return=representation"}
    body = {"status": "failed", "error": JOB_INTERRUPTED_ERROR, "updated_at": _utcnow_iso()}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(url, headers=headers, params=params, json=body)
        if resp.status_code not in (200, 204):
            logger.warning(f"[stale-job] PATCH {job_id[:8]} returned {resp.status_code}: {resp.text[:160]}")
            return False
        rows = resp.json() if resp.content else []
        changed = bool(rows)
        if changed:
            logger.warning(f"[stale-job] job {job_id[:8]} had no heartbeat for {STALE_JOB_SECONDS:.0f}s — marked failed (worker restarted)")
        return changed
    except Exception as e:
        logger.error(f"[stale-job] could not fail job {job_id[:8]}: {e}")
        return False


async def sweep_stale_jobs(stale_seconds: Optional[float] = None) -> Dict[str, Any]:
    """Every 'processing' job with no heartbeat for STALE_JOB_SECONDS is
    failed with JOB_INTERRUPTED_ERROR."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds or STALE_JOB_SECONDS)).isoformat()
    url = f"{supabase_service.url}/rest/v1/generation_jobs"
    params = {"status": "eq.processing", "updated_at": f"lt.{cutoff}", "select": "job_id,updated_at"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=supabase_service.headers, params=params)
        rows = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        logger.error(f"[stale-job] sweep query failed: {e}")
        return {"checked": False, "count": 0, "ids": []}
    failed: List[str] = []
    for row in rows if isinstance(rows, list) else []:
        jid = row.get("job_id")
        if jid and await fail_stale_job(jid, stale_seconds=stale_seconds):
            failed.append(jid)
    return {"checked": True, "count": len(failed), "ids": failed}
