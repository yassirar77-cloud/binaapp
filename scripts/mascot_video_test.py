#!/usr/bin/env python3
"""Mascot Video — Phase 1 model bake-off. Test only; nothing here is wired
into the app.

Takes one real clip (a shop, a dish), one mascot image and a prompt, and runs
the SAME input through every video-edit model a key is available for:

    wan      wan3.0-video video editing        DashScope   (existing key)
             input.media = reference_video + reference_image
    kling    Kling O3 video-to-video edit      Runway API  (RUNWAYML_API_SECRET)
             promptVideo + references[]
    runway   Runway Aleph 2.0 video-to-video   Runway API  (RUNWAYML_API_SECRET)
             videoUri + promptText (no reference-image input, see below)

Each output lands in test_outputs/ and a row (model, render time, billed
seconds, cost) is added to test_outputs/results.md.

What is reused from the backend
-------------------------------
The DashScope client in ``backend/app/services/zai_video_service.py``: its
key lookup (DASHSCOPE_API_KEY, then QWEN_API_KEY), base URL, async headers,
task poll (``fetch_result``), failure states and download. Only the request
body is built here, because the service's ``submit`` has no reference_video
shape yet — that is Phase 2. Mascots are generated with the same Z.ai
``/images/generations`` call (model ``glm-image``) that ``ai_service`` makes.

Where the request shapes come from (read 2026-11-22, not guessed)
----------------------------------------------------------------
* wan3.0-video: Alibaba Model Studio "Wan3.0 video generation API reference".
  Video editing = a ``reference_video`` (mp4/mov, 1-15 s, >=16 fps, <=100 MB)
  optionally with ``reference_image``; the prompt must state an edit intent and
  names media as "Video 1" / "Image 1"; ``duration: -1`` keeps the source
  length; billed seconds = input seconds + output seconds; Singapore price
  USD 0.05 / 0.10 / 0.20 per second at 480P / 720P / 1080P.
* Runway: the official ``runwayml`` SDK types (generated from their OpenAPI
  spec) and docs.dev.runwayml.com. ``aleph2`` is USD 0.28/s (min 0.56) and
  takes timed *keyframes*, not a free reference image, so the mascot reaches
  it through the prompt only. ``klingO3_pro`` takes ``references`` (up to 4
  images) and is 17 credits/s (USD 0.17/s).
* Kling's own API (api-singapore.klingai.com, access key + secret JWT): the
  official Omni spec could not be read (the docs site is a JS shell), so
  there is deliberately NO native Kling call here. Kling runs through Runway's
  API, where its schema is confirmed. A KLING_ACCESS_KEY alone is reported as
  skipped rather than fired at a guessed endpoint.

Usage
-----
    # the two test mascots (glm-image)
    python3 scripts/mascot_video_test.py make-mascots

    # one comparison run
    python3 scripts/mascot_video_test.py run \
        --clip path/to/shop.mp4 --mascot test_outputs/mascots/teh_tarik_uncle.png \
        --prompt "Add the mascot from Image 1 into Video 1 ..."

    python3 scripts/mascot_video_test.py run ... --dry-run     # payloads, no spend

Generation costs real money: a 5 s clip at 720P on wan3.0 is about USD 1.00
(5 s in + 5 s out). Requires ffmpeg/ffprobe and httpx.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services import zai_video_service as zvs  # noqa: E402
from app.services.zai_video_service import ZaiVideoError, zai_video_service  # noqa: E402

OUT_DIR = REPO_ROOT / "test_outputs"
MASCOT_DIR = OUT_DIR / "mascots"
RESULTS_JSON = OUT_DIR / "results.json"
RESULTS_MD = OUT_DIR / "results.md"

MAX_CLIP_SECONDS = 10
POLL_INTERVAL = 15          # the wan3.0 reference recommends ~15 s
MAX_WAIT_SECONDS = 1800

WAN_MODEL = "wan3.0-video"
#: USD per billed second, Singapore (international) region.
WAN_PRICE_PER_SECOND = {"480P": 0.05, "720P": 0.10, "1080P": 0.20}

RUNWAY_BASE_URL = "https://api.dev.runwayml.com"
RUNWAY_VERSION = "2024-11-06"
RUNWAY_USD_PER_CREDIT = 0.01
RUNWAY_MODELS = {
    # key -> (model id, credits per second, minimum credits)
    "runway": ("aleph2", 28, 56),
    "kling": ("klingO3_pro", 17, 0),
}
#: Runway takes a video as a data URI only up to 5 MB encoded.
RUNWAY_DATA_URI_MAX_BYTES = 3_300_000

DEFAULT_PROMPT = (
    "Edit Video 1: add the cartoon mascot character from Image 1 into the scene, "
    "standing naturally in the foreground, smiling and waving at the camera. "
    "Keep the mascot's flat colourful cartoon style exactly as in Image 1. "
    "Keep everything else in Video 1 unchanged: the same real shop, people, "
    "food, lighting and camera movement."
)

MASCOTS = {
    "teh_tarik_uncle": (
        "A friendly Malaysian teh tarik uncle mascot character, full body, standing, "
        "big warm smile, moustache, white songkok-style cap, apron, pulling teh tarik "
        "between two metal mugs with a long stream of milk tea. Flat vector cartoon "
        "style, bold clean outlines, bright happy colours, simple shapes, plain white "
        "background, no text, no logo."
    ),
    "cartoon_chicken": (
        "A cute cartoon chicken mascot character, full body, standing, big happy eyes, "
        "wide smile, one wing waving hello, small red comb, yellow beak. Flat vector "
        "cartoon style, bold clean outlines, bright happy colours, simple shapes, "
        "plain white background, no text, no logo."
    ),
}


# ---------------------------------------------------------------------------
# Local media helpers
# ---------------------------------------------------------------------------

def probe(path: Path) -> Dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    num, _, den = stream["r_frame_rate"].partition("/")
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": float(num) / float(den or 1),
        "duration": float(data["format"]["duration"]),
    }


def prepare_clip(src: Path, seconds: float) -> Path:
    """Normalise the clip to what every provider accepts: H.264 mp4, 30 fps,
    longest side <= 1280, no audio, trimmed to ``seconds``."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f"input_{src.stem}.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-t", f"{seconds:.2f}",
         "-vf", "scale='if(gt(iw,ih),min(1280,iw),-2)':'if(gt(iw,ih),-2,min(1280,ih))',fps=30",
         "-an", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)],
        check=True,
    )
    return dst


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


# ---------------------------------------------------------------------------
# DashScope — wan3.0-video video editing
# ---------------------------------------------------------------------------

def _dashscope_ready() -> bool:
    return bool(zvs._dashscope_api_key())


async def dashscope_temp_upload(path: Path, model: str) -> str:
    """DashScope's temporary file store: a signed OSS upload that returns an
    ``oss://`` URL valid for 48 h, resolved server-side when the submit carries
    ``X-DashScope-OssResourceResolve: enable``. Lets a local clip reach the
    model without first hosting it somewhere public."""
    auth = {"Authorization": f"Bearer {zvs._dashscope_api_key()}"}
    async with httpx.AsyncClient(timeout=300) as client:
        policy_resp = await client.get(
            f"{zvs._dashscope_base_url()}/uploads",
            params={"action": "getPolicy", "model": model}, headers=auth,
        )
        policy_resp.raise_for_status()
        policy = policy_resp.json()["data"]
        key = f"{policy['upload_dir']}/{path.name}"
        upload = await client.post(
            policy["upload_host"],
            data={
                "OSSAccessKeyId": policy["oss_access_key_id"],
                "Signature": policy["signature"],
                "policy": policy["policy"],
                "x-oss-object-acl": policy["x_oss_object_acl"],
                "x-oss-forbid-overwrite": policy["x_oss_forbid_overwrite"],
                "key": key,
                "success_action_status": "200",
            },
            files={"file": (path.name, path.read_bytes(), "video/mp4")},
        )
        if upload.status_code != 200:
            raise ZaiVideoError(f"DashScope temp upload failed ({upload.status_code}): {upload.text[:200]}")
    return f"oss://{key}"


def wan_payload(clip_url: str, mascot_url: str, prompt: str, resolution: str) -> Dict:
    return {
        "model": WAN_MODEL,
        "input": {
            "prompt": prompt,
            # Per-type numbering: the first reference_image is "Image 1", the
            # first reference_video "Video 1".
            "media": [
                {"type": "reference_image", "url": mascot_url},
                {"type": "reference_video", "url": clip_url},
            ],
        },
        "parameters": {
            "resolution": resolution,
            "ratio": "adaptive",   # recommended for editing: follow the source
            "duration": -1,        # smart duration: keep the source length
            "audio": False,
            "watermark": False,
            # The rewriter is told to preserve the scene by the prompt itself;
            # leaving it on lets it expand a short merchant prompt.
            "prompt_extend": True,
        },
    }


async def run_wan(clip: Path, clip_url: Optional[str], mascot: Path, prompt: str,
                  resolution: str, dry_run: bool) -> Dict:
    payload = wan_payload(clip_url or "oss://<uploaded at submit>", data_uri(mascot), prompt, resolution)
    if dry_run:
        shown = json.loads(json.dumps(payload))
        shown["input"]["media"][0]["url"] = f"data:image/...;base64,<{mascot.stat().st_size} bytes>"
        print(json.dumps(shown, indent=2))
        return {"status": "dry-run"}
    if not _dashscope_ready():
        return {"status": "skipped", "note": "DASHSCOPE_API_KEY / QWEN_API_KEY not set"}

    headers = zai_video_service._dashscope_headers()
    if not clip_url:
        clip_url = await dashscope_temp_upload(clip, WAN_MODEL)
        headers["X-DashScope-OssResourceResolve"] = "enable"
        payload["input"]["media"][1]["url"] = clip_url

    started = time.monotonic()
    async with httpx.AsyncClient(timeout=zvs.zai_video_timeout_seconds()) as client:
        response = await client.post(
            f"{zvs._dashscope_base_url()}/services/aigc/video-generation/video-synthesis",
            headers=headers, json=payload,
        )
    if response.status_code != 200:
        return {"status": "failed", "note": f"submit HTTP {response.status_code}: {response.text[:300]}"}
    task_id = (response.json().get("output") or {}).get("task_id")
    if not task_id:
        return {"status": "failed", "note": f"no task id: {response.text[:300]}"}
    print(f"  wan: task {task_id} accepted")

    while True:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            result = await zai_video_service.fetch_result(task_id, provider=zvs.PROVIDER_DASHSCOPE)
        except ZaiVideoError as exc:
            print(f"  wan: poll error ({exc}) — retrying")
            result = {"status": "processing"}
        elapsed = time.monotonic() - started
        if result["status"] == "success":
            break
        if result["status"] == "fail":
            return {"status": "failed", "task_id": task_id, "render_seconds": round(elapsed),
                    "note": f"{result.get('code')}: {result.get('message')}"}
        if elapsed > MAX_WAIT_SECONDS:
            return {"status": "failed", "task_id": task_id, "note": "timed out waiting"}
    render_seconds = time.monotonic() - started

    video_bytes = await zai_video_service.download(result["video_url"])
    # fetch_result keeps only the URL; the billed seconds are in `usage`.
    async with httpx.AsyncClient(timeout=60) as client:
        raw = await client.get(
            f"{zvs._dashscope_base_url()}/tasks/{task_id}",
            headers={"Authorization": f"Bearer {zvs._dashscope_api_key()}"},
        )
    usage = (raw.json() or {}).get("usage") or {}
    billed = float(usage.get("duration") or 0)
    price = WAN_PRICE_PER_SECOND.get(f"{usage.get('SR', '')}P", WAN_PRICE_PER_SECOND[resolution])
    return {
        "status": "ok", "task_id": task_id, "render_seconds": round(render_seconds),
        "billed_seconds": billed, "cost_usd": round(billed * price, 2),
        "usage": usage, "video_bytes": video_bytes,
    }


# ---------------------------------------------------------------------------
# Runway API — Aleph 2.0 and Kling O3 (video_to_video)
# ---------------------------------------------------------------------------

def _runway_key() -> Optional[str]:
    return (os.getenv("RUNWAYML_API_SECRET") or os.getenv("RUNWAY_API_KEY") or "").strip() or None


def _runway_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {_runway_key()}",
        "X-Runway-Version": RUNWAY_VERSION,
        "Content-Type": "application/json",
    }


async def runway_video_uri(client: httpx.AsyncClient, clip: Path) -> str:
    if clip.stat().st_size <= RUNWAY_DATA_URI_MAX_BYTES:
        return data_uri(clip)
    slot = await client.post(
        f"{RUNWAY_BASE_URL}/v1/uploads", headers=_runway_headers(),
        json={"filename": clip.name, "type": "ephemeral"},
    )
    slot.raise_for_status()
    info = slot.json()
    upload = await client.post(
        info["uploadUrl"], data=info["fields"],
        files={"file": (clip.name, clip.read_bytes(), "video/mp4")},
    )
    upload.raise_for_status()
    return info["runwayUri"]


def runway_payload(which: str, video_uri: str, mascot_uri: str, prompt: str) -> Dict:
    model = RUNWAY_MODELS[which][0]
    if which == "runway":
        # Aleph 2.0 has no free reference-image input (only keyframes pinned
        # to a timestamp), so the mascot is described by the prompt alone.
        return {"model": model, "videoUri": video_uri, "promptText": prompt}
    return {
        "model": model, "promptVideo": video_uri, "promptText": prompt,
        "references": [{"uri": mascot_uri}],
        "providerSettings": {"keepOriginalSound": False},
    }


async def run_runway(which: str, clip: Path, mascot: Path, prompt: str,
                     clip_seconds: float, dry_run: bool) -> Dict:
    model, credits_per_second, min_credits = RUNWAY_MODELS[which]
    if dry_run:
        print(json.dumps(runway_payload(which, "<clip>", "<mascot>", prompt), indent=2))
        return {"status": "dry-run"}
    if not _runway_key():
        note = "RUNWAYML_API_SECRET not set"
        if which == "kling" and os.getenv("KLING_ACCESS_KEY"):
            note = ("KLING_ACCESS_KEY is set, but Kling's native Omni API spec could not be "
                    "verified — set RUNWAYML_API_SECRET to run Kling O3 through Runway's API")
        return {"status": "skipped", "note": note}

    started = time.monotonic()
    async with httpx.AsyncClient(timeout=300) as client:
        video_uri = await runway_video_uri(client, clip)
        response = await client.post(
            f"{RUNWAY_BASE_URL}/v1/video_to_video", headers=_runway_headers(),
            json=runway_payload(which, video_uri, data_uri(mascot), prompt),
        )
        if response.status_code >= 300:
            return {"status": "failed", "note": f"submit HTTP {response.status_code}: {response.text[:300]}"}
        task_id = response.json()["id"]
        print(f"  {which}: task {task_id} accepted")
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            task = (await client.get(f"{RUNWAY_BASE_URL}/v1/tasks/{task_id}", headers=_runway_headers())).json()
            status = task.get("status")
            elapsed = time.monotonic() - started
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "CANCELLED"):
                return {"status": "failed", "task_id": task_id, "render_seconds": round(elapsed),
                        "note": f"{task.get('failureCode')}: {task.get('failure')}"}
            if elapsed > MAX_WAIT_SECONDS:
                return {"status": "failed", "task_id": task_id, "note": "timed out waiting"}
        render_seconds = time.monotonic() - started
        video = await client.get(task["output"][0], follow_redirects=True)
        video.raise_for_status()
    # Runway returns no usage block; this is list price x the source length.
    credits = max(min_credits, credits_per_second * clip_seconds)
    return {
        "status": "ok", "task_id": task_id, "render_seconds": round(render_seconds),
        "billed_seconds": clip_seconds, "cost_usd": round(credits * RUNWAY_USD_PER_CREDIT, 2),
        "cost_note": "list price, not metered", "video_bytes": video.content,
    }


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

MODEL_LABELS = {
    "wan": "wan3.0-video (DashScope, video edit + reference image)",
    "kling": "Kling O3 Pro (via Runway API, video-to-video + reference image)",
    "runway": "Runway Aleph 2.0 (video-to-video, prompt only)",
}


def record(rows: List[Dict]) -> None:
    existing = json.loads(RESULTS_JSON.read_text()) if RESULTS_JSON.exists() else []
    existing.extend(rows)
    RESULTS_JSON.write_text(json.dumps(existing, indent=2) + "\n")

    lines = [
        "# Mascot Video — Phase 1 test results",
        "",
        "Generated by `scripts/mascot_video_test.py`. Cost is USD per clip.",
        "",
        "| Model | Clip | Mascot | Status | Render time | Billed seconds | Cost per clip | Output |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in existing:
        render = f"{row['render_seconds']} s" if row.get("render_seconds") is not None else "–"
        billed = f"{row['billed_seconds']:g}" if row.get("billed_seconds") is not None else "–"
        cost = f"${row['cost_usd']:.2f}" if row.get("cost_usd") is not None else "–"
        if row.get("cost_note"):
            cost += f" ({row['cost_note']})"
        output = f"[{row['output']}]({row['output']})" if row.get("output") else (row.get("note") or "–")
        lines.append(
            f"| {MODEL_LABELS.get(row['model'], row['model'])} | {row['clip']} | {row['mascot']} "
            f"| {row['status']} | {render} | {billed} | {cost} | {output.replace('|', '/')} |"
        )
    prompts = sorted({row["prompt"] for row in existing})
    lines += ["", "## Prompts used", ""] + [f"- {p}" for p in prompts]
    RESULTS_MD.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_run(args: argparse.Namespace) -> int:
    src, mascot = Path(args.clip), Path(args.mascot)
    for path in (src, mascot):
        if not path.is_file():
            sys.exit(f"not a file: {path}")
    info = probe(src)
    seconds = min(info["duration"], MAX_CLIP_SECONDS)
    if seconds < 2:
        sys.exit("clip is shorter than 2 s")
    clip = prepare_clip(src, seconds)
    clip_seconds = round(probe(clip)["duration"], 2)
    print(f"clip: {src.name} -> {clip.name} ({clip_seconds} s, {clip.stat().st_size // 1024} KB)")

    rows: List[Dict] = []
    for which in args.models.split(","):
        which = which.strip()
        print(f"== {which}")
        try:
            if which == "wan":
                result = await run_wan(clip, args.clip_url, mascot, args.prompt, args.resolution, args.dry_run)
            elif which in RUNWAY_MODELS:
                result = await run_runway(which, clip, mascot, args.prompt, clip_seconds, args.dry_run)
            else:
                sys.exit(f"unknown model: {which}")
        except Exception as exc:  # noqa: BLE001 — one model failing must not lose the others
            result = {"status": "failed", "note": f"{type(exc).__name__}: {exc}"}
        if result["status"] == "dry-run":
            continue
        video_bytes = result.pop("video_bytes", None)
        row = {"model": which, "clip": src.name, "mascot": mascot.stem, "prompt": args.prompt, **result}
        if video_bytes:
            name = f"{which}__{src.stem}__{mascot.stem}.mp4"
            (OUT_DIR / name).write_bytes(video_bytes)
            row["output"] = name
        print(f"  {which}: {row['status']} {row.get('note', '')} "
              f"{row.get('render_seconds', '')}s ${row.get('cost_usd', '')}")
        rows.append(row)
    if rows:
        record(rows)
        print(f"results: {RESULTS_MD}")
    return 0


async def cmd_make_mascots(args: argparse.Namespace) -> int:
    """The same Z.ai images call ai_service._generate_image_zai makes
    (model glm-image, 1024x1024), saved locally instead of to Cloudinary."""
    key = zvs._zai_api_key()
    if not key:
        sys.exit("ZAI_API_KEY is not set")
    model = os.getenv("ZAI_IMAGE_MODEL", "glm-image")
    MASCOT_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=180) as client:
        for name, prompt in MASCOTS.items():
            if args.only and name not in args.only.split(","):
                continue
            response = await client.post(
                f"{zvs._zai_base_url()}/images/generations",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "prompt": prompt, "size": "1024x1024"},
            )
            if response.status_code != 200:
                sys.exit(f"{name}: Z.ai image failed {response.status_code}: {response.text[:300]}")
            url = response.json()["data"][0]["url"]
            image = await zai_video_service.download(url)  # same verbatim-URL CDN fetch
            out = MASCOT_DIR / f"{name}.png"
            out.write_bytes(image)
            print(f"{name}: {out} ({len(image) // 1024} KB)")
            await asyncio.sleep(1.0)  # the endpoint rejects concurrency
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run one clip + mascot through every available model")
    run.add_argument("--clip", required=True, help="local clip (any ffmpeg-readable format)")
    run.add_argument("--mascot", required=True, help="mascot image (png/jpg, no transparency)")
    run.add_argument("--prompt", default=DEFAULT_PROMPT)
    run.add_argument("--models", default="wan,kling,runway")
    run.add_argument("--resolution", default="720P", choices=sorted(WAN_PRICE_PER_SECOND))
    run.add_argument("--clip-url", help="public URL of the SAME clip, to skip the DashScope temp upload")
    run.add_argument("--dry-run", action="store_true", help="print payloads, spend nothing")

    mascots = sub.add_parser("make-mascots", help="generate the two test mascots with glm-image")
    mascots.add_argument("--only", help="comma-separated mascot names")

    args = parser.parse_args()
    handler = cmd_run if args.command == "run" else cmd_make_mascots
    return asyncio.run(handler(args))


if __name__ == "__main__":
    sys.exit(main())
