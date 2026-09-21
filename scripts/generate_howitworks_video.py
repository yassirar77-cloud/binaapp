#!/usr/bin/env python3
"""Build the 20-second "how it works" film that sits under the landing hero.

Four beats, cross-faded, following one real merchant — Dapur Western Kak Mira:

    1. she sits down with her phone after closing        (AI)
    2. the real /create flow, in a phone mockup          (her screenshots)
    3. her finished site, in the same phone              (her screen recording)
    4. she turns the phone toward a customer             (AI)
       then her site full frame, pin-sharp, held 2s      (her recording)

THE MERCHANT'S OWN FOOTAGE NEVER GOES TO A VIDEO MODEL. wan3.0 and happyhorse
redraw every frame, and UI text is the first thing they destroy — the point of
beats 2 and 3 is that the words on screen are real. Those beats are built
entirely in ffmpeg: a phone mockup over a brand gradient, an eased push-in, a
light sweep across the glass, cross-dissolves between stills. Only the two
beats with a person in them are generated.

The AI beats go to DashScope — same provider, endpoint and key the product
already uses for merchant hero videos, read as
``backend/app/services/zai_video_service.py`` reads them. Models are tried in
order until one accepts: wan3.0-video, then happyhorse-1.1-t2v. A model the
account does not have is rejected at submit, and a rejected submit is not
billed, so walking the list costs nothing.

ON CLIP LENGTH. The product's own limit is 5 or 10 seconds per job and nothing
between (``ALLOWED_DURATIONS`` in the service above). Two 10-second AI beats
would be 20 seconds on their own and leave no room for the merchant's real
footage, which is the part worth showing — so the AI beats are 5 seconds each
and her screenshots and recording get the remaining ~10. ``--ai-seconds 10``
is accepted but will refuse to run unless the total is raised with
``--total``.

Timing is computed, not hard-coded: the AI clips are measured after download
and the ffmpeg beats are stretched or squeezed so the finished film lands on
the target length exactly, whatever the provider returned.

Usage
-----
    python3 scripts/generate_howitworks_video.py --dry-run     # calls nothing
    python3 scripts/generate_howitworks_video.py --stills-only # no AI, no spend
    python3 scripts/generate_howitworks_video.py               # the real run

Requires ``ffmpeg``/``ffprobe`` and ``httpx``.
"""

from __future__ import annotations

import argparse
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
SHOTS_FILE = REPO_ROOT / "scripts" / "howitworks_shots.json"
ASSETS_DIR = REPO_ROOT / "scripts" / "howitworks_assets"
RAW_DIR = REPO_ROOT / "scripts" / "howitworks_raw"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "hero"
OUT_VIDEO = OUT_DIR / "binaapp-howitworks.mp4"
OUT_POSTER = OUT_DIR / "binaapp-howitworks.jpg"


# ---------------------------------------------------------------------------
# Provider — mirrored from backend/app/services/zai_video_service.py
# ---------------------------------------------------------------------------

#: Tried in order until one accepts. wan3.0 first: it looks better. happyhorse
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


# ---------------------------------------------------------------------------
# Look
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 1920, 1080
FPS = 30
ENCODE_CRF = 26
SIZE_BUDGET_BYTES = 6_000_000

#: The phone. Tall in frame — the merchant's screen is the subject, not a
#: postage stamp floating on a background.
PHONE_HEIGHT = 930
PHONE_RADIUS = 44

#: Fractions trimmed off a phone capture. The screenshots lose the OS status
#: bar and the navigation bar. The recording loses more from the top: from
#: about three seconds in, Chrome shows a "No internet connection" banner
#: between the status bar and the URL bar, and cropping past all three is the
#: only way to lose it without the crop changing halfway through.
STATUS_BAR_FRACTION = 0.052
NAV_BAR_FRACTION = 0.066
RECORDING_TOP_FRACTION = 0.135

#: A few degrees of turn, as if the phone were held rather than pasted on.
#: `perspective` pulls the far edge in; the numbers are pixels of inset at the
#: top-left and bottom-left corners.
TILT_INSET = 22
PHONE_TILT = (
    f"perspective=x0=0:y0={TILT_INSET}:x1=W:y1=0"
    f":x2=0:y2=H-{TILT_INSET}:x3=W:y3=H:sense=destination"
)

#: The shadow the phone casts: its own silhouette, blackened, blurred, offset.
SHADOW_ALPHA = 0.75
SHADOW_BLUR = 26
SHADOW_OFFSET = (14, 26)

#: Backdrop: a warm kedai-at-night wash with out-of-focus bulbs, so the
#: composited beats sit in the same room as the generated ones rather than on
#: a flat navy card. Drawn once with PIL and reused.
BACKDROP_SEED = 7
BACKDROP_BOKEH = 26

#: Step captions: bottom-left, bold, fading in and out.
CAPTION_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)
CAPTION_SIZE = 62
CAPTION_MARGIN = (96, 84)     # from the left, and up from the bottom
CAPTION_FADE = 0.45
CAPTION_BAND_HEIGHT = 300     # the scrim under the type, measured from the bottom
CAPTION_SCRIM_ALPHA = 0.72

#: The shape of a still beat: a moment at rest so the phone reads as a phone,
#: then the push in, then the hold. Without the rest at the front the zoom has
#: already cropped past the phone's edges within four frames and the mockup —
#: the tilt, the shadow, the whole point of it — is never actually seen.
PRE_HOLD_SECONDS = 0.35
PUNCH_IN_SECONDS = 0.55
MIN_HOLD_SECONDS = 1.4

#: Transitions. Any blend between two screenshots shows both at once and both
#: are full of text — which is what made the first cut look amateur. smoothleft
#: was no better: its ramp is wide enough to be a dissolve. A slide carries the
#: old frame off and the new one on with no overlap anywhere, so exactly one
#: screen is ever readable. Between whole beats, where the two sides are
#: different places rather than two documents, a dissolve is still right.
TRANSITION_SECONDS = 0.35
STILL_TRANSITION = "slideleft"
BEAT_TRANSITION = "fade"

#: The closing shot. 0 would sit at the top of the page, 1 at the bottom of
#: what the crop keeps; 0.30 frames her Halal badge, her headline and the rule
#: under it. The side trim loses Chrome's scrollbar sliver.
SITE_CROP_Y = 0.30
SITE_SIDE_TRIM = 0.015

#: Bounds on the speed-up applied to her screen recording: never slowed below
#: real time, never so fast the page becomes a blur.
MIN_SPEED = 1.0
MAX_SPEED = 3.0

#: Every intermediate is written with these exact settings. The timescale is
#: pinned because xfade refuses inputs whose timebases differ — two clips
#: encoded moments apart came back 1/15360 and 1/12800 and the assembly died
#: with "do not match the corresponding second input link xfade timebase".
INTERMEDIATE_ARGS = [
    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
    "-pix_fmt", "yuv420p", "-video_track_timescale", str(FPS * 512), "-r", str(FPS),
]


def rounded_alpha(radius: int) -> str:
    """A geq filter that rounds the corners of whatever it is applied to."""
    return (
        f"geq=lum='p(X,Y)':a='if(gt(abs(X-(W/2)),(W/2)-{radius})"
        f"*gt(abs(Y-(H/2)),(H/2)-{radius}),"
        f"if(lte(pow(abs(X-(W/2))-((W/2)-{radius}),2)"
        f"+pow(abs(Y-(H/2))-((H/2)-{radius}),2),pow({radius},2)),255,0),255)'"
    )


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
        "Set DASHSCOPE_API_KEY in your .env, or export it in this shell.\n"
        "Or run with --stills-only, which needs no key and no spend."
    )


def api_url() -> str:
    return (os.getenv("DASHSCOPE_API_URL") or DEFAULT_API_URL).rstrip("/")


def video_models() -> Tuple[str, ...]:
    pinned = (os.getenv("DASHSCOPE_VIDEO_MODEL") or "").strip()
    return (pinned,) if pinned else VIDEO_MODEL_CHAIN


def is_unified(model: str) -> bool:
    """wan3.x takes `audio`; the older -t2v models do not and may reject it."""
    return (model or "").strip().lower().startswith("wan3")


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"{name} is not on PATH. Install ffmpeg (it ships both ffmpeg and ffprobe).")


def run_quiet(command: List[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{command[0]} failed:\n{result.stderr[-2500:]}")


def probe(path: Path, entries: str, stream: bool = True) -> str:
    args = ["ffprobe", "-v", "error"]
    if stream:
        args += ["-select_streams", "v:0"]
    args += ["-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path.name}:\n{result.stderr[-500:]}")
    return result.stdout.strip()


def duration_of(path: Path) -> float:
    return float(probe(path, "format=duration", stream=False).splitlines()[0])


# ---------------------------------------------------------------------------
# DashScope
# ---------------------------------------------------------------------------


def poll_task(client: httpx.Client, task_id: str) -> Tuple[str, Dict]:
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
            url = output.get("video_url")
            if not url:
                raise RuntimeError(f"SUCCEEDED but no video_url: {str(body)[:300]}")
            return url, body
        if state in FAILED_STATES:
            raise RuntimeError(f"{state}: {output.get('message') or output.get('code') or '?'}")
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(f"still {last_state or 'running'} after {MAX_WAIT_SECONDS}s")


def submit_on(client: httpx.Client, model: str, prompt: str, seconds: int) -> str:
    parameters: Dict = {"resolution": RESOLUTION, "ratio": RATIO, "duration": seconds}
    if is_unified(model):
        parameters["audio"] = False
    else:
        parameters["watermark"] = False

    response = client.post(
        f"{api_url()}/services/aigc/video-generation/video-synthesis",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
        json={"model": model, "input": {"prompt": prompt}, "parameters": parameters},
        timeout=SUBMIT_TIMEOUT,
    )
    if response.status_code == 429:
        raise RuntimeError("rate limited (429) — wait a minute and rerun")
    if response.status_code in (401, 403):
        raise RuntimeError(f"DashScope rejected the key ({response.status_code})")
    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code}: {response.text[:300]}")

    output = ((response.json() or {}).get("output") or {})
    task_id = output.get("task_id")
    if not task_id:
        raise RuntimeError(f"accepted but returned no task id: {response.text[:300]}")
    if str(output.get("task_status", "")).upper() in FAILED_STATES:
        raise RuntimeError(f"rejected at submit ({output.get('message')})")
    return str(task_id)


def submit_video(client: httpx.Client, prompt: str, seconds: int) -> Tuple[str, str]:
    """Try each model until one accepts. Returns (task id, model)."""
    reasons: List[str] = []
    for model in video_models():
        try:
            task_id = submit_on(client, model, prompt, seconds)
        except RuntimeError as exc:
            if any(m in str(exc).lower() for m in MODEL_MISSING_MARKERS):
                print(f"      {model}: not available on this account")
            else:
                print(f"      {model}: {exc}")
            reasons.append(f"{model}: {exc}")
            continue
        print(f"      accepted by {model}")
        return task_id, model

    raise RuntimeError(
        "no model accepted the job.\n        " + "\n        ".join(reasons)
        + "\n      Set DASHSCOPE_VIDEO_MODEL (or the workflow's `model` input) to a model "
          "this account has."
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


def build_ai_shot(client: httpx.Client, prompt: str, seconds: int, out: Path) -> None:
    """Generate one AI beat, then normalise it to the film's size and rate."""
    master = out.with_name(out.stem + "-master.mp4")
    if master.is_file() and master.stat().st_size > 0:
        print("      master already downloaded — reusing it")
    else:
        print("      submitting")
        task_id, model = submit_video(client, prompt, seconds)
        print(f"      task {task_id} on {model}")
        url, body = poll_task(client, task_id)
        usage = (body.get("usage") or {})
        if usage:
            print(f"      usage: {' '.join(f'{k}={v}' for k, v in sorted(usage.items()))}")
        print("      downloading")
        download(client, url, master)

    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(master),
        "-an", "-vf",
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},format=yuv420p",
    ] + INTERMEDIATE_ARGS + [str(out)])


# ---------------------------------------------------------------------------
# The ffmpeg beats — the merchant's own footage, never sent anywhere
# ---------------------------------------------------------------------------


def backdrop_path() -> Path:
    """Draw the warm kedai-at-night backdrop once, and reuse it.

    PIL rather than ffmpeg: a radial wash with two dozen out-of-focus bulbs is
    a handful of lines here and an unreadable geq expression there. It also
    means the look does not depend on which filters a given ffmpeg was built
    with — this one has no drawtext at all.
    """
    destination = RAW_DIR / "backdrop.png"
    if destination.is_file():
        return destination

    from PIL import Image, ImageDraw, ImageFilter
    import random

    base = Image.new("RGB", (WIDTH, HEIGHT), (8, 6, 5))
    draw = ImageDraw.Draw(base)
    # A broad warm pool falling in from the upper right, like a lamp over a
    # counter, drawn as nested ellipses and then blurred smooth.
    for step in range(70, 0, -1):
        radius = int(step / 70 * 1400)
        weight = 1 - step / 70
        draw.ellipse(
            [1350 - radius, 120 - radius, 1350 + radius, 120 + radius],
            fill=(int(46 * weight + 8), int(26 * weight + 6), int(12 * weight + 5)),
        )
    base = base.filter(ImageFilter.GaussianBlur(90))

    random.seed(BACKDROP_SEED)
    bulbs = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bulb_draw = ImageDraw.Draw(bulbs)
    for _ in range(26):
        x, y = random.randint(0, WIDTH), random.randint(0, int(HEIGHT * 0.8))
        radius = random.randint(18, 70)
        warmth = random.randint(150, 255)
        bulb_draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=(warmth, int(warmth * 0.62), int(warmth * 0.28), random.randint(26, 74)),
        )
    bulbs = bulbs.filter(ImageFilter.GaussianBlur(BACKDROP_BOKEH))

    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(base.convert("RGBA"), bulbs).convert("RGB").save(destination)
    return destination


def caption_path(text: str) -> Path:
    """Render one step caption, on its scrim, to a full-width transparent PNG.

    Drawn rather than drawn-on: this ffmpeg has no `drawtext` filter at all
    (no libfreetype in the build), and a caption that only renders on some
    machines is worse than none.

    The band is the whole frame width so the gradient under the type has room
    to reach nothing at its top edge. Without it the caption lands on top of
    her own copy — white type on white type, which no drop shadow saves.
    """
    safe = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]
    destination = RAW_DIR / f"caption-{safe}.png"
    if destination.is_file():
        return destination

    from PIL import Image, ImageDraw, ImageFont

    font = None
    for candidate in CAPTION_FONTS:
        if Path(candidate).is_file():
            font = ImageFont.truetype(candidate, CAPTION_SIZE)
            break
    if font is None:
        raise RuntimeError(
            "no bold font found for the captions. Tried:\n        "
            + "\n        ".join(CAPTION_FONTS)
        )

    scratch = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    left, top, right, bottom = scratch.textbbox((0, 0), text, font=font)
    text_height = bottom - top

    band = Image.new("RGBA", (WIDTH, CAPTION_BAND_HEIGHT), (0, 0, 0, 0))

    # The scrim: opaque at the bottom of the frame, gone by the top of the
    # band, squared so it falls away quickly rather than greying half the shot.
    scrim = Image.new("L", (1, CAPTION_BAND_HEIGHT))
    for y in range(CAPTION_BAND_HEIGHT):
        down = y / (CAPTION_BAND_HEIGHT - 1)
        scrim.putpixel((0, y), int(CAPTION_SCRIM_ALPHA * 255 * down * down))
    band.paste(
        Image.new("RGBA", (WIDTH, CAPTION_BAND_HEIGHT), (0, 0, 0, 255)),
        (0, 0),
        scrim.resize((WIDTH, CAPTION_BAND_HEIGHT)),
    )

    draw = ImageDraw.Draw(band)
    baseline = CAPTION_BAND_HEIGHT - CAPTION_MARGIN[1] - text_height
    origin = (CAPTION_MARGIN[0] - left, baseline - top)
    # Still a shadow under the type: the scrim darkens, it does not flatten.
    draw.text((origin[0] + 3, origin[1] + 3), text, font=font, fill=(0, 0, 0, 200))
    draw.text(origin, text, font=font, fill=(255, 255, 255, 255))

    destination.parent.mkdir(parents=True, exist_ok=True)
    band.save(destination)
    return destination


def smoothstep(progress: str) -> str:
    """3p²-2p³ — the ease that stops a move starting and stopping with a jerk."""
    return f"({progress}*{progress}*(3-2*{progress}))"


def punch_in(seconds: float, focus: List[float]) -> str:
    """A zoompan that eases into a point and then holds there.

    `focus` is (x, y, zoom) in fractions of the phone screen. It is converted
    to the composed frame here, because the phone's size and position on that
    frame are known only to this module.

    The move is over in PUNCH_IN_SECONDS; the rest of the beat is the hold,
    which is the part that has to stay still long enough to read on a phone.
    """
    frames = max(2, int(round(seconds * FPS)))
    move_frames = max(1, int(round(min(PUNCH_IN_SECONDS, seconds * 0.35) * FPS)))
    rest_frames = max(0, int(round(min(PRE_HOLD_SECONDS, seconds * 0.25) * FPS)))
    # Clamped at both ends: flat through the rest at the front, flat again
    # through the hold at the back, eased only in between.
    progress = f"min(max((on-{rest_frames})/{move_frames},0),1)"
    eased = smoothstep(progress)

    focus_x, focus_y, zoom = focus
    # The phone is centred, PHONE_HEIGHT tall. A point on its screen maps onto
    # the frame through where the phone actually sits.
    phone_top = (HEIGHT - PHONE_HEIGHT) / 2
    target_x = 0.5                                   # the phone is horizontally centred
    target_y = (phone_top + focus_y * PHONE_HEIGHT) / HEIGHT
    # A touch of horizontal drift toward the focus, so the move is not purely
    # a dolly — it reads as a camera finding the thing.
    target_x = 0.5 + (focus_x - 0.5) * 0.35

    zoom_expr = f"1+{zoom - 1:.4f}*{eased}"
    # zoompan's x/y are the top-left of the crop, in input pixels.
    x_expr = f"(iw*({0.5:.4f}+({target_x:.4f}-0.5)*{eased}))-(iw/zoom/2)"
    y_expr = f"(ih*({0.5:.4f}+({target_y:.4f}-0.5)*{eased}))-(ih/zoom/2)"
    return (
        f"zoompan=z='{zoom_expr}':d={frames}"
        f":x='{x_expr}':y='{y_expr}'"
        f":s={WIDTH}x{HEIGHT}:fps={FPS}"
    )


def caption_overlay(caption_png: Path, seconds: float) -> Tuple[List[str], str]:
    """Extra ffmpeg input and filter for a caption that fades in and out."""
    hold_out = max(seconds - CAPTION_FADE, CAPTION_FADE)
    inputs = ["-loop", "1", "-t", f"{seconds:.3f}", "-i", str(caption_png)]
    chain = (
        f"format=rgba,"
        f"fade=t=in:st=0:d={CAPTION_FADE}:alpha=1,"
        f"fade=t=out:st={hold_out:.3f}:d={CAPTION_FADE}:alpha=1"
    )
    return inputs, chain


def phone_on_backdrop(screen_label: str, out_label: str) -> str:
    """Filter chain: a screen becomes a tilted, shadowed phone on the backdrop.

    The shadow is the phone's own silhouette — split, blackened, blurred and
    offset — rather than a drawn rectangle, so it follows the tilt for free.
    """
    return (
        f"[{screen_label}]format=rgba,{rounded_alpha(PHONE_RADIUS)},{PHONE_TILT}[phone];"
        f"[phone]split=2[ph][shadowsrc];"
        f"[shadowsrc]format=rgba,colorchannelmixer=rr=0:gg=0:bb=0:aa={SHADOW_ALPHA},"
        f"gblur=sigma={SHADOW_BLUR}[shadow];"
        f"[bg][shadow]overlay=(W-w)/2+{SHADOW_OFFSET[0]}:(H-h)/2+{SHADOW_OFFSET[1]}[shaded];"
        f"[shaded][ph]overlay=(W-w)/2:(H-h)/2[{out_label}]"
    )


def build_still_beat(still: Dict, seconds: float, out: Path) -> None:
    """One /create screenshot: phone on the backdrop, punched into its focus."""
    source = ASSETS_DIR / still["file"]
    focus = still.get("focus") or [0.5, 0.5, 1.6]
    caption = still.get("caption")

    inputs = [
        "-loop", "1", "-t", f"{seconds:.3f}", "-i", str(source),
        "-loop", "1", "-t", f"{seconds:.3f}", "-i", str(backdrop_path()),
    ]
    graph = (
        f"[1:v]format=rgba[bg];"
        f"[0:v]crop=iw:ih*{1 - STATUS_BAR_FRACTION - NAV_BAR_FRACTION}"
        f":0:ih*{STATUS_BAR_FRACTION},scale=-2:{PHONE_HEIGHT}[screen];"
        + phone_on_backdrop("screen", "composed") + ";"
        f"[composed]{punch_in(seconds, focus)}[moved]"
    )

    if caption:
        caption_inputs, caption_chain = caption_overlay(caption_path(caption), seconds)
        inputs += caption_inputs
        graph += (
            f";[2:v]{caption_chain}[cap];"
            f"[moved][cap]overlay=0:H-h[withcap];"
            f"[withcap]format=yuv420p[out]"
        )
    else:
        graph += ";[moved]format=yuv420p[out]"

    run_quiet(
        ["ffmpeg", "-y", "-loglevel", "error"] + inputs
        + ["-filter_complex", graph, "-map", "[out]", "-an", "-t", f"{seconds:.3f}"]
        + INTERMEDIATE_ARGS + [str(out)]
    )


def build_phone_stills(stills: List[Dict], seconds: float, out: Path) -> None:
    """Beat 2: her /create screenshots, each punched into and held.

    Built one still at a time and joined, rather than as one enormous filter
    graph: a graph with five zoompans and four transitions in it is both
    unreadable and, on some ffmpeg builds, unrunnable.
    """
    if not stills:
        raise RuntimeError("no stills to build beat 2 from")

    # The transition eats time from both neighbours, so each piece runs longer
    # than its share of the beat.
    transition = TRANSITION_SECONDS
    each = (seconds + transition * (len(stills) - 1)) / len(stills)
    hold = each - PRE_HOLD_SECONDS - PUNCH_IN_SECONDS
    if hold < MIN_HOLD_SECONDS:
        print(f"      note: {hold:.1f}s hold per still, under the {MIN_HOLD_SECONDS}s "
              f"that reads comfortably on a phone")

    pieces: List[Path] = []
    for index, still in enumerate(stills):
        piece = out.with_name(f"{out.stem}-{index}.mp4")
        build_still_beat(still, each, piece)
        pieces.append(piece)

    crossfade_concat(pieces, out, transition, transition_name=STILL_TRANSITION)
    for piece in pieces:
        piece.unlink(missing_ok=True)


def build_phone_recording(recording: Path, max_speed: float, seconds: float, out: Path,
                          top_crop: float = RECORDING_TOP_FRACTION,
                          caption: str = "") -> None:
    """Beat 3: her site recording, in the same phone, fitted to its slot.

    The speed-up is computed from the slot rather than fixed, so the beat
    always fills its share instead of running out and freezing on the last
    frame — which is what a hard-coded 1.8x did the first time this ran.
    """
    source_length = duration_of(recording)
    wanted = source_length / max(seconds, 0.1)
    speed = min(max(wanted, MIN_SPEED), min(max_speed, MAX_SPEED))
    take = min(seconds, source_length / speed)
    print(f"      {source_length:.1f}s recording at {speed:.2f}x → {take:.1f}s")

    inputs = [
        "-i", str(recording),
        "-loop", "1", "-t", f"{take:.3f}", "-i", str(backdrop_path()),
    ]
    graph = (
        f"[1:v]format=rgba[bg];"
        f"[0:v]setpts=PTS/{speed},fps={FPS},"
        f"crop=iw:ih*{1 - top_crop - NAV_BAR_FRACTION}:0:ih*{top_crop},"
        f"scale=-2:{PHONE_HEIGHT}[screen];"
        + phone_on_backdrop("screen", "composed")
    )

    if caption:
        caption_inputs, caption_chain = caption_overlay(caption_path(caption), take)
        inputs += caption_inputs
        graph += (
            f";[2:v]{caption_chain}[cap];"
            f"[composed][cap]overlay=0:H-h:shortest=1[withcap];"
            f"[withcap]format=yuv420p[out]"
        )
    else:
        graph += ";[composed]format=yuv420p[out]"

    run_quiet(
        ["ffmpeg", "-y", "-loglevel", "error"] + inputs
        + ["-filter_complex", graph, "-map", "[out]", "-an", "-t", f"{take:.3f}"]
        + INTERMEDIATE_ARGS + [str(out)]
    )


def build_site_fullframe(recording: Path, start: float, seconds: float, out: Path,
                         crop_y: float = SITE_CROP_Y) -> None:
    """The closing beat: her site filling the frame, sharp, barely moving.

    A portrait capture keeps under half its height in a 16:9 frame, so where
    that band sits is the whole composition. Centred it lands mid-headline and
    loses both the Halal badge above and the rule below; `crop_y` pulls it up
    to the top of her hero, which is the shot worth ending on.
    """
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(recording),
        "-an", "-t", f"{seconds:.3f}",
        "-vf",
        # The right edge of the capture carries a sliver of scrollbar; it
        # reads as a white line down the side of an otherwise full-bleed shot.
        f"crop=iw*{1 - SITE_SIDE_TRIM}:ih*{1 - RECORDING_TOP_FRACTION - NAV_BAR_FRACTION}"
        f":0:ih*{RECORDING_TOP_FRACTION},"
        f"scale={WIDTH}:-2,"
        f"crop={WIDTH}:{HEIGHT}:0:(ih-{HEIGHT})*{crop_y},"
        f"fps={FPS},unsharp=5:5:0.8,format=yuv420p",
    ] + INTERMEDIATE_ARGS + [str(out)])


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def crossfade_concat(clips: List[Path], out: Path, crossfade: float,
                     crf: int = ENCODE_CRF, faststart: bool = False,
                     transition_name: str = BEAT_TRANSITION) -> None:
    """Cross-fade a list of clips into one.

    Nothing may sit between an input and its xfade: putting scale, fps or even
    setpts in front drops the frame rate from the filter link and xfade rejects
    the whole graph with "current rate of 1/0 is invalid". Everything is
    normalised when each clip is written, so the inputs already match here.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(clips) == 1:
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
            f"[{previous}][{index}:v]xfade=transition={transition_name}:duration={crossfade}"
            f":offset={running - crossfade:.3f}[{label}]"
        )
        running = running + duration_of(clips[index]) - crossfade
        previous = label

    encode = ["-c:v", "libx264", "-crf", str(crf), "-preset", "slow", "-pix_fmt", "yuv420p",
              "-video_track_timescale", str(FPS * 512), "-r", str(FPS)]
    if faststart:
        encode += ["-movflags", "+faststart"]

    command += ["-filter_complex", ";".join(steps), "-map", f"[{previous}]", "-an"]
    command += encode + [str(out)]
    run_quiet(command)


def plan_durations(ai_lengths: Dict[str, float], target: float, crossfade: float,
                   shot_names: List[str], fixed: Dict[str, float]) -> Dict[str, float]:
    """Work out how long each ffmpeg beat runs so the film lands on `target`.

    Cross-fades overlap, so the pieces have to add up to more than the finished
    length. Whatever the AI beats actually came back as is measured, not
    assumed — a provider that returns 5.2s where 5 was asked for would
    otherwise push the whole film long.
    """
    raw_needed = target + crossfade * (len(shot_names) - 1)
    spoken_for = sum(ai_lengths.values()) + sum(fixed.values())
    flexible = [n for n in shot_names if n not in ai_lengths and n not in fixed]
    remaining = raw_needed - spoken_for

    if not flexible:
        return dict(fixed)
    if remaining < 1.5 * len(flexible):
        raise RuntimeError(
            f"no room left for the merchant's footage: the fixed beats already fill "
            f"{spoken_for:.1f}s of the {raw_needed:.1f}s needed for a {target:.0f}s film.\n"
            f"      Use --ai-seconds 5, or raise --total."
        )

    # Her /create flow carries more material than the site scroll, so it gets
    # the larger share of whatever is left.
    weights = {name: (0.6 if "create" in name else 0.4) for name in flexible}
    total_weight = sum(weights.values())
    plan = dict(fixed)
    for name in flexible:
        plan[name] = remaining * weights[name] / total_weight
    return plan


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Build the 20-second "how it works" film.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ai-seconds", type=int, choices=(5, 10), default=5,
                        help="length of each AI beat; the provider allows 5 or 10")
    parser.add_argument("--total", type=float, default=None,
                        help="finished length in seconds (default: from the shot plan)")
    parser.add_argument("--stills-only", action="store_true",
                        help="build only the beats made from the merchant's own footage — "
                             "no API key needed, nothing spent")
    parser.add_argument("--dry-run", action="store_true", help="print the plan; call nothing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / "backend" / ".env")

    plan = load_plan()
    shots = plan["shots"]
    timing = plan.get("timing", {})
    target = args.total if args.total else float(timing.get("target_total_seconds", 20.0))
    crossfade = float(timing.get("crossfade_seconds", 0.6))
    names = list(shots)

    print(f"\n{plan['merchant']['name']} — {target:.0f}s, {len(names)} beats, "
          f"{crossfade}s cross-fades")
    for name in names:
        shot = shots[name]
        source = "AI" if shot["kind"] == "ai" else "her own footage"
        print(f"  {name:16} {shot['title']}  ({source})")

    if args.dry_run:
        print(f"\n--dry-run: nothing submitted. Models, in order: "
              f"{', '.join(video_models())}\n")
        for name in names:
            if shots[name]["kind"] == "ai":
                print(f"  {name}:\n    {shots[name]['prompt']}\n")
        return 0

    require_tool("ffmpeg")
    require_tool("ffprobe")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # plan_durations is always given the whole film's beat list, even when only
    # some of them are rendered: cutting the AI beats out of the arithmetic too
    # would stretch her footage across their slots, and the preview would be
    # paced nothing like the film that gets paid for.
    all_names = list(names)
    ai_names = [n for n in names if shots[n]["kind"] == "ai"]
    reserved: Dict[str, float] = {}
    if args.stills_only:
        reserved = {name: float(args.ai_seconds) for name in ai_names}
        names = [n for n in names if n not in ai_names]
        ai_names = []
        print(f"\n--stills-only: the AI beats are skipped, nothing will be spent.\n"
              f"  Their slots are still reserved at {args.ai_seconds}s each, so every "
              f"beat below runs\n  exactly as long as it will in the finished film.")
    else:
        api_key()  # fail now, not after the first beat renders

    # --- the AI beats first: their real lengths decide everyone else's ---
    ai_lengths: Dict[str, float] = {}
    if ai_names:
        with httpx.Client() as client:
            for name in ai_names:
                print(f"\n[{name}] {shots[name]['title']}")
                clip = RAW_DIR / f"{name}.mp4"
                try:
                    build_ai_shot(client, shots[name]["prompt"], args.ai_seconds, clip)
                except Exception as exc:
                    print(f"      FAILED: {exc}")
                    return 1
                ai_lengths[name] = duration_of(clip)
                print(f"      {ai_lengths[name]:.1f}s")

    fixed = {
        name: float(shots[name]["seconds"])
        for name in all_names
        if shots[name]["kind"] == "site_fullframe"
    }
    try:
        lengths = plan_durations({**ai_lengths, **reserved}, target, crossfade,
                                 all_names, fixed)
    except RuntimeError as exc:
        print(f"\n{exc}\n")
        return 1

    # --- then her footage, stretched to fill exactly what is left ---
    for name in names:
        if name in ai_lengths:
            continue
        shot = shots[name]
        clip = RAW_DIR / f"{name}.mp4"
        seconds = lengths[name]
        print(f"\n[{name}] {shot['title']} — {seconds:.1f}s")

        if shot["kind"] == "phone_stills":
            build_phone_stills(shot["stills"], seconds, clip)
        elif shot["kind"] == "phone_recording":
            build_phone_recording(
                ASSETS_DIR / shot["recording"], float(shot["speed"]), seconds, clip,
                top_crop=float(shot.get("top_crop", RECORDING_TOP_FRACTION)),
                caption=shot.get("caption", ""),
            )
        elif shot["kind"] == "site_fullframe":
            build_site_fullframe(
                ASSETS_DIR / shot["recording"], float(shot["from_seconds"]), seconds, clip,
                crop_y=float(shot.get("crop_y", SITE_CROP_Y)),
            )
        else:
            raise RuntimeError(f"unknown shot kind: {shot['kind']}")
        print(f"      {duration_of(clip):.1f}s")

    ordered = [RAW_DIR / f"{n}.mp4" for n in names]
    missing = [c for c in ordered if not c.is_file()]
    if missing:
        print(f"\nMissing beats: {', '.join(c.name for c in missing)}\n")
        return 1

    print("\nCutting them together")
    crossfade_concat(ordered, OUT_VIDEO, crossfade, faststart=True)
    length = duration_of(OUT_VIDEO)
    size = OUT_VIDEO.stat().st_size
    make_poster(OUT_VIDEO, OUT_POSTER, at=min(1.0, length / 4))

    print(f"      → {OUT_VIDEO.relative_to(REPO_ROOT)}  {length:.2f}s  {size / 1e6:.2f} MB")
    print(f"      → {OUT_POSTER.relative_to(REPO_ROOT)}")
    if args.stills_only:
        print(f"      note: {length:.2f}s — the two AI beats are missing; with them "
              f"this is a {target:.0f}s film")
    elif abs(length - target) > 0.3:
        print(f"      note: {length:.2f}s against a {target:.0f}s target")
    if size > SIZE_BUDGET_BYTES:
        print(f"      note: over the {SIZE_BUDGET_BYTES / 1e6:.0f} MB budget")
    print("\nNext: cd frontend && npm run build, look at the section, then commit.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
