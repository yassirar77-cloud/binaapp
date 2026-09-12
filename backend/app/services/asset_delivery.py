"""Ship the bytes the page needs and none of the bytes it doesn't.

Two defects from the report, both about what a Malaysian visitor on mobile
data actually downloads before the page paints.

CLOUDINARY (report #13)
-----------------------
Generated pages referenced uploads raw::

    https://res.cloudinary.com/<cloud>/image/upload/v1789208034/xxx.jpg

That is the original file: full resolution, original format, no compression
budget — a 4MB phone photo served at 4MB into a 400px-wide card. Cloudinary
does the work for free if asked, so every upload URL gets

    /upload/f_auto,q_auto,c_limit,w_<cap>/v.../

``f_auto`` serves AVIF/WebP to browsers that take it, ``q_auto`` picks a
quality per image, and ``c_limit`` only ever scales DOWN — an image smaller
than the cap is untouched rather than upscaled. Typical saving is 60-80%.

FONT AWESOME (report #12)
-------------------------
Every page loaded ``all.min.css``, which carries the core plus the solid,
regular and brands families. Most generated pages use solid icons only, and
one or two use brands for social links. Font Awesome 6 ships those families
as separate stylesheets precisely so a page can take what it uses, so the
link is rewritten to the families the markup actually references.

Pure functions of html -> (html, report). Idempotent: a page that has
already been optimised is returned unchanged.

NOT in here: the Tailwind play CDN (``cdn.tailwindcss.com``), which compiles
CSS in the browser on every visit and is documented as not-for-production.
Replacing it means running a Tailwind build in the generation pipeline and
inlining the purged output — real work, and a change to how every page is
built, not a rewrite pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

#: Width caps per slot. A hero spans the viewport; a card never does.
HERO_WIDTH = 1920
GALLERY_WIDTH = 800
DEFAULT_WIDTH = 1200

#: The transformation applied to every upload URL. c_limit is the important
#: one: it scales down and never up, so a small source image is left alone.
_TRANSFORM = "f_auto,q_auto,c_limit,w_{width}"

#: `https://res.cloudinary.com/<cloud>/image/upload/` + what follows.
_CLOUDINARY_RE = re.compile(
    r"(https://res\.cloudinary\.com/[^/\s\"']+/(?:image|video)/upload/)([^\s\"'()<>]+)",
    re.IGNORECASE,
)

#: A path segment that is a transformation, not a version or a public id:
#: Cloudinary parameters are `<key>_<value>` joined by commas.
_TRANSFORM_SEGMENT_RE = re.compile(r"^[a-z]{1,3}_[^/,]+(?:,[a-z]{1,3}_[^/,]+)*$", re.IGNORECASE)

#: Markers that put an image in the hero rather than a card.
_HERO_MARKERS = ("hero", "banner", 'id="home"', "id='home'")
#: How far back from the URL's own tag to read for context. Short on
#: purpose: a wide window reaches past the card into the hero section
#: above it and caps every gallery image at hero width.
_CONTEXT_LOOKBACK = 160

_FA_LINK_RE = re.compile(
    r"""<link\b[^>]*href\s*=\s*["']([^"']*font-?awesome[^"']*)["'][^>]*>""",
    re.IGNORECASE,
)
_FA_ALL_RE = re.compile(r"/css/all(\.min)?\.css", re.IGNORECASE)


@dataclass
class AssetReport:
    images_optimized: int = 0
    font_awesome_families: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.images_optimized or self.font_awesome_families)


def _already_transformed(tail: str) -> bool:
    """True when the URL already carries a transformation segment."""
    first = tail.split("/", 1)[0]
    if first.startswith("v") and first[1:].isdigit():
        return False
    return bool(_TRANSFORM_SEGMENT_RE.match(first))


#: Markers that put an image in a card rather than the hero.
_CARD_MARKERS = ("gallery", "grid", "card", "menu-item", "thumb")


def _slot_width(html: str, position: int) -> int:
    """Hero or card? Decided by the NEAREST marker before the URL.

    Nearest matters: a gallery sits below the hero, so any rule that merely
    asks "is 'hero' somewhere above this" caps every card image at 1920 —
    the whole saving, lost on the images there are most of.
    """
    tag_start = html.rfind("<", 0, position)
    if tag_start == -1:
        tag_start = position
    tag = html[tag_start:position].lower()
    if any(marker in tag for marker in _HERO_MARKERS):
        return HERO_WIDTH
    if any(marker in tag for marker in _CARD_MARKERS):
        return GALLERY_WIDTH

    window = html[max(0, tag_start - _CONTEXT_LOOKBACK):tag_start].lower()
    nearest_hero = max((window.rfind(m) for m in _HERO_MARKERS), default=-1)
    nearest_card = max((window.rfind(m) for m in _CARD_MARKERS), default=-1)
    if nearest_hero > nearest_card:
        return HERO_WIDTH
    if nearest_card >= 0:
        return GALLERY_WIDTH
    return GALLERY_WIDTH if tag.startswith("<img") else DEFAULT_WIDTH


def optimize_cloudinary_urls(html: str) -> Tuple[str, AssetReport]:
    """Add delivery transformations to every raw Cloudinary upload URL."""
    report = AssetReport()
    if not html or "res.cloudinary.com" not in html:
        return html, report

    def _replace(match: re.Match) -> str:
        prefix, tail = match.group(1), match.group(2)
        if _already_transformed(tail):
            return match.group(0)
        width = _slot_width(html, match.start())
        report.images_optimized += 1
        return f"{prefix}{_TRANSFORM.format(width=width)}/{tail}"

    return _CLOUDINARY_RE.sub(_replace, html), report


def font_awesome_families(html: str) -> List[str]:
    """Which Font Awesome families the markup actually references."""
    found: List[str] = []
    lowered = html or ""
    if re.search(r"\b(?:fab|fa-brands)\b", lowered):
        found.append("brands")
    if re.search(r"\b(?:far|fa-regular)\b", lowered):
        found.append("regular")
    # Solid is the default family: `fa-utensils` with no family class is solid,
    # so it is assumed present whenever any icon is used at all.
    if re.search(r"\bfa[srlbd]?\b|\bfa-[a-z0-9-]+", lowered):
        found.append("solid")
    return found


def trim_font_awesome(html: str) -> Tuple[str, AssetReport]:
    """Swap the all-families stylesheet for the families in use.

    A page with no Font Awesome icons at all loses the stylesheet entirely.
    """
    report = AssetReport()
    link = _FA_LINK_RE.search(html or "")
    if not link or not _FA_ALL_RE.search(link.group(1)):
        return html, report

    # Look at the markup only — the <link> itself contains "fontawesome".
    markup = html[:link.start()] + html[link.end():]
    families = font_awesome_families(markup)

    if not families:
        report.notes.append("font-awesome removed — no icons on the page")
        return markup, report

    href = link.group(1)
    replacement = "\n".join(
        f'<link rel="stylesheet" href="{_FA_ALL_RE.sub(f"/css/{name}.min.css", href)}">'
        # `fontawesome` is the core (sizing, layout, the fa-* base class);
        # each family file adds only its own @font-face and glyph map.
        for name in ["fontawesome"] + families
    )
    report.font_awesome_families = families
    return html[:link.start()] + replacement + html[link.end():], report


def optimize_assets(html: str) -> Tuple[str, AssetReport]:
    """Every delivery optimisation, in one call. Idempotent."""
    html, images = optimize_cloudinary_urls(html)
    html, fonts = trim_font_awesome(html)
    return html, AssetReport(
        images_optimized=images.images_optimized,
        font_awesome_families=fonts.font_awesome_families,
        notes=images.notes + fonts.notes,
    )
