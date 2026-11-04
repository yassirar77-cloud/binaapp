"""A light ("Cerah") page keeps a light hero.

On the Cerah theme the model painted a dark gradient scrim AND a black
panel over the hero photo, so the page opened on a muddy block that
contradicted the theme the merchant picked. On a light page the scrim is
capped (no darker than 0.45 at its densest) and a near-black panel behind
the hero copy becomes a brand-coloured one — when white text reads on the
brand primary at WCAG AA — or a translucent white one with dark text.

Only the hero <section> is touched. Pure string transform; no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.services.branding import _HEX_RE, _luminance

MAX_SCRIM = 45  # percent

_HERO_OPEN_RE = re.compile(r"<section\b[^>]*(?:\bid\s*=\s*[\"'](?:home|hero|laman-utama)[\"']|data-binaapp-hero-video)[^>]*>", re.IGNORECASE)
_FIRST_SECTION_RE = re.compile(r"<section\b[^>]*>", re.IGNORECASE)
_SECTION_ANY_RE = re.compile(r"<(/?)section\b[^>]*>", re.IGNORECASE)
_DARK_OPACITY_RE = re.compile(r"(?<![\w-])((?:from|via|to|bg)-(?:black|neutral-950|neutral-900|zinc-950|zinc-900|gray-950|gray-900|stone-950|stone-900|slate-950|slate-900))/(\d{1,3})(?![\w-])")
_DARK_GRADIENT_BARE_RE = re.compile(r"(?<![\w-])((?:from|via|to)-(?:black|neutral-950|neutral-900|zinc-950|zinc-900|gray-950|gray-900|stone-950|stone-900|slate-950|slate-900))(?![\w/-])")
_RGBA_BLACK_RE = re.compile(r"rgba\(\s*(?:0|[0-3]?\d)\s*,\s*(?:0|[0-3]?\d)\s*,\s*(?:0|[0-3]?\d)\s*,\s*(0?\.\d+|1(?:\.0+)?)\s*\)", re.IGNORECASE)
_PANEL_RE = re.compile(r"<(div|article|aside)\b([^>]*\bclass\s*=\s*([\"'])((?:(?!\3).)*?)\3[^>]*)>", re.IGNORECASE)
_SOLID_DARK_CLASS_RE = re.compile(r"(?<![\w-])bg-(?:black|neutral-950|neutral-900|zinc-950|zinc-900|gray-950|gray-900|stone-950|stone-900|slate-950|slate-900|\[#(?:[0-2][0-9a-fA-F]){3}\])(?![\w/-])")
_LIGHT_TEXT_RE = re.compile(r"(?<![\w-])text-(?:white|neutral-50|neutral-100|gray-50|gray-100|zinc-50|zinc-100|stone-50|stone-100|slate-50|slate-100)(?:/\d{1,3})?(?![\w-])")


@dataclass
class ScrimReport:
    scrims_capped: int = 0
    panels_recoloured: int = 0
    panel_style: str = ""
    notes: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.scrims_capped or self.panels_recoloured)

    def as_dict(self):
        return {"scrims_capped": self.scrims_capped, "panels_recoloured": self.panels_recoloured, "panel_style": self.panel_style}


def contrast_ratio(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _hero_span(html: str) -> Optional[Tuple[int, int]]:
    m = _HERO_OPEN_RE.search(html) or _FIRST_SECTION_RE.search(html)
    if not m:
        return None
    depth = 0
    for mm in _SECTION_ANY_RE.finditer(html, m.start()):
        depth += -1 if mm.group(1) else 1
        if depth == 0:
            return m.start(), mm.end()
    return m.start(), len(html)


def panel_classes_for(primary: Optional[str]) -> Tuple[str, bool]:
    """(classes for the replacement panel, keep_light_text). The brand
    primary when white text passes AA on it; otherwise white at 90% with
    dark text."""
    p = (primary or "").strip()
    if _HEX_RE.match(p) and contrast_ratio(p, "#ffffff") >= 4.5:
        return f"bg-[{p}]/90 backdrop-blur-sm", True
    return "bg-white/90 backdrop-blur-sm", False


def soften_light_hero(html: str, primary: Optional[str] = None) -> Tuple[str, ScrimReport]:
    report = ScrimReport()
    span = _hero_span(html or "")
    if not span:
        return html, report
    start, end = span
    hero = html[start:end]
    original = hero

    def _cap(m: "re.Match") -> str:
        if int(m.group(2)) <= MAX_SCRIM:
            return m.group(0)
        report.scrims_capped += 1
        return f"{m.group(1)}/{MAX_SCRIM}"

    hero = _DARK_OPACITY_RE.sub(_cap, hero)

    def _bare(m: "re.Match") -> str:
        report.scrims_capped += 1
        return f"{m.group(1)}/{MAX_SCRIM}"

    hero = _DARK_GRADIENT_BARE_RE.sub(_bare, hero)

    def _rgba(m: "re.Match") -> str:
        if float(m.group(1)) <= MAX_SCRIM / 100:
            return m.group(0)
        report.scrims_capped += 1
        return m.group(0)[: m.start(1) - m.start()] + f"{MAX_SCRIM / 100:.2f}" + m.group(0)[m.end(1) - m.start():]

    hero = _RGBA_BLACK_RE.sub(_rgba, hero)

    panel_classes, keep_light_text = panel_classes_for(primary)
    report.panel_style = panel_classes

    def _panel(m: "re.Match") -> str:
        classes = m.group(4)
        if not _SOLID_DARK_CLASS_RE.search(classes):
            return m.group(0)
        new_classes = _SOLID_DARK_CLASS_RE.sub(panel_classes, classes, count=1)
        new_classes = re.sub(r"\s{2,}", " ", new_classes).strip()
        report.panels_recoloured += 1
        attrs = m.group(2).replace(m.group(0)[m.start(2) - m.start():m.end(2) - m.start()], "", 0)
        attrs = m.group(2)
        attrs = attrs.replace(f"{m.group(3)}{classes}{m.group(3)}", f"{m.group(3)}{new_classes}{m.group(3)}", 1)
        return f"<{m.group(1)}{attrs}>"

    hero = _PANEL_RE.sub(_panel, hero)
    if report.panels_recoloured and not keep_light_text:
        # Dark text on the white panel: flip light text utilities in the hero.
        hero, n = _LIGHT_TEXT_RE.subn("text-neutral-900", hero)
        if n:
            report.notes.append(f"{n} light text class(es) flipped to dark for the white panel")
    if hero == original:
        return html, report
    return html[:start] + hero + html[end:], report
