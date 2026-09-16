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

Job registry
------------
Jobs live in a process-local dict for speed, and every state change is
mirrored to the ``hero_video_jobs`` table by the endpoint module (see
``services/hero_video_jobs``). The table is the source of truth across a
restart: Render redeploys on every push, and a job that only existed in
this dict was forgotten mid-render — provider done, clip never collected,
credit never refunded, nothing logged. Nothing here touches quota counters
or subscription rows.
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
    Model Studio's async video-synthesis endpoint — happyhorse-1.1-t2v for a
    prompt-only clip, the unified wan3.0-video when there is a photo to
    animate; ``zai`` is the original CogVideoX path. Everything after the
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


#: DashScope task states. Anything else is logged as unexpected and treated
#: as still running until the hard timeout.
DASHSCOPE_RUNNING_STATES = ("PENDING", "RUNNING", "SUSPENDED")
DASHSCOPE_FAILED_STATES = ("FAILED", "CANCELED", "CANCELLED", "UNKNOWN")


def _poll_result(
    status: str,
    *,
    video_url: Optional[str] = None,
    cover_image_url: Optional[str] = None,
    raw_status: Optional[str] = None,
    code: str = "",
    message: str = "",
) -> Dict:
    """The provider-agnostic poll outcome. ``status`` is one of
    ``processing`` / ``success`` / ``fail``; ``raw_status`` is whatever the
    provider actually said, for the job record and the logs."""
    return {
        "status": status,
        "video_url": video_url,
        "cover_image_url": cover_image_url,
        "raw_status": raw_status,
        "code": code,
        "message": message,
    }


#: Alibaba's unified video model: text-, image- AND video-to-video on the one
#: video-synthesis endpoint. This is the model that animates the merchant's
#: own hero photo — HappyHorse-T2V could not, and silently dropped it.
DEFAULT_DASHSCOPE_VIDEO_MODEL = "wan3.0-video"

#: Text-to-video only, on the same endpoint. A prompt-only job has no photo
#: for the unified model to animate, so it runs on the cheaper text-to-video
#: model instead; a job WITH a photo still goes to wan3.0.
DEFAULT_DASHSCOPE_T2V_MODEL = "happyhorse-1.1-t2v"

#: Values that switch the split off and put every DashScope job back on one
#: model (whatever DASHSCOPE_VIDEO_MODEL says).
_T2V_MODEL_DISABLED = ("none", "off", "same", "-")


def dashscope_video_model() -> str:
    """The DashScope model for a job that has a photo to animate
    (image-to-video). ``wan3.0-video`` by default."""
    return (
        os.getenv("DASHSCOPE_VIDEO_MODEL", DEFAULT_DASHSCOPE_VIDEO_MODEL).strip()
        or DEFAULT_DASHSCOPE_VIDEO_MODEL
    )


def dashscope_t2v_model() -> str:
    """The DashScope model for a prompt-only job. ``happyhorse-1.1-t2v`` by
    default: text-to-video is all such a job needs and it costs less per
    clip than the unified model. Set ``DASHSCOPE_T2V_MODEL=none`` to run
    every job on ``DASHSCOPE_VIDEO_MODEL`` again."""
    raw = os.getenv("DASHSCOPE_T2V_MODEL")
    if raw is None:
        return DEFAULT_DASHSCOPE_T2V_MODEL
    value = raw.strip()
    if not value or value.lower() in _T2V_MODEL_DISABLED:
        return dashscope_video_model()
    return value


def dashscope_model_for(image_url: Optional[str] = None) -> str:
    """Which DashScope model makes this clip: the unified model when there is
    a photo to animate, the text-to-video model when there is not."""
    return dashscope_video_model() if image_url else dashscope_t2v_model()


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
    """480P / 720P / 1080P. 1080P by default.

    This was 720P, on the reasoning that a hero clip sits behind a scrim and
    1080P doubles what every visitor downloads. The second half of that is
    handled at delivery now (``c_limit`` caps the width and never upscales,
    and q_auto picks the bitrate), and the first half was simply wrong for a
    full-bleed hero on a retina phone: no delivery setting makes a 720p
    master sharp. Ask for the pixels once, at generation; spend them or not
    at delivery. DASHSCOPE_VIDEO_RESOLUTION=720P puts it back."""
    value = os.getenv("DASHSCOPE_VIDEO_RESOLUTION", "1080P").strip().upper()
    return value if value in DASHSCOPE_RESOLUTIONS else "1080P"


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


def hero_video_model(image: bool = False) -> str:
    """The model name shown in the picker, for whichever provider is active.
    On DashScope a prompt-only job and a photo job run on different models,
    so ``image=True`` asks for the one that animates a photo."""
    if hero_video_provider() != PROVIDER_DASHSCOPE:
        return zai_video_model()
    return dashscope_video_model() if image else dashscope_t2v_model()


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
    can. DashScope can with the unified wan3.x model (the default for a job
    that carries a photo); an operator who pins a ``-t2v`` model as
    DASHSCOPE_VIDEO_MODEL is text-to-video only and drops the photo on the
    floor. DASHSCOPE_T2V_MODEL never decides this — it is only consulted for
    a job that has no photo in the first place."""
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


def zai_video_poll_timeout_seconds() -> float:
    """Per-poll HTTP cap. Shorter than the submit/download cap: a poll is
    a small GET, and the driver holds the job lock while it waits."""
    try:
        return float(os.getenv("ZAI_VIDEO_POLL_TIMEOUT_SECONDS", "20"))
    except ValueError:
        return 20.0


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

#: Ambience presets the dashboard offers. Each is split in two, and the split
#: is the point: ``tone`` is palette, light and atmosphere; ``motion`` is what
#: MOVES and how fast.
#:
#: A merchant typed "Kerusi barber berpusing sangat perlahan" — a chair
#: turning very slowly — picked Bertenaga, and the prompt that reached the
#: model ended "...dynamic but smooth camera motion, ... upbeat energy." Two
#: contradictory motion instructions in one prompt, and the clip followed
#: neither: the chair did not turn at all. The merchant's own words are the
#: motion; the mood they picked is how it should LOOK, not how fast it moves.
#: So the mood contributes ``motion`` only when the merchant supplied none.
VIDEO_STYLE_PRESETS: Dict[str, Dict[str, str]] = {
    "cinematic": {
        "label_ms": "Sinematik",
        "label_en": "Cinematic",
        "tone": (
            "warm golden-hour light, shallow depth of field, soft bokeh, "
            "cinematic colour grade"
        ),
        "motion": "slow cinematic camera drift, gentle continuous motion",
    },
    "ambient": {
        "label_ms": "Tenang",
        "label_en": "Ambient",
        "tone": (
            "calm ambient atmosphere, soft diffused daylight, muted natural "
            "palette, serene mood"
        ),
        "motion": "very slow push-in, subtle steam and light movement",
    },
    "energetic": {
        "label_ms": "Bertenaga",
        "label_en": "Energetic",
        "tone": (
            "vibrant lively scene, rich saturated colours, bright punchy "
            "lighting"
        ),
        "motion": "dynamic but smooth camera motion, upbeat energy",
    },
    "elegant": {
        "label_ms": "Elegan",
        "label_en": "Elegant",
        "tone": (
            "luxurious minimal composition, dark moody lighting with soft "
            "highlights, premium feel"
        ),
        "motion": "slow elegant camera glide",
    },
    "nature": {
        "label_ms": "Alam semula jadi",
        "label_en": "Nature",
        "tone": (
            "lush natural setting, soft sunlight through foliage, tranquil "
            "green palette"
        ),
        "motion": "gentle breeze moving leaves, slow natural movement",
    },
}


def preset_scene(preset: Dict[str, str], *, with_motion: bool = True) -> str:
    """The preset's contribution to a prompt: its look, plus its motion only
    when the merchant did not describe motion themselves."""
    tone = preset.get("tone", "")
    motion = preset.get("motion", "")
    if with_motion and motion:
        return f"{tone}, {motion}" if tone else motion
    return tone


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

    THE MERCHANT OWNS THE MOTION. Whenever ``custom_prompt`` is present it
    describes what moves, so the style preset contributes its LOOK only — no
    motion adjectives, at any speed. "Kerusi barber berpusing sangat
    perlahan" plus Bertenaga's "dynamic ... upbeat energy" is one prompt
    giving the model two speeds, and what came back moved at neither.
    """
    preset = VIDEO_STYLE_PRESETS.get(style) or VIDEO_STYLE_PRESETS[DEFAULT_VIDEO_STYLE]

    custom = _squash(custom_prompt)
    hero_scene = _squash(hero_image_prompt)
    # The merchant described the motion → the preset keeps its tone and drops
    # its motion words, so the two cannot contradict each other.
    ambience = preset_scene(preset, with_motion=not custom)
    if hero_scene:
        scene = hero_scene
        motion = f"{_terminate(custom)} {ambience}" if custom else ambience
        scene = f"{_terminate(scene)} {motion}"
        logger.info(
            f"🎬 Video scene seeded from the merchant's hero image prompt "
            f"({'merchant motion + preset tone' if custom else 'preset ' + style})"
        )
    elif custom:
        # The merchant's own words lead the prompt, then the ambience they
        # picked in the UI. This branch used to be `scene = custom`, which
        # silently threw the style away: pick "Sinematik", type a prompt, and
        # the preset never reached the model — the style buttons were dead
        # controls for anyone who also wrote a prompt. Custom text stays first
        # so it remains the dominant subject.
        scene = f"{_terminate(custom)} {ambience}"
        logger.info(
            f"🎬 Video scene from the merchant's prompt + preset {style} (tone only)"
        )
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
        scene += f". {ambience}."

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

#: Forget FINISHED jobs after this long. A job that is still processing,
#: storing or ready is never dropped by age here: the hard timeout ends
#: the first two and the publish claim window ends the third, and each of
#: those paths refunds and logs. Dropping them silently by TTL was how a
#: ``ready`` clip could vanish from under a merchant still reviewing.
_JOB_TTL_SECONDS = 2 * 60 * 60
#: Absolute backstop for anything the above missed (a job whose driver
#: died and whose ledger row the sweep already closed).
_JOB_HARD_TTL_SECONDS = 48 * 60 * 60


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
    #: Raw provider state from the last poll (DashScope: PENDING / RUNNING /
    #: SUCCEEDED / FAILED / CANCELED / UNKNOWN; ``http_<code>`` when the
    #: poll request itself failed) and the provider's message, if any.
    #: Persisted so a stuck job can be explained from the ledger alone.
    provider_status: Optional[str] = None
    provider_message: Optional[str] = None
    #: Consecutive polls that raised (HTTP error, timeout). Reset on any
    #: poll that returns a state. Bounded by the hard job timeout.
    poll_errors: int = 0
    #: Wall-clock start / last poll, for the ledger row (``created_at`` above
    #: is monotonic and meaningless across processes).
    created_wall: float = field(default_factory=time.time)
    last_polled_wall: Optional[float] = None
    #: Monotonic time the job entered 'storing'. The sweep ages a storing
    #: job from here, not from creation: a clip that SUCCEEDED late in its
    #: window still gets its full download/upload allowance.
    storing_since: Optional[float] = None
    #: Set when a ledger save reports another process now owns the row.
    ownership_lost: bool = False
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
            "provider_status": self.provider_status,
            "charged": self.charged,
            "refunded": self.refunded,
        }


class ZaiVideoError(Exception):
    """A provider call failed in a way the caller should surface, not retry.

    ``status_code`` is the HTTP status when the failure was an HTTP
    response (a 403 poll, say), so the job can record ``http_403`` as its
    provider state instead of a bare "poll error"."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ZaiVideoService:
    def __init__(self) -> None:
        self._jobs: Dict[str, HeroVideoJob] = {}

    # ---- registry ---------------------------------------------------------

    def _sweep(self) -> None:
        stale = [
            job_id
            for job_id, job in self._jobs.items()
            if (
                job.status in (JOB_STATUS_COMPLETED, JOB_STATUS_FAILED)
                and job.age_seconds() > _JOB_TTL_SECONDS
            )
            or job.age_seconds() > _JOB_HARD_TTL_SECONDS
        ]
        for job_id in stale:
            self._jobs.pop(job_id, None)

    def adopt_job(self, job: HeroVideoJob) -> HeroVideoJob:
        """Put a job rebuilt from the ledger (restart recovery) into the
        registry. An existing entry with the same id wins — it is live."""
        return self._jobs.setdefault(job.job_id, job)

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
            f"🎬 ZAI VIDEO REQUEST model={payload['model']} size={payload['size']} "
            f"duration={payload['duration']}s fps={payload['fps']} "
            f"quality={payload['quality']} image={image_url or '-'} "
            f"prompt={payload['prompt']!r}"
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
            async with httpx.AsyncClient(timeout=zai_video_poll_timeout_seconds()) as client:
                response = await client.get(
                    f"{_zai_base_url()}/async-result/{task_id}",
                    headers=self._headers(),
                )
        except httpx.TimeoutException as exc:
            raise ZaiVideoError("Z.ai video poll timed out") from exc
        except httpx.HTTPError as exc:
            raise ZaiVideoError(f"Z.ai video poll failed: {exc}") from exc

        if response.status_code == 429:
            # Rate-limited poll: report "still processing" so the caller
            # simply asks again after its normal interval.
            logger.warning(f"🎬 Z.ai video poll for {task_id} rate-limited (429)")
            return _poll_result("processing", raw_status="HTTP_429")
        if response.status_code != 200:
            logger.error(
                f"🎬 Z.ai video poll failed: {response.status_code} - {response.text[:1000]}"
            )
            raise ZaiVideoError(
                f"Z.ai video poll failed ({response.status_code})",
                status_code=response.status_code,
            )

        data = response.json() or {}
        state = str(data.get("task_status", "")).upper()
        logger.info(f"🎬 Z.ai task {task_id} task_status={state or '(missing)'}")
        if state == "SUCCESS":
            results = data.get("video_result") or []
            first = (results[0] or {}) if results else {}
            video_url = first.get("url")
            if not video_url:
                logger.error(f"🎬 Z.ai task {task_id} SUCCESS without a video URL — full body: {response.text}")
                raise ZaiVideoError("Z.ai reported success but returned no video URL")
            return _poll_result(
                "success", video_url=video_url,
                cover_image_url=first.get("cover_image_url"), raw_status=state,
            )
        if state == "FAIL":
            logger.error(f"🎬 Z.ai task {task_id} FAIL — full body: {response.text}")
            return _poll_result("fail", raw_status=state, message=str(data.get("error") or ""))
        if state != "PROCESSING":
            # Not a documented state. Say so with the whole body rather
            # than quietly treating it as "still running".
            logger.error(f"🎬 Z.ai task {task_id} UNEXPECTED task_status={state!r} — full body: {response.text}")
        return _poll_result("processing", raw_status=state or "(missing)")

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

        An image job goes to a provider that can animate the image. On
        DashScope that is the unified wan3.0-video model, which the default
        config already picks for a job carrying a photo. Only when the
        primary CANNOT animate one — an operator pinning a text-to-video-only
        DASHSCOPE_VIDEO_MODEL — would ``image_url`` be silently dropped,
        which is how a merchant who uploaded their storefront got a clip of
        strangers in a different restaurant. In that case, and only then, a
        configured Z.ai is tried FIRST and the usual primary becomes the
        fallback, so an image job is never worse than a text job.
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
        # A prompt-only job runs on the text-to-video model, a job that
        # carries the merchant's photo on the unified one that can animate it.
        model = dashscope_model_for(image_url)
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
        # Everything that decides what comes back, in one greppable line, and
        # the prompt IN FULL — exactly as the provider receives it, after any
        # truncation. "Why is the clip like that?" was a database query
        # before this; now it is one log line per submit.
        logger.info(
            f"🎬 DASHSCOPE VIDEO REQUEST model={payload['model']} "
            f"mode={'image-to-video' if image_url else 'text-to-video'} "
            f"resolution={parameters['resolution']} ratio={parameters['ratio']} "
            f"duration={parameters['duration']}s audio={parameters.get('audio')} "
            f"watermark={parameters.get('watermark', False)} "
            f"image={image_url or '-'} prompt={input_block['prompt']!r}"
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
            async with httpx.AsyncClient(timeout=zai_video_poll_timeout_seconds()) as client:
                response = await client.get(
                    f"{_dashscope_base_url()}/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {_dashscope_api_key()}"},
                )
        except httpx.TimeoutException as exc:
            raise ZaiVideoError("DashScope video poll timed out") from exc
        except httpx.HTTPError as exc:
            raise ZaiVideoError(f"DashScope video poll failed: {exc}") from exc

        if response.status_code == 429:
            logger.warning(f"🎬 DashScope task {task_id} poll rate-limited (429)")
            return _poll_result("processing", raw_status="HTTP_429")
        if response.status_code != 200:
            # Body included in full: a 403 with an empty body (seen in
            # production on 2026-09-11 04:28:18, transient) and a 401
            # InvalidApiKey look identical from the status alone.
            logger.error(
                f"🎬 DashScope task {task_id} poll failed: HTTP {response.status_code} "
                f"— body: {response.text[:1000] or '(empty)'}"
            )
            raise ZaiVideoError(
                f"DashScope video poll failed ({response.status_code})",
                status_code=response.status_code,
            )

        try:
            data = response.json() or {}
        except ValueError:
            logger.error(f"🎬 DashScope task {task_id} poll returned non-JSON: {response.text[:1000]}")
            raise ZaiVideoError("DashScope video poll returned non-JSON", status_code=200)
        output = data.get("output") or {}
        state = str(output.get("task_status", "")).upper()
        # Every poll, the raw state — this is the line that answers "is
        # the provider still rendering or did we stop listening?".
        logger.info(
            f"🎬 DashScope task {task_id} task_status={state or '(missing)'} "
            f"request_id={data.get('request_id')} submit={output.get('submit_time')} "
            f"scheduled={output.get('scheduled_time')} end={output.get('end_time')}"
        )
        if state == "SUCCEEDED":
            video_url = output.get("video_url")
            if not video_url:
                logger.error(f"🎬 DashScope task {task_id} SUCCEEDED without video_url — full body: {response.text}")
                raise ZaiVideoError("DashScope reported success but returned no video URL")
            return _poll_result("success", video_url=video_url, raw_status=state)
        if state in DASHSCOPE_FAILED_STATES:
            logger.error(f"🎬 DashScope task {task_id} {state} — full body: {response.text}")
            return _poll_result(
                "fail", raw_status=state,
                code=str(output.get("code") or ""), message=str(output.get("message") or ""),
            )
        if state not in DASHSCOPE_RUNNING_STATES:
            # Undocumented state: not success, not one of the failure
            # states. Log everything and keep polling — the hard timeout
            # bounds how long this can go on.
            logger.error(f"🎬 DashScope task {task_id} UNEXPECTED task_status={state!r} — full body: {response.text}")
        return _poll_result("processing", raw_status=state or "(missing)")

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
