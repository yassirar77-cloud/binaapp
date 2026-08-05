"""Tests for the Doodle Cartoon design style — a user-choice-only look.

The properties that matter:

  1. Doodle appears ONLY when the user asks for it (picker choice or
     description words). It is in no seeded pool, so no existing site's
     reproducible variant walk changes.
  2. When it IS chosen, it arrives complete: the hand-drawn personality
     prompt AND the hand-drawn font pairing together — a serif face over
     sticker shadows reads broken, not playful.
  3. The picker surfaces it: /design/options styles and the font catalogue.
"""

import pytest

from app.services.design_system import (
    DESIGN_PERSONALITIES,
    DOODLE_FONT_PAIRING,
    PERSONALITY_POOL,
    DesignSystem,
    extract_design_preferences,
    get_font_pairing_by_key,
    list_font_pairings,
    list_styles,
)


class TestDetection:
    @pytest.mark.parametrize(
        "description",
        [
            "Saya nak website doodle untuk kedai kek",
            "cartoon style bakery please",
            "website gaya kartun untuk kedai saya",
            "comic hand-drawn design",
            "design macam lukisan tangan",
        ],
    )
    def test_doodle_words_force_the_doodle_hint(self, description):
        assert extract_design_preferences(description)["style_hint"] == "doodle"

    def test_doodle_words_beat_generic_playful_words(self):
        # "kartun" is a doodle ask even next to "comel" (a playful word).
        assert (
            extract_design_preferences("website kartun comel")["style_hint"]
            == "doodle"
        )

    def test_playful_words_alone_stay_playful(self):
        assert (
            extract_design_preferences("kek comel dan ceria")["style_hint"]
            == "playful"
        )

    def test_plain_descriptions_have_no_hint(self):
        assert extract_design_preferences("kedai makan biasa di KL")["style_hint"] is None


class TestBuild:
    def test_style_override_delivers_personality_and_fonts_together(self):
        bundle = DesignSystem().build(
            "food",
            business_name="Kedai Ali",
            description="kedai makan biasa",
            style_override="doodle",
        )
        assert bundle["personality"]["key"] == "doodle_cartoon"
        assert "DOODLE CARTOON" in bundle["personality"]["prompt"]
        # The doodle personality brings its own hand-drawn fonts.
        assert bundle["fonts"]["heading"] == DOODLE_FONT_PAIRING["heading"]
        assert bundle["fonts"]["body"] == DOODLE_FONT_PAIRING["body"]
        assert "Gloria+Hallelujah" in bundle["fonts"]["cdn_link"]
        # And the Tailwind config follows the swapped fonts.
        assert DOODLE_FONT_PAIRING["body"] in bundle["tailwind_config"]

    def test_description_words_alone_are_enough(self):
        bundle = DesignSystem().build(
            "bakery",
            business_name="Kek Comel",
            description="Saya nak website doodle kartun untuk kedai kek saya",
        )
        assert bundle["personality"]["key"] == "doodle_cartoon"

    def test_prompt_carries_concrete_drawing_directives(self):
        prompt = DESIGN_PERSONALITIES["doodle_cartoon"]["prompt"]
        # The directives that make the look land — pinned so a future prompt
        # edit cannot quietly reduce doodle to "just use round corners".
        for marker in ("border-radius: 255px", "rotate-", "shadow-[", "speech-bubble"):
            assert marker in prompt


class TestOptInOnly:
    def test_not_in_any_seeded_pool(self):
        for pool in PERSONALITY_POOL.values():
            assert "doodle_cartoon" not in pool

    def test_never_appears_without_an_explicit_ask(self):
        ds = DesignSystem()
        for btype in PERSONALITY_POOL:
            for name in ("Kedai Ali", "Restoran Seri Muka", "Butik Aisyah", "Gym Kuat"):
                for variant in range(6):
                    bundle = ds.build(
                        btype,
                        business_name=name,
                        description="perniagaan biasa",
                        variant=variant,
                    )
                    assert bundle["personality"]["key"] != "doodle_cartoon", (
                        f"doodle leaked into {btype}/{name}/variant={variant}"
                    )


class TestPickerExposure:
    def test_listed_in_styles_with_malay_label(self):
        styles = {s["key"]: s for s in list_styles()}
        assert "doodle" in styles
        assert styles["doodle"]["label_ms"] == "Doodle Kartun"
        assert styles["doodle"]["personality"] == "doodle_cartoon"

    def test_font_pairing_is_in_the_catalogue_and_resolvable(self):
        catalogue = list_font_pairings()
        doodle = [p for p in catalogue if p["heading"] == DOODLE_FONT_PAIRING["heading"]]
        assert doodle, "doodle pairing missing from the full catalogue"
        assert get_font_pairing_by_key(doodle[0]["key"])

    def test_catalogue_extra_does_not_enter_seeded_generation_pools(self):
        # The pairing is picker-only: no business type's generation pool may
        # contain it, or existing sites' font walks would shift.
        ds = DesignSystem()
        for btype in ("food", "cafe", "salon", "clothing", "bakery",
                      "services", "gym", "clinic", "general"):
            for pairing in ds._font_options(btype):
                assert pairing["heading"] != DOODLE_FONT_PAIRING["heading"]

    def test_design_options_api_serves_the_doodle_style(
        self, client
    ):
        resp = client.get("/api/v1/websites/design/options?color_mode=light")
        assert resp.status_code == 200
        styles = {s["key"] for s in resp.json().get("styles", [])}
        assert "doodle" in styles


class TestRequestSchema:
    def test_design_style_is_accepted(self):
        from app.models.schemas import WebsiteGenerationRequest

        req = WebsiteGenerationRequest(
            description="kedai makan sedap di kuala lumpur",
            business_name="Kedai Ali",
            subdomain="kedaiali",
            design_style="doodle",
        )
        assert req.design_style == "doodle"

    def test_design_style_defaults_to_none(self):
        from app.models.schemas import WebsiteGenerationRequest

        req = WebsiteGenerationRequest(
            description="kedai makan sedap di kuala lumpur",
            business_name="Kedai Ali",
            subdomain="kedaiali",
        )
        assert req.design_style is None
