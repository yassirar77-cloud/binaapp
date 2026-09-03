"""Design Director — the Senior Designer concept layer (design_director.py).

Covers the pure, side-effect-free half of Senior Designer mode:
  - freedom-mode resolution (request > env default; templates force guided)
  - brief normalisation
  - the concept prompt (brief, constraints, font catalogue)
  - concept parsing + validation: hex repair, contrast repair, colour-mode
    enforcement, brand-colour override, font catalogue resolution, display
    fonts kept out of body copy, required sections, hero-first/footer-last
  - prompt rendering of a validated concept
"""

import json

import pytest

from app.services import design_director as dd
from app.services.design_director import (
    ConceptBrief,
    DESIGN_BRIEF_MAX_CHARS,
    GOOGLE_FONTS,
    build_concept_prompt,
    contrast_ratio,
    design_brief_block,
    normalize_design_brief,
    normalize_hex,
    parse_concept,
    resolve_design_freedom,
    resolve_font,
)


LIGHT_FALLBACK = {
    "primary": "#B45309", "secondary": "#78350F", "accent": "#FDE68A",
    "background": "#FFFBEB", "surface": "#FFFFFF", "text": "#1C1917", "text_muted": "#57534E",
}
DARK_FALLBACK = {
    "primary": "#F59E0B", "secondary": "#FBBF24", "accent": "#78350F",
    "background": "#0F0F12", "surface": "#1C1C22", "text": "#F5F5F4", "text_muted": "#A8A29E",
}
FALLBACK_FONTS = {"heading": "Playfair Display", "body": "Mulish"}


def _brief(**kw) -> ConceptBrief:
    params = dict(
        business_name="Warung Kak Ropiah",
        description="Warung nasi campur masakan kampung di Shah Alam.",
        business_type="food",
        language="ms",
        color_mode="light",
    )
    params.update(kw)
    return ConceptBrief(**params)


def _good_concept(**overrides) -> str:
    data = {
        "concept_name": "Kampung Editorial",
        "mood": ["warm", "honest", "generous"],
        "rationale": "Home cooking sold on trust — editorial warmth over food-court flash.",
        "palette": {
            "primary": "#9A3412", "secondary": "#7C2D12", "accent": "#FACC15",
            "background": "#FFF7ED", "surface": "#FFFFFF", "text": "#1C1917", "text_muted": "#57534E",
        },
        "fonts": {"heading": "Fraunces", "body": "Manrope"},
        "typography_note": "Big italic serif moments for dish names.",
        "hero": {"pattern": "editorial-stack", "description": "Oversized name over a bleed photo."},
        "sections": [
            {"id": "hero", "title": "Hero", "layout": "full-bleed", "purpose": "first impression"},
            {"id": "menu", "title": "Menu Harian", "layout": "two-column list with prices", "purpose": "sell"},
            {"id": "story", "title": "Kisah Kak Ropiah", "layout": "split", "purpose": "trust"},
            {"id": "hubungi", "title": "Hubungi & Pesan", "layout": "band", "purpose": "convert"},
            {"id": "footer", "title": "Footer", "layout": "minimal", "purpose": "close"},
        ],
        "signature_details": ["Hand-set numerals on prices", "Cream paper background"],
        "copy_voice": "Warm, direct, Malay with a smile.",
        "motion": "Gentle fade-ups only.",
    }
    data.update(overrides)
    return json.dumps(data)


# ---------------------------------------------------------------------------
# Freedom mode + brief
# ---------------------------------------------------------------------------

class TestFreedomMode:
    def test_default_is_designer(self, monkeypatch):
        monkeypatch.delenv("AI_DESIGN_FREEDOM_DEFAULT", raising=False)
        assert resolve_design_freedom(None) == "designer"

    def test_env_default_can_flip_to_guided(self, monkeypatch):
        monkeypatch.setenv("AI_DESIGN_FREEDOM_DEFAULT", "guided")
        assert resolve_design_freedom(None) == "guided"

    def test_request_value_beats_env(self, monkeypatch):
        monkeypatch.setenv("AI_DESIGN_FREEDOM_DEFAULT", "guided")
        assert resolve_design_freedom("designer") == "designer"
        assert resolve_design_freedom(" DESIGNER ") == "designer"

    def test_unknown_request_value_falls_to_default(self, monkeypatch):
        monkeypatch.delenv("AI_DESIGN_FREEDOM_DEFAULT", raising=False)
        assert resolve_design_freedom("wild") == "designer"

    def test_gallery_template_forces_guided(self):
        assert resolve_design_freedom("designer", template_id="elegance_dark") == "guided"

    def test_concept_flag_defaults_on(self, monkeypatch):
        monkeypatch.delenv("AI_DESIGN_CONCEPT_ENABLED", raising=False)
        assert dd.design_concept_enabled() is True
        monkeypatch.setenv("AI_DESIGN_CONCEPT_ENABLED", "off")
        assert dd.design_concept_enabled() is False


class TestBriefNormalisation:
    def test_empty_and_whitespace_are_none(self):
        assert normalize_design_brief(None) is None
        assert normalize_design_brief("") is None
        assert normalize_design_brief("   \n\t ") is None

    def test_whitespace_collapsed_and_capped(self):
        raw = "  gelap   dan   mewah \n\n\n\n aksen emas  "
        assert normalize_design_brief(raw) == "gelap dan mewah\n\naksen emas"
        assert len(normalize_design_brief("x" * 5000)) == DESIGN_BRIEF_MAX_CHARS

    def test_block_renders_brief_with_precedence(self):
        block = design_brief_block("Dark, moody, one gold accent")
        assert "MERCHANT'S DESIGN BRIEF" in block
        assert "Dark, moody, one gold accent" in block
        assert "NEVER overrides a NON-NEGOTIABLE" in block

    def test_block_empty_without_brief(self):
        assert design_brief_block(None) == ""
        assert design_brief_block("  ") == ""


# ---------------------------------------------------------------------------
# Concept prompt
# ---------------------------------------------------------------------------

class TestConceptPrompt:
    def test_frames_a_senior_designer_and_carries_the_business(self):
        p = build_concept_prompt(_brief())
        assert "senior designer" in p
        assert "Warung Kak Ropiah" in p
        assert "nasi campur" in p
        assert "Return ONLY a JSON object" in p

    def test_brief_is_highest_priority(self):
        p = build_concept_prompt(_brief(design_brief="Ala kopitiam retro, hijau & krim"))
        assert "MERCHANT'S DESIGN BRIEF (HIGHEST PRIORITY" in p
        assert "Ala kopitiam retro" in p

    def test_constraints_are_stated(self):
        p = build_concept_prompt(_brief(
            color_mode="dark", style_hint="elegant", color_hint="gold",
            has_images=False, menu_item_count=12, include_ecommerce=True,
        ))
        assert "Colour mode: DARK" in p
        assert "ELEGANT style" in p
        assert "GOLD colour theme" in p
        assert "Photography: NONE" in p
        assert "12 real item(s)" in p
        assert "no order buttons on cards" in p

    def test_brand_colours_beat_colour_hint(self):
        p = build_concept_prompt(_brief(color_hint="blue", brand_colors={"primary": "#112233"}))
        assert "Merchant brand colours" in p and "#112233" in p
        assert "BLUE colour theme" not in p

    def test_font_catalogue_is_listed_by_category(self):
        p = build_concept_prompt(_brief())
        for cat in ("SANS:", "SERIF:", "DISPLAY:", "HANDWRITING:"):
            assert cat in p
        assert "Fraunces" in p and "Bebas Neue" in p

    def test_design_only_no_invented_facts(self):
        p = build_concept_prompt(_brief())
        assert "Do not invent business facts" in p


# ---------------------------------------------------------------------------
# Font catalogue
# ---------------------------------------------------------------------------

class TestFontCatalogue:
    def test_resolve_is_case_and_punctuation_tolerant(self):
        assert resolve_font("playfair display") == "Playfair Display"
        assert resolve_font("'DM Sans', sans-serif") == "DM Sans"
        assert resolve_font("Plus+Jakarta+Sans") == "Plus Jakarta Sans"
        assert resolve_font("Comic Sans MS") is None
        assert resolve_font(None) is None

    def test_every_catalogue_entry_has_category_and_weights(self):
        for name, meta in GOOGLE_FONTS.items():
            assert meta["category"] in dd.FONT_FALLBACKS, name
            assert meta["weights"].split(";"), name
            for w in meta["weights"].split(";"):
                assert w.isdigit(), (name, w)

    def test_single_weight_faces_are_pinned_to_400(self):
        # A wrong weight 400s the whole Google Fonts stylesheet — these
        # faces ship exactly one weight.
        for name in ("Bebas Neue", "Pacifico", "Abril Fatface", "DM Serif Display", "Gloria Hallelujah"):
            assert GOOGLE_FONTS[name]["weights"] == "400", name


# ---------------------------------------------------------------------------
# Colour utilities
# ---------------------------------------------------------------------------

class TestColour:
    def test_normalize_hex(self):
        assert normalize_hex("#abc") == "#AABBCC"
        assert normalize_hex("1e40af") == "#1E40AF"
        assert normalize_hex("blue") is None
        assert normalize_hex(None) is None

    def test_contrast_ratio_extremes(self):
        assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, rel=1e-3)
        assert contrast_ratio("#777777", "#777777") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Concept parsing + validation
# ---------------------------------------------------------------------------

class TestParseConcept:
    def test_clean_concept_round_trips(self):
        c = parse_concept(_good_concept(), _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert c is not None
        assert c.name == "Kampung Editorial"
        assert c.palette["primary"] == "#9A3412"
        assert c.fonts["heading"] == "Fraunces" and c.fonts["body"] == "Manrope"
        assert c.fonts["heading_weights"] == GOOGLE_FONTS["Fraunces"]["weights"]
        assert c.fonts["heading_category"] == "serif"
        assert [s.id for s in c.sections] == ["hero", "menu", "story", "hubungi", "footer"]
        assert c.hero_pattern == "editorial-stack"
        assert c.adjustments == []
        assert c.source == "ai"

    def test_tolerates_markdown_fences_and_preamble(self):
        raw = "Here is the concept:\n```json\n" + _good_concept() + "\n```"
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert c is not None and c.name == "Kampung Editorial"

    def test_tolerates_trailing_commas(self):
        raw = _good_concept().replace('"motion": "Gentle fade-ups only."', '"motion": "Gentle fade-ups only.",')
        assert parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK) is not None

    def test_garbage_returns_none(self):
        assert parse_concept("<html>nope</html>", _brief(), FALLBACK_FONTS, LIGHT_FALLBACK) is None
        assert parse_concept("", _brief(), FALLBACK_FONTS, LIGHT_FALLBACK) is None
        assert parse_concept(None, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK) is None

    def test_invalid_hex_repaired_from_fallback(self):
        c = parse_concept(
            _good_concept(palette={"primary": "burnt orange", "background": "#FFF7ED"}),
            _brief(), FALLBACK_FONTS, LIGHT_FALLBACK,
        )
        assert c.palette["primary"] == LIGHT_FALLBACK["primary"]
        assert c.palette["secondary"] == LIGHT_FALLBACK["secondary"]
        assert any("palette.primary" in a for a in c.adjustments)

    def test_unreadable_text_is_replaced(self):
        raw = _good_concept(palette={
            "primary": "#9A3412", "secondary": "#7C2D12", "accent": "#FACC15",
            "background": "#FFF7ED", "surface": "#FFFFFF",
            "text": "#FFF3E0",  # cream on cream
            "text_muted": "#FFFFFF",
        })
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert contrast_ratio(c.palette["text"], c.palette["background"]) >= dd.MIN_TEXT_CONTRAST
        assert contrast_ratio(c.palette["text_muted"], c.palette["background"]) >= dd.MIN_MUTED_CONTRAST
        assert any("palette.text:" in a for a in c.adjustments)

    def test_dark_mode_is_enforced_when_concept_goes_light(self):
        c = parse_concept(_good_concept(), _brief(color_mode="dark"), FALLBACK_FONTS, DARK_FALLBACK)
        assert dd.is_dark(c.palette["background"])
        assert dd.is_dark(c.palette["surface"])
        assert contrast_ratio(c.palette["text"], c.palette["background"]) >= dd.MIN_TEXT_CONTRAST
        assert c.palette["border"].startswith("rgba(255")

    def test_light_mode_is_enforced_when_concept_goes_dark(self):
        raw = _good_concept(palette={
            "primary": "#F59E0B", "secondary": "#FBBF24", "accent": "#78350F",
            "background": "#111111", "surface": "#1A1A1A", "text": "#FFFFFF", "text_muted": "#AAAAAA",
        })
        c = parse_concept(raw, _brief(color_mode="light"), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert dd.is_light(c.palette["background"])
        assert any("did not match light mode" in a for a in c.adjustments)

    def test_invisible_primary_is_replaced(self):
        raw = _good_concept(palette={
            "primary": "#FFF7ED", "secondary": "#7C2D12", "accent": "#FACC15",
            "background": "#FFF7ED", "surface": "#FFFFFF", "text": "#1C1917", "text_muted": "#57534E",
        })
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert contrast_ratio(c.palette["primary"], c.palette["background"]) >= 2.0

    def test_merchant_brand_colours_override_the_concept(self):
        c = parse_concept(
            _good_concept(),
            _brief(brand_colors={"primary": "#1D4ED8", "accent": "#FDE047"}),
            FALLBACK_FONTS, LIGHT_FALLBACK,
        )
        assert c.palette["primary"] == "#1D4ED8"
        assert c.palette["accent"] == "#FDE047"
        assert c.palette["secondary"] == "#7C2D12"  # untouched

    def test_unknown_font_falls_back(self):
        c = parse_concept(
            _good_concept(fonts={"heading": "Helvetica Neue", "body": "Manrope"}),
            _brief(), FALLBACK_FONTS, LIGHT_FALLBACK,
        )
        assert c.fonts["heading"] == "Playfair Display"
        assert c.fonts["body"] == "Manrope"
        assert any("fonts.heading" in a for a in c.adjustments)

    def test_display_face_is_not_allowed_for_body_copy(self):
        c = parse_concept(
            _good_concept(fonts={"heading": "Bebas Neue", "body": "Bangers"}),
            _brief(), FALLBACK_FONTS, LIGHT_FALLBACK,
        )
        assert c.fonts["heading"] == "Bebas Neue"
        assert c.fonts["body"] == "Mulish"

    def test_missing_fonts_use_fallback_pairing(self):
        c = parse_concept(_good_concept(fonts=None), _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert (c.fonts["heading"], c.fonts["body"]) == ("Playfair Display", "Mulish")

    def test_required_sections_are_added_when_missing(self):
        raw = _good_concept(sections=[
            {"id": "hero", "title": "Hero"},
            {"id": "gallery", "title": "Galeri"},
        ])
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        ids = [s.id for s in c.sections]
        assert ids[0] == "hero" and ids[-1] == "footer"
        assert "offerings" in ids and "about" in ids and "contact" in ids
        assert ids.index("offerings") < ids.index("contact") < ids.index("footer")

    def test_hero_first_footer_last_are_enforced(self):
        raw = _good_concept(sections=[
            {"id": "footer", "title": "Footer"},
            {"id": "menu", "title": "Menu"},
            {"id": "about", "title": "About"},
            {"id": "contact", "title": "Contact"},
            {"id": "hero", "title": "Hero"},
        ])
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        ids = [s.id for s in c.sections]
        assert ids[0] == "hero" and ids[-1] == "footer"

    def test_section_ids_are_slugged_and_unique(self):
        raw = _good_concept(sections=[
            {"id": "Hero Section!", "title": "Hero"},
            {"id": "Menu", "title": "Menu"},
            {"id": "Menu", "title": "Menu 2"},
            {"id": "about", "title": "About"},
            {"id": "contact", "title": "Contact"},
            {"id": "footer", "title": "Footer"},
        ])
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        ids = [s.id for s in c.sections]
        assert ids[0] == "hero-section"
        assert len(ids) == len(set(ids))

    def test_too_many_sections_are_trimmed(self):
        raw = _good_concept(sections=[{"id": f"s{i}", "title": f"Section {i}"} for i in range(20)])
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert len(c.sections) <= dd.MAX_SECTIONS + 2
        assert any("trimmed" in a for a in c.adjustments)

    def test_long_strings_are_clipped(self):
        raw = _good_concept(
            rationale="r" * 2000,
            signature_details=["d" * 1000] * 20,
            mood=["m" * 100] * 10,
        )
        c = parse_concept(raw, _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        assert len(c.rationale) <= dd._LONG
        assert len(c.signature_details) == dd.MAX_SIGNATURE_DETAILS
        assert all(len(d) <= dd._SHORT for d in c.signature_details)
        assert len(c.mood) == 5

    def test_missing_palette_is_the_fallback(self):
        c = parse_concept(_good_concept(palette=None), _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        for key in dd.PALETTE_KEYS:
            assert c.palette[key] == LIGHT_FALLBACK[key]


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

class TestConceptRendering:
    def test_prompt_block_carries_every_part(self):
        c = parse_concept(_good_concept(), _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        block = c.to_prompt_block()
        assert 'DESIGN CONCEPT — "Kampung Editorial"' in block
        assert "warm · honest · generous" in block
        assert "primary #9A3412" in block
        assert "headings in 'Fraunces'" in block and "body in 'Manrope'" in block
        assert "Hero: EDITORIAL-STACK" in block
        assert "2. Menu Harian — two-column list with prices" in block
        assert "Hand-set numerals on prices" in block
        assert "Copy voice: Warm, direct" in block

    def test_section_checklist_is_numbered_in_order(self):
        c = parse_concept(_good_concept(), _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        checklist = c.section_checklist().splitlines()
        assert checklist[0].startswith("1. HERO")
        assert checklist[-1].startswith("5. FOOTER")

    def test_as_dict_is_json_serialisable(self):
        c = parse_concept(_good_concept(), _brief(), FALLBACK_FONTS, LIGHT_FALLBACK)
        payload = json.loads(json.dumps(c.as_dict()))
        assert payload["fonts"] == {"heading": "Fraunces", "body": "Manrope"}
        assert payload["hero"]["pattern"] == "editorial-stack"
