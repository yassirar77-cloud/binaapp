"""
Post-generation linter for AI-generated website HTML.

Two independent, deterministic passes that run AFTER the model returns HTML and
BEFORE it is stored/served. Both are pure string transforms — no network, no DB —
so they are cheap enough to run on every generation and are unit-testable.

1. lint_fontawesome_icons()
   Font Awesome FREE 6.x is the only icon set loaded on generated sites
   (see ai_service HEAD section: font-awesome/6.4.0/css/all.min.css). Pro-only
   glyphs (e.g. `fa-pot-food`) render as empty squares. This pass scans every
   `fa-*` glyph token, and any token that is NOT a known free-6.x glyph and NOT
   a style/utility modifier is rewritten to a safe free fallback. Replacements
   are logged so we can audit what the model emitted.

2. lint_tailwind_classes()
   The generated pages use the Tailwind Play CDN, which silently no-ops classes
   whose value is outside the default scale — so `bg-amber-300/8` renders with
   NO opacity and `-right-30` positions at 0. This pass rewrites out-of-scale
   opacity modifiers and spacing values to the equivalent arbitrary-value syntax
   (`bg-amber-300/[0.08]`, `right-[-7.5rem]`) which the CDN honours.

`lint_html()` runs both and returns (html, report) where report lists every
change for logging / test assertions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from loguru import logger


# =============================================================================
# Font Awesome free-6.x whitelist
# =============================================================================
#
# Not exhaustive of all ~2000 free glyphs, but covers the icons the generator
# actually reaches for across the business verticals we support (food, retail,
# services, beauty, professional) plus every brand icon we care about. Anything
# outside this set is replaced with a safe free glyph — the goal is "never ship
# a blank square", and over-replacing a rare-but-valid icon degrades to a
# sensible fallback rather than breaking the page.

# fmt: off
_FREE_SOLID_ICONS = {
    # generic / ui
    "check", "check-circle", "circle-check", "xmark", "x", "times", "circle-xmark",
    "plus", "minus", "arrow-right", "arrow-left", "arrow-up", "arrow-down",
    "chevron-right", "chevron-left", "chevron-up", "chevron-down", "angle-right",
    "angle-left", "angle-up", "angle-down", "angles-right", "angles-left",
    "bars", "ellipsis", "ellipsis-vertical", "circle-info", "info", "info-circle",
    "circle-question", "question", "circle-exclamation", "exclamation",
    "triangle-exclamation", "exclamation-triangle", "star", "star-half",
    "star-half-stroke", "heart", "heart-circle-check", "bookmark", "flag",
    "eye", "eye-slash", "magnifying-glass", "search", "filter", "sliders",
    "gear", "cog", "gears", "wrench", "screwdriver-wrench", "tools", "hammer",
    "house", "home", "house-chimney", "building", "shop", "store", "warehouse",
    "location-dot", "map-marker-alt", "map-pin", "map-location-dot", "map",
    "location-arrow", "compass", "globe", "earth-asia",
    # contact
    "phone", "phone-flip", "mobile", "mobile-screen", "mobile-screen-button",
    "envelope", "envelope-open", "at", "paper-plane", "comment", "comments",
    "comment-dots", "message", "headset", "address-book", "address-card",
    "id-card", "user", "users", "user-group", "user-tie", "user-plus",
    "circle-user", "user-circle", "people-group", "person",
    # commerce
    "cart-shopping", "shopping-cart", "cart-plus", "bag-shopping",
    "shopping-bag", "basket-shopping", "shopping-basket", "credit-card",
    "money-bill", "money-bill-wave", "money-bill-1", "wallet", "sack-dollar",
    "coins", "cash-register", "receipt", "tag", "tags", "percent", "gift",
    "truck", "truck-fast", "box", "boxes-stacked", "box-open", "gifts",
    # food & drink
    "utensils", "bowl-food", "bowl-rice", "burger", "hamburger", "pizza-slice",
    "drumstick-bite", "fish", "shrimp", "egg", "bacon", "hotdog", "cheese",
    "bread-slice", "cookie", "cookie-bite", "ice-cream", "cake-candles",
    "birthday-cake", "candy-cane", "mug-hot", "mug-saucer", "coffee", "cup-togo",
    "martini-glass", "martini-glass-citrus", "wine-glass", "wine-bottle",
    "beer-mug-empty", "beer", "bottle-water", "blender", "kitchen-set",
    "carrot", "pepper-hot", "lemon", "apple-whole", "seedling", "leaf",
    "wheat-awn", "plate-wheat", "jar", "stroopwafel", "bacon",
    "champagne-glasses", "whiskey-glass", "mortar-pestle", "fire-burner",
    "temperature-half", "spoon", "bowl-food",
    # beauty / health / wellness
    "scissors", "spray-can", "spray-can-sparkles", "wand-magic-sparkles",
    "spa", "hand-sparkles", "hands-bubbles", "soap", "pump-soap", "brush",
    "paintbrush", "palette", "gem", "ring", "crown", "wand-magic",
    "heart-pulse", "stethoscope", "kit-medical", "pills", "capsules",
    "tooth", "dumbbell", "person-running", "spa",
    # services / trades
    "car", "car-side", "van-shuttle", "motorcycle", "bicycle", "plane",
    "briefcase", "handshake", "handshake-angle", "chart-line", "chart-simple",
    "chart-pie", "chart-column", "clipboard", "clipboard-check",
    "clipboard-list", "list-check", "calendar", "calendar-check",
    "calendar-days", "clock", "hourglass-half", "business-time",
    "graduation-cap", "book", "book-open", "chalkboard", "chalkboard-user",
    "laptop", "laptop-code", "desktop", "code", "database", "server",
    "cloud", "wifi", "print", "camera", "camera-retro", "image", "images",
    "video", "film", "music", "microphone", "headphones", "photo-film",
    "paint-roller", "trowel", "trowel-bricks", "helmet-safety", "hard-hat",
    "plug", "bolt", "lightbulb", "faucet", "broom", "bucket", "screwdriver",
    "ruler", "ruler-combined", "pen", "pen-nib", "pencil", "pen-to-square",
    # trust / quality
    "award", "trophy", "medal", "certificate", "ribbon", "shield", "shield-halved",
    "lock", "unlock", "thumbs-up", "thumbs-down", "circle-check", "badge-check",
    "fire", "bolt-lightning", "gauge-high", "rocket", "sparkles", "wand-sparkles",
    "hand-holding-heart", "hands-holding", "seedling", "recycle", "sun", "moon",
    "cloud-sun", "snowflake", "umbrella", "tree", "mountain-sun", "water",
    "wine-glass-empty", "quote-left", "quote-right", "play", "pause", "circle-play",
    "location-crosshairs", "route", "signs-post", "clock-rotate-left",
}

_FREE_BRAND_ICONS = {
    "whatsapp", "facebook", "facebook-f", "facebook-messenger", "instagram",
    "tiktok", "twitter", "x-twitter", "youtube", "linkedin", "linkedin-in",
    "telegram", "snapchat", "pinterest", "pinterest-p", "google", "google-plus-g",
    "apple", "android", "windows", "microsoft", "amazon", "shopify", "spotify",
    "whatsapp-square", "square-whatsapp", "square-facebook", "square-instagram",
    "square-x-twitter", "square-youtube", "square-twitter", "square-pinterest",
    "grab", "waze", "shopee", "lazada", "cc-visa", "cc-mastercard", "cc-paypal",
    "paypal", "stripe", "line", "weixin", "wechat", "threads",
}
# fmt: on

# Style prefixes and utility/animation modifiers that are NOT glyph names and
# must never be treated as icons to replace.
_FA_NON_GLYPH_TOKENS = {
    # style families
    "solid", "regular", "brands", "light", "thin", "duotone", "sharp",
    "sharp-solid", "sharp-regular",
    # sizing
    "2xs", "xs", "sm", "lg", "xl", "2xl", "1x", "2x", "3x", "4x", "5x", "6x",
    "7x", "8x", "9x", "10x",
    # layout / fixed width / lists
    "fw", "ul", "li", "border", "pull-left", "pull-right", "inverse",
    "stack", "stack-1x", "stack-2x", "layers", "sr-only",
    # animation
    "spin", "spin-pulse", "spin-reverse", "pulse", "beat", "fade", "beat-fade",
    "bounce", "flip", "shake",
    # transforms
    "rotate-90", "rotate-180", "rotate-270", "rotate-by",
    "flip-horizontal", "flip-vertical", "flip-both",
}

# Free-glyph fallbacks by rough business context. Keys are substrings matched
# against the (lowercased) context string the caller passes in.
_FALLBACK_BY_CONTEXT = [
    ("food", "utensils"), ("makan", "utensils"), ("restoran", "utensils"),
    ("cafe", "mug-hot"), ("kopi", "mug-hot"), ("coffee", "mug-hot"),
    ("kedai", "bowl-food"), ("tomyam", "bowl-food"), ("catering", "utensils"),
    ("salon", "scissors"), ("beauty", "spa"), ("spa", "spa"),
    ("shop", "bag-shopping"), ("retail", "bag-shopping"), ("store", "store"),
]
_DEFAULT_FALLBACK = "circle-info"

# A single `fa-<token>` inside a class list. Word-bounded so `fa-solidish`
# won't match and Tailwind's own classes are untouched.
_FA_TOKEN_RE = re.compile(r"fa-([a-z0-9]+(?:-[a-z0-9]+)*)")


@dataclass
class LintReport:
    fa_replacements: List[Tuple[str, str]] = field(default_factory=list)
    tw_rewrites: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.fa_replacements or self.tw_rewrites)

    def as_dict(self) -> Dict[str, List[Tuple[str, str]]]:
        return {
            "fa_replacements": self.fa_replacements,
            "tw_rewrites": self.tw_rewrites,
        }


def _pick_fallback(context: str) -> str:
    ctx = (context or "").lower()
    for needle, glyph in _FALLBACK_BY_CONTEXT:
        if needle in ctx:
            return glyph
    return _DEFAULT_FALLBACK


def _is_known_free_glyph(glyph: str) -> bool:
    return glyph in _FREE_SOLID_ICONS or glyph in _FREE_BRAND_ICONS


def lint_fontawesome_icons(html: str, context: str = "") -> Tuple[str, List[Tuple[str, str]]]:
    """
    Replace unknown / Pro-only Font Awesome glyph classes with a free fallback.

    Only tokens that look like glyph names are considered — style prefixes
    (fa-solid), sizing (fa-2x), and animation (fa-spin) modifiers are skipped.
    Returns (new_html, [(old_glyph, new_glyph), ...]).
    """
    if not html:
        return html, []

    fallback = _pick_fallback(context)
    replacements: List[Tuple[str, str]] = []

    # Only rewrite fa-* tokens that appear inside a class attribute so we never
    # touch unrelated text that happens to contain "fa-".
    class_attr_re = re.compile(r'class\s*=\s*(["\'])(.*?)\1', re.DOTALL)

    def _fix_class_value(match: re.Match) -> str:
        quote = match.group(1)
        value = match.group(2)
        # An element only carries a glyph if it also carries a fa style family
        # or the bare `fa`/`fas`/`far`/`fab` marker. Cheap guard to avoid
        # touching class lists that merely contain a false "fa-" token.
        tokens = value.split()
        has_fa_marker = any(
            t in ("fa", "fas", "far", "fab", "fal", "fat", "fad")
            or t in ("fa-solid", "fa-regular", "fa-brands", "fa-light", "fa-thin", "fa-duotone", "fa-sharp")
            for t in tokens
        )
        if not has_fa_marker and not any(t.startswith("fa-") for t in tokens):
            return match.group(0)

        new_tokens: List[str] = []
        for tok in tokens:
            m = _FA_TOKEN_RE.fullmatch(tok)
            if not m:
                new_tokens.append(tok)
                continue
            glyph = m.group(1)
            if glyph in _FA_NON_GLYPH_TOKENS or _is_known_free_glyph(glyph):
                new_tokens.append(tok)
                continue
            # Unknown glyph → replace with the context fallback.
            new_tokens.append(f"fa-{fallback}")
            replacements.append((glyph, fallback))
        return f"class={quote}{' '.join(new_tokens)}{quote}"

    new_html = class_attr_re.sub(_fix_class_value, html)

    if replacements:
        logger.info(
            f"🔤 FA linter replaced {len(replacements)} unknown/Pro icon(s) "
            f"with fa-{fallback}: {[r[0] for r in replacements]}"
        )
    return new_html, replacements


# =============================================================================
# Tailwind out-of-scale class rewriting
# =============================================================================

# Default Tailwind opacity scale (the CDN honours only these bare modifiers).
_VALID_OPACITY = {
    0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100
}

# Default Tailwind spacing scale (numeric keys, ×0.25rem). Fractions/keywords
# like w-full, h-screen, top-0 are handled separately (0 is valid).
_VALID_SPACING = {
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 20, 24, 28, 32, 36, 40,
    44, 48, 52, 56, 60, 64, 72, 80, 96,
    # half steps stored ×10 handled below via the decimal branch
}
_VALID_SPACING_HALF = {0.5, 1.5, 2.5, 3.5}

# Spacing-style utilities where a bare integer means a scale step. Restricted to
# the positioning / margin / padding / gap / translate families where the
# generator's decorative-blob classes live — deliberately NOT w-/h- to avoid
# touching sizing utilities that legitimately use other scales.
_SPACING_PREFIXES = [
    "inset-x", "inset-y", "inset", "top", "bottom", "left", "right", "start", "end",
    "translate-x", "translate-y",
    "mx", "my", "mt", "mb", "ml", "mr", "ms", "me", "m",
    "px", "py", "pt", "pb", "pl", "pr", "ps", "pe", "p",
    "gap-x", "gap-y", "gap",
    "space-x", "space-y",
]

# Opacity modifier on a color utility, e.g. `bg-amber-300/8`, `text-black/33`.
_OPACITY_RE = re.compile(
    r"(?P<pre>(?:bg|text|border|ring|ring-offset|from|via|to|divide|placeholder"
    r"|shadow|outline|decoration|fill|stroke|accent|caret)-[a-z0-9-]+)/(?P<op>\d{1,3})\b"
)


def _format_decimal(value: float) -> str:
    """0.08 -> '0.08', 0.5 -> '0.5', strip trailing zeros but keep leading 0."""
    s = f"{value:.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _rewrite_opacity(html: str, rewrites: List[Tuple[str, str]]) -> str:
    def repl(m: re.Match) -> str:
        op = int(m.group("op"))
        if op in _VALID_OPACITY or op > 100:
            return m.group(0)
        new = f"{m.group('pre')}/[{_format_decimal(op / 100)}]"
        rewrites.append((m.group(0), new))
        return new

    return _OPACITY_RE.sub(repl, html)


def _rewrite_spacing(html: str, rewrites: List[Tuple[str, str]]) -> str:
    # Build one alternation ordered longest-first so `inset-x` wins over `inset`.
    prefixes = sorted(_SPACING_PREFIXES, key=len, reverse=True)
    alt = "|".join(re.escape(p) for p in prefixes)
    # Optional leading `-` for negative utilities. Value is a bare integer or
    # half-step. Trailing boundary rejects fractions (w-1/2), arbitrary values
    # (right-[..]) and further identifier chars.
    pattern = re.compile(
        rf"(?<![\w-])(?P<neg>-)?(?P<prefix>{alt})-(?P<val>\d+(?:\.\d+)?)(?![\w./\[-])"
    )

    def repl(m: re.Match) -> str:
        raw = m.group("val")
        try:
            num = float(raw)
        except ValueError:
            return m.group(0)
        if num.is_integer():
            num_key: float = int(num)
            valid = num_key in _VALID_SPACING
        else:
            num_key = num
            valid = num_key in _VALID_SPACING_HALF
        if valid:
            return m.group(0)
        rem = num * 0.25
        rem_str = _format_decimal(rem)
        neg = m.group("neg") or ""
        prefix = m.group("prefix")
        if neg:
            new = f"{prefix}-[-{rem_str}rem]"
        else:
            new = f"{prefix}-[{rem_str}rem]"
        rewrites.append((m.group(0), new))
        return new

    return pattern.sub(repl, html)


def lint_tailwind_classes(html: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Rewrite out-of-scale Tailwind opacity/spacing utilities to arbitrary-value
    syntax the Play CDN honours. Returns (new_html, [(old, new), ...]).
    """
    if not html:
        return html, []
    rewrites: List[Tuple[str, str]] = []
    html = _rewrite_opacity(html, rewrites)
    html = _rewrite_spacing(html, rewrites)
    if rewrites:
        logger.info(
            f"🎨 Tailwind linter rewrote {len(rewrites)} out-of-scale class(es): "
            f"{[r[0] + '→' + r[1] for r in rewrites[:8]]}"
        )
    return html, rewrites


def lint_html(html: str, context: str = "") -> Tuple[str, LintReport]:
    """
    Run all post-generation linters. Safe to call on already-clean HTML
    (returns it unchanged with an empty report).

    Args:
        html: generated HTML
        context: business name/description/type — used to pick a sensible
                 icon fallback (food → utensils, salon → scissors, …).
    """
    report = LintReport()
    if not html:
        return html, report
    html, report.fa_replacements = lint_fontawesome_icons(html, context)
    html, report.tw_rewrites = lint_tailwind_classes(html)
    return html, report
