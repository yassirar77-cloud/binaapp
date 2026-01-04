"""
Menu Service - Comprehensive Menu Data Pipeline
Handles ALL scenarios for menu items in the delivery system:

SCENARIO A: User uploads items → Validate and use EXACTLY those items
SCENARIO B: User doesn't upload + delivery enabled → Generate items based on business type
SCENARIO C: User doesn't enable delivery → No menu needed

This service ensures deliveryMenuData is NEVER empty when delivery is enabled.
"""
import os
import logging
from typing import List, Dict, Optional, Any
import re

from app.services.menu_validator import is_valid_item_name, is_valid_price, log_menu_flow
from app.services.business_types import detect_business_type, detect_item_category, get_business_config

logger = logging.getLogger(__name__)

# ============================================================================
# DEFAULT MENU ITEMS BY BUSINESS TYPE
# These are used when user doesn't upload items but enables delivery
# ============================================================================

DEFAULT_MENU_ITEMS = {
    'food': [
        {
            'name': 'Nasi Lemak Special',
            'price': 12.00,
            'category': 'nasi',
            'desc': 'Nasi lemak dengan ayam goreng, sambal, dan telur',
            'image_prompt': 'Delicious Malaysian nasi lemak with fried chicken, sambal, egg, cucumber and peanuts on banana leaf, professional food photography'
        },
        {
            'name': 'Nasi Goreng Kampung',
            'price': 10.00,
            'category': 'nasi',
            'desc': 'Nasi goreng dengan ikan bilis dan telur mata',
            'image_prompt': 'Malaysian kampung fried rice with anchovies, sunny side up egg, and vegetables, professional food photography'
        },
        {
            'name': 'Mee Goreng Mamak',
            'price': 9.00,
            'category': 'mee',
            'desc': 'Mee goreng mamak style dengan telur dan sayur',
            'image_prompt': 'Malaysian mamak style fried noodles with egg and vegetables, professional food photography'
        },
        {
            'name': 'Ayam Goreng Berempah',
            'price': 8.00,
            'category': 'lauk',
            'desc': 'Ayam goreng rangup dengan rempah pilihan',
            'image_prompt': 'Crispy Malaysian spiced fried chicken, professional food photography'
        },
        {
            'name': 'Teh Tarik',
            'price': 3.00,
            'category': 'minuman',
            'desc': 'Teh tarik panas atau sejuk',
            'image_prompt': 'Malaysian teh tarik pulled milk tea in glass, professional photography'
        },
    ],
    'services': [
        {
            'name': 'Pakej Asas',
            'price': 500.00,
            'category': 'servis',
            'desc': 'Perkhidmatan asas untuk keperluan standard',
            'image_prompt': 'Professional service package, business consultation, clean modern office setting'
        },
        {
            'name': 'Pakej Premium',
            'price': 1000.00,
            'category': 'servis',
            'desc': 'Perkhidmatan premium dengan kualiti terbaik',
            'image_prompt': 'Premium professional service package, luxury business consultation'
        },
        {
            'name': 'Pakej Eksklusif',
            'price': 2000.00,
            'category': 'servis',
            'desc': 'Perkhidmatan eksklusif dan komprehensif',
            'image_prompt': 'Exclusive VIP professional service, high-end business package'
        },
    ],
    'photography': [
        {
            'name': 'Pakej Fotografi Asas',
            'price': 500.00,
            'category': 'servis',
            'desc': '2 jam sesi fotografi, 20 gambar edited',
            'image_prompt': 'Professional photographer with camera equipment in studio setting'
        },
        {
            'name': 'Pakej Perkahwinan',
            'price': 1500.00,
            'category': 'servis',
            'desc': 'Fotografi perkahwinan sehari penuh',
            'image_prompt': 'Wedding photography setup with romantic lighting and decorations'
        },
        {
            'name': 'Pakej Korporat',
            'price': 800.00,
            'category': 'servis',
            'desc': 'Fotografi korporat dan headshot profesional',
            'image_prompt': 'Corporate photography session in modern office environment'
        },
        {
            'name': 'Pakej Produk',
            'price': 600.00,
            'category': 'servis',
            'desc': 'Fotografi produk untuk e-commerce',
            'image_prompt': 'Product photography setup with white background and professional lighting'
        },
    ],
    'clothing': [
        {
            'name': 'Baju Kurung Moden',
            'price': 89.00,
            'category': 'baju',
            'desc': 'Baju kurung moden dengan potongan kontemporari',
            'image_prompt': 'Modern baju kurung Malaysian traditional dress on mannequin, fashion photography'
        },
        {
            'name': 'Tudung Bawal Premium',
            'price': 35.00,
            'category': 'tudung',
            'desc': 'Tudung bawal premium kualiti tinggi',
            'image_prompt': 'Premium bawal hijab scarf in beautiful colors, fashion photography'
        },
        {
            'name': 'Kebaya Nyonya',
            'price': 150.00,
            'category': 'baju',
            'desc': 'Kebaya tradisional dengan sulaman halus',
            'image_prompt': 'Traditional Nyonya kebaya with intricate embroidery, fashion photography'
        },
        {
            'name': 'Set Aksesori Muslimah',
            'price': 45.00,
            'category': 'aksesori',
            'desc': 'Set aksesori lengkap untuk muslimah',
            'image_prompt': 'Muslim fashion accessories set including brooch and inner, fashion photography'
        },
    ],
    'salon': [
        {
            'name': 'Potong Rambut',
            'price': 25.00,
            'category': 'rawatan',
            'desc': 'Potong rambut oleh stylist profesional',
            'image_prompt': 'Professional hair cutting in modern salon'
        },
        {
            'name': 'Warna Rambut',
            'price': 80.00,
            'category': 'rawatan',
            'desc': 'Pewarnaan rambut dengan produk premium',
            'image_prompt': 'Hair coloring service in beauty salon'
        },
        {
            'name': 'Rawatan Spa Rambut',
            'price': 120.00,
            'category': 'rawatan',
            'desc': 'Rawatan spa untuk rambut sihat',
            'image_prompt': 'Hair spa treatment in luxury salon'
        },
        {
            'name': 'Manicure & Pedicure',
            'price': 50.00,
            'category': 'rawatan',
            'desc': 'Rawatan kuku tangan dan kaki',
            'image_prompt': 'Professional manicure and pedicure service'
        },
    ],
    'general': [
        {
            'name': 'Produk Utama',
            'price': 50.00,
            'category': 'produk',
            'desc': 'Produk berkualiti pilihan kami',
            'image_prompt': 'High quality product on clean white background'
        },
        {
            'name': 'Produk Premium',
            'price': 100.00,
            'category': 'produk',
            'desc': 'Produk premium dengan kualiti terbaik',
            'image_prompt': 'Premium product with elegant packaging'
        },
        {
            'name': 'Set Combo',
            'price': 80.00,
            'category': 'produk',
            'desc': 'Set combo dengan nilai terbaik',
            'image_prompt': 'Product combo set with multiple items'
        },
    ],
}

# Fallback stock images by category when Stability AI is unavailable
FALLBACK_IMAGES = {
    'food': {
        'nasi': 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80',
        'mee': 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&q=80',
        'lauk': 'https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=600&q=80',
        'minuman': 'https://images.unsplash.com/photo-1571934811356-5cc061b6821f?w=600&q=80',
        'default': 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80',
    },
    'services': {
        'servis': 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=600&q=80',
        'default': 'https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=600&q=80',
    },
    'photography': {
        'servis': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&q=80',
        'default': 'https://images.unsplash.com/photo-1452587925148-ce544e77e70d?w=600&q=80',
    },
    'clothing': {
        'baju': 'https://images.unsplash.com/photo-1558171813-4c088753af8f?w=600&q=80',
        'tudung': 'https://images.unsplash.com/photo-1590073844006-33379778ae09?w=600&q=80',
        'aksesori': 'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600&q=80',
        'default': 'https://images.unsplash.com/photo-1445205170230-053b83016050?w=600&q=80',
    },
    'salon': {
        'rawatan': 'https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80',
        'default': 'https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80',
    },
    'general': {
        'produk': 'https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=600&q=80',
        'default': 'https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=600&q=80',
    },
}


def get_menu_items(
    form_data: dict,
    features: Optional[dict] = None,
    generate_images: bool = True
) -> List[Dict]:
    """
    COMPREHENSIVE MENU ITEM HANDLER
    
    This function handles ALL scenarios:
    
    SCENARIO A: User uploaded menu items → Validate and use EXACTLY those items
    SCENARIO B: No user items but delivery enabled → Generate based on business type
    SCENARIO C: Delivery not enabled → Return empty list
    
    Args:
        form_data: The form data containing user inputs (images, description, businessType, etc.)
        features: Feature flags (deliverySystem, deliverySendiri, etc.)
        generate_images: Whether to generate Stability AI images for generated items
        
    Returns:
        List of validated menu items ready for deliveryMenuData
    """
    logger.info("\n" + "=" * 70)
    logger.info("📦 MENU SERVICE: get_menu_items() CALLED")
    logger.info("=" * 70)
    
    # Step 1: Extract user-uploaded items
    user_items = extract_user_menu_items(form_data)
    
    # Step 2: Validate user items
    validated_user_items = validate_user_menu_items(user_items, form_data)
    
    if validated_user_items:
        # SCENARIO A: User uploaded valid items → Use them
        logger.info(f"✅ SCENARIO A: Using {len(validated_user_items)} USER-UPLOADED items")
        log_menu_flow("FINAL MENU ITEMS (user-uploaded)", validated_user_items)
        return validated_user_items
    
    # Step 3: Check if delivery is enabled
    delivery_enabled = is_delivery_enabled(form_data, features)
    
    if not delivery_enabled:
        # SCENARIO C: Delivery not enabled → No menu needed
        logger.info("ℹ️ SCENARIO C: Delivery NOT enabled, returning empty menu")
        return []
    
    # SCENARIO B: No user items but delivery enabled → Generate from business type
    logger.info("🤖 SCENARIO B: No user items, generating from business type")
    generated_items = generate_menu_from_business(form_data, generate_images)
    
    log_menu_flow("FINAL MENU ITEMS (AI-generated)", generated_items)
    return generated_items


def extract_user_menu_items(form_data: dict) -> List[Dict]:
    """
    Extract menu items from various possible locations in form data.
    
    User items can come from:
    - form_data['menuItems'] - Direct menu items
    - form_data['menu_items'] - Alternative key
    - form_data['images'] - Images with name/price metadata
    """
    user_items = []
    
    # Check direct menuItems field
    if form_data.get('menuItems'):
        items = form_data['menuItems']
        if isinstance(items, list):
            user_items.extend(items)
            logger.info(f"   Found {len(items)} items in 'menuItems'")
    
    # Check alternative menu_items field
    if form_data.get('menu_items') and not user_items:
        items = form_data['menu_items']
        if isinstance(items, list):
            user_items.extend(items)
            logger.info(f"   Found {len(items)} items in 'menu_items'")
    
    # Check images field for items with names/prices
    if form_data.get('images'):
        images = form_data['images']
        if isinstance(images, list):
            for img in images:
                if isinstance(img, dict):
                    # Check if image has a name (not just 'Hero Image')
                    name = img.get('name', '').strip()
                    if name and name.lower() != 'hero image' and 'hero' not in name.lower():
                        user_items.append({
                            'name': name,
                            'price': img.get('price'),
                            'imageUrl': img.get('url') or img.get('imageUrl'),
                            'description': img.get('description', '')
                        })
            logger.info(f"   Found {len([i for i in images if isinstance(i, dict) and i.get('name')])} named items in 'images'")
    
    logger.info(f"   Total extracted user items: {len(user_items)}")
    return user_items


def validate_user_menu_items(
    user_items: List[Dict],
    form_data: dict
) -> List[Dict]:
    """
    Validate user-uploaded menu items using RALPH LOOP pattern.
    
    CRITICAL: Only returns items that user EXPLICITLY provided.
    NEVER creates, modifies, or hallucinates menu items.
    
    Returns:
        List of validated menu items with exact user data
    """
    if not user_items:
        logger.info("   No user items to validate")
        return []
    
    logger.info(f"🔍 Validating {len(user_items)} user items...")
    
    # Detect business type for category assignment
    description = form_data.get('description', '')
    business_type = form_data.get('business_type') or detect_business_type(description)
    biz_config = get_business_config(business_type)
    default_desc = biz_config.get("item_description_default", "Produk pilihan kami")
    
    validated_items = []
    
    for idx, item in enumerate(user_items):
        if not isinstance(item, dict):
            logger.warning(f"   ⚠️ Item {idx}: Not a dict, skipping")
            continue
        
        # Extract name
        raw_name = item.get('name', '') or item.get('item_name', '') or ''
        name = raw_name.strip() if raw_name else ''
        
        # CRITICAL: Skip items without names - NEVER let AI generate names
        if not name:
            logger.info(f"   ⏭️ Item {idx}: No name provided, skipping (NO AI FALLBACK)")
            continue
        
        # Validate name against RALPH LOOP rules
        if not is_valid_item_name(name):
            logger.warning(f"   ⚠️ Item {idx}: Invalid name '{name}', skipping")
            continue
        
        # Extract and validate price
        raw_price = item.get('price') or item.get('item_price')
        is_price_valid, parsed_price = is_valid_price(raw_price)
        
        # For user items, we require a valid price
        if not is_price_valid:
            logger.warning(f"   ⚠️ Item {idx}: Invalid price '{raw_price}' for '{name}', using default 15.00")
            parsed_price = 15.0  # Default price for user items without valid price
        
        # Extract image URL
        image_url = (
            item.get('imageUrl') or 
            item.get('image_url') or 
            item.get('url') or 
            item.get('image') or 
            ''
        )
        
        # Get fallback image if no URL provided
        if not image_url:
            category = detect_item_category(name, business_type)
            image_url = get_fallback_image(business_type, category)
        
        # Auto-detect category
        category = detect_item_category(name, business_type)
        
        # Create validated item
        validated_item = {
            'id': len(validated_items) + 1,
            'name': name,  # EXACT name from user
            'price': parsed_price,  # User's price or default
            'image': image_url,
            'image_url': image_url,
            'desc': item.get('description') or default_desc,
            'description': item.get('description') or default_desc,
            'category': category,
            'category_id': category,
            'is_available': True,
        }
        
        validated_items.append(validated_item)
        logger.info(f"   ✅ Item {idx}: VALID - '{name}' @ RM{parsed_price:.2f} [{category}]")
    
    logger.info(f"📦 Validated {len(validated_items)} user items from {len(user_items)} inputs")
    return validated_items


def is_delivery_enabled(form_data: dict, features: Optional[dict] = None) -> bool:
    """Check if delivery feature is enabled."""
    # Check features dict
    if features:
        if features.get('deliverySystem') or features.get('delivery'):
            return True
    
    # Check form_data features
    form_features = form_data.get('features', {})
    if form_features:
        if form_features.get('deliverySystem') or form_features.get('delivery') or form_features.get('deliverySendiri'):
            return True
    
    # Check delivery config
    if form_data.get('delivery'):
        return True
    
    # Check fulfillment config
    if form_data.get('fulfillment'):
        return True
    
    return False


def generate_menu_from_business(
    form_data: dict,
    generate_images: bool = True
) -> List[Dict]:
    """
    Generate menu items based on business type and description.
    
    This is called when:
    - User doesn't upload any menu items
    - But delivery is enabled
    
    Generates appropriate items for the business type with optional Stability AI images.
    """
    # Detect business type from description
    description = form_data.get('description', '') or form_data.get('business_description', '')
    business_type = form_data.get('business_type') or detect_business_type(description)
    
    logger.info(f"🏢 Generating menu for business type: {business_type}")
    logger.info(f"   Description: {description[:100]}..." if len(description) > 100 else f"   Description: {description}")
    
    # Refine business type based on description keywords
    refined_type = refine_business_type(description, business_type)
    if refined_type != business_type:
        logger.info(f"   Refined type: {business_type} → {refined_type}")
        business_type = refined_type
    
    # Get default items for this business type
    default_items = DEFAULT_MENU_ITEMS.get(business_type, DEFAULT_MENU_ITEMS['general'])
    
    generated_items = []
    
    for idx, item_template in enumerate(default_items):
        # Get image URL
        if generate_images:
            image_url = generate_item_image(
                item_template.get('image_prompt', f"{item_template['name']} professional photo"),
                business_type,
                item_template.get('category', 'default')
            )
        else:
            image_url = get_fallback_image(business_type, item_template.get('category', 'default'))
        
        generated_item = {
            'id': idx + 1,
            'name': item_template['name'],
            'price': item_template['price'],
            'image': image_url,
            'image_url': image_url,
            'desc': item_template['desc'],
            'description': item_template['desc'],
            'category': item_template['category'],
            'category_id': item_template['category'],
            'is_available': True,
        }
        
        generated_items.append(generated_item)
        logger.info(f"   ✅ Generated: {item_template['name']} - RM{item_template['price']:.2f} [{item_template['category']}]")
    
    logger.info(f"📦 Generated {len(generated_items)} items for {business_type} business")
    return generated_items


def refine_business_type(description: str, base_type: str) -> str:
    """
    Refine business type based on description keywords.
    
    For example:
    - "photographer" + services → photography
    - "gambar" + services → photography
    - "salon" + services → salon
    """
    desc_lower = description.lower()
    
    # Photography keywords
    photography_keywords = ['photographer', 'photography', 'jurugambar', 'fotografi', 'gambar', 'photoshoot', 'wedding', 'perkahwinan', 'studio']
    if any(kw in desc_lower for kw in photography_keywords):
        return 'photography'
    
    # Salon keywords
    salon_keywords = ['salon', 'spa', 'rambut', 'hair', 'beauty', 'kecantikan', 'potong', 'cutting', 'manicure', 'pedicure']
    if any(kw in desc_lower for kw in salon_keywords):
        return 'salon'
    
    # Clothing keywords
    clothing_keywords = ['pakaian', 'baju', 'tudung', 'hijab', 'fashion', 'boutique', 'butik', 'kebaya', 'kurung']
    if any(kw in desc_lower for kw in clothing_keywords):
        return 'clothing'
    
    # Food keywords
    food_keywords = ['makanan', 'food', 'restaurant', 'restoran', 'cafe', 'nasi', 'mee', 'mamak', 'warung']
    if any(kw in desc_lower for kw in food_keywords):
        return 'food'
    
    return base_type


def generate_item_image(prompt: str, business_type: str, category: str) -> str:
    """
    Generate image for menu item using Stability AI.
    Falls back to stock image if Stability AI is unavailable.
    """
    # Try Stability AI first
    try:
        from app.services.stability_service import generate_stability_image
        image_url = generate_stability_image(prompt)
        if image_url:
            logger.info(f"   🎨 Generated Stability AI image for: {prompt[:40]}...")
            return image_url
    except Exception as e:
        logger.warning(f"   ⚠️ Stability AI failed: {e}")
    
    # Fallback to stock image
    return get_fallback_image(business_type, category)


def get_fallback_image(business_type: str, category: str) -> str:
    """Get fallback stock image for a category."""
    type_images = FALLBACK_IMAGES.get(business_type, FALLBACK_IMAGES['general'])
    return type_images.get(category, type_images.get('default', FALLBACK_IMAGES['general']['default']))


def create_default_delivery_zones(form_data: dict) -> List[Dict]:
    """
    Create default delivery zones from form data.
    
    Used when delivery is enabled but no zones are configured.
    """
    delivery_data = form_data.get('delivery') or {}
    fulfillment_data = form_data.get('fulfillment') or {}
    
    # Get zone name from multiple sources
    area_from_delivery = (delivery_data.get("area") or "").strip()
    area_from_fulfillment = (fulfillment_data.get("delivery_area") or "").strip()
    zone_name = area_from_delivery or area_from_fulfillment or "Kawasan Delivery"
    
    # Get delivery fee
    fee_raw = delivery_data.get("fee") or fulfillment_data.get("delivery_fee") or "5"
    if isinstance(fee_raw, str):
        try:
            fee_value = float(fee_raw.replace("RM", "").replace(",", "").strip())
        except ValueError:
            fee_value = 5.0
    else:
        fee_value = float(fee_raw) if fee_raw else 5.0
    
    # Get delivery time
    hours_raw = delivery_data.get("hours") or fulfillment_data.get("hours") or "30-45 min"
    
    default_zone = {
        "id": "default",
        "zone_name": zone_name,
        "name": zone_name,
        "delivery_fee": fee_value,
        "fee": fee_value,
        "estimated_time": hours_raw,
        "time": hours_raw,
        "is_active": True,
        "active": True,
    }
    
    logger.info(f"📍 Created default delivery zone: {zone_name} - RM{fee_value:.2f}")
    return [default_zone]
