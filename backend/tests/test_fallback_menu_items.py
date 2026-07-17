"""
Tests for the product-aware deterministic menu-item fallback.

Bug: a goreng pisang stall ("Kedai jual goreng pisang dengan macam-macam
topping") generated a full Nasi Lemak / Ayam Goreng / Mee Goreng / Roti Canai
site whenever the DeepSeek item-name extraction failed — _fallback_item_names
padded with unrelated generic dishes, those names drove the gallery image
prompts, and the HTML prompt then said "USE EXACTLY AS SPECIFIED". The
fallback must stay ON-PRODUCT whenever the description says what the shop
sells, and only use the generic Malaysian-dish pad when there is no clue.
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

    def test_topping_signal_gives_topping_variants(self, service):
        names = service._fallback_item_names(
            "Kedai jual goreng pisang dengan macam-macam topping", 4
        )
        # Base + topping variants, not Set/Combo qualifiers.
        assert names[0] == "Goreng Pisang"
        assert any("Coklat" in n for n in names)

    def test_no_variant_signal_uses_neutral_qualifiers(self, service):
        names = service._fallback_item_names("kedai kami menjual burger", 4)
        assert len(names) == 4
        assert all("Burger" in n for n in names)
        assert "Nasi Lemak" not in names

    def test_no_clue_keeps_generic_pad(self, service):
        """Graceful degradation is preserved: an uninformative description
        still yields a full plausible Malaysian menu, never blanks."""
        names = service._fallback_item_names("Restoran makanan melayu", 4)
        assert names == ["Nasi Lemak", "Ayam Goreng", "Mee Goreng", "Roti Canai"]

    def test_named_dishes_still_win(self, service):
        names = service._fallback_item_names(
            "Warung nasi lemak dan ayam goreng viral", 4
        )
        assert names[0] == "Nasi Lemak"
        assert "Ayam Goreng" in names
        # Pad stays on the first found dish, not unrelated generics.
        assert "Roti Canai" not in names

    def test_exactly_n_nonempty_unique(self, service):
        for desc in (
            "Kedai jual goreng pisang dengan macam-macam topping",
            "kedai menjual burger",
            "Restoran makanan melayu",
            "",
        ):
            names = service._fallback_item_names(desc, 4)
            assert len(names) == 4
            assert all(isinstance(n, str) and n.strip() for n in names)
            assert len(set(names)) == 4

    def test_extract_menu_items_knows_goreng_pisang(self, service):
        found = service._extract_menu_items("Kedai jual goreng pisang sedap")
        assert "goreng pisang" in found
