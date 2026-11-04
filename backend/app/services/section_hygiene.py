"""Section hygiene — nothing empty ships.

After the guards have done their work (the fact guard strips a section that
asserts what the merchant never said; the menu reconciler removes invented
cards) a page can be left with a <section> holding only comments and
whitespace, or a pair of decorative wave dividers with nothing between
them. ayamgepukpaglima shipped both: a "SIGNATURE BAND" reduced to two
orphan dividers, and an empty "SEAFOOD KRISPY" section.

Pure string transforms; no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

_SECTION_ANY_RE = re.compile(r"<(/?)(section|article)\b[^>]*>", re.IGNORECASE)
_SECTION_OPEN_RE = re.compile(r"<(section|article)\b[^>]*>", re.IGNORECASE)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_KEEP_TAGS_RE = re.compile(r"<(img|iframe|video|audio|form|input|textarea|select|button|canvas|picture|source|svg)\b", re.IGNORECASE)
_SLOT_RE = re.compile(r"\bid\s*=\s*[\"'][\w-]*slot[\w-]*[\"']", re.IGNORECASE)
_HERO_RE = re.compile(r"\bid\s*=\s*[\"'](home|hero|laman-utama)[\"']|data-binaapp-hero-video", re.IGNORECASE)
#: A decorative band/divider: a self-contained element whose class names a
#: divider/wave/separator and which carries no text.
_DIVIDER_RE = re.compile(
    r"<(div|span|hr|svg)\b[^>]*class\s*=\s*[\"'][^\"']*\b(?:[\w-]*(?:divider|wave|wavy|separator|zigzag|slant|curve)[\w-]*)\b[^\"']*[\"'][^>]*>(?:(?!</\1>).)*?</\1>|<hr\b[^>]*class\s*=\s*[\"'][^\"']*(?:divider|wave|separator)[^\"']*[\"'][^>]*/?>",
    re.IGNORECASE | re.DOTALL,
)
_ID_RE = re.compile(r"\bid\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_NAV_LINK_RE = re.compile(r"<a\b[^>]*href=[\"']#([^\"']+)[\"'][^>]*>.*?</a>\s*", re.IGNORECASE | re.DOTALL)


@dataclass
class HygieneReport:
    removed_sections: List[str] = field(default_factory=list)
    removed_dividers: int = 0
    removed_nav_links: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.removed_sections or self.removed_dividers or self.removed_nav_links)

    def as_dict(self):
        return {"removed_sections": list(self.removed_sections), "removed_dividers": self.removed_dividers, "removed_nav_links": self.removed_nav_links}


def _span(html: str, open_match: "re.Match") -> Tuple[int, int]:
    depth = 0
    for m in _SECTION_ANY_RE.finditer(html, open_match.start()):
        if m.group(1):
            depth -= 1
            if depth == 0:
                return open_match.start(), m.end()
        else:
            depth += 1
    return open_match.start(), len(html)


def is_empty_block(block: str) -> bool:
    """True when the element holds nothing a visitor can see or use: no
    text once comments and tags are gone, and no media, form, slot or svg."""
    inner = _COMMENT_RE.sub("", block)
    if _KEEP_TAGS_RE.search(inner) or _SLOT_RE.search(inner):
        return False
    text = _TAG_RE.sub("", inner)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    return not text.strip()


def remove_empty_sections(html: str, report: HygieneReport) -> str:
    """Drop every <section>/<article> that is empty (the hero is never
    judged: an image-less hero is the layout guard's business)."""
    out = html
    while True:
        removed_any = False
        for m in list(_SECTION_OPEN_RE.finditer(out)):
            start, end = _span(out, m)
            block = out[start:end]
            if _HERO_RE.search(m.group(0)) or not is_empty_block(block):
                continue
            sid = (_ID_RE.search(m.group(0)) or [None, ""])[1] if _ID_RE.search(m.group(0)) else ""
            report.removed_sections.append(sid or f"section@{start}")
            out = out[:start] + out[end:]
            if sid:
                dropped = 0

                def _drop(mm: "re.Match") -> str:
                    nonlocal dropped
                    if mm.group(1) == sid:
                        dropped += 1
                        return ""
                    return mm.group(0)

                out = _NAV_LINK_RE.sub(_drop, out)
                report.removed_nav_links += dropped
            removed_any = True
            break
        if not removed_any:
            return out


def remove_orphan_dividers(html: str, report: HygieneReport) -> str:
    """A divider only earns its place against content. Two dividers with
    nothing but whitespace/comments between them (the band they framed is
    gone) are removed; so is a divider followed by nothing before </body>,
    </main> or a closing section."""
    out = html
    while True:
        changed = False
        divs = list(_DIVIDER_RE.finditer(out))
        for i, d in enumerate(divs):
            if not is_empty_block(d.group(0)):
                continue
            # (a) the next divider is the only thing after this one
            if i + 1 < len(divs):
                between = out[d.end():divs[i + 1].start()]
                if is_empty_block(between) and not _TAG_RE.search(_COMMENT_RE.sub("", between)):
                    out = out[:d.start()] + out[divs[i + 1].end():]
                    report.removed_dividers += 2
                    changed = True
                    break
            # (b) nothing visible follows before the container closes
            tail = out[d.end():]
            m = re.match(r"(?:\s|<!--.*?-->)*(</(?:body|main|section|article|div)\b|$)", tail, re.DOTALL | re.IGNORECASE)
            if m:
                out = out[:d.start()] + out[d.end():]
                report.removed_dividers += 1
                changed = True
                break
        if not changed:
            return out


def clean_sections(html: str) -> Tuple[str, HygieneReport]:
    """Apply both passes until stable. Returns (html, report)."""
    report = HygieneReport()
    if not html:
        return html, report
    out = html
    for _ in range(4):
        before = out
        out = remove_empty_sections(out, report)
        out = remove_orphan_dividers(out, report)
        if out == before:
            break
    return out, report
