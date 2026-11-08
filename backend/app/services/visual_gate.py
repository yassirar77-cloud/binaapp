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

Then a vision model (``qwen3-vl-plus``) answers three questions at once:

- the page, as overlapping slices of the mobile screenshot: overlapping,
  tilted, cut-off or unreadable elements. A cut-off fails the gate only
  when the browser measured clipping or overflow too (a slice edge is not
  a page edge);
- each menu card's OWN photo against its OWN name (one crop per card);
  a mismatch drops that photo;
- the hero photo against the business; a mismatch swaps in the
  photo-free hero.

Every image is loaded AND decoded before the screenshot. Measurements are
facts; the model's opinion is advice: a measured check never passes
because the model liked the page.

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
VISION_MAX_TILES = int(os.getenv("VISUAL_GATE_VISION_TILES", "10"))
MAX_ATTEMPTS = 3  # original → auto-fixed → regenerated

HARD_CHECKS = (
    "no_horizontal_overflow", "hero_cta_unobstructed", "floating_button_unobstructed", "no_clipped_text",
    "contrast_aa", "images_load", "cta_icon_and_label", "map_visible", "vision_review",
)
#: Fixed by the gate itself, never a reason to fail: a mismatched card
#: photo is dropped, a mismatched hero photo becomes a solid hero, a slow
#: image is reported.
SOFT_CHECKS = ("photo_matches_name", "hero_matches_business", "images_drawn", "floating_whatsapp_present")


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

#: How long one image may take to arrive before the screenshot is taken
#: without it. A Cloudinary transform (c_fill, f_auto) is generated on its
#: first request and can take several seconds.
IMAGE_WAIT_MS = int(os.getenv("VISUAL_GATE_IMAGE_WAIT_MS", "15000"))

_PREPARE_JS = """
async (imgWaitMs) => {
  const frame = () => new Promise(r => requestAnimationFrame(() => r()));
  const eager = (imgs) => imgs.forEach(i => { try { i.loading = 'eager'; i.decoding = 'sync'; } catch (e) {} });
  eager(Array.from(document.images));
  // Walk the page once, a screen at a time: lazy loaders that wait for an
  // IntersectionObserver (data-src) and content-visibility sections only
  // start when they reach the viewport.
  const H = window.innerHeight || 800;
  const total = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
  for (let y = 0; y < total; y += Math.max(200, Math.floor(H * 0.9))) { window.scrollTo(0, y); await frame(); }
  const imgs = Array.from(document.images);
  eager(imgs);
  await Promise.all(imgs.map(i => new Promise(res => {
    if (i.complete) return res();
    const t = setTimeout(res, imgWaitMs);
    i.addEventListener('load', () => { clearTimeout(t); res(); }, { once: true });
    i.addEventListener('error', () => { clearTimeout(t); res(); }, { once: true });
  })));
  // Loaded is not drawn: the live agp screenshot showed every menu card as
  // an empty box with only its "Gambar hiasan" label, because the pixels
  // of a decoding="async" image were not ready when it was captured.
  // decode() resolves once they are.
  await Promise.all(imgs.filter(i => i.complete && i.naturalWidth > 0 && i.decode).map(i => i.decode().catch(() => null)));
  if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch (e) {} }
  window.scrollTo(0, 0);
  await frame(); await frame();
  return {
    total: imgs.length,
    loaded: imgs.filter(i => i.complete && i.naturalWidth > 0).length,
    pending: imgs.filter(i => !i.complete).length,
  };
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
  // ok = drawn; pending = still downloading after the wait (slow, not
  // broken: the customer's browser will show it); otherwise it failed.
  out.images = Array.from(document.images).map(i => ({ src: (i.currentSrc || i.src || '').slice(0, 160), ok: i.complete && i.naturalWidth > 0, pending: !i.complete, alt: (i.alt || '').slice(0, 40), visible: visible(i) }));

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


#: Flags that keep Chromium inside a small instance's memory (the Render
#: backend has 512 MB in total): one renderer process, no zygote, no
#: /dev/shm (often 64 MB in containers), a capped V8 heap, nothing running
#: in the background. Measured on the composed agp page; see
#: ``EXTRA_LAUNCH_ARGS`` / VISUAL_GATE_CHROMIUM_ARGS to add more.
LOW_MEMORY_ARGS = (
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-zygote",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--renderer-process-limit=1",
    "--disable-features=site-per-process,Translate,MediaRouter",
    "--js-flags=--max-old-space-size=96",
)
EXTRA_LAUNCH_ARGS: Tuple[str, ...] = ()


def launch_args() -> List[str]:
    extra = [a for a in os.getenv("VISUAL_GATE_CHROMIUM_ARGS", "").split() if a]
    return list(LOW_MEMORY_ARGS) + list(EXTRA_LAUNCH_ARGS) + extra


#: Menu cards whose photo is judged on its own (one small crop each).
CARD_PHOTO_LIMIT = int(os.getenv("VISUAL_GATE_CARD_PHOTOS", "16"))

_MARK_PHOTOS_JS = r"""
(limit) => {
  const drawn = (i) => i && i.complete && i.naturalWidth > 0 && i.getBoundingClientRect().width > 0;
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const cards = [];
  for (const card of Array.from(document.querySelectorAll('.bmf-card'))) {
    if (cards.length >= limit) break;
    const img = card.querySelector('img');
    const name = card.querySelector('.bmf-name');
    if (!drawn(img) || !name) continue;
    img.setAttribute('data-bvg-card', String(cards.length));
    cards.push(norm(name.innerText || name.textContent).slice(0, 120));
  }
  // The hero photo: the composed hero's media, else the biggest drawn
  // image in the first section, else the section itself when its photo is
  // a CSS background.
  let hero = null, heroKind = null;
  const sec = document.querySelector('#home, section.bs-hero, header + section, main > section:first-of-type, body > section:first-of-type');
  if (sec) {
    const media = sec.querySelector('.bs-hero-media img');
    if (drawn(media)) { hero = media; heroKind = 'img'; }
    if (!hero) {
      const W = window.innerWidth;
      const big = Array.from(sec.querySelectorAll('img')).filter(i => drawn(i) && i.getBoundingClientRect().width >= W * 0.5);
      if (big.length) { hero = big[0]; heroKind = 'img'; }
    }
    if (!hero) {
      for (const e of [sec, ...Array.from(sec.querySelectorAll('*')).slice(0, 40)]) {
        const bg = getComputedStyle(e).backgroundImage || '';
        if (/url\(/.test(bg) && e.getBoundingClientRect().width >= window.innerWidth * 0.5) { hero = e; heroKind = 'background'; break; }
      }
    }
  }
  if (hero) hero.setAttribute('data-bvg-hero', '1');
  return { cards, heroKind };
}
"""


def _shrink(png: Optional[bytes], width: int = 360) -> Optional[bytes]:
    """A crop at most ``width`` px wide (fewer vision tokens; a photo's
    subject survives the downscale)."""
    if not png:
        return png
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(png))
        if im.size[0] <= width:
            return png
        im = im.resize((width, max(1, round(im.size[1] * width / im.size[0]))))
        buf = io.BytesIO()
        im.convert("RGB").save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except Exception:
        return png


async def _photo_crops(page: Any) -> Dict[str, Any]:
    """Each menu card's OWN photo and the hero photo, as separate images,
    so the vision model judges a card by its picture alone. On the full
    page it attributed the hero's burger to all seven agp cards ("same
    burger photo used") and seven good photos were dropped."""
    out: Dict[str, Any] = {"cards": [], "hero": None, "hero_kind": None}
    try:
        marked = await page.evaluate(_MARK_PHOTOS_JS, CARD_PHOTO_LIMIT)
    except Exception as err:
        logger.warning(f"📐 photo marking failed: {err}")
        return out
    for i, name in enumerate(marked.get("cards") or []):
        try:
            png = await page.locator(f'[data-bvg-card="{i}"]').first.screenshot(type="png", timeout=5000)
            out["cards"].append({"name": name, "png": _shrink(png)})
        except Exception as err:
            logger.warning(f"📐 card photo {i} crop failed: {err}")
    if marked.get("heroKind"):
        try:
            png = await page.locator('[data-bvg-hero="1"]').first.screenshot(type="png", timeout=5000)
            out["hero"], out["hero_kind"] = _shrink(png, 512), marked["heroKind"]
        except Exception as err:
            logger.warning(f"📐 hero photo crop failed: {err}")
    return out


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


async def render(html: str, *, timeout: float = RENDER_TIMEOUT_SECONDS,
                 desktop_full_page: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[bytes], Optional[bytes], Optional[str]]:
    """(mobile_measured, desktop_measured, mobile_png, desktop_png, error).

    The mobile screenshot is full-page (the vision review reads it); the
    desktop one is the first viewport unless ``desktop_full_page`` (the
    golden suite keeps both for its artefacts) — a full-page desktop
    capture costs ~130 MB more at its peak. Refuses to launch Chromium
    when the container lacks the memory for it (services/browser_budget)."""
    if not playwright_available():
        return {}, {}, None, None, "playwright not installed"
    from app.services.browser_budget import can_launch
    allowed, why = can_launch()
    if not allowed:
        return {}, {}, None, None, why
    mobile: Dict[str, Any] = {}
    desktop: Dict[str, Any] = {}
    mpng = dpng = None
    try:
        from playwright.async_api import async_playwright

        async def _run() -> None:
            nonlocal mobile, desktop, mpng, dpng
            async with async_playwright() as pw:
                kwargs: Dict[str, Any] = {"headless": True, "args": launch_args()}
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
                            prepared = await page.evaluate(_PREPARE_JS, IMAGE_WAIT_MS)
                            if isinstance(prepared, dict) and prepared.get("pending"):
                                logger.warning(f"📐 {prepared['pending']}/{prepared.get('total')} image(s) still loading at the {name} screenshot")
                        except Exception as err:
                            logger.warning(f"📐 prepare step failed ({name}): {err}")
                        try:
                            measured = await page.evaluate(_MEASURE_JS)
                        except Exception as err:
                            logger.warning(f"📐 measurement failed ({name}): {err}")
                            measured = {"error": str(err)}
                        png = await page.screenshot(full_page=(name == "mobile" or desktop_full_page), type="png")
                        if name == "mobile":
                            # After the full-page shot: the crops scroll.
                            measured["_crops"] = await _photo_crops(page)
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
    # 6. images: a failed download is broken (the fix drops it); one still
    # arriving after the wait is slow, which is reported but never a
    # reason to take the merchant's photo off the page.
    imgs = mobile.get("images") or []
    broken = [i for i in imgs if not i.get("ok") and not i.get("pending")]
    checks.append(Check("images_load", not broken, "; ".join(str(i.get("src", ""))[:80] for i in broken[:5]), len(broken), broken))
    slow = [i for i in imgs if i.get("pending")]
    if slow:
        checks.append(Check("images_drawn", False, f"{len(slow)} still loading at the screenshot: "
                            + "; ".join(str(i.get("src", ""))[:80] for i in slow[:3]), len(slow), slow, hard=False))
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

#: The page is read in slices; each overlaps the next by this much, so an
#: element cut by one slice's bottom edge is whole at the top of the next.
VISION_TILE_HEIGHT = int(os.getenv("VISUAL_GATE_TILE_HEIGHT", "1400"))
VISION_TILE_OVERLAP = int(os.getenv("VISUAL_GATE_TILE_OVERLAP", "250"))

VISION_RUBRIC = (
    "You are reviewing screenshots of a small-business website rendered on a 390px-wide phone. The page is long, so "
    "it comes as consecutive SLICES, top of the page first. Each slice overlaps the next by about "
    f"{VISION_TILE_OVERLAP}px: content touching the top or bottom edge of a slice continues in the next slice. "
    "That is how the screenshots were cut, NOT a cut-off on the page — never report it. Answer ONLY with JSON of this "
    "exact shape:\n"
    '{"issues":[{"type":"overlap|tilted|cutoff|unreadable|other","where":"short location, e.g. hero buttons","detail":"what is wrong","severity":"high|low"}],"overall":"pass|fail"}\n'
    "Rules: report an issue ONLY when you can see it in the pixels: elements overlapping each other, text or buttons "
    "cut off by the LEFT or RIGHT edge of the phone or by their own box, rotated/tilted content, text too small or too "
    "low-contrast to read. Do not judge the photos (they are checked separately) and do not report an image that "
    "looks blank. Design taste is NOT an issue. 'overall' is 'fail' only when there is at least one high-severity "
    "issue. An empty list is the normal answer."
)

CARD_PHOTO_RUBRIC = (
    "Each image below is the photo on ONE menu card of a small-business website, and comes right after that card's "
    "printed name. Judge every photo ONLY against its own card's name. First find the NAMED DISH: the main item the "
    "name is about (for 'Set Udang Krispy' it is crispy prawns; for 'Set B – Ayam Gepuk Tauhu Tempe' it is ayam "
    "gepuk). If the named dish is clearly visible in the photo, the photo MATCHES, even when rice, side dishes, "
    "sambal or garnish take up much of the plate: a set meal is expected to come with sides. A mismatch is ONLY a "
    "photo where the named dish cannot be seen at all, or a different main dish takes its place: a drink pictured "
    "as a chicken dish, a burger for 'Ayam Gepuk', squid missing from 'Set Sotong Krispy', a live animal, a menu "
    "board or a poster photographed as a dish. Plating, angle and garnish are never a reason. Answer ONLY with JSON: "
    '{"mismatches":[{"card":<number>,"named_dish":"what the name is about","named_dish_visible":false,'
    '"reason":"what the photo shows instead"}]}. List only cards whose named dish is NOT visible. An empty list is '
    "the normal answer."
)

HERO_RUBRIC = (
    "This image is the hero (top banner) photo of the website of the business described below. Does it show this "
    "business's own kind of product, food or service? A generic but fitting scene counts as a match (a plate of "
    "Malaysian rice dishes for a Malaysian restaurant, tools for a workshop). A different kind of food or trade is a "
    "mismatch (a burger and fries for an ayam gepuk stall, a cake for a mechanic, a salon for a phone shop). Text "
    "laid over the photo is the page's own heading: ignore it. Answer ONLY with JSON: "
    '{"matches":true|false,"shows":"what the photo shows","reason":"why it does or does not fit"}'
)


def _tiles(png: bytes, *, height: int = VISION_TILE_HEIGHT, overlap: int = VISION_TILE_OVERLAP,
           limit: int = VISION_MAX_TILES) -> List[bytes]:
    """The full-page screenshot as overlapping slices. Non-overlapping
    1200px slices cut mamak's menu cards in two, the model reported every
    one as "cut off at the bottom edge", and a good page failed."""
    try:
        from PIL import Image
    except Exception:
        return [png]
    try:
        im = Image.open(io.BytesIO(png))
        w, h = im.size
    except Exception:
        return [png]
    step = max(200, height - max(0, overlap))
    out: List[bytes] = []
    top = 0
    while top < h and len(out) < limit:
        tile = im.crop((0, top, w, min(top + height, h)))
        buf = io.BytesIO()
        tile.save(buf, format="PNG", optimize=True)
        out.append(buf.getvalue())
        if top + height >= h:
            break
        top += step
    return out or [png]


def build_vision_messages(mobile_png: bytes, *, item_names: Sequence[str] = (), language: str = "ms") -> List[Dict[str, Any]]:
    tiles = _tiles(mobile_png)
    content: List[Dict[str, Any]] = [{"type": "text", "text": VISION_RUBRIC
        + f"\nPage language: {'Bahasa Malaysia' if language != 'en' else 'English'}. {len(tiles)} slice(s) follow, top of page first."}]
    for i, tile in enumerate(tiles, 1):
        content.append({"type": "text", "text": f"Slice {i} of {len(tiles)}:"})
        content.append({"type": "image_url", "image_url": {"url": _data_url(tile)}})
    return [{"role": "user", "content": content}]


def _data_url(img: bytes) -> str:
    mime = "image/jpeg" if img[:3] == b"\xff\xd8\xff" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(img).decode("ascii")


def build_card_photo_messages(cards: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    content: List[Dict[str, Any]] = [{"type": "text", "text": CARD_PHOTO_RUBRIC}]
    for i, card in enumerate(cards, 1):
        content.append({"type": "text", "text": f"Card {i}: {card['name']}"})
        content.append({"type": "image_url", "image_url": {"url": _data_url(card["png"])}})
    return [{"role": "user", "content": content}]


def build_hero_messages(hero_png: bytes, business: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = [str(x) for x in (business.get("items") or []) if x][:10]
    about = (
        f"Business: {business.get('name') or '-'}\nType: {business.get('type') or '-'}\n"
        f"What they sell / do: {str(business.get('description') or '-')[:400]}\n"
        + (f"Items: {', '.join(items)}\n" if items else "")
    )
    return [{"role": "user", "content": [
        {"type": "text", "text": HERO_RUBRIC + "\n\n" + about},
        {"type": "image_url", "image_url": {"url": _data_url(hero_png)}},
    ]}]


def _json_object(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    for candidate in (text[start:end + 1], re.sub(r",\s*([}\]])", r"\1", text[start:end + 1])):
        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def parse_card_photos(raw: Optional[str], cards: Sequence[Dict[str, Any]]) -> Optional[List[Dict[str, str]]]:
    """Mismatches as [{"item": card name, "reason": ...}]; None = no verdict."""
    data = _json_object(raw)
    if data is None:
        return None
    out: List[Dict[str, str]] = []
    for m in data.get("mismatches") or []:
        if not isinstance(m, dict):
            continue
        try:
            idx = int(str(m.get("card")).strip().lstrip("#")) - 1
        except (TypeError, ValueError):
            continue
        # The model listed the card but says the named dish IS there (agp's
        # Set Udang Krispy: "shrimp are present, but tofu and tempeh ..."):
        # that is a photo with side dishes, not a mismatch.
        visible = m.get("named_dish_visible")
        if visible is True or str(visible).strip().lower() in ("true", "yes"):
            continue
        if 0 <= idx < len(cards) and cards[idx]["name"] not in [x["item"] for x in out]:
            out.append({"item": cards[idx]["name"], "reason": str(m.get("reason") or "")[:200]})
    return out


def parse_hero(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    data = _json_object(raw)
    if data is None or "matches" not in data:
        return None
    val = data.get("matches")
    matches = val if isinstance(val, bool) else str(val).strip().lower() not in ("false", "no", "0")
    return {"matches": matches, "shows": str(data.get("shows") or "")[:160], "reason": str(data.get("reason") or "")[:200]}


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

#: Vision issue types that are about something being cut off. The model
#: cannot tell a page edge from a slice edge reliably, so these fail the
#: gate only when the browser measured clipping or overflow too.
_CUTOFF_TYPES = ("cutoff", "cut-off", "cut off", "clipped", "truncated")


def _is_cutoff(issue: Dict[str, Any]) -> bool:
    t = str(issue.get("type") or "").lower()
    if any(k in t for k in _CUTOFF_TYPES):
        return True
    return t == "other" and bool(re.search(r"\bcut(?:\s|-)?off\b|\btruncat", str(issue.get("detail") or ""), re.IGNORECASE))


async def _ask(call_vision: Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]], messages: List[Dict[str, Any]], what: str) -> Optional[str]:
    try:
        return await asyncio.wait_for(call_vision(messages), timeout=VISION_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning(f"👁️ Vision {what} timed out after {VISION_TIMEOUT_SECONDS:.0f}s")
    except Exception as verr:
        logger.warning(f"👁️ Vision {what} failed: {verr}")
    return None


async def run_gate(
    html: str,
    *,
    expect_map: bool,
    expect_whatsapp: bool,
    item_names: Sequence[str] = (),
    language: str = "ms",
    call_vision: Optional[Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]]] = None,
    attempt: int = 1,
    desktop_full_page: bool = False,
    business: Optional[Dict[str, Any]] = None,
) -> GateReport:
    """Render, measure, review. Never raises.

    Three vision questions, asked at once: the page layout (overlapping
    slices), each menu card's own photo against its own name, and the hero
    photo against the business (``business`` = name/type/description/items;
    skipped without it)."""
    report = GateReport(attempt=attempt, mode=gate_mode())
    mobile, desktop, mpng, dpng, err = await render(html, desktop_full_page=desktop_full_page)
    report.mobile_png, report.desktop_png, report.error = mpng, dpng, err
    report.rendered = bool(mpng and mobile and "scrollWidth" in mobile)
    if not report.rendered:
        logger.warning(f"👁️ Visual gate could not render the page: {err or 'no measurements'}")
        return report
    report.checks = evaluate_checks(mobile, desktop, expect_map=expect_map, expect_whatsapp=expect_whatsapp)
    crops = mobile.get("_crops") or {}
    if call_vision is not None and mpng:
        cards = [c for c in (crops.get("cards") or []) if c.get("png")]
        hero_png = crops.get("hero")
        asks = [_ask(call_vision, build_vision_messages(mpng, item_names=item_names, language=language), "page review")]
        asks.append(_ask(call_vision, build_card_photo_messages(cards), "card photo check") if cards else asyncio.sleep(0, result=None))
        asks.append(_ask(call_vision, build_hero_messages(hero_png, business), "hero check") if (hero_png and business) else asyncio.sleep(0, result=None))
        raw_page, raw_cards, raw_hero = await asyncio.gather(*asks)

        parsed = parse_vision(raw_page)
        if parsed is None:
            report.checks.append(Check("vision_review", True, "no verdict (model unavailable or unparseable)", 0, hard=False))
            logger.warning("👁️ Vision review produced no verdict — gating on measurements only")
        else:
            report.vision = parsed
            measured_clip = any(c.name in ("no_clipped_text", "no_horizontal_overflow") and not c.ok for c in report.checks)
            for issue in parsed["issues"]:
                if issue["severity"] == "high" and _is_cutoff(issue) and not measured_clip:
                    issue["severity"] = "low"
                    issue["note"] = "cut-off not confirmed by the browser's measurements"
            high = [i for i in parsed["issues"] if i["severity"] == "high"]
            unconfirmed = [i for i in parsed["issues"] if i.get("note")]
            detail = "; ".join(f"{i['type']} at {i['where']}: {i['detail']}" for i in high[:5])
            report.checks.append(Check("vision_review", not high, detail, len(high), high))
            if unconfirmed:
                logger.info(f"👁️ {len(unconfirmed)} cut-off report(s) ignored: the measurements show nothing clipped")
            # A page-level photo verdict (older prompt) still counts when
            # no card was cropped; the per-card check supersedes it.
            if parsed["photo_mismatches"] and not cards:
                report.photo_mismatches = [m["item"] for m in parsed["photo_mismatches"]]
                report.checks.append(Check("photo_matches_name", False, "; ".join(f"{m['item']}: {m['reason']}" for m in parsed["photo_mismatches"][:5]), len(parsed["photo_mismatches"]), parsed["photo_mismatches"], hard=False))

        if cards:
            mism = parse_card_photos(raw_cards, cards)
            if mism is None:
                logger.warning(f"👁️ Card photo check produced no verdict ({len(cards)} card(s)) — photos kept")
            else:
                report.vision = {**(report.vision or {}), "card_photos_checked": len(cards), "card_photo_mismatches": mism}
                if mism:
                    report.photo_mismatches = [m["item"] for m in mism]
                    report.checks.append(Check("photo_matches_name", False, "; ".join(f"{m['item']}: {m['reason']}" for m in mism[:5]), len(mism), mism, hard=False))
                else:
                    report.checks.append(Check("photo_matches_name", True, f"{len(cards)} card photo(s) match their names", 0, hard=False))

        if hero_png and business:
            hero = parse_hero(raw_hero)
            if hero is None:
                logger.warning("👁️ Hero check produced no verdict — hero kept")
            else:
                report.vision = {**(report.vision or {}), "hero": {**hero, "kind": crops.get("hero_kind")}}
                report.checks.append(Check(
                    "hero_matches_business", hero["matches"],
                    "" if hero["matches"] else f"hero shows {hero['shows'] or 'something else'}: {hero['reason']}",
                    0 if hero["matches"] else 1, [hero], hard=False,
                ))
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


_HERO_FALLBACK_CSS = """
<style id="binaapp-visual-gate-hero">
#home,section.bs-hero,body>section:first-of-type{background-image:none!important}
#home[data-bvg-solid],section[data-bvg-solid]{background-color:var(--primary-color,#1F2937)!important;color:#fff!important}
</style>
"""


def use_photo_free_hero(html: str) -> Tuple[str, int]:
    """The hero without its photo (a hero-vs-business mismatch: agp shipped
    a burger and fries above its ayam gepuk). A composed hero becomes the
    composer's own solid variant (``bs-hero-solid``: surface colour, dark
    text); a freeform hero loses its photo and takes the primary colour."""
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return html, 0
    soup = BeautifulSoup(html, "html.parser")
    hero = soup.select_one("section.bs-hero")
    if hero is not None:
        removed = 0
        for el in hero.select(".bs-hero-media, .bs-hero-scrim"):
            el.decompose()
            removed += 1
        cls = hero.get("class") or []
        if "bs-hero-solid" not in cls:
            hero["class"] = list(cls) + ["bs-hero-solid"]
            removed += 1
        return (str(soup), 1) if removed else (html, 0)
    hero = soup.select_one("#home") or soup.select_one("header + section") or soup.select_one("main > section") or soup.select_one("body > section")
    if hero is None:
        return html, 0
    n = 0
    imgs = hero.find_all("img")
    for img in imgs:
        w = str(img.get("width") or "")
        if img.get("fetchpriority") == "high" or (w.isdigit() and int(w) >= 600) or "hero" in " ".join(img.get("class") or []).lower() or len(imgs) == 1:
            img.decompose()
            n += 1
    style = str(hero.get("style") or "")
    if "background" in style and "url(" in style:
        hero["style"] = re.sub(r"background(?:-image)?\s*:[^;]*url\([^)]*\)[^;]*;?", "", style)
        n += 1
    hero["data-bvg-solid"] = "1"
    out = str(soup)
    out = out.replace("</head>", _HERO_FALLBACK_CSS + "</head>", 1) if "</head>" in out else _HERO_FALLBACK_CSS + out
    return out, 1


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
    if "hero_matches_business" in failed:
        out, n = use_photo_free_hero(out)
        if n:
            fixes.append("photo_free_hero")
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
    business: Optional[Dict[str, Any]] = None,
) -> Tuple[str, GateReport]:
    """Gate → auto-fix + re-gate → regenerate once + gate → fail.

    Returns the html to ship and the final report. In ``enforce`` mode a
    page that still fails raises ``VisualGateFailed``; in ``warn`` mode it
    is returned with the report; ``off`` skips the browser entirely."""
    mode = gate_mode()
    if mode == "off":
        rep = GateReport(mode=mode, error="gate off")
        return html, rep
    kw = dict(expect_map=expect_map, expect_whatsapp=expect_whatsapp, item_names=item_names, language=language, call_vision=call_vision,
              business=business)
    report = await run_gate(html, attempt=1, **kw)
    if not report.rendered:
        # No browser / render crash: nothing to gate on. Logged loudly; not
        # a reason to fail the merchant's job.
        if report.error and report.error.startswith("insufficient memory"):
            logger.warning(f"🧠 VISUAL_GATE_SKIPPED_MEMORY job={job_id[:8]} {report.error}")
        else:
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
