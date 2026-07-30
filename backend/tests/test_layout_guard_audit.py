"""P3: Layout Safety Guard telemetry + the one upstream fix.

The guard CSS ships ~200 lines to every visitor and patches generator defects
at serve time. Nothing may be removed on reasoning alone, so this suite pins
the detector behaviour that will produce the evidence for retiring rules —
plus the one defect whose cause was our own code (e_stripped_bg) and is now
fixed at source.

See docs/LAYOUT_SAFETY_GUARD_AUDIT.md.
"""

import pytest

from app.services.layout_guard_audit import (
    audit_layout_guards,
    firing_guards,
    guard_verdicts,
)
from app.services.templates import _repaint_emptied_background_urls


CLEAN_PAGE = """<!DOCTYPE html>
<html lang="ms"><head><style>html{scroll-padding-top:5rem;}</style></head>
<body>
<header class="fixed top-0"><a href="#menu">Menu</a></header>
<section id="home">
  <img src="https://cdn.test/hero.jpg" alt="Nasi campur di kaunter">
  <div class="grid"><div class="min-w-0"><span>RM7</span></div></div>
</section>
<section id="menu"><div class="grid">
  <div class="card"><img src="https://cdn.test/a.jpg" alt="Nasi Campur"></div>
  <div class="card"><img src="https://cdn.test/b.jpg" alt="Ayam Masak Merah"></div>
</div></section>
<a id="whatsapp-button" class="fixed bottom-5 right-5" href="https://wa.me/60193456781">WA</a>
</body></html>"""


class TestCleanPageFiresNothingAvoidable:
    def test_clean_page_only_needs_the_aos_guard(self):
        fired = firing_guards(CLEAN_PAGE)
        assert fired == [], f"clean page should need no guards, got {fired}"

    def test_aos_guard_fires_whenever_aos_is_used(self):
        """Not a defect — it guards a third-party CDN failure."""
        html = CLEAN_PAGE.replace('<section id="home">',
                                  '<section id="home" data-aos="fade-up">')
        assert "a_aos_rescue" in firing_guards(html)


class TestDetectors:
    def test_missing_scroll_padding(self):
        html = CLEAN_PAGE.replace("<style>html{scroll-padding-top:5rem;}</style>", "")
        assert "a0_scroll_padding" in firing_guards(html)

    def test_min_h_screen_on_non_hero_section(self):
        html = CLEAN_PAGE.replace('<section id="menu">',
                                  '<section id="menu" class="min-h-screen">')
        assert "b1_section_height_cap" in firing_guards(html)

    def test_min_h_screen_on_hero_is_allowed(self):
        html = CLEAN_PAGE.replace('<section id="home">',
                                  '<section id="home" class="min-h-screen">')
        assert "b1_section_height_cap" not in firing_guards(html)

    def test_hero_with_no_image(self):
        html = CLEAN_PAGE.replace(
            '<img src="https://cdn.test/hero.jpg" alt="Nasi campur di kaunter">', ""
        )
        assert "b2_empty_hero_cap" in firing_guards(html)

    def test_menu_cards_missing_images(self):
        html = CLEAN_PAGE.replace(
            '<div class="card"><img src="https://cdn.test/b.jpg" alt="Ayam Masak Merah"></div>',
            '<div class="card"><h3>Ayam Masak Merah</h3></div>',
        )
        assert "c_menu_grid" in firing_guards(html)

    def test_empty_aspect_box_outside_menu(self):
        html = CLEAN_PAGE.replace(
            "</body>", '<section id="about"><div class="aspect-[4/3] bg-gray-100"></div></section></body>'
        )
        assert "d_empty_media_box" in firing_guards(html)

    def test_aspect_box_with_an_image_is_fine(self):
        html = CLEAN_PAGE.replace(
            "</body>",
            '<section id="about"><div class="aspect-[4/3]">'
            '<img src="https://cdn.test/c.jpg" alt="Dapur"></div></section></body>',
        )
        assert "d_empty_media_box" not in firing_guards(html)

    def test_stat_grid_without_min_w_0(self):
        html = CLEAN_PAGE.replace('<div class="grid"><div class="min-w-0">',
                                  '<div class="grid"><div>')
        assert "f_stat_overflow" in firing_guards(html)

    def test_unpinned_whatsapp_button(self):
        html = CLEAN_PAGE.replace('id="whatsapp-button" class="fixed bottom-5 right-5"',
                                  'id="whatsapp-button" class="rounded-full"')
        assert "whatsapp_pin" in firing_guards(html)


class TestStrippedBackgroundFixedUpstream:
    """e_stripped_bg was OUR defect: the image safety guard blanked a banned
    URL and left `background-image: url()`. Fixed at source."""

    @pytest.mark.parametrize("style", [
        "background-image: url()",
        "background-image:url()",
        "background-image: url('')",
        'background-image:url("")',
    ])
    def test_emptied_urls_are_repainted(self, style):
        out = _repaint_emptied_background_urls(f'<div style="{style}">x</div>')
        assert "linear-gradient" in out
        assert "url()" not in out

    def test_real_urls_untouched(self):
        html = '<div style="background-image: url(https://cdn.test/a.jpg)">x</div>'
        assert _repaint_emptied_background_urls(html) == html

    def test_detector_agrees_after_the_fix(self):
        broken = '<html><body><div style="background-image: url()">x</div></body></html>'
        assert "e_stripped_bg" in firing_guards(broken)
        assert "e_stripped_bg" not in firing_guards(_repaint_emptied_background_urls(broken))

    def test_no_op_without_any_url(self):
        assert _repaint_emptied_background_urls("<p>hi</p>") == "<p>hi</p>"


class TestAuditContract:
    def test_every_guard_has_a_verdict(self):
        verdicts = guard_verdicts()
        assert set(verdicts) == set(audit_layout_guards(CLEAN_PAGE))
        for guard, probe in verdicts.items():
            assert probe.upstream, guard
            assert probe.verdict in {
                "keep", "fixable", "fixed-pending-telemetry", "fixed-upstream"
            }, (guard, probe.verdict)

    def test_aos_guard_is_marked_keep(self):
        """It guards a third-party CDN, not a generator defect."""
        assert guard_verdicts()["a_aos_rescue"].verdict == "keep"

    def test_stripped_bg_is_the_only_fixed_upstream_guard(self):
        fixed = [g for g, p in guard_verdicts().items() if p.verdict == "fixed-upstream"]
        assert fixed == ["e_stripped_bg"]

    def test_audit_is_pure_and_never_raises(self):
        for html in ("", "<html", "<<>>", "<section id='home'>", "&&&", None):
            audit_layout_guards(html or "")

    def test_audit_is_deterministic(self):
        assert audit_layout_guards(CLEAN_PAGE) == audit_layout_guards(CLEAN_PAGE)
