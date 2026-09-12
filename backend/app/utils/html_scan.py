"""A minimal balanced-tag scanner for generated HTML.

Regex cannot match nested elements, and every structural question this
codebase asks of a generated page ("what are this grid's direct children?",
"which child of the hero is its background image?") is a question about
nesting. This is the smallest thing that answers it: find where an element
ends, and enumerate the elements directly inside it.

Pure stdlib. Tolerant of the markup the model actually writes — unclosed
void elements, self-closing divs, attributes containing ``>`` inside
quotes are NOT handled (they are rare in generated output and the callers
degrade to "no match" rather than raising).
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

VOID_ELEMENTS = frozenset({
    "img", "br", "hr", "input", "meta", "link", "source", "area", "base",
    "col", "embed", "param", "track", "wbr",
})

OPEN_TAG_RE = re.compile(r"<([a-zA-Z][\w-]*)\b[^>]*?(/?)>")
CLASS_ATTR_RE = re.compile(r"(\bclass\s*=\s*)(['\"])(.*?)\2", re.IGNORECASE | re.DOTALL)


def tag_classes(open_tag: str) -> str:
    """The value of an opening tag's class attribute, or ''."""
    match = CLASS_ATTR_RE.search(open_tag)
    return match.group(3) if match else ""


def read_attr(open_tag: str, name: str) -> Optional[str]:
    """The value of ``name`` on an opening tag, or None when absent."""
    match = re.search(
        r"\b" + re.escape(name) + r"\s*=\s*([\"'])(.*?)\1", open_tag, re.IGNORECASE | re.DOTALL
    )
    return match.group(2) if match else None


def element_end(html: str, start: int) -> int:
    """Index just past the element whose opening tag begins at ``start``.

    -1 when the element never closes (truncated output) or ``start`` is not
    an opening tag. Void and self-closed elements end at their own tag.
    """
    open_match = OPEN_TAG_RE.match(html, start)
    if not open_match:
        return -1
    name = open_match.group(1).lower()
    if open_match.group(2) == "/" or name in VOID_ELEMENTS:
        return open_match.end()

    depth = 0
    pos = start
    pattern = re.compile(rf"<(/?){re.escape(name)}\b[^>]*?(/?)>", re.IGNORECASE)
    while True:
        match = pattern.search(html, pos)
        if not match:
            return -1
        if match.group(1) == "/":
            depth -= 1
            if depth == 0:
                return match.end()
        elif match.group(2) != "/":
            depth += 1
        pos = match.end()


def direct_children(html: str, inner_start: int, inner_end: int) -> List[Tuple[int, int]]:
    """``(start, end)`` of every element directly inside ``[inner_start, inner_end)``.

    Stops at the first child that does not close inside the range, so a
    truncated document yields the children it can prove rather than
    guessing at the rest.
    """
    children: List[Tuple[int, int]] = []
    pos = inner_start
    while pos < inner_end:
        nxt = html.find("<", pos)
        if nxt == -1 or nxt >= inner_end:
            break
        if not OPEN_TAG_RE.match(html, nxt):
            pos = nxt + 1
            continue
        end = element_end(html, nxt)
        if end == -1 or end > inner_end:
            break
        children.append((nxt, end))
        pos = end
    return children


def open_tag_end(html: str, start: int) -> int:
    """Index just past the ``>`` of the opening tag at ``start``."""
    match = OPEN_TAG_RE.match(html, start)
    return match.end() if match else -1
