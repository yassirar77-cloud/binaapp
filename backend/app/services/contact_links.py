"""Phone numbers on the page are links.

"012-697 3105" was printed as text in the contact section and the footer;
on a phone that is a number to retype. Every visible Malaysian phone
number that is not already inside a link becomes ``<a href="tel:+60…">``.
Numbers inside <a>, <script>, <style>, attributes and the JSON-LD block
are left alone. Pure string transform; no I/O.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

from app.services.generation_validator import normalize_my_phone_digits

#: Malaysian numbers as people write them: 012-697 3105, 0126973105,
#: +60 12-697 3105, 03-3323 1234.
_PHONE_RE = re.compile(
    r"(?<![\w/.=:-])(\+?6?0\s?1\d[\s-]?\d{3,4}[\s-]?\d{4}|\+?6?0[3-9][\s-]?\d{3,4}[\s-]?\d{4})(?![\w/-])"
)
_SKIP_RE = re.compile(r"<(a|script|style|textarea|option)\b[^>]*>.*?</\1>|<[^>]+>|<!--.*?-->", re.IGNORECASE | re.DOTALL)


def linkify_phones(html: str, known_digits: Optional[Iterable[str]] = None) -> Tuple[str, int]:
    """Wrap bare phone numbers in tel: links. ``known_digits`` (digit-only,
    60-prefixed) limits linking to the merchant's own numbers when given;
    otherwise every well-formed Malaysian number is linked. Returns
    (html, links added)."""
    if not html:
        return html, 0
    wanted = {d for d in (known_digits or []) if d}
    added = 0
    out: List[str] = []
    pos = 0

    def _text(segment: str) -> str:
        def _sub(m: "re.Match") -> str:
            nonlocal added
            digits = normalize_my_phone_digits(m.group(1))
            if not digits or (wanted and digits not in wanted):
                return m.group(0)
            added += 1
            return f'<a href="tel:+{digits}" class="binaapp-tel" style="text-decoration:inherit;color:inherit">{m.group(1)}</a>'

        return _PHONE_RE.sub(_sub, segment)

    for m in _SKIP_RE.finditer(html):
        out.append(_text(html[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_text(html[pos:]))
    return "".join(out), added
