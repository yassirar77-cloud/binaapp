"""Tests for the non-F&B image/icon bias fixes that ship around the gogoo
make-good (website 709f3a99-b988-4b14-b321-d9c42ab16d86):

1. find_card_images() — the make-good endpoint's pure card-image locator
   (hero excluded, titles from the following heading / alt fallback).
2. _build_strict_prompt() icon guidance — business-type aware: F&B keeps
   the food glyph list, everyone else gets an explicit food-icon ban and a
   neutral preferred set; the business type itself is in the prompt header.
3. Hero mini-stats overflow — prompt guidance (min-w-0 / break-words) and
   the layout-safety CSS rule that fixes already-published sites.
"""

import pytest

from app.api.admin.make_good import find_card_images
from app.services.ai_service import AIService
from app.services.templates import template_service


PHONE_SHOP_NAME = "Kedai Phone & Smart Line"
PHONE_SHOP_DESC = (
    "kedai phone & smart line, jual smartphone, gadget dan pelan smart line "
    "di Shah Alam"
)
FOOD_DESC = "Restoran tomyam dan nasi goreng, masakan kampung di Klang"


@pytest.fixture
def service():
    return AIService()


# ---------------------------------------------------------------------------
# 1. find_card_images
# ---------------------------------------------------------------------------

def _cl(name):  # short cloudinary URL builder
    return f"https://res.cloudinary.com/demo/image/upload/{name}.png"


SITE_HTML = f"""
<section id="home">
  <img src="{_cl('hero')}" alt="Hero">
</section>
<section id="produk">
  <div class="card"><img src="{_cl('card1')}" alt="Produk Pilihan"><h3>Produk Pilihan</h3></div>
  <div class="card"><img src="{_cl('card2')}" alt=""><h3>Koleksi Terbaru</h3></div>
  <div class="card"><img src="{_cl('card3')}" alt="Tawaran Istimewa"></div>
  <div class="card"><img src="{_cl('card4')}" alt=""><h4>Barangan Popular</h4></div>
</section>
<section id="galeri">
  <img src="https://images.unsplash.com/photo-123" alt="stock (not AI)">
  <img src="{_cl('card1')}" alt="duplicate of card1">
</section>
"""


class TestFindCardImages:
    def test_extracts_cards_excluding_hero(self):
        cards = find_card_images(SITE_HTML)
        urls = [c["url"] for c in cards]
        assert _cl("hero") not in urls
        assert urls == [_cl("card1"), _cl("card2"), _cl("card3"), _cl("card4")]

    def test_titles_from_following_heading(self):
        cards = find_card_images(SITE_HTML)
        assert cards[0]["title"] == "Produk Pilihan"
        assert cards[1]["title"] == "Koleksi Terbaru"
        assert cards[3]["title"] == "Barangan Popular"  # h4 accepted

    def test_title_falls_back_to_alt(self):
        cards = find_card_images(SITE_HTML)
        assert cards[2]["title"] == "Tawaran Istimewa"

    def test_non_cloudinary_images_ignored(self):
        assert all("unsplash" not in c["url"] for c in find_card_images(SITE_HTML))

    def test_duplicate_urls_deduped(self):
        urls = [c["url"] for c in find_card_images(SITE_HTML, max_images=10)]
        assert len(urls) == len(set(urls))

    def test_max_images_cap(self):
        assert len(find_card_images(SITE_HTML, max_images=2)) == 2

    def test_hero_only_site_returns_nothing(self):
        assert find_card_images(f'<img src="{_cl("hero")}">') == []

    def test_empty_html(self):
        assert find_card_images("") == []


# ---------------------------------------------------------------------------
# 2. Business-type-aware icon guidance in the GLM prompt
# ---------------------------------------------------------------------------

class TestIconPromptGuidance:
    def test_nonfood_prompt_forbids_food_icons(self, service):
        prompt = service._build_strict_prompt(
            name=PHONE_SHOP_NAME, desc=PHONE_SHOP_DESC, style="modern"
        )
        assert "BUSINESS TYPE: GENERAL" in prompt
        assert "NEVER use food or drink icons" in prompt
        assert "fa-mobile-screen" in prompt
        # The old unconditional food-glyph recommendation must be gone.
        assert "Safe free food/service glyphs to prefer" not in prompt

    def test_food_prompt_keeps_food_glyph_list(self, service):
        prompt = service._build_strict_prompt(
            name="Restoran Tomyam", desc=FOOD_DESC, style="modern"
        )
        assert "BUSINESS TYPE: FOOD" in prompt
        assert "Safe free food/service glyphs to prefer" in prompt
        assert "fa-bowl-food" in prompt
        assert "NEVER use food or drink icons" not in prompt

    def test_salon_prompt_forbids_food_icons(self, service):
        prompt = service._build_strict_prompt(
            name="Salon Ayu",
            desc="Salon rambut wanita, potong rambut dan rawatan",
            style="modern",
        )
        assert "BUSINESS TYPE: SALON" in prompt
        assert "NEVER use food or drink icons" in prompt


# ---------------------------------------------------------------------------
# 3. Hero mini-stats overflow protection
# ---------------------------------------------------------------------------

class TestHeroStatsOverflow:
    def test_prompt_carries_stat_grid_rules(self, service):
        prompt = service._build_strict_prompt(
            name=PHONE_SHOP_NAME, desc=PHONE_SHOP_DESC, style="modern"
        )
        assert "min-w-0" in prompt
        assert "break-words" in prompt
        assert "MUST NEVER OVERLAP" in prompt

    def test_layout_safety_css_fixes_published_sites(self):
        """The self-upgrading guard CSS must force hero grid cells to
        shrink (min-width:0) and long Malay stat labels to wrap."""
        css = template_service.LAYOUT_SAFETY_CSS
        assert 'section[id="home"] .grid > *' in css
        assert "min-width: 0" in css
        assert "overflow-wrap: break-word" in css

    def test_guard_injection_carries_new_rule(self):
        html = "<html><head></head><body><section id='home'></section></body></html>"
        out = template_service.apply_layout_safety_guard(html)
        assert 'section[id="home"] .grid > *' in out
