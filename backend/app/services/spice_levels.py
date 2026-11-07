"""Spice levels on a phone: one compact row, not three full-width blocks.

agp's page showed Level 1 / Level 2 / Level 3 as three cards in a
``grid grid-cols-1 sm:grid-cols-3`` — on a phone each card filled the
screen width and the three took a full screen of scrolling before the menu.

``compact_spice_levels`` finds the element whose direct children each hold
one of the levels (the cards / chips), marks it ``binaapp-spice-row`` and
the children ``binaapp-spice-chip``, and adds a small stylesheet that lays
them out as one row of three compact chips at every width. Only those
opening tags are edited; the rest of the document is untouched. A sentence
that merely mentions the levels ("Level 1, Level 2 atau Level 3") is left
alone. Idempotent.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag

ROW_CLASS = "binaapp-spice-row"
CHIP_CLASS = "binaapp-spice-chip"
HERO_ROW_CLASS = "binaapp-spice-in-hero"
_LEVEL_RE = re.compile(r"\b(?:level|tahap)\s*([1-5])\b", re.IGNORECASE)

SPICE_CSS = (
    '<style id="binaapp-spice-css">'
    f".{ROW_CLASS}{{display:grid!important;grid-template-columns:repeat(var(--binaapp-spice-n,3),minmax(0,1fr))!important;"
    "gap:.5rem!important;flex-direction:unset!important}"
    f".{ROW_CLASS}>.{CHIP_CLASS}{{width:auto!important;max-width:none!important;min-width:0!important;min-height:0!important;margin:0!important;"
    # Normal inline flow: icons share one line, the label wraps under them
    # ("🔥🔥🔥" / "Level 3 Extra Hot"), never one icon per line.
    "padding:.55rem .35rem!important;text-align:center!important;display:block!important;"
    # Straight and inside its own column: agp's 'sticker' chips ended a
    # drop animation at rotate(-6deg) and were nowrap, so the third chip
    # spilled over its neighbour.
    "transform:none!important;rotate:none!important;translate:none!important;animation:none!important;opacity:1!important;"
    "position:relative!important;inset:auto!important;white-space:normal!important;overflow-wrap:anywhere;"
    "border-radius:.75rem!important}"
    f".{ROW_CLASS}>.{CHIP_CLASS} *{{font-size:clamp(.7rem,3.2vw,.95rem)!important;line-height:1.2!important;margin:0!important}}"
    f".{ROW_CLASS}>.{CHIP_CLASS}>:first-child{{font-size:clamp(.85rem,4.2vw,1.2rem)!important;font-weight:800}}"
    f".{ROW_CLASS}{{transform:none!important;rotate:none!important}}"
    # In the hero, the floating WhatsApp button (60px, bottom-right) sat on
    # the third chip at first load: keep the row clear of it on phones.
    f"@media (max-width:767px){{.{ROW_CLASS}.{HERO_ROW_CLASS}{{padding-right:4.75rem!important}}}}"
    f"@media (min-width:768px){{.{ROW_CLASS}{{gap:1rem!important}}.{ROW_CLASS}>.{CHIP_CLASS}{{padding:.85rem .75rem!important}}}}"
    "</style>"
)


def _line_offsets(html: str) -> List[int]:
    offs = [0]
    for m in re.finditer(r"\n", html):
        offs.append(m.end())
    return offs


def _tag_offset(tag: Tag, offsets: List[int]) -> Optional[int]:
    if tag.sourceline is None or tag.sourcepos is None:
        return None
    return offsets[tag.sourceline - 1] + tag.sourcepos


def _level_of(el: Tag) -> List[str]:
    return sorted(set(_LEVEL_RE.findall(el.get_text(" ", strip=True))))


def _find_row(soup: BeautifulSoup) -> Optional[Tuple[Tag, List[Tag]]]:
    texts = [
        s for s in soup.find_all(string=_LEVEL_RE)
        if isinstance(s, NavigableString) and s.parent is not None and s.parent.name not in ("script", "style", "title", "a")
    ]
    seen = set()
    for s in texts:
        node = s.parent
        while node is not None and isinstance(node, Tag) and node.name not in ("body", "html", "[document]"):
            if id(node) in seen:
                break
            seen.add(id(node))
            children = [c for c in node.children if isinstance(c, Tag)]
            chips = [c for c in children if len(_level_of(c)) == 1]
            levels = [lv for c in chips for lv in _level_of(c)]
            if len(chips) >= 3 and len(set(levels)) == len(chips) and len(chips) >= len(children) - 1:
                if all(len(c.get_text(" ", strip=True)) <= 80 for c in chips):
                    return node, chips
            node = node.parent
    return None


def _in_hero(el: Tag) -> bool:
    """Inside the hero: a section/header with id 'hero', or the page's first
    section when it carries the page's <h1>."""
    first_section = None
    root = el
    while root.parent is not None:
        root = root.parent
    first_section = root.find("section") if isinstance(root, Tag) else None
    node = el
    while node is not None and isinstance(node, Tag):
        if node.name in ("section", "header") and (
            str(node.get("id") or "").lower() == "hero" or (node is first_section and node.find("h1") is not None)
        ):
            return True
        node = node.parent
    return False


def _add_class(tag_html: str, cls: str) -> str:
    m = re.search(r"""\bclass\s*=\s*(["'])(.*?)\1""", tag_html, re.IGNORECASE | re.DOTALL)
    if m:
        if all(c in m.group(2).split() for c in cls.split()):
            return tag_html
        return tag_html[: m.start(2)] + (m.group(2) + " " + cls).strip() + tag_html[m.end(2):]
    return re.sub(r"^<(\w+)", rf'<\1 class="{cls}"', tag_html, count=1)


def compact_spice_levels(html: str) -> Tuple[str, bool]:
    """(html, changed)."""
    if not html or ROW_CLASS in html or not _LEVEL_RE.search(html):
        return html, False
    soup = BeautifulSoup(html, "html.parser")
    found = _find_row(soup)
    if not found:
        return html, False
    row, chips = found
    offsets = _line_offsets(html)
    edits: List[Tuple[int, str]] = []
    row_cls = ROW_CLASS + (f" {HERO_ROW_CLASS}" if _in_hero(row) else "")
    for el, cls in [(row, row_cls)] + [(c, CHIP_CLASS) for c in chips]:
        off = _tag_offset(el, offsets)
        if off is None or html[off:off + 1] != "<":
            return html, False
        edits.append((off, cls))
    out = html
    for off, cls in sorted(edits, reverse=True):
        end = out.index(">", off) + 1
        new_tag = _add_class(out[off:end], cls)
        if cls == ROW_CLASS and len(chips) != 3:
            new_tag = re.sub(r"^<(\w+)", rf'<\1 style="--binaapp-spice-n:{len(chips)}"', new_tag, count=1) \
                if "style=" not in new_tag else new_tag
        out = out[:off] + new_tag + out[end:]
    m = re.search(r"</head>", out, re.IGNORECASE)
    out = (out[: m.start()] + SPICE_CSS + out[m.start():]) if m else (SPICE_CSS + out)
    return out, True
