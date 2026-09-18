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
  clip paints above the hero's own background and below every IN-FLOW child
  — the copy is never covered, whether or not the generator positioned it.
  The children themselves are never restyled — no re-ordering, no
  unwrapping, no forced ``position``. (Forcing ``position:relative`` on
  them, as an earlier version did, turned absolutely-positioned decorative
  blobs into in-flow blocks that pushed the hero copy off-screen.)
* The one thing a negative z-index does NOT paint above is a POSITIONED
  sibling with ``z-index:auto`` — and that is exactly what the generator
  makes the hero's own photo: ``<div class="absolute inset-0"><img …>``.
  On soon.binaapp.my that div sat on top of the running video and hid it
  completely, while the page reported the video as playing. So the patch
  finds the hero's full-cover media container at injection time, stamps it
  ``data-binaapp-hero-media="replaced"``, and hides it with one static
  rule. Matching by URL was tried first and failed: the rule keyed on the
  POSTER url, the element carried the HERO IMAGE url, and Cloudinary
  rewrites the transformation segment at delivery anyway.
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

from app.services.color_tone import (
    alpha_over,
    css_variables,
    inherited_text_tone,
    rule_text_tone,
    rule_tint,
    stylesheet_rules,
    text_tone,
    tint,
)
from app.utils.html_scan import (
    direct_children,
    element_end,
    open_tag_end,
    read_attr,
    tag_classes,
)

logger = logging.getLogger(__name__)

#: Marker attribute written onto the hero element. Every injected CSS rule is
#: scoped to it, so nothing in this module depends on the merchant's classes.
HERO_MARKER_ATTR = "data-binaapp-hero-video"
#: id of the injected <style> block, so a re-apply replaces rather than stacks.
STYLE_ID = "binaapp-hero-video-style"
#: Comment fence around the injected markup — exact, nesting-proof removal.
BLOCK_START = "<!--binaapp:hero-video-->"
BLOCK_END = "<!--/binaapp:hero-video-->"
#: Written onto the hero's own background-media element (the ``absolute
#: inset-0`` photo wrapper, or a full-cover <img>) so a static rule can hide
#: it while the video layer is present. Stripped again by remove().
HERO_MEDIA_ATTR = "data-binaapp-hero-media"
HERO_MEDIA_REPLACED = "replaced"
#: The same thing inside a HOST. A hosted clip is positioned against the
#: frame the photo sat in, so hiding that photo with ``display:none``
#: collapsed the frame to nothing and the clip had no box to fill (mimk:
#: `div.hero-photo-anim > img.aspect-[16/9]`, the only thing giving the
#: column its height). Hosted media keeps its box and gives up only its
#: pixels.
HERO_MEDIA_REPLACED_HOSTED = "replaced-hosted"
#: The wrapper the video is hosted IN when the hero's photo occupies a
#: distinct region rather than the whole section — a split hero's media
#: column, a framed card. The clip replaces the photo in place and the
#: layout the merchant asked for survives (maka: "split, model photo on the
#: right" must not become "full-bleed video with a dead column").
HERO_MEDIA_HOST = "host"
#: Stamped AT RUNTIME by the playback bootstrap on any hero element that
#: paints an opaque background of its own (and its descendants), so the
#: text-recolour rules leave it alone. A class-name test cannot see a
#: background set in the page's own <style>: `.btn-whatsapp{background:
#: #CE3560;color:#fff}` carries no "bg-" and no inline style, and the
#: forced navy text on that pink pill was 3.66:1 (bji). "Opaque" means at
#: least half: a `bg-white/10` pill is a tenth of a veil, its label sits on
#: whatever is behind it, and it needs the scrim's colour like any other.
KEEP_COLOR_ATTR = "data-binaapp-keep-color"

#: Overlay presets: the scrim painted between the video and the hero copy.
#: Without one, white hero text over a bright frame is unreadable.
#: ``auto`` reads the page: a dark page gets a dark scrim and light text, a
#: light page (Cerah) a light scrim and its own dark text — instead of every
#: hero becoming a heavy dark block on a cream, minimal site (maka).
OVERLAY_MODES = ("auto", "dark", "light", "none")
#: How the hero's own text colour is handled once a video sits behind it.
TEXT_MODES = ("auto", "light", "dark", "keep")

#: Playback speed as a multiple of the clip's own rate. 1.0 is the clip as
#: generated; below it is the "slow motion" a merchant asks for when steam
#: or a pour moves too fast; above it lifts a sluggish pan. Applied by the
#: playback bootstrap (``playbackRate``), so it costs nothing: no new clip,
#: no re-encode, the same bytes every visitor already downloads.
SPEED_CHOICES = (0.5, 0.75, 1.0, 1.25, 1.5)
DEFAULT_SPEED = 1.0
MIN_SPEED = 0.25
MAX_SPEED = 2.0

#: Colour looks painted over the clip with a CSS ``filter``. Credit-free
#: for the same reason as the scrim: the clip is reused, only the rules
#: change. ``scale`` is set on the looks that blur, because a blurred
#: edge lets the hero's own background bleed in as a soft fringe and a
#: few percent of overscan hides it.
VIDEO_EFFECTS: Dict[str, Dict[str, object]] = {
    "none": {"label_ms": "Asli", "label_en": "Original", "css": "", "scale": 1.0},
    "warm": {
        "label_ms": "Hangat",
        "label_en": "Warm",
        "css": "sepia(0.25) saturate(1.2) brightness(1.02)",
        "scale": 1.0,
    },
    "cool": {
        "label_ms": "Sejuk",
        "label_en": "Cool",
        "css": "saturate(0.9) hue-rotate(-12deg) brightness(1.02)",
        "scale": 1.0,
    },
    "vivid": {
        "label_ms": "Terang",
        "label_en": "Vivid",
        "css": "saturate(1.45) contrast(1.08)",
        "scale": 1.0,
    },
    "mono": {
        "label_ms": "Hitam putih",
        "label_en": "Black & white",
        "css": "grayscale(1) contrast(1.05)",
        "scale": 1.0,
    },
    "vintage": {
        "label_ms": "Retro",
        "label_en": "Vintage",
        "css": "sepia(0.55) contrast(0.92) brightness(0.95) saturate(1.1)",
        "scale": 1.0,
    },
    "dreamy": {
        "label_ms": "Lembut",
        "label_en": "Dreamy",
        "css": "blur(2px) brightness(1.05) saturate(1.1)",
        "scale": 1.05,
    },
}
DEFAULT_EFFECT = "none"

DEFAULT_OVERLAY = "auto"
DEFAULT_OVERLAY_OPACITY = 0.45
DEFAULT_TEXT_MODE = "auto"

#: Scrim strength from the clip's own first-frame luminance, per scrim
#: colour. A DARK scrim must get heavier over bright footage (white text
#: on a bright frame). A LIGHT scrim is the opposite: dark text on bright
#: footage is readable already, so a bright clip needs LESS white — the
#: 0.52 white veil that hid bji's flowers came from applying the dark
#: map to a light scrim. Endpoints are (luminance, opacity).
DARK_SCRIM_MAP = ((0.20, 0.35), (0.75, 0.70))
LIGHT_SCRIM_MAP = ((0.20, 0.50), (0.75, 0.25))

#: A first frame at or below this luminance is a DARK clip: a white scrim
#: over it produces the flat grey smear mimk shipped (poster_luminance
#: 0.264 under a 0.47→0.62 white veil), not a video. At or above
#: LIGHT_CLIP_MIN it is a bright clip. Between the two the clip states no
#: opinion. Same thresholds colour_tone sorts colours by, so a frame and a
#: hex cannot disagree about the same brightness.
DARK_CLIP_MAX_LUMINANCE = 0.35
LIGHT_CLIP_MIN_LUMINANCE = 0.60


def opacity_for(overlay: str, luminance: Optional[float]) -> float:
    """Scrim opacity for a resolved overlay colour and a measured luminance.

    None luminance → the historical fixed default. Linear between the two
    anchors, clamped outside them.
    """
    if luminance is None:
        return DEFAULT_OVERLAY_OPACITY
    lo, hi = LIGHT_SCRIM_MAP if overlay == "light" else DARK_SCRIM_MAP
    lum = min(max(float(luminance), 0.0), 1.0)
    if lum <= lo[0]:
        return lo[1]
    if lum >= hi[0]:
        return hi[1]
    t = (lum - lo[0]) / (hi[0] - lo[0])
    return round(lo[1] + t * (hi[1] - lo[1]), 2)

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
_MEDIA_ATTR_RE = re.compile(
    r'\s+' + re.escape(HERO_MEDIA_ATTR) + r'(?![\w-])'
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
    #: None = choose from poster_luminance per the resolved scrim colour at
    #: apply time. A number is the merchant's explicit choice, used as-is.
    overlay_opacity: Optional[float] = None
    #: Mean luminance of the clip's first frame, 0..1, measured once when
    #: the clip is stored. Kept on the layer so a re-apply (theme change,
    #: overlay change) can re-derive the opacity for the NEW scrim colour.
    poster_luminance: Optional[float] = None
    text_mode: str = DEFAULT_TEXT_MODE
    #: False → phones get the still poster instead of the video (data saver).
    show_on_mobile: bool = True
    #: ``playbackRate`` for the clip, 1.0 = as generated. See SPEED_CHOICES.
    speed: float = DEFAULT_SPEED
    #: A VIDEO_EFFECTS key: the CSS colour look painted over the clip.
    effect: str = DEFAULT_EFFECT

    def resolved_overlay(self, page_html: str = "") -> str:
        """``auto`` → ``dark`` or ``light`` from what the HERO paints.

        The hero is what the scrim sits in, and it is not always the page: a
        Cerah site can carry a dark editorial hero, and resolving that one
        from the page theme produced a white veil under the hero's own black
        gradient, with its white headline forced to navy (Run 1 site A). The
        page's background is the fallback for a hero that states nothing, and
        dark is the fallback for a page that states nothing.
        """
        if self.overlay != "auto":
            return self.overlay
        try:
            tone = detect_hero_tone(page_html) if page_html else ""
        except Exception:  # pragma: no cover - a guard must never take the patch down
            tone = ""
        choice = tone if tone in ("dark", "light") else ""
        if not choice:
            try:
                from app.services.color_mode_guard import detect_color_mode
                mode = detect_color_mode(page_html) if page_html else ""
            except Exception:  # pragma: no cover - a guard must never take the patch down
                mode = ""
            choice = mode if mode in ("dark", "light") else ""
        if not choice:
            # Neither the hero nor the page states a colour. The CLIP does:
            # a dark first frame under a white veil is the flat grey smear
            # mimk shipped. The scrim follows the footage rather than a
            # blanket default. It is consulted only here, below both page
            # signals: a dark clip on a genuinely light page still needs the
            # light scrim, because that is what keeps dark copy readable.
            choice = self.clip_tone()
        return self._sanity_checked(choice or "dark", page_html)

    def clip_tone(self) -> str:
        """What the CLIP ITSELF is: "dark", "light" or "" (unmeasured or
        mid-tone). Measured from the first frame when the clip was stored."""
        if self.poster_luminance is None:
            return ""
        if self.poster_luminance <= DARK_CLIP_MAX_LUMINANCE:
            return "dark"
        if self.poster_luminance >= LIGHT_CLIP_MIN_LUMINANCE:
            return "light"
        return ""

    def _sanity_checked(self, overlay: str, page_html: str) -> str:
        """Refuse a scrim the same colour as the copy that sits on it.

        A white veil under near-white copy, or a black one under near-black
        copy, is not a weaker version of the right answer — it is the copy
        made unreadable. It means the signals disagreed (the hero was read
        from its background while its text says the opposite), and no scrim
        at all is better than one that hides the words. The clip's own
        luminance decides nothing here; only the contradiction does.
        """
        if overlay not in ("dark", "light") or not page_html:
            return overlay
        try:
            copy = hero_copy_tone(page_html)
        except Exception:  # pragma: no cover - a guard must never take the patch down
            return overlay
        if copy and copy == overlay:
            logger.warning(
                "[hero-video] auto scrim resolved to %s over %s hero copy — "
                "self-contradictory, using no scrim instead",
                overlay, copy,
            )
            return "none"
        return overlay

    def resolved_opacity(self, page_html: str = "") -> float:
        """The scrim strength to paint: explicit, else from luminance for
        the scrim colour this page resolves to."""
        if self.overlay_opacity is not None:
            return self.overlay_opacity
        return opacity_for(self.resolved_overlay(page_html), self.poster_luminance)

    def resolved_text_mode(self, page_html: str = "") -> str:
        """Whether the hero's copy is recoloured, and to what.

        The default is to leave it alone. An ``auto`` scrim is chosen to match
        what the hero already paints, so the copy that was designed for that
        hero is readable on it by construction — and recolouring it anyway is
        what turned a white CTA label navy and inverted a whole hero. The
        recolour is kept for the one case that needs it: a merchant who picked
        a scrim colour that fights their own hero.
        """
        if self.text_mode != "auto":
            return self.text_mode
        overlay = self.resolved_overlay(page_html)
        if overlay not in ("dark", "light"):
            return "keep"
        if self.overlay == "auto":
            return "keep"
        tone = ""
        try:
            tone = detect_hero_tone(page_html) if page_html else ""
        except Exception:  # pragma: no cover - a guard must never take the patch down
            tone = ""
        if tone == overlay:
            # The hero already reads this way; its copy suits the scrim.
            return "keep"
        return "light" if overlay == "dark" else "dark"

    def as_dict(self) -> Dict:
        return {
            "video_url": self.video_url,
            "poster_url": self.poster_url,
            "overlay": self.overlay,
            "overlay_opacity": self.overlay_opacity,
            "poster_luminance": self.poster_luminance,
            "text_mode": self.text_mode,
            "show_on_mobile": self.show_on_mobile,
            "speed": self.speed,
            "effect": self.effect,
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
#:   q_auto:good    perceptual quality, the tier that keeps gradients clean
#:   w_1920,c_limit cap width at a retina hero, never upscale
#:   ac_none        drop any audio track (the clip plays muted regardless)
#:
#: This was ``q_auto:eco,w_1280`` and that was too far. eco is Cloudinary's
#: most aggressive tier, and a dark interior full of smooth gradients — a
#: barbershop at night, mimk — came back banded and mushy, then got stretched
#: across a full-bleed hero on a retina phone. good at 1920 is the same clip
#: at roughly 1.5–2× the bytes, still a fraction of the 12.9 MB source, and
#: c_limit means a 720p master is served at 720p rather than upscaled.
#: HERO_VIDEO_DELIVERY_TRANSFORM (env) overrides the whole string.
DEFAULT_HERO_VIDEO_DELIVERY_TRANSFORM = "q_auto:good,w_1920,c_limit,ac_none"

#: Transforms BinaApp itself wrote into stored URLs in earlier releases. A
#: URL carrying one is ours to re-cut: without this an eco/1280 page would
#: keep serving eco/1280 forever, because the URL already has a
#: transformation segment and the normaliser leaves those alone.
LEGACY_HERO_VIDEO_DELIVERY_TRANSFORMS = ("q_auto:eco,w_1280,c_limit,ac_none",)


def hero_video_delivery_transform() -> str:
    """The Cloudinary transformation every hero clip is delivered through.
    Read per call so the env var takes effect without a redeploy."""
    import os

    value = (os.getenv("HERO_VIDEO_DELIVERY_TRANSFORM") or "").strip()
    return value or DEFAULT_HERO_VIDEO_DELIVERY_TRANSFORM


#: Back-compat name for callers (and tests) that read the constant.
HERO_VIDEO_DELIVERY_TRANSFORM = DEFAULT_HERO_VIDEO_DELIVERY_TRANSFORM

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
    transform = hero_video_delivery_transform()
    first = rest.split("/", 1)[0]
    if first == transform:
        return url
    if first in LEGACY_HERO_VIDEO_DELIVERY_TRANSFORMS:
        # Ours, from an earlier release: re-cut it at the current quality.
        return f"{head}{transform}/{rest.split('/', 1)[1]}"
    if "," in first or _CLOUDINARY_TRANSFORM_SEGMENT_RE.match(first):
        return url
    return f"{head}{transform}/{rest}"


#: Cloudinary flag that makes the response a download (Content-Disposition:
#: attachment) instead of an inline play.
_ATTACHMENT_FLAG = "fl_attachment"


def hero_video_download_url(url: Optional[str]) -> Optional[str]:
    """A link that SAVES the stored clip instead of playing it, for the
    merchant to post as a WhatsApp status, a Reel or a TikTok.

    The delivery URL with ``fl_attachment`` added to its transformation
    segment (or as a new segment when it has none). Idempotent; a URL that
    is not a Cloudinary video upload comes back unchanged, so a legacy or
    merchant-supplied clip still gets a link that at least plays.
    """
    if not url:
        return url
    match = _CLOUDINARY_VIDEO_UPLOAD_RE.match(url.strip())
    if not match:
        return url
    head, rest = match.groups()
    first, _, tail = rest.partition("/")
    if _ATTACHMENT_FLAG in first.split(","):
        return url
    if tail and ("," in first or _CLOUDINARY_TRANSFORM_SEGMENT_RE.match(first)):
        return f"{head}{_ATTACHMENT_FLAG},{first}/{tail}"
    return f"{head}{_ATTACHMENT_FLAG}/{rest}"


def _clamp_unit(value: Optional[float]) -> Optional[float]:
    """0..1 or None — a luminance that cannot be parsed is simply unknown."""
    if value is None:
        return None
    try:
        return round(min(max(float(value), 0.0), 1.0), 3)
    except (TypeError, ValueError):
        return None


def clamp_opacity(value: Optional[float]) -> float:
    """Keep the scrim inside a range that stays readable and stays visible."""
    if value is None:
        return DEFAULT_OVERLAY_OPACITY
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return DEFAULT_OVERLAY_OPACITY
    return round(min(max(numeric, 0.0), 0.9), 2)


def clamp_speed(value: Optional[float]) -> float:
    """A playback rate inside [MIN_SPEED, MAX_SPEED], rounded to the
    hundredth the data-attribute round-trips. Anything unusable — None, a
    string, zero, a negative — is the clip's own speed."""
    if value is None:
        return DEFAULT_SPEED
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return DEFAULT_SPEED
    if speed != speed or speed <= 0:  # NaN, zero, negative
        return DEFAULT_SPEED
    return round(min(max(speed, MIN_SPEED), MAX_SPEED), 2)


def clean_effect(value: Optional[str]) -> str:
    """A VIDEO_EFFECTS key, or the original look for anything else."""
    key = (value or "").strip().lower()
    return key if key in VIDEO_EFFECTS else DEFAULT_EFFECT


def effect_css(effect: str) -> Tuple[str, float]:
    """(filter declaration, overscan scale) for an effect key."""
    spec = VIDEO_EFFECTS.get(effect) or VIDEO_EFFECTS[DEFAULT_EFFECT]
    return str(spec.get("css") or ""), float(spec.get("scale") or 1.0)


def build_settings(
    *,
    video_url: str,
    poster_url: Optional[str] = None,
    overlay: Optional[str] = None,
    overlay_opacity: Optional[float] = None,
    text_mode: Optional[str] = None,
    show_on_mobile: Optional[bool] = None,
    poster_luminance: Optional[float] = None,
    speed: Optional[float] = None,
    effect: Optional[str] = None,
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
        overlay_opacity=None if overlay_opacity is None else clamp_opacity(overlay_opacity),
        poster_luminance=_clamp_unit(poster_luminance),
        text_mode=text,
        show_on_mobile=True if show_on_mobile is None else bool(show_on_mobile),
        speed=clamp_speed(speed),
        effect=clean_effect(effect),
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
# Hero id
# ---------------------------------------------------------------------------

#: The id the pre-built templates use, nav anchors point at, and every
#: layout guard exempts. First entry of _HERO_IDS on purpose.
DEFAULT_HERO_ID = "home"

_ANY_ID_RE = re.compile(r"\bid=[\"'][^\"']*[\"']", re.IGNORECASE)
_HOME_ID_RE = re.compile(r"\bid=[\"']" + re.escape(DEFAULT_HERO_ID) + r"[\"']", re.IGNORECASE)


def ensure_hero_id(html: str) -> Tuple[str, bool]:
    """Give an id-less hero ``id="home"``. Returns ``(html, changed)``.

    The generator's editorial heroes often carry no id. Several defensive
    guards on a served page key off ``#home`` / ``#hero`` / ``#laman-utama``
    and fall back to ``:first-of-type`` — sibling order, which is exactly
    the thing an injected section above the hero changes. Stamping the id
    at generation time makes those guards, the nav's ``#home`` anchor and
    this patcher's own lookup agree on which element the hero is.

    Left alone when the hero already has any id, when the document already
    uses ``id="home"`` elsewhere, or when no hero can be found.
    """
    if not html:
        return html, False
    hero, _how = find_hero_open_tag(html)
    if hero is None:
        return html, False
    open_tag = hero.group(0)
    if _ANY_ID_RE.search(open_tag):
        return html, False
    if _HOME_ID_RE.search(html):
        return html, False
    insert_at = len(open_tag) - 1
    if open_tag[insert_at - 1] == "/":
        insert_at -= 1
    stamped = open_tag[:insert_at] + f' id="{DEFAULT_HERO_ID}"' + open_tag[insert_at:]
    return html[: hero.start()] + stamped + html[hero.end():], True


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
    luminance = _read_attr(tag, "data-binaapp-poster-luminance")
    mobile = (_read_attr(tag, "data-binaapp-mobile") or "video").lower()
    return {
        "video_url": video_url,
        "poster_url": _read_attr(tag, "data-binaapp-poster-url") or None,
        "overlay": (_read_attr(tag, "data-binaapp-overlay") or DEFAULT_OVERLAY).lower(),
        # None (not a default) when the page carries no explicit value, so a
        # re-apply keeps deriving it from luminance for the current scrim.
        "overlay_opacity": clamp_opacity(opacity) if opacity else None,
        "poster_luminance": _clamp_unit(luminance) if luminance else None,
        "text_mode": (_read_attr(tag, "data-binaapp-text-mode") or DEFAULT_TEXT_MODE).lower(),
        "show_on_mobile": mobile != "poster",
        # Absent on pages patched before these existed: the clip's own
        # speed and look, which is exactly what those pages show.
        "speed": clamp_speed(_read_attr(tag, "data-binaapp-speed")),
        "effect": clean_effect(_read_attr(tag, "data-binaapp-effect")),
    }


# ---------------------------------------------------------------------------
# The hero's own background media
# ---------------------------------------------------------------------------

#: Class tokens that make an element cover its parent.
_COVER_TOKENS = ("inset-0", "hero-slow-zoom")
_ABSOLUTE_RE = re.compile(r"(?<![\w-])(?:absolute|fixed)(?![\w-])")
_INLINE_ABSOLUTE_RE = re.compile(r"position\s*:\s*(?:absolute|fixed)", re.IGNORECASE)
_INLINE_BG_IMAGE_RE = re.compile(r"background(?:-image)?\s*:[^;]*url\(", re.IGNORECASE)
_MEDIA_INSIDE_RE = re.compile(r"<(?:img|picture|video|source)\b", re.IGNORECASE)
#: Anything that reads as content. A container holding one of these is the
#: hero's copy (or a card), never its background, however it is positioned.
_CONTENT_INSIDE_RE = re.compile(
    r"<(?:h[1-6]|p|a|button|form|input|ul|ol|nav)\b", re.IGNORECASE
)
_MEDIA_TAGS = ("img", "picture", "video")
_WRAPPER_TAGS = ("div", "figure", "span", "picture")


def _covers_parent(open_tag: str) -> bool:
    classes = tag_classes(open_tag)
    style = read_attr(open_tag, "style") or ""
    positioned = bool(_ABSOLUTE_RE.search(classes)) or bool(_INLINE_ABSOLUTE_RE.search(style))
    if not positioned:
        return False
    tokens = set(classes.split())
    if any(t in tokens for t in _COVER_TOKENS):
        return True
    if {"w-full", "h-full"} <= tokens or {"top-0", "left-0"} <= tokens:
        return True
    return "inset:0" in style.replace(" ", "") or "inset:0px" in style.replace(" ", "")


def _is_background_media(html: str, start: int, end: int) -> bool:
    """True when the element at [start, end) is the hero's own picture.

    Two shapes the generator emits: a full-cover <img> directly in the
    hero, or an ``absolute inset-0`` wrapper holding the <img> (with its own
    gradient inside). A wrapper is only media when it carries no copy —
    a positioned container with an <h1> in it is the headline, not the
    background, and must never be hidden.
    """
    tag_close = open_tag_end(html, start)
    if tag_close == -1:
        return False
    open_tag = html[start:tag_close]
    name = re.match(r"<([a-zA-Z][\w-]*)", open_tag).group(1).lower()
    classes = tag_classes(open_tag)
    tokens = set(classes.split())

    if name in _MEDIA_TAGS:
        if "binaapp-hero-video" in classes:
            return False
        return (
            _covers_parent(open_tag)
            or "object-cover" in tokens
            or {"w-full", "h-full"} <= tokens
        )

    if name not in _WRAPPER_TAGS or not _covers_parent(open_tag):
        return False
    inner = html[tag_close:end]
    if _CONTENT_INSIDE_RE.search(inner):
        return False
    style = read_attr(open_tag, "style") or ""
    return bool(_MEDIA_INSIDE_RE.search(inner)) or bool(_INLINE_BG_IMAGE_RE.search(style))


def _is_floating_overlay(html: str, start: int, end: int) -> bool:
    """A badge or card positioned ON TOP of the media it shares a box with.

    The split hero's floating price card — ``absolute bottom-6 right-6`` over
    the photo — is copy, but it is copy the design puts over the picture. It
    does not stop the column being the media column; replacing the photo with
    the clip leaves the card exactly where it was, on top.
    """
    tag_close = open_tag_end(html, start)
    if tag_close == -1:
        return False
    open_tag = html[start:tag_close]
    classes = tag_classes(open_tag)
    style = read_attr(open_tag, "style") or ""
    return bool(_ABSOLUTE_RE.search(classes)) or bool(_INLINE_ABSOLUTE_RE.search(style))


def _is_plain_media_wrapper(html: str, start: int, end: int) -> bool:
    """A wrapper whose meaningful content is media: the split hero's image
    column. Relative rather than full-cover, at least one picture inside, and
    no copy of its own except what floats over that picture.

    The copy exception is round 5. A column holding a photo AND a floating
    price card was excluded, so the clip fell back to full-bleed behind both
    columns and the image column was left empty — the rule behaved as written
    and the layout still lost. The card is part of the picture, not a reason
    to abandon the column.
    """
    tag_close = open_tag_end(html, start)
    if tag_close == -1:
        return False
    open_tag = html[start:tag_close]
    name = re.match(r"<([a-zA-Z][\w-]*)", open_tag).group(1).lower()
    if name not in _WRAPPER_TAGS or _covers_parent(open_tag):
        return False
    inner = html[tag_close:end]
    if not _MEDIA_INSIDE_RE.search(inner):
        return False
    if not _CONTENT_INSIDE_RE.search(inner):
        return True
    inner_end = html.rfind("</", 0, end)
    if inner_end <= tag_close:
        return False
    for c_start, c_end in direct_children(html, tag_close, inner_end):
        child = html[c_start:c_end]
        child_close = open_tag_end(html, c_start)
        if child_close == -1:
            return False
        child_name = re.match(r"<([a-zA-Z][\w-]*)", html[c_start:child_close])
        is_copy = bool(_CONTENT_INSIDE_RE.search(child)) or bool(
            child_name and _CONTENT_INSIDE_RE.match(f"<{child_name.group(1)}")
        )
        if is_copy and not _is_floating_overlay(html, c_start, c_end):
            return False
    return True


#: How deep below the hero the media walk goes. Two levels was the shape the
#: first split heroes had (hero > column > img). mimk's is five deep —
#: `section > div.max-w-7xl > div.grid > div.order-1 > div.hero-photo-anim >
#: img` — and at two levels the walk found NO media at all: the clip went
#: full-bleed behind the copy, the merchant's own photo was hidden by the
#: poster rules, and the media column was left holding two badges.
MAX_MEDIA_DEPTH = 6


def _media_host(
    html: str, chain: List[Tuple[int, int]]
) -> Optional[Tuple[int, int]]:
    """The wrapper the clip should be hosted in, given the ancestor chain
    from the hero's direct child down to the media's own parent.

    The INNERMOST qualifying wrapper wins: it is the frame the design drew
    around the picture (``rounded-2xl overflow-hidden shadow-2xl``), so the
    clip inherits the corners, the shadow and the aspect box instead of
    covering a whole column that happens to contain it.
    """
    for start, end in reversed(chain):
        if _is_plain_media_wrapper(html, start, end):
            return (start, end)
    return None


def find_hero_media(html: str, hero_start: int) -> List[Tuple[int, int, Optional[Tuple[int, int]]]]:
    """``(start, end, host)`` for every background-media element in the hero.

    Walks the hero's subtree to MAX_MEDIA_DEPTH. ``host`` is the innermost
    wrapper around that media which is a plain media wrapper occupying its
    own region (a split hero's image column, a framed photo card) — the
    video is then hosted in it instead of behind the whole section.
    ``None`` for full-cover media, whose wrapper is hidden with it.
    """
    hero_end = element_end(html, hero_start)
    tag_close = open_tag_end(html, hero_start)
    if hero_end == -1 or tag_close == -1:
        return []
    # The hero's content stops at its own closing tag.
    inner_end = html.rfind("</", tag_close, hero_end)
    if inner_end == -1:
        return []

    found: List[Tuple[int, int, Optional[Tuple[int, int]]]] = []

    def walk(scan_start: int, scan_end: int, chain: List[Tuple[int, int]]) -> None:
        if len(chain) > MAX_MEDIA_DEPTH:
            return
        for start, end in direct_children(html, scan_start, scan_end):
            if _is_background_media(html, start, end):
                host = _media_host(html, chain)
                # Deep media that belongs to NO media wrapper is not the
                # hero's background — it is a picture inside the layout (a
                # collage, a card, a logo lockup). Hiding it and painting a
                # full-bleed clip behind it would take content off the page,
                # so the walk only claims it within the old two-level reach.
                if host is None and len(chain) > 1:
                    continue
                found.append((start, end, host))
                continue
            child_close = open_tag_end(html, start)
            child_inner_end = html.rfind("</", 0, end)
            if child_close == -1 or child_inner_end <= child_close:
                continue
            walk(child_close, child_inner_end, chain + [(start, end)])

    walk(tag_close, inner_end, [])
    return found


#: How strong a veil the hero already paints has to be before it counts as a
#: scrim of its own. Below this it is decoration (a soft vignette, a tinted
#: corner) and the video still needs its own.
MIN_EXISTING_VEIL = 0.2

#: The hero's own copy, in the order its colour is trusted. The generator
#: writes the headline's colour on the headline.
_COPY_TAGS = ("h1", "h2", "p")
#: A box that paints at least this much of its own background is its own
#: surface: the copy inside it is coloured for THAT, not for the hero. The
#: floating white price card in a split hero carried `color:#1C1917`, and
#: reading it as the hero's copy made a dark hero look light (Run 1 site B).
OPAQUE_SURFACE_ALPHA = 0.5


def _hero_span(page_html: str) -> Optional[Tuple[int, int, int]]:
    """``(hero_start, inner_start, inner_end)`` for the page's hero, or None."""
    if not page_html:
        return None
    match, _how = find_hero_open_tag(page_html)
    if match is None:
        return None
    start = match.start()
    end = element_end(page_html, start)
    tag_close = open_tag_end(page_html, start)
    if end == -1 or tag_close == -1:
        return None
    inner_end = page_html.rfind("</", tag_close, end)
    if inner_end == -1:
        return None
    return start, tag_close, inner_end


def _iter_hero_copy(
    html: str,
    inner_start: int,
    inner_end: int,
    variables: Dict[str, str],
    depth: int = 0,
):
    """Every heading/paragraph in the hero that sits on the HERO's backdrop.

    Copy inside a box that paints its own surface is skipped, with its whole
    subtree: a card's text says what the card looks like, not the hero.
    """
    if depth > 6:
        return
    for c_start, c_end in direct_children(html, inner_start, inner_end):
        tag_close = open_tag_end(html, c_start)
        if tag_close == -1:
            continue
        open_tag = html[c_start:tag_close]
        name_match = re.match(r"<([a-zA-Z][\w-]*)", open_tag)
        if not name_match:
            continue
        name = name_match.group(1).lower()
        classes = tag_classes(open_tag)
        style = read_attr(open_tag, "style") or ""
        _tone, alpha = tint(classes, style, variables)
        if alpha >= OPAQUE_SURFACE_ALPHA:
            continue
        if name in _COPY_TAGS:
            yield name, open_tag
        child_inner_end = html.rfind("</", 0, c_end)
        if child_inner_end > tag_close:
            yield from _iter_hero_copy(html, tag_close, child_inner_end, variables, depth + 1)


def _veil_of(
    html: str, start: int, end: int, variables: Optional[Dict[str, str]] = None
) -> Optional[Tuple[str, float]]:
    """The tint of a full-cover, empty element — a scrim the hero paints over
    its own picture — or None for anything holding content or media."""
    tag_close = open_tag_end(html, start)
    if tag_close == -1:
        return None
    open_tag = html[start:tag_close]
    name_match = re.match(r"<([a-zA-Z][\w-]*)", open_tag)
    if not name_match or name_match.group(1).lower() not in _WRAPPER_TAGS:
        return None
    if not _covers_parent(open_tag):
        return None
    classes = tag_classes(open_tag)
    if "binaapp-hero-video" in classes:
        return None
    inner = html[tag_close:end]
    if _CONTENT_INSIDE_RE.search(inner) or _MEDIA_INSIDE_RE.search(inner):
        return None
    tone, alpha = tint(classes, read_attr(open_tag, "style") or "", variables)
    if not tone or alpha < MIN_EXISTING_VEIL:
        return None
    return tone, alpha


def hero_own_veil(page_html: str) -> Optional[Tuple[str, float]]:
    """``(tone, alpha)`` of the strongest scrim the hero already paints.

    Run 1 site A: ``<div class="absolute inset-0 bg-gradient-to-b from-black/40
    via-black/25 to-black/70">`` — a scrim the generator wrote for its own
    photo, which sits ABOVE the video layer and darkens the clip just as it
    darkened the photo. Painting a second full-strength scrim under it is what
    produced a hero veiled twice. Found here so the second one can be sized
    for what is left instead (see color_tone.alpha_over).
    """
    span = _hero_span(page_html)
    if span is None:
        return None
    _start, tag_close, inner_end = span
    variables = css_variables(page_html)
    best: Optional[Tuple[str, float]] = None
    for c_start, c_end in direct_children(page_html, tag_close, inner_end):
        found = _veil_of(page_html, c_start, c_end, variables)
        if found and (best is None or found[1] > best[1]):
            best = found
        child_close = open_tag_end(page_html, c_start)
        child_inner_end = page_html.rfind("</", 0, c_end)
        if child_close == -1 or child_inner_end <= child_close:
            continue
        for g_start, g_end in direct_children(page_html, child_close, child_inner_end):
            found = _veil_of(page_html, g_start, g_end, variables)
            if found and (best is None or found[1] > best[1]):
                best = found
    return best


def hero_copy_tone(page_html: str, *, inherited: bool = True) -> str:
    """The tone of the HERO'S OWN COPY: "light" for a near-white headline,
    "dark" for near-black, "" when the markup states nothing.

    Read in the order the colour actually cascades: an inline style, then a
    colour utility, then the rule the document's own stylesheet writes for
    that element, and finally — when ``inherited`` — what ``body`` gives it.
    The headline is trusted first; copy inside a box that paints its own
    surface never speaks for the hero.
    """
    span = _hero_span(page_html)
    if span is None:
        return ""
    start, tag_close, inner_end = span
    open_tag = page_html[start:tag_close]
    variables = css_variables(page_html)
    rules = stylesheet_rules(page_html)

    copy = list(_iter_hero_copy(page_html, tag_close, inner_end, variables))
    for headlines_only in (True, False):
        for name, tag in copy:
            if headlines_only and name != "h1":
                continue
            tone = text_tone(
                tag_classes(tag), read_attr(tag, "style") or "", variables
            ) or rule_text_tone(tag, rules, variables)
            if tone:
                return tone

    tone = text_tone(
        tag_classes(open_tag), read_attr(open_tag, "style") or "", variables
    ) or rule_text_tone(open_tag, rules, variables)
    if tone:
        return tone
    return inherited_text_tone(rules, variables) if inherited else ""


def detect_hero_tone(page_html: str) -> str:
    """Is the HERO painted dark or light? ``""`` when it says nothing.

    Not the page: the two disagree, and the hero is what the scrim has to sit
    in. A Cerah page can carry a dark editorial hero (white headline over a
    black gradient) and reading the page theme there produced a white veil
    under a black one, with the white copy forced to navy.

    Colours are read through the document's own custom properties AND its own
    style rules. This generator writes `style="color: var(--text-color)"` on
    some pages and `h1 { color: var(--text-color) }` in a `<style>` block on
    others; reading only inline styles and class names made the second kind
    look silent, and mimk — `--bg-color:#141518` with `--text-color:#F5F3EE`
    — got a white scrim over a dark clip and near-white copy on top of it.

    Order of trust:

    1. the hero's headline — light copy means a dark hero;
    2. its other copy, ignoring anything inside a box with its own surface;
    3. a text colour set on the hero element itself;
    4. a full-cover veil the hero paints (black gradient -> dark);
    5. the hero's own flat background, when it is opaque enough to be one;
    6. what the hero's copy INHERITS from the document (``body``/``:root``).
    """
    if _hero_span(page_html) is None:
        return ""
    tone = hero_copy_tone(page_html, inherited=False)
    if tone:
        # Light copy is written for a dark backdrop, and vice versa.
        return "dark" if tone == "light" else "light"

    veil = hero_own_veil(page_html)
    if veil:
        return veil[0]

    start, tag_close, _inner_end = _hero_span(page_html)
    open_tag = page_html[start:tag_close]
    variables = css_variables(page_html)
    rules = stylesheet_rules(page_html)
    tone, alpha = tint(tag_classes(open_tag), read_attr(open_tag, "style") or "", variables)
    if tone and alpha >= OPAQUE_SURFACE_ALPHA:
        return tone
    tone = rule_tint(open_tag, rules, variables)
    if tone:
        return tone
    tone = inherited_text_tone(rules, variables)
    if tone:
        return "dark" if tone == "light" else "light"
    return ""


def _stamp(html: str, start: int, value: str) -> str:
    tag_close = open_tag_end(html, start)
    insert_at = tag_close - 1
    if html[insert_at - 1] == "/":
        insert_at -= 1
    return html[:insert_at] + f' {HERO_MEDIA_ATTR}="{value}"' + html[insert_at:]


def _tag_hero_media(html: str, hero_start: int) -> Tuple[str, int, Optional[int]]:
    """Stamp every media element ``replaced`` and, when there is exactly one
    host wrapper, stamp it ``host``. Returns ``(html, media_count,
    host_start)`` — host_start is where the layer goes, or None for the
    hero itself."""
    targets = find_hero_media(html, hero_start)
    if not targets:
        return html, 0, None
    hosts = {host for _s, _e, host in targets if host}
    # One host or none: two separate media columns is not a shape the
    # layer can occupy, so fall back to the full-bleed layer and hide both.
    host = next(iter(hosts)) if len(hosts) == 1 else None
    stamps = [
        (s, HERO_MEDIA_REPLACED_HOSTED if host and h == host else HERO_MEDIA_REPLACED)
        for s, _e, h in targets
    ]
    if host:
        stamps.append((host[0], HERO_MEDIA_HOST))
    out = html
    # Back to front so earlier offsets survive each insertion.
    for start, value in sorted(stamps, reverse=True):
        out = _stamp(out, start, value)
    host_start = None
    if host:
        # The host's tag moved by every stamp inserted before it (none: it
        # is a direct child and its own media sits after its open tag), so
        # re-find it by the stamp we just wrote.
        host_start = out.find(f'{HERO_MEDIA_ATTR}="{HERO_MEDIA_HOST}"')
        host_start = out.rfind("<", 0, host_start)
    return out, len(targets), host_start


_CLOUDINARY_PUBLIC_ID_RE = re.compile(
    r"res\.cloudinary\.com/[^/]+/(?:image|video)/upload/"
    r"(?:[a-z]{1,3}_[^/]+/)*"      # zero or more transformation segments
    r"(?:v\d+/)?"                  # optional version
    r"(?P<public_id>[^?#]+?)(?:\.[a-zA-Z0-9]{2,5})?(?:[?#]|$)"
)


def cloudinary_public_id(url: Optional[str]) -> Optional[str]:
    """``binaapp/user_uploads/whale`` from any delivery URL of that asset.

    The transformation segment is rewritten at delivery (``f_auto,q_auto…``
    is added on publish), so two URLs of the same photo rarely compare
    equal. The public id is the part that does not move.
    """
    match = _CLOUDINARY_PUBLIC_ID_RE.search(url or "")
    if not match:
        return None
    public_id = match.group("public_id").strip("/")
    return public_id if len(public_id) >= 8 else None


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
        + (
            f' data-binaapp-overlay-opacity="{settings.overlay_opacity}"'
            if settings.overlay_opacity is not None
            else ""
        )
        + (
            f' data-binaapp-poster-luminance="{settings.poster_luminance}"'
            if settings.poster_luminance is not None
            else ""
        )
        + f' data-binaapp-text-mode="{settings.text_mode}"'
        f' data-binaapp-mobile="{"video" if settings.show_on_mobile else "poster"}"'
        # Written only when they differ from the clip as made, so a page
        # that never touched them is byte-identical to before they existed.
        + (
            f' data-binaapp-speed="{settings.speed}"'
            if settings.speed != DEFAULT_SPEED
            else ""
        )
        + (
            f' data-binaapp-effect="{settings.effect}"'
            if settings.effect != DEFAULT_EFFECT
            else ""
        )
        + f"{poster_style}>"
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
    "var h=l.parentNode;"
    # Playback speed. Set now and again once metadata is in: Safari resets
    # the rate when the source loads, so a rate set before ``loadedmetadata``
    # can silently go back to 1 on the very first play.
    "var sp=parseFloat(l.getAttribute('data-binaapp-speed')||'1');"
    "if(sp>0&&sp!==1){var rate=function(){try{v.defaultPlaybackRate=sp;v.playbackRate=sp;}catch(e){}};"
    "rate();v.addEventListener('loadedmetadata',rate);v.addEventListener('play',rate);}"
    # Keep-colour pass. Anything in the hero that paints an opaque
    # background keeps the text colour its designer gave it — a filled CTA
    # is readable already. Descendants too: the icon and label inside the
    # pill are the pill's. Runs before play() so the first paint is right.
    "var K='data-binaapp-keep-color';"
    "function op(e){var m=/rgba?\\(\\s*\\d+\\s*,\\s*\\d+\\s*,\\s*\\d+\\s*(?:,\\s*([\\d.]+))?\\s*\\)/.exec(getComputedStyle(e).backgroundColor||'');"
    "return !!m&&(m[1]===undefined||parseFloat(m[1])>=0.5);}"
    "function stamp(){try{var n=0,all=h.querySelectorAll('*');"
    "for(var i=0;i<all.length;i++){var e=all[i];"
    "if(l.contains(e)||e.hasAttribute(K))continue;"
    "if(op(e)){e.setAttribute(K,'');n++;"
    "var d=e.querySelectorAll('*');for(var j=0;j<d.length;j++)d[j].setAttribute(K,'');}}"
    "h.setAttribute('data-binaapp-keep-color-count',String(n));}catch(e){}}"
    # This script is the hero's FIRST child and runs while the document is
    # still being parsed: at this point the hero's own copy and buttons do
    # not exist yet, so the pass above walked an empty tree and stamped
    # nothing (Run 1 site A: keep-color count 0 on a page whose CTA was
    # recoloured). Wait for the parser to finish the document.
    "if(document.readyState==='loading')"
    "document.addEventListener('DOMContentLoaded',stamp);else stamp();"
    # Reduced motion: the CSS hides the frame, this stops the download. A
    # bare return left `autoplay preload=auto` to pull the whole clip on a
    # device that asked for stillness.
    "if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches){"
    "try{v.pause();v.removeAttribute('autoplay');v.preload='none';}catch(e){}"
    "if(h&&h.setAttribute)h.setAttribute('data-binaapp-video-playing','reduced-motion');return;}"
    "v.muted=true;v.defaultMuted=true;v.setAttribute('muted','');"
    # `playing` fired on soon.binaapp.my while the frame was fully behind
    # the hero's own photo. Sample the frame: an <img> or url() background
    # on top that is not ours means the visitor sees no video, whatever
    # the media element reports — stamp that, not a success.
    "function covered(){try{var r=v.getBoundingClientRect();if(r.bottom<=0||r.right<=0||r.width<40||r.height<40)return false;"
    "var xs=[r.left+r.width/2,r.left+r.width*0.15,r.left+r.width*0.85],ys=[r.top+r.height/2,r.top+r.height*0.15,r.top+r.height*0.85];"
    "for(var i=0;i<xs.length;i++){for(var j=0;j<ys.length;j++){"
    "var t=document.elementFromPoint(xs[i],ys[j]);if(!t||l.contains(t))continue;"
    "if(t.tagName==='IMG'||t.tagName==='PICTURE'||t.tagName==='VIDEO')return true;"
    "var cs=getComputedStyle(t),bg=cs.backgroundImage||'';if(bg.indexOf('url(')>=0)return true;"
    # A solid opaque box over most of the frame hides the clip as surely as
    # a photo does (maka: the media column's cream background). Small solid
    # boxes — a badge, a pill, a card behind the headline — are design.
    "var m=/rgba?\\(\\s*\\d+\\s*,\\s*\\d+\\s*,\\s*\\d+\\s*(?:,\\s*([\\d.]+))?\\s*\\)/.exec(cs.backgroundColor||'');"
    "if(m&&(m[1]===undefined||parseFloat(m[1])>=0.9)){var b=t.getBoundingClientRect();"
    "if(b.width*b.height>=0.4*r.width*r.height)return true;}}}"
    "}catch(e){}return false;}"
    "v.addEventListener('playing',function(){if(!h||!h.setAttribute)return;"
    "if(covered()){h.setAttribute('data-binaapp-video-playing','covered');"
    "if(window.console&&console.warn)console.warn('[binaapp] hero video is playing behind another element');}"
    "else h.setAttribute('data-binaapp-video-playing','1');});"
    "function go(){try{var p=v.play();if(p&&p.catch)p.catch(function(){});}catch(e){}}"
    "go();"
    "['touchstart','pointerdown','scroll','keydown'].forEach(function(t){"
    "window.addEventListener(t,go,{once:true,passive:true});});"
    "document.addEventListener('visibilitychange',function(){if(!document.hidden)go();});"
    "if(v.readyState<2){v.addEventListener('loadeddata',go,{once:true});}"
    "})();</script>"
)


_TEXT_ELEMENTS = ("h1", "h2", "h3", "h4", "p", "li", "blockquote")
#: Text that lives inline and is recoloured only when it paints no
#: background of its own (see the :not() guards where these are used).
_INLINE_TEXT_ELEMENTS = ("span", "a", "strong", "em", "small", "label")


def _css_string(value: str) -> str:
    """A URL as the body of a double-quoted CSS attribute-selector string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


#: Tailwind height utilities on the hero's own tag, unprefixed (a
#: ``md:`` variant is a breakpoint's choice and is left to it). Captures the
#: arbitrary value of ``min-h-[600px]`` / ``h-[70vh]``; the keyword forms
#: (screen / svh / dvh / lvh) carry no group.
_HEIGHT_CLASS_RE = re.compile(
    r"(?<![\w:-])(?:min-h|h)-(?:(screen|svh|dvh|lvh)|\[(\d+(?:\.\d+)?)(px|vh|svh|dvh|lvh|rem)\])(?![\w-])"
)


def hero_height_floor(open_tag: str) -> Optional[str]:
    """The height the hero's own classes ask for, as one CSS length — or
    None when they ask for nothing in particular.

    The layout safety guard caps every section that is not recognisably
    the hero (``min-height:auto !important`` on ``.h-screen`` /
    ``.min-h-screen``), and the generator's editorial heroes carry no id:
    goki's ``h-screen min-h-[600px]`` hero collapsed to the height of its
    two lines of text, with the clip squeezed into that band. The video
    patch knows which section the hero is, so it puts the height back.
    """
    classes = _read_attr(open_tag, "class") or ""
    values: List[str] = []
    for match in _HEIGHT_CLASS_RE.finditer(classes):
        keyword, number, unit = match.groups()
        if keyword:
            values.append("100vh" if keyword == "screen" else f"100{keyword}")
        else:
            values.append(f"{number}{unit}")
    unique = list(dict.fromkeys(values))
    if not unique:
        return None
    return unique[0] if len(unique) == 1 else f"max({','.join(unique)})"


def _build_style(
    settings: HeroVideoSettings,
    hero_open_tag: str = "",
    page_html: str = "",
    hosted: bool = False,
) -> str:
    hero = f"[{HERO_MARKER_ATTR}]"
    overlay = settings.resolved_overlay(page_html)
    opacity = settings.resolved_opacity(page_html)

    # ONE scrim, not two. When the hero already paints a veil of the same
    # colour — the generator's own `absolute inset-0 bg-gradient-to-b
    # from-black/40 … to-black/70`, which sits above the layer and darkens
    # the clip exactly as it darkened the photo — ours only has to make up
    # the difference, and usually there is none left to make up.
    veil = hero_own_veil(page_html) if page_html else None
    if veil and veil[0] == overlay:
        opacity = alpha_over(opacity, veil[1])
    if opacity <= 0.02:
        overlay = "none"

    if overlay == "dark":
        scrim = (
            f"background:linear-gradient(180deg,rgba(0,0,0,{opacity}) 0%,"
            f"rgba(0,0,0,{min(round(opacity + 0.15, 2), 0.95)}) 100%);"
        )
    elif overlay == "light":
        scrim = (
            f"background:linear-gradient(180deg,rgba(255,255,255,{opacity}) 0%,"
            f"rgba(255,255,255,{min(round(opacity + 0.15, 2), 0.95)}) 100%);"
        )
    else:
        scrim = "background:transparent;"

    host = f'{hero} [{HERO_MEDIA_ATTR}="{HERO_MEDIA_HOST}"]'
    rules = [
        # The hero becomes the positioning context. `isolation` keeps the new
        # stacking context local so nothing outside the hero is reordered.
        f"{hero}{{position:relative;isolation:isolate;overflow:hidden;}}",
        # HOSTED: the clip lives inside the hero's own media column and
        # replaces the photo in place. The host is the positioning context;
        # the layer is its first child at z-index:0, so a badge or caption
        # the merchant positioned over the photo still paints over the clip.
        f"{host}{{position:relative;overflow:hidden;}}",
        f"{host} > .binaapp-hero-video-layer{{position:absolute;inset:0;z-index:0;"
        "pointer-events:none;background-size:cover;background-position:center;"
        "background-repeat:no-repeat;}",
        f"{host} > .binaapp-hero-video-layer .binaapp-hero-video{{position:absolute;"
        "inset:0;width:100%;height:100%;object-fit:cover;border:0;pointer-events:none;}",
        # No scrim in the column: nothing of the merchant's sits on top of
        # it, and darkening the model photo's replacement helps no one.
        f"{host} > .binaapp-hero-video-layer .binaapp-hero-video-scrim{{display:none;}}",
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

    filter_css, overscan = effect_css(settings.effect)
    if filter_css:
        # One selector covers both placements (full-bleed and hosted): the
        # video element carries the same class in each.
        scale = f"transform:scale({overscan});" if overscan and overscan != 1.0 else ""
        rules.append(
            f"{hero} .binaapp-hero-video-layer .binaapp-hero-video{{"
            f"filter:{filter_css};{scale}}}"
        )

    floor = hero_height_floor(hero_open_tag) if hero_open_tag else None
    if floor:
        # Six copies of the marker: (0,6,0) outranks the layout guard's
        # (0,5,1) ``section:not(...)x4.h-screen`` cap, which is !important
        # and re-injected AFTER this block on every serve — so specificity,
        # not order, has to win. Newer guards exempt the marked hero
        # outright; this keeps pages that carry an older guard right too.
        # An inline ``style="min-height:…"`` on the hero would still beat
        # this (inline !important is the top of the cascade); no generated
        # page writes one, and if one ever does the fix is to strip it at
        # injection, not to pile on a seventh copy.
        rules.append(
            f"{hero * 6}{{min-height:{floor} !important;height:auto !important;}}"
        )

    # ONE hero visual, not two. The hero's own full-cover picture is found
    # at injection time and stamped HERO_MEDIA_ATTR (see find_hero_media);
    # this rule is what hides it. Structural, so it does not care what URL
    # the picture has or how Cloudinary rewrote it since.
    rules.append(
        f'{hero} [{HERO_MEDIA_ATTR}="{HERO_MEDIA_REPLACED}"]'
        "{display:none !important;}"
    )
    # A HOSTED clip fills the box its photo occupied, so that box has to
    # survive: the frame around a hero photo is usually sized BY the photo
    # (`aspect-[16/9]`, `h-full`), and removing it from the flow left the
    # host at zero height with an absolutely-positioned clip inside it.
    rules.append(
        f'{hero} [{HERO_MEDIA_ATTR}="{HERO_MEDIA_REPLACED_HOSTED}"]'
        "{visibility:hidden !important;}"
    )

    if settings.poster_url:
        # Second net, for the shape the structural pass does not claim: a
        # photo the clip was animated FROM that sits in the hero as a
        # pinned cut-out rather than a full-cover background (ikan, 14:00
        # — the whale bottom-right on top of the video of the whale). It
        # is the poster, so match it by URL, and by Cloudinary public id
        # because the transformation segment changes at delivery. A
        # clip-frame poster never appears in merchant markup, so for
        # text-to-video these match nothing — harmless.
        photo = _css_string(settings.poster_url)
        # `:not([data-binaapp-hero-media])` keeps this net off the media the
        # structural pass already claimed. It matters when the merchant
        # uploaded the hero photo: the clip was animated FROM it, so it is
        # also the poster, and a blanket display:none on that URL hid the
        # very <img> whose box a hosted clip needs (mimk).
        unstamped = f":not([{HERO_MEDIA_ATTR}])"
        rules.append(
            f'{hero} img[src="{photo}"]{unstamped}{{display:none !important;}}'
        )
        rules.append(
            f'{hero} [style*="{photo}"]:not(.binaapp-hero-video-layer)'
            "{background-image:none !important;}"
        )
        public_id = cloudinary_public_id(settings.poster_url)
        if public_id:
            pid = _css_string(public_id)
            rules.append(
                f'{hero} img[src*="{pid}"]{unstamped}{{display:none !important;}}'
            )
            rules.append(
                f'{hero} [style*="{pid}"]:not(.binaapp-hero-video-layer)'
                "{background-image:none !important;}"
            )

    text_mode = settings.resolved_text_mode(page_html)
    if text_mode in ("light", "dark") and not hosted:
        # Hosted clips sit under nothing of the merchant's, so their text
        # keeps the page's own colours; only a full-bleed layer changes
        # what the copy sits on.
        colour = "#FFFFFF" if text_mode == "light" else "#0F172A"
        keep = f":not([{KEEP_COLOR_ATTR}])"
        # !important because generated pages set the colour with a Tailwind
        # arbitrary value on the element itself. Every selector is scoped by
        # the runtime keep-colour stamp: the bootstrap reads each element's
        # COMPUTED background and stamps anything opaque (and everything
        # inside it), which is the only way to see a background the page
        # set in its own stylesheet. The old :not([class*="bg-"]) test
        # missed `.btn-whatsapp` and painted navy on a pink pill.
        selectors = ",".join(f"{hero} {tag}{keep}" for tag in _TEXT_ELEMENTS)
        rules.append(f"{selectors}{{color:{colour} !important;}}")
        # Inline text and ghost buttons too (maka: feature spans in #7A7A6E
        # and a bordered "Lihat Koleksi" stayed dark on the dark scrim).
        inline = ",".join(f"{hero} {tag}{keep}" for tag in _INLINE_TEXT_ELEMENTS)
        rules.append(f"{inline}{{color:{colour} !important;}}")
        rules.append(
            f"{hero} a{keep},{hero} button{keep}"
            "{border-color:currentColor !important;}"
        )
        if text_mode == "light":
            rules.append(
                f"{hero} .binaapp-hero-video-layer ~ * "
                "{text-shadow:0 1px 12px rgba(0,0,0,0.35);}"
            )

    # Motion behind text is precisely what this setting is for: hold the
    # poster frame still instead. The layer keeps the poster as its own
    # background-image, and with the hero's photo hidden above, that
    # poster is what the visitor sees — not a black band.
    rules.append(
        "@media (prefers-reduced-motion:reduce){"
        f"{hero} .binaapp-hero-video-layer .binaapp-hero-video{{display:none;}}}}"
    )
    if not settings.show_on_mobile:
        rules.append(
            "@media (max-width:640px){"
            f"{hero} .binaapp-hero-video-layer .binaapp-hero-video{{display:none;}}}}"
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
    """True when the page carries a hero video whose injected markup is not
    what the current release would write for the same settings — the
    first release's child-restyling CSS, a layer without the playback
    bootstrap, a hero whose own photo is not hidden, a hero whose height
    the guard took away. Defined as "would a re-apply change the page",
    so every future generation is covered without a new special case.
    False for pages without a video and for pages already current."""
    if not html:
        return False
    current = detect_hero_video(html)
    if not current:
        return False
    try:
        rebuilt = apply_hero_video(html, build_settings(**current))
    except ValueError:
        return False
    return rebuilt.changed and rebuilt.html != html


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
    stripped = _MEDIA_ATTR_RE.sub("", stripped)
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

    # Find the hero's own picture BEFORE the layer goes in, so the layer is
    # never a candidate, and stamp it so the stylesheet can hide it. Done on
    # `base` (marker-free), and re-found from scratch on every apply, so a
    # re-apply never stacks attributes.
    base, media_count, host_start = _tag_hero_media(base, hero.start())
    hero, how = find_hero_open_tag(base)
    if hero is None:  # pragma: no cover - tagging never removes the hero
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
    if host_start is not None and host_start > hero.end():
        # Hosted: the layer is the media column's first child. The hero's
        # own tag still gets the marker (every rule is scoped to it).
        host_tag_close = open_tag_end(base, host_start)
        patched = (
            base[: hero.start()] + marked_tag + base[hero.end():host_tag_close]
            + layer + base[host_tag_close:]
        )
        hosted = True
    else:
        patched = base[: hero.start()] + marked_tag + layer + base[hero.end():]
        hosted = False

    style = _build_style(settings, hero_open_tag=open_tag, page_html=base, hosted=hosted)
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

    if media_count:
        notes.append(f"hero_media_replaced:{media_count}")
    if hosted:
        notes.append("layer_hosted_in_media_column")
    own_veil = hero_own_veil(base)
    if own_veil and own_veil[0] == settings.resolved_overlay(base):
        notes.append(f"scrim_shared_with_hero_veil:{own_veil[0]}:{own_veil[1]}")
    logger.info(
        "[hero-video] injected (hero matched by %s, overlay=%s/%.2f, mobile=%s, media hidden=%d)",
        how,
        settings.overlay,
        settings.resolved_opacity(base),
        "video" if settings.show_on_mobile else "poster",
        media_count,
    )
    return HeroVideoResult(
        html=patched,
        changed=True,
        hero_match=how,
        settings=settings.as_dict(),
        notes=notes,
    )
