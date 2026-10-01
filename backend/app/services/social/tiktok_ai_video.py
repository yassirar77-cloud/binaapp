"""AI promo clips for TikTok on the existing Wan 3.0 (DashScope) integration.

The admin uploads 1–3 real photos (the dish, the shop, the product) and a
short brief; ``zai_video_service`` submits a wan3.0-video reference-to-video
job (the photos as ``reference_image`` media, named "Image 1…" in the
prompt, vertical 9:16, 10–15 s, 720P by default). The job is polled in the
background, the clip is copied into the private ``tiktok-media`` bucket, and
the admin previews it, regenerates, or loads it into the composer.

Money rules:
  * the estimated cost is shown before the button is pressed and written
    on every row (``tiktok_ai_videos``) as the cost log;
  * ``WAN_DAILY_VIDEO_LIMIT`` (default 10) caps the clips that reach the
    provider per UTC day — rows that failed before submit do not count.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from app.services import zai_video_service as video
from app.services.social import tiktok_media
from app.services.social._db import db_insert, db_select, db_update
from app.services.social.tiktok_client import utf16_length

TABLE = "tiktok_ai_videos"

RESOLUTIONS = ("720P", "1080P")
DEFAULT_RESOLUTION = "720P"
DURATIONS = (10, 15)
DEFAULT_DURATION = 10
MIN_PHOTOS = 1
MAX_PHOTOS = 3
BRIEF_MAX = 400

POLL_INTERVAL_SECONDS = 5.0

#: List price on Alibaba Cloud Model Studio for wan3.0-video, USD per output
#: second (480P $0.05, 720P $0.10, 1080P $0.20). Reference images are free.
#: Override with WAN_COST_USD_PER_SEC_<RES> if the account's rate differs.
_DEFAULT_USD_PER_SEC = {"480P": 0.05, "720P": 0.10, "1080P": 0.20}

_running: Set[asyncio.Task] = set()


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

def daily_limit() -> int:
    try:
        return max(0, int(os.getenv("WAN_DAILY_VIDEO_LIMIT", "10")))
    except ValueError:
        return 10


def usd_to_myr() -> float:
    try:
        return float(os.getenv("WAN_USD_TO_MYR", "4.40"))
    except ValueError:
        return 4.40


def usd_per_second(resolution: str) -> float:
    res = (resolution or "").upper()
    raw = os.getenv(f"WAN_COST_USD_PER_SEC_{res}")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return _DEFAULT_USD_PER_SEC.get(res, _DEFAULT_USD_PER_SEC["720P"])


def is_enabled() -> bool:
    """The AI step needs DashScope (Wan 3.0); Z.ai cannot take references."""
    return bool(video._dashscope_api_key()) and video._dashscope_is_unified(video.dashscope_video_model())


def clean_resolution(value: Optional[str]) -> str:
    v = (value or "").strip().upper()
    return v if v in RESOLUTIONS else DEFAULT_RESOLUTION


def clean_duration(value: Optional[int]) -> int:
    try:
        d = int(value) if value is not None else DEFAULT_DURATION
    except (TypeError, ValueError):
        return DEFAULT_DURATION
    return d if d in DURATIONS else DEFAULT_DURATION


def estimate_cost(resolution: str, duration_sec: int) -> Dict[str, float]:
    """``{"usd": …, "rm": …}`` for one clip. Pure."""
    res = clean_resolution(resolution)
    dur = clean_duration(duration_sec)
    usd = round(usd_per_second(res) * dur, 4)
    return {"usd": usd, "rm": round(usd * usd_to_myr(), 2)}


def cost_table() -> Dict[str, Dict[str, Dict[str, float]]]:
    return {res: {str(d): estimate_cost(res, d) for d in DURATIONS} for res in RESOLUTIONS}


# --------------------------------------------------------------------------
# prompt
# --------------------------------------------------------------------------

_SOCIAL_SUFFIX = (
    "Vertical 9:16 TikTok promo video, smooth cinematic camera movement, "
    "appetizing natural lighting, realistic, no text or captions, no logos, "
    "no watermark, high quality."
)


def build_promo_prompt(brief: str, photo_count: int) -> str:
    """The prompt wan3.0 receives. Names every photo as "Image n" so the
    model keeps the real product in frame; the brief carries the offer.
    Always ≤ ZAI_PROMPT_MAX_CHARS. Pure."""
    n = max(1, min(int(photo_count or 1), MAX_PHOTOS))
    names = ", ".join(f"Image {i}" for i in range(1, n + 1))
    subject = (
        f"Show the exact dish, product and place in {names} — keep them recognisable, "
        f"this is the real thing being promoted."
        if n > 1
        else "Show the exact dish, product or place in Image 1 — keep it recognisable, this is the real thing being promoted."
    )
    clean_brief = " ".join((brief or "").split())
    if clean_brief:
        clean_brief = clean_brief if clean_brief[-1] in ".!?" else clean_brief + "."
        scene = f"Promo brief: {clean_brief} {subject}"
    else:
        scene = subject
    room = video.ZAI_PROMPT_MAX_CHARS - len(_SOCIAL_SUFFIX) - 1
    if len(scene) > room:
        scene = scene[: room - 1].rstrip() + "…"
    return f"{scene} {_SOCIAL_SUFFIX}"


# --------------------------------------------------------------------------
# rows
# --------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def public_view(row: Dict[str, Any]) -> Dict[str, Any]:
    key = row.get("video_key")
    return {
        "id": row.get("id"),
        "status": row.get("status"),
        "brief": row.get("brief"),
        "prompt": row.get("prompt"),
        "resolution": row.get("resolution"),
        "duration_sec": row.get("duration_sec"),
        "provider": row.get("provider"),
        "model": row.get("model"),
        "provider_status": row.get("provider_status"),
        "error": row.get("error"),
        "photo_keys": row.get("photo_keys") or [],
        # The browser builds the playable URL from the key against the direct
        # backend origin (/api/v1/social/tiktok/media/{key}).
        "video_key": key,
        # True once the provider accepted the job (= it costs money and counts
        # against the daily cap).
        "submitted": bool(row.get("task_id")),
        "video_bytes": row.get("video_bytes"),
        "estimated_cost_usd": float(row.get("estimated_cost_usd") or 0),
        "estimated_cost_rm": float(row.get("estimated_cost_rm") or 0),
        "created_at": row.get("created_at"),
        "finished_at": row.get("finished_at"),
    }


async def submitted_today() -> int:
    rows = await db_select(
        TABLE,
        extra={"created_at": f"gte.{_day_start_iso()}", "task_id": "not.is.null", "select": "id"},
    )
    return len(rows)


def cap_reached(used: int, limit: int) -> bool:
    """Pure: a limit of 0 disables the feature."""
    return used >= limit


async def usage_today() -> Dict[str, int]:
    limit = daily_limit()
    used = await submitted_today()
    return {"used": used, "limit": limit, "remaining": max(0, limit - used)}


async def list_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    return await db_select(TABLE, extra={"order": "created_at.desc", "limit": str(max(1, min(limit, 100)))})


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    rows = await db_select(TABLE, filters={"id": job_id})
    return rows[0] if rows else None


async def _patch(job_id: str, patch: Dict[str, Any]) -> None:
    patch.setdefault("updated_at", _iso_now())
    await db_update(TABLE, {"id": job_id}, patch)


async def _fail(job_id: str, message: str, provider_status: Optional[str] = None) -> None:
    await _patch(
        job_id,
        {"status": "failed", "error": message[:500], "provider_status": provider_status, "finished_at": _iso_now()},
    )


class DailyCapReached(RuntimeError):
    pass


class AiVideoUnavailable(RuntimeError):
    pass


# --------------------------------------------------------------------------
# start + drive
# --------------------------------------------------------------------------

async def start_generation(
    *, user_id: str, brief: str, photo_keys: List[str], resolution: str, duration_sec: int
) -> Dict[str, Any]:
    """Create the row, submit to Wan 3.0, start the background driver."""
    if not is_enabled():
        raise AiVideoUnavailable(
            "AI video is not available: DASHSCOPE_API_KEY is not set or DASHSCOPE_VIDEO_MODEL is not a wan3.x model."
        )
    usage = await usage_today()
    if cap_reached(usage["used"], usage["limit"]):
        raise DailyCapReached(
            f"Daily AI video limit reached ({usage['used']}/{usage['limit']}). Try again tomorrow or raise WAN_DAILY_VIDEO_LIMIT."
        )

    res = clean_resolution(resolution)
    dur = clean_duration(duration_sec)
    brief = (brief or "").strip()
    if utf16_length(brief) > BRIEF_MAX:
        brief = brief[:BRIEF_MAX]
    prompt = build_promo_prompt(brief, len(photo_keys))
    cost = estimate_cost(res, dur)

    row = await db_insert(
        TABLE,
        {
            "created_by": user_id,
            "brief": brief,
            "prompt": prompt,
            "photo_keys": photo_keys,
            "resolution": res,
            "duration_sec": dur,
            "aspect": video.ASPECT_SOCIAL,
            "provider": video.PROVIDER_DASHSCOPE,
            "model": video.dashscope_video_model(),
            "status": "queued",
            "estimated_cost_usd": cost["usd"],
            "estimated_cost_rm": cost["rm"],
        },
    )
    job_id = str(row["id"])

    try:
        task_id = await video.zai_video_service.submit(
            prompt,
            duration=dur,
            provider=video.PROVIDER_DASHSCOPE,
            aspect=video.ASPECT_SOCIAL,
            reference_image_urls=[tiktok_media.public_url(k) for k in photo_keys],
            resolution=res,
            audio=False,
        )
    except video.ZaiVideoError as exc:
        logger.warning("tiktok ai video {} submit failed: {}", job_id, exc)
        await _fail(job_id, f"Wan 3.0 did not accept the job: {exc}")
        row = await get_job(job_id) or {**row, "status": "failed", "error": str(exc)}
        return row

    await _patch(job_id, {"task_id": task_id, "status": "processing", "provider_status": "PENDING"})
    logger.info(
        "tiktok ai video {} submitted (task={}, {}, {}s, est ${} / RM{})",
        job_id, task_id, res, dur, cost["usd"], cost["rm"],
    )
    task = asyncio.create_task(_drive(job_id, task_id))
    _running.add(task)
    task.add_done_callback(_running.discard)
    return await get_job(job_id) or {**row, "task_id": task_id, "status": "processing"}


async def _drive(job_id: str, task_id: str) -> None:
    deadline = asyncio.get_event_loop().time() + video.zai_video_max_wait_seconds()
    poll_errors = 0
    try:
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            try:
                result = await video.zai_video_service.fetch_result(task_id, provider=video.PROVIDER_DASHSCOPE)
            except video.ZaiVideoError as exc:
                poll_errors += 1
                logger.warning("tiktok ai video {} poll error {}: {}", job_id, poll_errors, exc)
                if poll_errors >= 8:
                    await _fail(job_id, f"Could not read the job status from Wan 3.0 ({exc}).")
                    return
                continue
            state = result.get("status")
            await _patch(job_id, {"provider_status": result.get("raw_status")})
            if state == "processing":
                continue
            if state == "fail":
                msg = result.get("message") or result.get("code") or "generation failed"
                await _fail(job_id, f"Wan 3.0 could not generate the clip: {msg}", result.get("raw_status"))
                return
            # success → copy the clip (provider URL lives 24 h) into our bucket
            data = await video.zai_video_service.download(str(result["video_url"]))
            key = await tiktok_media.store_bytes(data, "mp4")
            await _patch(
                job_id,
                {"status": "ready", "video_key": key, "video_bytes": len(data), "finished_at": _iso_now()},
            )
            logger.info("tiktok ai video {} ready ({} KB)", job_id, len(data) // 1024)
            return
        await _fail(job_id, "Wan 3.0 took too long; the job was abandoned. Try again.", "TIMEOUT")
    except Exception as exc:  # noqa: BLE001 - the row must never stay 'processing'
        logger.exception("tiktok ai video {} crashed", job_id)
        await _fail(job_id, f"Unexpected error while finishing the clip: {type(exc).__name__}")


async def sync_stale(row: Dict[str, Any]) -> Dict[str, Any]:
    """A row still 'processing' after a backend restart has no driver. One
    poll from the GET path moves it on or fails it after the wait limit."""
    if row.get("status") != "processing" or not row.get("task_id"):
        return row
    created = row.get("created_at")
    try:
        ts = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
    except ValueError:
        age = 0
    if age > video.zai_video_max_wait_seconds() + 120:
        await _fail(str(row["id"]), "The job was abandoned (backend restarted). Try again.", "TIMEOUT")
        return {**row, "status": "failed"}
    return row
