"""
Multi-style preview, the merchant's pick (preferred plan) and AI listening.

- generate_plan_variants: three distinct plans → three low-fidelity previews
  (no images generated, no critique), each carrying its plan
- a preferred_plan on the request is validated and used, never re-planned
- /api/generate/listen returns questions only below the threshold
- /api/generate/refine starts a full job with the picked plan from the stash
- /api/generate/status never leaks the stashed request body
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import app.services.ai_service as ai_service_module
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services.ai_service import AIService
from app.services.design_plan import PlanBrief, fallback_plan


def _request(**kw):
    base = dict(
        description="Nasi kandar mamak buka 24 jam di Shah Alam. Ayam goreng berempah dan kari kepala ikan.",
        language=Language.MALAY, business_name="Nasi Kandar Crystal", business_type="food", subdomain="crystal",
        whatsapp_number="0198765432", include_maps=False, location_address="Shah Alam", color_mode="light",
        design_freedom="designer", menu_items=[MenuItemInput(name="Ayam Goreng Berempah", price="RM8")],
    )
    base.update(kw)
    return WebsiteGenerationRequest(**base)


HTML = '<!DOCTYPE html><html lang="ms"><head></head><body><section id="home"><h1>Nasi Kandar Crystal</h1></section><footer>&copy; <span id="binaapp-year"></span> Nasi Kandar Crystal</footer></body></html>'


@pytest.mark.asyncio
async def test_generate_plan_variants_returns_three_distinct_previews(monkeypatch):
    monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
    svc = AIService()
    svc.deepseek_api_key = "k"
    svc._call_plan_model = AsyncMock(return_value=None)
    svc._call_deepseek = AsyncMock(return_value=HTML)
    variants = await svc.generate_plan_variants(_request(), image_choice="none", n_plans=3)
    assert len(variants) == 3
    assert len({v["style"] for v in variants}) == 3
    assert all(v["plan"]["direction"] == v["style"] and v["html"].startswith("<!DOCTYPE") for v in variants)
    assert svc._call_deepseek.await_count == 3
    prompts = [c.args[0] for c in svc._call_deepseek.call_args_list]
    assert all("BINDING SPEC" in p for p in prompts) and len({p for p in prompts}) == 3


@pytest.mark.asyncio
async def test_preferred_plan_is_validated_not_replanned():
    svc = AIService()
    svc.deepseek_api_key = "k"
    svc._call_plan_model = AsyncMock(return_value="{}")
    brief = svc._plan_brief_for(_request(), color_mode="light", has_images=False, image_count=0, design_brief=None, language="ms")
    picked = fallback_plan(brief, variant=1).as_dict()
    picked["palette"]["text"] = "#CCCCCC"  # unreadable on purpose → must be repaired
    plans = await svc._direct_design_plan(brief, history=[picked["direction"]], preferred_plan=picked)
    svc._call_plan_model.assert_not_awaited()
    assert plans[0].direction == picked["direction"]  # not rotated away despite history
    assert plans[0].palette["text"] != "#CCCCCC"


# ---- endpoints ---------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(main_module.app)


def test_listen_returns_questions_only_when_thin(client):
    r = client.post("/api/generate/listen", json={"description": "Kedai makan", "business_name": "Kedai Pak Mat", "business_type": "food"})
    data = r.json()
    assert r.status_code == 200 and data["completeness"] < 40 and data["questions"]
    assert any("hidangan" in q for q in data["questions"])
    full = client.post("/api/generate/listen", json={
        "description": " ".join(["kata"] * 80), "business_name": "Kedai Pak Mat", "business_type": "food",
        "menu_items": [{"name": "Nasi"}, {"name": "Mee"}], "images": [{"url": "u", "name": "Hero Image"}],
        "address": "Shah Alam", "whatsapp_number": "0198765432", "opening_hours": "9-5",
    }).json()
    assert full["completeness"] >= 40 and full["questions"] == []


def test_status_strips_stashed_request(client, monkeypatch):
    job = {"job_id": "j1", "status": "completed", "progress": 100, "html": HTML,
           "styles": json.dumps([{"style": "warung_cerah", "name": "Warung Cerah", "html": HTML, "plan": {"direction": "warung_cerah"}, "_request": {"secret": 1}}])}
    monkeypatch.setattr(main_module, "get_job_from_supabase", AsyncMock(return_value=job))
    r = client.get("/api/generate/status/j1")
    data = r.json()
    assert r.status_code == 200
    assert data["styles"][0]["plan"]["direction"] == "warung_cerah"
    assert "_request" not in data["styles"][0] and "secret" not in json.dumps(data)


def test_refine_starts_a_full_job_with_the_picked_plan(client, monkeypatch):
    stash = {"description": "Nasi kandar mamak buka 24 jam di Shah Alam.", "business_name": "Nasi Kandar Crystal",
             "language": "ms", "business_type": "food", "multi_style": True}
    job = {"job_id": "j1", "status": "completed", "progress": 100, "html": HTML, "styles": json.dumps([
        {"style": "warung_cerah", "name": "Warung Cerah", "html": HTML, "plan": {"direction": "warung_cerah", "source": "ai"}, "_request": stash},
        {"style": "pasar_pagi", "name": "Pasar Pagi", "html": HTML, "plan": {"direction": "pasar_pagi", "source": "ai"}},
    ])}
    monkeypatch.setattr(main_module, "get_job_from_supabase", AsyncMock(return_value=job))
    captured = {}

    async def _fake_start(body, preferred_plan=None):
        captured["body"] = body
        captured["plan"] = preferred_plan
        return {"success": True, "job_id": "j2"}

    monkeypatch.setattr(main_module, "_start_generation_from_body", _fake_start)
    r = client.post("/api/generate/refine", json={"job_id": "j1", "style": "pasar_pagi"})
    assert r.status_code == 200 and r.json()["job_id"] == "j2"
    assert captured["plan"]["direction"] == "pasar_pagi" and captured["body"]["business_name"] == "Nasi Kandar Crystal"
    r = client.post("/api/generate/refine", json={"job_id": "j1", "style": "nope"})
    assert r.status_code == 404
    r = client.post("/api/generate/refine", json={"job_id": "j1"})
    assert r.status_code == 400


def test_stash_drops_qr_image_and_multi_flag():
    stash = main_module._stash_request_body({"multi_style": True, "payment": {"cod": True, "qr_image": "data:...", "qr": False}, "x": 1})
    assert "multi_style" not in stash and "qr_image" not in stash["payment"] and stash["payment"]["cod"] is True
