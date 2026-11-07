"""Set-meal photos show ONE single portion matching the set's contents.

agp's Signature set was photographed as a whole roast chicken with boiled
eggs, the other sets as piles of chicken pieces."""


import pytest

import app.services.ai_service as ai_service_module
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services.ai_service import AIService
from app.services.image_subjects import set_meal_prompt

BRIEF = ("Ayam Gepuk Panglima ialah restoran ayam gepuk di Kota Bayu Emas, Klang. Resepi Panglima — ayam goreng rangup "
         "digepuk atas sambal pedas buatan sendiri, dihidang dengan nasi putih panas, tauhu, tempe, kubis dan timun.")
HERO = "Ayam gepuk ... atas pinggan rotan berlapik daun pisang, latar kuning terang"


class TestPrompt:
    def test_signature_set_is_one_portion_with_its_sides(self):
        p = set_meal_prompt("Set Panglima Signature – Ayam Gepuk Telur Mata", "", BRIEF, HERO)
        assert p.startswith("one piece of smashed crispy fried chicken with a sunny-side-up fried egg, with white rice, "
                            "fried tofu, tempeh, cabbage, cucumber slices and red sambal, on a rattan plate lined with banana leaf, "
                            "single portion for one person, top-down")
        assert "not a whole roast chicken" in p and "not a pile or platter" in p and "no text" in p
        assert "Panglima" not in p and "Set" not in p

    def test_item_description_wins_and_seafood_is_a_portion(self):
        p = set_meal_prompt("Set Sotong Krispy", "Sotong krispy dengan nasi putih dan sambal", "")
        assert p.startswith("one portion of crispy fried squid, with white rice and red sambal, on a plate,")

    def test_rice_is_always_part_of_a_set(self):
        assert ", with white rice" in set_meal_prompt("Set Ayam Bakar", "", "")


@pytest.mark.asyncio
async def test_autofill_sends_set_prompts_verbatim(monkeypatch):
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "false")
    monkeypatch.setenv("FREE_AI_IMAGES_PER_SITE", "8")
    monkeypatch.setattr(ai_service_module, "FREE_AI_IMAGES_PER_SITE", 8, raising=False)
    svc = AIService()
    svc.qwen_api_key = svc.zai_api_key = None
    svc.stability_api_key = "st"
    sent = []

    async def _gen(prompt, **kw):
        sent.append((prompt, kw.get("food")))
        return f"https://res.cloudinary.com/demo/image/upload/v1/{len(sent)}.jpg"

    svc._generate_image = _gen
    req = WebsiteGenerationRequest(
        description=BRIEF, language=Language.MALAY, business_name="AGP", business_type="food", subdomain="agp",
        whatsapp_number="0126973105", hero_image_prompt=HERO,
        menu_items=[MenuItemInput(name="Set Panglima Signature – Ayam Gepuk Telur Mata", price="15.90", category="Set Ayam"),
                    MenuItemInput(name="Mee Goreng", price="7", category="Mee")],
    )
    await svc._autofill_missing_images(req, {})
    set_calls = [(p, f) for p, f in sent if p.startswith("one piece of smashed crispy fried chicken")]
    assert len(set_calls) == 1 and set_calls[0][1] is False  # verbatim, not via the dish-name mapping
    # A non-set item keeps the dish-name path.
    assert ("Mee Goreng", True) in sent
