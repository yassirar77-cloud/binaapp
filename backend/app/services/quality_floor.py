"""
Quality floor (§8) — the invisible baseline every generated page gets,
applied deterministically after generation.

The prompt asks for all of this; the model forgets some of it every time.
So the floor is enforced here, idempotently, on the final HTML:

- ``<html lang>`` matches the site language
- a viewport meta tag exists
- ``prefers-reduced-motion`` is respected (all animation/transition off)
- keyboard focus stays visible (``:focus-visible`` outline), and Tailwind's
  ``outline-none`` never ships without a focus-visible replacement
- every image below the fold is lazy-loaded and async-decoded; the first
  (hero) image is eager and high-priority
- images get ``width``/``height`` when the URL carries Cloudinary
  ``w_``/``h_`` transforms or the tag has an aspect-ratio class
- the Tailwind Play CDN is replaced with the precompiled stylesheet when
  ``tailwind_precompile`` can produce one (optional, needs node + the
  Tailwind CLI on PATH); otherwise the CDN stays and a warning is recorded

Pure string transforms; no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_REDUCED_MOTION_CSS = (
    "@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation-duration:.01ms!important;"
    "animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}"
)
_FOCUS_CSS = ":focus-visible{outline:2px solid var(--accent-strong,currentColor);outline-offset:2px}"
_IMG_MAX_CSS = "img,video,iframe{max-width:100%}img{height:auto}"
_STYLE_ID = "binaapp-quality-floor"

_HTML_TAG_RE = re.compile(r"<html\b([^>]*)>", re.IGNORECASE)
_LANG_ATTR_RE = re.compile(r"\slang=[\"'][^\"']*[\"']", re.IGNORECASE)
_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
_VIEWPORT_RE = re.compile(r"<meta\b[^>]*name=[\"']viewport[\"']", re.IGNORECASE)
_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_CLOUDINARY_W_RE = re.compile(r"[/,]w_(\d+)")
_CLOUDINARY_H_RE = re.compile(r"[/,]h_(\d+)")
_ASPECT_RE = re.compile(r"aspect-\[(\d+)/(\d+)\]|aspect-(square|video)")
_TAILWIND_CDN_RE = re.compile(r"<script\b[^>]*cdn\.tailwindcss\.com[^>]*>\s*</script>", re.IGNORECASE)


@dataclass
class QualityFloorReport:
    applied: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict:
        return {"applied": list(self.applied), "warnings": list(self.warnings)}


def _set_lang(html: str, language: str, report: QualityFloorReport) -> str:
    lang = "en" if str(language or "").lower().startswith("en") else "ms"
    m = _HTML_TAG_RE.search(html)
    if not m:
        return html
    attrs = m.group(1)
    if _LANG_ATTR_RE.search(attrs):
        current = _LANG_ATTR_RE.search(attrs).group(0)
        if f'"{lang}"' not in current and f"'{lang}'" not in current:
            attrs = _LANG_ATTR_RE.sub(f' lang="{lang}"', attrs)
            report.applied.append(f"html lang set to {lang}")
    else:
        attrs = attrs + f' lang="{lang}"'
        report.applied.append(f"html lang added ({lang})")
    return html[: m.start()] + f"<html{attrs}>" + html[m.end():]


def _ensure_head_bits(html: str, report: QualityFloorReport) -> str:
    inject: List[str] = []
    if not _VIEWPORT_RE.search(html):
        inject.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
        report.applied.append("viewport meta added")
    css_bits: List[str] = []
    if "prefers-reduced-motion" not in html:
        css_bits.append(_REDUCED_MOTION_CSS)
        report.applied.append("prefers-reduced-motion rule added")
    if ":focus-visible" not in html:
        css_bits.append(_FOCUS_CSS)
        report.applied.append("focus-visible outline added")
    if "max-width:100%" not in html.replace(" ", "") and "max-w-full" not in html:
        css_bits.append(_IMG_MAX_CSS)
        report.applied.append("media max-width rule added")
    if css_bits and _STYLE_ID not in html:
        inject.append(f'<style id="{_STYLE_ID}">{"".join(css_bits)}</style>')
    if not inject:
        return html
    m = _HEAD_CLOSE_RE.search(html)
    if not m:
        return html
    return html[: m.start()] + "\n".join(inject) + "\n" + html[m.start():]


def _image_dimensions(tag: str) -> Optional[Tuple[int, int]]:
    src = re.search(r"\bsrc=[\"']([^\"']+)[\"']", tag, re.IGNORECASE)
    if src:
        w, h = _CLOUDINARY_W_RE.search(src.group(1)), _CLOUDINARY_H_RE.search(src.group(1))
        if w and h:
            return int(w.group(1)), int(h.group(1))
    m = _ASPECT_RE.search(tag)
    if m:
        if m.group(3) == "square":
            return 800, 800
        if m.group(3) == "video":
            return 1280, 720
        return int(m.group(1)) * 200, int(m.group(2)) * 200
    return None


def _fix_images(html: str, report: QualityFloorReport) -> str:
    index = {"i": 0, "lazy": 0, "dims": 0}

    def _sub(m: "re.Match") -> str:
        tag = m.group(0)
        i = index["i"]
        index["i"] += 1
        new = tag
        if i == 0:
            if "loading=" not in new.lower():
                new = new[:-1] + ' loading="eager" fetchpriority="high">'
        else:
            if "loading=" not in new.lower():
                new = new[:-1] + ' loading="lazy">'
                index["lazy"] += 1
            if "decoding=" not in new.lower():
                new = new[:-1] + ' decoding="async">'
        if "width=" not in new.lower() and "height=" not in new.lower():
            dims = _image_dimensions(new)
            if dims:
                new = new[:-1] + f' width="{dims[0]}" height="{dims[1]}">'
                index["dims"] += 1
        return new

    out = _IMG_RE.sub(_sub, html)
    if index["lazy"]:
        report.applied.append(f"{index['lazy']} image(s) set to lazy-load")
    if index["dims"]:
        report.applied.append(f"{index['dims']} image(s) given width/height")
    return out


def apply_quality_floor(
    html: str,
    *,
    language: str = "ms",
    precompiled_css: Optional[str] = None,
) -> Tuple[str, QualityFloorReport]:
    """Apply the floor. ``precompiled_css`` (from tailwind_precompile)
    replaces the Play CDN script when supplied."""
    report = QualityFloorReport()
    out = html or ""
    if not out:
        return out, report
    out = _set_lang(out, language, report)
    out = _ensure_head_bits(out, report)
    out = _fix_images(out, report)
    if precompiled_css:
        if _TAILWIND_CDN_RE.search(out):
            out = _TAILWIND_CDN_RE.sub(f'<style id="binaapp-tailwind">{precompiled_css}</style>', out, count=1)
            out = _TAILWIND_CDN_RE.sub("", out)
            report.applied.append("Tailwind Play CDN replaced with precompiled CSS")
    elif _TAILWIND_CDN_RE.search(out):
        report.warnings.append("Tailwind Play CDN still in use (no precompiled CSS available)")
    return out, report
