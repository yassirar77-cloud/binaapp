"""Round 2 §B8 with the Dobi brief: an invented "Waktu Paling Lengang"
section (quiet-hour times not in the brief) is stripped; facts the merchant
supplied (10kg, 20kg, RM6.00, 24 jam, the address numbers) survive; an
essential section loses only the element carrying an invented fact."""

from app.services.fact_guard import FactSources, facts_in, guard_facts, unsupported_facts

SOURCES = FactSources.from_texts([
    "Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. Mesin basuh 10kg dan 20kg, pengering panas.",
    "Dobi Layan Diri Seksyen 18", "L7/1, Jalan 18/2, Seksyen 18, Shah Alam", "Buka 24 jam",
    "Basuh 10kg RM6.00", "Basuh 20kg RM12.00", "Pengering RM4.00", "60198765432",
], is_24h=True)

PAGE = """<!DOCTYPE html><html lang="ms"><head></head><body>
<nav><a href="#servis">Servis</a><a href="#lengang">Waktu Lengang</a><a href="#hubungi">Hubungi</a></nav>
<section id="home"><h1>Dobi Layan Diri Seksyen 18</h1><p>Buka 24 jam. Mesin 10kg dan 20kg.</p><a href="https://wa.me/60198765432">WhatsApp</a></section>
<section id="servis"><h2>Servis</h2><ul><li>Basuh 10kg — RM6.00</li><li>Basuh 20kg — RM12.00</li><li>Pengering — RM4.00</li></ul></section>
<section id="lengang"><h2>Waktu Paling Lengang</h2><p>Paling lengang 6 pagi - 9 pagi dan 10.30 malam.</p><p>Purata 15 minit menunggu.</p></section>
<section id="tentang"><h2>Tentang Kami</h2><p>Dobi layan diri di Seksyen 18.</p><p>Lebih 500 pelanggan setiap bulan.</p></section>
<section id="lokasi"><h2>Lokasi</h2><p>L7/1, Jalan 18/2, Seksyen 18, Shah Alam</p></section>
<footer><p>&copy; <span id="binaapp-year"></span> Dobi Layan Diri Seksyen 18</p></footer>
</body></html>"""


def test_facts_are_extracted_and_checked():
    facts = facts_in("Paling lengang 6 pagi - 9 pagi dan 10.30 malam. Purata 15 minit. Mesin 10kg. Harga RM6.00. Sejak 2009.")
    kinds = {(f.kind, f.text) for f in facts}
    assert ("time", "6 pagi") in kinds and ("time", "10.30 malam") in kinds
    assert ("unit", "15 minit") in kinds and ("unit", "10kg") in kinds
    assert ("price", "RM6.00") in kinds and ("number", "2009") in kinds
    bad = {f.text for f in unsupported_facts("Mesin 10kg, RM6.00, buka 24 jam, 6 pagi, 15 minit, 500 pelanggan", SOURCES)}
    assert bad == {"6 pagi", "15 minit", "500"}


def test_invented_section_is_stripped_and_essentials_keep_their_facts():
    out, report = guard_facts(PAGE, SOURCES)
    assert "Waktu Paling Lengang" not in out and 'href="#lengang"' not in out
    assert report.stripped_sections == ["lengang"]
    # Essential "Tentang" keeps the true sentence and loses the invented count.
    assert "Dobi layan diri di Seksyen 18." in out and "500 pelanggan" not in out
    assert report.stripped_elements == 1
    # Supplied facts survive everywhere.
    for kept in ("Buka 24 jam", "10kg", "RM6.00", "RM12.00", "L7/1, Jalan 18/2", "60198765432", "Basuh 20kg"):
        assert kept in out, kept
    assert "Servis</a>" in out and "Hubungi</a>" in out


def test_clean_page_is_untouched():
    clean = PAGE.replace('<section id="lengang"><h2>Waktu Paling Lengang</h2><p>Paling lengang 6 pagi - 9 pagi dan 10.30 malam.</p><p>Purata 15 minit menunggu.</p></section>\n', '').replace("<p>Lebih 500 pelanggan setiap bulan.</p>", "")
    out, report = guard_facts(clean, SOURCES)
    assert out == clean and not report.changed


def test_supplied_hours_allow_their_times():
    src = FactSources.from_texts(["Kedai buka 10:00 - 22:00"], is_24h=False)
    assert unsupported_facts("Buka 10:00 hingga 22:00 setiap hari", src) == []
    assert [f.text for f in unsupported_facts("Buka 9:00 pagi", src)] == ["9:00 pagi"]


import pytest
from unittest.mock import AsyncMock, patch

import app.services.ai_service as ai_service_module
from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
from app.services.ai_service import AIService


@pytest.mark.asyncio
async def test_pipeline_strips_the_invented_section_end_to_end(monkeypatch):
    monkeypatch.setattr(ai_service_module, "USE_GLM_FOR_HTML", False)
    monkeypatch.setenv("DESIGN_CRITIQUE_ENABLED", "false")
    svc = AIService()
    svc.deepseek_api_key = "k"
    req = WebsiteGenerationRequest(
        description="Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. Mesin basuh 10kg dan 20kg.",
        language=Language.MALAY, business_name="Dobi Layan Diri Seksyen 18", business_type="services", subdomain="bebe",
        whatsapp_number="0198765432", include_maps=False, location_address="L7/1, Jalan 18/2, Seksyen 18, Shah Alam",
        color_mode="light", design_freedom="designer", is_24h=True, opening_hours="Buka 24 jam",
        menu_items=[MenuItemInput(name="Basuh 10kg", price="6"), MenuItemInput(name="Basuh 20kg", price="12")],
    )
    svc._call_plan_model = AsyncMock(return_value=None)
    svc._call_deepseek = AsyncMock(return_value=PAGE)
    svc._call_qwen = AsyncMock(return_value=None)
    svc._improve_with_qwen = AsyncMock(side_effect=lambda h, d: h)
    svc._generate_ai_food_images = AsyncMock(side_effect=lambda h, **k: (h, 0))
    svc._autofill_missing_images = AsyncMock(return_value=0)
    result = await svc.generate_website(req, image_choice="none")
    html = result.html_content
    assert "Waktu Paling Lengang" not in html and "500 pelanggan" not in html
    assert "RM6.00" in html and "Buka 24 jam" in html and "10kg" in html
    assert svc._last_fact_guard["stripped_sections"] == ["lengang"]
