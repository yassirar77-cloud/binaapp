"""P0 regression suite — menu-data integrity in the generation prompt.

Built from the Warung Kak Ropiah incident: a full F&B brief (25+ priced items,
catering packages, split hours, halal status) produced a published site whose
menu was four cards named by permuting the business name — "Kak Ropiah A0",
"Set Kak Ropiah A0", "Kak Ropiah A0 Combo", "Kak Ropiah A0 Istimewa" — with
every supplied price missing.

Root cause: item names for the gallery image slots were manufactured by
_fallback_item_names (business-name capture + Set/Combo/Istimewa permutation),
written to image_urls["gallery{i}_name"], and then injected into the HTML
prompt as "USE EXACTLY AS SPECIFIED / COPY EXACTLY - DO NOT MODIFY" — which
outranked the real menu sitting in the description. There was no structured
menu input at all, so prices had no channel to travel through.

These tests pin the three guarantees that fix:
  1. supplied menu_items reach the prompt VERBATIM (names + prices);
  2. with nothing grounded, the prompt asks for a PLACEHOLDER and forbids
     deriving items from the business name;
  3. no placeholder WhatsApp number is ever injected.
"""

import pytest

from app.services.ai_service import AIService


@pytest.fixture
def service():
    # __new__ skips __init__ network/key setup — the prompt builder is a pure
    # function of its arguments.
    return AIService.__new__(AIService)


KAK_ROPIAH_DESC = (
    "Warung Kak Ropiah A0 - warung nasi campur di Seksyen 13 Shah Alam. "
    "A0 MENU UTAMA. Masakan kampung harian, resipi arwah ibu."
)

KAK_ROPIAH_ITEMS = [
    {"name": "Nasi Campur Biasa", "price": "RM7.00"},
    {"name": "Ayam Masak Merah", "price": "RM5.50"},
    {"name": "Gulai Nangka", "price": "RM4.00"},
    {"name": "Sambal Sotong", "price": "RM6.50"},
    {"name": "Pakej Katering A", "price": "RM18/pax", "category": "Katering"},
    {"name": "Pakej Katering B", "price": "RM28/pax", "category": "Katering"},
    {"name": "Pakej Katering C", "price": "RM42/pax", "category": "Katering"},
]

FABRICATED = [
    "Kak Ropiah A0",
    "Set Kak Ropiah A0",
    "Kak Ropiah A0 Combo",
    "Kak Ropiah A0 Istimewa",
]


def _prompt(service, **kw):
    params = dict(
        name="Warung Kak Ropiah",
        desc=KAK_ROPIAH_DESC,
        style="modern",
        language="ms",
        whatsapp_number="0193456781",
        image_choice="ai",
        images={"hero": "https://cdn.test/hero.jpg"},
    )
    params.update(kw)
    return service._build_strict_prompt(**params)


class TestSuppliedMenuDataIsVerbatim:
    def test_every_item_name_and_price_reaches_the_prompt(self, service):
        p = _prompt(service, menu_items=KAK_ROPIAH_ITEMS)
        for item in KAK_ROPIAH_ITEMS:
            assert item["name"] in p, f"missing item name: {item['name']}"
            assert item["price"] in p, f"missing price: {item['price']}"

    def test_all_items_render_not_just_the_four_with_images(self, service):
        """The old pipeline capped the menu at the 4 image slots."""
        p = _prompt(service, menu_items=KAK_ROPIAH_ITEMS)
        assert "Pakej Katering C" in p and "RM42/pax" in p
        assert f"these {len(KAK_ROPIAH_ITEMS)} item(s)" in p

    def test_prices_are_not_reformatted(self, service):
        p = _prompt(service, menu_items=[{"name": "Set Ikan", "price": "RM18/pax"}])
        assert "RM18/pax" in p
        # No rounding/normalising into a plain decimal.
        assert "RM18.00" not in p

    def test_prompt_forbids_renaming_and_inventing(self, service):
        p = _prompt(service, menu_items=KAK_ROPIAH_ITEMS)
        assert "SOURCE OF TRUTH" in p
        assert "Copy each NAME character-for-character" in p
        assert "Copy each PRICE character-for-character" in p
        assert "Do NOT add any item that is not in this list." in p
        assert 'qualifiers like "Set", "Combo", "Istimewa"' in p

    def test_item_without_price_is_told_to_omit_not_guess(self, service):
        p = _prompt(service, menu_items=[{"name": "Air Suam"}])
        assert "omit the price element for this item" in p

    def test_supplied_items_survive_model_objects(self, service):
        """The API layer passes MenuItemInput models, not dicts."""
        from app.models.schemas import MenuItemInput
        items = [MenuItemInput(name="Nasi Campur Biasa", price="RM7.00")]
        p = _prompt(service, menu_items=items)
        assert "Nasi Campur Biasa" in p and "RM7.00" in p

    def test_malformed_items_do_not_break_generation(self, service):
        p = _prompt(service, menu_items=[
            {"name": "Nasi Campur", "price": "RM7.00"},
            {"name": "   "},          # blank name — dropped
            {"price": "RM9.00"},      # no name — dropped
            None,                     # junk — dropped
        ])
        assert "Nasi Campur" in p
        assert "these 1 item(s)" in p


class TestNoMenuDataRendersPlaceholder:
    def test_placeholder_requested_when_nothing_is_known(self, service):
        p = _prompt(service, menu_items=None)
        assert "RENDER A PLACEHOLDER" in p
        assert "DO NOT invent" in p

    def test_prompt_bans_business_name_derived_items(self, service):
        p = _prompt(service, menu_items=None)
        assert "NEVER derive an item name from the business name" in p
        # The exact incident is spelled out for the model.
        assert "Set Kak Ropiah" in p and "must NEVER produce items" in p

    def test_no_fabricated_card_is_mandated_to_the_model(self, service):
        """The fabricated names must never appear as COPY-EXACTLY titles."""
        p = _prompt(service, menu_items=None)
        for bad in FABRICATED:
            assert f'Title: "{bad}"' not in p

    def test_supplied_items_suppress_the_placeholder(self, service):
        p = _prompt(service, menu_items=KAK_ROPIAH_ITEMS)
        assert "RENDER A PLACEHOLDER" not in p

    def test_extracted_slot_names_suppress_the_placeholder(self, service):
        """Real dishes read from the description still drive named cards."""
        p = _prompt(
            service,
            menu_items=None,
            images={"hero": "https://cdn.test/h.jpg",
                    "gallery1": "https://cdn.test/g1.jpg",
                    "gallery1_name": "Nasi Lemak"},
        )
        assert "RENDER A PLACEHOLDER" not in p


class TestNoPlaceholderPhoneNumber:
    def test_missing_number_emits_no_wa_link(self, service):
        p = _prompt(service, whatsapp_number=None)
        assert "60123456789" not in p
        assert "wa.me/" not in p
        assert "NONE AVAILABLE" in p

    def test_known_dummy_number_is_rejected(self, service):
        p = _prompt(service, whatsapp_number="60123456789")
        assert "wa.me/60123456789" not in p
        assert "NONE AVAILABLE" in p

    def test_real_number_still_works(self, service):
        p = _prompt(service, whatsapp_number="0193456781")
        assert "wa.me/60193456781" in p
        assert "NONE AVAILABLE" not in p

    @pytest.mark.parametrize("raw,expected", [
        ("0193456781", "60193456781"),
        ("+60 19-345 6781", "60193456781"),
        ("60123456789", ""),      # the pipeline's own old default
        ("0123456789", ""),       # classic example number
        ("60111111111", ""),      # repeated-digit dummy
        ("123", ""),              # too short
        (None, ""),
        ("", ""),
    ])
    def test_normalizer_contract(self, service, raw, expected):
        assert service._normalize_wa_digits(raw) == expected
