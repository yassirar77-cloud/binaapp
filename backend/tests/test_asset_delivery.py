"""Bytes the visitor pays for and nobody chose. Report items #12 and #13."""

import re

from app.services.asset_delivery import (
    GALLERY_WIDTH,
    HERO_WIDTH,
    font_awesome_families,
    optimize_assets,
    optimize_cloudinary_urls,
    trim_font_awesome,
)

FA = "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0"

PAGE = (
    f'<head><link rel="stylesheet" href="{FA}/css/all.min.css"></head><body>'
    '<section class="hero" style="background-image:url('
    "https://res.cloudinary.com/dx/image/upload/v1789208034/hero.jpg)\"></section>"
    '<div class="gallery grid">'
    '<img src="https://res.cloudinary.com/dx/image/upload/v1789208035/g1.jpg">'
    '<img src="https://res.cloudinary.com/dx/image/upload/v1789208036/g2.jpg">'
    "</div>"
    '<i class="fas fa-utensils"></i><i class="fab fa-facebook"></i>'
    "</body>"
)


def _transform_for(html, version):
    return re.search(rf"upload/([^/]+)/{version}/", html).group(1)


class TestCloudinary:
    def test_every_raw_upload_gets_a_transformation(self):
        out, report = optimize_cloudinary_urls(PAGE)
        assert report.images_optimized == 3
        assert "f_auto,q_auto" in out

    def test_the_hero_gets_the_hero_cap(self):
        out, _ = optimize_cloudinary_urls(PAGE)
        assert f"w_{HERO_WIDTH}" in _transform_for(out, "v1789208034")

    def test_gallery_images_get_the_card_cap(self):
        # The saving lives here: a rule that only asks "is there a hero
        # above me" caps every card at 1920 and saves nothing.
        out, _ = optimize_cloudinary_urls(PAGE)
        for version in ("v1789208035", "v1789208036"):
            assert f"w_{GALLERY_WIDTH}" in _transform_for(out, version)

    def test_c_limit_never_upscales(self):
        out, _ = optimize_cloudinary_urls(PAGE)
        assert "c_limit" in out

    def test_an_already_transformed_url_is_left_alone(self):
        html = '<img src="https://res.cloudinary.com/dx/image/upload/f_auto,q_auto,w_400/v1/x.jpg">'
        out, report = optimize_cloudinary_urls(html)
        assert out == html and report.images_optimized == 0

    def test_idempotent(self):
        once, _ = optimize_cloudinary_urls(PAGE)
        twice, report = optimize_cloudinary_urls(once)
        assert twice == once and report.images_optimized == 0

    def test_pages_without_cloudinary_are_untouched(self):
        html = '<img src="https://images.unsplash.com/photo-1.jpg">'
        assert optimize_cloudinary_urls(html)[0] == html


class TestFontAwesome:
    def test_it_detects_the_families_in_use(self):
        assert set(font_awesome_families('<i class="fas fa-x"></i>')) == {"solid"}
        assert set(font_awesome_families('<i class="fab fa-facebook"></i>')) == {
            "brands", "solid",
        }

    def test_all_min_css_is_split_into_the_families_used(self):
        out, report = trim_font_awesome(PAGE)
        assert "/css/all.min.css" not in out
        assert f'{FA}/css/fontawesome.min.css' in out
        assert f'{FA}/css/solid.min.css' in out
        assert f'{FA}/css/brands.min.css' in out
        assert set(report.font_awesome_families) == {"solid", "brands"}

    def test_unused_families_are_not_loaded(self):
        out, _ = trim_font_awesome(PAGE)
        assert "/css/regular.min.css" not in out

    def test_a_page_with_no_icons_loses_the_stylesheet(self):
        html = f'<head><link rel="stylesheet" href="{FA}/css/all.min.css"></head><body>hi</body>'
        out, report = trim_font_awesome(html)
        assert "font-awesome" not in out
        assert report.notes

    def test_an_already_split_link_is_left_alone(self):
        html = f'<head><link rel="stylesheet" href="{FA}/css/solid.min.css"></head><i class="fas fa-x"></i>'
        out, report = trim_font_awesome(html)
        assert out == html and not report.font_awesome_families

    def test_idempotent(self):
        once, _ = trim_font_awesome(PAGE)
        assert trim_font_awesome(once)[0] == once


class TestCombined:
    def test_one_call_does_both_and_repeats_cleanly(self):
        once, report = optimize_assets(PAGE)
        assert report.changed
        twice, again = optimize_assets(once)
        assert twice == once and not again.changed

    def test_empty_input(self):
        out, report = optimize_assets("")
        assert out == "" and not report.changed
