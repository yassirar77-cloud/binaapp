#!/usr/bin/env python3
"""Build the 20-second "how it works" film that sits under the landing hero.

Four shots of five seconds each, joined with zoom transitions:

    1. she has the idea, phone in hand          generated  (text-to-video)
    2. her real /create brief, on that phone    composited (ffmpeg)
    3. her finished site, on that phone         composited (ffmpeg)
    4. she shows it to a customer               generated  (text-to-video)
       then a one-second hold on the last frame

Only the two shots with a person in them are generated. Shots 2 and 3 are
built here, from a frame drawn with PIL: her own captures, at full resolution,
on a 9:19.5 phone standing in the blurred dark of a steakhouse. They cost
nothing and their text is pin-sharp, which is the point — this was tried
through wan3.0 first and the model redrew the interface into letter-shaped
noise, because a video model redraws every frame it is given, including the
one it was handed.

Shot 3 goes further: the hero clip playing on the merchant's live site is
scraped from the page (`find_live_hero_video`, the same marker the showcase
builder uses), darkened to match her site's scrim, and composited into the
hero block of the phone screen — behind her headline, which is held out of it
by a mask built from the capture's own luma. So the flames move while every
word stays exactly as she published it.

The two generated shots go to DashScope. Models are tried in order until one
accepts: wan3.0-video, then happyhorse-1.1-t2v. A model the account does not
have is rejected at submit, and a rejected submit is not billed, so walking the
list costs nothing.

The film's own length is arithmetic, not a target to hit: four five-second
shots, three overlapping transitions and a tail hold come to about 19.5s.

Usage
-----
    python3 scripts/generate_howitworks_video.py --dry-run   # frames + prompts, no spend
    python3 scripts/generate_howitworks_video.py             # two billable shots
    python3 scripts/generate_howitworks_video.py --only 2-create,3-site   # free

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
FRAME_PHONE_BEZEL = 15
FRAME_SCREEN_RADIUS = 44
FRAME_BODY_RADIUS = 58
FRAME_PHONE_TILT = -4.0       # degrees; negative leans the top to the right
FRAME_SHADOW_OFFSET = (18, 34)
FRAME_SHADOW_BLUR = 34
FRAME_SHADOW_ALPHA = 205
BACKDROP_SEED = 11
BACKDROP_BOKEH = 40

#: A modern phone screen, 9:19.5. No single capture is that shape — hers are
#: about 0.63 wide-to-tall, and cropping the browser chrome off the top makes
#: them squarer still, not slimmer. Their content also runs to within 4% of
#: each side edge, so there is no margin to cut a 0.46 screen out of. The glass
#: is therefore filled by stacking more than one of her captures (see
#: `compose_screen`) and trimming the stack to shape. Padding remains only as
#: the fallback for a stack that still comes up short, and `pad_blend` feathers
#: its joins for an edge that is not flat.
FRAME_SCREEN_RATIO = 9 / 19.5
FRAME_PAD_SAMPLE_ROWS = 14
FRAME_PAD_BLEND = 72

#: How much of the frame's height the phone takes up, measured after the tilt.
#: Below 1.0 so the phone sits in the shot rather than running off both edges.
FRAME_PHONE_FRACTION = 0.85


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
    """The merchant's own room, thrown well out of focus.

    A modern steakhouse rather than a bright kedai: matte black and dark wood,
    Edison bulbs hanging warm, the open grill glowing low and off to one side,
    a leather booth and a couple of blurred diners. It is drawn to the same
    palette her website uses — near-black with orange — so the two composited
    shots sit in the same room as the two generated ones instead of announcing
    themselves as a different production.

    Everything is drawn, then blurred past recognition, then given its
    highlights back on top: blurring a bulb along with everything else just
    makes a smudge, so the bulbs go on after the blur and keep their shape.
    """
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

    rng = random.Random(seed)
    image = Image.new("RGB", (WIDTH, HEIGHT), (12, 8, 6))
    draw = ImageDraw.Draw(image)

    # The room falls away to black at the top; the warmth lives low, where the
    # grill and the table lamps are.
    for y in range(HEIGHT):
        down = (y / (HEIGHT - 1)) ** 1.3
        draw.line([(0, y), (WIDTH, y)],
                  fill=(int(10 + 46 * down), int(6 + 24 * down), int(5 + 13 * down)))

    # Dark wood panelling: vertical boards, barely separable once blurred.
    for i in range(14):
        x = WIDTH * i / 14
        shade = 26 + rng.randrange(0, 16)
        draw.rectangle([x, 0, x + WIDTH / 28, HEIGHT], fill=(shade, shade - 9, shade - 14))

    # The open grill: a low bed of fire off to the right, broken into a few
    # overlapping pools rather than drawn as one shape. A single ellipse
    # survives the blur as a single ellipse, and reads as a glowing oval
    # pasted on the wall instead of as fire.
    draw.rectangle([WIDTH * 0.50, HEIGHT * 0.30, WIDTH * 0.98, HEIGHT * 0.44],
                   fill=(34, 24, 20))
    for fx, fy, rx, ry, tint in (
        (0.60, 0.615, 0.10, 0.045, (120, 46, 12)),
        (0.72, 0.600, 0.13, 0.052, (146, 58, 15)),
        (0.85, 0.625, 0.10, 0.042, (118, 44, 11)),
        (0.69, 0.608, 0.07, 0.030, (168, 74, 20)),
        (0.80, 0.612, 0.05, 0.024, (160, 68, 18)),
    ):
        draw.ellipse([WIDTH * (fx - rx), HEIGHT * (fy - ry),
                      WIDTH * (fx + rx), HEIGHT * (fy + ry)], fill=tint)

    # A leather booth along the left, and two diners in it.
    draw.rounded_rectangle([WIDTH * -0.05, HEIGHT * 0.46, WIDTH * 0.34, HEIGHT * 1.05],
                           radius=120, fill=(42, 24, 17))
    for left, top, right, bottom in (
        (0.03, 0.54, 0.14, 0.95),
        (0.17, 0.58, 0.28, 0.95),
    ):
        draw.rounded_rectangle(
            [WIDTH * left, HEIGHT * top, WIDTH * right, HEIGHT * bottom],
            radius=90, fill=(30, 19, 15),
        )

    image = image.filter(ImageFilter.GaussianBlur(46))

    # Edison bulbs: few, warm, hung at different depths. Amber only — this room
    # has one colour of light in it.
    bulbs = [(0.12, 0.18, 30), (0.27, 0.11, 22), (0.44, 0.22, 26), (0.63, 0.14, 20),
             (0.79, 0.20, 28), (0.91, 0.09, 18), (0.36, 0.34, 16), (0.70, 0.31, 15)]
    for fx, fy, radius in bulbs:
        x, y = WIDTH * fx, HEIGHT * fy
        for scale, alpha, tint in ((5.5, 46, (196, 104, 34)),
                                   (2.2, 104, (240, 158, 66)),
                                   (1.0, 224, (255, 214, 150))):
            glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            size = radius * scale
            ImageDraw.Draw(glow).ellipse([x - size, y - size, x + size, y + size],
                                         fill=tint + (alpha,))
            image = Image.alpha_composite(
                image.convert("RGBA"),
                glow.filter(ImageFilter.GaussianBlur(size * 0.5)),
            ).convert("RGB")

    # Embers over the grill, and the flame-light bouncing off the hood.
    for _ in range(BACKDROP_BOKEH):
        x = rng.uniform(WIDTH * 0.48, WIDTH)
        y = rng.uniform(HEIGHT * 0.34, HEIGHT * 0.76)
        radius = rng.uniform(10, 46)
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill=(255, rng.randrange(110, 170), 48, rng.randrange(40, 110)),
        )
        image = Image.alpha_composite(
            image.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(radius * 0.8))
        ).convert("RGB")

    image = image.filter(ImageFilter.GaussianBlur(18))
    return ImageEnhance.Color(image).enhance(1.12)


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


def redact(screen, box: Dict) -> None:
    """Paint out part of the capture, in place, with its own background colour.

    The /create page carries the merchant's login: a session badge, a log-out
    button and her username sit along the right of the app header. Cropping the
    header would take the BinaApp logo with it, so the right of the strip is
    filled with the page background sampled from beside the logo instead. The
    fill is feathered, because a hard-edged rectangle over a UI reads as a
    rectangle over a UI.
    """
    from PIL import Image, ImageDraw, ImageFilter

    left, top, right, bottom = box["box"]
    x0, y0 = int(screen.width * left), int(screen.height * top)
    x1, y1 = int(screen.width * right), int(screen.height * bottom)
    if x1 <= x0 or y1 <= y0:
        return

    sample_x, sample_y = box.get("sample", [0.02, 0.5])
    colour = screen.getpixel(
        (min(int(screen.width * sample_x), screen.width - 1),
         min(int(screen.height * sample_y), screen.height - 1))
    )

    feather = int(box.get("feather", 10))
    patch = Image.new("RGBA", screen.size, colour + (0,))
    mask = Image.new("L", screen.size, 0)
    ImageDraw.Draw(mask).rectangle([x0, y0, x1, y1], fill=255)
    patch.putalpha(mask.filter(ImageFilter.GaussianBlur(feather)))
    screen.paste(patch, (0, 0), patch)


def pad_to_screen_ratio(screen, split: List[float]):
    """Grow the capture to FRAME_SCREEN_RATIO by extending its own edges.

    Padding rather than cropping is not a preference. The captures are 0.63
    wide-to-tall and the content reaches within 4% of both side edges, so there
    is neither the shape nor the margin to cut a 0.46 screen out of them.
    Extending them with the colour of their own outermost rows costs nothing
    and, on a flat dark background, cannot be seen.
    """
    from PIL import Image

    target_height = round(screen.width / FRAME_SCREEN_RATIO)
    extra = target_height - screen.height
    if extra <= 0:
        return screen

    weight = (split[0] + split[1]) or 1
    above = round(extra * split[0] / weight)
    below = extra - above

    def edge_colour(from_top: bool):
        rows = min(FRAME_PAD_SAMPLE_ROWS, screen.height)
        strip = screen.crop(
            (0, 0, screen.width, rows) if from_top
            else (0, screen.height - rows, screen.width, screen.height)
        )
        return strip.resize((1, 1), Image.BOX).getpixel((0, 0))

    padded = Image.new("RGB", (screen.width, target_height), edge_colour(True))
    if below:
        padded.paste(
            Image.new("RGB", (screen.width, below), edge_colour(False)),
            (0, target_height - below),
        )
    padded.paste(screen, (0, above))

    # Feather both joins. On these captures the edges are flat and there is
    # nothing to hide; on one whose edge lands mid-photograph, this is what
    # keeps the seam from being a line.
    blend = min(FRAME_PAD_BLEND, screen.height // 4)
    for edge_top, colour, start in (
        (True, edge_colour(True), above),
        (False, edge_colour(False), above + screen.height - blend),
    ):
        if (edge_top and not above) or (not edge_top and not below):
            continue
        for step in range(blend):
            alpha = 1 - step / blend if edge_top else step / blend
            y = start + step
            line = Image.new("RGB", (screen.width, 1), colour)
            padded.paste(
                Image.blend(padded.crop((0, y, screen.width, y + 1)), line, alpha),
                (0, y),
            )

    return padded


def layer_image(layer: Dict):
    """One capture, cropped to the part of it that belongs on screen."""
    screen = screen_image(layer)
    top = float(layer.get("top_crop", 0.0))
    bottom = float(layer.get("bottom_crop", 0.0))
    screen = screen.crop(
        (0, int(screen.height * top), screen.width, int(screen.height * (1 - bottom)))
    )
    for box in layer.get("redact", []):
        redact(screen, box)
    return screen


def compose_screen(spec: Dict):
    """Stack the merchant's captures into one full 9:19.5 screen.

    A single capture cannot fill a phone-shaped screen: they are about 0.63
    wide-to-tall and a screen is 0.46, so one of them leaves 40% of the glass
    empty. Padding that gap was honest but it looked like what it was. So the
    screen is built from more than one of her captures instead — the brief and
    then the page below it, her hero and then her menu — each cropped below its
    own header so the app's chrome is not repeated, and the stack trimmed to
    the screen's shape.

    Nothing here is drawn: every pixel on the glass is hers.
    """
    from PIL import Image

    layers = spec.get("layers") or [spec]
    parts = [layer_image(layer) for layer in layers]

    width = parts[0].width
    if any(part.width != width for part in parts):
        parts = [
            part if part.width == width
            else part.resize((width, round(part.height * width / part.width)), Image.LANCZOS)
            for part in parts
        ]

    if len(parts) == 1:
        stack = parts[0]
    else:
        stack = Image.new("RGB", (width, sum(p.height for p in parts)))
        y = 0
        for part in parts:
            stack.paste(part, (0, y))
            y += part.height

    target = round(width / FRAME_SCREEN_RATIO)
    if stack.height < target:
        # Not enough of her own page to fill the glass. Extend the edges rather
        # than invent UI; on a flat dark background the join cannot be seen.
        return pad_to_screen_ratio(stack, spec.get("pad_split", [0.3, 0.7]))

    focus = float(spec.get("stack_focus", 0.0))
    y0 = round((stack.height - target) * min(max(focus, 0.0), 1.0))
    return stack.crop((0, y0, width, y0 + target))


def phone_body(screen, height: int, tilt: float):
    """The screen, given a bezel, rounded, and turned by `tilt` degrees."""
    from PIL import Image

    width = max(2, round(screen.width * height / screen.height))
    glass = _rounded(screen.resize((width, height), Image.LANCZOS), FRAME_SCREEN_RADIUS)

    bezel = FRAME_PHONE_BEZEL
    body = _rounded(
        Image.new("RGBA", (width + bezel * 2, height + bezel * 2), (16, 16, 19, 255)),
        FRAME_BODY_RADIUS,
    )
    body.paste(glass, (bezel, bezel), glass)
    return body.rotate(tilt, resample=Image.BICUBIC, expand=True)


def hero_placement(spec: Dict, screen, screen_height: int, tilt: float,
                   body_size: Tuple[int, int], origin: Tuple[int, int],
                   frame_out: Path) -> Dict:
    """Where her hero block lands in the finished frame, and the patch to mask with.

    Shot 3 plays her live hero clip inside the phone. The clip has to be put
    there in ffmpeg, frame by frame, but only this function knows where "there"
    is: the phone is built here, tilted here, and placed here. So the geometry
    is computed once and written out beside the PNG.

    The tilt is a plain rotation, not a perspective, so the hero block stays a
    rectangle — it only turns. That is why ffmpeg can place it with `rotate` and
    an overlay rather than a four-corner warp.
    """
    from PIL import Image
    import math

    hero = spec.get("hero_video")
    if not hero:
        return {}

    top, bottom = hero.get("box", [0.076, 0.34])
    width = max(2, round(screen.width * screen_height / screen.height))
    scaled = screen.resize((width, screen_height), Image.LANCZOS)

    y0, y1 = round(screen_height * top), round(screen_height * bottom)
    patch = scaled.crop((0, y0, width, y1))
    patch_path = frame_out.with_name(frame_out.stem + "-hero.png")
    patch.save(patch_path)

    # The patch's centre, as an offset from the centre of the untilted body.
    bezel = FRAME_PHONE_BEZEL
    dx = 0.0
    dy = (bezel + (y0 + y1) / 2) - (screen_height + bezel * 2) / 2

    # PIL rotates counter-clockwise for a positive angle, with y pointing down.
    theta = math.radians(tilt)
    rotated_dx = dx * math.cos(theta) + dy * math.sin(theta)
    rotated_dy = -dx * math.sin(theta) + dy * math.cos(theta)

    return {
        "patch": patch_path.name,
        "size": [patch.width, patch.height],
        "center": [
            round(origin[0] + body_size[0] / 2 + rotated_dx, 2),
            round(origin[1] + body_size[1] / 2 + rotated_dy, 2),
        ],
        # ffmpeg's `rotate` turns clockwise for a positive angle; PIL's turns
        # the other way, so the sign flips on the way across.
        "rotate_radians": round(-theta, 6),
        "darken": hero.get("darken", 0.66),
        "keep_text_from": hero.get("keep_text_from", 100),
        "keep_text_to": hero.get("keep_text_to", 150),
    }


def build_first_frame(spec: Dict, out: Path) -> Path:
    """Draw the frame shots 2 and 3 start from, and save it as a PNG.

    A phone standing in the warm blur of her kedai, her own screenshot on the
    glass at full resolution. No hand: drawn fingers against a photographic
    backdrop read as clip art, and the model animates a drawn hand as a
    drawn hand. The phone is tilted and shadowed instead, which is a shot a
    camera could have taken.
    """
    from PIL import Image, ImageFilter

    screen = compose_screen(spec)
    tilt = float(spec.get("tilt", FRAME_PHONE_TILT))

    # The phone is sized by what it measures once it has been turned, not by
    # what it measured before. A rotation with expand=True grows the box by
    # both the height and the width of what is inside it, so a body built to
    # 85% of the frame comes out taller than 85% — which is how the last pass
    # ended up touching the top and bottom edges. Build once, measure, scale
    # the screen by what was actually wrong, build again.
    want = FRAME_PHONE_FRACTION * HEIGHT
    height = int(spec.get("screen_height", round(want)))
    for _ in range(2):
        body = phone_body(screen, height, tilt)
        if abs(body.height - want) <= 1:
            break
        height = max(64, round(height * want / body.height))

    offset_x, offset_y = spec.get("offset", [0.02, 0.0])
    x = int(WIDTH * (0.5 + float(offset_x)) - body.width / 2)
    y = int(HEIGHT * (0.5 + float(offset_y)) - body.height / 2)

    placement = hero_placement(spec, screen, height, tilt, body.size, (x, y), out)

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
    if placement:
        out.with_suffix(".hero.json").write_text(
            json.dumps(placement, indent=2), encoding="utf-8"
        )
    return out


# ---------------------------------------------------------------------------
# The clip already playing on her live site
# ---------------------------------------------------------------------------

#: The hero patcher writes `<video class="binaapp-hero-video" …><source src="…">`
#: into every generated site, so the clip is found by that class rather than by
#: guessing at the first <video> on the page. Same marker the showcase builder
#: uses to pull Wak Hassan's clip.
HERO_VIDEO_BLOCK = re.compile(
    r'<video[^>]*class="[^"]*binaapp-hero-video[^"]*"[^>]*>(.*?)</video>',
    re.IGNORECASE | re.DOTALL,
)
SOURCE_SRC = re.compile(r'<source[^>]*\bsrc="([^"]+)"', re.IGNORECASE)
ANY_MP4 = re.compile(r'https?://[^"\'<>\s]+\.mp4[^"\'<>\s]*', re.IGNORECASE)


def find_live_hero_video(client: httpx.Client, site: str) -> str:
    """The URL of the hero clip already playing on a live BinaApp site."""
    response = client.get(site, timeout=60, follow_redirects=True)
    response.raise_for_status()
    html = response.text

    block = HERO_VIDEO_BLOCK.search(html)
    if block:
        source = SOURCE_SRC.search(block.group(1))
        if source:
            return source.group(1)

    fallback = ANY_MP4.search(html)
    if fallback:
        print("      no binaapp-hero-video block — using the first MP4 on the page")
        return fallback.group(0)

    raise RuntimeError(f"no hero clip found on {site}")


def fetch_live_hero_video(client: httpx.Client, site: str) -> Path:
    """Download her site's hero clip once and keep it for later runs."""
    destination = RAW_DIR / "live-hero.mp4"
    if destination.is_file() and destination.stat().st_size > 0:
        print("      live hero clip already downloaded — reusing it")
        return destination

    url = find_live_hero_video(client, site)
    print(f"      {url}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    download(client, url, destination)
    return destination


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


def camera_move(seconds: float, move: Dict) -> str:
    """An eased push over a still frame. zoompan's floor is 1.0, so pushes only."""
    start = max(1.0, float(move.get("from", 1.0)))
    end = max(1.0, float(move.get("to", 1.16)))
    centre_x, centre_y = move.get("center", [0.5, 0.5])

    frames = max(2, int(round(seconds * FPS)))
    eased = smoothstep(f"min(on/{frames - 1},1)")
    x_expr = f"(iw*({0.5:.4f}+({float(centre_x):.4f}-0.5)*{eased}))-(iw/zoom/2)"
    y_expr = f"(ih*({0.5:.4f}+({float(centre_y):.4f}-0.5)*{eased}))-(ih/zoom/2)"
    return (
        f"zoompan=z='{start:.4f}+{end - start:.4f}*{eased}':d=1"
        f":x='{x_expr}':y='{y_expr}':s={WIDTH}x{HEIGHT}:fps={FPS}"
    )


def build_composite_shot(frame: Path, seconds: float, out: Path,
                         move: Dict = None, hero_clip: Path = None,
                         tail_push: Dict = None) -> None:
    """One shot built here rather than generated: the drawn frame, given motion.

    With `hero_clip`, her live site's hero video is played inside the phone.
    The clip goes down first and the capture goes on top of it, carrying an
    alpha built from its own luma — her headline, her Halal badge and her
    orange rule are the bright things in that block and the darkened
    photograph is everything else, so a ramp between two luma values separates
    them cleanly. The type therefore comes through untouched, at full
    resolution, with the fire moving behind it.
    """
    placement = {}
    hero_json = frame.with_suffix(".hero.json")
    if hero_clip and hero_json.is_file():
        placement = json.loads(hero_json.read_text(encoding="utf-8"))

    # -framerate, not just -loop: a looped image input is 25fps unless told
    # otherwise, so five seconds of it became 125 frames and the 30fps shot it
    # fed came out 4.2s long.
    still = ["-loop", "1", "-framerate", str(FPS), "-t", f"{seconds:.3f}", "-i"]
    inputs: List[str] = still + [str(frame)]
    steps: List[str] = []
    label = "0:v"

    if placement:
        patch = frame.with_name(placement["patch"])
        width, height = placement["size"]
        centre_x, centre_y = placement["center"]
        angle = placement["rotate_radians"]
        darken = float(placement["darken"])
        lo, hi = float(placement["keep_text_from"]), float(placement["keep_text_to"])

        inputs += ["-stream_loop", "-1", "-t", f"{seconds:.3f}", "-i", str(hero_clip)]
        inputs += still + [str(patch)]
        steps += [
            # Her site lays a dark scrim over this clip; the raw file has none,
            # so it is brought down to the capture's own level or the block
            # would light up brighter than the page around it.
            f"[1:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={FPS},lutyuv=y='val*{darken}',format=rgba[fire]",
            "[2:v]format=rgba,split=2[keep][luma]",
            f"[luma]format=gray,lutyuv=y='clip((val-{lo})*255/{max(hi - lo, 1):.1f},0,255)'[mask]",
            "[keep][mask]alphamerge[type]",
            "[fire][type]overlay=0:0[block]",
            # format=rgba before the turn, not just before the overlay: without
            # it the stream negotiates to YUV, `c=none` fills the corners with
            # Y=0,U=0,V=0, and that is bright green — which is exactly what
            # drew a dashed green line down two edges of the block.
            f"[block]format=rgba,rotate={angle}:c=none"
            f":ow=rotw({angle}):oh=roth({angle})[turned]",
            f"[0:v][turned]overlay=x={centre_x}-w/2:y={centre_y}-h/2[lit]",
        ]
        label = "lit"

    chain = camera_move(seconds, move or {})
    if tail_push:
        chain += "," + tail_push_filter(seconds, tail_push)
    steps.append(f"[{label}]{chain},format=yuv420p[out]")

    run_quiet(
        ["ffmpeg", "-y", "-loglevel", "error"] + inputs
        + ["-filter_complex", ";".join(steps), "-map", "[out]", "-an",
           "-t", f"{seconds:.3f}"]
        + INTERMEDIATE_ARGS + [str(out)]
    )


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
        description='Build the "how it works" film — two generated shots, two composited.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--seconds", type=int, choices=(5, 10), default=None,
                        help="length of each shot; the provider allows 5 or 10")
    parser.add_argument("--only", default="",
                        help="build only these shots, comma separated "
                             "(e.g. 1-idea,4-handover)")
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

    wanted = [n.strip() for n in args.only.split(",") if n.strip()]
    unknown = [n for n in wanted if n not in shots]
    if unknown:
        sys.exit(f"no shot named {', '.join(unknown)}. Have: {', '.join(shots)}")
    names = [n for n in shots if not wanted or n in wanted]

    generated = [n for n in names if shots[n].get("kind") == "text_to_video"]
    length = seconds * len(names) - transition * max(0, len(names) - 1) + tail_hold
    print(f"\n{plan['merchant']['name']} — {len(names)} shots of {seconds}s, "
          f"{transition}s {transition_name} transitions, {tail_hold}s tail hold "
          f"→ {length:.1f}s")
    for name in names:
        kind = ("generated" if shots[name].get("kind") == "text_to_video"
                else "composited here, free")
        print(f"  {name:12} {shots[name]['title']}  ({kind})")
    print(f"  {len(generated)} of {len(names)} shots are billable.")

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
        print(f"\n--{'dry-run' if args.dry_run else 'frames-only'}: nothing submitted, "
              f"nothing spent.")
        print(f"  A real run is {len(generated)} job(s), roughly "
              f"USD {len(generated) * ROUGH_COST_PER_SHOT_USD:.2f} at "
              f"~{ROUGH_COST_PER_SHOT_USD:.2f}/shot.")
        print(f"  Models, in order: {', '.join(video_models())}\n")
        for name in names:
            shot = shots[name]
            print(f"  ── {name} — {shot['title']}")
            if name in frames:
                print(f"     frame: {frames[name].relative_to(REPO_ROOT)}")
            if shot.get("kind") == "text_to_video":
                print(f"     {prompt_for(plan, shot)}\n")
            else:
                print("     composited here — no prompt, nothing sent\n")
        return 0

    if generated:
        api_key()  # fail now, not after the first shot renders
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        # Her live site's hero clip, for whichever shot plays it. Fetched once,
        # before anything is submitted, so a site that has moved or lost its
        # clip fails while the run is still free.
        hero_clips: Dict[str, Path] = {}
        for name in names:
            site = (shots[name].get("first_frame") or {}).get("hero_video", {}).get("site")
            if not site:
                continue
            print(f"\n[{name}] fetching the hero clip from {site}")
            try:
                hero_clips[name] = fetch_live_hero_video(client, site)
            except Exception as exc:
                print(f"\n      could not fetch her hero clip: {exc}\n")
                return 1

        for name in names:
            shot = shots[name]
            print(f"\n[{name}] {shot['title']}")
            clip = RAW_DIR / f"{name}.mp4"
            try:
                if shot.get("kind") == "text_to_video":
                    build_shot(client, prompt_for(plan, shot), seconds, clip,
                               tail_push=shot.get("tail_push"))
                else:
                    build_composite_shot(
                        frames[name], seconds, clip,
                        move=shot.get("move"),
                        hero_clip=hero_clips.get(name),
                        tail_push=shot.get("tail_push"),
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
