"""M1 recipe-pipeline tests: flag gating, end-to-end assembly (LLM mocked),
output contract, and the auto-fallback seam in AIService."""

import copy

import pytest

from app.models.schemas import AIGenerationResponse
from app.schemas.recipe import DesignBrief
from app.services import recipe_pipeline
from app.services.recipe_pipeline import (
    ALLOWLIST_ENV,
    FLAG_ENV,
    RecipePipelineError,
    _strip_image_refs,
    _uploaded_image_map,
    generate,
    is_enabled_for,
)
from app.utils.output_lint import lint_html

from tests.test_brief_generator import VALID_BRIEF, make_request


def make_brief(**overrides) -> DesignBrief:
    data = copy.deepcopy(VALID_BRIEF)
    data.update(overrides)
    return DesignBrief(**data)


async def fake_intent(description, language="ms", business_name=""):
    from app.services.intent_extractor import keyword_intent
    return keyword_intent(description)


class TestFlagGating:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv(FLAG_ENV, raising=False)
        assert not is_enabled_for(make_request(user_email="yassirar77@gmail.com"))

    def test_flag_on_but_no_allowlist_match(self, monkeypatch):
        monkeypatch.setenv(FLAG_ENV, "true")
        monkeypatch.setenv(ALLOWLIST_ENV, "someone@else.com")
        assert not is_enabled_for(make_request(user_email="yassirar77@gmail.com"))

    def test_flag_on_email_match_case_insensitive(self, monkeypatch):
        monkeypatch.setenv(FLAG_ENV, "true")
        monkeypatch.setenv(ALLOWLIST_ENV, "Yassirar77@Gmail.com , other@x.com")
        assert is_enabled_for(make_request(user_email="yassirar77@gmail.com"))

    def test_flag_on_user_id_match(self, monkeypatch):
        monkeypatch.setenv(FLAG_ENV, "true")
        monkeypatch.setenv(ALLOWLIST_ENV, "user-123")
        assert is_enabled_for(make_request(user_id="USER-123"))

    def test_flag_on_wildcard(self, monkeypatch):
        monkeypatch.setenv(FLAG_ENV, "true")
        monkeypatch.setenv(ALLOWLIST_ENV, "*")
        assert is_enabled_for(make_request())

    def test_flag_on_anonymous_not_allowed_without_wildcard(self, monkeypatch):
        monkeypatch.setenv(FLAG_ENV, "true")
        monkeypatch.setenv(ALLOWLIST_ENV, "yassirar77@gmail.com")
        assert not is_enabled_for(make_request())


class TestGenerateEndToEnd:
    async def test_full_assembly_meets_output_contract(self, monkeypatch):
        async def fake_brief(request, intent, keys=None):
            return make_brief()

        monkeypatch.setattr(recipe_pipeline, "extract_intent", fake_intent)
        monkeypatch.setattr(recipe_pipeline, "generate_brief", fake_brief)

        request = make_request()
        response = await generate(request, image_choice="ai")

        assert isinstance(response, AIGenerationResponse)
        html = response.html_content
        # Output contract (GENERATION_UPGRADE_PLAN.md §1.6)
        report = lint_html(html, language="ms")
        assert report.ok, report.issues
        assert "</body>" in html
        assert "<!-- Unknown component" not in html
        # Response shape consumed by run_generation_task
        assert response.sections == ["hero", "menu", "hours", "contact", "footer"]
        assert response.ai_images_count == 0
        assert response.was_truncated is False
        assert "Mamak Bintang" in response.meta_title
        assert "whatsapp" in response.integrations_included
        assert "brief_generation" in response.step_timings

    async def test_progress_callback_invoked(self, monkeypatch):
        async def fake_brief(request, intent, keys=None):
            return make_brief()

        monkeypatch.setattr(recipe_pipeline, "extract_intent", fake_intent)
        monkeypatch.setattr(recipe_pipeline, "generate_brief", fake_brief)

        seen = []

        async def progress(percent, message):
            seen.append(percent)

        await generate(make_request(), progress_callback=progress)
        assert seen == sorted(seen) and len(seen) >= 3

    async def test_brief_failure_propagates_for_fallback(self, monkeypatch):
        from app.services.brief_generator import BriefGenerationError

        async def failing_brief(request, intent, keys=None):
            raise BriefGenerationError("nope")

        monkeypatch.setattr(recipe_pipeline, "extract_intent", fake_intent)
        monkeypatch.setattr(recipe_pipeline, "generate_brief", failing_brief)
        with pytest.raises(BriefGenerationError):
            await generate(make_request())

    async def test_bad_render_raises_pipeline_error(self, monkeypatch):
        async def fake_brief(request, intent, keys=None):
            return make_brief()

        monkeypatch.setattr(recipe_pipeline, "extract_intent", fake_intent)
        monkeypatch.setattr(recipe_pipeline, "generate_brief", fake_brief)
        monkeypatch.setattr(recipe_pipeline, "render_html", lambda recipe: "<html><body>no end")
        with pytest.raises(RecipePipelineError):
            await generate(make_request())


class TestImageHandling:
    def test_strip_image_refs(self):
        brief = make_brief()
        stripped = _strip_image_refs(brief)
        assert stripped.image_map == {}
        assert stripped.cuisine_type is None
        for section in stripped.sections:
            assert "image_key" not in section.content
            assert "image_keys" not in section.content

    def test_uploaded_image_map_hero_only_if_named(self):
        request = make_request(uploaded_images=[
            {"url": "https://cdn.example/hero.jpg", "name": "Hero Image"},
            {"url": "https://cdn.example/a.jpg", "name": "Nasi Lemak"},
        ])
        mapped = _uploaded_image_map(request)
        assert mapped["hero"] == "https://cdn.example/hero.jpg"
        assert mapped["gallery_1"] == "https://cdn.example/a.jpg"

        request2 = make_request(uploaded_images=[
            {"url": "https://cdn.example/a.jpg", "name": "Nasi Lemak"},
        ])
        mapped2 = _uploaded_image_map(request2)
        assert "hero" not in mapped2
        assert mapped2["gallery_1"] == "https://cdn.example/a.jpg"

    async def test_image_choice_none_produces_imageless_hero(self, monkeypatch):
        async def fake_brief(request, intent, keys=None):
            return make_brief()

        monkeypatch.setattr(recipe_pipeline, "extract_intent", fake_intent)
        monkeypatch.setattr(recipe_pipeline, "generate_brief", fake_brief)
        response = await generate(make_request(), image_choice="none")
        # hero image_key stripped + cuisine auto-fill disabled → the hero
        # section renders its imageless layout (menu pool images are handled
        # downstream by run_generation_task's image safety guard).
        html = response.html_content
        hero_start = html.index('id="hero"')
        hero_end = html.index('id="menu"')
        assert "<img" not in html[hero_start:hero_end]
        report = lint_html(html, language="ms")
        assert report.ok, report.issues


class TestAIServiceFallbackSeam:
    async def test_disabled_returns_none_without_calling_generate(self, monkeypatch):
        from app.services.ai_service import AIService

        monkeypatch.delenv(FLAG_ENV, raising=False)
        called = []

        async def spy(*a, **k):
            called.append(1)

        monkeypatch.setattr(recipe_pipeline, "generate", spy)
        service = AIService()
        result = await service._try_recipe_pipeline(make_request(), "none", None, None)
        assert result is None
        assert not called

    async def test_pipeline_exception_returns_none(self, monkeypatch):
        from app.services.ai_service import AIService

        monkeypatch.setenv(FLAG_ENV, "true")
        monkeypatch.setenv(ALLOWLIST_ENV, "*")

        async def boom(*a, **k):
            raise RuntimeError("pipeline exploded")

        monkeypatch.setattr(recipe_pipeline, "generate", boom)
        service = AIService()
        result = await service._try_recipe_pipeline(make_request(), "none", None, None)
        assert result is None  # legacy pipeline proceeds

    async def test_pipeline_success_returned(self, monkeypatch):
        from app.services.ai_service import AIService

        monkeypatch.setenv(FLAG_ENV, "true")
        monkeypatch.setenv(ALLOWLIST_ENV, "yassirar77@gmail.com")

        sentinel = AIGenerationResponse(
            html_content="<!DOCTYPE html><html><body></body></html>",
            meta_title="t", meta_description="d",
            sections=[], integrations_included=[],
        )

        async def ok(*a, **k):
            return sentinel

        monkeypatch.setattr(recipe_pipeline, "generate", ok)
        service = AIService()
        result = await service._try_recipe_pipeline(
            make_request(user_email="yassirar77@gmail.com"), "none", None, None
        )
        assert result is sentinel
