"""Generate preview HTML for all V2 variants — BINA-30 sprint batch.

Generates one HTML file per variant to docs/previews/[variant_name].html.
All use Khulafa Bistro test data. Run twice — md5 of outputs must match (determinism).

Usage:
    cd /home/yassir/binaapp && python -m backend.scripts.generate_v2_previews
    # or from backend/:
    python scripts/generate_v2_previews.py
"""
import sys
import os

# Support running from backend/ directory: python scripts/generate_v2_previews.py
# or from repo root: cd backend && python scripts/generate_v2_previews.py
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_script_dir)
sys.path.insert(0, _backend_dir)

from app.schemas.recipe import DesignBrief
from app.services.recipe_builder import build_recipe
from app.services.html_renderer import render_html

# ---------------------------------------------------------------------------
# Shared Khulafa Bistro test data
# ---------------------------------------------------------------------------

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
            "Terletak di jantung Shah Alam, kami menyediakan suasana selesa untuk keluarga menikmati hidangan berkualiti tinggi.",
        ],
        "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, 40000 Shah Alam, Selangor",
        "whatsapp": "60173228899",
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

HERO = {
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
}

FOOTER = {
    "type": "footer",
    "variant": "brand",
    "content": {
        "business_name": "Khulafa Bistro",
        "tagline": "Citarasa Melayu Moden",
        "social_links": [
            {"platform": "instagram", "url": "https://instagram.com/khulafabistro", "icon": "fa-brands fa-instagram"},
            {"platform": "facebook", "url": "https://facebook.com/KhulafaBistroShahAlam", "icon": "fa-brands fa-facebook"},
            {"platform": "whatsapp", "url": "https://wa.me/60173228899", "icon": "fa-brands fa-whatsapp"},
        ],
        "copyright_year": 2026,
        "powered_by": True,
    },
}

HOURS_STRUCTURED = [
    {"day": "Selasa - Jumaat", "time": "11:00 pg - 10:00 mlm"},
    {"day": "Sabtu", "time": "9:00 pg - 11:00 mlm"},
    {"day": "Ahad", "time": "9:00 pg - 11:00 mlm"},
    {"day": "Isnin", "time": "Tutup"},
]

MENU_ITEMS_FULL = [
    # Nasi & Lauk
    {"name": "Nasi Kerabu Deconstructed", "description": "Nasi kerabu dengan bunga telang, ulam segar, dan ikan bakar — disusun gaya moden", "price": "RM 18.90", "image_key": "menu_1", "is_popular": True, "category": "Nasi & Lauk"},
    {"name": "Rendang Burger", "description": "Daging rendang juicy dalam roti brioche dengan acar jelatah dan sambal hijau", "price": "RM 22.90", "image_key": "menu_2", "is_popular": True, "category": "Fusion"},
    {"name": "Laksa Carbonara", "description": "Spaghetti dalam kuah laksa krimi, udang segar, dan taburan kerisik", "price": "RM 19.90", "image_key": "menu_3", "category": "Fusion"},
    # Western
    {"name": "Nasi Lemak Bistro", "description": "Nasi lemak premium dengan ayam goreng rempah, telur separuh masak dan sambal hijau", "price": "RM 16.90", "image_key": "menu_1", "category": "Nasi & Lauk"},
    {"name": "Satay Khulafa 10pc", "description": "Satay daging pilihan dengan sos kacang istimewa dan ketupat palas", "price": "RM 14.90", "image_key": "menu_2", "category": "Pembuka Selera"},
    {"name": "Teh Tarik Creamy", "description": "Teh tarik tarikan barista dengan lapisan susu buih pekat", "price": "RM 5.90", "category": "Minuman"},
    {"name": "Es Cendol", "description": "Cendol pandan, santan segar, gula melaka — hidangan sejuk tradisional", "price": "RM 7.90", "category": "Manisan"},
]

REVIEWS = [
    {"name": "Siti Rahmah", "rating": 5, "text": "Rendang Burger adalah kombinasi terbaik yang pernah saya rasa! Daging rendang yang juicy dalam roti brioche lembut. Memang layak 5 bintang!"},
    {"name": "Ahmad Fadzil", "rating": 5, "text": "Suasana sangat selesa dan makanan sungguh sedap. Laksa Carbonara adalah pilihan kegemaran kami. Anak-anak pun suka sangat!"},
    {"name": "Noraini Hassan", "rating": 5, "text": "Servis pantas, makanan sedap, harga berpatutan. Kami datang hampir setiap minggu. Terima kasih Khulafa Bistro!"},
    {"name": "Rizwan Ismail", "rating": 4, "text": "Nasi Kerabu Deconstructed adalah masterpiece. Presentation cantik, rasa autentik. Akan datang lagi!"},
]

GALLERY_PARAGRAPHS = [
    "Setiap sudut Khulafa Bistro direka untuk keselesaan keluarga — dari sudut santai kanak-kanak hinggalah meja makan keluarga besar.",
    "Dapur terbuka kami membenarkan tetamu melihat penyediaan hidangan secara langsung — kesegaran bahan adalah janji kami.",
]

# ---------------------------------------------------------------------------
# Variant definitions — (output_filename, [section_specs])
# ---------------------------------------------------------------------------

VARIANTS = [
    # -----------------------------------------------------------------------
    # WEEK 1: Menu variants
    # -----------------------------------------------------------------------
    ("menu_grid_classic", [
        HERO,
        {
            "type": "menu",
            "variant": "grid",
            "content": {
                "heading": "Menu Istimewa",
                "subheading": "Hidangan fusion halal yang memukau selera",
                "source": "supabase",
                "fallback_items": MENU_ITEMS_FULL[:6],
            },
        },
        FOOTER,
    ]),

    ("menu_editorial_list", [
        HERO,
        {
            "type": "menu",
            "variant": "list",
            "content": {
                "heading": "Menu Kami",
                "subheading": "Hidangan autentik dengan sentuhan moden",
                "source": "supabase",
                "fallback_items": MENU_ITEMS_FULL,
            },
        },
        FOOTER,
    ]),

    ("menu_chef_picks", [
        HERO,
        {
            "type": "menu",
            "variant": "featured",
            "content": {
                "heading": "Pilihan Chef",
                "subheading": "Hidangan terbaik yang disyorkan oleh chef kami",
                "source": "supabase",
                "fallback_items": MENU_ITEMS_FULL[:4],
            },
        },
        FOOTER,
    ]),

    ("menu_category_tabs", [
        HERO,
        {
            "type": "menu",
            "variant": "categorized",
            "content": {
                "heading": "Menu Khulafa",
                "categories": ["Nasi & Lauk", "Fusion", "Pembuka Selera", "Minuman", "Manisan"],
                "source": "supabase",
                "fallback_items": MENU_ITEMS_FULL,
            },
        },
        FOOTER,
    ]),

    # -----------------------------------------------------------------------
    # WEEK 2: Gallery variants
    # -----------------------------------------------------------------------
    ("gallery_mosaic_asymmetric", [
        HERO,
        {
            "type": "gallery",
            "variant": "masonry",
            "content": {
                "heading": "Suasana Kami",
                "subtitle": "Setiap sudut bercerita — dari dapur ke meja anda",
                "image_keys": ["gallery_1", "gallery_2", "gallery_3", "gallery_4"],
            },
        },
        FOOTER,
    ]),

    ("gallery_carousel_immersive", [
        HERO,
        {
            "type": "gallery",
            "variant": "carousel",
            "content": {
                "heading": "Galeri Khulafa",
                "subtitle": "Jelajahi suasana dan hidangan istimewa kami",
                "image_keys": ["gallery_1", "gallery_2", "gallery_3", "gallery_4"],
            },
        },
        FOOTER,
    ]),

    ("gallery_grid_uniform", [
        HERO,
        {
            "type": "gallery",
            "variant": "grid",
            "content": {
                "heading": "Koleksi Gambar",
                "subtitle": "Hidangan dan suasana Khulafa Bistro",
                "image_keys": ["gallery_1", "gallery_2", "gallery_3", "gallery_4"],
            },
        },
        FOOTER,
    ]),

    ("gallery_story_scroll", [
        HERO,
        {
            "type": "gallery",
            "variant": "full-width",
            "content": {
                "heading": "Cerita di Sebalik Khulafa",
                "subtitle": "Dari dapur ke meja — kisah cinta kami dengan masakan",
                "image_keys": ["gallery_1", "interior", "gallery_2", "gallery_3"],
                "pull_quote": "Resipi nenek, sentuhan moden — itu falsafah kami",
                "paragraphs": [
                    # Opening — Khulafa origin, Datuk Abdul Wahith founding, family kitchen 2018
                    "Khulafa Bistro bermula di dapur keluarga Datuk Abdul Wahith pada tahun 2018 — seorang pengusaha Muslim yang percaya bahawa masakan terbaik lahir dari resipi yang diwarisi, bukan dari formula kilang. Setiap hidangan yang keluar dari dapur kami membawa cerita yang sama: cinta, tradisi, dan bahan-bahan segar yang dipilih sendiri.",
                    # Middle — ingredient sourcing
                    "Kami bekerjasama rapat dengan pembekal tempatan di Selangor untuk memastikan setiap bahan — dari beras basmati hinggalah rempah rendang — tiba segar setiap pagi. Dapur terbuka kami bukan sekadar rekaan; ia adalah janji ketelusan kepada setiap tetamu yang makan bersama kami.",
                    # Closing — expansion to Subang Jaya
                    "Kini, dengan cabang baharu di Subang Jaya, kami membawa rasa yang sama ke lebih ramai keluarga Malaysia. Khulafa bukan sekadar restoran — ia adalah tempat di mana setiap meja menjadi meja makan keluarga.",
                ],
            },
        },
        FOOTER,
    ]),

    # -----------------------------------------------------------------------
    # WEEK 3: Contact variants
    # -----------------------------------------------------------------------
    ("contact_split_map", [
        HERO,
        {
            "type": "contact",
            "variant": "split",
            "content": {
                "heading": "Hubungi Kami",
                "whatsapp_cta": "WhatsApp Kami",
                "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, Shah Alam",
                "hours_structured": HOURS_STRUCTURED,
                "show_map": True,
                "map_query": "Khulafa Bistro Shah Alam",
                "email": "hello@khulafabistro.my",
            },
        },
        FOOTER,
    ]),

    ("contact_form_centered", [
        HERO,
        {
            "type": "contact",
            "variant": "form",
            "content": {
                "heading": "Tempah Meja",
                "show_map": True,
                "map_query": "Khulafa Bistro Shah Alam",
                "whatsapp_message": "Salam, saya ingin membuat tempahan meja di Khulafa Bistro.",
            },
        },
        FOOTER,
    ]),

    ("contact_minimal_essential", [
        HERO,
        {
            "type": "contact",
            "variant": "simple",
            "content": {
                "heading": "Jumpa Kami",
                "whatsapp_cta": "WhatsApp Sekarang",
                "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, 40000 Shah Alam, Selangor",
                "hours_structured": HOURS_STRUCTURED,
                "whatsapp_message": "Salam Khulafa Bistro! Saya nak tanya...",
            },
        },
        FOOTER,
    ]),

    ("contact_card_overlay", [
        HERO,
        {
            "type": "contact",
            "variant": "cards",
            "content": {
                "heading": "Hubungi Kami",
                "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, Shah Alam",
                "hours_structured": HOURS_STRUCTURED,
                "whatsapp_cta": "WhatsApp Kami",
                "whatsapp_message": "Salam Khulafa Bistro!",
                "background_image_key": "interior",
            },
        },
        FOOTER,
    ]),

    # -----------------------------------------------------------------------
    # WEEK 3: Footer variants
    # -----------------------------------------------------------------------
    ("footer_minimal", [
        HERO,
        {
            "type": "footer",
            "variant": "minimal",
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
    ]),

    ("footer_rich", [
        HERO,
        {
            "type": "footer",
            "variant": "columns",
            "content": {
                "business_name": "Khulafa Bistro",
                "tagline": "Citarasa Melayu Moden untuk Seluruh Keluarga",
                "social_links": [
                    {"platform": "instagram", "url": "https://instagram.com/khulafabistro", "icon": "fa-brands fa-instagram"},
                    {"platform": "facebook", "url": "https://facebook.com/KhulafaBistroShahAlam", "icon": "fa-brands fa-facebook"},
                    {"platform": "tiktok", "url": "https://tiktok.com/@khulafabistro", "icon": "fa-brands fa-tiktok"},
                    {"platform": "whatsapp", "url": "https://wa.me/60173228899", "icon": "fa-brands fa-whatsapp"},
                ],
                "newsletter": True,
                "newsletter_cta": "Sertai",
                "link_columns": [
                    {"title": "Menu", "links": [
                        {"label": "Nasi & Lauk", "href": "#menu"},
                        {"label": "Fusion", "href": "#menu"},
                        {"label": "Minuman", "href": "#menu"},
                        {"label": "Manisan", "href": "#menu"},
                    ]},
                    {"title": "Tentang", "links": [
                        {"label": "Kisah Kami", "href": "#about"},
                        {"label": "Galeri", "href": "#gallery"},
                        {"label": "Ulasan", "href": "#testimonial"},
                    ]},
                    {"title": "Hubungi", "links": [
                        {"label": "Lokasi", "href": "#contact"},
                        {"label": "Tempahan", "href": "#contact"},
                        {"label": "WhatsApp", "href": "https://wa.me/60173228899"},
                    ]},
                ],
                "copyright_year": 2026,
                "powered_by": True,
            },
        },
    ]),

    # -----------------------------------------------------------------------
    # WEEK 4: Reviews variants
    # -----------------------------------------------------------------------
    ("reviews_carousel", [
        HERO,
        {
            "type": "testimonial",
            "variant": "slider",
            "content": {
                "heading": "Kata Pelanggan Kami",
                "reviews": REVIEWS,
            },
        },
        FOOTER,
    ]),

    ("reviews_pull_quote", [
        HERO,
        {
            "type": "testimonial",
            "variant": "quote",
            "content": {
                "heading": "Ulasan Pilihan",
                "reviews": REVIEWS[:1],
            },
        },
        FOOTER,
    ]),

    # -----------------------------------------------------------------------
    # WEEK 4: Hours variants
    # -----------------------------------------------------------------------
    ("hours_simple_table", [
        HERO,
        {
            "type": "hours",
            "variant": "simple-table",
            "content": {
                "heading": "Waktu Operasi",
                "hours_structured": HOURS_STRUCTURED,
            },
        },
        FOOTER,
    ]),

    ("hours_today_focus", [
        HERO,
        {
            "type": "hours",
            "variant": "today-focus",
            "content": {
                "heading": "Waktu Operasi",
                "status_text": "Kami Buka Sekarang",
                "status_sub": "Tutup pukul 10:00 malam",
                "is_open": True,
                "week_heading": "Waktu Operasi Mingguan",
                "hours_structured": HOURS_STRUCTURED,
            },
        },
        # Adjacent contact section — fills page, removes dead whitespace (BINA-33)
        {
            "type": "contact",
            "variant": "simple",
            "content": {
                "heading": "Jumpa Kami",
                "whatsapp_cta": "WhatsApp Sekarang",
                "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, 40000 Shah Alam, Selangor",
                "hours_structured": HOURS_STRUCTURED,
                "whatsapp_message": "Salam Khulafa Bistro! Saya nak tanya tentang waktu operasi.",
            },
        },
        FOOTER,
    ]),

    # -----------------------------------------------------------------------
    # WEEK 4: CTA variants
    # -----------------------------------------------------------------------
    ("cta_booking_prominent", [
        HERO,
        {
            "type": "cta",
            "variant": "booking-prominent",
            "content": {
                "headline": "Tempah Meja Sekarang",
                "subheadline": "Jangan lepas peluang menikmati hidangan terbaik kami — tempah awal untuk elak kecewa.",
            },
        },
        FOOTER,
    ]),

    ("cta_whatsapp_first", [
        HERO,
        {
            "type": "cta",
            "variant": "whatsapp-first",
            "content": {
                "headline": "Bercakap Terus dengan Kami",
                "subheadline": "Tempah meja, tanya menu, atau sebarang pertanyaan — kami sentiasa bersedia.",
                "whatsapp_message": "Salam Khulafa Bistro, saya nak tempah meja...",
                "hours_short": "Sel-Ahad 11pg-10mlm",
                "supporting_info": [
                    {"icon": "fa-solid fa-clock", "text": "Respon dalam 15 minit"},
                    {"icon": "fa-solid fa-calendar", "text": "Tempahan 24 jam lebih awal"},
                    {"icon": "fa-solid fa-users", "text": "Boleh tampung hingga 50 orang"},
                ],
            },
        },
        FOOTER,
    ]),
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate_variant(filename: str, sections: list) -> None:
    brief_dict = {**BASE_BRIEF, "sections": sections}
    brief = DesignBrief(**brief_dict)
    recipe = build_recipe(brief)
    html = render_html(recipe)

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = os.path.join(repo_root, "docs", "previews")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{filename}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ {filename}.html — {len(html):,} bytes")


if __name__ == "__main__":
    print(f"Generating {len(VARIANTS)} V2 variant previews...\n")
    errors = []
    for vname, vsections in VARIANTS:
        try:
            generate_variant(vname, vsections)
        except Exception as e:
            errors.append((vname, str(e)))
            print(f"  ✗ {vname} — ERROR: {e}")

    print(f"\n{'='*60}")
    if errors:
        print(f"DONE — {len(VARIANTS) - len(errors)}/{len(VARIANTS)} succeeded, {len(errors)} failed:")
        for name, err in errors:
            print(f"  FAILED: {name} → {err}")
    else:
        print(f"DONE — All {len(VARIANTS)} previews generated to docs/previews/")
    print(f"{'='*60}")
