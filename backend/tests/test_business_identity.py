"""A site is never named by a fallback — see services/business_identity.py."""

import pytest

from app.services.business_identity import (
    derive_business_name,
    is_generic_business_name,
    missing_name_message,
    resolve_business_name,
)
from app.services.generation_validator import GenerationBrief, validate_generated_site


class TestGenericNames:
    @pytest.mark.parametrize("name", [
        "", "   ", "Kedai", "kedai", "Restoran", "Business", "My Business",
        "Kedai Kami", "Kedai Saya", "Warung", "Untitled", "Nama Kedai",
    ])
    def test_bare_type_nouns_are_generic(self, name):
        assert is_generic_business_name(name)

    @pytest.mark.parametrize("name", [
        "Kedai Pak Mat", "Nasi Kandar Daging Crystal", "Warung Kak Ropiah",
        "Oopoo", "Restoran Seri Melayu", "Kedai A", "Kedai 2",
    ])
    def test_names_with_a_distinguisher_are_real(self, name):
        assert not is_generic_business_name(name)

    def test_a_place_is_not_an_identity(self):
        # Deriving "Shah Alam" from "gerai di Shah Alam" would name the shop
        # after the town it stands in.
        assert is_generic_business_name("Shah Alam")
        assert is_generic_business_name("Kedai Kuala Lumpur")


class TestDerivation:
    def test_reads_a_leading_title_case_name(self):
        assert derive_business_name(
            "Nasi Kandar Daging Crystal, kedai mamak buka 24 jam di Shah Alam"
        ) == "Nasi Kandar Daging Crystal"

    def test_reads_an_explicit_marker(self):
        assert derive_business_name(
            "nama kedai saya ialah Warung Kak Ropiah, jual nasi lemak"
        ) == "Warung Kak Ropiah"

    def test_reads_a_quoted_name(self):
        assert derive_business_name('Business name: "Crystal Bites". Burgers.') == "Crystal Bites"

    def test_capitalises_a_lowercase_type_noun(self):
        assert derive_business_name("kedai Pak Mat di Klang, jual roti canai") == "Kedai Pak Mat"

    def test_returns_empty_rather_than_guessing(self):
        # Prose with no name in it must yield nothing — a plausible-looking
        # guess is the defect, not the fix.
        assert derive_business_name("kami jual nasi lemak sedap di shah alam") == ""
        assert derive_business_name("") == ""

    def test_does_not_name_the_shop_after_its_town(self):
        assert derive_business_name("Saya buka gerai di Shah Alam") == ""


class TestResolution:
    def test_merchant_name_wins(self):
        assert resolve_business_name("Restoran Oopoo", "anything at all") == "Restoran Oopoo"

    def test_generic_typed_name_falls_through_to_the_brief(self):
        assert resolve_business_name(
            "Kedai", "nama kedai saya ialah Warung Kak Ropiah"
        ) == "Warung Kak Ropiah"

    def test_nothing_usable_means_empty_not_a_placeholder(self):
        assert resolve_business_name(None, "jual makanan sedap") == ""
        assert resolve_business_name("Kedai", "jual makanan sedap") == ""

    def test_message_is_localised(self):
        assert "Nama kedai wajib" in missing_name_message("ms")
        assert "required" in missing_name_message("en").lower()


class TestValidatorCatchesItOnThePage:
    """The model can invent a generic name even when handed a real one."""

    BRIEF = GenerationBrief(business_name="Nasi Kandar Crystal")

    def _codes(self, html):
        return {e.code for e in validate_generated_site(html, self.BRIEF).errors}

    def test_generic_h1_blocks(self):
        html = '<html><body><h1>Kedai</h1><a href="https://wa.me/60193456781">W</a></body></html>'
        assert "generic_business_name" in self._codes(html)

    def test_generic_json_ld_name_blocks(self):
        html = (
            '<html><head><script type="application/ld+json">'
            '{"@type":"Restaurant","name":"Kedai"}</script></head>'
            '<body><h1>Nasi Kandar Crystal</h1>'
            '<a href="https://wa.me/60193456781">W</a></body></html>'
        )
        assert "generic_business_name" in self._codes(html)

    def test_a_real_name_passes(self):
        html = (
            '<html><head><title>Nasi Kandar Crystal | Mamak</title></head>'
            '<body><h1>Nasi Kandar Crystal</h1>'
            '<a href="https://wa.me/60193456781">W</a></body></html>'
        )
        assert "generic_business_name" not in self._codes(html)
