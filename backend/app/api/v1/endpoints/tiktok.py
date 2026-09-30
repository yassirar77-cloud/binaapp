"""TikTok publishing for BinaApp's own account — admin only.

    GET    /api/v1/social/tiktok/config           is it configured / audited, limits
    POST   /api/v1/social/tiktok/oauth/start      → authorize_url (state stored)
    POST   /api/v1/social/tiktok/oauth/callback   {code, state} → account
    GET    /api/v1/social/tiktok/account          connected account (no tokens)
    DELETE /api/v1/social/tiktok/account          revoke + delete stored tokens
    GET    /api/v1/social/tiktok/creator-info     creator_info/query passthrough
    POST   /api/v1/social/tiktok/caption          AI caption draft
    POST   /api/v1/social/tiktok/posts            multipart: media + post JSON
    GET    /api/v1/social/tiktok/posts            recent posts
    GET    /api/v1/social/tiktok/posts/{id}       one post, synced with TikTok
    GET    /api/v1/social/tiktok/media/{key}      PUBLIC: staged photo for TikTok to pull

The browser-facing redirect URI (https://binaapp.my/api/tiktok/callback) is
a Next.js route that forwards ``code`` and ``state`` to the admin page, which
calls ``oauth/callback`` here with its bearer token. That binds the state to
the admin's session as well as to the row we minted.

Every route except ``media/{key}`` requires ``require_admin``.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import tempfile
import uuid
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from app.core.admin import require_admin
from app.core.config import settings
from app.services.social import caption_ai, tiktok_accounts, tiktok_client, tiktok_publisher
from app.services.social.tiktok_client import (
    MAX_PHOTO_COUNT,
    PHOTO_DESCRIPTION_MAX_UTF16,
    PHOTO_TITLE_MAX_UTF16,
    VIDEO_MIME_TYPES,
    VIDEO_TITLE_MAX_UTF16,
    TikTokAPIError,
)
from app.services.social.tiktok_publisher import PostRequest
from app.services.supabase_client import supabase_service

router = APIRouter(prefix="/social/tiktok", tags=["Social: TikTok"])

MEDIA_BUCKET = "tiktok-media"
_MEDIA_KEY_RE = re.compile(r"^[a-f0-9]{32}\.(jpg|jpeg|png|webp)$")
_PHOTO_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_VIDEO_EXT_MIME = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _user_id(user: Dict[str, Any]) -> str:
    return str(user.get("sub") or user.get("id"))


def _not_configured() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": "tiktok_not_configured",
            "message": "TikTok is not configured on the server (TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / TIKTOK_REDIRECT_URI).",
        },
    )


def _api_error(exc: TikTokAPIError) -> HTTPException:
    http = 401 if exc.is_auth_error else (429 if exc.code == "rate_limit_exceeded" else 502)
    return HTTPException(
        status_code=http,
        detail={
            "error": exc.code,
            "message": tiktok_publisher.humanize_api_error(exc),
            "log_id": exc.log_id,
        },
    )


async def _connected_account() -> Dict[str, Any]:
    account = await tiktok_accounts.get_account()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_connected", "message": "No TikTok account is connected."},
        )
    return account


async def _access_token(account: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    try:
        return await tiktok_accounts.get_valid_access_token(account)
    except tiktok_accounts.TikTokAuthRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "reauth_required",
                "message": f"The TikTok connection needs to be renewed ({exc}). Disconnect and connect again.",
            },
        )
    except tiktok_accounts.TikTokNotConfigured:
        raise _not_configured()


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

@router.get("/config")
async def get_config(_: Dict[str, Any] = Depends(require_admin)):
    return {
        "configured": tiktok_accounts.is_configured(),
        "audited": bool(settings.TIKTOK_APP_AUDITED),
        "redirect_uri": settings.TIKTOK_REDIRECT_URI,
        "scopes": list(tiktok_client.SCOPES),
        "max_upload_mb": int(settings.TIKTOK_MAX_UPLOAD_MB),
        "limits": {
            "video_title_max": VIDEO_TITLE_MAX_UTF16,
            "photo_title_max": PHOTO_TITLE_MAX_UTF16,
            "photo_description_max": PHOTO_DESCRIPTION_MAX_UTF16,
            "max_photos": MAX_PHOTO_COUNT,
        },
        "photo_media_public_base": settings.TIKTOK_MEDIA_PUBLIC_BASE,
        "policy_links": {
            "music_usage_confirmation": "https://www.tiktok.com/legal/page/global/music-usage-confirmation/en",
            "branded_content_policy": "https://www.tiktok.com/legal/page/global/bc-policy/en",
        },
    }


# --------------------------------------------------------------------------
# OAuth
# --------------------------------------------------------------------------

@router.post("/oauth/start")
async def oauth_start(user: Dict[str, Any] = Depends(require_admin)):
    try:
        client_key, _, redirect_uri = tiktok_accounts.require_config()
    except tiktok_accounts.TikTokNotConfigured:
        raise _not_configured()
    state = await tiktok_accounts.create_oauth_state(_user_id(user), redirect_uri)
    return {
        "authorize_url": tiktok_client.build_authorize_url(client_key, redirect_uri, state),
        "redirect_uri": redirect_uri,
    }


class OAuthCallbackBody(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    state: str = Field(..., min_length=1, max_length=128)


@router.post("/oauth/callback")
async def oauth_callback(body: OAuthCallbackBody, user: Dict[str, Any] = Depends(require_admin)):
    if not tiktok_accounts.is_configured():
        raise _not_configured()
    try:
        redirect_uri = await tiktok_accounts.consume_oauth_state(body.state, _user_id(user))
    except tiktok_accounts.OAuthStateError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_state", "message": str(exc)})
    try:
        account = await tiktok_accounts.connect_with_code(body.code, redirect_uri, _user_id(user))
    except TikTokAPIError as exc:
        logger.warning("TikTok code exchange failed: {}", exc.code)
        raise HTTPException(
            status_code=400,
            detail={
                "error": exc.code,
                "message": "TikTok rejected the authorization code. Make sure the redirect URI matches exactly, then try again.",
                "log_id": exc.log_id,
            },
        )
    except tiktok_accounts.TikTokAuthRequired as exc:
        raise HTTPException(status_code=400, detail={"error": "connect_failed", "message": str(exc)})
    return {"connected": True, "account": tiktok_accounts.public_view(account)}


# --------------------------------------------------------------------------
# Account
# --------------------------------------------------------------------------

@router.get("/account")
async def get_account(
    refresh: bool = Query(False, description="Re-fetch display name and avatar from TikTok"),
    _: Dict[str, Any] = Depends(require_admin),
):
    account = await tiktok_accounts.get_account()
    if not account:
        return {"connected": False, "account": None}
    if refresh and account.get("status") == "connected":
        try:
            account = await tiktok_accounts.refresh_profile(account)
        except tiktok_accounts.TikTokAuthRequired:
            account = await tiktok_accounts.get_account() or account
        except tiktok_accounts.TikTokNotConfigured:
            pass
    return {"connected": account.get("status") == "connected", "account": tiktok_accounts.public_view(account)}


@router.delete("/account")
async def disconnect_account(_: Dict[str, Any] = Depends(require_admin)):
    account = await tiktok_accounts.get_account()
    if not account:
        return {"disconnected": True, "revoked": False}
    result = await tiktok_accounts.disconnect(account)
    return {"disconnected": True, **result}


# --------------------------------------------------------------------------
# Creator info
# --------------------------------------------------------------------------

@router.get("/creator-info")
async def creator_info(_: Dict[str, Any] = Depends(require_admin)):
    account = await _connected_account()
    token, account = await _access_token(account)
    try:
        info = await tiktok_client.query_creator_info(token)
    except TikTokAPIError as exc:
        raise _api_error(exc)
    # Keep the @handle around for the account card.
    if info.get("creator_username") and info.get("creator_username") != account.get("username"):
        try:
            await tiktok_accounts.db_update(
                tiktok_accounts.ACCOUNTS, {"id": account["id"]}, {"username": info["creator_username"]}
            )
        except Exception as exc:  # noqa: BLE001 - cosmetic
            logger.debug("username cache skipped: {}", exc)
    return {
        "creator_avatar_url": info.get("creator_avatar_url"),
        "creator_username": info.get("creator_username"),
        "creator_nickname": info.get("creator_nickname"),
        "privacy_level_options": list(info.get("privacy_level_options") or []),
        "comment_disabled": bool(info.get("comment_disabled")),
        "duet_disabled": bool(info.get("duet_disabled")),
        "stitch_disabled": bool(info.get("stitch_disabled")),
        "max_video_post_duration_sec": info.get("max_video_post_duration_sec"),
        "audited": bool(settings.TIKTOK_APP_AUDITED),
    }


# --------------------------------------------------------------------------
# Caption
# --------------------------------------------------------------------------

class CaptionBody(BaseModel):
    brief: str = Field("", max_length=2000)
    language: str = Field("mixed", pattern="^(ms|en|mixed)$")
    media_type: str = Field("video", pattern="^(video|photo)$")


@router.post("/caption")
async def draft_caption(body: CaptionBody, _: Dict[str, Any] = Depends(require_admin)):
    max_units = VIDEO_TITLE_MAX_UTF16 if body.media_type == "video" else PHOTO_DESCRIPTION_MAX_UTF16
    return await caption_ai.draft_caption(
        body.brief, language=body.language, media_type=body.media_type, max_units=max_units
    )


# --------------------------------------------------------------------------
# Posts
# --------------------------------------------------------------------------

def _parse_post_json(raw: str) -> PostRequest:
    try:
        data = json.loads(raw or "{}")
        return PostRequest(**data)
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_post", "message": str(exc)[:300]})


def _video_mime(upload: UploadFile) -> str:
    declared = (upload.content_type or "").lower()
    if declared in VIDEO_MIME_TYPES:
        return declared
    ext = os.path.splitext(upload.filename or "")[1].lower()
    guessed = _VIDEO_EXT_MIME.get(ext)
    if guessed:
        return guessed
    raise HTTPException(
        status_code=415,
        detail={"error": "unsupported_video", "message": "Use an MP4 (H.264), MOV or WebM video."},
    )


async def _spool_video(upload: UploadFile, max_bytes: int) -> tuple[str, int]:
    """Stream the upload to a temp file, enforcing the size cap as we go."""
    fd, path = tempfile.mkstemp(prefix="tiktok-", suffix=".bin")
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "too_large",
                            "message": f"Video exceeds the {max_bytes // (1024 * 1024)} MB upload limit.",
                        },
                    )
                out.write(chunk)
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise
    if size == 0:
        os.remove(path)
        raise HTTPException(status_code=422, detail={"error": "empty_file", "message": "The video file is empty."})
    return path, size


async def _stage_photos(uploads: List[UploadFile], max_bytes: int) -> List[str]:
    if not uploads:
        raise HTTPException(status_code=422, detail={"error": "no_photos", "message": "Add at least one photo."})
    if len(uploads) > MAX_PHOTO_COUNT:
        raise HTTPException(
            status_code=422, detail={"error": "too_many_photos", "message": f"TikTok allows up to {MAX_PHOTO_COUNT} photos."}
        )
    urls: List[str] = []
    base = settings.TIKTOK_MEDIA_PUBLIC_BASE.rstrip("/")
    for upload in uploads:
        mime = (upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or "").lower()
        ext = _PHOTO_MIME.get(mime)
        if not ext:
            raise HTTPException(
                status_code=415, detail={"error": "unsupported_photo", "message": "Photos must be JPEG, PNG or WebP."}
            )
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=422, detail={"error": "empty_file", "message": "A photo file is empty."})
        if len(data) > max_bytes:
            raise HTTPException(status_code=413, detail={"error": "too_large", "message": "A photo exceeds the upload limit."})
        key = f"{uuid.uuid4().hex}.{ext}"
        stored = await supabase_service.upload_file(MEDIA_BUCKET, key, data, content_type=mime)
        if not stored:
            raise HTTPException(
                status_code=502,
                detail={"error": "storage_failed", "message": "Could not stage the photo (Supabase Storage)."},
            )
        urls.append(f"{base}/{key}")
    return urls


def _post_view(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "mode": row.get("mode"),
        "media_type": row.get("media_type"),
        "title": row.get("title"),
        "status": row.get("status"),
        "tiktok_status": row.get("tiktok_status"),
        "fail_reason": row.get("fail_reason"),
        "error": row.get("error"),
        "publish_id": row.get("publish_id"),
        "uploaded_bytes": row.get("uploaded_bytes") or 0,
        "total_bytes": row.get("total_bytes") or 0,
        "public_post_ids": row.get("public_post_ids"),
        "privacy_level": (row.get("post_info") or {}).get("privacy_level"),
        "post_info": row.get("post_info") or {},
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "finished_at": row.get("finished_at"),
    }


@router.post("/posts", status_code=202)
async def create_post(
    post: str = Form("{}", description="JSON-encoded PostRequest"),
    files: List[UploadFile] = File(..., description="One video, or 1–35 photos"),
    user: Dict[str, Any] = Depends(require_admin),
):
    if not tiktok_accounts.is_configured():
        raise _not_configured()
    req = _parse_post_json(post)
    account = await _connected_account()
    # Fail fast on an expired grant before accepting a large upload.
    token, account = await _access_token(account)

    if req.mode == "direct":
        # Pre-validate against the latest creator info so the admin sees the
        # message immediately; the job re-validates right before posting.
        try:
            creator = await tiktok_client.query_creator_info(token)
        except TikTokAPIError as exc:
            raise _api_error(exc)
        errors = tiktok_publisher.validate_post(req, creator)
        if errors:
            raise HTTPException(status_code=422, detail={"error": "validation", "message": " ".join(errors)})

    max_bytes = int(settings.TIKTOK_MAX_UPLOAD_MB) * 1024 * 1024

    if req.media_type == "video":
        if len(files) != 1:
            raise HTTPException(status_code=422, detail={"error": "one_video", "message": "Upload exactly one video."})
        mime = _video_mime(files[0])
        path, size = await _spool_video(files[0], max_bytes)
        try:
            plan = tiktok_client.plan_chunks(size)
        except ValueError as exc:
            os.remove(path)
            raise HTTPException(status_code=422, detail={"error": "bad_size", "message": str(exc)})
        row = await tiktok_publisher.create_post_row(
            account, _user_id(user), req, source_info={**plan.source_info(), "mime_type": mime}, total_bytes=size
        )
        tiktok_publisher.start_video_job(post=row, account=account, req=req, file_path=path, mime_type=mime)
    else:
        urls = await _stage_photos(files, max_bytes)
        row = await tiktok_publisher.create_post_row(
            account,
            _user_id(user),
            req,
            source_info={"source": "PULL_FROM_URL", "photo_images": urls, "photo_cover_index": req.photo_cover_index},
            total_bytes=0,
        )
        tiktok_publisher.start_photo_job(post=row, account=account, req=req, photo_urls=urls)

    return {"post": _post_view(row), "processing_notice": PROCESSING_NOTICE}


PROCESSING_NOTICE = (
    "Your content has been sent to TikTok. It may take a few minutes to process "
    "before it appears on the profile."
)


@router.get("/posts")
async def list_posts(limit: int = Query(20, ge=1, le=100), _: Dict[str, Any] = Depends(require_admin)):
    account = await tiktok_accounts.get_account()
    if not account:
        return {"posts": []}
    rows = await tiktok_publisher.list_posts(str(account["id"]), limit)
    return {"posts": [_post_view(r) for r in rows]}


@router.get("/posts/{post_id}")
async def get_post(post_id: str, _: Dict[str, Any] = Depends(require_admin)):
    try:
        uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Post not found")
    row = await tiktok_publisher.get_post(post_id)
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    account = await tiktok_accounts.get_account_by_id(str(row["account_id"]))
    if account:
        row = await tiktok_publisher.sync_post_status(row, account)
    return {"post": _post_view(row)}


# --------------------------------------------------------------------------
# Public media (photos TikTok pulls)
# --------------------------------------------------------------------------

@router.get("/media/{key}", include_in_schema=False)
async def serve_media(key: str):
    """Unauthenticated by design: TikTok's servers fetch the photo from here.

    Keys are 128-bit random, so the URL is unguessable; the bucket itself is
    private and only reachable through this endpoint with the service key.
    """
    if not _MEDIA_KEY_RE.match(key):
        raise HTTPException(status_code=404, detail="Not found")
    url = f"{supabase_service.url}/storage/v1/object/{MEDIA_BUCKET}/{key}"
    headers = {"apikey": supabase_service.service_key, "Authorization": f"Bearer {supabase_service.service_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Not found")
    ext = key.rsplit(".", 1)[1]
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[ext]
    return Response(
        content=resp.content,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=86400", "X-Robots-Tag": "noindex"},
    )

