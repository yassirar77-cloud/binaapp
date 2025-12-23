"""
AI Service - Strict No-Placeholder Mode
Ensures real images and real content - NO placeholders allowed
"""

import os
import httpx
import random
from loguru import logger
from typing import Optional, List, Dict
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse


class AIService:
    """AI Service with strict anti-placeholder enforcement"""

    def __init__(self):
        self.qwen_api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

        logger.info("=" * 80)
        logger.info("🚀 AI SERVICE - STRICT NO-PLACEHOLDER MODE")
        logger.info(f"   DeepSeek: {'✅ Ready' if self.deepseek_api_key else '❌ NOT SET'}")
        logger.info(f"   Qwen: {'✅ Ready' if self.qwen_api_key else '❌ NOT SET'}")
        logger.info("   Mode: Real images only, no placeholders allowed")
        logger.info("=" * 80)

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
