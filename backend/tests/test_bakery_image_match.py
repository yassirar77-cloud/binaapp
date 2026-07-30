"""
Regression tests for the "kedai cake shows kuih pictures" mismatch.

A cake / bakery / dessert shop is a FOOD business, but the image pipeline
lumped every food business into one generic savoury "Malaysian dishes"
bucket:

  * the food hero prompt was hardcoded to an abundant spread of savoury
    Malaysian dishes (nasi-lemak-style), so a cake shop's banner never showed
    cakes; and
  * the deterministic menu-item fallback only recognised savoury dishes plus
    the single word "kuih", so a "kedai cake" that also mentioned kuih fell
    back to a Kuih / Set Kuih / Kuih Combo / Kuih Istimewa menu (and kuih
    images), never cakes.

The fix teaches the food path a SUB-TYPE (bakery / drinks / general) and
makes item extraction cake-aware, without ever misclassifying a savoury
business (whole-word matching keeps "kek" out of "kekacang").
"""

import pytest

from app.services.ai_service import AIService


@pytest.fixture
def service():
    # __new__ skips __init__ network/key setup — the helpers under test are
    # pure functions of the description.
    return AIService.__new__(AIService)


NO_TEXT = "no text, no signage, no words, no lettering anywhere in the image"

# The reported case: cake shop that also mentions kuih-muih.
CAKE_DESC = (
    "Kedai kek harijadi, kek perkahwinan, dan kuih-muih tradisional. "
    "Tempahan mudah, pickup fleksibel."
)


class TestFoodSubtype:
    @pytest.mark.parametrize("desc", [
        "kedai cake",
        "kedai kek",
        "Kedai kek harijadi dan cupcake",
        "Bakery jual brownies dan cheesecake",
        CAKE_DESC,
    ])
    def test_cake_business_is_bakery_subtype(self, service, desc):
        assert service._is_food_business(desc) is True
        assert service._food_subtype(desc) == "bakery"

    def test_drinks_business_is_drinks_subtype(self, service):
        desc = "Kedai minuman jus buah segar dan smoothie"
        assert service._is_food_business(desc) is True
        assert service._food_subtype(desc) == "drinks"

    def test_savoury_business_stays_general(self, service):
        assert service._food_subtype("Warung nasi lemak dan ayam goreng") == "general"

    def test_savoury_word_containing_kek_is_not_bakery(self, service):
        # "kekacang" (peanuts) contains the substring "kek" — whole-word
        # matching must NOT classify this savoury warung as a cake shop.
        desc = "Warung nasi lemak dengan kekacang dan ikan bilis"
        assert service._food_subtype(desc) == "general"
        assert "kek" not in service._extract_menu_items(desc)

    def test_bakery_beats_drinks_on_tie(self, service):
        # A cake shop that also sells coffee is still a cake shop.
        assert service._food_subtype("Kedai kek dan kopi") == "bakery"

    def test_kuih_alone_is_not_bakery(self, service):
        # Traditional kuih is NOT a western cake — a kuih-only shop must not
        # be pushed onto the western-cake hero/imagery.
        assert service._food_subtype("kedai jual kuih tradisional") == "general"

    def test_cake_shop_with_kuih_still_bakery(self, service):
        # Cake terms drive bakery detection even when kuih is also present.
        assert service._food_subtype(CAKE_DESC) == "bakery"


class TestBakeryHeroPrompt:
    def test_bakery_hero_shows_cakes_not_savoury(self, service):
        prompt = service._autofill_hero_prompt(
            "food", "bakery", "Kedai Kek", food_subtype="bakery"
        ).lower()
        assert "cake" in prompt or "pastr" in prompt
        assert "malaysian dishes" not in prompt
        assert NO_TEXT in prompt

    def test_drinks_hero_shows_beverages(self, service):
        prompt = service._autofill_hero_prompt(
            "food", "drinks shop", "Kedai Jus", food_subtype="drinks"
        ).lower()
        assert "drink" in prompt or "beverage" in prompt
        assert NO_TEXT in prompt

    def test_general_food_hero_unchanged(self, service):
        prompt = service._autofill_hero_prompt(
            "food", "restaurant", "Warung", food_subtype="general"
        ).lower()
        assert "malaysian dishes" in prompt

    def test_food_subtype_defaults_to_general(self, service):
        # Backward-compatible signature: old callers pass no food_subtype.
        prompt = service._autofill_hero_prompt("food", "restaurant").lower()
        assert "malaysian dishes" in prompt


class TestCakeMenuFallback:
    def test_cake_shop_fallback_is_cakes_not_kuih(self, service):
        names = service._fallback_item_names(CAKE_DESC, 4)
        assert names, "a description naming real cakes must still yield items"
        # The product cards lead with cake, never an all-kuih menu.
        assert names[0].lower().startswith("kek")
        joined = " ".join(names).lower()
        assert "kek" in joined
        # Must NOT be the old Kuih / Set Kuih / Kuih Combo / Kuih Istimewa menu.
        assert names != ["Kuih", "Set Kuih", "Kuih Combo", "Kuih Istimewa"]

    def test_pure_cake_shop_returns_the_product_only(self, service):
        """Replaces test_pure_cake_shop_pads_with_cake_variants.

        "Cake" is grounded — the shop says so. "Set Cake"/"Cake Combo"/
        "Cake Istimewa" are invented products (the P0 fabrication vector), so
        the fallback now returns the one real name and lets the caller render
        fewer cards.
        """
        assert service._fallback_item_names("kedai cake", 4) == ["Cake"]

    def test_extract_ranks_cake_ahead_of_kuih(self, service):
        found = service._extract_menu_items(CAKE_DESC)
        assert found[0].startswith("kek")
        # kuih is still detected (the shop does sell it) but not first.
        assert found.index("kuih") > 0

    def test_savoury_fallback_still_savoury(self, service):
        # No cake regression for savoury shops.
        names = service._fallback_item_names(
            "Warung nasi lemak dan ayam goreng, ada kekacang", 4
        )
        assert names[0] == "Nasi Lemak"
        assert not any("kek" in n.lower() or "cake" in n.lower() for n in names)


class TestCakeItemImagePrompt:
    @pytest.mark.parametrize("item", [
        "Kek Harijadi", "Kek Coklat", "Cupcake", "Brownies", "Cheesecake",
    ])
    def test_known_cake_items_get_bakery_prompt(self, service, item):
        prompt = service._get_malaysian_prompt(item).lower()
        assert "cake" in prompt or "dessert" in prompt or "bakery" in prompt
        assert "malaysian style" not in prompt
        assert NO_TEXT in prompt

    def test_unlisted_cake_item_uses_dessert_fallback(self, service):
        # "Kek Red Velvet" is not in the curated dict — the generic fallback
        # must still read as a cake, not "Malaysian style" savoury food.
        prompt = service._get_malaysian_prompt("Kek Red Velvet Istimewa").lower()
        assert "cake" in prompt or "dessert" in prompt or "bakery" in prompt
        assert "malaysian style" not in prompt

    def test_savoury_item_unchanged(self, service):
        prompt = service._get_malaysian_prompt("Nasi Lemak Special").lower()
        assert "nasi lemak" in prompt

    def test_kuih_item_keeps_traditional_treatment(self, service):
        # A "Kuih" card must NOT be redirected to a western "freshly baked
        # cake" prompt — traditional kuih stays traditional food.
        prompt = service._get_malaysian_prompt("Kuih").lower()
        assert "freshly baked cake" not in prompt
        assert "malaysian" in prompt
