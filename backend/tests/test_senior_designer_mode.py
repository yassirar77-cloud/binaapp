"""Senior Designer mode — the ai_service side.

  - _build_strict_prompt in designer mode: role framing, precedence ladder,
    house rules softened, hero blueprint dropped when a concept exists,
    concept palette/fonts wired into the HEAD, page plan replaces the
    numbered layout; every fact/technical rule still present verbatim.
  - guided mode is byte-for-byte the pre-upgrade prompt shape.
  - the merchant's brief reaches the prompt (both modes) and the reviewer.
  - request schema + generate/start parsing accept the new fields.
  - generate_website runs the concept step only in designer mode, hands the
    concept to the prompt builder, and survives a concept failure.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import ai_service as ai_service_module
from app.services.ai_service import AIService, DESIGNER_SYSTEM_PROMPT
from app.services.design_director import ConceptBrief, parse_concept


@pytest.fixture
def service():
    svc = AIService.__new__(AIService)
    svc._last_design_concept = None
    return svc


LIGHT = {
    "primary": "#B45309", "secondary": "#78350F", "accent": "#FDE68A",
    "background": "#FFFBEB", "surface": "#FFFFFF", "text": "#1C1917", "text_muted": "#57534E",
}


def _concept():
    raw = json.dumps({
        "concept_name": "Kopitiam Noir",
        "mood": ["moody", "nostalgic"],
        "rationale": "A late-night kopitiam deserves drama.",
        "palette": {
            "primary": "#B45309", "secondary": "#78350F", "accent": "#FDE68A",
            "background": "#FFFBEB", "surface": "#FFFFFF", "text": "#1C1917", "text_muted": "#57534E",
        },
        "fonts": {"heading": "Bodoni Moda", "body": "Figtree"},
        "hero": {"pattern": "poster", "description": "Giant name, one photo, one line."},
        "sections": [
            {"id": "hero", "title": "Hero", "layout": "poster"},
            {"id": "menu", "title": "Menu Malam", "layout": "single column list"},
            {"id": "about", "title": "Kisah", "layout": "split"},
            {"id": "contact", "title": "Hubungi", "layout": "band"},
            {"id": "footer", "title": "Footer"},
        ],
        "signature_details": ["Neon accent rule under the name"],
        "copy_voice": "Dry and warm.",
    })
    return parse_concept(
        raw,
        ConceptBrief(business_name="Kopitiam Ah Seng", description="kopitiam", color_mode="light"),
        {"heading": "Playfair Display", "body": "Mulish"},
        LIGHT,
    )


def _prompt(service, **kw):
    params = dict(
        name="Kopitiam Ah Seng",
        desc="Kopitiam lama di Ipoh, kopi cham dan roti bakar sejak pagi.",
        style="modern",
        language="ms",
        whatsapp_number="0193456781",
        image_choice="ai",
        images={"hero": "https://cdn.test/h.jpg", "gallery1": "https://cdn.test/g1.jpg"},
    )
    params.update(kw)
    return service._build_strict_prompt(**params)


# Fact/technical rules that must survive in BOTH modes, verbatim.
NON_NEGOTIABLES = (
    "STAT / BADGE NUMBERS MUST BE REAL",
    "MUST NEVER OVERLAP",
    "min-w-0",
    "RELATIONSHIPS AND PROVENANCE MUST BE EXACT",
    "IMAGE ALT TEXT",
    "IMAGE REUSE — EACH PHOTO APPEARS ONCE",
    "CARDS MUST STAY READABLE EVEN IF AN IMAGE FAILS",
    "Font Awesome FREE 6.x ONLY",
    "BRAND / LOGO (non-negotiable)",
    "Render the copyright year DYNAMICALLY",
    "MOBILE & POLISH (NON-NEGOTIABLE)",
    "WHATSAPP LINKS",
    "wa.me/60193456781",
    "Do NOT add any other <link> to fonts.googleapis.com",
    "ABSOLUTELY FORBIDDEN",
)


class TestGuidedModeUnchanged:
    def test_default_mode_is_guided_for_direct_callers(self, service):
        p = _prompt(service)
        assert p.startswith("Generate a COMPLETE production-ready HTML website.")
        assert "DESIGN MODE: GUIDED" in p
        assert "ART DIRECTION (NON-NEGOTIABLE)" in p
        assert "HERO BLUEPRINT (follow the structure, replace the content)" in p
        assert "LAYOUT STRUCTURE" in p and "MUST FOLLOW" in p
        assert "LAYOUT FLEXIBILITY" in p
        assert "CREATIVE FREEDOM" in p
        assert "STUDIO STANDARDS" not in p
        assert "PRECEDENCE" not in p
        assert "senior designer" not in p.lower()

    def test_guided_keeps_every_non_negotiable(self, service):
        p = _prompt(service)
        for rule in NON_NEGOTIABLES:
            assert rule in p, rule

    def test_brief_reaches_guided_prompt_too(self, service):
        p = _prompt(service, design_brief="Ala kopitiam retro hijau & krim")
        assert "MERCHANT'S DESIGN BRIEF (HIGHEST DESIGN PRIORITY)" in p
        assert "Ala kopitiam retro hijau & krim" in p


class TestDesignerModeWithoutConcept:
    def test_role_framing_and_softened_house_rules(self, service):
        p = _prompt(service, design_freedom="designer")
        assert p.startswith("You are the senior designer at a boutique web studio")
        assert "DESIGN MODE: SENIOR DESIGNER" in p
        assert "STUDIO STANDARDS (house defaults" in p
        assert "ART DIRECTION (NON-NEGOTIABLE)" not in p
        assert "HOUSE DEFAULTS (typography sizes, spacing, card patterns, animations)" in p
        assert "===== PRECEDENCE (when instructions conflict) =====" in p
        assert "CREATIVE OWNERSHIP" in p
        assert "LAYOUT OWNERSHIP" in p
        assert "LAYOUT FLEXIBILITY" not in p

    def test_hero_blueprint_becomes_a_reference(self, service):
        p = _prompt(service, design_freedom="designer")
        assert "HERO REFERENCE (one proven option" in p
        assert "This blueprint is a REFERENCE, not a mandate" in p
        # The placeholder-token rules still apply if the model uses it.
        assert "HERO_IMAGE_URL = the exact hero image URL" in p

    def test_layout_is_a_reference_checklist(self, service):
        p = _prompt(service, design_freedom="designer")
        assert "REFERENCE checklist, not a mandate" in p
        assert "LAYOUT STRUCTURE" in p  # still there as reference content

    def test_generic_font_rule_is_softened_not_removed(self, service):
        p = _prompt(service, design_freedom="designer")
        assert "Avoid Inter, Roboto, Arial or system-ui as the VISIBLE typeface" in p
        assert "Do NOT use Inter or Roboto — they read as generic defaults." not in p
        assert "Use ONLY the heading/body fonts provided in the HEAD section above." in p

    def test_all_non_negotiables_survive(self, service):
        p = _prompt(service, design_freedom="designer")
        for rule in NON_NEGOTIABLES:
            assert rule in p, rule
        assert "INTEGRITY & TECHNICAL RULES (NON-NEGOTIABLE IN EVERY MODE)" in p

    def test_brief_words_steer_the_seeded_fallback(self, service):
        # "warna hijau" in the BRIEF (not the description) must reach the
        # seeded palette extraction, so the no-concept path honours it.
        p = _prompt(service, design_freedom="designer", design_brief="Saya nak tema warna hijau")
        assert "explicitly asked for a GREEN colour theme" in p


class TestDesignerModeWithConcept:
    def test_concept_fonts_and_palette_are_wired_into_the_head(self, service):
        p = _prompt(service, design_freedom="designer", concept=_concept())
        assert "family=Bodoni+Moda" in p and "family=Figtree" in p
        assert "'heading': ['Bodoni Moda'" in p
        assert "'body': ['Figtree'" in p
        assert "'primary': '#B45309'" in p
        assert "--bg-color: #FFFBEB" in p
        # The seeded pairing must not linger anywhere.
        assert "Plus Jakarta Sans" not in p

    def test_concept_block_replaces_seeded_personality(self, service):
        p = _prompt(service, design_freedom="designer", concept=_concept())
        assert 'DESIGN CONCEPT — "Kopitiam Noir"' in p
        assert "DESIGN PERSONALITY —" not in p

    def test_hero_is_designed_from_the_concept(self, service):
        p = _prompt(service, design_freedom="designer", concept=_concept())
        assert "HERO (DESIGN IT YOURSELF — pattern from your concept: POSTER)" in p
        assert "Giant name, one photo, one line." in p
        assert "HERO BLUEPRINT" not in p
        assert "HERO REFERENCE" not in p

    def test_page_plan_replaces_numbered_layout(self, service):
        p = _prompt(service, design_freedom="designer", concept=_concept())
        assert "PAGE PLAN (from your concept" in p
        assert "2. MENU MALAM: single column list" in p
        assert "REQUIRED CONTENT (must exist somewhere on the page" in p
        # House layout is still available as reference material.
        assert "Reference only — the house layout" in p

    def test_concept_is_ignored_in_guided_mode(self, service):
        p = _prompt(service, design_freedom="guided", concept=_concept())
        assert "Kopitiam Noir" not in p
        assert "Bodoni" not in p
        assert "HERO BLUEPRINT (follow the structure" in p

    def test_doodle_pick_keeps_its_fonts_and_directives(self, service):
        p = _prompt(service, design_freedom="designer", concept=_concept(), design_style="doodle")
        assert "DOODLE CARTOON" in p
        assert "Gloria Hallelujah" in p
        assert "Bodoni" not in p  # concept fonts do not override the doodle look
        assert 'DESIGN CONCEPT — "Kopitiam Noir"' in p  # but the concept still informs it

    def test_non_negotiables_survive_with_concept(self, service):
        p = _prompt(service, design_freedom="designer", concept=_concept())
        for rule in NON_NEGOTIABLES:
            assert rule in p, rule


class TestReviewerBriefAdherence:
    def test_reviewer_checks_the_brief(self, service):
        p = service._build_design_review_prompt(True, design_brief="Gelap dan mewah")
        assert "BRIEF ADHERENCE CHECK" in p
        assert "Gelap dan mewah" in p
        assert "HARD RULES" in p

    def test_reviewer_unchanged_without_brief(self, service):
        p = service._build_design_review_prompt(True)
        assert "BRIEF ADHERENCE CHECK" not in p


class TestGlmSystemPrompt:
    @pytest.mark.asyncio
    async def test_designer_mode_wraps_the_same_rules(self, service):
        service.zai_api_key = "k"
        service.zai_base_url = "https://z.test"
        service.zai_model = "glm-test"
        captured = {}

        class _Resp:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "<html></html>"}, "finish_reason": "stop"}]}

        class _Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, headers=None, json=None):
                captured["json"] = json
                return _Resp()

        with patch.object(ai_service_module.httpx, "AsyncClient", _Client):
            await service._call_glm("prompt", designer_mode=True)
        content = captured["json"]["messages"][0]["content"]
        assert content.startswith("ROLE: You are the senior designer")
        assert content.index("GOAL:") < content.index("HARD RULES") < content.index("FREEDOM:")
        assert "PRECEDENCE:" in content and content.index("FREEDOM:") < content.index("PRECEDENCE:")

        with patch.object(ai_service_module.httpx, "AsyncClient", _Client):
            await service._call_glm("prompt", designer_mode=False)
        content = captured["json"]["messages"][0]["content"]
        assert content.startswith("GOAL:")
        assert "PRECEDENCE:" not in content


class TestRequestSchema:
    def test_new_fields_accepted_and_normalised(self):
        from app.models.schemas import WebsiteGenerationRequest

        req = WebsiteGenerationRequest(
            description="kedai makan sedap di kuala lumpur",
            business_name="Kedai Ali",
            subdomain="kedaiali",
            design_brief="  Gelap & mewah  ",
            design_freedom=" Designer ",
        )
        assert req.design_brief == "Gelap & mewah"
        assert req.design_freedom == "designer"

    def test_unknown_freedom_and_blank_brief_become_none(self):
        from app.models.schemas import WebsiteGenerationRequest

        req = WebsiteGenerationRequest(
            description="kedai makan sedap di kuala lumpur",
            business_name="Kedai Ali",
            subdomain="kedaiali",
            design_brief="   ",
            design_freedom="freestyle",
        )
        assert req.design_brief is None
        assert req.design_freedom is None

    def test_brief_over_cap_is_rejected(self):
        from pydantic import ValidationError
        from app.models.schemas import WebsiteGenerationRequest

        with pytest.raises(ValidationError):
            WebsiteGenerationRequest(
                description="kedai makan sedap di kuala lumpur",
                business_name="Kedai Ali",
                subdomain="kedaiali",
                design_brief="x" * 1501,
            )

    def test_regenerate_request_carries_the_fields(self):
        from app.models.schemas import WebsiteRegenerateRequest

        req = WebsiteRegenerateRequest(design_brief="lagi gelap", design_freedom="GUIDED")
        assert req.design_brief == "lagi gelap"
        assert req.design_freedom == "guided"


# ---------------------------------------------------------------------------
# generate_website wiring
# ---------------------------------------------------------------------------

VALID_HTML = (
    "<!DOCTYPE html><html><head><title>t</title></head>"
    "<body><h1>Kopitiam Ah Seng</h1><p>" + ("x" * 200) + "</p></body></html>"
)


def _request(**kw):
    from app.models.schemas import WebsiteGenerationRequest
    params = dict(
        business_name="Kopitiam Ah Seng",
        description="Kopitiam lama di Ipoh, kopi cham dan roti bakar",
        whatsapp_number="0123456789",
        subdomain="kopitiam-ah-seng",
    )
    params.update(kw)
    return WebsiteGenerationRequest(**params)


def _wire(service, html_return=VALID_HTML):
    from app.services.generation_validator import ValidationResult
    service.deepseek_api_key = "k"
    service.deepseek_model = "fast"
    service.deepseek_model_pro = "pro"
    service.zai_api_key = None
    service._last_api_call = {"provider": None, "finish_reason": None, "truncated": False}
    service._last_extract_info = {}
    service._last_sanitizer_trace = []
    service._call_deepseek = AsyncMock(return_value=html_return)
    service._validate_generated_html = MagicMock(return_value=[])
    service._improve_with_qwen = AsyncMock(side_effect=lambda html, desc: html)
    service._fix_placeholders = MagicMock(side_effect=lambda html, *a, **k: html)
    service._fix_menu_item_images = MagicMock(side_effect=lambda html, *a, **k: html)
    service._generate_ai_food_images = AsyncMock(side_effect=lambda html, **k: (html, 0))
    service._fix_broken_image_urls = MagicMock(side_effect=lambda html, *a, **k: html)
    service._sanitize_sensitive_claims = MagicMock(side_effect=lambda html, *a, **k: html)
    service._inject_seo_metadata = MagicMock(side_effect=lambda html, *a, **k: html)
    service._validate_and_repair = AsyncMock(side_effect=lambda html, request, **k: (html, ValidationResult()))
    service._build_strict_prompt = MagicMock(return_value="<prompt>")
    service._autofill_missing_images = AsyncMock(return_value=0)
    service._new_zai_image_phase = MagicMock(return_value={})


class TestGenerateWebsiteWiring:
    @pytest.mark.asyncio
    async def test_designer_mode_runs_concept_and_passes_it_to_the_prompt(self, service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
        monkeypatch.delenv("AI_DESIGN_FREEDOM_DEFAULT", raising=False)
        monkeypatch.delenv("AI_DESIGN_CONCEPT_ENABLED", raising=False)
        _wire(service)
        concept = _concept()
        service._direct_design_concept = AsyncMock(return_value=concept)

        result = await service.generate_website(
            _request(design_brief="Gelap dan mewah"), image_choice="none"
        )

        service._direct_design_concept.assert_awaited_once()
        kwargs = service._build_strict_prompt.call_args.kwargs
        assert kwargs["design_freedom"] == "designer"
        assert kwargs["design_brief"] == "Gelap dan mewah"
        assert kwargs["concept"] is concept
        # The HTML call carried the designer system prompt.
        assert service._call_deepseek.call_args.kwargs["system_prompt"] == DESIGNER_SYSTEM_PROMPT
        assert "design_concept" in result.step_timings
        assert "<h1>Kopitiam Ah Seng</h1>" in result.html_content

    @pytest.mark.asyncio
    async def test_guided_request_skips_the_concept_step(self, service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
        _wire(service)
        service._direct_design_concept = AsyncMock(return_value=_concept())

        await service.generate_website(_request(design_freedom="guided"), image_choice="none")

        service._direct_design_concept.assert_not_awaited()
        kwargs = service._build_strict_prompt.call_args.kwargs
        assert kwargs["design_freedom"] == "guided"
        assert kwargs["concept"] is None
        assert service._call_deepseek.call_args.kwargs["system_prompt"] is None

    @pytest.mark.asyncio
    async def test_concept_flag_off_skips_the_step_but_keeps_designer_prompt(self, service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
        monkeypatch.setenv("AI_DESIGN_CONCEPT_ENABLED", "false")
        _wire(service)
        service._direct_design_concept = AsyncMock(return_value=_concept())

        await service.generate_website(_request(), image_choice="none")

        service._direct_design_concept.assert_not_awaited()
        kwargs = service._build_strict_prompt.call_args.kwargs
        assert kwargs["design_freedom"] == "designer"
        assert kwargs["concept"] is None

    @pytest.mark.asyncio
    async def test_concept_failure_degrades_to_seeded_design(self, service, monkeypatch):
        monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
        monkeypatch.delenv("AI_DESIGN_FREEDOM_DEFAULT", raising=False)
        monkeypatch.delenv("AI_DESIGN_CONCEPT_ENABLED", raising=False)
        _wire(service)
        service._direct_design_concept = AsyncMock(return_value=None)

        result = await service.generate_website(_request(), image_choice="none")

        kwargs = service._build_strict_prompt.call_args.kwargs
        assert kwargs["design_freedom"] == "designer"
        assert kwargs["concept"] is None
        assert "<h1>Kopitiam Ah Seng</h1>" in result.html_content


class TestConceptStep:
    @pytest.mark.asyncio
    async def test_direct_design_concept_parses_the_model_reply(self, service):
        service.deepseek_api_key = "k"
        service.deepseek_model = "fast"
        service.zai_api_key = None
        raw = json.dumps({
            "concept_name": "Ipoh Morning",
            "palette": {"primary": "#0F766E", "background": "#F0FDFA", "text": "#042F2E"},
            "fonts": {"heading": "Lora", "body": "Karla"},
            "sections": [{"id": "hero", "title": "Hero"}, {"id": "menu", "title": "Menu"}],
        })
        service._call_deepseek = AsyncMock(return_value=raw)

        concept = await service._direct_design_concept(
            _request(design_brief="pagi, segar"),
            color_mode="light", has_images=True, image_count=3,
            design_brief="pagi, segar", language="ms",
        )

        assert concept is not None
        assert concept.name == "Ipoh Morning"
        assert concept.fonts["heading"] == "Lora"
        assert concept.palette["primary"] == "#0F766E"
        assert service._last_design_concept["name"] == "Ipoh Morning"
        # The concept call used the fast tier, the creative temperature and
        # a small output cap — never the 24K HTML budget.
        kwargs = service._call_deepseek.call_args.kwargs
        assert kwargs["model"] == "fast"
        assert kwargs["temperature"] == ai_service_module.AI_DESIGN_CONCEPT_TEMPERATURE
        assert kwargs["max_tokens"] == ai_service_module.AI_DESIGN_CONCEPT_MAX_TOKENS
        assert kwargs["system_prompt"] == ai_service_module.CONCEPT_SYSTEM_PROMPT
        # The brief reached the concept prompt.
        assert "pagi, segar" in service._call_deepseek.call_args.args[0]

    @pytest.mark.asyncio
    async def test_direct_design_concept_never_raises(self, service):
        service.deepseek_api_key = "k"
        service.deepseek_model = "fast"
        service.zai_api_key = None
        service._call_deepseek = AsyncMock(side_effect=RuntimeError("boom"))

        concept = await service._direct_design_concept(
            _request(), color_mode="light", has_images=False, image_count=0,
            design_brief=None, language="ms",
        )
        assert concept is None

    @pytest.mark.asyncio
    async def test_direct_design_concept_times_out_cleanly(self, service, monkeypatch):
        import asyncio
        service.deepseek_api_key = "k"
        service.deepseek_model = "fast"
        service.zai_api_key = None
        monkeypatch.setattr(ai_service_module, "AI_DESIGN_CONCEPT_TIMEOUT_SECONDS", 0.01)

        async def _slow(*a, **k):
            await asyncio.sleep(0.2)
            return "{}"

        service._call_deepseek = _slow
        concept = await service._direct_design_concept(
            _request(), color_mode="light", has_images=False, image_count=0,
            design_brief=None, language="ms",
        )
        assert concept is None
