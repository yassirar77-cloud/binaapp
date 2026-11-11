"""The golden suite, offline, as a pytest: every fixture merchant composes,
passes the structural checks and the visual gate's measured checks.
Browser tests skip where no Chromium is installed; the structural checks
always run. The CI workflow runs the same thing through scripts/golden_run.py
and keeps the screenshots."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from golden_run import build_site, list_fixtures, structural_checks  # noqa: E402

HAS_BROWSER = bool(os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")) or bool(__import__("app.services.browser_budget", fromlist=["x"]).headless_shell_dirs())
FIXTURES = list_fixtures()


@pytest.fixture(autouse=True)
def _composed_mode(monkeypatch):
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "deterministic")
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "false")
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")


def test_five_fixtures_present():
    assert sorted(f["name"] for f in FIXTURES) == ["agp", "kedai_telefon", "kek", "mamak", "salon"]


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["name"] for f in FIXTURES])
def test_golden_site_builds_and_passes_structural_checks(fixture):
    html, info = asyncio.run(build_site(fixture, mode="offline"))
    assert info["composed"] and info["validation_ok"], info["validation_errors"]
    report = structural_checks(html, fixture)
    assert report["ok"], {k: v for k, v in report["checks"].items() if not v} | {"missing": report["missing_items"], "prices": report["missing_prices"]}
    expect = fixture.get("expect", {})
    if expect.get("language"):
        assert f'<html lang="{expect["language"]}"' in html


@pytest.mark.skipif(not HAS_BROWSER, reason="no headless browser")
@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["name"] for f in FIXTURES])
def test_golden_site_passes_visual_gate(fixture):
    from app.services.visual_gate import run_gate
    html, _ = asyncio.run(build_site(fixture, mode="offline"))
    req = fixture["request"]
    rep = asyncio.run(run_gate(
        html, expect_map=bool(req.get("include_maps", True) and req.get("location_address")),
        expect_whatsapp=bool(req.get("whatsapp_number")), language=req.get("language", "ms"),
    ))
    if not rep.rendered:
        pytest.skip(rep.error)
    assert rep.passed, rep.summary() + " :: " + "; ".join(c.detail for c in rep.failed)


# ---------------------------------------------------------------------------
# The burger hero (live agp build, 2026-11-08)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["name"] for f in FIXTURES])
def test_golden_hero_prompt_is_about_the_merchant(fixture):
    """agp's hero photo was generated from "featuring Set A – Ayam Gepuk ...,
    a stacked burger and fries on kraft paper": the design direction's
    example subject, and menu labels the model lettered into the picture."""
    from golden_run import hero_prompt_check
    res = hero_prompt_check(fixture)
    assert res["ok"], res


def _png(colour, size):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def slow_image_server():
    """Photos served after a delay, like a Cloudinary transform on its first
    request: the live screenshots caught the cards before they were drawn."""
    import http.server
    import threading
    import time as _time
    images = {"/burger.png": _png((150, 75, 20), (1600, 900)), "/ayam.png": _png((20, 160, 60), (800, 600)),
              "/teh.png": _png((30, 60, 200), (800, 600))}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = images.get(self.path.split("?")[0])
            _time.sleep(1.5)
            self.send_response(200 if body else 404)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(body or b"")

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.mark.skipif(not HAS_BROWSER, reason="no headless browser")
def test_golden_burger_hero_is_replaced_and_card_photos_are_kept(monkeypatch, slow_image_server):
    """The agp page with a burger hero and two drawn card photos, through
    the gate the job worker runs: the hero becomes the photo-free hero, both
    card photos stay (each judged on its own), and a "cut off at the bottom
    edge" complaint the measurements do not confirm fails nothing."""
    import io
    import json
    import re
    from PIL import Image
    from app.services.visual_gate import gate_with_recovery

    fixture = next(f for f in FIXTURES if f["name"] == "agp")
    html, _ = asyncio.run(build_site(fixture, mode="offline"))
    base = slow_image_server
    html = html.replace('class="bs-hero bs-hero-solid"', 'class="bs-hero"', 1)
    html = re.sub(r'(<section class="bs-hero"[^>]*>)', r'\1<div class="bs-hero-media"><img src="' + base + '/burger.png" alt="" width="1600" height="900" fetchpriority="high"></div><div class="bs-hero-scrim"></div>', html, count=1)
    cards = re.findall(r'<li class="bmf-card bmf-text-only[^"]*">', html)
    assert len(cards) >= 2
    for card, src in zip(cards[:2], ("ayam.png", "teh.png")):
        html = html.replace(card, card.replace(" bmf-text-only", "") + f'<div class="bmf-media"><img src="{base}/{src}" alt="" loading="lazy" decoding="async"><span class="bmf-ai-label">Gambar hiasan</span></div>', 1)

    asked = {"cards": [], "hero": 0}

    async def vision(messages):
        content = messages[0]["content"]
        text = content[0]["text"]
        if "ONE card" in text:
            for part in content[2::2]:
                import base64
                im = Image.open(io.BytesIO(base64.b64decode(part["image_url"]["url"].split(",", 1)[1]))).convert("RGB")
                asked["cards"].append(im.getpixel((im.size[0] // 2, im.size[1] // 2)))
            return json.dumps({"mismatches": []})
        if "hero (top banner)" in text:
            asked["hero"] += 1
            return json.dumps({"matches": False, "shows": "a burger and fries", "reason": "the shop sells ayam gepuk"})
        return json.dumps({"issues": [{"type": "cutoff", "where": "menu", "detail": "card cut off at the bottom edge of the screen", "severity": "high"}], "overall": "fail"})

    req = fixture["request"]
    out, rep = asyncio.run(gate_with_recovery(
        html, expect_map=False, expect_whatsapp=True, item_names=[i["name"] for i in req["menu_items"]], call_vision=vision,
        business={"name": req["business_name"], "type": req["business_type"], "description": req["description"],
                  "items": [i["name"] for i in req["menu_items"]]},
    ))
    if not rep.rendered:
        pytest.skip(rep.error)
    assert rep.passed, rep.summary()
    assert "photo_free_hero" in rep.fixes and asked["hero"] == 1
    assert 'class="bs-hero bs-hero-solid"' in out and "burger.png" not in out
    assert "ayam.png" in out and "teh.png" in out
    # Both card photos were drawn when they were cropped (their colour, not
    # the grey placeholder box).
    assert asked["cards"][:2] == [(20, 160, 60), (30, 60, 200)]


# ---------------------------------------------------------------------------
# A live run without keys must say so, not pass as an offline run
# ---------------------------------------------------------------------------

class _Keys:
    def __init__(self, **kw):
        self.deepseek_api_key = kw.get("deepseek", "")
        self.qwen_api_key = kw.get("qwen", "")
        self.zai_api_key = kw.get("zai", "")
        self.stability_api_key = kw.get("stability", "")


def test_live_run_names_every_missing_key(monkeypatch):
    from golden_run import live_missing
    monkeypatch.setenv("IMAGE_PROVIDER", "stability")
    missing = live_missing(_Keys())
    assert len(missing) == 3 and "text models" in missing[0] and "vision reviewer" in missing[1] and "STABILITY_API_KEY" in missing[2]
    assert live_missing(_Keys(qwen="k", stability="k")) == []
    # Z.ai images need the Z.ai key, whatever else is set.
    monkeypatch.setenv("IMAGE_PROVIDER", "zai")
    assert [m for m in live_missing(_Keys(qwen="k", deepseek="k", stability="k")) if "ZAI_API_KEY" in m]
    assert live_missing(_Keys(qwen="k", zai="k")) == []


def test_live_run_without_keys_does_not_start(monkeypatch, tmp_path, capsys):
    import argparse

    import golden_run
    from app.services import ai_service as svc
    monkeypatch.setattr(svc, "AIService", lambda: _Keys())
    monkeypatch.setenv("IMAGE_PROVIDER", "stability")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    async def _never(*a, **kw):
        raise AssertionError("a live run with no keys must not build anything")
    monkeypatch.setattr(golden_run, "run_fixture", _never)
    args = argparse.Namespace(mode="live", out=str(tmp_path / "out"), fixtures=str(golden_run.FIXTURES_DIR),
                              baseline=str(golden_run.BASELINE_DIR), only=None, update_baseline=False)
    assert asyncio.run(golden_run.main_async(args)) == 3
    assert "Live golden run not started" in capsys.readouterr().err
    assert "NOT RUN" in summary.read_text(encoding="utf-8")
