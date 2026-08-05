"""Tests for doodle-aware AI images.

A site built with the Doodle Cartoon design personality must get cartoon
ILLUSTRATIONS in its AI image slots, not photographs — a photorealistic
nasi lemak inside a hand-drawn page breaks the whole look. The properties:

  1. Photography wording is REPLACED, not merely outweighed — diffusion
     models blend contradictory style words into an uncanny middle.
  2. The subject survives restyling: a doodle site's nasi lemak is still
     nasi lemak, just drawn. The no-text rule survives too.
  3. Doodle-ness is detected exactly like the design system detects it
     (explicit design_style first, description words second) — and never
     fires for ordinary sites.
"""

from types import SimpleNamespace

import pytest

from app.services.ai_service import AIService


@pytest.fixture
def svc():
    return AIService()


def _req(description="kedai makan biasa di KL", design_style=None):
    return SimpleNamespace(description=description, design_style=design_style)


class TestDoodleDetection:
    def test_explicit_design_style_wins(self, svc):
        assert svc._is_doodle_request(_req(design_style="doodle"))

    def test_description_words_are_enough(self, svc):
        assert svc._is_doodle_request(_req("website doodle untuk kedai kek"))
        assert svc._is_doodle_request(_req("cartoon style bakery"))

    def test_ordinary_requests_are_not_doodle(self, svc):
        assert not svc._is_doodle_request(_req("kedai makan biasa"))
        assert not svc._is_doodle_request(_req("kek comel dan ceria"))  # playful != doodle

    def test_request_without_fields_is_safe(self, svc):
        assert not svc._is_doodle_request(SimpleNamespace())


class TestPromptRestyling:
    def test_photography_becomes_illustration(self, svc):
        out = svc._apply_doodle_image_style(
            "Nasi lemak, professional food photography, high quality, realistic"
        )
        # The original photography DIRECTIVES must be gone. (The appended
        # style clause deliberately says "NOT a photograph" — that's the
        # exclusion, not a directive.)
        body = out.split("cute hand-drawn")[0]
        assert "photography" not in body.lower()
        assert "photograph" not in body.lower()
        assert "illustration" in body
        assert "doodle art style" in out
        assert "Nasi lemak" in out, "the subject must survive restyling"

    def test_realistic_is_removed(self, svc):
        out = svc._apply_doodle_image_style("dish, realistic, high quality")
        assert "realistic" not in out.lower().replace("photorealism", "")

    def test_idempotent(self, svc):
        once = svc._apply_doodle_image_style("teh tarik, food photography")
        assert svc._apply_doodle_image_style(once) == once

    def test_empty_prompt_passes_through(self, svc):
        assert svc._apply_doodle_image_style("") == ""


class TestShaping:
    def test_food_doodle_keeps_the_dish_and_draws_it(self, svc):
        shaped = svc._shape_image_prompt("nasi lemak", food=True, doodle=True)
        assert "nasi lemak" in shaped.lower()
        assert "doodle art style" in shaped
        assert "photography" not in shaped.lower()

    def test_food_without_doodle_is_unchanged_behaviour(self, svc):
        assert svc._shape_image_prompt("nasi lemak", food=True) == svc._get_malaysian_prompt(
            "nasi lemak"
        )

    def test_non_food_doodle_keeps_the_no_text_rule(self, svc):
        shaped = svc._shape_image_prompt("wooden toy car product shot", food=False, doodle=True)
        assert "no text" in shaped.lower()
        assert "doodle art style" in shaped

    def test_autofill_hero_prompts_restyle_cleanly_for_every_category(self, svc):
        # Every category's hero prompt must survive doodle restyling with no
        # photography wording left and its subject intact.
        for category in ("food", "creative", "services", "retail", "generic"):
            prompt = svc._autofill_hero_prompt(category, "bakery", "Kek Comel: kedai kek")
            shaped = svc._shape_image_prompt(prompt, food=False, doodle=True)
            assert "photography" not in shaped.lower(), category
            assert "doodle art style" in shaped, category

    def test_autofill_item_prompts_restyle_cleanly(self, svc):
        prompt = svc._autofill_item_prompt("retail", "Baju Kurung Moden", "clothing", "Butik A")
        shaped = svc._shape_image_prompt(prompt, food=False, doodle=True)
        assert "photography" not in shaped.lower()
        assert "Baju Kurung Moden" in shaped


class TestAutofillWiring:
    async def test_doodle_request_reaches_every_generated_image(self, svc):
        """A doodle site's free-image auto-fill must dispatch doodle=True."""
        from unittest.mock import AsyncMock
        from app.models.schemas import WebsiteGenerationRequest

        request = WebsiteGenerationRequest(
            description="Butik pakaian moden di Melaka, baju kurung dan tudung",
            business_name="Butik Aisyah",
            subdomain="butikaisyah",
            design_style="doodle",
        )
        svc.extract_product_category_names = AsyncMock(
            return_value=["Baju Kurung", "Tudung"]
        )
        calls = []

        async def _fake_generate(prompt, food=True, zai_phase=None, doodle=False):
            calls.append(doodle)
            return f"https://res.cloudinary.com/gen{len(calls)}.png"

        svc._generate_image = AsyncMock(side_effect=_fake_generate)

        image_urls = {}
        count = await svc._autofill_missing_images(request, image_urls, None)
        assert count >= 1
        assert calls and all(calls), "every dispatched image must carry doodle=True"

    async def test_ordinary_request_dispatches_without_doodle(self, svc):
        from unittest.mock import AsyncMock
        from app.models.schemas import WebsiteGenerationRequest

        request = WebsiteGenerationRequest(
            description="Butik pakaian moden di Melaka, baju kurung dan tudung",
            business_name="Butik Aisyah",
            subdomain="butikaisyah",
        )
        svc.extract_product_category_names = AsyncMock(return_value=["Baju Kurung"])
        calls = []

        async def _fake_generate(prompt, food=True, zai_phase=None, doodle=False):
            calls.append(doodle)
            return f"https://res.cloudinary.com/gen{len(calls)}.png"

        svc._generate_image = AsyncMock(side_effect=_fake_generate)
        await svc._autofill_missing_images(request, {}, None)
        assert calls and not any(calls)


class TestNegativePromptDefence:
    def test_doodle_negatives_exist_and_exclude_photos(self, svc):
        assert "photograph" in svc._DOODLE_NEGATIVE_TERMS
        assert "photorealistic" in svc._DOODLE_NEGATIVE_TERMS

    def test_style_clause_forbids_photorealism_positively(self, svc):
        # Z.ai accepts no negative prompt — the positive clause must carry
        # the exclusion by itself.
        assert "NOT a photograph" in svc._DOODLE_IMAGE_STYLE
