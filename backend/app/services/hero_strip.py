"""A strip pinned to the bottom of the hero must not cover the hero's CTA.

agp.binaapp.my (regeneration after #825): the plan's signature element was
a spice-level strip "pinned to the bottom of the hero photo" — the model
wrote it as ``absolute bottom-0 left-0 right-0 z-20`` inside a
``flex items-end`` hero whose headline and "Pesan di WhatsApp" /
"Lihat menu" buttons also sit at the bottom. On a phone the chips wrap to
three rows and the strip covered both buttons.

``dock_hero_bottom_strip`` takes such a strip out of absolute positioning
and puts it in the hero's flow, under the copy: the hero becomes a column
(``flex-col justify-end``) and the strip a full-width last row, still on
the photo. Pure string transform on the hero section; idempotent.
"""

from __future__ import annotations

import re
from typing import Tuple

_HERO_OPEN_RE = re.compile(r"<section\b[^>]*\bid\s*=\s*[\"']hero[\"'][^>]*>", re.IGNORECASE)
_DIV_OPEN_RE = re.compile(r"<div\b[^>]*\bclass\s*=\s*([\"'])([^\"']*)\1[^>]*>", re.IGNORECASE)
_CLASS_RE = re.compile(r"(\bclass\s*=\s*)([\"'])([^\"']*)\2", re.IGNORECASE)
_PIN_TOKENS = {"absolute", "bottom-0", "left-0", "right-0", "inset-x-0"}


def _section_end(html: str, start: int) -> int:
    depth = 0
    for m in re.finditer(r"<(/?)section\b[^>]*>", html[start:], re.IGNORECASE):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return start + m.end()
    return len(html)


def _div_inner_text(html: str, open_end: int) -> str:
    depth, pos = 1, open_end
    for m in re.finditer(r"<(/?)div\b[^>]*>", html[open_end:], re.IGNORECASE):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            pos = open_end + m.start()
            break
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html[open_end:pos])).strip()


def _is_bottom_strip(classes: str) -> bool:
    toks = set(classes.split())
    return "absolute" in toks and "bottom-0" in toks and (("left-0" in toks and "right-0" in toks) or "inset-x-0" in toks)


def dock_hero_bottom_strip(html: str) -> Tuple[str, int]:
    """(html, strips docked)."""
    if not html:
        return html, 0
    m = _HERO_OPEN_RE.search(html)
    if not m:
        return html, 0
    start, end = m.start(), _section_end(html, m.start())
    hero = html[start:end]
    docked = 0
    out, pos = [], 0
    for d in _DIV_OPEN_RE.finditer(hero):
        classes = d.group(2)
        if not _is_bottom_strip(classes):
            continue
        if not _div_inner_text(hero, d.end()):
            continue  # a decorative gradient/scrim, not content
        kept = [c for c in classes.split() if c not in _PIN_TOKENS]
        new_classes = " ".join(["relative", "w-full", *kept])
        tag = d.group(0)
        new_tag = tag.replace(d.group(1) + classes + d.group(1), d.group(1) + new_classes + d.group(1), 1)
        out.append(hero[pos:d.start()])
        out.append(new_tag)
        pos = d.end()
        docked += 1
    if not docked:
        return html, 0
    out.append(hero[pos:])
    hero = "".join(out)

    def _section_classes(cm: "re.Match") -> str:
        toks = cm.group(3).split()
        if "flex" in toks and "flex-col" not in toks:
            toks = ["flex-col" if t == "flex" else t for t in toks]
            toks.insert(toks.index("flex-col"), "flex")
            toks = ["justify-end" if t == "items-end" else t for t in toks]
        return f"{cm.group(1)}{cm.group(2)}{' '.join(toks)}{cm.group(2)}"

    open_tag = _HERO_OPEN_RE.match(hero).group(0)
    hero = _CLASS_RE.sub(_section_classes, open_tag, count=1) + hero[len(open_tag):]
    return html[:start] + hero + html[end:], docked
