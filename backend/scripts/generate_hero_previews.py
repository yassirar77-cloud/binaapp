"""Generate preview HTML for each hero variant using Khulafa Bistro data."""
import sys
sys.path.insert(0, ".")

from app.schemas.recipe import DesignBrief
from app.services.recipe_builder import build_recipe
from app.services.html_renderer import render_html

# Base brief — same Khulafa Bistro data for all variants
BASE_BRIEF = {
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
    "cuisine_type": "malay_fusion",
    "specific_dishes": ["Nasi Kerabu Deconstructed", "Rendang Burger", "Laksa Carbonara"],
    "image_map": {},
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

# Shared hero content
HERO_CONTENT = {
    "headline": "Masakan Melayu Fusion di Hati Shah Alam",
    "subheadline": "Resipi warisan nenek, dimasak dengan gaya masa kini untuk keluarga anda",
    "cta_text": "Lihat Menu",
    "cta_link": "#menu",
    "cta_secondary_text": "Tempah Meja",
    "cta_secondary_link": "https://wa.me/60173228899?text=Saya%20ingin%20tempah%20meja",
    "image_key": "hero",
    "halal_certified": True,
}

# Rest-of-page sections (same across all hero previews)
REST_SECTIONS = [
    {
        "type": "about",
        "variant": "story",
        "content": {
            "heading": "Kisah Kami",
            "paragraphs": [
                "Bermula dari dapur kecil di rumah pengasas kami, Khulafa Bistro lahir daripada cinta kepada masakan Melayu yang autentik.",
                "Kami percaya makanan tradisional boleh dipersembahkan dengan cara baru tanpa mengorbankan rasa asli. Setiap hidangan kami diolah menggunakan rempah tumbuk segar dan bahan tempatan pilihan.",
            ],
            "image_key": "interior",
            "signature": "— Keluarga Khulafa, Pengasas",
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
                {"name": "Nasi Kerabu Deconstructed", "description": "Nasi kerabu dengan bunga telang, ulam segar, dan ikan bakar — disusun gaya moden", "price": "RM 18.90", "image_key": "menu_1", "is_popular": True},
                {"name": "Rendang Burger", "description": "Daging rendang juicy dalam roti brioche dengan acar jelatah dan sambal hijau", "price": "RM 22.90", "image_key": "menu_2", "is_popular": True},
                {"name": "Laksa Carbonara", "description": "Spaghetti dalam kuah laksa krimi, udang segar, dan taburan kerisik", "price": "RM 19.90"},
            ],
        },
    },
    {
        "type": "gallery",
        "variant": "masonry",
        "content": {
            "heading": "Suasana Kami",
            "subtitle": "Setiap sudut bercerita — dari dapur ke meja anda",
            "image_keys": ["gallery_1", "gallery_2", "gallery_3", "gallery_4"],
        },
    },
    {
        "type": "testimonial",
        "variant": "cards",
        "content": {
            "heading": "Apa Kata Pelanggan",
            "reviews": [
                {"name": "Aisha R.", "text": "Rendang burger terbaik yang pernah saya rasa! Anak-anak pun suka.", "rating": 5, "avatar_fallback": "Y.Ar"},
                {"name": "Farid M.", "text": "Suasana cozy, sesuai untuk family dinner. Laksa carbonara memang unik!", "rating": 5},
                {"name": "Siti N.", "text": "Harga berpatutan untuk kualiti fusion macam ni. Mesti datang lagi.", "rating": 4},
            ],
        },
    },
    {
        "type": "contact",
        "variant": "split",
        "content": {
            "heading": "Hubungi Kami",
            "whatsapp_cta": "WhatsApp Kami",
            "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, Shah Alam",
            "hours_structured": [
                {"day": "Selasa - Jumaat", "time": "11:00 pg - 10:00 mlm"},
                {"day": "Sabtu - Ahad", "time": "9:00 pg - 11:00 mlm"},
                {"day": "Isnin", "time": "Tutup"},
            ],
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
]

HERO_VARIANTS = [
    ("centered", "hero_centered"),
    ("fullscreen-image", "hero_fullscreen_image"),
    ("split-reverse", "hero_minimal_text"),
    ("asymmetric-card", "hero_asymmetric_card"),
]


def generate_variant(variant_key: str, filename: str) -> None:
    brief_dict = {
        **BASE_BRIEF,
        "sections": [
            {"type": "hero", "variant": variant_key, "content": HERO_CONTENT},
            *REST_SECTIONS,
        ],
    }
    brief = DesignBrief(**brief_dict)
    recipe = build_recipe(brief)
    html = render_html(recipe)

    out_path = f"../docs/previews/{filename}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  {filename}.html — {len(html):,} bytes")


if __name__ == "__main__":
    print("Generating hero variant previews...")
    for variant_key, filename in HERO_VARIANTS:
        generate_variant(variant_key, filename)
    print("Done! All 4 hero previews saved to docs/previews/")
