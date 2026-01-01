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
    },
    "clothing": {
        "button_label": "🛍️ Order Sekarang",
        "button_label_en": "🛍️ Order Now",
        "order_emoji": "👗",
        "order_title": "PESANAN BARU",
        "order_title_en": "NEW ORDER",
        "page_title": "Order Produk",
        "page_title_en": "Order Products",
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
    },
    "services": {
        "button_label": "📅 Tempah Sekarang",
        "button_label_en": "📅 Book Now",
        "order_emoji": "📋",
        "order_title": "TEMPAHAN BARU",
        "order_title_en": "NEW BOOKING",
        "page_title": "Tempah Perkhidmatan",
        "page_title_en": "Book Service",
        "categories": [
            {"id": "servis", "name": "🔧 Perkhidmatan", "name_en": "🔧 Services", "icon": "🔧"},
            {"id": "pakej", "name": "📦 Pakej", "name_en": "📦 Packages", "icon": "📦"},
        ],
        "default_category": "servis",
        "category_keywords": {
            "servis": ["servis", "service", "repair", "baiki", "pasang", "install", "cuci", "clean", "urut", "massage", "potong", "cut", "salon", "spa", "treatment"],
            "pakej": ["pakej", "package", "bundle", "combo", "set", "membership", "subscription", "langganan"],
        },
        "item_description_default": "Perkhidmatan profesional dan berkualiti",
        "item_description_default_en": "Professional quality service",
        "whatsapp_closing": "Sila nyatakan tarikh dan masa yang dikehendaki. Terima kasih! 🙏",
        "whatsapp_closing_en": "Please provide preferred date and time. Thank you! 🙏",
        "primary_color": "#3b82f6",
    },
    "general": {
        "button_label": "🛒 Beli Sekarang",
        "button_label_en": "🛒 Buy Now",
        "order_emoji": "🛒",
        "order_title": "PESANAN BARU",
        "order_title_en": "NEW ORDER",
        "page_title": "Order Produk",
        "page_title_en": "Order Products",
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
        "roti", "canai", "tom yam", "tomyam", "laksa", "bakery", "kuih", "cake",
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
    "services": [
        # Service keywords
        "servis", "service", "perkhidmatan", "repair", "baiki", "maintenance",
        "penyelenggaraan", "salon", "spa", "urut", "massage", "reflexology",
        "facial", "treatment", "kecantikan", "beauty", "nail", "kuku", "waxing",
        "barbershop", "barber", "gunting rambut", "haircut", "potong rambut",
        "color", "dye", "bleach", "perm", "rebonding", "cleaning", "cuci",
        "laundry", "dobi", "aircond", "air cond", "plumber", "plumbing", "paip",
        "elektrik", "electrical", "wiring", "renovation", "ubahsuai", "kontraktor",
        "contractor", "photography", "fotografi", "videography", "wedding",
        "perkahwinan", "event", "acara", "catering servis", "consultant", "consulting",
        "tuition", "tuisyen", "class", "kelas", "course", "kursus", "training",
        "latihan", "personal trainer", "fitness", "gym", "studio", "workshop",
    ],
}


def detect_business_type(description: str) -> str:
    """
    Detect business type from description text.
    
    Args:
        description: Business description in Malay or English
        
    Returns:
        Business type: "food", "clothing", "services", or "general"
    """
    if not description:
        return "general"
    
    desc_lower = description.lower()
    
    # Count keyword matches for each type
    scores = {
        "food": 0,
        "clothing": 0,
        "services": 0,
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
