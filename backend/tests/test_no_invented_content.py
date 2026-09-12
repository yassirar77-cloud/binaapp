"""Two things the generator must never invent: a business name, and a review.

Both shipped on the same live site. With no name in the brief the pipeline
took the first word of the description and branded the whole page "Kedai";
with no reviews it wrote three named customers with quotes. These tests pin
the replacement contract at every layer that can produce either.
"""

import os

import pytest

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

from app.services.generation_validator import (
    business_name_placeholder,
    is_business_name_placeholder,
)
from app.services.reviews_policy import (
    REVIEWS_EMPTY_STATE_COPY,
    empty_state_copy,
    normalize_supplied_reviews,
)


class TestNormalizeSuppliedReviews:
    def test_keeps_a_complete_review(self):
        assert normalize_supplied_reviews(
            [{"name": "Encik Rahman", "text": "Nasi campur sedap.", "rating": 5}]
        ) == [{"name": "Encik Rahman", "text": "Nasi campur sedap.", "rating": 5}]

    def test_accepts_alternate_field_names(self):
        assert normalize_supplied_reviews(
            [{"author": "Kak Mah", "quote": "Sedap sangat!"}]
        ) == [{"name": "Kak Mah", "text": "Sedap sangat!"}]

    @pytest.mark.parametrize(
        "entry",
        [
            {"text": "Sedap!"},                      # quote with no author
            {"name": "Encik Rahman"},                # author with no quote
            {"name": "  ", "text": "Sedap!"},
            {"name": "Encik Rahman", "text": "  "},
            "just a string",
            None,
        ],
    )
    def test_drops_anything_that_is_not_an_attributable_review(self, entry):
        """An unattributed quote is the shape of the invented testimonials
        this policy exists to stop — dropping it renders the empty state,
        which is the safe outcome."""
        assert normalize_supplied_reviews([entry]) == []

    @pytest.mark.parametrize("rating", [0, 6, -1, "five", None, ""])
    def test_out_of_range_rating_is_dropped_not_guessed(self, rating):
        review = normalize_supplied_reviews(
            [{"name": "A", "text": "Sedap.", "rating": rating}]
        )
        assert review == [{"name": "A", "text": "Sedap."}]

    def test_never_raises_on_junk(self):
        assert normalize_supplied_reviews([object(), 3, []]) == []
        assert normalize_supplied_reviews(None) == []


class TestEmptyStateCopy:
    @pytest.mark.parametrize("lang", ["ms", "en"])
    def test_has_all_three_strings(self, lang):
        copy = empty_state_copy(lang)
        assert copy["heading"] and copy["body"] and copy["cta"]

    def test_unknown_language_falls_back_to_malay(self):
        assert empty_state_copy("fr") == REVIEWS_EMPTY_STATE_COPY["ms"]
        assert empty_state_copy(None) == REVIEWS_EMPTY_STATE_COPY["ms"]


class TestRendererEmptyState:
    """The deterministic renderer's three testimonial variants."""

    @pytest.fixture
    def components(self):
        from app.services.html_renderer import COMPONENT_RENDERERS

        return COMPONENT_RENDERERS

    @pytest.mark.parametrize(
        "name", ["TestimonialCards", "TestimonialSlider", "TestimonialQuote"]
    )
    def test_no_reviews_renders_the_empty_state_with_a_cta(self, components, name):
        html = components[name]({"heading": "Ulasan Pelanggan", "language": "ms"})
        copy = empty_state_copy("ms")
        assert copy["body"] in html
        assert copy["cta"] in html
        # Nothing that could read as a review.
        assert "fa-star" not in html
        assert "&ldquo;" not in html

    @pytest.mark.parametrize(
        "name", ["TestimonialCards", "TestimonialSlider", "TestimonialQuote"]
    )
    def test_supplied_reviews_still_render(self, components, name):
        html = components[name]({
            "heading": "Ulasan Pelanggan",
            "reviews": [{"name": "Encik Rahman", "text": "Nasi campur sedap.", "rating": 5}],
        })
        assert "Encik Rahman" in html
        assert "Nasi campur sedap." in html


class TestContactMapPlaceholder:
    """Fix 5: a real embed keyed on the address, or no map element at all."""

    @pytest.fixture
    def contact(self):
        from app.services.html_renderer import COMPONENT_RENDERERS

        return COMPONENT_RENDERERS["ContactSplit"]

    def test_address_produces_a_real_embed(self, contact):
        html = contact({
            "heading": "Hubungi Kami",
            "show_map": True,
            "address": "Seksyen 13, Shah Alam",
        })
        assert "maps.google.com/maps?q=" in html
        assert "output=embed" in html

    def test_no_address_renders_no_map_element_at_all(self, contact):
        html = contact({"heading": "Hubungi Kami", "whatsapp_number": "60193456781"})
        assert "map-container" not in html
        assert "fa-map" not in html
        assert "maps.google.com" not in html
        # ...and the contact details take the width instead of sitting in a
        # half-empty two-column grid.
        assert "lg:grid-cols-2" not in html

    def test_show_map_without_an_address_renders_nothing(self, contact):
        html = contact({"heading": "Hubungi Kami", "show_map": True})
        assert "map-container" not in html
        assert "fa-map" not in html


class TestPromptContract:
    """The generation prompt itself — where every invention starts."""

    @pytest.fixture(scope="class")
    def service(self):
        from app.services.ai_service import AIService

        return AIService()

    def build(self, service, **kwargs):
        kwargs.setdefault("name", "Warung Kak Ropiah")
        kwargs.setdefault("desc", "warung nasi campur di shah alam")
        kwargs.setdefault("style", "modern")
        kwargs.setdefault("language", "ms")
        kwargs.setdefault("image_choice", "none")
        return service._build_strict_prompt(**kwargs)

    def test_no_reviews_demands_an_empty_state(self, service):
        prompt = self.build(service)
        assert "NONE SUPPLIED — EMPTY STATE ONLY" in prompt
        assert empty_state_copy("ms")["cta"] in prompt

    def test_supplied_reviews_are_passed_through_verbatim(self, service):
        prompt = self.build(
            service,
            testimonials=[{"name": "Encik Rahman", "text": "Nasi campur sedap.", "rating": 5}],
        )
        assert "REAL — SUPPLIED BY THE MERCHANT" in prompt
        assert "Encik Rahman" in prompt
        assert "Nasi campur sedap." in prompt
        assert "EMPTY STATE ONLY" not in prompt

    def test_an_unattributed_quote_does_not_unlock_the_review_section(self, service):
        prompt = self.build(service, testimonials=[{"text": "Sedap!"}])
        assert "NONE SUPPLIED — EMPTY STATE ONLY" in prompt

    def test_an_address_produces_a_real_map_embed_instruction(self, service):
        prompt = self.build(
            service, location_address="Seksyen 13, Shah Alam", include_maps=True
        )
        assert "maps.google.com/maps?q=" in prompt
        assert "Seksyen+13" in prompt

    def test_no_address_forbids_a_map_placeholder(self, service):
        prompt = self.build(service, include_maps=True)
        assert "LOCATION MAP: NONE" in prompt
        assert "Peta lokasi akan dipaparkan di sini" in prompt  # named as forbidden

    def test_encoding_rule_is_stated(self, service):
        prompt = self.build(service)
        assert "TEXT ENCODING" in prompt
        assert chr(92) + "u2014" in prompt  # named as forbidden

    def test_placeholder_name_is_flagged_to_the_model(self, service):
        prompt = self.build(service, name=business_name_placeholder("ms"))
        assert "PLACEHOLDER the merchant has not" in prompt

    def test_a_real_name_carries_no_placeholder_note(self, service):
        prompt = self.build(service)
        assert "PLACEHOLDER the merchant has not" not in prompt

    def test_generic_shop_words_are_forbidden_as_a_brand(self, service):
        prompt = self.build(service)
        assert "never substitute a generic shop word" in prompt


class TestGenerationRequestNameIsNeverGuessed:
    """`description.split()[0]` is how "Kedai makan di Shah Alam…" became the
    brand "Kedai". The entrypoint must use the placeholder instead."""

    def test_supplied_name_wins(self):
        from app.main import business_name_placeholder as imported

        assert imported("ms") == business_name_placeholder("ms")

    def test_the_placeholder_is_recognisable_as_unfilled(self):
        for lang in ("ms", "en"):
            marker = business_name_placeholder(lang)
            assert is_business_name_placeholder(marker)
            # ...and is not something a merchant would plausibly have chosen.
            assert marker.isupper()
