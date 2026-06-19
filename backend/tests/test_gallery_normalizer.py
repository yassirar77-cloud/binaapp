"""
Tests for the deterministic gallery post-pass (app.services.gallery_normalizer).

Verifies that AI-generated gallery HTML is normalized to uniform card-image
heights and that duplicate category tags are removed, while hero/avatar images
and legitimately-repeating promo badges are left untouched.
"""

from app.services.gallery_normalizer import (
    normalize_gallery_html,
    normalize_gallery_heights,
    dedupe_gallery_tags,
)


class TestUniformHeights:
    def test_uneven_card_heights_become_aspect_ratio(self):
        html = (
            '<img src="a" class="w-full h-56 object-cover">'
            '<img src="b" class="w-full h-72 object-cover rounded-2xl">'
            '<img src="c" class="object-cover h-64 md:h-80">'
        )
        out = normalize_gallery_heights(html)
        for h in ("h-56", "h-72", "h-64", "md:h-80"):
            assert h not in out
        assert out.count("aspect-[4/3]") == 3
        assert out.count("w-full") == 3
        assert "rounded-2xl" in out  # other classes preserved

    def test_hero_and_arbitrary_heights_untouched(self):
        for hero in (
            '<img src="h" class="w-full h-screen object-cover">',
            '<img src="h" class="w-full h-[60vh] object-cover">',
        ):
            assert normalize_gallery_heights(hero) == hero

    def test_avatar_logo_icon_untouched(self):
        avatar = '<img src="av" class="h-12 w-12 rounded-full object-cover">'
        small = '<img src="s" class="h-24 object-cover">'  # below card floor
        assert normalize_gallery_heights(avatar) == avatar
        assert normalize_gallery_heights(small) == small

    def test_object_contain_untouched(self):
        contain = '<img src="x" class="h-64 object-contain">'
        assert normalize_gallery_heights(contain) == contain


class TestDuplicateTags:
    def test_duplicate_category_tag_removed(self):
        html = (
            '<span class="text-xs uppercase rounded-full">Color</span>'
            '<span class="text-xs uppercase rounded-full">Texture</span>'
            '<span class="text-xs uppercase rounded-full">Color</span>'
        )
        out = dedupe_gallery_tags(html)
        assert out.count(">Color<") == 1
        assert out.count(">Texture<") == 1

    def test_promo_badges_may_repeat(self):
        html = (
            '<span class="text-xs uppercase rounded-full">NEW</span>'
            '<span class="text-xs uppercase rounded-full">NEW</span>'
        )
        assert dedupe_gallery_tags(html).count(">NEW<") == 2

    def test_body_text_untouched(self):
        body = '<p class="text-lg">Color</p><p class="text-lg">Color</p>'
        assert dedupe_gallery_tags(body) == body


class TestSafetyAndIdempotency:
    def test_idempotent(self):
        html = (
            '<div class="grid"><img src="a" class="w-full h-56 object-cover">'
            '<span class="text-xs rounded-full">Color</span>'
            '<span class="text-xs rounded-full">Color</span></div>'
        )
        once = normalize_gallery_html(html)
        assert normalize_gallery_html(once) == once

    def test_none_and_empty_safe(self):
        assert normalize_gallery_html(None) is None
        assert normalize_gallery_html("") == ""

    def test_html_without_images_passthrough(self):
        html = "<div><p>no images here</p></div>"
        assert normalize_gallery_html(html) == html
