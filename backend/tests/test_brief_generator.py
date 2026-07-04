"""M1 brief-generator tests — LLM mocked, no network."""

import copy

import pytest

from app.models.schemas import Language, WebsiteGenerationRequest
from app.schemas.recipe import VALID_VARIANTS, SectionType
from app.schemas.style_dna import STYLE_DNAS
from app.services import brief_generator
from app.services.brief_generator import (
    IMPLEMENTED_VARIANTS,
    BriefGenerationError,
    generate_brief,
)
from app.services.intent_extractor import DNA_RUBRIC, keyword_intent
from app.utils.llm_json import LLMJSONError


def make_request(**overrides) -> WebsiteGenerationRequest:
    defaults = dict(
        description="Mamak 24 jam di Bangi, roti canai garing, gaya retro neon.",
        business_name="Mamak Bintang",
        subdomain="preview",
        language=Language.MALAY,
        whatsapp_number="+60123456789",
        color_mode="dark",
    )
    defaults.update(overrides)
    return WebsiteGenerationRequest(**defaults)


VALID_BRIEF = {
    "language": "ms",
    "business": {
        "name": "Mamak Bintang",
        "type": "restaurant",
        "tagline": "Roti canai garing sampai pagi",
        "about": ["Mamak 24 jam di Bangi.", "Port lepak paling happening."],
        "address": "Bangi, Selangor",
        "whatsapp": "+60123456789",
        "operating_hours": "24 jam",
    },
    "style_dna": "pasar_malam_neon",
    "color_mode": "dark",
    "cuisine_type": "mamak",
    "specific_dishes": ["roti canai", "teh tarik"],
    "sections": [
        {"type": "hero", "variant": "split", "content": {
            "headline": "Roti Canai Garing Sampai Pagi",
            "subheadline": "Mamak 24 jam di Bangi",
            "cta_text": "Pesan Sekarang", "cta_link": "#menu",
            "image_key": "hero", "halal_certified": True,
        }},
        {"type": "menu", "variant": "grid", "content": {
            "heading": "Menu Kami",
            "fallback_items": [
                {"name": "Roti Canai", "description": "Garing di luar", "price": "RM 2.00", "is_popular": True},
                {"name": "Teh Tarik", "description": "Kaw dan berbuih", "price": "RM 2.50"},
            ],
        }},
        {"type": "hours", "variant": "simple-table", "content": {
            "heading": "Waktu Operasi",
            "hours_structured": [{"day": "Setiap Hari", "time": "24 Jam"}],
        }},
        {"type": "contact", "variant": "simple", "content": {
            "heading": "Hubungi Kami", "address": "Bangi, Selangor",
            "whatsapp_number": "60123456789",
        }},
        {"type": "footer", "variant": "brand", "content": {
            "tagline": "Roti canai garing sampai pagi", "powered_by": True,
        }},
    ],
    "image_map": {},
    "features": {"whatsapp": True},
}


def mock_llm(responses):
    """Return an async fake for call_deepseek_json yielding queued responses
    (each entry is a dict to return, or an Exception to raise)."""
    queue = list(responses)
    calls = []

    async def fake(prompt, **kwargs):
        calls.append(prompt)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)

    fake.calls = calls
    return fake


class TestVariantCatalog:
    def test_only_renderable_variants_offered(self):
        # Known implemented ones present…
        assert "split" in IMPLEMENTED_VARIANTS["hero"]
        assert "grid" in IMPLEMENTED_VARIANTS["menu"]
        # …and known declared-but-unimplemented ones excluded.
        assert "video" not in IMPLEMENTED_VARIANTS["hero"]
        assert "lightbox" not in IMPLEMENTED_VARIANTS["gallery"]
        assert "cards" not in IMPLEMENTED_VARIANTS["menu"]

    def test_every_section_type_has_at_least_one_variant(self):
        for section in SectionType:
            assert IMPLEMENTED_VARIANTS[section.value], section

    def test_catalog_is_subset_of_declared(self):
        for section, variants in IMPLEMENTED_VARIANTS.items():
            declared = VALID_VARIANTS[SectionType(section)]
            assert set(variants) <= set(declared)

    def test_dna_rubric_covers_all_dnas(self):
        assert set(DNA_RUBRIC) == set(STYLE_DNAS)


class TestGenerateBrief:
    async def test_valid_output_returns_brief(self, monkeypatch):
        fake = mock_llm([VALID_BRIEF])
        monkeypatch.setattr(brief_generator, "call_deepseek_json", fake)
        request = make_request()
        brief = await generate_brief(request, keyword_intent(request.description))
        assert brief.style_dna.value == "pasar_malam_neon"
        assert brief.language == "ms"
        # WhatsApp normalized to digits by the DesignBrief validator
        assert brief.business.whatsapp == "60123456789"
        assert len(fake.calls) == 1

    async def test_language_is_forced_from_request(self, monkeypatch):
        wrong_lang = copy.deepcopy(VALID_BRIEF)
        wrong_lang["language"] = "ms"  # model ignored the English request
        monkeypatch.setattr(brief_generator, "call_deepseek_json", mock_llm([wrong_lang]))
        request = make_request(language=Language.ENGLISH)
        brief = await generate_brief(request, keyword_intent(request.description))
        assert brief.language == "en"

    async def test_unimplemented_variant_retried_with_feedback(self, monkeypatch):
        bad = copy.deepcopy(VALID_BRIEF)
        bad["sections"][0]["variant"] = "video"  # declared but no renderer
        fake = mock_llm([bad, VALID_BRIEF])
        monkeypatch.setattr(brief_generator, "call_deepseek_json", fake)
        request = make_request()
        brief = await generate_brief(request, keyword_intent(request.description))
        assert brief.sections[0].variant == "split"
        assert len(fake.calls) == 2
        assert "unimplemented section variants" in fake.calls[1]

    async def test_forbidden_wording_fails_after_retry(self, monkeypatch):
        bad = copy.deepcopy(VALID_BRIEF)
        bad["business"]["tagline"] = "Halal Certified sejak 1998"
        monkeypatch.setattr(brief_generator, "call_deepseek_json", mock_llm([bad, bad]))
        request = make_request()
        with pytest.raises(BriefGenerationError, match="forbidden wording"):
            await generate_brief(request, keyword_intent(request.description))

    async def test_schema_garbage_fails_after_retry(self, monkeypatch):
        monkeypatch.setattr(
            brief_generator, "call_deepseek_json",
            mock_llm([{"nonsense": True}, {"nonsense": True}]),
        )
        request = make_request()
        with pytest.raises(BriefGenerationError):
            await generate_brief(request, keyword_intent(request.description))

    async def test_llm_error_fails_after_retry(self, monkeypatch):
        monkeypatch.setattr(
            brief_generator, "call_deepseek_json",
            mock_llm([LLMJSONError("boom"), LLMJSONError("boom")]),
        )
        request = make_request()
        with pytest.raises(BriefGenerationError):
            await generate_brief(request, keyword_intent(request.description))

    async def test_prompt_carries_rules_and_intent(self, monkeypatch):
        fake = mock_llm([VALID_BRIEF])
        monkeypatch.setattr(brief_generator, "call_deepseek_json", fake)
        request = make_request()
        intent = keyword_intent(request.description)
        await generate_brief(request, intent)
        prompt = fake.calls[0]
        assert "Pengusaha Muslim" in prompt
        assert "Trade Descriptions Act" in prompt
        assert "Bahasa Malaysia" in prompt
        assert intent.recommended_style_dna in prompt


class TestKeywordIntentFallback:
    @pytest.mark.parametrize("description,expected_dna", [
        ("mamak retro neon 24 jam untuk student", "pasar_malam_neon"),
        ("kopitiam lama nostalgia sejak 1962", "kopitiam_nostalgia"),
        ("fine dining degustasi premium mewah", "fine_dining_obsidian"),
        ("kafe minimalist banyak white space", "sutera_putih"),
        ("katering kenduri perkahwinan grand", "warisan_emas"),
        ("restoran biasa sedap", "teh_tarik_warm"),
    ])
    def test_keyword_dna_mapping(self, description, expected_dna):
        intent = keyword_intent(description)
        assert intent.recommended_style_dna == expected_dna
        assert intent.source == "fallback"
