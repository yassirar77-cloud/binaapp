"""Stage 2 of the quality system: the visual QA gate.

Measurements run in a real browser (skipped where none is installed);
the verdict logic, the vision parser, the targeted fixes and the
recovery loop are tested without one.
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest

from app.services import visual_gate as vg
from app.services.visual_gate import (
    Check, GateReport, VisualGateFailed, auto_fix, build_vision_messages, drop_item_photos, evaluate_checks,
    gate_with_recovery, parse_vision, run_gate, targeted_fix_css,
)

HAS_BROWSER = bool(os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")) or bool(__import__("app.services.browser_budget", fromlist=["x"]).headless_shell_dirs())
browser = pytest.mark.skipif(not HAS_BROWSER, reason="no headless browser")

GOOD = """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width"><style>
body{margin:0;font-family:sans-serif;color:#111;background:#fff}#home{padding:24px 16px 120px;background:#222;color:#fff}
.btn{display:inline-flex;gap:6px;padding:12px 18px;background:#0E7466;color:#fff;border-radius:999px;text-decoration:none}
.btn svg{width:16px;height:16px;fill:#fff}#whatsapp-button{position:fixed;bottom:20px;right:20px;width:60px;height:60px;border-radius:50%;background:#25D366;z-index:1000;display:flex;align-items:center;justify-content:center}
</style></head><body><section id="home"><h1>Kedai Kopi</h1><p>Kopi sedap.</p>
<a class="btn" href="https://wa.me/60126973105"><svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>Pesan di WhatsApp</a></section>
<section><h2>Menu</h2><p>Teh tarik RM2.50</p><a class="btn" href="tel:+60126973105"><svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>Telefon</a></section>
<a id="whatsapp-button" href="https://wa.me/60126973105" aria-label="WhatsApp"><svg viewBox="0 0 10 10" width="30" height="30"><circle cx="5" cy="5" r="4" fill="#fff"/></svg></a>
</body></html>"""

BAD = """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width"><style>
body{margin:0;font-family:sans-serif}.wide{width:600px;background:#eee}.low{color:#bbb;background:#fff}
#home{position:relative;min-height:600px;background:#333;color:#fff}.strip{position:absolute;bottom:0;left:0;right:0;background:#fff;color:#000;height:120px}
.cta{display:inline-block;padding:12px 20px;background:#25D366;color:#fff;position:absolute;bottom:40px;left:20px}
.clip{width:120px;white-space:nowrap;overflow:hidden;text-overflow:clip}</style></head><body>
<section id="home"><h1>Kedai</h1><a class="cta" href="https://wa.me/60126973105">Pesan</a><div class="strip">Level 1 Level 2 Level 3</div></section>
<section><div class="wide md:flex">too wide</div><p class="low">faint text here</p><p class="clip">a very long unbreakable line of text that cannot fit</p>
<img src="https://example.invalid/x.jpg" alt="x"><a class="btn" href="tel:+60126973105">Telefon</a></section>
</body></html>"""


# ---------------------------------------------------------------------------
# Verdict logic (no browser)
# ---------------------------------------------------------------------------

def _measured(**over):
    base = {"innerWidth": 390, "scrollWidth": 390, "heroCtas": [], "floating": [{"id": "whatsapp-button", "isWa": True, "obstructedBy": None}],
            "clipped": [], "lowContrast": [], "images": [], "ctas": [], "map": None}
    base.update(over)
    return base


def test_evaluate_checks_all_clean():
    checks = evaluate_checks(_measured(), _measured(innerWidth=1280, scrollWidth=1280), expect_map=False, expect_whatsapp=True)
    assert all(c.ok for c in checks)
    assert {c.name for c in checks} == {"no_horizontal_overflow", "hero_cta_unobstructed", "floating_button_unobstructed", "no_clipped_text", "contrast_aa", "images_load", "cta_icon_and_label"}


def test_evaluate_checks_each_failure():
    m = _measured(
        scrollWidth=600,
        heroCtas=[{"text": "Pesan", "obstructedBy": {"by": "div.strip", "fixed": False}}],
        floating=[{"id": "whatsapp-button", "isWa": True, "obstructedBy": {"by": "div.banner", "fixed": True}}],
        clipped=[{"text": "x", "path": "p.clip"}],
        lowContrast=[{"text": "faint", "path": "p.low", "ratio": 1.9, "need": 4.5, "fg": "rgb(187, 187, 187)", "bg": "rgb(255, 255, 255)"}],
        images=[{"src": "https://x/y.jpg", "ok": False}],
        ctas=[{"text": "Pesan", "hasIcon": False, "hasLabel": True}, {"text": "", "hasIcon": True, "hasLabel": False}],
        map={"present": True, "width": 350, "height": 60, "visibleHeight": 60, "obstructedBy": None, "buttons": [{"text": "Waze", "inViewport": True}]},
    )
    checks = {c.name: c for c in evaluate_checks(m, _measured(innerWidth=1280, scrollWidth=1280), expect_map=True, expect_whatsapp=True)}
    for name in ("no_horizontal_overflow", "hero_cta_unobstructed", "floating_button_unobstructed", "no_clipped_text", "contrast_aa", "images_load", "cta_icon_and_label", "map_visible"):
        assert not checks[name].ok, name
    assert checks["cta_icon_and_label"].count == 2
    assert "need Google Maps + Waze" in checks["map_visible"].detail


def test_missing_floating_whatsapp_is_soft():
    checks = evaluate_checks(_measured(floating=[]), _measured(), expect_map=False, expect_whatsapp=True)
    soft = [c for c in checks if c.name == "floating_whatsapp_present"]
    assert soft and not soft[0].ok and not soft[0].hard


def test_report_summary_and_dict():
    r = GateReport(rendered=True, checks=[Check("a", True), Check("b", False, "bad", 2), Check("c", False, "soft", 1, hard=False)])
    assert not r.passed and r.summary() == "FAIL b(2)"
    d = r.as_dict()
    assert d["summary"] == "FAIL b(2)" and len(d["checks"]) == 3 and d["passed"] is False
    assert GateReport(rendered=False, error="boom").summary() == "not rendered (boom)"


# ---------------------------------------------------------------------------
# Vision review
# ---------------------------------------------------------------------------

def test_parse_vision_shapes():
    raw = '```json\n{"issues":[{"type":"overlap","where":"hero","detail":"strip over button","severity":"HIGH"},{"type":"other","where":"footer","detail":"meh","severity":"low"}],"photo_mismatches":[{"item":"Teh O Ice","reason":"shows fried chicken"},"Set A"],"overall":"fail"}\n```'
    v = parse_vision(raw)
    assert v["overall"] == "fail" and v["issues"][0]["severity"] == "high" and v["issues"][1]["severity"] == "low"
    assert [m["item"] for m in v["photo_mismatches"]] == ["Teh O Ice", "Set A"]
    assert parse_vision("nope") is None and parse_vision(None) is None and parse_vision("[]") is None
    assert parse_vision('{"issues": [], "photo_mismatches": [], "overall": "pass",}')["overall"] == "pass"


def test_vision_messages_tile_the_screenshot():
    from PIL import Image
    import io
    im = Image.new("RGB", (390, 5000), "white")
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    msgs = build_vision_messages(buf.getvalue(), item_names=["Set A", "Teh O"], language="ms")
    content = msgs[0]["content"]
    assert content[0]["type"] == "text" and "cut off" in content[0]["text"] and "SLICES" in content[0]["text"]
    assert "Do not judge the photos" in content[0]["text"]
    images = [c for c in content if c["type"] == "image_url"]
    assert 4 <= len(images) <= vg.VISION_MAX_TILES
    assert images[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert content[1] == {"type": "text", "text": f"Slice 1 of {len(images)}:"}


def test_tiles_overlap_and_cover_the_whole_page():
    """mamak's cards were cut in two by back-to-back 1200px slices and the
    model failed the page for "cut off at the bottom edge". Every slice now
    overlaps the next, and a 10,049px page (agp) is covered to the end."""
    from PIL import Image
    import io
    im = Image.new("RGB", (390, 10049), "white")
    for y in range(0, 10049, 50):  # a ruler: row y has red = y // 50 % 256
        im.paste((y // 50 % 256, 0, 0), (0, y, 390, min(y + 50, 10049)))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    tiles = [Image.open(io.BytesIO(t)) for t in vg._tiles(buf.getvalue())]
    assert len(tiles) <= vg.VISION_MAX_TILES
    tops, y = [], 0
    for t in tiles:
        tops.append(y)
        y += vg.VISION_TILE_HEIGHT - vg.VISION_TILE_OVERLAP
    for top, nxt in zip(tops, tops[1:]):
        assert nxt < top + vg.VISION_TILE_HEIGHT - 200  # >= 200px shared with the next slice
    assert tops[-1] + tiles[-1].size[1] == 10049  # the last slice reaches the bottom
    # The bottom row of each slice is inside the next one.
    for a, b in zip(tiles, tiles[1:]):
        assert a.getpixel((5, a.size[1] - 1)) == b.getpixel((5, vg.VISION_TILE_OVERLAP - 1))


def test_run_gate_vision_verdicts(monkeypatch):
    """A high-severity vision issue fails the gate; a photo mismatch is
    soft (fixed by dropping the photo); no verdict gates on measurements."""
    async def _render(html, **kw):
        return _measured(), _measured(innerWidth=1280, scrollWidth=1280), b"png", b"png", None
    monkeypatch.setattr(vg, "render", _render)

    async def _high(messages):
        if "A first reviewer reported" in messages[0]["content"][0]["text"]:
            return json.dumps({"confirmed": True, "evidence": "the strip covers the button"})
        return json.dumps({"issues": [{"slice": 1, "type": "overlap", "where": "hero", "detail": "strip over the button", "severity": "high"}], "photo_mismatches": [], "overall": "fail"})
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_high))
    assert not r.passed and [c.name for c in r.failed] == ["vision_review"]

    async def _mismatch(messages):
        return json.dumps({"issues": [], "photo_mismatches": [{"item": "Teh O Ice", "reason": "chicken"}], "overall": "pass"})
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_mismatch))
    assert r.passed and r.photo_mismatches == ["Teh O Ice"]
    assert any(c.name == "photo_matches_name" and not c.ok and not c.hard for c in r.checks)

    async def _none(messages):
        return None
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_none))
    assert r.passed and any(c.name == "vision_review" and c.ok and not c.hard for c in r.checks)


# ---------------------------------------------------------------------------
# Fixes
# ---------------------------------------------------------------------------

def test_targeted_fix_css_rules():
    r = GateReport(rendered=True, checks=[
        Check("no_clipped_text", False, "", 1, [{"path": "section>div.wide.md\\:flex"}]),
        Check("contrast_aa", False, "", 1, [{"path": "p.low", "fg": "rgb(187, 187, 187)", "bg": "rgb(255, 255, 255)", "need": 4.5}]),
        Check("hero_cta_unobstructed", False, "", 2, [
            {"obstructedBy": {"by": "section#home>div.strip", "fixed": False}},
            {"obstructedBy": {"by": "a#whatsapp-button", "fixed": True}},
        ]),
    ])
    css = targeted_fix_css(r)
    assert "section>div.wide.md\\:flex{max-width:100%!important" in css
    assert "p.low{color:#" in css and "color:#BBBBBB" not in css
    assert "section#home>div.strip{position:static!important" in css
    assert "a#whatsapp-button{position:static" not in css   # the floating button is never un-fixed


def test_targeted_fix_css_rejects_unsafe_selectors():
    r = GateReport(rendered=True, checks=[Check("no_clipped_text", False, "", 1, [{"path": "div{}</style><script>"}])])
    assert targeted_fix_css(r) == ""


def test_drop_item_photos_makes_card_text_only():
    html = ('<ul><li class="bmf-card"><div class="bmf-media"><img src="a.jpg"></div><div class="bmf-body"><h4 class="bmf-name">Teh O Ice</h4></div></li>'
            '<li class="bmf-card"><img src="b.jpg"><div class="bmf-body"><h4 class="bmf-name">Set A</h4></div></li></ul>')
    out, n = drop_item_photos(html, ["teh o ice"])
    assert n == 1 and "a.jpg" not in out and "b.jpg" in out and 'class="bmf-card bmf-text-only"' in out


def test_auto_fix_adds_icons_drops_images_and_injects_css():
    r = GateReport(rendered=True, checks=[
        Check("images_load", False, "", 1, [{"src": "https://example.invalid/x.jpg", "ok": False}]),
        Check("cta_icon_and_label", False, "", 2, []),
        Check("no_horizontal_overflow", False, "", 1, []),
    ])
    out, fixes = auto_fix(BAD, r)
    assert "example.invalid" not in out
    assert out.count("<svg") >= 2 and "binaapp-visual-gate-fixes" in out
    assert "dropped_broken_images(1)" in fixes and "cta_icons(2)" in fixes and "layout_fix_css" in fixes
    # idempotent on the generic sheet
    out2, fixes2 = auto_fix(out, r)
    assert out2.count("binaapp-visual-gate-fixes") == 1 and "layout_fix_css" not in fixes2


# ---------------------------------------------------------------------------
# Recovery loop (render + vision mocked)
# ---------------------------------------------------------------------------

def _fake_render(verdicts):
    """A render whose measurements fail when the html carries 'BROKEN'."""
    async def _render(html, **kw):
        m = _measured()
        if "BROKEN" in html:
            m = _measured(images=[{"src": "https://example.invalid/x.jpg", "ok": False}])
        verdicts.append("BROKEN" in html)
        return m, _measured(innerWidth=1280, scrollWidth=1280), b"png", b"png", None
    return _render


def test_recovery_passes_clean_page_first_time(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")
    seen = []
    monkeypatch.setattr(vg, "render", _fake_render(seen))
    html, rep = asyncio.run(gate_with_recovery("<html>ok</html>", expect_map=False, expect_whatsapp=False))
    assert rep.passed and rep.attempt == 1 and html == "<html>ok</html>" and seen == [False]


def test_recovery_auto_fix_then_pass(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")
    seen = []
    monkeypatch.setattr(vg, "render", _fake_render(seen))
    page = '<html><body><img src="https://example.invalid/x.jpg">BROKEN</body></html>'
    monkeypatch.setattr(vg, "auto_fix", lambda h, r: (h.replace("BROKEN", "fixed"), ["dropped_broken_images(1)"]))
    html, rep = asyncio.run(gate_with_recovery(page, expect_map=False, expect_whatsapp=False))
    assert rep.passed and rep.attempt == 2 and "fixed" in html and rep.fixes == ["dropped_broken_images(1)"]


def test_recovery_regenerates_once_then_fails_in_enforce(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")
    seen = []
    monkeypatch.setattr(vg, "render", _fake_render(seen))
    monkeypatch.setattr(vg, "auto_fix", lambda h, r: (h, []))
    regen = []

    async def _regen():
        regen.append(1)
        return "<html>BROKEN again</html>"
    with pytest.raises(VisualGateFailed) as exc:
        asyncio.run(gate_with_recovery("<html>BROKEN</html>", expect_map=False, expect_whatsapp=False, regenerate=_regen, job_id="job1"))
    assert regen == [1] and "Sila cuba lagi" in str(exc.value) and not exc.value.report.passed


def test_recovery_regeneration_can_pass(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")
    seen = []
    monkeypatch.setattr(vg, "render", _fake_render(seen))
    monkeypatch.setattr(vg, "auto_fix", lambda h, r: (h, []))

    async def _regen():
        return "<html>fresh and clean</html>"
    html, rep = asyncio.run(gate_with_recovery("<html>BROKEN</html>", expect_map=False, expect_whatsapp=False, regenerate=_regen))
    assert rep.passed and html == "<html>fresh and clean</html>" and rep.fixes == ["regenerated"]


def test_recovery_warn_mode_returns_failing_page(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "warn")
    monkeypatch.setattr(vg, "render", _fake_render([]))
    monkeypatch.setattr(vg, "auto_fix", lambda h, r: (h, []))
    html, rep = asyncio.run(gate_with_recovery("<html>BROKEN</html>", expect_map=False, expect_whatsapp=False))
    assert not rep.passed and html == "<html>BROKEN</html>" and rep.mode == "warn"


def test_recovery_off_and_unrenderable(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "off")
    html, rep = asyncio.run(gate_with_recovery("<html>BROKEN</html>", expect_map=False, expect_whatsapp=False))
    assert html == "<html>BROKEN</html>" and not rep.rendered
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")

    async def _no_browser(html, **kw):
        return {}, {}, None, None, "playwright not installed"
    monkeypatch.setattr(vg, "render", _no_browser)
    html, rep = asyncio.run(gate_with_recovery("<html>BROKEN</html>", expect_map=False, expect_whatsapp=False))
    assert html == "<html>BROKEN</html>" and not rep.rendered and "playwright" in rep.error


# ---------------------------------------------------------------------------
# Real browser
# ---------------------------------------------------------------------------

@browser
def test_browser_good_page_passes():
    rep = asyncio.run(run_gate(GOOD, expect_map=False, expect_whatsapp=True))
    if not rep.rendered:
        pytest.skip(rep.error)
    assert rep.passed, rep.summary()
    assert rep.mobile_png and rep.desktop_png


@browser
def test_browser_bad_page_fails_every_check_and_auto_fix_repairs_it():
    rep = asyncio.run(run_gate(BAD, expect_map=False, expect_whatsapp=False))
    if not rep.rendered:
        pytest.skip(rep.error)
    failed = {c.name for c in rep.failed}
    assert {"no_horizontal_overflow", "hero_cta_unobstructed", "no_clipped_text", "contrast_aa", "images_load", "cta_icon_and_label"} <= failed
    fixed, fixes = auto_fix(BAD, rep)
    assert fixes
    rep2 = asyncio.run(run_gate(fixed, expect_map=False, expect_whatsapp=False))
    assert rep2.passed, rep2.summary()


@browser
def test_browser_composed_agp_page_passes_with_widgets():
    """The stage-1 page, with the worker's widgets injected, passes the
    stage-2 gate — the two halves of the system agree."""
    from app.models.schemas import WebsiteGenerationRequest
    from app.services import menu_fidelity as mf
    from app.services.sections import build_spec, compose_page, fallback_copy, theme_from_plan
    from app.services.templates import TemplateService
    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "ayam_gepuk_panglima_menu.json")
    with open(fixture, encoding="utf-8") as fh:
        items = json.load(fh)["menu_items"]
    req = WebsiteGenerationRequest(
        description="Ayam Gepuk Panglima di Klang. Spice Level 1 Spicy / Level 2 Hot / Level 3 Extra Hot. FREE refill nasi & sambal (dine-in sahaja). Take away caj RM2.00.",
        business_name="Ayam Gepuk Panglima", business_type="food", subdomain="agp", whatsapp_number="0126973105",
        location_address="No. 44-1, Jalan Bayu Impian 4A/KS9, 41200 Klang, Selangor", menu_items=items, opening_hours="11 pagi - 10 malam",
    )
    spec = build_spec(req)
    html = compose_page(spec, theme_from_plan(None), fallback_copy(spec))
    html, _ = mf.fill_menu_slot(html, mf.render_menu_block(spec.items, language="ms", wa_digits=spec.wa_digits, order_prefill="saya nak order"))
    ts = TemplateService()
    html = ts.inject_google_maps(html, req.location_address, business_name=req.business_name, language="ms")
    html = ts.inject_whatsapp_button(html, "0126973105", language="ms", business_type="food")
    html = ts.inject_contact_form(html, "")
    rep = asyncio.run(run_gate(html, expect_map=True, expect_whatsapp=True))
    if not rep.rendered:
        pytest.skip(rep.error)
    # The map iframe cannot load without network; everything measurable must pass.
    assert {c.name for c in rep.failed} <= {"map_visible"} or rep.passed, rep.summary()
    names = {c.name: c for c in rep.checks}
    for n in ("no_horizontal_overflow", "hero_cta_unobstructed", "floating_button_unobstructed", "no_clipped_text", "contrast_aa", "cta_icon_and_label"):
        assert names[n].ok, names[n].detail
