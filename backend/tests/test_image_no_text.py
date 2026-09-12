"""Generated images must carry no lettering at all.

The reported page shipped a "Warisan" image with **NASI KANDAR** baked into
it and clipped at the edge, and a gallery image reading **"Bererrmpath"**.
The positive no-text clause was already on every prompt; what was missing
was the matching exclusion on the negative side, where the diffusion models
that actually draw the letters take instruction.
"""

import pytest

from app.services import stability_service
from app.services.ai_service import AIService

#: Every term the report asked for, plus the shapes text arrives in.
REQUIRED_NEGATIVES = (
    "text", "letters", "words", "watermark", "signage",
    "logo", "label", "caption", "typography", "writing",
)


def _terms(value: str):
    return {t.strip().lower() for t in value.split(",")}


class TestNegativePrompts:
    def test_service_negative_prompt_excludes_every_text_form(self):
        terms = _terms(AIService._IMAGE_NEGATIVE_PROMPT)
        for required in REQUIRED_NEGATIVES:
            assert required in terms, f"{required!r} missing from the negative prompt"

    def test_shared_stability_negative_prompt_matches(self):
        terms = _terms(stability_service.NEGATIVE_PROMPT)
        for required in REQUIRED_NEGATIVES:
            assert required in terms, f"{required!r} missing from the negative prompt"

    def test_the_couple_composition_exclusions_survive(self):
        # Pre-existing market requirement — the text terms were prepended,
        # not swapped in.
        for value in (AIService._IMAGE_NEGATIVE_PROMPT, stability_service.NEGATIVE_PROMPT):
            assert "same-sex couple" in value


class TestPositiveSuffix:
    @pytest.fixture
    def service(self):
        return AIService()

    def test_suffix_names_letters_words_and_watermarks(self):
        suffix = AIService._NO_TEXT_SUFFIX.lower()
        for required in ("no text", "no letters", "no words", "no watermark", "no signage"):
            assert required in suffix

    @pytest.mark.parametrize("dish", ["nasi kandar", "Nasi Kandar Special", "Kek Coklat", "sesuatu"])
    def test_every_food_mapping_branch_carries_it(self, service, dish):
        assert AIService._NO_TEXT_SUFFIX in service._get_malaysian_prompt(dish)

    def test_non_food_prompts_carry_it(self, service):
        shaped = service._shape_image_prompt("studio photo of a handbag", food=False)
        assert AIService._NO_TEXT_SUFFIX in shaped

    def test_application_is_idempotent(self, service):
        once = service._with_no_text_suffix("a photo")
        assert service._with_no_text_suffix(once) == once
