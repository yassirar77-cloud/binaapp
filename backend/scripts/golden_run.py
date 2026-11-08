#!/usr/bin/env python3
"""Golden suite runner — stage 3 of the quality system.

Five fixture merchants (tests/golden/fixtures/*.json) are built end to end
the way the job worker builds a site — generate → widgets → visual gate —
and every artefact is written out:

    <out>/<name>/site.html        the page as the customer would get it
    <out>/<name>/mobile.png       390 px full-page screenshot
    <out>/<name>/desktop.png      1280 px full-page screenshot
    <out>/<name>/gate.json        the visual gate report
    <out>/<name>/checks.json      structural checks (items, prices, facts, slots)
    <out>/<name>/diff.png|json    pixel diff against tests/golden/baseline/<name>-mobile.png
    <out>/summary.json, summary.md

Pass/fail per fixture = the visual gate's measured checks AND the
structural checks. The pixel diff is stored for eyes (copy and photos
vary between runs) and never fails the run on its own.

    python scripts/golden_run.py --mode offline --out golden-out
    python scripts/golden_run.py --mode live --out golden-out          # needs model keys
    python scripts/golden_run.py --mode offline --update-baseline     # refresh baselines

offline: no model keys, no images — the library theme and the fallback
copy, which is still the exact composed layout and the full gate.
live: the real pipeline (plan, copy, images, vision review).
"""

from __future__ import annotations

import argparse
import asyncio
import html as _html
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(HERE))

FIXTURES_DIR = BACKEND / "tests" / "golden" / "fixtures"
BASELINE_DIR = BACKEND / "tests" / "golden" / "baseline"
PLACEHOLDER_MARKERS = ("[ISI", "contoh:", "{{", "}}", "Lorem ipsum", "Nasi Kandar Daging Crystal")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def load_fixture(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    req = data["request"]
    items = req.get("menu_items")
    if isinstance(items, str) and items.startswith("@"):
        ref = (path.parent / items[1:]).resolve()
        payload = json.loads(ref.read_text(encoding="utf-8"))
        req["menu_items"] = payload["menu_items"] if isinstance(payload, dict) else payload
    data.setdefault("name", path.stem)
    return data


def list_fixtures(directory: Path = FIXTURES_DIR, only: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    out = []
    for p in sorted(directory.glob("*.json")):
        if only and p.stem not in only:
            continue
        out.append(load_fixture(p))
    return out


# ---------------------------------------------------------------------------
# Build (what the job worker does)
# ---------------------------------------------------------------------------

def _visible(html: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", text)))


async def build_site(fixture: Dict[str, Any], *, mode: str, service=None) -> Tuple[str, Dict[str, Any]]:
    """generate_website → widgets, exactly like run_generation_task.
    Returns (html, build_info)."""
    from app.models.schemas import WebsiteGenerationRequest
    from app.services import ai_service as svc
    from app.services.templates import TemplateService

    req = WebsiteGenerationRequest(**fixture["request"])
    service = service or svc.AIService()
    if mode == "offline":
        service.deepseek_api_key = service.zai_api_key = service.qwen_api_key = ""
        image_choice = "none"
    else:
        image_choice = "ai"
    t0 = time.time()
    resp = await service.generate_website(req, image_choice=image_choice)
    html = resp.html_content
    wa_digits = svc.AIService._normalize_wa_digits(req.whatsapp_number)
    features: List[str] = []
    if req.include_whatsapp and wa_digits:
        features.append("whatsapp")
    if req.include_maps and req.location_address:
        features.append("maps")
    if getattr(req, "include_contact_form", True):
        features.append("contact")
    if getattr(req, "include_social", False):
        features.append("social")
    user_data = {
        "phone": wa_digits, "address": req.location_address or "", "business_name": req.business_name, "name": req.business_name,
        "language": req.language.value if hasattr(req.language, "value") else str(req.language), "business_type": req.business_type,
        "description": req.description, "email": "", "theme_tokens": svc.extract_theme_tokens(html),
        "social_media": getattr(req, "social_media", None) or {}, "payment": {m: True for m in (req.payment_methods or [])},
        "generation_count": 1,
    }
    html = TemplateService().inject_integrations(html, features, user_data)
    info = {
        "mode": mode, "seconds": round(time.time() - t0, 1), "chars": len(html), "validation_ok": resp.validation_ok,
        "validation_errors": resp.validation_errors, "ai_images": resp.ai_images_count,
        "theme": getattr(service, "_last_theme", None), "copy_source": (getattr(service, "_last_copy", None) or {}).get("source"),
        "composed": "binaapp-composer" in html[:4000], "features": features,
    }
    return html, info


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------

def structural_checks(html: str, fixture: Dict[str, Any]) -> Dict[str, Any]:
    req, expect = fixture["request"], fixture.get("expect", {})
    text = _visible(html)
    items = req.get("menu_items") or []
    missing = [i["name"] for i in items if i["name"] not in text]
    wrong_price = [i["name"] for i in items if i.get("price") and f"RM{float(str(i['price']).replace('RM', '').replace(',', '')):.2f}" not in text]
    categories = [c for c in dict.fromkeys(i.get("category", "") for i in items) if c]
    placeholders = [m for m in PLACEHOLDER_MARKERS if m in text]
    wa = bool(req.get("whatsapp_number"))
    checks: Dict[str, bool] = {
        "all_items_present": not missing,
        "all_prices_present": not wrong_price,
        "categories_present": all(c in text for c in categories),
        "no_placeholder_text": not placeholders,
        "no_empty_sections": not re.search(r"<section\b[^>]*>(?:\s|<!--.*?-->)*</section>", html, flags=re.S | re.I),
        "tel_link": (not wa) or 'href="tel:+60' in html,
        "whatsapp_link": (not wa) or "wa.me/60" in html,
        "floating_whatsapp": (not wa) or 'id="whatsapp-button"' in html,
        "lang_attribute": f'<html lang="{req.get("language", "ms")}"' in html,
        "theme_color_meta": 'name="theme-color"' in html,
        "favicon": 'rel="icon"' in html,
        "jsonld": "application/ld+json" in html,
        "business_name_in_title": req["business_name"] in (re.search(r"<title>(.*?)</title>", html, flags=re.S | re.I) or [None, ""])[1],
    }
    if expect.get("map"):
        checks["map_iframe"] = bool(re.search(r'<iframe\b[^>]*src="https://www\.google\.com/maps\?q=', html))
        checks["map_buttons"] = "waze.com/ul" in html and ("Buka di Google Maps" in html or "Open in Google Maps" in html)
    if expect.get("chips"):
        checks["spice_chips"] = len(re.findall(r'class="bs-chip"', html)) >= int(expect["chips"])
    if expect.get("banners"):
        checks["info_banners"] = len(re.findall(r'class="bs-banner"', html)) >= int(expect["banners"])
    if expect.get("coming_soon"):
        checks["coming_soon"] = ("Akan datang" in text or "Coming soon" in text) and len(re.findall(r'<ul class="bs-soon-list">(.*?)</ul>', html, flags=re.S)) == 1
    if expect.get("is_24h"):
        checks["open_24h_copy"] = "24 jam" in text or "24 hours" in text
    if expect.get("socials"):
        checks["social_links"] = sum(1 for k in ("instagram.com", "tiktok.com", "facebook.com") if k in html) >= int(expect["socials"])
    if expect.get("dark"):
        checks["dark_background"] = bool(re.search(r"--bg-color:#(0|1)[0-9A-Fa-f]{5}", html))
    if req.get("business_type") in ("food", "bakery"):
        checks["fnb_whatsapp_prefill"] = "saya%20nak%20order" in html or "like%20to%20order" in html
    return {
        "ok": all(checks.values()), "checks": checks, "missing_items": missing, "missing_prices": wrong_price,
        "placeholders_found": placeholders,
    }


# ---------------------------------------------------------------------------
# Screenshot diff
# ---------------------------------------------------------------------------

def pixel_diff(png_a: Optional[bytes], png_b: Optional[bytes], out_png: Optional[Path] = None) -> Dict[str, Any]:
    """Fraction of differing pixels over the common area + a diff image."""
    if not png_a or not png_b:
        return {"compared": False, "reason": "missing image"}
    try:
        import io
        from PIL import Image, ImageChops
        a = Image.open(io.BytesIO(png_a)).convert("RGB")
        b = Image.open(io.BytesIO(png_b)).convert("RGB")
    except Exception as err:
        return {"compared": False, "reason": str(err)}
    w = min(a.width, b.width)
    h = min(a.height, b.height)
    a_c, b_c = a.crop((0, 0, w, h)), b.crop((0, 0, w, h))
    diff = ImageChops.difference(a_c, b_c).convert("L").point(lambda v: 255 if v > 24 else 0)
    changed = sum(1 for v in diff.getdata() if v)
    ratio = changed / float(w * h) if w and h else 0.0
    if out_png is not None:
        try:
            side = Image.new("RGB", (w * 3, h), "white")
            side.paste(a_c, (0, 0))
            side.paste(b_c, (w, 0))
            red = Image.new("RGB", (w, h), (220, 30, 30))
            side.paste(red, (w * 2, 0), diff)
            side.save(out_png, format="PNG", optimize=True)
        except Exception:
            pass
    return {"compared": True, "changed_ratio": round(ratio, 4), "height_baseline": b.height, "height_now": a.height, "width": w}


# ---------------------------------------------------------------------------
# One fixture
# ---------------------------------------------------------------------------

async def run_fixture(fixture: Dict[str, Any], *, mode: str, out_dir: Path, baseline_dir: Path, update_baseline: bool,
                      service=None) -> Dict[str, Any]:
    from app.services.visual_gate import run_gate
    name = fixture["name"]
    target = out_dir / name
    target.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {"name": name, "title": fixture.get("title", name), "mode": mode}
    try:
        html, info = await build_site(fixture, mode=mode, service=service)
    except Exception as err:
        result.update({"ok": False, "error": f"build failed: {type(err).__name__}: {err}"})
        (target / "error.txt").write_text(result["error"], encoding="utf-8")
        return result
    (target / "site.html").write_text(html, encoding="utf-8")
    result["build"] = info
    structural = structural_checks(html, fixture)
    (target / "checks.json").write_text(json.dumps(structural, indent=1, ensure_ascii=False), encoding="utf-8")
    result["structural"] = structural
    req = fixture["request"]
    call_vision = None
    if mode == "live" and service is not None and (service.qwen_api_key or service.zai_api_key):
        call_vision = service._call_gate_vision_model
    gate = await run_gate(
        html, expect_map=bool(req.get("include_maps", True) and req.get("location_address")),
        expect_whatsapp=bool(req.get("whatsapp_number")), item_names=[i["name"] for i in (req.get("menu_items") or [])],
        language=req.get("language", "ms"), call_vision=call_vision, desktop_full_page=True,
    )
    (target / "gate.json").write_text(json.dumps(gate.as_dict(), indent=1, ensure_ascii=False), encoding="utf-8")
    if gate.mobile_png:
        (target / "mobile.png").write_bytes(gate.mobile_png)
    if gate.desktop_png:
        (target / "desktop.png").write_bytes(gate.desktop_png)
    result["gate"] = {"rendered": gate.rendered, "passed": gate.passed, "summary": gate.summary(), "error": gate.error,
                      "failed": [c.name for c in gate.failed], "soft": [c.name for c in gate.checks if not c.ok and not c.hard]}
    baseline = baseline_dir / f"{name}-mobile.png"
    if gate.mobile_png and update_baseline:
        baseline_dir.mkdir(parents=True, exist_ok=True)
        baseline.write_bytes(gate.mobile_png)
        result["baseline"] = "updated"
    elif gate.mobile_png and baseline.exists():
        d = pixel_diff(gate.mobile_png, baseline.read_bytes(), target / "diff.png")
        (target / "diff.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        result["diff"] = d
    else:
        result["diff"] = {"compared": False, "reason": "no baseline"}
    # validation_ok is what production flags for manual review: a golden
    # site that would be flagged is a failing golden site.
    result["ok"] = bool(structural["ok"] and gate.rendered and gate.passed and info.get("validation_ok", True))
    if not gate.rendered:
        result["ok"] = False
        result["error"] = f"gate could not render: {gate.error}"
    return result


def summary_markdown(results: List[Dict[str, Any]]) -> str:
    rows = ["| fixture | build | structural | visual gate | diff vs baseline | time |", "|---|---|---|---|---|---|"]
    for r in results:
        if "error" in r and "build" not in r:
            rows.append(f"| {r['name']} | ❌ {r['error'][:80]} | – | – | – | – |")
            continue
        s = r.get("structural", {})
        bad = [k for k, v in s.get("checks", {}).items() if not v]
        g = r.get("gate", {})
        d = r.get("diff", {})
        diff_txt = f"{d['changed_ratio'] * 100:.1f}% px" if d.get("compared") else d.get("reason", "–")
        v_ok = r.get("build", {}).get("validation_ok", True)
        rows.append(
            f"| {r['name']} | {'✅' if r.get('build', {}).get('composed') else '🅰️ freeform'} {r['build']['chars']} chars{'' if v_ok else ' ⚠️ validation'} | "
            f"{'✅' if s.get('ok') else '❌ ' + ', '.join(bad[:4])} | {'✅' if g.get('passed') else '❌ ' + ', '.join(g.get('failed') or [g.get('error') or '?'])} | "
            f"{diff_txt} | {r['build']['seconds']}s |"
        )
    ok = sum(1 for r in results if r.get("ok"))
    return "\n".join(rows) + f"\n\n**{ok}/{len(results)} golden sites pass.**\n"


async def main_async(args: argparse.Namespace) -> int:
    os.environ.setdefault("BINAAPP_PAGE_MODE", "deterministic")
    os.environ.setdefault("IMAGE_CHECK_ENABLED", "false" if args.mode == "offline" else "true")
    os.environ.setdefault("DESIGN_CRITIQUE_ENABLED", "false")
    os.environ.setdefault("DESIGN_PLAN_STORE_ENABLED", "false")
    os.environ.setdefault("VISUAL_GATE_MODE", "enforce")
    from app.services import ai_service as svc
    service = svc.AIService()
    fixtures = list_fixtures(Path(args.fixtures), args.only)
    if not fixtures:
        print("no fixtures found", file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for fx in fixtures:
        print(f"▶ {fx['name']}: {fx.get('title', '')}", flush=True)
        r = await run_fixture(fx, mode=args.mode, out_dir=out_dir, baseline_dir=Path(args.baseline), update_baseline=args.update_baseline, service=service)
        results.append(r)
        print(f"  {'PASS' if r.get('ok') else 'FAIL'} — gate: {r.get('gate', {}).get('summary', r.get('error'))}; "
              f"structural: {'ok' if r.get('structural', {}).get('ok') else [k for k, v in r.get('structural', {}).get('checks', {}).items() if not v]}", flush=True)
    (out_dir / "summary.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    md = summary_markdown(results)
    (out_dir / "summary.md").write_text(md, encoding="utf-8")
    print("\n" + md)
    step_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(f"## Golden suite ({args.mode})\n\n{md}\n")
    return 0 if all(r.get("ok") for r in results) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("offline", "live"), default="offline")
    ap.add_argument("--out", default="golden-out")
    ap.add_argument("--fixtures", default=str(FIXTURES_DIR))
    ap.add_argument("--baseline", default=str(BASELINE_DIR))
    ap.add_argument("--only", nargs="*", help="fixture names to run")
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
