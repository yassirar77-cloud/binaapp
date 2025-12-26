"""
Stability AI Image Generation Service
Generates custom images for Malaysian businesses
"""

import os
import httpx
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
STABILITY_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"


# ========================================
# MALAYSIAN BUSINESS IMAGE PROMPTS
# ========================================

MALAYSIAN_PROMPTS = {
    # ============ FOOD - RICE ============
    "nasi kandar": "Malaysian nasi kandar plate with white rice, rich brown curry gravy, fried chicken, boiled egg, vegetables, authentic mamak restaurant style, food photography, top-down view, warm lighting",
    "nasi lemak": "Malaysian nasi lemak with coconut rice, sambal, fried anchovies, peanuts, cucumber, boiled egg wrapped in banana leaf, traditional breakfast, food photography",
    "nasi goreng": "Malaysian nasi goreng fried rice with egg, vegetables, chicken, served on white plate, garnished with cucumber and keropok, food photography",
    "nasi goreng kampung": "Malaysian kampung style fried rice with anchovies, egg, green vegetables, spicy, rustic presentation, food photography",
    "nasi ayam": "Malaysian chicken rice, steamed chicken with rice, chili sauce, clear soup on the side, Hainanese style, food photography",
    "nasi campur": "Malaysian mixed rice with various side dishes, curry, vegetables, meat, colorful presentation, economy rice style, food photography",
    "nasi biryani": "Malaysian biryani rice with aromatic spices, saffron yellow rice, tender meat, garnished with fried onions, raita on side, food photography",
    "nasi kerabu": "Kelantan blue rice nasi kerabu with herbs, salted egg, fish crackers, coconut, colorful traditional Malaysian dish, food photography",

    # ============ FOOD - NOODLES ============
    "mee goreng": "Malaysian mee goreng mamak style, yellow noodles stir-fried with egg, vegetables, tofu, spicy red sauce, lime wedge, food photography",
    "mee goreng mamak": "Authentic mamak mee goreng with thick yellow noodles, egg, potatoes, tofu puffs, bean sprouts, spicy, food photography",
    "char kway teow": "Penang char kway teow, flat rice noodles with prawns, cockles, egg, bean sprouts, chives, wok hei smoky flavor, food photography",
    "laksa": "Penang assam laksa with rice noodles in tangy fish broth, cucumber, onion, pineapple, mint, shrimp paste, food photography",
    "laksa penang": "Authentic Penang laksa, sour fish soup with thick rice noodles, garnished with torch ginger flower, mint leaves, food photography",
    "hokkien mee": "KL Hokkien mee, thick yellow noodles in dark soy sauce with pork, prawns, crispy lard, served on banana leaf, food photography",
    "pan mee": "Malaysian pan mee handmade noodles in anchovy broth with minced pork, ikan bilis, poached egg, leafy greens, food photography",
    "wantan mee": "Malaysian wonton noodles with char siu BBQ pork, wontons, choy sum, black sauce, food photography",

    # ============ FOOD - CHICKEN ============
    "ayam goreng": "Malaysian ayam goreng berempah, crispy fried chicken with turmeric and spices, golden brown, served with rice, food photography",
    "ayam goreng berempah": "Crispy Malaysian spiced fried chicken, golden turmeric coating, served on banana leaf with sambal, food photography",
    "ayam rendang": "Malaysian dry rendang ayam, tender chicken in rich coconut curry, caramelized spices, kerisik, food photography",
    "ayam masak merah": "Malaysian ayam masak merah, chicken in spicy red tomato sauce, garnished with fried shallots, food photography",
    "ayam percik": "Kelantan ayam percik, grilled chicken with spicy coconut sauce, charred marks, served with rice, food photography",
    "ayam penyet": "Indonesian-Malaysian ayam penyet, smashed fried chicken with sambal, lalapan vegetables, food photography",

    # ============ FOOD - MEAT & SEAFOOD ============
    "rendang": "Malaysian beef rendang, slow-cooked dry curry with tender meat, toasted coconut, aromatic spices, food photography",
    "rendang daging": "Traditional Minang beef rendang, dark caramelized coconut curry, tender chunks, rich and aromatic, food photography",
    "ikan bakar": "Malaysian ikan bakar, grilled fish with sambal wrapped in banana leaf, charred smoky flavor, food photography",
    "ikan goreng": "Crispy Malaysian fried whole fish, golden brown with turmeric, served with sambal and ulam, food photography",
    "sotong goreng": "Malaysian fried squid rings, crispy golden batter, served with chili sauce, food photography",
    "udang sambal": "Malaysian sambal udang, prawns in spicy red chili paste, onions, tomatoes, food photography",
    "ketam masak cili": "Malaysian chili crab, whole crab in sweet spicy sauce, garnished with egg ribbons, food photography",
    "sup kambing": "Malaysian mutton soup, clear aromatic broth with tender meat, celery, fried shallots, food photography",

    # ============ FOOD - ROTI & BREAD ============
    "roti canai": "Malaysian roti canai, flaky layered flatbread with dhal curry and sambal, crispy golden, food photography",
    "roti telur": "Malaysian roti telur, egg-filled flatbread, crispy edges, served with curry sauce, food photography",
    "roti tissue": "Malaysian roti tissue, tall cone-shaped crispy flatbread with condensed milk, impressive presentation, food photography",
    "roti john": "Malaysian roti john, French loaf with minced meat, egg, onion, mayo and chili sauce, food photography",
    "thosai": "South Indian thosai dosa, crispy fermented crepe with coconut chutney and sambar, food photography",
    "naan": "Fresh tandoor naan bread, fluffy and charred, served with curry, food photography",

    # ============ FOOD - SNACKS ============
    "satay": "Malaysian satay skewers, grilled chicken with peanut sauce, ketupat rice cakes, cucumber, onion, food photography",
    "sate ayam": "Chicken satay on bamboo skewers, charcoal grilled, served with chunky peanut sauce, food photography",
    "karipap": "Malaysian curry puff, golden crispy pastry filled with curried potato and chicken, food photography",
    "pisang goreng": "Malaysian pisang goreng, crispy banana fritters, golden batter, served hot, food photography",
    "popiah": "Malaysian fresh spring rolls popiah with turnip, egg, vegetables, sweet sauce, food photography",
    "dim sum": "Bamboo steamer with assorted dim sum, har gao, siu mai, char siu bao, food photography",
    "rojak": "Malaysian rojak fruit salad with thick sweet prawn paste sauce, peanuts, food photography",
    "cendol": "Malaysian cendol dessert, green pandan jelly, coconut milk, gula melaka, shaved ice, food photography",
    "ais kacang": "Malaysian ABC ais kacang, shaved ice with red beans, corn, jelly, colorful syrups, food photography",

    # ============ DRINKS ============
    "teh tarik": "Malaysian teh tarik pulled milk tea, frothy and creamy, being pulled between two cups, food photography",
    "kopi": "Malaysian kopi, traditional coffee in vintage cup, kopitiam style, food photography",
    "milo dinosaur": "Malaysian milo dinosaur, iced chocolate malt drink topped with milo powder, food photography",
    "sirap bandung": "Pink sirap bandung rose milk drink with ice, refreshing Malaysian beverage, food photography",
    "air kelapa": "Fresh coconut water served in young coconut, tropical refreshing drink, food photography",

    # ============ FASHION - WOMEN ============
    "baju kurung": "Elegant Malaysian baju kurung traditional dress, beautiful batik fabric, modest fashion, worn by Malay woman, studio photography",
    "baju kurung moden": "Modern Malaysian baju kurung with contemporary cut, stylish fabric, hijab fashion, studio photography",
    "tudung": "Beautiful Malaysian tudung hijab headscarf, elegant draping, modest fashion, studio photography",
    "tudung bawal": "Malaysian tudung bawal square hijab, neatly pinned, elegant style, modest fashion photography",
    "tudung shawl": "Flowing Malaysian tudung shawl, chiffon fabric, elegant draping, hijab fashion photography",
    "hijab": "Stylish Malaysian hijab fashion, modern modest wear, beautiful fabric and styling, fashion photography",
    "kebaya": "Malaysian nyonya kebaya, intricate embroidery, traditional blouse with sarong, elegant fashion photography",
    "kebaya nyonya": "Peranakan kebaya nyonya with beautiful embroidery, pastel colors, traditional Malaysian fashion, studio photography",
    "telekung": "White Malaysian telekung prayer garment, clean and elegant, modest Islamic wear, product photography",
    "jubah": "Elegant Malaysian jubah dress, flowing modest fashion, beautiful fabric, fashion photography",

    # ============ FASHION - MEN ============
    "baju melayu": "Malaysian baju melayu traditional outfit for men, songket sampin, songkok cap, formal Malay attire, studio photography",
    "baju melayu moden": "Modern slim-fit Malaysian baju melayu, contemporary style, Hari Raya fashion, studio photography",
    "sampin": "Malaysian sampin songket, woven fabric worn with baju melayu, intricate gold patterns, product photography",
    "songkok": "Malaysian songkok cap, black velvet traditional headwear, product photography",

    # ============ ACCESSORIES ============
    "aksesori": "Malaysian fashion accessories collection, elegant jewelry pieces, earrings, necklace, bracelet, product photography",
    "rantai tangan": "Elegant gold bracelet, Malaysian jewelry, delicate chain design, product photography on white background",
    "anting": "Beautiful earrings, Malaysian jewelry design, elegant and modern, product photography",
    "handbag": "Stylish handbag, designer look, elegant leather, product photography on clean background",
    "cincin": "Elegant ring, gold or silver band, Malaysian jewelry, close-up product photography",
    "jam tangan": "Stylish wristwatch, elegant design, leather or metal strap, product photography",

    # ============ HAIR SALON ============
    "haircut": "Professional hairstylist cutting hair in modern salon, salon interior, mirrors, professional lighting",
    "potong rambut": "Malaysian hair salon, professional haircut service, modern interior, styling chairs and mirrors",
    "hair coloring": "Hair coloring process in salon, applying hair dye, professional colorist, vibrant colors, salon photography",
    "pewarnaan rambut": "Professional hair coloring service, Malaysian salon, beautiful hair transformation, salon photography",
    "hair styling": "Professional hair styling, blow dry and styling, beautiful finished hairstyle, salon photography",
    "rebonding": "Hair rebonding treatment in salon, straightening process, sleek smooth hair result, salon photography",
    "hair treatment": "Luxury hair treatment spa, applying hair mask, pampering service, salon photography",
    "salon interior": "Modern hair salon interior, stylish design, mirrors, styling stations, professional equipment, interior photography",
    "barber": "Professional barbershop, barber cutting men's hair, classic interior, barbershop photography",

    # ============ BEAUTY & SPA ============
    "facial": "Relaxing facial treatment at spa, applying face mask, peaceful atmosphere, beauty photography",
    "facial treatment": "Professional facial skincare treatment, beautician working, spa environment, beauty photography",
    "spa": "Luxury spa treatment room, massage bed, candles, flowers, peaceful zen atmosphere, spa photography",
    "massage": "Relaxing body massage at spa, professional therapist, calming environment, spa photography",
    "urut": "Traditional Malaysian urut massage therapy, relaxation and wellness, spa photography",
    "manicure": "Professional manicure service, nail care and polish, beauty salon, beauty photography",
    "pedicure": "Professional pedicure service, foot spa treatment, relaxing beauty service, salon photography",
    "nail art": "Beautiful nail art design, intricate patterns and colors, professional nail service, beauty photography",
    "makeup": "Professional makeup application, bridal or event makeup, beauty transformation, beauty photography",
    "bridal makeup": "Beautiful bridal makeup, Malaysian wedding look, elegant and glamorous, bridal photography",
    "eyelash extension": "Professional eyelash extension application, close-up beauty service, beauty photography",

    # ============ AUTOMOTIVE ============
    "car wash": "Professional car wash service, washing luxury car, foam and water, automotive service photography",
    "cuci kereta": "Malaysian car wash, professional cleaning service, shiny clean car, automotive photography",
    "car service": "Professional car service center, mechanic working on engine, automotive workshop, service photography",
    "bengkel": "Malaysian bengkel workshop, car repair service, professional mechanics, automotive photography",
    "car detailing": "Professional car detailing service, polishing luxury car, showroom finish, automotive photography",
    "tayar": "Tyre shop display, various car tyres, professional tyre service center, automotive photography",
    "battery": "Car battery service, mechanic replacing battery, professional automotive service, photography",

    # ============ GENERAL BUSINESS ============
    "restaurant": "Modern restaurant interior, elegant dining setup, tables and chairs, warm ambient lighting, interior photography",
    "restoran": "Malaysian restaurant interior, warm atmosphere, traditional decor, dining tables, interior photography",
    "cafe": "Cozy cafe interior, coffee shop aesthetic, wooden furniture, plants, warm lighting, interior photography",
    "kedai kopi": "Traditional Malaysian kopitiam coffee shop, vintage interior, marble tables, nostalgic atmosphere, interior photography",
    "bakery": "Beautiful bakery display, fresh bread and pastries, warm lighting, appetizing presentation, food photography",
    "grocery": "Well-organized grocery store, fresh produce display, clean aisles, retail photography",
    "pharmacy": "Modern pharmacy interior, organized medicine shelves, professional healthcare retail, interior photography",
    "gym": "Modern gym interior, fitness equipment, weights and machines, motivating atmosphere, interior photography",
    "laundry": "Clean modern laundromat, washing machines in row, bright interior, service photography",

    # ============ HERO/BANNER IMAGES ============
    "hero_food": "Malaysian food feast spread, nasi kandar, satay, rendang, colorful dishes, aerial food photography, warm lighting",
    "hero_fashion": "Malaysian fashion showcase, beautiful baju kurung and modern modest wear, elegant models, fashion photography",
    "hero_salon": "Luxury hair salon hero image, stylish interior, professional styling, glamorous atmosphere, salon photography",
    "hero_beauty": "Spa and beauty hero image, relaxing treatments, elegant spa interior, wellness photography",
    "hero_cafe": "Cozy cafe hero image, latte art coffee, pastries, warm inviting atmosphere, cafe photography",
    "hero_car": "Premium car service hero image, shiny luxury car, professional service center, automotive photography",
}


async def generate_image_stability(
    prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, ugly, bad anatomy",
    aspect_ratio: str = "1:1",
    output_format: str = "webp"
) -> Optional[str]:
    """
    Generate image using Stability AI.

    Args:
        prompt: Image generation prompt
        negative_prompt: What to avoid in the image
        aspect_ratio: Image aspect ratio (1:1, 16:9, 4:3, 3:2, etc.)
        output_format: Output format (webp, png, jpeg)

    Returns:
        Base64 encoded image string or None if failed
    """
    if not STABILITY_API_KEY:
        logger.error("❌ STABILITY_API_KEY not set!")
        return None

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Accept": "image/*"
    }

    data = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                STABILITY_API_URL,
                headers=headers,
                files={"none": ""},  # Required for multipart
                data=data
            )

            if response.status_code == 200:
                # Return base64 encoded image
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                logger.info("✅ Image generated successfully")
                return image_base64
            else:
                logger.error(f"❌ Stability API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"❌ Stability API exception: {e}")
        return None


def get_malaysian_prompt(item_name: str, business_type: str = "") -> str:
    """
    Get the best prompt for a Malaysian business item.

    Args:
        item_name: Product/service name
        business_type: Type of business

    Returns:
        Detailed prompt for Stability AI
    """
    item = item_name.lower().strip()

    # 1. Exact match
    if item in MALAYSIAN_PROMPTS:
        return MALAYSIAN_PROMPTS[item]

    # 2. Partial match
    for key, prompt in MALAYSIAN_PROMPTS.items():
        if key in item or item in key:
            return prompt

    # 3. Keyword matching
    keyword_mapping = {
        ("nasi", "rice"): "nasi kandar",
        ("mee", "noodle"): "mee goreng",
        ("ayam", "chicken"): "ayam goreng",
        ("ikan", "fish"): "ikan bakar",
        ("roti", "bread"): "roti canai",
        ("kurung",): "baju kurung",
        ("tudung", "hijab"): "tudung",
        ("salon", "hair", "rambut"): "salon interior",
        ("facial", "spa"): "facial",
        ("car", "kereta", "cuci"): "car wash",
    }

    for keywords, key in keyword_mapping.items():
        for kw in keywords:
            if kw in item:
                return MALAYSIAN_PROMPTS.get(key, "")

    # 4. Business type default
    if business_type:
        bt = business_type.lower()
        if "food" in bt or "makan" in bt:
            return MALAYSIAN_PROMPTS["hero_food"]
        if "fashion" in bt or "butik" in bt:
            return MALAYSIAN_PROMPTS["hero_fashion"]
        if "salon" in bt:
            return MALAYSIAN_PROMPTS["hero_salon"]
        if "beauty" in bt or "spa" in bt:
            return MALAYSIAN_PROMPTS["hero_beauty"]

    # 5. Generic fallback
    return f"Professional photograph of {item_name}, high quality, commercial photography, clean background"


async def generate_malaysian_image(
    item_name: str,
    business_type: str = "",
    aspect_ratio: str = "1:1"
) -> Optional[str]:
    """
    Generate a Malaysian business image.

    Args:
        item_name: Product/service name (e.g., "Nasi Kandar", "Baju Kurung")
        business_type: Business category
        aspect_ratio: Image aspect ratio

    Returns:
        Base64 encoded image or None
    """
    prompt = get_malaysian_prompt(item_name, business_type)

    if not prompt:
        prompt = f"Professional photograph of {item_name}, Malaysian style, high quality, commercial photography"

    logger.info(f"🎨 Generating image for: {item_name}")
    logger.info(f"📝 Prompt: {prompt[:100]}...")

    return await generate_image_stability(prompt, aspect_ratio=aspect_ratio)


# ========================================
# HELPER: Save generated image to Storage
# ========================================

async def save_image_to_storage(
    image_base64: str,
    filename: str,
    supabase_url: str,
    supabase_key: str
) -> Optional[str]:
    """
    Save generated image to Supabase Storage.

    Returns:
        Public URL of saved image or None
    """
    import base64

    # Decode base64 to bytes
    image_bytes = base64.b64decode(image_base64)

    # Upload to Supabase Storage
    storage_url = f"{supabase_url}/storage/v1/object/menu-images/{filename}"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "image/webp",
        "x-upsert": "true"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                storage_url,
                content=image_bytes,
                headers=headers
            )

            if response.status_code in [200, 201]:
                public_url = f"{supabase_url}/storage/v1/object/public/menu-images/{filename}"
                logger.info(f"✅ Image saved: {public_url}")
                return public_url
            else:
                logger.error(f"❌ Storage upload failed: {response.text}")
                return None

    except Exception as e:
        logger.error(f"❌ Storage exception: {e}")
        return None
