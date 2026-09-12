"""Colour mode is a constraint, not a suggestion.

WHY THIS EXISTS
---------------
A merchant picked **Gelap** on the create page and wrote "background hitam
kopi, aksen emas gelap" in the brief. The page that shipped had

    --bg-color: #F5F3EF     /* cream */

with one dark hero and one forest-green band — a light site. The prompt does
carry the dark palette (ai_service builds a DARK MODE STYLING block and pins
``:root { --bg-color: … }``), and design_director already overrules an AI
concept whose palette contradicts the mode. Neither survives the last step:
the model writes the whole document itself and simply substitutes its own
value for the one it was given. A prompt rule cannot be enforced by a prompt.

So this module closes the loop after generation, deterministically:

    mode = detect_color_mode(html)          # what the page actually is
    html, report = enforce_color_mode(html, "dark", palette)

``detect_color_mode`` is also what the post-generation validator uses to
raise ``color_mode_mismatch`` — an ERROR, so the normal repair path gets one
chance to regenerate properly before the deterministic repaint below is used
as the floor.

WHAT THE REPAINT DOES
---------------------
1. Rewrites the neutral palette roles (background/surface/text/text_muted/
   border) to mode-correct values via theme_patcher, keeping the brand roles
   (primary/secondary/accent) exactly as the model chose them — the merchant
   asked for a dark page, not a different brand.
2. Adds a small stylesheet that re-points the Tailwind neutral utilities the
   model sprinkled through the markup (``bg-white``, ``text-gray-900`` …) at
   those same variables. Without step 2 the variables are correct and the
   page still renders light, because most of the document never reads them.

Pure functions. No I/O, no network, no globals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.theme_patcher import (
    apply_theme,
    detect_palette,
    normalize_hex,
    relative_luminance,
)

#: Same thresholds design_director validates its palettes against, so the
#: pre-generation check and this post-generation check cannot disagree.
DARK_MAX_LUMINANCE = 0.35
LIGHT_MIN_LUMINANCE = 0.60

#: Mode-correct neutrals used when the caller has no palette to hand. Warm
#: near-black rather than pure #000: the briefs that ask for dark ask for
#: "hitam kopi", and pure black kills the depth of a photo-led page.
DARK_NEUTRALS: Dict[str, str] = {
    "background": "#12100E",
    "surface": "#1C1917",
    "text": "#F5F3EF",
    "text_muted": "#A8A29E",
    "border": "#2E2A27",
}
LIGHT_NEUTRALS: Dict[str, str] = {
    "background": "#FAFAF9",
    "surface": "#FFFFFF",
    "text": "#1C1917",
    "text_muted": "#57534E",
    "border": "#E7E5E4",
}

_NEUTRAL_ROLES = ("background", "surface", "text", "text_muted", "border")

#: Tailwind neutral utilities generated pages reach for. Grouped by the role
#: they should adopt once the page is repainted.
_SURFACE_CLASSES = (
    "bg-white", "bg-gray-50", "bg-gray-100", "bg-slate-50", "bg-slate-100",
    "bg-neutral-50", "bg-neutral-100", "bg-stone-50", "bg-stone-100",
    "bg-zinc-50", "bg-zinc-100",
)
_BODY_BG_CLASSES = ("bg-gray-900", "bg-slate-900", "bg-neutral-900", "bg-black")
_TEXT_STRONG_CLASSES = (
    "text-gray-900", "text-gray-800", "text-slate-900", "text-slate-800",
    "text-neutral-900", "text-neutral-800", "text-stone-900", "text-stone-800",
    "text-zinc-900", "text-black",
)
_TEXT_MUTED_CLASSES = (
    "text-gray-700", "text-gray-600", "text-gray-500", "text-slate-600",
    "text-slate-500", "text-neutral-600", "text-neutral-500",
    "text-stone-600", "text-stone-500", "text-zinc-600", "text-zinc-500",
)
_BORDER_CLASSES = (
    "border-gray-200", "border-gray-100", "border-slate-200", "border-slate-100",
    "border-neutral-200", "border-stone-200", "border-zinc-200",
)

_STYLE_ID = "binaapp-color-mode"
_STYLE_BLOCK_RE = re.compile(
    rf"<style\b[^>]*id=[\"']{_STYLE_ID}[\"'][^>]*>.*?</style>\s*",
    re.IGNORECASE | re.DOTALL,
)

#: `body { background: #hex }` written directly rather than through a variable.
_BODY_BG_RE = re.compile(
    r"\bbody\b[^{}]*\{[^{}]*?background(?:-color)?\s*:\s*"
    r"(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))\b",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ColorModeReport:
    """What the guard found and what it did about it."""
    requested: str = ""
    detected: str = ""
    background: str = ""
    matched: bool = True
    repainted: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def mismatch(self) -> bool:
        return not self.matched


def page_background(html: str) -> str:
    """The colour the page actually paints behind everything, or ''.

    Reads the generator's own contract first (``--bg-color`` and its
    aliases), then a literal ``body { background: … }``, then the Tailwind
    config's ``background`` entry.
    """
    palette = detect_palette(html or "")
    if palette.get("background"):
        return palette["background"]
    match = _BODY_BG_RE.search(html or "")
    if match:
        return normalize_hex(match.group(1)) or ""
    return ""


def detect_color_mode(html: str) -> str:
    """'dark', 'light' or '' when the page states no background at all.

    Anything between the two thresholds is deliberately reported as the mode
    it is CLOSER to, so a mid-grey page never silently satisfies both.
    """
    background = page_background(html)
    if not background:
        return ""
    luminance = relative_luminance(background)
    if luminance <= DARK_MAX_LUMINANCE:
        return "dark"
    if luminance >= LIGHT_MIN_LUMINANCE:
        return "light"
    return "dark" if luminance < 0.5 else "light"


def matches_color_mode(html: str, color_mode: str) -> bool:
    """True when the page honours the mode (or states no background)."""
    wanted = "dark" if str(color_mode or "").lower() == "dark" else "light"
    detected = detect_color_mode(html)
    return not detected or detected == wanted


def _target_palette(html: str, color_mode: str, palette: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Brand roles from the page, neutral roles forced to match the mode."""
    wants_dark = color_mode == "dark"
    defaults = DARK_NEUTRALS if wants_dark else LIGHT_NEUTRALS
    supplied = {k: v for k, v in (palette or {}).items() if normalize_hex(str(v or ""))}

    target: Dict[str, str] = {}
    # Keep whatever brand colours the page already carries.
    current = detect_palette(html)
    for role in ("primary", "secondary", "accent"):
        value = normalize_hex(str(supplied.get(role) or current.get(role) or ""))
        if value:
            target[role] = value

    for role in _NEUTRAL_ROLES:
        candidate = normalize_hex(str(supplied.get(role) or ""))
        # A supplied neutral is only usable if it is on the right side of the
        # line — a "dark" palette carrying a cream background is the bug.
        if candidate:
            luminance = relative_luminance(candidate)
            on_side = luminance <= DARK_MAX_LUMINANCE if wants_dark else luminance >= LIGHT_MIN_LUMINANCE
            if role in ("text", "text_muted"):
                on_side = luminance >= LIGHT_MIN_LUMINANCE if wants_dark else luminance <= DARK_MAX_LUMINANCE
            if role == "border":
                on_side = True
            if on_side:
                target[role] = candidate
                continue
        target[role] = defaults[role]
    return target


def _override_stylesheet(color_mode: str) -> str:
    """Re-point the Tailwind neutral utilities at the repainted variables.

    Only emitted as part of a repair. The variables alone are not enough:
    a generated page writes most of its colour as utility classes, so a
    correct ``--bg-color`` with `bg-white` cards still renders light.
    """
    surface = ",".join(f".{c}" for c in _SURFACE_CLASSES)
    body_bg = ",".join(f".{c}" for c in _BODY_BG_CLASSES)
    strong = ",".join(f".{c}" for c in _TEXT_STRONG_CLASSES)
    muted = ",".join(f".{c}" for c in _TEXT_MUTED_CLASSES)
    borders = ",".join(f".{c}" for c in _BORDER_CLASSES)
    return f"""
<!-- BinaApp colour-mode guard ({color_mode}) -->
<style id="{_STYLE_ID}">
body {{ background-color: var(--bg-color) !important; color: var(--text-color) !important; }}
{surface} {{ background-color: var(--surface-color) !important; }}
{body_bg} {{ background-color: var(--bg-color) !important; }}
{strong} {{ color: var(--text-color) !important; }}
{muted} {{ color: var(--text-muted-color) !important; }}
{borders} {{ border-color: var(--border-color, var(--surface-color)) !important; }}
</style>
"""


def enforce_color_mode(
    html: str,
    color_mode: str,
    palette: Optional[Dict[str, str]] = None,
) -> tuple:
    """Make ``html`` honour ``color_mode``. Returns ``(html, ColorModeReport)``.

    A page that already matches is returned byte-for-byte unchanged, so this
    is safe to call unconditionally on every generation path and idempotent
    across re-publishes.
    """
    wanted = "dark" if str(color_mode or "").lower() == "dark" else "light"
    report = ColorModeReport(requested=wanted)
    if not html or not html.strip():
        report.notes.append("empty_html")
        return html, report

    report.background = page_background(html)
    report.detected = detect_color_mode(html)
    if not report.detected:
        # No stated background at all — nothing to contradict, and inventing
        # one here would be the guard picking the design.
        report.notes.append("no_background_declared")
        return html, report

    report.matched = report.detected == wanted
    if report.matched:
        return html, report

    target = _target_palette(html, wanted, palette)
    patched = apply_theme(html, palette=target)
    out = patched.html
    report.notes.extend(patched.notes)

    # Replace (never stack) the override stylesheet, then place it LAST in
    # <head> so it wins over the generator's own <style> block.
    out = _STYLE_BLOCK_RE.sub("", out)
    block = _override_stylesheet(wanted)
    if re.search(r"</head\s*>", out, re.IGNORECASE):
        out = re.sub(r"</head\s*>", block + "</head>", out, count=1, flags=re.IGNORECASE)
    elif re.search(r"<body\b[^>]*>", out, re.IGNORECASE):
        out = re.sub(r"(<body\b[^>]*>)", r"\1" + block, out, count=1, flags=re.IGNORECASE)
    else:
        out = block + out

    report.repainted = True
    report.notes.append(
        f"repainted {report.detected} -> {wanted} (was {report.background or 'unknown'})"
    )
    return out, report
