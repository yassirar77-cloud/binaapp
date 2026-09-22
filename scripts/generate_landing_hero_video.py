#!/usr/bin/env python3
"""Build the clip that plays behind the landing hero.

ONE continuous shot: a merchant in a tudung in a warm, dim kedai makan,
phone in hand, slow push-in. Nothing else.

It used to be three shots, two of them screen captures of real BinaApp pages.
That was wrong and the result was unusable: the hero headline sits on top of
this clip, and text behind text makes both unreadable. So both prompts here
forbid anything legible — no signage, no menu boards, no writing, no labels —
and the encode grades the frame down hardest where the copy sits.

Text-to-video: there is no photograph to start from, so nothing needs a first
frame. An earlier version generated one with a text-to-image model and handed
it straight back to the video model — a step that bought nothing and failed on
an account without that image model. The product itself routes prompt-only
jobs the same way, to text-to-video on the same endpoint.

Provider, endpoint and key are the ones the product already uses for merchant
hero videos — DashScope (Alibaba Model Studio), read exactly as
``backend/app/services/zai_video_service.py`` reads them. The key comes from
the environment or a ``.env`` git already ignores; nothing is hardcoded.

Models are tried in order until one accepts: wan3.0-video, then
happyhorse-1.1-t2v. A model the account does not have is rejected at submit
and a rejected submit is not billed, so the list costs nothing to walk;
whichever accepts is charged exactly once. DASHSCOPE_VIDEO_MODEL pins a single
name instead.

A first frame is still used if one is actually supplied — drop a PNG in
``scripts/hero_frames/01-merchant.png``, or pass --frame-urls. Then it is
hosted first (DashScope's own upload endpoint, then Cloudinary, then a generic
host, each retried through transient 5xx, all before anything billable) and
the job runs as image-to-video on wan3.0.

The encode does three things the raw clip does not:

  * scales it so its long edge is at most 1280 and strips the audio,
  * grades it down — less brightness, a touch more contrast — and lays a
    black gradient over the upper left, where the headline and CTA sit, so
    white copy keeps its contrast over any frame. The gradient is spent
    before the middle of the frame, because a phone crops a 16:9 hero to its
    middle band and the merchant has to stay lit there,
  * fades the first and last half second, so the loop point reads as
    deliberate rather than as a jump cut. These models do not produce a
    genuinely seamless loop and no prompt makes them.

Usage
-----
    # the plan and the prompts — calls nothing
    python3 scripts/generate_landing_hero_video.py --dry-run

    # the real run
    python3 scripts/generate_landing_hero_video.py

    # re-grade what is already downloaded, without paying again
    python3 scripts/generate_landing_hero_video.py --regrade

Requires ``ffmpeg``/``ffprobe`` and ``httpx``. No browser, no dev server.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import httpx
except ImportError:  # pragma: no cover
    sys.exit("httpx is not installed. Run: pip install httpx")


REPO_ROOT = Path(__file__).resolve().parent.parent
SHOTS_FILE = REPO_ROOT / "scripts" / "hero_shots.json"
FRAMES_DIR = REPO_ROOT / "scripts" / "hero_frames"
RAW_DIR = REPO_ROOT / "scripts" / "hero_raw"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "hero"
OUT_VIDEO = OUT_DIR / "binaapp-hero.mp4"
OUT_POSTER = OUT_DIR / "binaapp-hero.jpg"


# ---------------------------------------------------------------------------
# Provider settings — mirrored from backend/app/services/zai_video_service.py
# ---------------------------------------------------------------------------

#: Models to try, in order, until one is accepted. A model an account does not
#: have is rejected at submit with 400 InvalidParameter "Model not exist." —
#: and a rejected submit is not billed, so walking the list costs nothing.
#:
#: wan3.0-video first: it is the unified model, it looks better, and it is the
#: one that can animate a supplied first frame. happyhorse-1.1-t2v second: it
#: is text-to-video only, it costs less, and it is the model that generated
#: all sixteen showcase clips on this account, so it is known to work.
#: DASHSCOPE_VIDEO_MODEL overrides the list with a single name.
VIDEO_MODEL_CHAIN = ("wan3.0-video", "happyhorse-1.1-t2v")

DEFAULT_API_URL = "https://dashscope-intl.aliyuncs.com/api/v1"

RUNNING_STATES = ("PENDING", "RUNNING", "SUSPENDED")
FAILED_STATES = ("FAILED", "CANCELED", "CANCELLED", "UNKNOWN")

#: Landscape. The hero is a full-bleed band on every screen, so a 16:9 frame
#: fills it without cropping on desktop. A phone shows roughly the middle
#: third of it, which is why the shot is framed with the subject near centre
#: rather than at an edge.
RESOLUTION = "1080P"
RATIO = "16:9"
DURATION_SECONDS = 10

SUBMIT_TIMEOUT = 90
POLL_TIMEOUT = 60
POLL_INTERVAL = 10
MAX_WAIT_SECONDS = 1200
DOWNLOAD_TIMEOUT = 600

#: The clip sits behind a scrim, graded down, at full bleed. Capping the long
#: edge at 1280 is plenty on a retina phone and keeps the loop to a couple of
#: megabytes.
ENCODE_LONG_EDGE = 1280
ENCODE_CRF = 30
SIZE_BUDGET_BYTES = 2_500_000

#: The grade. `eq` pulls the whole frame down; the gradient is a black overlay
#: strongest at the top-left, where the headline and the CTA sit, falling away
#: toward the right and the bottom, where the subject is.
#:
#: The left reach is short on purpose. A phone crops this 16:9 frame to the
#: source's middle band — x 37% to 63% — so a gradient still going at 40%
#: would darken the merchant herself on the screen most merchants use. It is
#: spent by 48%, which covers the desktop headline and stops short of her.
GRADE_EQ = "eq=brightness=-0.10:contrast=1.06:saturation=0.92"
GRADE_LEFT_STRENGTH = 0.80     # how black the left edge goes
GRADE_LEFT_REACH = 0.48        # ... fading out by this fraction of the width
GRADE_TOP_STRENGTH = 0.50      # how black the top edge goes
GRADE_TOP_REACH = 0.50         # ... fading out by this fraction of the height

#: wan3.0 does not loop seamlessly and no prompt makes it. Fading the ends
#: into the dark grade makes the loop point read as deliberate.
LOOP_FADE_SECONDS = 0.5


def load_dotenv(path: Path) -> None:
    """Read ``KEY=value`` lines into the environment, without overwriting what
    is already set, so a key exported in the shell wins over the file."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = re.split(r"\s+#", value.strip().strip('"').strip("'"), maxsplit=1)[0].strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


def api_key() -> str:
    for name in ("DASHSCOPE_API_KEY", "QWEN_API_KEY"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    sys.exit(
        "No DashScope key found.\n"
        "Set DASHSCOPE_API_KEY in your .env (the same key the backend uses for\n"
        "merchant hero videos), or export it in this shell. See ENV_TEMPLATE.txt."
    )


def api_url() -> str:
    return (os.getenv("DASHSCOPE_API_URL") or DEFAULT_API_URL).rstrip("/")


def video_models() -> Tuple[str, ...]:
    """The models to try, in order. A single name in DASHSCOPE_VIDEO_MODEL
    replaces the list entirely — an operator who pins one wants that one."""
    pinned = (os.getenv("DASHSCOPE_VIDEO_MODEL") or "").strip()
    return (pinned,) if pinned else VIDEO_MODEL_CHAIN


def video_model() -> str:
    """The first model that will be tried. Only for display and for the
    DashScope upload policy, which wants a model name up front."""
    return video_models()[0]


def is_unified(model: str) -> bool:
    """wan3.x takes the unified request shape: `input.media` for a supplied
    first frame, and an `audio` parameter. The older `-t2v` models have
    neither, and sending `audio` to one risks a rejected request — so the
    shape follows the model, exactly as the backend does it."""
    return (model or "").strip().lower().startswith("wan3")


def auth_headers(asynchronous: bool = True) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }
    if asynchronous:
        headers["X-DashScope-Async"] = "enable"
    return headers


# ---------------------------------------------------------------------------
# DashScope
# ---------------------------------------------------------------------------


def poll_task(client: httpx.Client, task_id: str, want: str) -> Tuple[str, Dict]:
    """Poll ``GET /tasks/{id}`` until it settles. Returns (url, full body).

    ``want`` is "video" or "image" — the two endpoints report their result
    under different keys.
    """
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    last_state = ""

    while time.monotonic() < deadline:
        response = client.get(
            f"{api_url()}/tasks/{task_id}",
            headers={"Authorization": f"Bearer {api_key()}"},
            timeout=POLL_TIMEOUT,
        )
        if response.status_code == 429:
            time.sleep(POLL_INTERVAL)
            continue
        if response.status_code != 200:
            raise RuntimeError(f"poll failed ({response.status_code}): {response.text[:300]}")

        body = response.json() or {}
        output = body.get("output") or {}
        state = str(output.get("task_status", "")).upper()

        if state != last_state:
            print(f"      {state or '(no state)'}", flush=True)
            last_state = state

        if state == "SUCCEEDED":
            if want == "video":
                url = output.get("video_url")
            else:
                results = output.get("results") or []
                url = (results[0] or {}).get("url") if results else None
            if not url:
                raise RuntimeError(f"SUCCEEDED but no {want} url: {str(body)[:400]}")
            return url, body
        if state in FAILED_STATES:
            raise RuntimeError(
                f"{state}: {output.get('message') or output.get('code') or 'no reason given'}"
            )
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(f"still {last_state or 'running'} after {MAX_WAIT_SECONDS}s — gave up")


def describe_usage(body: Dict) -> str:
    """Whatever the response says this cost, and nothing when it says nothing —
    DashScope reports usage inconsistently, and a made-up number is worse than
    none. The authoritative figure is the Model Studio billing console."""
    usage = body.get("usage") or {}
    return " ".join(f"{k}={v}" for k, v in sorted(usage.items())) if usage else ""


# ---------------------------------------------------------------------------
# Getting the first frame somewhere wan3.0 can fetch it
# ---------------------------------------------------------------------------
#
# wan3.0 wants a URL for the first frame, not bytes, so a local PNG has to be
# hosted before the video job is submitted. The first version of this used a
# free anonymous paste host and run #1 died on its 503 — a single unowned
# dependency between a working capture and a billable call.
#
# Three ways to host it are tried in order, all of them before a single
# billable call is made, and each retried through transient 5xx:
#
#   1. DashScope's own upload endpoint. First-party, needs no credential
#      beyond the key already in hand, and the resulting oss:// reference is
#      what the provider's own SDK passes for a local file.
#   2. Cloudinary — BinaApp's own storage, the bucket the merchant sites and
#      the existing hero clips already live in (see zai_video_service.py).
#      Used automatically when its credentials are in the environment.
#   3. A generic file host, last and never by default.

FRAME_UPLOAD_ATTEMPTS = 4
FRAME_UPLOAD_BACKOFF_SECONDS = 2

#: Worth trying again: an overloaded gateway, a rate limit, a dropped
#: connection. A 4xx that is not one of these is a real rejection.
TRANSIENT_STATUSES = (408, 425, 429, 500, 502, 503, 504)


def request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    attempts: int = FRAME_UPLOAD_ATTEMPTS,
    **kwargs,
) -> httpx.Response:
    """One request, retried through transient failures with backoff.

    ``files=`` is not reusable across attempts — the handle is consumed by the
    first one — so callers hand over bytes and this rebuilds the form each
    time.
    """
    delay = FRAME_UPLOAD_BACKOFF_SECONDS
    last = ""

    for attempt in range(1, attempts + 1):
        try:
            response = client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            last = f"{type(exc).__name__}: {exc}"
        else:
            if response.status_code not in TRANSIENT_STATUSES:
                return response
            last = f"HTTP {response.status_code}"

        if attempt < attempts:
            print(f"      {last} — retrying in {delay}s ({attempt}/{attempts - 1})")
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(f"{last} after {attempts} attempts")


def upload_via_dashscope(client: httpx.Client, frame: Path) -> str:
    """Upload through DashScope's own endpoint. Returns an ``oss://`` ref.

    The endpoint hands back a short-lived OSS policy, the file is POSTed to the
    bucket it names, and the resulting reference is passed back to the video
    API with ``X-DashScope-OssResourceResolve: enable``.
    """
    policy = request_with_retry(
        client,
        "GET",
        f"{api_url()}/uploads",
        params={"action": "getPolicy", "model": video_model()},
        headers={"Authorization": f"Bearer {api_key()}"},
        timeout=SUBMIT_TIMEOUT,
    )
    if policy.status_code != 200:
        raise RuntimeError(f"policy request returned {policy.status_code}: {policy.text[:200]}")

    data = (policy.json() or {}).get("data") or {}
    missing = [k for k in ("upload_host", "upload_dir", "oss_access_key_id",
                           "policy", "signature") if not data.get(k)]
    if missing:
        raise RuntimeError(f"policy response is missing {', '.join(missing)}")

    key = f"{data['upload_dir']}/{frame.name}"
    form = {
        "OSSAccessKeyId": data["oss_access_key_id"],
        "policy": data["policy"],
        "Signature": data["signature"],
        "key": key,
        "success_action_status": "200",
    }
    for optional, field in (("x_oss_object_acl", "x-oss-object-acl"),
                            ("x_oss_forbid_overwrite", "x-oss-forbid-overwrite")):
        if data.get(optional):
            form[field] = data[optional]

    payload = frame.read_bytes()
    upload = request_with_retry(
        client,
        "POST",
        data["upload_host"],
        data=form,
        files={"file": (frame.name, payload, "image/png")},
        timeout=DOWNLOAD_TIMEOUT,
    )
    if upload.status_code not in (200, 201, 204):
        raise RuntimeError(f"bucket returned {upload.status_code}: {upload.text[:200]}")

    return f"oss://{key}"


def cloudinary_credentials() -> Tuple[str, str, str]:
    """(cloud name, key, secret) from either the split vars or CLOUDINARY_URL."""
    cloud = (os.getenv("CLOUDINARY_CLOUD_NAME") or "").strip()
    key = (os.getenv("CLOUDINARY_API_KEY") or "").strip()
    secret = (os.getenv("CLOUDINARY_API_SECRET") or "").strip()
    if cloud and key and secret:
        return cloud, key, secret

    # cloudinary://<key>:<secret>@<cloud>
    match = re.match(r"cloudinary://([^:]+):([^@]+)@(.+)", (os.getenv("CLOUDINARY_URL") or "").strip())
    if match:
        return match.group(3), match.group(1), match.group(2)
    return "", "", ""


def upload_via_cloudinary(client: httpx.Client, frame: Path) -> str:
    """Upload to BinaApp's own Cloudinary, the way the backend does."""
    cloud, key, secret = cloudinary_credentials()
    if not (cloud and key and secret):
        raise RuntimeError("no Cloudinary credentials in the environment")

    folder = os.getenv("HERO_FRAME_CLOUDINARY_FOLDER", "binaapp/hero-frames")
    timestamp = str(int(time.time()))

    # Cloudinary signs the upload params: every signed field except file,
    # api_key and the signature itself, sorted by name, joined as a query
    # string, with the secret appended, then SHA-1.
    signed = {"folder": folder, "timestamp": timestamp}
    to_sign = "&".join(f"{k}={signed[k]}" for k in sorted(signed)) + secret
    signature = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

    payload = frame.read_bytes()
    response = request_with_retry(
        client,
        "POST",
        f"https://api.cloudinary.com/v1_1/{cloud}/image/upload",
        data={**signed, "api_key": key, "signature": signature},
        files={"file": (frame.name, payload, "image/png")},
        timeout=DOWNLOAD_TIMEOUT,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Cloudinary returned {response.status_code}: {response.text[:200]}")

    url = (response.json() or {}).get("secure_url")
    if not url:
        raise RuntimeError(f"Cloudinary returned no secure_url: {response.text[:200]}")
    return url


def upload_via_generic_host(client: httpx.Client, frame: Path) -> str:
    """Last resort: a plain file host. Never reached unless the two above fail.

    The frames are screenshots of public marketing pages and a generated stock
    image, so there is nothing private in them — but an unowned host is still
    an unowned host, which is why it is last.
    """
    endpoint = os.getenv("HERO_FRAME_UPLOAD_URL", "https://0x0.st")
    payload = frame.read_bytes()
    response = request_with_retry(
        client,
        "POST",
        endpoint,
        files={"file": (frame.name, payload, "image/png")},
        timeout=DOWNLOAD_TIMEOUT,
        headers={"User-Agent": "binaapp-hero-builder/1.0"},
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"{endpoint} returned {response.status_code}")

    url = response.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"{endpoint} returned something odd: {url[:200]}")
    return url


def upload_frame(client: httpx.Client, frame: Path) -> str:
    """Host the first frame and return the reference to pass to wan3.0.

    Every route is attempted before the job is submitted, so a hosting problem
    still costs nothing — which is how run #1 failed, and should stay that way.
    """
    routes = [
        ("DashScope", upload_via_dashscope),
        ("Cloudinary", upload_via_cloudinary),
        ("file host", upload_via_generic_host),
    ]

    reasons: List[str] = []
    for name, route in routes:
        try:
            url = route(client, frame)
        except Exception as exc:
            print(f"      {name} upload failed: {exc}")
            reasons.append(f"{name}: {exc}")
            continue
        print(f"      hosted via {name}")
        return url

    raise RuntimeError(
        "could not host the first frame anywhere.\n        "
        + "\n        ".join(reasons)
        + "\n      Host the PNG yourself and pass --frame-urls "
          '\'{"02-create": "https://..."}\' to skip this step.'
    )


#: A model the account does not have comes back like this. Anything else that
#: is rejected at submit is worth showing rather than silently walking past.
MODEL_MISSING_MARKERS = ("model not exist", "model does not exist", "invalidparameter")


def submit_on(client: httpx.Client, model: str, prompt: str, seconds: int,
              frame_url: str = "") -> str:
    """Submit one video job on one model. Returns the task id.

    Text-to-video when there is no first frame, which is the normal case now:
    nothing here starts from a photograph, so asking an image model for one
    just to hand it straight back was a step that could only add failures.
    A first frame is still used when one has been supplied.
    """
    unified = is_unified(model)
    input_block: Dict = {"prompt": prompt}
    parameters: Dict = {
        "resolution": RESOLUTION,
        "ratio": RATIO,
        "duration": seconds,
    }

    if frame_url:
        if not unified:
            raise RuntimeError(
                f"{model} is text-to-video only and cannot animate a first frame"
            )
        input_block["media"] = [{"type": "first_frame", "url": frame_url}]

    if unified:
        # wan3.x generates a soundtrack unless told not to. The hero is always
        # muted, so it would only cost money and bytes.
        parameters["audio"] = False
    else:
        # The older models have no `audio`; they do stamp a provider mark
        # unless told not to.
        parameters["watermark"] = False

    headers = auth_headers()
    if frame_url.startswith("oss://"):
        # A reference into DashScope's own bucket is only resolved when the
        # request says so; without this header the API sees an unusable URL.
        headers["X-DashScope-OssResourceResolve"] = "enable"

    response = client.post(
        f"{api_url()}/services/aigc/video-generation/video-synthesis",
        headers=headers,
        json={"model": model, "input": input_block, "parameters": parameters},
        timeout=SUBMIT_TIMEOUT,
    )
    if response.status_code == 429:
        raise RuntimeError("rate limited (429) — wait a minute and rerun")
    if response.status_code in (401, 403):
        raise RuntimeError(
            f"DashScope rejected the key ({response.status_code}). Check it is a key for "
            f"this region — an international key only works on dashscope-intl."
        )
    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code}: {response.text[:300]}")

    output = ((response.json() or {}).get("output") or {})
    task_id = output.get("task_id")
    if not task_id:
        raise RuntimeError(f"accepted but returned no task id: {response.text[:300]}")
    if str(output.get("task_status", "")).upper() in FAILED_STATES:
        raise RuntimeError(f"rejected at submit ({output.get('message')})")
    return str(task_id)


def submit_video(client: httpx.Client, prompt: str, seconds: int,
                 frame_url: str = "") -> Tuple[str, str]:
    """Try each model until one accepts the job. Returns (task id, model).

    A model the account does not have is rejected at submit, and a rejected
    submit is not billed — so walking the list costs nothing, and the run
    survives an account that has one of these models but not the other.
    Whichever model accepts is the one that is charged, exactly once.
    """
    models = video_models()
    reasons: List[str] = []

    for model in models:
        if frame_url and not is_unified(model):
            print(f"      {model}: skipped (cannot animate a supplied first frame)")
            reasons.append(f"{model}: text-to-video only, but a first frame was given")
            continue
        try:
            task_id = submit_on(client, model, prompt, seconds, frame_url)
        except RuntimeError as exc:
            message = str(exc).lower()
            if any(marker in message for marker in MODEL_MISSING_MARKERS):
                print(f"      {model}: not available on this account")
            else:
                print(f"      {model}: {exc}")
            reasons.append(f"{model}: {exc}")
            continue
        print(f"      accepted by {model}")
        return task_id, model

    raise RuntimeError(
        "no model accepted the job.\n        "
        + "\n        ".join(reasons)
        + "\n      Set DASHSCOPE_VIDEO_MODEL (or the workflow's `model` input) to a "
          "video model your\n      Model Studio account actually has."
    )


def download(client: httpx.Client, url: str, destination: Path) -> None:
    """Stream to a temp file and move it into place, so an interrupted download
    never leaves a half file behind for a later run to trust."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=65536):
                handle.write(chunk)
    partial.replace(destination)


# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"{name} is not on PATH. Install ffmpeg (which ships both ffmpeg and ffprobe).")


def run_quiet(command: List[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{command[0]} failed:\n{result.stderr[-2000:]}")


def duration_of(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path.name}:\n{result.stderr[-500:]}")
    return float(result.stdout.strip())


def gradient_alpha_expression() -> str:
    """The black overlay's alpha, as an ffmpeg geq expression.

    Strongest at the top-left corner and falling to nothing by
    GRADE_*_REACH across the frame. The two edges are combined with `max`
    rather than added, so the corner where they meet does not go to solid
    black.
    """
    left = f"{GRADE_LEFT_STRENGTH}*(1-X/(W*{GRADE_LEFT_REACH}))"
    top = f"{GRADE_TOP_STRENGTH}*(1-Y/(H*{GRADE_TOP_REACH}))"
    return f"255*clip(max({left}, {top}),0,1)"


def grade_and_encode(clip: Path, out: Path, crf: int = ENCODE_CRF) -> None:
    """Scale, grade, fade the ends and write the clip the hero will play.

    The gradient is a second input — a black source the same size as the
    scaled video — given a per-pixel alpha by `geq` and laid over the graded
    frame. Doing it as an overlay rather than inside the video's own filter
    chain keeps `geq` off the video, which is both faster and avoids the
    frame-rate loss this ffmpeg build shows when filters stack up.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    width, height = scaled_size(clip)
    length = duration_of(clip)
    fade_out_at = max(0.0, length - LOOP_FADE_SECONDS)

    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(clip),
        "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r=30",
        "-filter_complex",
        (
            f"[0:v]scale={width}:{height},fps=30,{GRADE_EQ}[base];"
            f"[1:v]format=rgba,geq=r=0:g=0:b=0:a='{gradient_alpha_expression()}'[grad];"
            f"[base][grad]overlay=shortest=1,"
            f"fade=t=in:st=0:d={LOOP_FADE_SECONDS},"
            f"fade=t=out:st={fade_out_at:.2f}:d={LOOP_FADE_SECONDS},"
            f"format=yuv420p[out]"
        ),
        "-map", "[out]",
        "-an",
        "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out),
    ])


def scaled_size(clip: Path) -> Tuple[int, int]:
    """Target size: long edge capped at ENCODE_LONG_EDGE, aspect kept, both
    dimensions even (H.264 cannot encode odd ones)."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(clip)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {clip.name}:\n{result.stderr[-500:]}")
    raw_w, _, raw_h = result.stdout.strip().partition("x")
    width, height = int(raw_w), int(raw_h)

    scale = min(1.0, ENCODE_LONG_EDGE / max(width, height))
    width = max(2, int(width * scale) // 2 * 2)
    height = max(2, int(height * scale) // 2 * 2)
    return width, height


def grade_within_budget(clip: Path, out: Path) -> int:
    """Grade, stepping quality down if the result busts the size budget."""
    for crf in (ENCODE_CRF, ENCODE_CRF + 3, ENCODE_CRF + 6):
        grade_and_encode(clip, out, crf=crf)
        size = out.stat().st_size
        if size <= SIZE_BUDGET_BYTES:
            if crf != ENCODE_CRF:
                print(f"      needed crf {crf} to fit the budget")
            return size
    print(f"      still {out.stat().st_size / 1e6:.2f} MB at crf {ENCODE_CRF + 6} — kept anyway")
    return out.stat().st_size


def make_poster(video: Path, poster: Path) -> None:
    """First frame as a JPG — what the hero shows before playback starts, and
    all it shows for a visitor who has asked for reduced motion."""
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vframes", "1", "-q:v", "5", str(poster),
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_shots() -> Dict[str, Dict]:
    if not SHOTS_FILE.is_file():
        sys.exit(f"{SHOTS_FILE} not found.")
    data = json.loads(SHOTS_FILE.read_text(encoding="utf-8"))
    shots = data.get("shots")
    if not isinstance(shots, dict) or not shots:
        sys.exit(f"{SHOTS_FILE} has no 'shots' object.")
    return shots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the clip that plays behind the landing hero.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Generating costs real money. --dry-run prints the prompts and calls\n"
            "nothing; --regrade re-cuts the master already on disk for free."
        ),
    )
    parser.add_argument("--only", metavar="SHOT",
                        help="build just this shot (there is only one: 01-merchant)")
    parser.add_argument("--seconds", type=int, choices=(5, 10), default=DURATION_SECONDS,
                        help="clip length; wan3.0 allows 5 or 10 and nothing else")
    parser.add_argument("--regrade", action="store_true",
                        help="re-grade the downloaded master without generating anything")
    parser.add_argument("--frames-dir", metavar="DIR",
                        help="take the first frame from here instead of scripts/hero_frames/")
    parser.add_argument("--frame-urls", metavar="JSON",
                        help='{"01-merchant": "https://...png"} — skip hosting, use these')
    parser.add_argument("--dry-run", action="store_true",
                        help="print the prompts; call nothing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / "backend" / ".env")

    global FRAMES_DIR
    if args.frames_dir:
        FRAMES_DIR = Path(args.frames_dir).resolve()

    shots = load_shots()
    names = list(shots)

    if args.only:
        if args.only not in names:
            sys.exit(f"Unknown shot '{args.only}'. Known: {', '.join(names)}")
        names = [args.only]

    name = names[0]
    shot = shots[name]
    raw = RAW_DIR / f"{name}.mp4"

    print(f"\n{name} — {shot['title']}")
    print(f"  {RESOLUTION} {RATIO}, {args.seconds}s")

    if args.dry_run:
        print("\n--dry-run: nothing submitted.\n")
        print(f"  models, in order: {', '.join(video_models())}")
        print(f"\n  prompt:\n    {shot['video_prompt']}\n")
        print("  (frame_prompt in the shot file is only used when a first "
              "frame is supplied\n   by hand; the default path is "
              "text-to-video and needs no first frame.)\n")
        return 0

    require_tool("ffmpeg")
    require_tool("ffprobe")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.regrade:
        if not raw.is_file():
            sys.exit(f"Nothing to re-grade: {raw} does not exist. Run without --regrade.")
        print("\n--regrade: using the master already on disk, generating nothing.")
    else:
        api_key()  # fail now, not after the frame has been generated
        frame = FRAMES_DIR / f"{name}.png"
        frame_urls: Dict[str, str] = json.loads(args.frame_urls) if args.frame_urls else {}

        with httpx.Client() as client:
            try:
                if raw.is_file() and raw.stat().st_size > 0:
                    print("      master already downloaded — re-grading only")
                else:
                    # Text-to-video by default. A first frame is only used if
                    # one was actually supplied — a real photograph dropped in
                    # by hand, or a URL passed on the command line. Nothing is
                    # generated just to be handed straight back.
                    url = frame_urls.get(name, "")
                    if not url and frame.is_file():
                        print(f"      using the supplied first frame {frame.name}")
                        url = upload_frame(client, frame)
                        print(f"      first frame: {url}")
                    elif url:
                        print(f"      using the supplied first frame URL: {url}")
                    else:
                        print("      text-to-video (no first frame supplied)")

                    print("      submitting")
                    task_id, used = submit_video(
                        client, shot["video_prompt"], args.seconds, url
                    )
                    print(f"      task {task_id} on {used}")
                    video_url, body = poll_task(client, task_id, want="video")
                    usage = describe_usage(body)
                    if usage:
                        print(f"      usage: {usage}")
                    print("      downloading")
                    download(client, video_url, raw)
            except Exception as exc:
                print(f"      FAILED: {exc}")
                return 1

    print("\nGrading")
    size = grade_within_budget(raw, OUT_VIDEO)
    make_poster(OUT_VIDEO, OUT_POSTER)
    width, height = scaled_size(OUT_VIDEO)
    print(f"      → {OUT_VIDEO.relative_to(REPO_ROOT)}  "
          f"{duration_of(OUT_VIDEO):.1f}s  {width}x{height}  {size / 1e6:.2f} MB")
    print(f"      → {OUT_POSTER.relative_to(REPO_ROOT)}")
    print("\nNext: cd frontend && npm run build, look at the hero, then commit "
          "the MP4 and the poster.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
