"""P2 technical fixes from the generation-defect audit.

  - No Open Graph tags: Malaysian SMEs share by pasting the link into
    WhatsApp, which rendered as a bare URL.
  - No JSON-LD: generated sites were invisible to local search.
  - Widget data-primary-color="#1f2937" (grey) on a #B91C1C red site.
  - data-business-type="general" on an F&B site.
  - Two WhatsApp implementations: an English floating button on a Malay page
    alongside Malay menu CTAs.
  - alt text derived from a fabricated item name; images reused across slots.
"""

import json
import re

import pytest

from app.services.ai_service import AIService, extract_theme_tokens
from app.services.seo_metadata import (
    SeoMeta,
    build_json_ld,
    build_meta_tags,
    inject_seo_metadata,
)
from app.services.templates import TemplateService, resolve_widget_primary_color


@pytest.fixture
def service():
    return AIService.__new__(AIService)


FULL_META = SeoMeta(
    business_name="Warung Kak Ropiah",
    description="Warung nasi campur masakan kampung di Seksyen 13 Shah Alam.",
    subdomain="kakropiah",
    site_url="https://kakropiah.binaapp.my",
    hero_image="https://cdn.test/hero.jpg",
    address="Seksyen 13, Shah Alam, Selangor",
    phone="60193456781",
    language="ms",
    business_type="food",
    menu_items=[
        {"name": "Nasi Campur Biasa", "price": "RM7.00"},
        {"name": "Pakej Katering C", "price": "RM42/pax"},
    ],
    operating_hours=[
        {"days": "Isnin - Khamis", "hours": "7:00 pagi - 4:00 petang"},
        {"days": "Jumaat",
         "hours": ["7:00 pagi - 12:00 tgh", "2:30 petang - 4:00 petang"]},
    ],
)


class TestOpenGraphTags:
    def test_all_four_required_og_tags_present(self):
        tags = build_meta_tags(FULL_META)
        for prop in ("og:title", "og:description", "og:image", "og:url"):
            assert f'property="{prop}"' in tags, prop

    def test_meta_description_within_160_chars(self):
        long_meta = SeoMeta(business_name="X", description="lorem ipsum " * 40)
        tags = build_meta_tags(long_meta)
        content = re.search(r'name="description" content="([^"]*)"', tags).group(1)
        assert len(content) <= 160

    def test_twitter_card_matches_image_availability(self):
        assert 'content="summary_large_image"' in build_meta_tags(FULL_META)
        no_image = SeoMeta(business_name="X", description="y")
        assert 'content="summary"' in build_meta_tags(no_image)

    def test_no_og_image_tag_when_there_is_no_image(self):
        tags = build_meta_tags(SeoMeta(business_name="X", description="y"))
        assert "og:image" not in tags

    def test_locale_follows_language(self):
        assert 'content="ms_MY"' in build_meta_tags(FULL_META)
        en = SeoMeta(business_name="X", description="y", language="en")
        assert 'content="en_MY"' in build_meta_tags(en)

    def test_attribute_values_are_escaped(self):
        meta = SeoMeta(business_name='Kedai "Best" & Co', description="a<b>c")
        tags = build_meta_tags(meta)
        assert '&quot;Best&quot;' in tags and "&amp;" in tags
        assert "<b>" not in tags


class TestJsonLd:
    def test_restaurant_schema_for_food(self):
        node = build_json_ld(FULL_META)
        assert node["@type"] == "Restaurant"
        assert node["@context"] == "https://schema.org"
        assert node["name"] == "Warung Kak Ropiah"
        assert node["servesCuisine"] == "Malaysian"

    def test_address_and_phone_from_supplied_data(self):
        node = build_json_ld(FULL_META)
        assert node["address"]["streetAddress"] == "Seksyen 13, Shah Alam, Selangor"
        assert node["address"]["addressCountry"] == "MY"
        assert node["telephone"] == "60193456781"

    def test_price_range_derived_from_supplied_prices(self):
        assert build_json_ld(FULL_META)["priceRange"] == "RM7 - RM42"

    def test_no_price_range_without_prices(self):
        meta = SeoMeta(business_name="X", business_type="food",
                       menu_items=[{"name": "Nasi"}])
        assert "priceRange" not in build_json_ld(meta)

    def test_split_friday_yields_two_opening_specs(self):
        """The P1-2 hours work must reach structured data too."""
        spec = build_json_ld(FULL_META)["openingHoursSpecification"]
        fridays = [s for s in spec if s["dayOfWeek"] == ["Friday"]]
        assert len(fridays) == 2
        assert {"07:00", "14:30"} == {f["opens"] for f in fridays}

    def test_day_range_expands(self):
        spec = build_json_ld(FULL_META)["openingHoursSpecification"]
        weekday = next(s for s in spec if "Monday" in s["dayOfWeek"])
        assert weekday["dayOfWeek"] == ["Monday", "Tuesday", "Wednesday", "Thursday"]

    def test_nothing_invented_when_data_is_absent(self):
        node = build_json_ld(SeoMeta(business_name="Kuih Mak Ngah"))
        for absent in ("address", "telephone", "priceRange",
                       "openingHoursSpecification", "image"):
            assert absent not in node

    def test_none_without_a_business_name(self):
        assert build_json_ld(SeoMeta()) is None

    @pytest.mark.parametrize("biz,expected", [
        ("food", "Restaurant"), ("cafe", "CafeOrCoffeeShop"),
        ("bakery", "Bakery"), ("salon", "BeautySalon"),
        ("clinic", "MedicalClinic"), ("general", "LocalBusiness"),
        ("unknown-type", "LocalBusiness"),
    ])
    def test_schema_type_by_business(self, biz, expected):
        assert build_json_ld(SeoMeta(business_name="X", business_type=biz))["@type"] == expected

    def test_emitted_json_ld_is_parseable(self):
        out = inject_seo_metadata("<html><head></head><body></body></html>", FULL_META)
        block = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', out, re.DOTALL
        ).group(1)
        assert json.loads(block)["name"] == "Warung Kak Ropiah"


class TestInjection:
    def test_injects_into_head(self):
        out = inject_seo_metadata("<html><head><title></title></head><body></body></html>",
                                  FULL_META)
        head = out[:out.lower().index("</head>")]
        assert "og:title" in head and "ld+json" in head

    def test_idempotent(self):
        once = inject_seo_metadata("<html><head></head><body></body></html>", FULL_META)
        twice = inject_seo_metadata(once, FULL_META)
        assert twice.count("og:title") == 1
        assert twice.count("application/ld+json") == 1

    def test_existing_title_is_preserved(self):
        html = "<html><head><title>Menu Terbaik Shah Alam</title></head><body></body></html>"
        assert "Menu Terbaik Shah Alam" in inject_seo_metadata(html, FULL_META)

    def test_empty_title_is_replaced(self):
        html = "<html><head><title>  </title></head><body></body></html>"
        out = inject_seo_metadata(html, FULL_META)
        assert "Warung Kak Ropiah" in re.search(
            r"<title>(.*?)</title>", out, re.DOTALL
        ).group(1)

    def test_no_head_still_injects(self):
        out = inject_seo_metadata("<body><h1>X</h1></body>", FULL_META)
        assert "og:title" in out

    def test_empty_html_untouched(self):
        assert inject_seo_metadata("", FULL_META) == ""

    def test_wired_into_generation(self, service):
        from app.models.schemas import WebsiteGenerationRequest

        request = WebsiteGenerationRequest(
            description="warung nasi campur di shah alam",
            business_name="Warung Kak Ropiah",
            subdomain="kakropiah",
            whatsapp_number="0193456781",
            location_address="Seksyen 13, Shah Alam",
            menu_items=[{"name": "Nasi Campur", "price": "RM7.00"}],
        )
        out = service._inject_seo_metadata(
            "<html><head></head><body><h1>Warung Kak Ropiah</h1></body></html>",
            request,
            {"hero": "https://cdn.test/h.jpg"},
        )
        assert 'content="https://kakropiah.binaapp.my"' in out
        assert '"@type":"Restaurant"' in out.replace(" ", "")


class TestWidgetTheming:
    def test_tailwind_config_primary_is_read(self):
        """The key is quoted in the emitted config ('primary': '#B91C1C');
        the old pattern required an unquoted key so it never matched and
        every widget fell back to grey."""
        html = ("<script>tailwind.config={theme:{extend:{colors:"
                "{'primary':'#B91C1C','secondary':'#7F1D1D'}}}}</script>")
        assert extract_theme_tokens(html)["primary"] == "#B91C1C"

    def test_widget_uses_the_site_colour_not_grey(self):
        html = ("<script>tailwind.config={theme:{extend:{colors:"
                "{'primary':'#B91C1C'}}}}</script>")
        assert resolve_widget_primary_color(html).lower() == "#b91c1c"

    def test_css_variable_form_still_works(self):
        assert extract_theme_tokens("<style>:root{--primary:#123456}</style>")["primary"] == "#123456"

    def test_grey_fallback_only_when_nothing_found(self):
        assert resolve_widget_primary_color("<html><body>x</body></html>") == "#1f2937"


class TestWhatsAppUnification:
    def test_malay_is_the_default(self):
        msg = TemplateService.whatsapp_default_message("ms")
        assert "saya berminat" in msg.lower()

    def test_english_when_page_is_english(self):
        assert "interested" in TemplateService.whatsapp_default_message("en").lower()

    def test_unspecified_language_defaults_to_malay(self):
        assert TemplateService.whatsapp_default_message(None) == \
            TemplateService.whatsapp_default_message("ms")

    def test_floating_button_no_longer_hardcodes_english(self):
        import inspect
        from app.services import templates as templates_module

        source = inspect.getsource(templates_module.TemplateService.inject_whatsapp_button)
        assert "Hi, I'm interested" not in source


class TestAltTextAndImageReuse:
    def _prompt(self, service):
        return service._build_strict_prompt(
            name="Warung Kak Ropiah",
            desc="warung nasi campur",
            style="modern",
            language="ms",
            whatsapp_number="0193456781",
            image_choice="ai",
            images={"hero": "https://cdn.test/h.jpg",
                    "gallery1": "https://cdn.test/g1.jpg"},
        )

    def test_alt_rules_present(self, service):
        p = self._prompt(service)
        assert "IMAGE ALT TEXT" in p
        assert 'FORBIDDEN alt values' in p

    def test_hero_alt_is_a_token_not_the_word_hero(self, service):
        from app.services.design_system import HERO_VARIANTS, HERO_VARIANTS_NO_IMAGES
        blob = " ".join(list(HERO_VARIANTS.values()) + list(HERO_VARIANTS_NO_IMAGES.values()))
        assert 'alt="Hero"' not in blob
        p = self._prompt(service)
        assert "HERO_ALT_TEXT" in p

    def test_image_reuse_rules_cover_hero_and_about(self, service):
        p = self._prompt(service)
        assert "IMAGE REUSE — EACH PHOTO APPEARS ONCE" in p
        flat = " ".join(p.split())
        assert "never reuse it in an about section" in flat
        assert "OMIT that image or the whole section" in flat


class TestContactSlotFallback:
    def test_generator_is_told_to_fill_the_slot(self):
        from app.services.widget_catalogue import (
            build_prompt_context_block,
            widgets_for_request,
        )

        block = build_prompt_context_block(
            widgets_for_request(
                include_whatsapp=True,
                include_contact=True,
                include_maps=True,
                include_ecommerce=False,
            ),
            primary_color="#B91C1C",
        )
        assert "data-binaapp-fallback" in block
        assert "A slot MUST NOT be empty" in block

    def test_serve_time_script_is_fallback_aware(self):
        from app.middleware.subdomain import _CONTACT_SLOT_FALLBACK_SCRIPT

        assert "data-binaapp-fallback" in _CONTACT_SLOT_FALLBACK_SCRIPT
        # A real widget clears the static fallback; fallback alone is kept.
        assert "realChildren" in _CONTACT_SLOT_FALLBACK_SCRIPT
