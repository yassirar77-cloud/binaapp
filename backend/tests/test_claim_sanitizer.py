"""
Tests for the sensitive-claim sanitizer (Layer 2 of the invented-claims fix)
and the strengthened prompts / no-text hero prompts.

Covers:
- sanitize_sensitive_claims(): invented badge removal, merchant-stated claims
  kept, est-year verification against merchant data, prose stripping that
  keeps the surrounding sentence, removal logging, config extensibility
- Pipeline wiring: the sanitizer runs on BOTH the GLM primary path and the
  DeepSeek fallback path of generate_website
- Rule 4 / reviewer checklist: the GLM system prompt and design-review prompt
  carry the sensitive-claim categories
- _autofill_hero_prompt(): no-text suffix + food-centric composition; item
  prompts unchanged

All HTTP calls are mocked — no live API usage.
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from loguru import logger

import app.services.ai_service as ai_service_module
from app.services.ai_service import AIService
from app.services.claim_sanitizer import (
    sanitize_sensitive_claims,
    sensitive_claim_patterns,
    DEFAULT_SENSITIVE_CLAIM_PATTERNS,
)


def _page(body: str) -> str:
    return (
        "<!DOCTYPE html><html><head><title>t</title></head>"
        f"<body>{body}</body></html>"
    )


# ── sanitize_sensitive_claims ────────────────────────────────────────────────

class TestSanitizeSensitiveClaims:

    def test_invented_pengusaha_muslim_badge_removed(self):
        """The exact production failure: an invented 'Est. 2024 · Pengusaha
        Muslim' badge the merchant never provided is removed entirely."""
        html = _page(
            '<h1>Restoran Nasi Kandar Yassir</h1>'
            '<span class="badge">Est. 2024 · Pengusaha Muslim</span>'
            '<p>Nasi kandar paling sedap di Pulau Pinang.</p>'
        )
        out, removed = sanitize_sensitive_claims(
            html, ["Restoran Nasi Kandar Yassir", "Nasi kandar paling sedap di Pulau Pinang"]
        )
        assert "Pengusaha Muslim" not in out
        assert "Est. 2024" not in out
        assert removed  # at least one claim reported
        # The rest of the page is intact.
        assert "<h1>Restoran Nasi Kandar Yassir</h1>" in out
        assert "Nasi kandar paling sedap di Pulau Pinang." in out

    def test_badge_element_removed_not_just_text(self):
        """A small badge/pill element is dropped wholesale — no empty husk."""
        html = _page('<p>Selamat datang.</p><span class="pill">Pengusaha Muslim</span>')
        out, removed = sanitize_sensitive_claims(html, ["Kedai makan biasa"])
        assert '<span class="pill">' not in out
        assert removed == ["Pengusaha Muslim"]

    def test_halal_kept_when_merchant_states_it(self):
        """A merchant who declares halal status themselves keeps the claim."""
        html = _page('<span class="badge">100% Halal</span><p>Makanan halal untuk semua.</p>')
        out, removed = sanitize_sensitive_claims(
            html, ["Restoran Contoh", "Restoran makanan halal di KL, dijamin halal"]
        )
        assert "Halal" in out
        assert removed == []

    def test_halal_removed_when_absent_from_merchant_data(self):
        html = _page('<span class="badge">Halal Certified</span>')
        out, removed = sanitize_sensitive_claims(html, ["Kedai Barat", "Western food restaurant"])
        assert "Halal" not in out
        assert removed == ["Halal"]

    def test_halal_word_boundary_no_false_positive(self):
        """'halal' must match on word boundaries only — no substring hits."""
        html = _page("<p>Kedai kami di Jalan Mahalalila.</p>")
        out, removed = sanitize_sensitive_claims(html, ["Kedai Contoh"])
        assert removed == []
        assert out == html

    def test_est_year_removed_when_no_year_in_data(self):
        html = _page('<span class="badge">Est. 2024</span>')
        out, removed = sanitize_sensitive_claims(html, ["Restoran Yassir", "Nasi kandar sedap"])
        assert "Est. 2024" not in out
        assert removed == ["Est. 2024"]

    def test_est_year_kept_when_merchant_provided_year(self):
        html = _page('<span class="badge">Est. 1998</span>')
        out, removed = sanitize_sensitive_claims(
            html, ["Restoran Lama", "Beroperasi sejak tahun 1998 di Georgetown"]
        )
        assert "Est. 1998" in out
        assert removed == []

    def test_sejak_year_verified_against_data(self):
        html = _page("<p>Kami berkhidmat sejak 2010 dengan penuh dedikasi.</p>")
        out, removed = sanitize_sensitive_claims(html, ["Kedai", "Dibuka pada 2010"])
        assert "sejak 2010" in out
        assert removed == []
        out2, removed2 = sanitize_sensitive_claims(html, ["Kedai", "Kedai makan"])
        assert "sejak 2010" not in out2
        assert removed2 == ["sejak 2010"]

    def test_prose_stripping_keeps_surrounding_sentence(self):
        """Inside long prose only the claim text is stripped — the paragraph
        element and the rest of the sentence survive."""
        html = _page(
            "<p>Kami menyajikan nasi kandar yang paling autentik di Pulau Pinang, "
            "disediakan tanpa babi oleh chef berpengalaman lebih sepuluh tahun "
            "untuk seluruh keluarga anda menikmatinya setiap hari.</p>"
        )
        out, removed = sanitize_sensitive_claims(html, ["Restoran", "Nasi kandar autentik"])
        assert removed == ["tanpa babi"]
        assert "<p>Kami menyajikan nasi kandar yang paling autentik" in out
        assert "chef berpengalaman" in out
        assert "tanpa babi" not in out

    def test_compound_badge_dangling_separator_cleaned(self):
        """Stripping one claim from a compound text leaves no dangling '·'."""
        html = _page(
            "<p>Restoran keluarga terkenal dengan pelbagai juadah istimewa "
            "yang memikat selera · Milik Muslim · dan kami sedia melayani anda "
            "dari pagi hingga lewat malam setiap hari tanpa henti.</p>"
        )
        out, removed = sanitize_sensitive_claims(html, ["Restoran Keluarga"])
        assert removed == ["Milik Muslim"]
        assert "· ·" not in out and "··" not in out

    def test_removals_are_logged(self):
        """Every removal is logged with the 🛡 marker."""
        records = []
        sink_id = logger.add(lambda m: records.append(str(m)), level="INFO")
        try:
            sanitize_sensitive_claims(
                _page('<span class="badge">Pengusaha Muslim</span>'), ["Kedai"]
            )
        finally:
            logger.remove(sink_id)
        assert any("🛡 Removed unverified claim: 'Pengusaha Muslim'" in r for r in records)

    def test_no_pork_and_pork_free_and_jakim_removed(self):
        html = _page(
            '<span class="b1">No Pork No Lard</span>'
            '<span class="b2">Pork-Free</span>'
            '<span class="b3">Disahkan JAKIM</span>'
        )
        out, removed = sanitize_sensitive_claims(html, ["Kedai Kopi", "Kopi dan roti bakar"])
        assert "Pork" not in out and "JAKIM" not in out
        assert len(removed) == 3

    def test_bumiputera_removed_when_uninvented_kept_when_stated(self):
        html = _page('<span class="badge">Syarikat Bumiputera</span>')
        out, removed = sanitize_sensitive_claims(html, ["Syarikat ABC"])
        assert "Bumiputera" not in out
        out2, removed2 = sanitize_sensitive_claims(
            html, ["Syarikat ABC", "Syarikat 100% milik Bumiputera"]
        )
        assert "Bumiputera" in out2 and removed2 == []

    def test_claims_inside_tag_markup_are_left_alone(self):
        """Matches inside <...> markup (class names, attrs) are skipped so
        stylesheet/JS hooks are never broken."""
        html = _page('<div class="halal-badge-style">Menu istimewa kami</div>')
        out, removed = sanitize_sensitive_claims(html, ["Kedai"])
        assert out == html
        assert removed == []

    def test_empty_html_is_safe(self):
        assert sanitize_sensitive_claims("", ["x"]) == ("", [])

    def test_pattern_list_extensible_via_env(self, monkeypatch):
        """SENSITIVE_CLAIM_PATTERNS_EXTRA extends the list without code changes."""
        monkeypatch.setenv(
            "SENSITIVE_CLAIM_PATTERNS_EXTRA",
            json.dumps([{"label": "mesti", "pattern": r"\bkoshersure\b", "verify": "pattern"}]),
        )
        labels = [p["label"] for p in sensitive_claim_patterns()]
        assert "mesti" in labels
        assert "halal" in labels  # defaults still active
        html = _page('<span class="badge">KosherSure</span>')
        out, removed = sanitize_sensitive_claims(html, ["Kedai"])
        assert "KosherSure" not in out and removed == ["KosherSure"]

    def test_pattern_env_full_override(self, monkeypatch):
        monkeypatch.setenv(
            "SENSITIVE_CLAIM_PATTERNS",
            json.dumps([{"label": "only", "pattern": r"\bfoo\b", "verify": "pattern"}]),
        )
        assert [p["label"] for p in sensitive_claim_patterns()] == ["only"]
        # With the defaults replaced, halal is no longer scanned.
        html = _page('<span class="badge">Halal</span>')
        out, removed = sanitize_sensitive_claims(html, ["Kedai"])
        assert "Halal" in out and removed == []

    def test_malformed_pattern_env_falls_back_to_defaults(self, monkeypatch):
        monkeypatch.setenv("SENSITIVE_CLAIM_PATTERNS", "{not json")
        assert sensitive_claim_patterns() == DEFAULT_SENSITIVE_CLAIM_PATTERNS

    def test_default_pattern_list_covers_spec(self):
        labels = {p["label"] for p in DEFAULT_SENSITIVE_CLAIM_PATTERNS}
        assert {
            "pengusaha-muslim", "muslim-owned", "milik-muslim", "bumiputera",
            "halal", "jakim", "no-pork", "tanpa-babi", "pork-free",
            "est-year", "sejak-year", "established-year",
        } <= labels


# ── pipeline wiring: sanitizer runs on BOTH provider paths ───────────────────

TAINTED_HTML = (
    "<!DOCTYPE html><html><head><title>t</title></head>"
    "<body><h1>Kedai Test</h1>"
    '<span class="badge">Est. 2024 · Pengusaha Muslim</span>'
    "<p>" + ("x" * 200) + "</p></body></html>"
)


def _make_request():
    from app.models.schemas import WebsiteGenerationRequest
    return WebsiteGenerationRequest(
        business_name="Kedai Test",
        description="Kedai makan mamak di KL",
        whatsapp_number="0123456789",
        subdomain="kedai-test",
    )


from app.services.generation_validator import ValidationResult

_PASSING_VALIDATION = ValidationResult()


def _neutralize_post_processing(service):
    """Stub the deterministic post-HTML steps EXCEPT the claim sanitizer."""
    service._validate_generated_html = MagicMock(return_value=[])
    service._improve_with_qwen = AsyncMock(side_effect=lambda html, desc: html)
    service._fix_placeholders = MagicMock(side_effect=lambda html, *a, **k: html)
    service._fix_menu_item_images = MagicMock(side_effect=lambda html, *a, **k: html)
    service._generate_ai_food_images = AsyncMock(side_effect=lambda html, **k: (html, 0))
    service._fix_broken_image_urls = MagicMock(side_effect=lambda html, *a, **k: html)
    # Validation is post-processing too: it can trigger a repair call,
    # which would otherwise look like a fallback-chain DeepSeek hit.
    service._validate_and_repair = AsyncMock(
        side_effect=lambda html, request, **k: (html, _PASSING_VALIDATION)
    )


@pytest.fixture
def service():
    svc = AIService()
    svc.zai_api_key = "test-zai-key"
    return svc


class TestSanitizerPipelineWiring:

    @pytest.mark.asyncio
    async def test_glm_path_output_is_sanitized(self, service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", True)
        service._call_glm = AsyncMock(return_value=TAINTED_HTML)
        service._call_deepseek = AsyncMock(return_value="<html>deepseek</html>")
        _neutralize_post_processing(service)

        result = await service.generate_website(_make_request(), image_choice="none")

        service._call_glm.assert_awaited_once()
        service._call_deepseek.assert_not_awaited()  # GLM path, not fallback
        assert "Pengusaha Muslim" not in result.html_content
        assert "Est. 2024" not in result.html_content
        assert "<h1>Kedai Test</h1>" in result.html_content

    @pytest.mark.asyncio
    async def test_deepseek_fallback_output_is_sanitized(self, service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
        service._call_glm = AsyncMock(return_value=None)
        service._call_deepseek = AsyncMock(return_value=TAINTED_HTML)
        _neutralize_post_processing(service)

        result = await service.generate_website(_make_request(), image_choice="none")

        service._call_deepseek.assert_awaited()
        assert "Pengusaha Muslim" not in result.html_content
        assert "Est. 2024" not in result.html_content
        assert "<h1>Kedai Test</h1>" in result.html_content

    @pytest.mark.asyncio
    async def test_merchant_stated_claim_survives_pipeline(self, service, monkeypatch):
        """A merchant whose description states halal keeps the halal badge."""
        from app.models.schemas import WebsiteGenerationRequest
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
        request = WebsiteGenerationRequest(
            business_name="Kedai Test",
            description="Kedai makan mamak halal di KL",
            whatsapp_number="0123456789",
            subdomain="kedai-test",
        )
        html = (
            "<!DOCTYPE html><html><head><title>t</title></head>"
            '<body><h1>Kedai Test</h1><span class="badge">Halal</span>'
            "<p>" + ("x" * 200) + "</p></body></html>"
        )
        service._call_deepseek = AsyncMock(return_value=html)
        _neutralize_post_processing(service)

        result = await service.generate_website(request, image_choice="none")

        assert "Halal" in result.html_content


# ── Layer 1: prompt rules ────────────────────────────────────────────────────

class TestPromptRules:

    def test_glm_rule_4_covers_sensitive_claims(self):
        rules = ai_service_module.AIService._GLM_PROMPT_RULES_HEAD
        for phrase in (
            "Pengusaha Muslim", "Muslim-owned", "Milik Muslim", "Bumiputera",
            "JAKIM", "HACCP", "ISO", "Est. 20XX", "Sejak 19XX",
            "Established 20XX", "pork-free", "no pork no lard", "tanpa babi",
        ):
            assert phrase in rules, f"Rule 4 missing sensitive-claim phrase: {phrase}"
        assert "ONLY if the exact claim is present" in rules

    def test_rule_4_reaches_both_image_mode_branches(self, service):
        """RULES_HEAD (carrying rule 4) is shared by the photo-slot and
        no-photo prompt compositions."""
        for has_images in (True, False):
            composed = (
                ai_service_module.AIService._GLM_PROMPT_GOAL
                + ai_service_module.AIService._GLM_PROMPT_RULES_HEAD
                + (
                    ai_service_module.AIService._GLM_PHOTO_SLOT_CLAUSE
                    if has_images
                    else ai_service_module.AIService._GLM_NO_PHOTO_CLAUSE
                )
                + ai_service_module.AIService._GLM_PROMPT_RULES_TAIL
            )
            assert "Pengusaha Muslim" in composed

    def test_design_review_checklist_covers_sensitive_claims(self, service):
        for has_images in (True, False):
            prompt = service._build_design_review_prompt(has_images=has_images)
            assert "SENSITIVE-CLAIM CHECK" in prompt
            assert "Pengusaha Muslim" in prompt
            assert "JAKIM" in prompt


# ── Fix 2: hero prompts ──────────────────────────────────────────────────────

NO_TEXT_SUFFIX = "no text, no signage, no words, no lettering anywhere in the image"


class TestHeroPrompts:

    def test_food_hero_has_no_text_suffix(self, service):
        prompt = service._autofill_hero_prompt("food", "restaurant")
        assert NO_TEXT_SUFFIX in prompt

    def test_food_hero_is_food_centric_not_interior(self, service):
        prompt = service._autofill_hero_prompt("food", "restaurant").lower()
        # Food-centric composition terms
        assert "spread" in prompt
        assert "plated food" in prompt or "close-up" in prompt
        assert "hands serving" in prompt
        assert "warm ambience" in prompt
        assert "shallow depth of field" in prompt
        # No storefront/interior scene where signboards appear garbled
        assert "interior" not in prompt
        assert "hanging menu" not in prompt
        assert "storefront" not in prompt

    @pytest.mark.parametrize("category", ["creative", "retail", "generic"])
    def test_other_hero_categories_carry_no_text_suffix(self, service, category):
        prompt = service._autofill_hero_prompt(category, "photography studio")
        assert NO_TEXT_SUFFIX in prompt

    def test_item_prompts_keep_their_subjects(self, service):
        """Item-level subjects are unchanged by the no-text rollout: the
        item stays the subject, the suffix is purely additive. (Item prompts
        used to ship WITHOUT the suffix — that's how gallery images got
        garbled baked-in text; see test_autofill_image_prompts.py for the
        full no-text coverage.)"""
        # Food still returns the raw name — the suffix is applied later by
        # _get_malaysian_prompt inside the provider dispatch.
        assert service._autofill_item_prompt("food", "Nasi Kandar", "restaurant") == "Nasi Kandar"
        # Retail now grounds the item in the business type (gogoo fix) —
        # the item is still the leading subject.
        retail = service._autofill_item_prompt("retail", "Baju Kurung", "clothing store")
        assert retail.startswith(
            "Professional product photography of Baju Kurung, a clothing store product"
        )
        assert "commercial product shot" in retail
        assert NO_TEXT_SUFFIX in retail
        creative = service._autofill_item_prompt("creative", "Wedding Photography", "photography")
        assert "Wedding Photography" in creative
        assert NO_TEXT_SUFFIX in creative
        generic = service._autofill_item_prompt("generic", "Servis Aircond", "aircond service")
        assert generic.startswith(
            "Professional photography of Servis Aircond, aircond service, "
            "high quality, sharp focus"
        )
        assert NO_TEXT_SUFFIX in generic
