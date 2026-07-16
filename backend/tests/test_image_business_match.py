"""
Tests for AI-image ↔ business matching (the "content and image not the same"
bug reported for non-restaurant websites).

Root causes covered:

1. FOOD PASS ON NON-FOOD SITES — _generate_ai_food_images ran on every
   build regardless of business type, so a gym / photocopy / coworking
   site could get Malaysian dish photos injected. It must now skip
   entirely when the business description is not a food business.

2. SUBSTRING KEYWORD MATCHING — food/category detection used raw
   substring checks, so 'rice' matched "Price List", 'mee' matched
   "Meeting Room", 'ikan' matched "kecantikan", 'kopi' matched
   "fotokopi", 'cat' matched "catering", 'kandar' matched "Iskandar".
   All keyword matching must be whole-word.
"""

import pytest
from unittest.mock import AsyncMock

from app.services.ai_service import AIService
from app.services.business_types import detect_business_type
from app.data.malaysian_prompts import get_smart_stability_prompt


NON_FOOD_DESCRIPTIONS = [
    "Pusat fotokopi dan percetakan dokumen di Kuala Lumpur",
    "Coworking space dengan bilik meeting dan wifi laju",
    "Gym dan pusat kecergasan, personal trainer profesional",
    "Salon kecantikan dan rawatan muka di Shah Alam",
    "Kedai jual telefon bimbit dan aksesori gadget",
]

FOOD_DESCRIPTIONS = [
    "Restoran nasi kandar di Penang, ayam goreng dan kari",
    "Warung makan menjual nasi lemak dan mee goreng",
    "Cafe kopi dan kek di Bangsar",
]


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("ZAI_API_KEY", "test-zai-key")
    monkeypatch.setenv("STABILITY_API_KEY", "test-stability-key")
    return AIService()


# ---------------------------------------------------------------------------
# 1. Food-image pass is gated on the business type
# ---------------------------------------------------------------------------

class TestFoodPassSkipsNonFoodBusinesses:
    HTML_WITH_TRAP_HEADINGS = """
    <section>
      <img src="https://images.unsplash.com/photo-1?w=800&q=80">
      <h3>Price List</h3>
      <img src="https://images.unsplash.com/photo-2?w=800&q=80">
      <h3>Meeting Room</h3>
      <img src="https://images.unsplash.com/photo-3?w=800&q=80">
      <h3>Rawatan Kecantikan</h3>
    </section>
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("description", NON_FOOD_DESCRIPTIONS)
    async def test_pass_skipped_for_non_food_business(self, service, description):
        service.generate_food_image = AsyncMock(
            return_value="https://res.cloudinary.com/x/food.png"
        )
        html, count = await service._generate_ai_food_images(
            self.HTML_WITH_TRAP_HEADINGS, business_description=description
        )
        assert count == 0
        assert html == self.HTML_WITH_TRAP_HEADINGS
        service.generate_food_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_trap_headings_not_detected_as_food_even_on_food_sites(self, service):
        # Even for a food business, "Price List" / "Meeting Room" headings
        # must not be treated as dishes (whole-word matching).
        service.generate_food_image = AsyncMock(
            return_value="https://res.cloudinary.com/x/food.png"
        )
        html, count = await service._generate_ai_food_images(
            self.HTML_WITH_TRAP_HEADINGS,
            business_description=FOOD_DESCRIPTIONS[0],
        )
        assert count == 0
        service.generate_food_image.assert_not_called()

    @pytest.mark.asyncio
    async def test_real_dish_still_replaced_on_food_sites(self, service):
        html_in = """
        <img src="https://images.unsplash.com/photo-9?w=800&q=80">
        <h3>Nasi Lemak</h3>
        """
        service.generate_food_image = AsyncMock(
            return_value="https://res.cloudinary.com/x/nasi-lemak.png"
        )
        html, count = await service._generate_ai_food_images(
            html_in, business_description=FOOD_DESCRIPTIONS[1]
        )
        assert count == 1
        assert "res.cloudinary.com/x/nasi-lemak.png" in html


# ---------------------------------------------------------------------------
# 2. Whole-word keyword matching everywhere
# ---------------------------------------------------------------------------

class TestWordBoundaryMatching:
    def test_has_word_rejects_substrings(self, service):
        assert not service._has_word("price list", "rice")
        assert not service._has_word("meeting room", "mee")
        assert not service._has_word("rawatan kecantikan", "ikan")
        assert not service._has_word("pusat fotokopi", "kopi")
        assert not service._has_word("bandar iskandar", "kandar")
        assert not service._has_word("beard trim", "bear")

    def test_has_word_accepts_whole_words_and_phrases(self, service):
        assert service._has_word("nasi lemak special", "nasi lemak")
        assert service._has_word("ikan bakar istimewa", "ikan")
        assert service._has_word("kopi o ais", "kopi")

    def test_malaysian_prompt_not_applied_to_lookalike_words(self, service):
        # 'kopi' ⊂ "fotokopi" must NOT return the coffee prompt
        assert "kopi coffee" not in service._get_malaysian_prompt("Servis Fotokopi")
        # 'ikan' ⊂ "kecantikan" must NOT return the fish prompt
        assert "grilled fish" not in service._get_malaysian_prompt("Rawatan Kecantikan")

    def test_malaysian_prompt_still_matches_real_dishes(self, service):
        assert "nasi lemak" in service._get_malaysian_prompt("Nasi Lemak Special").lower()

    def test_smart_image_prompt_ignores_meeting_and_fotokopi(self, service):
        for text in ("meeting", "fotokopi", "price"):
            _prompt, confidence = service.get_smart_image_prompt(text)
            assert confidence < 0.9, f"'{text}' matched a dish with confidence {confidence}"

    def test_get_matching_image_price_is_not_rice(self, service):
        url = service.get_matching_image("Price List", business_type="kedai gadget")
        assert url != service.FOOD_IMAGES["mee goreng"]
        assert url not in service.FOOD_IMAGES.values()

    def test_get_food_image_rejects_lookalikes(self, service):
        assert service.get_food_image("Meeting Room") == service.FOOD_IMAGES["default"]
        assert service.get_food_image("Price List") == service.FOOD_IMAGES["default"]


# ---------------------------------------------------------------------------
# 3. Description-level classification
# ---------------------------------------------------------------------------

class TestBusinessClassification:
    @pytest.mark.parametrize("description", NON_FOOD_DESCRIPTIONS)
    def test_non_food_descriptions_not_food(self, service, description):
        assert not service._is_food_business(description)
        assert service._autofill_prompt_category(description) != "food"

    @pytest.mark.parametrize("description", FOOD_DESCRIPTIONS)
    def test_food_descriptions_are_food(self, service, description):
        assert service._is_food_business(description)
        assert service._autofill_prompt_category(description) == "food"

    def test_image_prompts_no_dishes_for_non_food_business(self, service):
        prompts = service.get_image_prompts(
            "Coworking space dengan bilik meeting dan fotokopi"
        )
        joined = (prompts["hero"] + " ".join(prompts["gallery"])).lower()
        for dish_word in ("nasi", "mee goreng", "laksa", "teh tarik"):
            assert dish_word not in joined

    def test_detect_type_catering_is_not_pet_shop(self, service):
        assert service._detect_type("kedai catering untuk majlis") != "pet_shop"

    def test_business_types_spa_not_matched_in_spare_parts(self):
        # 'spa' ⊂ "spare parts" must not classify a car parts shop as salon
        assert detect_business_type("Kedai spare parts kereta dan servis repair") != "salon"

    def test_smart_stability_prompt_fotokopi_not_coffee(self):
        prompt = get_smart_stability_prompt("Servis Fotokopi", "printing shop")
        assert "kopitiam" not in prompt.lower()
        assert "food photography" not in prompt.lower()
