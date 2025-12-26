"""
AI Service - Strict No-Placeholder Mode
Ensures real images and real content - NO placeholders allowed
"""

import os
import httpx
import random
from loguru import logger
from typing import Optional, List, Dict, Tuple
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse
from difflib import SequenceMatcher


class AIService:
    """AI Service with strict anti-placeholder enforcement"""

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

    def get_fallback_images(self, description: str) -> Dict:
        """Get fallback stock images"""
        d = description.lower()

        if "teddy" in d or "bear" in d:
            return {
                "hero": "https://images.unsplash.com/photo-1558679908-541bcf1249ff?w=1920&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1562040506-a9b32cb51b94?w=800&q=80",
                    "https://images.unsplash.com/photo-1559454403-b8fb88521f11?w=800&q=80",
                    "https://images.unsplash.com/photo-1530325553241-4f6e7690cf36?w=800&q=80",
                    "https://images.unsplash.com/photo-1566669437687-7040a6926753?w=800&q=80"
                ]
            }

        if "ikan" in d or "fish" in d:
            return {
                "hero": "https://images.unsplash.com/photo-1534043464124-3be32fe000c9?w=1920&q=80",
                "gallery": [
                    "https://images.unsplash.com/photo-1510130387422-82bed34b37e9?w=800&q=80",
                    "https://images.unsplash.com/photo-1498654200943-1088dd4438ae?w=800&q=80",
                    "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=800&q=80",
                    "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&q=80"
                ]
            }

        # Use existing IMAGES dict for other types
        biz_type = self._detect_type(description)
        return self.IMAGES.get(biz_type, self.IMAGES["default"])

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

    def _build_strict_prompt(self, name: str, desc: str, style: str, user_images: list = None) -> str:
        """Build STRICT prompt that forbids placeholders"""
        biz_type = self._detect_type(desc)
        imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])

        # Use user images if provided, otherwise use curated Unsplash
        hero = user_images[0] if user_images and len(user_images) > 0 else imgs["hero"]
        g1 = user_images[1] if user_images and len(user_images) > 1 else imgs["gallery"][0]
        g2 = user_images[2] if user_images and len(user_images) > 2 else imgs["gallery"][1]
        g3 = user_images[3] if user_images and len(user_images) > 3 else imgs["gallery"][2]
        g4 = user_images[4] if user_images and len(user_images) > 4 else imgs["gallery"][3]

        return f"""Generate a COMPLETE production-ready HTML website.

BUSINESS: {name}
DESCRIPTION: {desc}
STYLE: {style}
TYPE: {biz_type}

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
   ✅ WhatsApp button linking to: https://wa.me/60123456789

4. TECHNICAL REQUIREMENTS:
   - Single complete HTML file
   - Tailwind CSS CDN: <script src="https://cdn.tailwindcss.com"></script>
   - Mobile responsive (critical!)
   - Sections: Header with Navigation, Hero, About, Services/Gallery, Contact, Footer
   - Smooth animations and hover effects
   - Professional {style} design

5. LANGUAGE:
   - Use Bahasa Malaysia if description contains Malay words (saya, kami, untuk, etc.)
   - Otherwise use English
   - Keep consistent throughout

6. IMAGE REQUIREMENTS:
   - Use ONLY the exact URLs provided above
   - Do NOT modify the URLs
   - Do NOT use any other image sources

Generate ONLY the complete HTML code. No explanations. No markdown. Just pure HTML."""

    async def _call_deepseek(self, prompt: str) -> Optional[str]:
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
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 8000
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

    async def _call_qwen(self, prompt: str) -> Optional[str]:
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
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 8000
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
        """Extract HTML from response"""
        if not text:
            return None
        if "```html" in text:
            text = text.split("```html")[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
        return text.strip()

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
        """Generate website with strict anti-placeholder enforcement"""

        logger.info("=" * 80)
        logger.info("🌐 WEBSITE GENERATION - NO PLACEHOLDER MODE")
        logger.info(f"   Business: {request.business_name}")
        logger.info(f"   Style: {style or 'modern'}")
        logger.info(f"   User Images: {len(request.uploaded_images) if request.uploaded_images else 0}")
        logger.info("=" * 80)

        prompt = self._build_strict_prompt(
            request.business_name,
            request.description,
            style or "modern",
            request.uploaded_images
        )

        # Try DeepSeek first (better at code)
        html = await self._call_deepseek(prompt)
        if not html:
            logger.warning("⚠️ DeepSeek failed, trying Qwen...")
            html = await self._call_qwen(prompt)

        if not html:
            logger.error("❌ Both AIs failed to generate")
            raise Exception("Failed to generate website")

        # Extract and fix
        html = self._extract_html(html)
        html = self._fix_placeholders(html, request.business_name, request.description)

        logger.info("✅ Website generated successfully!")
        logger.info(f"   Final size: {len(html)} characters")

        return AIGenerationResponse(
            html_content=html,
            css_content=None,
            js_content=None,
            meta_title=request.business_name,
            meta_description=f"{request.business_name} - {request.description[:150]}",
            sections=["Header", "Hero", "About", "Services", "Gallery", "Contact", "Footer"],
            integrations_included=["WhatsApp", "Contact Form", "Mobile Responsive"]
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

            prompt = self._build_strict_prompt(
                request.business_name,
                request.description,
                style,
                request.uploaded_images
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
                html = self._fix_placeholders(html, request.business_name, request.description)

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
