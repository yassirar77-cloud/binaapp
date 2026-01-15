"""
Business Type Configuration Module

This module provides dynamic configuration for different business types.
Instead of hardcoding food-specific categories and labels, the system
detects the business type and applies appropriate configurations.

Business Types:
- food: Restaurants, cafes, food stalls (Nasi, Lauk, Minuman)
- clothing: Butik, fashion, clothing stores (Baju, Tudung, Aksesori)
- services: Service providers (Perkhidmatan, Pakej)
- general: General stores, other businesses (Produk, Lain-lain)
"""

from typing import Dict, List, Tuple
import re
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# BUSINESS TYPE CONFIGURATIONS
# ============================================================================

BUSINESS_CONFIGS = {
    "food": {
        "button_label": "🛵 Pesan Delivery",
        "button_label_en": "🛵 Order Delivery",
        "order_emoji": "🍛",
        "order_title": "PESANAN DELIVERY",
        "order_title_en": "DELIVERY ORDER",
        "page_title": "Pesan Delivery",
        "page_title_en": "Order Delivery",
        "categories": [
            {"id": "nasi", "name": "🍚 Nasi", "name_en": "🍚 Rice", "icon": "🍚"},
            {"id": "lauk", "name": "🍗 Lauk", "name_en": "🍗 Dishes", "icon": "🍗"},
            {"id": "minuman", "name": "🥤 Minuman", "name_en": "🥤 Drinks", "icon": "🥤"},
        ],
        "default_category": "lauk",
        "category_keywords": {
            "nasi": ["nasi", "rice", "briyani", "naan", "roti"],
            "lauk": ["ayam", "chicken", "ikan", "fish", "daging", "meat", "sayur", "vegetable", "sambal", "curry"],
            "minuman": ["air", "minuman", "drink", "juice", "tea", "teh", "kopi", "coffee", "smoothie", "jus"],
        },
        "item_description_default": "Hidangan istimewa dari dapur kami",
        "item_description_default_en": "Special dish from our kitchen",
        "whatsapp_closing": "Sila nyatakan alamat penuh. Terima kasih! 🙏",
        "whatsapp_closing_en": "Please provide your full address. Thank you! 🙏",
        "primary_color": "#ea580c",
        "features": {
            "delivery_zones": True,
            "time_slots": True,
            "special_instructions": True,
            "promo_code": True,
            "size_options": False,
            "color_options": False,
            "appointment_date": False,
            "staff_selection": False,
            "shipping_options": False,
            "custom_message": False,
        },
    },
    "clothing": {
        "button_label": "🛍️ Beli Sekarang",
        "button_label_en": "🛍️ Buy Now",
        "order_emoji": "👗",
        "order_title": "PESANAN BARU",
        "order_title_en": "NEW ORDER",
        "page_title": "Beli Sekarang",
        "page_title_en": "Buy Now",
        "categories": [
            {"id": "baju", "name": "👗 Baju", "name_en": "👗 Clothes", "icon": "👗"},
            {"id": "tudung", "name": "🧕 Tudung", "name_en": "🧕 Hijab", "icon": "🧕"},
            {"id": "aksesori", "name": "👜 Aksesori", "name_en": "👜 Accessories", "icon": "👜"},
        ],
        "default_category": "baju",
        "category_keywords": {
            "baju": ["baju", "kurung", "kebaya", "dress", "blouse", "shirt", "kemeja", "pants", "seluar", "skirt", "jubah", "abaya"],
            "tudung": ["tudung", "hijab", "shawl", "scarf", "headscarf", "selendang", "bawal", "instant"],
            "aksesori": ["aksesori", "accessory", "bag", "beg", "handbag", "wallet", "dompet", "belt", "tali", "jewelry", "anting", "gelang", "rantai", "brooch", "pin", "kasut", "shoes"],
        },
        "item_description_default": "Koleksi pilihan berkualiti tinggi",
        "item_description_default_en": "High quality selected collection",
        "whatsapp_closing": "Sila nyatakan saiz dan alamat penuh. Terima kasih! 🙏",
        "whatsapp_closing_en": "Please provide size and full address. Thank you! 🙏",
        "primary_color": "#ec4899",
        "features": {
            "delivery_zones": False,
            "time_slots": False,
            "special_instructions": True,
            "promo_code": True,
            "size_options": True,
            "color_options": True,
            "appointment_date": False,
            "staff_selection": False,
            "shipping_options": True,
            "custom_message": False,
        },
        "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
        "shipping_options": [
            {"id": "cod", "name": "COD (Cash on Delivery)", "price": 8, "desc": "Bayar bila terima"},
            {"id": "jnt", "name": "J&T Express", "price": 6, "desc": "2-3 hari bekerja"},
            {"id": "pos", "name": "Pos Laju", "price": 7, "desc": "1-2 hari bekerja"},
            {"id": "pickup", "name": "Self Pickup", "price": 0, "desc": "Ambil di kedai"},
        ],
    },
    "salon": {
        "button_label": "📅 Tempah Sekarang",
        "button_label_en": "📅 Book Now",
        "order_emoji": "💇",
        "order_title": "TEMPAHAN BARU",
        "order_title_en": "NEW BOOKING",
        "page_title": "Tempah Temujanji",
        "page_title_en": "Book Appointment",
        "categories": [
            {"id": "potong", "name": "✂️ Potong", "name_en": "✂️ Haircut", "icon": "✂️"},
            {"id": "warna", "name": "🎨 Warna", "name_en": "🎨 Coloring", "icon": "🎨"},
            {"id": "rawatan", "name": "💆 Rawatan", "name_en": "💆 Treatment", "icon": "💆"},
        ],
        "default_category": "potong",
        "category_keywords": {
            "potong": ["potong", "cut", "haircut", "trim", "layer", "bob", "pixie", "fade", "undercut"],
            "warna": ["warna", "color", "colour", "dye", "highlight", "ombre", "balayage", "bleach"],
            "rawatan": ["rawatan", "treatment", "spa", "mask", "keratin", "rebonding", "perm", "facial", "manicure", "pedicure", "massage", "urut"],
        },
        "item_description_default": "Perkhidmatan profesional dari pakar kami",
        "item_description_default_en": "Professional service from our experts",
        "whatsapp_closing": "Sila nyatakan tarikh, masa dan staff pilihan. Terima kasih! 🙏",
        "whatsapp_closing_en": "Please provide preferred date, time and staff. Thank you! 🙏",
        "primary_color": "#8b5cf6",
        "features": {
            "delivery_zones": False,
            "time_slots": True,
            "special_instructions": True,
            "promo_code": True,
            "size_options": False,
            "color_options": False,
            "appointment_date": True,
            "staff_selection": True,
            "shipping_options": False,
            "custom_message": False,
        },
        "default_staff": [
            {"id": 1, "name": "Sesiapa", "icon": "🙋"},
            {"id": 2, "name": "Kak Amy", "icon": "👩"},
            {"id": 3, "name": "Abg Rizal", "icon": "👨"},
        ],
    },
    "services": {
        "button_label": "🔧 Tempah Servis",
        "button_label_en": "🔧 Book Service",
        "order_emoji": "🔧",
        "order_title": "TEMPAHAN SERVIS",
        "order_title_en": "SERVICE BOOKING",
        "page_title": "Tempah Servis",
        "page_title_en": "Book Service",
        "categories": [
            {"id": "servis", "name": "🔧 Servis", "name_en": "🔧 Services", "icon": "🔧"},
            {"id": "pakej", "name": "📦 Pakej", "name_en": "📦 Packages", "icon": "📦"},
        ],
        "default_category": "servis",
        "category_keywords": {
            "servis": ["servis", "service", "repair", "baiki", "pasang", "install", "cuci", "clean"],
            "pakej": ["pakej", "package", "bundle", "combo", "set", "membership", "subscription", "langganan"],
        },
        "item_description_default": "Perkhidmatan profesional dan berkualiti",
        "item_description_default_en": "Professional quality service",
        "whatsapp_closing": "Sila nyatakan tarikh, masa dan lokasi. Terima kasih! 🙏",
        "whatsapp_closing_en": "Please provide preferred date, time and location. Thank you! 🙏",
        "primary_color": "#3b82f6",
        "features": {
            "delivery_zones": True,
            "time_slots": True,
            "special_instructions": True,
            "promo_code": True,
            "size_options": False,
            "color_options": False,
            "appointment_date": True,
            "staff_selection": False,
            "shipping_options": False,
            "custom_message": False,
            "location_choice": True,
        },
        "location_options": [
            {"id": "home", "name": "Ke Rumah/Lokasi Saya", "icon": "🏠", "extra_fee": 20},
            {"id": "shop", "name": "Di Kedai/Workshop", "icon": "🏪", "extra_fee": 0},
        ],
    },
    "bakery": {
        "button_label": "🎂 Tempah Kek",
        "button_label_en": "🎂 Order Cake",
        "order_emoji": "🎂",
        "order_title": "TEMPAHAN KEK",
        "order_title_en": "CAKE ORDER",
        "page_title": "Tempah Kek",
        "page_title_en": "Order Cake",
        "categories": [
            {"id": "kek", "name": "🎂 Kek", "name_en": "🎂 Cakes", "icon": "🎂"},
            {"id": "pastri", "name": "🥐 Pastri", "name_en": "🥐 Pastries", "icon": "🥐"},
            {"id": "cookies", "name": "🍪 Cookies", "name_en": "🍪 Cookies", "icon": "🍪"},
        ],
        "default_category": "kek",
        "category_keywords": {
            "kek": ["kek", "cake", "birthday", "wedding", "anniversary", "fondant", "buttercream", "cheesecake", "brownies"],
            "pastri": ["pastri", "pastry", "croissant", "puff", "danish", "tart", "pie", "eclair", "donut"],
            "cookies": ["cookies", "cookie", "biskut", "biscuit", "macarons", "brownies", "kuih", "raya"],
        },
        "item_description_default": "Dibakar segar dengan bahan berkualiti",
        "item_description_default_en": "Freshly baked with quality ingredients",
        "whatsapp_closing": "Sila nyatakan tarikh pickup/delivery dan mesej kek jika ada. Terima kasih! 🙏",
        "whatsapp_closing_en": "Please provide pickup/delivery date and cake message if any. Thank you! 🙏",
        "primary_color": "#f59e0b",
        "features": {
            "delivery_zones": True,
            "time_slots": True,
            "special_instructions": True,
            "promo_code": True,
            "size_options": True,
            "color_options": False,
            "appointment_date": True,
            "staff_selection": False,
            "shipping_options": False,
            "custom_message": True,
        },
        "sizes": ["0.5kg", "1kg", "1.5kg", "2kg", "3kg"],
        "custom_message_placeholder": "Tulis mesej atas kek (cth: Happy Birthday Ali!)",
    },
    "general": {
        "button_label": "🛒 Beli Sekarang",
        "button_label_en": "🛒 Buy Now",
        "order_emoji": "🛒",
        "order_title": "PESANAN BARU",
        "order_title_en": "NEW ORDER",
        "page_title": "Beli Sekarang",
        "page_title_en": "Buy Now",
        "categories": [
            {"id": "produk", "name": "🛍️ Produk", "name_en": "🛍️ Products", "icon": "🛍️"},
            {"id": "lain", "name": "📦 Lain-lain", "name_en": "📦 Others", "icon": "📦"},
        ],
        "default_category": "produk",
        "category_keywords": {
            "produk": ["produk", "product", "item", "barang", "goods"],
            "lain": ["lain", "other", "misc"],
        },
        "item_description_default": "Produk berkualiti pilihan kami",
        "item_description_default_en": "Our quality selected product",
        "whatsapp_closing": "Sila nyatakan alamat penuh. Terima kasih! 🙏",
        "whatsapp_closing_en": "Please provide your full address. Thank you! 🙏",
        "primary_color": "#10b981",
        "features": {
            "delivery_zones": True,
            "time_slots": False,
            "special_instructions": True,
            "promo_code": True,
            "size_options": False,
            "color_options": False,
            "appointment_date": False,
            "staff_selection": False,
            "shipping_options": True,
            "custom_message": False,
        },
        "shipping_options": [
            {"id": "cod", "name": "COD", "price": 8, "desc": "Bayar bila terima"},
            {"id": "postage", "name": "Postage", "price": 6, "desc": "2-4 hari"},
            {"id": "pickup", "name": "Self Pickup", "price": 0, "desc": "Ambil sendiri"},
        ],
    },
}


# ============================================================================
# BUSINESS TYPE DETECTION KEYWORDS
# ============================================================================

BUSINESS_TYPE_KEYWORDS = {
    "food": [
        # Malay food keywords
        "makan", "restoran", "restaurant", "cafe", "kafe", "kedai makan", "warung",
        "nasi", "mee", "ayam", "ikan", "daging", "sayur", "lauk", "makanan", "food",
        "mamak", "gerai", "stall", "catering", "katering", "masakan", "goreng",
        "bakar", "kukus", "rebus", "sup", "kari", "curry", "rendang", "satay",
        "roti", "canai", "tom yam", "tomyam", "laksa", "kuih",
        "dessert", "pencuci mulut", "minuman", "drinks", "beverages", "kopitiam",
        "hawker", "dapur", "kitchen", "chef", "tukang masak", "menu", "hidangan",
        "masakan kampung", "western food", "fast food", "delivery makanan",
        "nasi kandar", "nasi lemak", "char kuey teow", "mee goreng", "teh tarik",
    ],
    "clothing": [
        # Clothing/fashion keywords
        "butik", "boutique", "fashion", "fesyen", "pakaian", "clothing", "baju",
        "kurung", "kebaya", "jubah", "abaya", "dress", "blouse", "shirt", "kemeja",
        "seluar", "pants", "skirt", "tudung", "hijab", "shawl", "scarf", "headscarf",
        "bawal", "instant hijab", "telekung", "aksesori", "accessories", "handbag",
        "bag", "beg", "kasut", "shoes", "sandal", "heels", "sneakers", "sport wear",
        "attire", "wardrobe", "collection", "koleksi", "designer", "tailor", "jahit",
        "sewing", "alterations", "custom made", "ready stock", "pre-order", "dropship",
        "online shop pakaian", "muslimah", "modest wear", "plus size", "petite",
    ],
    "salon": [
        # Salon/spa keywords - high priority for beauty businesses
        "salon", "spa", "barbershop", "barber", "gunting rambut", "haircut",
        "potong rambut", "hair salon", "beauty salon", "nail salon", "kuku",
        "manicure", "pedicure", "facial", "treatment", "kecantikan", "beauty",
        "waxing", "threading", "brow", "lash", "eyelash", "makeup", "mekap",
        "hair color", "warna rambut", "highlight", "balayage", "ombre", "dye",
        "bleach", "perm", "rebonding", "keratin", "smoothing", "blow dry",
        "styling", "updo", "bridal", "pengantin", "massage", "urut", "reflexology",
        "body scrub", "body wrap", "sauna", "steam", "jacuzzi",
    ],
    "services": [
        # General service keywords (excluding salon-specific)
        "servis", "service", "perkhidmatan", "repair", "baiki", "maintenance",
        "penyelenggaraan", "cleaning", "cuci", "laundry", "dobi",
        "aircond", "air cond", "plumber", "plumbing", "paip",
        "elektrik", "electrical", "wiring", "renovation", "ubahsuai", "kontraktor",
        "contractor", "photography", "fotografi", "videography", "wedding",
        "perkahwinan", "event", "acara", "catering servis", "consultant", "consulting",
        "tuition", "tuisyen", "class", "kelas", "course", "kursus", "training",
        "latihan", "personal trainer", "fitness", "gym", "studio", "workshop",
    ],
    "bakery": [
        # Bakery/cake keywords
        "bakery", "bakeri", "kek", "cake", "cupcake", "birthday cake", "kek hari jadi",
        "wedding cake", "kek kahwin", "anniversary", "fondant", "buttercream",
        "cheesecake", "brownies", "pastry", "pastri", "croissant", "puff pastry",
        "danish", "tart", "pie", "eclair", "donut", "donat", "cookies", "cookie",
        "biskut", "biscuit", "macarons", "raya cookies", "kuih raya",
        "bread", "roti", "artisan bread", "sourdough", "bun", "muffin",
    ],
}


def detect_business_type(description: str) -> str:
    """
    Detect business type from description text.

    Args:
        description: Business description in Malay or English

    Returns:
        Business type: "food", "clothing", "salon", "services", "bakery", or "general"
    """
    if not description:
        return "general"

    desc_lower = description.lower()

    # Count keyword matches for each type
    scores = {
        "food": 0,
        "clothing": 0,
        "salon": 0,
        "services": 0,
        "bakery": 0,
    }

    for btype, keywords in BUSINESS_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                # Multi-word keywords get higher weight
                weight = len(keyword.split())
                scores[btype] += weight

    # Find the type with highest score
    max_score = max(scores.values())

    if max_score == 0:
        return "general"

    # Return the type with highest score
    for btype, score in scores.items():
        if score == max_score:
            logger.info(f"🔍 Detected business type: {btype} (score: {score})")
            return btype

    return "general"


def get_business_config(business_type: str) -> Dict:
    """
    Get configuration for a business type.
    
    Args:
        business_type: One of "food", "clothing", "services", "general"
        
    Returns:
        Business configuration dictionary
    """
    return BUSINESS_CONFIGS.get(business_type, BUSINESS_CONFIGS["general"])


def get_categories_for_business_type(business_type: str) -> List[Dict]:
    """
    Get category list for a business type.
    
    Args:
        business_type: Business type string
        
    Returns:
        List of category dictionaries with id, name, icon
    """
    config = get_business_config(business_type)
    return config.get("categories", BUSINESS_CONFIGS["general"]["categories"])


def detect_item_category(item_name: str, business_type: str) -> str:
    """
    Auto-detect category for an item based on its name and business type.
    
    Args:
        item_name: Name of the item/product
        business_type: Business type for category context
        
    Returns:
        Category ID
    """
    if not item_name:
        config = get_business_config(business_type)
        return config.get("default_category", "produk")
    
    name_lower = item_name.lower()
    config = get_business_config(business_type)
    keywords_map = config.get("category_keywords", {})
    
    for category_id, keywords in keywords_map.items():
        for keyword in keywords:
            if keyword in name_lower:
                return category_id
    
    return config.get("default_category", "produk")


def generate_category_buttons_html(business_type: str, language: str = "ms") -> str:
    """
    Generate HTML for category filter buttons based on business type.
    
    Args:
        business_type: Business type string
        language: "ms" for Malay, "en" for English
        
    Returns:
        HTML string for category buttons
    """
    config = get_business_config(business_type)
    categories = config.get("categories", [])
    
    # "All" button (always first)
    all_label = "Semua" if language == "ms" else "All"
    buttons_html = f'''<button onclick="filterDeliveryCategory('all')" class="delivery-cat-btn active" style="background:#f97316;color:white;padding:8px 16px;border-radius:9999px;font-size:14px;font-weight:500;white-space:nowrap;border:none;cursor:pointer;">{all_label}</button>'''
    
    # Category buttons
    for cat in categories:
        name = cat.get("name") if language == "ms" else cat.get("name_en", cat.get("name"))
        cat_id = cat.get("id")
        buttons_html += f'''
                        <button onclick="filterDeliveryCategory('{cat_id}')" class="delivery-cat-btn" style="background:#f3f4f6;color:#374151;padding:8px 16px;border-radius:9999px;font-size:14px;font-weight:500;white-space:nowrap;border:none;cursor:pointer;">{name}</button>'''
    
    return buttons_html


def get_delivery_button_label(business_type: str, language: str = "ms") -> str:
    """
    Get the delivery/order button label for a business type.
    
    Args:
        business_type: Business type string
        language: "ms" for Malay, "en" for English
        
    Returns:
        Button label string
    """
    config = get_business_config(business_type)
    if language == "en":
        return config.get("button_label_en", config.get("button_label"))
    return config.get("button_label")


def get_order_config(business_type: str, language: str = "ms") -> Dict:
    """
    Get order-related configuration (emoji, title, closing message).
    
    Args:
        business_type: Business type string
        language: "ms" for Malay, "en" for English
        
    Returns:
        Dict with order_emoji, order_title, whatsapp_closing
    """
    config = get_business_config(business_type)
    
    if language == "en":
        return {
            "order_emoji": config.get("order_emoji"),
            "order_title": config.get("order_title_en", config.get("order_title")),
            "whatsapp_closing": config.get("whatsapp_closing_en", config.get("whatsapp_closing")),
            "page_title": config.get("page_title_en", config.get("page_title")),
        }
    
    return {
        "order_emoji": config.get("order_emoji"),
        "order_title": config.get("order_title"),
        "whatsapp_closing": config.get("whatsapp_closing"),
        "page_title": config.get("page_title"),
    }


def get_all_category_options() -> Dict[str, List[Dict]]:
    """
    Get all category options for all business types.
    Useful for frontend dropdowns that need to show categories per business type.
    
    Returns:
        Dict mapping business_type to list of category options
    """
    return {
        btype: config["categories"]
        for btype, config in BUSINESS_CONFIGS.items()
    }
