"""
Two-pass generation wiring in ai_service (Pass 1 plan → Pass 2 binding spec).

Covers:
- the create form → PlanBrief mapping (merchant picks are hard constraints)
- the plan step always yields a plan: model JSON when usable, library
  fallback on timeout / garbage / no key
- the Pass 2 prompt carries the plan as a binding spec, the anti-template
  rules, the section standards, the string table, the typography contract,
  and NO AOS / fade-up instructions
- feature toggles OFF are stated as absences in the prompt
- the resolved theme (brief beats toggle) drives color_mode downstream

All model calls are mocked — no live API usage.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

import app.services.ai_service as ai_service_module
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services.ai_service import AIService
from app.services.design_plan import fallback_plan


def _request(**kw) -> WebsiteGenerationRequest:
    base = dict(
        description="Nasi kandar mamak buka 24 jam di Shah Alam. Ayam goreng berempah dan kari kepala ikan yang pekat.",
        language=Language.MALAY,
        business_name="Nasi Kandar Crystal",
        business_type="food",
        subdomain="crystal",
        include_whatsapp=True,
        whatsapp_number="0198765432",
        include_maps=False,
        location_address="12, Jalan Tengku Ampuan, Shah Alam",
        color_mode="light",
        design_freedom="designer",
        menu_items=[MenuItemInput(name="Ayam Goreng Berempah", price="RM8"), MenuItemInput(name="Kari Kepala Ikan", price="RM25")],
        include_contact_form=False,
        payment_methods=["cod"],
    )
    base.update(kw)
    return WebsiteGenerationRequest(**base)


@pytest.fixture
def service():
    svc = AIService()
    svc.deepseek_api_key = "test-key"
    return svc


# ---- brief mapping ----------------------------------------------------------

def test_plan_brief_maps_the_create_form(service):
    req = _request(design_style="bold", design_brief="Saya nak warna oren terang", include_social=True,
                   social_media={"instagram": "@crystal"}, hero_video=True, opening_hours="10am-2am")
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=2, design_brief=req.design_brief, language="ms")
    assert brief.vertical == "food" and brief.vertical_source == "merchant"
    assert brief.theme == "bright" and brief.style == "bold" and brief.freedom == "designer"
    assert brief.whatsapp is True and brief.maps is False and brief.contact_form is False and brief.social is True
    assert brief.payment_methods == ["cod"] and brief.hero_video is True and brief.hours == "10am-2am"
    assert brief.menu_item_count == 2 and brief.address.startswith("12, Jalan")


def test_plan_brief_auto_vertical_and_no_whatsapp(service):
    req = _request(business_type=None, whatsapp_number=None, business_name="Salon Ayu",
                   description="Salon rambut dan spa untuk wanita di Bangi, rawatan muka dan kuku.")
    brief = service._plan_brief_for(req, color_mode="light", has_images=False, image_count=0, design_brief=None, language="ms")
    assert brief.vertical == "salon" and brief.vertical_source == "auto"
    assert brief.whatsapp is False


def test_brief_beats_theme_toggle(service):
    req = _request(color_mode="light", design_brief="Tema gelap dan mewah, aksen emas")
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=1, design_brief=req.design_brief, language="ms")
    assert brief.theme == "dark" and brief.theme_source == "brief" and "brief wins" in brief.theme_note


# ---- plan step --------------------------------------------------------------

@pytest.mark.asyncio
async def test_plan_step_uses_model_json_when_usable(service):
    req = _request()
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=2, design_brief=None, language="ms")
    reply = json.dumps({
        "direction": "halal_street", "why": "Fast counter food for a young crowd.",
        "palette": {"bg": "#FFFFFF", "surface": "#FFF8E1", "text": "#121212", "muted": "#4A4A4A", "accent": "#FF3D00", "accent_2": "#FFC400"},
        "type": {"display": "Archivo Black", "body": "Rubik", "scale": "1.414 augmented fourth", "display_weight": 400},
        "hero_treatment": "menu-first", "signature_element": "rotated price stickers", "layout_notes": "tight grid",
        "motion": "stickers pop once", "avoid": [],
    })
    with patch.object(service, "_call_plan_model", new=AsyncMock(return_value=reply)):
        plans = await service._direct_design_plan(brief, history=[])
    assert plans[0].direction == "halal_street" and plans[0].source == "ai"
    assert service._last_design_plan["direction"] == "halal_street"


@pytest.mark.asyncio
async def test_plan_step_falls_back_to_library_on_garbage_and_timeout(service):
    req = _request()
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=2, design_brief=None, language="ms")
    with patch.object(service, "_call_plan_model", new=AsyncMock(return_value="not json at all")):
        plans = await service._direct_design_plan(brief, history=[])
    assert plans[0].source == "fallback" and plans[0].direction == "warung_cerah"

    async def _slow(_prompt):
        import asyncio
        await asyncio.sleep(5)
        return "{}"

    with patch.object(ai_service_module, "AI_DESIGN_PLAN_TIMEOUT_SECONDS", 0.01), \
         patch.object(service, "_call_plan_model", new=_slow):
        plans = await service._direct_design_plan(brief, history=[])
    assert plans[0].source == "fallback"


@pytest.mark.asyncio
async def test_plan_step_rotates_away_from_history(service):
    req = _request()
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=2, design_brief=None, language="ms")
    with patch.object(service, "_call_plan_model", new=AsyncMock(return_value=None)):
        plans = await service._direct_design_plan(brief, history=["warung_cerah"])
    assert plans[0].direction != "warung_cerah"


@pytest.mark.asyncio
async def test_multi_plan_returns_three_distinct(service):
    req = _request()
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=2, design_brief=None, language="ms")
    with patch.object(service, "_call_plan_model", new=AsyncMock(return_value=None)):
        plans = await service._direct_design_plan(brief, n_plans=3, history=[])
    assert len(plans) == 3 and len({p.direction for p in plans}) == 3


# ---- Pass 2 prompt ----------------------------------------------------------

def _prompt_with_plan(service, req, **extra):
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=2, design_brief=req.design_brief, language="ms")
    plan = fallback_plan(brief)
    return plan, service._build_strict_prompt(
        req.business_name, req.description, "modern", [], "ms",
        whatsapp_number=req.whatsapp_number, location_address=req.location_address,
        image_choice="upload", images={"hero": "https://img/hero.jpg", "gallery1": "https://img/1.jpg"},
        include_ecommerce=False, color_mode="light", include_whatsapp=True, include_maps=req.include_maps,
        include_contact_form=req.include_contact_form, menu_items=req.menu_items, show_prices=True,
        design_style=req.design_style, design_brief=req.design_brief, design_freedom="designer",
        concept=plan.to_concept("ms"), plan=plan, payment_methods=req.payment_methods, **extra,
    )


def test_pass2_prompt_carries_binding_spec_and_no_aos(service):
    req = _request()
    plan, prompt = _prompt_with_plan(service, req)
    assert "DESIGN PLAN" in prompt and "BINDING SPEC" in prompt
    assert plan.direction_name in prompt and plan.palette["accent"] in prompt
    assert "ANTI-TEMPLATE RULES" in prompt and "SECTION STANDARDS" in prompt and "UI STRING TABLE" in prompt
    assert "TYPOGRAPHY (from the plan" in prompt and plan.type["display"] in prompt
    assert "QUALITY FLOOR" in prompt and "prefers-reduced-motion" in prompt
    assert "aos@2.3.4" not in prompt and 'data-aos="fade-up"' not in prompt and "AOS.init" not in prompt
    assert "SCROLL ANIMATIONS (MUST include AOS library)" not in prompt
    assert 'style="font-size: clamp' not in prompt
    assert "TWO-PASS" in prompt


def test_pass2_prompt_states_feature_absences(service):
    req = _request(include_maps=False, include_contact_form=False)
    _, prompt = _prompt_with_plan(service, req)
    assert "Google Maps OFF" in prompt and "NO map card" in prompt
    assert "Borang Tempahan OFF" in prompt and "NO contact form" in prompt
    assert "Social Media OFF" in prompt
    assert "Bayar semasa terima (COD)" in prompt
    assert "Hours were NOT supplied" in prompt


def test_pass2_prompt_maps_on_uses_widget_slot(service):
    req = _request(include_maps=True)
    _, prompt = _prompt_with_plan(service, req)
    assert "binaapp-maps-slot" in prompt and "do NOT embed your own iframe" in prompt


def test_pass2_prompt_no_whatsapp_means_no_buttons(service):
    req = _request(whatsapp_number=None)
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=1, design_brief=None, language="ms")
    plan = fallback_plan(brief)
    prompt = service._build_strict_prompt(
        req.business_name, req.description, "modern", [], "ms", whatsapp_number=None,
        location_address=req.location_address, image_choice="upload", images={"hero": "https://img/hero.jpg"},
        color_mode="light", include_whatsapp=True, include_maps=False, include_contact_form=False,
        menu_items=req.menu_items, design_freedom="designer", concept=plan.to_concept("ms"), plan=plan,
    )
    assert "tiles carry no order button" in prompt
    assert "DO NOT output any wa.me link" in prompt


def test_pass2_prompt_english_string_table(service):
    req = _request(language=Language.ENGLISH)
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=1, design_brief=None, language="en")
    plan = fallback_plan(brief)
    prompt = service._build_strict_prompt(
        req.business_name, req.description, "modern", [], "en", whatsapp_number=req.whatsapp_number,
        location_address=req.location_address, image_choice="upload", images={"hero": "https://img/hero.jpg"},
        color_mode="light", include_whatsapp=True, include_maps=False, include_contact_form=False,
        menu_items=req.menu_items, design_freedom="designer", concept=plan.to_concept("en"), plan=plan,
    )
    assert 'html lang="en"' in prompt and "Order on WhatsApp" in prompt and "Pesan di WhatsApp" not in prompt


def test_non_fnb_prompt_has_no_menu_section(service):
    req = _request(business_type="salon", description="Salon rambut dan spa wanita di Bangi dengan rawatan muka.",
                   menu_items=[MenuItemInput(name="Gunting rambut", price="RM35")])
    plan, prompt = _prompt_with_plan(service, req)
    assert "menu" not in plan.sections
    assert "SERVIS & HARGA" in prompt and "No Menu section" in prompt


def test_hero_video_forces_full_bleed_marker(service):
    req = _request(hero_video=True)
    brief = service._plan_brief_for(req, color_mode="light", has_images=True, image_count=1, design_brief=None, language="ms")
    plan = fallback_plan(brief)
    assert plan.hero_treatment == "photo-full-bleed"
    prompt = service._build_strict_prompt(
        req.business_name, req.description, "modern", [], "ms", whatsapp_number=req.whatsapp_number,
        location_address=req.location_address, image_choice="upload", images={"hero": "https://img/hero.jpg"},
        color_mode="light", include_whatsapp=True, include_maps=False, include_contact_form=False,
        menu_items=req.menu_items, design_freedom="designer", concept=plan.to_concept("ms"), plan=plan, hero_video=True,
    )
    assert "data-binaapp-hero-video" in prompt


@pytest.mark.asyncio
async def test_glm_system_prompt_gets_plan_clause(service):
    from unittest.mock import MagicMock
    captured = {}

    async def _fake_post(*args, **kwargs):
        captured["body"] = kwargs.get("json")
        resp = MagicMock()
        resp.status_code = 500
        resp.text = "x"
        return resp

    client = MagicMock()
    client.post = _fake_post
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    service.zai_api_key = "k"
    with patch.object(ai_service_module.httpx, "AsyncClient", return_value=ctx):
        await service._call_glm("p", has_images=True, designer_mode=True, plan_mode=True)
    system = captured["body"]["messages"][0]["content"]
    assert "DESIGN PLAN" in system and "do not decorate headlines" in system


# ---- imagery wiring (§6) --------------------------------------------------------

def test_hero_cue_comes_from_the_plan(service):
    req = _request(hero_image_prompt=None)
    cue = service._hero_cue_for(req, "light", "ms")
    assert cue and "Ayam Goreng Berempah" in cue and "daylight" in cue
    prompt = service._autofill_hero_prompt("food", "restaurant", "Nasi Kandar Crystal", direction_cue=cue)
    assert prompt.startswith("featuring Ayam Goreng Berempah")
    # The merchant's own hero words still beat the plan cue.
    prompt = service._autofill_hero_prompt("food", "restaurant", "x", merchant_prompt="Kari kepala ikan berasap", direction_cue=cue)
    assert prompt.startswith("Kari kepala ikan berasap")


@pytest.mark.asyncio
async def test_generate_applies_section_crops_and_uses_the_plan(service, monkeypatch):
    """End-to-end through generate_website with every provider mocked: the
    plan step runs, Cloudinary URLs get section crops, and the prompt
    carries the plan."""
    monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
    monkeypatch.setenv("DESIGN_CRITIQUE_ENABLED", "false")
    hero = "https://res.cloudinary.com/demo/image/upload/v1/hero.jpg"
    item = "https://res.cloudinary.com/demo/image/upload/v1/ayam.jpg"
    req = _request(uploaded_images=[{"url": hero, "name": "Hero Image"}, {"url": item, "name": "Ayam Goreng Berempah", "price": "RM8"}])
    html = f'<!DOCTYPE html><html lang="ms"><head><title>x</title></head><body><section id="home"><h1>Nasi Kandar Crystal</h1><img src="{hero.replace("/upload/", "/upload/c_fill,ar_16:9,g_auto,w_1600,q_auto,f_auto/")}" alt="Hero"></section><section id="menu"><h2>Menu</h2><img src="{item.replace("/upload/", "/upload/c_fill,ar_4:3,g_auto,w_900,q_auto,f_auto/")}" alt="Ayam Goreng Berempah"><h3>Ayam Goreng Berempah</h3><span>RM8</span></section><footer>&copy; <span id="binaapp-year"></span> Nasi Kandar Crystal</footer></body></html>'
    service._call_plan_model = AsyncMock(return_value=None)
    service._call_deepseek = AsyncMock(return_value=html)
    service._call_qwen = AsyncMock(return_value=None)
    service._improve_with_qwen = AsyncMock(side_effect=lambda h, d: h)
    service._generate_ai_food_images = AsyncMock(side_effect=lambda h, **k: (h, 0))
    service._autofill_missing_images = AsyncMock(return_value=0)
    with patch("app.services.image_intelligence.hero_quality", new=AsyncMock(side_effect=Exception("offline"))):
        result = await service.generate_website(req, image_choice="upload")
    assert service._last_design_plan is not None
    prompt = service._call_deepseek.call_args.args[0]
    assert "BINDING SPEC" in prompt and "ar_16:9" in prompt and "ar_4:3" in prompt
    assert "ar_16:9" in result.html_content
    assert 'lang="ms"' in result.html_content and "prefers-reduced-motion" in result.html_content


def test_outer_budget_covers_plan_and_gate_retries(monkeypatch):
    monkeypatch.setenv("AI_DESIGN_PLAN_ENABLED", "true")
    monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", True)
    monkeypatch.setattr(ai_service_module, "PREMIUM_DESIGN_LOOP", False)
    budget = ai_service_module.generation_outer_timeout_seconds()
    expected_min = ai_service_module.AI_DESIGN_PLAN_TIMEOUT_SECONDS + ai_service_module.AI_GLM_TIMEOUT_SECONDS * (1 + ai_service_module.DESIGN_GATE_MAX_RETRIES)
    assert budget >= expected_min
    monkeypatch.setenv("AI_DESIGN_PLAN_ENABLED", "false")
    assert ai_service_module.generation_outer_timeout_seconds() < budget
