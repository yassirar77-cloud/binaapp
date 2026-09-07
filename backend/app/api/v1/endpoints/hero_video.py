"""Hero video background — a GLM-generated clip behind the hero, credit-free
to apply and remove.

    GET    /api/v1/websites/hero-video/options            style presets
    GET    /api/v1/websites/{id}/hero-video               what the page has now
    POST   /api/v1/websites/{id}/hero-video/generate      start a GLM video job
    GET    /api/v1/websites/{id}/hero-video/jobs/{job_id} poll; applies on success
    PATCH  /api/v1/websites/{id}/hero-video               change overlay / text / mobile
    DELETE /api/v1/websites/{id}/hero-video               remove it

TWO HALVES
----------
1. MAKING the clip is an AI call (Z.ai CogVideoX via ``zai_video_service``).
   It is asynchronous on Z.ai's side, so it is asynchronous here: ``generate``
   returns a job id at once and the dashboard polls ``jobs/{job_id}``. The
   poll that sees SUCCESS downloads the clip, stores it on Cloudinary, patches
   the page and republishes — all inside that one request.
2. PUTTING it on the page (and every later tweak or removal) is a
   deterministic HTML patch from ``hero_video_patcher``: no AI, no quota, no
   content drift. Same contract as the Design Studio.

GATES
-----
* HERO_VIDEO_ENABLED (env, default false): off → every route 404s.
* Plan: ``plan_features.can_use_hero_video`` (admin bypass; fail closed).
* One in-flight job per site, a small per-user concurrency cap, and a
  per-site daily submit cap — generation costs real money.

QUOTA NOTE (protected zone): nothing here touches check_limit,
subscription_service, usage_tracking or any credit counter.

PUBLISH SAFETY
--------------
Identical to the theme and contact edit paths (the mimba rule): patch the
LIVE storage snapshot when the site is published, fall back to the DB blob,
only ever accept a structurally balanced base, refuse to publish an
unbalanced result, and change nothing when no safe base exists.
"""

from __future__ import annotations

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
    DEFAULT_OVERLAY_OPACITY,
    DEFAULT_TEXT_MODE,
    HeroVideoSettings,
    apply_hero_video,
    build_settings,
    detect_hero_video,
    find_hero_open_tag,
    needs_style_upgrade,
    remove_hero_video,
)
from app.services.plan_features import can_use_hero_video
from app.services.storage_service import storage_service
from app.services.supabase_client import supabase_service
from app.services.zai_video_service import (
    ALLOWED_DURATIONS,
    DEFAULT_VIDEO_STYLE,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_STORING,
    VIDEO_STYLE_PRESETS,
    ZaiVideoError,
    build_hero_video_prompt,
    hero_video_enabled,
    zai_video_duration,
    zai_video_max_wait_seconds,
    zai_video_model,
    zai_video_service,
)

# Mounted under /websites in router.py.
router = APIRouter()

#: Seconds the dashboard should wait between polls.
POLL_INTERVAL_SECONDS = 8

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
    overlay_opacity: float = Field(default=DEFAULT_OVERLAY_OPACITY, ge=0.0, le=0.9)
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
        live, warning = await _persist(website, user_id, patched.html)
        logger.info(
            f"🎬 Hero video CSS upgraded for {website.get('id')} "
            f"(live={live}, warning={warning})"
        )
        return patched.html, True
    except Exception as exc:  # noqa: BLE001 - a read must never fail on this
        logger.warning(f"🎬 Hero video CSS upgrade skipped for {website.get('id')}: {exc}")
        return html, False


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
        "model": zai_video_model(),
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
        "allowed": await can_use_hero_video(user_id),
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

    if not await can_use_hero_video(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "plan_not_allowed",
                "message": (
                    "Video latar hero tidak termasuk dalam pelan anda. "
                    "Naik taraf pelan untuk menggunakannya."
                ),
            },
        )

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
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "too_many_jobs",
                "message": "Terlalu banyak video sedang dijana. Sila tunggu sebentar.",
            },
        )
    if _count_recent_submits(website_id) >= _max_per_site_per_day():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "daily_limit_reached",
                "message": "Had harian video untuk laman web ini telah dicapai. Cuba lagi esok.",
            },
        )

    style = body.style if body.style in VIDEO_STYLE_PRESETS else DEFAULT_VIDEO_STYLE
    prompt = build_hero_video_prompt(
        business_name=website.get("business_name") or website.get("name") or "",
        business_type=website.get("business_type") or "",
        description=website.get("description") or "",
        style=style,
        custom_prompt=body.prompt or "",
    )

    image_url = (body.image_url or "").strip() or None
    if image_url and not image_url.startswith("https://"):
        image_url = None

    try:
        task_id = await zai_video_service.submit(
            prompt, duration=body.duration, image_url=image_url
        )
    except ZaiVideoError as exc:
        logger.error(f"[hero-video] submit failed for {website_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "video_submit_failed",
                "message": "Penjanaan video gagal dimulakan. Sila cuba lagi sebentar.",
            },
        )

    _record_submit(website_id)
    job = zai_video_service.register_job(
        task_id=task_id,
        website_id=website_id,
        user_id=user_id,
        prompt=prompt,
        settings=HeroVideoLook(**body.model_dump(include=set(HeroVideoLook.model_fields))).model_dump(),
    )
    logger.info(
        f"🎬 Hero video job {job.job_id} started for {website_id} "
        f"(style={style}, task={task_id})"
    )
    return {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "prompt": prompt,
        "message": "Video sedang dijana. Ini mengambil masa 1–3 minit.",
    }


@router.get("/{website_id}/hero-video/jobs/{job_id}")
async def poll_hero_video_job(
    website_id: str,
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Poll a job. The call that observes SUCCESS also stores the clip,
    patches the page and republishes, then reports ``completed``."""
    _feature_gate()
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)

    job = zai_video_service.get_job(job_id)
    if not job or job.website_id != website_id or job.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "job_not_found",
                "message": "Tugasan video tidak dijumpai atau telah tamat. Sila cuba lagi.",
            },
        )

    if job.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
        return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}

    # Two dashboard tabs polling the same job must not both store + publish.
    async with job.lock:
        if job.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED):
            return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}

        if job.age_seconds() > zai_video_max_wait_seconds():
            job.status = JOB_STATUS_FAILED
            job.error = "timeout"
            logger.warning(f"[hero-video] job {job.job_id} timed out")
            return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}

        try:
            result = await zai_video_service.fetch_result(job.task_id)
        except ZaiVideoError as exc:
            # A transient poll error is not a failed job — report processing
            # and let the client ask again.
            logger.warning(f"[hero-video] poll error for {job.job_id}: {exc}")
            return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}

        if result["status"] == "fail":
            job.status = JOB_STATUS_FAILED
            job.error = "generation_failed"
            return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}
        if result["status"] != "success":
            return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}

        job.status = JOB_STATUS_STORING
        try:
            stored = await zai_video_service.store(result["video_url"], website_id=website_id)
        except ZaiVideoError as exc:
            job.status = JOB_STATUS_FAILED
            job.error = "storage_failed"
            logger.error(f"[hero-video] storage failed for {job.job_id}: {exc}")
            return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}

        job.video_url = stored["video_url"]
        job.poster_url = stored["poster_url"]

        # Apply to the page. A failure here keeps the stored URLs on the job
        # so the merchant can retry the apply without regenerating.
        look = HeroVideoLook(**job.settings)
        settings = _settings_from_look(look, job.video_url, job.poster_url)
        try:
            base_html, base_source = await _load_base_html(website)
            patched = apply_hero_video(base_html, settings)
            if not patched.changed:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": "hero_not_found", "message": "Bahagian hero tidak dijumpai."},
                )
            live, warning = await _persist(website, user_id, patched.html)
        except HTTPException as exc:
            job.status = JOB_STATUS_FAILED
            job.error = (
                exc.detail.get("error") if isinstance(exc.detail, dict) else "apply_failed"
            )
            logger.error(f"[hero-video] apply failed for {job.job_id}: {exc.detail}")
            return {"success": True, **job.to_dict(), "poll_interval_seconds": POLL_INTERVAL_SECONDS}

        job.status = JOB_STATUS_COMPLETED
        job.applied = True
        job.live_site_updated = live
        logger.info(
            f"🎬 Hero video applied for {website_id} "
            f"(base={base_source}, live={live}, {patched.summary()})"
        )
        response = {
            "success": True,
            **job.to_dict(),
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
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
            response["warning"] = warning
        return response


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
