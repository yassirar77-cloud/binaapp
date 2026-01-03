"""
Simple Generate Endpoint
POST /api/generate - Generate website from description
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger
import asyncio
import json

from app.services.ai_service import ai_service
from app.services.templates import template_service
from app.services.screenshot_service import screenshot_service
from app.services.job_service import job_service, JobStatus
from app.services.business_types import detect_business_type, detect_item_category, get_business_config, get_categories_for_business_type
from app.models.schemas import WebsiteGenerationRequest, Language
from app.utils.content_moderation import is_content_allowed, log_blocked_attempt
import re

router = APIRouter()


class SimpleGenerateRequest(BaseModel):
    """Simplified generation request"""
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="User's description in Malay or English"
    )
    user_id: Optional[str] = Field(default="demo-user", description="Optional user ID")
    images: Optional[List] = Field(default=[], description="Optional list of uploaded image URLs or image metadata objects with url and name")
    gallery_metadata: Optional[List] = Field(default=[], description="Gallery images with metadata (url, name)")
    business_description: Optional[str] = Field(default=None, description="Business description for context")
    language: Optional[str] = Field(default="ms", description="Language for generation (ms or en)")
    email: Optional[str] = Field(default=None, description="User email")
    logo: Optional[str] = Field(default=None, description="Logo URL")
    fonts: Optional[List[str]] = Field(default=[], description="Font names to use (e.g., ['Inter', 'Poppins'])")
    colors: Optional[dict] = Field(default=None, description="Color scheme (primary, secondary, accent)")
    theme: Optional[str] = Field(default=None, description="Detected theme name (e.g., 'Purrfect Paws Theme')")
    multi_style: Optional[bool] = Field(default=False, description="Generate multiple style variations")
    generate_previews: Optional[bool] = Field(default=False, description="Generate preview thumbnails (slower)")
    mode: Optional[str] = Field(default="single", description="Generation mode: 'single', 'dual', 'best', or 'strategic'")
    features: Optional[dict] = Field(default=None, description="Selected features (whatsapp, googleMap, deliverySystem, etc.)")
    delivery: Optional[dict] = Field(default=None, description="Delivery system settings (area, fee, minimum, hours)")
    fulfillment: Optional[dict] = Field(default=None, description="Fulfillment options (delivery, pickup, fees, area)")
    address: Optional[str] = Field(default=None, description="Full address for Google Map")
    social_media: Optional[dict] = Field(default=None, description="Social media handles (instagram, facebook, tiktok)")
    business_type: Optional[str] = Field(default=None, description="Business type: food, clothing, services, general (auto-detected if not provided)")
    payment: Optional[dict] = Field(default=None, description="Payment methods (cod: bool, qr: bool, qr_image: str)")


class SimpleGenerateResponse(BaseModel):
    """Simplified generation response"""
    html: str
    detected_features: List[str]
    template_used: str
    success: bool = True


class StyleVariation(BaseModel):
    """Single style variation"""
    style: str
    html: str
    preview_image: Optional[str] = None
    thumbnail: Optional[str] = None
    social_preview: Optional[str] = None


class MultiStyleResponse(BaseModel):
    """Multi-style generation response"""
    variations: List[StyleVariation]
    detected_features: List[str]
    template_used: str
    success: bool = True


class DualGenerateResponse(BaseModel):
    """Dual AI generation response"""
    qwen_html: Optional[str] = None
    deepseek_html: Optional[str] = None
    detected_features: List[str]
    template_used: str
    success: bool = True


async def fetch_menu_items_from_database(website_id: str) -> List[dict]:
    """
    Fetch menu items from database for a website
    """
    try:
        from app.core.supabase import get_supabase_sync
        supabase = get_supabase_sync()

        result = supabase.table("menu_items")\
            .select("*")\
            .eq("website_id", website_id)\
            .eq("is_available", True)\
            .order("sort_order")\
            .execute()

        if result.data:
            logger.info(f"✓ Fetched {len(result.data)} menu items from database")
            # Convert database format to expected format
            return [
                {
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "description": item.get('description', 'Hidangan istimewa'),
                    "price": float(item.get('price', 0)),
                    "image_url": item.get('image_url', ''),
                    "category_id": item.get('category_id', 'lauk'),
                    "is_available": item.get('is_available', True)
                }
                for item in result.data
            ]
        return []
    except Exception as e:
        logger.error(f"Error fetching menu items from database: {e}")
        return []


# ========================================================================
# INVALID MENU NAME VALIDATOR - Prevents AI from hallucinating menu items
# ========================================================================

# Exact match invalid names - these must match whole words
INVALID_MENU_WORDS = [
    # Feature/UI elements (NOT food!)
    'whatsapp', 'hubungi', 'contact', 'call', 'message',
    'facebook', 'instagram', 'tiktok', 'twitter', 'youtube', 'social',
    # Business name prefixes (NOT food!)
    'saya', 'kami', 'nama', 'name', 'kedai', 'restoran',
    # Navigation/UI
    'home', 'laman', 'menu', 'gallery', 'galeri', 'about', 'tentang',
    'lokasi', 'location', 'alamat', 'address', 'order', 'pesanan',
    # Generic greetings (NOT food!)
    'welcome', 'hello', 'salam',
    # Operating hours
    'waktu', 'operasi', 'operating', 'hours', 'buka', 'tutup', 'open', 'close',
    # Section headers
    'kenali', 'story', 'footer', 'header', 'nav', 'copyright', 'powered',
    # Other non-food
    'scan', 'imbas', 'download', 'subscribe', 'newsletter',
]

# Phrase match - these should be substring matches
INVALID_MENU_PHRASES = [
    'selamat datang',  # Welcome greeting
    'hubungi kami',    # Contact us
    'contact us',
    'get in touch',    # Contact section header
    'ikuti kami',      # Follow us
    'follow us',
    'open shop',       # Store header
    'shop now',
    'learn more',
    'read more',
    'our story',
    'about us',
    'find us',
    'visit us',
    'call now',
    'book now',
    'order now',       # Only when full phrase (not just 'order')
    'get started',
    'join us',
    'view menu',       # Navigation text
    'see all',
    'view all',
    'show more',
]


def is_valid_menu_item_name(name: str) -> bool:
    """
    CRITICAL VALIDATION: Check if a name is a valid menu item name
    
    Returns False if name contains invalid keywords that indicate
    it's NOT a real food/product item (e.g., "WhatsApp", "SAYA", "Hubungi")
    
    This prevents AI from hallucinating menu items from generated HTML content.
    """
    if not name or not isinstance(name, str):
        return False
    
    # Clean and normalize
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    # Must be at least 2 characters
    if len(name_clean) < 2:
        return False
    
    # Must not be too long (probably a sentence, not a dish name)
    if len(name_clean) > 60:
        return False
    
    # Must contain at least one letter
    if not re.search(r'[a-zA-Z\u0080-\uFFFF]', name_clean):
        return False
    
    # Check against invalid phrases (substring match)
    for phrase in INVALID_MENU_PHRASES:
        if phrase in name_lower:
            logger.debug(f"   ✗ Rejected menu name '{name}' - contains phrase '{phrase}'")
            return False
    
    # Check against invalid words (whole word match only)
    # Split name into words and check if any word matches exactly
    name_words = set(re.split(r'[\s\-_.,;:!?]+', name_lower))
    for invalid in INVALID_MENU_WORDS:
        if invalid in name_words:
            logger.debug(f"   ✗ Rejected menu name '{name}' - contains word '{invalid}'")
            return False
    
    # Check for time patterns (7am, 10:00 - these are operating hours, not food)
    if re.search(r'\d{1,2}[:.]\d{2}|\d{1,2}\s*(am|pm|pagi|petang|malam)', name_lower):
        logger.debug(f"   ✗ Rejected menu name '{name}' - looks like time")
        return False
    
    return True


def extract_menu_items_from_html(html: str, business_type: str = "food") -> List[dict]:
    """
    Extract REAL menu items from AI-generated HTML gallery/menu section.
    
    ⚠️  DEPRECATED: This function should NOT be used for delivery menu items!
    
    The delivery system should ONLY use user-uploaded menu items with their
    prices and names. Do NOT extract menu items from AI-generated HTML as
    this causes hallucination issues (e.g., "WhatsApp" appearing as a menu item).
    
    This function is kept for backward compatibility but returns empty list
    when user has uploaded their own menu items.

    Uses Python's built-in HTMLParser for reliable parsing.

    CRITICAL: Only extract actual menu/product items, NOT:
    - Operating hours ("Waktu Operasi", "Buka Setiap Hari")
    - Price labels ("Harga")
    - Generic section headers
    - Contact information
    """
    from html.parser import HTMLParser

    menu_items = []

    # ========================================================================
    # SKIP PHRASES - Full phrases that indicate NON-menu content
    # These are checked FIRST before individual words
    # ========================================================================
    skip_phrases = [
        # Operating hours (Malay)
        'buka setiap hari', 'waktu operasi', 'waktu perniagaan', 'jam operasi',
        'hari operasi', 'masa operasi', 'buka dari', 'buka pada', 'tutup pada',
        'isnin hingga', 'ahad hingga', 'setiap hari', 'hari-hari',
        'isnin - ahad', 'isnin-ahad', 'sabtu dan ahad',
        # Operating hours (English)
        'open daily', 'operating hours', 'business hours', 'opening hours',
        'open every day', 'monday to', 'sunday to', 'daily from',
        'mon - sun', 'mon-sun', 'saturday and sunday',
        # Contact info
        'hubungi kami', 'contact us', 'call us', 'whatsapp kami',
        'alamat kami', 'our address', 'lokasi kami', 'our location',
        # Section headers
        'menu kami', 'our menu', 'makanan kami', 'our food',
        'tentang kami', 'about us', 'kenali kami', 'our story',
        'galeri kami', 'our gallery',
        # Footer/header content
        'hak cipta', 'copyright', 'all rights reserved', 'powered by',
        'follow us', 'ikuti kami', 'social media',
        # Navigation
        'laman utama', 'home page', 'kembali ke', 'back to',
        # Price labels (not actual prices)
        'harga bermula', 'price starts', 'senarai harga', 'price list',
    ]

    # Skip words - individual words that indicate non-menu content
    # These are matched as whole words only (not substrings)
    skip_words = [
        'waktu', 'operasi', 'operating', 'hours', 'hubungi', 'contact',
        'alamat', 'address', 'lokasi', 'location', 'tentang', 'about',
        'footer', 'header', 'nav', 'navigation', 'copyright', 'powered',
        'terma', 'terms', 'privacy', 'polisi', 'policy',
        'subscribe', 'newsletter', 'telefon', 'telephone',
        'facebook', 'instagram', 'tiktok', 'twitter', 'youtube',
        'scan', 'imbas', 'qrcode', 'whatsapp', 'saya', 'kami',
        'welcome', 'selamat', 'datang', 'home', 'laman', 'gallery', 'galeri',
    ]

    # ========================================================================
    # HTML PARSER - Extract structured data from HTML
    # ========================================================================
    class MenuCardParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.cards = []  # List of extracted cards
            self.current_card = None
            self.in_card = False
            self.in_heading = False
            self.in_paragraph = False
            self.current_tag = None
            self.card_depth = 0
            self.heading_text = ""
            self.paragraph_text = ""
            self.found_sections = []  # Track sections like menu, gallery
            self.in_menu_section = False

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            class_attr = attrs_dict.get('class', '').lower()
            id_attr = attrs_dict.get('id', '').lower()

            # Detect menu/gallery sections
            if tag in ['section', 'div']:
                if any(x in class_attr or x in id_attr for x in ['menu', 'gallery', 'products', 'grid']):
                    self.in_menu_section = True
                    self.found_sections.append(tag)

            # Detect card containers
            if tag in ['div', 'article', 'li', 'figure']:
                if any(x in class_attr for x in ['card', 'item', 'product', 'menu-item', 'gallery-item']):
                    self.in_card = True
                    self.card_depth += 1
                    self.current_card = {
                        'name': '',
                        'image': '',
                        'price': 0,
                        'description': '',
                        'raw_text': ''
                    }

            # Track nested depth
            if self.in_card and tag in ['div', 'article', 'li', 'figure']:
                self.card_depth += 1

            # Get image URL
            if tag == 'img' and self.in_card:
                src = attrs_dict.get('src', '')
                if src and 'placeholder' not in src.lower():
                    self.current_card['image'] = src

            # Track headings
            if tag in ['h2', 'h3', 'h4', 'h5', 'h6']:
                self.in_heading = True
                self.heading_text = ""

            # Track paragraphs
            if tag == 'p':
                self.in_paragraph = True
                self.paragraph_text = ""

        def handle_endtag(self, tag):
            if tag in ['h2', 'h3', 'h4', 'h5', 'h6'] and self.in_heading:
                self.in_heading = False
                if self.in_card and self.heading_text.strip():
                    self.current_card['name'] = self.heading_text.strip()

            if tag == 'p' and self.in_paragraph:
                self.in_paragraph = False
                if self.in_card and self.paragraph_text.strip():
                    # Store first paragraph as description
                    if not self.current_card['description']:
                        self.current_card['description'] = self.paragraph_text.strip()[:150]

            # Close card
            if self.in_card and tag in ['div', 'article', 'li', 'figure']:
                self.card_depth -= 1
                if self.card_depth <= 0:
                    self.in_card = False
                    self.card_depth = 0
                    if self.current_card and self.current_card.get('name'):
                        self.cards.append(self.current_card)
                    self.current_card = None

            # Exit menu section
            if tag in ['section', 'div'] and self.found_sections:
                if self.found_sections[-1] == tag:
                    self.found_sections.pop()
                    if not self.found_sections:
                        self.in_menu_section = False

        def handle_data(self, data):
            text = data.strip()
            if not text:
                return

            if self.in_heading:
                self.heading_text += " " + text

            if self.in_paragraph:
                self.paragraph_text += " " + text

            # Collect raw text for price extraction
            if self.in_card and self.current_card:
                self.current_card['raw_text'] += " " + text

    # ========================================================================
    # PARSE HTML
    # ========================================================================
    try:
        parser = MenuCardParser()
        parser.feed(html)
        extracted_cards = parser.cards
        logger.info(f"   HTMLParser found {len(extracted_cards)} potential cards")
    except Exception as e:
        logger.error(f"   HTMLParser error: {e}")
        extracted_cards = []

    # ========================================================================
    # FALLBACK: Regex extraction if parser finds nothing
    # ========================================================================
    if not extracted_cards:
        logger.info("   Using regex fallback extraction...")
        # Find cards with class containing card/item/product
        card_pattern = r'<(?:div|article|li|figure)[^>]*class=["\'][^"\']*(?:card|item|product|menu)[^"\']*["\'][^>]*>(.*?)</(?:div|article|li|figure)>'
        blocks = re.findall(card_pattern, html, re.IGNORECASE | re.DOTALL)

        for block in blocks:
            if len(block) < 50:
                continue

            # Extract image
            img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', block, re.IGNORECASE)
            image = img_match.group(1) if img_match else ''

            # Extract heading
            name_match = re.search(r'<h[2-6][^>]*>([^<]+)</h[2-6]>', block, re.IGNORECASE)
            name = name_match.group(1).strip() if name_match else ''

            # Extract description
            desc_match = re.search(r'<p[^>]*>([^<]{10,150})</p>', block, re.IGNORECASE)
            desc = desc_match.group(1).strip() if desc_match else ''

            if name:
                extracted_cards.append({
                    'name': name,
                    'image': image,
                    'description': desc,
                    'raw_text': block,
                    'price': 0
                })

    # ========================================================================
    # PROCESS EXTRACTED CARDS
    # ========================================================================
    item_id = 1

    for card in extracted_cards:
        name = card.get('name', '').strip()
        if not name:
            continue

        name_lower = name.lower()

        # ====================================================================
        # SKIP CHECK 1: Full phrase matching (CRITICAL for "Buka Setiap Hari")
        # ====================================================================
        skip_this = False
        for phrase in skip_phrases:
            if phrase in name_lower:
                logger.info(f"   ✗ Skipped (phrase match '{phrase}'): {name}")
                skip_this = True
                break
        if skip_this:
            continue

        # ====================================================================
        # SKIP CHECK 2: Individual word matching
        # ====================================================================
        if any(word in name_lower for word in skip_words):
            logger.info(f"   ✗ Skipped (word match): {name}")
            continue

        # ====================================================================
        # SKIP CHECK 3: Name too short or too long
        # ====================================================================
        if len(name) < 2 or len(name) > 60:
            continue

        # ====================================================================
        # SKIP CHECK 4: Name is just numbers/special chars
        # ====================================================================
        if not re.search(r'[a-zA-Z\u0080-\uFFFF]{2,}', name):
            continue

        # ====================================================================
        # SKIP CHECK 5: Looks like time pattern (7am, 10:00, etc.)
        # ====================================================================
        if re.search(r'\d{1,2}[:.]\d{2}|\d{1,2}\s*(am|pm|pagi|petang|malam)', name_lower):
            logger.info(f"   ✗ Skipped (time pattern): {name}")
            continue

        # ====================================================================
        # EXTRACT PRICE from raw text
        # ====================================================================
        raw_text = card.get('raw_text', '')
        price_match = re.search(r'RM\s*(\d{1,3}(?:\.\d{2})?)', raw_text, re.IGNORECASE)
        price = float(price_match.group(1)) if price_match else 0

        # Price sanity check (RM 1 - RM 500)
        if price < 1 or price > 500:
            # Try to find price in entire card block
            price = 15.0  # Default price if not found

        # ====================================================================
        # GET IMAGE URL
        # ====================================================================
        image_url = card.get('image', '')
        if not image_url or 'placeholder' in image_url.lower():
            # Use business-type appropriate default image
            if business_type == 'food':
                image_url = 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80'  # Malaysian food
            elif business_type == 'clothing':
                image_url = 'https://images.unsplash.com/photo-1445205170230-053b83016050?w=600&q=80'  # Fashion
            else:
                image_url = 'https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=600&q=80'  # Products

        # ====================================================================
        # GET DESCRIPTION
        # ====================================================================
        description = card.get('description', '')
        if description:
            desc_lower = description.lower()
            # Skip if description looks like operating hours
            if any(skip in desc_lower for skip in ['waktu', 'operasi', 'hour', 'am', 'pm', 'isnin', 'ahad', 'monday', 'sunday', 'buka', 'tutup']):
                description = ''

        if not description:
            if business_type == 'food':
                description = 'Hidangan istimewa dari dapur kami'
            elif business_type == 'clothing':
                description = 'Koleksi pilihan berkualiti tinggi'
            else:
                description = 'Produk pilihan kami'

        # ====================================================================
        # DETECT CATEGORY based on business type
        # ====================================================================
        category = detect_item_category(name, business_type)

        # ====================================================================
        # CREATE MENU ITEM
        # ====================================================================
        menu_item = {
            "id": f"menu-{item_id}",
            "name": name,
            "description": description,
            "price": price,
            "image_url": image_url,
            "category_id": category,
            "is_available": True
        }
        menu_items.append(menu_item)
        logger.info(f"   ✓ Extracted: {name} - RM{price} [{category}]")
        item_id += 1

        # Limit to 20 items
        if len(menu_items) >= 20:
            break

    logger.info(f"   Total extracted: {len(menu_items)} menu items")
    return menu_items


@router.post("/generate")
async def generate_website(request: SimpleGenerateRequest):
    """
    Generate complete website from description

    This endpoint:
    - Accepts description in Bahasa Malaysia or English
    - Detects website type automatically
    - Auto-injects integrations based on detected features
    - Returns complete, functional HTML
    - Supports multi-style generation (Modern, Minimal, Bold)
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 NEW GENERATION REQUEST RECEIVED")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Description length: {len(request.description)} chars")
        logger.info(f"Description preview: {request.description[:100]}...")
        logger.info(f"Multi-style: {request.multi_style}")
        logger.info(f"Generate previews: {request.generate_previews}")
        logger.info(f"Generation mode: {request.mode}")
        logger.info(f"Images: {len(request.images) if request.images else 0}")
        logger.info("=" * 80)

        # ==================== CONTENT MODERATION ====================
        # Check for illegal/harmful content BEFORE generation
        is_allowed, block_reason = is_content_allowed(request.description)
        if not is_allowed:
            log_blocked_attempt(
                description=request.description,
                reason=block_reason,
                user_id=request.user_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=block_reason
            )
        logger.info("✅ Content moderation check passed")

        # Detect website type
        logger.info("Step 1: Detecting website type...")
        website_type = template_service.detect_website_type(request.description)
        logger.info(f"✓ Detected website type: {website_type}")

        # Detect business type for categories (food, clothing, services, general)
        business_type = request.business_type or detect_business_type(request.description)
        logger.info(f"✓ Detected business type: {business_type}")

        # Detect required features
        logger.info("Step 2: Detecting features...")
        features = template_service.detect_features(request.description)

        # Merge user-selected features from frontend
        if request.features:
            logger.info(f"User-selected features: {request.features}")
            # Add features that user explicitly selected
            if request.features.get("deliverySystem"):
                if "delivery_system" not in features:
                    features.append("delivery_system")
            if request.features.get("googleMap"):
                if "maps" not in features:
                    features.append("maps")
            if request.features.get("contactForm"):
                if "contact" not in features:
                    features.append("contact")
            if request.features.get("socialMedia"):
                if "social" not in features:
                    features.append("social")
            # WhatsApp is usually included by default, but respect if user disabled it
            if not request.features.get("whatsapp", True) and "whatsapp" in features:
                features.remove("whatsapp")

        logger.info(f"✓ Final features: {features}")

        # Extract business name from description (simple extraction)
        logger.info("Step 3: Extracting business information...")
        business_name = extract_business_name(request.description)
        logger.info(f"✓ Business name: {business_name}")

        # Detect language
        language = detect_language(request.description)
        logger.info(f"✓ Language: {language}")

        # Extract phone number if mentioned
        phone_number = extract_phone_number(request.description)
        logger.info(f"✓ Phone: {phone_number or 'Not found'}")

        # Extract address if mentioned
        address = extract_address(request.description)
        logger.info(f"✓ Address: {address or 'Not found'}")

        # Log assets
        if request.logo:
            logger.info(f"✓ Logo: {request.logo}")
        if request.fonts and len(request.fonts) > 0:
            logger.info(f"✓ Fonts: {', '.join(request.fonts)}")
        if request.colors:
            logger.info(f"✓ Colors: {request.colors}")
        if request.theme:
            logger.info(f"✓ Theme: {request.theme}")

        # Build AI generation request
        ai_request = WebsiteGenerationRequest(
            description=request.description,
            business_name=business_name,
            business_type=website_type,
            language=language,
            subdomain="preview",  # Placeholder
            include_whatsapp=("whatsapp" in features),
            whatsapp_number=phone_number if phone_number else "+60123456789",
            include_maps=("maps" in features),
            location_address=address if address else "",
            include_ecommerce=("cart" in features),
            contact_email=None,
            uploaded_images=request.images if request.images else [],
            logo=request.logo,
            fonts=request.fonts if request.fonts else [],
            colors=request.colors,
            theme=request.theme
        )

        # Log uploaded images
        if request.images and len(request.images) > 0:
            logger.info(f"✓ User uploaded {len(request.images)} images:")
            for i, img in enumerate(request.images):
                logger.info(f"   Image {i+1}: {img}")

        # Create menu items from uploaded images (for ordering system)
        # CRITICAL FIX: Only use user's uploaded items with their prices - NO AI extraction
        menu_items = []
        if request.images and len(request.images) > 0:
            logger.info(f"🍽️ Creating menu items from {len(request.images)} user-uploaded images...")
            default_prices = [15, 12, 18, 10, 20, 14, 16, 13]  # Fallback prices only if user didn't set

            # Get business-type specific descriptions
            biz_config = get_business_config(business_type)
            default_desc = biz_config.get("item_description_default", "Produk pilihan kami")

            for idx, img in enumerate(request.images):
                # Extract image data
                if isinstance(img, dict):
                    img_url = img.get('url', '')
                    img_name = img.get('name', f'Item {idx+1}')
                    # CRITICAL FIX: Use user's price if provided
                    user_price = img.get('price')
                    if user_price:
                        try:
                            img_price = float(str(user_price).replace('RM', '').replace(',', '').strip())
                        except (ValueError, TypeError):
                            img_price = default_prices[idx % len(default_prices)]
                    else:
                        img_price = default_prices[idx % len(default_prices)]
                else:
                    img_url = str(img)
                    img_name = f'Item {idx+1}'
                    img_price = default_prices[idx % len(default_prices)]

                # Skip hero image (first image is usually hero)
                if idx == 0 and 'hero' in img_name.lower():
                    continue

                # Skip empty names or "Hero Image"
                if not img_name or img_name == 'Hero Image' or img_name == '':
                    continue

                # CRITICAL FIX: Validate menu item name to prevent hallucinated items
                if not is_valid_menu_item_name(img_name):
                    logger.warning(f"   ⚠️ Skipping invalid menu item name: '{img_name}'")
                    continue

                # Auto-detect category based on item name and business type
                category = detect_item_category(img_name, business_type)

                # Create menu item
                menu_item = {
                    "id": f"menu-{idx}",
                    "name": img_name,
                    "description": default_desc,
                    "price": img_price,  # FIXED: Use user's price
                    "image_url": img_url,
                    "category_id": category,
                    "is_available": True
                }
                menu_items.append(menu_item)
                logger.info(f"   ✅ Added menu item: {img_name} - RM{img_price:.2f} [{category}]")

        # Create delivery zones if delivery feature is enabled
        # CRITICAL FIX: Check BOTH request.delivery AND request.fulfillment for zone info
        # Frontend sends area in request.delivery.area OR request.fulfillment.delivery_area
        delivery_zones = []
        if request.features and request.features.get("deliverySystem"):
            delivery_data = request.delivery or {}
            fulfillment_data = request.fulfillment or {}
            
            # Get zone name from multiple sources (in order of priority)
            zone_name = (
                delivery_data.get("area") or 
                fulfillment_data.get("delivery_area") or 
                "Kawasan Delivery"
            )
            
            # Get delivery fee from multiple sources
            fee_raw = delivery_data.get("fee") or fulfillment_data.get("delivery_fee") or "5"
            if isinstance(fee_raw, str):
                fee_value = float(fee_raw.replace("RM", "").replace(",", "").strip()) if fee_raw else 5.0
            else:
                fee_value = float(fee_raw) if fee_raw else 5.0
            
            default_zone = {
                "id": "default",
                "zone_name": zone_name,
                "delivery_fee": fee_value,
                "estimated_time": delivery_data.get("hours", "30-45 min"),
                "is_active": True
            }
            delivery_zones = [default_zone]
            logger.info(f"✅ Created delivery zone: {zone_name} - RM{fee_value:.2f}")

        # User data for integrations
        user_data = {
            "phone": phone_number if phone_number else "+60123456789",
            "address": address if address else "",
            "email": "contact@business.com",
            "url": "https://preview.binaapp.my",
            "whatsapp_message": "Hi, I'm interested",
            "business_name": business_name,
            "business_type": business_type,  # For dynamic categories
            "description": request.description,  # For business type detection
            "menu_items": menu_items,
            "delivery_zones": delivery_zones
        }

        # Add delivery info if provided
        if request.delivery:
            user_data["delivery"] = request.delivery

        # Dual AI generation mode - return both designs
        if request.mode == "dual":
            logger.info("=" * 80)
            logger.info("Step 4: DUAL AI GENERATION")
            logger.info("Calling both Qwen and DeepSeek in parallel...")
            logger.info("=" * 80)

            dual_results = await ai_service.generate_website_dual(ai_request)

            # CRITICAL FIX: Do NOT extract menu items from AI-generated HTML!
            # This was causing hallucinated items like "WhatsApp", "SAYA" to appear as menu items.
            # Only use user's uploaded menu items from the form.
            if menu_items:
                logger.info(f"✅ Using {len(menu_items)} user-uploaded menu items (NOT extracting from AI HTML)")
                user_data["menu_items"] = menu_items
            else:
                logger.info("⚠️ No user-uploaded menu items found")

            # Inject integrations into both designs
            qwen_html = None
            deepseek_html = None

            if dual_results["qwen"]:
                qwen_html = template_service.inject_integrations(
                    dual_results["qwen"],
                    features,
                    user_data
                )

            if dual_results["deepseek"]:
                deepseek_html = template_service.inject_integrations(
                    dual_results["deepseek"],
                    features,
                    user_data
                )

            logger.info(f"✓ Dual generation complete")

            return DualGenerateResponse(
                qwen_html=qwen_html,
                deepseek_html=deepseek_html,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Best-of-both mode - combine best parts
        elif request.mode == "best":
            logger.info("=" * 80)
            logger.info("Step 4: BEST-OF-BOTH GENERATION")
            logger.info("Generating with both AIs and combining best parts...")
            logger.info("=" * 80)

            html_content = await ai_service.generate_website_best(ai_request)

            # CRITICAL FIX: Do NOT extract menu items from AI-generated HTML!
            # This was causing hallucinated items like "WhatsApp", "SAYA" to appear as menu items.
            # Only use user's uploaded menu items from the form.
            if menu_items:
                logger.info(f"✅ Using {len(menu_items)} user-uploaded menu items (NOT extracting from AI HTML)")
                user_data["menu_items"] = menu_items
            else:
                logger.info("⚠️ No user-uploaded menu items found")

            # Inject integrations
            html_content = template_service.inject_integrations(
                html_content,
                features,
                user_data
            )

            logger.info("✓ Best-of-both generation complete")

            return SimpleGenerateResponse(
                html=html_content,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Strategic mode - task-based routing (DeepSeek for code, Qwen for content)
        elif request.mode == "strategic":
            logger.info("=" * 80)
            logger.info("Step 4: STRATEGIC TASK-BASED GENERATION")
            logger.info("Using DeepSeek for code structure, Qwen for content...")
            logger.info("=" * 80)

            ai_response = await ai_service.generate_website_strategic(ai_request)

            # Get the generated HTML
            html_content = ai_response.html_content

            # CRITICAL FIX: Do NOT extract menu items from AI-generated HTML!
            # This was causing hallucinated items like "WhatsApp", "SAYA" to appear as menu items.
            # Only use user's uploaded menu items from the form.
            if menu_items:
                logger.info(f"✅ Using {len(menu_items)} user-uploaded menu items (NOT extracting from AI HTML)")
                user_data["menu_items"] = menu_items
            else:
                logger.info("⚠️ No user-uploaded menu items found")

            # Inject additional integrations
            html_content = template_service.inject_integrations(
                html_content,
                features,
                user_data
            )

            logger.info("✓ Strategic generation complete")

            return SimpleGenerateResponse(
                html=html_content,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Multi-style generation
        elif request.multi_style:
            logger.info("=" * 80)
            logger.info("Step 4: MULTI-STYLE GENERATION")
            logger.info("Calling AI service to generate 3 style variations...")
            logger.info("=" * 80)
            variations_dict = await ai_service.generate_multi_style(ai_request)
            logger.info(f"✓ Received {len(variations_dict)} variations from AI service")

            # CRITICAL FIX: Do NOT extract menu items from AI-generated HTML!
            # This was causing hallucinated items like "WhatsApp", "SAYA" to appear as menu items.
            # Only use user's uploaded menu items from the form.
            if menu_items:
                logger.info(f"✅ Using {len(menu_items)} user-uploaded menu items (NOT extracting from AI HTML)")
                user_data["menu_items"] = menu_items
            else:
                logger.info("⚠️ No user-uploaded menu items found")

            # Process each variation
            variations = []
            for style, ai_response in variations_dict.items():
                html_content = ai_response.html_content

                # Inject integrations
                html_content = template_service.inject_integrations(
                    html_content,
                    features,
                    user_data
                )

                variations.append({
                    "style": style,
                    "html": html_content
                })

            logger.info(f"Generated {len(variations)} style variations successfully!")

            # Generate previews if requested
            if request.generate_previews:
                logger.info("Generating preview thumbnails...")
                try:
                    variations = await screenshot_service.generate_variation_previews(variations)
                    logger.info("Preview thumbnails generated successfully")
                except Exception as e:
                    logger.warning(f"Failed to generate previews: {e}")
                    # Continue without previews

            # Convert to StyleVariation objects
            variations = [
                StyleVariation(
                    style=v.get("style"),
                    html=v.get("html"),
                    thumbnail=v.get("thumbnail"),
                    social_preview=v.get("social_preview")
                )
                for v in variations
            ]

            return MultiStyleResponse(
                variations=variations,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Single style generation (original behavior)
        else:
            logger.info("=" * 80)
            logger.info("Step 4: SINGLE-STYLE GENERATION")
            logger.info("Calling AI service to generate website...")
            logger.info("=" * 80)
            ai_response = await ai_service.generate_website(ai_request)
            logger.info("✓ Received response from AI service")

            # Get the generated HTML
            html_content = ai_response.html_content

            # CRITICAL FIX: Do NOT extract menu items from AI-generated HTML!
            # This was causing hallucinated items like "WhatsApp", "SAYA" to appear as menu items.
            # 
            # Priority order for menu items:
            # 1. User's uploaded menu items (from request.images with names and prices)
            # 2. Database menu items (if website_id exists)
            # 3. DO NOT extract from AI-generated HTML!
            
            if menu_items:
                # User uploaded menu items - use them
                logger.info(f"✅ Using {len(menu_items)} user-uploaded menu items")
                user_data["menu_items"] = menu_items
            elif user_data.get("website_id"):
                # Try database as fallback
                db_menu_items = await fetch_menu_items_from_database(user_data["website_id"])
                if db_menu_items:
                    logger.info(f"✅ Using {len(db_menu_items)} menu items from DATABASE")
                    menu_items = db_menu_items
                    user_data["menu_items"] = menu_items
                else:
                    logger.info("⚠️ No menu items found in database and no user uploads")
            else:
                logger.info("⚠️ No user-uploaded menu items found")

            # Inject additional integrations
            html_content = template_service.inject_integrations(
                html_content,
                features,
                user_data
            )

            # Inject delivery widget if deliverySystem is enabled
            if request.features and request.features.get("deliverySystem") is True:
                from app.api.simple.publish import inject_delivery_widget_if_needed
                import uuid
                website_id = str(uuid.uuid4())
                html_content = inject_delivery_widget_if_needed(
                    html=html_content,
                    website_id=website_id,
                    business_name=business_name,
                    description=request.description,
                    language=request.language or "ms"
                )

            logger.info("Website generated successfully!")

            return SimpleGenerateResponse(
                html=html_content,
                detected_features=features,
                template_used=website_type,
                success=True
            )

    except Exception as e:
        import traceback
        logger.error("=" * 80)
        logger.error("❌ ERROR GENERATING WEBSITE")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate website: {type(e).__name__}: {str(e)}"
        )


def extract_business_name(description: str) -> str:
    """Extract business name from description"""
    import re

    # Look for patterns like "Kedai X", "Restoran X", "X Cafe", etc.
    patterns = [
        r'(?:kedai|restoran|cafe|salon|butik|toko)\s+([A-Za-z\s]+?)(?:\s+yang|\s+di|\s+untuk|\.|\,|$)',
        r'([A-Z][A-Za-z\s]+?)(?:\s+adalah|\s+merupakan|\s+ialah)',
        r'^([A-Z][A-Za-z\s]+?)(?:\s+-|\s+:)',
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 3 <= len(name) <= 50:
                return name

    # Fallback: use first few words
    words = description.split()[:3]
    return " ".join(words) if words else "My Business"


def detect_language(description: str) -> Language:
    """Detect if description is in Malay or English"""
    malay_keywords = ['saya', 'kami', 'yang', 'untuk', 'adalah', 'dengan', 'ini', 'dan', 'di', 'ke']

    description_lower = description.lower()
    malay_count = sum(1 for keyword in malay_keywords if keyword in description_lower)

    return Language.MALAY if malay_count >= 2 else Language.ENGLISH


def extract_phone_number(description: str) -> Optional[str]:
    """Extract phone number from description"""
    import re

    # Malaysian phone patterns
    patterns = [
        r'\+60\s?1[0-9]{1,2}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}',  # +60 format
        r'01[0-9]{1,2}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}',  # 01X format
        r'60\s?1[0-9]{1,2}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}',  # 60 format
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            phone = match.group(0)
            # Clean and format
            phone = re.sub(r'[-\s]', '', phone)
            if not phone.startswith('+'):
                if phone.startswith('60'):
                    phone = '+' + phone
                elif phone.startswith('0'):
                    phone = '+6' + phone
            return phone

    return None


def extract_address(description: str) -> Optional[str]:
    """Extract address from description"""
    import re

    # Look for address keywords
    patterns = [
        r'(?:alamat|address|lokasi|location|terletak|located)[\s:]+([^.!?]+)',
        r'(?:di|at)\s+([^.!?]+?(?:kuala lumpur|kl|selangor|penang|johor|melaka|perak|pahang|[0-9]{5}))',
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            if 10 <= len(address) <= 200:
                return address

    return None


# ==================== ASYNC GENERATION ENDPOINTS ====================

class AsyncGenerateStartResponse(BaseModel):
    """Response when starting async generation"""
    job_id: str
    status: str
    message: str


class AsyncGenerateStatusResponse(BaseModel):
    """Response for job status check"""
    job_id: str
    status: str
    progress: int
    variants: List[dict] = []
    error: Optional[str] = None
    detected_features: List[str] = []
    template_used: str = ""


def build_feature_instructions(features: dict, delivery: dict, address: str, social_media: dict) -> str:
    """Build feature instructions for AI based on user selections"""
    if not features:
        return ""

    feature_instructions = "\n\n=== REQUIRED FEATURES ===\n"

    # WhatsApp
    if features.get("whatsapp", True):
        feature_instructions += "- WhatsApp button (floating and in contact section)\n"
    else:
        feature_instructions += "- DO NOT include WhatsApp button\n"

    # Google Map
    if features.get("googleMap") and address:
        feature_instructions += f"- Google Map embed showing: {address}\n"
        feature_instructions += f"  Use iframe: <iframe src='https://maps.google.com/maps?q={address}&output=embed'>\n"

    # Delivery System
    if features.get("deliverySystem") and delivery:
        area = delivery.get('area', 'Dalam 5km')
        fee = delivery.get('fee', 'RM5')
        minimum = delivery.get('minimum', 'RM20')
        hours = delivery.get('hours', '11am-9pm')

        feature_instructions += f"""- DELIVERY SECTION with:
  - Kawasan: {area}
  - Caj: {fee}
  - Minimum order: {minimum}
  - Waktu: {hours}
  - Order button that sends WhatsApp with delivery request
  - Simple order form: Name, Phone, Address, Items, Total
"""

    # Contact Form
    if features.get("contactForm"):
        feature_instructions += "- Contact form with Name, Email, Phone, Message fields\n"

    # Social Media
    if features.get("socialMedia") and social_media:
        feature_instructions += "- Social media icons in footer"
        social_links = []
        if social_media.get('instagram'):
            social_links.append(f"Instagram ({social_media['instagram']})")
        if social_media.get('facebook'):
            social_links.append(f"Facebook ({social_media['facebook']})")
        if social_media.get('tiktok'):
            social_links.append(f"TikTok ({social_media['tiktok']})")
        if social_links:
            feature_instructions += f": {', '.join(social_links)}\n"
        else:
            feature_instructions += "\n"

    # Price List
    if features.get("priceList", True):
        feature_instructions += "- Show prices for each menu item\n"
    else:
        feature_instructions += "- DO NOT show prices (customer will ask via WhatsApp)\n"

    # Operating Hours
    if features.get("operatingHours", True):
        feature_instructions += "- Show operating hours\n"

    # Gallery
    if features.get("gallery", True):
        feature_instructions += "- Include photo gallery section\n"

    feature_instructions += "=== END FEATURES ===\n\n"

    return feature_instructions


async def generate_variants_background(job_id: str, request: SimpleGenerateRequest):
    """Background task to generate 3 website variants"""
    try:
        logger.info(f"🚀 Starting background generation for job {job_id}")
        job_service.update_status(job_id, JobStatus.PROCESSING)
        job_service.update_progress(job_id, 0)

        # Step 1: Detect website type and features
        logger.info(f"Job {job_id}: Detecting website type and features...")
        website_type = template_service.detect_website_type(request.description)
        features = template_service.detect_features(request.description)

        # Merge user-selected features from frontend
        if request.features:
            logger.info(f"User-selected features: {request.features}")
            if request.features.get("deliverySystem"):
                if "delivery_system" not in features:
                    features.append("delivery_system")
            if request.features.get("googleMap"):
                if "maps" not in features:
                    features.append("maps")
            if request.features.get("contactForm"):
                if "contact" not in features:
                    features.append("contact")
            if request.features.get("socialMedia"):
                if "social" not in features:
                    features.append("social")
            if not request.features.get("whatsapp", True) and "whatsapp" in features:
                features.remove("whatsapp")

        business_name = extract_business_name(request.description)
        language = detect_language(request.description)
        phone_number = extract_phone_number(request.description)
        address = request.address if request.address else extract_address(request.description)

        # Build feature instructions from user selections
        feature_instructions = ""
        if request.features:
            feature_instructions = build_feature_instructions(
                request.features,
                request.delivery or {},
                address or "",
                request.social_media or {}
            )
            logger.info(f"Job {job_id}: User-selected features:")
            logger.info(feature_instructions)

        # Update job metadata
        job_service.set_metadata(job_id, features, website_type)
        job_service.update_progress(job_id, 10)
        logger.info(f"Job {job_id}: Type={website_type}, Features={features}")

        # Build enhanced description with feature instructions
        enhanced_description = request.description
        if feature_instructions:
            enhanced_description = f"{request.description}\n{feature_instructions}"

        # Build AI generation request
        ai_request = WebsiteGenerationRequest(
            description=enhanced_description,
            business_name=business_name,
            business_type=website_type,
            language=language,
            subdomain="preview",
            include_whatsapp=("whatsapp" in features) or (request.features and request.features.get("whatsapp", True)),
            whatsapp_number=phone_number if phone_number else "+60123456789",
            include_maps=("maps" in features) or (request.features and request.features.get("googleMap", False)),
            location_address=address if address else "",
            include_ecommerce=("cart" in features),
            contact_email=None,
            uploaded_images=request.images if request.images else [],
            logo=request.logo,
            fonts=request.fonts if request.fonts else [],
            colors=request.colors,
            theme=request.theme
        )

        # Detect business type FIRST - needed for categories and menu items
        business_type = request.business_type or detect_business_type(request.description)
        logger.info(f"Job {job_id}: 🏢 Business type: {business_type}")

        # User data for integrations - INCLUDE business_type and description for proper category detection
        user_data = {
            "phone": phone_number if phone_number else "+60123456789",
            "address": address if address else "",
            "email": "contact@business.com",
            "url": "https://preview.binaapp.my",
            "whatsapp_message": "Hi, I'm interested",
            "business_name": business_name,
            "business_type": business_type,  # CRITICAL: Pass for dynamic categories
            "description": request.description,  # CRITICAL: Pass for business type detection
        }

        # Add social media to user_data if provided
        if request.social_media:
            user_data["social_media"] = request.social_media

        # Add delivery info to user_data if provided
        if request.delivery:
            user_data["delivery"] = request.delivery

        # Add fulfillment info to user_data if provided
        if request.fulfillment:
            user_data["fulfillment"] = request.fulfillment

        # Add payment info to user_data if provided (for QR payment support)
        if request.payment:
            user_data["payment"] = request.payment
            logger.info(f"Job {job_id}: 💳 Payment config - COD: {request.payment.get('cod')}, QR: {request.payment.get('qr')}, QR Image: {'Yes' if request.payment.get('qr_image') else 'No'}")

        # CRITICAL: Create delivery zones if delivery feature is enabled
        # CRITICAL FIX: Check BOTH request.delivery AND request.fulfillment for zone info
        # Frontend sends area in request.delivery.area OR request.fulfillment.delivery_area
        delivery_zones = []
        if request.features and request.features.get("deliverySystem"):
            delivery_data = request.delivery or {}
            fulfillment_data = request.fulfillment or {}

            # Get zone name from multiple sources (in order of priority)
            # CRITICAL FIX: Strip whitespace and check for actual content
            area_from_delivery = (delivery_data.get("area") or "").strip()
            area_from_fulfillment = (fulfillment_data.get("delivery_area") or "").strip()
            zone_name = area_from_delivery if area_from_delivery else (area_from_fulfillment if area_from_fulfillment else "Kawasan Delivery")

            # Get delivery fee from multiple sources
            fee_raw = delivery_data.get("fee") or fulfillment_data.get("delivery_fee") or "5"
            if isinstance(fee_raw, str):
                fee_value = float(fee_raw.replace("RM", "").replace(",", "").strip()) if fee_raw.strip() else 5.0
            else:
                fee_value = float(fee_raw) if fee_raw else 5.0

            # Get delivery hours/time from multiple sources
            hours_raw = delivery_data.get("hours") or fulfillment_data.get("hours") or "30-45 min"
            if isinstance(hours_raw, str):
                hours_value = hours_raw.strip() if hours_raw.strip() else "30-45 min"
            else:
                hours_value = "30-45 min"

            default_zone = {
                "id": "default",
                "zone_name": zone_name,
                "delivery_fee": fee_value,
                "estimated_time": hours_value,
                "is_active": True
            }
            delivery_zones = [default_zone]
            logger.info(f"Job {job_id}: ✅ Created delivery zone: {zone_name} - RM{fee_value:.2f}")
        
        # Add delivery_zones to user_data
        user_data["delivery_zones"] = delivery_zones
        logger.info(f"Job {job_id}: Delivery zones in user_data: {len(delivery_zones)}")

        # Create menu items from uploaded images (for ordering system)
        # CRITICAL FIX: Use user's prices and validate names to prevent hallucinated items
        menu_items = []
        if request.images and len(request.images) > 0:
            logger.info(f"Job {job_id}: 🍽️ Creating menu items from {len(request.images)} user-uploaded images...")
            default_prices = [15, 12, 18, 10, 20, 14, 16, 13]  # Fallback prices only if user didn't set

            # Get business-type specific descriptions (business_type already defined above)
            biz_config = get_business_config(business_type)
            default_desc = biz_config.get("item_description_default", "Hidangan istimewa dari dapur kami")

            for idx, img in enumerate(request.images):
                # Extract image data
                if isinstance(img, dict):
                    img_url = img.get('url', '')
                    img_name = img.get('name', f'Item {idx+1}')
                    # CRITICAL FIX: Use user's price if provided
                    user_price = img.get('price')
                    if user_price:
                        try:
                            img_price = float(str(user_price).replace('RM', '').replace(',', '').strip())
                        except (ValueError, TypeError):
                            img_price = default_prices[idx % len(default_prices)]
                    else:
                        img_price = default_prices[idx % len(default_prices)]
                else:
                    img_url = str(img)
                    img_name = f'Item {idx+1}'
                    img_price = default_prices[idx % len(default_prices)]

                # Skip hero image (first image is usually hero)
                if idx == 0 and 'hero' in img_name.lower():
                    continue

                # Skip empty names or "Hero Image"
                if not img_name or img_name == 'Hero Image' or img_name == '':
                    continue

                # CRITICAL FIX: Validate menu item name to prevent hallucinated items
                if not is_valid_menu_item_name(img_name):
                    logger.warning(f"Job {job_id}:    ⚠️ Skipping invalid menu item name: '{img_name}'")
                    continue

                # Auto-detect category based on item name and business type
                category = detect_item_category(img_name, business_type)

                # Create menu item
                menu_item = {
                    "id": f"menu-{idx}",
                    "name": img_name,
                    "description": default_desc,
                    "price": img_price,  # FIXED: Use user's price
                    "image_url": img_url,
                    "category_id": category,  # FIXED: Use detected category
                    "is_available": True
                }
                menu_items.append(menu_item)
                logger.info(f"Job {job_id}:    ✅ Added menu item: {img_name} - RM{img_price:.2f} [{category}]")

        # Add menu items to user_data
        if menu_items:
            user_data["menu_items"] = menu_items
            logger.info(f"Job {job_id}: Created {len(menu_items)} menu items for ordering system")
        else:
            # Create default menu items if none provided but delivery is enabled
            if request.features and request.features.get("deliverySystem"):
                default_menu_items = [
                    {"id": "1", "name": "Nasi Lemak Special", "description": "Nasi lemak dengan ayam goreng, sambal, dan telur", "price": 12.0, "image_url": "https://images.unsplash.com/photo-1598514983318-2f64f8f4796c?w=600&q=80", "category_id": "nasi"},
                    {"id": "2", "name": "Nasi Goreng Kampung", "description": "Nasi goreng dengan ikan bilis dan telur mata", "price": 10.0, "image_url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80", "category_id": "nasi"},
                    {"id": "3", "name": "Ayam Goreng Berempah", "description": "Ayam goreng rangup dengan rempah pilihan", "price": 8.0, "image_url": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=600&q=80", "category_id": "lauk"},
                    {"id": "4", "name": "Teh Tarik", "description": "Teh tarik panas atau sejuk", "price": 3.0, "image_url": "https://images.unsplash.com/photo-1571934811356-5cc061b6821f?w=600&q=80", "category_id": "minuman"},
                ]
                user_data["menu_items"] = default_menu_items
                logger.info(f"Job {job_id}: Created {len(default_menu_items)} default menu items for delivery system")
            else:
                logger.warning(f"Job {job_id}: No menu items created - ordering system will be empty")

        # Step 2: Generate 3 style variations
        job_service.update_progress(job_id, 20)
        logger.info(f"Job {job_id}: Generating 3 style variations...")
        variations_dict = await ai_service.generate_multi_style(ai_request)
        job_service.update_progress(job_id, 30)
        logger.info(f"Job {job_id}: Received {len(variations_dict)} variations from AI")

        # Process each variation
        for idx, (style, ai_response) in enumerate(variations_dict.items()):
            try:
                logger.info(f"Job {job_id}: Processing variant {idx+1}/3 ({style})...")

                html_content = ai_response.html_content

                # Inject integrations
                html_content = template_service.inject_integrations(
                    html_content,
                    features,
                    user_data
                )

                variant = {
                    "style": style,
                    "html": html_content,
                    "thumbnail": None,
                    "social_preview": None
                }

                # Add variant to job
                job_service.add_variant(job_id, variant)

                # Update progress: 50%, 70%, 90% (we already hit 30% before AI generation)
                # Progress formula: 30% + (variant_number / 3) * 60%
                progress = 30 + int(((idx + 1) / 3) * 60)
                job_service.update_progress(job_id, progress)
                logger.info(f"Job {job_id}: Progress {progress}% - Variant {idx+1} completed")

            except Exception as e:
                logger.error(f"Job {job_id}: Error processing variant {idx+1}: {e}")
                # Continue with other variants even if one fails

        # Step 3: Mark as completed
        job_service.update_status(job_id, JobStatus.COMPLETED)
        job_service.update_progress(job_id, 100)
        logger.info(f"✅ Job {job_id} completed successfully with {len(variations_dict)} variants")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"❌ Job {job_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        job_service.update_status(job_id, JobStatus.FAILED, error=error_msg)
        job_service.update_progress(job_id, 0)


@router.post("/generate/start", response_model=AsyncGenerateStartResponse)
async def start_async_generation(request: SimpleGenerateRequest, background_tasks: BackgroundTasks):
    """
    Start async website generation (returns immediately)

    This endpoint:
    - Creates a generation job
    - Returns job_id immediately (< 1 second)
    - Generates 3 design variants in the background
    - Client polls /generate/status/{job_id} for updates
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 ASYNC GENERATION START")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Description: {request.description[:100]}...")
        logger.info("=" * 80)

        # ==================== CONTENT MODERATION ====================
        # Check for illegal/harmful content BEFORE generation
        is_allowed, block_reason = is_content_allowed(request.description)
        if not is_allowed:
            log_blocked_attempt(
                description=request.description,
                reason=block_reason,
                user_id=request.user_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=block_reason
            )
        logger.info("✅ Content moderation check passed")

        # Create job
        request_data = request.dict()
        job_id = job_service.create_job(
            user_id=request.user_id or "demo-user",
            description=request.description,
            request_data=request_data
        )

        # Start background task
        background_tasks.add_task(generate_variants_background, job_id, request)

        logger.info(f"✅ Job {job_id} created and queued for processing")

        return AsyncGenerateStartResponse(
            job_id=job_id,
            status="pending",
            message="Generation started. Poll /generate/status/{job_id} for updates."
        )

    except Exception as e:
        import traceback
        logger.error(f"Failed to start async generation: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start generation: {str(e)}"
        )


@router.get("/generate/status/{job_id}", response_model=AsyncGenerateStatusResponse)
async def get_generation_status(job_id: str):
    """
    Get status of async generation job

    Returns:
    - status: pending, processing, completed, failed
    - progress: 0-100
    - variants: List of completed variants (populated as they're generated)
    """
    try:
        job_status = job_service.get_job_status(job_id)

        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        return AsyncGenerateStatusResponse(**job_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/generate/result/{job_id}")
async def get_generation_result(job_id: str):
    """
    Get completed generation result

    Returns full result when job is completed
    Throws 404 if job not found
    Throws 425 (Too Early) if job not completed yet
    """
    try:
        job = job_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        if job.status == JobStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation failed: {job.error}"
            )

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=425,  # Too Early
                detail=f"Job not completed yet. Status: {job.status.value}, Progress: {job.progress}%"
            )

        # Convert variants to StyleVariation format
        variations = [
            StyleVariation(
                style=v.get("style"),
                html=v.get("html"),
                thumbnail=v.get("thumbnail"),
                social_preview=v.get("social_preview")
            )
            for v in job.variants
        ]

        return MultiStyleResponse(
            variations=variations,
            detected_features=job.detected_features,
            template_used=job.template_used,
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job result: {str(e)}"
        )


@router.post("/generate/stream")
async def generate_stream(request: SimpleGenerateRequest):
    """
    Generate website with Server-Sent Events (SSE)

    This endpoint:
    - Uses SSE to stream real-time progress updates
    - No background tasks (works on Render!)
    - No polling required
    - Single persistent connection
    - Returns final HTML when complete
    """
    async def event_generator():
        try:
            logger.info("=" * 80)
            logger.info("🚀 SSE GENERATION REQUEST")
            logger.info(f"User ID: {request.user_id}")
            logger.info(f"Description: {request.description[:100]}...")
            logger.info(f"Multi-style: {request.multi_style}")
            logger.info("=" * 80)

            # ==================== CONTENT MODERATION ====================
            # Check for illegal/harmful content BEFORE generation
            is_allowed, block_reason = is_content_allowed(request.description)
            if not is_allowed:
                log_blocked_attempt(
                    description=request.description,
                    reason=block_reason,
                    user_id=request.user_id
                )
                yield f"data: {json.dumps({'progress': 0, 'status': 'failed', 'error': block_reason, 'message': 'Kandungan disekat / Content blocked'})}\n\n"
                return
            logger.info("✅ Content moderation check passed")

            # Progress 10% - Starting
            yield f"data: {json.dumps({'progress': 10, 'status': 'processing', 'message': 'Menganalisis perniagaan anda...'})}\n\n"
            await asyncio.sleep(0.1)

            # Detect website type and features
            logger.info("Step 1: Detecting website type and features...")
            website_type = template_service.detect_website_type(request.description)
            features = template_service.detect_features(request.description)

            # Merge user-selected features from frontend
            if request.features:
                logger.info(f"User-selected features: {request.features}")
                if request.features.get("deliverySystem"):
                    if "delivery_system" not in features:
                        features.append("delivery_system")
                if request.features.get("googleMap"):
                    if "maps" not in features:
                        features.append("maps")
                if request.features.get("contactForm"):
                    if "contact" not in features:
                        features.append("contact")
                if request.features.get("socialMedia"):
                    if "social" not in features:
                        features.append("social")
                if not request.features.get("whatsapp", True) and "whatsapp" in features:
                    features.remove("whatsapp")

            business_name = extract_business_name(request.description)
            language = detect_language(request.description)
            phone_number = extract_phone_number(request.description)
            address = extract_address(request.description)

            logger.info(f"✓ Type={website_type}, Features={features}")

            # Progress 20%
            yield f"data: {json.dumps({'progress': 20, 'status': 'processing', 'message': 'Menyediakan reka bentuk...', 'detected_features': features, 'template_used': website_type})}\n\n"
            await asyncio.sleep(0.1)

            # Build AI generation request
            ai_request = WebsiteGenerationRequest(
                description=request.description,
                business_name=business_name,
                business_type=website_type,
                language=language,
                subdomain="preview",
                include_whatsapp=("whatsapp" in features),
                whatsapp_number=phone_number if phone_number else "+60123456789",
                include_maps=("maps" in features),
                location_address=address if address else "",
                include_ecommerce=("cart" in features),
                contact_email=None,
                uploaded_images=request.images if request.images else [],
                logo=request.logo,
                fonts=request.fonts if request.fonts else [],
                colors=request.colors,
                theme=request.theme
            )

            # User data for integrations
            user_data = {
                "phone": phone_number if phone_number else "+60123456789",
                "address": address if address else "",
                "email": "contact@business.com",
                "url": "https://preview.binaapp.my",
                "whatsapp_message": "Hi, I'm interested"
            }

            # Multi-style generation
            if request.multi_style:
                logger.info("Generating 3 style variations with SSE...")

                # Progress 30%
                yield f"data: {json.dumps({'progress': 30, 'status': 'processing', 'message': 'AI sedang menjana 3 reka bentuk...'})}\n\n"

                # Generate all 3 styles
                variations_dict = await ai_service.generate_multi_style(ai_request)
                logger.info(f"✓ Received {len(variations_dict)} variations from AI")

                # Process each variation
                variations = []
                for idx, (style, ai_response) in enumerate(variations_dict.items()):
                    logger.info(f"Processing {style} variant ({idx+1}/3)...")

                    html_content = ai_response.html_content

                    # Inject integrations
                    html_content = template_service.inject_integrations(
                        html_content,
                        features,
                        user_data
                    )

                    variant = {
                        "style": style,
                        "html": html_content,
                        "thumbnail": None,
                        "social_preview": None
                    }

                    variations.append(variant)

                    # Update progress: 40%, 70%, 100%
                    progress = 40 + int(((idx + 1) / 3) * 60)
                    message = f"Reka bentuk {style.upper()} siap! ({idx+1}/3)"
                    yield f"data: {json.dumps({'progress': progress, 'status': 'processing', 'message': message})}\n\n"
                    await asyncio.sleep(0.1)

                # Progress 100% - Completed
                logger.info(f"✅ SSE generation completed with {len(variations)} variants")
                yield f"data: {json.dumps({'progress': 100, 'status': 'completed', 'message': 'Siap!', 'variants': variations, 'detected_features': features, 'template_used': website_type})}\n\n"

            else:
                # Single style generation
                logger.info("Generating single style with SSE...")

                # Progress 50%
                yield f"data: {json.dumps({'progress': 50, 'status': 'processing', 'message': 'AI sedang menulis kod...'})}\n\n"

                # Generate website
                ai_response = await ai_service.generate_website(ai_request)
                html_content = ai_response.html_content

                # Inject integrations
                html_content = template_service.inject_integrations(
                    html_content,
                    features,
                    user_data
                )

                # Progress 100% - Completed
                logger.info("✅ SSE generation completed")
                yield f"data: {json.dumps({'progress': 100, 'status': 'completed', 'message': 'Siap!', 'html': html_content, 'detected_features': features, 'template_used': website_type})}\n\n"

        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ SSE generation failed: {error_msg}")
            logger.error(traceback.format_exc())
            yield f"data: {json.dumps({'progress': 0, 'status': 'failed', 'error': error_msg, 'message': 'Ralat berlaku'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/api/generate-simple")
async def generate_website_simple(request: SimpleGenerateRequest):
    """
    Simple JSON endpoint - No SSE, returns complete result

    This endpoint:
    - Returns regular JSON (not SSE)
    - Uses Stability AI for custom images (if STABILITY_API_KEY is set)
    - Falls back to stock images if Stability unavailable
    - Works perfectly with Render backend
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 SIMPLE JSON GENERATION REQUEST")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Description: {request.description[:100]}...")
        logger.info("=" * 80)

        # ==================== CONTENT MODERATION ====================
        # Check for illegal/harmful content BEFORE generation
        is_allowed, block_reason = is_content_allowed(request.description)
        if not is_allowed:
            log_blocked_attempt(
                description=request.description,
                reason=block_reason,
                user_id=request.user_id
            )
            return {
                "success": False,
                "error": block_reason,
                "blocked": True,
                "html": "",
                "styles": []
            }
        logger.info("✅ Content moderation check passed")

        # Detect website type
        website_type = template_service.detect_website_type(request.description)
        features = template_service.detect_features(request.description)

        # Merge user-selected features from frontend
        if request.features:
            logger.info(f"User-selected features: {request.features}")
            if request.features.get("deliverySystem"):
                if "delivery_system" not in features:
                    features.append("delivery_system")
            if request.features.get("googleMap"):
                if "maps" not in features:
                    features.append("maps")
            if request.features.get("contactForm"):
                if "contact" not in features:
                    features.append("contact")
            if request.features.get("socialMedia"):
                if "social" not in features:
                    features.append("social")
            if not request.features.get("whatsapp", True) and "whatsapp" in features:
                features.remove("whatsapp")

        business_name = extract_business_name(request.description)
        language = detect_language(request.description)
        phone_number = extract_phone_number(request.description)
        address = extract_address(request.description)

        logger.info(f"✓ Type={website_type}, Features={features}")

        # Try to generate custom images with Stability AI
        images = None
        if ai_service.stability_api_key:
            logger.info("🎨 Attempting Stability AI image generation...")
            images = await ai_service.generate_business_images(request.description)
            if images:
                logger.info("🎨 ✅ Using Stability AI custom images")
            else:
                logger.info("🎨 ⚠️ Stability AI failed, using fallback")

        # Fallback to stock images
        if not images:
            images = ai_service.get_fallback_images(request.description)
            logger.info("📸 Using stock images")

        # Build AI generation request
        ai_request = WebsiteGenerationRequest(
            description=request.description,
            business_name=business_name,
            business_type=website_type,
            language=language,
            subdomain="preview",
            include_whatsapp=("whatsapp" in features),
            whatsapp_number=phone_number if phone_number else "+60123456789",
            include_maps=("maps" in features),
            location_address=address if address else "",
            include_ecommerce=("cart" in features),
            contact_email=None,
            uploaded_images=images.get("gallery", []),  # Use generated images
            logo=request.logo,
            fonts=request.fonts if request.fonts else [],
            colors=request.colors,
            theme=request.theme
        )

        # User data for integrations
        user_data = {
            "phone": phone_number if phone_number else "+60123456789",
            "address": address if address else "",
            "email": "contact@business.com",
            "url": "https://preview.binaapp.my",
            "whatsapp_message": "Hi, I'm interested",
            "business_name": business_name
        }

        # Generate website
        logger.info("🔷 Generating HTML with AI...")
        ai_response = await ai_service.generate_website(ai_request)
        html_content = ai_response.html_content

        # Inject integrations
        html_content = template_service.inject_integrations(
            html_content,
            features,
            user_data
        )

        logger.info("✅ Simple generation complete")

        return {
            "success": True,
            "html": html_content,
            "styles": [{"style": "modern", "html": html_content}],
            "detected_features": features,
            "template_used": website_type
        }

    except Exception as e:
        import traceback
        logger.error("=" * 80)
        logger.error("❌ ERROR IN SIMPLE GENERATION")
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        return {
            "success": False,
            "error": str(e),
            "html": "",
            "styles": []
        }


@router.get("/test-ai")
async def test_ai_connectivity():
    """
    Test AI API connectivity

    This endpoint tests connection to Qwen and DeepSeek APIs
    and returns detailed status information for debugging.
    """
    try:
        logger.info("=" * 80)
        logger.info("🧪 AI CONNECTIVITY TEST REQUESTED")
        logger.info("=" * 80)

        results = await ai_service.test_api_connectivity()

        return {
            "success": True,
            "message": "AI connectivity test completed",
            "results": results
        }
    except Exception as e:
        import traceback
        logger.error(f"AI connectivity test failed: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"Test failed: {str(e)}",
            "results": {}
        }
