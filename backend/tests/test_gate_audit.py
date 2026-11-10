"""The gate audit: what the visual gate did not measure, now measured.

Planting 22 known design defects on a good page showed the gate caught 7.
These are the unit tests of the 15 new checks, their fixes, the second
look that keeps one reviewer opinion from failing a build, and the
repair-only gate for pages rebuilt outside the create flow. The planted
defects themselves run in tests/test_gate_calibration.py (real browser).
"""

from __future__ import annotations

import asyncio
import io
import json

from app.services import visual_gate as vg
from app.services.visual_gate import GateReport, auto_fix, design_checks, evaluate_checks, run_gate


def _measured(**over):
    base = {"innerWidth": 390, "scrollWidth": 390, "heroCtas": [], "floating": [{"id": "whatsapp-button", "isWa": True, "obstructedBy": None}],
            "clipped": [], "lowContrast": [], "images": [], "ctas": [], "map": None}
    base.update(over)
    return base


def _design(**over):
    base = {"tinyText": [], "overlaps": [], "smallTargets": [], "distorted": [], "blurry": [], "duplicates": [], "emptySections": [],
            "junk": [], "deadLinks": [], "h1Count": 1, "h1Top": 300, "ctaTop": 560, "viewportHeight": 844}
    base.update(over)
    return base


def _names(checks, ok=False):
    return {c.name: c for c in checks if c.ok is ok}


# ---------------------------------------------------------------------------
# The new checks
# ---------------------------------------------------------------------------

def test_clean_design_measurement_passes_every_new_check():
    checks = design_checks(_measured(design=_design(), heroText=[{"text": "Kedai", "ratio": 9.1}], blankBands=[]), _measured(design=_design()))
    assert not _names(checks) and {"hero_text_legible", "text_readable_size", "tap_targets", "no_overlapping_text",
                                    "images_not_distorted", "no_empty_sections", "no_junk_text"} <= set(_names(checks, ok=True))
    # No design measurement (older callers): the new checks are not invented.
    assert design_checks(_measured(), _measured()) == []


def test_each_new_check_fails_on_its_defect_with_the_right_tier():
    d = _design(
        tinyText=[{"text": "Harga termasuk nasi", "path": "body>p:nth-of-type(1)", "size": 9}],
        smallTargets=[{"text": "Pesan", "path": "body>a:nth-of-type(1)", "size": [40, 13]}],
        overlaps=[{"text": "Free refill", "other": "Take away", "path": "body>p:nth-of-type(3)", "under": "body>p:nth-of-type(2)"}],
        distorted=[{"src": "x.jpg", "path": "body>img:nth-of-type(1)", "drawn": 4.5, "natural": 1.33}],
        emptySections=[{"heading": "Galeri", "path": "#galeri"}],
        junk=[{"text": "Harga bermula RMundefined", "found": "undefined", "path": "body>p:nth-of-type(4)"}],
        duplicates=[{"src": "a.jpg", "count": 3, "cards": ["Set A", "Set B", "Set C"], "paths": []}],
        deadLinks=[{"text": "Lihat menu", "href": "#senarai", "why": "no section with this id", "path": "a"}],
        blurry=[{"src": "s.jpg", "path": "img", "natural": 48, "shown": 356}], h1Count=2, h1Top=1300, ctaTop=1500,
    )
    mobile = _measured(design=d, heroText=[{"text": "Ayam Gepuk", "path": "#home>h1:nth-of-type(1)", "ratio": 1.2, "light_text": True}],
                       blankBands=[{"top": 900, "height": 1100}])
    failed = _names(design_checks(mobile, _measured(design=_design())))
    hard = {n for n, c in failed.items() if c.hard}
    soft = {n for n, c in failed.items() if not c.hard}
    assert hard == {"hero_text_legible", "text_readable_size", "tap_targets", "no_overlapping_text", "images_not_distorted",
                    "no_empty_sections", "no_junk_text"}
    assert soft == {"no_duplicate_photos", "links_work", "no_blank_bands", "images_sharp", "heading_structure", "primary_action_above_fold"}
    assert "1.2:1 over the hero photo (mobile)" in failed["hero_text_legible"].detail
    assert "40x13px" in failed["tap_targets"].detail and "'undefined'" in failed["no_junk_text"].detail
    assert failed["no_duplicate_photos"].count == 2  # two repeats of one photo


def test_desktop_only_defects_are_caught():
    """Hero buttons covered, or text faint, at 1280px only: the gate used
    to evaluate both on the phone alone."""
    desktop = _measured(innerWidth=1280, scrollWidth=1280,
                        heroCtas=[{"text": "Pesan", "obstructedBy": {"by": "div.x-strip", "fixed": False}}],
                        lowContrast=[{"text": "Buka setiap hari", "path": "p.x", "ratio": 1.6, "need": 4.5, "fg": "rgb(201, 201, 201)", "bg": "rgb(255, 255, 255)"}])
    failed = _names(evaluate_checks(_measured(), desktop, expect_map=False, expect_whatsapp=True))
    assert "(desktop)" in failed["hero_cta_unobstructed"].detail and failed["contrast_aa"].items[0]["viewport"] == "desktop"
    tiny_desktop = design_checks(_measured(design=_design()), _measured(design=_design(tinyText=[{"text": "x" * 30, "path": "p", "size": 9}])))
    assert "(desktop)" in _names(tiny_desktop)["text_readable_size"].detail


def test_tap_targets_are_a_phone_check_only():
    desktop = _measured(design=_design(smallTargets=[{"text": "x", "path": "a", "size": [20, 20]}]))
    assert "tap_targets" not in _names(design_checks(_measured(design=_design()), desktop))


def test_a_check_can_be_demoted_without_a_deploy(monkeypatch):
    mobile = _measured(design=_design(junk=[{"text": "RMundefined", "found": "undefined", "path": "p"}]))

    async def _render(html, **kw):
        return mobile, _measured(innerWidth=1280, scrollWidth=1280), b"png", b"png", None
    monkeypatch.setattr(vg, "render", _render)
    assert not asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=True)).passed
    monkeypatch.setenv("VISUAL_GATE_SOFT_CHECKS", "no_junk_text, tap_targets")
    rep = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=True))
    assert rep.passed and any(c.name == "no_junk_text" and not c.ok and not c.hard for c in rep.checks)


# ---------------------------------------------------------------------------
# Pixels: hero text over a photo, holes in the page
# ---------------------------------------------------------------------------

def _png(colour, size):
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    return buf.getvalue()


def test_hero_text_contrast_is_measured_against_the_pixels_behind_it():
    marked = [{"text": "Ayam Gepuk", "path": "h1", "color": [255, 255, 255], "size": 34, "boxes": [[20, 100, 300, 140]]}]
    pale = vg.hero_text_contrast(_png((245, 240, 225), (390, 844)), marked)[0]
    dark = vg.hero_text_contrast(_png((40, 25, 15), (390, 844)), marked)[0]
    assert pale["ratio"] < 1.3 and dark["ratio"] > 12 and pale["light_text"] is True
    dark_text = vg.hero_text_contrast(_png((40, 25, 15), (390, 844)), [dict(marked[0], color=[28, 25, 23])])[0]
    assert dark_text["ratio"] < 1.3 and dark_text["light_text"] is False
    assert vg.hero_text_contrast(b"not a png", marked) == []


def test_blank_bands_find_a_hole_and_ignore_normal_spacing():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (390, 3000), (255, 252, 245))
    draw = ImageDraw.Draw(im)
    for y in list(range(0, 800, 40)) + list(range(1900, 3000, 40)):  # "text" every 40px, a hole 800..1900
        draw.rectangle((20, y, 300, y + 12), fill=(30, 30, 30))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    bands = vg.blank_bands(buf.getvalue())
    assert len(bands) == 1 and 760 <= bands[0]["top"] <= 800 and 1100 <= bands[0]["height"] <= 1140
    assert vg.blank_bands(buf.getvalue(), min_height=1200) == [] and vg.blank_bands(None) == []


# ---------------------------------------------------------------------------
# Fixes
# ---------------------------------------------------------------------------

def test_targeted_fixes_for_the_new_checks():
    d = _design(
        tinyText=[{"text": "kecil", "path": "body>p:nth-of-type(1)", "size": 9}],
        smallTargets=[{"text": "Pesan", "path": "body>a:nth-of-type(1)", "size": [40, 13]}],
        overlaps=[{"text": "a", "other": "b", "path": "body>p:nth-of-type(3)", "under": "body>p:nth-of-type(2)"}],
        distorted=[{"src": "x.jpg", "path": "body>img:nth-of-type(1)", "drawn": 4.5, "natural": 1.33}],
        emptySections=[{"heading": "Galeri", "path": "#galeri"}],
    )
    rep = GateReport(checks=design_checks(_measured(design=d), _measured(design=_design())), rendered=True)
    out, fixes = auto_fix("<html><head></head><body></body></html>", rep)
    assert fixes and fixes[-1].startswith("targeted_css(")
    for rule in ("body>p:nth-of-type(1){font-size:12.5px!important", "body>a:nth-of-type(1){min-height:40px!important",
                 "body>p:nth-of-type(3){position:static!important", "body>img:nth-of-type(1){object-fit:cover!important",
                 "#galeri{display:none!important"):
        assert rule in out, rule


HERO = ('<html><head></head><body><section class="bs-hero" id="home"><div class="bs-hero-media"><img src="h.jpg"></div>'
        '<div class="bs-wrap"><h1>AGP</h1></div></section></body></html>')


def test_faint_hero_text_gets_a_darker_scrim_on_a_composed_hero():
    faint = [{"text": "AGP", "path": "#home>div:nth-of-type(2)>h1:nth-of-type(1)", "ratio": 1.2, "light_text": True}]
    rep = GateReport(checks=design_checks(_measured(design=_design(), heroText=faint), _measured(design=_design())), rendered=True)
    out, fixes = auto_fix(HERO, rep)
    assert fixes == ["darker_hero_scrim"]  # the scrim, not a backing box on each line
    assert '<div class="bs-hero-scrim"></div>' in out and "binaapp-visual-gate-scrim" in out and "rgba(0,0,0,.58)" in out
    assert vg.darken_hero_scrim(out) == (out, 0)  # once


def test_faint_hero_text_on_a_freeform_hero_gets_its_own_backing():
    page = '<html><head></head><body><section id="home" style="background-image:url(a.jpg)"><h1>Kedai</h1></section></body></html>'
    faint = [{"text": "Kedai", "path": "#home>h1:nth-of-type(1)", "ratio": 1.4, "light_text": False}]
    rep = GateReport(checks=design_checks(_measured(design=_design(), heroText=faint), _measured(design=_design())), rendered=True)
    out, fixes = auto_fix(page, rep)
    assert fixes == ["targeted_css(1)"] and "#home>h1:nth-of-type(1){background:rgba(255,255,255,.86)!important;color:#111!important" in out


def test_one_photo_on_three_cards_keeps_the_first():
    page = "".join(f'<li class="bmf-card"><div class="bmf-media"><img src="a.jpg"></div><h4 class="bmf-name">{n}</h4></li>' for n in ("Set A", "Set B", "Set C"))
    d = _design(duplicates=[{"src": "a.jpg", "count": 3, "cards": ["Set A", "Set B", "Set C"], "paths": []}])
    rep = GateReport(checks=design_checks(_measured(design=d), _measured(design=_design())), rendered=True)
    out, fixes = auto_fix(page, rep)
    assert fixes == ["dropped_repeated_photos(2)"] and out.count("a.jpg") == 1 and out.count("bmf-text-only") == 2
    # A repeat outside the menu cards (a gallery) is not a card problem.
    assert "no_duplicate_photos" not in _names(design_checks(_measured(design=_design(duplicates=[{"src": "g.jpg", "count": 2, "cards": [], "paths": []}])), _measured()))


# ---------------------------------------------------------------------------
# One reviewer opinion never fails a build
# ---------------------------------------------------------------------------

OVERLAP = {"issues": [{"slice": 1, "type": "overlap", "where": "menu", "detail": "price over the name", "severity": "high"}],
           "design": {"score": 7, "weakest": "cards without photos"}, "overall": "fail"}


def _reviewer(page, confirm):
    seen = []

    async def _call(messages):
        text = messages[0]["content"][0]["text"]
        seen.append(text)
        if "A first reviewer reported" in text:
            return confirm if isinstance(confirm, str) or confirm is None else json.dumps(confirm)
        return json.dumps(page)
    return _call, seen


def _gate(monkeypatch, call):
    async def _render(html, **kw):
        return _measured(), _measured(innerWidth=1280, scrollWidth=1280), b"png", b"png", None
    monkeypatch.setattr(vg, "render", _render)
    return asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=True, call_vision=call))


def test_high_issue_fails_only_when_a_second_look_confirms_it(monkeypatch):
    call, seen = _reviewer(OVERLAP, {"confirmed": True, "evidence": "RM12.50 sits on the dish name"})
    rep = _gate(monkeypatch, call)
    assert [c.name for c in rep.failed] == ["vision_review"] and rep.vision["issues"][0]["confirmed"] is True
    second = next(t for t in seen if "A first reviewer reported" in t)
    assert "overlap at menu: price over the name" in second

    call, _ = _reviewer(OVERLAP, {"confirmed": False, "evidence": "price and name are on separate lines"})
    rep = _gate(monkeypatch, call)
    assert rep.passed and rep.vision["issues"][0]["severity"] == "low" and "did not confirm" in rep.vision["issues"][0]["note"]


def test_no_second_answer_or_no_slice_is_not_a_confirmation(monkeypatch):
    call, _ = _reviewer(OVERLAP, None)
    assert _gate(monkeypatch, call).passed
    no_slice = {"issues": [dict(OVERLAP["issues"][0])], "overall": "fail"}
    no_slice["issues"][0].pop("slice")
    call, seen = _reviewer(no_slice, {"confirmed": True})
    rep = _gate(monkeypatch, call)
    assert rep.passed and not any("A first reviewer reported" in t for t in seen)
    assert "no second look" in rep.vision["issues"][0]["note"]


def test_design_score_is_recorded_and_never_gates(monkeypatch):
    call, _ = _reviewer({"issues": [], "design": {"score": 2, "weakest": "everything is one colour"}, "overall": "pass"}, None)
    rep = _gate(monkeypatch, call)
    assert rep.passed and rep.vision["design"] == {"score": 2, "weakest": "everything is one colour"}
    assert vg.parse_vision('{"issues":[],"design":{"score":"11"},"overall":"pass"}')["design"]["score"] == 10
    assert "design" not in vg.parse_vision('{"issues":[],"design":{"score":"great"},"overall":"pass"}')
    assert rep.as_dict()["vision"]["design"]["score"] == 2  # stored on the job for the weekly summary


# ---------------------------------------------------------------------------
# Pages rebuilt outside the create flow
# ---------------------------------------------------------------------------

def test_gate_and_repair_fixes_what_it_can_and_never_blocks(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")

    async def _render(html, **kw):
        d = _design(junk=[{"text": "RMundefined", "found": "undefined", "path": "p"}]) if "RMundefined" in html else _design()
        if "TINY" in html and "font-size:12.5px" not in html:
            d["tinyText"] = [{"text": "TINY", "path": "body>p:nth-of-type(1)", "size": 9}]
        return _measured(design=d), _measured(innerWidth=1280, scrollWidth=1280, design=_design()), b"png", b"png", None
    monkeypatch.setattr(vg, "render", _render)

    page = "<html><head></head><body><p>TINY</p></body></html>"
    out, rep = asyncio.run(vg.gate_and_repair(page, path="make_good_regen", expect_map=False, expect_whatsapp=True))
    assert rep.passed and "font-size:12.5px" in out and rep.fixes == ["targeted_css(1)"]

    # Nothing fixes junk text: enforce mode would block a new build, a
    # rebuild ships and is reported.
    junk = "<html><head></head><body><p>RMundefined</p></body></html>"
    out, rep = asyncio.run(vg.gate_and_repair(junk, path="make_good_regen", expect_map=False, expect_whatsapp=True))
    assert out == junk and not rep.passed and [c.name for c in rep.failed] == ["no_junk_text"]

    async def _boom(html, **kw):
        raise RuntimeError("chromium fell over")
    monkeypatch.setattr(vg, "render", _boom)
    out, rep = asyncio.run(vg.gate_and_repair(page, path="websites_api", expect_map=False, expect_whatsapp=True))
    assert out == page and not rep.rendered


def test_weekly_summary_reports_the_design_score():
    from datetime import datetime, timezone
    from app.services import ops_alerts as oa
    jobs = [{"status": "completed", "validation": {"visual_gate": {"rendered": True, "passed": True, "fixes": [], "vision": {"design": {"score": s}}}}} for s in (8, 6, 4)]
    summary = oa.summarize(jobs, [{"kind": "gate_warning"}], since=datetime(2026, 11, 2, tzinfo=timezone.utc), until=datetime(2026, 11, 9, tzinfo=timezone.utc))
    text = oa.format_summary(summary)
    assert "average 6.0 over 3 pages, lowest 4" in text and "rebuilt pages shipped with problems: 1" in text
    assert "no scored pages" in oa.format_summary(oa.summarize([], [], since=summary["since"], until=summary["until"]))


def test_fixes_target_only_the_element_that_failed():
    """Calibration found the contrast fix writing ``p{color:#757575}``: one
    faint line turned every paragraph grey, white hero text included."""
    low = [{"text": "Buka setiap hari", "path": "p", "sel": "body>p:nth-of-type(2)", "ratio": 1.74, "need": 4.5,
            "fg": "rgb(196, 196, 196)", "bg": "rgb(255, 255, 255)"}]
    clipped = [{"text": "Sambal", "path": "p", "sel": "body>p:nth-of-type(5)", "scrollWidth": 300, "clientWidth": 120, "right": 300}]
    covered = [{"text": "Pesan", "obstructedBy": {"by": "div", "bySel": "#home>div:nth-of-type(2)>div:nth-of-type(1)", "fixed": False}}]
    rep = GateReport(rendered=True, checks=evaluate_checks(
        _measured(lowContrast=low, clipped=clipped, heroCtas=covered), _measured(innerWidth=1280, scrollWidth=1280), expect_map=False, expect_whatsapp=True))
    css = vg.targeted_fix_css(rep)
    assert "body>p:nth-of-type(2){color:" in css and "body>p:nth-of-type(5){max-width:100%" in css
    assert "#home>div:nth-of-type(2)>div:nth-of-type(1){position:static" in css
    assert "\np{" not in css and "\ndiv{" not in css
