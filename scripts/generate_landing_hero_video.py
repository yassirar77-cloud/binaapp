#!/usr/bin/env python3
"""Build the clip that plays behind the landing hero.

ONE continuous shot: a merchant in a tudung in a warm, dim kedai makan,
phone in hand, slow push-in. Nothing else.

It used to be three shots, two of them screen captures of real BinaApp pages.
That was wrong and the result was unusable: the hero headline sits on top of
this clip, and text behind text makes both unreadable. So both prompts here
forbid anything legible — no signage, no menu boards, no writing, no labels —
and the encode grades the frame down hardest where the copy sits.

There is no photograph to start from, so the first frame is generated with
text-to-image and then animated with wan3.0 image-to-video.

Provider, endpoint and key are the ones the product already uses for merchant
hero videos — DashScope (Alibaba Model Studio), read exactly as
``backend/app/services/zai_video_service.py`` reads them. The key comes from
the environment or a ``.env`` git already ignores; nothing is hardcoded.

wan3.0 fetches the first frame by URL, so the generated PNG has to be hosted
before the job is submitted. Three routes are tried in order — DashScope's own
upload endpoint, then Cloudinary (BinaApp's own storage, used when its
credentials are in the environment), then a generic file host — each retried
through transient 5xx. All of it happens before anything billable.

The encode does three things the raw clip does not:

  * scales it so its long edge is at most 1280 and strips the audio,
  * grades it down — less brightness, a touch more contrast — and lays a
    black gradient over the upper left, where the headline and CTA sit, so
    white copy keeps its contrast over any frame,
  * fades the first and last half second, so the loop point reads as
    deliberate rather than as a jump cut. wan3.0 does not produce a genuinely
    seamless loop and no prompt makes it.

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

#: The unified model: the only DashScope one that can animate a supplied first
#: frame. happyhorse is text-to-video and would silently drop the screenshots.
DEFAULT_VIDEO_MODEL = "wan3.0-video"

#: Text-to-image, for shot 1's first frame only. Overridable because Model
#: Studio renames these more often than it renames the video models.
DEFAULT_IMAGE_MODEL = "wanx2.1-t2i-turbo"

DEFAULT_API_URL = "https://dashscope-intl.aliyuncs.com/api/v1"

RUNNING_STATES = ("PENDING", "RUNNING", "SUSPENDED")
FAILED_STATES = ("FAILED", "CANCELED", "CANCELLED", "UNKNOWN")

#: Vertical. The hero is full-bleed, and a portrait frame keeps the subject
#: whole on a phone — which is where most Malaysian merchants will see it.
RESOLUTION = "1080P"
RATIO = "9:16"
DURATION_SECONDS = 10

#: Size asked of the text-to-image model for the first frame. Portrait, to
#: match the video's own aspect so nothing is cropped on the way in.
IMAGE_SIZE = "720*1280"

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
#: toward the lower right, where the subject is. Measured on a bright test
#: pattern: -60% luminance under the copy, -31% over the subject.
GRADE_EQ = "eq=brightness=-0.10:contrast=1.06:saturation=0.92"
GRADE_LEFT_STRENGTH = 0.72     # how black the left edge goes
GRADE_LEFT_REACH = 0.85        # ... fading out by this fraction of the width
GRADE_TOP_STRENGTH = 0.60      # how black the top edge goes
GRADE_TOP_REACH = 0.45         # ... fading out by this fraction of the height

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


def video_model() -> str:
    return (os.getenv("DASHSCOPE_VIDEO_MODEL") or DEFAULT_VIDEO_MODEL).strip() or DEFAULT_VIDEO_MODEL


def image_model() -> str:
    return (os.getenv("DASHSCOPE_T2I_MODEL") or DEFAULT_IMAGE_MODEL).strip() or DEFAULT_IMAGE_MODEL


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


def generate_first_frame(client: httpx.Client, prompt: str, destination: Path) -> None:
    """Text-to-image for the one shot with no photograph to start from."""
    payload = {
        "model": image_model(),
        "input": {"prompt": prompt},
        "parameters": {"size": os.getenv("HERO_IMAGE_SIZE", IMAGE_SIZE), "n": 1},
    }
    response = client.post(
        f"{api_url()}/services/aigc/text2image/image-synthesis",
        headers=auth_headers(),
        json=payload,
        timeout=SUBMIT_TIMEOUT,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"image submit failed ({response.status_code}): {response.text[:300]}\n"
            f"      If the model name is wrong, set DASHSCOPE_T2I_MODEL to a text-to-image\n"
            f"      model your account has, or pass --frames-dir with your own PNG."
        )
    task_id = ((response.json() or {}).get("output") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"image submit returned no task id: {response.text[:300]}")
    print(f"      image task {task_id}")

    url, body = poll_task(client, str(task_id), want="image")
    usage = describe_usage(body)
    if usage:
        print(f"      usage: {usage}")
    download(client, url, destination)


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


def submit_video(client: httpx.Client, prompt: str, frame_url: str, seconds: int) -> str:
    """Image-to-video on the unified model, with the frame as the first frame."""
    payload = {
        "model": video_model(),
        "input": {
            "prompt": prompt,
            "media": [{"type": "first_frame", "url": frame_url}],
        },
        "parameters": {
            "resolution": RESOLUTION,
            "ratio": RATIO,
            "duration": seconds,
            # wan3.x generates a soundtrack unless told not to. The hero is
            # always muted, so it would only cost money and bytes.
            "audio": False,
        },
    }
    headers = auth_headers()
    if frame_url.startswith("oss://"):
        # A reference into DashScope's own bucket is only resolved when the
        # request says so; without this header the API sees an unusable URL.
        headers["X-DashScope-OssResourceResolve"] = "enable"

    response = client.post(
        f"{api_url()}/services/aigc/video-generation/video-synthesis",
        headers=headers,
        json=payload,
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
        raise RuntimeError(f"video submit failed ({response.status_code}): {response.text[:300]}")

    output = ((response.json() or {}).get("output") or {})
    task_id = output.get("task_id")
    if not task_id:
        raise RuntimeError(f"video submit returned no task id: {response.text[:300]}")
    if str(output.get("task_status", "")).upper() in FAILED_STATES:
        raise RuntimeError(f"rejected at submit ({output.get('message')})")
    return str(task_id)


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
    print(f"  {video_model()}, {RESOLUTION} {RATIO}, {args.seconds}s")

    if args.dry_run:
        print("\n--dry-run: nothing submitted.\n")
        print(f"  first frame ({image_model()}):\n    {shot['frame_prompt']}\n")
        print(f"  motion:\n    {shot['video_prompt']}\n")
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
                    if not frame.is_file():
                        print("      generating the first frame")
                        generate_first_frame(client, shot["frame_prompt"], frame)
                    else:
                        print(f"      using the first frame already at {frame.name}")

                    url = frame_urls.get(name)
                    if not url:
                        print("      hosting the first frame")
                        url = upload_frame(client, frame)
                    print(f"      first frame: {url}")

                    print("      submitting")
                    task_id = submit_video(client, shot["video_prompt"], url, args.seconds)
                    print(f"      task {task_id}")
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
