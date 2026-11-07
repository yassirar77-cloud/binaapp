"""First/"Set" category menu photos get a third, dish-only attempt before
they are dropped. Set Panglima Krispy lost its photo to two images with
'Ayam Krispy Krisps' lettered into them."""

import json

import pytest

import app.services.ai_service as ai_service_module
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services.ai_service import AIService
from app.services.image_subjects import plain_dish_prompt

TEXT = json.dumps({"has_text": True, "has_food": True, "has_face": False, "matches_category": True, "reason": "lettering"})
CLEAN = json.dumps({"has_text": False, "has_food": True, "has_face": False, "matches_category": True, "reason": "ok"})


class TestPlainDishPrompt:
    def test_no_menu_name_plain_english_and_no_text(self):
        p = plain_dish_prompt("Set Panglima Krispy – Ayam Krispy", set_meal=True)
        assert p.startswith("crispy fried chicken, served as a set meal with white rice and side dishes, top-down food photo")
        assert "Panglima" not in p and "Set" not in p and "no text" in p and "no letters" in p

    def test_sides_join_naturally(self):
        p = plain_dish_prompt("Set B – Ayam Gepuk Tauhu Tempe", set_meal=True)
        assert p.startswith("smashed crispy fried chicken with fried tofu and tempeh, served as a set meal")


def _svc(monkeypatch, verdicts):
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "true")
    monkeypatch.setenv("FREE_AI_IMAGES_PER_SITE", "8")
    monkeypatch.setattr(ai_service_module, "FREE_AI_IMAGES_PER_SITE", 8, raising=False)
    svc = AIService()
    svc.qwen_api_key, svc.zai_api_key, svc.stability_api_key = "q", None, "st"
    prompts = []

    async def _gen(prompt, **kw):
        prompts.append((prompt, kw.get("food")))
        return f"https://res.cloudinary.com/demo/image/upload/v1/{len(prompts)}.jpg"

    async def _check(messages):
        return verdicts.pop(0) if verdicts else CLEAN

    svc._generate_image = _gen
    svc._call_image_check_model = _check
    svc._last_image_rejections = []
    return svc, prompts


def _req(items):
    return WebsiteGenerationRequest(
        description="Restoran ayam gepuk di Klang", language=Language.MALAY, business_name="AGP",
        business_type="food", subdomain="agp", whatsapp_number="0126973105",
        menu_items=[MenuItemInput(name=n, price=p, category=c) for n, p, c in items],
    )


@pytest.mark.asyncio
async def test_set_item_passes_on_the_dish_only_third_attempt(monkeypatch):
    svc, prompts = _svc(monkeypatch, [CLEAN, TEXT, TEXT, CLEAN])  # hero ok; set item: text, text, clean
    urls = {}
    await svc._autofill_missing_images(_req([("Set Panglima Krispy – Ayam Krispy", "14.90", "Set Ayam")]), urls)
    assert urls.get("gallery1_name") == "Set Panglima Krispy – Ayam Krispy"
    last_prompt, food = prompts[-1]
    # Set items: the third attempt is the single-portion set prompt, plainer.
    assert last_prompt.startswith("one piece of crispy fried chicken, with white rice") and food is False
    assert last_prompt.endswith("simple composition, plain light background")
    assert any(r.get("outcome") == "passed_on_attempt_3" for r in svc._last_image_rejections)


@pytest.mark.asyncio
async def test_set_item_dropped_after_three_text_rejections(monkeypatch):
    svc, prompts = _svc(monkeypatch, [CLEAN, TEXT, TEXT, TEXT])
    urls = {}
    await svc._autofill_missing_images(_req([("Set Sotong Krispy", "20.90", "Set Seafood Krispy")]), urls)
    assert "gallery1" not in urls and len(prompts) == 4  # hero + 3 attempts


@pytest.mark.asyncio
async def test_items_outside_the_set_tier_keep_two_attempts(monkeypatch):
    # First category is "Set Ayam"; "Teh O Ice" (drinks) never gets a slot,
    # so use a non-set second category food item ranked after the sets.
    svc, prompts = _svc(monkeypatch, [CLEAN, CLEAN, TEXT, TEXT])
    urls = {}
    await svc._autofill_missing_images(_req([
        ("Set A – Ayam Gepuk", "12.50", "Set Ayam"),
        ("Mee Goreng Mamak", "8.00", "Mee"),
    ]), urls)
    assert urls.get("gallery1_name") == "Set A – Ayam Gepuk"
    assert "gallery2" not in urls  # Mee Goreng: 2 attempts, then dropped
    assert len(prompts) == 4  # hero, Set A, Mee x2 — no third attempt
