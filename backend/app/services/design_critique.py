"""
Critique gate (§7) — a vision model scores the rendered page against the
plan, and the score decides whether Pass 2 runs again.

Flow:
1. ``render_screenshots`` renders the HTML with Playwright at desktop 1280
   and mobile 390 (when Playwright + a browser are available) and measures
   what a screenshot alone cannot prove: horizontal overflow at 390px and
   the size of the hero text.
2. ``build_critique_messages`` sends both screenshots + the plan + the
   rubric to the vision model; without screenshots the same rubric is
   applied to the HTML text (weaker, but never silent).
3. ``parse_critique`` turns the reply into eight 1–10 scores, an average
   and the improvement notes per criterion; deterministic measurements
   (overflow) override the model where they disagree.
4. Gate: average ≥ 7 and no criterion < 5.

The module is pure apart from ``render_screenshots``; the model call is
injected as an async callable so ai_service owns keys and providers and
the tests own the replies.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from app.services.design_plan import DesignPlan

logger = logging.getLogger(__name__)

GATE_AVERAGE = 7.0
GATE_MINIMUM = 5
MAX_RETRIES = 2
DESKTOP = (1280, 800)
MOBILE = (390, 844)
SCREENSHOT_TIMEOUT_SECONDS = float(os.getenv("DESIGN_CRITIQUE_SCREENSHOT_TIMEOUT_SECONDS", "25"))

RUBRIC: Tuple[Tuple[str, str], ...] = (
    ("distinctiveness", "Would this be mistaken for another BinaApp site? 10 = unmistakably designed for this business; 1 = the same template with a new colour."),
    ("appetite", "Does the food/product look good and does the page feel warm and bright (unless a dark theme was chosen)? 1 = cold, grey, unappetising."),
    ("hierarchy", "Is the most important thing (menu / order / book) obvious within 3 seconds? 1 = buried."),
    ("typography", "Deliberate scale, readable line lengths, no decorated headlines (no italic or recoloured word, no eyebrow above every heading)."),
    ("layout", "Not a stack of identical cards; sections have rhythm and variety (open story layout, one band, one grid)."),
    ("restraint", "One signature element, no clutter, no template chrome (no arrow buttons, no middle-dot meta, no fake badges)."),
    ("mobile", "The 390px view has no horizontal overflow, a readable hero, and a thumb-reachable CTA."),
    ("honesty", "No placeholder or invented content: no fake map, no invented hours/ratings/reviews, no empty gallery."),
)
RUBRIC_KEYS = tuple(k for k, _ in RUBRIC)


@dataclass
class ScreenshotBundle:
    desktop_png: Optional[bytes] = None
    mobile_png: Optional[bytes] = None
    mobile_overflow: bool = False
    mobile_scroll_width: int = 0
    hero_font_px: float = 0.0
    hero_text_visible: bool = True
    error: Optional[str] = None
    #: Full measurement dicts per viewport (page_hierarchy reads these).
    desktop_measured: Dict[str, Any] = field(default_factory=dict)
    mobile_measured: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.desktop_png and self.mobile_png)


@dataclass
class CritiqueResult:
    scores: Dict[str, int]
    notes: List[str] = field(default_factory=list)
    mode: str = "vision"  # vision | text | measured-only
    measured: Dict[str, Any] = field(default_factory=dict)

    @property
    def average(self) -> float:
        vals = [v for v in self.scores.values() if isinstance(v, (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    @property
    def minimum(self) -> int:
        vals = [v for v in self.scores.values() if isinstance(v, (int, float))]
        return int(min(vals)) if vals else 0

    @property
    def passed(self) -> bool:
        return self.average >= GATE_AVERAGE and self.minimum >= GATE_MINIMUM

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scores": dict(self.scores),
            "average": self.average,
            "minimum": self.minimum,
            "passed": self.passed,
            "notes": list(self.notes),
            "mode": self.mode,
            "measured": dict(self.measured),
        }

    def feedback_lines(self) -> List[str]:
        lines = []
        for key, _ in RUBRIC:
            score = self.scores.get(key)
            if score is not None and score < 8:
                lines.append(f"- CRITIQUE {key} scored {score}/10")
        lines += [f"- CRITIQUE NOTE: {n}" for n in self.notes]
        return lines


# ---------------------------------------------------------------------------
# Screenshots
# ---------------------------------------------------------------------------

_MEASURE_JS = """
() => {
  const doc = document.documentElement;
  const bodyPx = parseFloat(getComputedStyle(document.body).fontSize) || 16;
  const h1 = document.querySelector('h1');
  let fontPx = 0, visible = true;
  const cssPath = (el) => {
    const parts = [];
    while (el && el.nodeType === 1 && el !== document.body) {
      let part = el.tagName.toLowerCase();
      if (el.id) { part += '#' + CSS.escape(el.id); parts.unshift(part); break; }
      const parent = el.parentElement;
      if (parent) {
        const same = Array.from(parent.children).filter(c => c.tagName === el.tagName);
        if (same.length > 1) part += ':nth-of-type(' + (same.indexOf(el) + 1) + ')';
      }
      parts.unshift(part);
      el = parent;
    }
    return parts.join(' > ');
  };
  if (h1) {
    fontPx = parseFloat(getComputedStyle(h1).fontSize) || 0;
    const r = h1.getBoundingClientRect();
    visible = r.width > 0 && r.height > 0 && r.top < window.innerHeight;
  }
  // Every element with its own text: largest non-H1 text and small H2s.
  const largerThanH1 = [], smallH2 = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node;
  while ((node = walker.nextNode())) {
    if (['SCRIPT','STYLE','NOSCRIPT','SVG','PATH'].includes(node.tagName)) continue;
    const hasText = Array.from(node.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!hasText) continue;
    const px = parseFloat(getComputedStyle(node).fontSize) || 0;
    if (node.tagName !== 'H1' && !node.closest('h1') && fontPx && px >= fontPx && largerThanH1.length < 12) {
      largerThanH1.push({ path: cssPath(node), px: px, text: node.textContent.trim().slice(0, 40) });
    }
    if (node.tagName === 'H2' && px < 1.6 * bodyPx && smallH2.length < 12) {
      smallH2.push({ path: cssPath(node), px: px, text: node.textContent.trim().slice(0, 40) });
    }
  }
  // Hero text block: the H1's nearest block container with a photo behind it.
  let heroText = null;
  if (h1) {
    let holder = h1.parentElement;
    for (let i = 0; i < 4 && holder && holder !== document.body; i++) {
      const cs = getComputedStyle(holder);
      if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent') break;
      holder = holder.parentElement;
    }
    const block = h1.parentElement || h1;
    const r = block.getBoundingClientRect();
    const scrollY = window.scrollY || 0;
    heroText = { path: cssPath(block), color: getComputedStyle(h1).color,
      box: { x: r.left, y: r.top + scrollY, width: r.width, height: r.height } };
  }
  const floating = Array.from(document.querySelectorAll('[style*="position:fixed"], [style*="position: fixed"], #binaapp-open-badge, #binaapp-chat-btn, #whatsapp-button, .binaapp-order-button'))
    .filter(el => getComputedStyle(el).position === 'fixed')
    .map(el => { const r = el.getBoundingClientRect(); return { id: el.id || el.className || el.tagName, x: r.left, y: r.top, width: r.width, height: r.height }; });
  return {
    scrollWidth: Math.max(doc.scrollWidth, document.body ? document.body.scrollWidth : 0),
    innerWidth: window.innerWidth,
    bodyFontPx: bodyPx,
    h1FontPx: fontPx,
    heroFontPx: fontPx,
    heroVisible: visible,
    largerThanH1: largerThanH1,
    smallH2: smallH2,
    heroText: heroText,
    floating: floating,
  };
}
"""


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
    except Exception:
        return False
    return True


async def render_screenshots(html: str, *, timeout: float = SCREENSHOT_TIMEOUT_SECONDS) -> ScreenshotBundle:
    """Render ``html`` at desktop + mobile. Never raises: a missing
    browser, a timeout or a crash returns a bundle with ``error`` set."""
    bundle = ScreenshotBundle()
    if not playwright_available():
        bundle.error = "playwright not installed"
        return bundle
    try:
        from playwright.async_api import async_playwright

        async def _run() -> None:
            async with async_playwright() as pw:
                launch_kwargs: Dict[str, Any] = {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]}
                exe = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
                if exe:
                    launch_kwargs["executable_path"] = exe
                browser = await pw.chromium.launch(**launch_kwargs)
                try:
                    for name, (w, h) in (("desktop", DESKTOP), ("mobile", MOBILE)):
                        page = await browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                        # External fonts/CDN may be unreachable in the sandbox;
                        # the layout still renders with fallbacks.
                        await page.route("**/*", lambda route: route.continue_())
                        await page.set_content(html, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                        try:
                            await page.wait_for_load_state("networkidle", timeout=4000)
                        except Exception:
                            pass
                        png = await page.screenshot(full_page=True, type="png")
                        try:
                            m = await page.evaluate(_MEASURE_JS)
                        except Exception as err:
                            logger.warning(f"📐 {name} measurement failed: {err}")
                            m = {}
                        if name == "desktop":
                            bundle.desktop_png = png
                            bundle.desktop_measured = m or {}
                        else:
                            bundle.mobile_png = png
                            bundle.mobile_measured = m or {}
                            if m:
                                bundle.mobile_scroll_width = int(m.get("scrollWidth") or 0)
                                bundle.mobile_overflow = bundle.mobile_scroll_width > int(m.get("innerWidth") or w) + 2
                                bundle.hero_font_px = float(m.get("heroFontPx") or 0)
                                bundle.hero_text_visible = bool(m.get("heroVisible", True))
                        await page.close()
                finally:
                    await browser.close()

        await asyncio.wait_for(_run(), timeout=timeout + 10)
    except Exception as err:
        bundle.error = f"{type(err).__name__}: {err}"
        logger.warning(f"📸 Screenshot render unavailable: {bundle.error}")
    return bundle


# ---------------------------------------------------------------------------
# Prompt + parse
# ---------------------------------------------------------------------------

_JSON_SHAPE = (
    '{"scores": {' + ", ".join(f'"{k}": 1-10' for k in RUBRIC_KEYS) + '}, '
    '"notes": ["at most 6 specific, actionable fixes, each naming the section and what to change"]}'
)


def _rubric_text(plan: DesignPlan) -> str:
    dark = plan.theme == "dark"
    rows = []
    for key, desc in RUBRIC:
        if key == "appetite" and dark:
            desc = "Does the food/product look good and does the page feel rich and inviting (a dark theme WAS chosen — do not penalise darkness)?"
        rows.append(f"- {key}: {desc}")
    return "\n".join(rows)


def build_critique_messages(plan: DesignPlan, bundle: Optional[ScreenshotBundle], html: str, language: str) -> List[Dict[str, Any]]:
    """OpenAI-style messages for the vision (or text) critique call."""
    plan_summary = json.dumps({
        "direction": plan.direction_name, "theme": plan.theme, "hero_treatment": plan.hero_treatment,
        "signature_element": plan.signature_element, "palette": plan.palette, "type": plan.type,
        "sections": plan.sections, "avoid": plan.avoid,
    }, ensure_ascii=False)
    system = (
        "You are a strict senior design reviewer for a Malaysian small-business website builder. "
        "Score the page on each rubric criterion from 1 (bad) to 10 (excellent). Be harsh on anything "
        "that looks like a template: cream page + serif + gold accent, an italic word in a headline, an "
        "ALL-CAPS eyebrow above every heading, identical rounded cards everywhere, arrow glyphs on buttons. "
        "Respond with ONLY a JSON object in exactly this shape:\n" + _JSON_SHAPE
    )
    text = (
        f"DESIGN PLAN the page was built against:\n{plan_summary}\n\n"
        f"RUBRIC:\n{_rubric_text(plan)}\n\n"
        f"Site language: {'Bahasa Malaysia' if language != 'en' else 'English'}."
    )
    content: List[Dict[str, Any]] = []
    if bundle and bundle.ok:
        content.append({"type": "text", "text": text + "\n\nScreenshot 1 = desktop 1280px, screenshot 2 = mobile 390px."})
        for png in (bundle.desktop_png, bundle.mobile_png):
            b64 = base64.b64encode(png).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
        if bundle.mobile_overflow:
            content.append({"type": "text", "text": f"MEASURED: the mobile page overflows horizontally ({bundle.mobile_scroll_width}px wide at 390px)."})
        return [{"role": "system", "content": system}, {"role": "user", "content": content}]
    # Text fallback: no screenshots — review the HTML itself.
    snippet = html if len(html) <= 60000 else html[:60000]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": text + "\n\nNo screenshot is available; review the HTML source below as the page it would render.\n\n" + snippet},
    ]


def parse_critique(raw: Optional[str], bundle: Optional[ScreenshotBundle] = None, mode: str = "vision") -> Optional[CritiqueResult]:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        try:
            data = json.loads(re.sub(r",\s*([}\]])", r"\1", text[start:end + 1]))
        except (json.JSONDecodeError, ValueError):
            return None
    if not isinstance(data, dict):
        return None
    raw_scores = data.get("scores") if isinstance(data.get("scores"), dict) else data
    scores: Dict[str, int] = {}
    for key in RUBRIC_KEYS:
        value = raw_scores.get(key)
        try:
            n = int(round(float(value)))
        except (TypeError, ValueError):
            continue
        scores[key] = max(1, min(10, n))
    if len(scores) < 4:
        return None
    notes = [re.sub(r"\s+", " ", str(n)).strip()[:240] for n in (data.get("notes") or []) if str(n).strip()][:6]
    result = CritiqueResult(scores=scores, notes=notes, mode=mode)
    return apply_measurements(result, bundle)


def apply_measurements(result: CritiqueResult, bundle: Optional[ScreenshotBundle]) -> CritiqueResult:
    """Deterministic measurements override the model where they disagree."""
    if bundle is None:
        return result
    result.measured = {
        "mobile_overflow": bundle.mobile_overflow,
        "mobile_scroll_width": bundle.mobile_scroll_width,
        "hero_font_px": bundle.hero_font_px,
        "hero_text_visible": bundle.hero_text_visible,
        "screenshots": bundle.ok,
    }
    if bundle.mobile_overflow:
        result.scores["mobile"] = min(result.scores.get("mobile", 10), 4)
        result.notes.insert(0, f"Mobile: the page overflows horizontally at 390px ({bundle.mobile_scroll_width}px). Fix widths, grids and images so nothing exceeds the viewport.")
    m = bundle.desktop_measured or {}
    if m.get("largerThanH1"):
        result.scores["typography"] = min(result.scores.get("typography", 10), 4)
        result.notes.insert(0, f"Typography: {len(m['largerThanH1'])} element(s) are as large as the H1 ({m['largerThanH1'][0].get('text', '')!r}) — the H1 must be the largest text on the page.")
    if m.get("smallH2"):
        result.scores["typography"] = min(result.scores.get("typography", 10), 5)
        result.notes.insert(0, f"Typography: {len(m['smallH2'])} section heading(s) render at body size — H2 must be at least 1.6× body with a distinct weight.")
    if bundle.ok and (not bundle.hero_text_visible or (0 < bundle.hero_font_px < 28)):
        result.scores["mobile"] = min(result.scores.get("mobile", 10), 5)
        result.notes.insert(0, "Mobile: the hero headline is not readable on a 390px screen (too small or not visible) — set it with clamp() so it is at least 28px.")
    return result


def measured_only_result(bundle: ScreenshotBundle) -> CritiqueResult:
    """When no critique model answered, still gate on what was measured so
    an overflowing mobile page never ships as 'passed'."""
    scores = {k: 7 for k in RUBRIC_KEYS}
    return apply_measurements(CritiqueResult(scores=scores, notes=[], mode="measured-only"), bundle)


async def run_critique(
    html: str,
    plan: DesignPlan,
    *,
    language: str,
    call_model: Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]],
    render: bool = True,
    bundle: Optional[ScreenshotBundle] = None,
) -> Optional[CritiqueResult]:
    """Screenshots (when possible) → model → parsed, measured result.
    Returns None only when neither the model nor a measurement produced
    anything to gate on. A pre-rendered ``bundle`` skips the render."""
    if bundle is None:
        bundle = await render_screenshots(html) if render else None
    messages = build_critique_messages(plan, bundle, html, language)
    mode = "vision" if (bundle and bundle.ok) else "text"
    raw = None
    try:
        raw = await call_model(messages)
    except Exception as err:
        logger.warning(f"🧑‍⚖️ Critique model call failed: {err}")
    result = parse_critique(raw, bundle, mode=mode)
    if result is None and bundle is not None and bundle.ok:
        result = measured_only_result(bundle)
    if result is not None:
        logger.info(f"🧑‍⚖️ Critique ({result.mode}): avg {result.average} min {result.minimum} passed={result.passed} notes={len(result.notes)}")
    return result
