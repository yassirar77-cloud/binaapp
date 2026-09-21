#!/usr/bin/env python3
"""Build the clip that plays behind the landing hero.

Three shots, cut together into one silent loop:

    1. a merchant in a tudung using BinaApp on her phone, shot from behind
    2. the real /create page with her brief typed into it
    3. the site that brief produced — wesddd.binaapp.my

Shots 2 and 3 start from a REAL screenshot of the real page, so the Malay copy
and the layout are genuine pixels before the video model ever sees them. That
matters: wan3.0 redraws every frame, and text is the first thing it loses.
Their prompts are camera motion only — a slow push-in with slight parallax —
and spell out, element by element, that no text, button, icon, border or
layout may be redrawn. Shot 1 is the only one with motion in the scene, and
the only one whose first frame is generated rather than captured.

A prompt cannot make a redraw-every-frame model preserve typography, only bias
it. Judge shot 2 on its own (``--only 02-create``) before paying for the rest.

Provider, endpoint and key are the ones the product already uses for merchant
hero videos — DashScope (Alibaba Model Studio), read exactly as
``backend/app/services/zai_video_service.py`` reads them. The key comes from
the environment or a ``.env`` git already ignores; nothing is hardcoded.

Per shot: submit → poll → download the master into ``scripts/hero_raw/``
(gitignored) → and once all three are in, ffmpeg cross-fades them together,
strips the audio, scales to 720p and writes:

    frontend/public/hero/binaapp-hero.mp4
    frontend/public/hero/binaapp-hero.jpg

wan3.0 takes 5 or 10 seconds per job and nothing in between, so "longer" means
more shots, not a longer one: three 5s shots cross-faded make about 14s, and
``--seconds 10`` makes about 28s. Longer shots also drift further from their
first frame, which is the opposite of what shots 2 and 3 want.

Usage
-----
    # what it would do, and what it would cost — calls nothing
    python3 scripts/generate_landing_hero_video.py --dry-run

    # capture the two screenshots first, then look at them before paying
    python3 scripts/generate_landing_hero_video.py --capture-only

    # the real run
    python3 scripts/generate_landing_hero_video.py

    # redo one shot you did not like
    python3 scripts/generate_landing_hero_video.py --only 03-website

Requires ``ffmpeg``/``ffprobe``, ``httpx``, and ``playwright`` for --capture.
Shot 2 is captured from a LOCAL dev server (``npm run dev`` in frontend/), so
start that first or pass --frames-dir with your own PNGs.
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

RESOLUTION = "1080P"
RATIO = "16:9"

SUBMIT_TIMEOUT = 90
POLL_TIMEOUT = 60
POLL_INTERVAL = 10
MAX_WAIT_SECONDS = 1200
DOWNLOAD_TIMEOUT = 600

#: The hero sits behind a heavy scrim at full width. 1280 wide is enough for a
#: retina phone once the scrim is over it, and CRF 30 keeps the whole loop in
#: the low megabytes.
ENCODE_WIDTH = 1280
ENCODE_CRF = 30
CROSSFADE_SECONDS = 0.7
SIZE_BUDGET_BYTES = 3_500_000

#: Screenshots are captured at this size — the video's own aspect, so nothing
#: is letterboxed or cropped when it becomes a first frame.
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720


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
        "parameters": {"size": "1280*720", "n": 1},
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


def upload_frame(client: httpx.Client, frame: Path) -> str:
    """wan3.0 wants a URL for the first frame, not bytes.

    A local PNG is put somewhere the API can fetch it. 0x0.st is a plain
    anonymous file host with no account: it is used because the frames here are
    screenshots of public marketing pages and a generated stock image, nothing
    private. Set HERO_FRAME_UPLOAD_URL to point at your own host if you would
    rather not use it, or put the frames on Cloudinary and pass --frame-urls.
    """
    endpoint = os.getenv("HERO_FRAME_UPLOAD_URL", "https://0x0.st")
    with frame.open("rb") as handle:
        response = client.post(
            endpoint,
            files={"file": (frame.name, handle, "image/png")},
            timeout=DOWNLOAD_TIMEOUT,
            headers={"User-Agent": "binaapp-hero-builder/1.0"},
        )
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"could not upload the first frame ({response.status_code}). "
            f"Host the PNGs yourself and pass --frame-urls instead."
        )
    url = response.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"upload host returned something odd: {url[:200]}")
    return url


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
    response = client.post(
        f"{api_url()}/services/aigc/video-generation/video-synthesis",
        headers=auth_headers(),
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
# Capturing the two real pages
# ---------------------------------------------------------------------------


def capture_frames(shots: Dict[str, Dict], names: List[str]) -> None:
    """Screenshot the pages that shots 2 and 3 start from.

    Shot 2 is captured from a local dev server with the brief typed into the
    real textarea, so the frame the model animates already contains her words.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "playwright is not installed, so the frames cannot be captured.\n"
            "Either: pip install playwright && playwright install chromium\n"
            "Or:     put your own 1280x720 PNGs in scripts/hero_frames/ and rerun."
        )

    wanted = [n for n in names if shots[n].get("frame_from") == "capture"]
    if not wanted:
        return

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    # A machine whose Chromium is not where playwright expects it (a CI image,
    # a pinned browser bundle) can say where it is rather than re-downloading.
    executable = os.getenv("PLAYWRIGHT_CHROMIUM_PATH") or None

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(executable_path=executable)
        except Exception as exc:
            sys.exit(
                f"Could not start Chromium: {exc}\n\n"
                "Run `playwright install chromium`, or set PLAYWRIGHT_CHROMIUM_PATH to a\n"
                "Chromium binary you already have, or put your own "
                f"{CAPTURE_WIDTH}x{CAPTURE_HEIGHT} PNGs\n"
                f"in {FRAMES_DIR} and rerun with --no-capture."
            )
        page = browser.new_page(
            viewport={"width": CAPTURE_WIDTH, "height": CAPTURE_HEIGHT},
            device_scale_factor=2,
        )

        for name in wanted:
            shot = shots[name]
            url = shot["capture_url"]
            destination = FRAMES_DIR / f"{name}.png"
            print(f"      capturing {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
            except Exception as exc:
                print(f"      could not load {url}: {exc}")
                print(f"      put a 1280x720 PNG at {destination} and rerun")
                continue

            brief = shot.get("capture_brief")
            if brief:
                # Type into whichever box the page actually offers, rather than
                # assuming a selector that a redesign would silently break.
                box = page.query_selector("textarea") or page.query_selector(
                    "input[type=text]"
                )
                if box:
                    box.click()
                    box.fill(brief)
                    page.wait_for_timeout(600)
                else:
                    print("      no text box found on the page — capturing it empty")

            page.wait_for_timeout(2500)
            page.screenshot(path=str(destination))
            print(f"      → {destination.relative_to(REPO_ROOT)}")

        page.close()
        browser.close()


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


def video_size(path: Path) -> Tuple[int, int]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path.name}:\n{result.stderr[-500:]}")
    width, _, height = result.stdout.strip().partition("x")
    return int(width), int(height)


def normalise(clip: Path, destination: Path) -> None:
    """Re-encode one shot to the wall's size and frame rate, on its own.

    This exists because of a real ffmpeg limitation rather than taste: putting
    `scale`, `fps` or even `setpts` in front of `xfade` in a filter_complex
    drops the frame rate from the filter link, and xfade then refuses the whole
    graph with "current rate of 1/0 is invalid". Normalising to a file first
    and cross-fading the files raw is the version that actually runs. The
    intermediate is near-lossless so the second pass costs no visible quality.
    """
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(clip),
        "-an", "-vf", f"scale={ENCODE_WIDTH}:-2,fps=30,format=yuv420p",
        "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", str(destination),
    ])


def assemble(clips: List[Path], out: Path, crf: int = ENCODE_CRF) -> None:
    """Cross-fade the shots into one silent clip.

    Each fade eats CROSSFADE_SECONDS of overlap, so the result is shorter than
    the sum of its parts. Offsets come from the real measured durations, never
    the requested ones — a provider that returns 5.2s where 5 was asked for
    would otherwise put a black gap at every seam.
    """
    out.parent.mkdir(parents=True, exist_ok=True)

    if len(clips) == 1:
        run_quiet([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(clips[0]),
            "-an", "-vf", f"scale={ENCODE_WIDTH}:-2,fps=30,format=yuv420p",
            "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ])
        return

    # xfade needs every input the same size. They normally are — same model,
    # same resolution, same ratio — so the extra pass is skipped unless the
    # provider actually returned something different.
    sizes = {video_size(clip) for clip in clips}
    staged: List[Path] = list(clips)
    temporary: List[Path] = []

    if len(sizes) > 1:
        print(f"      shots came back at {len(sizes)} different sizes — normalising")
        staged = []
        for index, clip in enumerate(clips):
            destination = clip.parent / f".norm-{index}-{clip.name}"
            normalise(clip, destination)
            staged.append(destination)
            temporary.append(destination)

    try:
        command: List[str] = ["ffmpeg", "-y", "-loglevel", "error"]
        for clip in staged:
            command += ["-i", str(clip)]

        # Nothing may sit between an input and its xfade — see normalise().
        steps: List[str] = []
        running = duration_of(staged[0])
        previous = "0:v"
        for i in range(1, len(staged)):
            label = f"x{i}"
            steps.append(
                f"[{previous}][{i}:v]xfade=transition=fade:"
                f"duration={CROSSFADE_SECONDS}:offset={running - CROSSFADE_SECONDS:.3f}[{label}]"
            )
            running = running + duration_of(staged[i]) - CROSSFADE_SECONDS
            previous = label

        steps.append(f"[{previous}]scale={ENCODE_WIDTH}:-2,format=yuv420p[out]")

        command += [
            "-filter_complex", ";".join(steps),
            "-map", "[out]",
            "-an",
            "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out),
        ]
        run_quiet(command)
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)


def assemble_within_budget(clips: List[Path], out: Path) -> int:
    """Assemble, stepping quality down if the result busts the size budget."""
    for crf in (ENCODE_CRF, ENCODE_CRF + 3, ENCODE_CRF + 6):
        assemble(clips, out, crf=crf)
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
            "Generation costs real money. --dry-run prints the plan and the prompts\n"
            "and calls nothing; a shot whose master is already downloaded is re-cut\n"
            "for free rather than re-generated."
        ),
    )
    parser.add_argument("--only", metavar="SHOT", help="build just this shot (e.g. 03-website)")
    parser.add_argument("--seconds", type=int, choices=(5, 10), default=5,
                        help="length per shot; wan3.0 allows 5 or 10 and nothing else")
    parser.add_argument("--capture-only", action="store_true",
                        help="capture the screenshots and stop, so you can look at them first")
    parser.add_argument("--no-capture", action="store_true",
                        help="use the PNGs already in scripts/hero_frames/ as they are")
    parser.add_argument("--frames-dir", metavar="DIR",
                        help="take first frames from here instead of scripts/hero_frames/")
    parser.add_argument("--frame-urls", metavar="JSON",
                        help='{"01-merchant": "https://...png"} — skip uploading, use these')
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and the prompts; call nothing")
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

    print(f"\n{len(names)} shot(s), {args.seconds}s each on {video_model()} "
          f"({RESOLUTION} {RATIO}).")
    for name in names:
        print(f"  {name} — {shots[name]['title']}")

    if args.dry_run:
        print("\n--dry-run: nothing submitted.\n")
        for name in names:
            shot = shots[name]
            print(f"  {name}")
            if shot.get("frame_from") == "generate":
                print(f"    first frame (generated): {shot['frame_prompt']}\n")
            else:
                print(f"    first frame (captured):  {shot['capture_url']}")
                if shot.get("capture_brief"):
                    print(f"    typed into the page:     {shot['capture_brief']}")
            print(f"    motion: {shot['video_prompt']}\n")
        return 0

    require_tool("ffmpeg")
    require_tool("ffprobe")
    api_key()  # fail now, not after the first shot renders
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    if not args.no_capture:
        print("\nCapturing the pages the shots start from:")
        capture_frames(shots, names)

    if args.capture_only:
        print(f"\nFrames are in {FRAMES_DIR.relative_to(REPO_ROOT)}. "
              f"Look at them, then rerun without --capture-only.\n")
        return 0

    frame_urls: Dict[str, str] = json.loads(args.frame_urls) if args.frame_urls else {}
    built: List[str] = []
    failed: List[Tuple[str, str]] = []

    with httpx.Client() as client:
        for index, name in enumerate(names, start=1):
            shot = shots[name]
            print(f"\n[{index}/{len(names)}] {name} — {shot['title']}")
            raw = RAW_DIR / f"{name}.mp4"
            frame = FRAMES_DIR / f"{name}.png"

            try:
                if raw.is_file() and raw.stat().st_size > 0:
                    print("      master already downloaded — reusing it")
                    built.append(name)
                    continue

                if not frame.is_file():
                    if shot.get("frame_from") == "generate":
                        print("      generating the first frame")
                        generate_first_frame(client, shot["frame_prompt"], frame)
                    else:
                        raise RuntimeError(
                            f"no first frame at {frame}. Capture it (drop --no-capture) "
                            f"or put a {CAPTURE_WIDTH}x{CAPTURE_HEIGHT} PNG there."
                        )

                url = frame_urls.get(name)
                if not url:
                    print("      uploading the first frame")
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
                built.append(name)

            except Exception as exc:  # one bad shot must not lose the others
                print(f"      FAILED: {exc}")
                failed.append((name, str(exc)))

    ordered = [RAW_DIR / f"{n}.mp4" for n in shots if (RAW_DIR / f"{n}.mp4").is_file()]
    if not ordered:
        print("\nNo shots to cut together.\n")
        return 1

    if len(ordered) < len(shots):
        missing = [n for n in shots if not (RAW_DIR / f"{n}.mp4").is_file()]
        print(f"\nCutting {len(ordered)} of {len(shots)} shots — still missing: {', '.join(missing)}")

    print("\nCutting them together")
    size = assemble_within_budget(ordered, OUT_VIDEO)
    make_poster(OUT_VIDEO, OUT_POSTER)
    length = duration_of(OUT_VIDEO)
    print(f"      → {OUT_VIDEO.relative_to(REPO_ROOT)}  {length:.1f}s  {size / 1e6:.2f} MB")
    print(f"      → {OUT_POSTER.relative_to(REPO_ROOT)}")

    if failed:
        print(f"\n{len(failed)} shot(s) failed:")
        for name, reason in failed:
            print(f"  {name}: {reason}")
        print("\nRerun to retry only those — finished shots are reused, not re-paid for.")

    print("\nNext: cd frontend && npm run build, look at the hero, then commit "
          "the MP4 and the poster.\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
