"""Visual QA gate — stage 2 of the quality system.

Before a page reaches the merchant it is rendered in a real browser at
390 px and 1280 px, with the widgets the customer will see, and measured:

- no horizontal overflow;
- nothing overlapping the hero CTAs, nothing overlapping the floating
  WhatsApp button;
- no clipped text;
- contrast >= 4.5:1 on every text element (3:1 for large text);
- every <img> loads;
- every CTA button has an icon AND a label;
- the map iframe is visible with both direction buttons (when an address
  was given).

Then a vision model (``qwen3-vl-plus``) reviews the mobile screenshot with
one fixed rubric: overlapping, tilted, cut-off or unreadable elements, and
photos that do not match their item name. Measurements are facts; the
model's opinion is advice: a measured check never passes because the
model liked the page, and a model complaint on something the measurements
cleared is logged as a warning, except an explicit photo mismatch, which
is fixed by dropping that photo.

``run_gate`` is pure apart from the browser; ``gate_with_recovery`` adds
the auto-fix → re-render → regenerate-once → fail loop the job worker
runs. ``VISUAL_GATE_MODE`` = ``enforce`` (default; a failing page never
ships), ``warn`` (report only), ``off``.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

MOBILE = (390, 844)
DESKTOP = (1280, 800)
RENDER_TIMEOUT_SECONDS = float(os.getenv("VISUAL_GATE_RENDER_TIMEOUT_SECONDS", "40"))
VISION_MODEL = os.getenv("VISUAL_GATE_VISION_MODEL", "qwen3-vl-plus")
VISION_TIMEOUT_SECONDS = float(os.getenv("VISUAL_GATE_VISION_TIMEOUT_SECONDS", "60"))
VISION_MAX_TILES = int(os.getenv("VISUAL_GATE_VISION_TILES", "6"))
MAX_ATTEMPTS = 3  # original → auto-fixed → regenerated

HARD_CHECKS = (
    "no_horizontal_overflow", "hero_cta_unobstructed", "floating_button_unobstructed", "no_clipped_text",
    "contrast_aa", "images_load", "cta_icon_and_label", "map_visible", "vision_review",
)


def gate_mode() -> str:
    raw = os.getenv("VISUAL_GATE_MODE", "enforce").strip().lower()
    return raw if raw in ("enforce", "warn", "off") else "enforce"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    count: int = 0
    items: List[Any] = field(default_factory=list)
    hard: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail, "count": self.count,
                "items": self.items[:12], "hard": self.hard}


@dataclass
class GateReport:
    checks: List[Check] = field(default_factory=list)
    vision: Optional[Dict[str, Any]] = None
    photo_mismatches: List[str] = field(default_factory=list)
    mobile_png: Optional[bytes] = None
    desktop_png: Optional[bytes] = None
    error: Optional[str] = None
    attempt: int = 1
    fixes: List[str] = field(default_factory=list)
    mode: str = "enforce"
    rendered: bool = False

    @property
    def failed(self) -> List[Check]:
        return [c for c in self.checks if not c.ok and c.hard]

    @property
    def passed(self) -> bool:
        return self.rendered and not self.failed

    def summary(self) -> str:
        if not self.rendered:
            return f"not rendered ({self.error})"
        bad = ", ".join(f"{c.name}({c.count or 1})" for c in self.failed)
        return "pass" if not bad else f"FAIL {bad}"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed, "rendered": self.rendered, "mode": self.mode, "attempt": self.attempt,
            "summary": self.summary(), "error": self.error, "fixes": list(self.fixes),
            "checks": [c.as_dict() for c in self.checks], "vision": self.vision,
            "photo_mismatches": list(self.photo_mismatches),
        }


# ---------------------------------------------------------------------------
# Measurement (runs in the page)
# ---------------------------------------------------------------------------

_PREPARE_JS = """
async () => {
  // Load every image now (lazy ones included) so "did it load" is a fact.
  const imgs = Array.from(document.images);
  imgs.forEach(i => { try { i.loading = 'eager'; } catch (e) {} });
  await Promise.all(imgs.map(i => new Promise(res => {
    if (i.complete) return res();
    const t = setTimeout(res, 8000);
    i.addEventListener('load', () => { clearTimeout(t); res(); }, { once: true });
    i.addEventListener('error', () => { clearTimeout(t); res(); }, { once: true });
  })));
  if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (e) {} }
  window.scrollTo(0, 0);
  return imgs.length;
}
"""

_MEASURE_JS = r"""
() => {
  const W = window.innerWidth, H = window.innerHeight;
  const doc = document.documentElement;
  // scrollIntoView must be instant: a smooth scroll would still be
  // animating when the rects are read.
  doc.style.scrollBehavior = 'auto';
  document.body.style.scrollBehavior = 'auto';
  const out = { innerWidth: W, innerHeight: H, scrollWidth: Math.max(doc.scrollWidth, document.body.scrollWidth) };
  // A real CSS selector (ids and classes escaped), so a failing element
  // can be targeted by a fix rule.
  const path = (el) => {
    const parts = [];
    while (el && el.nodeType === 1 && el !== document.body && parts.length < 6) {
      let p = el.tagName.toLowerCase();
      if (el.id) { p += '#' + CSS.escape(el.id); parts.unshift(p); break; }
      const cls = (el.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
      if (cls.length) p += '.' + cls.map(c => CSS.escape(c)).join('.');
      parts.unshift(p); el = el.parentElement;
    }
    return parts.join('>');
  };
  const visible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const text = (el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  const ownText = (el) => Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').replace(/\s+/g, ' ').trim();
  const isFixed = (el) => { for (let e = el; e && e !== document.body; e = e.parentElement) { if (getComputedStyle(e).position === 'fixed') return true; } return false; };
  const contains = (a, b) => a === b || a.contains(b) || b.contains(a);

  // --- overlap helper: what is on top at (x, y)? ---
  const topAt = (x, y) => document.elementFromPoint(Math.max(0, Math.min(W - 1, x)), Math.max(0, Math.min(H - 1, y)));
  const obstructed = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return null;
    // Probe the centre and four points a quarter of the way in along each
    // axis: inside a pill or a circle, where the box corners are not.
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const pts = [[cx, cy], [r.left + r.width * 0.25, cy], [r.right - r.width * 0.25, cy], [cx, r.top + r.height * 0.25], [cx, r.bottom - r.height * 0.25]];
    for (const [x, y] of pts) {
      if (y < 0 || y > H || x < 0 || x > W) continue;
      const t = topAt(x, y);
      if (t && !contains(t, el)) return { by: path(t), at: [Math.round(x), Math.round(y)], fixed: isFixed(t) };
    }
    return null;
  };

  // --- hero CTAs ---
  const hero = document.querySelector('#home, section.bs-hero, header + section, main > section:first-of-type, body > section:first-of-type');
  out.hero = hero ? path(hero) : null;
  out.heroCtas = [];
  if (hero) {
    const ctas = Array.from(hero.querySelectorAll('a[href*="wa.me"], a[href^="tel:"], a[href^="#"], a.bs-btn, a[class*="btn"], button')).filter(visible).slice(0, 6);
    for (const c of ctas) {
      const r = c.getBoundingClientRect();
      const inView = r.top < H && r.bottom > 0;
      let ob = null;
      if (inView) ob = obstructed(c);
      else {
        // Scroll the CTA into the viewport and test there as well: the
        // floating button is fixed, so it can cover a CTA at any scroll.
        c.scrollIntoView({ block: 'center' });
        ob = obstructed(c);
        window.scrollTo(0, 0);
      }
      out.heroCtas.push({ text: text(c).slice(0, 40), path: path(c), rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], obstructedBy: ob });
    }
  }

  // --- floating button(s) ---
  out.floating = [];
  const fixedEls = Array.from(document.querySelectorAll('#whatsapp-button, a[href*="wa.me"], .binaapp-order-button, #binaapp-chat-btn, [style*="position:fixed"], [style*="position: fixed"]'))
    .filter(el => visible(el) && getComputedStyle(el).position === 'fixed');
  const seen = new Set();
  for (const el of fixedEls) {
    if (seen.has(el)) continue; seen.add(el);
    const r = el.getBoundingClientRect();
    const ob = obstructed(el);
    out.floating.push({ id: el.id || path(el), rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], obstructedBy: ob, isWa: /wa\.me/.test(el.getAttribute('href') || '') });
  }

  // --- text: clipping + contrast ---
  const parseRGBA = (s) => { const m = (s || '').match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const blend = (fg, bg) => ({ r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a), a: 1 });
  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05); };
  const bgOf = (el) => {
    // Composite background-colors up the tree; a background-image or a
    // positioned <img> behind the element counts as a photo (unknown).
    let acc = null, photo = false;
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none' && !/gradient/.test(cs.backgroundImage)) photo = true;
      if (/gradient/.test(cs.backgroundImage || '') && (!acc || acc.a < 1)) photo = true;
      const c = parseRGBA(cs.backgroundColor);
      if (c && c.a > 0) {
        if (!acc) acc = c; else if (acc.a < 1) acc = blend(acc, c);
        if (acc.a >= 1) break;
      }
      if (e.querySelector && e !== el) {
        const cover = Array.from(e.children).find(ch => (ch.tagName === 'IMG' || ch.querySelector && ch.querySelector('img')) && getComputedStyle(ch).position === 'absolute');
        if (cover) photo = true;
      }
      if (e === document.body) break;
    }
    if (!acc) acc = { r: 255, g: 255, b: 255, a: 1 };
    if (acc.a < 1) acc = blend(acc, { r: 255, g: 255, b: 255, a: 1 });
    return { color: acc, photo };
  };
  out.clipped = []; out.lowContrast = []; out.textCount = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node;
  while ((node = walker.nextNode())) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'PATH', 'IFRAME', 'OPTION'].includes(node.tagName)) continue;
    const t = ownText(node);
    if (!t) continue;
    if (!visible(node)) continue;
    out.textCount++;
    const cs = getComputedStyle(node);
    const r = node.getBoundingClientRect();
    // clipped: content wider than its box and the box hides overflow, or the box runs off the viewport
    const hidesX = cs.overflowX === 'hidden' || cs.overflowX === 'clip' || cs.textOverflow === 'clip' && cs.whiteSpace === 'nowrap';
    if ((node.scrollWidth > node.clientWidth + 2 && hidesX && cs.textOverflow !== 'ellipsis') || r.right > W + 2 || r.left < -2) {
      if (out.clipped.length < 20) out.clipped.push({ text: t.slice(0, 40), path: path(node), scrollWidth: node.scrollWidth, clientWidth: node.clientWidth, right: Math.round(r.right) });
    }
    // contrast
    const fg = parseRGBA(cs.color);
    if (!fg) continue;
    const { color: bg, photo } = bgOf(node);
    if (photo) continue;  // text over a photo: the scrim is the renderer's job, the vision review's call
    const fgc = fg.a < 1 ? blend(fg, bg) : fg;
    const px = parseFloat(cs.fontSize) || 16, bold = parseInt(cs.fontWeight, 10) >= 700;
    const need = (px >= 24 || (px >= 18.66 && bold)) ? 3.0 : 4.5;
    const rr = ratio(fgc, bg);
    if (rr < need && out.lowContrast.length < 20) out.lowContrast.push({ text: t.slice(0, 40), path: path(node), ratio: Math.round(rr * 100) / 100, need, fg: cs.color, bg: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})` });
  }

  // --- images ---
  out.images = Array.from(document.images).map(i => ({ src: (i.currentSrc || i.src || '').slice(0, 160), ok: i.complete && i.naturalWidth > 0, alt: (i.alt || '').slice(0, 40), visible: visible(i) }));

  // --- CTA buttons: icon + label ---
  const ctaSel = 'a.bs-btn, .binaapp-map-actions a, a[href*="wa.me"]:not(.bmf-order), a[href^="tel:"], a[class*="btn"]:not(.bmf-order), button.bs-btn';
  // A link is a BUTTON when it is dressed as one: a btn/button/cta class,
  // a filled background, or a border. A phone number printed as a plain
  // tel: link in the footer is text, not a CTA.
  const buttonLike = (el) => {
    if (/\b(btn|button|cta)/i.test(el.getAttribute('class') || '')) return true;
    if (el.closest('.binaapp-map-actions, .bs-cta-row, nav, header')) return true;
    const cs = getComputedStyle(el);
    const bg = parseRGBA(cs.backgroundColor);
    const padded = (parseFloat(cs.paddingLeft) || 0) >= 6;
    return (bg && bg.a > 0 && padded) || (parseFloat(cs.borderTopWidth) > 0 && padded) || cs.position === 'fixed';
  };
  out.ctas = [];
  for (const el of Array.from(document.querySelectorAll(ctaSel))) {
    if (!visible(el) || !buttonLike(el)) continue;
    const label = text(el) || (el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
    const icon = !!el.querySelector('svg, i[class*="fa-"], img, [class*="icon"]') || /\p{Extended_Pictographic}/u.test(text(el));
    out.ctas.push({ text: label.slice(0, 40), path: path(el), hasIcon: icon, hasLabel: !!label, fixed: isFixed(el) });
  }

  // --- map ---
  const iframe = document.querySelector('iframe[src*="google.com/maps"], iframe[src*="maps.google"]');
  out.map = null;
  if (iframe) {
    const r = iframe.getBoundingClientRect();
    const abs = { top: r.top + window.scrollY, height: r.height, width: r.width };
    iframe.scrollIntoView({ block: 'center' });
    const r2 = iframe.getBoundingClientRect();
    const ob = obstructed(iframe);
    const btns = Array.from(document.querySelectorAll('.binaapp-map-actions a')).filter(visible).map(a => { const b = a.getBoundingClientRect(); return { text: text(a).slice(0, 30), width: Math.round(b.width), inViewport: b.right <= W + 1 && b.left >= -1 }; });
    window.scrollTo(0, 0);
    out.map = { present: true, width: Math.round(abs.width), height: Math.round(abs.height), visibleHeight: Math.round(Math.min(r2.bottom, H) - Math.max(r2.top, 0)), obstructedBy: ob, buttons: btns };
  }
  return out;
}
"""


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


async def render(html: str, *, timeout: float = RENDER_TIMEOUT_SECONDS) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[bytes], Optional[bytes], Optional[str]]:
    """(mobile_measured, desktop_measured, mobile_png, desktop_png, error)."""
    if not playwright_available():
        return {}, {}, None, None, "playwright not installed"
    mobile: Dict[str, Any] = {}
    desktop: Dict[str, Any] = {}
    mpng = dpng = None
    try:
        from playwright.async_api import async_playwright

        async def _run() -> None:
            nonlocal mobile, desktop, mpng, dpng
            async with async_playwright() as pw:
                kwargs: Dict[str, Any] = {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]}
                exe = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
                if exe:
                    kwargs["executable_path"] = exe
                browser = await pw.chromium.launch(**kwargs)
                try:
                    for name, (w, h) in (("mobile", MOBILE), ("desktop", DESKTOP)):
                        page = await browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                        await page.set_content(html, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                        try:
                            await page.wait_for_load_state("networkidle", timeout=6000)
                        except Exception:
                            pass
                        try:
                            await page.evaluate(_PREPARE_JS)
                        except Exception as err:
                            logger.warning(f"📐 prepare step failed ({name}): {err}")
                        try:
                            measured = await page.evaluate(_MEASURE_JS)
                        except Exception as err:
                            logger.warning(f"📐 measurement failed ({name}): {err}")
                            measured = {"error": str(err)}
                        png = await page.screenshot(full_page=True, type="png")
                        if name == "mobile":
                            mobile, mpng = measured, png
                        else:
                            desktop, dpng = measured, png
                        await page.close()
                finally:
                    await browser.close()

        await asyncio.wait_for(_run(), timeout=timeout * 2 + 10)
        return mobile, desktop, mpng, dpng, None
    except Exception as err:
        return mobile, desktop, mpng, dpng, f"{type(err).__name__}: {err}"


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def evaluate_checks(mobile: Dict[str, Any], desktop: Dict[str, Any], *, expect_map: bool, expect_whatsapp: bool) -> List[Check]:
    checks: List[Check] = []
    # 1. overflow
    over = []
    for name, m in (("mobile", mobile), ("desktop", desktop)):
        if m and int(m.get("scrollWidth") or 0) > int(m.get("innerWidth") or 0) + 2:
            over.append(f"{name}: {m['scrollWidth']}px > {m['innerWidth']}px")
    checks.append(Check("no_horizontal_overflow", not over, "; ".join(over), len(over), over))
    # 2. hero CTAs
    bad = [c for c in (mobile.get("heroCtas") or []) if c.get("obstructedBy")]
    checks.append(Check("hero_cta_unobstructed", not bad, "; ".join(f"{c.get('text')!r} covered by {c['obstructedBy'].get('by')}" for c in bad), len(bad), bad))
    # 3. floating button
    fl = [f for f in (mobile.get("floating") or []) if f.get("obstructedBy")]
    checks.append(Check("floating_button_unobstructed", not fl, "; ".join(f"{f.get('id')} covered by {f['obstructedBy'].get('by')}" for f in fl), len(fl), fl))
    if expect_whatsapp and not any(f.get("isWa") for f in (mobile.get("floating") or [])):
        checks.append(Check("floating_whatsapp_present", False, "no fixed wa.me button on the page", 1, hard=False))
    # 4. clipped text
    clipped = list(mobile.get("clipped") or []) + [dict(c, viewport="desktop") for c in (desktop.get("clipped") or [])]
    checks.append(Check("no_clipped_text", not clipped, "; ".join(f"{c.get('text')!r} ({c.get('path')})" for c in clipped[:5]), len(clipped), clipped))
    # 5. contrast
    low = list(mobile.get("lowContrast") or [])
    checks.append(Check("contrast_aa", not low, "; ".join(f"{c.get('text')!r} {c.get('ratio')}:1 ({c.get('fg')} on {c.get('bg')})" for c in low[:5]), len(low), low))
    # 6. images
    broken = [i for i in (mobile.get("images") or []) if not i.get("ok")]
    checks.append(Check("images_load", not broken, "; ".join(str(i.get("src", ""))[:80] for i in broken[:5]), len(broken), broken))
    # 7. CTA icon + label
    ctas = mobile.get("ctas") or []
    bad_cta = [c for c in ctas if not (c.get("hasIcon") and c.get("hasLabel"))]
    checks.append(Check("cta_icon_and_label", not bad_cta, "; ".join(f"{c.get('text') or c.get('path')!r} missing {'icon' if not c.get('hasIcon') else 'label'}" for c in bad_cta[:5]), len(bad_cta), bad_cta))
    # 8. map
    if expect_map:
        m = mobile.get("map")
        if not m:
            checks.append(Check("map_visible", False, "no Google Maps iframe", 1))
        else:
            problems = []
            if m.get("height", 0) < 120 or m.get("visibleHeight", 0) < 100:
                problems.append(f"iframe {m.get('width')}x{m.get('height')} (visible {m.get('visibleHeight')}px)")
            if m.get("obstructedBy"):
                problems.append(f"covered by {m['obstructedBy']['by']}")
            btns = m.get("buttons") or []
            if len(btns) < 2:
                problems.append(f"{len(btns)} direction button(s) visible, need Google Maps + Waze")
            elif any(not b.get("inViewport") for b in btns):
                problems.append("a direction button sits outside the viewport")
            checks.append(Check("map_visible", not problems, "; ".join(problems), len(problems), problems))
    return checks


# ---------------------------------------------------------------------------
# Vision review
# ---------------------------------------------------------------------------

VISION_RUBRIC = (
    "You are reviewing screenshots of a small-business website rendered on a 390px-wide phone, top to bottom, "
    "in order. Answer ONLY with JSON of this exact shape:\n"
    '{"issues":[{"type":"overlap|tilted|cutoff|unreadable|other","where":"short location, e.g. hero buttons","detail":"what is wrong","severity":"high|low"}],'
    '"photo_mismatches":[{"item":"menu item name as printed","reason":"what the photo shows instead"}],"overall":"pass|fail"}\n'
    "Rules: report an issue ONLY when you can see it in the pixels: elements overlapping each other, text or buttons "
    "cut off at an edge, rotated/tilted content, text too small or too low-contrast to read. A photo mismatch is a "
    "menu card whose picture clearly shows a different kind of thing than its printed name (a drink pictured as a "
    "chicken dish, a live animal, a menu board photographed as a dish). Design taste is NOT an issue. "
    "'overall' is 'fail' only when there is at least one high-severity issue. Empty lists are the normal answer."
)


def _tiles(png: bytes, *, height: int = 1200, limit: int = VISION_MAX_TILES) -> List[bytes]:
    try:
        from PIL import Image
    except Exception:
        return [png]
    try:
        im = Image.open(io.BytesIO(png))
        w, h = im.size
    except Exception:
        return [png]
    out: List[bytes] = []
    for top in range(0, h, height):
        if len(out) >= limit:
            break
        tile = im.crop((0, top, w, min(top + height, h)))
        buf = io.BytesIO()
        tile.save(buf, format="PNG", optimize=True)
        out.append(buf.getvalue())
    return out or [png]


def build_vision_messages(mobile_png: bytes, *, item_names: Sequence[str] = (), language: str = "ms") -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = [{"type": "text", "text": VISION_RUBRIC + (
        f"\nMenu items on this page (name as printed): {', '.join(list(item_names)[:40])}." if item_names else "")
        + f"\nPage language: {'Bahasa Malaysia' if language != 'en' else 'English'}. The screenshots follow, top of page first."}]
    for tile in _tiles(mobile_png):
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(tile).decode("ascii")}})
    return [{"role": "user", "content": content}]


def parse_vision(raw: Optional[str]) -> Optional[Dict[str, Any]]:
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
    issues = []
    for i in data.get("issues") or []:
        if isinstance(i, dict):
            issues.append({
                "type": str(i.get("type") or "other")[:20], "where": str(i.get("where") or "")[:80],
                "detail": str(i.get("detail") or "")[:200], "severity": "high" if str(i.get("severity") or "").lower() == "high" else "low",
            })
    mism = []
    for m in data.get("photo_mismatches") or []:
        if isinstance(m, dict) and str(m.get("item") or "").strip():
            mism.append({"item": str(m["item"])[:120], "reason": str(m.get("reason") or "")[:200]})
        elif isinstance(m, str) and m.strip():
            mism.append({"item": m[:120], "reason": ""})
    return {"issues": issues, "photo_mismatches": mism, "overall": "fail" if str(data.get("overall") or "").lower() == "fail" else "pass", "model": VISION_MODEL}


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

async def run_gate(
    html: str,
    *,
    expect_map: bool,
    expect_whatsapp: bool,
    item_names: Sequence[str] = (),
    language: str = "ms",
    call_vision: Optional[Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]]] = None,
    attempt: int = 1,
) -> GateReport:
    """Render, measure, review. Never raises."""
    report = GateReport(attempt=attempt, mode=gate_mode())
    mobile, desktop, mpng, dpng, err = await render(html)
    report.mobile_png, report.desktop_png, report.error = mpng, dpng, err
    report.rendered = bool(mpng and mobile and "scrollWidth" in mobile)
    if not report.rendered:
        logger.warning(f"👁️ Visual gate could not render the page: {err or 'no measurements'}")
        return report
    report.checks = evaluate_checks(mobile, desktop, expect_map=expect_map, expect_whatsapp=expect_whatsapp)
    if call_vision is not None and mpng:
        raw = None
        try:
            raw = await asyncio.wait_for(call_vision(build_vision_messages(mpng, item_names=item_names, language=language)), timeout=VISION_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logger.warning(f"👁️ Vision review timed out after {VISION_TIMEOUT_SECONDS:.0f}s")
        except Exception as verr:
            logger.warning(f"👁️ Vision review failed: {verr}")
        parsed = parse_vision(raw)
        if parsed is None:
            report.checks.append(Check("vision_review", True, "no verdict (model unavailable or unparseable)", 0, hard=False))
            logger.warning("👁️ Vision review produced no verdict — gating on measurements only")
        else:
            report.vision = parsed
            report.photo_mismatches = [m["item"] for m in parsed["photo_mismatches"]]
            high = [i for i in parsed["issues"] if i["severity"] == "high"]
            detail = "; ".join(f"{i['type']} at {i['where']}: {i['detail']}" for i in high[:5])
            report.checks.append(Check("vision_review", not high, detail, len(high), high))
            if parsed["photo_mismatches"]:
                report.checks.append(Check("photo_matches_name", False, "; ".join(f"{m['item']}: {m['reason']}" for m in parsed["photo_mismatches"][:5]), len(parsed["photo_mismatches"]), parsed["photo_mismatches"], hard=False))
    logger.info(f"👁️ Visual gate attempt {attempt}: {report.summary()}")
    for c in report.checks:
        if not c.ok:
            logger.warning(f"👁️   ✗ {c.name}{'' if c.hard else ' (soft)'}: {c.detail}")
    return report


# ---------------------------------------------------------------------------
# Auto-fix: the existing guards, keyed by the failing check
# ---------------------------------------------------------------------------

_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_RE = re.compile(r"""\bsrc\s*=\s*(["'])(.*?)\1""", re.IGNORECASE)
_WA_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true" style="display:inline-block;vertical-align:-3px;margin-right:.4em"><path d="M17.5 14.4c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.8 1-.9 1.2-.2.2-.3.2-.6.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.4-.5.3-.5c.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5 2.5 1 3 .8 3.6.7.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.3-.6-.4zM12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2z"/></svg>'
_TEL_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true" style="display:inline-block;vertical-align:-3px;margin-right:.4em"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z"/></svg>'
_FIX_CSS = """
<style id="binaapp-visual-gate-fixes">
html,body{overflow-x:hidden!important;max-width:100vw}
img,video,iframe,svg,table{max-width:100%}
@media (max-width:767px){
  #home,section.bs-hero,body>section:first-of-type,header+section{padding-bottom:7rem!important}
  [class*="truncate"],[class*="nowrap"],[style*="nowrap"]{white-space:normal!important;overflow:visible!important}
}
</style>
"""


def _drop_images(html: str, srcs: Sequence[str]) -> Tuple[str, int]:
    n = 0

    def _repl(m: "re.Match") -> str:
        nonlocal n
        s = _SRC_RE.search(m.group(0))
        src = s.group(2) if s else ""
        if any(src.startswith(x[:120]) or x[:120].startswith(src[:120]) for x in srcs if x and src):
            n += 1
            return ""
        return m.group(0)
    return _IMG_RE.sub(_repl, html), n


def drop_item_photos(html: str, item_names: Sequence[str]) -> Tuple[str, int]:
    """Remove the photo from the menu card whose name is ``item`` (a vision
    photo-mismatch): the card becomes text-only, which the block styles."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return html, 0
    if not item_names:
        return html, 0
    soup = BeautifulSoup(html, "html.parser")
    n = 0
    wanted = {re.sub(r"\s+", " ", x).strip().lower() for x in item_names}
    for card in soup.select(".bmf-card"):
        name = card.select_one(".bmf-name")
        if not name or re.sub(r"\s+", " ", name.get_text()).strip().lower() not in wanted:
            continue
        media = card.select_one(".bmf-media") or card.select_one("img")
        if media is None:
            continue
        media.decompose()
        n += 1
        cls = card.get("class") or []
        if "bmf-text-only" not in cls:
            card["class"] = list(cls) + ["bmf-text-only"]
    return (str(soup) if n else html), n


def _add_cta_icons(html: str) -> Tuple[str, int]:
    n = 0

    def _fix(m: "re.Match") -> str:
        nonlocal n
        tag, inner = m.group(1), m.group(2)
        if re.search(r"<svg|<i\b|<img|class=\"[^\"]*icon", inner, re.IGNORECASE) or not re.sub(r"<[^>]+>", "", inner).strip():
            return m.group(0)
        icon = _WA_ICON if "wa.me" in tag else _TEL_ICON
        n += 1
        return f"{tag}{icon}{inner}</a>"
    out = re.sub(r"""(<a\b[^>]*href=["'](?:https?://(?:api\.)?wa\.me/|tel:)[^"']*["'][^>]*>)(.*?)</a>""", _fix, html, flags=re.IGNORECASE | re.DOTALL)
    return out, n


_RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")


def _hex_of(css_colour: str) -> Optional[str]:
    m = _RGB_RE.search(str(css_colour or ""))
    if not m:
        return None
    return "#{:02X}{:02X}{:02X}".format(*(min(255, int(v)) for v in m.groups()))


def _safe_selector(sel: str) -> bool:
    return bool(sel) and len(sel) < 300 and "{" not in sel and "}" not in sel and "<" not in sel


def targeted_fix_css(report: GateReport) -> str:
    """Rules aimed at the exact elements the measurement flagged: a clipped
    block becomes fluid, low-contrast text takes a readable shade of its
    own colour, an in-flow element covering a hero CTA loses its absolute
    position (the floating button is handled by hero padding instead)."""
    rules: List[str] = []
    failed = {c.name: c for c in report.checks if not c.ok}
    for item in (failed.get("no_clipped_text").items if "no_clipped_text" in failed else []):
        sel = item.get("path") if isinstance(item, dict) else None
        if _safe_selector(sel):
            rules.append(f"{sel}{{max-width:100%!important;width:auto!important;min-width:0!important;white-space:normal!important;overflow-wrap:anywhere}}")
    if "contrast_aa" in failed:
        try:
            from app.services.contrast_guard import adjust_for_contrast
        except Exception:  # pragma: no cover
            adjust_for_contrast = None
        for item in failed["contrast_aa"].items:
            if not isinstance(item, dict):
                continue
            sel, fg, bg = item.get("path"), _hex_of(item.get("fg")), _hex_of(item.get("bg"))
            if not (_safe_selector(sel) and fg and bg):
                continue
            fixed = adjust_for_contrast(fg, [bg], float(item.get("need") or 4.5)) if adjust_for_contrast else None
            if not fixed:
                from app.services.theme_patcher import contrast_ratio
                fixed = "#111111" if contrast_ratio("#111111", bg) >= contrast_ratio("#FFFFFF", bg) else "#FFFFFF"
            rules.append(f"{sel}{{color:{fixed}!important}}")
    for item in (failed.get("hero_cta_unobstructed").items if "hero_cta_unobstructed" in failed else []):
        ob = item.get("obstructedBy") if isinstance(item, dict) else None
        if isinstance(ob, dict) and not ob.get("fixed") and _safe_selector(ob.get("by")):
            rules.append(f"{ob['by']}{{position:static!important;transform:none!important}}")
    if not rules:
        return ""
    return '<style id="binaapp-visual-gate-targeted">\n' + "\n".join(rules) + "\n</style>\n"


def auto_fix(html: str, report: GateReport) -> Tuple[str, List[str]]:
    """Apply the guard that matches each failing check. Returns the new
    html and the list of fixes applied (empty = nothing left to try)."""
    fixes: List[str] = []
    failed = {c.name: c for c in report.checks if not c.ok}
    out = html
    if "contrast_aa" in failed:
        try:
            from app.services.contrast_guard import enforce_contrast
            out2, rep = enforce_contrast(out)
            if out2 != out:
                out = out2
                fixes.append("contrast_guard")
        except Exception as err:
            logger.warning(f"👁️ contrast guard failed: {err}")
    if "images_load" in failed:
        srcs = [i.get("src", "") for i in failed["images_load"].items if isinstance(i, dict)]
        out, n = _drop_images(out, srcs)
        if n:
            fixes.append(f"dropped_broken_images({n})")
    if "photo_matches_name" in failed:
        out, n = drop_item_photos(out, report.photo_mismatches)
        if n:
            fixes.append(f"dropped_mismatched_photos({n})")
    if "cta_icon_and_label" in failed:
        out, n = _add_cta_icons(out)
        if n:
            fixes.append(f"cta_icons({n})")
    if "hero_cta_unobstructed" in failed:
        try:
            from app.services.hero_strip import dock_hero_bottom_strip
            out2, n = dock_hero_bottom_strip(out)
            if n:
                out = out2
                fixes.append("dock_hero_strip")
        except Exception as err:
            logger.warning(f"👁️ hero strip guard failed: {err}")
    if "map_visible" in failed:
        try:
            from app.services.templates import _unclip_slot
            out2 = _unclip_slot(out, "binaapp-maps-slot")
            if out2 != out:
                out = out2
                fixes.append("unclip_map_slot")
        except Exception as err:
            logger.warning(f"👁️ map unclip failed: {err}")
    layout_keys = {"no_horizontal_overflow", "no_clipped_text", "hero_cta_unobstructed", "floating_button_unobstructed"}
    if layout_keys & set(failed) and "binaapp-visual-gate-fixes" not in out:
        out = out.replace("</head>", _FIX_CSS + "</head>", 1) if "</head>" in out else _FIX_CSS + out
        fixes.append("layout_fix_css")
    targeted = targeted_fix_css(report)
    if targeted:
        # Later rules win: appended at the end of <head>, after the page's
        # own styles and the generic fix sheet.
        out = out.replace("</head>", targeted + "</head>", 1) if "</head>" in out else out + targeted
        fixes.append(f"targeted_css({targeted.count(chr(10)) - 2})")
    return out, fixes


# ---------------------------------------------------------------------------
# Preview upload
# ---------------------------------------------------------------------------

def upload_preview(png: Optional[bytes], job_id: str, *, name: str = "mobile") -> Optional[str]:
    """The screenshot to Cloudinary (``binaapp/previews``); its URL, or
    None when Cloudinary is not configured or the upload fails."""
    if not png or not job_id:
        return None
    try:
        import cloudinary
        import cloudinary.uploader
        if not (os.getenv("CLOUDINARY_CLOUD_NAME") and os.getenv("CLOUDINARY_API_KEY") and os.getenv("CLOUDINARY_API_SECRET")):
            return None
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True,
        )
        result = cloudinary.uploader.upload(
            png, folder="binaapp/previews", public_id=f"job-{job_id}-{name}", resource_type="image",
            overwrite=True, format="png",
        )
        return result.get("secure_url") or result.get("url")
    except Exception as err:
        logger.warning(f"📸 Preview upload failed: {err}")
        return None


# ---------------------------------------------------------------------------
# Recovery loop (what the job worker runs)
# ---------------------------------------------------------------------------

class VisualGateFailed(Exception):
    """The page failed the gate after auto-fix and one regeneration."""

    MESSAGE = "Penjanaan tidak lulus semakan kualiti visual. Sila cuba lagi."

    def __init__(self, report: GateReport):
        super().__init__(self.MESSAGE)
        self.report = report


async def gate_with_recovery(
    html: str,
    *,
    expect_map: bool,
    expect_whatsapp: bool,
    item_names: Sequence[str] = (),
    language: str = "ms",
    call_vision: Optional[Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]]] = None,
    regenerate: Optional[Callable[[], Awaitable[Optional[str]]]] = None,
    job_id: str = "",
) -> Tuple[str, GateReport]:
    """Gate → auto-fix + re-gate → regenerate once + gate → fail.

    Returns the html to ship and the final report. In ``enforce`` mode a
    page that still fails raises ``VisualGateFailed``; in ``warn`` mode it
    is returned with the report; ``off`` skips the browser entirely."""
    mode = gate_mode()
    if mode == "off":
        rep = GateReport(mode=mode, error="gate off")
        return html, rep
    kw = dict(expect_map=expect_map, expect_whatsapp=expect_whatsapp, item_names=item_names, language=language, call_vision=call_vision)
    report = await run_gate(html, attempt=1, **kw)
    if not report.rendered:
        # No browser / render crash: nothing to gate on. Logged loudly; not
        # a reason to fail the merchant's job.
        logger.error(f"🚨 VISUAL_GATE_UNAVAILABLE job={job_id[:8]} error={report.error}")
        return html, report
    soft_only = report.passed and any(not c.ok for c in report.checks)
    if report.passed and not soft_only:
        return html, report
    # Attempt 2: the guards.
    fixed, fixes = auto_fix(html, report)
    if fixes:
        logger.info(f"👁️ Visual gate auto-fix: {fixes}")
        report2 = await run_gate(fixed, attempt=2, **kw)
        report2.fixes = fixes
        if report2.rendered and report2.passed:
            return fixed, report2
        if report2.rendered:
            report = report2
            html = fixed
    if report.passed:
        return html, report
    # Attempt 3: regenerate once.
    if regenerate is not None:
        logger.warning(f"👁️ Visual gate still failing ({report.summary()}) — regenerating once")
        try:
            fresh = await regenerate()
        except Exception as err:
            logger.error(f"👁️ Regeneration for the visual gate failed: {err}")
            fresh = None
        if fresh:
            report3 = await run_gate(fresh, attempt=3, **kw)
            report3.fixes = list(report.fixes) + ["regenerated"]
            if report3.rendered and report3.passed:
                return fresh, report3
            if report3.rendered:
                fixed3, fixes3 = auto_fix(fresh, report3)
                if fixes3:
                    report4 = await run_gate(fixed3, attempt=3, **kw)
                    report4.fixes = report3.fixes + fixes3
                    if report4.rendered and report4.passed:
                        return fixed3, report4
                    if report4.rendered:
                        report3, fresh = report4, fixed3
                # Serve whichever attempt failed less badly, for the warn
                # mode and the diagnostics.
                if len(report3.failed) <= len(report.failed):
                    report, html = report3, fresh
    logger.error(f"🚨 VISUAL_GATE_FAIL job={job_id[:8]} mode={mode} {report.summary()} fixes={report.fixes}")
    if mode == "enforce":
        raise VisualGateFailed(report)
    return html, report
