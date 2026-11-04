"""Round 2: a menu-board photo is the menu; item names stay grounded; the
logo is never doubled; Waze beside an existing Google Maps link."""

import pytest

from app.services.branding import apply_branding
from app.services.map_embed import add_waze_beside_maps_links
from app.services.menu_ocr import build_messages, parse_items, read_menu_from_image

OCR_RAW = """```json
{"is_menu": true, "items": [
  {"name": "Set A – Ayam Gepuk", "price": "RM12.50", "category": "Set Ayam"},
  {"name": "Set B – Ayam Gepuk Tauhu Tempe", "price": "13.50", "category": "Set Ayam"},
  {"name": "Air Mineral 500ml", "price": "2.00", "category": "Minuman"},
  {"name": "Bakso Daging (Coming Soon)", "price": "", "category": "Akan Datang"},
  {"name": "Set A – Ayam Gepuk", "price": "12.50", "category": "Set Ayam"},
]}
```"""


def test_parse_items_reads_names_prices_and_sections_and_dedupes():
    out = parse_items(OCR_RAW)
    assert out["is_menu"] and len(out["items"]) == 4
    assert out["items"][0] == {"name": "Set A – Ayam Gepuk", "price": "12.50", "category": "Set Ayam"}
    assert out["items"][2] == {"name": "Air Mineral 500ml", "price": "2.00", "category": "Minuman"}
    assert out["items"][3]["price"] == "" and out["items"][3]["category"] == "Akan Datang"


def test_parse_items_rejects_non_menus_and_garbage():
    assert parse_items('{"is_menu": false, "items": []}') == {"is_menu": False, "items": []}
    assert parse_items("not json at all")["items"] == []
    assert parse_items(None)["is_menu"] is False


@pytest.mark.asyncio
async def test_read_menu_from_image_uses_the_vision_model():
    seen = {}

    async def fake_model(messages):
        seen["messages"] = messages
        return OCR_RAW

    result = await read_menu_from_image("https://res.cloudinary.com/d/image/upload/v1/board.jpg", call_model=fake_model)
    assert result["is_menu"] and len(result["items"]) == 4 and result["image_url"].endswith("board.jpg")
    assert seen["messages"][1]["content"][0]["image_url"]["url"].endswith("board.jpg")
    assert "Never invent an item" in build_messages("u")[0]["content"]


class TestGroundedNames:
    def _svc(self):
        from app.services.ai_service import AIService
        return AIService()

    def test_fried_chicken_restaurant_gets_no_chocolate_or_cheese_variants(self):
        desc = ("Ayam Gepuk Panglima ialah restoran ayam gepuk di Klang. Pilih tahap kepedasan anda: Level 1, 2, 3. "
                "Slogan kami: Makin Pedas, Rasa Makin Padu. Set ayam gepuk, sotong krispy dan udang krispy.")
        names = self._svc()._fallback_item_names(desc, 4, "Ayam Gepuk Panglima")
        assert not any("coklat" in n.lower() or "keju" in n.lower() for n in names)

    def test_dessert_shop_that_names_toppings_keeps_its_variants(self):
        desc = "Kedai goreng pisang dengan macam-macam topping: coklat, keju, kacang."
        names = self._svc()._fallback_item_names(desc, 4, "Gerai Pisang")
        assert any("coklat" in n.lower() for n in names)

    def test_ungrounded_model_names_are_dropped(self):
        svc = self._svc()
        desc = "Restoran ayam gepuk dengan sambal pedas. Set ayam gepuk, sotong krispy, udang krispy, es jeruk."
        kept = svc._grounded_item_names(["Ayam Gepuk", "Ayam Goreng Coklat", "Sotong Krispy", "Es Jeruk", "Nasi Lemak"], desc)
        assert kept == ["Ayam Gepuk", "Sotong Krispy", "Es Jeruk"]


LOGO = "https://res.cloudinary.com/dpisgucmw/image/upload/v1793793862/binaapp/user_uploads/1bab975a.jpg"
MODEL_PAGE = """<html><head></head><body>
<header><a href="#hero" class="flex items-center gap-3"><img alt="Ayam Gepuk Panglima" class="h-10" src="https://res.cloudinary.com/dpisgucmw/image/upload/f_auto,q_auto,c_limit,w_1920/v1793793862/binaapp/user_uploads/1bab975a.jpg"><span>Ayam Gepuk Panglima</span></a></header>
<footer><div class="max-w-7xl"><div class="grid"><div><div class="flex items-center gap-3 mb-4"><img alt="Ayam Gepuk Panglima" class="h-8" src="https://res.cloudinary.com/dpisgucmw/image/upload/f_auto,q_auto,c_limit,w_800/v1793793862/binaapp/user_uploads/1bab975a.jpg"><span>Ayam Gepuk Panglima</span></div></div></div></div></footer>
</body></html>"""


def test_logo_already_rendered_by_the_model_is_not_added_again():
    out, rep = apply_branding(MODEL_PAGE, business_name="Ayam Gepuk Panglima", primary="#E63312", logo_url=LOGO)
    assert out.count("<img") == 2 and "data-binaapp-logo" not in out
    assert not rep.logo_header and not rep.logo_footer and rep.favicon == "logo"


def test_footer_logo_lands_beside_the_brand_text_not_before_the_grid():
    page = '<html><body><footer><div class="max-w-7xl"><div class="grid"><div><span class="font-heading">Ayam Gepuk Panglima</span><p>Alamat</p></div></div></div></footer></body></html>'
    out, rep = apply_branding(page, business_name="Ayam Gepuk Panglima", primary="#E63312", logo_url=LOGO)
    assert rep.logo_footer
    assert '<img src="' + LOGO in out and out.index("data-binaapp-logo") > out.index('<div class="grid"><div>')


def test_waze_link_is_added_once_beside_an_existing_google_maps_link():
    html = '<a class="btn-secondary" href="https://www.google.com/maps/search/?api=1&amp;query=No.+44-1" rel="noopener" target="_blank">Buka di Google Maps</a>'
    out, n = add_waze_beside_maps_links(html, "No. 44-1, Jalan Bayu Impian, 41200 Klang, Selangor")
    assert n == 1 and 'href="https://waze.com/ul?q=No.+44-1%2C+Jalan+Bayu+Impian%2C+41200+Klang%2C+Selangor&amp;navigate=yes"' in out
    waze_anchor = out[out.index("<a href=\"https://waze.com"):]
    assert 'class="btn-secondary"' in waze_anchor
    again, n2 = add_waze_beside_maps_links(out, "x")
    assert n2 == 0 and again == out
    assert add_waze_beside_maps_links(html, "") == (html, 0)
