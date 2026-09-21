#!/usr/bin/env python3
"""Build the 20-second "how it works" film that sits under the landing hero.

Four generated shots of five seconds each, joined with zoom transitions:

    1. she has the idea, phone in hand          text-to-video
    2. her real /create brief, on that phone    image-to-video
    3. her finished site, on that phone         image-to-video
    4. she shows it to a customer               text-to-video
       then a one-second hold on the last frame

Shots 2 and 3 start from a frame this script draws: the merchant's own
screenshot, pin-sharp, on a phone standing in a warm out-of-focus kedai. The
frame is built with PIL (`build_first_frame`), hosted, and handed to the model
as `input.media[0].type == "first_frame"`.

WHAT THAT COSTS YOU. wan3.0 redraws every frame it generates, including the
first one it was given. UI text is the first thing it destroys — this was
tried before and the clips came back with the interface melted into
letter-shaped noise. The prompts for those two shots therefore say "camera
move only" about as loudly as a prompt can, but the model is under no
obligation to listen, and the first frame is the only part guaranteed sharp.
Judge shots 2 and 3 on their first second.

Models are tried in order until one accepts: wan3.0-video, then
happyhorse-1.1-t2v. A model the account does not have is rejected at submit,
and a rejected submit is not billed, so walking the list costs nothing. Note
that the fallback is text-to-video only: if wan3.0 is unavailable, shots 1 and
4 still generate and shots 2 and 3 cannot.

The film's own length is arithmetic, not a target to hit: four five-second
shots, three overlapping transitions and a tail hold come to about 19.5s.

Usage
-----
    python3 scripts/generate_howitworks_video.py --dry-run   # frames + prompts, no spend
    python3 scripts/generate_howitworks_video.py             # the real run, four clips

Requires ``ffmpeg``/``ffprobe``, ``httpx`` and ``pillow``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
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
SHOTS_FILE = REPO_ROOT / "scripts" / "howitworks_shots.json"
ASSETS_DIR = REPO_ROOT / "scripts" / "howitworks_assets"
RAW_DIR = REPO_ROOT / "scripts" / "howitworks_raw"
FRAMES_DIR = RAW_DIR / "frames"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "hero"
OUT_VIDEO = OUT_DIR / "binaapp-howitworks.mp4"
OUT_POSTER = OUT_DIR / "binaapp-howitworks.jpg"


# ---------------------------------------------------------------------------
# Provider — mirrored from backend/app/services/zai_video_service.py
# ---------------------------------------------------------------------------

#: Tried in order until one accepts. wan3.0 first: it looks better, and it is
#: the only one of the two that can animate a supplied first frame. happyhorse
#: second: it generated all sixteen showcase clips on this account, so it is
#: known to work here. DASHSCOPE_VIDEO_MODEL pins one name instead.
VIDEO_MODEL_CHAIN = ("wan3.0-video", "happyhorse-1.1-t2v")
DEFAULT_API_URL = "https://dashscope-intl.aliyuncs.com/api/v1"

FAILED_STATES = ("FAILED", "CANCELED", "CANCELLED", "UNKNOWN")
MODEL_MISSING_MARKERS = ("model not exist", "model does not exist", "invalidparameter")

RESOLUTION = "1080P"
RATIO = "16:9"

SUBMIT_TIMEOUT = 90
POLL_TIMEOUT = 60
POLL_INTERVAL = 10
MAX_WAIT_SECONDS = 1200
DOWNLOAD_TIMEOUT = 600

#: What one 5-second wan3.0 job has been costing on this account, near enough
#: to plan with. The API returns a `usage` block per job and this script prints
#: it verbatim; that, not this number, is what you were actually charged.
ROUGH_COST_PER_SHOT_USD = 0.70


# ---------------------------------------------------------------------------
# Look
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 1920, 1080
FPS = 30
ENCODE_CRF = 26
SIZE_BUDGET_BYTES = 6_000_000

#: Every intermediate is written with these exact settings. The timescale is
#: pinned because xfade refuses inputs whose timebases differ — two clips
#: encoded moments apart came back 1/15360 and 1/12800 and the assembly died
#: with "do not match the corresponding second input link xfade timebase".
INTERMEDIATE_ARGS = [
    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
    "-pix_fmt", "yuv420p", "-video_track_timescale", str(FPS * 512), "-r", str(FPS),
]

#: The first frame, drawn rather than photographed.
FRAME_PHONE_HEIGHT = 840      # the screen itself, before the bezel
FRAME_PHONE_BEZEL = 15
FRAME_SCREEN_RADIUS = 40
FRAME_BODY_RADIUS = 54
FRAME_PHONE_TILT = -4.0       # degrees; negative leans the top to the right
FRAME_SHADOW_OFFSET = (18, 34)
FRAME_SHADOW_BLUR = 34
FRAME_SHADOW_ALPHA = 205
BACKDROP_SEED = 11
BACKDROP_BOKEH = 40


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def api_key() -> str:
    key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if not key:
        sys.exit(
            "DASHSCOPE_API_KEY is not set.\n"
            "  Locally: put it in .env (which is gitignored).\n"
            "  In CI:   it is already a repository secret."
        )
    return key


def api_url() -> str:
    return (os.getenv("DASHSCOPE_API_URL") or DEFAULT_API_URL).rstrip("/")


def video_models() -> Tuple[str, ...]:
    pinned = (os.getenv("DASHSCOPE_VIDEO_MODEL") or "").strip()
    return (pinned,) if pinned else VIDEO_MODEL_CHAIN


def video_model() -> str:
    return video_models()[0]


def is_unified(model: str) -> bool:
    """wan3.x takes `input.media` and generates audio; the older ones do not."""
    return model.startswith("wan3") and not model.endswith(("-t2v", "-i2v"))


def auth_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"{name} is not on PATH.")


def run_quiet(command: List[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{command[0]} failed:\n{result.stderr.strip()[-1500:]}")


def probe(path: Path, entries: str, stream: bool = True) -> str:
    command = ["ffprobe", "-v", "error"]
    if stream:
        command += ["-select_streams", "v:0"]
    command += ["-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {result.stderr.strip()[-400:]}")
    return result.stdout.strip()


def duration_of(path: Path) -> float:
    return float(probe(path, "format=duration", stream=False).splitlines()[0])


def smoothstep(progress: str) -> str:
    """3p²-2p³ — the ease that stops a move starting and stopping with a jerk."""
    return f"({progress}*{progress}*(3-2*{progress}))"


# ---------------------------------------------------------------------------
# The first frame for the image-to-video shots
# ---------------------------------------------------------------------------


def _rounded(image, radius: int):
    from PIL import Image, ImageDraw

    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, image.size[0] - 1, image.size[1] - 1], radius=radius, fill=255
    )
    out = image.convert("RGBA")
    out.putalpha(mask)
    return out


def build_backdrop(seed: int = BACKDROP_SEED):
    """A bright, colourful kedai afternoon, thrown well out of focus.

    Everything is drawn, then blurred past recognition, then given its
    highlights back on top — blurring a bokeh bulb along with everything else
    just makes a smudge, so the bulbs go on after the blur and keep their
    shape.
    """
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

    rng = random.Random(seed)
    image = Image.new("RGB", (WIDTH, HEIGHT), (58, 30, 18))
    draw = ImageDraw.Draw(image)

    # Afternoon sun through the shopfront: a broad warm band across the top,
    # falling away to the deep warm shade of the room below.
    for y in range(HEIGHT):
        fall = (1 - y / (HEIGHT - 1)) ** 1.6
        draw.line(
            [(0, y), (WIDTH, y)],
            fill=(int(52 + 168 * fall), int(30 + 118 * fall), int(20 + 72 * fall)),
        )
    draw.rectangle([0, int(HEIGHT * 0.74), WIDTH, HEIGHT], fill=(44, 22, 14))

    # Customers at the tables, the drinks fridge, a shopfront awning. None of
    # it is meant to be identifiable — it is there to give the blur something
    # with the right colours and the right weights in the right places.
    masses = [
        ((0.08, 0.58, 0.20, 0.92), (96, 52, 46)),
        ((0.22, 0.52, 0.33, 0.92), (128, 74, 52)),
        ((0.72, 0.55, 0.85, 0.92), (86, 48, 44)),
        ((0.86, 0.48, 0.99, 0.92), (150, 92, 58)),
        ((0.02, 0.06, 0.30, 0.20), (206, 88, 56)),
        ((0.66, 0.05, 0.98, 0.17), (72, 150, 142)),
    ]
    for (left, top, right, bottom), colour in masses:
        draw.rounded_rectangle(
            [WIDTH * left, HEIGHT * top, WIDTH * right, HEIGHT * bottom],
            radius=90, fill=colour,
        )
    image = image.filter(ImageFilter.GaussianBlur(40))

    palette = [
        (255, 214, 132), (255, 176, 96), (255, 244, 206), (128, 226, 212),
        (255, 122, 96), (196, 240, 150), (255, 198, 150),
    ]
    for _ in range(BACKDROP_BOKEH):
        x, y = rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT * 0.86)
        radius = rng.uniform(30, 130)
        colour = palette[rng.randrange(len(palette))]
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=colour + (rng.randrange(85, 190),),
        )
        image = Image.alpha_composite(
            image.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(radius * 0.42))
        ).convert("RGB")

    image = image.filter(ImageFilter.GaussianBlur(14))
    return ImageEnhance.Color(image).enhance(1.25)


def screen_image(spec: Dict):
    """The merchant's own pixels: a screenshot, or one frame of her recording."""
    from PIL import Image

    if spec.get("source"):
        source = ASSETS_DIR / spec["source"]
        if not source.is_file():
            raise RuntimeError(f"first-frame source not found: {source}")
        return Image.open(source).convert("RGB")

    recording = ASSETS_DIR / spec["source_video"]
    if not recording.is_file():
        raise RuntimeError(f"first-frame source not found: {recording}")
    grab = FRAMES_DIR / f"grab-{recording.stem}-{spec.get('at_seconds', 0)}.png"
    grab.parent.mkdir(parents=True, exist_ok=True)
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{float(spec.get('at_seconds', 0)):.3f}", "-i", str(recording),
        "-vframes", "1", str(grab),
    ])
    return Image.open(grab).convert("RGB")


def build_first_frame(spec: Dict, out: Path) -> Path:
    """Draw the frame shots 2 and 3 start from, and save it as a PNG.

    A phone standing in the warm blur of her kedai, her own screenshot on the
    glass at full resolution. No hand: drawn fingers against a photographic
    backdrop read as clip art, and the model animates a drawn hand as a
    drawn hand. The phone is tilted and shadowed instead, which is a shot a
    camera could have taken.
    """
    from PIL import Image, ImageFilter

    screen = screen_image(spec)
    top = float(spec.get("top_crop", 0.052))
    bottom = float(spec.get("bottom_crop", 0.066))
    screen = screen.crop(
        (0, int(screen.height * top), screen.width, int(screen.height * (1 - bottom)))
    )

    height = int(spec.get("screen_height", FRAME_PHONE_HEIGHT))
    width = int(screen.width * height / screen.height)
    screen = screen.resize((width, height), Image.LANCZOS)

    bezel = FRAME_PHONE_BEZEL
    body = _rounded(
        Image.new("RGBA", (width + bezel * 2, height + bezel * 2), (16, 16, 19, 255)),
        FRAME_BODY_RADIUS,
    )
    glass = _rounded(screen, FRAME_SCREEN_RADIUS)
    body.paste(glass, (bezel, bezel), glass)
    body = body.rotate(
        float(spec.get("tilt", FRAME_PHONE_TILT)), resample=Image.BICUBIC, expand=True
    )

    offset_x, offset_y = spec.get("offset", [0.02, 0.0])
    x = int(WIDTH * (0.5 + float(offset_x)) - body.width / 2)
    y = int(HEIGHT * (0.5 + float(offset_y)) - body.height / 2)

    silhouette = Image.new("RGBA", body.size, (0, 0, 0, 0))
    silhouette.paste((0, 0, 0, FRAME_SHADOW_ALPHA), (0, 0), body)
    shadow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    shadow.paste(silhouette, (x + FRAME_SHADOW_OFFSET[0], y + FRAME_SHADOW_OFFSET[1]),
                 silhouette)

    frame = Image.alpha_composite(
        build_backdrop().convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(FRAME_SHADOW_BLUR))
    )
    frame.paste(body, (x, y), body)

    out.parent.mkdir(parents=True, exist_ok=True)
    frame.convert("RGB").save(out)
    return out


# ---------------------------------------------------------------------------
# Hosting the first frame
#
# The model takes a URL, not an upload, so the PNG has to be reachable before
# the job is submitted. An earlier run died on a free paste host's 503 — one
# unowned dependency between a working frame and a billable call. Three routes
# are tried in order, all of them before anything is charged, each retried
# through transient 5xx.
# ---------------------------------------------------------------------------

FRAME_UPLOAD_ATTEMPTS = 4
FRAME_UPLOAD_BACKOFF_SECONDS = 2
TRANSIENT_STATUSES = (408, 425, 429, 500, 502, 503, 504)


def request_with_retry(client: httpx.Client, method: str, url: str, *,
                       attempts: int = FRAME_UPLOAD_ATTEMPTS, **kwargs) -> httpx.Response:
    """One request, retried through transient failures with backoff.

    ``files=`` is not reusable across attempts — the handle is consumed by the
    first one — so callers hand over bytes and this rebuilds the form each time.
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
    """Upload through DashScope's own endpoint. Returns an ``oss://`` ref."""
    policy = request_with_retry(
        client, "GET", f"{api_url()}/uploads",
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
        client, "POST", data["upload_host"], data=form,
        files={"file": (frame.name, payload, "image/png")}, timeout=DOWNLOAD_TIMEOUT,
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

    match = re.match(r"cloudinary://([^:]+):([^@]+)@(.+)",
                     (os.getenv("CLOUDINARY_URL") or "").strip())
    if match:
        return match.group(3), match.group(1), match.group(2)
    return "", "", ""


def upload_via_cloudinary(client: httpx.Client, frame: Path) -> str:
    """Upload to BinaApp's own Cloudinary, the way the backend does."""
    cloud, key, secret = cloudinary_credentials()
    if not (cloud and key and secret):
        raise RuntimeError("no Cloudinary credentials in the environment")

    folder = os.getenv("HOWITWORKS_FRAME_CLOUDINARY_FOLDER", "binaapp/howitworks-frames")
    timestamp = str(int(time.time()))

    # Cloudinary signs the upload params: every signed field except file,
    # api_key and the signature itself, sorted by name, joined as a query
    # string, with the secret appended, then SHA-1.
    signed = {"folder": folder, "timestamp": timestamp}
    to_sign = "&".join(f"{k}={signed[k]}" for k in sorted(signed)) + secret
    signature = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

    payload = frame.read_bytes()
    response = request_with_retry(
        client, "POST", f"https://api.cloudinary.com/v1_1/{cloud}/image/upload",
        data={**signed, "api_key": key, "signature": signature},
        files={"file": (frame.name, payload, "image/png")}, timeout=DOWNLOAD_TIMEOUT,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Cloudinary returned {response.status_code}: {response.text[:200]}")

    url = (response.json() or {}).get("secure_url")
    if not url:
        raise RuntimeError(f"Cloudinary returned no secure_url: {response.text[:200]}")
    return url


def upload_via_generic_host(client: httpx.Client, frame: Path) -> str:
    """Last resort: a plain file host. Never reached unless the two above fail.

    The frames carry the merchant's own screenshots of her own public site and
    of a logged-in builder page. There is nothing secret in them, but an
    unowned host is still an unowned host, which is why it is last.
    """
    endpoint = os.getenv("HOWITWORKS_FRAME_UPLOAD_URL", "https://0x0.st")
    payload = frame.read_bytes()
    response = request_with_retry(
        client, "POST", endpoint,
        files={"file": (frame.name, payload, "image/png")},
        timeout=DOWNLOAD_TIMEOUT, headers={"User-Agent": "binaapp-film-builder/1.0"},
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"{endpoint} returned {response.status_code}")

    url = response.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"{endpoint} returned something odd: {url[:200]}")
    return url


def upload_frame(client: httpx.Client, frame: Path) -> str:
    """Host the first frame and return the reference to pass to the model."""
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
          '\'{"2-create": "https://..."}\' to skip this step.'
    )


# ---------------------------------------------------------------------------
# Generating
# ---------------------------------------------------------------------------


def poll_task(client: httpx.Client, task_id: str) -> Tuple[str, Dict]:
    deadline = time.time() + MAX_WAIT_SECONDS
    last_state = ""

    while time.time() < deadline:
        response = client.get(
            f"{api_url()}/tasks/{task_id}",
            headers={"Authorization": f"Bearer {api_key()}"},
            timeout=POLL_TIMEOUT,
        )
        if response.status_code in TRANSIENT_STATUSES:
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
            url = output.get("video_url")
            if not url:
                raise RuntimeError(f"SUCCEEDED but no video_url: {str(body)[:300]}")
            return url, body
        if state in FAILED_STATES:
            raise RuntimeError(f"{state}: {output.get('message') or output.get('code') or '?'}")
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(f"still {last_state or 'running'} after {MAX_WAIT_SECONDS}s")


def submit_on(client: httpx.Client, model: str, prompt: str, seconds: int,
              frame_url: str = "") -> str:
    """Submit one job on one model. Returns the task id."""
    unified = is_unified(model)
    input_block: Dict = {"prompt": prompt}
    parameters: Dict = {"resolution": RESOLUTION, "ratio": RATIO, "duration": seconds}

    if frame_url:
        if not unified:
            raise RuntimeError(f"{model} is text-to-video only and cannot animate a first frame")
        input_block["media"] = [{"type": "first_frame", "url": frame_url}]

    if unified:
        # wan3.x generates a soundtrack unless told not to. The film is always
        # muted, so it would only cost money and bytes.
        parameters["audio"] = False
    else:
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
    """Try each model until one accepts. Returns (task id, model)."""
    reasons: List[str] = []

    for model in video_models():
        if frame_url and not is_unified(model):
            print(f"      {model}: skipped (cannot animate a supplied first frame)")
            reasons.append(f"{model}: text-to-video only, but a first frame was given")
            continue
        try:
            task_id = submit_on(client, model, prompt, seconds, frame_url)
        except RuntimeError as exc:
            if any(marker in str(exc).lower() for marker in MODEL_MISSING_MARKERS):
                print(f"      {model}: not available on this account")
            else:
                print(f"      {model}: {exc}")
            reasons.append(f"{model}: {exc}")
            continue
        print(f"      accepted by {model}")
        return task_id, model

    raise RuntimeError(
        "no model accepted the job.\n        " + "\n        ".join(reasons)
        + "\n      Set DASHSCOPE_VIDEO_MODEL (or the workflow's `model` input) to a video "
          "model this account has."
    )


def download(client: httpx.Client, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=65536):
                handle.write(chunk)
    partial.replace(destination)


def build_shot(client: httpx.Client, prompt: str, seconds: int, out: Path,
               frame_url: str = "", tail_push: Dict = None) -> None:
    """Generate one shot, normalise it, and give it its tail move if it has one."""
    master = out.with_name(out.stem + "-master.mp4")
    if master.is_file() and master.stat().st_size > 0:
        print("      master already downloaded — reusing it")
    else:
        print("      submitting")
        task_id, model = submit_video(client, prompt, seconds, frame_url)
        print(f"      task {task_id} on {model}")
        url, body = poll_task(client, task_id)
        usage = body.get("usage") or {}
        if usage:
            print(f"      usage: {' '.join(f'{k}={v}' for k, v in sorted(usage.items()))}")
        print("      downloading")
        download(client, url, master)

    normalise(master, out, tail_push)


def normalise(master: Path, out: Path, tail_push: Dict = None) -> None:
    """One clip to the film's size, rate and timebase, with its tail move.

    The tail move is what makes the cut into the next shot read as a dive
    rather than a dissolve: the frame is already travelling when the
    transition starts, so the transition finishes a move the shot began.
    """
    chain = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS}"
    )
    if tail_push:
        chain += "," + tail_push_filter(duration_of(master), tail_push)
    chain += ",format=yuv420p"

    run_quiet(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(master), "-an", "-vf", chain]
        + INTERMEDIATE_ARGS + [str(out)]
    )


def tail_push_filter(clip_seconds: float, push: Dict) -> str:
    """A zoompan that sits still, then eases into a point near the end.

    d=1 makes zoompan a per-frame move over a video rather than a pan over a
    still, so `on` counts the clip's own frames.
    """
    zoom = float(push.get("zoom", 1.5))
    move_seconds = min(float(push.get("seconds", 1.2)), max(clip_seconds - 0.2, 0.2))
    centre_x, centre_y = push.get("center", [0.5, 0.5])

    total_frames = max(2, int(round(clip_seconds * FPS)))
    move_frames = max(1, int(round(move_seconds * FPS)))
    start_frame = max(0, total_frames - move_frames)
    eased = smoothstep(f"min(max((on-{start_frame})/{move_frames},0),1)")

    x_expr = f"(iw*({0.5:.4f}+({float(centre_x):.4f}-0.5)*{eased}))-(iw/zoom/2)"
    y_expr = f"(ih*({0.5:.4f}+({float(centre_y):.4f}-0.5)*{eased}))-(ih/zoom/2)"
    return (
        f"zoompan=z='1+{zoom - 1:.4f}*{eased}':d=1"
        f":x='{x_expr}':y='{y_expr}':s={WIDTH}x{HEIGHT}:fps={FPS}"
    )


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def join(clips: List[Path], out: Path, transition: float, transition_name: str,
         tail_hold: float, crf: int = ENCODE_CRF) -> None:
    """Join the shots with zoom transitions and hold the last frame.

    Nothing may sit between an input and its xfade: putting scale, fps or even
    setpts in front drops the frame rate from the filter link and xfade rejects
    the whole graph with "current rate of 1/0 is invalid". Every clip was
    normalised when it was written, so the inputs already match here, and the
    only filter after the joins is the hold.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(clips) == 1 and tail_hold <= 0:
        # One clip and nothing to hold leaves no filter graph at all, and
        # ffmpeg rejects an empty -filter_complex.
        shutil.copy(clips[0], out)
        return

    command: List[str] = ["ffmpeg", "-y", "-loglevel", "error"]
    for clip in clips:
        command += ["-i", str(clip)]

    steps: List[str] = []
    running = duration_of(clips[0])
    previous = "0:v"
    for index in range(1, len(clips)):
        label = f"x{index}"
        steps.append(
            f"[{previous}][{index}:v]xfade=transition={transition_name}"
            f":duration={transition}:offset={running - transition:.3f}[{label}]"
        )
        running = running + duration_of(clips[index]) - transition
        previous = label

    if tail_hold > 0:
        steps.append(f"[{previous}]tpad=stop_mode=clone:stop_duration={tail_hold}[held]")
        previous = "held"

    command += ["-filter_complex", ";".join(steps), "-map", f"[{previous}]", "-an"]
    command += [
        "-c:v", "libx264", "-crf", str(crf), "-preset", "slow", "-pix_fmt", "yuv420p",
        "-video_track_timescale", str(FPS * 512), "-r", str(FPS), "-movflags", "+faststart",
        str(out),
    ]
    run_quiet(command)


def make_poster(video: Path, poster: Path, at: float) -> None:
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(video),
        "-vframes", "1", "-q:v", "4", str(poster),
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_plan() -> Dict:
    if not SHOTS_FILE.is_file():
        sys.exit(f"{SHOTS_FILE} not found.")
    return json.loads(SHOTS_FILE.read_text(encoding="utf-8"))


def prompt_for(plan: Dict, shot: Dict) -> str:
    """Shots 1 and 4 share one description of her, interpolated the same way.

    Having the woman in one place in the plan is the only way two prompts stay
    word-for-word identical about her face, her tudung and her clothes — which
    is the whole reason the same person appears at both ends of the film.
    """
    return shot["prompt"].replace("{woman}", plan.get("woman", "").strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Build the "how it works" film — four generated shots.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--seconds", type=int, choices=(5, 10), default=None,
                        help="length of each shot; the provider allows 5 or 10")
    parser.add_argument("--only", default="", help="build one shot by name")
    parser.add_argument("--frames-only", action="store_true",
                        help="draw the first frames and stop — nothing is submitted")
    parser.add_argument("--frame-urls", default="",
                        help='JSON of already-hosted first frames, {"2-create": "https://..."}')
    parser.add_argument("--dry-run", action="store_true",
                        help="draw the first frames and print the prompts; call nothing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / "backend" / ".env")

    plan = load_plan()
    shots = plan["shots"]
    timing = plan.get("timing", {})
    seconds = args.seconds or int(timing.get("shot_seconds", 5))
    transition = float(timing.get("transition_seconds", 0.5))
    transition_name = str(timing.get("transition", "zoomin"))
    tail_hold = float(timing.get("tail_hold_seconds", 1.0))

    names = [n for n in shots if not args.only or n == args.only]
    if args.only and not names:
        sys.exit(f"no shot named {args.only}. Have: {', '.join(shots)}")

    length = seconds * len(names) - transition * max(0, len(names) - 1) + tail_hold
    print(f"\n{plan['merchant']['name']} — {len(names)} shots of {seconds}s, "
          f"{transition}s {transition_name} transitions, {tail_hold}s tail hold "
          f"→ {length:.1f}s")
    for name in names:
        kind = "image-to-video" if shots[name].get("first_frame") else "text-to-video"
        print(f"  {name:12} {shots[name]['title']}  ({kind})")

    require_tool("ffmpeg")
    require_tool("ffprobe")
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    # --- the first frames: drawn from her own pixels, costing nothing ---
    frames: Dict[str, Path] = {}
    for name in names:
        spec = shots[name].get("first_frame")
        if not spec:
            continue
        frame = FRAMES_DIR / f"{name}.png"
        print(f"\n[{name}] drawing the first frame")
        build_first_frame(spec, frame)
        frames[name] = frame
        print(f"      → {frame.relative_to(REPO_ROOT)}")

    if args.dry_run or args.frames_only:
        billable = len(names)
        print(f"\n--{'dry-run' if args.dry_run else 'frames-only'}: nothing submitted, "
              f"nothing spent.")
        print(f"  A real run is {billable} jobs, roughly "
              f"USD {billable * ROUGH_COST_PER_SHOT_USD:.2f} at "
              f"~{ROUGH_COST_PER_SHOT_USD:.2f}/shot.")
        print(f"  Models, in order: {', '.join(video_models())}\n")
        for name in names:
            print(f"  ── {name} — {shots[name]['title']}")
            if name in frames:
                print(f"     first frame: {frames[name].relative_to(REPO_ROOT)}")
            print(f"     {prompt_for(plan, shots[name])}\n")
        return 0

    api_key()  # fail now, not after the first shot renders
    supplied = json.loads(args.frame_urls) if args.frame_urls else {}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        # Every frame is hosted before any job is submitted: a hosting problem
        # should cost nothing, which is how it failed the first time and how
        # it should keep failing.
        frame_urls: Dict[str, str] = {}
        for name, frame in frames.items():
            if name in supplied:
                frame_urls[name] = supplied[name]
                print(f"\n[{name}] using the supplied first-frame URL")
                continue
            print(f"\n[{name}] hosting the first frame")
            try:
                frame_urls[name] = upload_frame(client, frame)
            except RuntimeError as exc:
                print(f"\n{exc}\n")
                return 1

        for name in names:
            print(f"\n[{name}] {shots[name]['title']}")
            clip = RAW_DIR / f"{name}.mp4"
            try:
                build_shot(
                    client, prompt_for(plan, shots[name]), seconds, clip,
                    frame_url=frame_urls.get(name, ""),
                    tail_push=shots[name].get("tail_push"),
                )
            except Exception as exc:
                print(f"      FAILED: {exc}")
                return 1
            print(f"      {duration_of(clip):.1f}s")

    ordered = [RAW_DIR / f"{n}.mp4" for n in names]
    missing = [c for c in ordered if not c.is_file()]
    if missing:
        print(f"\nMissing shots: {', '.join(c.name for c in missing)}\n")
        return 1

    print("\nJoining them")
    join(ordered, OUT_VIDEO, transition, transition_name, tail_hold)
    final = duration_of(OUT_VIDEO)
    size = OUT_VIDEO.stat().st_size
    make_poster(OUT_VIDEO, OUT_POSTER, at=min(1.0, final / 4))

    print(f"      → {OUT_VIDEO.relative_to(REPO_ROOT)}  {final:.2f}s  {size / 1e6:.2f} MB")
    print(f"      → {OUT_POSTER.relative_to(REPO_ROOT)}")
    if size > SIZE_BUDGET_BYTES:
        print(f"      note: over the {SIZE_BUDGET_BYTES / 1e6:.0f} MB budget")
    print("\nNext: cd frontend && npm run build, look at the section, then commit.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
