"""What a piece of markup PAINTS, read from its own classes and inline style.

WHY THIS EXISTS
---------------
The hero video scrim was chosen from the *page* theme. Run 1 site A shipped a
Cerah (light) page whose hero was designed dark: ``text-white`` headline over
``bg-gradient-to-b from-black/40 … to-black/70``. "Light page" produced a white
veil under the AI's own black gradient and forced the white copy to navy — the
video washed out, then darkened again, and the hero stopped looking like the
thing the generator designed.

The signal that matters is not what the page paints, it is what the HERO
paints. That is readable from the markup the generator emits, which is
Tailwind utilities plus the occasional inline style. This module is the token
reader: pure string in, tone out. It knows nothing about heroes, videos or
documents — see ``hero_video_patcher.detect_hero_tone`` for the DOM walk that
uses it.

Two questions, both answered without rendering anything:

    text_tone("text-white/80")      -> "light"   (the copy is light)
    tint("bg-black/40 …")           -> ("dark", 0.4)

"" means "this markup states no opinion", which every caller treats as "ask
something else" — never as a default.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from app.services.theme_patcher import normalize_hex, relative_luminance

#: A colour at or above this luminance reads as light, at or below DARK_MAX as
#: dark. Same thresholds colour_mode_guard sorts page backgrounds by, so the
#: two cannot disagree about the same hex.
LIGHT_MIN_LUMINANCE = 0.60
DARK_MAX_LUMINANCE = 0.35

#: Tailwind shades. 50–300 are the light end of every family, 600–950 the dark
#: end; 400 and 500 are the middle, where the family's hue decides and a
#: number cannot — those are reported as "no opinion" rather than guessed.
_LIGHT_SHADES = {"50", "100", "200", "300"}
_DARK_SHADES = {"600", "700", "800", "900", "950"}

#: Tailwind's own families, so ``text-xl`` / ``text-center`` / ``text-balance``
#: are never mistaken for colours.
_FAMILIES = frozenset(
    """slate gray grey zinc neutral stone red orange amber yellow lime green
    emerald teal cyan sky blue indigo violet purple fuchsia pink rose"""
    .split()
)

#: Colour keywords a generated page actually uses, plus the two that carry a
#: tone on their own.
_NAMED = {
    "white": "light",
    "black": "dark",
    "transparent": "",
    "current": "",
    "inherit": "",
}

_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})\s*(?:[,/]\s*([\d.]+%?))?\s*\)",
    re.IGNORECASE,
)
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")

#: ``text-white``, ``text-slate-900``, ``text-[#0F172A]``, each with an
#: optional ``/40`` opacity suffix. The negative look-behind keeps variant
#: prefixes (``md:``, ``hover:``, ``group-hover:``) out of the match so a
#: breakpoint's or a state's colour is never read as the resting one.
_TEXT_CLASS_RE = re.compile(
    r"(?<![\w:./-])text-(\[[^\]\s]+\]|[a-z]+(?:-\d{2,3})?)(?:/(\d{1,3}))?(?![\w-])"
)
#: The utilities that paint a flat colour or a gradient stop.
_TINT_CLASS_RE = re.compile(
    r"(?<![\w:./-])(?:bg|from|via|to)-(\[[^\]\s]+\]|[a-z]+(?:-\d{2,3})?)(?:/(\d{1,3}))?(?![\w-])"
)

_INLINE_COLOR_RE = re.compile(r"(?:^|;)\s*color\s*:\s*([^;]+)", re.IGNORECASE)
_INLINE_BG_RE = re.compile(
    r"(?:^|;)\s*background(?:-color|-image)?\s*:\s*([^;]+)", re.IGNORECASE
)


def _alpha(raw: Optional[str]) -> float:
    """A Tailwind ``/NN`` suffix as a 0..1 alpha. Absent -> fully opaque."""
    if raw is None:
        return 1.0
    try:
        return max(0.0, min(1.0, int(raw) / 100.0))
    except (TypeError, ValueError):
        return 1.0


def tone_of_color(value: str) -> str:
    """"light", "dark" or "" for one CSS colour literal.

    Understands hex, rgb()/rgba() and the handful of keywords a generated
    page uses. A colour between the two thresholds states no opinion: a
    mid-tone is readable either way and must not decide a scrim.
    """
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if raw in _NAMED:
        return _NAMED[raw]
    match = _RGB_RE.search(raw)
    if match:
        r, g, b = (min(255, int(match.group(i))) for i in (1, 2, 3))
        return _tone_of_luminance(relative_luminance(f"#{r:02X}{g:02X}{b:02X}"))
    hex_match = _HEX_RE.search(raw)
    if hex_match:
        # #RRGGBBAA and #RGBA carry an alpha the tone does not depend on.
        digits = hex_match.group(0)[1:]
        if len(digits) in (4, 8):
            digits = digits[: len(digits) // 4 * 3]
        normalized = normalize_hex(digits)
        if normalized:
            return _tone_of_luminance(relative_luminance(normalized))
    return ""


def _tone_of_luminance(luminance: float) -> str:
    if luminance >= LIGHT_MIN_LUMINANCE:
        return "light"
    if luminance <= DARK_MAX_LUMINANCE:
        return "dark"
    return ""


def _tone_of_token(token: str) -> str:
    """The tone of one Tailwind colour token (the part after ``text-``/``bg-``)."""
    token = token.strip().lower()
    if not token:
        return ""
    if token.startswith("[") and token.endswith("]"):
        # Arbitrary value: text-[#0F172A], bg-[rgba(0,0,0,.4)], bg-[--var].
        return tone_of_color(token[1:-1].replace("_", " "))
    if token in _NAMED:
        return _NAMED[token]
    family, _, shade = token.rpartition("-")
    if not family or family not in _FAMILIES:
        return ""
    if shade in _LIGHT_SHADES:
        return "light"
    if shade in _DARK_SHADES:
        return "dark"
    return ""


def text_tone(classes: str = "", style: str = "") -> str:
    """The tone of the text colour this element sets, or "".

    The inline style wins: it is the more specific of the two and it is what
    the generator reaches for when it wants an exact colour.
    """
    inline = _INLINE_COLOR_RE.search(style or "")
    if inline:
        tone = tone_of_color(inline.group(1))
        if tone:
            return tone
    for match in _TEXT_CLASS_RE.finditer(classes or ""):
        tone = _tone_of_token(match.group(1))
        if tone:
            return tone
    return ""


def tint(classes: str = "", style: str = "") -> Tuple[str, float]:
    """The strongest flat colour or gradient stop this element paints.

    Returns ``(tone, alpha)`` — ``("dark", 0.7)`` for the ``to-black/70`` end
    of a hero's own scrim gradient — or ``("", 0.0)`` when it paints nothing
    with a tone. "Strongest" is by alpha, because that is the stop that
    decides what the copy on top has to survive.
    """
    best_tone, best_alpha = "", 0.0

    for match in _TINT_CLASS_RE.finditer(classes or ""):
        tone = _tone_of_token(match.group(1))
        if not tone:
            continue
        alpha = _alpha(match.group(2))
        if alpha > best_alpha:
            best_tone, best_alpha = tone, alpha

    for match in _INLINE_BG_RE.finditer(style or ""):
        value = match.group(1)
        for rgb in _RGB_RE.finditer(value):
            r, g, b = (min(255, int(rgb.group(i))) for i in (1, 2, 3))
            tone = _tone_of_luminance(relative_luminance(f"#{r:02X}{g:02X}{b:02X}"))
            if not tone:
                continue
            raw = rgb.group(4)
            if raw is None:
                alpha = 1.0
            elif raw.endswith("%"):
                alpha = max(0.0, min(1.0, float(raw[:-1]) / 100.0))
            else:
                alpha = max(0.0, min(1.0, float(raw)))
            if alpha > best_alpha:
                best_tone, best_alpha = tone, alpha
        if not _RGB_RE.search(value):
            tone = tone_of_color(value)
            if tone and 1.0 > best_alpha:
                best_tone, best_alpha = tone, 1.0

    return best_tone, best_alpha


def alpha_over(target: float, existing: float) -> float:
    """The alpha a second veil needs so the two together reach ``target``.

    Two stacked veils of alpha *a* and *b* composite to ``1-(1-a)(1-b)``, so
    painting the full target on top of a scrim the hero already has is what
    doubled the darkening. 0.0 when the existing veil is already at or past
    the target — there is nothing left to add.
    """
    target = max(0.0, min(1.0, target))
    existing = max(0.0, min(1.0, existing))
    if existing >= target:
        return 0.0
    if existing >= 1.0:
        return 0.0
    return round((target - existing) / (1.0 - existing), 2)
