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
  tilted, cut-off or unreadable elements. A cut-off, an overlap or
  unreadable text fails the gate only when the browser measured the same
  kind of problem too (the numbers overrule the picture); anything else
  needs a second look to confirm it;
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
    # gate audit (each proven by a planted defect in scripts/gate_calibration.py)
    "hero_text_legible", "text_readable_size", "tap_targets", "no_overlapping_text", "images_not_distorted",
    "no_empty_sections", "no_junk_text",
)
#: Fixed by the gate itself, never a reason to fail: a mismatched card
#: photo is dropped, a mismatched hero photo becomes a solid hero, a slow
#: image is reported.
SOFT_CHECKS = ("photo_matches_name", "hero_matches_business", "images_drawn", "floating_whatsapp_present",
               "no_duplicate_photos", "links_work", "no_blank_bands", "images_sharp", "heading_structure",
               "primary_action_above_fold")


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
#: How long to wait for the network to go quiet after the page is set.
NETWORK_IDLE_MS = int(os.getenv("VISUAL_GATE_NETWORK_IDLE_MS", "6000"))

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
  // A selector that matches this element and no other: what a fix rule is
  // written for. (`path` is the readable one for the report; a fix on
  // `p` recoloured every paragraph on the page.)
  const uniq = (el) => {
    const parts = [];
    for (let e = el; e && e.nodeType === 1 && e !== document.documentElement; e = e.parentElement) {
      if (e === document.body) { parts.unshift('body'); break; }
      if (e.id && document.querySelectorAll('#' + CSS.escape(e.id)).length === 1) { parts.unshift('#' + CSS.escape(e.id)); break; }
      let i = 1;
      for (let sib = e.previousElementSibling; sib; sib = sib.previousElementSibling) if (sib.tagName === e.tagName) i++;
      parts.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + i + ')');
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
      if (t && !contains(t, el)) return { by: path(t), bySel: uniq(t), at: [Math.round(x), Math.round(y)], fixed: isFixed(t) };
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
      if (out.clipped.length < 20) out.clipped.push({ text: t.slice(0, 40), path: path(node), sel: uniq(node), scrollWidth: node.scrollWidth, clientWidth: node.clientWidth, right: Math.round(r.right) });
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
    if (rr < need && out.lowContrast.length < 120) out.lowContrast.push({ text: t.slice(0, 40), path: path(node), sel: uniq(node), ratio: Math.round(rr * 100) / 100, need, fg: cs.color, bg: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})` });
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


#: Design measurements added by the gate audit (scripts/gate_calibration.py
#: plants one defect per check and proves each is caught). Separate from
#: _MEASURE_JS so the original checks stay as they were.
_DESIGN_JS = r"""
() => {
  const W = window.innerWidth, H = window.innerHeight;
  document.documentElement.style.scrollBehavior = 'auto';
  window.scrollTo(0, 0);
  const out = {};
  // A selector that matches this element and no other.
  const uniq = (el) => {
    const parts = [];
    for (let e = el; e && e.nodeType === 1 && e !== document.documentElement; e = e.parentElement) {
      if (e === document.body) { parts.unshift('body'); break; }
      if (e.id && document.querySelectorAll('#' + CSS.escape(e.id)).length === 1) { parts.unshift('#' + CSS.escape(e.id)); break; }
      let i = 1;
      for (let sib = e.previousElementSibling; sib; sib = sib.previousElementSibling) if (sib.tagName === e.tagName) i++;
      parts.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + i + ')');
    }
    return parts.join('>');
  };
  const shown = (el) => {
    if (el.checkVisibility && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const ownText = (el) => Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join('').replace(/\s+/g, ' ').trim();
  const isFixed = (el) => { for (let e = el; e && e !== document.body; e = e.parentElement) { const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') return true; } return false; };
  const SKIP = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'PATH', 'IFRAME', 'OPTION', 'SELECT', 'TEXTAREA', 'TEMPLATE'];
  const sy = window.scrollY;

  // ---- every element that prints text of its own, with its line boxes ----
  const texts = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node;
  while ((node = walker.nextNode())) {
    if (SKIP.includes(node.tagName) || node.closest('svg')) continue;
    const t = ownText(node);
    if (!t || !shown(node)) continue;
    const r = node.getBoundingClientRect();
    if (r.right < 2 || r.left > W - 2) continue;  // parked off-screen (closed drawers)
    const lines = [];
    for (const child of node.childNodes) {
      if (child.nodeType !== 3 || !child.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(child);
      for (const lr of range.getClientRects()) if (lr.width > 1 && lr.height > 1) lines.push([lr.left, lr.top + sy, lr.right, lr.bottom + sy]);
    }
    const cs = getComputedStyle(node);
    texts.push({ el: node, text: t, lines, size: parseFloat(cs.fontSize) || 16, fixed: isFixed(node) });
  }

  // ---- text too small to read ----
  out.tinyText = [];
  for (const t of texts) {
    if (t.el.closest('.bmf-ai-label, .bs-ai-label, sup, sub')) continue;  // the "Gambar hiasan" tag is small on purpose
    if ((t.size < 11.5 && t.text.length >= 25) || t.size < 9) {
      if (out.tinyText.length < 120) out.tinyText.push({ text: t.text.slice(0, 40), path: uniq(t.el), size: Math.round(t.size * 10) / 10 });
    }
  }

  // ---- text printed on top of other text ----
  out.overlaps = [];
  const flow = texts.filter(t => !t.fixed && t.lines.length).sort((a, b) => a.lines[0][1] - b.lines[0][1]);
  const bottom = (t) => Math.max(...t.lines.map(l => l[3]));
  for (let i = 0; i < flow.length && out.overlaps.length < 12; i++) {
    const a = flow[i], aBottom = bottom(a);
    for (let j = i + 1; j < flow.length; j++) {
      const b = flow[j];
      if (b.lines[0][1] > aBottom) break;
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      let hit = false;
      for (const la of a.lines) {
        for (const lb of b.lines) {
          const iw = Math.min(la[2], lb[2]) - Math.max(la[0], lb[0]);
          const ih = Math.min(la[3], lb[3]) - Math.max(la[1], lb[1]);
          if (iw <= 4 || ih <= 5) continue;
          const small = Math.min((la[2] - la[0]) * (la[3] - la[1]), (lb[2] - lb[0]) * (lb[3] - lb[1]));
          if (small > 0 && (iw * ih) / small >= 0.35) { hit = true; break; }
        }
        if (hit) break;
      }
      if (hit) { out.overlaps.push({ text: a.text.slice(0, 30), other: b.text.slice(0, 30), path: uniq(b.el), under: uniq(a.el) }); break; }
    }
  }

  // ---- things you tap that are too small to tap ----
  const rgba = (str) => { const m = (str || '').match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(parseFloat); return { a: p.length > 3 ? p[3] : 1 }; };
  const buttonLike = (el) => {
    if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') return true;
    if (/\b(btn|button|cta|order)/i.test(el.getAttribute('class') || '')) return true;
    const cs = getComputedStyle(el);
    const bg = rgba(cs.backgroundColor);
    const padded = (parseFloat(cs.paddingLeft) || 0) >= 6;
    return (bg && bg.a > 0 && padded) || (parseFloat(cs.borderTopWidth) > 0 && padded) || cs.position === 'fixed';
  };
  out.smallTargets = [];
  for (const el of document.querySelectorAll('a[href], button, [role="button"], input[type="submit"], input[type="button"]')) {
    if (!shown(el) || !buttonLike(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right < 2 || r.left > W - 2) continue;
    if (Math.min(r.width, r.height) < 24 && out.smallTargets.length < 120) {
      out.smallTargets.push({ text: ((el.innerText || el.getAttribute('aria-label') || '').trim()).slice(0, 30), path: uniq(el), size: [Math.round(r.width), Math.round(r.height)] });
    }
  }

  // ---- photos: squashed, blurry, repeated ----
  const norm = (src) => (src || '').replace(/(\/upload\/)(?:[a-z]{1,3}_[^\/]+\/)+/, '$1').split('?')[0];
  out.distorted = []; out.blurry = [];
  const bySrc = {};
  for (const img of document.images) {
    if (!shown(img) || !img.complete || !img.naturalWidth) continue;
    const r = img.getBoundingClientRect();
    if (r.width < 80 || r.height < 50) continue;
    const cs = getComputedStyle(img);
    const drawn = r.width / r.height, natural = img.naturalWidth / img.naturalHeight;
    if (cs.objectFit === 'fill' && Math.abs(drawn / natural - 1) > 0.18) {
      out.distorted.push({ src: (img.currentSrc || img.src || '').slice(0, 120), path: uniq(img), drawn: Math.round(drawn * 100) / 100, natural: Math.round(natural * 100) / 100 });
    }
    if (r.width >= 160 && img.naturalWidth < r.width * 0.5 && !/\.svg(\?|$)/i.test(img.src)) {
      out.blurry.push({ src: (img.currentSrc || img.src || '').slice(0, 120), path: uniq(img), natural: img.naturalWidth, shown: Math.round(r.width) });
    }
    if (r.width >= 140) {
      const key = norm(img.currentSrc || img.src);
      const card = img.closest('.bmf-card');
      const name = card && card.querySelector('.bmf-name');
      (bySrc[key] = bySrc[key] || []).push({ path: uniq(img), card: name ? (name.innerText || name.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80) : null });
    }
  }
  out.duplicates = Object.entries(bySrc).filter(([, v]) => v.length >= 2).map(([src, v]) => ({ src: src.slice(0, 120), count: v.length, cards: v.map(x => x.card).filter(Boolean), paths: v.map(x => x.path) }));

  // ---- a section with a heading and nothing under it ----
  out.emptySections = [];
  for (const sec of document.querySelectorAll('section')) {
    if (!shown(sec)) continue;
    const heads = Array.from(sec.querySelectorAll('h1, h2, h3, h4'));
    if (!heads.length) continue;
    if (sec.querySelector('img, iframe, video, canvas, form, input, table, picture, [style*="background-image"]')) continue;
    let rest = (sec.innerText || '').replace(/\s+/g, ' ').trim();
    for (const h of heads) rest = rest.replace((h.innerText || '').replace(/\s+/g, ' ').trim(), '');
    if (rest.trim().length < 3) out.emptySections.push({ heading: (heads[0].innerText || '').trim().slice(0, 40), path: uniq(sec) });
  }

  // ---- text nobody wrote ----
  const JUNK = [/\bundefined\b/, /\bNaN\b/, /\[object Object\]/, /\{\{[^}]{0,40}\}\}/, /Lorem ipsum/i, /\[ISI\b/, /\bRM\s?(?:null|None|nan)\b/i, /\$\{[^}]{0,40}\}/, /\bTODO\b/, /%[sd]\b/];
  out.junk = [];
  for (const t of texts) {
    const m = JUNK.map(re => t.text.match(re)).find(Boolean);
    if (m && out.junk.length < 12) out.junk.push({ text: t.text.slice(0, 60), found: m[0], path: uniq(t.el) });
  }

  // ---- links that go nowhere ----
  out.deadLinks = [];
  for (const a of document.querySelectorAll('a[href]')) {
    if (!shown(a)) continue;
    const href = a.getAttribute('href') || '';
    let why = null;
    if (href.length > 1 && href[0] === '#' && href !== '#top') {
      let id = href.slice(1);
      try { id = decodeURIComponent(id); } catch (e) {}
      if (!document.getElementById(id) && !document.getElementsByName(id).length) why = 'no section with this id';
    } else if (/wa\.me\//.test(href)) {
      const digits = (href.split('wa.me/')[1] || '').split('?')[0].replace(/\D/g, '');
      if (digits.length < 9) why = 'WhatsApp number too short';
    } else if (/^tel:/.test(href)) {
      if (href.replace(/\D/g, '').length < 7) why = 'phone number too short';
    }
    if (why && out.deadLinks.length < 12) out.deadLinks.push({ text: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 30), href: href.slice(0, 80), why, path: uniq(a) });
  }

  // ---- headings and the first screen ----
  const h1s = Array.from(document.querySelectorAll('h1')).filter(shown);
  out.h1Count = h1s.length;
  out.h1Top = h1s.length ? Math.round(h1s[0].getBoundingClientRect().top + sy) : null;
  const hero = document.querySelector('#home, section.bs-hero, header + section, main > section:first-of-type, body > section:first-of-type');
  const cta = hero ? Array.from(hero.querySelectorAll('a[href*="wa.me"], a[href^="tel:"], a.bs-btn, a[class*="btn"], button')).find(shown) : null;
  out.ctaTop = cta ? Math.round(cta.getBoundingClientRect().top + sy) : null;
  out.viewportHeight = H;
  return out;
}
"""

#: Hero text drawn over a photo: mark it, make it invisible, and let the
#: caller sample the pixels behind it. Returns the marked elements.
_HERO_TEXT_JS = r"""
() => {
  const H = window.innerHeight, W = window.innerWidth;
  window.scrollTo(0, 0);
  const hero = document.querySelector('#home, section.bs-hero, header + section, main > section:first-of-type, body > section:first-of-type');
  if (!hero) return [];
  const rgba = (str) => { const m = (str || '').match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map(parseFloat); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const overPhoto = (el) => {
    // Opaque colour of its own before the hero is reached = not on the photo.
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      const c = rgba(cs.backgroundColor);
      if (c && c.a >= 0.9) return false;
      if (cs.backgroundImage && /url\(/.test(cs.backgroundImage)) return true;
      if (e === hero) break;
    }
    const hr = hero.getBoundingClientRect();
    return Array.from(hero.querySelectorAll('img, video')).some(m => { const r = m.getBoundingClientRect(); return r.width >= hr.width * 0.5 && r.height >= Math.min(hr.height, H) * 0.4; });
  };
  const out = [];
  const walker = document.createTreeWalker(hero, NodeFilter.SHOW_ELEMENT);
  let node, n = 0;
  while ((node = walker.nextNode())) {
    if (node.closest('svg') || ['SCRIPT', 'STYLE'].includes(node.tagName)) continue;
    const own = Array.from(node.childNodes).filter(c => c.nodeType === 3).map(c => c.textContent).join('').replace(/\s+/g, ' ').trim();
    if (!own) continue;
    if (node.checkVisibility && !node.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    if (node.closest('.bs-ai-label, .bmf-ai-label')) continue;
    if (!overPhoto(node)) continue;
    const boxes = [];
    for (const child of node.childNodes) {
      if (child.nodeType !== 3 || !child.textContent.trim()) continue;
      const range = document.createRange(); range.selectNodeContents(child);
      for (const r of range.getClientRects()) {
        if (r.width < 4 || r.height < 4 || r.bottom <= 0 || r.top >= H || r.right <= 0 || r.left >= W) continue;
        boxes.push([Math.max(0, Math.floor(r.left)), Math.max(0, Math.floor(r.top)), Math.min(W, Math.ceil(r.right)), Math.min(H, Math.ceil(r.bottom))]);
      }
    }
    if (!boxes.length) continue;
    const cs = getComputedStyle(node);
    const c = rgba(cs.color) || { r: 0, g: 0, b: 0, a: 1 };
    node.setAttribute('data-bvg-ht', String(n++));
    let sel = '';
    { const parts = []; for (let e = node; e && e.nodeType === 1 && e !== document.documentElement; e = e.parentElement) { if (e === document.body) { parts.unshift('body'); break; } if (e.id && document.querySelectorAll('#' + CSS.escape(e.id)).length === 1) { parts.unshift('#' + CSS.escape(e.id)); break; } let i = 1; for (let sib = e.previousElementSibling; sib; sib = sib.previousElementSibling) if (sib.tagName === e.tagName) i++; parts.unshift(e.tagName.toLowerCase() + ':nth-of-type(' + i + ')'); } sel = parts.join('>'); }
    out.push({ text: own.slice(0, 40), path: sel, color: [c.r, c.g, c.b], size: parseFloat(cs.fontSize) || 16, bold: parseInt(cs.fontWeight, 10) >= 700, boxes });
    if (out.length >= 12) break;
  }
  if (out.length) {
    const st = document.createElement('style');
    st.id = 'bvg-hide-hero-text';
    st.textContent = '[data-bvg-ht]{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important}';
    document.head.appendChild(st);
  }
  return out;
}
"""

_HERO_TEXT_RESTORE_JS = "() => { const s = document.getElementById('bvg-hide-hero-text'); if (s) s.remove(); document.querySelectorAll('[data-bvg-ht]').forEach(e => e.removeAttribute('data-bvg-ht')); }"


def _lum(rgb: Sequence[float]) -> float:
    def f(v: float) -> float:
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])


def _ratio(a: float, b: float) -> float:
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def hero_text_contrast(viewport_png: bytes, marked: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """For each hero text element drawn over a photo: the contrast between
    its colour and the pixels behind it (text hidden in ``viewport_png``).
    ``ratio`` is the 25th percentile over the sampled pixels: three
    quarters of the text sits on at least that much contrast."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(viewport_png)).convert("RGB")
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for el in marked:
        fg = _lum(el.get("color") or (0, 0, 0))
        ratios: List[float] = []
        for box in el.get("boxes") or []:
            x0, y0, x1, y1 = (int(v) for v in box)
            x1, y1 = min(x1, im.size[0]), min(y1, im.size[1])
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            region = im.crop((x0, y0, x1, y1))
            region.thumbnail((48, 24))
            ratios.extend(_ratio(fg, _lum(px)) for px in region.getdata())
        if not ratios:
            continue
        ratios.sort()
        out.append({"text": el.get("text"), "path": el.get("path"), "ratio": round(ratios[len(ratios) // 4], 2),
                    "light_text": fg > 0.4, "size": el.get("size")})
    return out


def blank_bands(png: Optional[bytes], *, min_height: int = 600) -> List[Dict[str, int]]:
    """Runs of at least ``min_height`` rows of the full-page screenshot in
    which every row is one flat colour: a hole in the page."""
    if not png:
        return []
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(png)).convert("RGB")
    except Exception:
        return []
    w, h = im.size
    small = im.resize((max(8, w // 6), h))  # width only: a row stays a row
    sw = small.size[0]
    data = small.tobytes()
    out: List[Dict[str, int]] = []
    start = None
    for y in range(h):
        row = data[y * sw * 3:(y + 1) * sw * 3]
        flat = all(max(row[c::3]) - min(row[c::3]) <= 10 for c in range(3))
        if flat and start is None:
            start = y
        elif not flat and start is not None:
            if y - start >= min_height:
                out.append({"top": start, "height": y - start})
            start = None
    if start is not None and h - start >= min_height:
        out.append({"top": start, "height": h - start})
    return out


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
    cards.push({ name: norm(name.innerText || name.textContent).slice(0, 120), src: (img.currentSrc || img.src || '').slice(0, 300) });
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
    for i, card in enumerate(marked.get("cards") or []):
        name, src = (card.get("name"), card.get("src")) if isinstance(card, dict) else (card, "")
        try:
            png = await page.locator(f'[data-bvg-card="{i}"]').first.screenshot(type="png", timeout=5000)
            out["cards"].append({"name": name, "src": src or "", "png": _shrink(png)})
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
                            await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_MS)
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
                        if "error" not in measured:
                            try:
                                measured["design"] = await page.evaluate(_DESIGN_JS)
                            except Exception as err:
                                logger.warning(f"📐 design measurement failed ({name}): {err}")
                            try:
                                # Hero text over a photo: hide it, sample
                                # the pixels behind it, put it back.
                                marked = await page.evaluate(_HERO_TEXT_JS)
                                if marked:
                                    shot = await page.screenshot(full_page=False, type="png")
                                    measured["heroText"] = hero_text_contrast(shot, marked)
                                await page.evaluate(_HERO_TEXT_RESTORE_JS)
                            except Exception as err:
                                logger.warning(f"📐 hero text measurement failed ({name}): {err}")
                        png = await page.screenshot(full_page=(name == "mobile" or desktop_full_page), type="png")
                        if name == "mobile":
                            measured["blankBands"] = blank_bands(png)
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
    bad += [dict(c, viewport="desktop") for c in (desktop.get("heroCtas") or []) if c.get("obstructedBy")]
    checks.append(Check("hero_cta_unobstructed", not bad, "; ".join(
        f"{c.get('text')!r} covered by {c['obstructedBy'].get('by')}" + (" (desktop)" if c.get("viewport") else "") for c in bad), len(bad), bad))
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
    _seen_low = {c.get("path") for c in low}
    low += [dict(c, viewport="desktop") for c in (desktop.get("lowContrast") or []) if c.get("path") not in _seen_low]
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
    checks.extend(design_checks(mobile, desktop))
    return checks


#: Hero text over a photo fails below this contrast (25th percentile of
#: the pixels behind it). 3:1 is WCAG's floor for large text; small hero
#: text over a photo is held to the same floor, not 4.5, because a photo
#: is never one colour.
HERO_TEXT_MIN_RATIO = float(os.getenv("VISUAL_GATE_HERO_TEXT_RATIO", "3.0"))


def design_checks(mobile: Dict[str, Any], desktop: Dict[str, Any]) -> List[Check]:
    """The checks the gate audit added. Each is proven by one planted
    defect in scripts/gate_calibration.py. Skipped when the design
    measurement did not run (older callers, fake measurements in tests).

    Hard = the page is broken and the gate has a fix for it (or it is junk
    nobody should see). Soft = worth knowing and fixing where possible,
    never a reason to fail a merchant's build."""
    md, dd = mobile.get("design"), desktop.get("design") or {}
    if not isinstance(md, dict):
        return []
    out: List[Check] = []

    def both(key: str) -> List[Dict[str, Any]]:
        items = list(md.get(key) or [])
        seen = {i.get("path") for i in items}
        return items + [dict(i, viewport="desktop") for i in (dd.get(key) or []) if i.get("path") not in seen]

    def vp(i: Dict[str, Any]) -> str:
        return " (desktop)" if i.get("viewport") else ""

    faint = [dict(i, viewport=name) for name, m in (("mobile", mobile), ("desktop", desktop))
             for i in (m.get("heroText") or []) if float(i.get("ratio") or 99) < HERO_TEXT_MIN_RATIO]
    out.append(Check("hero_text_legible", not faint, "; ".join(
        f"{i.get('text')!r} {i.get('ratio')}:1 over the hero photo ({i['viewport']})" for i in faint[:4]), len(faint), faint))

    tiny = both("tinyText")
    out.append(Check("text_readable_size", not tiny, "; ".join(f"{i.get('text')!r} at {i.get('size')}px{vp(i)}" for i in tiny[:4]), len(tiny), tiny))

    small = list(md.get("smallTargets") or [])  # touch: the phone only
    out.append(Check("tap_targets", not small, "; ".join(
        f"{i.get('text') or i.get('path')!r} is {i['size'][0]}x{i['size'][1]}px" for i in small[:4]), len(small), small))

    over = both("overlaps")
    out.append(Check("no_overlapping_text", not over, "; ".join(f"{i.get('other')!r} printed over {i.get('text')!r}{vp(i)}" for i in over[:4]), len(over), over))

    squashed = both("distorted")
    out.append(Check("images_not_distorted", not squashed, "; ".join(
        f"{str(i.get('src'))[:60]} drawn {i.get('drawn')} but is {i.get('natural')}{vp(i)}" for i in squashed[:3]), len(squashed), squashed))

    empty = list(md.get("emptySections") or [])
    out.append(Check("no_empty_sections", not empty, "; ".join(f"section {i.get('heading')!r} has nothing under its heading" for i in empty[:4]), len(empty), empty))

    junk = list(md.get("junk") or [])
    out.append(Check("no_junk_text", not junk, "; ".join(f"{i.get('found')!r} in {i.get('text')!r}" for i in junk[:4]), len(junk), junk))

    # ---- soft ----
    dup = [d for d in (md.get("duplicates") or []) if len(d.get("cards") or []) >= 2]
    if dup:
        out.append(Check("no_duplicate_photos", False, "; ".join(
            f"one photo on {d['count']} cards: {', '.join(d['cards'][:4])}" for d in dup[:3]), sum(d["count"] - 1 for d in dup), dup, hard=False))
    dead = list(md.get("deadLinks") or [])
    if dead:
        out.append(Check("links_work", False, "; ".join(f"{i.get('text')!r} -> {i.get('href')} ({i.get('why')})" for i in dead[:4]), len(dead), dead, hard=False))
    bands = list(mobile.get("blankBands") or [])
    if bands:
        out.append(Check("no_blank_bands", False, "; ".join(f"{b['height']}px of nothing at {b['top']}px" for b in bands[:3]), len(bands), bands, hard=False))
    blurry = list(md.get("blurry") or [])
    if blurry:
        out.append(Check("images_sharp", False, "; ".join(
            f"{str(i.get('src'))[:60]} is {i.get('natural')}px wide, shown at {i.get('shown')}px" for i in blurry[:3]), len(blurry), blurry, hard=False))
    if md.get("h1Count") is not None and md.get("h1Count") != 1:
        out.append(Check("heading_structure", False, f"{md.get('h1Count')} H1 headings on the page (one expected)", 1, hard=False))
    fold = int(md.get("viewportHeight") or 0)
    late = []
    if fold and md.get("h1Top") is not None and md["h1Top"] >= fold:
        late.append(f"headline starts at {md['h1Top']}px")
    if fold and md.get("ctaTop") is not None and md["ctaTop"] >= fold:
        late.append(f"first button at {md['ctaTop']}px")
    if late:
        out.append(Check("primary_action_above_fold", False, "; ".join(late) + f" (first screen ends at {fold}px)", len(late), late, hard=False))
    return out


def soft_overrides() -> set:
    """Checks demoted to soft without a deploy (VISUAL_GATE_SOFT_CHECKS,
    comma-separated): the valve for a check that starts failing good
    pages in production."""
    return {x.strip() for x in os.getenv("VISUAL_GATE_SOFT_CHECKS", "").split(",") if x.strip()}


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
    '{"issues":[{"slice":<number of the slice it is in>,"type":"overlap|tilted|cutoff|unreadable|other","where":"short location, e.g. hero buttons","detail":"what is wrong","severity":"high|low"}],'
    '"design":{"score":<1-10>,"weakest":"the one thing that most hurts how this page looks, or empty"},"overall":"pass|fail"}\n'
    "Rules: report an issue ONLY when you can see it in the pixels: elements overlapping each other, text or buttons "
    "cut off by the LEFT or RIGHT edge of the phone or by their own box, rotated/tilted content, text too small or too "
    "low-contrast to read. Do not judge the photos (they are checked separately) and do not report an image that "
    "looks blank. Design taste is NOT an issue. 'overall' is 'fail' only when there is at least one high-severity "
    "issue. An empty list is the normal answer. Separately, 'design.score' is your overall impression of the page as "
    "a customer would see it, 1 (looks broken or amateur) to 10 (looks professionally designed): judge visual "
    "hierarchy, spacing and alignment, how consistent the sections are, and whether the page feels complete. The "
    "score never changes 'issues' or 'overall'."
)

CONFIRM_RUBRIC = (
    "A first reviewer reported a problem in this screenshot of a small-business website on a 390px-wide phone. The "
    "image is ONE slice cut out of a long page: content touching its top or bottom edge continues above or below and "
    "is NOT cut off. Look at the image yourself and decide whether the reported problem is clearly visible. Answer "
    'ONLY with JSON: {"confirmed":true|false,"evidence":"what you see at that place"}. Say true only when you can see '
    "the problem itself; when in doubt, say false."
)

#: How many high-severity page-review issues get a second look.
VISION_CONFIRM_LIMIT = int(os.getenv("VISUAL_GATE_VISION_CONFIRM_LIMIT", "3"))

CARD_PHOTO_RUBRIC = (
    "Each image below is the photo on ONE card (a menu item, a product or a service) of a small-business website, "
    "and comes right after that card's printed name. Judge every photo ONLY against its own card's name. First find "
    "what the name is about. For FOOD it is the named dish (for 'Set Udang Krispy' crispy prawns, for 'Set B – Ayam "
    "Gepuk Tauhu Tempe' ayam gepuk): if that dish is clearly visible the photo MATCHES, even when rice, side dishes, "
    "sambal or garnish take up much of the plate, because a set meal comes with sides. A filling cooked inside the "
    "dish (the egg in roti telur, the meat in murtabak, the filling of a kuih or a pie) does not have to be visible: "
    "judge it by how the dish looks. For a SERVICE (a haircut, hair colouring, a repair, a cleaning job) the photo "
    "MATCHES when it shows that kind of work, its tools, the items it is done on or the place it is done in: a salon "
    "interior for 'Warna Penuh' or 'Gunting Kanak-kanak', a phone being repaired for 'Screen Replacement'. A service "
    "never has to show a customer or the result. A MISMATCH is ONLY a photo where the named thing cannot be seen at "
    "all or something of a different kind takes its place: a drink pictured as a chicken dish, a burger for 'Ayam "
    "Gepuk', squid missing from 'Set Sotong Krispy', a car workshop for a hair service, a live animal, a menu board or "
    "a poster photographed as a dish. Variants of one base food that look alike count as a MATCH when the photo "
    "shows that base food: every roti (canai, planta, bom, telur, tisu, kosong), every kopi or teh, every nasi "
    "lemak or nasi goreng style; a photo cannot show margarine, the flakiness of a dough or which sugar was used. "
    "Plating, angle, garnish and how the variant is usually served are never a reason. Answer ONLY with JSON: "
    '{"mismatches":[{"card":<number>,"named_dish":"what the name is about","named_dish_visible":false,'
    '"reason":"what the photo shows instead"}]}. List only cards whose named thing is NOT visible. An empty list is '
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


def build_vision_messages(mobile_png: bytes, *, item_names: Sequence[str] = (), language: str = "ms",
                          tiles: Optional[Sequence[bytes]] = None) -> List[Dict[str, Any]]:
    tiles = list(tiles) if tiles is not None else _tiles(mobile_png)
    content: List[Dict[str, Any]] = [{"type": "text", "text": VISION_RUBRIC
        + f"\nPage language: {'Bahasa Malaysia' if language != 'en' else 'English'}. {len(tiles)} slice(s) follow, top of page first."}]
    for i, tile in enumerate(tiles, 1):
        content.append({"type": "text", "text": f"Slice {i} of {len(tiles)}:"})
        content.append({"type": "image_url", "image_url": {"url": _data_url(tile)}})
    return [{"role": "user", "content": content}]


def build_confirm_messages(tile: bytes, issue: Dict[str, Any]) -> List[Dict[str, Any]]:
    told = f"Reported problem: {issue.get('type')} at {issue.get('where')}: {issue.get('detail')}"
    return [{"role": "user", "content": [
        {"type": "text", "text": CONFIRM_RUBRIC + "\n\n" + told},
        {"type": "image_url", "image_url": {"url": _data_url(tile)}},
    ]}]


def parse_confirm(raw: Optional[str]) -> Optional[bool]:
    data = _json_object(raw)
    if data is None or "confirmed" not in data:
        return None
    val = data.get("confirmed")
    return val if isinstance(val, bool) else str(val).strip().lower() in ("true", "yes", "1")


def _data_url(img: bytes) -> str:
    mime = "image/jpeg" if img[:3] == b"\xff\xd8\xff" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(img).decode("ascii")


#: Business types whose cards are dishes, drinks or baked goods: each card
#: photo is judged against its own name. Every other business (a salon, a
#: repair shop, a laundry) has cards for services, where the photo is a
#: picture OF the business: it is judged only on belonging to it. Three live
#: rounds of salon cards dropped for "empty salon interior, no colouring
#: visible" showed the model will not apply a service rule inside the dish
#: rubric.
FOOD_BUSINESS_TYPES = ("food", "bakery", "restaurant", "cafe", "café", "catering", "drinks", "fnb", "f&b")

TRADE_PHOTO_RUBRIC = (
    "Each image below is the photo on ONE card of a small-business website, and comes right after that card's "
    "printed name. The business is described at the end. Cards here are mostly services, and a card photo is a "
    "picture of the business: its premises, its tools, its equipment, the items it works on or sells, or its work "
    "in progress. Such a photo MATCHES every card of the business, even when it does not show that exact service, a "
    "customer or the finished result (an empty salon interior matches 'Warna Penuh'; a phone on a repair bench "
    "matches 'Battery Replacement'). A MISMATCH is ONLY a photo that belongs to a different kind of business or "
    "shows something unrelated: food on a salon card, a car engine on a phone-repair card, a live animal, a poster or "
    "a menu board. Answer ONLY with JSON: "
    '{"mismatches":[{"card":<number>,"named_dish":"the service or product","named_dish_visible":false,'
    '"reason":"what unrelated thing the photo shows"}]}. List only cards whose photo is unrelated to this business. '
    "An empty list is the normal answer."
)


def is_food_business(business: Optional[Dict[str, Any]]) -> bool:
    """True unless the business is known to be something other than F&B
    (no business given = the dish rubric, as before)."""
    if not business:
        return True
    kind = str(business.get("type") or "").strip().lower()
    return (not kind) or kind in FOOD_BUSINESS_TYPES


def build_card_photo_messages(cards: Sequence[Dict[str, Any]], business: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    about = ""
    if business:
        about = (f"\n\nThe business: {business.get('name') or '-'} (type: {business.get('type') or '-'}). "
                 f"What it sells or does: {str(business.get('description') or '-')[:300]}")
    rubric = CARD_PHOTO_RUBRIC if is_food_business(business) else TRADE_PHOTO_RUBRIC
    content: List[Dict[str, Any]] = [{"type": "text", "text": rubric + about}]
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
            entry = {"item": cards[idx]["name"], "reason": str(m.get("reason") or "")[:200]}
            if cards[idx].get("src"):
                # The dropped photo, so every drop can be checked by eye.
                entry["src"] = cards[idx]["src"]
            out.append(entry)
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
            issue = {
                "type": str(i.get("type") or "other")[:20], "where": str(i.get("where") or "")[:80],
                "detail": str(i.get("detail") or "")[:200], "severity": "high" if str(i.get("severity") or "").lower() == "high" else "low",
            }
            try:
                issue["slice"] = int(str(i.get("slice")).strip())
            except (TypeError, ValueError):
                pass
            issues.append(issue)
    mism = []
    for m in data.get("photo_mismatches") or []:
        if isinstance(m, dict) and str(m.get("item") or "").strip():
            mism.append({"item": str(m["item"])[:120], "reason": str(m.get("reason") or "")[:200]})
        elif isinstance(m, str) and m.strip():
            mism.append({"item": m[:120], "reason": ""})
    out = {"issues": issues, "photo_mismatches": mism, "overall": "fail" if str(data.get("overall") or "").lower() == "fail" else "pass", "model": VISION_MODEL}
    design = data.get("design")
    if isinstance(design, dict):
        try:
            score = max(1, min(10, int(round(float(design.get("score"))))))
            out["design"] = {"score": score, "weakest": str(design.get("weakest") or "")[:160]}
        except (TypeError, ValueError):
            pass
    return out


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

#: Vision issue types that are about something being cut off. The model
#: cannot tell a page edge from a slice edge reliably, so these fail the
#: gate only when the browser measured clipping or overflow too.
_CUTOFF_TYPES = ("cutoff", "cut-off", "cut off", "clipped", "truncated")


def _is_cutoff(issue: Dict[str, Any]) -> bool:
    return _measured_kind(issue) == "cutoff"


#: What the browser measures for each kind of reviewer report. The reviewer
#: is a language model looking at a picture; the browser has the numbers. On
#: these kinds the numbers decide: a report blocks only when one of the
#: matching measured checks failed too. (Found on a real page: the reviewer
#: reported, and on a second look confirmed, an overlap and a low-contrast
#: label that were not there.) "tilted" and "other" have no measurement and
#: stay with the reviewer and its second look.
MEASURED_FOR_KIND: Dict[str, Tuple[str, ...]] = {
    "cutoff": ("no_clipped_text", "no_horizontal_overflow"),
    "overlap": ("no_overlapping_text", "hero_cta_unobstructed", "floating_button_unobstructed"),
    "unreadable": ("contrast_aa", "hero_text_legible", "text_readable_size"),
}

_KIND_IN_DETAIL = (
    ("cutoff", re.compile(r"\bcut(?:\s|-)?off\b|\btruncat", re.IGNORECASE)),
    ("overlap", re.compile(r"\boverlap", re.IGNORECASE)),
    ("unreadable", re.compile(r"\bcontrast\b|\bunreadable\b|\billegible\b|\btoo small\b", re.IGNORECASE)),
)


def _measured_kind(issue: Dict[str, Any]) -> Optional[str]:
    """The measurable kind a reviewer report belongs to, or None."""
    t = str(issue.get("type") or "").lower()
    if any(k in t for k in _CUTOFF_TYPES):
        return "cutoff"
    if "overlap" in t:
        return "overlap"
    if "unreadable" in t or "contrast" in t or "illegible" in t:
        return "unreadable"
    if t == "other":
        detail = str(issue.get("detail") or "")
        for kind, pattern in _KIND_IN_DETAIL:
            if pattern.search(detail):
                return kind
    return None


_KIND_WORD = {"cutoff": "cut-off", "overlap": "overlap", "unreadable": "unreadable text"}


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
        tiles = _tiles(mpng)
        asks = [_ask(call_vision, build_vision_messages(mpng, item_names=item_names, language=language, tiles=tiles), "page review")]
        asks.append(_ask(call_vision, build_card_photo_messages(cards, business), "card photo check") if cards else asyncio.sleep(0, result=None))
        asks.append(_ask(call_vision, build_hero_messages(hero_png, business), "hero check") if (hero_png and business) else asyncio.sleep(0, result=None))
        raw_page, raw_cards, raw_hero = await asyncio.gather(*asks)

        parsed = parse_vision(raw_page)
        if parsed is None:
            report.checks.append(Check("vision_review", True, "no verdict (model unavailable or unparseable)", 0, hard=False))
            logger.warning("👁️ Vision review produced no verdict — gating on measurements only")
        else:
            report.vision = parsed
            failed_measured = {c.name for c in report.checks if not c.ok}
            for issue in parsed["issues"]:
                kind = _measured_kind(issue)
                if issue["severity"] == "high" and kind and not failed_measured.intersection(MEASURED_FOR_KIND[kind]):
                    issue["severity"] = "low"
                    issue["note"] = f"{_KIND_WORD[kind]} not confirmed by the browser's measurements"
            # One opinion never fails a build: each high-severity issue gets
            # a second look at its own slice, and counts only if that look
            # confirms it. (No slice named, no second answer, or more than
            # VISION_CONFIRM_LIMIT issues: not confirmed.)
            candidates = [i for i in parsed["issues"] if i["severity"] == "high"]
            looks = []
            for issue in candidates[:VISION_CONFIRM_LIMIT]:
                idx = int(issue.get("slice") or 0) - 1
                looks.append(_ask(call_vision, build_confirm_messages(tiles[idx], issue), "second look")
                             if 0 <= idx < len(tiles) else asyncio.sleep(0, result=None))
            answers = await asyncio.gather(*looks) if looks else []
            for n, issue in enumerate(candidates):
                confirmed = parse_confirm(answers[n]) if n < len(answers) else None
                issue["confirmed"] = bool(confirmed)
                if not confirmed:
                    issue["severity"] = "low"
                    issue["note"] = ("second look did not confirm it" if confirmed is False
                                     else "no second look (slice not named or reviewer unavailable)")
            high = [i for i in parsed["issues"] if i["severity"] == "high"]
            unconfirmed = [i for i in parsed["issues"] if i.get("note")]
            detail = "; ".join(f"{i['type']} at {i['where']}: {i['detail']}" for i in high[:5])
            report.checks.append(Check("vision_review", not high, detail, len(high), high))
            if unconfirmed:
                logger.info(f"👁️ {len(unconfirmed)} reviewer report(s) not counted: "
                            + "; ".join(f"{i['type']} at {i['where']} ({i['note']})" for i in unconfirmed[:4]))
            if parsed.get("design"):
                logger.info(f"👁️ Design score {parsed['design']['score']}/10" + (f" — weakest: {parsed['design']['weakest']}" if parsed['design']['weakest'] else ""))
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
                    for m in mism:
                        logger.info(f"👁️ card photo mismatch: {m['item']!r} src={m.get('src', '')}")
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
    _demoted = soft_overrides()
    for c in report.checks:
        if c.name in _demoted and c.hard:
            c.hard = False
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
    return bool(sel) and len(sel) < 700 and "{" not in sel and "}" not in sel and "<" not in sel


def targeted_fix_css(report: GateReport, skip: Sequence[str] = ()) -> str:
    """Rules aimed at the exact elements the measurement flagged: a clipped
    block becomes fluid, low-contrast text takes a readable shade of its
    own colour, an in-flow element covering a hero CTA loses its absolute
    position (the floating button is handled by hero padding instead)."""
    rules: List[str] = []
    failed = {c.name: c for c in report.checks if not c.ok and c.name not in skip}
    for item in (failed.get("no_clipped_text").items if "no_clipped_text" in failed else []):
        sel = (item.get("sel") or item.get("path")) if isinstance(item, dict) else None
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
            sel, fg, bg = item.get("sel") or item.get("path"), _hex_of(item.get("fg")), _hex_of(item.get("bg"))
            if not (_safe_selector(sel) and fg and bg):
                continue
            fixed = adjust_for_contrast(fg, [bg], float(item.get("need") or 4.5)) if adjust_for_contrast else None
            if not fixed:
                from app.services.theme_patcher import contrast_ratio
                fixed = "#111111" if contrast_ratio("#111111", bg) >= contrast_ratio("#FFFFFF", bg) else "#FFFFFF"
            rules.append(f"{sel}{{color:{fixed}!important}}")
    for item in (failed.get("hero_cta_unobstructed").items if "hero_cta_unobstructed" in failed else []):
        ob = item.get("obstructedBy") if isinstance(item, dict) else None
        if isinstance(ob, dict) and not ob.get("fixed") and _safe_selector(ob.get("bySel") or ob.get("by")):
            rules.append(f"{ob.get('bySel') or ob['by']}{{position:static!important;transform:none!important}}")
    def _paths(name: str) -> List[Dict[str, Any]]:
        return [i for i in (failed[name].items if name in failed else []) if isinstance(i, dict) and _safe_selector(i.get("path"))]

    for item in _paths("text_readable_size"):
        rules.append(f"{item['path']}{{font-size:12.5px!important;line-height:1.45!important}}")
    for item in _paths("tap_targets"):
        rules.append(
            f"{item['path']}{{min-height:40px!important;min-width:40px!important;display:inline-flex!important;"
            "align-items:center!important;justify-content:center!important;padding:.5rem .85rem!important;"
            "font-size:max(.82rem,13px)!important;line-height:1.2!important;box-sizing:border-box!important}"
        )
    for item in _paths("no_overlapping_text"):
        rules.append(f"{item['path']}{{position:static!important;margin-top:.4em!important;transform:none!important;float:none!important}}")
    for item in _paths("images_not_distorted"):
        rules.append(f"{item['path']}{{object-fit:cover!important}}")
    for item in _paths("no_empty_sections"):
        rules.append(f"{item['path']}{{display:none!important}}")
    for item in _paths("hero_text_legible"):
        # A hero that is not the composer's (no scrim to darken): the text
        # gets its own backing, light or dark to suit its colour.
        if item.get("light_text", True):
            rules.append(f"{item['path']}{{background:rgba(0,0,0,.68)!important;color:#fff!important;-webkit-box-decoration-break:clone;"
                         "box-decoration-break:clone;padding:.1em .35em!important;border-radius:.2em}}")
        else:
            rules.append(f"{item['path']}{{background:rgba(255,255,255,.86)!important;color:#111!important;-webkit-box-decoration-break:clone;"
                         "box-decoration-break:clone;padding:.1em .35em!important;border-radius:.2em}}")
    if not rules:
        return ""
    return '<style id="binaapp-visual-gate-targeted">\n' + "\n".join(rules) + "\n</style>\n"


_SCRIM_CSS = """
<style id="binaapp-visual-gate-scrim">
.bs-hero:not(.bs-hero-solid) .bs-hero-scrim{background:linear-gradient(180deg,rgba(0,0,0,.58) 0%,rgba(0,0,0,.66) 45%,rgba(0,0,0,.86) 100%)!important}
</style>
"""


def darken_hero_scrim(html: str) -> Tuple[str, int]:
    """The composed hero's scrim, made dark enough for white text over any
    photo (and added when the hero has a photo but no scrim)."""
    if "bs-hero-media" not in html or "binaapp-visual-gate-scrim" in html:
        return html, 0
    out = html
    m = re.search(r'<section[^>]*class="[^"]*\bbs-hero\b[^"]*"[^>]*>.*?</section>', out, re.S)
    if m and "bs-hero-scrim" not in m.group(0):
        hero = re.sub(r'(<div class="bs-hero-media">.*?</div>)', r'\1<div class="bs-hero-scrim"></div>', m.group(0), count=1, flags=re.S)
        out = out[:m.start()] + hero + out[m.end():]
    out = out.replace("</head>", _SCRIM_CSS + "</head>", 1) if "</head>" in out else _SCRIM_CSS + out
    return out, 1


def drop_repeated_card_photos(html: str, duplicates: Sequence[Dict[str, Any]]) -> Tuple[str, int]:
    """One photo on several menu cards: the first card keeps it, the rest
    become text cards (a photo that claims to be three dishes is none)."""
    names: List[str] = []
    for d in duplicates or []:
        names.extend((d.get("cards") or [])[1:])
    if not names:
        return html, 0
    return drop_item_photos(html, names)


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
    _composed_hero_scrimmed = False
    if "hero_text_legible" in failed and "photo_free_hero" not in fixes:
        out, n = darken_hero_scrim(out)
        if n:
            fixes.append("darker_hero_scrim")
            _composed_hero_scrimmed = True
    if "no_duplicate_photos" in failed:
        out, n = drop_repeated_card_photos(out, failed["no_duplicate_photos"].items)
        if n:
            fixes.append(f"dropped_repeated_photos({n})")
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
    # The hero's own fix (darker scrim, or no photo at all) replaces the
    # per-element backing.
    _hero_handled = _composed_hero_scrimmed or "photo_free_hero" in fixes
    targeted = targeted_fix_css(report, skip=("hero_text_legible",) if _hero_handled else ())
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


async def gate_and_repair(
    html: str,
    *,
    path: str,
    expect_map: bool,
    expect_whatsapp: bool,
    item_names: Sequence[str] = (),
    language: str = "ms",
    call_vision: Optional[Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]]] = None,
    business: Optional[Dict[str, Any]] = None,
    job_id: str = "",
) -> Tuple[str, GateReport]:
    """The gate for pages written outside the create flow (a regeneration,
    a make-good rebuild): gate → auto-fix → re-gate, and the better page is
    returned. Never blocks and never raises: these paths replace a page the
    merchant already has, so a page that still fails is shipped, logged
    (``VISUAL_GATE_FAIL path=...``) and left to the caller to alert on."""
    mode = gate_mode()
    if mode == "off":
        return html, GateReport(mode=mode, error="gate off")
    kw = dict(expect_map=expect_map, expect_whatsapp=expect_whatsapp, item_names=item_names, language=language,
              call_vision=call_vision, business=business)
    try:
        report = await run_gate(html, attempt=1, **kw)
        if not report.rendered:
            logger.warning(f"🧠 VISUAL_GATE_SKIPPED path={path} job={job_id[:8]} {report.error}")
            return html, report
        if all(c.ok for c in report.checks):
            return html, report
        fixed, fixes = auto_fix(html, report)
        if fixes:
            report2 = await run_gate(fixed, attempt=2, **kw)
            report2.fixes = fixes
            if report2.rendered and len(report2.failed) <= len(report.failed):
                html, report = fixed, report2
        if not report.passed:
            logger.error(f"🚨 VISUAL_GATE_FAIL path={path} job={job_id[:8]} shipped=yes {report.summary()} fixes={report.fixes}")
        else:
            logger.info(f"👁️ Visual gate ({path}): {report.summary()} fixes={report.fixes}")
        return html, report
    except Exception as err:  # the gate must never take a rebuild down
        logger.error(f"🚨 VISUAL_GATE_ERROR path={path} job={job_id[:8]}: {err}")
        return html, GateReport(mode=mode, error=str(err))


# ---------------------------------------------------------------------------
# Watch: pages the merchant changes themselves (theme, editor)
# ---------------------------------------------------------------------------

#: One watch at a time (each launches Chromium), and at most one per site
#: every WATCH_MIN_INTERVAL_SECONDS: an editor that saves on every change
#: must not queue a browser per keystroke.
WATCH_MIN_INTERVAL_SECONDS = float(os.getenv("VISUAL_GATE_WATCH_INTERVAL_SECONDS", "60"))
_watch_lock: Optional[asyncio.Lock] = None
_watch_last: Dict[str, float] = {}
_watch_tasks: set = set()


async def watch_page(html: str, *, path: str, website_id: str, business_name: str = "", user_id: str = "",
                     expect_map: bool = False, expect_whatsapp: bool = False) -> Optional[GateReport]:
    """Measure a page the merchant just saved (a theme change, an editor
    save) and tell the operator when it is broken. Measured checks only: no
    reviewer call. The page is NEVER changed and the save never waits: the
    merchant chose it, and a rewrite behind their back could overwrite a
    newer save. Returns the report, or None when skipped."""
    global _watch_lock
    if gate_mode() == "off" or not html or not website_id:
        return None
    import time as _time
    now = _time.monotonic()
    if now - _watch_last.get(website_id, -1e9) < WATCH_MIN_INTERVAL_SECONDS:
        return None
    _watch_last[website_id] = now
    if len(_watch_last) > 2000:
        for key in sorted(_watch_last, key=_watch_last.get)[:1000]:
            _watch_last.pop(key, None)
    if _watch_lock is None:
        _watch_lock = asyncio.Lock()
    try:
        async with _watch_lock:
            report = await run_gate(html, expect_map=expect_map, expect_whatsapp=expect_whatsapp, call_vision=None)
        if not report.rendered:
            logger.info(f"👁️ VISUAL_GATE_WATCH path={path} site={website_id[:8]} skipped: {report.error}")
            return report
        soft = [c.name for c in report.checks if not c.ok and not c.hard]
        if report.passed:
            logger.info(f"👁️ VISUAL_GATE_WATCH path={path} site={website_id[:8]} pass" + (f" (soft: {', '.join(soft)})" if soft else ""))
            return report
        logger.error(f"🚨 VISUAL_GATE_WATCH path={path} site={website_id[:8]} {report.summary()}")
        try:
            from app.services.ops_alerts import alert as _ops_alert
            _ops_alert(
                "gate_watch", business_name=business_name, user_id=user_id, website_id=website_id,
                reason=f"{report.summary()} — " + "; ".join(f"{c.name}: {c.detail}" for c in report.failed)[:600],
                details={"Changed by": path},
            )
        except Exception as alert_err:
            logger.warning(f"📣 watch alert skipped: {alert_err}")
        return report
    except Exception as err:
        logger.warning(f"👁️ VISUAL_GATE_WATCH path={path} site={website_id[:8]} error: {err}")
        return None


def watch_in_background(html: str, **kw: Any) -> bool:
    """Start ``watch_page`` without waiting for it. False outside an event
    loop (nothing started)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    task = loop.create_task(watch_page(html, **kw))
    _watch_tasks.add(task)
    task.add_done_callback(_watch_tasks.discard)
    return True


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
