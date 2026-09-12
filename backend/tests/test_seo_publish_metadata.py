"""SEO metadata the merchant can actually share.

Report items #9, #10 and #11: og:url and the JSON-LD node pointed at
preview.binaapp.my with no canonical link; the meta description was cut
mid-sentence; and the Restaurant node carried neither openingHours (for a
business whose own brief says "buka 24 jam") nor its menu.
"""

import json
import re

import pytest

from app.services.seo_metadata import (
    ALWAYS_OPEN_SPEC,
    META_DESCRIPTION_LIMIT,
    SeoMeta,
    build_json_ld,
    favicon_data_uri,
    finalize_published_seo,
    inject_seo_metadata,
    is_always_open,
    meta_description,
)

BRIEF = (
    "Nasi Kandar Daging Crystal buka 24 jam di Shah Alam. Kuah dimasak dua "
    "kali sehari dan customer datang jauh dari Klang dan KL khas untuk rasa "
    "kuah kami yang pekat."
)


class TestMetaDescription:
    def test_it_stops_at_a_sentence_not_mid_clause(self):
        out = meta_description(BRIEF)
        assert len(out) <= META_DESCRIPTION_LIMIT
        # The old cut landed on "...khas untuk" — a whole word, half a thought.
        assert not out.endswith("khas untuk")
        assert out.endswith("…") or out.endswith(".")

    def test_a_late_sentence_break_wins(self):
        text = "Satu ayat pendek yang cukup panjang untuk mengisi ruang meta. " + "x" * 200
        assert meta_description(text).endswith("meta.")

    def test_an_early_sentence_break_loses_to_a_word_break(self):
        # Cutting at "Ya." would throw away almost the whole description.
        text = "Ya. " + "perkataan " * 40
        out = meta_description(text)
        assert out.endswith("…") and len(out) > 20

    def test_short_text_is_returned_whole(self):
        assert meta_description("Pendek sahaja.") == "Pendek sahaja."

    def test_empty_is_empty(self):
        assert meta_description("") == ""
        assert meta_description(None) == ""

    def test_the_tag_uses_it(self):
        html = inject_seo_metadata(
            "<html><head></head><body></body></html>",
            SeoMeta(business_name="Crystal", description=BRIEF),
        )
        content = re.search(r'<meta name="description" content="([^"]*)"', html).group(1)
        assert len(content) <= META_DESCRIPTION_LIMIT + 1  # the ellipsis


class TestRestaurantSchema:
    META = SeoMeta(
        business_name="Nasi Kandar Daging Crystal",
        description=BRIEF,
        business_type="food",
        phone="60193456781",
        address="No.41 Jalan Kristal L7/L, 40000, Shah Alam",
        menu_items=[
            {"name": "Nasi Kandar Ayam", "price": "RM12", "category": "Nasi"},
            {"name": "Roti Canai", "price": "RM1.50", "category": "Roti"},
        ],
    )

    @pytest.fixture
    def node(self):
        return build_json_ld(self.META)

    def test_always_open_is_detected_from_the_brief(self):
        assert is_always_open("buka 24 jam")
        assert is_always_open("open 24 hours")
        assert is_always_open("24/7")
        assert not is_always_open("buka 8 pagi hingga 10 malam")

    def test_it_publishes_mo_su_00_00_23_59(self, node):
        assert node["openingHoursSpecification"] == [ALWAYS_OPEN_SPEC]

    def test_supplied_hours_beat_the_always_open_guess(self):
        meta = SeoMeta(
            business_name="X", description="buka 24 jam", business_type="food",
            operating_hours=[{"days": "Isnin - Jumaat", "hours": "8:00 pagi - 10:00 malam"}],
        )
        spec = build_json_ld(meta)["openingHoursSpecification"]
        assert spec[0]["opens"] == "08:00" and spec[0]["closes"] == "22:00"

    def test_the_menu_is_published(self, node):
        sections = node["hasMenu"]["hasMenuSection"]
        names = {s["name"] for s in sections}
        assert names == {"Nasi", "Roti"}
        item = sections[0]["hasMenuItem"][0]
        assert item["offers"]["priceCurrency"] == "MYR"

    def test_uncategorised_items_stay_flat(self):
        meta = SeoMeta(
            business_name="X", business_type="food",
            menu_items=[{"name": "Roti Canai", "price": "RM1.50"}],
        )
        assert build_json_ld(meta)["hasMenu"]["hasMenuItem"][0]["name"] == "Roti Canai"

    def test_an_unpriced_item_gets_no_invented_offer(self):
        meta = SeoMeta(
            business_name="X", business_type="food",
            menu_items=[{"name": "Special hari ini", "price": ""}],
        )
        assert "offers" not in build_json_ld(meta)["hasMenu"]["hasMenuItem"][0]

    def test_non_food_businesses_get_no_menu(self):
        meta = SeoMeta(
            business_name="X", business_type="salon",
            menu_items=[{"name": "Gunting", "price": "RM30"}],
        )
        assert "hasMenu" not in build_json_ld(meta)

    def test_telephone_comes_from_the_merchant(self, node):
        assert node["telephone"] == "60193456781"


class TestPublishFinalisation:
    GENERATED = (
        '<html><head><title>T</title>'
        '<style>:root{--primary-color:#1F3A2F}</style>'
        '<meta property="og:url" content="https://preview.binaapp.my">'
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Restaurant","name":"Oopoo",'
        '"url":"https://preview.binaapp.my"}</script>'
        "</head><body>hi</body></html>"
    )
    LIVE = "https://oopoo.binaapp.my"

    def _published(self, geo=None):
        return finalize_published_seo(self.GENERATED, self.LIVE, "Oopoo", geo)

    def test_the_preview_host_is_gone_everywhere(self):
        assert "preview.binaapp.my" not in self._published()

    def test_og_url_points_at_the_live_site(self):
        assert f'content="{self.LIVE}"' in self._published()

    def test_a_canonical_link_is_added(self):
        assert f'<link rel="canonical" href="{self.LIVE}">' in self._published()

    def test_the_json_ld_url_is_corrected(self):
        out = self._published()
        node = json.loads(re.search(r"ld\+json[^>]*>(.*?)</script>", out, re.S).group(1))
        assert node["url"] == self.LIVE

    def test_geo_is_published_when_the_address_geocoded(self):
        out = self._published({"lat": 3.0738, "lng": 101.5183})
        node = json.loads(re.search(r"ld\+json[^>]*>(.*?)</script>", out, re.S).group(1))
        assert node["geo"] == {
            "@type": "GeoCoordinates", "latitude": 3.0738, "longitude": 101.5183,
        }

    def test_no_geo_is_invented_when_geocoding_failed(self):
        out = self._published({"lat": None, "lng": None})
        assert '"geo"' not in out

    def test_a_favicon_and_theme_colour_are_added(self):
        out = self._published()
        assert '<link rel="icon"' in out
        assert '<meta name="theme-color" content="#1F3A2F">' in out

    def test_the_favicon_carries_the_first_letter(self):
        assert "%3EO%3C" in favicon_data_uri("Oopoo")

    def test_existing_tags_are_not_duplicated(self):
        once = self._published()
        twice = finalize_published_seo(once, self.LIVE, "Oopoo")
        assert twice == once
        assert twice.count("rel=\"canonical\"") == 1

    def test_an_empty_site_url_changes_nothing(self):
        assert finalize_published_seo(self.GENERATED, "") == self.GENERATED
