"""An element the page's own CSS hides on phones must actually hide.

agp's header nav was ``<nav class="desktop-nav flex ...">`` with the page's
own ``@media (max-width:767px){ .desktop-nav{display:none} }``. Tailwind's
``.flex{display:flex}`` is injected later at the same specificity, so it
won: the five desktop links and the 'Pesan di WhatsApp' button rendered on
a phone, and the page was 527px wide on a 390px screen.

``fix_hidden_display_conflicts`` finds custom classes the page hides inside
a ``max-width`` media query, and on any element carrying one of them plus an
unprefixed Tailwind display utility (flex, grid, block, inline-flex, …)
replaces that utility with ``hidden <bp>:<utility>`` — Tailwind's own way
to say the same thing, which no stylesheet order can undo. The breakpoint
matches the media query (767px → md, 639px → sm, 1023px → lg). Only those
class attributes change. Idempotent.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

_DISPLAY_UTILS = ("flex", "grid", "block", "inline-flex", "inline-block", "inline-grid", "inline", "table", "contents")
_MEDIA_RE = re.compile(r"@media\s*\(\s*max-width\s*:\s*(\d+)px\s*\)\s*\{", re.IGNORECASE)
_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_CLASS_ATTR_RE = re.compile(r"""(\bclass\s*=\s*)(["'])([^"']*)\2""", re.IGNORECASE)


def _breakpoint(max_width: int) -> str:
    """The Tailwind prefix where the element should show again."""
    if max_width < 640:
        return "sm"
    if max_width < 768:
        return "md"
    if max_width < 1024:
        return "lg"
    if max_width < 1280:
        return "xl"
    return "2xl"


def _media_body(css: str, open_end: int) -> str:
    depth, i = 1, open_end
    while i < len(css) and depth:
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
        i += 1
    return css[open_end:i - 1]


def hidden_below(html: str) -> Dict[str, str]:
    """{custom class: tailwind breakpoint} for classes the page hides with
    display:none inside a max-width media query."""
    out: Dict[str, str] = {}
    for style in re.findall(r"<style\b[^>]*>(.*?)</style>", html or "", re.IGNORECASE | re.DOTALL):
        for m in _MEDIA_RE.finditer(style):
            bp = _breakpoint(int(m.group(1)))
            for rule in _RULE_RE.finditer(_media_body(style, m.end())):
                if not re.search(r"display\s*:\s*none", rule.group(2), re.IGNORECASE):
                    continue
                for sel in rule.group(1).split(","):
                    sel = sel.strip()
                    if re.fullmatch(r"\.[A-Za-z_][\w-]*", sel):
                        out.setdefault(sel[1:], bp)
    return out


def fix_hidden_display_conflicts(html: str) -> Tuple[str, int]:
    """(html, elements fixed)."""
    hidden = hidden_below(html)
    if not hidden:
        return html, 0
    fixed = 0

    def _sub(m: "re.Match") -> str:
        nonlocal fixed
        toks = m.group(3).split()
        hits = [c for c in toks if c in hidden]
        if not hits or "hidden" in toks:
            return m.group(0)
        bp = hidden[hits[0]]
        out, changed = [], False
        for t in toks:
            if t in _DISPLAY_UTILS:
                out.extend(["hidden", f"{bp}:{t}"])
                changed = True
            else:
                out.append(t)
        if not changed:
            return m.group(0)
        fixed += 1
        return f"{m.group(1)}{m.group(2)}{' '.join(out)}{m.group(2)}"

    return _CLASS_ATTR_RE.sub(_sub, html), fixed
