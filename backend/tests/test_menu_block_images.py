"""The deterministic menu block shows the photos generated or uploaded for
the merchant's items, spending a limited image budget on the items that
matter (signature, first category, sets, above-median price) and keeping
drinks, kids' items and add-ons as text-only cards.

agp.binaapp.my shipped 32 text-only cards although image source was
"AI Gambar — Percuma" and four item photos had been generated.
"""

import json
import os
import re

import pytest

from app.services import menu_fidelity as mf

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ayam_gepuk_panglima_menu.json")


@pytest.fixture(scope="module")
def items():
    with open(FIXTURE, encoding="utf-8") as fh:
        return mf.normalize_items(json.load(fh)["menu_items"])


def _cards(block):
    return re.findall(r'<li class="([^"]+)"[^>]*>(.*?)</li>', block, re.DOTALL)


class TestCategories:
    @pytest.mark.parametrize("cat", ["Minuman", "Special Drink", "Kid's Menu", "Air Balang", "Tambahan", "Add-ons", "Menu Kanak-kanak"])
    def test_text_only_categories(self, cat):
        assert mf.text_only_category(cat)

    @pytest.mark.parametrize("cat", ["Set Ayam", "Set Seafood Krispy", "Nasi", "Mee", ""])
    def test_main_categories_may_have_photos(self, cat):
        assert not mf.text_only_category(cat)


class TestPriority:
    def test_signature_then_first_category_sets_then_others(self, items):
        ranked = [it.name for it in mf.image_priority(items)]
        assert ranked[0] == "Set Panglima Signature – Ayam Gepuk Telur Mata"
        # The rest of the first category (all "Set …") before the seafood sets.
        assert ranked[1:5] == [
            "Set A – Ayam Gepuk", "Set B – Ayam Gepuk Tauhu Tempe",
            "Set C – Ayam Gepuk Kubis Goreng", "Set Panglima Krispy – Ayam Krispy",
        ]
        assert set(ranked[5:]) == {"Set Sotong Krispy", "Set Udang Krispy"}

    def test_drinks_kids_and_addons_are_never_ranked(self, items):
        cats = {it.category for it in mf.image_priority(items)}
        assert cats == {"Set Ayam", "Set Seafood Krispy"}

    def test_drinks_only_menu_still_gets_photos(self):
        drinks = mf.normalize_items([
            {"name": "Kopi O", "price": "2", "category": "Minuman"},
            {"name": "Teh Tarik", "price": "3", "category": "Minuman"},
        ])
        assert [it.name for it in mf.image_priority(drinks)] == ["Kopi O", "Teh Tarik"]

    def test_above_median_price_breaks_ties(self):
        menu = mf.normalize_items([
            {"name": "Mee Goreng", "price": "6", "category": "Mee"},
            {"name": "Nasi Goreng", "price": "7", "category": "Nasi"},
            {"name": "Nasi Ayam Penyet", "price": "15", "category": "Nasi"},
        ])
        assert [it.name for it in mf.image_priority(menu)][0] == "Mee Goreng"  # first category
        assert [it.name for it in mf.image_priority(menu)][1] == "Nasi Ayam Penyet"  # above median


class TestAttach:
    def test_generated_photos_reach_the_block(self, items):
        pairs = [
            ("Set Panglima Signature – Ayam Gepuk Telur Mata", "https://res.cloudinary.com/x/sig.png"),
            ("Set A – Ayam Gepuk", "https://res.cloudinary.com/x/a.png"),
        ]
        with_photos, n = mf.attach_item_images(items, pairs)
        assert n == 2
        block = mf.render_menu_block(with_photos, wa_digits="60126973105")
        assert block.count("<img ") == 2
        assert 'src="https://res.cloudinary.com/x/a.png" alt="Set A – Ayam Gepuk"' in block
        assert len([c for c, _ in _cards(block) if "bmf-text-only" in c]) == len(items) - 2
        # Inputs are not mutated.
        assert all(not it.image_url for it in items)

    def test_a_drink_photo_is_not_attached(self, items):
        _, n = mf.attach_item_images(items, [("Teh O Ice", "https://x/teh.png"), ("Fries", "https://x/f.png"), ("Sambal Extra", "https://x/s.png")])
        assert n == 0

    def test_budget_and_unknown_names(self, items):
        pairs = [("Set A – Ayam Gepuk", "https://x/a.png"), ("Nasi Kerabu", "https://x/k.png"), ("Set Udang Krispy", "https://x/u.png")]
        out, n = mf.attach_item_images(items, pairs, budget=1)
        assert n == 1 and [it.name for it in out if it.image_url] == ["Set A – Ayam Gepuk"]

    def test_merchant_own_photo_wins(self):
        menu = mf.normalize_items([{"name": "Set A", "price": "10", "category": "Set", "image_url": "https://x/own.png"}] * 1)
        out, n = mf.attach_item_images(menu, [("Set A", "https://x/gen.png")])
        assert n == 0 and out[0].image_url == "https://x/own.png"


class TestPipelineWiring:
    def test_enforce_menu_fidelity_uses_gallery_pairs(self, items):
        from types import SimpleNamespace
        from app.services.ai_service import AIService

        svc = AIService.__new__(AIService)
        svc._last_poster_uploads = ["https://x/board.png"]
        with open(FIXTURE, encoding="utf-8") as fh:
            raw = json.load(fh)["menu_items"]
        req = SimpleNamespace(
            menu_items=raw, description="Ayam gepuk", business_name="AGP", show_prices=True,
            uploaded_images=[{"url": "https://x/board.png", "name": "Set B – Ayam Gepuk Tauhu Tempe"}],
        )
        image_urls = {
            "hero": "https://x/hero.png",
            "gallery1": "https://x/sig.png", "gallery1_name": "Set Panglima Signature – Ayam Gepuk Telur Mata",
            "gallery2": "https://x/a.png", "gallery2_name": "Set A – Ayam Gepuk",
        }
        html = '<html><body><section id="menu"><h2>Menu</h2><div id="binaapp-menu-slot"></div></section><footer></footer></body></html>'
        out = svc._enforce_menu_fidelity(html, req, wa_digits="60126973105", image_urls=image_urls)
        assert 'src="https://x/sig.png"' in out and 'src="https://x/a.png"' in out
        assert "https://x/board.png" not in out  # a menu board is never an item photo
        assert "https://x/hero.png" not in out

    def test_images_off_keeps_text_only(self):
        from types import SimpleNamespace
        from app.services.ai_service import AIService

        svc = AIService.__new__(AIService)
        with open(FIXTURE, encoding="utf-8") as fh:
            raw = json.load(fh)["menu_items"]
        req = SimpleNamespace(menu_items=raw, description="", business_name="AGP", show_prices=True, uploaded_images=[])
        html = '<html><body><section id="menu"><div id="binaapp-menu-slot"></div></section></body></html>'
        out = svc._enforce_menu_fidelity(html, req, image_urls=None)
        assert "<img " not in out


@pytest.mark.asyncio
async def test_autofill_spends_the_budget_on_priority_items(monkeypatch):
    import app.services.ai_service as ai_service_module
    from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
    from app.services.ai_service import AIService

    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "false")
    monkeypatch.setattr(ai_service_module, "FREE_AI_IMAGES_PER_SITE", 6, raising=False)
    svc = AIService()
    svc.qwen_api_key = svc.zai_api_key = None
    svc.stability_api_key = "st-key"
    n_calls = []

    async def _gen(prompt, **kw):
        n_calls.append(prompt)
        return f"https://res.cloudinary.com/demo/image/upload/v1/{len(n_calls)}.jpg"

    svc._generate_image = _gen
    req = WebsiteGenerationRequest(
        description="Restoran ayam gepuk di Klang", language=Language.MALAY, business_name="AGP",
        business_type="food", subdomain="agp", whatsapp_number="0126973105",
        menu_items=[
            MenuItemInput(name="Teh O Ice", price="3", category="Minuman"),
            MenuItemInput(name="Sambal Extra", price="3", category="Tambahan"),
            MenuItemInput(name="Fries", price="5", category="Kid's Menu"),
            MenuItemInput(name="Set A – Ayam Gepuk", price="12.50", category="Set Ayam"),
            MenuItemInput(name="Set Panglima Signature", price="15.90", category="Set Ayam"),
            MenuItemInput(name="Set Udang Krispy", price="22.90", category="Set Seafood"),
        ],
    )
    image_urls = {}
    await svc._autofill_missing_images(req, image_urls, max_ai_images=6)
    names = [image_urls.get(f"gallery{i}_name") for i in range(1, 5)]
    assert names[:3] == ["Set Panglima Signature", "Set A – Ayam Gepuk", "Set Udang Krispy"]
    assert not {"Teh O Ice", "Sambal Extra", "Fries"} & set(names)
