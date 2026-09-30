"""Publish orchestration for TikTok: validation, the upload job, status sync.

A publish is a row in ``tiktok_posts`` plus an asyncio task that runs after
the HTTP request has returned:

    queued → uploading → processing → published | sent_to_inbox | failed

The task: (1) queries creator info again and validates the request against
it (the docs require the latest creator info at post time), (2) calls the
right init endpoint, (3) PUTs the chunks sequentially, (4) polls
``status/fetch`` until a terminal status or a timeout. The admin UI polls
``GET /posts/{id}``; ``sync_post_status`` re-checks TikTok for any row that
is still processing so a backend restart never leaves the UI stuck.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from pydantic import BaseModel, Field

from app.services.social import tiktok_accounts, tiktok_client
from app.services.social._db import db_insert, db_select, db_update
from app.services.social.tiktok_client import (
    PHOTO_DESCRIPTION_MAX_UTF16,
    PHOTO_TITLE_MAX_UTF16,
    PRIVACY_LEVELS,
    VIDEO_TITLE_MAX_UTF16,
    TikTokAPIError,
    utf16_length,
)

POSTS = "tiktok_posts"

POLL_INTERVAL_SECONDS = 4.0
#: Give TikTok up to this long to finish processing before we stop polling
#: in the background task. The GET endpoint keeps syncing after that.
POLL_TIMEOUT_SECONDS = 15 * 60

# Keep strong references to running jobs so they are not garbage-collected.
_running: Set[asyncio.Task] = set()


class PostRequest(BaseModel):
    """What the admin UI submits. Field names mirror TikTok's post_info."""

    mode: str = Field(..., pattern="^(direct|inbox)$")
    media_type: str = Field(..., pattern="^(video|photo)$")
    title: str = ""
    description: str = ""  # photo posts only
    privacy_level: Optional[str] = None
    disable_comment: bool = True
    disable_duet: bool = True
    disable_stitch: bool = True
    brand_content_toggle: bool = False
    brand_organic_toggle: bool = False
    is_aigc: bool = False
    video_cover_timestamp_ms: Optional[int] = Field(default=None, ge=0)
    photo_cover_index: int = Field(default=0, ge=0)
    auto_add_music: bool = False
    #: Measured client-side from the <video> element; checked against creator info.
    duration_sec: Optional[float] = Field(default=None, ge=0)


def validate_post(req: PostRequest, creator: Dict[str, Any]) -> List[str]:
    """Rules from the Content Sharing Guidelines + field limits. Pure."""
    errors: List[str] = []
    is_video = req.media_type == "video"

    if req.mode == "direct":
        options = list(creator.get("privacy_level_options") or [])
        if not req.privacy_level:
            errors.append("Choose who can view this post (privacy level).")
        elif req.privacy_level not in PRIVACY_LEVELS:
            errors.append(f"Unknown privacy level '{req.privacy_level}'.")
        elif options and req.privacy_level not in options:
            errors.append("That privacy level is not available for this creator account.")

        if req.brand_content_toggle and req.privacy_level == "SELF_ONLY":
            errors.append("Branded content visibility cannot be set to private.")

        title_cap = VIDEO_TITLE_MAX_UTF16 if is_video else PHOTO_TITLE_MAX_UTF16
        if utf16_length(req.title or "") > title_cap:
            errors.append(f"Caption is longer than TikTok's limit of {title_cap} characters.")
        if not is_video and utf16_length(req.description or "") > PHOTO_DESCRIPTION_MAX_UTF16:
            errors.append(
                f"Description is longer than TikTok's limit of {PHOTO_DESCRIPTION_MAX_UTF16} characters."
            )

    if is_video and req.duration_sec is not None:
        max_dur = creator.get("max_video_post_duration_sec")
        if isinstance(max_dur, (int, float)) and max_dur > 0 and req.duration_sec > max_dur:
            errors.append(
                f"Video is {req.duration_sec:.0f}s; this account can post up to {int(max_dur)}s."
            )
    return errors


def build_post_info(req: PostRequest, creator: Dict[str, Any]) -> Dict[str, Any]:
    """The ``post_info`` object for a Direct Post, honouring creator settings.

    When creator_info says an interaction is disabled on the account, the
    toggle is forced off (the UI also greys it out). Photo posts carry only
    the comment setting — duet and stitch do not apply.
    """
    info: Dict[str, Any] = {
        "title": req.title or "",
        "privacy_level": req.privacy_level,
        "disable_comment": bool(req.disable_comment or creator.get("comment_disabled")),
    }
    if req.media_type == "video":
        info["disable_duet"] = bool(req.disable_duet or creator.get("duet_disabled"))
        info["disable_stitch"] = bool(req.disable_stitch or creator.get("stitch_disabled"))
        if req.video_cover_timestamp_ms is not None:
            info["video_cover_timestamp_ms"] = int(req.video_cover_timestamp_ms)
        if req.is_aigc:
            info["is_aigc"] = True
    else:
        info["description"] = req.description or ""
        if req.auto_add_music:
            info["auto_add_music"] = True
    # Commercial content disclosure. Sent only when the toggle is on.
    if req.brand_organic_toggle:
        info["brand_organic_toggle"] = True
    if req.brand_content_toggle:
        info["brand_content_toggle"] = True
    return info


# --------------------------------------------------------------------------
# Status mapping
# --------------------------------------------------------------------------

STATUS_MAP = {
    "PROCESSING_UPLOAD": "processing",
    "PROCESSING_DOWNLOAD": "processing",
    "SEND_TO_USER_INBOX": "sent_to_inbox",
    "PUBLISH_COMPLETE": "published",
    "FAILED": "failed",
}

FAIL_REASON_TEXT = {
    "file_format_check_failed": "Unsupported media format. Use MP4 (H.264), MOV or WebM.",
    "duration_check_failed": "Video duration is outside what this account can post.",
    "frame_rate_check_failed": "Unsupported frame rate.",
    "picture_size_check_failed": "Unsupported picture size or resolution.",
    "video_pull_failed": "TikTok could not download the video from the URL.",
    "photo_pull_failed": "TikTok could not download one of the photos. Check the media URL prefix is verified in the TikTok portal.",
    "publish_cancelled": "The publish was cancelled.",
    "auth_removed": "Access was revoked on TikTok while processing. Reconnect the account.",
    "scope_not_authorized": "The connected account did not grant the required permission.",
    "access_token_invalid": "The TikTok session expired. Reconnect the account.",
    "spam_risk_too_many_posts": "Daily post limit reached for this account. Try again later.",
    "spam_risk_user_banned_from_posting": "This account is not allowed to post right now.",
    "spam_risk_text": "TikTok flagged the caption as risky. Edit it and try again.",
    "spam_risk": "TikTok flagged this request as risky.",
    "spam_risk_adult_content": "TikTok flagged the content as adult content.",
    "spam_risk_unaudited_client": "Until the app passes TikTok review, only private (Only you) posts are allowed.",
    "spam_risk_pull_url_unverified": "The media URL prefix is not verified in the TikTok developer portal.",
    "internal": "TikTok had an internal error. Try again in a few minutes.",
    "page_not_found": "TikTok could not find the publish task.",
}

API_ERROR_TEXT = {
    "unaudited_client_can_only_post_to_private_accounts": (
        "This app has not passed TikTok review yet, so Direct Post only works "
        "with privacy 'Only you' (SELF_ONLY). Choose 'Only you' or send to drafts."
    ),
    "privacy_level_option_mismatch": "That privacy level is not allowed for this account. Reload the creator settings.",
    "spam_risk_too_many_posts": "Daily post limit reached for this account.",
    "spam_risk_too_many_pending_share": "TikTok allows at most 5 pending draft uploads in 24 hours.",
    "spam_risk_user_banned_from_posting": "This account is not allowed to post right now.",
    "reached_active_user_cap": "The app's daily TikTok user quota is exhausted. Try again tomorrow.",
    "url_ownership_unverified": "The media URL prefix is not verified in the TikTok developer portal.",
    "rate_limit_exceeded": "TikTok rate limit hit. Wait a minute and try again.",
    "access_token_invalid": "The TikTok session expired. Reconnect the account.",
    "scope_not_authorized": "The connected account did not grant the required permission. Reconnect and accept all permissions.",
    "invalid_param": "TikTok rejected a parameter.",
}


def humanize_fail_reason(reason: Optional[str]) -> Optional[str]:
    if not reason:
        return None
    return FAIL_REASON_TEXT.get(reason, f"TikTok reported: {reason}")


def humanize_api_error(exc: TikTokAPIError) -> str:
    base = API_ERROR_TEXT.get(exc.code)
    if base:
        return f"{base} ({exc.message})" if exc.code == "invalid_param" and exc.message else base
    return f"TikTok error {exc.code}: {exc.message}".strip()


def apply_status_payload(row: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a ``status/fetch`` payload into a row patch. Pure."""
    tiktok_status = str(data.get("status") or "")
    patch: Dict[str, Any] = {"tiktok_status": tiktok_status, "updated_at": _iso_now()}
    ours = STATUS_MAP.get(tiktok_status)
    if ours:
        patch["status"] = ours
    if "uploaded_bytes" in data and isinstance(data.get("uploaded_bytes"), int):
        patch["uploaded_bytes"] = data["uploaded_bytes"]
    if tiktok_status == "FAILED":
        reason = data.get("fail_reason")
        patch["fail_reason"] = reason
        patch["error"] = humanize_fail_reason(reason) or "TikTok reported a failure."
    if data.get("publicaly_available_post_id"):
        patch["public_post_ids"] = data["publicaly_available_post_id"]
    if ours in ("published", "sent_to_inbox", "failed"):
        patch["finished_at"] = _iso_now()
    return patch


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------

async def create_post_row(
    account: Dict[str, Any], user_id: str, req: PostRequest, *, source_info: Dict[str, Any], total_bytes: int
) -> Dict[str, Any]:
    return await db_insert(
        POSTS,
        {
            "account_id": account["id"],
            "created_by": user_id,
            "mode": req.mode,
            "media_type": req.media_type,
            "title": req.title or None,
            "description": req.description or None,
            "post_info": {},
            "source_info": source_info,
            "status": "queued",
            "total_bytes": total_bytes,
        },
    )


async def _patch(post_id: str, patch: Dict[str, Any]) -> None:
    patch.setdefault("updated_at", _iso_now())
    await db_update(POSTS, {"id": post_id}, patch)


async def _fail(post_id: str, message: str, *, reason: Optional[str] = None) -> None:
    await _patch(
        post_id,
        {"status": "failed", "error": message[:500], "fail_reason": reason, "finished_at": _iso_now()},
    )


def start_video_job(
    *, post: Dict[str, Any], account: Dict[str, Any], req: PostRequest, file_path: str, mime_type: str
) -> asyncio.Task:
    task = asyncio.create_task(_run_video_job(post, account, req, file_path, mime_type))
    _running.add(task)
    task.add_done_callback(_running.discard)
    return task


def start_photo_job(
    *, post: Dict[str, Any], account: Dict[str, Any], req: PostRequest, photo_urls: List[str]
) -> asyncio.Task:
    task = asyncio.create_task(_run_photo_job(post, account, req, photo_urls))
    _running.add(task)
    task.add_done_callback(_running.discard)
    return task


async def _run_video_job(
    post: Dict[str, Any], account: Dict[str, Any], req: PostRequest, file_path: str, mime_type: str
) -> None:
    post_id = str(post["id"])
    try:
        token, account = await tiktok_accounts.get_valid_access_token(account)
        size = os.path.getsize(file_path)
        plan = tiktok_client.plan_chunks(size)

        if req.mode == "direct":
            creator = await tiktok_client.query_creator_info(token)
            errors = validate_post(req, creator)
            if errors:
                await _fail(post_id, " ".join(errors), reason="validation")
                return
            post_info = build_post_info(req, creator)
            await _patch(post_id, {"post_info": post_info, "source_info": plan.source_info()})
            data = await tiktok_client.init_direct_video(token, post_info, plan.source_info())
        else:
            await _patch(post_id, {"source_info": plan.source_info()})
            data = await tiktok_client.init_inbox_video(token, plan.source_info())

        publish_id = str(data.get("publish_id") or "")
        upload_url = str(data.get("upload_url") or "")
        if not publish_id or not upload_url:
            await _fail(post_id, "TikTok did not return an upload URL.", reason="init_incomplete")
            return
        await _patch(post_id, {"publish_id": publish_id, "status": "uploading"})

        def read_range(start: int, end: int) -> bytes:
            with open(file_path, "rb") as fh:
                fh.seek(start)
                return fh.read(end - start + 1)

        async def on_progress(done: int) -> None:
            await _patch(post_id, {"uploaded_bytes": done})

        await tiktok_client.upload_chunks(upload_url, plan, read_range, mime_type, on_progress=on_progress)
        await _patch(post_id, {"status": "processing", "uploaded_bytes": size})
        await _poll_until_terminal(post_id, token, publish_id)
    except tiktok_accounts.TikTokAuthRequired as exc:
        await _fail(post_id, f"TikTok session needs reconnecting ({exc}).", reason="reauth_required")
    except TikTokAPIError as exc:
        logger.warning("TikTok video job {} failed: {}", post_id, exc.code)
        await _fail(post_id, humanize_api_error(exc), reason=exc.code)
    except Exception as exc:  # noqa: BLE001 - the row must never stay 'uploading'
        logger.exception("TikTok video job {} crashed", post_id)
        await _fail(post_id, f"Unexpected error: {type(exc).__name__}", reason="internal")
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


async def _run_photo_job(
    post: Dict[str, Any], account: Dict[str, Any], req: PostRequest, photo_urls: List[str]
) -> None:
    post_id = str(post["id"])
    try:
        token, account = await tiktok_accounts.get_valid_access_token(account)
        creator = await tiktok_client.query_creator_info(token)
        if req.mode == "direct":
            errors = validate_post(req, creator)
            if errors:
                await _fail(post_id, " ".join(errors), reason="validation")
                return
            post_info = build_post_info(req, creator)
            post_mode = "DIRECT_POST"
        else:
            post_info = {"title": req.title or "", "description": req.description or ""}
            post_mode = "MEDIA_UPLOAD"
        await _patch(post_id, {"post_info": post_info, "status": "uploading"})
        data = await tiktok_client.init_photo_content(
            token,
            post_mode=post_mode,
            post_info=post_info,
            photo_urls=photo_urls,
            cover_index=min(req.photo_cover_index, max(0, len(photo_urls) - 1)),
        )
        publish_id = str(data.get("publish_id") or "")
        if not publish_id:
            await _fail(post_id, "TikTok did not return a publish id.", reason="init_incomplete")
            return
        await _patch(post_id, {"publish_id": publish_id, "status": "processing"})
        await _poll_until_terminal(post_id, token, publish_id)
    except tiktok_accounts.TikTokAuthRequired as exc:
        await _fail(post_id, f"TikTok session needs reconnecting ({exc}).", reason="reauth_required")
    except TikTokAPIError as exc:
        logger.warning("TikTok photo job {} failed: {}", post_id, exc.code)
        await _fail(post_id, humanize_api_error(exc), reason=exc.code)
    except Exception as exc:  # noqa: BLE001
        logger.exception("TikTok photo job {} crashed", post_id)
        await _fail(post_id, f"Unexpected error: {type(exc).__name__}", reason="internal")


async def _poll_until_terminal(post_id: str, token: str, publish_id: str) -> None:
    deadline = asyncio.get_event_loop().time() + POLL_TIMEOUT_SECONDS
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        try:
            data = await tiktok_client.fetch_publish_status(token, publish_id)
        except TikTokAPIError as exc:
            if exc.code == "rate_limit_exceeded":
                await asyncio.sleep(POLL_INTERVAL_SECONDS * 4)
                continue
            raise
        patch = apply_status_payload({}, data)
        await _patch(post_id, patch)
        if patch.get("status") in ("published", "sent_to_inbox", "failed"):
            return
    logger.warning("TikTok post {} still processing after {}s; GET keeps syncing", post_id, POLL_TIMEOUT_SECONDS)


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

async def list_posts(account_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    return await db_select(
        POSTS,
        filters={"account_id": account_id},
        extra={"order": "created_at.desc", "limit": str(max(1, min(limit, 100)))},
    )


async def get_post(post_id: str) -> Optional[Dict[str, Any]]:
    rows = await db_select(POSTS, filters={"id": post_id})
    return rows[0] if rows else None


async def sync_post_status(post: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any]:
    """Re-check TikTok for a row that is still in flight. Returns the fresh row."""
    if post.get("status") not in ("processing", "uploading") or not post.get("publish_id"):
        return post
    # A row stuck in 'uploading' after the upload URL's one-hour life is dead.
    if post.get("status") == "uploading":
        started = post.get("updated_at") or post.get("created_at")
        try:
            ts = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - ts).total_seconds() > 3600:
                await _fail(str(post["id"]), "Upload did not finish (backend restarted?). Try again.", reason="upload_stalled")
                return {**post, "status": "failed"}
        except ValueError:
            pass
        return post
    try:
        token, _ = await tiktok_accounts.get_valid_access_token(account)
        data = await tiktok_client.fetch_publish_status(token, str(post["publish_id"]))
    except (tiktok_accounts.TikTokAuthRequired, TikTokAPIError) as exc:
        logger.debug("status sync skipped for {}: {}", post.get("id"), exc)
        return post
    patch = apply_status_payload(post, data)
    await _patch(str(post["id"]), patch)
    return {**post, **patch}
