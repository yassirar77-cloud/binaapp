"""
Phase 1 — Step 4/5 E2E test: hand-crafted Khulafa Bistro Design Brief
→ recipe_builder → html_renderer → valid HTML output.
"""

import pytest
from app.schemas.recipe import DesignBrief
from app.services.recipe_builder import build_recipe
from app.services.html_renderer import render_html


KHULAFA_BRIEF = {
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
        "social_media": {"instagram": "@khulafabistro", "facebook": "KhulafaBistroShahAlam"},
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
                "subheadline": "Resipi warisan nenek, dimasak dengan gaya masa kini untuk keluarga anda",
                "cta_text": "Lihat Menu",
                "cta_link": "#menu",
                "cta_secondary_text": "Tempah Meja",
                "cta_secondary_link": "https://wa.me/60173228899?text=Saya%20ingin%20tempah%20meja",
                "image_key": "hero",
            },
        },
        {
            "type": "about",
            "variant": "story",
            "content": {
                "heading": "Kisah Kami",
                "paragraphs": [
                    "Bermula dari dapur kecil di rumah pengasas kami, Khulafa Bistro lahir daripada cinta kepada masakan Melayu yang autentik.",
                    "Kami percaya makanan tradisional boleh dipersembahkan dengan cara baru tanpa mengorbankan rasa asli.",
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
                        "description": "Nasi kerabu dengan bunga telang, ulam segar, dan ikan bakar",
                        "price": "RM 18.90",
                        "image_key": "gallery_2",
                        "is_popular": True,
                    },
                    {
                        "name": "Rendang Burger",
                        "description": "Daging rendang juicy dalam roti brioche dengan sambal hijau",
                        "price": "RM 22.90",
                        "image_key": "gallery_3",
                        "is_popular": True,
                    },
                    {
                        "name": "Laksa Carbonara",
                        "description": "Spaghetti dalam kuah laksa krimi, udang segar, dan taburan kerisik",
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
            "type": "testimonial",
            "variant": "cards",
            "content": {
                "heading": "Apa Kata Pelanggan",
                "reviews": [
                    {"name": "Aisha R.", "text": "Rendang burger terbaik yang pernah saya rasa!", "rating": 5},
                    {"name": "Farid M.", "text": "Suasana cozy, sesuai untuk family dinner.", "rating": 5},
                    {"name": "Siti N.", "text": "Harga berpatutan untuk kualiti fusion macam ni.", "rating": 4},
                ],
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
                "map_query": "Khulafa Bistro Shah Alam",
                "email": "hello@khulafabistro.my",
            },
        },
        {
            "type": "footer",
            "variant": "brand",
            "content": {
                "business_name": "Khulafa Bistro",
                "tagline": "Citarasa Melayu Moden",
                "social_links": [
                    {"platform": "instagram", "url": "https://instagram.com/khulafabistro", "icon": "fa-brands fa-instagram"},
                    {"platform": "facebook", "url": "https://facebook.com/KhulafaBistroShahAlam", "icon": "fa-brands fa-facebook"},
                ],
                "copyright_year": 2026,
                "powered_by": True,
            },
        },
    ],
    "image_map": {
        "hero": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1200",
        "gallery_1": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800",
        "gallery_2": "https://images.unsplash.com/photo-1562967916-eb82221dfb44?w=800",
        "gallery_3": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800",
        "gallery_4": "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800",
    },
    "features": {
        "whatsapp": True,
        "google_map": True,
        "delivery_system": False,
        "gallery": True,
        "price_list": True,
        "operating_hours": True,
        "testimonials": True,
        "social_media": True,
    },
}


class TestAssemblerE2E:
    def test_brief_to_recipe(self):
        """DesignBrief → PageRecipe succeeds with correct structure."""
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)

        assert recipe.meta.title.startswith("Khulafa Bistro")
        assert recipe.theme.style_dna.value == "teh_tarik_warm"
        assert recipe.theme.colors.primary == "#C2410C"
        assert recipe.theme.fonts.heading == "Lora"
        assert len(recipe.sections) == 7
        assert recipe.sections[0].component == "HeroSplit"
        assert recipe.sections[1].component == "AboutStory"
        assert recipe.sections[2].component == "MenuGrid"
        assert recipe.sections[3].component == "GalleryMasonry"
        assert recipe.sections[4].component == "TestimonialCards"
        assert recipe.sections[5].component == "ContactSplit"
        assert recipe.sections[6].component == "FooterBrand"

    def test_nav_has_links(self):
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)

        assert recipe.nav.logo_text == "Khulafa Bistro"
        assert len(recipe.nav.links) >= 4
        assert recipe.nav.cta is not None
        assert "wa.me" in recipe.nav.cta.href

    def test_image_keys_resolved(self):
        """image_key references become image_url in recipe props."""
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)

        hero_props = recipe.sections[0].props
        assert "image_url" in hero_props
        assert hero_props["image_url"].startswith("https://")

        menu_props = recipe.sections[2].props
        assert "items" in menu_props
        assert menu_props["items"][0]["image_url"].startswith("https://")

    def test_recipe_to_html(self):
        """PageRecipe → HTML produces valid, complete HTML."""
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        # Structural checks
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert '<html lang="ms">' in html
        assert "<title>" in html
        assert "Khulafa Bistro" in html

    def test_html_contains_all_sections(self):
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        assert 'id="hero"' in html
        assert 'id="about"' in html
        assert 'id="menu"' in html
        assert 'id="gallery"' in html
        assert 'id="testimonials"' in html or 'id="testimonial"' in html
        assert 'id="contact"' in html
        assert 'id="footer"' in html

    def test_html_contains_theme_css(self):
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        assert "--color-primary: #C2410C" in html
        assert "--font-heading" in html
        assert "Lora" in html
        assert "Nunito" in html

    def test_html_contains_content(self):
        """Actual business content appears in the rendered HTML."""
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        assert "Masakan Melayu Fusion" in html
        assert "Nasi Kerabu Deconstructed" in html
        assert "RM 18.90" in html
        assert "Rendang Burger" in html
        assert "WhatsApp Kami" in html
        assert "wa.me/60173228899" in html
        assert "BinaApp" in html

    def test_html_has_tailwind_and_animations(self):
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        assert "tailwindcss" in html
        assert "font-awesome" in html
        # AOS replaced with custom IO observer (BINA-36-B)
        assert "aos@" not in html
        assert "AOS.init" not in html
        assert "data-reveal" in html
        assert "IntersectionObserver" in html
        assert "--reveal-easing" in html

    def test_html_has_nav(self):
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        assert "<nav" in html
        assert "Laman Utama" in html
        assert "Tentang" in html
        assert "Menu" in html
        assert "Hubungi" in html

    def test_html_has_mobile_menu(self):
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        assert "mobile-menu" in html
        assert "fa-bars" in html

    def test_html_size_reasonable(self):
        """Output should be well under 100KB for a standard site."""
        brief = DesignBrief(**KHULAFA_BRIEF)
        recipe = build_recipe(brief)
        html = render_html(recipe)

        size_kb = len(html.encode("utf-8")) / 1024
        assert size_kb < 50, f"HTML is {size_kb:.1f}KB — too large"
        assert size_kb > 3, f"HTML is {size_kb:.1f}KB — suspiciously small"


def test_write_sample_output(tmp_path):
    """Write sample HTML to file for manual inspection (not a real assertion test)."""
    brief = DesignBrief(**KHULAFA_BRIEF)
    recipe = build_recipe(brief)
    html = render_html(recipe)

    out = tmp_path / "khulafa_bistro.html"
    out.write_text(html, encoding="utf-8")
    print(f"\n📄 Sample HTML written to: {out}")
    print(f"   Size: {len(html):,} bytes ({len(html)/1024:.1f} KB)")
    assert out.exists()
