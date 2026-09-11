#!/usr/bin/env python3
"""End-to-end check of the hero-video pipeline against a REAL deployment.

    python scripts/hero_video_e2e.py --api https://binaapp-backend.onrender.com \
        --website-id <uuid> --token <jwt> [--style elegant] [--prompt "..."] \
        [--image-url https://...] [--timeout 720]

or with --email/--password instead of --token (logs in through /api/v1/auth/login).

What it proves, in order, and prints as it goes:

  1. POST …/hero-video/generate is accepted (202) and returns a job id.
  2. GET  …/hero-video/jobs/{id} is READ-ONLY: it reports the driver's
     progress (status, provider_status, elapsed) — the server advances the
     job whether or not this script keeps polling. Pass --disconnect to
     stop polling for 90 s mid-job and prove the clip still lands.
  3. The job reaches `completed` with a Cloudinary video_url.
  4. The websites row (via GET /api/v1/websites/{id}/hero-video) reports
     has_video with the same URL.
  5. The LIVE page at https://{subdomain}.binaapp.my carries
     `data-binaapp-hero-video="1"` on the hero and a <video> whose <source>
     is that URL — fetched fresh (no-cache), the snippet is printed.

Exit code 0 only when every step holds. Costs one real clip.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

MARKER = 'data-binaapp-hero-video="1"'


def _req(method: str, url: str, token: str | None = None, body: dict | None = None, timeout: float = 60.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Cache-Control", "no-cache")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def _login(api: str, email: str, password: str) -> str:
    status, raw = _req("POST", f"{api}/api/v1/auth/login", body={"email": email, "password": password})
    if status != 200:
        sys.exit(f"login failed: HTTP {status} {raw[:300]}")
    data = json.loads(raw)
    token = data.get("access_token") or (data.get("session") or {}).get("access_token")
    if not token:
        sys.exit(f"login returned no access_token: {raw[:300]}")
    return token


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--website-id", required=True)
    ap.add_argument("--token")
    ap.add_argument("--email")
    ap.add_argument("--password")
    ap.add_argument("--style", default="cinematic")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--image-url", default=None)
    ap.add_argument("--timeout", type=float, default=720.0, help="seconds to wait for the job")
    ap.add_argument("--disconnect", action="store_true", help="stop polling for 90s mid-job")
    args = ap.parse_args()

    api = args.api.rstrip("/")
    token = args.token or (_login(api, args.email, args.password) if args.email else None)
    if not token:
        sys.exit("need --token or --email/--password")

    t0 = time.time()

    def log(msg: str) -> None:
        print(f"[{time.strftime('%H:%M:%S')} +{time.time() - t0:6.1f}s] {msg}", flush=True)

    # 0. the site, before
    status, raw = _req("GET", f"{api}/api/v1/websites/{args.website_id}/hero-video", token)
    if status != 200:
        sys.exit(f"GET hero-video state failed: HTTP {status} {raw[:300]}")
    before = json.loads(raw)
    log(f"before: has_video={before.get('has_video')} hero_found={before.get('hero_found')} "
        f"allowed={before.get('allowed')} job={before.get('job')}")
    if not before.get("hero_found"):
        sys.exit("no hero on this page — pick a website with a hero section")
    if before.get("job"):
        sys.exit(f"a job is already in flight for this site: {before['job']}")

    # 1. start
    body = {"style": args.style}
    if args.prompt:
        body["prompt"] = args.prompt
    if args.image_url:
        body["image_url"] = args.image_url
    status, raw = _req("POST", f"{api}/api/v1/websites/{args.website_id}/hero-video/generate", token, body)
    if status != 202:
        sys.exit(f"generate refused: HTTP {status} {raw[:400]}")
    started = json.loads(raw)
    job_id = started["job_id"]
    interval = max(2, int(started.get("poll_interval_seconds") or 8))
    log(f"job {job_id} accepted (status={started['status']}) — prompt: {started.get('prompt', '')[:120]}…")

    # 2/3. poll (read-only) until terminal
    deadline = t0 + args.timeout
    disconnected = False
    last = None
    while time.time() < deadline:
        if args.disconnect and not disconnected and time.time() - t0 > 20:
            log("DISCONNECT: not polling for 90 s — the server must finish the job on its own")
            time.sleep(90)
            disconnected = True
        status, raw = _req("GET", f"{api}/api/v1/websites/{args.website_id}/hero-video/jobs/{job_id}", token)
        if status != 200:
            log(f"poll HTTP {status}: {raw[:200]}")
            time.sleep(interval)
            continue
        last = json.loads(raw)
        log(f"poll: status={last['status']} provider_status={last.get('provider_status')} "
            f"elapsed={last.get('elapsed_seconds')}s error={last.get('error')}")
        if last["status"] in ("completed", "failed"):
            break
        time.sleep(interval)
    if not last or last["status"] != "completed":
        log(f"FAIL: job did not complete: {last}")
        return 2
    video_url = last.get("video_url")
    log(f"completed: applied={last.get('applied')} live_site_updated={last.get('live_site_updated')} "
        f"warning={last.get('warning')} video_url={video_url}")
    if not video_url or not last.get("live_site_updated"):
        log("FAIL: completed without a live update or a video URL")
        return 3

    # 4. the row
    status, raw = _req("GET", f"{api}/api/v1/websites/{args.website_id}/hero-video", token)
    after = json.loads(raw) if status == 200 else {}
    log(f"row: has_video={after.get('has_video')} settings.video_url={(after.get('settings') or {}).get('video_url')}")
    if not after.get("has_video") or (after.get("settings") or {}).get("video_url") != video_url:
        log("FAIL: the site's state does not report the new clip")
        return 4

    # 5. the live page
    status, raw = _req("GET", f"{api}/api/v1/websites/{args.website_id}", token)
    subdomain = (json.loads(raw).get("subdomain") if status == 200 else None) or (json.loads(raw).get("website") or {}).get("subdomain")
    if not subdomain:
        log(f"FAIL: could not read the subdomain from GET /api/v1/websites/{args.website_id}: HTTP {status} {raw[:200]}")
        return 5
    live_url = f"https://{subdomain}.binaapp.my/?e2e={int(time.time())}"
    status, html = _req("GET", live_url, timeout=30)
    log(f"live page {live_url}: HTTP {status}, {len(html)} bytes")
    has_marker = MARKER in html
    video_tag = re.search(r"<video\b[^>]*class=\"binaapp-hero-video\"[^>]*>.*?</video>", html, re.S)
    has_source = bool(video_tag and video_url in video_tag.group(0))
    log(f"live page: marker={has_marker} video_tag={bool(video_tag)} source_matches_job={has_source}")
    if video_tag:
        print("---- live <video> snippet ----")
        print(video_tag.group(0)[:900])
        print("------------------------------")
    hero_open = re.search(r"<[a-z]+\b[^>]*" + re.escape(MARKER) + r"[^>]*>", html)
    if hero_open:
        print("---- hero opening tag ----")
        print(hero_open.group(0)[:400])
        print("--------------------------")
    if not (has_marker and has_source):
        log("FAIL: the live page does not carry the clip")
        return 6
    log("PASS: clip generated, persisted, injected and served live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
