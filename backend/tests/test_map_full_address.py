"""The map, the Maps/Waze buttons and the JSON-LD use the full street
address — not a short place name from the location field.

agp.binaapp.my: location "bayumas klang" (pin, Google Maps query, Waze
query, JSON-LD streetAddress) while the brief and footer carried
"No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor".
"""

import pytest

from app.services.data_consistency import is_short_place_name, prefer_full_address
from app.services.templates import TemplateService

FULL = "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor"
BRIEF = f"Ayam Gepuk Panglima di Kota Bayu Emas.\n\nAlamat: {FULL}.\nWhatsApp: 012-697 3105"


class TestResolve:
    @pytest.mark.parametrize("loc", ["bayumas klang", "Shah Alam", "Kota Bayu Emas, Klang", ""])
    def test_place_names(self, loc):
        assert is_short_place_name(loc)

    @pytest.mark.parametrize("loc", [FULL, "Lot 12 Pasar Seni", "Jalan Tun Razak", "41200 Klang"])
    def test_addresses(self, loc):
        assert not is_short_place_name(loc)

    def test_place_name_gives_way_to_the_brief_address(self):
        assert prefer_full_address("bayumas klang", BRIEF) == FULL

    def test_a_real_address_in_the_field_wins(self):
        assert prefer_full_address("L7/1, Jalan 18/2, Seksyen 18, Shah Alam", BRIEF) == "L7/1, Jalan 18/2, Seksyen 18, Shah Alam"

    def test_no_address_in_the_brief_keeps_the_place_name(self):
        assert prefer_full_address("bayumas klang", "Kedai ayam gepuk.") == "bayumas klang"


@pytest.mark.asyncio
async def test_generation_rewrites_the_request_before_anything_reads_it(monkeypatch):
    """The resolver runs at the top of generate_website, so the prompt,
    map, buttons and JSON-LD downstream all see the full address."""
    from app.models.schemas import Language, WebsiteGenerationRequest
    from app.services.ai_service import AIService
    from app.services.seo_metadata import SeoMeta, inject_seo_metadata

    req = WebsiteGenerationRequest(
        description=BRIEF, language=Language.MALAY, business_name="Ayam Gepuk Panglima",
        business_type="food", subdomain="agp", location_address="bayumas klang",
    )
    svc = AIService.__new__(AIService)

    class _Stop(Exception):
        pass

    def _boom(*a, **k):
        raise _Stop()

    monkeypatch.setattr(svc, "_new_zai_image_phase", _boom, raising=False)
    with pytest.raises(_Stop):
        await svc.generate_website(req, image_choice="none")
    assert req.location_address == FULL
    page = inject_seo_metadata("<html><head></head><body></body></html>", SeoMeta(
        business_name="AGP", description=BRIEF, address=req.location_address, business_type="food"))
    assert "Jalan Bayu Impian" in page and '"streetAddress": "bayumas' not in page


def test_buttons_and_embed_use_the_full_address():
    html = '<html><body><footer></footer></body></html>'
    out = TemplateService().inject_google_maps(html, FULL, business_name="Ayam Gepuk Panglima")
    assert "waze.com/ul?q=No.+44-1%2C+Jalan+Bayu+Impian" in out
    assert "query=No.+44-1%2C+Jalan+Bayu+Impian" in out


class TestWidgetInSlot:
    def test_slot_under_a_heading_gets_no_second_heading_or_padding(self):
        html = (
            '<html><body><section id="lokasi"><div class="container"><h2>Lokasi Kami</h2>'
            '<div id="binaapp-maps-slot"></div></div></section><footer></footer></body></html>'
        )
        out = TemplateService().inject_google_maps(html, FULL, business_name="Ayam Gepuk Panglima")
        section = out[out.index('id="lokasi"'):out.index("</section>")]
        assert section.count("<h2") == 1 and "Ayam Gepuk Panglima</h2>" not in section
        assert "padding:60px 20px" not in section and "<iframe" in section

    def test_bare_slot_keeps_its_heading(self):
        html = '<html><body><section id="x"><div id="binaapp-maps-slot"></div></section><footer></footer></body></html>'
        out = TemplateService().inject_google_maps(html, FULL, business_name="Ayam Gepuk Panglima")
        assert "Ayam Gepuk Panglima</h2>" in out and "padding:60px 20px" in out

    def test_fallback_section_keeps_its_heading(self):
        out = TemplateService().inject_google_maps("<html><body><footer></footer></body></html>", FULL, business_name="AGP")
        assert "AGP</h2>" in out
