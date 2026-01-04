"""
Menu Validator Service - RALPH LOOP Pattern
(Repeat And Loop Properly until Handled)

CRITICAL: This service ensures ONLY user-uploaded menu items appear in the delivery system.
NO AI hallucination, NO generated items, NO modified names/prices.

The AI was previously creating fake menu items like "Wedding" and "Model" for photography
businesses instead of using the user's actual uploaded items.
"""
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# INVALID ITEM NAMES - Terms that indicate NON-product items
# These should NEVER appear as menu items
# ============================================================================

# Single word matches (exact word match)
INVALID_ITEM_WORDS = [
    # UI/Feature elements
    'whatsapp', 'hubungi', 'contact', 'call', 'message', 'chat',
    'facebook', 'instagram', 'tiktok', 'twitter', 'youtube', 'social',

    # Navigation/Sections
    'home', 'laman', 'menu', 'gallery', 'galeri', 'about', 'tentang',
    'lokasi', 'location', 'alamat', 'address', 'footer', 'header',
    'nav', 'copyright', 'powered', 'hero', 'banner',

    # Generic business terms (NOT actual products)
    'saya', 'kami', 'nama', 'name', 'kedai', 'restoran', 'shop',

    # Greetings/Headers (NOT products)
    'welcome', 'selamat', 'hello', 'salam', 'professional',

    # Operating info (NOT products)
    'waktu', 'operasi', 'operating', 'hours', 'buka', 'tutup', 'open', 'close',

    # Actions (NOT products)
    'scan', 'imbas', 'download', 'subscribe', 'newsletter', 'order', 'pesanan',
    'book', 'booking', 'cart', 'checkout',

    # =========================================================================
    # SERVICE-TYPE HALLUCINATED TERMS (commonly AI-generated for services)
    # These appear when AI analyzes business type instead of actual items
    # =========================================================================
    'wedding',      # Photography hallucination
    'model',        # Photography hallucination
    'portrait',     # Photography hallucination
    'photoshoot',   # Photography hallucination
    'session',      # Generic session (e.g., "photo session")
    'package',      # Generic package without specific name
    'service',      # Generic service without specific name
    'servis',       # Malay generic service
    'perkhidmatan', # Malay generic service (when alone)
    'consultation', # Generic consultation
    'perundingan',  # Malay consultation

    # Generic category names (NOT actual products)
    'produk', 'product', 'item', 'barang', 'lain', 'other', 'misc',
]

# Phrase matches (substring match - if phrase appears anywhere in name)
INVALID_ITEM_PHRASES = [
    # Contact/CTA phrases
    'selamat datang',
    'hubungi kami',
    'contact us',
    'get in touch',
    'ikuti kami',
    'follow us',
    'call now',
    'book now',
    'order now',
    'shop now',
    'learn more',
    'read more',
    'view more',
    'see all',
    'view all',
    'show more',
    'get started',
    'join us',

    # Section headers
    'our story',
    'about us',
    'find us',
    'visit us',
    'view menu',
    'open shop',

    # Generic service descriptions (AI hallucination patterns)
    'perkhidmatan profesional',
    'perkhidmatan berkualiti',
    'professional service',
    'quality service',
    'our services',
    'perkhidmatan kami',

    # Default/placeholder patterns
    'item name',
    'nama item',
    'product name',
    'nama produk',
    'untitled',
    'no name',
    'sample',
]


def is_valid_item_name(name: str) -> bool:
    """
    STRICT validation of menu item names.

    Returns False if:
    - Name is empty, too short, or too long
    - Name contains invalid words/phrases
    - Name looks like a time/date pattern
    - Name is a generic service description
    """
    if not name or not isinstance(name, str):
        return False

    name_clean = name.strip()
    name_lower = name_clean.lower()

    # Length checks
    if len(name_clean) < 2:
        logger.debug(f"   ✗ Rejected '{name}' - too short")
        return False

    if len(name_clean) > 80:
        logger.debug(f"   ✗ Rejected '{name}' - too long")
        return False

    # Must contain at least one letter
    if not re.search(r'[a-zA-Z\u0080-\uFFFF]', name_clean):
        logger.debug(f"   ✗ Rejected '{name}' - no letters")
        return False

    # Check against invalid phrases first (substring match)
    for phrase in INVALID_ITEM_PHRASES:
        if phrase in name_lower:
            logger.debug(f"   ✗ Rejected '{name}' - contains phrase '{phrase}'")
            return False

    # Check against invalid words (whole word match)
    name_words = set(re.split(r'[\s\-_.,;:!?()]+', name_lower))
    for invalid in INVALID_ITEM_WORDS:
        if invalid in name_words:
            logger.debug(f"   ✗ Rejected '{name}' - contains word '{invalid}'")
            return False

    # Reject time patterns (operating hours)
    if re.search(r'\d{1,2}[:.]\d{2}|\d{1,2}\s*(am|pm|pagi|petang|malam)', name_lower):
        logger.debug(f"   ✗ Rejected '{name}' - looks like time")
        return False

    # Reject if name is ONLY generic terms combined
    # e.g., "Photo Package" (Photo + Package = both generic)
    generic_only_words = {'photo', 'gambar', 'foto', 'pakej', 'package', 'set', 'combo'}
    if name_words and name_words.issubset(generic_only_words | {'a', 'b', 'c', '1', '2', '3'}):
        logger.debug(f"   ✗ Rejected '{name}' - only contains generic terms")
        return False

    return True


def is_valid_price(price) -> tuple:
    """
    Validate and parse price.

    Returns (is_valid, parsed_price)
    """
    if price is None:
        return (False, 0)

    try:
        # Handle string prices like "RM15", "15.00", etc.
        if isinstance(price, str):
            price_str = price.replace('RM', '').replace('rm', '').replace(',', '').strip()
            price_float = float(price_str)
        else:
            price_float = float(price)

        # Price must be positive
        if price_float <= 0:
            return (False, 0)

        # Reasonable price range (0.01 to 100000)
        if price_float > 100000:
            return (False, 0)

        return (True, price_float)

    except (ValueError, TypeError):
        return (False, 0)


def validate_and_extract_menu_items(form_data: dict, strict_mode: bool = True) -> List[Dict]:
    """
    RALPH LOOP: Repeat And Loop Properly until Handled

    This function ONLY returns items that user explicitly uploaded.
    It NEVER creates, modifies, or hallucinates menu items.

    Args:
        form_data: The form data containing user inputs
        strict_mode: If True, requires both name AND price. If False, allows name-only items.

    Returns:
        List of validated menu items with exact user data
    """
    # Get menu items from various possible locations in form data
    user_menu_items = (
        form_data.get('menuItems') or
        form_data.get('menu_items') or
        form_data.get('images') or  # Images with names/prices
        []
    )

    if not user_menu_items:
        logger.warning("⚠️ RALPH LOOP: No menu items provided by user")
        return []

    logger.info(f"🔍 RALPH LOOP: Validating {len(user_menu_items)} potential menu items...")

    validated_items = []

    for index, item in enumerate(user_menu_items):
        if not isinstance(item, dict):
            logger.warning(f"   ⚠️ Item {index}: Not a dict, skipping")
            continue

        # Extract user-provided fields
        raw_name = item.get('name', '') or item.get('item_name', '') or ''
        name = raw_name.strip() if raw_name else ''

        raw_price = item.get('price') or item.get('item_price')
        image_url = item.get('imageUrl') or item.get('image_url') or item.get('url') or item.get('image') or ''

        # ===================================================================
        # SKIP if no name provided - NEVER let AI generate names
        # ===================================================================
        if not name:
            logger.info(f"   ⏭️ Item {index}: No name provided, skipping (NO AI FALLBACK)")
            continue

        # ===================================================================
        # SKIP if name fails validation
        # ===================================================================
        if not is_valid_item_name(name):
            logger.warning(f"   ⚠️ Item {index}: Invalid name '{name}', skipping")
            continue

        # ===================================================================
        # SKIP if no valid price in strict mode
        # ===================================================================
        is_price_valid, parsed_price = is_valid_price(raw_price)

        if strict_mode and not is_price_valid:
            logger.warning(f"   ⚠️ Item {index}: Invalid price '{raw_price}' for '{name}', skipping")
            continue

        # If not strict mode, use fallback price
        if not is_price_valid:
            parsed_price = 0  # Will need to be handled by caller

        # ===================================================================
        # VALID ITEM - Add to list with EXACT user data
        # ===================================================================
        validated_item = {
            'id': len(validated_items) + 1,
            'name': name,  # EXACT name from user, NO modification
            'price': parsed_price,  # EXACT price from user
            'image': image_url or 'https://placehold.co/400x300?text=No+Image',
            'image_url': image_url or 'https://placehold.co/400x300?text=No+Image',
            'desc': 'Produk pilihan kami',
            'description': 'Produk pilihan kami',
            'category': detect_item_category(name),
            'category_id': detect_item_category(name),
            'is_available': True,
        }

        validated_items.append(validated_item)
        logger.info(f"   ✅ Item {index}: VALID - '{name}' @ RM{parsed_price:.2f}")

    logger.info(f"\n📦 RALPH LOOP COMPLETE: {len(validated_items)} validated items from {len(user_menu_items)} inputs")

    return validated_items


def detect_item_category(name: str) -> str:
    """
    Auto-detect category from item name.
    This is a helper function and doesn't modify the item name.
    """
    if not name:
        return 'general'

    name_lower = name.lower()

    # Food categories
    if any(w in name_lower for w in ['nasi', 'rice', 'biryani', 'mee', 'laksa', 'roti', 'bihun', 'kuetiau']):
        return 'nasi'
    if any(w in name_lower for w in ['ayam', 'ikan', 'daging', 'sotong', 'udang', 'kambing', 'chicken', 'fish', 'beef', 'mutton']):
        return 'lauk'
    if any(w in name_lower for w in ['teh', 'kopi', 'air', 'milo', 'sirap', 'drink', 'jus', 'juice', 'coffee', 'tea']):
        return 'minuman'
    if any(w in name_lower for w in ['cake', 'kek', 'kuih', 'dessert', 'ice', 'ais', 'pudding']):
        return 'pencuci'

    # Clothing categories
    if any(w in name_lower for w in ['baju', 'shirt', 'kurung', 'kebaya', 'blouse', 'top']):
        return 'baju'
    if any(w in name_lower for w in ['tudung', 'shawl', 'hijab', 'scarf']):
        return 'tudung'
    if any(w in name_lower for w in ['seluar', 'pants', 'trouser', 'skirt', 'rok']):
        return 'seluar'

    # Service categories
    if any(w in name_lower for w in ['potong', 'cut', 'trim', 'style', 'curl', 'color', 'pewarna']):
        return 'rawatan'
    if any(w in name_lower for w in ['spa', 'urut', 'massage', 'facial', 'treatment']):
        return 'rawatan'

    # Default
    return 'general'


def log_menu_flow(step: str, items: list):
    """
    Log menu items at each step for debugging.
    Helps trace where hallucination might be happening.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"📍 MENU FLOW: {step}")
    logger.info(f"   Items count: {len(items)}")

    for i, item in enumerate(items[:5]):  # Show first 5
        name = item.get('name', 'NO NAME')
        price = item.get('price', 'NO PRICE')
        logger.info(f"   • {i+1}. {name} - RM{price}")

    if len(items) > 5:
        logger.info(f"   ... and {len(items) - 5} more items")

    logger.info('='*60 + '\n')
