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
from typing import Dict, Optional, Tuple

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

#: ``var(--text-color)`` / ``var(--brand, #fff)``. The generator writes hero
#: colours this way — `style="color: var(--text-color)"` over
#: `style="background-color: var(--bg-color)"` — which is neither a Tailwind
#: token nor a literal, so every tone test fell through to "no opinion" and a
#: dark hero was read as unknown (Run 1 site B).
_VAR_USE_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,\s*([^()]*))?\)")
#: A custom-property DECLARATION, as written in the page's own :root block.
_VAR_DECL_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;}{]+)")
_STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)


def css_variables(html: str) -> Dict[str, str]:
    """Every custom property the document declares, first declaration wins.

    First rather than last on purpose: the base ``:root`` block is written
    ahead of any ``@media (prefers-color-scheme: dark)`` override, and taking
    the override would report the colours of a mode the visitor may not be in.
    """
    found: Dict[str, str] = {}
    for block in _STYLE_BLOCK_RE.findall(html or ""):
        for name, value in _VAR_DECL_RE.findall(block):
            value = value.strip()
            if value and name not in found:
                found[name] = value
    return found


def resolve_vars(value: str, variables: Optional[Dict[str, str]], depth: int = 4) -> str:
    """``var(--text-color)`` -> ``#FEF2F2``, using the document's own values.

    A ``var()`` with no declaration falls back to the fallback the author
    wrote, or to the empty string — which every caller reads as "no opinion".
    Depth-bounded, so a variable defined in terms of itself cannot spin.
    """
    text = value or ""
    for _ in range(depth):
        match = _VAR_USE_RE.search(text)
        if not match:
            break
        name, fallback = match.group(1), (match.group(2) or "").strip()
        replacement = (variables or {}).get(name, fallback)
        text = text[: match.start()] + replacement + text[match.end():]
    return text


_INLINE_BG_RE = re.compile(
    r"(?:^|;)\s*background(?:-color|-image)?\s*:\s*([^;]+)", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# The document's own stylesheet
# ---------------------------------------------------------------------------

#: One ``selector { declarations }`` rule. Nested at-rules need no special
#: case: ``[^{}]`` cannot cross a brace, so ``@media (…){:root{…}}`` matches
#: the INNER rule and the wrapper is skipped.
_CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
#: The only selectors we are willing to match an element against: one bare
#: tag, one class, one id, or ``:root``. A descendant selector (``.card p``)
#: is deliberately ignored — matching it would need the ancestor chain, and
#: guessing costs more than the "no opinion" it saves.
_SIMPLE_SELECTOR_RE = re.compile(r"^(?::root|[a-zA-Z][\w-]*|\.[-\w]+|#[-\w]+)$")

_ID_ATTR_RE = re.compile(r"""\bid\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)
_TAG_NAME_RE = re.compile(r"<([a-zA-Z][\w-]*)")


class StyleRules:
    """What the document's ``<style>`` blocks paint, by simple selector.

    A generated page sets its hero colours in a stylesheet, not on the
    element: ``h1 { color: var(--text-color) }`` over ``body { color:
    var(--text-color) }``. An ``<h1>`` with neither a colour class nor an
    inline style is not silent — it is near-white — and reading only classes
    and inline styles made the most explicit hero on the page look like it
    stated nothing (mimk, 2026-09-16: a dark page with near-white copy got a
    white scrim over a dark clip).

    First declaration wins, the same rule ``css_variables`` follows and for
    the same reason: the base block is written before any
    ``prefers-color-scheme`` override, and the override describes a mode the
    visitor may not be in.
    """

    __slots__ = ("color", "background")

    def __init__(self, color: Dict[str, str], background: Dict[str, str]) -> None:
        self.color = color
        self.background = background

    def __bool__(self) -> bool:
        return bool(self.color or self.background)


#: A document with no <style> block at all.
EMPTY_RULES = StyleRules({}, {})


def stylesheet_rules(html: str) -> StyleRules:
    """Read every ``color`` / ``background`` declaration the document writes
    under a selector simple enough to match an element against."""
    color: Dict[str, str] = {}
    background: Dict[str, str] = {}
    for block in _STYLE_BLOCK_RE.findall(html or ""):
        for selectors, declarations in _CSS_RULE_RE.findall(_CSS_COMMENT_RE.sub("", block)):
            keys = []
            for selector in selectors.split(","):
                key = selector.strip()
                if _SIMPLE_SELECTOR_RE.match(key):
                    keys.append(key.lower() if not key.startswith("#") else key)
            if not keys:
                continue
            found_color = _INLINE_COLOR_RE.search(";" + declarations)
            found_bg = _INLINE_BG_RE.search(";" + declarations)
            for key in keys:
                if found_color and key not in color:
                    color[key] = found_color.group(1).strip()
                if found_bg and key not in background:
                    background[key] = found_bg.group(1).strip()
    return StyleRules(color, background)


_CLASS_ATTR_RE = re.compile(
    r"""\bclass\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE
)


def _class_attr_value(open_tag: str) -> str:
    match = _CLASS_ATTR_RE.search(open_tag or "")
    if not match:
        return ""
    return (match.group(1) or match.group(2) or match.group(3) or "").strip()


def selector_keys(open_tag: str) -> list:
    """The stylesheet keys that could paint this element, most specific
    first: its id, then each of its classes, then its tag name."""
    keys: list = []
    id_match = _ID_ATTR_RE.search(open_tag or "")
    if id_match:
        value = (id_match.group(1) or id_match.group(2) or id_match.group(3) or "").strip()
        if value:
            keys.append(f"#{value}")
    for cls in _class_attr_value(open_tag).split():
        # A Tailwind utility is never declared as a class rule in the page's
        # own stylesheet, but a hand-written one (.hero-title) is.
        keys.append(f".{cls.lower()}")
    name_match = _TAG_NAME_RE.match((open_tag or "").strip())
    if name_match:
        keys.append(name_match.group(1).lower())
    return keys


def rule_text_tone(
    open_tag: str,
    rules: Optional[StyleRules],
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """The tone of the text colour the DOCUMENT'S STYLESHEET gives this
    element, or "". Nothing is inherited here — see ``inherited_text_tone``
    for the ``body`` fallback."""
    if not rules:
        return ""
    for key in selector_keys(open_tag):
        value = rules.color.get(key)
        if value:
            tone = tone_of_color(value, variables)
            if tone:
                return tone
    return ""


def rule_tint(
    open_tag: str,
    rules: Optional[StyleRules],
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """The tone of the background the stylesheet gives this element, or ""."""
    if not rules:
        return ""
    for key in selector_keys(open_tag):
        value = rules.background.get(key)
        if value:
            tone = tone_of_color(value, variables)
            if tone:
                return tone
    return ""


def inherited_text_tone(
    rules: Optional[StyleRules], variables: Optional[Dict[str, str]] = None
) -> str:
    """The colour the page's copy inherits when nothing nearer sets one:
    ``body``, then ``html``, then ``:root``."""
    if not rules:
        return ""
    for key in ("body", "html", ":root"):
        value = rules.color.get(key)
        if value:
            tone = tone_of_color(value, variables)
            if tone:
                return tone
    return ""


def _alpha(raw: Optional[str]) -> float:
    """A Tailwind ``/NN`` suffix as a 0..1 alpha. Absent -> fully opaque."""
    if raw is None:
        return 1.0
    try:
        return max(0.0, min(1.0, int(raw) / 100.0))
    except (TypeError, ValueError):
        return 1.0


def tone_of_color(value: str, variables: Optional[Dict[str, str]] = None) -> str:
    """"light", "dark" or "" for one CSS colour literal.

    Understands hex, rgb()/rgba(), the handful of keywords a generated page
    uses, and ``var(--name)`` when the document's declarations are passed in.
    A colour between the two thresholds states no opinion: a mid-tone is
    readable either way and must not decide a scrim.
    """
    raw = resolve_vars(value or "", variables).strip().lower()
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


def _tone_of_token(token: str, variables: Optional[Dict[str, str]] = None) -> str:
    """The tone of one Tailwind colour token (the part after ``text-``/``bg-``)."""
    token = token.strip().lower()
    if not token:
        return ""
    if token.startswith("[") and token.endswith("]"):
        # Arbitrary value: text-[#0F172A], bg-[rgba(0,0,0,.4)], bg-[var(--x)].
        return tone_of_color(token[1:-1].replace("_", " "), variables)
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


def text_tone(
    classes: str = "", style: str = "", variables: Optional[Dict[str, str]] = None
) -> str:
    """The tone of the text colour this element sets, or "".

    The inline style wins: it is the more specific of the two and it is what
    the generator reaches for when it wants an exact colour.
    """
    inline = _INLINE_COLOR_RE.search(style or "")
    if inline:
        tone = tone_of_color(inline.group(1), variables)
        if tone:
            return tone
    for match in _TEXT_CLASS_RE.finditer(classes or ""):
        tone = _tone_of_token(match.group(1), variables)
        if tone:
            return tone
    return ""


def tint(
    classes: str = "", style: str = "", variables: Optional[Dict[str, str]] = None
) -> Tuple[str, float]:
    """The strongest flat colour or gradient stop this element paints.

    Returns ``(tone, alpha)`` — ``("dark", 0.7)`` for the ``to-black/70`` end
    of a hero's own scrim gradient — or ``("", 0.0)`` when it paints nothing
    with a tone. "Strongest" is by alpha, because that is the stop that
    decides what the copy on top has to survive.
    """
    best_tone, best_alpha = "", 0.0

    for match in _TINT_CLASS_RE.finditer(classes or ""):
        tone = _tone_of_token(match.group(1), variables)
        if not tone:
            continue
        alpha = _alpha(match.group(2))
        if alpha > best_alpha:
            best_tone, best_alpha = tone, alpha

    for match in _INLINE_BG_RE.finditer(style or ""):
        value = resolve_vars(match.group(1), variables)
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
            tone = tone_of_color(value, variables)
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
