"""
Round 2 §B5–§B7 with the Dobi brief: a 24-hour dobi shows "Buka 24 jam" and
never "tutup 23:59"; prices are decimals through one formatter and a typo
like "RM25.oo" is refused at the form and fails the build; the address is
normalised and never rendered as a heading.
"""

import json
import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.main as main_module
from app.middleware.subdomain import _OPEN_BADGE_SCRIPT, _inject_open_badge
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services.ai_service import AIService
from app.services.data_consistency import enforce_24h_copy
from app.services.generation_validator import GenerationBrief, validate_generated_site
from app.services.templates import TemplateService

DOBI_BODY = {
    "description": "Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. Mesin basuh 10kg dan 20kg.",
    "business_name": "Dobi Layan Diri Seksyen 18", "business_type": "services",
    "address": "l7/l, jalan 18/2, seksyen 18, shah alam", "language": "ms", "user_id": "anonymous",
    "features": {"whatsapp": True, "googleMap": True}, "whatsapp_number": "0198765432",
    "menu_items": [{"name": "Basuh 10kg", "price": "6"}, {"name": "Basuh 20kg", "price": "12.5"}],
}


@pytest.fixture
def client():
    return TestClient(main_module.app)


def _capture_task(monkeypatch):
    recorder = AsyncMock()
    monkeypatch.setattr(main_module, "run_generation_task", recorder)
    monkeypatch.setattr(main_module.asyncio, "create_task", lambda coro: (coro.close(), MagicMock())[1])
    monkeypatch.setattr(main_module, "supabase", None)
    return recorder


# ---- B5 hours ------------------------------------------------------------

def test_start_marks_the_dobi_as_24h_and_normalises_the_address(client, monkeypatch):
    recorder = _capture_task(monkeypatch)
    r = client.post("/api/generate/start", json={**DOBI_BODY, "opening_hours": "00:00 - 23:59"})
    assert r.status_code == 200, r.text
    call = recorder.call_args
    assert call.kwargs["is_24h"] is True and call.kwargs["opening_hours"] == "Buka 24 jam"
    assert call.args[7] == "L7/1, Jalan 18/2, Seksyen 18, Shah Alam"
    # The story alone ("24 jam") is enough when no structured hours were sent.
    r = client.post("/api/generate/start", json=DOBI_BODY)
    assert recorder.call_args.kwargs["is_24h"] is True


def test_structured_hours_and_24h_copy():
    req = WebsiteGenerationRequest(description="Dobi layan diri 24 jam", business_name="Dobi", subdomain="dobi", is_24h=True, opening_hours="Buka 24 jam")
    assert AIService._structured_hours_for(req) == [{"days": "Isnin - Ahad", "hours": "00:00 - 23:59"}]
    daily = WebsiteGenerationRequest(description="Kedai runcit di Shah Alam", business_name="Kedai", subdomain="kedai", opening_hours="10:00 - 22:00")
    assert AIService._structured_hours_for(daily) == [{"days": "Isnin - Ahad", "hours": "10:00 - 22:00"}]
    assert AIService._structured_hours_for(WebsiteGenerationRequest(description="Kedai runcit di Shah Alam", business_name="Kedai", subdomain="kedai")) is None
    html = '<p>Buka sekarang · tutup 23:59</p><p>Waktu: 00:00 - 23:59 setiap hari</p><span>Buka 24 jam</span>'
    out, n = enforce_24h_copy(html, "ms")
    assert n == 2 and "23:59" not in out and out.count("Buka 24 jam") == 3


def test_open_badge_script_says_buka_24_jam():
    assert "Buka 24 jam" in _OPEN_BADGE_SCRIPT and "Open 24 hours" in _OPEN_BADGE_SCRIPT
    page = '<html lang="ms"><head><script type="application/ld+json">{"@type":"LocalBusiness","openingHoursSpecification":[{"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],"opens":"00:00","closes":"23:59"}]}</script></head><body></body></html>'
    injected = _inject_open_badge(page)
    assert "BinaApp Open Badge" in injected


@pytest.mark.asyncio
async def test_open_badge_renders_buka_24_jam_in_a_browser():
    try:
        from playwright.async_api import async_playwright
    except Exception:
        pytest.skip("playwright not installed")
    page_html = '<html lang="ms"><head><script type="application/ld+json">{"@type":"LocalBusiness","openingHoursSpecification":[{"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"],"opens":"00:00","closes":"23:59"}]}</script></head><body><h1>Dobi</h1></body></html>'
    injected = _inject_open_badge(page_html)
    try:
        async with async_playwright() as pw:
            kwargs = {"headless": True, "args": ["--no-sandbox"]}
            if os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
                kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"]
            browser = await pw.chromium.launch(**kwargs)
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.set_content(injected)
            await page.wait_for_timeout(300)
            label = await page.evaluate("() => (document.getElementById('binaapp-open-badge') || {}).textContent || ''")
            await browser.close()
    except Exception as err:
        pytest.skip(f"no browser: {err}")
    assert "Buka 24 jam" in label and "23:59" not in label


# ---- B6 prices -----------------------------------------------------------

def test_menu_item_price_is_normalised_or_refused():
    assert MenuItemInput(name="Basuh 10kg", price="6").price == "RM6.00"
    assert MenuItemInput(name="Basuh 20kg", price="RM 12,5").price == "RM12.50"
    assert MenuItemInput(name="Pengering", price="").price is None
    assert MenuItemInput(name="Set Kenduri", price="RM18/pax").price == "RM18.00/pax"
    with pytest.raises(ValidationError):
        MenuItemInput(name="Cuci selimut", price="RM25.oo")


def test_start_refuses_a_typo_price(client, monkeypatch):
    recorder = _capture_task(monkeypatch)
    r = client.post("/api/generate/start", json={**DOBI_BODY, "menu_items": [{"name": "Cuci selimut", "price": "RM25.oo"}]})
    assert r.status_code == 400 and r.json()["error"] == "invalid_price" and "RM25.oo" in r.json()["message"]
    recorder.assert_not_called()
    r = client.post("/api/generate/start", json=DOBI_BODY)
    assert r.status_code == 200
    assert [i["price"] for i in recorder.call_args.kwargs["menu_items"]] == ["RM6.00", "RM12.50"]


def test_validator_fails_the_build_on_bad_price_format():
    brief = GenerationBrief(business_name="Dobi", description="dobi", menu_items=[{"name": "Cuci selimut", "price": "RM25.00"}])
    bad = '<html><body><h1>Dobi</h1><section id="servis"><h2>Servis</h2><p>Cuci selimut RM25.oo</p></section></body></html>'
    result = validate_generated_site(bad, brief)
    assert any(i.code == "bad_price_format" for i in result.errors)
    good = bad.replace("RM25.oo", "RM25.00")
    assert not any(i.code == "bad_price_format" for i in validate_generated_site(good, brief).errors)


# ---- B7 address ----------------------------------------------------------

def test_map_block_heading_is_the_business_name_not_the_address():
    svc = TemplateService()
    html = '<html><body><section id="lokasi"><div id="binaapp-maps-slot"></div></section></body></html>'
    out = svc.inject_google_maps(html, "L7/1, Jalan 18/2, Seksyen 18, Shah Alam", business_name="Dobi Layan Diri Seksyen 18")
    assert "<h2" in out and "Dobi Layan Diri Seksyen 18</h2>" in out
    assert "📍 L7/1, Jalan 18/2, Seksyen 18, Shah Alam</p>" in out
    assert "18/2, Seksyen 18, Shah Alam</h2>" not in out
