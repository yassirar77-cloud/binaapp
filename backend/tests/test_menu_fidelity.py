"""Menu fidelity: the merchant's items reach the page exactly as entered.

The fixture is the Ayam Gepuk Panglima menu (32 items in 6 sections) that
shipped as four cards, two of them invented, with every price wrong.
"""

import json
import os
import re

import pytest

from app.services import menu_fidelity as mf
from app.services.menu_persistence import items_from_rows, rows_for
from app.services.whatsapp_prefill import (
    default_prefill, enrich_order_links, order_options, order_prefill_for,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ayam_gepuk_panglima_menu.json")


@pytest.fixture(scope="module")
def panglima():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def _card(name, price, desc="Sedap."):
    return (
        f'<div class="card"><h3>{name}</h3><p>{desc}</p>'
        f'<span class="price">RM{price}</span>'
        f'<a href="https://wa.me/60126973105?text=Assalamualaikum%2C%20saya%20nak%20pesan%20{name.replace(" ", "%20")}">Pesan</a></div>'
    )


SMALL_ITEMS = [
    {"name": "Nasi Lemak Ayam", "price": "8.50", "category": "Nasi"},
    {"name": "Mee Goreng Mamak", "price": "7.00", "category": "Mee"},
    {"name": "Teh Tarik", "price": "2.50", "category": "Minuman"},
]


def _page(menu_inner, extra=""):
    return f"""<!DOCTYPE html><html><head><title>t</title></head><body>
<header><nav>Menu</nav></header>
<section id="hero"><h1>Warung</h1><p>Set bermula RM8.50</p></section>
<section id="menu" class="py-16"><div class="container"><h2>Menu</h2>{menu_inner}</div></section>
{extra}
<footer><p>&copy; Warung</p></footer></body></html>"""


class TestReconcile:
    def test_invented_item_is_removed(self):
        html = _page(_card("Nasi Lemak Ayam", "8.50") + _card("Nasi Lemak Coklat", "9.90") + _card("Mee Goreng Mamak", "7.00") + _card("Teh Tarik", "2.50"))
        out, rep = mf.reconcile_menu(html, SMALL_ITEMS, wa_digits="60126973105")
        assert rep.removed == ["Nasi Lemak Coklat"]
        assert "Nasi Lemak Coklat" not in out
        assert rep.injected == [] and rep.price_fixed == []
        assert rep.matched == 3
        # 1 of 3 is over the 20% line: loud by design.
        assert rep.severe

    def test_wrong_price_is_corrected_to_the_supplied_price(self):
        html = _page(_card("Nasi Lemak Ayam", "12.50") + _card("Mee Goreng Mamak", "7.00") + _card("Teh Tarik", "2.50"))
        out, rep = mf.reconcile_menu(html, SMALL_ITEMS)
        assert rep.price_fixed == ["Nasi Lemak Ayam: RM12.50 -> RM8.50"]
        assert "RM12.50" not in out and "RM8.50" in out

    def test_missing_item_is_injected_into_the_menu_section(self):
        html = _page(_card("Nasi Lemak Ayam", "8.50") + _card("Mee Goreng Mamak", "7.00"))
        out, rep = mf.reconcile_menu(html, SMALL_ITEMS, wa_digits="60126973105", order_prefill="Assalamualaikum, saya nak order")
        assert rep.injected == ["Teh Tarik"]
        menu = out[out.index('<section id="menu"'):out.index("</section>", out.index('<section id="menu"'))]
        assert "Teh Tarik" in menu and "RM2.50" in menu
        assert "wa.me/60126973105?text=Assalamualaikum%2C%20saya%20nak%20order%20Teh%20Tarik" in menu
        # The rest of the document is untouched.
        assert out.startswith("<!DOCTYPE html>") and "<footer><p>&copy; Warung</p></footer>" in out

    def test_informational_tile_without_a_price_is_left_alone(self):
        html = _page('<div class="levels"><h3>Level 1</h3><p>Spicy</p></div>' + _card("Nasi Lemak Ayam", "8.50") + _card("Mee Goreng Mamak", "7.00") + _card("Teh Tarik", "2.50"))
        out, rep = mf.reconcile_menu(html, SMALL_ITEMS)
        assert "Level 1" in out and rep.removed == []

    def test_fragment_of_a_longer_item_name_is_not_a_match(self):
        items = [{"name": "Pedal Ayam Goreng (3 pcs)", "price": "3.00"}, {"name": "Set Panglima Krispy", "price": "14.90"}, {"name": "Set Panglima Signature", "price": "15.90"}]
        html = _page(_card("Ayam Goreng", "12.50") + _card("Set Panglima", "12.50"))
        out, rep = mf.reconcile_menu(html, items)
        assert sorted(rep.removed) == ["Ayam Goreng", "Set Panglima"]
        assert len(rep.injected) == 3

    def test_qualified_name_still_matches_and_is_renamed_verbatim(self):
        html = _page(_card("Teh Tarik (panas)", "2.50") + _card("Nasi Lemak Ayam", "8.50") + _card("Mee Goreng Mamak", "7.00"))
        out, rep = mf.reconcile_menu(html, SMALL_ITEMS)
        assert rep.removed == [] and rep.injected == []
        assert rep.renamed == ["Teh Tarik (panas) -> Teh Tarik"]
        assert "<h3>Teh Tarik</h3>" in out

    def test_more_than_twenty_percent_corrections_is_severe(self, panglima):
        html = _page(_card("Set Panglima", "12.50") + _card("Ayam Goreng Keju", "12.50"))
        out, rep = mf.reconcile_menu(html, panglima["menu_items"], wa_digits="60126973105")
        assert rep.total == 32 and rep.severe and rep.ratio > 0.2
        assert len(rep.injected) == 32

    def test_no_menu_section_gets_a_full_menu_before_the_footer(self):
        html = "<html><body><section id='hero'><h1>W</h1></section><footer>f</footer></body></html>"
        out, rep = mf.reconcile_menu(html, SMALL_ITEMS)
        assert rep.injected == [i["name"] for i in SMALL_ITEMS]
        assert out.index('<section id="menu"') < out.index("<footer>")

    def test_clean_page_needs_no_correction_and_is_returned_unchanged(self):
        html = _page(_card("Nasi Lemak Ayam", "8.50") + _card("Mee Goreng Mamak", "7.00") + _card("Teh Tarik", "2.50"))
        out, rep = mf.reconcile_menu(html, SMALL_ITEMS)
        assert out == html and not rep.changed and rep.matched == 3

    def test_no_items_means_nothing_to_do(self):
        html = _page(_card("Anything", "1.00"))
        out, rep = mf.reconcile_menu(html, [])
        assert out == html and rep.total == 0


class TestDeterministicRender:
    def test_large_menu_uses_the_slot(self, panglima):
        items = mf.normalize_items(panglima["menu_items"])
        assert len(items) == 32 and mf.use_deterministic_menu(items)
        assert not mf.use_deterministic_menu(mf.normalize_items(SMALL_ITEMS))

    def test_block_keeps_every_item_price_and_category_grouping(self, panglima):
        items = mf.normalize_items(panglima["menu_items"])
        block = mf.render_menu_block(items, language="ms", wa_digits="60126973105", order_prefill="Assalamualaikum, saya nak order")
        for it in panglima["menu_items"]:
            assert it["name"] in block or mf._esc(it["name"]) in block
            assert f"RM{it['price']}" in block
        cats = re.findall(r'<div class="bmf-cat"><h3>(.*?)</h3>', block)
        assert cats == ["Set Ayam", "Set Seafood Krispy", "Tambahan", "Minuman", "Special Drink", "Kid&#x27;s Menu"]
        assert block.count('class="bmf-order"') == 32
        assert 'class="bmf-badge">Signature' in block
        assert "justify-content:center" in block  # a short last row is centred

    def test_slot_is_filled_and_model_written_duplicates_are_dropped(self, panglima):
        items = mf.normalize_items(panglima["menu_items"])
        html = _page(f'<p>Intro</p><div id="{mf.MENU_SLOT_ID}"></div>' + _card("Set Sotong Krispy", "19.00") + _card("Ayam Goreng Keju", "9.00"))
        block = mf.render_menu_block(items, wa_digits="60126973105")
        html, filled = mf.fill_menu_slot(html, block)
        assert filled
        out, rep = mf.reconcile_menu(html, items, wa_digits="60126973105")
        assert rep.injected == [] and rep.price_fixed == []
        assert "Ayam Goreng Keju" in rep.removed and "Set Sotong Krispy" in rep.duplicates
        assert out.count("Set Sotong Krispy") >= 1 and "RM19.00" not in out and "RM20.90" in out

    def test_missing_slot_is_handled_by_reconciliation(self, panglima):
        html = _page("<p>Intro only</p>")
        out, rep = mf.reconcile_menu(html, panglima["menu_items"])
        assert len(rep.injected) == 32 and "Fries + Nugget (5 pcs)" in out

    def test_prices_off_renders_no_price(self):
        block = mf.render_menu_block(mf.normalize_items(SMALL_ITEMS), show_prices=False)
        assert "RM" not in block


class TestPromptRules:
    def _prompt(self, items):
        from app.services.ai_service import AIService
        svc = AIService()
        return svc._build_strict_prompt(
            name="Ayam Gepuk Panglima", desc="Restoran ayam gepuk di Klang.", style="modern",
            language="ms", whatsapp_number="0126973105", image_choice="none", menu_items=items,
        )

    def test_large_menu_prompt_asks_for_the_slot_not_the_cards(self, panglima):
        prompt = self._prompt(panglima["menu_items"])
        assert f'<div id="{mf.MENU_SLOT_ID}"></div>' in prompt
        assert "DO NOT write the item cards yourself" in prompt
        assert "NEVER invent a dish" in prompt

    def test_small_menu_prompt_keeps_the_verbatim_contract(self):
        prompt = self._prompt(SMALL_ITEMS)
        assert "Render EVERY item listed above" in prompt
        assert mf.MENU_SLOT_ID not in prompt
        assert "Do NOT add any item that is not in this list" in prompt

    def test_no_items_with_labelled_photos_forbids_prices(self):
        from app.services.ai_service import AIService
        prompt = AIService()._build_strict_prompt(
            name="Ayam Gepuk Panglima", desc="Restoran ayam gepuk.", style="modern", language="ms",
            image_choice="upload", images={"hero": "https://x/h.jpg", "gallery1": "https://x/1.jpg", "gallery1_name": "Ayam Goreng"},
        )
        assert "PHOTOS ONLY" in prompt and "DO NOT render a price for any tile" in prompt


class TestPersistenceShapes:
    def test_rows_for_keeps_categories_and_skips_unpriced(self):
        plan = rows_for("w1", [{"name": "Sup", "price": "1.00", "category": "Tambahan"}, {"name": "Tanya harga", "price": "", "category": "Lain"}])
        assert [c["name"] for c in plan["categories"]] == ["Tambahan", "Lain"]
        assert plan["items"][0]["_category"] == "Tambahan" and plan["items"][0]["price"] == 1.0
        assert plan["skipped"] == ["Tanya harga"]

    def test_items_from_rows_round_trips_the_generator_shape(self):
        cats = [{"id": "c1", "name": "Minuman", "sort_order": 1}, {"id": "c0", "name": "Menu", "sort_order": 0}]
        rows = [
            {"name": "Teh O Ice", "price": 3, "category_id": "c1", "sort_order": 0, "is_popular": False},
            {"name": "Set A", "price": 12.5, "category_id": "c0", "sort_order": 0, "is_popular": True},
        ]
        items = items_from_rows(rows, cats)
        assert items[0] == {"name": "Set A", "price": "12.50", "category": "", "description": "", "image_url": "", "signature": True}
        assert items[1]["category"] == "Minuman" and items[1]["price"] == "3.00"


class TestWhatsAppPrefill:
    def test_food_business_gets_order_wording(self):
        assert default_prefill("ms", "food") == "Assalamualaikum, saya nak order"
        assert default_prefill("ms", "salon").startswith("Assalamualaikum, saya berminat")
        assert default_prefill("en", "food") == "Hi, I would like to order"
        assert order_prefill_for("", "ms") == "Assalamualaikum, saya nak order"

    def test_options_follow_the_brief(self):
        brief = "Pilih tahap kepedasan anda: Level 1 (Spicy). Makan di kedai: FREE refill. Take away: caj RM2."
        assert order_options(brief) == ["Level: _", "Dine-in/Take away: _"]
        assert order_options("Kedai kuih tradisional") == []

    def test_item_links_get_the_blanks_and_the_floating_button_does_not(self):
        html = (
            '<a href="https://wa.me/60126973105?text=Assalamualaikum%2C%20saya%20nak%20order%20Set%20A">Pesan</a>'
            '<a href="https://wa.me/60126973105?text=Assalamualaikum,%20saya%20nak%20order" id="whatsapp-button">x</a>'
        )
        out, n = enrich_order_links(html, "Level 1 Spicy, dine-in atau take away", "ms")
        assert n == 1
        assert "Set%20A%20%28Level%3A%20_%2C%20Dine-in%2FTake%20away%3A%20_%29" in out
        assert 'text=Assalamualaikum,%20saya%20nak%20order" id="whatsapp-button"' in out
        again, n2 = enrich_order_links(out, "Level 1", "ms")
        assert n2 == 0 and again == out
