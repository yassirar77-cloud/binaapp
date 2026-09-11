"""Durable ledger for hero-video jobs (table ``hero_video_jobs``).

The in-memory registry in ``zai_video_service`` is fast and is what the
request handlers and the driver read. It is also the reason clips went
missing: Render restarts the process on every deploy, and a job that was
rendering, or stored and waiting for its publish, was simply forgotten —
no log line, no refund, invisible to the stuck sweep.

Every state change is mirrored here. On startup the endpoint module reads
back every row that is not terminal and resumes it; the stuck sweep reads
rows that exceeded the hard timeout and fails them whether or not a
driver is alive for them.

Write failures are LOGGED AT ERROR AND NOT RAISED: the ledger exists to
make the pipeline recoverable, and a Supabase blip must not stop a clip
that is already on Cloudinary from reaching the page. Every caller gets a
bool back and the log names the job, so a failing ledger is loud, not
silent.

Ownership
---------
Render overlaps the old and the new instance while deploying, so two
processes can hold the same job. Every save stamps a lease
(``lease_owner`` = this process, ``lease_until`` = now + a state-specific
length); a driver renews it on every poll. Adoption — at startup and from
the sweep — goes through ``claim``: a conditional PATCH that succeeds only
while the lease is null or lapsed, so one process wins and the other sees
zero rows. A terminal write (fail + refund) first checks that nobody else
holds a live lease and that the row is not already terminal.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from app.services.supabase_client import supabase_service

TABLE = "hero_video_jobs"

#: States the ledger considers "still in flight" for restart recovery.
UNFINISHED_STATUSES = ("processing", "storing", "ready")
TERMINAL_STATUSES = ("completed", "failed")

#: Identifies this process in ``lease_owner``. New on every start.
PROCESS_ID = uuid.uuid4().hex

#: How long a lease lasts before another process may adopt the row. A
#: processing job renews on every 8 s poll, so 60 s means "three missed
#: polls". Storing has no poll loop (one download + upload, up to ~2 min
#: on a slow clip) and a ready job only wakes to renew, so those are
#: longer and the ready-wait renews itself at half the lease.
LEASE_SECONDS = {"processing": 60.0, "storing": 300.0, "ready": 300.0}


def lease_seconds_for(status: str) -> float:
    return LEASE_SECONDS.get(status, 60.0)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: Optional[datetime]) -> Optional[str]:
    return ts.isoformat() if ts else None


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def row_from_job(job) -> Dict[str, Any]:
    """The ledger row for a ``HeroVideoJob``. ``created_at`` is the job's
    wall-clock start so the sweep can age it without a running process."""
    started = datetime.fromtimestamp(job.created_wall, tz=timezone.utc)
    terminal = job.status in ("completed", "failed")
    now = _utcnow()
    return {
        "job_id": job.job_id,
        "task_id": job.task_id,
        "provider": job.provider or "",
        # Terminal rows drop the lease: nothing is left to own.
        "lease_owner": None if terminal else PROCESS_ID,
        "lease_until": None if terminal else _iso(now + timedelta(seconds=lease_seconds_for(job.status))),
        "website_id": job.website_id or "",
        "user_id": job.user_id,
        "status": job.status,
        "error": job.error,
        "provider_status": job.provider_status,
        "provider_message": (job.provider_message or None) and str(job.provider_message)[:500],
        "prompt": job.prompt or "",
        "image_url": job.image_url,
        "settings": job.settings or {},
        "video_url": job.video_url,
        "poster_url": job.poster_url,
        "charged": bool(job.charged),
        "refunded": bool(job.refunded),
        "applied": bool(job.applied),
        "live_site_updated": bool(job.live_site_updated),
        "poll_errors": int(job.poll_errors),
        "created_at": _iso(started),
        "updated_at": _iso(now),
        "last_polled_at": _iso(
            datetime.fromtimestamp(job.last_polled_wall, tz=timezone.utc)
        ) if job.last_polled_wall else None,
        "finished_at": _iso(now) if terminal else None,
    }


def lease_is_live(row: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """True when another process holds a current lease on this row."""
    owner = row.get("lease_owner")
    until = _parse_ts(row.get("lease_until"))
    if not owner or owner == PROCESS_ID or until is None:
        return False
    return until > (now or _utcnow())


def job_from_row(row: Dict[str, Any]):
    """Rebuild a ``HeroVideoJob`` from its ledger row (restart recovery).

    ``created_at`` is restored as both wall time and the monotonic clock
    the timeout check reads, so a job that was already eight minutes old
    when the process died is still eight minutes old after the restart —
    the hard timeout counts from the real start, not the resume."""
    from app.services.zai_video_service import HeroVideoJob

    started = _parse_ts(row.get("created_at")) or _utcnow()
    age = max(0.0, (_utcnow() - started).total_seconds())
    job = HeroVideoJob(
        job_id=str(row["job_id"]),
        task_id=str(row.get("task_id") or ""),
        website_id=str(row.get("website_id") or ""),
        user_id=str(row.get("user_id") or ""),
        prompt=str(row.get("prompt") or ""),
        settings=dict(row.get("settings") or {}),
        status=str(row.get("status") or "processing"),
        error=row.get("error"),
        video_url=row.get("video_url"),
        poster_url=row.get("poster_url"),
        image_url=row.get("image_url"),
        applied=bool(row.get("applied")),
        live_site_updated=bool(row.get("live_site_updated")),
        provider=str(row.get("provider") or ""),
        charged=bool(row.get("charged")),
        refunded=bool(row.get("refunded")),
        provider_status=row.get("provider_status"),
        provider_message=row.get("provider_message"),
        poll_errors=int(row.get("poll_errors") or 0),
    )
    job.created_at = time.monotonic() - age
    job.created_wall = started.timestamp()
    polled = _parse_ts(row.get("last_polled_at"))
    job.last_polled_wall = polled.timestamp() if polled else None
    return job


SAVE_OK = "ok"
SAVE_ERROR = "error"
#: The row is owned by another live process: this process must stop
#: driving the job. Returned only when the row exists and is not ours.
SAVE_LOST = "lost"


async def create(job) -> bool:
    """First write for a new job: an upsert that stamps this process's
    lease. Returns False (after an ERROR log) on failure."""
    url = f"{supabase_service.url}/rest/v1/{TABLE}"
    headers = {**supabase_service.headers, "Prefer": "resolution=merge-duplicates,return=minimal"}
    try:
        async with supabase_service._client() as client:
            resp = await client.post(url, headers=headers, json=row_from_job(job))
        if resp.status_code in (200, 201, 204):
            return True
        logger.error(
            f"[hero-video-ledger] create failed for job {job.job_id}: HTTP {resp.status_code} {resp.text[:300]}"
        )
        return False
    except Exception as exc:  # noqa: BLE001 — logged, never raised into the driver
        logger.error(f"[hero-video-ledger] create raised for job {job.job_id}: {exc!r}")
        return False


async def save(job) -> str:
    """Write the job's state — only while this process owns the row. A
    PATCH filtered on the lease owner: one row back means saved (and the
    lease renewed); zero rows means either the row is gone (re-created)
    or another process claimed it after our lease lapsed (SAVE_LOST — the
    caller must stop driving). Returns SAVE_OK / SAVE_ERROR / SAVE_LOST."""
    url = f"{supabase_service.url}/rest/v1/{TABLE}"
    params = {
        "job_id": f"eq.{job.job_id}",
        "or": f"(lease_owner.is.null,lease_owner.eq.{PROCESS_ID})",
    }
    try:
        async with supabase_service._client() as client:
            resp = await client.patch(
                url,
                headers={**supabase_service.headers, "Prefer": "return=representation"},
                params=params,
                json=row_from_job(job),
            )
        if resp.status_code not in (200, 204):
            logger.error(
                f"[hero-video-ledger] save failed for job {job.job_id} "
                f"(status={job.status}): HTTP {resp.status_code} {resp.text[:300]}"
            )
            return SAVE_ERROR
        rows = resp.json() if resp.text else []
        if isinstance(rows, list) and len(rows) == 1:
            return SAVE_OK
        existing = await load(job.job_id)
        if existing is None:
            return SAVE_OK if await create(job) else SAVE_ERROR
        logger.error(
            f"[hero-video-ledger] job {job.job_id} is owned by process "
            f"{str(existing.get('lease_owner'))[:8]} (lease until {existing.get('lease_until')}) — "
            "this process lost the job and must stop driving it"
        )
        return SAVE_LOST
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[hero-video-ledger] save raised for job {job.job_id}: {exc!r}")
        return SAVE_ERROR


async def mark_refunded(job_id: str) -> Optional[bool]:
    """Claim the one refund a job may ever get: PATCH refunded=true only
    where it is still false. True → we won and must refund; False → it
    was already refunded; None → the ledger could not answer."""
    url = f"{supabase_service.url}/rest/v1/{TABLE}"
    try:
        async with supabase_service._client() as client:
            resp = await client.patch(
                url,
                headers={**supabase_service.headers, "Prefer": "return=representation"},
                params={"job_id": f"eq.{job_id}", "refunded": "eq.false"},
                json={"refunded": True, "updated_at": _iso(_utcnow())},
            )
        if resp.status_code not in (200, 204):
            logger.error(f"[hero-video-ledger] mark_refunded({job_id}) failed: HTTP {resp.status_code} {resp.text[:300]}")
            return None
        rows = resp.json() if resp.text else []
        if isinstance(rows, list) and len(rows) == 1:
            return True
        existing = await load(job_id)
        if existing is None:
            return None
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[hero-video-ledger] mark_refunded({job_id}) raised: {exc!r}")
        return None


async def _select(params: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{supabase_service.url}/rest/v1/{TABLE}"
    query = {"select": "*", "order": "created_at.asc", **params}
    try:
        async with supabase_service._client() as client:
            resp = await client.get(url, headers=supabase_service.headers, params=query)
        if resp.status_code != 200:
            logger.error(
                f"[hero-video-ledger] select failed: HTTP {resp.status_code} {resp.text[:300]}"
            )
            return []
        rows = resp.json()
        return rows if isinstance(rows, list) else []
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[hero-video-ledger] select raised: {exc!r}")
        return []


async def load(job_id: str) -> Optional[Dict[str, Any]]:
    rows = await _select({"job_id": f"eq.{job_id}", "limit": "1"})
    return rows[0] if rows else None


async def load_unfinished() -> List[Dict[str, Any]]:
    """Every row that is still rendering, being stored, or stored and
    waiting for its publish — whoever owns it."""
    return await _select({"status": f"in.({','.join(UNFINISHED_STATUSES)})"})


async def load_claimable() -> List[Dict[str, Any]]:
    """Unfinished rows nobody currently owns: lease null or lapsed. What a
    restart resumes and the sweep adopts."""
    now = _iso(_utcnow())
    return await _select({
        "status": f"in.({','.join(UNFINISHED_STATUSES)})",
        "or": f"(lease_until.is.null,lease_until.lt.{now})",
    })


async def claim(job_id: str, status: str) -> bool:
    """Take ownership of a row, atomically: PATCH the lease only where the
    current lease is null or lapsed and the row is still unfinished.
    PostgREST returns the rows it updated; one row means we own it, zero
    means another process got there first (or the job finished)."""
    url = f"{supabase_service.url}/rest/v1/{TABLE}"
    now = _utcnow()
    payload = {
        "lease_owner": PROCESS_ID,
        "lease_until": _iso(now + timedelta(seconds=lease_seconds_for(status))),
        "updated_at": _iso(now),
    }
    params = {
        "job_id": f"eq.{job_id}",
        "status": f"in.({','.join(UNFINISHED_STATUSES)})",
        "or": f"(lease_until.is.null,lease_until.lt.{_iso(now)})",
    }
    try:
        async with supabase_service._client() as client:
            resp = await client.patch(
                url,
                headers={**supabase_service.headers, "Prefer": "return=representation"},
                params=params,
                json=payload,
            )
        if resp.status_code not in (200, 204):
            logger.error(
                f"[hero-video-ledger] claim({job_id}) failed: HTTP {resp.status_code} {resp.text[:300]}"
            )
            return False
        rows = resp.json() if resp.text else []
        return isinstance(rows, list) and len(rows) == 1
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[hero-video-ledger] claim({job_id}) raised: {exc!r}")
        return False


async def load_stale(older_than_seconds: float) -> List[Dict[str, Any]]:
    """Rows still processing/storing that started more than
    ``older_than_seconds`` ago — the sweep's definition of stuck."""
    cutoff = _utcnow() - timedelta(seconds=older_than_seconds)
    return await _select({
        "status": "in.(processing,storing)",
        "created_at": f"lt.{cutoff.isoformat()}",
    })


async def mark_failed(job_id: str, error: str, *, refunded: Optional[bool] = None) -> bool:
    """Terminal write for a row whose in-memory job no longer exists (the
    process that owned it is gone). Used by the sweep."""
    url = f"{supabase_service.url}/rest/v1/{TABLE}"
    payload: Dict[str, Any] = {
        "status": "failed",
        "error": error,
        "updated_at": _iso(_utcnow()),
        "finished_at": _iso(_utcnow()),
    }
    if refunded is not None:
        payload["refunded"] = bool(refunded)
    try:
        async with supabase_service._client() as client:
            resp = await client.patch(
                url,
                headers={**supabase_service.headers, "Prefer": "return=minimal"},
                params={"job_id": f"eq.{job_id}"},
                json=payload,
            )
        if resp.status_code in (200, 204):
            return True
        logger.error(
            f"[hero-video-ledger] mark_failed({job_id}, {error}) failed: "
            f"HTTP {resp.status_code} {resp.text[:300]}"
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[hero-video-ledger] mark_failed({job_id}) raised: {exc!r}")
        return False
