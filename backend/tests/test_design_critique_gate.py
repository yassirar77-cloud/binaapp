"""
Critique gate (design_critique.py) and its wiring (_run_plan_gate).

Covers:
- rubric parsing (clean / fenced / partial / garbage), clamping, notes cap
- the gate: average ≥ 7 and no criterion < 5
- deterministic measurements override the model (mobile overflow)
- message building: screenshots become image parts; no screenshots → text mode
- _run_plan_gate: passes clean HTML through once; a lint failure triggers
  a regeneration with the failures in the prompt; the retry budget is
  bounded; the best attempt is served; no critique model = lint-only gate

Screenshot rendering itself is exercised in test_screenshot_render.py
(skipped when Playwright has no browser).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

import app.services.ai_service as ai_service_module
from app.services import design_critique as dc
from app.services.ai_service import AIService
from app.services.design_plan import PlanBrief, fallback_plan


def _plan():
    return fallback_plan(PlanBrief(business_name="Nasi Kandar Crystal", description="Nasi kandar mamak", vertical="food", menu_item_count=3, has_hero_image=True))


def _scores(**over):
    base = {k: 8 for k in dc.RUBRIC_KEYS}
    base.update(over)
    return base


# ---- parsing + gate -----------------------------------------------------------

def test_parse_clean_and_fenced():
    raw = json.dumps({"scores": _scores(), "notes": ["Menu: align the prices"]})
    r = dc.parse_critique(raw)
    assert r.average == 8.0 and r.passed and r.notes == ["Menu: align the prices"]
    r = dc.parse_critique("```json\n" + raw + "\n```")
    assert r is not None and r.passed


def test_parse_clamps_and_rejects_garbage():
    r = dc.parse_critique(json.dumps({"scores": _scores(mobile=14, honesty=-2)}))
    assert r.scores["mobile"] == 10 and r.scores["honesty"] == 1 and not r.passed
    assert dc.parse_critique("nothing here") is None
    assert dc.parse_critique(json.dumps({"scores": {"mobile": 9}})) is None  # too few criteria
    r = dc.parse_critique(json.dumps({"scores": _scores(), "notes": [f"n{i}" for i in range(10)]}))
    assert len(r.notes) == 6


def test_gate_thresholds():
    assert dc.parse_critique(json.dumps({"scores": _scores(distinctiveness=6, layout=6)})).passed  # avg 7.5, min 6
    low_avg = dc.parse_critique(json.dumps({"scores": {k: 6 for k in dc.RUBRIC_KEYS}}))
    assert not low_avg.passed
    one_bad = dc.parse_critique(json.dumps({"scores": _scores(honesty=4)}))
    assert one_bad.average >= 7 and not one_bad.passed
    assert any("honesty scored 4" in line for line in one_bad.feedback_lines())


def test_measurements_override_the_model():
    bundle = dc.ScreenshotBundle(desktop_png=b"x", mobile_png=b"y", mobile_overflow=True, mobile_scroll_width=612, hero_font_px=40)
    r = dc.parse_critique(json.dumps({"scores": _scores()}), bundle)
    assert r.scores["mobile"] == 4 and not r.passed
    assert "overflows horizontally" in r.notes[0]
    small_hero = dc.ScreenshotBundle(desktop_png=b"x", mobile_png=b"y", hero_font_px=18)
    r = dc.parse_critique(json.dumps({"scores": _scores()}), small_hero)
    assert r.scores["mobile"] == 5 and "hero headline" in r.notes[0]
    measured = dc.measured_only_result(bundle)
    assert measured.mode == "measured-only" and not measured.passed


def test_messages_use_screenshots_when_available():
    plan = _plan()
    bundle = dc.ScreenshotBundle(desktop_png=b"\x89PNG", mobile_png=b"\x89PNG")
    msgs = dc.build_critique_messages(plan, bundle, "<html></html>", "ms")
    parts = msgs[1]["content"]
    assert sum(1 for p in parts if p["type"] == "image_url") == 2
    assert all(p["image_url"]["url"].startswith("data:image/png;base64,") for p in parts if p["type"] == "image_url")
    assert plan.direction_name in parts[0]["text"]
    text_msgs = dc.build_critique_messages(plan, dc.ScreenshotBundle(error="no browser"), "<html>page</html>", "en")
    assert isinstance(text_msgs[1]["content"], str) and "<html>page</html>" in text_msgs[1]["content"]
    dark = fallback_plan(PlanBrief(business_name="X", description="Steakhouse", vertical="food", theme="dark"))
    assert "dark theme WAS chosen" in dc.build_critique_messages(dark, None, "", "ms")[1]["content"]


@pytest.mark.asyncio
async def test_run_critique_text_mode_without_browser():
    plan = _plan()
    with patch.object(dc, "render_screenshots", new=AsyncMock(return_value=dc.ScreenshotBundle(error="none"))):
        r = await dc.run_critique("<html></html>", plan, language="ms", call_model=AsyncMock(return_value=json.dumps({"scores": _scores()})))
    assert r.mode == "text" and r.passed
    with patch.object(dc, "render_screenshots", new=AsyncMock(return_value=dc.ScreenshotBundle(error="none"))):
        r = await dc.run_critique("<html></html>", plan, language="ms", call_model=AsyncMock(return_value=None))
    assert r is None


# ---- _run_plan_gate ----------------------------------------------------------

import re as _re


def _without_hierarchy_css(html: str) -> str:
    """The gate injects the §C9/§C10 type floor; compare the page without it."""
    return _re.sub(r'<style id="binaapp-hierarchy">.*?</style>\n?', "", html, flags=_re.DOTALL)


CLEAN = """<!DOCTYPE html><html lang="ms"><head></head><body><section id="home"><h1 class="text-5xl">Ayam Goreng</h1>
<a href="#menu">Lihat menu</a></section><section id="menu"><h2 class="text-3xl md:text-4xl">Menu</h2></section><footer></footer></body></html>"""
TEMPLATEY = CLEAN.replace('<h1 class="text-5xl">Ayam Goreng</h1>', '<h1 class="text-5xl">Ayam <span class="italic text-primary">Goreng</span></h1>').replace(
    ">Lihat menu</a>", ">Lihat menu →</a>"
)


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setattr(ai_service_module, "DESIGN_GATE_MAX_RETRIES", 2)
    svc = AIService()
    svc.zai_api_key = None
    svc.qwen_api_key = None
    return svc


@pytest.mark.asyncio
async def test_gate_passes_clean_html_without_regenerating(service):
    service._regenerate_pass2 = AsyncMock()
    out = await service._run_plan_gate(CLEAN, plan=_plan(), prompt="P", has_images=False, designer_mode=True, language="ms")
    assert _without_hierarchy_css(out) == CLEAN and 'id="binaapp-hierarchy"' in out
    service._regenerate_pass2.assert_not_awaited()
    assert service._last_plan_gate["attempts"] == 1 and service._last_plan_gate["critique"] is None


@pytest.mark.asyncio
async def test_gate_regenerates_on_lint_failure_with_notes(service):
    service._regenerate_pass2 = AsyncMock(return_value=CLEAN)
    out = await service._run_plan_gate(TEMPLATEY, plan=_plan(), prompt="P", has_images=False, designer_mode=True, language="ms")
    assert _without_hierarchy_css(out) == CLEAN
    service._regenerate_pass2.assert_awaited_once()
    feedback = service._regenerate_pass2.call_args.args[1]
    assert any("italic or recoloured" in line for line in feedback) and any("arrow" in line for line in feedback)
    assert service._last_plan_gate["attempts"] == 2 and service._last_plan_gate["served_attempt"] == 2


@pytest.mark.asyncio
async def test_gate_retry_budget_is_bounded_and_best_attempt_served(service):
    service._regenerate_pass2 = AsyncMock(return_value=TEMPLATEY)
    out = await service._run_plan_gate(TEMPLATEY, plan=_plan(), prompt="P", has_images=False, designer_mode=True, language="ms")
    assert service._regenerate_pass2.await_count == 2
    assert service._last_plan_gate["attempts"] == 3
    # Repairs still applied to what is served: the arrow is gone even though the retries never fixed it.
    assert "→" not in out


@pytest.mark.asyncio
async def test_gate_stops_when_regeneration_fails(service):
    service._regenerate_pass2 = AsyncMock(return_value=None)
    await service._run_plan_gate(TEMPLATEY, plan=_plan(), prompt="P", has_images=False, designer_mode=True, language="ms")
    assert service._regenerate_pass2.await_count == 1
    assert service._last_plan_gate["attempts"] == 1


@pytest.mark.asyncio
async def test_gate_uses_critique_scores_when_model_available(service, monkeypatch):
    service.zai_api_key = "k"
    monkeypatch.setenv("DESIGN_CRITIQUE_ENABLED", "true")
    low = dc.CritiqueResult(scores={k: 5 for k in dc.RUBRIC_KEYS}, notes=["Hero: the headline is buried"])
    high = dc.CritiqueResult(scores={k: 9 for k in dc.RUBRIC_KEYS})
    critiques = [low, high]
    with patch.object(dc, "run_critique", new=AsyncMock(side_effect=lambda *a, **k: critiques.pop(0))):
        service._regenerate_pass2 = AsyncMock(return_value=CLEAN.replace("Ayam Goreng", "Ayam Goreng Berempah"))
        out = await service._run_plan_gate(CLEAN, plan=_plan(), prompt="P", has_images=False, designer_mode=True, language="ms")
    assert "Berempah" in out
    feedback = service._regenerate_pass2.call_args.args[1]
    assert any("headline is buried" in line for line in feedback)
    assert service._last_plan_gate["critique"]["average"] == 9.0 and service._last_plan_gate["served_attempt"] == 2


@pytest.mark.asyncio
async def test_gate_serves_higher_scoring_earlier_attempt(service, monkeypatch):
    service.zai_api_key = "k"
    first = dc.CritiqueResult(scores={**{k: 8 for k in dc.RUBRIC_KEYS}, "honesty": 4})  # fails on min
    worse = dc.CritiqueResult(scores={k: 5 for k in dc.RUBRIC_KEYS})
    critiques = [first, worse, worse]
    with patch.object(dc, "run_critique", new=AsyncMock(side_effect=lambda *a, **k: critiques.pop(0))):
        service._regenerate_pass2 = AsyncMock(return_value=CLEAN.replace("Ayam Goreng", "Worse"))
        out = await service._run_plan_gate(CLEAN, plan=_plan(), prompt="P", has_images=False, designer_mode=True, language="ms")
    assert "Worse" not in out and service._last_plan_gate["served_attempt"] == 1


@pytest.mark.asyncio
async def test_regenerate_pass2_keeps_photo_slot_contract(service):
    service.zai_api_key = "k"
    service._call_glm = AsyncMock(return_value="<html><body><h1>x</h1></body></html>")
    service._last_api_call = {"truncated": False}
    out = await service._regenerate_pass2("P", ["- LINT FAIL: x"], previous_html='<img src="PHOTO_SLOT_1">', has_images=True, designer_mode=True, provider="glm")
    assert out is None  # dropped the slots → rejected
    service._call_glm = AsyncMock(return_value='<html><body><img src="PHOTO_SLOT_1"></body></html>')
    out = await service._regenerate_pass2("P", ["- LINT FAIL: x"], previous_html='<img src="PHOTO_SLOT_1">', has_images=True, designer_mode=True, provider="glm")
    assert out and "PHOTO_SLOT_1" in out
    assert "REVISION NOTES" in service._call_glm.call_args.args[0] and "LINT FAIL: x" in service._call_glm.call_args.args[0]
