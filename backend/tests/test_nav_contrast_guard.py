"""The serve-time nav contrast guard and the img-attribute fix (jojokitchen,
2026-10-29).

The page shipped a navigation bar painted `rgba(43,30,26,0.9)` by its own
stylesheet with `#1C1917` links on it — a dark bar with near-black text on
a light page, unreadable. No static pass sees a background a page sets in
its own <style>, so the guard is a script the browser runs: it reads each
nav text's computed colour against the first opaque background above it
and repaints only what fails 3:1. It ships with the layout guard, so it is
stripped and re-injected the same way (self-upgrading on every serve, never
duplicated, never left in the HTML the editor model sees).
"""

import re

from app.services.edit_guards import _LAYOUT_GUARD_BLOCK_RE
from app.services.quality_floor import _with_attrs, apply_quality_floor
from app.services.templates import TemplateService, template_service

PAGE = (
    "<html><head><style>.nav-blur{background-color:rgba(43,30,26,0.9)}</style></head>"
    '<body><header class="nav-blur"><nav><a class="text-[#1C1917]" href="#hero">Kedai</a></nav></header>'
    '<section id="hero"><h1>Hai</h1></section></body></html>'
)


class TestInjection:
    def test_the_script_rides_with_the_layout_guard(self):
        out = template_service.apply_layout_safety_guard(PAGE)
        assert out.count('id="binaapp-layout-safety"') == 1
        assert out.count('id="binaapp-nav-contrast"') == 1
        assert out.index('id="binaapp-nav-contrast"') < out.index("</head>")

    def test_applying_twice_is_applying_once(self):
        once = template_service.apply_layout_safety_guard(PAGE)
        twice = template_service.apply_layout_safety_guard(once)
        # (The guard has always left one extra newline per pass before </head>.)
        assert re.sub(r"\s+", "", twice) == re.sub(r"\s+", "", once)
        assert twice.count("<script id=\"binaapp-nav-contrast\">") == 1

    def test_an_old_copy_is_replaced_not_stacked(self):
        stale = PAGE.replace(
            "</head>",
            '<!-- BinaApp Nav Contrast Guard --><script id="binaapp-nav-contrast">old();</script></head>',
        )
        out = template_service.apply_layout_safety_guard(stale)
        assert "old();" not in out
        assert out.count('id="binaapp-nav-contrast"') == 1

    def test_the_edit_path_strips_it_before_the_model_sees_the_page(self):
        out = template_service.apply_layout_safety_guard(PAGE)
        bare = _LAYOUT_GUARD_BLOCK_RE.sub("", out)
        assert "binaapp-nav-contrast" not in bare
        assert "binaapp-layout-safety" not in bare
        assert ".nav-blur" in bare  # the merchant's own stylesheet survives

    def test_the_script_is_scoped_to_navigation_and_judges_nothing_transparent(self):
        js = TemplateService.NAV_CONTRAST_GUARD_JS
        assert "querySelectorAll('header,body>nav')" in js
        # A nav with no opaque background above it (transparent over the hero)
        # is left alone, as is any control that paints its own surface.
        assert "if(!rootBg)return;" in js
        assert "control=(e.tagName==='A'||e.tagName==='BUTTON')" in js
        assert "var MIN=3" in js
        # An icon-only control (the hamburger) carries no text node but its
        # icon inherits the colour, so it is judged too.
        assert "el.querySelector('i,svg')" in js
        # Nothing in the block is a Python escape gone wrong.
        assert re.search(r"/rgba\?\\\(", js)


class TestImgAttributes:
    def test_attributes_land_before_a_self_closing_slash(self):
        assert _with_attrs('<img src="a.jpg"/>', 'decoding="async"') == '<img src="a.jpg" decoding="async"/>'
        assert _with_attrs('<img src="a.jpg" />', 'loading="lazy"') == '<img src="a.jpg" loading="lazy"/>'
        assert _with_attrs('<img src="a.jpg">', 'loading="lazy"') == '<img src="a.jpg" loading="lazy">'

    def test_the_floor_no_longer_writes_a_slash_before_the_attribute(self):
        html = (
            "<html><head></head><body>"
            '<img src="https://res.cloudinary.com/d/image/upload/w_1600,h_900/a.jpg" alt=""/>'
            '<img src="https://res.cloudinary.com/d/image/upload/w_900,h_675/b.jpg" alt=""/>'
            "</body></html>"
        )
        out, _ = apply_quality_floor(html, language="ms")
        assert "/ decoding=" not in out and "/ loading=" not in out and "/ width=" not in out
        assert 'loading="lazy" decoding="async" width="900" height="675"/>' in out
        assert 'loading="eager" fetchpriority="high"' in out
