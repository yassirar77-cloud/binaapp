"""An element the page's own CSS hides on phones must actually hide.

agp: <nav class="desktop-nav flex ..."> with @media (max-width:767px)
{.desktop-nav{display:none}}; Tailwind's later .flex won, the desktop nav
showed on phones and the page was 632px wide on a 390px screen."""

import os
import sys

from app.services.display_conflicts import fix_hidden_display_conflicts, hidden_below

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from verify_site_menu import _display_conflicts  # noqa: E402

PAGE = """<html><head><style>
.mobile-menu { display: none; }
@media (max-width: 767px) { .mobile-menu { display: block; } .desktop-nav { display: none; } }
@media (max-width: 639px) { .wide-only, .also { display:none } }
</style></head><body><header>
<nav class="desktop-nav flex items-center gap-6"><a href="#menu">Menu</a></nav>
<button class="mobile-menu p-2">=</button>
<div class="wide-only grid grid-cols-3">x</div>
<div class="other flex">y</div>
</header></body></html>"""


def test_hidden_classes_and_breakpoints():
    assert hidden_below(PAGE) == {"desktop-nav": "md", "wide-only": "sm", "also": "sm"}


def test_tailwind_display_class_becomes_hidden_plus_breakpoint():
    out, n = fix_hidden_display_conflicts(PAGE)
    assert n == 2
    assert '<nav class="desktop-nav hidden md:flex items-center gap-6">' in out
    assert '<div class="wide-only hidden sm:grid grid-cols-3">' in out
    # Unrelated elements and the mobile button are untouched.
    assert '<div class="other flex">' in out and '<button class="mobile-menu p-2">' in out
    assert fix_hidden_display_conflicts(out) == (out, 0)


def test_no_media_rule_no_change():
    page = '<style>.desktop-nav{display:flex}</style><nav class="desktop-nav flex"></nav>'
    assert fix_hidden_display_conflicts(page) == (page, 0)


def test_verify_script_flags_the_conflict():
    assert _display_conflicts(PAGE)
    fixed, _ = fix_hidden_display_conflicts(PAGE)
    assert not _display_conflicts(fixed)
