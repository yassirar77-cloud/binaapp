#!/usr/bin/env python3
"""Generate the homepage showcase clips on DashScope, compress them, and wire
them into the frontend.

The showcase wall (``frontend/src/components/landing/LandingShowcase.tsx``) is
sixteen cards, each one a restaurant site's hero video. Fifteen are design
examples with no footage behind them; this script makes that footage.

It uses the same provider the product already uses for merchant hero videos —
Alibaba Model Studio (DashScope), the ``happyhorse-1.1-t2v`` text-to-video
model on the async video-synthesis endpoint, reading ``DASHSCOPE_API_KEY``
exactly as ``backend/app/services/zai_video_service.py`` does. Nothing new is
configured and no key is written down anywhere: the key is read from the
environment or from a ``.env`` file that git already ignores.

The sixteenth card, Nasi Kukus Wak Hassan, is a real trading site, so its clip
is taken from that site rather than generated. It costs nothing and it is the
merchant's own footage.

Per clip:

    submit  → DashScope accepts the job and returns a task id
    poll    → until SUCCEEDED (or FAILED, or the wall-clock limit)
    download→ the raw master into scripts/showcase_raw/  (gitignored)
    encode  → 480px-wide muted MP4 into frontend/public/showcase/<name>.mp4
    poster  → first frame into frontend/public/showcase/<name>.jpg
    wire    → src + poster onto the matching clip in showcaseClips.ts

Generation costs real money (HappyHorse is roughly USD 0.70 for five seconds
at the time of writing), so ``--skip-existing`` is the flag to reach for on
any rerun: a clip that already has a compressed MP4 is never submitted twice.
The raw masters are kept for the same reason — re-encoding is free, and a
tweak to the encode settings should never mean paying for the footage again.

Usage
-----
    python3 scripts/generate_showcase_videos.py --skip-existing
    python3 scripts/generate_showcase_videos.py --only ckt-ah-seng
    python3 scripts/generate_showcase_videos.py --dry-run

Requires ``ffmpeg`` and ``ffprobe`` on PATH, and ``httpx`` (already a backend
dependency).
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
from typing import Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:  # pragma: no cover - a missing dep is an operator problem
    sys.exit("httpx is not installed. Run: pip install httpx")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_FILE = REPO_ROOT / "scripts" / "showcase_prompts.json"
RAW_DIR = REPO_ROOT / "scripts" / "showcase_raw"
OUT_DIR = REPO_ROOT / "frontend" / "public" / "showcase"
CLIPS_TS = REPO_ROOT / "frontend" / "src" / "lib" / "landing" / "showcaseClips.ts"

#: The one card that is a real trading site. Its hero clip is lifted from the
#: live page instead of generated — the merchant's own footage, and free.
LIVE_CLIP_NAME = "nasi-kukus-wak-hassan"
LIVE_CLIP_SITE = "https://mayam.binaapp.my"


# ---------------------------------------------------------------------------
# Provider settings — mirrored from backend/app/services/zai_video_service.py
# ---------------------------------------------------------------------------

#: Text-to-video on the video-synthesis endpoint. The backend picks this model
#: for any job with no photo to animate, which is every job here.
DEFAULT_T2V_MODEL = "happyhorse-1.1-t2v"
DEFAULT_API_URL = "https://dashscope-intl.aliyuncs.com/api/v1"

RUNNING_STATES = ("PENDING", "RUNNING", "SUSPENDED")
FAILED_STATES = ("FAILED", "CANCELED", "CANCELLED", "UNKNOWN")

#: What the showcase cards want, regardless of what the running service is
#: configured for: tall, 720p, five seconds.
RESOLUTION = "720P"
RATIO = "9:16"
DURATION = 5

SUBMIT_TIMEOUT = 90
POLL_TIMEOUT = 60
POLL_INTERVAL = 10
MAX_WAIT_SECONDS = 900
DOWNLOAD_TIMEOUT = 300

#: Encode target for the wall. Cards are ~250-330px wide on a desktop screen,
#: so 480px is already generous; CRF 30 lands a five-second clip in the few
#: hundred KB the section's README asks for.
ENCODE_WIDTH = 480
ENCODE_CRF = 30
SIZE_BUDGET_BYTES = 1_000_000


def load_dotenv(path: Path) -> None:
    """Read ``KEY=value`` lines from a .env file into the environment.

    Only fills what is not already set, so a key exported in the shell wins.
    This is the only way the script ever learns a key: nothing is hardcoded,
    and ``.env`` is in .gitignore, so a key read here cannot be committed.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # A trailing comment on a value line ("sk-xxx  # prod key") would
        # otherwise become part of the key and the API would reject it.
        value = re.split(r"\s+#", value, maxsplit=1)[0].strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


def api_key() -> str:
    """The DashScope key, from the same two env vars the backend reads, in the
    same order. Whitespace stripped — a key pasted from a phone arrives with a
    trailing newline and the API rejects it as InvalidApiKey."""
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


def t2v_model() -> str:
    return (os.getenv("DASHSCOPE_T2V_MODEL") or DEFAULT_T2V_MODEL).strip() or DEFAULT_T2V_MODEL


def is_unified(model: str) -> bool:
    """wan3.x takes the unified request shape, which accepts ``audio``. The
    ``-t2v`` models do not have the parameter at all — sending it risks a
    rejected request, so audio is only switched off where it exists. The
    encode strips any audio track regardless, so the clips are silent either
    way; this only decides whether we pay to render a soundtrack."""
    return (model or "").strip().lower().startswith("wan3")


# ---------------------------------------------------------------------------
# DashScope calls
# ---------------------------------------------------------------------------


def submit(client: httpx.Client, prompt: str) -> str:
    """Create the video job. Returns the task id."""
    model = t2v_model()
    parameters: Dict = {
        "resolution": RESOLUTION,
        "ratio": RATIO,
        "duration": DURATION,
    }
    if is_unified(model):
        parameters["audio"] = False
    else:
        # HappyHorse burns a "Happy Horse" mark into the corner unless told not to.
        parameters["watermark"] = False

    payload = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": parameters,
    }
    response = client.post(
        f"{api_url()}/services/aigc/video-generation/video-synthesis",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            # Video synthesis is async-only: this returns a task id, and
            # GET /tasks/{id} is polled until it settles.
            "X-DashScope-Async": "enable",
        },
        json=payload,
        timeout=SUBMIT_TIMEOUT,
    )
    if response.status_code == 429:
        raise RuntimeError("rate limited (429) — wait a minute and rerun with --skip-existing")
    if response.status_code in (401, 403):
        raise RuntimeError(
            f"DashScope rejected the key ({response.status_code}). Check it is a key for "
            f"this region — an international key only works on dashscope-intl."
        )
    if response.status_code != 200:
        raise RuntimeError(f"submit failed ({response.status_code}): {response.text[:300]}")

    output = (response.json() or {}).get("output") or {}
    task_id = output.get("task_id")
    if not task_id:
        raise RuntimeError(f"submit returned no task id: {str(response.json())[:300]}")
    state = str(output.get("task_status", "")).upper()
    if state in FAILED_STATES:
        raise RuntimeError(f"rejected at submit ({output.get('message') or state})")
    return str(task_id)


def describe_cost(body: Dict) -> str:
    """Whatever the response says this cost, if it says anything.

    DashScope reports usage inconsistently across models — sometimes
    ``usage.video_duration``, sometimes nothing at all — so this reports what
    is there and stays quiet when there is nothing rather than inventing a
    number. The authoritative figure is the Model Studio billing console.
    """
    usage = body.get("usage") or {}
    if not usage:
        return ""
    parts = [f"{key}={value}" for key, value in sorted(usage.items())]
    return " ".join(parts)


def poll(client: httpx.Client, task_id: str) -> Tuple[str, str]:
    """Poll until the task settles. Returns (video_url, cost description)."""
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
            video_url = output.get("video_url")
            if not video_url:
                raise RuntimeError("SUCCEEDED but no video_url in the response")
            return video_url, describe_cost(body)
        if state in FAILED_STATES:
            raise RuntimeError(
                f"{state}: {output.get('message') or output.get('code') or 'no reason given'}"
            )
        # Anything undocumented is treated as still running; the deadline below
        # is what stops us waiting forever.
        time.sleep(POLL_INTERVAL)

    raise RuntimeError(f"still {last_state or 'running'} after {MAX_WAIT_SECONDS}s — gave up")


def download(client: httpx.Client, url: str, destination: Path) -> None:
    """Stream to a temp file and move it into place, so an interrupted
    download never leaves a half file that --skip-existing would trust."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", url, timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=65536):
                handle.write(chunk)
    partial.replace(destination)


# ---------------------------------------------------------------------------
# Wak Hassan — the live site's own clip
# ---------------------------------------------------------------------------

#: The hero patcher writes `<video class="binaapp-hero-video" …><source src="…">`
#: into every generated site, so the clip is found by that class rather than by
#: guessing at the first <video> on the page.
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

    # The site may not carry the marker (hand-edited, or an older build).
    # Fall back to the first MP4 on the page and say so, rather than failing.
    fallback = ANY_MP4.search(html)
    if fallback:
        print(f"      no binaapp-hero-video block — using first MP4 found: {fallback.group(0)}")
        return fallback.group(0)

    raise RuntimeError(
        f"no hero video found on {site}. If the site has no hero clip yet, add one "
        f"there first, or drop a file at {OUT_DIR / (LIVE_CLIP_NAME + '.mp4')} by hand."
    )


# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        sys.exit(f"{name} is not on PATH. Install ffmpeg (which ships both ffmpeg and ffprobe).")


def run_quiet(command: List[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{command[0]} failed:\n{result.stderr[-1500:]}")


def encode(raw: Path, out: Path, crf: int = ENCODE_CRF) -> None:
    """Compress the master down to what the wall actually displays.

    ``-an`` drops audio (the wall is always muted), the scale keeps the clip's
    own aspect at 480px wide, and ``+faststart`` moves the index to the front
    so playback can start before the file finishes arriving. The width is
    forced even, since H.264 cannot encode odd dimensions.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(raw),
        "-an",
        "-t", str(DURATION),
        "-vf", f"scale={ENCODE_WIDTH}:-2",
        "-c:v", "libx264", "-crf", str(crf), "-preset", "slow",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out),
    ])


def make_poster(video: Path, poster: Path) -> None:
    """First frame as a JPG. The card shows it while the video loads — without
    one, a card sits on its bare gradient until playback starts."""
    run_quiet([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video),
        "-vframes", "1", "-q:v", "6",
        str(poster),
    ])


def encode_within_budget(raw: Path, out: Path) -> int:
    """Encode, and step the quality down if the result busts the size budget.

    A busy clip (the wok fire, the steamer) can exceed 1 MB at CRF 30 where a
    calm one lands at 300 KB. Rather than leave the operator to notice, retry
    at progressively lower quality and report what it took.
    """
    for crf in (ENCODE_CRF, ENCODE_CRF + 3, ENCODE_CRF + 6):
        encode(raw, out, crf=crf)
        size = out.stat().st_size
        if size <= SIZE_BUDGET_BYTES:
            if crf != ENCODE_CRF:
                print(f"      needed crf {crf} to fit the budget")
            return size
    # Three passes and still over: keep the smallest attempt and let the
    # operator decide. A slightly heavy clip is better than no clip.
    print(f"      still {out.stat().st_size / 1e6:.2f} MB after crf {ENCODE_CRF + 6} — kept anyway")
    return out.stat().st_size


# ---------------------------------------------------------------------------
# Wiring the results into showcaseClips.ts
# ---------------------------------------------------------------------------


def wire_clips_ts(names: List[str]) -> int:
    """Uncomment / insert `src` and `poster` for every clip whose files exist.

    The TypeScript already carries each clip's `src`; what is missing is the
    `poster`. This adds the poster line directly after the src line for any
    clip that now has a JPG, and leaves a clip alone if it is already wired.
    Returns how many clips were changed.
    """
    if not CLIPS_TS.is_file():
        print(f"! {CLIPS_TS} not found — skipping the wiring step")
        return 0

    source = CLIPS_TS.read_text(encoding="utf-8")
    changed = 0

    for name in names:
        video = OUT_DIR / f"{name}.mp4"
        poster = OUT_DIR / f"{name}.jpg"
        if not video.is_file():
            continue

        src_line = f"    src: '/showcase/{name}.mp4',"
        poster_line = f"    poster: '/showcase/{name}.jpg',"

        if src_line not in source:
            print(f"! {name}: no matching src line in showcaseClips.ts — wire it by hand")
            continue
        if not poster.is_file() or poster_line in source:
            continue

        source = source.replace(src_line, f"{src_line}\n{poster_line}", 1)
        changed += 1

    if changed:
        CLIPS_TS.write_text(source, encoding="utf-8")
    return changed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def load_prompts() -> Dict[str, str]:
    if not PROMPTS_FILE.is_file():
        sys.exit(f"{PROMPTS_FILE} not found.")
    data = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    clips = data.get("clips")
    if not isinstance(clips, dict) or not clips:
        sys.exit(f"{PROMPTS_FILE} has no 'clips' object.")
    return clips


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the homepage showcase clips on DashScope.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Generation costs real money. Use --skip-existing on every rerun so a\n"
            "clip that already has an MP4 is never paid for twice."
        ),
    )
    parser.add_argument("--only", metavar="NAME", help="generate just this one clip")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="skip any clip that already has an MP4 in frontend/public/showcase/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be generated and what it would cost; call nothing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / "backend" / ".env")

    prompts = load_prompts()
    names = [LIVE_CLIP_NAME] + list(prompts.keys())

    if args.only:
        if args.only not in names:
            sys.exit(f"Unknown clip '{args.only}'. Known: {', '.join(names)}")
        names = [args.only]

    # Decide the work before touching the network, so --dry-run is honest and
    # the cost is stated before a single job is paid for.
    todo = []
    for name in names:
        if args.skip_existing and (OUT_DIR / f"{name}.mp4").is_file():
            print(f"· {name}: already built, skipping")
            continue
        todo.append(name)

    if not todo:
        print("\nNothing to do.")
        return 0

    billable = [n for n in todo if n != LIVE_CLIP_NAME]
    print(f"\n{len(todo)} clip(s) to build, {len(billable)} of them billable "
          f"({t2v_model()}, {RESOLUTION} {RATIO} {DURATION}s).")
    if LIVE_CLIP_NAME in todo:
        print(f"  {LIVE_CLIP_NAME} is taken from {LIVE_CLIP_SITE} — free.")

    if args.dry_run:
        print("\n--dry-run: nothing submitted.\n")
        for name in todo:
            print(f"  {name}")
            if name != LIVE_CLIP_NAME:
                print(f"    {prompts[name]}")
        return 0

    require_tool("ffmpeg")
    require_tool("ffprobe")
    api_key()  # fail now, not after the first clip renders
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    built: List[str] = []
    failed: List[Tuple[str, str]] = []

    with httpx.Client() as client:
        for index, name in enumerate(todo, start=1):
            print(f"\n[{index}/{len(todo)}] {name}")
            raw = RAW_DIR / f"{name}.mp4"
            out = OUT_DIR / f"{name}.mp4"
            poster = OUT_DIR / f"{name}.jpg"

            try:
                # A master already downloaded is re-encoded for free — never
                # pay twice because the encode settings changed.
                if raw.is_file() and raw.stat().st_size > 0:
                    print("      raw master already downloaded — re-encoding only")
                elif name == LIVE_CLIP_NAME:
                    print(f"      fetching the live hero clip from {LIVE_CLIP_SITE}")
                    url = find_live_hero_video(client, LIVE_CLIP_SITE)
                    print(f"      downloading {url}")
                    download(client, url, raw)
                else:
                    print("      submitting")
                    task_id = submit(client, prompts[name])
                    print(f"      task {task_id}")
                    url, cost = poll(client, task_id)
                    if cost:
                        print(f"      usage: {cost}")
                    print("      downloading")
                    download(client, url, raw)

                size = encode_within_budget(raw, out)
                make_poster(out, poster)
                print(f"      → {out.relative_to(REPO_ROOT)}  {size / 1e6:.2f} MB")
                print(f"      → {poster.relative_to(REPO_ROOT)}")
                built.append(name)

            except Exception as exc:  # one bad clip must not lose the rest
                print(f"      FAILED: {exc}")
                failed.append((name, str(exc)))

    wired = wire_clips_ts(built)

    print(f"\nBuilt {len(built)} clip(s).")
    if wired:
        print(f"Wired {wired} poster(s) into {CLIPS_TS.relative_to(REPO_ROOT)}.")
    if failed:
        print(f"\n{len(failed)} failed:")
        for name, reason in failed:
            print(f"  {name}: {reason}")
        print("\nRerun with --skip-existing to retry only these.")
    print(
        "\nNext: cd frontend && npm run build, check the wall, then commit the "
        "MP4s and posters.\n"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
