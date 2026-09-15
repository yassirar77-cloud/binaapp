"""
Round 2 §A regression with the Dobi Layan Diri Seksyen 18 brief: service
images must be laundry subjects (no chef, no handshake), every prompt
carries the universal negative, and the vision check rejects text, food and
faces — regenerating once, then falling back to a typographic tile.
"""

import json
from unittest.mock import AsyncMock

import pytest

import app.services.ai_service as ai_service_module
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services import image_subjects
from app.services.ai_service import AIService

DOBI_DESC = (
    "Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. "
    "Mesin basuh 10kg dan 20kg, pengering panas, bayar dengan syiling atau QR. Buka setiap hari."
)


def _dobi(**kw) -> WebsiteGenerationRequest:
    base = dict(
        description=DOBI_DESC, language=Language.MALAY, business_name="Dobi Layan Diri Seksyen 18",
        business_type="services", subdomain="bebe", whatsapp_number="0198765432", include_maps=True,
        location_address="L7/1, Jalan 18/2, Seksyen 18, Shah Alam", color_mode="light", design_freedom="designer",
        menu_items=[MenuItemInput(name="Basuh 10kg", price="6"), MenuItemInput(name="Basuh 20kg", price="12"),
                    MenuItemInput(name="Pengering", price="4"), MenuItemInput(name="Cuci selimut", price="15")],
    )
    base.update(kw)
    return WebsiteGenerationRequest(**base)


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "true")
    monkeypatch.setattr(ai_service_module, "FREE_AI_IMAGES_PER_SITE", 6, raising=False)
    svc = AIService()
    svc.qwen_api_key = "qwen-key"
    svc.zai_api_key = None
    svc.stability_api_key = "st-key"
    return svc


def _verdict(**kw):
    base = {"has_text": False, "has_food": False, "has_face": False, "matches_category": True, "reason": "ok"}
    base.update(kw)
    return json.dumps(base)


@pytest.mark.asyncio
async def test_dobi_prompts_are_laundry_locked_and_negative(service):
    prompts = []

    async def _gen(prompt, **kw):
        prompts.append(prompt)
        return f"https://res.cloudinary.com/demo/image/upload/v1/{len(prompts)}.jpg"

    service._generate_image = _gen
    service._call_image_check_model = AsyncMock(return_value=_verdict())
    image_urls = {}
    n = await service._autofill_missing_images(_dobi(), image_urls, max_ai_images=6)
    assert n == 5 and image_urls["hero"] and image_urls["gallery1_name"] == "Basuh 10kg"
    assert prompts[0].startswith("self-service laundromat interior")
    assert all(p.endswith(image_subjects.NEGATIVE_PROMPT) for p in prompts)
    for p in prompts:
        assert not image_subjects.has_fnb_wording(p), p
        assert "professional at work with a client" not in p
    assert "Basuh 10kg in a self-service laundromat" in prompts[1]
    # Every generated image was checked against the laundry label.
    assert service._call_image_check_model.await_count == 5
    sent = service._call_image_check_model.call_args.args[0]
    assert "laundromat" in sent[1]["content"][1]["text"]


@pytest.mark.asyncio
async def test_vision_check_rejects_then_retries_then_drops(service):
    calls = []

    async def _gen(prompt, **kw):
        calls.append(prompt)
        return f"https://res.cloudinary.com/demo/image/upload/v1/img{len(calls)}.jpg"

    service._generate_image = _gen
    # hero: text baked in → retry passes; gallery1: face → retry still a face → dropped;
    # gallery2: food on a laundry site → retry passes; gallery3/4 pass.
    verdicts = [
        _verdict(has_text=True, reason="'10 kg' printed on the machine"), _verdict(),
        _verdict(has_face=True, reason="two people shaking hands"), _verdict(has_face=True, reason="a smiling person"),
        _verdict(has_food=True, reason="a chef plating food"), _verdict(),
        _verdict(), _verdict(),
    ]
    service._call_image_check_model = AsyncMock(side_effect=verdicts)
    image_urls = {}
    n = await service._autofill_missing_images(_dobi(), image_urls, max_ai_images=6)
    assert image_urls["hero"] == "https://res.cloudinary.com/demo/image/upload/v1/img6.jpg"  # stricter retry
    assert "gallery1" not in image_urls  # dropped → typographic tile
    assert image_urls["gallery2"].endswith("img8.jpg")
    assert n == 4
    stricter = [p for p in calls if "no people at all" in p]
    assert len(stricter) == 3
    rejections = service._last_image_rejections
    assert [(r["slot"], r["outcome"]) for r in rejections] == [
        ("hero", "retried"), ("gallery1", "retried"), ("gallery1", "dropped"), ("gallery2", "retried"),
    ]
    assert rejections[0]["reasons"] == ["rendered text in the image"] and "10 kg" in rejections[0]["reason"]
    assert rejections[1]["reasons"] == ["a person's face in the image"]
    assert rejections[3]["reasons"] == ["food in a non-F&B image"]


@pytest.mark.asyncio
async def test_provider_failure_on_non_fnb_never_falls_back_to_stock(service):
    service._generate_image = AsyncMock(return_value=None)
    service._call_image_check_model = AsyncMock(return_value=_verdict())
    image_urls = {}
    n = await service._autofill_missing_images(_dobi(), image_urls, max_ai_images=6)
    assert n == 0 and image_urls == {}  # no Unsplash pool image on a laundry site


@pytest.mark.asyncio
async def test_check_skipped_without_vision_key(service, monkeypatch):
    service.qwen_api_key = None
    service._generate_image = AsyncMock(return_value="https://res.cloudinary.com/demo/image/upload/v1/a.jpg")
    service._call_image_check_model = AsyncMock()
    image_urls = {}
    await service._autofill_missing_images(_dobi(), image_urls, max_ai_images=1)
    service._call_image_check_model.assert_not_awaited()
    assert image_urls["hero"]


def test_food_sites_keep_the_curated_dish_path(service):
    req = _dobi(business_type="food", business_name="Nasi Kandar Crystal", description="Nasi kandar mamak 24 jam")
    prompt = service._autofill_item_prompt("food", "Ayam Goreng", "restaurant", "ctx", subject=None)
    assert prompt == "Ayam Goreng"
    assert image_subjects.subject_for("food", req.description) is None
