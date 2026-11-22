"""Mascot Video API — a merchant's clip with a cartoon mascot added.

    GET    /api/v1/mascot-videos/config             limits, today's usage
    POST   /api/v1/mascot-videos/mascots/generate   make a mascot image (glm-image)
    POST   /api/v1/mascot-videos/jobs               multipart: clip + mascot + prompt + consent → async job
    GET    /api/v1/mascot-videos/jobs               the merchant's recent jobs
    GET    /api/v1/mascot-videos/jobs/{id}          one job (poll this)
    POST   /api/v1/mascot-videos/jobs/{id}/use-as-hero   put a finished clip behind a site's hero
    GET    /api/v1/mascot-videos/media/{key}        PUBLIC: stored clip / mascot / result (unguessable key)

Flag-gated: with MASCOT_VIDEO_ENABLED off (the default) every route 404s.
Everything except ``media/{key}`` needs a logged-in merchant, and a merchant
only ever sees their own jobs. The rules (consent, 10 s, file size,
moderation, daily cap) live in ``services/mascot_video.py``.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services import image_moderation_service as moderation
from app.services import mascot_video as mv
from app.services.social._db import DbError

router = APIRouter(prefix="/mascot-videos")

#: Hosts a ``mascot_url`` may point at: only what /mascots/generate returns.
MASCOT_URL_HOSTS = ("res.cloudinary.com",)
MASCOT_DESCRIPTION_MAX = 200

_MASCOT_STYLE = (
    "mascot character, full body, standing, friendly and smiling. Flat vector cartoon "
    "style, bold clean outlines, bright happy colours, simple shapes, plain white "
    "background, no text, no logo."
)

#: (merchant id, UTC day) → mascot images generated. In memory on purpose: a
#: glm-image call costs cents, and a restart resetting it is harmless. The
#: expensive thing — the render — is capped from the database.
_mascot_images: Dict[Tuple[str, str], int] = {}


def _gate() -> None:
    """404 when the flag is off — the feature does not exist."""
    if not mv.mascot_video_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _error(code: int, error: str, message: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"error": error, "message": message})


def _merchant_id(current_user: dict) -> str:
    merchant_id = str(current_user.get("sub") or "")
    try:
        uuid.UUID(merchant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return merchant_id


def mascot_image_daily_limit() -> int:
    try:
        return max(0, int(os.getenv("MASCOT_IMAGE_DAILY_LIMIT", "5")))
    except ValueError:
        return 5


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

@router.get("/config")
async def mascot_video_config(current_user: dict = Depends(get_current_user)):
    _gate()
    merchant_id = _merchant_id(current_user)
    return {
        "enabled": True,
        "available": mv.provider_ready(),
        "min_clip_seconds": mv.MIN_CLIP_SECONDS,
        "max_clip_seconds": mv.MAX_CLIP_SECONDS,
        "max_clip_mb": mv.max_clip_bytes() // 1024 // 1024,
        "max_mascot_mb": mv.MASCOT_MAX_BYTES // 1024 // 1024,
        "prompt_max": mv.PROMPT_MAX,
        "mascot_description_max": MASCOT_DESCRIPTION_MAX,
        "poll_interval_seconds": mv.POLL_INTERVAL_SECONDS,
        "daily": await mv.usage_today(merchant_id),
    }


# --------------------------------------------------------------------------
# mascots
# --------------------------------------------------------------------------

class GenerateMascotRequest(BaseModel):
    description: str = Field(min_length=3, max_length=MASCOT_DESCRIPTION_MAX)


@router.post("/mascots/generate")
async def generate_mascot(body: GenerateMascotRequest, current_user: dict = Depends(get_current_user)):
    """Make a mascot image from a short description with glm-image."""
    _gate()
    merchant_id = _merchant_id(current_user)
    day = (merchant_id, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    for stale in [k for k in _mascot_images if k[1] != day[1]]:
        _mascot_images.pop(stale, None)
    if _mascot_images.get(day, 0) >= mascot_image_daily_limit():
        raise _error(429, "mascot_limit_reached", "Had penjanaan maskot harian telah dicapai. Cuba lagi esok.")

    from app.services.ai_service import ai_service

    description = " ".join(body.description.split())
    prompt = f"{description}, {_MASCOT_STYLE}"
    _mascot_images[day] = _mascot_images.get(day, 0) + 1
    # Z.ai rejects concurrent image requests: take the same lock and pacing
    # the site builder uses.
    async with ai_service._get_zai_image_lock():
        await ai_service._pace_zai_image_request()
        try:
            url = await ai_service._generate_image_zai(prompt)
        finally:
            ai_service._zai_last_request_at = time.monotonic()
    if not url:
        _mascot_images[day] = max(0, _mascot_images.get(day, 1) - 1)
        raise _error(502, "mascot_failed", "Maskot tidak dapat dijana. Sila cuba lagi.")
    return {"mascot_url": url}


async def _download_mascot(url: str) -> Tuple[bytes, str]:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in MASCOT_URL_HOSTS:
        raise _error(422, "bad_mascot_url", "Pautan maskot tidak sah.")
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
            resp = await client.get(url)
    except httpx.HTTPError:
        raise _error(502, "mascot_unreachable", "Gambar maskot tidak dapat dimuat turun.")
    if resp.status_code != 200:
        raise _error(502, "mascot_unreachable", "Gambar maskot tidak dapat dimuat turun.")
    return resp.content, resp.headers.get("content-type", "")


# --------------------------------------------------------------------------
# jobs
# --------------------------------------------------------------------------

@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_mascot_video(
    clip: UploadFile = File(...),
    prompt: str = Form("", max_length=mv.PROMPT_MAX),
    consent: bool = Form(False),
    mascot: Optional[UploadFile] = File(None),
    mascot_url: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    _gate()
    merchant_id = _merchant_id(current_user)
    if not consent:
        raise _error(
            422, "consent_required",
            "Sila sahkan bahawa semua orang dalam klip telah memberi kebenaran.",
        )
    if not mv.provider_ready():
        raise _error(503, "unavailable", "Video maskot tidak tersedia buat masa ini.")

    try:
        usage = await mv.usage_today(merchant_id)
        if mv.cap_reached(usage["used"], usage["limit"]):
            raise _error(
                429, "daily_limit_reached",
                f"Had harian dicapai ({usage['used']}/{usage['limit']}). Cuba lagi esok.",
            )
        if await mv.active_jobs(merchant_id) > 0:
            raise _error(409, "job_in_progress", "Satu video sedang dijana. Tunggu sehingga ia siap.")
    except DbError as exc:
        logger.error(f"mascot video cap check failed: {exc}")
        raise _error(503, "unavailable", "Video maskot tidak tersedia buat masa ini.")

    # Read at most one byte past the limit: an oversized upload is refused
    # without being held in memory whole.
    clip_bytes = await clip.read(mv.max_clip_bytes() + 1)
    if mascot is not None:
        mascot_bytes = await mascot.read(mv.MASCOT_MAX_BYTES + 1)
        mascot_type = mascot.content_type or ""
    elif mascot_url:
        mascot_bytes, mascot_type = await _download_mascot(mascot_url.strip())
    else:
        raise _error(422, "mascot_required", "Pilih atau muat naik satu maskot.")

    try:
        clip_info = mv.validate_clip(clip_bytes, clip.content_type or "")
        mascot_ext = mv.validate_mascot(mascot_bytes, mascot_type)
    except mv.ClipRejected as exc:
        raise _error(413 if exc.code.endswith("too_large") else 422, exc.code, str(exc))

    # A merchant's own image goes through the existing image moderation; the
    # clip itself is checked by the job before anything is rendered.
    if mascot is not None:
        verdict = await moderation.moderate_uploaded_image(mascot_bytes, mascot.filename or "mascot")
        if not verdict["allowed"]:
            raise _error(422, "mascot_rejected", verdict["message"])

    try:
        row = await mv.create_job(
            merchant_id=merchant_id,
            clip=clip_bytes,
            clip_ext=clip_info["ext"],
            clip_seconds=clip_info["seconds"],
            mascot=mascot_bytes,
            mascot_ext=mascot_ext,
            prompt=prompt,
        )
    except (DbError, RuntimeError) as exc:
        logger.error(f"mascot video create failed: {exc}")
        raise _error(502, "storage_failed", "Fail tidak dapat disimpan. Sila cuba lagi.")
    return {"job": mv.public_view(row), "daily": usage}


@router.get("/jobs")
async def list_mascot_videos(
    limit: int = Query(20, ge=1, le=50), current_user: dict = Depends(get_current_user)
):
    _gate()
    merchant_id = _merchant_id(current_user)
    rows = await mv.list_jobs(merchant_id, limit)
    rows = [await mv.ensure_driver(row) for row in rows]
    return {"jobs": [mv.public_view(row) for row in rows], "daily": await mv.usage_today(merchant_id)}


@router.get("/jobs/{job_id}")
async def get_mascot_video(job_id: str, current_user: dict = Depends(get_current_user)):
    _gate()
    row = await mv.get_job(job_id, _merchant_id(current_user))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    row = await mv.ensure_driver(row)
    return {"job": mv.public_view(row)}


# --------------------------------------------------------------------------
# use as hero video
# --------------------------------------------------------------------------

class UseAsHeroRequest(BaseModel):
    website_id: str = Field(min_length=8, max_length=64)


@router.post("/jobs/{job_id}/use-as-hero")
async def use_as_hero(job_id: str, body: UseAsHeroRequest, current_user: dict = Depends(get_current_user)):
    """Put a finished mascot clip behind the hero of one of the merchant's
    sites: the same credit-free patch the hero-video library uses, after
    copying the clip to Cloudinary where hero clips are served from."""
    _gate()
    merchant_id = _merchant_id(current_user)
    row = await mv.get_job(job_id, merchant_id)
    if not row or row.get("status") != "ready" or not row.get("result_key"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Imported here: hero_video is a large module with its own feature flag,
    # and only this route needs it.
    from app.api.v1.endpoints import hero_video as hero
    from app.services.hero_video_patcher import (
        apply_hero_video, build_settings, detect_hero_video, hero_video_delivery_url,
    )
    from app.services.zai_video_service import hero_video_enabled, zai_video_service

    if not hero_video_enabled():
        raise _error(409, "hero_video_disabled", "Video hero belum diaktifkan untuk akaun ini.")
    website = await hero._load_owned_website(body.website_id, merchant_id)

    data = await mv.fetch_bytes(row["result_key"])
    if not data:
        raise _error(404, "clip_missing", "Klip tidak dijumpai dalam storan.")
    try:
        stored = await asyncio.to_thread(
            zai_video_service._upload_sync, data, f"{body.website_id}-mascot-{uuid.uuid4().hex[:8]}"
        )
    except Exception as exc:  # noqa: BLE001 - Cloudinary raises its own types
        logger.error(f"mascot video hero upload failed: {exc}")
        raise _error(502, "storage_failed", "Klip tidak dapat disimpan. Sila cuba lagi.")
    secure_url = (stored or {}).get("secure_url")
    if not secure_url:
        raise _error(502, "storage_failed", "Klip tidak dapat disimpan. Sila cuba lagi.")

    base_html, base_source = await hero._load_base_html(website)
    current = detect_hero_video(base_html) or {}
    settings = build_settings(
        video_url=hero_video_delivery_url(secure_url),
        poster_url=zai_video_service.poster_url_for(secure_url),
        overlay=current.get("overlay"),
        overlay_opacity=current.get("overlay_opacity"),
        text_mode=current.get("text_mode"),
        show_on_mobile=current.get("show_on_mobile"),
        speed=current.get("speed"),
        effect=current.get("effect"),
    )
    patched = apply_hero_video(base_html, settings)
    if not patched.changed:
        raise _error(422, "hero_not_found", "Bahagian hero tidak dijumpai pada laman web ini.")
    await hero._record_video_on_row(body.website_id, settings)
    live, warning = await hero._persist(website, merchant_id, patched.html)
    logger.info(f"🎬 Mascot video {job_id} applied to hero of {body.website_id} (live={live})")
    response = {
        "success": True,
        "message": "Video maskot telah dipasang pada hero.",
        "website_id": body.website_id,
        "live_site_updated": live,
        "base_source": base_source,
    }
    if warning:
        response["warning"] = warning
    return response


# --------------------------------------------------------------------------
# media
# --------------------------------------------------------------------------

@router.get("/media/{key}", include_in_schema=False)
async def serve_media(key: str):
    """Unauthenticated by design: a <video> tag cannot send a bearer token.
    Keys are 128-bit random, so the URL is unguessable; the bucket itself is
    private and only reachable through this endpoint with the service key."""
    _gate()
    if not mv.MEDIA_KEY_RE.match(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = await mv.fetch_bytes(key)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return Response(
        content=data,
        media_type=mv.EXT_MIME[key.rsplit(".", 1)[1]],
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )
