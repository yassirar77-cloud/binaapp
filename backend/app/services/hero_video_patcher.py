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
      <script>…playback bootstrap: force muted, play() now + on first touch…</script>
      <div class="binaapp-hero-video-scrim"></div>
    </div>
    <!--/binaapp:hero-video-->

plus a ``<style id="binaapp-hero-video-style">`` block in ``<head>``, and a
``data-binaapp-hero-video`` marker attribute on the hero element itself (the
only CSS hook — the rules never depend on the merchant's own class names).

SAFETY RULES
------------
* The layer is ``position:absolute; inset:0; z-index:-1`` INSIDE the hero,
  which gets ``isolation:isolate`` so that negative z-index stays local: the
  clip paints above the hero's own background and below every one of its
  children. The children themselves are never restyled — no re-ordering,
  no unwrapping, no forced ``position``. (Forcing ``position:relative`` on
  them, as an earlier version did, turned absolutely-positioned decorative
  blobs into in-flow blocks that pushed the hero copy off-screen.)
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


#: Cloudinary delivery transformation applied to every hero clip URL.
#:
#: The provider's MP4 is far too heavy for a background. wan3.0-video
#: returned 12.9 MB for a five-second 1108×832 clip — 20.7 Mbit/s — so every
#: visitor downloaded all of it before a single frame moved, and on a phone
#: the hero sat on the poster for the whole visit. The merchant, whose poster
#: is their own photo, saw "no video". The same asset through this transform
#: is ~620 KB, at a quality nobody can tell apart behind a text scrim.
#:
#:   q_auto:eco     perceptual quality tuned for size
#:   w_1280,c_limit cap width at the hero's display size, never upscale
#:   ac_none        drop any audio track (the clip plays muted regardless)
HERO_VIDEO_DELIVERY_TRANSFORM = "q_auto:eco,w_1280,c_limit,ac_none"

_CLOUDINARY_VIDEO_UPLOAD_RE = re.compile(
    r"^(https://res\.cloudinary\.com/[^/]+/video/upload/)(.+)$"
)
#: Cloudinary transformation parameters are short letter codes followed by
#: an underscore (q_, w_, c_, ac_, br_, e_, so_ …). A version marker (v1789…)
#: or a folder name (binaapp) is not one.
_CLOUDINARY_TRANSFORM_SEGMENT_RE = re.compile(r"^[a-z]{1,3}_")


def hero_video_delivery_url(url: Optional[str]) -> Optional[str]:
    """The URL the page should embed for a stored hero clip: the Cloudinary
    asset with HERO_VIDEO_DELIVERY_TRANSFORM inserted after ``/video/upload/``.

    Idempotent — a URL that already carries a transformation segment comes
    back unchanged — and a no-op for anything that is not a Cloudinary video
    upload URL, so a merchant-supplied or legacy URL is never mangled.
    """
    if not url:
        return url
    match = _CLOUDINARY_VIDEO_UPLOAD_RE.match(url.strip())
    if not match:
        return url
    head, rest = match.groups()
    first = rest.split("/", 1)[0]
    if "," in first or _CLOUDINARY_TRANSFORM_SEGMENT_RE.match(first):
        return url
    return f"{head}{HERO_VIDEO_DELIVERY_TRANSFORM}/{rest}"


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
    # Normalised here as well as at store time so a page that was patched
    # with the raw 12.9 MB asset picks up the slim delivery URL the next
    # time its look is adjusted, without the merchant regenerating.
    clean_video = hero_video_delivery_url(clean_video)

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
        f' preload="auto" disablepictureinpicture tabindex="-1"'
        f'{poster_attr}>'
        f'<source src="{video_url}" type="video/mp4">'
        f"</video>"
        f'<div class="binaapp-hero-video-scrim"></div>'
        f"{PLAYBACK_BOOTSTRAP}"
        f"</div>"
        f"{BLOCK_END}"
    )


#: Inline playback bootstrap, emitted inside the layer so the comment fence
#: still removes it byte-exactly. The HTML attributes alone are not enough on
#: every phone: some Android/Samsung browsers and iOS Low Power Mode refuse
#: the initial autoplay and just sit on the poster, and a few browsers ignore
#: the ``muted`` attribute until the property is set from script (autoplay is
#: only ever allowed for muted media). So: force muted, call play() at once,
#: and call it again on the first touch/scroll/key and whenever the tab comes
#: back — each of those is a user gesture or visibility change the autoplay
#: policy accepts. Honours prefers-reduced-motion (the CSS hides the video
#: there; we simply do not try to play it). Stamps
#: ``data-binaapp-video-playing`` on the hero once frames are really moving,
#: so "is it playing?" can be answered from the page itself.
PLAYBACK_BOOTSTRAP = (
    "<script>(function(){"
    "var s=document.currentScript,l=s&&s.parentNode,v=l&&l.querySelector('video.binaapp-hero-video');"
    "if(!v)return;"
    "if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;"
    "v.muted=true;v.defaultMuted=true;v.setAttribute('muted','');"
    "var h=l.parentNode;"
    "v.addEventListener('playing',function(){if(h&&h.setAttribute)h.setAttribute('data-binaapp-video-playing','1');});"
    "function go(){try{var p=v.play();if(p&&p.catch)p.catch(function(){});}catch(e){}}"
    "go();"
    "['touchstart','pointerdown','scroll','keydown'].forEach(function(t){"
    "window.addEventListener(t,go,{once:true,passive:true});});"
    "document.addEventListener('visibilitychange',function(){if(!document.hidden)go();});"
    "if(v.readyState<2){v.addEventListener('loadeddata',go,{once:true});}"
    "})();</script>"
)


_TEXT_ELEMENTS = ("h1", "h2", "h3", "h4", "p", "li", "blockquote")


def _css_string(value: str) -> str:
    """A URL as the body of a double-quoted CSS attribute-selector string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


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
        # z-index:-1 INSIDE the hero's own stacking context (isolation:isolate
        # above) paints the layer above the hero's background and below every
        # one of its children — without touching those children at all. The
        # earlier approach (force children to position:relative; z-index:1)
        # broke heroes whose decorative blobs are absolutely positioned: they
        # became in-flow blocks and shoved the real content down the page.
        f"{hero} > .binaapp-hero-video-layer{{position:absolute;inset:0;"
        "z-index:-1;pointer-events:none;background-size:cover;"
        "background-position:center;background-repeat:no-repeat;}",
        f"{hero} > .binaapp-hero-video-layer .binaapp-hero-video{{position:absolute;"
        "inset:0;width:100%;height:100%;object-fit:cover;border:0;"
        "pointer-events:none;}",
        f"{hero} > .binaapp-hero-video-layer .binaapp-hero-video-scrim{{"
        f"position:absolute;inset:0;{scrim}}}",
    ]

    if settings.poster_url:
        # ONE hero visual, not two. When the clip was animated from the
        # merchant's own hero photo, that photo is the poster — and it is
        # also still on the page as the hero's <img> (or a background
        # div), now painted on top of its own moving version: a cut-out
        # of the whale over the video of the whale (ikan, 14:00). Hide
        # the hero's copy while the layer is present; the layer shows the
        # same photo as its poster whenever the video is not playing, so
        # nothing is lost. A clip-frame poster never appears in the
        # merchant's markup, so for text-to-video this matches nothing.
        photo = _css_string(settings.poster_url)
        rules.append(f'{hero} img[src="{photo}"]{{display:none !important;}}')
        rules.append(
            f'{hero} [style*="{photo}"]:not(.binaapp-hero-video-layer)'
            "{background-image:none !important;}"
        )

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

#: The stacking rule the first release emitted. It forced every direct child
#: of the hero to ``position:relative`` so it would sit above a ``z-index:0``
#: layer — which turned absolutely-positioned decorative blobs into in-flow
#: blocks and pushed the hero copy below the fold. Pages still carrying it
#: are re-applied with the current CSS on their next owner visit.
LEGACY_CHILD_RULE = (
    f"[{HERO_MARKER_ATTR}] > *:not(.binaapp-hero-video-layer)"
    "{position:relative;z-index:1;}"
)


def needs_style_upgrade(html: str) -> bool:
    """True when the page has a hero video whose injected markup predates
    the current release: the child-restyling CSS (LEGACY_CHILD_RULE) or a
    layer without the playback bootstrap. False for pages without a video
    and for pages already on the current output."""
    if not html:
        return False
    style = _STYLE_RE.search(html)
    if not style:
        return False
    if LEGACY_CHILD_RULE in style.group(0):
        return True
    # Second generation: the block exists but predates the playback
    # bootstrap (poster-only on phones that refuse the initial autoplay).
    block = _BLOCK_RE.search(html)
    if not block:
        return False
    if "v.play()" not in block.group(0):
        return True
    # Third generation: a poster is set but the hero's own copy of that
    # photo is not hidden — the page shows the visual twice.
    current = detect_hero_video(html)
    return bool(current and current.get("poster_url")) and " img[src=" not in style.group(0)


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
