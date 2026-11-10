"""Operator alerts on Telegram, so a merchant whose build was stopped gets
help quickly.

Two things send an alert the moment they happen:

- ``gate_failed``: the visual gate failed a page after auto-fix and one
  regeneration (``VISUAL_GATE_FAIL``); the merchant was told "Sila cuba
  lagi" and has no site.
- ``location_conflict``: ``/api/generate/start`` refused to start because
  the brief and the address name different places (the "Cerita sebut
  Melaka tapi alamat Kuala Lumpur" question). Sometimes a real mistake in
  the brief, sometimes the guard being wrong (kek's "gula melaka").

Each alert carries the merchant (business name, account email), the
website id (none yet for a refused start) and the reason, and is stored in
``ops_events`` (migration 060) for the weekly summary. A weekly summary
(builds, passed / failed, auto-fixes, photos dropped, refusals) goes out
every Monday morning Malaysia time.

Configuration (Render dashboard; never in code):
  TELEGRAM_BOT_TOKEN       the bot's token from @BotFather
  TELEGRAM_ALERT_CHAT_ID   the chat that receives alerts
  OPS_ALERT_IGNORE_USERS   comma-separated user ids or emails to leave out
                           of alerts and the summary (test accounts)

Without a token or chat id nothing is sent and the alert is only logged
(``OPS_ALERT ...``). Sending never blocks or fails a build.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from loguru import logger

TELEGRAM_API = "https://api.telegram.org"
#: The same alert (kind + account + reason) is not repeated within this
#: window: a merchant retrying three times is one alert, not three.
DEDUPE_SECONDS = float(os.getenv("OPS_ALERT_DEDUPE_SECONDS", "1800"))
MAX_TEXT = 3500  # Telegram caps a message at 4096 characters
_recent: Dict[Tuple[str, str, str], float] = {}

KIND_TITLES = {
    "gate_failed": "🚨 Build blocked by the visual gate",
    "location_conflict": "⚠️ Build refused before starting: location question",
    "gate_warning": "⚠️ Rebuilt page shipped with design problems the gate could not fix",
}


def _uuid(value: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(value))) if value else None
    except (ValueError, TypeError, AttributeError):
        return None


def telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip() and os.getenv("TELEGRAM_ALERT_CHAT_ID", "").strip())


def ignored_users() -> set:
    return {x.strip().lower() for x in os.getenv("OPS_ALERT_IGNORE_USERS", "").split(",") if x.strip()}


def is_ignored(user_id: Optional[str], email: Optional[str]) -> bool:
    skip = ignored_users()
    return bool(skip) and (str(user_id or "").lower() in skip or str(email or "").lower() in skip)


def format_alert(kind: str, *, business_name: str = "", email: str = "", user_id: str = "", website_id: str = "",
                 job_id: str = "", reason: str = "", details: Optional[Dict[str, Any]] = None) -> str:
    lines = [f"BinaApp {KIND_TITLES.get(kind, kind)}"]
    who = business_name or "(no business name)"
    acct = ", ".join(x for x in (email, user_id) if x)
    lines.append(f"Merchant: {who}" + (f" ({acct})" if acct else ""))
    lines.append(f"Website: {website_id or 'none yet (refused before a site was created)'}"
                 + (f"  Job: {job_id}" if job_id else ""))
    lines.append(f"Reason: {reason or '-'}")
    for key, value in (details or {}).items():
        if value:
            lines.append(f"{key}: {value}")
    text = "\n".join(lines)
    return text if len(text) <= MAX_TEXT else text[: MAX_TEXT - 1] + "…"


async def send_telegram(text: str, *, client: Optional[httpx.AsyncClient] = None) -> bool:
    """Plain text (no Markdown: a business name with * or _ must not break
    the message). False when not configured or the API refuses."""
    if not telegram_configured():
        return False
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_ALERT_CHAT_ID", "").strip()
    payload = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    try:
        if client is not None:
            resp = await client.post(f"{TELEGRAM_API}/bot{token}/sendMessage", json=payload)
        else:
            async with httpx.AsyncClient(timeout=10) as c:
                resp = await c.post(f"{TELEGRAM_API}/bot{token}/sendMessage", json=payload)
        if resp.status_code != 200:
            logger.warning(f"📣 Telegram alert refused: HTTP {resp.status_code} {resp.text[:200]}")
            return False
        return True
    except Exception as err:
        logger.warning(f"📣 Telegram alert failed: {type(err).__name__}: {err}")
        return False


def _record_event(row: Dict[str, Any]) -> None:
    """Best-effort insert into ops_events (migration 060)."""
    try:
        from app.core.supabase import get_supabase_client
        get_supabase_client().table("ops_events").insert(row).execute()
    except Exception as err:
        logger.warning(f"📣 ops_events insert skipped ({type(err).__name__}): {str(err)[:160]}")


async def _deliver(kind: str, text: str, row: Dict[str, Any]) -> None:
    await asyncio.to_thread(_record_event, row)
    sent = await send_telegram(text)
    logger.info(f"📣 OPS_ALERT kind={kind} sent={'yes' if sent else 'no (telegram not configured)' if not telegram_configured() else 'FAILED'} "
                + text.replace("\n", " | ")[:400])


def alert(kind: str, *, business_name: str = "", email: str = "", user_id: str = "", website_id: str = "",
          job_id: str = "", reason: str = "", details: Optional[Dict[str, Any]] = None) -> bool:
    """Record and send one alert in the background. Returns False when the
    account is ignored or the same alert went out within DEDUPE_SECONDS."""
    if is_ignored(user_id, email):
        logger.info(f"📣 OPS_ALERT kind={kind} skipped: ignored account {email or user_id}")
        return False
    key = (kind, str(user_id or email or business_name), re.sub(r"\s+", " ", reason or "")[:120])
    now = time.monotonic()
    for k, t in list(_recent.items()):
        if now - t > DEDUPE_SECONDS:
            _recent.pop(k, None)
    if key in _recent:
        logger.info(f"📣 OPS_ALERT kind={kind} suppressed (same alert within {DEDUPE_SECONDS:.0f}s)")
        return False
    _recent[key] = now
    text = format_alert(kind, business_name=business_name, email=email, user_id=user_id, website_id=website_id,
                        job_id=job_id, reason=reason, details=details)
    extra = dict(details or {})
    if user_id and not _uuid(user_id):
        extra["user_id"] = str(user_id)  # "anonymous" etc.: the column is a uuid
    row = {
        "kind": kind, "business_name": (business_name or "")[:200], "email": (email or "")[:200] or None,
        "user_id": _uuid(user_id), "website_id": _uuid(website_id), "job_id": job_id or None,
        "reason": (reason or "")[:1000], "details": extra,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        loop.create_task(_deliver(kind, text, row))
    else:
        asyncio.run(_deliver(kind, text, row))
    return True


# ---------------------------------------------------------------------------
# Weekly summary
# ---------------------------------------------------------------------------

_DROPPED_RE = re.compile(r"dropped_mismatched_photos\((\d+)\)")


def summarize(jobs: Iterable[Dict[str, Any]], events: Iterable[Dict[str, Any]], *, since: datetime, until: datetime) -> Dict[str, Any]:
    """Counts for the week from generation_jobs rows and ops_events rows
    (ignored accounts already filtered out by the caller)."""
    s = {"builds": 0, "completed": 0, "failed": 0, "processing": 0, "gate_passed": 0, "gate_failed": 0,
         "gate_not_run": 0, "auto_fixed": 0, "photos_dropped": 0, "photo_free_hero": 0, "regenerated": 0,
         "location_refusals": 0, "gate_alerts": 0, "gate_warnings": 0, "design_scores": [],
         "since": since, "until": until}
    for job in jobs:
        s["builds"] += 1
        status = str(job.get("status") or "")
        if status == "completed":
            s["completed"] += 1
        elif status == "failed":
            s["failed"] += 1
        else:
            s["processing"] += 1
        gate = ((job.get("validation") or {}).get("visual_gate") or {}) if isinstance(job.get("validation"), dict) else {}
        if not gate or not gate.get("rendered", "checks" in gate):
            s["gate_not_run"] += 1
            continue
        if gate.get("passed"):
            s["gate_passed"] += 1
        else:
            s["gate_failed"] += 1
        score = ((gate.get("vision") or {}).get("design") or {}).get("score") if isinstance(gate.get("vision"), dict) else None
        if isinstance(score, (int, float)):
            s["design_scores"].append(float(score))
        fixes = [str(f) for f in (gate.get("fixes") or [])]
        if fixes:
            s["auto_fixed"] += 1
        for f in fixes:
            m = _DROPPED_RE.search(f)
            if m:
                s["photos_dropped"] += int(m.group(1))
            if f == "photo_free_hero":
                s["photo_free_hero"] += 1
            if f == "regenerated":
                s["regenerated"] += 1
    for ev in events:
        if ev.get("kind") == "location_conflict":
            s["location_refusals"] += 1
        elif ev.get("kind") == "gate_failed":
            s["gate_alerts"] += 1
        elif ev.get("kind") == "gate_warning":
            s["gate_warnings"] += 1
    return s


def format_summary(s: Dict[str, Any]) -> str:
    span = f"{s['since']:%d %b} – {s['until']:%d %b %Y}"
    pct = (100 * s["gate_passed"] / max(1, s["gate_passed"] + s["gate_failed"]))
    return "\n".join([
        f"📊 BinaApp weekly summary ({span})",
        f"Builds: {s['builds']} — completed {s['completed']}, failed {s['failed']}"
        + (f", still running {s['processing']}" if s["processing"] else ""),
        f"Visual gate: {s['gate_passed']} passed, {s['gate_failed']} failed ({pct:.0f}% pass)"
        + (f", not run on {s['gate_not_run']}" if s["gate_not_run"] else ""),
        f"Auto-fixed pages: {s['auto_fixed']} — photos dropped {s['photos_dropped']}, photo-free hero "
        f"{s['photo_free_hero']}, regenerated {s['regenerated']}",
        f"Refused before starting (location question): {s['location_refusals']}",
        f"Gate-failure alerts sent: {s['gate_alerts']}"
        + (f"; rebuilt pages shipped with problems: {s['gate_warnings']}" if s.get("gate_warnings") else ""),
        (f"Design score (reviewer, 1-10): average {sum(s['design_scores']) / len(s['design_scores']):.1f} over "
         f"{len(s['design_scores'])} pages, lowest {min(s['design_scores']):.0f}") if s.get("design_scores")
        else "Design score: no scored pages this week",
    ])


def _fetch_week(since: datetime) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    from app.core.supabase import get_supabase_client
    sb = get_supabase_client()
    iso = since.isoformat()
    jobs: List[Dict[str, Any]] = []
    start = 0
    while True:
        page = (sb.table("generation_jobs").select("job_id,status,user_id,validation,created_at")
                .gte("created_at", iso).order("created_at").range(start, start + 999).execute().data or [])
        jobs += page
        if len(page) < 1000:
            break
        start += 1000
    try:
        events = sb.table("ops_events").select("kind,user_id,email,created_at").gte("created_at", iso).execute().data or []
    except Exception as err:
        logger.warning(f"📣 ops_events read skipped: {str(err)[:160]}")
        events = []
    return jobs, events


async def send_weekly_summary(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    jobs, events = await asyncio.to_thread(_fetch_week, since)
    skip = ignored_users()
    if skip:
        jobs = [j for j in jobs if str(j.get("user_id") or "").lower() not in skip]
        events = [e for e in events if str(e.get("user_id") or "").lower() not in skip and str(e.get("email") or "").lower() not in skip]
    text = format_summary(summarize(jobs, events, since=since, until=now))
    sent = await send_telegram(text)
    logger.info(f"📣 OPS_WEEKLY sent={'yes' if sent else 'no'} " + text.replace("\n", " | "))
    return text


_weekly_scheduler = None


def start_weekly_summary() -> bool:
    """Every Monday 08:23 Malaysia time (in-process; one instance)."""
    global _weekly_scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except Exception:
        logger.warning("📣 Weekly summary not scheduled: APScheduler unavailable")
        return False
    if _weekly_scheduler is not None:
        return True
    _weekly_scheduler = AsyncIOScheduler(timezone="Asia/Kuala_Lumpur",
                                         job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600})
    _weekly_scheduler.add_job(send_weekly_summary, CronTrigger(day_of_week="mon", hour=8, minute=23,
                                                               timezone="Asia/Kuala_Lumpur"),
                              id="ops_weekly_summary", replace_existing=True)
    _weekly_scheduler.start()
    logger.info(f"📣 Weekly ops summary scheduled (Mondays 08:23 MYT); telegram={'configured' if telegram_configured() else 'NOT configured'}")
    return True
