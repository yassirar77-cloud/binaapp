"""Unit tests for the credit-free theme repaint (services/theme_patcher.py).

The repaint runs over a merchant's LIVE page and the result is republished
without an AI in the loop, so the bar is: it must change every colour token
the generator emits, and it must not touch anything else. These tests pin
both halves — especially the "anything else", which is where a naive
find/replace quietly breaks a live site.
"""

import pytest

from app.services.design_system import get_font_pairing_by_key, get_named_palette
from app.services.theme_patcher import (
    apply_theme,
    clean_palette,
    contrast_ratio,
    detect_fonts,
    detect_palette,
    is_greyscale,
    normalize_hex,
)


# A page shaped like real generator output: CSS variables, an inline
# tailwind.config, a Google Fonts link, inline styles, Tailwind arbitrary
# values, plus the hostile cases (anchor that looks like a hex, hex in a URL
# fragment, SVG paint reference, structural whites).
GENERATED_HTML = """<!DOCTYPE html>
<html lang="ms"><head>
<meta charset="utf-8">
<meta name="theme-color" content="#EA580C">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = { theme: { extend: { colors: {
  'primary': '#EA580C', 'secondary': '#9A3412', 'accent': '#FED7AA', 'surface': '#FFFFFF' },
  fontFamily: { 'heading': ['Playfair Display','Georgia'], 'body': ['DM Sans','system-ui'] } } } }
</script>
<style>
:root { --primary-color: #EA580C; --secondary-color: #9A3412; --accent-color: #FED7AA;
        --bg-color: #FFFBF5; --surface-color: #FFFFFF; --text-color: #1C1917;
        --text-muted-color: #78716C; --border-color: #F3E6DA; }
body { background: var(--bg-color); font-family: 'DM Sans', system-ui; }
h1 { font-family: 'Playfair Display', Georgia, serif; }
.badge { background: #EA580C; color: #FFFFFF; }
.rule { border-top: 1px solid #F3E6DA; }
</style></head>
<body style="background-color:#FFFBF5">
<a href="#menu">Menu</a>
<a href="#EA580C-promo">Promosi</a>
<img src="https://cdn.example.com/hero.jpg?v=1#EA580C" alt="hero">
<svg><linearGradient id="EA580C"></linearGradient><rect fill="url(#EA580C)"/><rect fill="#EA580C"/></svg>
<h1 style="color:#1C1917">Kedai Ali</h1>
<div class="text-[#EA580C] bg-[#FFFFFF]">arbitrary values</div>
<p style="color:#78716C">Nasi lemak</p>
<footer style="background:#9A3412;color:#FFFFFF">Hubungi</footer>
</body></html>"""

BLUE = get_named_palette("blue", "light")


class TestHexHelpers:
    def test_normalize_expands_shorthand_and_uppercases(self):
        assert normalize_hex("#abc") == "#AABBCC"
        assert normalize_hex("2563eb") == "#2563EB"
        assert normalize_hex("#2563EB") == "#2563EB"

    @pytest.mark.parametrize("bad", ["", None, "blue", "#12", "#1234567", "rgb(1,2,3)"])
    def test_normalize_rejects_non_hex(self, bad):
        assert normalize_hex(bad) is None

    def test_greyscale_detection_protects_structural_neutrals(self):
        assert is_greyscale("#FFFFFF")
        assert is_greyscale("#000")
        assert is_greyscale("#FAFAF9"), "near-neutral page backgrounds count too"
        assert not is_greyscale("#EA580C")
        assert not is_greyscale("#6B7280"), "slate has enough hue to be a brand colour"

    def test_contrast_ratio_matches_wcag_reference(self):
        # Black on white is the canonical 21:1.
        assert contrast_ratio("#000000", "#FFFFFF") == 21.0
        assert contrast_ratio("#FFFFFF", "#FFFFFF") == 1.0

    def test_clean_palette_drops_unknown_roles_and_bad_hexes(self):
        cleaned = clean_palette(
            {"primary": "#2563eb", "nonsense": "#111111", "accent": "not-a-colour"}
        )
        assert cleaned == {"primary": "#2563EB"}


class TestDetection:
    def test_reads_every_role_from_css_variables(self):
        palette = detect_palette(GENERATED_HTML)
        assert palette["primary"] == "#EA580C"
        assert palette["secondary"] == "#9A3412"
        assert palette["accent"] == "#FED7AA"
        assert palette["background"] == "#FFFBF5"
        assert palette["surface"] == "#FFFFFF"
        assert palette["text"] == "#1C1917"
        assert palette["text_muted"] == "#78716C"
        assert palette["border"] == "#F3E6DA"

    def test_falls_back_to_tailwind_config_without_css_variables(self):
        html = (
            "<html><head><script>tailwind.config = { theme: { extend: { colors: "
            "{ 'primary': '#B91C1C', 'secondary': '#7F1D1D' } } } }</script>"
            "</head><body>x</body></html>"
        )
        palette = detect_palette(html)
        assert palette["primary"] == "#B91C1C"
        assert palette["secondary"] == "#7F1D1D"

    def test_reads_font_pairing_from_google_fonts_link(self):
        assert detect_fonts(GENERATED_HTML) == {
            "heading": "Playfair Display",
            "body": "DM Sans",
        }

    def test_no_fonts_link_reads_as_empty(self):
        assert detect_fonts("<html><head></head><body>x</body></html>") == {}

    def test_empty_html_is_safe(self):
        assert detect_palette("") == {}
        assert detect_fonts("") == {}


class TestRepaint:
    def test_every_palette_token_moves(self):
        result = apply_theme(GENERATED_HTML, palette=BLUE)
        assert result.changed
        assert detect_palette(result.html) == clean_palette(BLUE)

    def test_css_variables_tailwind_and_literals_all_rewritten(self):
        result = apply_theme(GENERATED_HTML, palette=BLUE)
        summary = result.summary()
        assert summary["variables"] == 8, "one write per CSS custom property"
        assert summary["tailwind"] == 4, "primary/secondary/accent/surface"
        assert summary["hex"] > 0, "inline styles and arbitrary values too"
        assert "--primary-color: #2563EB" in result.html
        assert "'primary': '#2563EB'" in result.html
        assert "class=\"text-[#2563EB]" in result.html

    def test_theme_color_meta_follows_the_new_primary(self):
        result = apply_theme(GENERATED_HTML, palette=BLUE)
        assert '<meta name="theme-color" content="#2563EB">' in result.html

    def test_theme_color_meta_is_added_when_absent(self):
        html = "<html><head><style>:root{--primary-color:#EA580C}</style></head><body>x</body></html>"
        result = apply_theme(html, palette=BLUE)
        assert 'name="theme-color" content="#2563EB"' in result.html

    def test_anchor_that_looks_like_a_hex_survives(self):
        # href="#EA580C-promo" is a section id, not a colour.
        result = apply_theme(GENERATED_HTML, palette=BLUE)
        assert 'href="#EA580C-promo"' in result.html

    def test_hex_inside_an_image_url_survives(self):
        result = apply_theme(GENERATED_HTML, palette=BLUE)
        assert "hero.jpg?v=1#EA580C" in result.html

    def test_svg_paint_reference_survives(self):
        # fill="url(#EA580C)" points at a gradient id, not a colour.
        result = apply_theme(GENERATED_HTML, palette=BLUE)
        assert 'fill="url(#EA580C)"' in result.html
        # …while the sibling literal fill IS repainted.
        assert 'fill="#2563EB"' in result.html

    def test_structural_white_is_never_repainted(self):
        # The page's surface is #FFFFFF. Ask for a different surface: the CSS
        # variable must move, but the *literal* whites scattered through the
        # document (button label colour, footer text) must NOT — white there is
        # structural, and repainting all of it is how a recolour breaks a page.
        palette = {**BLUE, "surface": "#F1F5F9"}
        result = apply_theme(GENERATED_HTML, palette=palette)

        assert "--surface-color: #F1F5F9" in result.html
        assert ".badge { background: #2563EB; color: #FFFFFF; }" in result.html
        assert "color:#FFFFFF" in result.html, "footer text colour untouched"

    def test_old_brand_colour_only_survives_where_it_is_an_identifier(self):
        result = apply_theme(GENERATED_HTML, palette=BLUE)
        # The anchor target, the image URL fragment and the url() paint
        # reference — three identifiers, zero colours.
        assert result.html.count("#EA580C") == 3

    def test_repaint_is_idempotent(self):
        once = apply_theme(GENERATED_HTML, palette=BLUE).html
        twice = apply_theme(once, palette=BLUE).html
        assert once == twice

    def test_repaint_does_not_change_the_word_count_of_the_page(self):
        # A recolour must never touch copy — that is the whole point of not
        # going through the AI.
        import re

        def words(html):
            body = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S)
            return re.findall(r"[A-Za-z]{3,}", re.sub(r"<[^>]+>", " ", body))

        result = apply_theme(GENERATED_HTML, palette=BLUE)
        assert words(GENERATED_HTML) == words(result.html)

    def test_empty_palette_is_a_no_op(self):
        result = apply_theme(GENERATED_HTML, palette={})
        assert result.changed is False
        assert result.html == GENERATED_HTML

    def test_empty_html_reports_rather_than_raises(self):
        result = apply_theme("", palette=BLUE)
        assert result.changed is False
        assert "empty_html" in result.notes

    def test_page_without_colour_tokens_is_reported(self):
        result = apply_theme("<html><body>Hello</body></html>", palette=BLUE)
        assert "no_colour_tokens_found" in result.notes

    def test_low_contrast_palette_is_flagged_not_blocked(self):
        muddy = {**BLUE, "text": "#8899AA", "background": "#FFFFFF"}
        result = apply_theme(GENERATED_HTML, palette=muddy)
        assert any(note.startswith("low_text_contrast:") for note in result.notes)
        assert result.changed, "the flag is advisory — the repaint still applies"

    def test_partial_palette_only_moves_the_roles_given(self):
        result = apply_theme(GENERATED_HTML, palette={"primary": "#2563EB"})
        after = detect_palette(result.html)
        assert after["primary"] == "#2563EB"
        assert after["secondary"] == "#9A3412", "untouched roles keep their value"


class TestTypography:
    def test_font_link_and_family_references_both_swap(self):
        fonts = get_font_pairing_by_key("bebas-neue__barlow")
        assert fonts, "fixture pairing must exist in the catalogue"
        result = apply_theme(GENERATED_HTML, palette=BLUE, fonts=fonts)

        assert detect_fonts(result.html) == {"heading": "Bebas Neue", "body": "Barlow"}
        assert "Playfair Display" not in result.html
        assert "DM Sans" not in result.html
        assert "font-family: 'Bebas Neue'" in result.html
        assert "font-family: 'Barlow'" in result.html
        assert "'heading': ['Bebas Neue'" in result.html

    def test_previous_fonts_are_reported(self):
        fonts = get_font_pairing_by_key("bebas-neue__barlow")
        result = apply_theme(GENERATED_HTML, fonts=fonts)
        assert result.previous_fonts == {
            "heading": "Playfair Display",
            "body": "DM Sans",
        }

    def test_font_link_is_added_to_a_page_that_had_none(self):
        html = "<html><head><title>x</title></head><body>hi</body></html>"
        result = apply_theme(html, fonts=get_font_pairing_by_key("bebas-neue__barlow"))
        assert "fonts.googleapis.com/css2?family=Bebas+Neue" in result.html

    def test_fonts_only_change_leaves_colours_alone(self):
        result = apply_theme(
            GENERATED_HTML, fonts=get_font_pairing_by_key("bebas-neue__barlow")
        )
        assert detect_palette(result.html)["primary"] == "#EA580C"
