"""
Phase 1 — Step 1 validation: construct Design Brief + Page Recipe for
Khulafa Bistro and verify roundtrip through Pydantic.
"""

import json
import pytest
from app.schemas.recipe import (
    DesignBrief,
    PageRecipe,
    SectionSpec,
    SectionType,
    StyleDNA,
    FeatureFlags,
    resolve_component_name,
    VALID_VARIANTS,
)
from app.schemas.style_dna import get_style_dna, STYLE_DNAS


# ---------------------------------------------------------------------------
# Fixture: Khulafa Bistro Design Brief (hand-crafted, as if AI produced it)
# ---------------------------------------------------------------------------

KHULAFA_BRIEF_JSON = {
    "$schema": "design_brief_v1",
    "version": "1.0",
    "language": "ms",
    "business": {
        "name": "Khulafa Bistro",
        "type": "restaurant",
        "tagline": "Citarasa Melayu Moden untuk Seluruh Keluarga",
        "about": [
            "Khulafa Bistro menghidangkan masakan Melayu fusion yang menggabungkan resipi tradisional dengan sentuhan moden.",
            "Terletak di jantung Shah Alam, kami menyediakan suasana selesa untuk keluarga menikmati hidangan halal berkualiti tinggi.",
        ],
        "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, 40000 Shah Alam, Selangor",
        "whatsapp": "017-3228899",
        "email": "hello@khulafabistro.my",
        "social_media": {
            "instagram": "@khulafabistro",
            "facebook": "KhulafaBistroShahAlam",
        },
        "operating_hours": "Selasa - Ahad, 11:00 pagi - 10:00 malam. Isnin tutup.",
    },
    "style_dna": "teh_tarik_warm",
    "color_mode": "light",
    "sections": [
        {
            "type": "hero",
            "variant": "split",
            "content": {
                "headline": "Masakan Melayu Fusion di Hati Shah Alam",
                "subheadline": "Resipi warisan nenek, dimasak dengan gaya masa kini",
                "cta_text": "Lihat Menu",
                "cta_link": "#menu",
                "image_key": "hero",
            },
        },
        {
            "type": "about",
            "variant": "story",
            "content": {
                "heading": "Kisah Kami",
                "paragraphs": [
                    "Bermula dari dapur kecil, Khulafa Bistro lahir daripada cinta kepada masakan Melayu autentik.",
                    "Setiap hidangan diolah menggunakan rempah tumbuk segar dan bahan tempatan pilihan.",
                ],
                "image_key": "gallery_1",
            },
        },
        {
            "type": "menu",
            "variant": "grid",
            "content": {
                "heading": "Menu Istimewa",
                "subheading": "Hidangan fusion halal yang memukau",
                "source": "supabase",
                "fallback_items": [
                    {
                        "name": "Nasi Kerabu Deconstructed",
                        "description": "Nasi kerabu dengan bunga telang dan ulam segar",
                        "price": "RM 18.90",
                        "image_key": "gallery_2",
                        "is_popular": True,
                    },
                    {
                        "name": "Rendang Burger",
                        "description": "Daging rendang dalam roti brioche dengan sambal hijau",
                        "price": "RM 22.90",
                        "image_key": "gallery_3",
                        "is_popular": True,
                    },
                    {
                        "name": "Laksa Carbonara",
                        "description": "Spaghetti dalam kuah laksa krimi dengan udang segar",
                        "price": "RM 19.90",
                    },
                ],
            },
        },
        {
            "type": "gallery",
            "variant": "masonry",
            "content": {
                "heading": "Suasana Kami",
                "image_keys": ["gallery_1", "gallery_2", "gallery_3", "gallery_4"],
            },
        },
        {
            "type": "contact",
            "variant": "split",
            "content": {
                "heading": "Hubungi Kami",
                "whatsapp_cta": "WhatsApp Kami",
                "address_display": "No. 12, Jalan Plumbum V7/V, Seksyen 7, Shah Alam",
                "hours": "Selasa - Ahad, 11 pagi - 10 malam",
                "show_map": True,
            },
        },
        {
            "type": "footer",
            "variant": "brand",
            "content": {
                "business_name": "Khulafa Bistro",
                "tagline": "Citarasa Melayu Moden",
                "copyright_year": 2026,
                "powered_by": True,
            },
        },
    ],
    "image_map": {
        "hero": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/hero.jpg",
        "gallery_1": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/interior.jpg",
        "gallery_2": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/nasi-kerabu.jpg",
        "gallery_3": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/rendang-burger.jpg",
        "gallery_4": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/laksa.jpg",
    },
    "features": {
        "whatsapp": True,
        "google_map": True,
        "delivery_system": False,
        "gallery": True,
        "price_list": True,
        "operating_hours": True,
        "testimonials": False,
        "social_media": True,
    },
}


# ---------------------------------------------------------------------------
# Tests: DesignBrief
# ---------------------------------------------------------------------------


class TestDesignBrief:
    def test_khulafa_parses(self):
        brief = DesignBrief(**KHULAFA_BRIEF_JSON)
        assert brief.business.name == "Khulafa Bistro"
        assert brief.style_dna == StyleDNA.teh_tarik_warm
        assert len(brief.sections) == 6

    def test_whatsapp_normalised(self):
        brief = DesignBrief(**KHULAFA_BRIEF_JSON)
        assert brief.business.whatsapp == "60173228899"

    def test_roundtrip_json(self):
        brief = DesignBrief(**KHULAFA_BRIEF_JSON)
        dumped = json.loads(brief.model_dump_json(by_alias=True))
        reparsed = DesignBrief(**dumped)
        assert reparsed.business.name == brief.business.name
        assert len(reparsed.sections) == len(brief.sections)

    def test_missing_hero_fails(self):
        data = {**KHULAFA_BRIEF_JSON}
        data["sections"] = [s for s in data["sections"] if s["type"] != "hero"]
        with pytest.raises(Exception, match="hero"):
            DesignBrief(**data)

    def test_missing_footer_fails(self):
        data = {**KHULAFA_BRIEF_JSON}
        data["sections"] = [s for s in data["sections"] if s["type"] != "footer"]
        with pytest.raises(Exception, match="footer"):
            DesignBrief(**data)

    def test_invalid_variant_fails(self):
        data = {**KHULAFA_BRIEF_JSON}
        bad_sections = list(data["sections"])
        bad_sections[0] = {**bad_sections[0], "variant": "nonexistent"}
        data["sections"] = bad_sections
        with pytest.raises(Exception, match="invalid"):
            DesignBrief(**data)

    def test_bad_image_key_fails(self):
        data = {**KHULAFA_BRIEF_JSON}
        bad_sections = list(data["sections"])
        bad_sections[0] = {
            **bad_sections[0],
            "content": {**bad_sections[0]["content"], "image_key": "nonexistent_img"},
        }
        data["sections"] = bad_sections
        with pytest.raises(Exception, match="nonexistent_img"):
            DesignBrief(**data)

    def test_no_images_mode(self):
        """image_map can be empty — 'no images' mode."""
        data = {**KHULAFA_BRIEF_JSON}
        data["image_map"] = {}
        # Remove image refs from content
        new_sections = []
        for s in data["sections"]:
            content = {k: v for k, v in s["content"].items()
                       if k not in ("image_key", "image_keys")}
            if "fallback_items" in content:
                content["fallback_items"] = [
                    {k: v for k, v in it.items() if k != "image_key"}
                    for it in content["fallback_items"]
                ]
            new_sections.append({**s, "content": content})
        data["sections"] = new_sections
        brief = DesignBrief(**data)
        assert brief.image_map == {}

    def test_invalid_style_dna_fails(self):
        data = {**KHULAFA_BRIEF_JSON, "style_dna": "bubble_gum"}
        with pytest.raises(Exception):
            DesignBrief(**data)


# ---------------------------------------------------------------------------
# Tests: PageRecipe
# ---------------------------------------------------------------------------

KHULAFA_RECIPE_JSON = {
    "$schema": "page_recipe_v1",
    "version": "1.0",
    "meta": {
        "title": "Khulafa Bistro | Masakan Melayu Fusion di Shah Alam",
        "description": "Citarasa Melayu Moden untuk Seluruh Keluarga.",
        "language": "ms",
        "og_image": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/hero.jpg",
    },
    "theme": {
        "style_dna": "teh_tarik_warm",
        "fonts": {
            "heading": "Lora",
            "heading_weight": "700",
            "body": "Nunito",
            "body_weight": "400",
            "cdn_url": "https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap",
        },
        "colors": {
            "primary": "#C2410C",
            "primary_hover": "#9A3412",
            "secondary": "#78350F",
            "accent": "#FED7AA",
            "background": "#FFFBF5",
            "surface": "#FFFFFF",
            "text": "#1C1917",
            "text_muted": "#78716C",
            "border": "rgba(194,65,12,0.1)",
            "gradient_from": "#C2410C",
            "gradient_to": "#78350F",
        },
        "component_styles": {
            "button_primary": "bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200",
            "button_secondary": "border-2 border-[var(--color-primary)] text-[var(--color-primary)] font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200",
            "card": "bg-[var(--color-surface)] rounded-3xl shadow-md hover:shadow-lg transition-shadow duration-200",
            "nav": "bg-white/90 backdrop-blur-xl shadow-sm fixed top-0 w-full z-50",
            "section_padding": "py-20 px-4 sm:px-6 lg:px-8",
        },
    },
    "nav": {
        "logo_text": "Khulafa Bistro",
        "links": [
            {"label": "Laman Utama", "href": "#hero"},
            {"label": "Tentang", "href": "#about"},
            {"label": "Menu", "href": "#menu"},
            {"label": "Hubungi", "href": "#contact"},
        ],
        "cta": {"label": "Tempah Meja", "href": "https://wa.me/60173228899"},
    },
    "sections": [
        {
            "id": "hero",
            "component": "HeroSplit",
            "props": {
                "headline": "Masakan Melayu Fusion di Hati Shah Alam",
                "subheadline": "Resipi warisan nenek, dimasak dengan gaya masa kini",
                "cta_text": "Lihat Menu",
                "cta_link": "#menu",
                "image_url": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/hero.jpg",
                "image_alt": "Khulafa Bistro",
            },
            "animation": {"type": "fade-up", "delay": 0},
        },
        {
            "id": "about",
            "component": "AboutStory",
            "props": {
                "heading": "Kisah Kami",
                "paragraphs": [
                    "Bermula dari dapur kecil, Khulafa Bistro lahir daripada cinta kepada masakan Melayu autentik.",
                ],
                "image_url": "https://example.supabase.co/storage/v1/object/public/websites/khulafa/interior.jpg",
            },
            "animation": {"type": "fade-up", "delay": 100},
        },
        {
            "id": "footer",
            "component": "FooterBrand",
            "props": {"business_name": "Khulafa Bistro", "powered_by": True},
            "animation": {"type": "fade-up", "delay": 0},
        },
    ],
    "head_assets": [
        "https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap",
        "https://unpkg.com/aos@2.3.4/dist/aos.css",
        "https://cdn.tailwindcss.com",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
    ],
    "tailwind_config": {
        "theme": {
            "extend": {
                "colors": {
                    "primary": "var(--color-primary)",
                    "secondary": "var(--color-secondary)",
                },
                "fontFamily": {
                    "heading": ["Lora", "serif"],
                    "body": ["Nunito", "sans-serif"],
                },
            }
        }
    },
    "body_scripts": ["https://unpkg.com/aos@2.3.4/dist/aos.js"],
    "init_scripts": ["AOS.init({ duration: 800, once: true, offset: 100 });"],
}


class TestPageRecipe:
    def test_khulafa_parses(self):
        recipe = PageRecipe(**KHULAFA_RECIPE_JSON)
        assert recipe.meta.title.startswith("Khulafa")
        assert len(recipe.sections) == 3

    def test_roundtrip_json(self):
        recipe = PageRecipe(**KHULAFA_RECIPE_JSON)
        dumped = json.loads(recipe.model_dump_json(by_alias=True))
        reparsed = PageRecipe(**dumped)
        assert reparsed.sections[0].component == "HeroSplit"

    def test_needs_at_least_2_sections(self):
        data = {**KHULAFA_RECIPE_JSON}
        data["sections"] = [data["sections"][0]]
        with pytest.raises(Exception):
            PageRecipe(**data)


# ---------------------------------------------------------------------------
# Tests: Component name resolution
# ---------------------------------------------------------------------------


class TestComponentResolution:
    def test_hero_split(self):
        assert resolve_component_name("hero", "split") == "HeroSplit"

    def test_menu_grid(self):
        assert resolve_component_name("menu", "grid") == "MenuGrid"

    def test_gallery_full_width(self):
        assert resolve_component_name("gallery", "full-width") == "GalleryFullWidth"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown variant"):
            resolve_component_name("hero", "banana")


# ---------------------------------------------------------------------------
# Tests: Style DNA registry
# ---------------------------------------------------------------------------


class TestStyleDNA:
    def test_all_8_registered(self):
        assert len(STYLE_DNAS) == 8

    def test_lookup_teh_tarik(self):
        dna = get_style_dna("teh_tarik_warm")
        assert dna.heading_font == "Lora"
        assert dna.mode == "light"

    def test_lookup_kopi_hitam_dark(self):
        dna = get_style_dna("kopi_hitam")
        assert dna.mode == "dark"

    def test_unknown_raises(self):
        with pytest.raises(KeyError):
            get_style_dna("nonexistent")

    def test_all_dnas_have_required_fields(self):
        for key, dna in STYLE_DNAS.items():
            assert dna.primary, f"{key} missing primary"
            assert dna.heading_font, f"{key} missing heading_font"
            assert dna.font_cdn.startswith("https://"), f"{key} bad font_cdn"
            assert dna.button_primary, f"{key} missing button_primary"
