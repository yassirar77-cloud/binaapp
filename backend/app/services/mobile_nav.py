"""The mobile navigation panel carries the WhatsApp / order CTA.

The desktop nav had a "Pesan" button; the slide-down panel phone users
actually open did not. The CTA the page already has (its first header
WhatsApp link, or a fresh one from the merchant's number) is appended to
the mobile panel when it is missing. Pure string transform; no I/O.
"""

from __future__ import annotations

import html as _html
import re
from typing import Optional, Tuple
from urllib.parse import quote

_PANEL_OPEN_RE = re.compile(
    r"<(div|nav|ul)\b[^>]*\b(?:id|class)\s*=\s*[\"'][^\"']*mobile[^\"']*(?:menu|nav|panel|drawer)[^\"']*[\"'][^>]*>",
    re.IGNORECASE,
)
_HEADER_RE = re.compile(r"<(header|nav)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_WA_LINK_RE = re.compile(r"<a\b[^>]*href=[\"']https?://(?:api\.)?(?:wa\.me|whatsapp\.com)/[^\"']*[\"'][^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)


def _element_span(html: str, open_match: "re.Match") -> Tuple[int, int]:
    tag = open_match.group(1).lower()
    depth = 0
    for m in re.finditer(rf"<(/?){tag}\b[^>]*>", html[open_match.start():], re.IGNORECASE):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return open_match.start(), open_match.start() + m.end()
    return open_match.start(), len(html)


def ensure_mobile_nav_cta(html: str, wa_digits: str, *, label: str = "Pesan di WhatsApp", prefill: str = "") -> Tuple[str, bool]:
    """Append a WhatsApp CTA to the mobile panel when it has none.
    Returns (html, added)."""
    if not html or not wa_digits:
        return html, False
    m = _PANEL_OPEN_RE.search(html)
    if not m:
        return html, False
    start, end = _element_span(html, m)
    panel = html[start:end]
    if _WA_LINK_RE.search(panel):
        return html, False
    cta: Optional[str] = None
    hm = _HEADER_RE.search(html)
    if hm:
        existing = _WA_LINK_RE.search(hm.group(0))
        if existing:
            cta = existing.group(0)
            if "block" not in cta and "w-full" not in cta:
                cta = re.sub(r"\bclass=([\"'])", r"class=\1block w-full text-center mt-3 ", cta, count=1) if "class=" in cta else cta.replace("<a ", '<a class="block w-full text-center mt-3" ', 1)
    if cta is None:
        href = f"https://wa.me/{wa_digits}" + (f"?text={quote(prefill, safe='')}" if prefill else "")
        cta = (
            f'<a href="{_html.escape(href)}" target="_blank" rel="noopener" '
            'class="block w-full text-center mt-3 px-4 py-3 rounded-full font-semibold" '
            'style="background:#25D366;color:#fff;text-decoration:none">'
            f'<i class="fa-brands fa-whatsapp" aria-hidden="true"></i> {_html.escape(label)}</a>'
        )
    close_tag = f"</{m.group(1).lower()}>"
    idx = panel.lower().rfind(close_tag)
    if idx == -1:
        return html, False
    if m.group(1).lower() == "ul":
        cta = f"<li>{cta}</li>"
    panel = panel[:idx] + "\n" + cta + "\n" + panel[idx:]
    return html[:start] + panel + html[end:], True
