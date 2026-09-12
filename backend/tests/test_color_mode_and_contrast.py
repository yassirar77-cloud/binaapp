"""Colour mode is a constraint; contrast is measured, not eyeballed.

Regression cover for the oopoo.binaapp.my report: merchant picked Gelap and
got a cream page, whose gold eyebrow labels sat at 2.02:1 on that cream.
"""

import pytest

from app.services.color_mode_guard import (
    DARK_NEUTRALS,
    detect_color_mode,
    enforce_color_mode,
    matches_color_mode,
    page_background,
)
from app.services.contrast_guard import (
    AA_TEXT,
    adjust_for_contrast,
    audit_contrast,
    document_backgrounds,
    enforce_contrast,
)
from app.services.generation_validator import GenerationBrief, validate_generated_site
from app.services.theme_patcher import contrast_ratio

# The palette the reported page actually shipped.
SHIPPED = (
    '<html><head><style>:root{'
    '--bg-color:#F5F3EF;--surface-color:#EBE7E0;'
    '--text-color:#5C5C5C;--accent-color:#C9A96E;--primary-color:#1F3A2F;'
    '}body{background:var(--bg-color)}</style></head>'
    '<body class="bg-white"><h1 class="text-gray-900">Oopoo</h1>'
    '<section style="background:#1F3A2F"><p style="color:#C9A96E">Warisan</p></section>'
    '</body></html>'
)


class TestDetection:
    def test_reads_the_declared_background(self):
        assert page_background(SHIPPED) == "#F5F3EF"
        assert detect_color_mode(SHIPPED) == "light"

    def test_reads_a_literal_body_background(self):
        html = "<html><head><style>body { background-color: #101014; }</style></head></html>"
        assert detect_color_mode(html) == "dark"

    def test_no_background_declared_is_not_a_verdict(self):
        assert detect_color_mode("<html><body>hi</body></html>") == ""
        # ...and therefore contradicts nothing.
        assert matches_color_mode("<html><body>hi</body></html>", "dark")


class TestEnforcement:
    def test_a_light_page_asked_to_be_dark_is_repainted(self):
        out, report = enforce_color_mode(SHIPPED, "dark")
        assert report.mismatch and report.repainted
        assert detect_color_mode(out) == "dark"

    def test_the_repaint_also_covers_tailwind_neutral_utilities(self):
        # The variables alone are not enough: the page writes most of its
        # colour as utility classes, so bg-white cards stay white without this.
        out, _ = enforce_color_mode(SHIPPED, "dark")
        assert 'id="binaapp-color-mode"' in out
        assert ".bg-white" in out and ".text-gray-900" in out

    def test_brand_colours_survive_the_repaint(self):
        out, _ = enforce_color_mode(SHIPPED, "dark")
        assert "#C9A96E" in out  # the gold is the brand, not the mode

    def test_a_matching_page_is_returned_byte_for_byte(self):
        dark = SHIPPED.replace("#F5F3EF", DARK_NEUTRALS["background"])
        out, report = enforce_color_mode(dark, "dark")
        assert out == dark
        assert report.matched and not report.repainted

    def test_idempotent(self):
        once, _ = enforce_color_mode(SHIPPED, "dark")
        twice, report = enforce_color_mode(once, "dark")
        assert twice == once and not report.repainted

    def test_empty_html_is_survivable(self):
        out, report = enforce_color_mode("", "dark")
        assert out == "" and "empty_html" in report.notes


class TestValidatorBlocksTheMismatch:
    def test_mismatch_is_an_error(self):
        brief = GenerationBrief(business_name="Oopoo", color_mode="dark")
        codes = {e.code for e in validate_generated_site(SHIPPED, brief).errors}
        assert "color_mode_mismatch" in codes

    def test_no_preference_means_no_opinion(self):
        brief = GenerationBrief(business_name="Oopoo")
        codes = {e.code for e in validate_generated_site(SHIPPED, brief).errors}
        assert "color_mode_mismatch" not in codes


class TestContrastAudit:
    def test_it_finds_the_gold_on_cream(self):
        issues = {(i.foreground, i.background): i.ratio for i in audit_contrast(SHIPPED)}
        assert issues[("#C9A96E", "#F5F3EF")] == pytest.approx(2.02, abs=0.05)
        assert issues[("#C9A96E", "#EBE7E0")] == pytest.approx(1.82, abs=0.05)

    def test_literal_section_backgrounds_count(self):
        # The forest-green band exists only as an inline literal, and it is
        # the reason the same gold must not simply be darkened.
        assert "#1F3A2F" in document_backgrounds(SHIPPED)

    def test_surfaced_as_a_warning_not_a_block(self):
        result = validate_generated_site(SHIPPED, GenerationBrief(business_name="Oopoo"))
        assert any(w.code == "low_contrast" for w in result.warnings)
        assert not any(e.code == "low_contrast" for e in result.errors)


class TestContrastRepair:
    def test_adjusts_within_the_same_hue(self):
        out = adjust_for_contrast("#C9A96E", ["#F5F3EF"], AA_TEXT)
        assert out is not None
        assert contrast_ratio(out, "#F5F3EF") >= AA_TEXT

    def test_refuses_when_no_value_works_everywhere(self):
        # Readable on cream AND on forest green is not reachable in this hue.
        assert adjust_for_contrast("#C9A96E", ["#F5F3EF", "#1F3A2F"], AA_TEXT) is None

    def test_leaves_the_document_alone_when_it_cannot_repair_safely(self):
        out, report = enforce_contrast(SHIPPED)
        assert out == SHIPPED
        assert report.repairs == {}
        assert any("left as is" in n for n in report.notes)

    def test_repairs_the_token_when_it_is_safe(self):
        html = SHIPPED.replace('background:#1F3A2F', 'background:#FFFFFF')
        out, report = enforce_contrast(html)
        old, new = report.repairs["accent"]
        assert old == "#C9A96E" and new != old
        assert f"--accent-color:{new}" in out
        for background in document_backgrounds(out):
            assert contrast_ratio(new, background) >= AA_TEXT

    def test_a_clean_palette_is_untouched(self):
        html = (
            '<html><head><style>:root{--bg-color:#FFFFFF;--surface-color:#FFFFFF;'
            '--text-color:#111827;--accent-color:#8A6D2F}</style></head><body></body></html>'
        )
        out, report = enforce_contrast(html)
        assert out == html and report.ok
