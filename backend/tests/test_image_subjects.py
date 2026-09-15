"""Category-locked image prompts and the vision check (Round 2, §A), with
the Dobi Layan Diri brief as the fixture."""

import json
from unittest.mock import AsyncMock

import pytest

from app.services import image_subjects as isub
from app.services import image_vision_check as ivc

DOBI = "Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. Mesin basuh 10kg dan 20kg, pengering panas."


def test_subject_for_dobi_is_laundry_and_prompts_are_locked():
    subject = isub.subject_for("services", "Dobi Layan Diri Seksyen 18", DOBI)
    assert subject.key == "laundry"
    hero = isub.lock_prompt("hero", subject, context="Dobi Layan Diri Seksyen 18: dobi layan diri 24 jam")
    assert hero.startswith("self-service laundromat interior, front-load washing machines" if False else "self-service laundromat interior")
    assert "front-load washing machines" in hero and hero.endswith(isub.NEGATIVE_PROMPT)
    item = isub.lock_prompt("item", subject, item="Basuh 10kg", context=DOBI)
    assert item.startswith("Basuh 10kg in a self-service laundromat")
    assert not isub.has_fnb_wording(hero) and not isub.has_fnb_wording(item)
    # Idempotent negative.
    assert isub.with_negative(hero) == hero


def test_subjects_by_vertical_and_words():
    assert isub.subject_for("salon", "Salon rambut wanita").key == "salon"
    assert isub.subject_for("salon", "Barbershop lelaki, fade").key == "barber"
    assert isub.subject_for("services", "Bengkel aircond dan paip").key == "workshop"
    assert isub.subject_for("clothing", "Butik baju kurung").key == "clothing"
    assert isub.subject_for("general", "Kedai gadget dan telefon").key == "retail"
    assert isub.subject_for("services", "Perkhidmatan am").key == "services_generic"
    assert isub.subject_for("food", "Nasi kandar") is None
    assert isub.subject_for("bakery", "Kek") is None


def test_fnb_wording_is_scrubbed_from_non_fnb_prompts():
    dirty = "Skilled chef plating a dish, restaurant kitchen, appetizing food photography, for the business: Dobi Layan Diri"
    clean = isub.scrub_fnb_wording(dirty)
    assert not isub.has_fnb_wording(clean)
    assert "Dobi Layan Diri" in clean
    subject = isub.subject_for("services", DOBI)
    locked = isub.lock_prompt("item", subject, item="Cuci selimut", context="restaurant-grade chef service dobi")
    assert "chef" not in locked and "restaurant" not in locked and "Cuci selimut" in locked


def test_stricter_prompt_is_stricter_and_keeps_negative():
    p = isub.lock_prompt("hero", isub.subject_for("services", DOBI))
    s = isub.stricter_prompt(p)
    assert "no people at all" in s and "absolutely no text" in s and s.endswith(isub.NEGATIVE_PROMPT)
    assert s.count("no people's faces") == 1


def test_negative_terms_cover_the_brief():
    for word in ("text", "letters", "logo", "watermark", "faces"):
        assert word in isub.NEGATIVE_TERMS
    assert isub.NEGATIVE_PROMPT.startswith("no text, no letters") and isub.NEGATIVE_PROMPT.endswith("no people's faces")


# ---- vision check -------------------------------------------------------------

def test_verdict_parsing_and_failures():
    raw = json.dumps({"has_text": True, "has_food": False, "has_face": False, "matches_category": True, "reason": "the sign says 10 kg"})
    v = ivc.parse_verdict(raw)
    assert v.failures(food_allowed=False) == ["rendered text in the image"]
    v = ivc.parse_verdict('```json\n{"has_text": "no", "has_food": "yes", "has_face": "no", "matches_category": "no"}\n```')
    assert v.failures(food_allowed=False) == ["food in a non-F&B image", "does not match the category"]
    assert v.passes(food_allowed=True) is False  # category mismatch still fails
    ok = ivc.parse_verdict('{"has_text": false, "has_food": true, "has_face": false, "matches_category": true}')
    assert ok.passes(food_allowed=True) and not ok.passes(food_allowed=False)
    assert ivc.parse_verdict("garbage") is None and ivc.parse_verdict('{"x": 1}') is None


def test_messages_carry_image_and_category():
    msgs = ivc.build_messages("https://img/x.jpg", "a self-service laundromat")
    parts = msgs[1]["content"]
    assert parts[0]["image_url"]["url"] == "https://img/x.jpg" and "laundromat" in parts[1]["text"]


@pytest.mark.asyncio
async def test_check_image_passes_when_model_unavailable():
    v = await ivc.check_image("https://img/x.jpg", "laundry", call_model=AsyncMock(return_value=None))
    assert v.checked is False and v.passes(food_allowed=False)
    v = await ivc.check_image("https://img/x.jpg", "laundry", call_model=AsyncMock(side_effect=RuntimeError("down")))
    assert v.checked is False
    face = await ivc.check_image("https://img/x.jpg", "laundry", call_model=AsyncMock(return_value='{"has_text": false, "has_food": false, "has_face": true, "matches_category": true}'))
    assert face.failures(food_allowed=False) == ["a person's face in the image"]
