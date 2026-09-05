"""Video background for the hero section — a deterministic HTML patch.

    new_html = apply_hero_video(html, video_url=..., poster_url=...)
    state    = detect_hero_video(html)
    new_html = remove_hero_video(html)

WHY THIS IS NOT REGENERATION
----------------------------
Same contract as ``theme_patcher``: adding motion behind the hero must not
cost a generation credit and must not move a single word of the merchant's
copy. The AI is used to MAKE the video (see ``zai_video_service``); putting
it on the page is a pure, offline, idempotent string edit.

WHAT GETS INJECTED
------------------
One self-contained block, fenced by HTML comments so removal is exact:

    <!--binaapp:hero-video-->
    <div class="binaapp-hero-video-layer" data-binaapp-video-url="..." ...>
      <video class="binaapp-hero-video" autoplay muted loop playsinline …>
      <div class="binaapp-hero-video-scrim"></div>
    </div>
    <!--/binaapp:hero-video-->

plus a ``<style id="binaapp-hero-video-style">`` block in ``<head>``, and a
``data-binaapp-hero-video`` marker attribute on the hero element itself (the
only CSS hook — the rules never depend on the merchant's own class names).

SAFETY RULES
------------
* The layer is ``position:absolute; inset:0`` INSIDE the hero, so it paints
  over the hero's own background and under its content. Existing hero
  children are lifted to ``z-index:1`` — no re-ordering, no unwrapping.
* Everything is inert to the reader: ``aria-hidden``, ``tabindex="-1"``,
  ``pointer-events:none``. A muted, looping, ``playsinline`` video is the
  only shape mobile Safari/Chrome will autoplay.
* ``prefers-reduced-motion`` hides the video and leaves the poster still —
  motion behind text is exactly the thing that setting exists for.
* Applying twice is applying once: apply() removes any previous block first,
  so settings changes never stack layers or nest markers.
* URLs are validated (https, no quotes/spaces) and HTML-escaped before they
  reach an attribute — a merchant-supplied URL can never close the tag.
"""

from __future__ import annotations

import html as html_lib
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: Marker attribute written onto the hero element. Every injected CSS rule is
#: scoped to it, so nothing in this module depends on the merchant's classes.
HERO_MARKER_ATTR = "data-binaapp-hero-video"
#: id of the injected <style> block, so a re-apply replaces rather than stacks.
STYLE_ID = "binaapp-hero-video-style"
#: Comment fence around the injected markup — exact, nesting-proof removal.
BLOCK_START = "<!--binaapp:hero-video-->"
BLOCK_END = "<!--/binaapp:hero-video-->"

#: Overlay presets: the scrim painted between the video and the hero copy.
#: Without one, white hero text over a bright frame is unreadable.
OVERLAY_MODES = ("dark", "light", "none")
#: How the hero's own text colour is handled once a video sits behind it.
TEXT_MODES = ("auto", "light", "dark", "keep")

DEFAULT_OVERLAY = "dark"
DEFAULT_OVERLAY_OPACITY = 0.45
DEFAULT_TEXT_MODE = "auto"

_BLOCK_RE = re.compile(
    re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END),
    re.DOTALL | re.IGNORECASE,
)
_STYLE_RE = re.compile(
    r'<style\b[^>]*\bid=["\']' + re.escape(STYLE_ID) + r'["\'][^>]*>.*?</style>',
    re.DOTALL | re.IGNORECASE,
)
_MARKER_ATTR_RE = re.compile(
    r'\s+' + re.escape(HERO_MARKER_ATTR) + r'(?![\w-])'
    r'(?:=(?:"[^"]*"|\'[^\']*\'|[^\s>]*))?',
    re.IGNORECASE,
)

#: A URL we are willing to write into an attribute: https only, and none of
#: the characters that could break out of the attribute or smuggle a second
#: one. Cloudinary and Z.ai URLs are both comfortably inside this.
_SAFE_URL_RE = re.compile(r'^https://[^\s"\'<>\\`]+$')

#: Hero-section identifiers the generator and the pre-built templates use.
_HERO_IDS = ("home", "hero", "utama", "laman-utama", "main-hero")

#: Elements that can plausibly BE the hero. <div> is last on purpose: a
#: generated page wraps everything in divs, so it only wins by id/class.
_HERO_TAGS = ("section", "header", "div")

_BODY_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)
_HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)


@dataclass
class HeroVideoSettings:
    """Everything the patch needs, already validated."""

    video_url: str
    poster_url: Optional[str] = None
    overlay: str = DEFAULT_OVERLAY
    overlay_opacity: float = DEFAULT_OVERLAY_OPACITY
    text_mode: str = DEFAULT_TEXT_MODE
    #: False → phones get the still poster instead of the video (data saver).
    show_on_mobile: bool = True

    def resolved_text_mode(self) -> str:
        """``auto`` reads the scrim: dark scrim → light text, and vice versa."""
        if self.text_mode != "auto":
            return self.text_mode
        if self.overlay == "dark":
            return "light"
        if self.overlay == "light":
            return "dark"
        return "keep"

    def as_dict(self) -> Dict:
        return {
            "video_url": self.video_url,
            "poster_url": self.poster_url,
            "overlay": self.overlay,
            "overlay_opacity": self.overlay_opacity,
            "text_mode": self.text_mode,
            "show_on_mobile": self.show_on_mobile,
        }


@dataclass
class HeroVideoResult:
    """What a patch did, for the endpoint's response and the logs."""

    html: str
    changed: bool
    #: How the hero was found: "id", "class", "first-section" or "" (missing).
    hero_match: str = ""
    settings: Optional[Dict] = None
    notes: List[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.changed:
            return "no change"
        return f"hero matched by {self.hero_match or 'unknown'}"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def is_safe_media_url(url: Optional[str]) -> bool:
    """True for an https URL safe to embed in an HTML attribute."""
    return bool(url) and bool(_SAFE_URL_RE.match(url.strip()))


def clamp_opacity(value: Optional[float]) -> float:
    """Keep the scrim inside a range that stays readable and stays visible."""
    if value is None:
        return DEFAULT_OVERLAY_OPACITY
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return DEFAULT_OVERLAY_OPACITY
    return round(min(max(numeric, 0.0), 0.9), 2)


def build_settings(
    *,
    video_url: str,
    poster_url: Optional[str] = None,
    overlay: Optional[str] = None,
    overlay_opacity: Optional[float] = None,
    text_mode: Optional[str] = None,
    show_on_mobile: Optional[bool] = None,
) -> HeroVideoSettings:
    """Normalise raw request values into settings. Raises ValueError on a
    video URL we refuse to embed; every other field falls back to a default
    rather than failing the whole edit."""
    clean_video = (video_url or "").strip()
    if not is_safe_media_url(clean_video):
        raise ValueError("video_url must be an https URL")

    clean_poster = (poster_url or "").strip() or None
    if clean_poster and not is_safe_media_url(clean_poster):
        clean_poster = None

    mode = (overlay or DEFAULT_OVERLAY).strip().lower()
    if mode not in OVERLAY_MODES:
        mode = DEFAULT_OVERLAY

    text = (text_mode or DEFAULT_TEXT_MODE).strip().lower()
    if text not in TEXT_MODES:
        text = DEFAULT_TEXT_MODE

    return HeroVideoSettings(
        video_url=clean_video,
        poster_url=clean_poster,
        overlay=mode,
        overlay_opacity=clamp_opacity(overlay_opacity),
        text_mode=text,
        show_on_mobile=True if show_on_mobile is None else bool(show_on_mobile),
    )


# ---------------------------------------------------------------------------
# Finding the hero
# ---------------------------------------------------------------------------

def _iter_open_tags(html: str, start: int):
    """Yield (match, tag_name) for every hero-candidate opening tag."""
    pattern = re.compile(
        r"<(" + "|".join(_HERO_TAGS) + r")\b[^>]*>", re.IGNORECASE
    )
    for match in pattern.finditer(html, start):
        yield match, match.group(1).lower()


def find_hero_open_tag(html: str) -> Tuple[Optional[re.Match], str]:
    """Locate the hero's opening tag.

    Three passes, strongest signal first:
      1. ``id="home"`` / ``id="hero"`` — what the pre-built templates emit and
         what generated nav anchors point at;
      2. a class containing ``hero`` as a whole word;
      3. the first ``<section>`` in the body — the generator is told to put
         the hero first.
    Returns (match, how) where *how* is "", "id", "class" or "first-section".
    """
    body = _BODY_RE.search(html)
    start = body.end() if body else 0

    id_re = re.compile(
        r'\bid=["\'](?:' + "|".join(_HERO_IDS) + r')["\']', re.IGNORECASE
    )
    class_re = re.compile(r'\bclass=["\'][^"\']*\bhero\b[^"\']*["\']', re.IGNORECASE)

    first_section: Optional[re.Match] = None
    class_hit: Optional[re.Match] = None

    for match, tag in _iter_open_tags(html, start):
        open_tag = match.group(0)
        if id_re.search(open_tag):
            return match, "id"
        if class_hit is None and class_re.search(open_tag):
            class_hit = match
        if first_section is None and tag == "section":
            first_section = match

    if class_hit is not None:
        return class_hit, "class"
    if first_section is not None:
        return first_section, "first-section"
    return None, ""


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

_LAYER_RE = re.compile(
    r'<div\b[^>]*\bclass=["\']binaapp-hero-video-layer["\'][^>]*>',
    re.IGNORECASE,
)


def _read_attr(tag: str, name: str) -> Optional[str]:
    match = re.search(
        r'\b' + re.escape(name) + r'=["\']([^"\']*)["\']', tag, re.IGNORECASE
    )
    return html_lib.unescape(match.group(1)) if match else None


def detect_hero_video(html: str) -> Optional[Dict]:
    """The video background currently on the page, or None.

    Read back from the data-attributes the patch writes, so the stored HTML
    stays the single source of truth — there is no parallel DB column to
    drift out of sync with what visitors actually see.
    """
    if not html:
        return None
    layer = _LAYER_RE.search(html)
    if not layer:
        return None
    tag = layer.group(0)
    video_url = _read_attr(tag, "data-binaapp-video-url")
    if not video_url:
        return None
    opacity = _read_attr(tag, "data-binaapp-overlay-opacity")
    mobile = (_read_attr(tag, "data-binaapp-mobile") or "video").lower()
    return {
        "video_url": video_url,
        "poster_url": _read_attr(tag, "data-binaapp-poster-url") or None,
        "overlay": (_read_attr(tag, "data-binaapp-overlay") or DEFAULT_OVERLAY).lower(),
        "overlay_opacity": clamp_opacity(opacity) if opacity else DEFAULT_OVERLAY_OPACITY,
        "text_mode": (_read_attr(tag, "data-binaapp-text-mode") or DEFAULT_TEXT_MODE).lower(),
        "show_on_mobile": mobile != "poster",
    }


# ---------------------------------------------------------------------------
# Markup + CSS
# ---------------------------------------------------------------------------

def _esc(value: str) -> str:
    return html_lib.escape(value, quote=True)


def _build_layer(settings: HeroVideoSettings) -> str:
    poster_attr = f' poster="{_esc(settings.poster_url)}"' if settings.poster_url else ""
    poster_style = (
        f" style=\"background-image:url('{_esc(settings.poster_url)}')\""
        if settings.poster_url
        else ""
    )
    video_url = _esc(settings.video_url)
    return (
        f"{BLOCK_START}"
        f'<div class="binaapp-hero-video-layer" aria-hidden="true"'
        f' data-binaapp-video-url="{video_url}"'
        + (
            f' data-binaapp-poster-url="{_esc(settings.poster_url)}"'
            if settings.poster_url
            else ""
        )
        + f' data-binaapp-overlay="{settings.overlay}"'
        f' data-binaapp-overlay-opacity="{settings.overlay_opacity}"'
        f' data-binaapp-text-mode="{settings.text_mode}"'
        f' data-binaapp-mobile="{"video" if settings.show_on_mobile else "poster"}"'
        f"{poster_style}>"
        f'<video class="binaapp-hero-video" autoplay muted loop playsinline'
        f' preload="metadata" disablepictureinpicture tabindex="-1"'
        f'{poster_attr}>'
        f'<source src="{video_url}" type="video/mp4">'
        f"</video>"
        f'<div class="binaapp-hero-video-scrim"></div>'
        f"</div>"
        f"{BLOCK_END}"
    )


_TEXT_ELEMENTS = ("h1", "h2", "h3", "h4", "p", "li", "blockquote")


def _build_style(settings: HeroVideoSettings) -> str:
    hero = f"[{HERO_MARKER_ATTR}]"
    opacity = settings.overlay_opacity

    if settings.overlay == "dark":
        scrim = (
            f"background:linear-gradient(180deg,rgba(0,0,0,{opacity}) 0%,"
            f"rgba(0,0,0,{min(round(opacity + 0.15, 2), 0.95)}) 100%);"
        )
    elif settings.overlay == "light":
        scrim = (
            f"background:linear-gradient(180deg,rgba(255,255,255,{opacity}) 0%,"
            f"rgba(255,255,255,{min(round(opacity + 0.15, 2), 0.95)}) 100%);"
        )
    else:
        scrim = "background:transparent;"

    rules = [
        # The hero becomes the positioning context. `isolation` keeps the new
        # stacking context local so nothing outside the hero is reordered.
        f"{hero}{{position:relative;isolation:isolate;overflow:hidden;}}",
        f"{hero} > .binaapp-hero-video-layer{{position:absolute;inset:0;"
        "z-index:0;pointer-events:none;background-size:cover;"
        "background-position:center;background-repeat:no-repeat;}",
        f"{hero} > .binaapp-hero-video-layer .binaapp-hero-video{{position:absolute;"
        "inset:0;width:100%;height:100%;object-fit:cover;border:0;"
        "pointer-events:none;}",
        f"{hero} > .binaapp-hero-video-layer .binaapp-hero-video-scrim{{"
        f"position:absolute;inset:0;{scrim}}}",
        # Lift the hero's own children above the layer. Only DIRECT children
        # are touched, so nothing inside the merchant's markup is restacked.
        f"{hero} > *:not(.binaapp-hero-video-layer){{position:relative;z-index:1;}}",
    ]

    text_mode = settings.resolved_text_mode()
    if text_mode in ("light", "dark"):
        colour = "#FFFFFF" if text_mode == "light" else "#0F172A"
        selectors = ",".join(f"{hero} {tag}" for tag in _TEXT_ELEMENTS)
        # !important because generated pages set the colour with a Tailwind
        # arbitrary value on the element itself. Links and buttons are left
        # alone on purpose — they carry the brand colour and their own
        # background, so they stay readable and stay branded.
        rules.append(f"{selectors}{{color:{colour} !important;}}")
        if text_mode == "light":
            rules.append(
                f"{hero} .binaapp-hero-video-layer ~ * "
                "{text-shadow:0 1px 12px rgba(0,0,0,0.35);}"
            )

    # Motion behind text is precisely what this setting is for: hold the
    # poster frame still instead.
    rules.append(
        "@media (prefers-reduced-motion:reduce){"
        f"{hero} > .binaapp-hero-video-layer .binaapp-hero-video{{display:none;}}}}"
    )
    if not settings.show_on_mobile:
        rules.append(
            "@media (max-width:640px){"
            f"{hero} > .binaapp-hero-video-layer .binaapp-hero-video{{display:none;}}}}"
        )

    return f'<style id="{STYLE_ID}">' + "".join(rules) + "</style>"


# ---------------------------------------------------------------------------
# Patch entry points
# ---------------------------------------------------------------------------

def remove_hero_video(html: str) -> HeroVideoResult:
    """Strip the injected block, its stylesheet and the hero marker.

    Returns the document byte-identical to its pre-patch state (the patch
    only ever adds; nothing merchant-authored is rewritten).
    """
    if not html:
        return HeroVideoResult(html=html or "", changed=False)

    stripped = _BLOCK_RE.sub("", html)
    stripped = _STYLE_RE.sub("", stripped)
    stripped = _MARKER_ATTR_RE.sub("", stripped)
    return HeroVideoResult(html=stripped, changed=stripped != html)


def apply_hero_video(html: str, settings: HeroVideoSettings) -> HeroVideoResult:
    """Put (or re-put) a video background behind the hero.

    Idempotent: any existing block is removed first, so changing the overlay
    replaces the layer rather than stacking a second one.
    """
    if not html or not html.strip():
        return HeroVideoResult(
            html=html or "",
            changed=False,
            notes=["empty_html"],
        )

    base = remove_hero_video(html).html
    hero, how = find_hero_open_tag(base)
    if hero is None:
        return HeroVideoResult(html=html, changed=False, notes=["hero_not_found"])

    open_tag = hero.group(0)
    # Write the marker onto the hero's opening tag, before its ">" (or "/>"
    # — self-closing would mean we picked a void element, which the tag list
    # already rules out, but the slice is written to survive it).
    insert_at = len(open_tag) - 1
    if open_tag[insert_at - 1] == "/":
        insert_at -= 1
    marked_tag = (
        open_tag[:insert_at] + f' {HERO_MARKER_ATTR}="1"' + open_tag[insert_at:]
    )

    layer = _build_layer(settings)
    patched = (
        base[: hero.start()] + marked_tag + layer + base[hero.end():]
    )

    style = _build_style(settings)
    head_close = _HEAD_CLOSE_RE.search(patched)
    notes: List[str] = []
    if head_close:
        patched = (
            patched[: head_close.start()] + style + patched[head_close.start():]
        )
    else:
        # No </head> (a fragment, or a truncated document): put the rules
        # immediately before the layer so they still reach the browser.
        notes.append("style_inlined_without_head")
        patched = patched.replace(layer, style + layer, 1)

    logger.info(
        "[hero-video] injected (hero matched by %s, overlay=%s/%.2f, mobile=%s)",
        how,
        settings.overlay,
        settings.overlay_opacity,
        "video" if settings.show_on_mobile else "poster",
    )
    return HeroVideoResult(
        html=patched,
        changed=True,
        hero_match=how,
        settings=settings.as_dict(),
        notes=notes,
    )
