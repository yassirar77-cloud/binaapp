"""
Tests for the product-aware deterministic menu-item fallback.

Bug 1 (bana): a goreng pisang stall ("Kedai jual goreng pisang dengan
macam-macam topping") generated a full Nasi Lemak / Ayam Goreng / Mee Goreng /
Roti Canai site whenever the DeepSeek item-name extraction failed —
_fallback_item_names padded with unrelated generic dishes, those names drove
the gallery image prompts, and the HTML prompt then said "USE EXACTLY AS
SPECIFIED". The fallback must stay ON-PRODUCT.

Bug 2 (Warung Kak Ropiah, P0): the same fallback shipped a live site whose
entire menu was the BUSINESS NAME permuted — "Kak Ropiah A0", "Set Kak Ropiah
A0", "Kak Ropiah A0 Combo", "Kak Ropiah A0 Istimewa" — because
_extract_product_phrase's "warung X" pattern captured the business name and
_fallback_item_names permuted it with Set/Combo/Istimewa qualifiers.

The contract is now GROUNDED-OR-NOTHING:
  - names come only from real dishes in the description, or from the shop's
    own product phrase (rejected when it overlaps the business name);
  - Set/Combo/Istimewa permutation and the generic Malaysian-dish pad are
    GONE — both fabricate items the merchant never listed;
  - the function may return FEWER than n names, or none, and callers render
    a placeholder section rather than invented items.
"""

import pytest

from app.services.ai_service import AIService


@pytest.fixture
def service():
    # __new__ skips __init__ network/key setup — the helpers under test are
    # pure functions of the description.
    return AIService.__new__(AIService)


class TestExtractProductPhrase:
    def test_jual_phrase(self, service):
        assert service._extract_product_phrase(
            "Kedai jual goreng pisang dengan macam-macam topping"
        ) == "goreng pisang"

    def test_menjual_phrase(self, service):
        assert service._extract_product_phrase(
            "kedai kami menjual burger ayam special"
        ) == "burger ayam special"

    def test_kedai_fallback_pattern(self, service):
        assert service._extract_product_phrase(
            "gerai keropok lekor di pantai"
        ) == "keropok lekor"

    def test_no_clue_returns_empty(self, service):
        assert service._extract_product_phrase(
            "Restoran makanan melayu tradisional"
        ) == ""

    def test_marketing_tail_cut_at_stopword(self, service):
        # "dengan" ends the phrase — the tail never leaks into the name.
        assert service._extract_product_phrase(
            "jual cendol dengan pelbagai pilihan"
        ) == "cendol"

    def test_colloquial_connectors_cut(self, service):
        # Real bana description shape: "ade macam2 toping nama ..." — the
        # colloquial "ade" must end the phrase, not join the product name.
        assert service._extract_product_phrase(
            "Kedai jual goreng pisang ade macam2 toping nama banana bro"
        ) == "goreng pisang"


class TestFallbackItemNames:
    def test_goreng_pisang_stall_stays_on_product(self, service):
        """The bana bug: every fallback name must be about goreng pisang."""
        names = service._fallback_item_names(
            "Kedai jual goreng pisang dengan macam-macam topping. Banana Bro.", 4
        )
        assert len(names) == 4
        assert all("Goreng Pisang" in n for n in names)
        assert "Nasi Lemak" not in names
        assert "Roti Canai" not in names

    def test_business_name_never_becomes_menu_items(self, service):
        """P0 regression: the exact Warung Kak Ropiah failure.

        'warung X' captured the business name; the permutation turned it into
        four confident menu cards on a published site.
        """
        desc = (
            "Warung Kak Ropiah A0 - warung nasi campur di Seksyen 13 Shah Alam. "
            "A0 MENU UTAMA. Masakan kampung harian."
        )
        names = service._fallback_item_names(desc, 4, business_name="Warung Kak Ropiah")
        for bad in (
            "Kak Ropiah A0", "Set Kak Ropiah A0",
            "Kak Ropiah A0 Combo", "Kak Ropiah A0 Istimewa",
        ):
            assert bad not in names, f"fabricated item resurfaced: {bad}"
        # Nothing derived from the business name at all.
        assert not any("ropiah" in n.lower() or "kak" in n.lower() for n in names)

    def test_product_phrase_rejected_when_it_is_the_business_name(self, service):
        assert service._extract_product_phrase(
            "Warung Kak Ropiah A0 - warung nasi campur",
            business_name="Warung Kak Ropiah",
        ) == ""

    def test_shop_named_after_its_dish_still_works(self, service):
        """Overlap with the business name is allowed when every overlapping
        token is real dish vocabulary — 'Nasi Lemak Ali' genuinely sells it."""
        assert service._extract_product_phrase(
            "Kedai nasi lemak panas setiap pagi",
            business_name="Nasi Lemak Ali",
        ) == "nasi lemak"

    def test_section_label_never_becomes_an_item(self, service):
        """'A0'/'B12' are source-brief section labels, never products."""
        assert service._extract_product_phrase(
            "warung a0 masakan kampung", business_name="Warung Sedap"
        ) == ""

    def test_no_set_combo_istimewa_permutation(self, service):
        names = service._fallback_item_names("kedai kami menjual burger", 4)
        assert names == ["Burger"], names
        for n in names:
            assert not n.startswith("Set ")
            assert "Combo" not in n and "Istimewa" not in n

    def test_topping_signal_gives_topping_variants(self, service):
        names = service._fallback_item_names(
            "Kedai jual goreng pisang dengan macam-macam topping", 4
        )
        # Base + topping variants, not Set/Combo qualifiers.
        assert names[0] == "Goreng Pisang"
        assert any("Coklat" in n for n in names)

    def test_no_variant_signal_returns_the_product_only(self, service):
        """Without a variant signal the shop's product is the ONLY grounded
        name — we return one item, not four invented qualifiers."""
        names = service._fallback_item_names("kedai kami menjual burger", 4)
        assert names == ["Burger"]

    def test_no_clue_returns_nothing(self, service):
        """Replaces test_no_clue_keeps_generic_pad.

        An uninformative description used to yield a full fabricated
        Malaysian menu. Inventing a menu for a business we know nothing about
        is the P0 defect; returning nothing (→ placeholder section) is correct.
        """
        assert service._fallback_item_names("Restoran makanan melayu", 4) == []

    def test_named_dishes_still_win(self, service):
        names = service._fallback_item_names(
            "Warung nasi lemak dan ayam goreng viral", 4
        )
        assert names[0] == "Nasi Lemak"
        assert "Ayam Goreng" in names
        # Pad stays on the first found dish, not unrelated generics.
        assert "Roti Canai" not in names

    def test_at_most_n_nonempty_unique_never_raises(self, service):
        """Replaces test_exactly_n_nonempty_unique — the contract is now
        AT MOST n (possibly zero), but every returned name must still be a
        clean, unique, non-empty string and the call must never raise."""
        for desc in (
            "Kedai jual goreng pisang dengan macam-macam topping",
            "kedai menjual burger",
            "Restoran makanan melayu",
            "",
        ):
            names = service._fallback_item_names(desc, 4, business_name="Kedai Test")
            assert len(names) <= 4
            assert all(isinstance(n, str) and n.strip() for n in names)
            assert len(set(names)) == len(names)

    def test_extract_menu_items_knows_goreng_pisang(self, service):
        found = service._extract_menu_items("Kedai jual goreng pisang sedap")
        assert "goreng pisang" in found
