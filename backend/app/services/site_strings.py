"""
String table for every UI string a generated site carries, keyed by the
page's ``<html lang>``.

The generator used to write nav labels, button text and footer lines ad hoc
in whichever language the model felt like, so a Bahasa site could ship an
"Order Now" button and an English site a "Hubungi Kami" heading. Every UI
string now comes from this table — the HTML prompt renders the table for
the chosen language and the model copies from it; the linter can then check
the page against the same table.

Copy the merchant wrote (name, story, item names, prices) is never
translated or touched — this table is UI chrome only.
"""

from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    "ms": {
        "nav_home": "Utama",
        "nav_menu": "Menu",
        "nav_products": "Produk",
        "nav_collection": "Koleksi",
        "nav_services": "Servis",
        "nav_about": "Tentang",
        "nav_location": "Lokasi",
        "nav_contact": "Hubungi",
        "nav_book": "Tempah",
        "cta_order_whatsapp": "Pesan di WhatsApp",
        "cta_chat_whatsapp": "WhatsApp Kami",
        "cta_view_menu": "Lihat menu",
        "cta_view_products": "Lihat produk",
        "cta_view_collection": "Lihat koleksi",
        "cta_view_services": "Lihat servis",
        "cta_book": "Tempah sekarang",
        "cta_call": "Telefon",
        "cta_full_menu": "Menu penuh",
        "cta_open_maps": "Buka di Google Maps",
        "cta_order_item": "Pesan",
        "heading_menu": "Menu",
        "heading_featured": "Pilihan Kami",
        "heading_about": "Tentang Kami",
        "heading_location": "Lokasi & Waktu",
        "heading_hours": "Waktu Operasi",
        "heading_contact": "Hubungi Kami",
        "heading_gallery": "Galeri",
        "heading_collection": "Koleksi",
        "heading_sizes_delivery": "Saiz & Penghantaran",
        "heading_how_to_order": "Cara Order",
        "heading_services_prices": "Servis & Harga",
        "heading_book": "Tempah Slot",
        "heading_our_work": "Galeri Kerja",
        "heading_services": "Perkhidmatan",
        "heading_areas": "Kawasan Liputan",
        "heading_testimonials": "Testimoni",
        "heading_products": "Produk",
        "label_address": "Alamat",
        "label_price": "Harga",
        "label_payment": "Cara bayaran",
        "payment_cod": "Bayar semasa terima (COD)",
        "payment_qr": "QR / Bayaran online",
        "footer_rights": "Hak cipta terpelihara",
        "footer_built_with": "Dibina dengan BinaApp",
        "delivery_available": "Penghantaran tersedia",
        "pickup_available": "Ambil sendiri",
        "menu_placeholder_heading": "Menu Akan Datang",
        "menu_placeholder_body": "Menu penuh akan dikemas kini tidak lama lagi. Hubungi kami untuk pertanyaan.",
        "wa_prefill": "Assalamualaikum, saya nak pesan",
    },
    "en": {
        "nav_home": "Home",
        "nav_menu": "Menu",
        "nav_products": "Products",
        "nav_collection": "Collection",
        "nav_services": "Services",
        "nav_about": "About",
        "nav_location": "Location",
        "nav_contact": "Contact",
        "nav_book": "Book",
        "cta_order_whatsapp": "Order on WhatsApp",
        "cta_chat_whatsapp": "WhatsApp us",
        "cta_view_menu": "View menu",
        "cta_view_products": "View products",
        "cta_view_collection": "View collection",
        "cta_view_services": "View services",
        "cta_book": "Book now",
        "cta_call": "Call",
        "cta_full_menu": "Full menu",
        "cta_open_maps": "Open in Google Maps",
        "cta_order_item": "Order",
        "heading_menu": "Menu",
        "heading_featured": "Our Picks",
        "heading_about": "About Us",
        "heading_location": "Location & Hours",
        "heading_hours": "Opening Hours",
        "heading_contact": "Contact Us",
        "heading_gallery": "Gallery",
        "heading_collection": "Collection",
        "heading_sizes_delivery": "Sizes & Delivery",
        "heading_how_to_order": "How to Order",
        "heading_services_prices": "Services & Prices",
        "heading_book": "Book a Slot",
        "heading_our_work": "Our Work",
        "heading_services": "Services",
        "heading_areas": "Areas Served",
        "heading_testimonials": "Testimonials",
        "heading_products": "Products",
        "label_address": "Address",
        "label_price": "Price",
        "label_payment": "Payment",
        "payment_cod": "Cash on delivery (COD)",
        "payment_qr": "QR / Online payment",
        "footer_rights": "All rights reserved",
        "footer_built_with": "Built with BinaApp",
        "delivery_available": "Delivery available",
        "pickup_available": "Self pickup",
        "menu_placeholder_heading": "Menu Coming Soon",
        "menu_placeholder_body": "Our full menu is being updated. Contact us for enquiries.",
        "wa_prefill": "Hi, I would like to order",
    },
}


def strings_for(language: str) -> Dict[str, str]:
    lang = "en" if str(language or "").lower().startswith("en") else "ms"
    return dict(STRINGS[lang])


def string_table_block(language: str, keys=None) -> str:
    """The table as the HTML prompt renders it."""
    table = strings_for(language)
    lang = "en" if str(language or "").lower().startswith("en") else "ms"
    rows = [f"  {k}: \"{v}\"" for k, v in table.items() if not keys or k in keys]
    return (
        f"===== UI STRING TABLE (html lang=\"{lang}\") — COPY THESE EXACTLY =====\n"
        "Every navigation label, button, heading and footer line on the page comes from this table. "
        "Do not translate, paraphrase or mix languages. The merchant's own copy (name, story, item names, prices) is never translated.\n"
        + "\n".join(rows)
    )
