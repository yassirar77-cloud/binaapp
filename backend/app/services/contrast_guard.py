"""WCAG contrast, checked and repaired deterministically.

WHY THIS EXISTS
---------------
A generated page shipped with gold eyebrow labels on a cream page:

    #C9A96E on #F5F3EF  ->  2.02:1   (AA body text needs 4.5:1)
    #C9A96E on #EBE7E0  ->  1.82:1
    #C9A96E on #1F3A2F  ->  5.51:1   (fine — the same gold, a dark band)

Every "WARISAN KAMI" / "HIDANGAN ISTIMEWA" label on the page was effectively
invisible. Nothing in the pipeline measured this: design_director asked only
that ``primary`` clear **2.0:1** against the background, and never looked at
``accent`` at all.

The last line above is why the repair here is conservative. The same accent
is readable on one of the page's own backgrounds and unreadable on another,
so "darken the gold" globally would fix the labels and break the band. This
module therefore:

  * ``audit_contrast``  — measures every declared foreground/background pair
    and reports the failures (the validator surfaces these as warnings);
  * ``enforce_contrast`` — rewrites a failing palette TOKEN only when a value
    exists that clears the threshold against **every** background colour the
    document actually paints. When no such value exists it changes nothing
    and says so, rather than trading one unreadable pairing for another.

The real prevention lives one step earlier: design_director now requires
accent and primary to clear 4.5:1 against background and surface before the
palette is ever handed to the model.

Pure functions. No I/O, no globals.
"""

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.services.theme_patcher import (
    contrast_ratio,
    detect_palette,
    is_greyscale,
    normalize_hex,
    relative_luminance,
)

#: WCAG AA for body-size text. Muted/secondary text is decorative meta and
#: gets the large-text threshold, matching design_director's own constants.
AA_TEXT = 4.5
AA_LARGE = 3.0

#: Foreground role -> threshold it must clear against the page backgrounds.
_FOREGROUND_THRESHOLDS = {
    "text": AA_TEXT,
    "primary": AA_TEXT,
    "accent": AA_TEXT,
    "secondary": AA_TEXT,
    "text_muted": AA_LARGE,
}
_BACKGROUND_ROLES = ("background", "surface")

#: Colours the document paints behind content: `background:#hex`,
#: `background-color:#hex`, and Tailwind arbitrary values `bg-[#hex]`.
_BG_HEX_RE = re.compile(
    r"background(?:-color)?\s*:\s*(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))\b"
    r"|\bbg-\[(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))\]",
    re.IGNORECASE,
)


@dataclass
class ContrastIssue:
    foreground: str
    background: str
    ratio: float
    required: float
    role: str = ""

    def __str__(self) -> str:
        return (
            f"{self.role or 'colour'} {self.foreground} on {self.background} "
            f"= {self.ratio}:1 (needs {self.required}:1)"
        )


@dataclass
class ContrastReport:
    issues: List[ContrastIssue] = field(default_factory=list)
    #: role -> (old hex, new hex) for tokens this module actually rewrote.
    repairs: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _to_hls(hex_value: str) -> Tuple[float, float, float]:
    normalized = normalize_hex(hex_value) or "#000000"
    r = int(normalized[1:3], 16) / 255.0
    g = int(normalized[3:5], 16) / 255.0
    b = int(normalized[5:7], 16) / 255.0
    return colorsys.rgb_to_hls(r, g, b)


def _from_hls(h: float, l: float, s: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, min(max(l, 0.0), 1.0), s)
    return "#{:02X}{:02X}{:02X}".format(
        round(r * 255), round(g * 255), round(b * 255)
    )


def adjust_for_contrast(
    foreground: str,
    backgrounds: List[str],
    target: float = AA_TEXT,
) -> Optional[str]:
    """A hue-preserving variant of ``foreground`` readable on ALL backgrounds.

    Returns None when no lightness of this hue clears ``target`` everywhere —
    which is the honest answer for an accent used on both a cream page and a
    forest-green band. The caller must then leave the document alone.
    """
    base = normalize_hex(foreground)
    backgrounds = [b for b in (normalize_hex(x) for x in backgrounds) if b]
    if not base or not backgrounds:
        return None

    def passes(candidate: str) -> bool:
        return all(contrast_ratio(candidate, bg) >= target for bg in backgrounds)

    if passes(base):
        return base

    hue, lightness, saturation = _to_hls(base)
    # Try darker and lighter in the same hue; prefer the direction that stays
    # closer to the colour the designer picked.
    best: Optional[str] = None
    best_distance = 2.0
    for direction in (-1, 1):
        for step in range(1, 101):
            candidate = _from_hls(hue, lightness + direction * step / 100.0, saturation)
            if passes(candidate):
                distance = abs(relative_luminance(candidate) - relative_luminance(base))
                if distance < best_distance:
                    best, best_distance = candidate, distance
                break
    return best


def document_backgrounds(html: str, limit: int = 24) -> List[str]:
    """Every colour the document actually paints behind content.

    Includes the declared palette roles plus literal backgrounds the model
    wrote inline — the forest-green band that makes the gold readable exists
    only as a literal, and ignoring it is how a "fix" breaks a good pairing.
    """
    found: List[str] = []
    palette = detect_palette(html or "")
    for role in _BACKGROUND_ROLES:
        value = palette.get(role)
        if value and value not in found:
            found.append(value)
    for match in _BG_HEX_RE.finditer(html or ""):
        raw = match.group(1) or match.group(2)
        value = normalize_hex(raw or "")
        if value and value not in found:
            found.append(value)
        if len(found) >= limit:
            break
    return found


def audit_contrast(html: str) -> List[ContrastIssue]:
    """Failing foreground/background pairs among the DECLARED palette roles.

    Only the declared roles are audited: those are the values the pipeline
    chose and can be held responsible for. Measuring every literal pair in
    the document would report on colours nobody can act on.
    """
    palette = detect_palette(html or "")
    issues: List[ContrastIssue] = []
    for role, threshold in _FOREGROUND_THRESHOLDS.items():
        foreground = palette.get(role)
        if not foreground:
            continue
        for bg_role in _BACKGROUND_ROLES:
            background = palette.get(bg_role)
            if not background or background == foreground:
                continue
            ratio = contrast_ratio(foreground, background)
            if ratio < threshold:
                issues.append(ContrastIssue(
                    foreground=foreground,
                    background=background,
                    ratio=ratio,
                    required=threshold,
                    role=f"{role} on {bg_role}",
                ))
    return issues


def enforce_contrast(html: str) -> tuple:
    """Repair failing palette tokens where it is safe. ``(html, report)``.

    "Safe" means: the replacement clears the threshold against every
    background the document paints, not merely the one it failed on. A token
    with no such replacement is reported and left alone.

    ``text`` and ``background`` are never rewritten here — a page whose body
    text fails against its own background is a colour-mode failure, and
    color_mode_guard owns that repair.
    """
    report = ContrastReport()
    if not html or not html.strip():
        return html, report

    report.issues = audit_contrast(html)
    if not report.issues:
        return html, report

    backgrounds = document_backgrounds(html)
    palette = detect_palette(html)
    out = html

    failing_roles = {
        issue.role.split(" on ")[0]
        for issue in report.issues
        if issue.role.split(" on ")[0] in ("primary", "secondary", "accent", "text_muted")
    }

    for role in sorted(failing_roles):
        current = palette.get(role)
        if not current or is_greyscale(current) and role != "text_muted":
            continue
        threshold = _FOREGROUND_THRESHOLDS[role]
        replacement = adjust_for_contrast(current, backgrounds, threshold)
        if not replacement or replacement == current:
            report.notes.append(
                f"{role} {current}: no variant clears {threshold}:1 on every "
                f"background the page paints ({', '.join(backgrounds[:6])}) — left as is"
            )
            continue
        # Rewrite the TOKEN only. Literal occurrences elsewhere may be sitting
        # on a background this value was chosen for.
        patched, count = _rewrite_token(out, role, replacement)
        if count:
            out = patched
            report.repairs[role] = (current, replacement)
        else:
            report.notes.append(f"{role}: no CSS variable to rewrite")

    return out, report


#: CSS custom-property names per role, mirroring theme_patcher's aliases.
_ROLE_VARS = {
    "primary": ("--primary-color", "--color-primary", "--brand-color", "--primary"),
    "secondary": ("--secondary-color", "--color-secondary", "--secondary"),
    "accent": ("--accent-color", "--color-accent", "--accent"),
    "text_muted": ("--text-muted-color", "--text-muted", "--muted-color", "--text-secondary"),
}


def _rewrite_token(html: str, role: str, new_hex: str) -> Tuple[str, int]:
    total = 0
    out = html
    for name in _ROLE_VARS.get(role, ()):
        pattern = re.compile(
            rf"({re.escape(name)}\s*:\s*)#(?:[0-9a-fA-F]{{3}}|[0-9a-fA-F]{{6}})\b"
        )
        out, count = pattern.subn(rf"\g<1>{new_hex}", out)
        total += count
    return out, total
