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


_WA_LABEL_RE = re.compile(r"whats\s*app\s*[:：-]?\s*$", re.IGNORECASE)


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
            # A number the page labels as WhatsApp ("WhatsApp: 012-697 3105")
            # opens WhatsApp, not a phone call (agp's footer).
            if _WA_LABEL_RE.search(segment[max(0, m.start() - 24):m.start()]):
                return f'<a href="https://wa.me/{digits}" class="binaapp-wa" style="text-decoration:inherit;color:inherit">{m.group(1)}</a>'
            return f'<a href="tel:+{digits}" class="binaapp-tel" style="text-decoration:inherit;color:inherit">{m.group(1)}</a>'

        return _PHONE_RE.sub(_sub, segment)

    for m in _SKIP_RE.finditer(html):
        out.append(_text(html[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_text(html[pos:]))
    return "".join(out), added


# ---------------------------------------------------------------------------
# Tap-to-call next to WhatsApp
# ---------------------------------------------------------------------------

_CONTAINER_OPEN_RE = re.compile(
    r"<(footer)\b[^>]*>|<(section)\b[^>]*\b(?:id|class)\s*=\s*[\"'][^\"']*\b(contact|hubungi|kontak|tempah|order)[^\"']*[\"'][^>]*>",
    re.IGNORECASE,
)
_WA_ANCHOR_RE = re.compile(r"<a\b[^>]*href=[\"']https?://(?:api\.)?(?:wa\.me|whatsapp\.com)/[^\"']*[\"'][^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)
_CLASS_ATTR_RE = re.compile(r"""\bclass\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
#: Colour utilities in WhatsApp green — dropped from the call link's copy
#: of the classes. Shape/spacing classes (and a custom .btn-whatsapp that
#: carries the padding and radius) are KEPT: stripping every class with
#: "whatsapp" in it left agp's call link as bare highlighted text.
_GREEN_CLASS_RE = re.compile(
    r"^(?:[\w-]+:)*(?:bg|text|border|ring|from|via|to|shadow|fill|stroke)-(?:\[#?(?:25d366|128c7e|075e54|1da851|20ba5a|22c55e)\]|(?:green|emerald|lime)-\d+(?:/\d+)?)$",
    re.IGNORECASE,
)
_BRAND_CLASS_RE = re.compile(r"whatsapp|\bwa\b|-wa\b|wa-", re.IGNORECASE)
_NEUTRAL_CALL_STYLE = "background:#FFFFFF;color:#141414;border-color:#141414"


def display_phone(digits: str) -> str:
    """60126973105 → "012-697 3105"; 601123456789 → "011-2345 6789";
    60333231234 → "03-3323 1234"."""
    d = re.sub(r"\D", "", str(digits or ""))
    if d.startswith("60"):
        d = "0" + d[2:]
    if d.startswith("01"):
        head, rest = d[:3], d[3:]
    elif d.startswith("0"):
        head, rest = d[:2], d[2:]
    else:
        return d
    if len(rest) >= 7:
        cut = len(rest) - 4
        return f"{head}-{rest[:cut]} {rest[cut:]}"
    return f"{head}-{rest}"


def _container_end(html: str, start: int, tag: str) -> int:
    depth = 0
    for m in re.finditer(rf"<(/?){tag}\b[^>]*>", html[start:], re.IGNORECASE):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return start + m.end()
    return len(html)


def add_call_links(html: str, wa_digits: str, *, language: str = "ms") -> Tuple[str, int]:
    """Add a tap-to-call link (``tel:+60…``) right after the first WhatsApp
    link in the footer and in the contact section, when that container has
    no tel: link yet. A restaurant's customers both message and call; the
    page only had WhatsApp. The call link copies the WhatsApp link's
    classes minus its green, so it reads as a sibling. Idempotent.
    Returns (html, links added)."""
    digits = re.sub(r"\D", "", str(wa_digits or ""))
    if not html or len(digits) < 9:
        return html, 0
    if not digits.startswith("60"):
        digits = "60" + digits.lstrip("0")
    label = "Call" if str(language or "ms").lower().startswith("en") else "Telefon"
    number = display_phone(digits)
    added = 0
    out = html
    pos = 0
    while True:
        m = _CONTAINER_OPEN_RE.search(out, pos)
        if not m:
            break
        tag = (m.group(1) or m.group(2)).lower()
        end = _container_end(out, m.start(), tag)
        block = out[m.start():end]
        pos = end
        if "href=\"tel:" in block or "href='tel:" in block:
            continue
        wa = _WA_ANCHOR_RE.search(block)
        if not wa:
            continue
        cls_m = _CLASS_ATTR_RE.search(wa.group(0))
        classes = " ".join(c for c in (cls_m.group(1).split() if cls_m else []) if not _GREEN_CLASS_RE.match(c))
        # A WhatsApp-named class (.btn-whatsapp) keeps the button's shape
        # but paints it green: neutralise the colour inline, not the shape.
        # A footer text link only gets a neutral colour when it is green.
        style_attr = ""
        if _BRAND_CLASS_RE.search(classes):
            style_attr = f' style="{_NEUTRAL_CALL_STYLE}"'

        anchor_text = re.sub(r"<[^>]+>", "", wa.group(0)).strip()
        insert_at = m.start() + wa.end()
        call_attrs = (
            f'href="tel:+{digits}" class="{(classes + " binaapp-call").strip()}"{style_attr} '
            f'aria-label="{label} {number}"'
        )
        icon = '<i class="fa-solid fa-phone" aria-hidden="true"></i>'
        if tag == "footer":
            # Its own line, number shown: "Telefon: 012-697 3105". No "·"
            # separator — agp's footer stacked the links, leaving a lone
            # dot between the WhatsApp and Telefon lines.
            text = f"{label}: {number}"
            before = out[:m.start() + wa.start()]
            li_open = re.search(r"<li\b([^>]*)>\s*$", before, re.IGNORECASE)
            li_close = re.match(r"\s*</li>", out[insert_at:], re.IGNORECASE)
            block_level = bool(re.search(r"(?:^|\s)(?:flex|block|grid|w-full|inline-flex)(?:\s|$)", classes))
            if li_open and li_close:
                insert_at += li_close.end()
                call = f"<li{li_open.group(1)}><a {call_attrs}>{icon} {text}</a></li>"
            elif block_level:
                call = f'<a {call_attrs} style="margin-top:.5rem">{icon} {text}</a>' if not style_attr else f"<a {call_attrs}>{icon} {text}</a>"
            else:
                call = f"<br><a {call_attrs}>{icon} {text}</a>"
        else:
            # Contact section: a sibling button with the number on it.
            text = label if re.sub(r"\D", "", anchor_text).endswith(digits[-7:]) else f"{label} {number}"
            call = f" <a {call_attrs}>{icon} {text}</a>"
        out = out[:insert_at] + call + out[insert_at:]
        pos = end + len(call)
        added += 1
    return out, added


# ---------------------------------------------------------------------------
# WhatsApp buttons carry the WhatsApp icon
# ---------------------------------------------------------------------------

_WA_LINK_RE = re.compile(
    r"(<a\b[^>]*href=[\"']https?://(?:api\.)?(?:wa\.me|whatsapp\.com)/[^\"']*[\"'][^>]*>)(.*?)(</a>)",
    re.IGNORECASE | re.DOTALL,
)
WA_ICON = '<i class="fa-brands fa-whatsapp" aria-hidden="true"></i>'


def ensure_whatsapp_icons(html: str) -> Tuple[str, int]:
    """A link that SAYS WhatsApp ("WhatsApp Kami", "Pesan di WhatsApp") gets
    the WhatsApp icon when it has no icon or image of its own. agp's
    'WhatsApp Kami' button came out bare in one generation and with the
    icon in the next. Per-item 'Pesan' links and a footer line that only
    prints the number are left alone. Idempotent. Returns (html, added)."""
    if not html:
        return html, 0
    added = 0

    def _sub(m: "re.Match") -> str:
        nonlocal added
        inner = m.group(2)
        text = re.sub(r"<[^>]+>", " ", inner)
        if not re.search(r"\bwhats\s*app\b", text, re.IGNORECASE):
            return m.group(0)
        if re.search(r"<(?:i|svg|img)\b", inner, re.IGNORECASE):
            return m.group(0)
        added += 1
        return f"{m.group(1)}{WA_ICON} {inner.lstrip()}{m.group(3)}"

    out = _WA_LINK_RE.sub(_sub, html)
    return out, added
