"""GLM video generation (Z.ai CogVideoX) for hero video backgrounds.

The Z.ai video API is asynchronous:

    POST {ZAI_API_URL}/videos/generations      → {"id", "task_status": "PROCESSING"}
    GET  {ZAI_API_URL}/async-result/{id}       → {"task_status": "SUCCESS",
                                                  "video_result": [{"url", "cover_image_url"}]}

A 5-second clip takes anywhere from ~30s to a few minutes, far past what a
single HTTP request from the dashboard should hold open, so the flow is
split in two exactly like the API itself:

    task_id = await zai_video_service.submit(prompt)       # instant
    result  = await zai_video_service.fetch_result(task_id) # poll from the client
    stored  = await zai_video_service.store(result)         # → Cloudinary URLs

The Z.ai download URL is temporary; ``store`` pushes the bytes into
Cloudinary (``resource_type="video"``) so the page keeps working after the
Z.ai link expires. The poster is a Cloudinary-derived first frame of the
same asset — no second upload, no second thing to expire.

Feature flag: HERO_VIDEO_ENABLED (env, default false, read per call). With
it off the endpoints 404 and nothing in this module is reached.

In-memory job registry
----------------------
Jobs live in a process-local dict, the same shape as ``job_service`` for
website generation: a Render restart forgets in-flight tasks and the
dashboard simply asks the merchant to try again. Nothing here touches the
database, quota counters or subscription rows.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Tuple, Dict, Optional
from urllib.parse import quote, urlsplit

import cloudinary
import cloudinary.uploader
import httpx

from app.services.hero_video_patcher import hero_video_delivery_url
from loguru import logger


# ---------------------------------------------------------------------------
# Configuration (read at call time so Render env changes need no redeploy)
# ---------------------------------------------------------------------------

def hero_video_enabled() -> bool:
    """HERO_VIDEO_ENABLED=true turns the feature on. Default off."""
    return os.getenv("HERO_VIDEO_ENABLED", "false").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _zai_api_key() -> Optional[str]:
    return (os.getenv("ZAI_API_KEY") or "").strip() or None


def _zai_base_url() -> str:
    # Same precedence as ai_service: the Render var is ZAI_BASE_URL,
    # ZAI_API_URL also works and wins when both are set.
    return (
        os.getenv("ZAI_API_URL")
        or os.getenv("ZAI_BASE_URL")
        or "https://api.z.ai/api/paas/v4"
    ).rstrip("/")


def zai_video_model() -> str:
    """The Z.ai video model code. ``cogvideox-3`` is the current one."""
    return os.getenv("ZAI_VIDEO_MODEL", "cogvideox-3").strip() or "cogvideox-3"


# ---------------------------------------------------------------------------
# Provider switch — DashScope (Alibaba Model Studio) or Z.ai
# ---------------------------------------------------------------------------

PROVIDER_DASHSCOPE = "dashscope"
PROVIDER_ZAI = "zai"
PROVIDERS = (PROVIDER_DASHSCOPE, PROVIDER_ZAI)


def hero_video_provider() -> str:
    """Which video API makes the clip. ``dashscope`` (default) is Alibaba
    Model Studio's async video-synthesis endpoint running the unified
    wan3.0-video model; ``zai`` is the original CogVideoX path. Everything after the
    clip exists (download, Cloudinary, patch, publish) is provider-agnostic."""
    value = os.getenv("HERO_VIDEO_PROVIDER", PROVIDER_DASHSCOPE).strip().lower()
    return value if value in PROVIDERS else PROVIDER_DASHSCOPE


def _dashscope_key_source() -> Tuple[Optional[str], str]:
    """(key, env var name it came from). Whitespace is stripped: a key pasted
    from a phone often arrives with a trailing newline, which the API rejects
    as InvalidApiKey. DASHSCOPE_API_KEY wins over the Qwen text key."""
    for name in ("DASHSCOPE_API_KEY", "QWEN_API_KEY"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value, name
    return None, ""


def _dashscope_api_key() -> Optional[str]:
    return _dashscope_key_source()[0]


def _key_fingerprint(key: Optional[str]) -> str:
    """Enough to tell two keys apart in a log, never enough to use one."""
    if not key:
        return "none"
    if len(key) <= 10:
        return f"{key[:2]}…({len(key)} chars)"
    return f"{key[:6]}…{key[-4:]} ({len(key)} chars)"


def _dashscope_base_url() -> str:
    # The NATIVE DashScope API root (not the OpenAI-compatible one QWEN_BASE_URL
    # points at). International endpoint by default.
    return (
        os.getenv("DASHSCOPE_API_URL") or "https://dashscope-intl.aliyuncs.com/api/v1"
    ).rstrip("/")


#: Alibaba's unified video model: text-, image- AND video-to-video on the one
#: video-synthesis endpoint. Replaced HappyHorse-T2V, which could only do
#: text-to-video and silently dropped the merchant's hero photo.
DEFAULT_DASHSCOPE_VIDEO_MODEL = "wan3.0-video"


def dashscope_video_model() -> str:
    """DashScope video model. ``wan3.0-video`` by default."""
    return (
        os.getenv("DASHSCOPE_VIDEO_MODEL", DEFAULT_DASHSCOPE_VIDEO_MODEL).strip()
        or DEFAULT_DASHSCOPE_VIDEO_MODEL
    )


def _dashscope_is_unified(model: str) -> bool:
    """wan3.x takes the request shape documented for the unified model:
    ``input.media`` for image-to-video, ``audio`` (on by default, we turn it
    off), ``ratio: adaptive``. Older / ``-t2v`` models keep the legacy shape
    byte-for-byte so an operator who pins one is not broken."""
    return (model or "").strip().lower().startswith("wan3")


DASHSCOPE_RESOLUTIONS = ("480P", "720P", "1080P")
#: "adaptive" follows the input material's own aspect (wan3.x only).
DASHSCOPE_RATIOS = ("16:9", "9:16", "1:1", "4:3", "3:4", "adaptive")


def dashscope_video_resolution() -> str:
    """480P / 720P / 1080P. 720P by default — the hero is wide and 1080P
    costs more per second and doubles what every visitor downloads."""
    value = os.getenv("DASHSCOPE_VIDEO_RESOLUTION", "720P").strip().upper()
    return value if value in DASHSCOPE_RESOLUTIONS else "720P"


def dashscope_video_ratio() -> str:
    value = os.getenv("DASHSCOPE_VIDEO_RATIO", "16:9").strip()
    return value if value in DASHSCOPE_RATIOS else "16:9"


def dashscope_video_watermark() -> bool:
    """Whether DashScope may stamp its provider mark ("Happy Horse" /
    "AI generated") in the clip's corner. Off by default: the clip sits
    behind a merchant's own brand, and the first HappyHorse output arrived
    with the mark burned into the bottom-right corner."""
    return os.getenv("DASHSCOPE_VIDEO_WATERMARK", "false").strip().lower() in (
        "1", "true", "yes", "on",
    )


def hero_video_model() -> str:
    """The model name shown in the picker, for whichever provider is active."""
    return dashscope_video_model() if hero_video_provider() == PROVIDER_DASHSCOPE else zai_video_model()


def hero_video_fallback_provider() -> Optional[str]:
    """Provider to try when the primary cannot ACCEPT a job (bad key, quota,
    outage — anything that fails at submit). Defaults to Z.ai when DashScope
    is primary, so a misconfigured DashScope key degrades to the older path
    instead of a dead feature. ``none`` disables the fallback. Never used for
    a job that was accepted and then failed — that is a real failure."""
    raw = os.getenv("HERO_VIDEO_FALLBACK_PROVIDER", "").strip().lower()
    if raw in ("none", "off", "false", "0"):
        return None
    if raw in PROVIDERS:
        return raw if raw != hero_video_provider() else None
    return PROVIDER_ZAI if hero_video_provider() == PROVIDER_DASHSCOPE else None


def _provider_configured(provider: str) -> bool:
    if provider == PROVIDER_DASHSCOPE:
        return bool(_dashscope_api_key())
    return bool(_zai_api_key())


def _provider_animates_images(provider: str) -> bool:
    """Can this provider make image-to-video? Z.ai's CogVideoX path always
    can. DashScope can with the unified wan3.x model (the default); a pinned
    ``-t2v`` model such as HappyHorse is text-to-video only and drops the
    photo on the floor."""
    if provider == PROVIDER_DASHSCOPE:
        return _dashscope_is_unified(dashscope_video_model())
    return True


#: Landscape 720p: a hero is wide, and 1080p doubles the bytes every visitor
#: downloads for no visible gain behind a text scrim.
DEFAULT_VIDEO_SIZE = "1280x720"
ALLOWED_VIDEO_SIZES = (
    "1280x720", "1920x1080", "720x1280", "1080x1920", "1024x1024",
)
ALLOWED_DURATIONS = (5, 10)


def zai_video_size() -> str:
    size = os.getenv("ZAI_VIDEO_SIZE", DEFAULT_VIDEO_SIZE).strip()
    return size if size in ALLOWED_VIDEO_SIZES else DEFAULT_VIDEO_SIZE


def zai_video_duration() -> int:
    try:
        value = int(os.getenv("ZAI_VIDEO_DURATION", "5"))
    except ValueError:
        value = 5
    return value if value in ALLOWED_DURATIONS else 5


def zai_video_fps() -> int:
    try:
        value = int(os.getenv("ZAI_VIDEO_FPS", "30"))
    except ValueError:
        value = 30
    return 60 if value == 60 else 30


def zai_video_quality() -> str:
    """``speed`` (default) or ``quality``."""
    value = os.getenv("ZAI_VIDEO_QUALITY", "speed").strip().lower()
    return "quality" if value == "quality" else "speed"


def zai_video_timeout_seconds() -> float:
    """Per-HTTP-call cap (submit, poll, download)."""
    try:
        return float(os.getenv("ZAI_VIDEO_TIMEOUT_SECONDS", "90"))
    except ValueError:
        return 90.0


def zai_video_max_wait_seconds() -> float:
    """How long a task may stay PROCESSING before the job is marked failed."""
    try:
        return float(os.getenv("ZAI_VIDEO_MAX_WAIT_SECONDS", "600"))
    except ValueError:
        return 600.0


def zai_video_max_bytes() -> int:
    """Refuse to store anything bigger — a hero clip should be a few MB."""
    try:
        return int(os.getenv("ZAI_VIDEO_MAX_BYTES", str(60 * 1024 * 1024)))
    except ValueError:
        return 60 * 1024 * 1024


#: Z.ai caps the prompt at 512 characters.
ZAI_PROMPT_MAX_CHARS = 512

_DOWNLOAD_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

#: Ambience presets the dashboard offers. Each is a short, loop-friendly
#: scene description; the merchant's business is prepended by the builder.
VIDEO_STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "cinematic": {
        "label_ms": "Sinematik",
        "label_en": "Cinematic",
        "scene": (
            "slow cinematic camera drift, warm golden-hour light, shallow depth "
            "of field, soft bokeh, gentle continuous motion"
        ),
    },
    "ambient": {
        "label_ms": "Tenang",
        "label_en": "Ambient",
        "scene": (
            "calm ambient atmosphere, soft diffused daylight, very slow push-in, "
            "subtle steam and light movement, serene mood"
        ),
    },
    "energetic": {
        "label_ms": "Bertenaga",
        "label_en": "Energetic",
        "scene": (
            "vibrant lively scene, dynamic but smooth camera motion, rich "
            "saturated colours, upbeat energy"
        ),
    },
    "elegant": {
        "label_ms": "Elegan",
        "label_en": "Elegant",
        "scene": (
            "luxurious minimal composition, dark moody lighting with soft "
            "highlights, slow elegant camera glide, premium feel"
        ),
    },
    "nature": {
        "label_ms": "Alam semula jadi",
        "label_en": "Nature",
        "scene": (
            "lush natural setting, gentle breeze moving leaves, soft sunlight "
            "through foliage, tranquil slow motion"
        ),
    },
}
DEFAULT_VIDEO_STYLE = "cinematic"

#: Rules appended to every prompt. Text and logos render as gibberish in
#: generated video, and a hero background must never fight the copy on top.
_PROMPT_SUFFIX = (
    "Background video for a website hero: no text, no letters, no logos, "
    "no watermarks, no captions, no people looking at camera, seamless loop, "
    "smooth motion, high quality, 16:9."
)

_WHITESPACE_RE = re.compile(r"\s+")


def _squash(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "")).strip()


#: Characters that already close a sentence, so _terminate leaves them alone.
_SENTENCE_ENDINGS = ".!?…"


def _terminate(text: str) -> str:
    """End a fragment with a full stop so the next one starts a new sentence.

    Merchant-written prompts almost never end in punctuation, and every part
    of this prompt used to be joined with a bare space. That produced run-on
    sentences that swallowed the subject: "Golden dress rotate behind
    beautifully Background video for a website hero: no text, ..." reads as
    one clause about a background video, not as an instruction to rotate a
    golden dress. Video models weight a run-on clause as a single thought, so
    the merchant's actual request was competing with the boilerplate instead
    of leading it.
    """
    t = (text or "").rstrip()
    if not t:
        return t
    return t if t[-1] in _SENTENCE_ENDINGS else t + "."


def build_hero_video_prompt(
    *,
    business_name: str = "",
    business_type: str = "",
    description: str = "",
    style: str = DEFAULT_VIDEO_STYLE,
    custom_prompt: str = "",
    hero_image_prompt: str = "",
) -> str:
    """Compose the video prompt. Always ≤ 512 characters.

    ONE hero visual, two renderings. ``hero_image_prompt`` is the merchant's
    description of the hero picture (persisted on the website row and used
    to generate the still hero). When present it is the SCENE of the video
    too, so the clip animates the picture the merchant asked for instead of
    a second guess at the business. ``custom_prompt`` is the video card's
    own field — what MOVES — and is appended as the motion. With no hero
    prompt, a custom prompt is the whole scene (previous behaviour); with
    neither, the business description and the style preset become the scene.
    """
    preset = VIDEO_STYLE_PRESETS.get(style) or VIDEO_STYLE_PRESETS[DEFAULT_VIDEO_STYLE]

    custom = _squash(custom_prompt)
    hero_scene = _squash(hero_image_prompt)
    if hero_scene:
        scene = hero_scene
        motion = custom or preset["scene"]
        scene = f"{_terminate(scene)} {motion}"
        logger.info(
            f"🎬 Video scene seeded from the merchant's hero image prompt "
            f"({'merchant motion' if custom else 'preset ' + style})"
        )
    elif custom:
        # The merchant's own words lead the prompt, then the ambience they
        # picked in the UI. This branch used to be `scene = custom`, which
        # silently threw the style away: pick "Sinematik", type a prompt, and
        # the preset never reached the model — the style buttons were dead
        # controls for anyone who also wrote a prompt. Custom text stays first
        # so it remains the dominant subject.
        scene = f"{_terminate(custom)} {preset['scene']}"
        logger.info(f"🎬 Video scene from the merchant's prompt + preset {style}")
    else:
        subject_bits = []
        kind = _squash(business_type).replace("_", " ")
        if kind:
            subject_bits.append(f"a {kind} business")
        if business_name:
            subject_bits.append(f"called {_squash(business_name)}")
        subject = " ".join(subject_bits) or "a small business"
        desc = _squash(description)
        if len(desc) > 160:
            desc = desc[:157].rstrip() + "..."
        scene = f"Atmospheric scene for {subject}"
        if desc:
            scene += f": {desc}"
        scene += f". {preset['scene']}."

    # -2 not -1: one char for the space before the suffix, one for the full
    # stop _terminate may add after truncation. Without the extra char a
    # max-length scene would push the finished prompt one over the provider
    # limit and get clipped mid-word by the API.
    suffix_room = ZAI_PROMPT_MAX_CHARS - len(_PROMPT_SUFFIX) - 2
    if len(scene) > suffix_room:
        scene = scene[: suffix_room - 3].rstrip() + "..."
    # Close the scene before the boilerplate so the suffix reads as its own
    # instruction rather than as the tail of the merchant's sentence.
    prompt = f"{_terminate(scene)} {_PROMPT_SUFFIX}"
    # Full, untruncated — same rule as the image prompt log.
    logger.info(f"🎬 VIDEO PROMPT [style={style}]: {prompt}")
    return prompt


# ---------------------------------------------------------------------------
# Job registry
# ---------------------------------------------------------------------------

JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_STORING = "storing"
#: A clip generated BEFORE its site existed (prepared while the page was
#: being generated) is stored and waiting for the publish that will carry
#: it. Not "active": it costs nothing to hold and blocks no new job.
JOB_STATUS_READY = "ready"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

#: Forget finished jobs after this long; in-flight ones after max-wait + slack.
_JOB_TTL_SECONDS = 2 * 60 * 60


@dataclass
class HeroVideoJob:
    job_id: str
    task_id: str
    #: Empty for a job prepared before its site existed; the publish that
    #: claims the clip fills it in.
    website_id: str
    user_id: str
    prompt: str
    settings: Dict
    created_at: float = field(default_factory=time.monotonic)
    status: str = JOB_STATUS_PROCESSING
    error: Optional[str] = None
    video_url: Optional[str] = None
    poster_url: Optional[str] = None
    #: The merchant's hero photo the job was asked to animate, if any. Kept
    #: so the finaliser can use it as the still fallback instead of the
    #: clip's first frame.
    image_url: Optional[str] = None
    applied: bool = False
    live_site_updated: bool = False
    #: Which API holds this task — polling must go back to the same one even
    #: if HERO_VIDEO_PROVIDER changes or the job came from the fallback.
    provider: str = ""
    #: One hero_video add-on credit was consumed for this job (paid users).
    #: A job that then fails to deliver gives it back exactly once.
    charged: bool = False
    refunded: bool = False
    #: Filled by the background finaliser once the clip is on the page:
    #: settings / base_source / html_content / message / warning. The poll
    #: merges it into the completed response so the dashboard gets the
    #: patched page without the request that observed SUCCESS having to do
    #: the download + upload + patch + publish inline.
    result_payload: Optional[Dict] = None
    #: The asyncio task doing that finalising, so tests (and a shutdown
    #: hook) can await it.
    finalize_task: Optional["asyncio.Task"] = field(default=None, repr=False)
    #: The server-side task that polls the provider until the job is
    #: terminal, so the clip lands even when no browser is polling.
    driver_task: Optional["asyncio.Task"] = field(default=None, repr=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def age_seconds(self) -> float:
        return time.monotonic() - self.created_at

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "website_id": self.website_id,
            "status": self.status,
            "error": self.error,
            "video_url": self.video_url,
            "poster_url": self.poster_url,
            "image_url": self.image_url,
            "applied": self.applied,
            "live_site_updated": self.live_site_updated,
            "elapsed_seconds": round(self.age_seconds()),
            "provider": self.provider or hero_video_provider(),
            "charged": self.charged,
            "refunded": self.refunded,
        }


class ZaiVideoError(Exception):
    """A Z.ai call failed in a way the caller should surface, not retry."""


class ZaiVideoService:
    def __init__(self) -> None:
        self._jobs: Dict[str, HeroVideoJob] = {}

    # ---- registry ---------------------------------------------------------

    def _sweep(self) -> None:
        stale = [
            job_id
            for job_id, job in self._jobs.items()
            if job.age_seconds() > _JOB_TTL_SECONDS
        ]
        for job_id in stale:
            self._jobs.pop(job_id, None)

    def get_job(self, job_id: str) -> Optional[HeroVideoJob]:
        self._sweep()
        return self._jobs.get(job_id)

    def active_job_for_website(self, website_id: str) -> Optional[HeroVideoJob]:
        """The in-flight job for a site, if any — one at a time per site."""
        self._sweep()
        for job in self._jobs.values():
            if job.website_id == website_id and job.status in (
                JOB_STATUS_PROCESSING, JOB_STATUS_STORING,
            ):
                return job
        return None

    def active_jobs_for_user(self, user_id: str) -> int:
        self._sweep()
        return sum(
            1
            for job in self._jobs.values()
            if job.user_id == user_id
            and job.status in (JOB_STATUS_PROCESSING, JOB_STATUS_STORING)
        )

    def register_job(
        self,
        *,
        task_id: str,
        website_id: str,
        user_id: str,
        prompt: str,
        settings: Dict,
        provider: Optional[str] = None,
        charged: bool = False,
        image_url: Optional[str] = None,
    ) -> HeroVideoJob:
        job = HeroVideoJob(
            job_id=uuid.uuid4().hex,
            task_id=task_id,
            website_id=website_id,
            user_id=user_id,
            prompt=prompt,
            settings=settings,
            provider=provider or hero_video_provider(),
            charged=charged,
            image_url=image_url,
        )
        self._jobs[job.job_id] = job
        return job

    def drop_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    # ---- Z.ai calls -------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {_zai_api_key()}",
            "Content-Type": "application/json",
        }

    async def submit(
        self,
        prompt: str,
        *,
        duration: Optional[int] = None,
        size: Optional[str] = None,
        image_url: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> str:
        """Start a generation. Returns the provider's task id.

        ``with_audio`` is always false: the clip plays muted behind the hero,
        and audio would only make the file heavier.
        """
        if (provider or hero_video_provider()) == PROVIDER_DASHSCOPE:
            return await self._submit_dashscope(prompt, duration=duration, image_url=image_url)
        if not _zai_api_key():
            raise ZaiVideoError("ZAI_API_KEY is not configured")

        payload: Dict = {
            "model": zai_video_model(),
            "prompt": prompt[:ZAI_PROMPT_MAX_CHARS],
            "quality": zai_video_quality(),
            "with_audio": False,
            "size": size if size in ALLOWED_VIDEO_SIZES else zai_video_size(),
            "duration": duration if duration in ALLOWED_DURATIONS else zai_video_duration(),
            "fps": zai_video_fps(),
        }
        if image_url:
            # Image-to-video: animate the merchant's own hero photo.
            payload["image_url"] = image_url

        logger.info(
            f"🎬 Z.ai video submit ({payload['model']}, {payload['size']}, "
            f"{payload['duration']}s): {prompt[:80]}..."
        )
        try:
            async with httpx.AsyncClient(timeout=zai_video_timeout_seconds()) as client:
                response = await client.post(
                    f"{_zai_base_url()}/videos/generations",
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ZaiVideoError("Z.ai video submit timed out") from exc
        except httpx.HTTPError as exc:
            raise ZaiVideoError(f"Z.ai video submit failed: {exc}") from exc

        if response.status_code == 429:
            raise ZaiVideoError("Z.ai video rate limit — try again in a minute")
        if response.status_code != 200:
            logger.error(
                f"🎬 Z.ai video submit failed: {response.status_code} - {response.text[:200]}"
            )
            raise ZaiVideoError(f"Z.ai video submit failed ({response.status_code})")

        data = response.json() or {}
        task_id = data.get("id")
        if not task_id:
            raise ZaiVideoError("Z.ai video submit returned no task id")
        if str(data.get("task_status", "")).upper() == "FAIL":
            raise ZaiVideoError("Z.ai rejected the video request")
        logger.info(f"🎬 Z.ai video task {task_id} accepted")
        return str(task_id)

    async def fetch_result(self, task_id: str, provider: Optional[str] = None) -> Dict:
        """One poll of ``/async-result/{id}``.

        Returns ``{"status": "processing"|"success"|"fail",
                   "video_url": str|None, "cover_image_url": str|None}``.
        """
        if (provider or hero_video_provider()) == PROVIDER_DASHSCOPE:
            return await self._fetch_result_dashscope(task_id)
        if not _zai_api_key():
            raise ZaiVideoError("ZAI_API_KEY is not configured")
        try:
            async with httpx.AsyncClient(timeout=zai_video_timeout_seconds()) as client:
                response = await client.get(
                    f"{_zai_base_url()}/async-result/{task_id}",
                    headers=self._headers(),
                )
        except httpx.TimeoutException as exc:
            raise ZaiVideoError("Z.ai video poll timed out") from exc
        except httpx.HTTPError as exc:
            raise ZaiVideoError(f"Z.ai video poll failed: {exc}") from exc

        if response.status_code == 429:
            # Rate-limited poll: report "still processing" so the client
            # simply asks again after its normal interval.
            return {"status": "processing", "video_url": None, "cover_image_url": None}
        if response.status_code != 200:
            logger.error(
                f"🎬 Z.ai video poll failed: {response.status_code} - {response.text[:200]}"
            )
            raise ZaiVideoError(f"Z.ai video poll failed ({response.status_code})")

        data = response.json() or {}
        state = str(data.get("task_status", "")).upper()
        if state == "SUCCESS":
            results = data.get("video_result") or []
            first = (results[0] or {}) if results else {}
            video_url = first.get("url")
            if not video_url:
                raise ZaiVideoError("Z.ai reported success but returned no video URL")
            return {
                "status": "success",
                "video_url": video_url,
                "cover_image_url": first.get("cover_image_url"),
            }
        if state == "FAIL":
            return {"status": "fail", "video_url": None, "cover_image_url": None}
        return {"status": "processing", "video_url": None, "cover_image_url": None}

    async def submit_with_fallback(
        self,
        prompt: str,
        *,
        duration: Optional[int] = None,
        image_url: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Submit to the primary provider; if it cannot accept the job, try
        the fallback. Returns ``(task_id, provider)`` so the job remembers
        where to poll. Raises ZaiVideoError (the primary's) when nothing
        accepted the job.

        An image job goes to a provider that can animate the image. The
        default primary (DashScope) is text-to-video only and silently drops
        ``image_url`` — which is how a merchant who uploaded their storefront
        got a clip of strangers in a different restaurant. When a photo is
        supplied and Z.ai is configured, Z.ai is tried FIRST and the usual
        primary becomes the fallback, so an image job is never worse than a
        text job; with no Z.ai key the order is exactly as before.
        """
        primary = hero_video_provider()
        fallback = hero_video_fallback_provider()
        if (
            image_url
            and not _provider_animates_images(primary)
            and _provider_configured(PROVIDER_ZAI)
        ):
            logger.info(
                f"🎬 Hero photo supplied — routing to {PROVIDER_ZAI} (image-to-video); "
                f"{primary} is the fallback"
            )
            primary, fallback = PROVIDER_ZAI, primary
        try:
            return await self.submit(prompt, duration=duration, image_url=image_url, provider=primary), primary
        except ZaiVideoError as primary_exc:
            if not fallback or not _provider_configured(fallback):
                raise
            logger.warning(
                f"🎬 {primary} could not accept the video job ({primary_exc}) — "
                f"falling back to {fallback}"
            )
            try:
                task_id = await self.submit(prompt, duration=duration, image_url=image_url, provider=fallback)
            except ZaiVideoError as fallback_exc:
                logger.error(f"🎬 fallback {fallback} failed too: {fallback_exc}")
                raise primary_exc from fallback_exc
            return task_id, fallback

    # ---- DashScope (Alibaba Model Studio) ---------------------------------

    def _dashscope_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {_dashscope_api_key()}",
            "Content-Type": "application/json",
            # Video synthesis is async-only: the create call returns a task id
            # and GET /tasks/{id} is polled until SUCCEEDED/FAILED.
            "X-DashScope-Async": "enable",
        }

    async def _submit_dashscope(
        self,
        prompt: str,
        *,
        duration: Optional[int] = None,
        image_url: Optional[str] = None,
    ) -> str:
        if not _dashscope_api_key():
            raise ZaiVideoError("DASHSCOPE_API_KEY is not configured")
        model = dashscope_video_model()
        unified = _dashscope_is_unified(model)
        if image_url and not unified:
            # A pinned text-to-video-only model. We only land here with a
            # photo when Z.ai is not configured either (submit_with_fallback
            # routes image jobs there first), so say loudly that the clip
            # will not be based on it. The photo still serves as the poster.
            logger.warning(
                f"🎬 DashScope model {model} cannot animate a photo (text-to-video "
                "only) — the clip will NOT be based on the merchant's hero image"
            )

        input_block: Dict = {"prompt": prompt[:ZAI_PROMPT_MAX_CHARS]}
        parameters: Dict = {
            "resolution": dashscope_video_resolution(),
            "ratio": dashscope_video_ratio(),
            "duration": duration if duration in ALLOWED_DURATIONS else zai_video_duration(),
        }
        if unified:
            if image_url:
                # Image-to-video: the merchant's photo is the clip's first
                # frame, and "adaptive" makes the clip follow the photo's own
                # aspect — the pairing the wan3.0 reference documents.
                input_block["media"] = [{"type": "first_frame", "url": image_url}]
                parameters["ratio"] = "adaptive"
            # wan3.x generates a soundtrack by default. The clip plays muted
            # behind the hero, so audio only makes every visitor's download
            # heavier (same call the Z.ai path makes with with_audio=False).
            parameters["audio"] = False
            # "watermark" is not in wan3.0's documented parameter list. Send
            # it only when an operator explicitly opts in, rather than risk
            # a rejected request on every job for a default of False.
            if dashscope_video_watermark():
                parameters["watermark"] = True
        else:
            parameters["watermark"] = dashscope_video_watermark()

        payload: Dict = {"model": model, "input": input_block, "parameters": parameters}
        logger.info(
            f"🎬 DashScope video submit ({payload['model']}, "
            f"{payload['parameters']['resolution']} {payload['parameters']['ratio']}, "
            f"{payload['parameters']['duration']}s): {prompt[:80]}..."
        )
        try:
            async with httpx.AsyncClient(timeout=zai_video_timeout_seconds()) as client:
                response = await client.post(
                    f"{_dashscope_base_url()}/services/aigc/video-generation/video-synthesis",
                    headers=self._dashscope_headers(),
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ZaiVideoError("DashScope video submit timed out") from exc
        except httpx.HTTPError as exc:
            raise ZaiVideoError(f"DashScope video submit failed: {exc}") from exc

        if response.status_code == 429:
            raise ZaiVideoError("DashScope video rate limit — try again in a minute")
        if response.status_code != 200:
            logger.error(
                f"🎬 DashScope video submit failed: {response.status_code} - {response.text[:300]}"
            )
            if response.status_code in (401, 403):
                key, source = _dashscope_key_source()
                logger.error(
                    f"🎬 DashScope rejected the key from {source or 'no env var'} "
                    f"[{_key_fingerprint(key)}] at {_dashscope_base_url()} — check it is an "
                    f"API key for THIS region (intl keys only work on dashscope-intl)"
                )
            raise ZaiVideoError(f"DashScope video submit failed ({response.status_code})")

        data = response.json() or {}
        output = data.get("output") or {}
        task_id = output.get("task_id")
        if not task_id:
            logger.error(f"🎬 DashScope video submit returned no task id: {str(data)[:300]}")
            raise ZaiVideoError("DashScope video submit returned no task id")
        state = str(output.get("task_status", "")).upper()
        if state in ("FAILED", "CANCELED"):
            raise ZaiVideoError(f"DashScope rejected the video request ({output.get('message') or state})")
        logger.info(f"🎬 DashScope video task {task_id} accepted ({state or 'PENDING'})")
        return str(task_id)

    async def _fetch_result_dashscope(self, task_id: str) -> Dict:
        """One poll of ``GET /tasks/{task_id}``.

        DashScope states: PENDING / RUNNING → processing; SUCCEEDED → success
        with ``output.video_url`` (valid 24h — we copy it to Cloudinary at
        once); FAILED / CANCELED / UNKNOWN → fail.
        """
        if not _dashscope_api_key():
            raise ZaiVideoError("DASHSCOPE_API_KEY is not configured")
        try:
            async with httpx.AsyncClient(timeout=zai_video_timeout_seconds()) as client:
                response = await client.get(
                    f"{_dashscope_base_url()}/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {_dashscope_api_key()}"},
                )
        except httpx.TimeoutException as exc:
            raise ZaiVideoError("DashScope video poll timed out") from exc
        except httpx.HTTPError as exc:
            raise ZaiVideoError(f"DashScope video poll failed: {exc}") from exc

        if response.status_code == 429:
            return {"status": "processing", "video_url": None, "cover_image_url": None}
        if response.status_code != 200:
            logger.error(
                f"🎬 DashScope video poll failed: {response.status_code} - {response.text[:300]}"
            )
            raise ZaiVideoError(f"DashScope video poll failed ({response.status_code})")

        data = response.json() or {}
        output = data.get("output") or {}
        state = str(output.get("task_status", "")).upper()
        if state == "SUCCEEDED":
            video_url = output.get("video_url")
            if not video_url:
                raise ZaiVideoError("DashScope reported success but returned no video URL")
            return {"status": "success", "video_url": video_url, "cover_image_url": None}
        if state in ("FAILED", "CANCELED", "UNKNOWN"):
            logger.error(
                f"🎬 DashScope video task {task_id} {state}: "
                f"{output.get('code')} {str(output.get('message'))[:200]}"
            )
            return {"status": "fail", "video_url": None, "cover_image_url": None}
        return {"status": "processing", "video_url": None, "cover_image_url": None}

    # ---- storage ----------------------------------------------------------

    @staticmethod
    def _verbatim_download_url(url: str):
        """Keep the Z.ai CDN URL byte-for-byte — see ai_service for why."""
        try:
            parts = urlsplit(url)
            target = parts.path + (f"?{parts.query}" if parts.query else "")
            wire_target = "".join(
                ch if 0x20 < ord(ch) < 0x7F else quote(ch) for ch in target
            )
            return httpx.URL(
                scheme=parts.scheme,
                host=parts.hostname,
                port=parts.port,
                raw_path=wire_target.encode("ascii"),
            )
        except Exception:
            return url

    async def download(self, url: str) -> bytes:
        limit = zai_video_max_bytes()
        try:
            async with httpx.AsyncClient(
                timeout=zai_video_timeout_seconds(), follow_redirects=True
            ) as client:
                response = await client.get(
                    self._verbatim_download_url(url),
                    headers={
                        "User-Agent": _DOWNLOAD_USER_AGENT,
                        "Accept": "video/*,*/*;q=0.8",
                    },
                )
        except httpx.TimeoutException as exc:
            raise ZaiVideoError("Video download timed out") from exc
        except httpx.HTTPError as exc:
            raise ZaiVideoError(f"Video download failed: {exc}") from exc

        if response.status_code != 200:
            raise ZaiVideoError(f"Video download failed ({response.status_code})")
        content = response.content
        if not content:
            raise ZaiVideoError("Video download was empty")
        if len(content) > limit:
            raise ZaiVideoError(
                f"Video is too large ({len(content) // 1024 // 1024} MB)"
            )
        return content

    @staticmethod
    def _upload_sync(video_bytes: bytes, public_id: str) -> Dict:
        return cloudinary.uploader.upload(
            video_bytes,
            resource_type="video",
            folder="binaapp/hero-videos",
            public_id=public_id,
            overwrite=True,
        )

    @staticmethod
    def poster_url_for(video_secure_url: str) -> Optional[str]:
        """Cloudinary derives a still by swapping the video extension for
        ``.jpg`` — the first frame, no extra upload."""
        if not video_secure_url:
            return None
        base, dot, ext = video_secure_url.rpartition(".")
        if not dot or "/" in ext:
            return None
        return f"{base}.jpg"

    async def store(self, video_url: str, *, website_id: str) -> Dict[str, Optional[str]]:
        """Download the Z.ai clip and push it to Cloudinary.

        Returns ``{"video_url", "poster_url"}`` on Cloudinary. The upload is
        a blocking HTTP call, so it runs in a worker thread rather than on
        the event loop.
        """
        video_bytes = await self.download(video_url)
        public_id = f"{website_id}-{uuid.uuid4().hex[:8]}"
        try:
            result = await asyncio.to_thread(self._upload_sync, video_bytes, public_id)
        except Exception as exc:
            logger.error(f"☁️ Cloudinary video upload failed: {exc}")
            raise ZaiVideoError("Video storage failed") from exc

        secure_url = result.get("secure_url") if result else None
        if not secure_url:
            raise ZaiVideoError("Video storage returned no URL")
        logger.info(
            f"☁️ Hero video stored ({len(video_bytes) // 1024} KB): {secure_url[:60]}..."
        )
        # The page embeds the slimmed delivery URL, never the raw asset (see
        # HERO_VIDEO_DELIVERY_TRANSFORM). The poster is derived from the raw
        # asset: Cloudinary swaps the extension for a first-frame JPEG, and
        # a video transform in that path would be applied to an image.
        delivery_url = hero_video_delivery_url(secure_url)
        await self._warm_delivery(delivery_url)
        return {
            "video_url": delivery_url,
            "poster_url": self.poster_url_for(secure_url),
        }

    async def _warm_delivery(self, delivery_url: Optional[str]) -> None:
        """Ask Cloudinary for the transformed clip once, now, off the request
        path. The first request for a derived asset makes Cloudinary
        transcode it (~2–3 s for a 13 MB source); paying that here means the
        first visitor never does. Best-effort: any failure is logged and the
        raw asset still serves through the same URL."""
        if not delivery_url:
            return
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.get(delivery_url, headers={"User-Agent": _DOWNLOAD_USER_AGENT})
            size = len(getattr(response, "content", b"") or b"")
            logger.info(
                f"☁️ Hero video delivery warmed: HTTP {response.status_code}, "
                f"{size // 1024} KB served"
            )
        except Exception as exc:  # noqa: BLE001 — warming is best-effort
            logger.warning(f"☁️ Hero video delivery warm-up failed (non-fatal): {exc}")


zai_video_service = ZaiVideoService()
