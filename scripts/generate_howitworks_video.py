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

#: The phone. Height in canvas pixels, and the bezel it sits in.
PHONE_HEIGHT = 976
BEZEL_WIDTH, BEZEL_HEIGHT = 520, 1000
PHONE_RADIUS, BEZEL_RADIUS = 44, 52

#: Fractions trimmed off a phone capture: the OS status bar at the top and the
#: navigation bar at the bottom. Measured against these screenshots rather than
#: assumed — a different phone would need different numbers.
STATUS_BAR_FRACTION = 0.052
NAV_BAR_FRACTION = 0.066

#: The background behind the phone: a brand-dark diagonal gradient.
GRADIENT = (
    f"gradients=s={WIDTH}x{HEIGHT}:c0=0x141033:c1=0x07070F"
    f":x0=300:y0=0:x1=1700:y1={HEIGHT}:d=1:r={FPS}"
)
BEZEL_COLOUR = "0x2E2E44"

#: A flat colour source at the film's rate. lavfi sources default to 25fps,
#: and an overlay takes its rate from them — which is how a 30fps beat came
#: out at 25 and xfade then refused to cut it against the others.
def colour_source(colour: str, width: int = WIDTH, height: int = HEIGHT) -> str:
    return f"color=c={colour}:s={width}x{height}:r={FPS}"

#: How far the eased push-in travels over a beat.
PUSH_IN_ZOOM = 1.09

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


def eased_push_in(seconds: float) -> str:
    """A zoompan that eases in and out rather than ramping linearly.

    `on` is the output frame index; the smoothstep 3p²-2p³ is what stops the
    move from starting and stopping with a visible jerk.
    """
    frames = max(2, int(round(seconds * FPS)))
    progress = f"(on/{frames})"
    smooth = f"({progress}*{progress}*(3-2*{progress}))"
    return (
        f"zoompan=z='1+{PUSH_IN_ZOOM - 1:.4f}*{smooth}':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={WIDTH}x{HEIGHT}:fps={FPS}"
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


def phone_layer(label_in: str, label_out: str, crop: bool, sweep_seconds: float) -> str:
    """Filter chain: a capture becomes the lit, rounded phone screen.

    The light sweep is applied to the screen BEFORE the corners are rounded, so
    it is clipped to the glass for free instead of needing a second mask.
    """
    trim = (
        f"crop=iw:ih*{1 - STATUS_BAR_FRACTION - NAV_BAR_FRACTION}:0:ih*{STATUS_BAR_FRACTION},"
        if crop else ""
    )
    return (
        f"[{label_in}]{trim}scale=-2:{PHONE_HEIGHT},format=rgba[{label_out}_lit];"
        f"[{label_out}_lit]{rounded_alpha(PHONE_RADIUS)}[{label_out}]"
    ) if sweep_seconds <= 0 else (
        f"[{label_in}]{trim}scale=-2:{PHONE_HEIGHT},format=rgba[{label_out}_scr];"
        f"[{label_out}_scr]{rounded_alpha(PHONE_RADIUS)}[{label_out}]"
    )


def build_phone_stills(stills: List[Path], wide: List[Path], seconds: float, out: Path) -> None:
    """Beat 2: her /create screenshots, each in the phone, cross-dissolving.

    Built one still at a time and concatenated, rather than as one enormous
    filter graph — a graph with six zoompans and five xfades in it is both
    unreadable and, on some ffmpeg builds, unrunnable.
    """
    pieces: List[Path] = []
    everything = [(s, True) for s in stills] + [(w, False) for w in wide]
    if not everything:
        raise RuntimeError("no stills to build beat 2 from")

    # A cross-dissolve eats time from both neighbours, so each piece is a
    # little longer than its share.
    dissolve = 0.5
    each = (seconds + dissolve * (len(everything) - 1)) / len(everything)

    for index, (still, as_phone) in enumerate(everything):
        piece = out.with_name(f"{out.stem}-{index}.mp4")
        sweep_at = each * 0.45

        if as_phone:
            graph = (
                f"[1:v]format=rgba[bg];"
                f"[2:v]scale={BEZEL_WIDTH}:{BEZEL_HEIGHT},format=rgba,"
                f"{rounded_alpha(BEZEL_RADIUS)}[bezel];"
                f"[0:v]crop=iw:ih*{1 - STATUS_BAR_FRACTION - NAV_BAR_FRACTION}"
                f":0:ih*{STATUS_BAR_FRACTION},scale=-2:{PHONE_HEIGHT},format=rgba[screen];"
                f"[3:v]scale=260:{int(PHONE_HEIGHT * 2)},rotate=0.35"
                f":c=none:ow=rotw(0.35):oh=roth(0.35),format=rgba,"
                f"colorchannelmixer=aa=0.10[sweep];"
                f"[screen][sweep]overlay=x='-w+(t/{max(each, 0.1):.3f})*(W+w*2)'"
                f":y=(H-h)/2:eval=frame[screenlit];"
                f"[screenlit]{rounded_alpha(PHONE_RADIUS)}[phone];"
                f"[bg][bezel]overlay=(W-w)/2:(H-h)/2[framed];"
                f"[framed][phone]overlay=(W-w)/2:(H-h)/2,{eased_push_in(each)},"
                f"format=yuv420p[out]"
            )
            inputs = [
                "-loop", "1", "-t", f"{each:.3f}", "-i", str(still),
                "-f", "lavfi", "-t", f"{each:.3f}", "-i", GRADIENT,
                "-f", "lavfi", "-t", f"{each:.3f}", "-i", colour_source(BEZEL_COLOUR),
                "-f", "lavfi", "-t", f"{each:.3f}", "-i",
                colour_source("white", 260, int(PHONE_HEIGHT * 2)),
            ]
        else:
            # The landscape capture gets a wide card instead of a phone.
            card_w = int(WIDTH * 0.74)
            graph = (
                f"[1:v]format=rgba[bg];"
                f"[0:v]scale={card_w}:-2,format=rgba,{rounded_alpha(24)}[card];"
                f"[bg][card]overlay=(W-w)/2:(H-h)/2,{eased_push_in(each)},"
                f"format=yuv420p[out]"
            )
            inputs = [
                "-loop", "1", "-t", f"{each:.3f}", "-i", str(still),
                "-f", "lavfi", "-t", f"{each:.3f}", "-i", GRADIENT,
            ]
            _ = sweep_at

        run_quiet(
            ["ffmpeg", "-y", "-loglevel", "error"] + inputs
            + ["-filter_complex", graph, "-map", "[out]", "-an",
               "-t", f"{each:.3f}"] + INTERMEDIATE_ARGS + [str(piece)]
        )
        pieces.append(piece)

    crossfade_concat(pieces, out, dissolve)
    for piece in pieces:
        piece.unlink(missing_ok=True)


#: How fast the site recording may be pushed. Below 1.0 would be slow motion;
#: above about 3x a page scroll stops reading as browsing and starts reading as
#: a glitch.
MIN_SPEED, MAX_SPEED = 1.0, 3.0


def build_phone_recording(recording: Path, max_speed: float, seconds: float, out: Path) -> None:
    """Beat 3: her site recording, in the same phone, fitted to its slot.

    The speed-up is computed from the slot rather than fixed, so the beat
    always fills its share instead of running out and freezing on the last
    frame — which is what a hard-coded 1.8x did the first time this ran.
    `max_speed` from the shot plan is a ceiling, not the value.
    """
    source_length = duration_of(recording)
    wanted = source_length / max(seconds, 0.1)
    speed = min(max(wanted, MIN_SPEED), min(max_speed, MAX_SPEED))
    take = min(seconds, source_length / speed)
    print(f"      {source_length:.1f}s recording at {speed:.2f}x → {take:.1f}s")
    if take < seconds - 0.05:
        print(f"      (short of the {seconds:.1f}s slot even at {speed:.2f}x)")

    graph = (
        f"[1:v]format=rgba[bg];"
        f"[2:v]scale={BEZEL_WIDTH}:{BEZEL_HEIGHT},format=rgba,"
        f"{rounded_alpha(BEZEL_RADIUS)}[bezel];"
        f"[0:v]setpts=PTS/{speed},fps={FPS},"
        f"crop=iw:ih*{1 - STATUS_BAR_FRACTION - NAV_BAR_FRACTION}:0:ih*{STATUS_BAR_FRACTION},"
        f"scale=-2:{PHONE_HEIGHT},format=rgba,{rounded_alpha(PHONE_RADIUS)}[phone];"
        f"[bg][bezel]overlay=(W-w)/2:(H-h)/2[framed];"
        f"[framed][phone]overlay=(W-w)/2:(H-h)/2:shortest=1,format=yuv420p[out]"
    )
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(recording),
        "-f", "lavfi", "-t", f"{take:.3f}", "-i", GRADIENT,
        "-f", "lavfi", "-t", f"{take:.3f}", "-i", colour_source(BEZEL_COLOUR),
        "-filter_complex", graph, "-map", "[out]", "-an",
        "-t", f"{take:.3f}",
    ] + INTERMEDIATE_ARGS + [str(out)])


def build_site_fullframe(recording: Path, start: float, seconds: float, out: Path) -> None:
    """The closing beat: her site filling the frame, sharp, barely moving."""
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(recording),
        "-an", "-t", f"{seconds:.3f}",
        "-vf",
        f"crop=iw:ih*{1 - STATUS_BAR_FRACTION - NAV_BAR_FRACTION}:0:ih*{STATUS_BAR_FRACTION},"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},unsharp=5:5:0.8,format=yuv420p",
    ] + INTERMEDIATE_ARGS + [str(out)])


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def crossfade_concat(clips: List[Path], out: Path, crossfade: float,
                     crf: int = ENCODE_CRF, faststart: bool = False) -> None:
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
            f"[{previous}][{index}:v]xfade=transition=fade:duration={crossfade}"
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

    ai_names = [n for n in names if shots[n]["kind"] == "ai"]
    if args.stills_only:
        names = [n for n in names if n not in ai_names]
        ai_names = []
        print("\n--stills-only: the AI beats are skipped, nothing will be spent.")
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
        for name in names
        if shots[name]["kind"] == "site_fullframe"
    }
    try:
        lengths = plan_durations(ai_lengths, target, crossfade, names, fixed)
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
            build_phone_stills(
                [ASSETS_DIR / s for s in shot["stills"]],
                [ASSETS_DIR / s for s in shot.get("wide_stills", [])],
                seconds, clip,
            )
        elif shot["kind"] == "phone_recording":
            build_phone_recording(
                ASSETS_DIR / shot["recording"], float(shot["speed"]), seconds, clip
            )
        elif shot["kind"] == "site_fullframe":
            build_site_fullframe(
                ASSETS_DIR / shot["recording"], float(shot["from_seconds"]), seconds, clip
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
    if abs(length - target) > 0.3 and not args.stills_only:
        print(f"      note: {length:.2f}s against a {target:.0f}s target")
    if size > SIZE_BUDGET_BYTES:
        print(f"      note: over the {SIZE_BUDGET_BYTES / 1e6:.0f} MB budget")
    print("\nNext: cd frontend && npm run build, look at the section, then commit.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
