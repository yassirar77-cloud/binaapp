"""M0 quality-harness lint tests.

Two layers:
  1. Unit tests of the lint functions with synthetic HTML.
  2. A CI gate over every committed preview in docs/previews/ — the V2
     assembler's own demo output must stay compliant (no forbidden wording,
     balanced, widget-injectable).
"""

from pathlib import Path

import pytest

from app.utils.output_lint import (
    contrast_ratio,
    extract_root_hex_vars,
    find_forbidden_wording,
    find_language_leakage,
    lint_html,
)

PREVIEWS_DIR = Path(__file__).resolve().parents[2] / "docs" / "previews"

GOOD_PAGE = """<!DOCTYPE html>
<html lang="ms">
<head><style>:root { --color-text: #1C1917; --color-background: #FFFBF5; }</style></head>
<body>
<nav><a href="#home">Laman Utama</a><a href="#menu">Menu</a></nav>
<section><h1>Restoran Contoh</h1><p>Pengusaha Muslim · Sejak 1998</p></section>
</body>
</html>"""


class TestForbiddenWording:
    def test_clean_page_passes(self):
        assert find_forbidden_wording(GOOD_PAGE) == []

    @pytest.mark.parametrize(
        "phrase",
        ["Halal Certified", "halal certified", "SIJIL HALAL", "Jakim", "100% Halal"],
    )
    def test_forbidden_phrases_detected(self, phrase):
        html = GOOD_PAGE.replace("Pengusaha Muslim", phrase)
        assert find_forbidden_wording(html), phrase
        report = lint_html(html, language="ms")
        assert not report.ok
        assert any("forbidden wording" in i for i in report.issues)

    def test_pengusaha_muslim_is_allowed(self):
        report = lint_html(GOOD_PAGE, language="ms")
        assert report.ok, report.issues


class TestStructuralContract:
    def test_missing_closing_body_flagged(self):
        html = GOOD_PAGE.replace("</body>", "")
        report = lint_html(html)
        assert any("</body>" in i for i in report.issues)

    def test_missing_doctype_flagged(self):
        html = GOOD_PAGE.replace("<!DOCTYPE html>", "")
        report = lint_html(html)
        assert any("DOCTYPE" in i for i in report.issues)

    def test_unbalanced_html_flagged(self):
        html = GOOD_PAGE.replace("</section>", "")
        report = lint_html(html)
        assert any("unbalanced" in i for i in report.issues)

    def test_website_id_marker_optional_then_required(self):
        assert lint_html(GOOD_PAGE).ok
        report = lint_html(GOOD_PAGE, require_website_id=True)
        assert any("data-website-id" in i for i in report.issues)
        marked = GOOD_PAGE.replace("<body>", '<body data-website-id="abc-123">')
        assert lint_html(marked, require_website_id=True).ok

    def test_empty_html(self):
        assert not lint_html("").ok


class TestLanguage:
    def test_ms_page_with_english_nav_flagged(self):
        html = GOOD_PAGE.replace("Laman Utama", "Home")
        assert find_language_leakage(html, "ms") == ["Home"]
        report = lint_html(html, language="ms")
        assert any("wrong-language" in i for i in report.issues)

    def test_en_page_with_ms_nav_flagged(self):
        html = GOOD_PAGE.replace('lang="ms"', 'lang="en"')
        assert "Laman Utama" in find_language_leakage(html, "en")

    def test_lang_attribute_mismatch_flagged(self):
        report = lint_html(GOOD_PAGE, language="en")
        assert any("lang attribute" in i for i in report.issues)

    def test_body_copy_can_mix_languages(self):
        # Dish names / brand words in body copy must not trip the check.
        html = GOOD_PAGE.replace("Sejak 1998", "Best roti canai in town since 1998")
        assert find_language_leakage(html, "ms") == []


class TestContrast:
    def test_ratio_black_on_white(self):
        assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.1)

    def test_low_contrast_tokens_flagged(self):
        html = GOOD_PAGE.replace("#1C1917", "#CCCCCC")
        report = lint_html(html, language="ms")
        assert any("contrast" in i for i in report.issues)

    def test_extract_root_vars(self):
        assert extract_root_hex_vars(GOOD_PAGE) == {
            "color-text": "#1C1917",
            "color-background": "#FFFBF5",
        }

    def test_unparsable_colors_skipped(self):
        assert contrast_ratio("#nothex", "#FFFFFF") is None


@pytest.mark.skipif(not PREVIEWS_DIR.is_dir(), reason="docs/previews not present")
class TestCommittedPreviews:
    """Every committed V2 preview must stay compliant."""

    def test_previews_pass_lint(self):
        failures = {}
        for path in sorted(PREVIEWS_DIR.glob("*.html")):
            html = path.read_text(encoding="utf-8")
            report = lint_html(html)  # language unknown per-file: structural + wording only
            if not report.ok:
                failures[path.name] = report.issues
        assert not failures, f"preview lint failures: {failures}"
