"""Screenshot the golden set and build a paired side-by-side review gallery.

Reads docs/previews/golden/{old,new}/*.html, screenshots each at desktop
(1440×900) and mobile (375×812) viewports, and writes:

    docs/previews/golden/screenshots/{prompt_id}__{pipeline}__{viewport}.png
    docs/previews/golden/review.html   ← open this for manual visual review

The gallery pairs OLD vs NEW per prompt per viewport, with the producing
model IDs (from each run's meta.json) printed under every image. Human
visual review of review.html is the quality gate; lint/self-scores are
secondary.

Requires playwright:  pip install playwright
(This repo's cloud env pre-installs Chromium at PLAYWRIGHT_BROWSERS_PATH —
do NOT run `playwright install` there.)

Usage (from backend/):
    python scripts/screenshot_golden.py
    python scripts/screenshot_golden.py --golden-dir ../docs/previews/golden
"""

from __future__ import annotations

import argparse
import glob
import html as html_mod
import json
import os
import sys
from pathlib import Path

_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _backend_dir)

DEFAULT_GOLDEN = Path(_backend_dir).parent / "docs" / "previews" / "golden"

VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 375, "height": 812},
}


def _launch_browser(p):
    """Launch Chromium; fall back to the pre-installed system Chromium if the
    playwright-managed download is absent (cloud env). Honors HTTPS_PROXY so
    CDN assets (Tailwind, Google Fonts) load in proxied environments."""
    kwargs = {}
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if proxy:
        kwargs["proxy"] = {"server": proxy}
    try:
        return p.chromium.launch(**kwargs)
    except Exception:
        candidates = glob.glob("/opt/pw-browsers/**/chrome-linux/chrome", recursive=True)
        if not candidates:
            raise
        return p.chromium.launch(executable_path=candidates[0], **kwargs)


def screenshot_all(golden_dir: Path) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("playwright not installed: pip install playwright")

    shots_dir = golden_dir / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    with sync_playwright() as p:
        browser = _launch_browser(p)
        for pipeline_dir in sorted(golden_dir.glob("*")):
            if pipeline_dir.name not in ("old", "new"):
                continue
            for html_file in sorted(pipeline_dir.glob("*.html")):
                prompt_id = html_file.stem
                meta_file = html_file.with_suffix(".meta.json")
                meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
                for vp_name, vp in VIEWPORTS.items():
                    page = browser.new_page(viewport=vp, ignore_https_errors=True)
                    page.goto(html_file.resolve().as_uri())
                    page.wait_for_timeout(1500)  # let fonts + entrance animations settle
                    out = shots_dir / f"{prompt_id}__{pipeline_dir.name}__{vp_name}.png"
                    page.screenshot(path=str(out), full_page=True)
                    page.close()
                    print(f"  {out.name}")
                entries.append({
                    "prompt_id": prompt_id,
                    "pipeline": pipeline_dir.name,
                    "meta": meta,
                })
        browser.close()
    return entries


def build_gallery(golden_dir: Path, entries: list[dict]) -> Path:
    by_prompt: dict[str, dict] = {}
    for e in entries:
        by_prompt.setdefault(e["prompt_id"], {})[e["pipeline"]] = e["meta"]

    def model_line(meta: dict) -> str:
        models = meta.get("models", {})
        parts = [
            f"deepseek: {models.get('deepseek_model', '?')}",
            f"pro: {models.get('deepseek_model_pro', '?')}",
        ]
        if meta.get("duration_s") is not None:
            parts.append(f"{meta['duration_s']}s")
        lint = meta.get("lint", {})
        parts.append("lint OK" if lint.get("ok") else f"lint: {len(lint.get('issues', []))} issue(s)")
        return " · ".join(parts)

    rows = []
    for prompt_id in sorted(by_prompt):
        metas = by_prompt[prompt_id]
        cells_by_vp = []
        for vp_name in VIEWPORTS:
            cells = []
            for pipeline in ("old", "new"):
                img = f"screenshots/{prompt_id}__{pipeline}__{vp_name}.png"
                if (golden_dir / img).exists():
                    info = html_mod.escape(model_line(metas.get(pipeline, {})))
                    cells.append(
                        f"<figure><figcaption><b>{pipeline.upper()}</b> — {info}</figcaption>"
                        f'<a href="{img}" target="_blank"><img src="{img}" loading="lazy"></a></figure>'
                    )
                else:
                    cells.append(f"<figure><figcaption><b>{pipeline.upper()}</b> — missing</figcaption></figure>")
            cells_by_vp.append(
                f"<h3>{vp_name}</h3><div class='pair'>{''.join(cells)}</div>"
            )
        rows.append(f"<section><h2>{html_mod.escape(prompt_id)}</h2>{''.join(cells_by_vp)}</section>")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Golden Set Review — OLD vs NEW</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f5f5f4; }}
  section {{ background: #fff; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;
             box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  h2 {{ margin-top: 0; font-family: ui-monospace, monospace; }}
  .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
  figure {{ margin: 0; }}
  figcaption {{ font-size: .8rem; color: #555; padding: .25rem 0; }}
  img {{ width: 100%; border: 1px solid #ddd; border-radius: 6px;
         max-height: 70vh; object-fit: contain; object-position: top; background: #fff; }}
</style>
</head>
<body>
<h1>Golden Set Review — OLD vs NEW pipeline</h1>
<p>Click any image for full size. Model IDs under each shot come from the run's meta.json (env-pinned).</p>
{''.join(rows)}
</body>
</html>"""
    out = golden_dir / "review.html"
    out.write_text(page, encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-dir", default=str(DEFAULT_GOLDEN))
    args = parser.parse_args()

    golden_dir = Path(args.golden_dir)
    if not golden_dir.is_dir():
        print(f"No golden dir at {golden_dir}. Run generate_golden_set.py first.")
        return 2

    entries = screenshot_all(golden_dir)
    if not entries:
        print("No golden HTML found. Run generate_golden_set.py first.")
        return 2
    out = build_gallery(golden_dir, entries)
    print(f"\nReview gallery: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
