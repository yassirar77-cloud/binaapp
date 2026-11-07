"""AI food photos are labelled "Gambar hiasan"; menu photos are not reused
in the about section.

- Malaysian F&B sites mark an illustrative photo as such. Every image the
  pipeline GENERATED (never a merchant upload, never a stock fallback)
  carries a small "Gambar hiasan" label: the menu block draws its own
  (menu_fidelity); ``label_ai_images`` does the rest of the page (hero,
  about, gallery).
- agp's "Tentang Kami" showed the Signature set's menu photo a second time.
  ``remove_menu_photo_reuse`` drops any about-section image that is also a
  menu item's photo; a wrapper left empty goes with it, and a two-column
  grid left with only the text becomes one column, so the section reads as
  text-only rather than half empty.

Pure string transforms; no I/O.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple

from app.services.menu_fidelity import AI_LABEL, MENU_BLOCK_CLASS, _url_key

_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_RE = re.compile(r"""\bsrc\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)
_CLASS_RE = re.compile(r"""\bclass\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)
_ABOUT_OPEN_RE = re.compile(
    r"""<section\b[^>]*\b(?:id|class)\s*=\s*["'][^"']*\b(about|tentang|kisah|story|cerita)\b[^"']*["'][^>]*>""",
    re.IGNORECASE,
)


def _section_end(html: str, start: int) -> int:
    depth = 0
    for m in re.finditer(r"<(/?)section\b[^>]*>", html[start:], re.IGNORECASE):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return start + m.end()
    return len(html)


def _div_end(html: str, start: int) -> int:
    depth = 0
    for m in re.finditer(r"<(/?)div\b[^>]*>", html[start:], re.IGNORECASE):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return start + m.end()
    return len(html)


def _lang(language: str) -> str:
    return "en" if str(language or "ms").lower().startswith("en") else "ms"


def remove_menu_photo_reuse(html: str, menu_urls: Iterable[str]) -> Tuple[str, int]:
    """Drop about-section images that are a menu item's photo. (html, removed)"""
    keys = {_url_key(u) for u in menu_urls if u}
    if not html or not keys:
        return html, 0
    removed = 0
    out, pos = [], 0
    for m in _ABOUT_OPEN_RE.finditer(html):
        if m.start() < pos:
            continue
        start, end = m.start(), _section_end(html, m.start())
        section = html[start:end]
        n_before = len(_IMG_RE.findall(section))

        def _drop(mm: "re.Match") -> str:
            nonlocal removed
            src = _SRC_RE.search(mm.group(0))
            if src and _url_key(src.group(2).strip()) in keys:
                removed += 1
                return ""
            return mm.group(0)

        new = _IMG_RE.sub(_drop, section)
        if len(_IMG_RE.findall(new)) != n_before:
            # Wrappers the image leaves empty (<div ...></div>, <figure>...).
            for _ in range(3):
                new = re.sub(r"<(div|figure|picture|a)\b[^>]*>\s*(?:<figcaption\b[^>]*>.*?</figcaption>\s*)?</\1>", "", new,
                             flags=re.IGNORECASE | re.DOTALL)
            if not _IMG_RE.search(new):
                # Text-only now: a two-column grid would leave half empty.
                new = re.sub(r"\b(md|lg):grid-cols-2\b", r"\1:grid-cols-1", new)
        out.append(html[pos:start])
        out.append(new)
        pos = end
    out.append(html[pos:])
    return "".join(out), removed


def _menu_block_spans(html: str) -> List[Tuple[int, int]]:
    spans = []
    for m in re.finditer(rf"<div\b[^>]*class=\"{MENU_BLOCK_CLASS}\b", html):
        spans.append((m.start(), _div_end(html, m.start())))
    return spans


_LABEL_STYLE = (
    "position:absolute;right:.5rem;{v}:.5rem;z-index:40;padding:.15rem .45rem;border-radius:4px;"
    "background:rgba(0,0,0,.6);color:#fff;font-size:.68rem;font-weight:600;line-height:1.3;pointer-events:none"
)


def label_ai_images(html: str, ai_urls: Iterable[str], language: str = "ms") -> Tuple[str, int]:
    """Put "Gambar hiasan" on every AI-generated <img> outside the menu
    block (which labels its own). An absolutely positioned image (a hero
    background) gets the label in its section's top-right corner; any other
    image is wrapped so the label sits on its bottom-right. Idempotent.
    (html, labelled)"""
    keys = {_url_key(u) for u in ai_urls if u}
    if not html or not keys:
        return html, 0
    label = AI_LABEL[_lang(language)]
    skip = _menu_block_spans(html)
    labelled = 0
    out, pos = [], 0
    for m in _IMG_RE.finditer(html):
        if any(s <= m.start() < e for s, e in skip):
            continue
        tag = m.group(0)
        src = _SRC_RE.search(tag)
        if not src or _url_key(src.group(2).strip()) not in keys:
            continue
        after = html[m.end():m.end() + 160]
        if "binaapp-ai-label" in after:
            continue
        before = html[max(0, m.start() - 160):m.start()]
        if "binaapp-ai-wrap" in before[-120:]:
            continue
        cls = (_CLASS_RE.search(tag).group(2) if _CLASS_RE.search(tag) else "")
        toks = cls.split()
        if "absolute" in toks or "fixed" in toks:
            new = tag + f'<span class="binaapp-ai-label" style="{_LABEL_STYLE.format(v="top")}">{label}</span>'
        else:
            height = "height:100%;" if "h-full" in toks else ""
            new = (
                f'<span class="binaapp-ai-wrap" style="position:relative;display:block;{height}">{tag}'
                f'<span class="binaapp-ai-label" style="{_LABEL_STYLE.format(v="bottom")}">{label}</span></span>'
            )
        out.append(html[pos:m.start()])
        out.append(new)
        pos = m.end()
        labelled += 1
    out.append(html[pos:])
    html2, n_bg = _label_ai_backgrounds("".join(out), keys, label)
    return html2, labelled + n_bg


_BG_URL_RE = re.compile(r"""background(?:-image)?\s*:[^;{}]*url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.IGNORECASE)
_POSITIONED_RE = re.compile(r"(?:^|\s)(?:relative|absolute|fixed|sticky)(?:\s|$)")


def _label_ai_backgrounds(html: str, keys: set, label: str) -> Tuple[str, int]:
    """An AI photo used as a CSS background (agp's hero: .hero-image{
    background-image:url(...)}, or an inline style) gets the label in the
    element's top-right corner. The element is made position:relative only
    when it has no positioning of its own."""
    targets: List[str] = []
    for css in re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.IGNORECASE | re.DOTALL):
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
            m = _BG_URL_RE.search(body)
            if not m or _url_key(m.group(1).strip()) not in keys:
                continue
            for one in sel.split(","):
                one = one.strip()
                if re.fullmatch(r"[.#][A-Za-z_][\w-]*", one):
                    targets.append(one)
    n = 0
    for target in dict.fromkeys(targets):
        if target.startswith("."):
            pat = rf"<(\w+)\b[^>]*\bclass\s*=\s*([\"'])(?:[^\"']*\s)?{re.escape(target[1:])}(?:\s[^\"']*)?\2[^>]*>"
        else:
            pat = rf"<(\w+)\b[^>]*\bid\s*=\s*([\"']){re.escape(target[1:])}\2[^>]*>"
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            html, ok = _insert_bg_label(html, m, label)
            n += ok
    # Inline background-image styles.
    for m in list(re.finditer(r"<(\w+)\b[^>]*\bstyle\s*=\s*([\"'])[^\"']*\2[^>]*>", html, re.IGNORECASE))[::-1]:
        bg = _BG_URL_RE.search(m.group(0))
        if bg and _url_key(bg.group(1).strip()) in keys:
            html, ok = _insert_bg_label(html, m, label)
            n += ok
    return html, n


def _insert_bg_label(html: str, m: "re.Match", label: str) -> Tuple[str, int]:
    tag = m.group(0)
    after = html[m.end():m.end() + 200]
    if "binaapp-ai-label" in after:
        return html, 0
    cls = _CLASS_RE.search(tag)
    positioned = bool(cls and _POSITIONED_RE.search(" " + cls.group(2) + " ")) or re.search(r"position\s*:", tag, re.IGNORECASE)
    new_tag = tag
    if not positioned:
        if re.search(r"\bstyle\s*=\s*[\"']", tag, re.IGNORECASE):
            new_tag = re.sub(r"(\bstyle\s*=\s*[\"'])", r"\1position:relative;", tag, count=1, flags=re.IGNORECASE)
        else:
            new_tag = tag[:-1] + ' style="position:relative">'
    span = f'<span class="binaapp-ai-label" style="{_LABEL_STYLE.format(v="top")}">{label}</span>'
    return html[: m.start()] + new_tag + span + html[m.end():], 1
