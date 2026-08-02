"""Credit-free theme repaint for an already-generated site.

WHY THIS EXISTS
---------------
Changing "warna oren jadi biru" used to mean a full AI regeneration: the
merchant burned a generation credit, waited ~2 minutes, and got back a page
whose copy, images and layout had all silently moved as well. A colour swap is
not a redesign — it is a find/replace over a handful of tokens the generator
already emitted.

This module does exactly that, deterministically and offline:

    new_html, result = apply_theme(html, palette=NEW_PALETTE, fonts=NEW_FONTS)

Nothing here calls the AI, touches quota, or reorders content. It rewrites the
colour/typography tokens the generator emits and leaves every other byte of the
document alone.

WHAT GETS REWRITTEN
-------------------
1. CSS custom properties (``--primary-color``, ``--bg-color``, ``--text``, …
   plus the common aliases the generator and the pre-built templates use).
2. The inline ``tailwind.config`` colour block that generated pages carry.
3. Literal hex colours anywhere else in the document (inline ``style=``
   attributes, ``<style>`` blocks, Tailwind arbitrary values like
   ``text-[#34d399]`` that the pre-built templates hardcode) — but ONLY hexes
   that belong to the page's *current* palette, so unrelated colours survive.
4. ``<meta name="theme-color">`` (the Android browser-chrome colour).
5. The Google Fonts ``<link>`` and every reference to the old font families.

SAFETY RULES
------------
* Greyscale hexes (``#FFFFFF``, ``#000``, ``#6B7280`` …) are NEVER swapped
  globally. White is structural — it is the text colour on hero overlays, the
  card background, the divider — and repainting every white in the document is
  how a recolour turns into a broken page.
* ``href`` attributes are masked out before the hex pass so an anchor like
  ``href="#abcdef"`` can never be mangled into a colour.
* The hex pass is SINGLE-PASS: replacements never cascade (old A → new B is
  never re-read as old B → new C).
* The function is pure and idempotent: applying the same palette twice yields
  the same document.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: Palette roles this module understands. Mirrors the design_system palettes.
PALETTE_ROLES: Tuple[str, ...] = (
    "primary",
    "secondary",
    "accent",
    "background",
    "surface",
    "text",
    "text_muted",
    "border",
)

#: CSS custom-property names seen in generated output, mapped to palette roles.
#: Longest/most-specific names are checked first so ``--primary-color`` never
#: gets matched by the shorter ``--primary`` rule.
_VAR_ALIASES: Dict[str, Tuple[str, ...]] = {
    "primary": ("--primary-color", "--color-primary", "--brand-color", "--primary", "--brand"),
    "secondary": ("--secondary-color", "--color-secondary", "--secondary"),
    "accent": ("--accent-color", "--color-accent", "--accent"),
    "background": ("--background-color", "--color-background", "--bg-color", "--background", "--bg"),
    "surface": ("--surface-color", "--color-surface", "--card-color", "--card-bg", "--surface"),
    "text": ("--text-color", "--color-text", "--foreground-color", "--text", "--foreground"),
    "text_muted": (
        "--text-muted-color",
        "--text-muted",
        "--muted-color",
        "--text-secondary",
        "--muted",
    ),
    "border": ("--border-color", "--color-border", "--border"),
}

_HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
#: Places a "#abcdef" is an IDENTIFIER, not a colour: anchor targets
#: (href="#EA580C-promo"), URL fragments inside src, and SVG paint references
#: (fill="url(#a1b2c3)"). All are masked out before the hex pass.
_URLISH_RE = re.compile(
    r"""((?:xlink:href|href|src|srcset|action|data)\s*=\s*)(["'])(.*?)\2"""
    r"""|(url\(\s*)(#[\w.\-]+)(\s*\))""",
    re.DOTALL | re.IGNORECASE,
)
_GOOGLE_FONTS_LINK_RE = re.compile(
    r"""<link\b[^>]*href\s*=\s*["'][^"']*fonts\.googleapis\.com/css2\?[^"']*["'][^>]*>""",
    re.IGNORECASE,
)
_FONT_FAMILY_IN_URL_RE = re.compile(r"family=([^:&\"']+)")
_THEME_COLOR_META_RE = re.compile(
    r"""(<meta\b[^>]*name\s*=\s*["']theme-color["'][^>]*content\s*=\s*["'])([^"']*)(["'])""",
    re.IGNORECASE,
)
#: Tailwind config colour entries: 'primary': '#B91C1C' (key quoting optional).
_TW_COLOR_RE_TEMPLATE = r"""(['"]?{role}['"]?\s*:\s*['"])#(?:[0-9a-fA-F]{{3}}|[0-9a-fA-F]{{6}})(['"])"""
#: The inline tailwind.config script generated pages carry.
_TW_CONFIG_BLOCK_RE = re.compile(
    r"<script\b[^>]*>(?:(?!</script>).)*?tailwind\.config(?:(?!</script>).)*?</script>",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ThemePatchResult:
    """Outcome of a repaint. ``html`` is always safe to publish."""

    html: str
    changed: bool = False
    #: How many literal hex colours were swapped in the document body.
    hex_replacements: int = 0
    #: How many CSS custom properties were rewritten.
    variable_replacements: int = 0
    #: How many tailwind.config colour entries were rewritten.
    tailwind_replacements: int = 0
    #: Palette detected on the page BEFORE the patch.
    previous_palette: Dict[str, str] = field(default_factory=dict)
    #: Palette written by the patch.
    palette: Dict[str, str] = field(default_factory=dict)
    #: Font families detected before / written by the patch.
    previous_fonts: Dict[str, str] = field(default_factory=dict)
    fonts: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, int]:
        return {
            "hex": self.hex_replacements,
            "variables": self.variable_replacements,
            "tailwind": self.tailwind_replacements,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_hex(value: str) -> Optional[str]:
    """``'#abc'`` / ``'ABCDEF'`` -> ``'#AABBCC'`` / ``'#ABCDEF'``; None if invalid."""
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw.startswith("#"):
        raw = "#" + raw
    if re.fullmatch(r"#[0-9a-fA-F]{3}", raw):
        r, g, b = raw[1], raw[2], raw[3]
        return f"#{r}{r}{g}{g}{b}{b}".upper()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return raw.upper()
    return None


def is_greyscale(hex_value: str) -> bool:
    """True for white/black/greys — colours too structural to swap globally."""
    normalized = normalize_hex(hex_value)
    if not normalized:
        return False
    r = int(normalized[1:3], 16)
    g = int(normalized[3:5], 16)
    b = int(normalized[5:7], 16)
    # A tiny tolerance catches "almost grey" neutrals (#FAFAF9 and friends)
    # that generated pages use as page backgrounds AND as generic surfaces.
    return max(r, g, b) - min(r, g, b) <= 6


def relative_luminance(hex_value: str) -> float:
    """WCAG relative luminance in [0, 1]. Invalid input -> 0.0."""
    normalized = normalize_hex(hex_value)
    if not normalized:
        return 0.0

    def channel(component: int) -> float:
        srgb = component / 255.0
        return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4

    r = channel(int(normalized[1:3], 16))
    g = channel(int(normalized[3:5], 16))
    b = channel(int(normalized[5:7], 16))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG contrast ratio between two hex colours (1.0 – 21.0)."""
    light = relative_luminance(foreground)
    dark = relative_luminance(background)
    if light < dark:
        light, dark = dark, light
    return round((light + 0.05) / (dark + 0.05), 2)


def clean_palette(raw: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Keep only known roles with valid hex values, normalised to #RRGGBB."""
    if not raw:
        return {}
    cleaned: Dict[str, str] = {}
    for role in PALETTE_ROLES:
        normalized = normalize_hex(str(raw.get(role) or ""))
        if normalized:
            cleaned[role] = normalized
    return cleaned


def _mask_urls(html: str) -> Tuple[str, List[str]]:
    """Replace URL-ish values with placeholders so the hex pass can't touch them."""
    stash: List[str] = []

    def _stash(match: re.Match) -> str:
        if match.group(1) is not None:
            stash.append(match.group(3))
            token = f"\x00URL{len(stash) - 1}\x00"
            return f"{match.group(1)}{match.group(2)}{token}{match.group(2)}"
        stash.append(match.group(5))
        token = f"\x00URL{len(stash) - 1}\x00"
        return f"{match.group(4)}{token}{match.group(6)}"

    return _URLISH_RE.sub(_stash, html), stash


def _unmask_urls(html: str, stash: List[str]) -> str:
    if not stash:
        return html

    def _restore(match: re.Match) -> str:
        return stash[int(match.group(1))]

    return re.sub(r"\x00URL(\d+)\x00", _restore, html)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_palette(html: str) -> Dict[str, str]:
    """Best-effort read of the palette currently baked into ``html``.

    Looks at CSS custom properties first (the generator's own contract), then
    falls back to the inline ``tailwind.config`` colour block. Missing roles
    are simply absent — callers must not assume a complete palette.
    """
    if not html:
        return {}

    found: Dict[str, str] = {}
    for role, names in _VAR_ALIASES.items():
        for name in names:
            match = re.search(
                rf"{re.escape(name)}\s*:\s*(#(?:[0-9a-fA-F]{{3}}|[0-9a-fA-F]{{6}}))\b", html
            )
            if match:
                normalized = normalize_hex(match.group(1))
                if normalized:
                    found[role] = normalized
                    break

    # Tailwind config fills whatever the CSS variables did not provide.
    for role in ("primary", "secondary", "accent", "surface", "background"):
        if role in found:
            continue
        match = re.search(
            rf"""['"]?{role}['"]?\s*:\s*['"](#(?:[0-9a-fA-F]{{3}}|[0-9a-fA-F]{{6}}))['"]""",
            html,
        )
        if match:
            normalized = normalize_hex(match.group(1))
            if normalized:
                found[role] = normalized

    return found


def detect_fonts(html: str) -> Dict[str, str]:
    """Read the heading/body font families out of the Google Fonts link.

    The generator always emits ``family=<Heading>&family=<Body>`` in that
    order, so position carries the role. Returns ``{}`` when there is no link.
    """
    if not html:
        return {}
    link = _GOOGLE_FONTS_LINK_RE.search(html)
    if not link:
        return {}
    families = [
        name.replace("+", " ").strip()
        for name in _FONT_FAMILY_IN_URL_RE.findall(link.group(0))
    ]
    families = [f for f in families if f]
    if not families:
        return {}
    fonts = {"heading": families[0]}
    if len(families) > 1:
        fonts["body"] = families[1]
    else:
        fonts["body"] = families[0]
    return fonts


# ---------------------------------------------------------------------------
# Patching
# ---------------------------------------------------------------------------


def _swap_literal_hexes(html: str, mapping: Dict[str, str]) -> Tuple[str, int]:
    """Single-pass swap of the old palette's hexes. Never cascades."""
    if not mapping:
        return html, 0

    counter = {"n": 0}

    def _replace(match: re.Match) -> str:
        normalized = normalize_hex(match.group(0))
        if not normalized:
            return match.group(0)
        new_value = mapping.get(normalized)
        if not new_value or new_value == normalized:
            return match.group(0)
        counter["n"] += 1
        return new_value

    return _HEX_RE.sub(_replace, html), counter["n"]


def _write_css_variables(html: str, palette: Dict[str, str]) -> Tuple[str, int]:
    """Force every known CSS custom property to the new palette value."""
    total = 0
    for role, names in _VAR_ALIASES.items():
        new_value = palette.get(role)
        if not new_value:
            continue
        for name in names:
            pattern = re.compile(
                rf"({re.escape(name)}\s*:\s*)#(?:[0-9a-fA-F]{{3}}|[0-9a-fA-F]{{6}})\b"
            )
            html, count = pattern.subn(rf"\g<1>{new_value}", html)
            total += count
    return html, total


def _write_tailwind_colors(html: str, palette: Dict[str, str]) -> Tuple[str, int]:
    """Force the inline tailwind.config colour entries to the new palette.

    Scoped to the tailwind.config <script> so an unrelated JSON blob with a
    ``"primary"`` key elsewhere on the page is never touched.
    """
    total = 0

    def _patch_block(block_match: re.Match) -> str:
        nonlocal total
        block = block_match.group(0)
        for role in ("primary", "secondary", "accent", "surface", "background"):
            new_value = palette.get(role)
            if not new_value:
                continue
            pattern = re.compile(_TW_COLOR_RE_TEMPLATE.format(role=role))
            block, count = pattern.subn(rf"\g<1>{new_value}\g<2>", block)
            total += count
        return block

    return _TW_CONFIG_BLOCK_RE.sub(_patch_block, html), total


def _write_theme_color_meta(html: str, primary: str) -> str:
    """Point <meta name="theme-color"> at the new primary; add it if missing."""
    if not primary:
        return html
    patched, count = _THEME_COLOR_META_RE.subn(rf"\g<1>{primary}\g<3>", html)
    if count:
        return patched
    tag = f'<meta name="theme-color" content="{primary}">'
    match = re.search(r"<head\b[^>]*>", html, re.IGNORECASE)
    if match:
        return html[: match.end()] + "\n    " + tag + html[match.end() :]
    return html


def _build_google_fonts_link(fonts: Dict[str, str]) -> str:
    heading = (fonts.get("heading") or "").strip()
    body = (fonts.get("body") or "").strip()
    if not heading and not body:
        return ""
    parts = []
    if heading:
        weights = fonts.get("heading_weights") or "400;600;700"
        parts.append(f"family={heading.replace(' ', '+')}:wght@{weights}")
    if body and body != heading:
        weights = fonts.get("body_weights") or "400;500;600;700"
        parts.append(f"family={body.replace(' ', '+')}:wght@{weights}")
    return (
        '<link href="https://fonts.googleapis.com/css2?'
        + "&".join(parts)
        + '&display=swap" rel="stylesheet">'
    )


def _apply_fonts(
    html: str, fonts: Dict[str, str], previous: Dict[str, str]
) -> Tuple[str, List[str]]:
    """Swap the Google Fonts link and every reference to the old families."""
    notes: List[str] = []
    new_link = _build_google_fonts_link(fonts)
    if not new_link:
        return html, notes

    if _GOOGLE_FONTS_LINK_RE.search(html):
        html = _GOOGLE_FONTS_LINK_RE.sub(lambda _m: new_link, html, count=1)
        # A page can carry more than one css2 link (template + generator);
        # drop the extras so the old family stops loading.
        html = _GOOGLE_FONTS_LINK_RE.sub(
            lambda m: "" if m.group(0) != new_link else m.group(0), html
        )
        if new_link not in html:
            html = html.replace("</head>", f"    {new_link}\n</head>", 1)
    else:
        head_match = re.search(r"<head\b[^>]*>", html, re.IGNORECASE)
        if head_match:
            html = html[: head_match.end()] + "\n    " + new_link + html[head_match.end() :]
        else:
            notes.append("no_head_for_font_link")
            return html, notes

    # Rename the families wherever the page references them by name
    # (font-family declarations, tailwind fontFamily arrays, inline styles).
    for role in ("heading", "body"):
        old_name = (previous.get(role) or "").strip()
        new_name = (fonts.get(role) or "").strip()
        if not old_name or not new_name or old_name == new_name:
            continue
        html = re.sub(
            rf"(?<![\w+]){re.escape(old_name)}(?![\w+])",
            new_name,
            html,
        )
    return html, notes


def apply_theme(
    html: str,
    palette: Optional[Dict[str, str]] = None,
    fonts: Optional[Dict[str, str]] = None,
) -> ThemePatchResult:
    """Repaint ``html`` with ``palette`` (and optionally ``fonts``).

    Pure function. Returns the patched document plus a report of what moved.
    An empty/invalid palette is a no-op rather than an error — the caller
    decides whether that is worth surfacing.
    """
    result = ThemePatchResult(html=html or "")
    if not html:
        result.notes.append("empty_html")
        return result

    target = clean_palette(palette)
    previous = detect_palette(html)
    result.previous_palette = previous
    result.palette = target

    if target:
        # 1. Global literal-hex swap FIRST, using old -> new. Runs before the
        #    authoritative variable/tailwind writes so a freshly written value
        #    can never be re-mapped by a later rule.
        mapping: Dict[str, str] = {}
        for role, old_hex in previous.items():
            new_hex = target.get(role)
            if not new_hex or new_hex == old_hex:
                continue
            if is_greyscale(old_hex):
                # White/black/grey are structural, not brand colours.
                continue
            mapping.setdefault(old_hex, new_hex)

        masked, stash = _mask_urls(html)
        masked, hex_count = _swap_literal_hexes(masked, mapping)
        html = _unmask_urls(masked, stash)
        result.hex_replacements = hex_count

        # 2. Authoritative token writes.
        html, var_count = _write_css_variables(html, target)
        html, tw_count = _write_tailwind_colors(html, target)
        result.variable_replacements = var_count
        result.tailwind_replacements = tw_count

        if target.get("primary"):
            html = _write_theme_color_meta(html, target["primary"])

        if target.get("text") and target.get("background"):
            ratio = contrast_ratio(target["text"], target["background"])
            if ratio < 4.5:
                result.notes.append(f"low_text_contrast:{ratio}")

        if not (hex_count or var_count or tw_count):
            result.notes.append("no_colour_tokens_found")

    if fonts:
        previous_fonts = detect_fonts(result.html)
        result.previous_fonts = previous_fonts
        result.fonts = {k: v for k, v in fonts.items() if k in ("heading", "body")}
        html, font_notes = _apply_fonts(html, fonts, previous_fonts)
        result.notes.extend(font_notes)

    result.changed = html != result.html
    result.html = html
    return result
