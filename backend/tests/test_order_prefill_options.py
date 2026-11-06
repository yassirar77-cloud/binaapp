"""Per-item WhatsApp order prefill: "(Level: _, Dine-in/Take away: _)".

On agp.binaapp.my the Level blank was added to drinks and kids' items, and
items whose names contain parentheses ("Pedal Ayam Goreng (3 pcs)") got no
suffix at all — the idempotency check treated any "(" as already enriched.
"""

import json
import os
from urllib.parse import quote, unquote

import pytest

from app.services import menu_fidelity as mf
from app.services.whatsapp_prefill import enrich_order_links, level_applies

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ayam_gepuk_panglima_menu.json")
BRIEF = (
    "Tahap kepedasan: Level 1 (Spicy), Level 2 (Hot) atau Level 3 (Extra Hot).\n"
    "Makan di kedai: FREE refill nasi & sambal. Take away: caj tambahan RM2.00."
)
BOTH = " (Level: _, Dine-in/Take away: _)"
DINE = " (Dine-in/Take away: _)"


@pytest.fixture(scope="module")
def raw_items():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)["menu_items"]


def _texts(html):
    import re
    return {unquote(m) for m in re.findall(r'text=([^"&]+)', html)}


def _link(name):
    return f'<a href="https://wa.me/60126973105?text={quote("Assalamualaikum, saya nak order " + name, safe="")}">Pesan</a>'


class TestLevelApplies:
    @pytest.mark.parametrize("name", ["Set A – Ayam Gepuk", "Set Sotong Krispy", "Set Panglima Signature – Ayam Gepuk Telur Mata"])
    def test_main_and_set_food(self, raw_items, name):
        assert level_applies(name, raw_items)

    @pytest.mark.parametrize("name", ["Teh O Ice", "Air Mineral 500ml", "Bali Blues", "Es Jeruk", "Fries", "Fries + Nugget (5 pcs)", "Sambal Extra"])
    def test_never_on_drinks_kids_or_addons(self, raw_items, name):
        assert not level_applies(name, raw_items)

    def test_without_categories_drink_names_are_still_recognised(self):
        assert not level_applies("Teh Tarik") and not level_applies("Kopi O Ais")
        assert level_applies("Nasi Lemak Ayam")

    def test_category_named_air(self):
        assert not level_applies("Balang Mango", [{"name": "Balang Mango", "category": "Air Balang"}])


class TestEnrich:
    def test_whole_menu_block(self, raw_items):
        items = mf.normalize_items(raw_items)
        block = mf.render_menu_block(items, wa_digits="60126973105", order_prefill="Assalamualaikum, saya nak order")
        out, n = enrich_order_links(block, BRIEF, "ms", items=raw_items)
        assert n == len(items)  # every item, including "(3 pcs)" names
        texts = _texts(out)
        assert "Assalamualaikum, saya nak order Set A – Ayam Gepuk" + BOTH in texts
        assert "Assalamualaikum, saya nak order Pedal Ayam Goreng (3 pcs)" + DINE in texts
        assert "Assalamualaikum, saya nak order Fries + Tender Chicken (3 pcs)" + DINE in texts
        assert "Assalamualaikum, saya nak order Teh O Ice" + DINE in texts
        assert "Assalamualaikum, saya nak order Bali Blues" + DINE in texts
        assert not any("Level" in t for t in texts if "Teh" in t or "Fries" in t or "Air" in t)
        again, n2 = enrich_order_links(out, BRIEF, "ms", items=raw_items)
        assert n2 == 0 and again == out

    def test_parenthesised_food_name_gets_level(self):
        out, n = enrich_order_links(_link("Ayam Gepuk (2 pcs)"), BRIEF, "ms", items=[{"name": "Ayam Gepuk (2 pcs)", "category": "Set Ayam"}])
        assert n == 1 and "Assalamualaikum, saya nak order Ayam Gepuk (2 pcs)" + BOTH in _texts(out)

    def test_dine_in_only_brief(self):
        out, n = enrich_order_links(_link("Teh O Ice"), "Dine-in atau take away", "ms")
        assert n == 1 and _texts(out) == {"Assalamualaikum, saya nak order Teh O Ice" + DINE}

    def test_level_only_brief_skips_drinks_entirely(self):
        out, n = enrich_order_links(_link("Teh O Ice"), "Level 1 Spicy", "ms")
        assert n == 0
