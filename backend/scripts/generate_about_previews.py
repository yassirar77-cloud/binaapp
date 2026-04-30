"""Generate preview HTML for each About variant using Khulafa Bistro data."""
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

# Shared hero section (same across all about previews)
HERO_SECTION = {
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
        "halal_certified": True,
    },
}

# About variant content — each variant uses different data from the spec
ABOUT_VARIANTS = {
    "story": {
        "heading": "Kisah Kami",
        "paragraphs": [
            "Bermula dari dapur kecil di rumah pengasas kami, Khulafa Bistro lahir daripada cinta kepada masakan Melayu yang autentik.",
            "Kami percaya makanan tradisional boleh dipersembahkan dengan cara baru tanpa mengorbankan rasa asli. Setiap hidangan kami diolah menggunakan rempah tumbuk segar dan bahan tempatan pilihan.",
        ],
        "image_key": "interior",
        "signature": "— Yassir Ar., Pengasas",
    },
    "stats": {
        "heading": "Khulafa Dalam Angka",
        "stats": [
            {"value": "5+", "label": "Tahun Pengalaman"},
            {"value": "200+", "label": "Menu Items"},
            {"value": "4.8/5", "label": "Rating Pelanggan"},
            {"value": "1,500+", "label": "Pelanggan Tetap"},
        ],
        "description": "Sejak 2018, Khulafa Bistro telah menjadi destinasi kegemaran keluarga di Shah Alam untuk menikmati masakan Melayu fusion yang autentik dan berkualiti.",
        "quote": "Resipi nenek, sentuhan moden — itu falsafah kami",
        "quote_author": "Yassir Ar., Pengasas",
    },
    "timeline": {
        "heading": "Sejarah Kami",
        "milestones": [
            {
                "year": "2018",
                "title": "Bermula dari Dapur Rumah",
                "description": "Khulafa Bistro bermula sebagai projek keluarga — memasak untuk jiran-jiran dan tempahan kecil sempena Hari Raya.",
                # Assorted kuih on steel tray — handcrafted home kitchen feel
                "image_url": "https://images.unsplash.com/photo-1617694455712-77ce4c1ce7b3?w=800&h=600&fit=crop&q=80",
            },
            {
                "year": "2020",
                "title": "Restoran Pertama di Shah Alam",
                "description": "Walaupun cabaran MCO, kami membuka pintu restoran pertama di Seksyen 7. Penghantaran menjadi tulang belakang perniagaan.",
                # Hawker serving plates — busy takeaway/shopfront context
                "image_url": "https://images.unsplash.com/photo-1751704316221-7e7e6887d0ed?w=800&h=600&fit=crop&q=80",
            },
            {
                "year": "2022",
                "title": "Sijil Halal JAKIM",
                "description": "Pencapaian yang membanggakan — pensijilan halal JAKIM diterima, mengukuhkan kepercayaan pelanggan kami.",
                # Rendang in bowl close-up — halal-certified dish detail
                "image_url": "https://images.unsplash.com/photo-1688084546323-fcd3f9d8389b?w=800&h=600&fit=crop&q=80",
            },
            {
                "year": "2024",
                "title": "Cawangan Ke-3 Dibuka",
                "description": "Alhamdulillah, cawangan ketiga di Subang Jaya dibuka — membawa citarasa Khulafa kepada lebih ramai keluarga Malaysia.",
                # Bright cafe interior with plants — modern restaurant
                "image_url": "https://images.unsplash.com/photo-1773927005455-8efc55a8d512?w=800&h=600&fit=crop&q=80",
            },
        ],
    },
    "cards": {
        "heading": "Mengapa Khulafa?",
        "subtitle": "Tiga nilai teras yang menjadi asas setiap hidangan kami",
        "cards": [
            {
                "icon": "fa-solid fa-certificate",
                "title": "100% Halal",
                "description": "Semua bahan dan proses penyediaan disahkan halal oleh JAKIM. Keluarga anda boleh makan dengan tenang.",
            },
            {
                "icon": "fa-solid fa-leaf",
                "title": "Bahan Segar Harian",
                "description": "Rempah ditumbuk setiap pagi. Sayur dan daging dibekalkan terus dari pembekal tempatan yang dipercayai.",
            },
            {
                "icon": "fa-solid fa-heart",
                "title": "Mesra Keluarga",
                "description": "Ruang permainan kanak-kanak, kerusi tinggi bayi, dan menu khas kecil-kecil — kami faham keperluan keluarga.",
            },
        ],
    },
}

# Rest-of-page sections (after about)
REST_SECTIONS = [
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

VARIANT_FILES = [
    ("story", "about_story"),
    ("stats", "about_stats"),
    ("timeline", "about_timeline"),
    ("cards", "about_cards"),
]


def generate_variant(variant_key: str, filename: str) -> None:
    about_content = ABOUT_VARIANTS[variant_key]
    brief_dict = {
        **BASE_BRIEF,
        "sections": [
            HERO_SECTION,
            {"type": "about", "variant": variant_key, "content": about_content},
            *REST_SECTIONS,
        ],
    }
    brief = DesignBrief(**brief_dict)
    recipe = build_recipe(brief)
    html = render_html(recipe)

    import os
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_path = os.path.join(repo_root, "docs", "previews", f"{filename}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  {filename}.html — {len(html):,} bytes")


if __name__ == "__main__":
    print("Generating About variant previews...")
    for variant_key, filename in VARIANT_FILES:
        generate_variant(variant_key, filename)
    print("Done! All 4 About previews saved to docs/previews/")
