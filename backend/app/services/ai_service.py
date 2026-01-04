"""
AI Service - Strict No-Placeholder Mode
Ensures real images and real content - NO placeholders allowed
"""

import os
import httpx
import random
import asyncio
import time
import json
import re
from loguru import logger
from typing import Optional, List, Dict, Tuple
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse
from difflib import SequenceMatcher
import cloudinary
import cloudinary.uploader


class AIService:
    """AI Service with strict anti-placeholder enforcement"""

    # FOOD IMAGES - Unique Unsplash images for each dish category
    FOOD_IMAGES = {
        "nasi kandar": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80",
        "nasi lemak": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&q=80",
        "nasi goreng": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",
        "nasi kerabu": "https://images.unsplash.com/photo-1596040033229-a0b3b7b43107?w=600&q=80",
        "nasi ayam": "https://images.unsplash.com/photo-1603360946369-dc9bb6258143?w=600&q=80",
        "nasi briyani": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&q=80",

        "ayam goreng": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=600&q=80",
        "ayam percik": "https://images.unsplash.com/photo-1598103442097-8b74394b95c6?w=600&q=80",
        "rendang": "https://images.unsplash.com/photo-1574484284002-952d92456975?w=600&q=80",

        "ikan bakar": "https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=600&q=80",
        "ikan": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80",

        "mee goreng": "https://images.unsplash.com/photo-1617093727343-374698b1b08d?w=600&q=80",
        "char kway teow": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&q=80",
        "laksa": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=600&q=80",
        "hokkien mee": "https://images.unsplash.com/photo-1612927601601-6638404737ce?w=600&q=80",
        "mee rebus": "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&q=80",

        "roti canai": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&q=80",
        "roti": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80",
        "murtabak": "https://images.unsplash.com/photo-1599020792689-9fde458e7e17?w=600&q=80",

        "satay": "https://images.unsplash.com/photo-1529563021893-cc83c992d75d?w=600&q=80",

        "pelbagai lauk": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80",
        "lauk": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&q=80",

        "teh tarik": "https://images.unsplash.com/photo-1594631661960-17f1e5fc3d08?w=600&q=80",
        "kopi": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&q=80",

        "cendol": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=600&q=80",
        "ais kacang": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&q=80",

        # Generic fallback
        "default": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80"
    }

    # COMPREHENSIVE BUSINESS IMAGES - Verified URLs for Malaysian Businesses
    BUSINESS_IMAGES = {
        # ===== MALAYSIAN FASHION & CLOTHING =====
        "baju kurung": "https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=600&q=80",  # Traditional Malay dress
        "baju melayu": "https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=600&q=80",
        "kurung": "https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=600&q=80",

        "tudung": "https://images.unsplash.com/photo-1601924357840-3e2a98b997f5?w=600&q=80",  # Hijab/headscarf
        "hijab": "https://images.unsplash.com/photo-1601924357840-3e2a98b997f5?w=600&q=80",
        "shawl": "https://images.unsplash.com/photo-1610976215686-875f2da6f249?w=600&q=80",
        "scarf": "https://images.unsplash.com/photo-1610976215686-875f2da6f249?w=600&q=80",

        "kebaya": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&q=80",  # Traditional blouse
        "baju kebaya": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&q=80",

        "pakaian": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",  # General clothing
        "fashion": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",
        "clothing": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",
        "boutique": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&q=80",

        # Fashion accessories
        "brooch": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600&q=80",
        "accessories": "https://images.unsplash.com/photo-1492707892479-7bc8d5a4ee93?w=600&q=80",
        "jewelry": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600&q=80",
        "anting": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&q=80",  # Earrings
        "rantai": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&q=80",  # Necklace

        # ===== HAIR SALON SERVICES =====
        "salon": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80",
        "hair salon": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80",
        "salon rambut": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80",

        "haircut": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80",
        "potong rambut": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80",
        "gunting rambut": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80",

        "hair coloring": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",
        "hair color": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",
        "cat rambut": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",
        "warna rambut": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",

        "hair treatment": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=600&q=80",
        "rawatan rambut": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=600&q=80",
        "hair spa": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=600&q=80",

        "hair styling": "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=600&q=80",
        "styling": "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=600&q=80",
        "blowdry": "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=600&q=80",

        # ===== BEAUTY & SPA SERVICES =====
        "beauty": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=600&q=80",
        "kecantikan": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=600&q=80",
        "beauty salon": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=600&q=80",

        "facial": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=600&q=80",
        "facial treatment": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=600&q=80",
        "rawatan muka": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=600&q=80",

        "spa": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=600&q=80",
        "massage": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=600&q=80",
        "urut": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=600&q=80",
        "body massage": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=600&q=80",

        "manicure": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",
        "pedicure": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",
        "nails": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",
        "nail salon": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",

        "makeup": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=80",
        "makeover": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=80",
        "solek": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=80",

        # ===== CAR & AUTOMOTIVE SERVICES =====
        "car wash": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=600&q=80",
        "cuci kereta": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=600&q=80",
        "auto wash": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=600&q=80",

        "bengkel": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "workshop": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "car repair": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "auto repair": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "mechanic": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",

        "car service": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?w=600&q=80",
        "servis kereta": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?w=600&q=80",
        "auto service": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?w=600&q=80",

        "tire service": "https://images.unsplash.com/photo-1592840496694-26d035b52b48?w=600&q=80",
        "tayar": "https://images.unsplash.com/photo-1592840496694-26d035b52b48?w=600&q=80",
        "tyre": "https://images.unsplash.com/photo-1592840496694-26d035b52b48?w=600&q=80",

        "kereta": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80",  # General car
        "car": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80",
        "automotive": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80",

        # ===== GENERAL BUSINESS CATEGORIES =====
        "bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&q=80",
        # Fix malformed Unsplash URL (was breaking image loads)
        "kedai roti": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&q=80",
        "cake": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600&q=80",
        "kek": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600&q=80",

        "florist": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&q=80",
        "bunga": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&q=80",
        "flowers": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&q=80",

        "pet shop": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&q=80",
        "kedai haiwan": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&q=80",
        "pet": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&q=80",

        "grocery": "https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80",
        "kedai runcit": "https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80",
        "mini market": "https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80",

        "laundry": "https://images.unsplash.com/photo-1517677208171-0bc6725a3e60?w=600&q=80",
        "dobi": "https://images.unsplash.com/photo-1517677208171-0bc6725a3e60?w=600&q=80",

        "cafe": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&q=80",
        "kafe": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&q=80",
        "coffee": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&q=80",

        "restaurant": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80",
        # Fix malformed Unsplash URL (was breaking image loads)
        "restoran": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80",

        # Generic fallback
        "business": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&q=80",
        "perniagaan": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&q=80",
        "default": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80"
    }

    # MALAYSIAN FOOD PROMPTS - 60+ Authentic Malaysian Dishes
    MALAYSIAN_FOOD_PROMPTS = {
        # Rice Dishes
        "nasi lemak": "Malaysian nasi lemak plate with fragrant coconut rice, crispy fried anchovies (ikan bilis), roasted peanuts, hard-boiled egg, cucumber slices, and spicy sambal sauce",
        "nasi kandar": "Malaysian nasi kandar plate with steamed white rice, rich curry gravy, fried chicken, okra in curry sauce, and pickled vegetables",
        "nasi kerabu": "Malaysian nasi kerabu blue rice dish with herbs, kerisik (toasted coconut), fish crackers, salted egg, and ulam (raw vegetables)",
        "nasi dagang": "Malaysian nasi dagang brown rice with tuna curry, pickled vegetables, and hard-boiled egg",
        "nasi goreng": "Malaysian nasi goreng fried rice with egg, vegetables, chicken, shrimp paste, and cucumber garnish",
        "nasi ayam": "Malaysian chicken rice with poached chicken slices, fragrant rice, cucumber, and chili sauce",
        "nasi tomato": "Malaysian nasi tomato red rice cooked with tomatoes, spices, raisins, and cashew nuts",
        "nasi minyak": "Malaysian nasi minyak ghee rice with aromatic spices, garnished with fried onions and cashews",
        "nasi briyani": "Malaysian nasi briyani spiced rice with tender chicken or lamb, yogurt, and aromatic spices",
        "nasi hujan panas": "Malaysian nasi hujan panas rice with anchovies, peanuts, and spicy sambal",

        # Noodle Dishes
        "mee goreng": "Malaysian mee goreng yellow noodles stir-fried with tofu, vegetables, egg, and spicy sauce",
        "char kway teow": "Malaysian char kway teow flat rice noodles wok-fried with prawns, cockles, egg, bean sprouts, and soy sauce",
        "laksa": "Malaysian laksa spicy noodle soup with thick rice noodles, fish broth, tamarind, and coconut milk",
        "assam laksa": "Malaysian assam laksa sour fish noodle soup with mackerel, tamarind, mint, and pineapple",
        "curry laksa": "Malaysian curry laksa coconut curry noodle soup with tofu puffs, prawns, and bean sprouts",
        "mee rebus": "Malaysian mee rebus yellow noodles in thick sweet potato gravy with egg, tofu, and lime",
        "mee bandung": "Malaysian mee bandung noodles in spicy tomato-based gravy with prawns and vegetables",
        "hokkien mee": "Malaysian Hokkien mee thick noodles braised in dark soy sauce with pork, seafood, and cabbage",
        "pan mee": "Malaysian pan mee handmade flat noodles in anchovy broth with minced pork, mushrooms, and fried anchovies",
        "wantan mee": "Malaysian wantan mee egg noodles with char siu (BBQ pork), wonton dumplings, and dark soy sauce",
        "kolo mee": "Malaysian kolo mee Sarawak-style springy noodles with char siu, minced pork, and fried shallots",
        "maggi goreng": "Malaysian maggi goreng instant noodles stir-fried with egg, vegetables, and spicy sauce",
        "mihun goreng": "Malaysian mihun goreng rice vermicelli stir-fried with vegetables, egg, and meat",
        "kuey teow goreng": "Malaysian kuey teow goreng flat rice noodles stir-fried with prawns and vegetables",

        # Meat Dishes
        "rendang": "Malaysian beef rendang slow-cooked in thick spicy coconut curry with lemongrass and galangal",
        "ayam percik": "Malaysian ayam percik grilled chicken with spicy coconut gravy",
        "ayam masak merah": "Malaysian ayam masak merah chicken in red tomato chili gravy",
        "ayam goreng berempah": "Malaysian ayam goreng berempah spiced fried chicken with turmeric and herbs",
        "gulai kambing": "Malaysian gulai kambing lamb curry in spicy coconut gravy",
        "daging masak hitam": "Malaysian daging masak hitam beef in thick dark soy sauce with spices",
        "sambal udang": "Malaysian sambal udang prawns in spicy chili sambal sauce",
        "ikan bakar": "Malaysian ikan bakar grilled fish with sambal and lime",
        "ikan patin masak tempoyak": "Malaysian ikan patin fish curry with fermented durian paste",
        "asam pedas": "Malaysian asam pedas sour and spicy fish stew with tamarind and chilies",
        "gulai ikan": "Malaysian gulai ikan fish curry in turmeric coconut gravy",

        # Satay & Grilled
        "satay": "Malaysian chicken satay skewers grilled over charcoal with peanut sauce, cucumber, and onions",
        "satay ayam": "Malaysian chicken satay marinated skewers with thick peanut dipping sauce",
        "satay daging": "Malaysian beef satay grilled meat skewers with spicy peanut sauce",
        "satay kambing": "Malaysian lamb satay skewers with aromatic peanut sauce",

        # Soups
        "soto": "Malaysian soto chicken soup with turmeric, rice vermicelli, bean sprouts, and hard-boiled egg",
        "sup tulang": "Malaysian sup tulang bone marrow soup with beef bones and spices",
        "bakso": "Malaysian bakso meatball soup with noodles and vegetables",

        # Snacks & Appetizers
        "roti canai": "Malaysian roti canai crispy flaky flatbread with curry dipping sauce",
        "roti telur": "Malaysian roti telur flatbread with egg filling",
        "roti tissue": "Malaysian roti tissue paper-thin crispy flatbread cone with sugar",
        "murtabak": "Malaysian murtabak stuffed pancake with minced meat, egg, and onions",
        "curry puff": "Malaysian curry puff pastry filled with spiced potato and chicken",
        "epok epok": "Malaysian epok epok crispy fried curry puff with sardine filling",
        "kuih": "Malaysian traditional kuih colorful sweet cakes and pastries",
        "onde onde": "Malaysian onde onde pandan glutinous rice balls with palm sugar filling",
        "kuih lapis": "Malaysian kuih lapis colorful layered steamed cake",
        "kuih ketayap": "Malaysian kuih ketayap green pandan crepes with coconut filling",
        "pisang goreng": "Malaysian pisang goreng crispy fried banana fritters",
        "cempedak goreng": "Malaysian cempedak goreng fried jackfruit fritters",
        "keropok lekor": "Malaysian keropok lekor fish crackers from Terengganu",
        "otak otak": "Malaysian otak otak grilled fish cake wrapped in banana leaf",

        # Desserts
        "cendol": "Malaysian cendol iced dessert with pandan jelly noodles, coconut milk, and gula melaka",
        "ais kacang": "Malaysian ais kacang shaved ice with red beans, corn, jelly, and colorful syrups",
        "bubur chacha": "Malaysian bubur chacha warm coconut dessert soup with sweet potato and sago pearls",
        "pengat": "Malaysian pengat sweet banana in coconut milk and palm sugar",
        "sago gula melaka": "Malaysian sago gula melaka sago pearls with coconut milk and palm sugar syrup",
        "kuih talam": "Malaysian kuih talam two-layer steamed coconut pandan cake",

        # Beverages
        "teh tarik": "Malaysian teh tarik pulled milk tea being poured between two containers creating foam",
        "kopi o": "Malaysian kopi o black coffee in traditional coffee shop",
        "milo ais": "Malaysian milo ais iced chocolate malt drink",
        "air bandung": "Malaysian air bandung pink rose syrup milk drink",
        "sirap": "Malaysian sirap rose syrup drink with ice",

        # Special & Regional
        "nasi ambeng": "Malaysian nasi ambeng Javanese rice platter with fried chicken, bergedel, serunding, and sambal",
        "nasi tumpang": "Malaysian nasi tumpang cone-shaped rice wrapped in banana leaf with curry",
        "nasi kukus": "Malaysian nasi kukus steamed rice with fried chicken and sambal",
        "lontong": "Malaysian lontong rice cakes in coconut vegetable curry",
        "ketupat": "Malaysian ketupat rice dumplings wrapped in woven palm leaves",
        "lemang": "Malaysian lemang glutinous rice cooked in bamboo with coconut milk",
    }

    def __init__(self):
        self.qwen_api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")

        logger.info("=" * 80)
        logger.info("🚀 AI SERVICE - STRICT NO-PLACEHOLDER MODE")
        logger.info(f"   DeepSeek: {'✅ Ready' if self.deepseek_api_key else '❌ NOT SET'}")
        logger.info(f"   Qwen: {'✅ Ready' if self.qwen_api_key else '❌ NOT SET'}")
        logger.info(f"   Stability: {'✅ Ready' if self.stability_api_key else '❌ NOT SET'}")
        logger.info("   Mode: Real images only, no placeholders allowed")
        logger.info("=" * 80)

    def get_food_image(self, dish_name: str) -> str:
        """
        Get unique food image URL for a dish name

        Uses fuzzy matching to find the best image for a dish.
        Ensures different dishes get different images.
        """
        if not dish_name:
            return self.FOOD_IMAGES["default"]

        dish_lower = dish_name.lower().strip()

        # Direct exact match
        if dish_lower in self.FOOD_IMAGES:
            return self.FOOD_IMAGES[dish_lower]

        # Fuzzy matching - check if dish name contains any key
        best_match = None
        best_score = 0.0

        for key, url in self.FOOD_IMAGES.items():
            if key == "default":
                continue

            # Check if key is in dish name or vice versa
            if key in dish_lower:
                score = len(key) / len(dish_lower)
                if score > best_score:
                    best_score = score
                    best_match = url
            elif dish_lower in key:
                score = len(dish_lower) / len(key)
                if score > best_score:
                    best_score = score
                    best_match = url

        if best_match and best_score >= 0.3:
            return best_match

        # Keyword fallback
        if "nasi kandar" in dish_lower:
            return self.FOOD_IMAGES["nasi kandar"]
        if "nasi lemak" in dish_lower:
            return self.FOOD_IMAGES["nasi lemak"]
        if "nasi" in dish_lower:
            return self.FOOD_IMAGES["nasi goreng"]
        if "ayam" in dish_lower or "chicken" in dish_lower:
            return self.FOOD_IMAGES["ayam goreng"]
        if "ikan" in dish_lower or "fish" in dish_lower:
            return self.FOOD_IMAGES["ikan bakar"]
        if "mee" in dish_lower or "noodle" in dish_lower:
            return self.FOOD_IMAGES["mee goreng"]
        if "laksa" in dish_lower:
            return self.FOOD_IMAGES["laksa"]
        if "roti" in dish_lower:
            return self.FOOD_IMAGES["roti canai"]
        if "satay" in dish_lower:
            return self.FOOD_IMAGES["satay"]
        if "rendang" in dish_lower:
            return self.FOOD_IMAGES["rendang"]
        if "lauk" in dish_lower or "side" in dish_lower:
            return self.FOOD_IMAGES["pelbagai lauk"]
        if "teh" in dish_lower or "tea" in dish_lower:
            return self.FOOD_IMAGES["teh tarik"]
        if "kopi" in dish_lower or "coffee" in dish_lower:
            return self.FOOD_IMAGES["kopi"]
        if "cendol" in dish_lower:
            return self.FOOD_IMAGES["cendol"]

        return self.FOOD_IMAGES["default"]

    def get_matching_image(self, text: str, category: str = "all") -> str:
        """
        Get matching image URL for any Malaysian business product/service

        Uses smart keyword matching to find the best image from BUSINESS_IMAGES
        Combines FOOD_IMAGES and BUSINESS_IMAGES for comprehensive coverage

        Args:
            text: Product/service name or description (e.g., "Baju Kurung", "Tudung", "Haircut")
            category: Optional category hint ("fashion", "salon", "beauty", "food", "auto", "all")

        Returns:
            Best matching image URL
        """
        if not text:
            return self.BUSINESS_IMAGES["default"]

        text_lower = text.lower().strip()

        # Combine food and business images for comprehensive matching
        all_images = {**self.FOOD_IMAGES, **self.BUSINESS_IMAGES}

        # Direct exact match
        if text_lower in all_images:
            logger.info(f"🎯 Exact match for '{text}': {all_images[text_lower][:60]}...")
            return all_images[text_lower]

        # Fuzzy matching - check if text contains any key or vice versa
        best_match = None
        best_score = 0.0
        best_url = None

        for key, url in all_images.items():
            if key == "default":
                continue

            # Check if key is in text or vice versa
            if key in text_lower:
                score = len(key) / len(text_lower)
                if score > best_score:
                    best_score = score
                    best_match = key
                    best_url = url
            elif text_lower in key:
                score = len(text_lower) / len(key)
                if score > best_score:
                    best_score = score
                    best_match = key
                    best_url = url

        # Return if we have a good match (30% similarity or higher)
        if best_url and best_score >= 0.3:
            logger.info(f"🎯 Fuzzy match for '{text}' → '{best_match}' (score: {best_score:.2f})")
            return best_url

        # Keyword-based fallback for common categories
        # Fashion & Clothing
        if any(word in text_lower for word in ['baju', 'kurung', 'melayu', 'traditional', 'dress']):
            return self.BUSINESS_IMAGES.get("baju kurung", self.BUSINESS_IMAGES["clothing"])
        if any(word in text_lower for word in ['tudung', 'hijab', 'headscarf', 'shawl']):
            return self.BUSINESS_IMAGES.get("tudung", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['kebaya', 'blouse']):
            return self.BUSINESS_IMAGES.get("kebaya", self.BUSINESS_IMAGES["clothing"])
        if any(word in text_lower for word in ['pakaian', 'clothing', 'fashion', 'boutique']):
            return self.BUSINESS_IMAGES.get("clothing", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['jewelry', 'brooch', 'anting', 'necklace', 'rantai', 'accessories']):
            return self.BUSINESS_IMAGES.get("accessories", self.BUSINESS_IMAGES["default"])

        # Hair Salon
        if any(word in text_lower for word in ['haircut', 'potong rambut', 'gunting', 'cut']):
            return self.BUSINESS_IMAGES.get("haircut", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['hair color', 'cat rambut', 'warna', 'coloring', 'dye']):
            return self.BUSINESS_IMAGES.get("hair coloring", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['hair treatment', 'rawatan rambut', 'hair spa']):
            return self.BUSINESS_IMAGES.get("hair treatment", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['styling', 'blowdry', 'blow dry']):
            return self.BUSINESS_IMAGES.get("hair styling", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['salon', 'rambut', 'hair']):
            return self.BUSINESS_IMAGES.get("salon", self.BUSINESS_IMAGES["default"])

        # Beauty & Spa
        if any(word in text_lower for word in ['facial', 'rawatan muka', 'face treatment']):
            return self.BUSINESS_IMAGES.get("facial", self.BUSINESS_IMAGES["beauty"])
        if any(word in text_lower for word in ['massage', 'urut', 'body massage']):
            return self.BUSINESS_IMAGES.get("massage", self.BUSINESS_IMAGES["spa"])
        if any(word in text_lower for word in ['manicure', 'pedicure', 'nail', 'nails']):
            return self.BUSINESS_IMAGES.get("manicure", self.BUSINESS_IMAGES["beauty"])
        if any(word in text_lower for word in ['makeup', 'makeover', 'solek']):
            return self.BUSINESS_IMAGES.get("makeup", self.BUSINESS_IMAGES["beauty"])
        if any(word in text_lower for word in ['spa', 'beauty', 'kecantikan']):
            return self.BUSINESS_IMAGES.get("beauty", self.BUSINESS_IMAGES["default"])

        # Automotive
        if any(word in text_lower for word in ['car wash', 'cuci kereta', 'auto wash', 'wash']):
            return self.BUSINESS_IMAGES.get("car wash", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['bengkel', 'workshop', 'repair', 'mechanic']):
            return self.BUSINESS_IMAGES.get("bengkel", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['car service', 'servis kereta', 'auto service', 'servicing']):
            return self.BUSINESS_IMAGES.get("car service", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['tire', 'tyre', 'tayar']):
            return self.BUSINESS_IMAGES.get("tire service", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['kereta', 'car', 'automotive', 'auto']):
            return self.BUSINESS_IMAGES.get("car", self.BUSINESS_IMAGES["default"])

        # Food (use existing get_food_image for better food matching)
        if any(word in text_lower for word in ['nasi', 'mee', 'rice', 'noodle', 'food', 'makan', 'dish']):
            food_img = self.get_food_image(text)
            if food_img != self.FOOD_IMAGES["default"]:
                return food_img

        # Other categories
        if any(word in text_lower for word in ['bakery', 'roti', 'bread', 'cake', 'kek']):
            return self.BUSINESS_IMAGES.get("bakery", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['flower', 'bunga', 'florist']):
            return self.BUSINESS_IMAGES.get("florist", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['pet', 'haiwan', 'cat', 'dog']):
            return self.BUSINESS_IMAGES.get("pet shop", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['grocery', 'runcit', 'mini market', 'mart']):
            return self.BUSINESS_IMAGES.get("grocery", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['laundry', 'dobi']):
            return self.BUSINESS_IMAGES.get("laundry", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['cafe', 'kafe', 'coffee', 'kopi']):
            return self.BUSINESS_IMAGES.get("cafe", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['restaurant', 'restoran']):
            return self.BUSINESS_IMAGES.get("restaurant", self.BUSINESS_IMAGES["default"])

        # Final fallback
        logger.info(f"⚠️ No specific match for '{text}', using default")
        return self.BUSINESS_IMAGES["default"]

    def get_smart_image_prompt(self, text: str) -> Tuple[str, float]:
        """
        Get smart image prompt using fuzzy matching for Malaysian food

        Returns: (prompt, confidence_score)
        """
        if not text:
            return ("", 0.0)

        text_lower = text.lower().strip()

        # Direct exact match
        if text_lower in self.MALAYSIAN_FOOD_PROMPTS:
            logger.info(f"🎯 Exact match found: {text_lower}")
            return (self.MALAYSIAN_FOOD_PROMPTS[text_lower], 1.0)

        # Fuzzy matching - find best match
        best_match = None
        best_score = 0.0
        best_prompt = ""

        for dish_name, prompt in self.MALAYSIAN_FOOD_PROMPTS.items():
            # Calculate similarity score
            score = SequenceMatcher(None, text_lower, dish_name).ratio()

            # Also check if text contains the dish name or vice versa
            if dish_name in text_lower:
                score = max(score, 0.9)
            elif text_lower in dish_name:
                score = max(score, 0.85)

            # Check word-by-word matching for partial matches
            text_words = set(text_lower.split())
            dish_words = set(dish_name.split())
            common_words = text_words & dish_words
            if common_words:
                word_match_score = len(common_words) / max(len(text_words), len(dish_words))
                score = max(score, word_match_score * 0.8)

            if score > best_score:
                best_score = score
                best_match = dish_name
                best_prompt = prompt

        # Only use fuzzy match if confidence is high enough
        if best_score >= 0.6:
            logger.info(f"🎯 Fuzzy match: '{text}' → '{best_match}' (confidence: {best_score:.2f})")
            return (best_prompt, best_score)
        else:
            logger.info(f"⚠️ No good match for '{text}' (best: {best_match} at {best_score:.2f})")
            return ("", best_score)

    async def analyze_uploaded_image(self, image_url: str) -> Dict:
        """
        Analyze an uploaded image using AI Vision to detect its content.
        
        This helps:
        1. Suggest names for images without user-provided names
        2. Detect image content type (food, salon service, product, etc.)
        3. Warn about mismatches between image content and business type
        
        Args:
            image_url: URL of the uploaded image (Cloudinary or other CDN)
            
        Returns:
            Dict with:
            - suggested_name: Suggested item name
            - category: Detected category (food, salon, clothing, etc.)
            - description: Short description of the image
            - confidence: Confidence level (high, medium, low)
            - is_food: Boolean indicating if this appears to be food
        """
        logger.info(f"🔍 Analyzing uploaded image: {image_url[:60]}...")
        
        default_result = {
            "suggested_name": None,
            "category": "unknown",
            "description": "Unable to analyze image",
            "confidence": "low",
            "is_food": False
        }
        
        try:
            # Use Qwen VL (Vision-Language) for image analysis
            # Qwen-VL-Max supports image input via URL
            if self.qwen_api_key:
                logger.info("🟡 Using Qwen-VL for image analysis...")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.qwen_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.qwen_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "qwen-vl-max",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "image_url",
                                            "image_url": {"url": image_url}
                                        },
                                        {
                                            "type": "text",
                                            "text": """Analyze this image and respond in JSON format:
{
  "suggested_name": "Item name in Malay or English (e.g., 'Nasi Lemak Special', 'Haircut Men')",
  "category": "food|salon|clothing|product|other",
  "description": "Brief description of what you see",
  "is_food": true/false,
  "food_type": "malaysian|western|asian|dessert|beverage|none"
}

If it's Malaysian food, suggest authentic Malay names.
If it's a service (haircut, treatment), describe the service.
Respond ONLY with valid JSON, no other text."""
                                        }
                                    ]
                                }
                            ],
                            "temperature": 0.3,
                            "max_tokens": 200
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result["choices"][0]["message"]["content"].strip()
                        logger.info(f"🟡 Qwen-VL response: {content[:100]}...")
                        
                        # Parse JSON response
                        import json as json_module
                        try:
                            # Clean up response - remove markdown code blocks if present
                            if content.startswith("```"):
                                content = content.split("```")[1]
                                if content.startswith("json"):
                                    content = content[4:]
                            content = content.strip()
                            
                            analysis = json_module.loads(content)
                            analysis["confidence"] = "high"
                            logger.info(f"✅ Image analyzed: {analysis.get('suggested_name')} - {analysis.get('category')}")
                            return analysis
                        except json_module.JSONDecodeError:
                            logger.warning(f"⚠️ Could not parse Qwen-VL response as JSON")
                    else:
                        logger.warning(f"⚠️ Qwen-VL failed: {response.status_code}")
            
            # Fallback to DeepSeek (if it supports vision)
            if self.deepseek_api_key:
                logger.info("🔷 Trying DeepSeek for image analysis...")
                # Note: DeepSeek chat doesn't support vision, but we can try
                # to describe based on URL patterns or use a different approach
                
            return default_result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing image: {e}")
            return default_result

    async def analyze_images_batch(self, images: List[Dict]) -> List[Dict]:
        """
        Analyze a batch of uploaded images.
        
        Args:
            images: List of image dicts with 'url' and optional 'name'
            
        Returns:
            List of analysis results with suggested names and categories
        """
        results = []
        for img in images:
            url = img.get('url', '') if isinstance(img, dict) else str(img)
            existing_name = img.get('name', '') if isinstance(img, dict) else ''
            
            if not url:
                continue
                
            # Skip if user already provided a valid name
            if existing_name and existing_name.strip() and existing_name != 'Hero Image':
                results.append({
                    "url": url,
                    "user_name": existing_name,
                    "suggested_name": existing_name,
                    "category": "user_provided",
                    "analyzed": False
                })
                continue
            
            # Analyze the image
            analysis = await self.analyze_uploaded_image(url)
            results.append({
                "url": url,
                "user_name": existing_name,
                "suggested_name": analysis.get("suggested_name"),
                "category": analysis.get("category", "unknown"),
                "description": analysis.get("description"),
                "is_food": analysis.get("is_food", False),
                "analyzed": True
            })
            
            # Small delay between API calls
            await asyncio.sleep(0.5)
        
        return results

    async def test_api_connectivity(self) -> Dict[str, any]:
        """Test connectivity to both AI APIs"""
        results = {
            "qwen": {"status": "not_configured", "error": None},
            "deepseek": {"status": "not_configured", "error": None}
        }

        # Test Qwen API
        if self.qwen_api_key:
            try:
                logger.info("🟡 Testing Qwen API connectivity...")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.post(
                        f"{self.qwen_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.qwen_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "qwen-max",
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 10
                        }
                    )
                    if r.status_code == 200:
                        results["qwen"]["status"] = "connected"
                        logger.info("🟡 Qwen API ✅ Connection successful")
                    else:
                        results["qwen"]["status"] = "error"
                        results["qwen"]["error"] = f"HTTP {r.status_code}: {r.text}"
                        logger.error(f"🟡 Qwen API ❌ Status {r.status_code}")
            except Exception as e:
                results["qwen"]["status"] = "error"
                results["qwen"]["error"] = str(e)
                logger.error(f"🟡 Qwen API ❌ Exception: {e}")

        # Test DeepSeek API
        if self.deepseek_api_key:
            try:
                logger.info("🔷 Testing DeepSeek API connectivity...")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.post(
                        f"{self.deepseek_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.deepseek_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 10
                        }
                    )
                    if r.status_code == 200:
                        results["deepseek"]["status"] = "connected"
                        logger.info("🔷 DeepSeek API ✅ Connection successful")
                    else:
                        results["deepseek"]["status"] = "error"
                        results["deepseek"]["error"] = f"HTTP {r.status_code}: {r.text}"
                        logger.error(f"🔷 DeepSeek API ❌ Status {r.status_code}")
            except Exception as e:
                results["deepseek"]["status"] = "error"
                results["deepseek"]["error"] = str(e)
                logger.error(f"🔷 DeepSeek API ❌ Exception: {e}")

        return results

    # ==================== STABILITY AI IMAGE GENERATION ====================
    async def generate_image(self, prompt: str) -> Optional[str]:
        """Generate image using Stability AI"""
        if not self.stability_api_key:
            logger.info("🎨 No Stability API key")
            return None

        try:
            logger.info(f"🎨 Generating: {prompt[:40]}...")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.stability_api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json={
                        "text_prompts": [
                            {"text": f"{prompt}, professional photography, high quality, realistic", "weight": 1},
                            {"text": "blurry, bad quality, cartoon, illustration, drawing, anime", "weight": -1}
                        ],
                        "cfg_scale": 7,
                        "width": 1024,
                        "height": 576,
                        "steps": 30,
                        "samples": 1,
                        "style_preset": "photographic"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    base64_img = data["artifacts"][0]["base64"]
                    logger.info("🎨 ✅ Image generated")
                    return f"data:image/png;base64,{base64_img}"
                else:
                    logger.error(f"🎨 ❌ Failed: {response.status_code}")
        except Exception as e:
            logger.error(f"🎨 ❌ Error: {e}")

        return None

    def get_image_prompts(self, description: str) -> Dict:
        """Get image prompts based on business description - WITH MALAYSIAN FOOD SUPPORT"""
        d = description.lower()

        # Check for Malaysian food dishes using smart matching
        logger.info(f"🍽️ Analyzing description for Malaysian food: {description[:100]}...")

        # Try to find Malaysian food mentions in the description
        words = d.split()
        detected_dishes = []

        # Check for multi-word dish names (like "nasi lemak", "char kway teow")
        for i in range(len(words)):
            for j in range(i + 1, min(i + 5, len(words) + 1)):  # Check up to 4-word phrases
                phrase = " ".join(words[i:j])
                prompt, confidence = self.get_smart_image_prompt(phrase)
                if prompt and confidence >= 0.6:
                    detected_dishes.append((phrase, prompt, confidence))

        # If we found Malaysian dishes, use them!
        if detected_dishes:
            # Use the best match
            detected_dishes.sort(key=lambda x: x[2], reverse=True)
            best_dish, best_prompt, confidence = detected_dishes[0]

            logger.info(f"🎯 MALAYSIAN FOOD DETECTED: '{best_dish}' (confidence: {confidence:.2f})")

            # Generate 4 different prompts for gallery
            gallery_prompts = [best_prompt]

            # Add variations
            if "nasi" in best_dish:
                gallery_prompts.extend([
                    best_prompt.replace("plate", "serving platter"),
                    f"Close-up of {best_dish} showing delicious details",
                    f"Traditional Malaysian {best_dish} in authentic setting"
                ])
            elif "mee" in best_dish or "laksa" in best_dish or "noodle" in best_dish:
                gallery_prompts.extend([
                    best_prompt.replace("noodles", "noodle bowl close-up"),
                    f"Steaming hot bowl of {best_dish}",
                    f"Traditional {best_dish} with all toppings"
                ])
            else:
                gallery_prompts.extend([
                    best_prompt + ", close-up view",
                    f"Traditional {best_dish} presentation",
                    f"Authentic Malaysian {best_dish}"
                ])

            return {
                "hero": best_prompt,
                "gallery": gallery_prompts[:4]
            }

        # Fallback to existing logic for non-Malaysian food
        if "teddy" in d or "bear" in d or "plush" in d or "patung" in d:
            return {
                "hero": "Cute teddy bear shop with soft plush toys on shelves, warm cozy lighting",
                "gallery": [
                    "Adorable brown teddy bear sitting, soft fluffy plush toy",
                    "Collection of colorful teddy bears on display",
                    "Giant pink teddy bear in gift shop",
                    "Small cute teddy bears with ribbon bows"
                ]
            }

        if "ikan" in d or "fish" in d or "seafood" in d:
            return {
                "hero": "Fresh fish market with seafood on ice display",
                "gallery": [
                    "Fresh red snapper fish on ice",
                    "Fresh prawns and shrimp display",
                    "Fresh salmon fillets at counter",
                    "Variety of tropical fish"
                ]
            }

        if "makan" in d or "restoran" in d or "food" in d or "nasi" in d:
            return {
                "hero": "Modern Malaysian restaurant interior with warm lighting",
                "gallery": [
                    "Delicious nasi lemak with sambal",
                    "Chef cooking in restaurant kitchen",
                    "Elegant restaurant table setting",
                    "Malaysian cuisine dishes spread"
                ]
            }

        if any(w in d for w in ['salon', 'rambut', 'hair', 'beauty']):
            return {
                "hero": "Modern luxury hair salon interior",
                "gallery": [
                    "Hairstylist cutting hair in salon",
                    "Hair coloring treatment",
                    "Hair washing station",
                    "Hair styling products"
                ]
            }

        if any(w in d for w in ['kucing', 'cat', 'pet']):
            return {
                "hero": "Modern pet shop with cute cats",
                "gallery": [
                    "Adorable orange tabby cat",
                    "Cat food and supplies",
                    "Playful kittens",
                    "Cat grooming service"
                ]
            }

        if "bakery" in d or "roti" in d or "kek" in d or "cake" in d:
            return {
                "hero": "Artisan bakery with fresh bread and pastries",
                "gallery": [
                    "Fresh baked bread loaves",
                    "Decorated birthday cakes",
                    "Croissants and pastries",
                    "Baker preparing dough"
                ]
            }

        if "kereta" in d or "car" in d or "bengkel" in d or "workshop" in d:
            return {
                "hero": "Modern car workshop garage",
                "gallery": [
                    "Mechanic working on car engine",
                    "Car tire service",
                    "Auto mechanic under car",
                    "Automotive service center"
                ]
            }

        # Default
        return {
            "hero": f"{description} business storefront, professional",
            "gallery": [
                f"{description} products",
                f"{description} service",
                f"Customer at {description}",
                f"{description} interior"
            ]
        }

    async def generate_business_images(self, description: str) -> Optional[Dict]:
        """Generate all images for a business"""
        if not self.stability_api_key:
            return None

        prompts = self.get_image_prompts(description)

        logger.info("🎨 GENERATING IMAGES WITH STABILITY AI...")

        # Generate hero
        import asyncio
        hero = await self.generate_image(prompts["hero"])
        if not hero:
            return None

        # Generate gallery
        gallery = []
        for i, prompt in enumerate(prompts["gallery"]):
            logger.info(f"🎨 Gallery {i+1}/4...")
            img = await self.generate_image(prompt)
            if img:
                gallery.append(img)
            await asyncio.sleep(0.3)

        if len(gallery) < 3:
            return None

        logger.info(f"🎨 ✅ Generated {len(gallery) + 1} images")
        return {"hero": hero, "gallery": gallery}

    async def generate_food_image(self, food_name: str) -> Optional[str]:
        """
        Generate AI image for a food item using the full pipeline:
        1. DeepSeek/Qwen generates detailed English description
        2. Stability AI generates image from description
        3. Image uploaded to Cloudinary

        Args:
            food_name: Name of the food item (e.g., "Nasi Kandar Special", "Ayam Goreng Berempah")

        Returns:
            Cloudinary URL of generated image, or None if generation fails
        """
        if not self.stability_api_key:
            logger.warning("🎨 No Stability API key configured")
            return None

        try:
            logger.info(f"🎨 Generating AI image for: {food_name}")

            # Step 1: Check if it's a known Malaysian dish - prioritize Malaysian prompts
            malaysian_prompt = self._get_malaysian_prompt(food_name)
            if malaysian_prompt and "Malaysian" in malaysian_prompt:
                # Known Malaysian dish - use predefined prompt for accuracy
                detailed_description = malaysian_prompt
                logger.info(f"🇲🇾 Using Malaysian-specific prompt: {detailed_description[:100]}...")
            else:
                # Unknown dish - generate description using AI
                detailed_description = await self._generate_food_description(food_name)
                if not detailed_description:
                    logger.warning(f"⚠️ Failed to generate description, using generic fallback")
                    detailed_description = malaysian_prompt or f"{food_name}, professional food photography, high quality, realistic"
                else:
                    logger.info(f"📝 AI Description: {detailed_description[:100]}...")

            # Step 2: Generate image with Stability AI using the detailed description
            image_url = await self._generate_stability_image(detailed_description)

            if image_url:
                logger.info(f"✅ Generated image: {image_url[:60]}...")
            else:
                logger.warning(f"⚠️ Failed to generate image for: {food_name}")

            return image_url
        except Exception as e:
            logger.error(f"❌ Error generating food image: {e}")
            return None

    async def _generate_food_description(self, food_name: str) -> Optional[str]:
        """
        Use DeepSeek/Qwen to generate a detailed English description for Stability AI

        Args:
            food_name: Name of the food (e.g., "Nasi Kandar Special")

        Returns:
            Detailed English description for image generation, or None if failed
        """
        try:
            # Prepare prompt for AI to generate image description
            system_prompt = """You are an expert at creating detailed image prompts for AI image generation, specializing in Malaysian cuisine.

CRITICAL: Pay attention to the food's origin and style:
- Malaysian dishes (nasi kandar, ayam goreng, ikan bakar, etc.) should be described in authentic Malaysian/Mamak style
- Avoid confusing Malaysian food with Chinese, Thai, or other Asian cuisines
- Use specific Malaysian ingredients and presentation (banana leaf, curry gravy, sambal, etc.)

Focus on:
- Visual appearance (colors, textures, arrangement)
- Authentic traditional presentation (mamak style for Malaysian food)
- Serving method (banana leaf, plate, traditional serving)
- Specific ingredients visible (curry, rice, sambal for Malaysian)
- Photography style (food photography, professional lighting)

Keep the description concise (under 100 words) but highly descriptive and culturally accurate."""

            user_prompt = f"""Create a detailed image generation prompt for: "{food_name}"

IMPORTANT:
- If this contains "nasi", "ayam", "ikan", "mee" or other Malay words, it's MALAYSIAN food
- Describe Malaysian dishes authentically with curry, rice, sambal, banana leaf
- DO NOT describe Malaysian food as Chinese food
- Use "Malaysian" explicitly in the description for Malaysian dishes

Format: Just the image description, no explanations."""

            # Try DeepSeek first (better for descriptions)
            if self.deepseek_api_key:
                logger.info(f"🔷 Using DeepSeek to generate description for: {food_name}")
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.post(
                            f"{self.deepseek_base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.deepseek_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "deepseek-chat",
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                "temperature": 0.7,
                                "max_tokens": 200
                            }
                        )

                        if response.status_code == 200:
                            result = response.json()
                            description = result["choices"][0]["message"]["content"].strip()
                            logger.info(f"✅ DeepSeek generated description")
                            return description
                        else:
                            logger.warning(f"DeepSeek failed: {response.status_code}")
                except Exception as e:
                    logger.warning(f"DeepSeek error: {e}")

            # Fallback to Qwen
            if self.qwen_api_key:
                logger.info(f"🟡 Using Qwen to generate description for: {food_name}")
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.post(
                            f"{self.qwen_base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.qwen_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "qwen-max",
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                "temperature": 0.7,
                                "max_tokens": 200
                            }
                        )

                        if response.status_code == 200:
                            result = response.json()
                            description = result["choices"][0]["message"]["content"].strip()
                            logger.info(f"✅ Qwen generated description")
                            return description
                        else:
                            logger.warning(f"Qwen failed: {response.status_code}")
                except Exception as e:
                    logger.warning(f"Qwen error: {e}")

            # No AI available
            logger.warning("No AI service available for description generation")
            return None

        except Exception as e:
            logger.error(f"Error generating food description: {e}")
            return None

    async def _generate_stability_image(self, prompt: str) -> Optional[str]:
        """Generate image with Stability AI and upload to Cloudinary"""
        stability_key = os.getenv("STABILITY_API_KEY")
        if not stability_key:
            logger.warning("🎨 No STABILITY_API_KEY")
            return None

        try:
            # Smart prompt for Malaysian context
            smart_prompt = self._get_malaysian_prompt(prompt)
            logger.info(f"🎨 Prompt: {smart_prompt[:80]}...")

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.stability.ai/v2beta/stable-image/generate/core",
                    headers={
                        "Authorization": f"Bearer {stability_key}",
                        "Accept": "image/*"
                    },
                    files={"none": ""},
                    data={
                        "prompt": smart_prompt,
                        "output_format": "png",
                        "aspect_ratio": "16:9"
                    }
                )

                if response.status_code == 200:
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        response.content,
                        folder="binaapp"
                    )
                    url = result.get("secure_url")
                    logger.info(f"☁️ Uploaded to Cloudinary: {url[:50]}...")
                    return url
                else:
                    logger.error(f"🎨 Stability AI failed: {response.status_code} - {response.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"🎨 Error generating image: {e}")
            return None

    def _get_malaysian_prompt(self, item: str) -> str:
        """Convert Malaysian food names to detailed prompts"""
        prompts = {
            "nasi kandar": "Malaysian nasi kandar with rice, curry chicken, vegetables, banana leaf, food photography, high quality, realistic",
            "nasi lemak": "Malaysian nasi lemak coconut rice, sambal, egg, anchovies, peanuts, banana leaf, food photography, high quality",
            "nasi goreng": "Malaysian nasi goreng fried rice, egg, vegetables, sambal, food photography, high quality",
            "nasi ayam": "Malaysian chicken rice hainanese nasi ayam, roasted chicken, rice, cucumber, food photography",
            "nasi briyani": "Malaysian nasi briyani biryani rice, spiced rice, chicken, raita, food photography",
            "nasi kerabu": "Malaysian nasi kerabu blue rice, herbs, vegetables, fish, food photography, traditional",

            "mee goreng": "Malaysian mee goreng yellow noodles, egg, vegetables, spicy, food photography, high quality",
            "char kway teow": "Malaysian char kway teow flat noodles, prawns, cockles, wok fried, food photography",
            "laksa": "Malaysian laksa spicy noodle soup, coconut milk, shrimp, food photography, traditional",
            "hokkien mee": "Malaysian hokkien mee dark noodles, prawns, pork, food photography, high quality",
            "mee rebus": "Malaysian mee rebus noodles, thick gravy, egg, food photography",

            "ayam goreng": "Malaysian fried chicken ayam goreng berempah, crispy, golden, turmeric, food photography, close up",
            "ayam percik": "Malaysian ayam percik grilled chicken, coconut sauce, food photography, traditional",
            "rendang": "Malaysian beef rendang curry, coconut milk, spicy, food photography, close up, high quality",

            "ikan bakar": "Malaysian ikan bakar grilled fish, sambal, banana leaf, food photography, traditional",
            "ikan": "Malaysian grilled fish, sambal sauce, food photography, high quality",

            "roti canai": "Malaysian roti canai flatbread crispy, served with curry, food photography, close up",
            "roti": "Malaysian roti flatbread, curry, food photography",
            "murtabak": "Malaysian murtabak stuffed pancake, egg, meat, curry, food photography",

            "satay": "Malaysian satay skewered meat, peanut sauce, cucumber, food photography, traditional, close up",

            "teh tarik": "Malaysian teh tarik pulled milk tea, frothy, glass, food photography, traditional",
            "kopi": "Malaysian kopi coffee traditional, glass cup, food photography",

            "cendol": "Malaysian cendol dessert, shaved ice, coconut milk, gula melaka, green jelly, food photography",
            "ais kacang": "Malaysian ais kacang shaved ice dessert, colorful toppings, food photography",

            "pelbagai lauk": "Malaysian mixed side dishes, variety of curries and vegetables, food photography",
            "lauk": "Malaysian side dishes curry vegetables, food photography",
        }

        item_lower = item.lower().strip()

        # Direct exact match
        if item_lower in prompts:
            return prompts[item_lower]

        # Fuzzy matching - check if item contains any key
        for key, prompt in prompts.items():
            if key in item_lower:
                return prompt

        # Generic food prompt
        return f"Professional close-up photo of {item}, Malaysian style, food photography, high quality, realistic, appetizing"

    def _extract_menu_items(self, description: str) -> list:
        """Extract menu items from description"""
        common_items = ["nasi kandar", "nasi lemak", "mee goreng", "ayam goreng",
                        "roti canai", "teh tarik", "ikan bakar", "pelbagai lauk", "satay"]
        found = []
        desc_lower = description.lower()
        for item in common_items:
            if item in desc_lower:
                found.append(item)
        return found if found else ["hero image"]

    def _detect_business_category(self, description: str) -> str:
        """Detect if business is food/restaurant or clothing/fashion"""
        desc_lower = description.lower()

        # Clothing/Fashion keywords
        clothing_keywords = [
            "baju", "shirt", "t-shirt", "kemeja", "fashion", "boutique", "clothing",
            "pakaian", "tudung", "hijab", "scarf", "shawl", "dress", "pants",
            "seluar", "skirt", "jacket", "blazer", "apparel", "garment",
            "butik", "koleksi", "collection", "wear", "attire"
        ]

        # Food/Restaurant keywords
        food_keywords = [
            "nasi", "mee", "ayam", "ikan", "restaurant", "restoran", "cafe",
            "kafe", "kedai makan", "food", "makan", "masak", "cook", "menu",
            "roti", "satay", "rendang", "curry", "mamak", "warung"
        ]

        # Count matches
        clothing_score = sum(1 for keyword in clothing_keywords if keyword in desc_lower)
        food_score = sum(1 for keyword in food_keywords if keyword in desc_lower)

        if clothing_score > food_score:
            return "clothing"
        elif food_score > 0:
            return "food"
        else:
            return "general"

    def _extract_clothing_items(self, description: str) -> list:
        """Extract clothing/fashion items from description"""
        common_items = ["shirt", "baju", "t-shirt", "kemeja", "seluar", "pants",
                        "dress", "tudung", "hijab", "koleksi", "collection"]
        found = []
        desc_lower = description.lower()
        for item in common_items:
            if item in desc_lower:
                found.append(item)
        # If nothing found, return generic clothing items
        return found if found else ["shirt", "baju", "koleksi", "collection"]

    def _get_clothing_prompt(self, item: str) -> str:
        """Get appropriate Stability AI prompt for clothing items"""
        item_lower = item.lower()

        prompts = {
            "shirt": "Premium men's dress shirt on mannequin, elegant fabric, professional product photography, boutique setting",
            "baju": "Malaysian men's traditional and modern clothing, baju melayu and casual shirts, fashion photography",
            "t-shirt": "Stylish men's t-shirt on display, modern casual wear, product photography",
            "kemeja": "Elegant men's formal shirt, crisp fabric, professional fashion photography",
            "seluar": "Men's premium pants on display, formal and casual wear, boutique photography",
            "pants": "Men's premium pants on display, formal and casual wear, boutique photography",
            "dress": "Elegant dress on mannequin, luxury boutique setting, fashion photography",
            "tudung": "Elegant hijab tudung collection display, various styles, Malaysian fashion photography",
            "hijab": "Elegant hijab collection display, various colors and styles, fashion photography",
            "koleksi": "Stylish men's clothing collection display, premium shirts and apparel, boutique setting",
            "collection": "Premium men's clothing collection, modern boutique display, fashion photography",
        }

        for key, prompt in prompts.items():
            if key in item_lower:
                return prompt

        return f"Professional {item} display, Malaysian boutique, fashion photography"

    # Malay to English translation for Stability AI
    MALAY_TO_ENGLISH = {
        "jam tangan": "wristwatch timepiece",
        "jam": "watch clock",
        "baju": "shirt clothing garment",
        "kasut": "shoes footwear",
        "tudung": "hijab headscarf",
        "makanan": "food cuisine",
        "restoran": "restaurant dining",
        "kedai": "shop store",
        "perkhidmatan": "services",
        "kecantikan": "beauty cosmetics",
        "salon": "hair salon beauty parlor",
        "nasi": "rice dish",
        "mee": "noodles",
        "ayam": "chicken",
        "ikan": "fish seafood",
        "daging": "beef meat",
        "sayur": "vegetables",
        "kuih": "traditional cakes pastries",
        "minuman": "beverages drinks",
    }

    def _translate_for_stability(self, text: str) -> str:
        """Translate Malay keywords to English for Stability AI"""
        text_lower = text.lower()
        for malay, english in self.MALAY_TO_ENGLISH.items():
            if malay in text_lower:
                text_lower = text_lower.replace(malay, english)
        return text_lower

    def _get_product_prompts(self, description: str, business_category: str) -> list:
        """Generate smart product image prompts based on business type"""
        desc_lower = description.lower()

        # Translate Malay to English for better detection
        desc_english = self._translate_for_stability(description)

        # WATCHES / JEWELRY
        if any(word in desc_lower for word in ["watch", "jam tangan", "timepiece", "jam"]):
            return [
                "Luxury silver wristwatch on white background, product photography, elegant timepiece, professional lighting",
                "Black sports watch with rubber strap, waterproof dive watch, product photography, studio lighting",
                "Rose gold women's watch with diamond bezel, luxury feminine timepiece, product photography, elegant display",
                "Chronograph watch with leather strap, men's luxury watch, detailed product photography, white background"
            ]

        # JEWELRY / ACCESSORIES
        elif any(word in desc_lower for word in ["jewelry", "necklace", "bracelet", "ring", "earing", "perhiasan"]):
            return [
                "Gold necklace on display, luxury jewelry, product photography, elegant presentation",
                "Silver bracelet on white background, premium jewelry, professional product photography",
                "Diamond ring on velvet cushion, luxury engagement ring, professional jewelry photography",
                "Pearl earrings on display, elegant jewelry, product photography, studio lighting"
            ]

        # CLOTHING / FASHION (already handled but adding here for completeness)
        elif business_category == "clothing":
            return [
                "Premium men's dress shirt on mannequin, business formal, product photography",
                "Casual men's polo shirt, modern style, product photography",
                "Traditional baju melayu, elegant Malaysian menswear, product photography",
                "Men's casual jacket, modern fashion, product photography"
            ]

        # FOOD / RESTAURANT (already handled but adding here for completeness)
        elif business_category == "food":
            return [
                "Malaysian nasi kandar with curry, food photography, professional lighting",
                "Crispy fried chicken ayam goreng, food photography, delicious presentation",
                "Grilled fish ikan bakar on banana leaf, food photography, authentic Malaysian",
                "Malaysian curry dishes assortment, food photography, colorful spread"
            ]

        # BEAUTY / SALON
        elif any(word in desc_lower for word in ["beauty", "salon", "kecantikan", "spa", "facial", "makeup"]):
            return [
                "Professional hair styling service, modern salon interior, beauty photography",
                "Facial treatment spa session, relaxing ambiance, professional beauty photography",
                "Makeup application service, cosmetics display, professional beauty photography",
                "Manicure pedicure service, nail salon, professional beauty photography"
            ]

        # GENERIC FALLBACK - use business type
        else:
            business_type = request.business_type if hasattr(self, 'request') else "product"
            return [
                f"Professional product photo, {business_type}, clean white background, studio lighting",
                f"Premium {business_type} showcase, commercial photography, professional presentation",
                f"Elegant {business_type} display, professional product photography, modern style",
                f"High-end {business_type} product, studio photography, luxury presentation"
            ]

    async def generate_smart_image_prompts(self, description: str) -> dict:
        """Use AI to generate appropriate image prompts for ANY business type"""

        # Check if this is a Malaysian food business - use specific prompts
        desc_lower = description.lower()
        if any(word in desc_lower for word in ['nasi', 'mee', 'ayam', 'ikan', 'restoran', 'restaurant', 'kedai makan', 'warung', 'mamak', 'kandar', 'lemak', 'goreng']):
            logger.info("🍽️ Detected Malaysian food business - using Malaysian food prompts")
            return self._get_malaysian_food_prompts(description)

        prompt = f"""You are an expert at creating image prompts for Stability AI.

BUSINESS DESCRIPTION:
{description}

TASK:
Analyze this business and generate 5 specific image prompts that match this EXACT business type.

IMPORTANT FOR MALAYSIAN FOOD BUSINESSES:
- If it's a Malaysian restaurant/food business, use specific Malaysian dish names
- Examples: "nasi kandar", "nasi lemak", "mee goreng", "char kway teow", "roti canai"
- Each prompt must describe the ACTUAL Malaysian dish, not generic food

RULES:
1. If it's a PHOTOGRAPHER business → generate prompts for cameras, wedding photos, portrait sessions
2. If it's a RESTAURANT/FOOD → generate prompts for SPECIFIC dishes mentioned in description
3. If it's a FASHION store → generate prompts for clothing items, boutique display
4. If it's a SALON → generate prompts for hairstyling, beauty treatments
5. If it's a WATCH/JEWELRY store → generate prompts for watches, jewelry products
6. If it's an AUTOMOTIVE business → generate prompts for cars, workshop, mechanics
7. NEVER generate food images for non-food businesses
8. NEVER generate random/generic images - they must match the EXACT business
9. All prompts must be in ENGLISH for Stability AI
10. Each prompt should be detailed (20-50 words)
11. Include "professional photography" or "food photography" in each prompt
12. For food businesses: Describe the SPECIFIC dishes, not just "food" or "restaurant interior"

OUTPUT FORMAT (JSON only, no explanation):
{{
    "hero": "detailed prompt for hero/banner image",
    "image1": "detailed prompt for first product/service image",
    "image2": "detailed prompt for second product/service image",
    "image3": "detailed prompt for third product/service image",
    "image4": "detailed prompt for fourth product/service image"
}}

Generate prompts now:"""

        try:
            # Use DeepSeek to analyze and generate prompts
            api_key = os.getenv("DEEPSEEK_API_KEY")

            if not api_key:
                logger.warning("🧠 No DEEPSEEK_API_KEY, using fallback prompts")
                return self._get_fallback_prompts(description)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.3
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Parse JSON from response - extract JSON from response
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        prompts = json.loads(json_match.group())
                        logger.info(f"🧠 AI Generated prompts for: {description[:50]}")
                        logger.info(f"🧠 Hero: {prompts.get('hero', '')[:50]}...")
                        return prompts
                else:
                    logger.error(f"🧠 DeepSeek API failed: {response.status_code}")

        except Exception as e:
            logger.error(f"🧠 Smart prompt generation failed: {e}")

        # Fallback - use specific prompts based on business type
        return self._get_fallback_prompts(description)

    def _get_malaysian_food_prompts(self, description: str) -> dict:
        """Generate Malaysian food-specific prompts using MALAYSIAN_FOOD_PROMPTS database"""
        desc_lower = description.lower()

        # Find specific Malaysian dishes mentioned in description
        dishes_found = []
        for dish_name, prompt in self.MALAYSIAN_FOOD_PROMPTS.items():
            if dish_name in desc_lower:
                dishes_found.append((dish_name, prompt))

        # If we found specific dishes, use them
        if len(dishes_found) >= 4:
            logger.info(f"🍽️ Found {len(dishes_found)} Malaysian dishes in description")
            return {
                "hero": f"Malaysian restaurant interior, traditional food stall, authentic atmosphere, food photography, welcoming ambiance",
                "image1": dishes_found[0][1] + ", professional food photography, high quality, appetizing",
                "image2": dishes_found[1][1] + ", professional food photography, high quality, delicious",
                "image3": dishes_found[2][1] + ", professional food photography, high quality, authentic",
                "image4": dishes_found[3][1] + ", professional food photography, high quality, traditional"
            }

        # Default Malaysian food prompts - common dishes
        logger.info("🍽️ Using default Malaysian food prompts")
        return {
            "hero": "Malaysian restaurant interior, food stall with hanging menu, authentic atmosphere, people eating, warm lighting, food photography",
            "image1": self.MALAYSIAN_FOOD_PROMPTS["nasi kandar"] + ", professional food photography, close-up, appetizing presentation",
            "image2": self.MALAYSIAN_FOOD_PROMPTS["nasi lemak"] + ", professional food photography, banana leaf, traditional serving",
            "image3": self.MALAYSIAN_FOOD_PROMPTS["mee goreng"] + ", professional food photography, wok-fried, steaming hot",
            "image4": self.MALAYSIAN_FOOD_PROMPTS["roti canai"] + ", professional food photography, curry sauce, close-up"
        }

    def _get_fallback_prompts(self, description: str) -> dict:
        """Generate fallback prompts when AI fails"""
        desc_lower = description.lower()

        # Check if it's a Malaysian food business
        if any(word in desc_lower for word in ['nasi', 'mee', 'ayam', 'ikan', 'restoran', 'restaurant', 'kedai makan', 'warung', 'mamak']):
            return self._get_malaysian_food_prompts(description)

        # Check for other business types
        if any(word in desc_lower for word in ['salon', 'rambut', 'hair', 'beauty', 'kecantikan']):
            return {
                "hero": "Modern hair salon interior, styling chairs, mirrors, professional lighting, commercial photography",
                "image1": "Professional haircut service, stylist cutting hair, modern salon, beauty photography",
                "image2": "Hair coloring treatment, professional hair color application, salon interior, beauty photography",
                "image3": "Hair treatment service, professional hair spa, relaxing atmosphere, beauty photography",
                "image4": "Hair styling service, blow dry, professional salon, beauty photography"
            }

        if any(word in desc_lower for word in ['baju', 'pakaian', 'fashion', 'clothing', 'boutique', 'tudung']):
            return {
                "hero": "Modern fashion boutique interior, clothing displays, elegant atmosphere, commercial photography",
                "image1": "Traditional baju kurung display, elegant Malaysian clothing, product photography, boutique setting",
                "image2": "Hijab and tudung collection, colorful scarves, product photography, elegant display",
                "image3": "Fashion accessories display, jewelry and brooches, product photography, luxury presentation",
                "image4": "Clothing boutique interior, modern retail space, professional photography"
            }

        # Generic business fallback
        desc_short = description[:50]
        return {
            "hero": f"Professional business establishment for {desc_short}, modern interior, welcoming atmosphere, commercial photography",
            "image1": f"Professional service showcase for {desc_short}, high quality, commercial photography",
            "image2": f"Business products and services, {desc_short}, professional setting, product photography",
            "image3": f"Customer experience at business, {desc_short}, professional photography",
            "image4": f"Quality service delivery, {desc_short}, commercial photography"
        }

    async def _improve_with_qwen(self, html: str, description: str) -> str:
        """Use Qwen to improve content"""
        prompt = (
            "Improve the copywriting in this HTML for a Malaysian business.\n"
            "STRICT RULES:\n"
            "- Do NOT add new facts (no invented addresses, phone numbers, awards, years, prices, or claims).\n"
            "- Do NOT change any links (especially WhatsApp wa.me links).\n"
            "- Keep all image URLs unchanged.\n"
            "- Keep the language consistent with the existing page (if it's Bahasa Malaysia, keep it fully Bahasa Malaysia; do NOT introduce English headings).\n"
            "- Only improve wording/clarity while preserving meaning.\n\n"
            f"{html}"
        )
        improved = await self._call_qwen(prompt, temperature=0.7)
        return improved if improved else html

    def get_fallback_images(self, description: str) -> Dict:
        """Get fallback stock images using comprehensive image matching"""
        d = description.lower()

        # Use get_matching_image for smart image selection
        hero_img = self.get_matching_image(description)

        # Generate gallery images based on description keywords
        gallery_images = []

        # Extract key products/services from description
        # Split into words and try to match each phrase
        words = d.split()

        # Try to find specific products/services mentioned
        for i in range(len(words)):
            if len(gallery_images) >= 4:
                break
            for j in range(min(i + 3, len(words)), i, -1):  # Check up to 3-word phrases
                phrase = " ".join(words[i:j])
                if len(phrase) >= 3:  # Skip very short words
                    img = self.get_matching_image(phrase)
                    if img not in gallery_images and img != self.BUSINESS_IMAGES["default"]:
                        gallery_images.append(img)
                        break

        # If we didn't find enough specific images, add category-based defaults
        if len(gallery_images) < 4:
            # Detect business type and add relevant category images
            if any(w in d for w in ['baju', 'tudung', 'fashion', 'pakaian']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("baju kurung", self.BUSINESS_IMAGES["clothing"]),
                    self.BUSINESS_IMAGES.get("tudung", self.BUSINESS_IMAGES["clothing"]),
                    self.BUSINESS_IMAGES.get("kebaya", self.BUSINESS_IMAGES["clothing"]),
                    self.BUSINESS_IMAGES.get("accessories", self.BUSINESS_IMAGES["clothing"])
                ]
            elif any(w in d for w in ['salon', 'rambut', 'hair']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("haircut", self.BUSINESS_IMAGES["salon"]),
                    self.BUSINESS_IMAGES.get("hair coloring", self.BUSINESS_IMAGES["salon"]),
                    self.BUSINESS_IMAGES.get("hair treatment", self.BUSINESS_IMAGES["salon"]),
                    self.BUSINESS_IMAGES.get("hair styling", self.BUSINESS_IMAGES["salon"])
                ]
            elif any(w in d for w in ['beauty', 'kecantikan', 'spa']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("facial", self.BUSINESS_IMAGES["beauty"]),
                    self.BUSINESS_IMAGES.get("massage", self.BUSINESS_IMAGES["spa"]),
                    self.BUSINESS_IMAGES.get("manicure", self.BUSINESS_IMAGES["beauty"]),
                    self.BUSINESS_IMAGES.get("makeup", self.BUSINESS_IMAGES["beauty"])
                ]
            elif any(w in d for w in ['kereta', 'car', 'bengkel', 'automotive']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("car wash", self.BUSINESS_IMAGES["car"]),
                    self.BUSINESS_IMAGES.get("bengkel", self.BUSINESS_IMAGES["car"]),
                    self.BUSINESS_IMAGES.get("car service", self.BUSINESS_IMAGES["car"]),
                    self.BUSINESS_IMAGES.get("tire service", self.BUSINESS_IMAGES["car"])
                ]
            elif any(w in d for w in ['nasi', 'makan', 'restoran', 'food']):
                fallback_imgs = [
                    self.FOOD_IMAGES.get("nasi lemak", self.FOOD_IMAGES["default"]),
                    self.FOOD_IMAGES.get("nasi kandar", self.FOOD_IMAGES["default"]),
                    self.FOOD_IMAGES.get("mee goreng", self.FOOD_IMAGES["default"]),
                    self.FOOD_IMAGES.get("roti canai", self.FOOD_IMAGES["default"])
                ]
            else:
                # Use existing IMAGES dict for other types
                biz_type = self._detect_type(description)
                imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])
                fallback_imgs = imgs["gallery"]

            # Add fallback images that aren't already in the list
            for img in fallback_imgs:
                if img not in gallery_images:
                    gallery_images.append(img)
                if len(gallery_images) >= 4:
                    break

        # Ensure we have exactly 4 gallery images
        while len(gallery_images) < 4:
            gallery_images.append(self.BUSINESS_IMAGES["default"])

        return {
            "hero": hero_img,
            "gallery": gallery_images[:4]
        }

    # HARDCODED WORKING IMAGES - Guaranteed to work
    IMAGES = {
        "pet_shop": {
            "hero": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=800&q=80",
                "https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800&q=80",
                "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=800&q=80",
                "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&q=80"
            ]
        },
        "salon": {
            "hero": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&q=80",
                "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=800&q=80",
                "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=800&q=80",
                "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=800&q=80"
            ]
        },
        "restaurant": {
            "hero": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80",
                "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&q=80",
                "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80",
                "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800&q=80"
            ]
        },
        "clothing": {
            "hero": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=800&q=80",
                "https://images.unsplash.com/photo-1558171813-4c088753af8f?w=800&q=80",
                "https://images.unsplash.com/photo-1467043237213-65f2da53396f?w=800&q=80",
                "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=800&q=80"
            ]
        },
        "default": {
            "hero": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
                "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&q=80",
                "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800&q=80",
                "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&q=80"
            ]
        }
    }

    def _detect_type(self, desc: str) -> str:
        """Detect business type"""
        d = desc.lower()
        if any(w in d for w in ['kucing', 'cat', 'pet', 'haiwan', 'anjing', 'dog']):
            return "pet_shop"
        if any(w in d for w in ['salon', 'rambut', 'hair', 'haircut', 'beauty', 'spa', 'kecantikan', 'gunting']):
            return "salon"
        if any(w in d for w in ['makan', 'restoran', 'restaurant', 'food', 'nasi', 'cafe', 'kafe', 'warung']):
            return "restaurant"
        if any(w in d for w in ['pakaian', 'clothing', 'fashion', 'baju', 'boutique', 'fesyen', 'tudung', 'hijab']):
            return "clothing"
        return "default"

    def _build_strict_prompt(
        self,
        name: str,
        desc: str,
        style: str,
        user_images: list = None,
        language: str = "ms",
        whatsapp_number: Optional[str] = None,
        location_address: Optional[str] = None,
    ) -> str:
        """Build STRICT prompt that forbids placeholders"""
        biz_type = self._detect_type(desc)
        imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])

        # Use user images if provided, otherwise use curated Unsplash
        # Helper to extract URL from image (can be string or dict)
        def get_url(img):
            if isinstance(img, dict):
                return img.get('url', img.get('URL', ''))
            return str(img) if img else ''
        
        def get_name(img):
            if isinstance(img, dict):
                return img.get('name', '')
            return ''
        
        # IMPORTANT: Separate hero image from product/gallery images
        # Hero image is ONLY used if explicitly named 'Hero Image'
        # Product/gallery images should NOT appear as hero background
        hero = imgs["hero"]  # Default to curated hero
        gallery_start_index = 0  # Start index for gallery images
        
        if user_images and len(user_images) > 0:
            first_img_name = get_name(user_images[0])
            # Only use first image as hero if it's explicitly a hero image
            if first_img_name == 'Hero Image' or 'hero' in first_img_name.lower():
                hero = get_url(user_images[0])
                gallery_start_index = 1  # Gallery starts from index 1
            # Otherwise, don't use any product image as hero - keep default
            # Product images will be used in gallery section only
        
        # Gallery images - use user's product images (starting after hero if present)
        g1 = get_url(user_images[gallery_start_index]) if user_images and len(user_images) > gallery_start_index else imgs["gallery"][0]
        g2 = get_url(user_images[gallery_start_index + 1]) if user_images and len(user_images) > gallery_start_index + 1 else imgs["gallery"][1]
        g3 = get_url(user_images[gallery_start_index + 2]) if user_images and len(user_images) > gallery_start_index + 2 else imgs["gallery"][2]
        g4 = get_url(user_images[gallery_start_index + 3]) if user_images and len(user_images) > gallery_start_index + 3 else imgs["gallery"][3]

        # Determine language instruction based on explicit language parameter
        if language == "ms":
            language_instruction = """5. LANGUAGE - BAHASA MALAYSIA (WAJIB):
   PENTING: Hasilkan SEMUA kandungan dalam BAHASA MELAYU sepenuhnya!
   ✅ Semua teks MESTI dalam Bahasa Melayu
   ✅ Gunakan: "Selamat Datang", "Tentang Kami", "Hubungi Kami", "Menu", "Perkhidmatan"
   ✅ Navigasi: "Laman Utama", "Menu", "Tentang", "Hubungi"
   ✅ Butang: "Pesan Sekarang", "Hubungi Kami", "Lihat Menu"
   ❌ JANGAN gunakan Bahasa Inggeris untuk kandungan
   ❌ JANGAN tulis tajuk/navigasi dalam English (contoh: Home, About Us, Contact, Services)
   
   CONTOH TEKS YANG BETUL:
   - Hero: "Selamat Datang ke Nama Perniagaan" 
   - About: "Kami menyediakan perkhidmatan terbaik..."
   - Contact: "Hubungi kami untuk sebarang pertanyaan"
   - Footer: "Hak Cipta © 2024. Semua Hak Terpelihara."""
        else:
            language_instruction = """5. LANGUAGE - ENGLISH:
   Generate ALL content in English
   ✅ Use: "Welcome", "About Us", "Contact Us", "Menu", "Services"
   ✅ Navigation: "Home", "Menu", "About", "Contact"
   ✅ Buttons: "Order Now", "Contact Us", "View Menu"
   Keep all text consistent in English throughout."""

        # WhatsApp number normalization for wa.me links (digits only)
        wa_raw = whatsapp_number or "60123456789"
        wa_digits = re.sub(r"\D", "", str(wa_raw))
        if wa_digits.startswith("0"):
            wa_digits = "6" + wa_digits
        elif wa_digits.startswith("1"):
            wa_digits = "60" + wa_digits
        if not wa_digits:
            wa_digits = "60123456789"

        # Only mention an address if we actually have one (avoid AI inventing locations)
        address_line = ""
        if location_address and str(location_address).strip():
            address_line = f"   ✅ Address (use EXACTLY, do not invent): {str(location_address).strip()}"

        examples = ""
        if language == "ms":
            examples = """

CONTOH HERO (tunjuk imej penuh):
<section id="home" class="relative h-[400px] bg-gray-100">
    <img src="HERO_URL" alt="Imej Hero" class="w-full h-full object-contain">
    <div class="absolute inset-0 bg-black/30 flex items-center">
        <!-- kandungan -->
    </div>
</section>

ATAU gaya cover tetapi tunjuk bahagian atas:
<section id="home" class="relative h-[50vh] md:h-[400px]">
    <img src="HERO_URL" alt="Imej Hero" class="w-full h-full object-cover object-top">
</section>

CONTOH KAD GALERI:
<div class="rounded-xl overflow-hidden shadow-lg">
  <img src="..." class="w-full h-48 object-cover" alt="Gambar produk">
  <div class="p-4">
    <h3>Nama Produk</h3>
    <p>Penerangan ringkas</p>
  </div>
</div>
"""
        else:
            examples = """

Example hero that shows FULL image:
<section id="home" class="relative h-[400px] bg-gray-100">
    <img src="HERO_URL" alt="Hero Image" class="w-full h-full object-contain">
    <div class="absolute inset-0 bg-black/30 flex items-center">
        <!-- content -->
    </div>
</section>

OR if you want cover style but show top:
<section id="home" class="relative h-[50vh] md:h-[400px]">
    <img src="HERO_URL" alt="Hero Image" class="w-full h-full object-cover object-top">
</section>

Example gallery card:
<div class="rounded-xl overflow-hidden shadow-lg">
  <img src="..." class="w-full h-48 object-cover" alt="Product image">
  <div class="p-4">
    <h3>Product Name</h3>
    <p>Short description</p>
  </div>
</div>
"""

        return f"""Generate a COMPLETE production-ready HTML website.

BUSINESS: {name}
DESCRIPTION: {desc}
STYLE: {style}
TYPE: {biz_type}
TARGET LANGUAGE: {"BAHASA MALAYSIA" if language == "ms" else "ENGLISH"}

===== CRITICAL RULES - MUST FOLLOW =====

1. USE THESE EXACT IMAGE URLS (copy-paste exactly as shown):
   - HERO IMAGE: {hero}
   - GALLERY IMAGE 1: {g1}
   - GALLERY IMAGE 2: {g2}
   - GALLERY IMAGE 3: {g3}
   - GALLERY IMAGE 4: {g4}

2. ABSOLUTELY FORBIDDEN - DO NOT USE:
   ❌ via.placeholder.com
   ❌ placeholder.com
   ❌ example.com
   ❌ [PLACEHOLDER] or any [ ] brackets
   ❌ [BUSINESS_TAGLINE]
   ❌ [ABOUT_TEXT]
   ❌ [SERVICE_X_NAME]
   ❌ Any text with brackets

3. MUST WRITE REAL CONTENT:
   ✅ Real business name: {name}
   ✅ Real catchy tagline based on the business description
   ✅ Real about section (2-3 sentences about the business)
   ✅ Real service names and descriptions (3-4 services)
   ✅ Real contact message
   ✅ WhatsApp button linking to: https://wa.me/{wa_digits}
{address_line}
   🚫 DO NOT invent phone numbers, addresses, city names, awards, certifications, years, or prices not provided.

4. TECHNICAL REQUIREMENTS:
   - Single complete HTML file
   - Tailwind CSS CDN: <script src="https://cdn.tailwindcss.com"></script>
   - Mobile responsive (critical!)
   - Sections: Header with Navigation, Hero, About, Services/Gallery, Contact, Footer
   - Smooth animations and hover effects
   - Professional {style} design

{language_instruction}

6. IMAGE REQUIREMENTS:
   - Use ONLY the exact URLs provided above
   - Do NOT modify the URLs
   - Do NOT use any other image sources

7. IMAGE SIZE GUIDELINES:
   - Gallery images: Use 'h-48' or 'h-52' (NOT h-64 - too big on desktop!)
   - Gallery images: Use 'object-cover' for proper fill

HERO SECTION - IMPORTANT:
- Use h-[50vh] or h-[400px] (NOT 60vh or 90vh - too tall!)
- Use object-contain (NOT object-cover) if image has logo/text
- OR use object-cover with object-top to show top of image
- Background color behind image: bg-gray-100 or bg-white

{examples}

Generate ONLY the complete HTML code. No explanations. No markdown. Just pure HTML."""

    async def _call_deepseek(self, prompt: str, temperature: float = 0.2) -> Optional[str]:
        """Call DeepSeek API"""
        if not self.deepseek_api_key:
            logger.warning("❌ DEEPSEEK_API_KEY not configured")
            return None

        try:
            logger.info("🔷 Calling DeepSeek API...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    f"{self.deepseek_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You generate production-ready HTML only. Follow constraints exactly. Do not invent facts. Output ONLY HTML.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": 8000,
                    }
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    logger.info(f"🔷 DeepSeek ✅ Generated {len(content)} characters")
                    return content
                else:
                    logger.error(f"🔷 DeepSeek ❌ Status {r.status_code}")
        except Exception as e:
            logger.error(f"🔷 DeepSeek ❌ Exception: {e}")
        return None

    async def _call_qwen(self, prompt: str, temperature: float = 0.2) -> Optional[str]:
        """Call Qwen API"""
        if not self.qwen_api_key:
            logger.warning("❌ QWEN_API_KEY not configured")
            return None

        try:
            logger.info("🟡 Calling Qwen API...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    f"{self.qwen_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.qwen_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-max",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You generate production-ready HTML only. Follow constraints exactly. Do not invent facts. Output ONLY HTML.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": 8000,
                    }
                )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    logger.info(f"🟡 Qwen ✅ Generated {len(content)} characters")
                    return content
                else:
                    logger.error(f"🟡 Qwen ❌ Status {r.status_code}")
        except Exception as e:
            logger.error(f"🟡 Qwen ❌ Exception: {e}")
        return None

    def _extract_html(self, text: str) -> Optional[str]:
        """Extract only HTML from AI response, remove explanations"""
        import re

        if not text:
            return None

        # Remove markdown code blocks
        if "```html" in text:
            match = re.search(r'```html\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)
        elif "```" in text:
            match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)

        # Remove any text before <!DOCTYPE or <html
        if "<!DOCTYPE" in text:
            text = text[text.find("<!DOCTYPE"):]
        elif "<html" in text:
            text = text[text.find("<html"):]

        # Remove any text after </html>
        if "</html>" in text:
            text = text[:text.find("</html>") + 7]

        # Remove common AI explanation patterns
        patterns_to_remove = [
            r"Here's an improved version.*?(?=<!DOCTYPE|<html)",
            r"(?<=</html>).*?###.*",
            r"(?<=</html>).*?Key Improvements:.*",
            r"(?<=</html>).*?\*\*Engaging Descriptions\*\*.*",
            r"^---\s*",  # Remove markdown separators at start
            r"\s*---$",  # Remove markdown separators at end
        ]

        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

        return text.strip()

    def _validate_generated_html(
        self,
        html: str,
        required_image_urls: List[str],
        required_wa_digits: str,
    ) -> List[str]:
        """
        Validate AI output and detect common hallucination/constraint violations.
        Returns list of human-readable errors (empty list means OK).
        """
        errors: List[str] = []
        if not html or not isinstance(html, str):
            return ["Empty HTML output"]

        lower = html.lower()

        # Basic structure
        if "<html" not in lower or "</html>" not in lower:
            errors.append("Missing <html> wrapper")
        if "cdn.tailwindcss.com" not in lower:
            errors.append("Missing Tailwind CDN script (cdn.tailwindcss.com)")

        # Forbidden placeholder patterns
        forbidden_substrings = [
            "via.placeholder.com",
            "placeholder.com",
            "example.com",
            "[business_tagline]",
            "[about_text]",
            "[service_",
        ]
        for s in forbidden_substrings:
            if s in lower:
                errors.append(f"Contains forbidden placeholder/text: '{s}'")

        if re.search(r"\[[^\]]+\]", html):
            errors.append("Contains bracket placeholder text like [SOMETHING]")

        # WhatsApp link correctness
        wa_expected = f"wa.me/{required_wa_digits}"
        if wa_expected.lower() not in lower:
            errors.append(f"Missing or incorrect WhatsApp link (expected '{wa_expected}')")

        # Required image URLs (when user supplied)
        for url in required_image_urls:
            if url and url not in html:
                errors.append(f"Missing required image URL in HTML: {url}")

        return errors

    def _fix_menu_item_images(self, html: str) -> str:
        """
        Fix duplicate product/service images - ensure each item has a unique image

        This function finds product/service items with duplicate images and replaces them
        with unique images based on the product/service name.
        Works for food, fashion, salon services, and all Malaysian business products.
        """
        if not html:
            return html

        import re

        logger.info("🖼️ Fixing product/service images to ensure uniqueness...")

        # Track image URLs we've seen
        image_usage = {}
        replacements = []

        # Pattern to match product/service items with images
        # This matches common HTML patterns for menu/product items:
        # - <img src="..."> followed by text (product name)
        # - Or text followed by <img>
        patterns = [
            # Pattern 1: <img src="URL"> ... <h3>Product Name</h3>
            r'<img[^>]*src="([^"]+)"[^>]*>[\s\S]{0,200}?<h[2-4][^>]*>(.*?)</h[2-4]>',
            # Pattern 2: <h3>Product Name</h3> ... <img src="URL">
            r'<h[2-4][^>]*>(.*?)</h[2-4]>[\s\S]{0,200}?<img[^>]*src="([^"]+)"[^>]*>',
            # Pattern 3: Direct img with alt containing product name
            r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"[^>]*>',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    if 'src=' in match.group(0)[:30]:  # Pattern 1 or 3
                        img_url = match.group(1)
                        item_name = match.group(2).strip()
                    else:  # Pattern 2
                        item_name = match.group(1).strip()
                        img_url = match.group(2)

                    # Clean item name (remove HTML tags)
                    item_name = re.sub(r'<[^>]+>', '', item_name).strip()

                    if not item_name or not img_url:
                        continue

                    # Never "fix" user-provided/CDN images (Cloudinary, etc.).
                    # Only dedupe/replace known stock/placeholder sources.
                    img_url_lower = img_url.lower()
                    if (
                        "images.unsplash.com" not in img_url_lower
                        and "via.placeholder.com" not in img_url_lower
                        and "placeholder.com" not in img_url_lower
                    ):
                        continue

                    # Track this image URL
                    if img_url not in image_usage:
                        image_usage[img_url] = []
                    image_usage[img_url].append(item_name)

        # Find duplicate image URLs
        duplicate_images = {url: items for url, items in image_usage.items() if len(items) > 1}

        if duplicate_images:
            logger.warning(f"⚠️ Found {len(duplicate_images)} image URLs used for multiple items!")
            for url, items in duplicate_images.items():
                logger.warning(f"   {url[:60]}... used for: {', '.join(items[:3])}")

            # Fix duplicates - use comprehensive image matching
            for dup_url, items in duplicate_images.items():
                # Skip the first occurrence, replace others
                for i, item in enumerate(items):
                    if i == 0:
                        continue  # Keep first usage

                    # Get unique image for this item using comprehensive matching
                    new_url = self.get_matching_image(item)
                    logger.info(f"   🔄 Replacing image for '{item}': {new_url}")

            # Simpler approach: Scan for common product/service item patterns and fix images
            fixed_html = html
            seen_urls = set()

            def replace_image(match):
                full_match = match.group(0)
                img_url = match.group(1)

                # Try to extract product/service name from context
                # Look for nearby h2, h3, h4 tags
                context_start = max(0, match.start() - 300)
                context_end = min(len(html), match.end() + 300)
                context = html[context_start:context_end]

                item_name = None
                heading_match = re.search(r'<h[2-4][^>]*>(.*?)</h[2-4]>', context)
                if heading_match:
                    item_name = re.sub(r'<[^>]+>', '', heading_match.group(1)).strip()

                # If we've seen this URL before and we have an item name, replace it
                if img_url in seen_urls and item_name:
                    # Use comprehensive image matching for all product types
                    new_url = self.get_matching_image(item_name)
                    logger.info(f"   🔄 '{item_name}': {img_url[:50]}... → {new_url[:50]}...")
                    return full_match.replace(img_url, new_url)
                else:
                    seen_urls.add(img_url)
                    return full_match

            # Replace images
            fixed_html = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', replace_image, fixed_html)

            logger.info("✅ Product/service images fixed")
            return fixed_html

        logger.info("✅ No duplicate product/service images found")
        return html

    async def _generate_ai_food_images(self, html: str) -> str:
        """
        NEW METHOD: Replace Unsplash food images with AI-generated images

        This is the CRITICAL FIX for Problem #2:
        - Scans HTML for Malaysian food items
        - Generates AI images using DeepSeek/Qwen → Stability AI → Cloudinary pipeline
        - Replaces Unsplash URLs with Cloudinary URLs

        Returns HTML with AI-generated images for food items
        """
        if not html or not self.stability_api_key:
            logger.info("   ⚠️ Skipping AI image generation (no Stability API key)")
            return html

        import re

        logger.info("🎨 GENERATING AI IMAGES FOR MALAYSIAN FOOD ITEMS...")

        # Pattern to find images with food names
        # Matches: <img src="URL"> near <h3>Food Name</h3>
        patterns = [
            r'(<img[^>]*src=")([^"]+unsplash[^"]+)("[^>]*>[\s\S]{0,200}?<h[2-4][^>]*>)(.*?)(</h[2-4]>)',
            r'(<h[2-4][^>]*>)(.*?)(</h[2-4]>[\s\S]{0,200}?<img[^>]*src=")([^"]+unsplash[^"]+)("[^>]*>)',
        ]

        replacements = {}
        food_items_found = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE)
            for match in matches:
                groups = match.groups()

                # Extract item name and URL based on pattern
                if 'src=' in groups[0]:  # Pattern 1
                    img_url = groups[1]
                    item_name = groups[3].strip()
                else:  # Pattern 2
                    item_name = groups[1].strip()
                    img_url = groups[3]

                # Clean item name
                item_name = re.sub(r'<[^>]+>', '', item_name).strip()
                item_name = re.sub(r'[🍛🍗🐟🥤]', '', item_name).strip()  # Remove emojis

                # Check if it's Malaysian food
                is_food = any(word in item_name.lower() for word in [
                    'nasi', 'mee', 'ayam', 'ikan', 'roti', 'satay', 'rendang', 'laksa',
                    'rice', 'noodle', 'chicken', 'fish', 'bread', 'curry', 'teh', 'kopi',
                    'cendol', 'kuih', 'goreng', 'lemak', 'kandar', 'bakar'
                ])

                if is_food and 'unsplash' in img_url.lower():
                    food_items_found.append((item_name, img_url))

        if not food_items_found:
            logger.info("   ℹ️ No Malaysian food items found that need AI generation")
            return html

        logger.info(f"   🍽️ Found {len(food_items_found)} food items to generate:")
        for name, _ in food_items_found:
            logger.info(f"      - {name}")

        # Generate AI images for each food item
        for item_name, old_url in food_items_found:
            try:
                logger.info(f"   🎨 Generating AI image for: {item_name}")
                ai_url = await self.generate_food_image(item_name)

                if ai_url and 'cloudinary' in ai_url.lower():
                    replacements[old_url] = ai_url
                    logger.info(f"   ✅ Generated: {ai_url[:60]}...")
                else:
                    logger.warning(f"   ⚠️ Failed to generate image for: {item_name}")
            except Exception as e:
                logger.error(f"   ❌ Error generating image for {item_name}: {e}")

        # Apply replacements
        if replacements:
            logger.info(f"   🔄 Replacing {len(replacements)} Unsplash URLs with AI-generated images...")
            for old_url, new_url in replacements.items():
                html = html.replace(old_url, new_url)
            logger.info("   ✅ AI image generation complete!")
        else:
            logger.warning("   ⚠️ No AI images were generated")

        return html

    def _fix_placeholders(self, html: str, name: str, desc: str) -> str:
        """Fix any remaining placeholders as a safety net"""
        if not html:
            return html

        biz_type = self._detect_type(desc)
        imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])

        # Fix placeholder image URLs
        html = html.replace("via.placeholder.com/400x300", imgs["gallery"][0].replace("?w=800&q=80", "?w=400&h=300&q=80"))
        html = html.replace("via.placeholder.com/600x400", imgs["gallery"][1].replace("?w=800&q=80", "?w=600&h=400&q=80"))
        html = html.replace("via.placeholder.com/300", imgs["gallery"][2].replace("?w=800&q=80", "?w=300&q=80"))
        html = html.replace("https://via.placeholder.com", imgs["gallery"][0].split("?")[0])
        html = html.replace("placeholder.com", "images.unsplash.com")

        # Fix text placeholders
        html = html.replace("[BUSINESS_TAGLINE]", f"Selamat Datang ke {name}!")
        html = html.replace("[ABOUT_TEXT]", f"{name} adalah destinasi utama untuk semua keperluan anda. Kami menyediakan perkhidmatan berkualiti tinggi dengan harga berpatutan.")
        html = html.replace("[SERVICE_1_NAME]", "Perkhidmatan Premium")
        html = html.replace("[SERVICE_1_DESC]", "Perkhidmatan berkualiti tinggi untuk kepuasan anda.")
        html = html.replace("[SERVICE_2_NAME]", "Harga Berpatutan")
        html = html.replace("[SERVICE_2_DESC]", "Harga yang kompetitif tanpa mengorbankan kualiti.")
        html = html.replace("[SERVICE_3_NAME]", "Sokongan Pelanggan")
        html = html.replace("[SERVICE_3_DESC]", "Pasukan kami sentiasa bersedia membantu anda.")
        html = html.replace("[CONTACT_TEXT]", "Hubungi kami untuk sebarang pertanyaan. Kami sentiasa bersedia membantu!")

        return html

    async def generate_website(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """Generate website with Stability AI + Cloudinary + DeepSeek + Qwen"""

        logger.info("=" * 80)
        logger.info("🌐 WEBSITE GENERATION - FULL AI PIPELINE")
        logger.info(f"   Business: {request.business_name}")
        logger.info(f"   Style: {style or 'modern'}")
        logger.info(f"   User Images: {len(request.uploaded_images) if request.uploaded_images else 0}")
        logger.info("=" * 80)

        # Check if user uploaded images - skip AI image generation if so
        image_urls = {}

        if request.uploaded_images and len(request.uploaded_images) > 0:
            # User uploaded images - use them directly, skip AI generation
            logger.info(f"☁️ User uploaded {len(request.uploaded_images)} images - SKIPPING AI image generation")
            logger.info("   Using user-uploaded Cloudinary URLs...")

            # Helper function to extract URL from image (can be string or dict with 'url' key)
            def get_image_url(img):
                if isinstance(img, dict):
                    return img.get('url', img.get('URL', ''))
                return str(img)

            # Helper function to extract name from image metadata
            def get_image_name(img):
                if isinstance(img, dict):
                    return img.get('name', '')
                return ''

            # Map uploaded images to expected keys
            # IMPORTANT: Only treat an uploaded image as HERO if explicitly named as hero.
            gallery_start_index = 0
            first_name = (get_image_name(request.uploaded_images[0]) or "").strip().lower()
            if first_name == "hero image" or "hero" in first_name:
                image_urls["hero"] = get_image_url(request.uploaded_images[0])
                gallery_start_index = 1

            # Gallery images start after hero (if present)
            for i in range(1, 5):
                idx = gallery_start_index + (i - 1)
                if idx < len(request.uploaded_images):
                    image_urls[f"gallery{i}"] = get_image_url(request.uploaded_images[idx])
                    image_urls[f"gallery{i}_name"] = get_image_name(request.uploaded_images[idx])

            logger.info(f"   ✅ Using {len(image_urls)} user-uploaded images with metadata")

        else:
            # No user images - generate with Stability AI
            logger.info("🎨 No user images - generating with Stability AI...")

            # STEP 0: Use AI to generate smart image prompts
            logger.info("🧠 STEP 0: AI analyzing business type and generating smart prompts...")
            smart_prompts = await self.generate_smart_image_prompts(request.description)

            hero_prompt = smart_prompts.get("hero", "")
            product_prompt_1 = smart_prompts.get("image1", "")
            product_prompt_2 = smart_prompts.get("image2", "")
            product_prompt_3 = smart_prompts.get("image3", "")
            product_prompt_4 = smart_prompts.get("image4", "")

            # STEP 1: Generate images with Stability AI
            logger.info("🎨 STEP 1: Generating images with Stability AI using smart prompts...")
            logger.info(f"   Hero prompt: {hero_prompt[:60]}...")
            logger.info(f"   Product 1: {product_prompt_1[:60]}...")

            # ===================================================================
            # PARALLEL IMAGE GENERATION - Generate ALL images at the same time
            # ===================================================================
            logger.info(f"🎨 Generating ALL images in PARALLEL (hero + 4 products)...")

            # Create tasks for parallel execution using AI-generated prompts
            image_tasks = [
                self._generate_stability_image(hero_prompt),  # Task 0: Hero
                self._generate_stability_image(product_prompt_1),  # Task 1: Product 1
                self._generate_stability_image(product_prompt_2),  # Task 2: Product 2
                self._generate_stability_image(product_prompt_3),  # Task 3: Product 3
                self._generate_stability_image(product_prompt_4),  # Task 4: Product 4
            ]

            # Run ALL tasks in parallel (much faster than sequential)
            start_time = time.time()
            results = await asyncio.gather(*image_tasks, return_exceptions=True)
            elapsed = time.time() - start_time

            # Extract results with error handling
            hero_image = results[0] if results[0] and not isinstance(results[0], Exception) else None
            product1_image = results[1] if results[1] and not isinstance(results[1], Exception) else None
            product2_image = results[2] if results[2] and not isinstance(results[2], Exception) else None
            product3_image = results[3] if results[3] and not isinstance(results[3], Exception) else None
            product4_image = results[4] if results[4] and not isinstance(results[4], Exception) else None

            # Build image_urls dict
            if hero_image:
                image_urls["hero"] = hero_image
            if product1_image:
                image_urls["gallery1"] = product1_image
            if product2_image:
                image_urls["gallery2"] = product2_image
            if product3_image:
                image_urls["gallery3"] = product3_image
            if product4_image:
                image_urls["gallery4"] = product4_image

            # Log results
            successful = sum(1 for r in results if r and not isinstance(r, Exception))
            failed = len(results) - successful
            logger.info(f"☁️ Parallel generation complete in {elapsed:.1f}s")
            logger.info(f"   ✅ Successful: {successful}/5 images")
            if failed > 0:
                logger.warning(f"   ⚠️ Failed: {failed}/5 images")
            logger.info(f"   Total URLs: {len(image_urls)} images ready for HTML generation")

        # Build prompt WITH image URLs
        logger.info("🔷 STEP 2: DeepSeek generating HTML...")
        # Get language from request (default to "ms" for Bahasa Malaysia)
        language = request.language.value if hasattr(request, 'language') and request.language else "ms"
        logger.info(f"   Language: {language}")
        prompt = self._build_strict_prompt(
            request.business_name,
            request.description,
            style or "modern",
            request.uploaded_images,
            language,
            whatsapp_number=request.whatsapp_number,
            location_address=request.location_address,
        )

        # Add image URLs to prompt with STRONG emphasis
        if image_urls:
            # Build gallery section with dish names
            gallery_items = []
            dish_names_list = []
            menu_items_structured = []

            for i in range(1, 5):
                key = f'gallery{i}'
                name_key = f'gallery{i}_name'
                if key in image_urls:
                    dish_name = image_urls.get(name_key, '')
                    if dish_name:
                        gallery_items.append(f"- Product/Gallery image {i}: {image_urls[key]} (Dish: {dish_name})")
                        dish_names_list.append(dish_name)
                        menu_items_structured.append(f"""ITEM {i}:
- Image URL: {image_urls[key]}
- Title: "{dish_name}" (COPY EXACTLY - DO NOT MODIFY)
- Generate description in Malay based on the title""")
                    else:
                        gallery_items.append(f"- Product/Gallery image {i}: {image_urls[key]}")

            # Build structured menu items section
            menu_items_section = ""
            if menu_items_structured:
                menu_items_section = f"""

MENU ITEMS - USE EXACTLY AS SPECIFIED:

{chr(10).join(menu_items_structured)}

CRITICAL RULES:
1. The HTML <h3> for each menu card MUST contain the EXACT title text specified above
2. DO NOT modify, translate, or change the title in any way
3. DO NOT add prefixes like "Nasi Kandar" if not in the original title
4. ONLY generate the description in Malay - the title stays EXACTLY as written
5. Copy-paste the title EXACTLY into your HTML <h3> tags

EXAMPLES:
❌ WRONG: Title is "Ayam Penyet" → AI writes <h3>Nasi Kandar Ayam Goreng</h3>
✅ CORRECT: Title is "Ayam Penyet" → AI writes <h3>Ayam Penyet</h3>

❌ WRONG: Title is "Mee Goreng Mamak" → AI writes <h3>Nasi Kandar Ikan Bakar</h3>
✅ CORRECT: Title is "Mee Goreng Mamak" → AI writes <h3>Mee Goreng Mamak</h3>
"""

            image_instructions = f"""
USE THESE EXACT IMAGE URLS IN THE HTML:
- Hero/Banner image: {image_urls.get('hero', 'generate appropriate image')}
{menu_items_section}

IMPORTANT INSTRUCTIONS:
1. Use these EXACT URLs in the img src attributes. Do NOT use placeholder or Unsplash URLs.
2. Use the EXACT menu item titles shown above - DO NOT modify them.
3. Write compelling descriptions in Malay for each dish, but keep the dish NAME/TITLE exactly as provided.
4. Make sure ALL menu items with images are displayed in the menu/gallery section.
"""

            prompt += image_instructions

        html = await self._call_deepseek(prompt)

        if not html:
            logger.warning("⚠️ DeepSeek failed, trying Qwen...")
            html = await self._call_qwen(prompt)

        if not html:
            logger.error("❌ Both AIs failed to generate")
            raise Exception("Failed to generate website")

        # Extract HTML
        html = self._extract_html(html)

        # Validate and retry once if the model ignored hard constraints
        if html:
            required_urls: List[str] = []
            if request.uploaded_images and len(request.uploaded_images) > 0:
                def _url(img):
                    if isinstance(img, dict):
                        return img.get("url", img.get("URL", ""))
                    return str(img) if img else ""

                def _name(img):
                    if isinstance(img, dict):
                        return img.get("name", "")
                    return ""

                gallery_start_index = 0
                first_name = (_name(request.uploaded_images[0]) or "").strip().lower()
                if first_name == "hero image" or "hero" in first_name:
                    required_urls.append(_url(request.uploaded_images[0]))
                    gallery_start_index = 1
                for i in range(4):
                    idx = gallery_start_index + i
                    if idx < len(request.uploaded_images):
                        required_urls.append(_url(request.uploaded_images[idx]))

            wa_raw = request.whatsapp_number or "60123456789"
            wa_digits = re.sub(r"\D", "", str(wa_raw))
            if wa_digits.startswith("0"):
                wa_digits = "6" + wa_digits
            elif wa_digits.startswith("1"):
                wa_digits = "60" + wa_digits
            if not wa_digits:
                wa_digits = "60123456789"

            errors = self._validate_generated_html(
                html,
                required_image_urls=[u for u in required_urls if u],
                required_wa_digits=wa_digits,
            )
            if errors:
                logger.warning("⚠️ HTML validation failed; retrying once with stricter constraints")
                retry_prompt = (
                    prompt
                    + "\n\n=== VALIDATION FAILURES (MUST FIX) ===\n"
                    + "\n".join(f"- {e}" for e in errors)
                    + "\nRegenerate the FULL HTML from scratch. Output ONLY HTML."
                )
                retry = await self._call_deepseek(retry_prompt, temperature=0.1)
                if not retry:
                    retry = await self._call_qwen(retry_prompt, temperature=0.1)
                retry_html = self._extract_html(retry) if retry else None
                if retry_html:
                    html = retry_html

        # STEP 3: Improve content with Qwen
        if html:
            logger.info("🟡 STEP 3: Qwen improving content...")
            html = await self._improve_with_qwen(html, request.description)
            # Extract HTML again to remove Qwen's explanation text
            if html:
                html = self._extract_html(html)

        # Fix any remaining issues
        html = self._fix_placeholders(html, request.business_name, request.description)
        html = self._fix_menu_item_images(html)

        # CRITICAL FIX: Generate AI images for Malaysian food items
        # This replaces Unsplash URLs with Cloudinary URLs from Stability AI.
        # Never override user-provided images.
        if not (request.uploaded_images and len(request.uploaded_images) > 0):
            html = await self._generate_ai_food_images(html)

        logger.info("✅ ALL STEPS COMPLETE")
        logger.info(f"   Final size: {len(html)} characters")

        return AIGenerationResponse(
            html_content=html,
            css_content=None,
            js_content=None,
            meta_title=request.business_name,
            meta_description=f"{request.business_name} - {request.description[:150]}",
            sections=["Header", "Hero", "About", "Services", "Gallery", "Contact", "Footer"],
            integrations_included=["WhatsApp", "Contact Form", "Mobile Responsive", "Cloudinary Images"]
        )

    async def generate_multi_style(
        self,
        request: WebsiteGenerationRequest
    ) -> Dict[str, AIGenerationResponse]:
        """Generate 3 style variations"""

        logger.info("=" * 80)
        logger.info("🎨 MULTI-STYLE GENERATION - 3 VARIATIONS")
        logger.info("=" * 80)

        results = {}

        for style, ai_pref in [("modern", "deepseek"), ("minimal", "qwen"), ("bold", "deepseek")]:
            logger.info(f"\n--- Generating {style.upper()} style ---")
            
            # Get language from request
            language = request.language.value if hasattr(request, 'language') and request.language else "ms"

            prompt = self._build_strict_prompt(
                request.business_name,
                request.description,
                style,
                request.uploaded_images,
                language,
                whatsapp_number=request.whatsapp_number,
                location_address=request.location_address,
            )

            # Try preferred AI first
            if ai_pref == "deepseek":
                html = await self._call_deepseek(prompt)
                if not html:
                    html = await self._call_qwen(prompt)
            else:
                html = await self._call_qwen(prompt)
                if not html:
                    html = await self._call_deepseek(prompt)

            if html:
                html = self._extract_html(html)

                # Validate and retry once if constraints were ignored
                if html:
                    required_urls: List[str] = []
                    if request.uploaded_images and len(request.uploaded_images) > 0:
                        def _url(img):
                            if isinstance(img, dict):
                                return img.get("url", img.get("URL", ""))
                            return str(img) if img else ""

                        def _name(img):
                            if isinstance(img, dict):
                                return img.get("name", "")
                            return ""

                        gallery_start_index = 0
                        first_name = (_name(request.uploaded_images[0]) or "").strip().lower()
                        if first_name == "hero image" or "hero" in first_name:
                            required_urls.append(_url(request.uploaded_images[0]))
                            gallery_start_index = 1
                        for i in range(4):
                            idx = gallery_start_index + i
                            if idx < len(request.uploaded_images):
                                required_urls.append(_url(request.uploaded_images[idx]))

                    wa_raw = request.whatsapp_number or "60123456789"
                    wa_digits = re.sub(r"\D", "", str(wa_raw))
                    if wa_digits.startswith("0"):
                        wa_digits = "6" + wa_digits
                    elif wa_digits.startswith("1"):
                        wa_digits = "60" + wa_digits
                    if not wa_digits:
                        wa_digits = "60123456789"

                    errors = self._validate_generated_html(
                        html,
                        required_image_urls=[u for u in required_urls if u],
                        required_wa_digits=wa_digits,
                    )
                    if errors:
                        logger.warning(f"⚠️ {style} HTML validation failed; retrying once")
                        retry_prompt = (
                            prompt
                            + "\n\n=== VALIDATION FAILURES (MUST FIX) ===\n"
                            + "\n".join(f"- {e}" for e in errors)
                            + "\nRegenerate the FULL HTML from scratch. Output ONLY HTML."
                        )
                        retry = await self._call_deepseek(retry_prompt, temperature=0.1)
                        if not retry:
                            retry = await self._call_qwen(retry_prompt, temperature=0.1)
                        retry_html = self._extract_html(retry) if retry else None
                        if retry_html:
                            html = retry_html

                html = self._fix_placeholders(html, request.business_name, request.description)
                html = self._fix_menu_item_images(html)

                # CRITICAL FIX: Generate AI images for Malaysian food items
                # This replaces Unsplash URLs with Cloudinary URLs from Stability AI
                if not (request.uploaded_images and len(request.uploaded_images) > 0):
                    html = await self._generate_ai_food_images(html)

                results[style] = AIGenerationResponse(
                    html_content=html,
                    css_content=None,
                    js_content=None,
                    meta_title=f"{request.business_name} - {style.title()}",
                    meta_description=f"{request.business_name} - {request.description[:150]}",
                    sections=["Header", "Hero", "About", "Services", "Gallery", "Contact", "Footer"],
                    integrations_included=["WhatsApp", "Contact Form", "Mobile Responsive"]
                )
                logger.info(f"✅ {style} style complete")
            else:
                logger.error(f"❌ {style} style failed")

        logger.info(f"\n✅ Generated {len(results)}/3 styles successfully")
        return results


# Create singleton instance
ai_service = AIService()
