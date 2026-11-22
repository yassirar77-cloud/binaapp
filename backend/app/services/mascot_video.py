"""Mascot Video: a merchant's own clip, with a cartoon mascot added to it.

The merchant uploads a 2–10 s clip of their shop or food and picks a mascot
image; wan3.0-video (DashScope) edits the clip so the mascot is in the real
scene. Same shape as the other AI video flows: a ledger row per attempt
(``mascot_videos``, migration 071), an async provider job polled in the
background, the result copied into our own storage.

Life of a job
-------------
    queued      row written, clip + mascot stored in the ``mascot-videos`` bucket
    moderating  the clip is being checked by Qwen (fails closed)
    processing  wan3.0 accepted the job (from here it costs money)
    ready       result stored; ``result_url`` set
    rejected    moderation refused the clip — nothing was rendered
    failed      anything else; ``error`` says what

Money rules
-----------
  * ``MASCOT_VIDEO_ENABLED`` is off by default: every route 404s.
  * ``MASCOT_VIDEO_DAILY_LIMIT`` (default 3) caps the renders per merchant
    per UTC day, and one merchant has one job in flight at a time. A render
    that comes back with no mascot in it is not delivered and not counted;
    ``MASCOT_VIDEO_DAILY_ATTEMPT_LIMIT`` (default 2x) is the hard ceiling on
    everything that reaches the provider, counted or not.
  * Every delivered clip has a small "Dijana AI" label burned in with ffmpeg.
  * DashScope bills input seconds + output seconds, so a 10 s clip is 20
    billed seconds. The estimate is written on the row at submit and replaced
    by the metered figure when the job finishes.

TODO(billing): charge BinaCredits per render (at the point the provider
accepts the job, refund on failure — see hero_video._charge_if_paid /
_refund_if_charged) once the credit deduction bug is fixed. Until then the
daily cap is the only thing between a merchant and the provider bill.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.services import image_moderation_service as moderation
from app.services import zai_video_service as video
from app.services.social._db import db_insert, db_select, db_update
from app.services.supabase_client import supabase_service

TABLE = "mascot_videos"
BUCKET = "mascot-videos"

MIN_CLIP_SECONDS = 2.0
MAX_CLIP_SECONDS = 10.0
#: A phone rounds "10 seconds" up to 10.03; do not refuse that.
CLIP_SECONDS_TOLERANCE = 0.5
PROMPT_MAX = 300
MASCOT_MAX_BYTES = 5 * 1024 * 1024
POLL_INTERVAL_SECONDS = 10.0

ACTIVE_STATUSES = ("queued", "moderating", "processing")

CLIP_MIME_EXT = {"video/mp4": "mp4", "video/quicktime": "mov"}
MASCOT_MIME_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
EXT_MIME = {
    "mp4": "video/mp4", "mov": "video/quicktime",
    "png": "image/png", "jpg": "image/jpeg", "webp": "image/webp",
}
MEDIA_KEY_RE = re.compile(r"^[a-f0-9]{32}\.(mp4|mov|png|jpg|webp)$")

_DEFAULT_USD_PER_SEC = {"480P": 0.05, "720P": 0.10, "1080P": 0.20}

_running: Dict[str, asyncio.Task] = {}


# --------------------------------------------------------------------------
# config (read at call time, so a Render env change needs no redeploy)
# --------------------------------------------------------------------------

def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def mascot_video_enabled() -> bool:
    """MASCOT_VIDEO_ENABLED=true turns the feature on. Default off."""
    return _flag("MASCOT_VIDEO_ENABLED", "false")


def provider_ready() -> bool:
    return bool(video._dashscope_api_key()) and video._dashscope_is_unified(video.dashscope_video_model())


def daily_limit() -> int:
    try:
        return max(0, int(os.getenv("MASCOT_VIDEO_DAILY_LIMIT", "3")))
    except ValueError:
        return 3


def daily_attempt_limit() -> int:
    """Every render that reaches the provider is paid for, including the ones
    that come back without a mascot and so do not count against
    ``daily_limit``. This is the hard ceiling on those: without it a clip the
    model can never edit would be free to retry all day. Default: twice the
    daily limit."""
    try:
        return max(0, int(os.getenv("MASCOT_VIDEO_DAILY_ATTEMPT_LIMIT", str(2 * daily_limit()))))
    except ValueError:
        return 2 * daily_limit()


def max_clip_bytes() -> int:
    try:
        megabytes = float(os.getenv("MASCOT_VIDEO_MAX_MB", "50"))
    except ValueError:
        megabytes = 50.0
    # wan3.0 refuses a reference video over 100 MB.
    return int(min(max(megabytes, 1.0), 100.0) * 1024 * 1024)


def resolution() -> str:
    value = os.getenv("MASCOT_VIDEO_RESOLUTION", "720P").strip().upper()
    return value if value in _DEFAULT_USD_PER_SEC else "720P"


def watermark() -> bool:
    """Burn the provider's own AI mark into the clip. Off by default: on
    wan3.0 the mark reads "AI 生成" (Chinese) in the bottom-right corner,
    which is not a label a Malaysian merchant's customers can read. The
    dashboard shows its own "Dijana AI" label on every result instead."""
    return _flag("MASCOT_VIDEO_WATERMARK", "false")


def usd_per_second(res: str) -> float:
    raw = os.getenv(f"WAN_COST_USD_PER_SEC_{res}")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return _DEFAULT_USD_PER_SEC.get(res, _DEFAULT_USD_PER_SEC["720P"])


def estimate_cost_usd(clip_seconds: float, res: Optional[str] = None) -> float:
    """Input seconds + output seconds, at the output resolution's rate. Pure."""
    return round(2 * float(clip_seconds) * usd_per_second(res or resolution()), 4)


def cap_reached(used: int, limit: int) -> bool:
    """Pure: a limit of 0 disables rendering."""
    return used >= limit


# --------------------------------------------------------------------------
# clip inspection — no ffmpeg on the server, so read the container directly
# --------------------------------------------------------------------------

def _boxes(data: bytes, start: int, end: int):
    """Yield (type, body_start, body_end) for each ISO-BMFF box in a range."""
    offset = start
    while offset + 8 <= end:
        size, kind = struct.unpack(">I4s", data[offset:offset + 8])
        header = 8
        if size == 1:
            if offset + 16 > end:
                return
            size = struct.unpack(">Q", data[offset + 8:offset + 16])[0]
            header = 16
        elif size == 0:
            size = end - offset
        if size < header or offset + size > end:
            return
        yield kind, offset + header, offset + size
        offset += size


def mp4_duration_seconds(data: bytes) -> Optional[float]:
    """Duration of an MP4/MOV from its ``moov/mvhd`` box, or None when the
    bytes are not a readable MP4/MOV. Pure."""
    try:
        for kind, body_start, body_end in _boxes(data, 0, len(data)):
            if kind != b"moov":
                continue
            for inner, start, end in _boxes(data, body_start, body_end):
                if inner != b"mvhd":
                    continue
                version = data[start]
                if version == 1:
                    timescale, duration = struct.unpack(">IQ", data[start + 20:start + 32])
                else:
                    timescale, duration = struct.unpack(">II", data[start + 12:start + 20])
                if not timescale:
                    return None
                return duration / timescale
    except (struct.error, IndexError):
        return None
    return None


class ClipRejected(ValueError):
    """The upload cannot be used; ``code`` is the API error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_clip(data: bytes, content_type: str) -> Dict[str, Any]:
    """``{"ext", "seconds"}`` for a usable clip; raises ClipRejected. Pure."""
    ext = CLIP_MIME_EXT.get((content_type or "").split(";")[0].strip().lower())
    if not ext:
        raise ClipRejected("unsupported_clip", "Klip mesti dalam format MP4 atau MOV.")
    if not data:
        raise ClipRejected("empty_clip", "Fail klip kosong.")
    if len(data) > max_clip_bytes():
        raise ClipRejected(
            "clip_too_large", f"Klip terlalu besar. Maksimum {max_clip_bytes() // 1024 // 1024} MB."
        )
    seconds = mp4_duration_seconds(data)
    if seconds is None:
        raise ClipRejected("unreadable_clip", "Klip tidak dapat dibaca. Cuba rakam semula dalam format MP4.")
    if seconds < MIN_CLIP_SECONDS:
        raise ClipRejected("clip_too_short", f"Klip terlalu pendek. Minimum {MIN_CLIP_SECONDS:.0f} saat.")
    if seconds > MAX_CLIP_SECONDS + CLIP_SECONDS_TOLERANCE:
        raise ClipRejected(
            "clip_too_long", f"Klip terlalu panjang ({seconds:.0f} saat). Maksimum {MAX_CLIP_SECONDS:.0f} saat."
        )
    return {"ext": ext, "seconds": round(seconds, 2)}


def validate_mascot(data: bytes, content_type: str) -> str:
    """The storage extension for a usable mascot image; raises ClipRejected."""
    ext = MASCOT_MIME_EXT.get((content_type or "").split(";")[0].strip().lower())
    if not ext:
        raise ClipRejected("unsupported_mascot", "Maskot mesti gambar PNG, JPEG atau WebP.")
    if not data:
        raise ClipRejected("empty_mascot", "Fail maskot kosong.")
    if len(data) > MASCOT_MAX_BYTES:
        raise ClipRejected("mascot_too_large", "Gambar maskot terlalu besar. Maksimum 5 MB.")
    return ext


# --------------------------------------------------------------------------
# prompt
# --------------------------------------------------------------------------

_EDIT_PREFIX = "Edit Video 1: add the cartoon mascot character from Image 1 into the scene."
#: Wording matters a great deal here, and each of these was a paid render in
#: Phase 1 (same clip, same mascot):
#:   * told only to "add" the mascot, wan3.0 pastes it over the frame like a
#:     sticker and, one run in two, fades it out mid-clip;
#:   * told where it STANDS (this wording), it places the mascot on the
#:     ground in the scene and keeps it to the last frame — small, but there;
#:   * told additionally to make it "large, one third of the frame height",
#:     it returned the clip with no mascot at all.
#: So: say where it stands, do not dictate its size.
_EDIT_SUFFIX = (
    "The mascot stands on the ground in the lower foreground, feet on the floor, and stays "
    "fully visible and solid from the first frame to the last frame of the video. It never "
    "fades, never becomes transparent and never leaves the frame. It moves with the camera "
    "so it stays anchored in the scene. Keep the mascot's flat colourful cartoon style "
    "exactly as in Image 1. Keep everything else in Video 1 unchanged: the same real shop, "
    "people, food, lighting and camera movement."
)
DEFAULT_ACTION = "The mascot smiles and waves at the camera."

NO_MASCOT_MESSAGE = (
    "Maskot tidak muncul dalam video yang dijana. Percubaan ini tidak dikira dalam had "
    "harian anda. Sila cuba lagi, atau guna klip yang menunjukkan lantai atau meja dengan jelas."
)


def build_edit_prompt(merchant_prompt: str) -> str:
    """What wan3.0 receives. The merchant only says what the mascot does; the
    edit instruction and the "keep the real scene" half are ours. Pure."""
    action = " ".join((merchant_prompt or "").split())[:PROMPT_MAX]
    if action:
        action = action if action[-1] in ".!?" else action + "."
        action = f"What the mascot does: {action}"
    else:
        action = DEFAULT_ACTION
    return f"{_EDIT_PREFIX} {action} {_EDIT_SUFFIX}"


# --------------------------------------------------------------------------
# finishing — is the mascot actually there, and the burned-in AI label
# --------------------------------------------------------------------------

_RESULT_CHECK_PROMPT = (
    "The image is a cartoon mascot character. The video is a real-world clip that the mascot "
    "was supposed to be added to. Watch the whole video and answer ONLY with this JSON, "
    "nothing else:\n"
    '{"mascot_visible": true, "visible_at_end": true, "reason": "one short sentence"}\n'
    "mascot_visible: true only if that cartoon character (or a clearly recognisable version "
    "of it) appears anywhere in the video. visible_at_end: true only if it is still clearly "
    "visible in the final second. If there is no cartoon character in the video at all, both "
    "are false."
)


async def check_mascot_in_result(result: bytes, mascot: bytes, mascot_mime: str) -> Optional[Dict[str, Any]]:
    """Ask Qwen whether the rendered clip actually contains the mascot.

    Returns ``{"mascot_visible", "visible_at_end", "reason"}``, or None when
    the check could not run. None is NOT "missing": a render we could not
    inspect is delivered and counted like any other.
    """
    model = moderation.moderation_video_model()
    api_key = video._dashscope_api_key()
    if not api_key:
        return None
    try:
        video_url = await video.zai_video_service.upload_temp_file(
            result, f"{uuid.uuid4().hex}.mp4", model=model
        )
        payload = {
            "model": model,
            "input": {"messages": [{"role": "user", "content": [
                {"image": f"data:{mascot_mime};base64,{base64.b64encode(mascot).decode()}"},
                {"video": video_url},
                {"text": _RESULT_CHECK_PROMPT},
            ]}]},
            "parameters": {"max_tokens": 200},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                moderation.QWEN_VL_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-OssResourceResolve": "enable",
                },
                json=payload,
            )
        if response.status_code != 200:
            logger.warning("mascot result check failed: {} {}", response.status_code, response.text[:200])
            return None
        content = response.json()["output"]["choices"][0]["message"]["content"]
        text = content if isinstance(content, str) else next(
            (item["text"] for item in content if isinstance(item, dict) and "text" in item), ""
        )
        verdict = json.loads(text[text.index("{"):text.rindex("}") + 1])
        return {
            "mascot_visible": verdict.get("mascot_visible") is True,
            "visible_at_end": verdict.get("visible_at_end") is True,
            "reason": str(verdict.get("reason") or "")[:300],
        }
    except Exception as exc:  # noqa: BLE001 - a broken check must not lose a paid render
        logger.warning("mascot result check errored: {}: {}", type(exc).__name__, exc)
        return None


AI_LABEL_TEXT = "Dijana AI"


class LabelError(RuntimeError):
    pass


def ffmpeg_path() -> Optional[str]:
    """The system ffmpeg, else the one bundled with imageio-ffmpeg (the
    Render runtime has no system ffmpeg)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - not installed, or no binary for this platform
        return None


def ai_label_png() -> bytes:
    """The label as a transparent PNG: white text on a dark rounded pill.
    Drawn with Pillow so ffmpeg needs neither drawtext nor a font file."""
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.load_default(size=44)
    except TypeError:  # Pillow < 10.1 has only the small bitmap font
        font = ImageFont.load_default()
    left, top, right, bottom = font.getbbox(AI_LABEL_TEXT)
    pad_x, pad_y = 26, 16
    width, height = (right - left) + 2 * pad_x, (bottom - top) + 2 * pad_y
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=height // 2, fill=(0, 0, 0, 170))
    draw.text((pad_x - left, pad_y - top), AI_LABEL_TEXT, font=font, fill=(255, 255, 255, 240))
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def burn_ai_label(data: bytes) -> bytes:
    """Re-encode the clip with a small "Dijana AI" label in the bottom-left
    corner, so a downloaded file or a hero clip carries it. The label is
    scaled to 5.5 % of the video's height whatever its size. Blocking — call
    it through ``asyncio.to_thread``. Raises LabelError."""
    binary = ffmpeg_path()
    if not binary:
        raise LabelError("ffmpeg is not available")
    with tempfile.TemporaryDirectory(prefix="mascot-label-") as folder:
        src, label, dst = (os.path.join(folder, name) for name in ("in.mp4", "label.png", "out.mp4"))
        with open(src, "wb") as handle:
            handle.write(data)
        with open(label, "wb") as handle:
            handle.write(ai_label_png())
        command = [
            binary, "-v", "error", "-y", "-i", src, "-i", label,
            "-filter_complex",
            "[1:v][0:v]scale2ref=w=oh*mdar:h=ih*0.055[label][clip];"
            "[clip][label]overlay=x=main_h*0.025:y=main_h-overlay_h-main_h*0.025",
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart", dst,
        ]
        try:
            done = subprocess.run(command, capture_output=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LabelError(f"ffmpeg did not finish: {type(exc).__name__}") from exc
        if done.returncode != 0 or not os.path.exists(dst):
            raise LabelError(f"ffmpeg failed: {done.stderr.decode(errors='replace')[-300:]}")
        with open(dst, "rb") as handle:
            labelled = handle.read()
    if not labelled:
        raise LabelError("ffmpeg wrote an empty file")
    return labelled


# --------------------------------------------------------------------------
# storage — private bucket, served through /mascot-videos/media/{key}
# --------------------------------------------------------------------------

def media_url(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    return f"{settings.BACKEND_URL.rstrip('/')}/api/v1/mascot-videos/media/{key}"


async def store_bytes(data: bytes, ext: str) -> str:
    key = f"{uuid.uuid4().hex}.{ext}"
    stored = await supabase_service.upload_file(BUCKET, key, data, content_type=EXT_MIME[ext])
    if not stored:
        raise RuntimeError("Supabase Storage refused the upload")
    return key


async def fetch_bytes(key: str) -> Optional[bytes]:
    """Read an object with the service key; None when it is not there."""
    if not MEDIA_KEY_RE.match(key or ""):
        return None
    url = f"{supabase_service.url}/storage/v1/object/{BUCKET}/{key}"
    headers = {"apikey": supabase_service.service_key, "Authorization": f"Bearer {supabase_service.service_key}"}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url, headers=headers)
    return resp.content if resp.status_code == 200 else None


# --------------------------------------------------------------------------
# rows
# --------------------------------------------------------------------------

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _day_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def public_view(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "status": row.get("status"),
        "prompt": row.get("prompt"),
        "clip_url": row.get("clip_url"),
        "mascot_url": row.get("mascot_url"),
        "result_url": row.get("result_url"),
        "clip_seconds": float(row.get("clip_seconds") or 0),
        "error": row.get("error"),
        "ai_generated": True,
        "created_at": row.get("created_at"),
        "finished_at": row.get("finished_at"),
    }


async def get_job(job_id: str, merchant_id: str) -> Optional[Dict[str, Any]]:
    """The merchant's own row, or None — another merchant's id is 'not found'."""
    try:
        uuid.UUID(str(job_id))
    except ValueError:
        return None
    rows = await db_select(TABLE, filters={"id": job_id, "merchant_id": merchant_id})
    return rows[0] if rows else None


async def list_jobs(merchant_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    return await db_select(
        TABLE,
        filters={"merchant_id": merchant_id},
        extra={"order": "created_at.desc", "limit": str(max(1, min(limit, 50)))},
    )


async def _submitted_today(merchant_id: str) -> List[Dict[str, Any]]:
    return await db_select(
        TABLE,
        filters={"merchant_id": merchant_id},
        extra={"created_at": f"gte.{_day_start_iso()}", "task_id": "not.is.null"},
        select="id,mascot_found",
    )


def count_usage(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """``renders`` is what the merchant's daily cap counts: jobs that reached
    the provider, minus those that came back with no mascot. ``attempts`` is
    every job that reached the provider, mascot or not. Pure."""
    return {
        "renders": sum(1 for row in rows if row.get("mascot_found") is not False),
        "attempts": len(rows),
    }


async def renders_today(merchant_id: str) -> int:
    """Renders that count against the cap today. A clip refused by moderation
    or validation was never rendered; a render that came back without the
    mascot is the provider's miss. Neither counts."""
    return count_usage(await _submitted_today(merchant_id))["renders"]


async def active_jobs(merchant_id: str) -> int:
    rows = await db_select(
        TABLE,
        filters={"merchant_id": merchant_id},
        extra={"status": f"in.({','.join(ACTIVE_STATUSES)})"},
        select="id",
    )
    return len(rows)


async def usage_today(merchant_id: str) -> Dict[str, int]:
    limit = daily_limit()
    counts = count_usage(await _submitted_today(merchant_id))
    return {
        "used": counts["renders"],
        "limit": limit,
        "remaining": max(0, limit - counts["renders"]),
        "attempts": counts["attempts"],
        "attempt_limit": daily_attempt_limit(),
    }


async def _patch(job_id: str, patch: Dict[str, Any]) -> None:
    patch.setdefault("updated_at", _iso_now())
    await db_update(TABLE, {"id": job_id}, patch)


async def _finish(job_id: str, status: str, message: str, provider_status: Optional[str] = None) -> None:
    patch: Dict[str, Any] = {"status": status, "error": message[:500], "finished_at": _iso_now()}
    if provider_status:
        patch["provider_status"] = provider_status
    await _patch(job_id, patch)


# --------------------------------------------------------------------------
# start + drive
# --------------------------------------------------------------------------

async def create_job(
    *,
    merchant_id: str,
    clip: bytes,
    clip_ext: str,
    clip_seconds: float,
    mascot: bytes,
    mascot_ext: str,
    prompt: str,
) -> Dict[str, Any]:
    """Store the inputs, write the row, start the background driver. The
    caller has validated the files, the consent box, the cap and the flag."""
    clip_key = await store_bytes(clip, clip_ext)
    mascot_key = await store_bytes(mascot, mascot_ext)
    res = resolution()
    row = await db_insert(
        TABLE,
        {
            "merchant_id": merchant_id,
            "clip_key": clip_key,
            "clip_url": media_url(clip_key),
            "mascot_key": mascot_key,
            "mascot_url": media_url(mascot_key),
            "prompt": " ".join((prompt or "").split())[:PROMPT_MAX],
            "status": "queued",
            "clip_seconds": clip_seconds,
            "resolution": res,
            "model": video.dashscope_video_model(),
            "consent_at": _iso_now(),
        },
    )
    _spawn(str(row["id"]))
    return row


def _spawn(job_id: str) -> None:
    task = asyncio.create_task(_drive(job_id))
    _running[job_id] = task
    task.add_done_callback(lambda _t: _running.pop(job_id, None))


async def _load(job_id: str) -> Optional[Dict[str, Any]]:
    rows = await db_select(TABLE, filters={"id": job_id})
    return rows[0] if rows else None


async def _drive(job_id: str) -> None:
    """Moderate → submit → poll → store. The row never stays in an active
    status when this returns."""
    try:
        row = await _load(job_id)
        if not row or row.get("status") not in ACTIVE_STATUSES:
            return
        task_id = row.get("task_id")
        if not task_id:
            task_id = await _moderate_and_submit(row)
            if not task_id:
                return
        await _poll_and_store(row, str(task_id))
    except Exception as exc:  # noqa: BLE001 - the row must never stay active
        logger.exception("mascot video {} crashed", job_id)
        await _finish(job_id, "failed", f"Ralat tidak dijangka ({type(exc).__name__}). Sila cuba lagi.")


async def _moderate_and_submit(row: Dict[str, Any]) -> Optional[str]:
    job_id = str(row["id"])
    clip = await fetch_bytes(row["clip_key"])
    mascot = await fetch_bytes(row["mascot_key"])
    if not clip or not mascot:
        await _finish(job_id, "failed", "Fail yang dimuat naik tidak dijumpai. Sila muat naik semula.")
        return None
    clip_name = f"{uuid.uuid4().hex}.{row['clip_key'].rsplit('.', 1)[1]}"
    clip_mime = EXT_MIME[row["clip_key"].rsplit(".", 1)[1]]

    # 1. Moderation, before anything is rendered. A temp URL is only
    #    resolvable by the model it was uploaded for, hence two uploads.
    await _patch(job_id, {"status": "moderating"})
    try:
        check_url = await video.zai_video_service.upload_temp_file(
            clip, clip_name, model=moderation.moderation_video_model(), content_type=clip_mime
        )
    except video.ZaiVideoError as exc:
        await _finish(job_id, "failed", f"Semakan kandungan tidak dapat dijalankan ({exc}). Sila cuba lagi.")
        return None
    verdict = await moderation.check_video_safety(check_url)
    if verdict.get("unavailable"):
        await _finish(job_id, "failed", "Semakan kandungan tidak tersedia buat masa ini. Sila cuba lagi nanti.")
        return None
    if not verdict.get("is_safe"):
        logger.warning("mascot video {} rejected by moderation: {}", job_id, verdict.get("reason"))
        await _finish(job_id, "rejected", "Klip ditolak: kandungan tidak sesuai dengan garis panduan kami.")
        return None

    # 2. Submit the edit.
    mascot_mime = EXT_MIME[row["mascot_key"].rsplit(".", 1)[1]]
    mascot_uri = f"data:{mascot_mime};base64,{base64.b64encode(mascot).decode()}"
    res = row.get("resolution") or resolution()
    try:
        clip_url = await video.zai_video_service.upload_temp_file(
            clip, clip_name, model=video.dashscope_video_model(), content_type=clip_mime
        )
        task_id = await video.zai_video_service.submit_video_edit(
            build_edit_prompt(row.get("prompt") or ""),
            video_url=clip_url,
            reference_image_urls=[mascot_uri],
            resolution=res,
            watermark=watermark(),
        )
    except video.ZaiVideoError as exc:
        logger.warning("mascot video {} submit failed: {}", job_id, exc)
        await _finish(job_id, "failed", "Penjana video tidak menerima permintaan ini. Sila cuba lagi.")
        return None
    await _patch(
        job_id,
        {
            "task_id": task_id,
            "status": "processing",
            "provider_status": "PENDING",
            "cost": estimate_cost_usd(float(row.get("clip_seconds") or 0), res),
        },
    )
    return task_id


async def _poll_and_store(row: Dict[str, Any], task_id: str) -> None:
    job_id = str(row["id"])
    loop = asyncio.get_event_loop()
    deadline = loop.time() + video.zai_video_max_wait_seconds()
    poll_errors = 0
    while loop.time() < deadline:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        try:
            result = await video.zai_video_service.fetch_result(task_id, provider=video.PROVIDER_DASHSCOPE)
        except video.ZaiVideoError as exc:
            poll_errors += 1
            logger.warning("mascot video {} poll error {}: {}", job_id, poll_errors, exc)
            if poll_errors >= 8:
                await _finish(job_id, "failed", "Status penjanaan tidak dapat dibaca. Sila cuba lagi.")
                return
            continue
        state = result.get("status")
        if state == "processing":
            continue
        if state == "fail":
            logger.warning("mascot video {} failed at provider: {} {}", job_id, result.get("code"), result.get("message"))
            await _finish(job_id, "failed", "Video tidak dapat dijana daripada klip ini. Cuba klip lain.", result.get("raw_status"))
            return
        # success → the provider URL lives 24 h.
        data = await video.zai_video_service.download(str(result["video_url"]))
        patch: Dict[str, Any] = {"provider_status": result.get("raw_status"), "finished_at": _iso_now()}
        usage = await video.zai_video_service.fetch_dashscope_usage(task_id)
        billed = float(usage.get("duration") or 0)
        if billed > 0:
            res = f"{usage.get('SR')}P" if usage.get("SR") else (row.get("resolution") or resolution())
            patch["cost"] = round(billed * usd_per_second(res), 4)

        # Did the model actually add the mascot? One render in five in Phase 1
        # came back as the untouched clip. That is the provider's miss, not
        # the merchant's: it is not delivered and not counted against the cap.
        mascot = await fetch_bytes(row["mascot_key"])
        verdict = None
        if mascot:
            mascot_mime = EXT_MIME[row["mascot_key"].rsplit(".", 1)[1]]
            verdict = await check_mascot_in_result(data, mascot, mascot_mime)
        if verdict is not None and not verdict["mascot_visible"]:
            logger.warning("mascot video {} has no mascot: {}", job_id, verdict.get("reason"))
            await _patch(job_id, {**patch, "status": "failed", "mascot_found": False, "error": NO_MASCOT_MESSAGE})
            return

        try:
            data = await asyncio.to_thread(burn_ai_label, data)
        except LabelError as exc:
            # An unlabelled AI clip is not handed out.
            logger.error("mascot video {} could not be labelled: {}", job_id, exc)
            await _patch(job_id, {**patch, "status": "failed", "error": "Video tidak dapat disiapkan. Sila cuba lagi."})
            return
        key = await store_bytes(data, "mp4")
        patch.update({
            "status": "ready",
            "result_key": key,
            "result_url": media_url(key),
            "mascot_found": True if verdict is not None else None,
            "error": None,
        })
        await _patch(job_id, patch)
        logger.info("mascot video {} ready ({} KB)", job_id, len(data) // 1024)
        return
    await _finish(job_id, "failed", "Penjanaan mengambil masa terlalu lama. Sila cuba lagi.", "TIMEOUT")


def _age_seconds(row: Dict[str, Any]) -> float:
    try:
        ts = datetime.fromisoformat(str(row.get("created_at")).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - ts).total_seconds()
    except ValueError:
        return 0.0


async def ensure_driver(row: Dict[str, Any]) -> Dict[str, Any]:
    """A row left active by a backend restart has no driver. Called from the
    GET path: a job the provider already accepted is picked up again (it was
    paid for); one that never got that far, or is past the wait limit, fails."""
    if row.get("status") not in ACTIVE_STATUSES:
        return row
    job_id = str(row["id"])
    if job_id in _running:
        return row
    age = _age_seconds(row)
    if age > video.zai_video_max_wait_seconds() + 300:
        await _finish(job_id, "failed", "Penjanaan terhenti. Sila cuba lagi.", "TIMEOUT")
        return {**row, "status": "failed", "error": "Penjanaan terhenti. Sila cuba lagi."}
    if row.get("task_id") or age > 60:
        # Either resume the poll, or (no task yet, driver gone for a minute)
        # run the job from the top — nothing has been billed for it yet.
        _spawn(job_id)
    return row
