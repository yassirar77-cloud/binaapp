"""A control that does nothing is worse than no control.

WHY THIS EXISTS
---------------
The reported page shipped with three kinds of link that go nowhere:

  * Section "Lawati" had a button "WhatsApp Kami" -> ``#hubungi``.
    Section "Hubungi" had a button "Lihat Lokasi Kami" -> ``#lawati``.
    The two pointed at each other, and neither opened WhatsApp.
  * Every footer social icon was ``href="#"`` — rendered because the merchant
    ticked "Social Media", dead because they never gave a single URL.
  * Anchors to ``#menu``-style targets that the document never defines.

Each one is a customer who tried to reach the business and did not. The
generator cannot be talked out of emitting them (it writes the markup and the
section ids independently), so they are removed here, deterministically,
after the fact.

THE RULES
---------
1. A link labelled WhatsApp must be a WhatsApp link. If the page has a real
   ``wa.me`` number, the label is re-pointed at it; if it has none, the
   control is removed rather than left pointing at a section.
2. A social icon with no destination is removed entirely — icon and all.
   An icon row with one dead icon in it is a broken row.
3. Any other anchor with no destination (``#``, empty, ``javascript:``) or
   one pointing at an id the document does not define is UNWRAPPED: its text
   survives, its false affordance does not.

Pure function of html -> (html, report).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set, Tuple

_ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a\s*>", re.IGNORECASE | re.DOTALL)
_HREF_RE = re.compile(r"""\bhref\s*=\s*(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)
_ID_RE = re.compile(r"""\b(?:id|name)\s*=\s*(["'])([^"']+)\1""", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WA_LINK_RE = re.compile(r"https?://(?:wa\.me|api\.whatsapp\.com)/\S*?(?=[\"'\s>])", re.IGNORECASE)
_WA_DIGITS_RE = re.compile(r"wa\.me/(\d{8,15})", re.IGNORECASE)

#: Platform markers in a class, aria-label, title or the icon glyph itself.
_SOCIAL_MARKERS = (
    "facebook", "instagram", "tiktok", "twitter", "x-twitter", "youtube",
    "linkedin", "telegram", "pinterest", "snapchat", "threads", "whatsapp",
    "fa-brands", "fab ",
)

#: A control that CLAIMS to be WhatsApp. Malay and English labels.
_WA_LABEL_RE = re.compile(r"whats\s*app|wasap", re.IGNORECASE)

#: Destinations that go nowhere.
_DEAD_HREFS = ("", "#", "#!", "javascript:void(0)", "javascript:void(0);", "javascript:;")


@dataclass
class LinkReport:
    removed: List[str] = field(default_factory=list)
    unwrapped: List[str] = field(default_factory=list)
    repointed: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.removed or self.unwrapped or self.repointed)

    def summary(self) -> str:
        return (
            f"{len(self.removed)} removed, {len(self.unwrapped)} unwrapped, "
            f"{len(self.repointed)} re-pointed"
        )


def document_anchor_ids(html: str) -> Set[str]:
    """Every in-page target the document actually defines."""
    return {match.group(2).strip() for match in _ID_RE.finditer(html or "")}


def page_whatsapp_link(html: str) -> str:
    """The first real wa.me link on the page, or ''.

    Placeholder numbers do not count — a control re-pointed at an example
    number is exactly the defect this module exists to remove.
    """
    from app.services.generation_validator import normalize_my_phone_digits

    for match in _WA_LINK_RE.finditer(html or ""):
        url = match.group(0)
        digits = _WA_DIGITS_RE.search(url)
        if digits and normalize_my_phone_digits(digits.group(1)):
            return url
    return ""


def _label_of(attrs: str, inner: str) -> str:
    aria = re.search(r"""\baria-label\s*=\s*(["'])(.*?)\1""", attrs, re.IGNORECASE | re.DOTALL)
    title = re.search(r"""\btitle\s*=\s*(["'])(.*?)\1""", attrs, re.IGNORECASE | re.DOTALL)
    text = _TAG_RE.sub(" ", inner or "")
    return " ".join(
        part for part in (
            aria.group(2) if aria else "",
            title.group(2) if title else "",
            text,
        ) if part
    )


def _is_social(attrs: str, inner: str) -> bool:
    hay = f"{attrs} {inner}".lower()
    return any(marker in hay for marker in _SOCIAL_MARKERS)


def _is_dead(href: str, anchor_ids: Set[str]) -> bool:
    value = (href or "").strip()
    if value.lower() in _DEAD_HREFS:
        return True
    if value.lower().startswith("javascript:"):
        return True
    if value.startswith("#") and len(value) > 1:
        return value[1:] not in anchor_ids
    return False


#: Anchors written inside <script>/<style> are code, not controls.
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)


def _mask_code(html: str) -> Tuple[str, List[str]]:
    stash: List[str] = []

    def _stash(match: re.Match) -> str:
        stash.append(match.group(0))
        return f"\x00CODE{len(stash) - 1}\x00"

    return _SCRIPT_STYLE_RE.sub(_stash, html), stash


def _unmask_code(html: str, stash: List[str]) -> str:
    if not stash:
        return html
    return re.sub(r"\x00CODE(\d+)\x00", lambda m: stash[int(m.group(1))], html)


def _with_href(attrs: str, url: str) -> str:
    """``attrs`` with its href set to ``url``, adding one if it had none."""
    if _HREF_RE.search(attrs):
        attrs = _HREF_RE.sub(
            lambda m: f"href={m.group(1)}{url}{m.group(1)}", attrs, count=1
        )
    else:
        attrs = f' href="{url}"' + attrs
    if "target=" not in attrs.lower():
        attrs += ' target="_blank"'
    if "rel=" not in attrs.lower():
        attrs += ' rel="noopener"'
    return attrs


def strip_dead_links(html: str) -> Tuple[str, LinkReport]:
    """Remove, unwrap or re-point every anchor that leads nowhere.

    Idempotent: a second pass finds nothing left to change.
    """
    report = LinkReport()
    if not html or "<a" not in html.lower():
        return html, report

    masked, stash = _mask_code(html)
    anchor_ids = document_anchor_ids(masked)
    wa_link = page_whatsapp_link(masked)

    def _replace(match: re.Match) -> str:
        attrs, inner = match.group(1), match.group(2)
        href_match = _HREF_RE.search(attrs)
        href = href_match.group(2) if href_match else ""
        label = _label_of(attrs, inner)
        lowered = href.lower()

        # Rule 1 — a control labelled WhatsApp must BE a WhatsApp link. The
        # reported page had "WhatsApp Kami" scrolling to #hubungi, whose own
        # button scrolled back. Two buttons, no WhatsApp.
        claims_whatsapp = bool(_WA_LABEL_RE.search(label))
        is_whatsapp = "wa.me/" in lowered or "api.whatsapp.com" in lowered
        if claims_whatsapp and not is_whatsapp:
            if wa_link:
                report.repointed.append(label.strip()[:60] or "whatsapp control")
                return f"<a{_with_href(attrs, wa_link)}>{inner}</a>"
            report.removed.append(label.strip()[:60] or "whatsapp control")
            return ""

        if not _is_dead(href, anchor_ids):
            return match.group(0)

        # Rule 2 — a social icon with no destination is not an icon.
        if _is_social(attrs, inner):
            report.removed.append(label.strip()[:60] or "social icon")
            return ""

        # Rule 3 — everything else keeps its words, loses its affordance.
        report.unwrapped.append(label.strip()[:60] or "link")
        return inner

    return _unmask_code(_ANCHOR_RE.sub(_replace, masked), stash), report
