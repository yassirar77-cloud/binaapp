"""TikTok API client — Login Kit (OAuth v2) and the Content Posting API.

Everything here is a faithful, minimal mapping of the documented endpoints:

  Login Kit for Web
    https://www.tiktok.com/v2/auth/authorize/            (browser redirect)
    POST https://open.tiktokapis.com/v2/oauth/token/      code / refresh
    POST https://open.tiktokapis.com/v2/oauth/revoke/
    GET  https://open.tiktokapis.com/v2/user/info/?fields=...

  Content Posting API
    POST /v2/post/publish/creator_info/query/             before every post
    POST /v2/post/publish/video/init/                     Direct Post (video)
    POST /v2/post/publish/inbox/video/init/               Upload to drafts
    POST /v2/post/publish/content/init/                   Photos (PULL_FROM_URL only)
    PUT  <upload_url>                                     chunked FILE_UPLOAD
    POST /v2/post/publish/status/fetch/

Chunk rules (Media Transfer Guide): each chunk 5 MB – 64 MB except the final
one which may run to 128 MB; a file under 5 MB goes up whole; at most 1000
chunks; ``total_chunk_count = floor(video_size / chunk_size)`` with the
remainder merged into the final chunk; chunks are uploaded sequentially;
206 = partial accepted, 201 = complete.

Web apps do not use PKCE (the token doc says ``code_verifier`` is "required
for mobile and desktop app only"), so ``state`` is the CSRF control.

No function in this module logs a token, a client secret, or a request body
that could contain one.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx
from loguru import logger

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
REVOKE_URL = "https://open.tiktokapis.com/v2/oauth/revoke/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
INBOX_VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
CONTENT_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/content/init/"
STATUS_FETCH_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

#: The scopes this integration asks for, in the order TikTok lists them.
SCOPES = ("user.info.basic", "video.upload", "video.publish")

USER_INFO_FIELDS = (
    "open_id",
    "union_id",
    "avatar_url",
    "avatar_url_100",
    "avatar_large_url",
    "display_name",
)

MB = 1024 * 1024
MIN_CHUNK_BYTES = 5 * MB
MAX_CHUNK_BYTES = 64 * MB
MAX_FINAL_CHUNK_BYTES = 128 * MB
MAX_CHUNK_COUNT = 1000
DEFAULT_CHUNK_BYTES = 10 * MB
MAX_VIDEO_BYTES = 4 * 1024 * MB  # 4 GB

#: Direct-post title cap: "The maximum length is 2200 in UTF-16 runes."
VIDEO_TITLE_MAX_UTF16 = 2200
PHOTO_TITLE_MAX_UTF16 = 90
PHOTO_DESCRIPTION_MAX_UTF16 = 4000
MAX_PHOTO_COUNT = 35

VIDEO_MIME_TYPES = ("video/mp4", "video/quicktime", "video/webm")

PRIVACY_LEVELS = (
    "PUBLIC_TO_EVERYONE",
    "MUTUAL_FOLLOW_FRIENDS",
    "FOLLOWER_OF_CREATOR",
    "SELF_ONLY",
)

TERMINAL_STATUSES = ("PUBLISH_COMPLETE", "FAILED", "SEND_TO_USER_INBOX")


class TikTokAPIError(Exception):
    """A non-``ok`` answer from TikTok, with the documented ``error.code``."""

    def __init__(
        self,
        code: str,
        message: str = "",
        *,
        http_status: int = 0,
        log_id: Optional[str] = None,
    ):
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.log_id = log_id

    @property
    def is_auth_error(self) -> bool:
        return self.code in ("access_token_invalid", "scope_not_authorized", "invalid_grant")


def utf16_length(text: str) -> int:
    """Length in UTF-16 code units — the unit TikTok counts titles in."""
    return len(text.encode("utf-16-le")) // 2


# --------------------------------------------------------------------------
# Login Kit
# --------------------------------------------------------------------------

def build_authorize_url(client_key: str, redirect_uri: str, state: str) -> str:
    """The URL the browser is sent to. Scopes are comma-separated per the docs."""
    query = urlencode(
        {
            "client_key": client_key,
            "scope": ",".join(SCOPES),
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def _oauth_error(resp: httpx.Response) -> Optional[TikTokAPIError]:
    """OAuth endpoints answer ``{"error": "...", "error_description": "..."}``."""
    try:
        body = resp.json()
    except ValueError:
        body = {}
    err = body.get("error") if isinstance(body, dict) else None
    if resp.status_code >= 400 or (err and err != "ok"):
        return TikTokAPIError(
            str(err or f"http_{resp.status_code}"),
            str(body.get("error_description", "") if isinstance(body, dict) else ""),
            http_status=resp.status_code,
            log_id=body.get("log_id") if isinstance(body, dict) else None,
        )
    return None


async def exchange_code(
    client_key: str, client_secret: str, code: str, redirect_uri: str
) -> Dict[str, Any]:
    """authorization_code grant. Returns the raw token payload (never log it)."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            },
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
    err = _oauth_error(resp)
    if err:
        raise err
    return resp.json()


async def refresh_access_token(
    client_key: str, client_secret: str, refresh_token: str
) -> Dict[str, Any]:
    """refresh_token grant. The returned refresh_token may differ — use it."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            },
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
    err = _oauth_error(resp)
    if err:
        raise err
    return resp.json()


async def revoke_token(client_key: str, client_secret: str, token: str) -> None:
    """Best-effort revoke; empty body on success."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            REVOKE_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            },
            data={"client_key": client_key, "client_secret": client_secret, "token": token},
        )
    err = _oauth_error(resp)
    if err:
        raise err


# --------------------------------------------------------------------------
# Signed API calls
# --------------------------------------------------------------------------

def _bearer(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def _unwrap(resp: httpx.Response) -> Dict[str, Any]:
    """Return ``data`` from a v2 envelope or raise the documented error code."""
    try:
        body = resp.json()
    except ValueError:
        raise TikTokAPIError(
            f"http_{resp.status_code}", "Non-JSON response from TikTok", http_status=resp.status_code
        )
    error = (body or {}).get("error") or {}
    code = error.get("code", "ok" if resp.status_code < 400 else f"http_{resp.status_code}")
    if code != "ok":
        raise TikTokAPIError(
            str(code),
            str(error.get("message", "")),
            http_status=resp.status_code,
            log_id=error.get("log_id"),
        )
    return (body or {}).get("data") or {}


async def fetch_user_info(access_token: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": ",".join(USER_INFO_FIELDS)},
        )
    return _unwrap(resp).get("user") or {}


async def query_creator_info(access_token: str) -> Dict[str, Any]:
    """Must be called right before rendering the post form and again before posting."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(CREATOR_INFO_URL, headers=_bearer(access_token), json={})
    return _unwrap(resp)


async def init_direct_video(
    access_token: str, post_info: Dict[str, Any], source_info: Dict[str, Any]
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            VIDEO_INIT_URL,
            headers=_bearer(access_token),
            json={"post_info": post_info, "source_info": source_info},
        )
    return _unwrap(resp)


async def init_inbox_video(access_token: str, source_info: Dict[str, Any]) -> Dict[str, Any]:
    """Upload-to-drafts: no post_info; the creator finishes in the TikTok app."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            INBOX_VIDEO_INIT_URL,
            headers=_bearer(access_token),
            json={"source_info": source_info},
        )
    return _unwrap(resp)


async def init_photo_content(
    access_token: str,
    *,
    post_mode: str,
    post_info: Dict[str, Any],
    photo_urls: List[str],
    cover_index: int = 0,
) -> Dict[str, Any]:
    body = {
        "post_info": post_info,
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": cover_index,
            "photo_images": photo_urls,
        },
        "post_mode": post_mode,  # DIRECT_POST | MEDIA_UPLOAD
        "media_type": "PHOTO",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(CONTENT_INIT_URL, headers=_bearer(access_token), json=body)
    return _unwrap(resp)


async def fetch_publish_status(access_token: str, publish_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            STATUS_FETCH_URL, headers=_bearer(access_token), json={"publish_id": publish_id}
        )
    return _unwrap(resp)


# --------------------------------------------------------------------------
# Chunked FILE_UPLOAD
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ChunkPlan:
    video_size: int
    chunk_size: int
    total_chunk_count: int

    def ranges(self) -> List[Tuple[int, int]]:
        """Inclusive byte ranges, one per chunk; the last absorbs the remainder."""
        out: List[Tuple[int, int]] = []
        for i in range(self.total_chunk_count):
            start = i * self.chunk_size
            end = self.video_size - 1 if i == self.total_chunk_count - 1 else start + self.chunk_size - 1
            out.append((start, end))
        return out

    def source_info(self) -> Dict[str, Any]:
        return {
            "source": "FILE_UPLOAD",
            "video_size": self.video_size,
            "chunk_size": self.chunk_size,
            "total_chunk_count": self.total_chunk_count,
        }


def plan_chunks(video_size: int, preferred_chunk: int = DEFAULT_CHUNK_BYTES) -> ChunkPlan:
    """Pick a chunk size that satisfies every documented rule for ``video_size``."""
    if video_size <= 0:
        raise ValueError("video_size must be positive")
    if video_size > MAX_VIDEO_BYTES:
        raise ValueError("video exceeds TikTok's 4 GB limit")
    if video_size < MIN_CHUNK_BYTES:
        # "must be uploaded as a whole, with chunk_size equal to the entire video's byte size"
        return ChunkPlan(video_size, video_size, 1)

    chunk = max(MIN_CHUNK_BYTES, min(int(preferred_chunk), MAX_CHUNK_BYTES))
    # Respect the 1000-chunk ceiling for very large files.
    if math.floor(video_size / chunk) > MAX_CHUNK_COUNT:
        chunk = min(MAX_CHUNK_BYTES, math.ceil(video_size / MAX_CHUNK_COUNT))
    count = max(1, math.floor(video_size / chunk))
    final = video_size - (count - 1) * chunk
    if final > MAX_FINAL_CHUNK_BYTES:  # only possible near the 64 MB cap
        raise ValueError("cannot satisfy the final-chunk limit for this file size")
    return ChunkPlan(video_size, chunk, count)


async def upload_chunks(
    upload_url: str,
    plan: ChunkPlan,
    read_range: Callable[[int, int], bytes],
    mime_type: str,
    *,
    on_progress: Optional[Callable[[int], Any]] = None,
    max_attempts: int = 3,
) -> None:
    """PUT every chunk in order. ``read_range(start, end)`` returns the bytes.

    206 acknowledges an intermediate chunk, 201 the final one (200 tolerated).
    5xx is retried with backoff; 4xx is final (416 = Content-Range mismatch).
    """
    ranges = plan.ranges()
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
        for index, (start, end) in enumerate(ranges):
            payload = await asyncio.to_thread(read_range, start, end)
            expected_len = end - start + 1
            if len(payload) != expected_len:
                raise TikTokAPIError(
                    "upload_read_short",
                    f"chunk {index}: read {len(payload)} bytes, expected {expected_len}",
                )
            headers = {
                "Content-Type": mime_type,
                "Content-Length": str(expected_len),
                "Content-Range": f"bytes {start}-{end}/{plan.video_size}",
            }
            attempt = 0
            while True:
                attempt += 1
                try:
                    resp = await client.put(upload_url, headers=headers, content=payload)
                except httpx.HTTPError as exc:
                    if attempt >= max_attempts:
                        raise TikTokAPIError("upload_network_error", str(exc)) from exc
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code in (200, 201, 206):
                    break
                if resp.status_code >= 500 and attempt < max_attempts:
                    logger.warning(
                        "TikTok upload chunk {} got {} — retrying ({}/{})",
                        index, resp.status_code, attempt, max_attempts,
                    )
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise TikTokAPIError(
                    f"upload_http_{resp.status_code}",
                    _UPLOAD_HTTP_MEANING.get(resp.status_code, resp.text[:200]),
                    http_status=resp.status_code,
                )
            if on_progress:
                result = on_progress(end + 1)
                if asyncio.iscoroutine(result):
                    await result


_UPLOAD_HTTP_MEANING = {
    400: "Malformed upload headers or chunk size mismatch",
    403: "Upload URL expired (valid for one hour after init)",
    404: "Upload task not found",
    416: "Content-Range does not match upload progress",
}

