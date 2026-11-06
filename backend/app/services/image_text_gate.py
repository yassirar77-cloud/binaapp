"""The no-baked-in-text gate for about / gallery images.

agp.binaapp.my shipped an about-section image with garbled text rendered
into it ("Anam Gepuk / A Taste of the Taste in Ayum Gepok", alt "Set A –
Ayam Gepuk"). Generated item images were checked when they were made, but
the about and gallery sections are filled from the same pool AND from later
passes (stock fallbacks, food-image post-pass) that never went through the
check — and a check that came back "unchecked" let it through anyway.

``gate_section_images`` runs every non-upload <img> in the about / gallery
sections through the same text check as the menu images (``has_text``):
cached verdicts from the generation gate are reused, unchecked images are
checked here, and an image with text is swapped for a verified clean one
from the same build — or removed when there is none. Merchant uploads are
never touched (a photo of their own signboard is meant to have text).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

from loguru import logger

from app.services.image_vision_check import VisionVerdict

_SECTION_OPEN_RE = re.compile(r"<section\b[^>]*>", re.IGNORECASE)
_SECTION_ANY_RE = re.compile(r"<(/?)section\b[^>]*>", re.IGNORECASE)
_GATED_SECTION_RE = re.compile(
    r"""\b(?:id|class)\s*=\s*["'][^"']*\b(about|tentang|kisah|story|cerita|gallery|galeri|galery|kami)\b""",
    re.IGNORECASE,
)
_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_RE = re.compile(r"""\bsrc\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)
_ALT_RE = re.compile(r"""\balt\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)

#: Vision calls this pass may spend per page.
MAX_CHECKS = 6

CheckFn = Callable[[str], Awaitable[VisionVerdict]]


@dataclass
class GateReport:
    checked: List[str] = field(default_factory=list)
    replaced: List[Tuple[str, str]] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    unchecked: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.replaced or self.removed)


def _norm(url: str) -> str:
    """Compare URLs without Cloudinary transforms or query strings."""
    u = str(url or "").split("?", 1)[0]
    return re.sub(r"/upload/(?:[^/]*[,_][^/]*/)+", "/upload/", u)


def gated_section_spans(html: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for m in _SECTION_OPEN_RE.finditer(html):
        if not _GATED_SECTION_RE.search(m.group(0)):
            continue
        depth, end = 0, len(html)
        for t in _SECTION_ANY_RE.finditer(html, m.start()):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                end = t.end()
                break
        if not any(s <= m.start() < e for s, e in spans):
            spans.append((m.start(), end))
    return spans


async def gate_section_images(
    html: str,
    *,
    check: CheckFn,
    verdicts: Optional[Dict[str, VisionVerdict]] = None,
    uploads: Iterable[str] = (),
    clean_pool: Iterable[str] = (),
    alt_fallback: str = "",
    max_checks: int = MAX_CHECKS,
) -> Tuple[str, GateReport]:
    """Swap / remove about & gallery images that have text baked in."""
    report = GateReport()
    if not html:
        return html, report
    verdicts = dict(verdicts or {})
    by_norm = {_norm(u): v for u, v in verdicts.items()}
    upload_keys = {_norm(u) for u in uploads if u}
    calls = 0

    async def _verdict(url: str) -> Optional[VisionVerdict]:
        nonlocal calls
        v = by_norm.get(_norm(url))
        if v is not None and v.checked:
            return v
        if calls >= max_checks:
            return None
        calls += 1
        try:
            v = await check(url)
        except Exception as err:  # never blocks the page
            logger.warning(f"👁️ About/gallery text check failed for {url[:80]}: {err}")
            return None
        by_norm[_norm(url)] = v
        report.checked.append(url)
        return v

    async def _is_clean(url: str) -> bool:
        if _norm(url) in upload_keys:
            return True
        v = await _verdict(url)
        return v is not None and v.checked and not v.has_text

    pool = [u for u in clean_pool if u]
    out: List[str] = []
    pos = 0
    for start, end in gated_section_spans(html):
        section = html[start:end]
        used = {_norm(_SRC_RE.search(t).group(2)) for t in _IMG_RE.findall(section) if _SRC_RE.search(t)}
        new_parts: List[str] = []
        spos = 0
        for m in _IMG_RE.finditer(section):
            tag = m.group(0)
            src_m = _SRC_RE.search(tag)
            src = src_m.group(2).strip() if src_m else ""
            if not src.startswith(("http://", "https://")) or _norm(src) in upload_keys:
                continue
            v = await _verdict(src)
            if v is None or not v.checked:
                report.unchecked.append(src)
                continue
            if not v.has_text:
                continue
            replacement = None
            for cand in pool:
                if _norm(cand) in used or _norm(cand) == _norm(src):
                    continue
                if await _is_clean(cand):
                    replacement = cand
                    break
            new_parts.append(section[spos:m.start()])
            if replacement:
                used.add(_norm(replacement))
                new_tag = tag[:src_m.start(2)] + replacement + tag[src_m.end(2):]
                alt_m = _ALT_RE.search(new_tag)
                if alt_m and alt_fallback:
                    new_tag = new_tag[:alt_m.start(2)] + alt_fallback + new_tag[alt_m.end(2):]
                new_parts.append(new_tag)
                report.replaced.append((src, replacement))
                logger.warning(f"👁️ About/gallery image had baked-in text ({v.reason or 'text'}) — replaced with a clean image")
            else:
                report.removed.append(src)
                logger.warning(f"👁️ About/gallery image had baked-in text ({v.reason or 'text'}) — removed, no clean image to swap in")
            spos = m.end()
        new_parts.append(section[spos:])
        out.append(html[pos:start])
        out.append("".join(new_parts))
        pos = end
    out.append(html[pos:])
    return "".join(out), report
