"""
Dual AI Service - Task-based AI routing
- DeepSeek: Backend logic, Bug fixing, API design, Code generation (HTML structure)
- Qwen: UI ideas, Text & copy, Chatbot, Code explanation (Content writing)
- Website: BOTH - DeepSeek for code structure, then Qwen for content improvement
"""

import os
import httpx
import asyncio
import random
from loguru import logger
from typing import Optional, List, Dict
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse


class DualAIService:
    """
    Dual AI Service - Uses the right AI for each task:
    - DeepSeek: Code, Backend, Bug fixing, API design
    - Qwen: Content, UI ideas, Text, Chatbot
    - Website: Both (DeepSeek for structure + Qwen for content)
    """

    def __init__(self):
        # API Keys
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

        self.qwen_api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")

        # Log status
        logger.info("=" * 80)
        logger.info("🤖 DUAL AI SERVICE INITIALIZED")
        logger.info(f"   DeepSeek (Code Generation): {'✅ Ready' if self.deepseek_api_key else '❌ NOT SET'}")
        logger.info(f"   Qwen (Content Writing): {'✅ Ready' if self.qwen_api_key else '❌ NOT SET'}")
        logger.info("   Architecture: DeepSeek → Structure | Qwen → Content")
        logger.info("=" * 80)

    # ==================== CORE API CALLS ====================

    async def _call_deepseek(self, prompt: str, task: str = "code") -> Optional[str]:
        """
        Call DeepSeek API - Best for:
        - Backend logic
        - Bug fixing
        - API design
        - Code generation
        - HTML/CSS structure
        """
        if not self.deepseek_api_key:
            logger.error("❌ DEEPSEEK_API_KEY not configured!")
            return None

        try:
            logger.info(f"🔷 DEEPSEEK [{task}] - Generating...")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
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

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    logger.info(f"🔷 DEEPSEEK [{task}] - ✅ Success ({len(content)} chars)")
                    return content
                else:
                    logger.error(f"🔷 DEEPSEEK [{task}] - ❌ Error {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"🔷 DEEPSEEK [{task}] - ❌ Exception: {e}")
            return None

    async def _call_qwen(self, prompt: str, task: str = "content") -> Optional[str]:
        """
        Call Qwen API - Best for:
        - UI ideas
        - Text & copy writing
        - Chatbot responses
        - Code explanation
        - Creative content
        """
        if not self.qwen_api_key:
            logger.error("❌ QWEN_API_KEY not configured!")
            return None

        try:
            logger.info(f"🟡 QWEN [{task}] - Generating...")

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.qwen_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.qwen_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-max",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.8,
                        "max_tokens": 8000
                    }
                )

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    logger.info(f"🟡 QWEN [{task}] - ✅ Success ({len(content)} chars)")
                    return content
                else:
                    logger.error(f"🟡 QWEN [{task}] - ❌ Error {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"🟡 QWEN [{task}] - ❌ Exception: {e}")
            return None

    # ==================== BUSINESS TYPE DETECTION ====================

    def _get_business_config(self, description: str) -> dict:
        """Detect business type and return config with relevant images"""
        desc = description.lower()

        configs = {
            "salon": {
                "keywords": ["salon", "rambut", "hair", "haircut", "gunting", "beauty", "spa", "kecantikan"],
                "hero": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920",
                "images": [
                    "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800",
                    "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=800",
                    "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=800",
                    "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=800"
                ],
                "colors": ["pink", "rose", "purple", "gold"],
                "vibe": "elegant",
                "components": ["ServiceList", "BookingForm", "Gallery"]
            },
            "restaurant": {
                "keywords": ["makan", "restoran", "restaurant", "food", "nasi", "cafe", "kedai makan", "warung", "kafe"],
                "hero": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920",
                "images": [
                    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
                    "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800",
                    "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800",
                    "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800"
                ],
                "colors": ["red", "orange", "amber", "brown"],
                "vibe": "warm",
                "components": ["FoodMenuGrid", "WhatsAppOrdering", "GoogleMaps"]
            },
            "pet_shop": {
                "keywords": ["kucing", "cat", "pet", "haiwan", "anjing", "dog", "kedai haiwan", "binatang"],
                "hero": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1920",
                "images": [
                    "https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=800",
                    "https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800",
                    "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=800",
                    "https://images.unsplash.com/photo-1583795128727-6ec3642408f8?w=800"
                ],
                "colors": ["orange", "amber", "yellow", "purple"],
                "vibe": "playful",
                "components": ["ProductGallery", "ServiceList", "ContactForm"]
            },
            "clothing": {
                "keywords": ["pakaian", "clothing", "fashion", "baju", "boutique", "fesyen", "tudung", "hijab"],
                "hero": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1920",
                "images": [
                    "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=800",
                    "https://images.unsplash.com/photo-1558171813-4c088753af8f?w=800",
                    "https://images.unsplash.com/photo-1467043237213-65f2da53396f?w=800",
                    "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=800"
                ],
                "colors": ["slate", "neutral", "black", "white"],
                "vibe": "minimal",
                "components": ["ProductGallery", "ContactForm", "About"]
            },
            "photography": {
                "keywords": ["photo", "photographer", "gambar", "fotografi", "wedding", "kamera"],
                "hero": "https://images.unsplash.com/photo-1452587925148-ce544e77e70d?w=1920",
                "images": [
                    "https://images.unsplash.com/photo-1511285560929-80b456fea0bc?w=800",
                    "https://images.unsplash.com/photo-1606216794074-735e91aa2c92?w=800",
                    "https://images.unsplash.com/photo-1583939003579-730e3918a45a?w=800",
                    "https://images.unsplash.com/photo-1519741497674-611481863552?w=800"
                ],
                "colors": ["slate", "zinc", "neutral", "stone"],
                "vibe": "minimal",
                "components": ["ImageGallery", "Portfolio", "ContactForm"]
            },
            "default": {
                "keywords": [],
                "hero": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920",
                "images": [
                    "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800",
                    "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800",
                    "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800",
                    "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800"
                ],
                "colors": ["blue", "indigo", "cyan", "teal"],
                "vibe": "modern",
                "components": ["Hero", "Services", "About", "Contact"]
            }
        }

        for biz_type, config in configs.items():
            if biz_type != "default" and any(kw in desc for kw in config["keywords"]):
                logger.info(f"🎯 Detected business type: {biz_type}")
                return {"type": biz_type, **config}

        logger.info("🎯 Using default business config")
        return {"type": "default", **configs["default"]}

    # ==================== WEBSITE GENERATION (DUAL AI) ====================

    async def generate_website(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """
        Generate website using DUAL AI approach:
        1. DeepSeek: Generate HTML structure and code
        2. Qwen: Improve content, text, and copy
        """

        logger.info("=" * 80)
        logger.info("🌐 WEBSITE GENERATION - DUAL AI MODE")
        logger.info(f"   Business: {request.business_name}")
        logger.info(f"   Style: {style or 'default'}")
        logger.info(f"   User Images: {len(request.uploaded_images) if request.uploaded_images else 0}")
        logger.info("=" * 80)

        # Get business config
        config = self._get_business_config(request.description)

        # Prepare images (prioritize user uploads)
        if request.uploaded_images and len(request.uploaded_images) > 0:
            logger.info(f"🖼️  Using {len(request.uploaded_images)} user-uploaded images")
            hero_image = request.uploaded_images[0]
            gallery_images = request.uploaded_images[1:5] if len(request.uploaded_images) > 1 else request.uploaded_images + config["images"][:4]
        else:
            hero_image = config["hero"]
            gallery_images = config["images"]

        color = random.choice(config["colors"])

        # ==================== STEP 1: DeepSeek generates HTML structure ====================
        logger.info("🔷 STEP 1/2: DeepSeek generating HTML structure...")

        structure_prompt = f"""You are an expert web developer. Generate a complete, production-ready HTML website.

BUSINESS: {request.business_name}
TYPE: {config['type']}
DESCRIPTION: {request.description}
STYLE: {style or 'modern'}
COLOR THEME: {color}
VIBE: {config['vibe']}

USE THESE EXACT IMAGES:
- Hero Banner: {hero_image}
- Gallery Image 1: {gallery_images[0]}
- Gallery Image 2: {gallery_images[1]}
- Gallery Image 3: {gallery_images[2]}
- Gallery Image 4: {gallery_images[3] if len(gallery_images) > 3 else gallery_images[0]}

REQUIRED COMPONENTS:
{chr(10).join([f"- {comp}" for comp in config['components']])}

TECHNICAL REQUIREMENTS:
1. Single HTML file with Tailwind CSS CDN
2. Mobile responsive (critical!)
3. Sections: Header, Hero, About, Services/Gallery, Contact, Footer
4. WhatsApp floating button (use: {request.whatsapp_number or '+60123456789'})
5. Use the EXACT image URLs provided above
6. Clean, well-structured semantic HTML5
7. {style or 'modern'} design aesthetic with {color} color scheme
8. Smooth animations and hover effects

For text content, use placeholders like:
- [BUSINESS_TAGLINE] - catchy one-liner
- [ABOUT_TEXT] - 2-3 sentences about business
- [SERVICE_1_NAME], [SERVICE_1_DESC] - service details
- [SERVICE_2_NAME], [SERVICE_2_DESC]
- [SERVICE_3_NAME], [SERVICE_3_DESC]
- [CONTACT_TEXT] - welcoming message

Generate ONLY the complete HTML code, no explanations or markdown."""

        html_structure = await self._call_deepseek(structure_prompt, "html_structure")

        if not html_structure:
            logger.warning("⚠️ DeepSeek failed, trying Qwen for structure...")
            html_structure = await self._call_qwen(structure_prompt, "html_structure_fallback")

        if not html_structure:
            logger.error("❌ Both AIs failed to generate structure")
            raise Exception("Failed to generate website structure")

        # Extract HTML
        html_structure = self._extract_html(html_structure)

        # ==================== STEP 2: Qwen improves content ====================
        logger.info("🟡 STEP 2/2: Qwen improving content and copy...")

        # Detect language
        is_malay = any(w in request.description.lower() for w in ["saya", "kami", "yang", "untuk", "adalah", "dengan"])
        language = "Bahasa Malaysia" if is_malay else "English"

        content_prompt = f"""You are a professional copywriter for {language} businesses.

I have a website HTML that needs better content. Replace all placeholder text with compelling, professional copy.

BUSINESS: {request.business_name}
TYPE: {config['type']}
DESCRIPTION: {request.description}
LANGUAGE: {language}

CURRENT HTML (first 4000 chars):
{html_structure[:4000]}

TASKS:
1. Replace [BUSINESS_TAGLINE] with a catchy, memorable tagline
2. Replace [ABOUT_TEXT] with compelling about section (2-3 sentences explaining what makes this business special)
3. Replace all [SERVICE_X_NAME] and [SERVICE_X_DESC] with real, specific service names and descriptions based on business type
4. Replace [CONTACT_TEXT] with welcoming, friendly contact message
5. Make sure all text is in {language} and sounds professional
6. Appeal to Malaysian customers
7. Keep HTML structure exactly the same - ONLY replace placeholder text
8. Do NOT change image URLs or Tailwind classes

Return the COMPLETE improved HTML code with better content. Output ONLY HTML, no explanations."""

        improved_html = await self._call_qwen(content_prompt, "content_improvement")

        if improved_html:
            final_html = self._extract_html(improved_html)
            logger.info("✅ Dual AI generation complete!")
            logger.info(f"   Final size: {len(final_html)} characters")
        else:
            logger.warning("⚠️ Qwen content improvement failed, using original structure")
            final_html = html_structure

        return AIGenerationResponse(
            html_content=final_html,
            css_content=None,
            js_content=None,
            meta_title=request.business_name,
            meta_description=f"{request.business_name} - {request.description[:150]}",
            sections=config['components'],
            integrations_included=["WhatsApp", "Contact Form", "Mobile Responsive"]
        )

    async def generate_multi_style(
        self,
        request: WebsiteGenerationRequest
    ) -> Dict[str, AIGenerationResponse]:
        """
        Generate 3 style variations using dual AI:
        - modern: DeepSeek structure + Qwen content
        - minimal: DeepSeek structure + Qwen content
        - bold: DeepSeek structure + Qwen content
        """

        logger.info("=" * 80)
        logger.info("🎨 MULTI-STYLE GENERATION - DUAL AI MODE")
        logger.info("   Generating 3 variations: modern, minimal, bold")
        logger.info("=" * 80)

        results = {}
        styles = ["modern", "minimal", "bold"]

        for style in styles:
            logger.info(f"\n--- Generating {style.upper()} style ---")

            try:
                response = await self.generate_website(request, style)
                results[style] = response
                logger.info(f"✅ {style} style complete")
            except Exception as e:
                logger.error(f"❌ {style} style failed: {e}")

        logger.info(f"\n✅ Generated {len(results)}/3 styles successfully")
        return results

    def _extract_html(self, text: str) -> str:
        """Extract HTML from AI response"""
        if not text:
            return None

        # Remove markdown code blocks
        if "```html" in text:
            text = text.split("```html")[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]

        return text.strip()


# Create singleton instance
ai_service = DualAIService()
