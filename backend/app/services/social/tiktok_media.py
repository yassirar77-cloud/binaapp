"""Staged media for TikTok: the private ``tiktok-media`` bucket.

Photos TikTok pulls (photo posts), reference photos handed to Wan 3.0, and
the AI clips it returns all live here under unguessable keys and are served
by the public ``/api/v1/social/tiktok/media/{key}`` endpoint, reachable as
``TIKTOK_MEDIA_PUBLIC_BASE/{key}`` through the Next.js rewrite.
"""

from __future__ import annotations

import mimetypes
import re
import uuid
from typing import List, Optional, Sequence

import httpx
from fastapi import HTTPException, UploadFile

from app.core.config import settings
from app.services.social.tiktok_client import MAX_PHOTO_COUNT
from app.services.supabase_client import supabase_service

MEDIA_BUCKET = "tiktok-media"

MEDIA_KEY_RE = re.compile(r"^[a-f0-9]{32}\.(jpg|jpeg|png|webp|mp4)$")
PHOTO_MIME_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
EXT_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "mp4": "video/mp4",
}


def public_url(key: str) -> str:
    return f"{settings.TIKTOK_MEDIA_PUBLIC_BASE.rstrip('/')}/{key}"


async def store_bytes(data: bytes, ext: str) -> str:
    """Upload ``data`` under a fresh key; returns the key."""
    mime = EXT_MIME[ext]
    key = f"{uuid.uuid4().hex}.{ext}"
    stored = await supabase_service.upload_file(MEDIA_BUCKET, key, data, content_type=mime)
    if not stored:
        raise HTTPException(
            status_code=502,
            detail={"error": "storage_failed", "message": "Could not store the media (Supabase Storage)."},
        )
    return key


async def stage_photos(
    uploads: Sequence[UploadFile], *, max_bytes: int, max_count: int = MAX_PHOTO_COUNT, min_count: int = 1
) -> List[str]:
    """Validate and store photos; returns their keys."""
    if len(uploads) < min_count:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_photos", "message": f"Add at least {min_count} photo{'s' if min_count > 1 else ''}."},
        )
    if len(uploads) > max_count:
        raise HTTPException(
            status_code=422, detail={"error": "too_many_photos", "message": f"Up to {max_count} photos are allowed."}
        )
    keys: List[str] = []
    for upload in uploads:
        mime = (upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or "").lower()
        ext = PHOTO_MIME_EXT.get(mime)
        if not ext:
            raise HTTPException(
                status_code=415, detail={"error": "unsupported_photo", "message": "Photos must be JPEG, PNG or WebP."}
            )
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=422, detail={"error": "empty_file", "message": "A photo file is empty."})
        if len(data) > max_bytes:
            raise HTTPException(status_code=413, detail={"error": "too_large", "message": "A photo exceeds the upload limit."})
        keys.append(await store_bytes(data, ext))
    return keys


async def fetch_object(key: str) -> Optional[httpx.Response]:
    """Read an object with the service key; None when it is not there."""
    if not MEDIA_KEY_RE.match(key):
        return None
    url = f"{supabase_service.url}/storage/v1/object/{MEDIA_BUCKET}/{key}"
    headers = {"apikey": supabase_service.service_key, "Authorization": f"Bearer {supabase_service.service_key}"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, headers=headers)
    return resp if resp.status_code == 200 else None
