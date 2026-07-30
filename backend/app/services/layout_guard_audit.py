"""Telemetry for the Layout Safety Guard CSS (P3).

LAYOUT_SAFETY_CSS is ~200 lines of well-written CSS that ships to every
visitor of every generated site. Each rule in it patches a generator defect
at serve time: empty heroes, stalled AOS, misapplied min-h-screen, empty
image containers, stripped background URLs, overflowing grid labels.

It treats symptoms. Every guard is evidence of a defect that belongs upstream
as a prompt constraint or a post-generation fix — but removing one blind
risks re-exposing a bug on live merchant sites, and nobody currently knows
which guards still fire.

This module answers that. It is a PURE FUNCTION of html -> which guards WOULD
fire, so it can run on every generation, log the result, and build the
evidence base for retiring rules safely. It changes nothing about the page.

Read the verdicts in docs/LAYOUT_SAFETY_GUARD_AUDIT.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class GuardProbe:
    """One guard, and how to detect the condition it exists to patch."""
    guard: str          # rule id in LAYOUT_SAFETY_CSS
    upstream: str       # the generator defect it patches
    verdict: str        # keep | fixable | fixed-pending-telemetry


def _body(html: str) -> str:
    return _SCRIPT_STYLE_RE.sub(" ", html or "")


# --- detectors -------------------------------------------------------------
# Each returns True when the guard WOULD have work to do on this page.

def _needs_scroll_padding(html: str) -> bool:
    """(a0) fixed header + in-page anchors, and no scroll-padding of its own."""
    body = _body(html)
    has_fixed_nav = bool(re.search(r"<(?:header|nav)\b[^>]*class=[\"'][^\"']*\bfixed\b", body, re.I))
    has_anchor = bool(re.search(r'href=["\']#[a-z]', body, re.I))
    declares = "scroll-padding-top" in (html or "")
    return has_fixed_nav and has_anchor and not declares


def _needs_aos_rescue(html: str) -> bool:
    """(a) AOS attributes present — the guard is the fallback if aos.js fails.

    Always 'fires' in the sense of being load-bearing whenever data-aos is
    used, because it guards a third-party CDN failure we do not control.
    """
    return "data-aos" in (html or "")


def _needs_section_height_cap(html: str) -> bool:
    """(b1) min-h-screen / h-screen on a NON-hero section."""
    for match in re.finditer(r"<section\b([^>]*)>", _body(html), re.I):
        attrs = match.group(1)
        if not re.search(r"\b(?:min-h-screen|h-screen)\b", attrs):
            continue
        ident = re.search(r'id=["\']([^"\']+)["\']', attrs)
        if not ident or ident.group(1).lower() not in (
            "home", "hero", "laman-utama", "page-order"
        ):
            return True
    return False


def _needs_empty_hero_cap(html: str) -> bool:
    """(b2) hero section with no <img> and no inline background-image."""
    for match in re.finditer(
        r'<section\b[^>]*id=["\'](home|hero|laman-utama)["\'][^>]*>(.*?)</section>',
        _body(html), re.I | re.S,
    ):
        inner = match.group(2)
        if "<img" not in inner.lower() and "background-image" not in inner.lower():
            return True
    return False


def _needs_menu_grid_fix(html: str) -> bool:
    """(c) a menu grid where some cards have images and some do not."""
    for match in re.finditer(
        r'<section\b[^>]*id=["\'][^"\']*menu[^"\']*["\'][^>]*>(.*?)</section>',
        _body(html), re.I | re.S,
    ):
        cards = re.findall(r"<div\b[^>]*>", match.group(1))
        if not cards:
            continue
        inner = match.group(1)
        images = inner.lower().count("<img")
        # Uneven when there are cards but fewer images than cards.
        card_like = len(re.findall(r'class=["\'][^"\']*\b(?:card|rounded-)', inner, re.I))
        if card_like and images < card_like:
            return True
    return False


def _needs_empty_media_box_fix(html: str) -> bool:
    """(d) an aspect-ratio box outside the menu with no media inside."""
    for match in re.finditer(
        r'<div\b([^>]*class=["\'][^"\']*aspect-[^"\']*["\'][^>]*)>(.*?)</div>',
        _body(html), re.I | re.S,
    ):
        attrs, inner = match.group(1), match.group(2)
        if "gradient" in attrs.lower() or "background-image" in attrs.lower():
            continue
        if not re.search(r"<(?:img|picture|svg|i|video|iframe)\b", inner, re.I):
            return True
    return False


def _needs_stripped_bg_repaint(html: str) -> bool:
    """(e) an emptied `background-image: url()` — now fixed upstream."""
    return bool(re.search(
        r"background-image\s*:\s*url\(\s*['\"]?\s*['\"]?\s*\)", html or "", re.I
    ))


def _needs_stat_overflow_fix(html: str) -> bool:
    """(f) a hero/header grid whose cells lack min-w-0."""
    for match in re.finditer(
        r'<(?:section\b[^>]*id=["\'](?:home|hero)["\']|header\b)[^>]*>(.*?)'
        r"</(?:section|header)>",
        _body(html), re.I | re.S,
    ):
        inner = match.group(1)
        if re.search(r'class=["\'][^"\']*\bgrid\b', inner, re.I) and "min-w-0" not in inner:
            return True
    return False


def _needs_whatsapp_pin(html: str) -> bool:
    """(b cont.) floating WhatsApp button without its own fixed positioning."""
    match = re.search(r'<[^>]*id=["\']whatsapp-button["\']([^>]*)>', html or "", re.I)
    if not match:
        return False
    attrs = match.group(1)
    return "fixed" not in attrs.lower()


_PROBES: List[tuple] = [
    (GuardProbe("a0_scroll_padding", "generated page omits scroll-padding-top under a fixed nav",
                "fixed-pending-telemetry"), _needs_scroll_padding),
    (GuardProbe("a_aos_rescue", "third-party aos.js may fail or stall (NOT a generator defect)",
                "keep"), _needs_aos_rescue),
    (GuardProbe("b1_section_height_cap", "min-h-screen emitted on non-hero sections",
                "fixable"), _needs_section_height_cap),
    (GuardProbe("b2_empty_hero_cap", "100vh hero emitted with no image behind it",
                "fixable"), _needs_empty_hero_cap),
    (GuardProbe("c_menu_grid", "menu cards mix image and no-image, collapsing heights",
                "fixed-pending-telemetry"), _needs_menu_grid_fix),
    (GuardProbe("d_empty_media_box", "aspect-ratio media box emitted with nothing in it",
                "fixed-pending-telemetry"), _needs_empty_media_box_fix),
    (GuardProbe("e_stripped_bg", "OUR image safety guard left `background-image: url()`",
                "fixed-upstream"), _needs_stripped_bg_repaint),
    (GuardProbe("f_stat_overflow", "hero stat grid cells lack min-w-0, long Malay labels collide",
                "fixed-pending-telemetry"), _needs_stat_overflow_fix),
    (GuardProbe("whatsapp_pin", "injected WhatsApp button relies on the guard for positioning",
                "fixable"), _needs_whatsapp_pin),
]


def audit_layout_guards(html: str) -> Dict[str, bool]:
    """Which guards WOULD fire on this page. Pure; never raises."""
    result: Dict[str, bool] = {}
    for probe, detector in _PROBES:
        try:
            result[probe.guard] = bool(detector(html))
        except Exception:
            result[probe.guard] = False
    return result


def firing_guards(html: str) -> List[str]:
    """Just the guard ids with work to do — the shape worth logging."""
    return [name for name, fired in audit_layout_guards(html).items() if fired]


def guard_verdicts() -> Dict[str, GuardProbe]:
    """The audit table, for docs and tests."""
    return {probe.guard: probe for probe, _ in _PROBES}
