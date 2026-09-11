"""Hero video background — a GLM-generated clip behind the hero, credit-free
to apply and remove.

    GET    /api/v1/websites/hero-video/options            style presets
    POST   /api/v1/websites/hero-video/prepare            start a clip with NO site yet
    GET    /api/v1/websites/hero-video/jobs/{job_id}      read its state; `ready` = stored, waiting
    GET    /api/v1/websites/{id}/hero-video               what the page has now
    POST   /api/v1/websites/{id}/hero-video/generate      start a video job for a site
    GET    /api/v1/websites/{id}/hero-video/jobs/{job_id} read its state (never polls the provider)
    PATCH  /api/v1/websites/{id}/hero-video               change overlay / text / mobile
    DELETE /api/v1/websites/{id}/hero-video               remove it

WITH THE PAGE, NOT AFTER IT
---------------------------
The /create page prepares the clip the moment generation starts (photo,
style and description are all known; the page takes minutes to build) and
sends the job id to /api/publish, which stages a ``ready`` clip into the
page it uploads (stage_prepared_hero_video) and confirms or attaches the
job once the site is live (settle_prepared_hero_video). The site goes live
carrying its video; a clip still rendering at publish is applied by the
server driver the moment it lands.

TWO HALVES
----------
1. MAKING the clip is an AI call (DashScope wan3.0-video, or Z.ai CogVideoX,
   via ``zai_video_service``). It is asynchronous on the provider's side, so
   it is asynchronous here: ``generate`` returns a job id at once and a
   server-side driver task (``_drive_hero_video_job``) is the ONE thing that
   polls the provider, stores the clip on Cloudinary, patches the page and
   republishes. The dashboard's ``jobs/{job_id}`` poll only reads the job.
   Every state change is mirrored to the ``hero_video_jobs`` table
   (``services/hero_video_jobs``): on startup ``resume_hero_video_jobs``
   picks up whatever the previous process was doing, and the stuck sweep
   (``sweep_stuck_hero_video_jobs``) fails anything that outlived the hard
   timeout, whatever the website's own status is.
2. PUTTING it on the page (and every later tweak or removal) is a
   deterministic HTML patch from ``hero_video_patcher``: no AI, no quota, no
   content drift. Same contract as the Design Studio.

GATES
-----
* HERO_VIDEO_ENABLED (env, default false): off → every route 404s.
* Paid per clip: ``plan_features.hero_video_access`` — free for admin /
  plan feature / env switch, otherwise one hero_video add-on credit (RM5)
  consumed once the provider accepts and refunded if it never delivers.
* One in-flight job per site, a small per-user concurrency cap, and a
  per-site daily submit cap — generation costs real money.

QUOTA NOTE (protected zone): nothing here touches check_limit or
usage_tracking. The ONLY credit it moves is the hero_video add-on credit
(use_addon_credit on accept, refund_addon_credit on a failed delivery).

PUBLISH SAFETY
--------------
Identical to the theme and contact edit paths (the mimba rule): patch the
LIVE storage snapshot when the site is published, fall back to the DB blob,
only ever accept a structurally balanced base, refuse to publish an
unbalanced result, and change nothing when no safe base exists.
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from typing import Dict, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services.hero_video_patcher import (
    DEFAULT_OVERLAY,
    DEFAULT_TEXT_MODE,
    HeroVideoSettings,
    apply_hero_video,
    build_settings,
    detect_hero_video,
    find_hero_open_tag,
    needs_style_upgrade,
    remove_hero_video,
)
from app.services.plan_features import (
    HERO_VIDEO_ADDON_TYPE,
    HERO_VIDEO_PRICE_RM,
    hero_video_access,
)
from app.services.subscription_service import subscription_service
from app.services.storage_service import storage_service
from app.services.hero_luminance import auto_overlay_opacity
from app.services import hero_video_jobs as ledger
from app.services.supabase_client import supabase_service
from app.services.zai_video_service import (
    ALLOWED_DURATIONS,
    DEFAULT_VIDEO_STYLE,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_READY,
    JOB_STATUS_STORING,
    VIDEO_STYLE_PRESETS,
    ZaiVideoError,
    build_hero_video_prompt,
    hero_video_enabled,
    zai_video_duration,
    zai_video_max_wait_seconds,
    hero_video_model,
    hero_video_provider,
    zai_video_service,
)

# Mounted under /websites in router.py.
router = APIRouter()

#: Seconds the dashboard should wait between polls.
POLL_INTERVAL_SECONDS = 8

#: How long a clip prepared during page generation waits for the publish
#: that will carry it. This was 45 minutes, and that lost a paid clip on
#: 2026-09-11: job b15c3794 was stored at 03:29:18, released as "never
#: published" at 04:14:18, and the merchant published at 04:25:55 — eleven
#: minutes too late for a clip that was sitting on Cloudinary. The site
#: went live static and a second clip was generated. Generation takes
#: minutes, review takes longer, and the Starter flow pays before it
#: publishes; a stored clip costs nothing to hold. One day: long enough
#: for any review, short enough that an abandoned draft's credit goes
#: back tomorrow. Survives restarts through the ledger.
PREPARED_CLAIM_WINDOW_SECONDS = 24 * 60 * 60


def prepared_claim_window_seconds() -> float:
    """HERO_VIDEO_CLAIM_WINDOW_SECONDS overrides the day. A held credit is
    the trade-off: a create page that loses its job id (reload) leaves the
    credit refunded only when the window closes."""
    try:
        return float(os.getenv("HERO_VIDEO_CLAIM_WINDOW_SECONDS", str(PREPARED_CLAIM_WINDOW_SECONDS)))
    except ValueError:
        return float(PREPARED_CLAIM_WINDOW_SECONDS)


#: How long a job may sit in 'storing' (download + Cloudinary + apply)
#: before the sweep treats it as hung. Aged from entering 'storing', so a
#: clip that SUCCEEDED late still gets its full allowance.
HERO_VIDEO_STORING_LIMIT_SECONDS = 300

#: Hard timeout on the provider task: ZAI_VIDEO_MAX_WAIT_SECONDS, default
#: 600. Why ten minutes: across every job in the 2026-09-04..11 production
#: logs, DashScope wan3.0-video SUCCEEDED in 2 m 15 s – 3 m 45 s and Z.ai in
#: ~65 s; DashScope documents PENDING queueing under load. 600 s is ~2.7×
#: the slowest clip observed, short enough that nobody is left watching a
#: spinner, and the moment a paid credit goes back. Past it the job is
#: FAILED with error='timeout', refunded, and HERO_VIDEO_TIMEOUT fires
#: (log + admin email). The provider task itself is abandoned — DashScope
#: has no cancel — so a late SUCCEEDED is wasted, deliberately.
#:
#: The sweep gives the driver this much slack past the limit before it
#: steps in, so the two never race over the same job.
HERO_VIDEO_SWEEP_GRACE_SECONDS = 120

#: Per-user in-flight jobs (across all their sites).
MAX_ACTIVE_JOBS_PER_USER = 2


def _max_per_site_per_day() -> int:
    try:
        return max(1, int(os.getenv("HERO_VIDEO_MAX_PER_SITE_PER_DAY", "5")))
    except ValueError:
        return 5


#: Process-local daily submit counter: {website_id: [monotonic timestamps]}.
#: Resets on restart; it is a cost guard, not an entitlement ledger.
_submits: Dict[str, list] = {}


def _count_recent_submits(website_id: str) -> int:
    cutoff = time.monotonic() - 24 * 3600
    stamps = [t for t in _submits.get(website_id, []) if t >= cutoff]
    _submits[website_id] = stamps
    return len(stamps)


def _record_submit(website_id: str) -> None:
    _submits.setdefault(website_id, []).append(time.monotonic())


def _reset_submit_counters() -> None:
    """Test hook."""
    _submits.clear()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class HeroVideoLook(BaseModel):
    """The presentation knobs — shared by generate and PATCH."""

    overlay: Literal["dark", "light", "none"] = DEFAULT_OVERLAY
    #: None = choose from the clip's own first-frame luminance (≈0.35 over
    #: dark footage, up to 0.70 over bright footage). A number is the
    #: merchant's explicit choice and is used as-is.
    overlay_opacity: Optional[float] = Field(default=None, ge=0.0, le=0.9)
    text_mode: Literal["auto", "light", "dark", "keep"] = DEFAULT_TEXT_MODE
    show_on_mobile: bool = True


class GenerateHeroVideoRequest(HeroVideoLook):
    #: A VIDEO_STYLE_PRESETS key.
    style: str = DEFAULT_VIDEO_STYLE
    #: Merchant's own scene description (Malay or English). Optional.
    prompt: Optional[str] = Field(default=None, max_length=400)
    duration: Optional[int] = None
    #: Animate an existing photo (image-to-video) instead of text-to-video.
    image_url: Optional[str] = Field(default=None, max_length=1000)


class PrepareHeroVideoRequest(GenerateHeroVideoRequest):
    """Generate a clip BEFORE the site exists — while the page is still
    being generated — so the publish that follows already carries it.
    Without a website row the prompt's business context comes from the
    form instead of the row."""

    business_name: str = Field(default="", max_length=120)
    business_type: str = Field(default="", max_length=60)
    description: str = Field(default="", max_length=2000)
    hero_image_prompt: str = Field(default="", max_length=400)


class PatchHeroVideoRequest(BaseModel):
    overlay: Optional[Literal["dark", "light", "none"]] = None
    overlay_opacity: Optional[float] = Field(default=None, ge=0.0, le=0.9)
    text_mode: Optional[Literal["auto", "light", "dark", "keep"]] = None
    show_on_mobile: Optional[bool] = None


# ---------------------------------------------------------------------------
# Gates and helpers
# ---------------------------------------------------------------------------

def _feature_gate() -> None:
    """404 when the flag is off — the feature does not exist."""
    if not hero_video_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


async def _fetch_serving_snapshot(subdomain: str) -> Optional[str]:
    """The live storage snapshot — see services/serving_snapshot.py."""
    from app.services.serving_snapshot import fetch_published_snapshot

    return await fetch_published_snapshot(subdomain, cache_bust="hero-video")


async def _load_owned_website(website_id: str, user_id: str) -> dict:
    website = await supabase_service.get_website(website_id)
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Website not found"
        )
    if website.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this website",
        )
    return website


async def _load_base_html(website: dict) -> Tuple[str, str]:
    """The HTML we are allowed to patch, and where it came from.

    Storage snapshot first for a published site, DB blob otherwise; only a
    structurally balanced document qualifies.
    """
    from app.utils.html_balance import is_html_balanced

    is_published = bool(website.get("status") == "published" and website.get("subdomain"))
    serving_html = None
    if is_published:
        serving_html = await _fetch_serving_snapshot(website["subdomain"])
    db_html = website.get("html_content") or ""

    for candidate, source in ((serving_html, "storage"), (db_html, "db")):
        if candidate and is_html_balanced(candidate)[0]:
            return candidate, source

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": "no_balanced_html_base",
            "message": (
                "Laman web ini belum ada HTML yang lengkap untuk ditambah "
                "video latar. Sila jana semula laman web anda dahulu."
            ),
        },
    )


async def _persist(website: dict, user_id: str, new_html: str) -> Tuple[bool, Optional[str]]:
    """Write the patched page to storage (if live) and the DB.

    Returns (live_site_updated, warning). Refuses an unbalanced result.
    """
    from app.utils.html_balance import is_html_balanced

    balanced, unbalanced = is_html_balanced(new_html)
    if not balanced:
        logger.error(
            f"[hero-video] refusing to publish unbalanced HTML for "
            f"{website.get('subdomain')} (tags: {unbalanced})"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "rewrite_produced_unbalanced_html",
                "message": "Perubahan dibatalkan kerana struktur HTML tidak sah.",
            },
        )

    is_published = bool(website.get("status") == "published" and website.get("subdomain"))
    live_site_updated = False
    warning = None
    if is_published:
        try:
            await storage_service.publish_website(
                subdomain=website["subdomain"],
                html_content=new_html,
                website_id=website["id"],
                user_id=user_id,
            )
            live_site_updated = True
        except Exception as storage_err:
            warning = "storage_refresh_failed"
            logger.warning(
                f"⚠️ Hero video: storage refresh failed "
                f"(DB will still be updated): {storage_err}"
            )

    await supabase_service.update_website(
        website["id"],
        {"html_content": new_html, "updated_at": datetime.utcnow().isoformat()},
    )
    return live_site_updated, warning


async def _upgrade_legacy_css(website: dict, user_id: str, html: str) -> Tuple[str, bool]:
    """Re-apply the page's own video settings with the current CSS.

    Returns (html_to_report, upgraded). On any failure the original HTML is
    reported unchanged and the reason is logged — the state read must still
    succeed so the editor panel can render.
    """
    from app.utils.html_balance import is_html_balanced

    try:
        current = detect_hero_video(html)
        if not current or not is_html_balanced(html)[0]:
            return html, False
        settings = build_settings(**current)
        patched = apply_hero_video(html, settings)
        if not patched.changed or patched.html == html:
            return html, False
        await _record_video_on_row(website["id"], settings)
        live, warning = await _persist(website, user_id, patched.html)
        logger.info(
            f"🎬 Hero video CSS upgraded for {website.get('id')} "
            f"(live={live}, warning={warning})"
        )
        return patched.html, True
    except Exception as exc:  # noqa: BLE001 - a read must never fail on this
        logger.warning(f"🎬 Hero video CSS upgrade skipped for {website.get('id')}: {exc}")
        return html, False


def _access_fields(access: Dict) -> Dict:
    return {
        "allowed": access["allowed"],
        "free_access": access["free"],
        "credits": access["credits"],
        "price_rm": access["price_rm"],
        "addon_type": access["addon_type"],
        # Free plan: the panel offers the Starter upgrade instead of a credit.
        "requires_upgrade": bool(access.get("requires_upgrade", False)),
    }


async def _refund_if_charged(job) -> None:
    """A paid job the provider never delivered gives its credit back, once.
    Logged loudly either way; a refund that fails is a support case, not a
    reason to fail the poll."""
    if not job.charged or job.refunded:
        return
    # One refund per job, decided by the ledger row, not by whichever
    # process happens to hold a copy of the job: a conditional PATCH on
    # refunded=false that only one caller can win. A ledger that cannot
    # answer does not block the refund — the merchant's money outranks a
    # possible double credit, and the failure is logged.
    won = await ledger.mark_refunded(job.job_id)
    if won is False:
        logger.warning(f"↩️ Hero video job {job.job_id} was already refunded (ledger) — not refunding again")
        job.refunded = True
        return
    if won is None:
        logger.error(f"↩️ Hero video job {job.job_id}: ledger could not confirm the refund claim — refunding anyway")
    try:
        ok = await subscription_service.refund_addon_credit(job.user_id, HERO_VIDEO_ADDON_TYPE)
    except Exception as exc:  # noqa: BLE001 — a refund that raises is a support case, logged below
        logger.error(
            f"🎬 Hero video credit refund RAISED for job {job.job_id} "
            f"(user {job.user_id}): {exc!r} — refund manually"
        )
        ok = False
    job.refunded = ok
    if ok:
        logger.info(f"↩️ Hero video credit refunded for job {job.job_id} ({job.error})")
    else:
        logger.error(
            f"🎬 Hero video credit refund FAILED for job {job.job_id} "
            f"(user {job.user_id}, error={job.error}) — refund manually"
        )


async def _ledger_save(job) -> bool:
    """Mirror the job to ``hero_video_jobs``. A failure is logged by the
    ledger and returned, never raised: the clip must still land. If the
    ledger says another process now owns the row, the job is flagged so
    this process's driver stops."""
    result = await ledger.save(job)
    if result == ledger.SAVE_LOST:
        job.ownership_lost = True
    return result == ledger.SAVE_OK


async def _job_is_ours_to_end(job) -> bool:
    """Before a terminal write: is this job still ours, and still open?

    Two processes can hold the same job across a deploy, and the sweep can
    rebuild one from its row. So read the row: already terminal → another
    process finished it (sync our copy, do nothing); leased by a live
    process that is not us → theirs to end. A ledger that cannot be read
    answers True: the in-memory ``refunded`` flag still stops a double
    refund within this process, and a stuck job must still be ended."""
    row = await ledger.load(job.job_id)
    if not row:
        return True
    if row.get("status") in ledger.TERMINAL_STATUSES:
        logger.warning(
            f"[hero-video] job {job.job_id} is already {row.get('status')} in the ledger "
            f"(error={row.get('error')}, refunded={row.get('refunded')}) — another process "
            "ended it; adopting that outcome, not refunding again"
        )
        job.status = str(row.get("status"))
        job.error = row.get("error")
        job.refunded = bool(row.get("refunded")) or job.refunded
        return False
    if ledger.lease_is_live(row):
        logger.warning(
            f"[hero-video] job {job.job_id} is leased by process {str(row.get('lease_owner'))[:8]} "
            f"until {row.get('lease_until')} — leaving it to that process"
        )
        return False
    return True


async def _fail_job(job, error: str, *, detail: str = "") -> None:
    """The ONE way a job ends in failure: ownership check, state, ledger,
    refund, and a single ERROR line naming the job, the site, the provider
    task, the last provider state and the reason. Callers hold
    ``job.lock`` wherever a driver could be racing them.

    One refund per job is enforced by the ledger (mark_refunded), not by
    this process's memory, so a job failed here and again after a restart
    is still refunded once."""
    if not await _job_is_ours_to_end(job):
        return
    job.status = JOB_STATUS_FAILED
    job.error = error
    logger.error(
        f"[hero-video] job {job.job_id} FAILED error={error} "
        f"website={job.website_id or '-'} user={job.user_id} provider={job.provider} "
        f"task={job.task_id} provider_status={job.provider_status or '-'} "
        f"poll_errors={job.poll_errors} age={int(job.age_seconds())}s"
        + (f" — {detail}" if detail else "")
    )
    await _ledger_save(job)
    if job.ownership_lost:
        logger.error(f"[hero-video] job {job.job_id}: another process owns this job — not refunding here")
        return
    if job.charged and not job.refunded:
        await _refund_if_charged(job)
        await _ledger_save(job)


async def _alert_timeout(job) -> None:
    """A job outlived the hard timeout. One greppable CRITICAL line
    (``HERO_VIDEO_TIMEOUT``) plus an admin email through the existing
    notification path, so it surfaces without anyone reading logs. Never
    raises — it runs from the driver and from the sweep."""
    limit = int(zai_video_max_wait_seconds())
    summary = (
        f"job={job.job_id} website={job.website_id or '-'} user={job.user_id} "
        f"provider={job.provider} task={job.task_id} waited={int(job.age_seconds())}s "
        f"limit={limit}s last_provider_status={job.provider_status or '-'} "
        f"poll_errors={job.poll_errors} charged={job.charged} refunded={job.refunded}"
    )
    logger.critical(f"🚨 HERO_VIDEO_TIMEOUT {summary}")
    try:
        from app.services.email_service import email_service

        sent = await email_service.send_admin_notification(
            subject=f"Hero video job timed out ({job.job_id[:8]})",
            message=(
                f"A hero-video job outlived its {limit}s limit and was marked failed. "
                "The provider task may still finish on its own; the merchant's credit "
                "has been refunded if one was charged."
            ),
            notification_type="error",
            details={
                "job_id": job.job_id,
                "website_id": job.website_id or "-",
                "user_id": job.user_id,
                "provider": job.provider,
                "provider_task": job.task_id,
                "last_provider_status": job.provider_status or "-",
                "poll_errors": job.poll_errors,
                "waited_seconds": int(job.age_seconds()),
                "charged": job.charged,
                "refunded": job.refunded,
            },
        )
        if not sent:
            logger.error(
                f"🚨 HERO_VIDEO_TIMEOUT admin email NOT sent for job {job.job_id} "
                "(SMTP unconfigured or rejected) — the CRITICAL line above is the alert"
            )
    except Exception as exc:  # noqa: BLE001 — the alert must never take the sweep down
        logger.error(f"🚨 HERO_VIDEO_TIMEOUT admin email raised for job {job.job_id}: {exc!r}")


async def _record_video_on_row(website_id: str, settings: Optional[HeroVideoSettings]) -> bool:
    """Write the clip the site is supposed to carry onto the websites row
    (hero_video_url / hero_video_poster_url / hero_video_settings), or
    clear it. Written BEFORE the HTML is patched so the row says what the
    page should show even if the process dies between the two writes.
    Returns False — after an ERROR line — when PostgREST updated no row."""
    payload = {
        "hero_video_url": settings.video_url if settings else None,
        "hero_video_poster_url": settings.poster_url if settings else None,
        "hero_video_settings": settings.as_dict() if settings else None,
        "hero_video_updated_at": datetime.utcnow().isoformat(),
    }
    ok = await supabase_service.update_website(website_id, payload)
    if not ok:
        logger.error(
            f"[hero-video] websites row {website_id}: hero_video_* write updated no row "
            f"(migration 056 applied?) — the page is still patched, the row is not"
        )
    return ok


async def _submit_or_502(prompt: str, *, duration: Optional[int], image_url: Optional[str], label: str) -> Tuple[str, str]:
    """Hand the prompt to the provider; a refusal becomes a 502 that says
    whether it is the merchant's to retry or a server-side key problem."""
    try:
        return await zai_video_service.submit_with_fallback(
            prompt, duration=duration, image_url=image_url
        )
    except ZaiVideoError as exc:
        logger.error(f"[hero-video] submit failed for {label}: {exc}")
        text = str(exc)
        # A key/permission problem is a server-side configuration issue, not
        # something the merchant can retry their way out of — say so.
        config_problem = "401" in text or "403" in text or "not configured" in text
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "provider_not_configured" if config_problem else "video_submit_failed",
                "message": (
                    "Penyedia video belum dikonfigurasi dengan betul di pelayan "
                    "(kunci API ditolak). Sila hubungi sokongan BinaApp."
                    if config_problem
                    else "Penjanaan video gagal dimulakan. Sila cuba lagi sebentar."
                ),
            },
        )


def _payment_required(access: Dict) -> HTTPException:
    # Paid per clip. No free access and no prepaid credit → 402 with
    # what it costs, so the UI can offer the purchase right there.
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "error": "payment_required",
            "message": (
                f"Video latar hero berharga RM{HERO_VIDEO_PRICE_RM:.0f} setiap klip. "
                "Beli 1 kredit video untuk meneruskan."
            ),
            "price_rm": HERO_VIDEO_PRICE_RM,
            "addon_type": HERO_VIDEO_ADDON_TYPE,
            "credits": access["credits"],
        },
    )


def _too_many_jobs() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "too_many_jobs",
            "message": "Terlalu banyak video sedang dijana. Sila tunggu sebentar.",
        },
    )


def _daily_limit_reached() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "daily_limit_reached",
            "message": "Had harian video untuk laman web ini telah dicapai. Cuba lagi esok.",
        },
    )


async def _charge_if_paid(access: Dict, user_id: str, task_id: str, label: str) -> bool:
    """Charge only now: the provider has ACCEPTED the job, so a rejected
    submit never costs the merchant anything. If the clip then fails to
    arrive, the driver refunds this credit."""
    if access["free"]:
        return False
    charged = await subscription_service.use_addon_credit(user_id, HERO_VIDEO_ADDON_TYPE)
    if not charged:
        logger.error(
            f"🎬 Hero video credit could NOT be consumed for {user_id} "
            f"({label}) although the provider accepted task {task_id}"
        )
    return charged


def _current_state(html: str) -> Dict:
    current = detect_hero_video(html or "")
    hero, how = find_hero_open_tag(remove_hero_video(html or "").html) if html else (None, "")
    return {
        "has_video": current is not None,
        "settings": current,
        "hero_found": hero is not None,
        "hero_match": how,
    }


def _settings_from_look(look: HeroVideoLook, video_url: str, poster_url: Optional[str]) -> HeroVideoSettings:
    return build_settings(
        video_url=video_url,
        poster_url=poster_url,
        overlay=look.overlay,
        overlay_opacity=look.overlay_opacity,
        text_mode=look.text_mode,
        show_on_mobile=look.show_on_mobile,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/hero-video/options")
async def get_hero_video_options():
    """The style presets and generation defaults behind the picker UI.

    Public like the Design Studio catalogue: it is static and carries no
    merchant data.
    """
    _feature_gate()
    return {
        "success": True,
        "model": hero_video_model(),
        "provider": hero_video_provider(),
        # Paid per clip: one hero_video add-on credit (RM5) unless the
        # account has free access (admin / plan feature / env switch).
        "price_rm": HERO_VIDEO_PRICE_RM,
        "addon_type": HERO_VIDEO_ADDON_TYPE,
        "duration_seconds": zai_video_duration(),
        "durations": list(ALLOWED_DURATIONS),
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "styles": [
            {"key": key, "label_ms": preset["label_ms"], "label_en": preset["label_en"]}
            for key, preset in VIDEO_STYLE_PRESETS.items()
        ],
        "overlays": ["dark", "light", "none"],
        "text_modes": ["auto", "light", "dark", "keep"],
    }


@router.get("/hero-video/access")
async def get_hero_video_access(current_user: dict = Depends(get_current_user)):
    """Whether THIS account may generate: free access, or prepaid credits.

    The create page asks this before there is a website to ask about, so it
    can show the price and the credit balance next to the toggle.
    """
    _feature_gate()
    return {"success": True, **await hero_video_access(current_user.get("sub"))}


@router.post("/hero-video/prepare", status_code=status.HTTP_202_ACCEPTED)
async def prepare_hero_video(
    body: PrepareHeroVideoRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start the clip while the page is still being generated.

    The merchant's hero photo, style and description are all known the
    moment they press Generate, and the page takes minutes to build. Made
    here, the clip is usually stored before the merchant has finished
    reviewing the page — and the publish that follows sends this job's id
    so the page goes live WITH its video, instead of static for the two or
    three minutes a post-publish job took (the "again no video" report on
    every site the merchant checked right after publishing).

    No website row yet: the job is registered without one, the server
    drives it to ``ready``, and ``/api/publish`` claims it. Unclaimed after
    PREPARED_CLAIM_WINDOW_SECONDS → refunded and forgotten.
    """
    _feature_gate()
    user_id = current_user.get("sub")

    access = await hero_video_access(user_id)
    if not access["allowed"]:
        raise _payment_required(access)
    if zai_video_service.active_jobs_for_user(user_id) >= MAX_ACTIVE_JOBS_PER_USER:
        raise _too_many_jobs()
    # No site to key the daily cap on yet: cap the account instead.
    daily_key = f"user:{user_id}"
    if _count_recent_submits(daily_key) >= _max_per_site_per_day():
        raise _daily_limit_reached()

    from app.services.business_types import normalize_business_type

    style = body.style if body.style in VIDEO_STYLE_PRESETS else DEFAULT_VIDEO_STYLE
    prompt = build_hero_video_prompt(
        business_name=body.business_name,
        business_type=normalize_business_type(body.business_type) or "",
        description=body.description,
        style=style,
        custom_prompt=body.prompt or "",
        hero_image_prompt=body.hero_image_prompt,
    )

    image_url = (body.image_url or "").strip() or None
    if image_url and not image_url.startswith("https://"):
        image_url = None

    task_id, provider = await _submit_or_502(
        prompt, duration=body.duration, image_url=image_url, label=f"prepare/{user_id}"
    )
    _record_submit(daily_key)
    charged = await _charge_if_paid(access, user_id, task_id, "prepared, no site yet")

    job = zai_video_service.register_job(
        task_id=task_id,
        website_id="",
        user_id=user_id,
        prompt=prompt,
        settings=HeroVideoLook(**body.model_dump(include=set(HeroVideoLook.model_fields))).model_dump(),
        charged=charged,
        provider=provider,
        image_url=image_url,
    )
    logger.info(
        f"🎬 Hero video job {job.job_id} prepared ahead of publish for user {user_id} "
        f"(style={style}, provider={provider}, task={task_id})"
    )
    await ledger.create(job)
    job.driver_task = asyncio.create_task(_drive_hero_video_job(job, "", user_id))
    return {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "prompt": prompt,
        "message": "Video latar hero sedang dijana bersama laman anda dan akan dipasang semasa terbit.",
    }


@router.get("/hero-video/jobs/{job_id}")
async def poll_prepared_hero_video_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll a job prepared ahead of publish. ``ready`` means the clip is
    stored and waiting for the publish that will carry it."""
    _feature_gate()
    user_id = current_user.get("sub")
    job = zai_video_service.get_job(job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "job_not_found",
                "message": "Tugasan video tidak dijumpai atau telah tamat. Sila cuba lagi.",
            },
        )
    # Read-only: the driver is the only poller (see poll_hero_video_job).
    body = {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}
    if job.status in (JOB_STATUS_READY, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
        body.update(job.result_payload or {})
    return body


@router.get("/{website_id}/hero-video")
async def get_hero_video(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """What the page is showing now, plus any in-flight job."""
    _feature_gate()
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)

    html = ""
    source = "none"
    if website.get("status") == "published" and website.get("subdomain"):
        html = await _fetch_serving_snapshot(website["subdomain"]) or ""
        source = "storage" if html else source
    if not html:
        html = website.get("html_content") or ""
        source = "db" if html else source

    upgraded = False
    if html and needs_style_upgrade(html):
        # Self-heal: the page carries the first release's stacking CSS, which
        # broke heroes with absolutely-positioned decoration. Re-apply the
        # same clip and settings with the current CSS and republish. Wrapped
        # so a persist failure can never turn a read into an error.
        html, upgraded = await _upgrade_legacy_css(website, user_id, html)

    job = zai_video_service.active_job_for_website(website_id)
    return {
        "success": True,
        "website_id": website_id,
        "source": source,
        **_access_fields(await hero_video_access(user_id)),
        "job": job.to_dict() if job else None,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "upgraded_css": upgraded,
        **_current_state(html),
    }


@router.post("/{website_id}/hero-video/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_hero_video(
    website_id: str,
    body: GenerateHeroVideoRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start a GLM video generation for this site's hero.

    Returns at once with a job id; poll ``jobs/{job_id}``. The look settings
    in the body are remembered on the job and applied when the clip lands.
    """
    _feature_gate()
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)

    access = await hero_video_access(user_id)
    if not access["allowed"]:
        raise _payment_required(access)

    # Confirm there is a page — and a hero — to put the video on BEFORE we
    # spend money generating one.
    base_html, _ = await _load_base_html(website)
    hero, _ = find_hero_open_tag(remove_hero_video(base_html).html)
    if hero is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "hero_not_found",
                "message": "Bahagian hero tidak dijumpai pada laman web ini.",
            },
        )

    if zai_video_service.active_job_for_website(website_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "job_in_progress",
                "message": "Video untuk laman web ini sedang dijana. Sila tunggu.",
            },
        )
    if zai_video_service.active_jobs_for_user(user_id) >= MAX_ACTIVE_JOBS_PER_USER:
        raise _too_many_jobs()
    if _count_recent_submits(website_id) >= _max_per_site_per_day():
        raise _daily_limit_reached()

    style = body.style if body.style in VIDEO_STYLE_PRESETS else DEFAULT_VIDEO_STYLE
    prompt = build_hero_video_prompt(
        business_name=website.get("business_name") or website.get("name") or "",
        # Real since migration 055 — was '' on every row before it.
        business_type=website.get("business_type") or "",
        description=website.get("description") or "",
        style=style,
        custom_prompt=body.prompt or "",
        # The same hero visual the still image was generated from.
        hero_image_prompt=website.get("hero_image_prompt") or "",
    )

    image_url = (body.image_url or "").strip() or None
    if image_url and not image_url.startswith("https://"):
        image_url = None

    task_id, provider = await _submit_or_502(
        prompt, duration=body.duration, image_url=image_url, label=website_id
    )
    _record_submit(website_id)
    charged = await _charge_if_paid(access, user_id, task_id, f"website {website_id}")

    job = zai_video_service.register_job(
        task_id=task_id,
        website_id=website_id,
        user_id=user_id,
        prompt=prompt,
        settings=HeroVideoLook(**body.model_dump(include=set(HeroVideoLook.model_fields))).model_dump(),
        charged=charged,
        provider=provider,
        image_url=image_url,
    )
    logger.info(
        f"🎬 Hero video job {job.job_id} started for {website_id} "
        f"(style={style}, provider={provider}, task={task_id})"
    )
    # The server polls the provider from here on — and ONLY the server.
    # Before 2026-09-10 the browser's poll was the only thing that advanced
    # a job (website malan, task 144693e5: five polls over 56 seconds, then
    # silence; the clip was made and never applied). After that the driver
    # and the browser poll both polled the provider. Now the browser poll
    # reads state and nothing else, and the ledger row written here is
    # what a restarted process resumes from.
    await ledger.create(job)
    job.driver_task = asyncio.create_task(_drive_hero_video_job(job, website_id, user_id))
    return {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "prompt": prompt,
        "message": "Video sedang dijana (1–3 minit) dan akan dipasang secara automatik.",
    }


@router.get("/{website_id}/hero-video/jobs/{job_id}")
async def poll_hero_video_job(
    website_id: str,
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Report a job's state. READ-ONLY.

    The server-side driver is the only thing that polls the provider,
    stores the clip and patches the page. Until 2026-09-11 this handler
    polled the provider too — two pollers per job, one of them on a
    request path a phone fires every 8 s, and a DB read of the website
    row on each — so a job's progress depended on which caller got the
    lock first. Now it returns what the driver has recorded, nothing more,
    and touches no other table.
    """
    _feature_gate()
    user_id = current_user.get("sub")
    job = zai_video_service.get_job(job_id)
    if not job or job.website_id != website_id or job.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "job_not_found",
                "message": "Tugasan video tidak dijumpai atau telah tamat. Sila cuba lagi.",
            },
        )
    body = {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}
    if job.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
        body.update(job.result_payload or {})
    elif job.status == JOB_STATUS_STORING:
        body["message"] = "Video sedia — sedang dipasang pada laman web."
    return body


async def _advance_hero_video_job(
    job, website_id: str, user_id: str, website: Optional[dict] = None
) -> bool:
    """One step of the job, taken by the driver. Every outcome is explicit
    and logged — there is no branch that changes nothing and says nothing:

      over the hard timeout      → FAILED 'timeout' + refund + HERO_VIDEO_TIMEOUT alert
      the poll itself raised     → still processing; poll_errors+1,
                                   provider_status='http_<code>'; bounded by the timeout
      provider says FAILED/…     → FAILED 'generation_failed' + refund (full body in the log)
      provider says SUCCEEDED    → 'storing', clip handed to the finaliser
      provider still running     → still processing; raw state recorded,
                                   lease renewed, last_polled_at stamped

    Returns True only on the call that hands off. Idempotent on terminal
    states and serialised by the job lock, so the finaliser runs exactly
    once even if the sweep and the driver race. The timeout alert (a
    CRITICAL line and an SMTP send) runs after the lock is released, so a
    publish request waiting to settle this job is never held behind a
    mail server.

    ``website`` is the row when the caller already loaded it; the driver
    leaves it None and it is loaded only at hand-off, so a job in flight
    costs no reads.
    """
    handed_off, timed_out = await _advance_locked(job, website_id, user_id, website)
    if timed_out:
        await _alert_timeout(job)
    return handed_off


async def _advance_locked(
    job, website_id: str, user_id: str, website: Optional[dict]
) -> Tuple[bool, bool]:
    """(handed_off, timed_out) — see _advance_hero_video_job."""
    async with job.lock:
        if job.status != JOB_STATUS_PROCESSING:
            return False, False

        limit = zai_video_max_wait_seconds()
        if job.age_seconds() > limit:
            await _fail_job(job, "timeout", detail=f"outlived the {int(limit)}s limit")
            return False, job.status == JOB_STATUS_FAILED and job.error == "timeout"

        job.last_polled_wall = time.time()
        try:
            result = await zai_video_service.fetch_result(job.task_id, provider=job.provider)
        except ZaiVideoError as exc:
            # A failed POLL is not a failed JOB: DashScope answered one poll
            # with a bare 403 on 2026-09-11 04:28:18 and SUCCEEDED on the
            # next. Count it, record what it was, keep going; the hard
            # timeout above ends a poll that never recovers.
            job.poll_errors += 1
            job.provider_status = f"http_{exc.status_code}" if exc.status_code else "poll_error"
            job.provider_message = str(exc)[:500]
            logger.warning(
                f"[hero-video] job {job.job_id} poll error #{job.poll_errors} "
                f"({job.provider_status}): {exc} — still processing, "
                f"{max(0, int(limit - job.age_seconds()))}s left before timeout"
            )
            await _ledger_save(job)
            return False, False

        raw = str(result.get("raw_status") or "?")
        state_changed = raw != job.provider_status or job.poll_errors > 0
        job.poll_errors = 0
        job.provider_status = raw
        if result.get("message") or result.get("code"):
            job.provider_message = f"{result.get('code') or ''} {result.get('message') or ''}".strip()[:500]

        if result["status"] == "fail":
            await _fail_job(
                job, "generation_failed",
                detail=f"provider said {raw}: {job.provider_message or '(no message)'}",
            )
            return False, False
        if result["status"] != "success":
            if state_changed:
                logger.info(
                    f"[hero-video] job {job.job_id} still processing "
                    f"(provider_status={raw}, age={int(job.age_seconds())}s)"
                )
            # Every poll renews the lease and stamps last_polled_at, so a
            # process that dies mid-render is visible as a lapsed lease.
            await _ledger_save(job)
            return False, False

        # A job prepared ahead of publish has no site yet (job.website_id
        # is empty until /api/publish claims it): the finaliser stores the
        # clip and parks it as `ready`. Once attached — by the publish that
        # happened while the provider was still rendering — the finaliser
        # applies it to that site like any other job.
        target_id = job.website_id or website_id
        if website is None and target_id:
            try:
                website = await _load_owned_website_retrying(target_id, user_id)
            except HTTPException as exc:
                # The site is gone or changed hands mid-job (after three
                # reads, so a Supabase blip is not mistaken for that).
                # Nothing to patch; do not keep the merchant's money.
                await _fail_job(job, "website_unavailable", detail=str(exc.detail))
                return False, False

        # The provider is done. Download, Cloudinary, patch, storage and DB
        # writes run as a background task, never on a request path.
        job.status = JOB_STATUS_STORING
        job.storing_since = time.monotonic()
        logger.info(
            f"[hero-video] job {job.job_id} provider {raw} after {int(job.age_seconds())}s "
            f"— storing the clip{' for ' + target_id if target_id else ' (no site yet)'}"
        )
        await _ledger_save(job)
        job.finalize_task = asyncio.create_task(
            _finalize_hero_video_job(job, website, user_id, result["video_url"])
        )
        return True, False


async def _load_owned_website_retrying(website_id: str, user_id: str, attempts: int = 3):
    """get_website answers None for 'no such row' AND for any transport
    error, so one miss must not end a job whose clip is finished. Three
    reads with a short backoff; 403 (not the owner) is final at once."""
    last: Optional[HTTPException] = None
    for attempt in range(attempts):
        try:
            return await _load_owned_website(website_id, user_id)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                raise
            last = exc
            logger.warning(
                f"[hero-video] website {website_id} not readable (attempt {attempt + 1}/{attempts}): {exc.detail}"
            )
            if attempt + 1 < attempts:
                await asyncio.sleep(2 * (attempt + 1))
    raise last  # type: ignore[misc]


async def _drive_hero_video_job(job, website_id: str, user_id: str) -> None:
    """Advance the job to a terminal state whether or not a browser is
    polling. THE poller.

    Never dies on an unexpected exception: a driver that died left its
    job 'processing' forever, invisible to everything. A step that raises
    is logged with its traceback and the loop keeps going; the hard
    timeout inside _advance_hero_video_job ends any job that cannot make
    progress, and the sweep ends any job whose driver is gone. Exits
    quietly only when the registry no longer holds this job (a reset), so
    a stale driver never acts on a dead job.
    """
    try:
        while job.status == JOB_STATUS_PROCESSING:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            if zai_video_service.get_job(job.job_id) is not job:
                logger.warning(
                    f"[hero-video] driver for job {job.job_id} stopping: "
                    "the registry no longer holds this job"
                )
                return
            try:
                await _advance_hero_video_job(job, website_id, user_id)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — logged with traceback; the loop continues
                logger.exception(
                    f"[hero-video] driver step for job {job.job_id} raised; "
                    "retrying on the next tick (the hard timeout still applies)"
                )
            if job.ownership_lost:
                logger.error(
                    f"[hero-video] driver for job {job.job_id} stopping: another process owns the row"
                )
                zai_video_service.drop_job(job.job_id)
                return
        if job.website_id:
            return
        # Prepared ahead of publish and still unattached: wait for the
        # clip to be stored, then give the publish its claim window,
        # measured from the job's start so a resumed job does not get a
        # fresh day. A clip nobody published is not delivered — hand the
        # credit back rather than keep it for a video that never reached
        # a page.
        if job.finalize_task is not None:
            await asyncio.shield(job.finalize_task)
        if job.status != JOB_STATUS_READY:
            return
        # Sleep in slices and re-save each time: the save renews this
        # process's lease on the row, so a replacement instance knows the
        # clip is still held here and does not adopt it too.
        slice_seconds = ledger.lease_seconds_for(JOB_STATUS_READY) / 2
        while job.status == JOB_STATUS_READY:
            remaining = prepared_claim_window_seconds() - job.age_seconds()
            if remaining <= 0:
                break
            await asyncio.sleep(min(remaining, slice_seconds))
            if job.status == JOB_STATUS_READY and zai_video_service.get_job(job.job_id) is job:
                await _ledger_save(job)
                if job.ownership_lost:
                    logger.error(f"[hero-video] ready job {job.job_id} now owned elsewhere — releasing it here")
                    zai_video_service.drop_job(job.job_id)
                    return
        async with job.lock:
            if job.status != JOB_STATUS_READY:
                return
            await _fail_job(
                job, "unclaimed",
                detail=f"stored clip was never published within {int(prepared_claim_window_seconds())}s",
            )
    except asyncio.CancelledError:
        logger.warning(
            f"[hero-video] driver for job {job.job_id} cancelled at status={job.status} "
            "(shutdown?) — the ledger row resumes it on the next start"
        )
        raise
    except Exception:  # noqa: BLE001 — a driver must never die silently
        logger.exception(f"[hero-video] driver for job {job.job_id} crashed outside a step")


async def _store_clip(job, provider_video_url: str, *, website_id: str) -> bool:
    """Download the provider's clip into Cloudinary and settle the look.
    False (with the job failed and refunded) when storage fails."""
    try:
        stored = await zai_video_service.store(provider_video_url, website_id=website_id)
    except ZaiVideoError as exc:
        await _fail_job(job, "storage_failed", detail=str(exc))
        return False

    job.video_url = stored["video_url"]
    # The still shown while the clip loads, on data-saver phones, and
    # under prefers-reduced-motion. When the job had a hero photo, that
    # photo is the still: with image-to-video the clip opens on it
    # anyway, and with text-to-video the generic first frame is exactly
    # the "not my shop" picture we must not leave in the merchant's hero.
    job.poster_url = job.image_url or stored["poster_url"]

    look = HeroVideoLook(**job.settings)
    if look.overlay_opacity is None and look.overlay != "none":
        # Bug 5: a fixed 0.45 was fine over dark footage and unreadable
        # over bright footage. Measure the first frame instead — the
        # clip's own frame, since the scrim sits over the playing video.
        look.overlay_opacity = await auto_overlay_opacity(stored["poster_url"])
        job.settings = look.model_dump()
    return True


def _stored_settings(job) -> HeroVideoSettings:
    return _settings_from_look(HeroVideoLook(**job.settings), job.video_url, job.poster_url)


def _mark_applied(job, website: dict, patched, base_source: str, live: bool, warning: Optional[str]) -> None:
    job.applied = True
    job.live_site_updated = live
    job.result_payload = {
        "settings": patched.settings,
        "base_source": base_source,
        "html_content": patched.html,
        "message": (
            "Video latar hero telah dipasang."
            if live or website.get("status") != "published"
            else "Video disimpan, tetapi laman web langsung belum dikemas kini. Sila cuba lagi sebentar."
        ),
    }
    if warning:
        job.result_payload["warning"] = warning
    job.status = JOB_STATUS_COMPLETED
    logger.info(
        f"🎬 Hero video applied for {website['id']} "
        f"(base={base_source}, live={live}, {patched.summary()})"
    )


def _still_storing(job, step: str) -> bool:
    """The sweep may have ended this job while the finaliser was busy
    (a clip that took longer than the timeout to download). Check before
    each write so a failed-and-refunded job is not also applied."""
    if job.status == JOB_STATUS_STORING:
        return True
    logger.warning(
        f"[hero-video] job {job.job_id} is {job.status} (error={job.error}) — "
        f"stopping before {step}; the clip is stored at {job.video_url}"
    )
    return False


async def _apply_stored_clip(job, website: dict, user_id: str) -> None:
    """Record the clip on the websites row, patch it into the page,
    publish. In that order: the row says what the page SHOULD carry before
    the page is rewritten, so a crash between the two leaves evidence
    rather than a mystery. A failure here keeps the stored URLs on the job
    so the merchant can retry the apply without regenerating."""
    if not _still_storing(job, "writing the websites row"):
        return
    settings = _stored_settings(job)
    row_ok = await _record_video_on_row(website["id"], settings)
    if not _still_storing(job, "patching the page"):
        return
    try:
        base_html, base_source = await _load_base_html(website)
        patched = apply_hero_video(base_html, settings)
        if not patched.changed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "hero_not_found", "message": "Bahagian hero tidak dijumpai."},
            )
        if not _still_storing(job, "publishing the page"):
            await _record_video_on_row(website["id"], None)
            return
        live, warning = await _persist(website, user_id, patched.html)
    except HTTPException as exc:
        # The row must not claim a clip the page does not carry.
        await _record_video_on_row(website["id"], None)
        await _fail_job(
            job,
            exc.detail.get("error") if isinstance(exc.detail, dict) else "apply_failed",
            detail=str(exc.detail),
        )
        return
    if not row_ok and not warning:
        warning = "row_write_failed"
    async with job.lock:
        if not _still_storing(job, "marking the job completed"):
            return
        _mark_applied(job, website, patched, base_source, live, warning)
    await _ledger_save(job)


async def _apply_stored_clip_task(job, website: dict, user_id: str) -> None:
    """Background apply for a clip that is already stored (a prepared clip
    claimed by a publish, or a resumed job). Same guarantee as the
    finaliser: the job cannot be left in 'storing'."""
    try:
        await _apply_stored_clip(job, website, user_id)
    except Exception as exc:  # noqa: BLE001 — never leave a job stuck in 'storing'
        logger.exception(f"[hero-video] apply crashed for {job.job_id}: {exc}")
        await _fail_job(job, "apply_failed", detail=repr(exc))


async def _finalize_hero_video_job(job, website: Optional[dict], user_id: str, provider_video_url: str) -> None:
    """Store the clip, choose the overlay, patch the page, publish. Runs off
    the request path; the poll reads the outcome from the job.

    ``website`` is None for a job prepared ahead of publish: the clip is
    stored under the job's own id and parked as ``ready`` for the publish
    to claim — unless that publish already happened while the provider was
    rendering, in which case the site it attached is patched right away.
    """
    try:
        if not await _store_clip(
            job, provider_video_url, website_id=website["id"] if website else job.job_id
        ):
            return
        if not _still_storing(job, "parking or applying the stored clip"):
            return

        if website is None:
            async with job.lock:
                if not job.website_id:
                    job.status = JOB_STATUS_READY
                    job.result_payload = {
                        "message": "Video sedia — akan dipasang semasa laman diterbitkan."
                    }
                    logger.info(f"🎬 Hero video {job.job_id} ready ahead of publish")
                    await _ledger_save(job)
                    return
            try:
                website = await _load_owned_website(job.website_id, user_id)
            except HTTPException as exc:
                await _fail_job(job, "website_unavailable", detail=str(exc.detail))
                return

        await _apply_stored_clip(job, website, user_id)
    except Exception as exc:  # noqa: BLE001 — never leave a job stuck in 'storing'
        logger.exception(f"[hero-video] finaliser crashed for {job.job_id}: {exc}")
        await _fail_job(job, "apply_failed", detail=repr(exc))


# ---------------------------------------------------------------------------
# Publish-time claim of a prepared clip (called from /api/publish)
# ---------------------------------------------------------------------------

def stage_prepared_hero_video(job_id: Optional[str], user_id: str, html: str) -> Tuple[str, Dict]:
    """Patch a ``ready`` clip into the page that is ABOUT to be published.

    Pure string work, no I/O, and the job is left untouched: if the publish
    then fails nothing has been consumed and the next attempt can stage it
    again. Returns the page to publish and what happened — ``staged`` for
    the publish to confirm afterwards (settle_prepared_hero_video), or the
    job's state for it to act on then.
    """
    job = zai_video_service.get_job(job_id) if job_id else None
    if not job or job.user_id != user_id:
        return html, {"status": "none", "job_id": job_id, "reason": "job_not_found"}
    if job.status in (JOB_STATUS_PROCESSING, JOB_STATUS_STORING):
        return html, {"status": "pending", "job_id": job_id}
    if job.status != JOB_STATUS_READY:
        return html, {"status": "none", "job_id": job_id, "reason": job.error or job.status}
    patched = apply_hero_video(html, _stored_settings(job))
    if not patched.changed:
        return html, {"status": "none", "job_id": job_id, "reason": "hero_not_found"}
    return patched.html, {
        "status": "staged",
        "job_id": job_id,
        "settings": patched.settings,
        "hero_match": patched.hero_match,
    }


async def settle_prepared_hero_video(job_id: Optional[str], user_id: str, website: dict, staged: Dict) -> Dict:
    """After the publish has gone live: confirm a staged clip, or attach an
    in-flight job to the new site so the driver applies it when it lands.
    A clip that became ready between staging and upload is applied by a
    background task — this runs inside the publish request and does no
    storage or provider work itself.

    Returns the ``hero_video`` block of the publish response:
    ``applied`` (the live page carries the clip), ``pending`` (it will be
    applied automatically; poll ``jobs/{job_id}`` on the site), ``failed``
    or ``none``.
    """
    job = zai_video_service.get_job(job_id) if job_id else None
    if not job or job.user_id != user_id:
        logger.warning(
            f"🎬 [PUBLISH] hero video job {job_id} not settled for {website.get('id')}: "
            f"{'not in this process' if not job else 'owned by another user'} — the page starts a new clip"
        )
        return {"status": "none", "job_id": job_id, "reason": "job_not_found"}
    website_id = website["id"]

    if staged.get("status") == "staged":
        async with job.lock:
            if job.status != JOB_STATUS_READY:
                # The window closed (or the sweep acted) between staging
                # and settling: the page uploaded does carry the clip, but
                # the job has already been ended and refunded. Say so; do
                # not rewrite a terminal job as completed.
                logger.warning(
                    f"[hero-video] job {job.job_id} was {job.status} (error={job.error}) by the time "
                    f"{website_id} settled its staged clip — page carries it, job left as is"
                )
                return {"status": "applied", "job_id": job_id, "message": "Video latar hero dipasang bersama laman.",
                        "note": f"job_{job.status}"}
            job.website_id = website_id
            job.applied = True
            job.live_site_updated = True
            job.result_payload = {
                "settings": staged.get("settings"),
                "base_source": "publish",
                "message": "Video latar hero dipasang bersama laman.",
            }
            job.status = JOB_STATUS_COMPLETED
        logger.info(
            f"🎬 Hero video {job.job_id} published together with {website_id} "
            f"(hero matched by {staged.get('hero_match') or 'unknown'})"
        )
        # The publish wrote the page; the row must say the same thing.
        await _record_video_on_row(website_id, _stored_settings(job))
        await _ledger_save(job)
        return {"status": "applied", "job_id": job_id, "message": job.result_payload["message"]}

    async with job.lock:
        if job.status in (JOB_STATUS_PROCESSING, JOB_STATUS_STORING):
            if not job.website_id:
                job.website_id = website_id
            if job.website_id != website_id:
                return {"status": "none", "job_id": job_id, "reason": "attached_elsewhere"}
            logger.info(f"🎬 Hero video {job.job_id} attached to {website_id}; applies when the clip lands")
            await _ledger_save(job)
            return {
                "status": "pending",
                "job_id": job_id,
                "message": "Video latar hero hampir siap dan akan dipasang secara automatik.",
            }
        if job.status != JOB_STATUS_READY:
            return {"status": "none", "job_id": job_id, "reason": job.error or job.status}
        # Became ready after staging looked, before the upload finished.
        # The apply (snapshot read, patch, two storage writes, DB) is
        # background work like every other completion; the create page
        # follows the job and receives the patched page from the poll
        # that sees it complete.
        job.website_id = website_id
        job.status = JOB_STATUS_STORING
        await _ledger_save(job)
        job.finalize_task = asyncio.create_task(_apply_stored_clip_task(job, website, user_id))
    logger.info(f"🎬 Hero video {job.job_id} was ready at settle; applying to {website_id} in the background")
    return {
        "status": "pending",
        "job_id": job_id,
        "message": "Video sedia — sedang dipasang pada laman web.",
    }


@router.patch("/{website_id}/hero-video")
async def update_hero_video_look(
    website_id: str,
    body: PatchHeroVideoRequest,
    current_user: dict = Depends(get_current_user),
):
    """Change the scrim, text treatment or mobile behaviour of the video
    already on the page. Credit-FREE: no AI call, the clip is reused."""
    _feature_gate()
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)
    base_html, base_source = await _load_base_html(website)

    current = detect_hero_video(base_html)
    if not current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "no_hero_video",
                "message": "Laman web ini belum ada video latar hero.",
            },
        )

    merged = {**current}
    for key, value in body.model_dump(exclude_none=True).items():
        merged[key] = value

    settings = build_settings(
        video_url=merged["video_url"],
        poster_url=merged.get("poster_url"),
        overlay=merged.get("overlay"),
        overlay_opacity=merged.get("overlay_opacity"),
        text_mode=merged.get("text_mode"),
        show_on_mobile=merged.get("show_on_mobile"),
    )
    patched = apply_hero_video(base_html, settings)
    if not patched.changed or patched.html == base_html:
        return {
            "success": True,
            "changed": False,
            "message": "Tiada perubahan.",
            "website_id": website_id,
            "settings": settings.as_dict(),
            "base_source": base_source,
            "live_site_updated": False,
        }

    await _record_video_on_row(website_id, settings)
    live, warning = await _persist(website, user_id, patched.html)
    logger.info(f"🎬 Hero video look updated for {website_id} (base={base_source}, live={live})")
    response = {
        "success": True,
        "changed": True,
        "message": "Tetapan video latar dikemas kini.",
        "website_id": website_id,
        "settings": patched.settings,
        "base_source": base_source,
        "live_site_updated": live,
        "html_content": patched.html,
    }
    if warning:
        response["warning"] = warning
    return response


@router.delete("/{website_id}/hero-video")
async def delete_hero_video(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Take the video off the hero. Credit-FREE and exact: the page goes back
    to the bytes it had before the video was added."""
    _feature_gate()
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)
    base_html, base_source = await _load_base_html(website)

    result = remove_hero_video(base_html)
    if not result.changed:
        return {
            "success": True,
            "changed": False,
            "message": "Laman web ini tiada video latar hero.",
            "website_id": website_id,
            "base_source": base_source,
            "live_site_updated": False,
        }

    await _record_video_on_row(website_id, None)
    live, warning = await _persist(website, user_id, result.html)
    logger.info(f"🎬 Hero video removed for {website_id} (base={base_source}, live={live})")
    response = {
        "success": True,
        "changed": True,
        "message": "Video latar hero telah dibuang.",
        "website_id": website_id,
        "base_source": base_source,
        "live_site_updated": live,
        "html_content": result.html,
    }
    if warning:
        response["warning"] = warning
    return response


# ---------------------------------------------------------------------------
# Durability: restart recovery and the stuck sweep (ledger-backed)
# ---------------------------------------------------------------------------

async def _resume_apply(job) -> None:
    """A resumed job whose clip is already on Cloudinary: only the apply
    was lost with the old process."""
    try:
        website = await _load_owned_website(job.website_id, job.user_id)
    except HTTPException as exc:
        await _fail_job(job, "website_unavailable", detail=str(exc.detail))
        return
    await _apply_stored_clip_task(job, website, job.user_id)


def _adopt_row(row: Dict) -> Optional[str]:
    """Put a claimed ledger row into the registry and drive it. Returns
    the job id, or None when the row could not be rebuilt or is already
    live here."""
    try:
        job = ledger.job_from_row(row)
    except Exception as exc:  # noqa: BLE001 — one bad row must not block the rest
        logger.error(f"[hero-video] ledger row {row.get('job_id')} could not be rebuilt: {exc!r}")
        return None
    if zai_video_service.get_job(job.job_id) is not None:
        return None
    job = zai_video_service.adopt_job(job)
    if job.status == JOB_STATUS_STORING and job.video_url:
        if job.website_id:
            # The clip is stored; only the apply was lost.
            job.finalize_task = asyncio.create_task(_resume_apply(job))
        else:
            # Stored, never parked: it is ready for its publish.
            job.status = JOB_STATUS_READY
            job.result_payload = {"message": "Video sedia — akan dipasang semasa laman diterbitkan."}
            job.driver_task = asyncio.create_task(_drive_hero_video_job(job, "", job.user_id))
    elif job.status == JOB_STATUS_STORING:
        # Died between SUCCEEDED and the upload: ask the provider again —
        # the result URL is valid for 24 h.
        job.status = JOB_STATUS_PROCESSING
        job.driver_task = asyncio.create_task(
            _drive_hero_video_job(job, job.website_id, job.user_id)
        )
    else:  # processing, or ready and waiting for its publish
        job.driver_task = asyncio.create_task(
            _drive_hero_video_job(job, job.website_id, job.user_id)
        )
    logger.warning(
        f"[hero-video] adopted job {job.job_id} from the ledger "
        f"(status={job.status}, website={job.website_id or '-'}, "
        f"age={int(job.age_seconds())}s, provider_status={job.provider_status or '-'})"
    )
    return job.job_id


async def adopt_unowned_jobs() -> int:
    """Claim and drive every unfinished ledger row nobody owns. A row still
    leased by the outgoing instance is skipped — that process is alive and
    driving it — and picked up once its lease lapses. Returns how many
    were adopted here."""
    adopted = 0
    for row in await ledger.load_claimable():
        job_id = str(row.get("job_id") or "")
        if not job_id or zai_video_service.get_job(job_id) is not None:
            continue
        if not await ledger.claim(job_id, str(row.get("status") or "processing")):
            logger.info(f"[hero-video] job {job_id} claimed by another process first — skipping")
            continue
        if _adopt_row(row):
            adopted += 1
    return adopted


#: After a start, keep looking for rows the previous instance is still
#: holding: Render keeps the old process alive until the new one is
#: healthy, so its leases lapse a minute or two AFTER we start.
RESUME_RECHECK_SECONDS = 30
RESUME_RECHECK_WINDOW_SECONDS = 10 * 60


async def _resume_recheck_loop() -> None:
    try:
        deadline = time.monotonic() + RESUME_RECHECK_WINDOW_SECONDS
        while time.monotonic() < deadline:
            await asyncio.sleep(RESUME_RECHECK_SECONDS)
            adopted = await adopt_unowned_jobs()
            if adopted:
                logger.warning(f"[hero-video] adopted {adopted} job(s) left by the previous instance")
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        logger.exception("[hero-video] resume re-check loop crashed")


_resume_recheck_task: Optional["asyncio.Task"] = None


async def resume_hero_video_jobs() -> int:
    """Startup: adopt every job the previous process left unfinished and
    drive it again. Render restarts the backend on every deploy; before
    this, every job in flight at that moment was forgotten — provider
    done, clip never collected, credit never refunded, nothing logged.

    Ages are restored from the ledger's ``created_at``, so the hard
    timeout and the claim window keep counting from the real start. Rows
    the outgoing instance still leases are re-checked every
    RESUME_RECHECK_SECONDS for RESUME_RECHECK_WINDOW_SECONDS. Returns how
    many jobs were adopted now."""
    global _resume_recheck_task
    adopted = await adopt_unowned_jobs()
    _resume_recheck_task = asyncio.create_task(_resume_recheck_loop())
    return adopted


async def sweep_stuck_hero_video_jobs() -> Dict:
    """Fail every job that outlived the hard timeout, whether or not a
    driver exists for it and whatever the website's own status is, and
    adopt unfinished rows nobody owns. Runs from the stuck-generation
    scheduler.

    Three passes:
      * the live registry — a driver that crashed out of its loop, or a
        finaliser that hung (a job 'storing' for longer than the limit);
      * the ledger — rows past the limit with no process behind them: the
        row is claimed first (one sweeper wins), then failed and refunded;
      * adoption — unfinished rows inside the limit whose lease lapsed
        (their process died): claimed and driven here.
    Each failure is refunded if charged, written to the ledger, and raises
    HERO_VIDEO_TIMEOUT."""
    limit = zai_video_max_wait_seconds() + HERO_VIDEO_SWEEP_GRACE_SECONDS
    failed_ids = []
    alerts = []
    checked = 0

    for job in list(zai_video_service._jobs.values()):
        if job.status not in (JOB_STATUS_PROCESSING, JOB_STATUS_STORING):
            continue
        checked += 1
        if job.status == JOB_STATUS_STORING:
            since = job.storing_since if job.storing_since is not None else job.created_at
            if time.monotonic() - since <= HERO_VIDEO_STORING_LIMIT_SECONDS:
                continue
        elif job.age_seconds() <= limit:
            continue
        async with job.lock:
            if job.status not in (JOB_STATUS_PROCESSING, JOB_STATUS_STORING):
                continue
            await _fail_job(
                job, "timeout",
                detail=f"swept: still {job.status} after {int(limit)}s, its driver made no progress",
            )
            if job.status == JOB_STATUS_FAILED and job.error == "timeout":
                alerts.append(job)
        failed_ids.append(job.job_id)

    for row in await ledger.load_stale(limit):
        job_id = str(row.get("job_id") or "")
        if not job_id or job_id in failed_ids:
            continue
        checked += 1
        live = zai_video_service.get_job(job_id)
        if live is not None:
            if live.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
                # The row fell behind the process (a ledger write failed
                # earlier). Bring it up to date; nothing to refund.
                await _ledger_save(live)
            continue
        if ledger.lease_is_live(row):
            continue  # another process is driving it; its own timeout applies
        if not await ledger.claim(job_id, str(row.get("status") or "processing")):
            continue
        try:
            job = ledger.job_from_row(row)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[hero-video] sweep: ledger row {job_id} could not be rebuilt: {exc!r}")
            continue
        await _fail_job(job, "timeout", detail="swept from the ledger: no process owns this job")
        if job.status == JOB_STATUS_FAILED and job.error == "timeout":
            alerts.append(job)
            failed_ids.append(job_id)

    for job in alerts:
        await _alert_timeout(job)

    adopted = await adopt_unowned_jobs()

    return {"checked_rows": checked, "count": len(failed_ids), "ids": failed_ids, "adopted": adopted}
