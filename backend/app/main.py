from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import logging
import base64
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BinaApp Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys from environment
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

# Request models
class GenerateRequest(BaseModel):
    description: Optional[str] = None
    business_description: Optional[str] = None
    style: Optional[str] = "modern"


@app.get("/")
async def root():
    return {"status": "BinaApp Backend Running", "version": "3.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/keys")
async def check_keys():
    return {
        "deepseek": bool(DEEPSEEK_API_KEY),
        "qwen": bool(QWEN_API_KEY),
        "stability": bool(STABILITY_API_KEY)
    }


def detect_business_type(desc: str) -> str:
    """Detect business type from description"""
    desc_lower = desc.lower()

    if any(word in desc_lower for word in ['salon', 'hair', 'beauty', 'spa', 'nail', 'makeup']):
        return 'beauty_salon'
    elif any(word in desc_lower for word in ['restaurant', 'cafe', 'food', 'makan', 'nasi', 'kedai makan', 'catering']):
        return 'restaurant'
    elif any(word in desc_lower for word in ['pet', 'kucing', 'cat', 'dog', 'anjing', 'haiwan', 'veterinar']):
        return 'pet_shop'
    elif any(word in desc_lower for word in ['gym', 'fitness', 'workout', 'exercise']):
        return 'fitness'
    elif any(word in desc_lower for word in ['clinic', 'doctor', 'medical', 'klinik', 'dentist']):
        return 'clinic'
    elif any(word in desc_lower for word in ['shop', 'store', 'kedai', 'boutique', 'retail']):
        return 'retail'
    elif any(word in desc_lower for word in ['hotel', 'homestay', 'resort', 'accommodation']):
        return 'hospitality'
    else:
        return 'general_business'


def get_stock_images(desc: str) -> dict:
    """Get relevant stock images from Unsplash based on business type"""
    business_type = detect_business_type(desc)

    image_keywords = {
        'beauty_salon': 'hair+salon+interior',
        'restaurant': 'restaurant+interior+food',
        'pet_shop': 'pet+shop+animals',
        'fitness': 'gym+fitness+workout',
        'clinic': 'medical+clinic+healthcare',
        'retail': 'retail+shop+store',
        'hospitality': 'hotel+lobby+resort',
        'general_business': 'modern+office+business'
    }

    keyword = image_keywords.get(business_type, 'business+office')

    return {
        'hero': f'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=1200&h=600&fit=crop&q=80',
        'gallery': [
            f'https://source.unsplash.com/600x400/?{keyword},1',
            f'https://source.unsplash.com/600x400/?{keyword},2',
            f'https://source.unsplash.com/600x400/?{keyword},3',
            f'https://source.unsplash.com/600x400/?{keyword},4'
        ]
    }


async def generate_stability_image(prompt: str) -> Optional[str]:
    """STEP 1: Generate image using Stability AI v2beta API"""
    if not STABILITY_API_KEY:
        logger.info("🎨 STABILITY - No API key configured")
        return None

    try:
        logger.info(f"🎨 STABILITY - Generating: {prompt[:50]}...")

        async with httpx.AsyncClient(timeout=90.0) as client:
            # Using v2beta stable-image/generate/core endpoint
            response = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": f"{prompt}, professional photography, high quality, realistic, commercial",
                    "negative_prompt": "blurry, low quality, cartoon, anime, drawing, sketch, amateur",
                    "output_format": "png",
                    "aspect_ratio": "16:9"
                }
            )

            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                logger.info("🎨 STABILITY - ✅ Image generated successfully")
                return f"data:image/png;base64,{image_base64}"
            else:
                logger.error(f"🎨 STABILITY - ❌ Failed: {response.status_code} - {response.text[:100]}")
                return None

    except Exception as e:
        logger.error(f"🎨 STABILITY - ❌ Error: {e}")
        return None


async def generate_all_images(desc: str) -> Optional[dict]:
    """Generate hero and gallery images"""
    business_type = detect_business_type(desc)

    hero_prompt = f"Modern {business_type.replace('_', ' ')} interior, professional, luxurious, {desc}"
    hero_image = await generate_stability_image(hero_prompt)

    if hero_image:
        return {
            'hero': hero_image,
            'gallery': [hero_image, hero_image, hero_image, hero_image]  # Reuse for now
        }
    return None


async def call_deepseek(prompt: str) -> Optional[str]:
    """STEP 2: Call DeepSeek V3 API for HTML structure"""
    if not DEEPSEEK_API_KEY:
        logger.info("🔷 DEEPSEEK - No API key configured")
        return None

    try:
        logger.info("🔷 DEEPSEEK [html_structure] - Calling API...")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "You are an expert web developer. Output only valid HTML code, no explanations."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 8000,
                    "temperature": 0.7
                }
            )

            logger.info(f"🔷 DEEPSEEK - Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"🔷 DEEPSEEK [html_structure] - ✅ Success ({len(content)} chars)")
                return content
            else:
                logger.error(f"🔷 DEEPSEEK - ❌ Failed: {response.status_code} - {response.text[:200]}")
                return None

    except Exception as e:
        logger.error(f"🔷 DEEPSEEK - ❌ Error: {e}")
        return None


async def call_qwen(prompt: str) -> Optional[str]:
    """STEP 3: Call Qwen API for content improvement"""
    if not QWEN_API_KEY:
        logger.info("🟡 QWEN - No API key configured")
        return None

    try:
        logger.info("🟡 QWEN [content_improvement] - Calling API...")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-plus",  # Use qwen-plus for international
                    "messages": [
                        {"role": "system", "content": "You are a Malaysian copywriter expert. Output only valid HTML code with improved content, no explanations."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 8000,
                    "temperature": 0.7
                }
            )

            logger.info(f"🟡 QWEN - Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"🟡 QWEN [content_improvement] - ✅ Success ({len(content)} chars)")
                return content
            else:
                logger.error(f"🟡 QWEN - ❌ Failed: {response.status_code} - {response.text[:200]}")
                return None

    except Exception as e:
        logger.error(f"🟡 QWEN - ❌ Error: {e}")
        return None


def extract_html(text: str) -> str:
    """Extract HTML from AI response"""
    if not text:
        return ""

    # Try to find HTML in code blocks
    patterns = [
        r'```html\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'<!DOCTYPE[\s\S]*</html>',
        r'<html[\s\S]*</html>'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            html = match.group(1) if '```' in pattern else match.group(0)
            return html.strip()

    # If no pattern matches, return original if it looks like HTML
    if '<' in text and '>' in text:
        return text.strip()

    return text


@app.post("/api/generate-simple")
async def generate_simple(request: GenerateRequest):
    """3-Step AI Pipeline: Stability AI → DeepSeek → Qwen"""

    desc = request.business_description or request.description or ""
    if not desc:
        return JSONResponse(status_code=400, content={"success": False, "error": "Description required"})

    logger.info("=" * 70)
    logger.info("🌐 WEBSITE GENERATION - 3-STEP AI PIPELINE")
    logger.info(f"   Business: {desc[:60]}...")
    logger.info("=" * 70)

    try:
        # Detect business type
        business_type = detect_business_type(desc)
        logger.info(f"📋 Detected business type: {business_type}")

        stock_images = get_stock_images(desc)

        # ============================================
        # STEP 1: STABILITY AI - Generate Images
        # ============================================
        logger.info("")
        logger.info("🎨 STEP 1: Stability AI generating images...")
        ai_images = None

        if STABILITY_API_KEY:
            ai_images = await generate_all_images(desc)
            if ai_images:
                logger.info("🎨 STABILITY [images] - ✅ Success")
            else:
                logger.info("🎨 STABILITY [images] - ⚠️ Failed, using stock images")
        else:
            logger.info("🎨 STABILITY [images] - ⚠️ No API key, using stock images")

        # Use AI images or fallback to stock
        hero_img = ai_images['hero'] if ai_images else stock_images['hero']
        gallery_imgs = ai_images['gallery'] if ai_images else stock_images['gallery']

        # ============================================
        # STEP 2: DEEPSEEK - Generate HTML Structure
        # ============================================
        logger.info("")
        logger.info("🔷 STEP 2: DeepSeek V3 generating HTML structure...")

        deepseek_prompt = f"""Create a complete HTML website structure for: {desc}

Business Type: {business_type}

Use these EXACT placeholders that will be replaced later:
- [BUSINESS_NAME] - The business name
- [BUSINESS_TAGLINE] - A catchy tagline
- [ABOUT_TEXT] - About us paragraph (2-3 sentences)
- [SERVICE_1_TITLE], [SERVICE_1_DESC] - First service
- [SERVICE_2_TITLE], [SERVICE_2_DESC] - Second service
- [SERVICE_3_TITLE], [SERVICE_3_DESC] - Third service
- [CTA_TEXT] - Call to action button text
- [FOOTER_TEXT] - Footer tagline

IMAGES (use these exact URLs):
- Hero background: {stock_images['hero']}
- Gallery 1: {stock_images['gallery'][0]}
- Gallery 2: {stock_images['gallery'][1]}
- Gallery 3: {stock_images['gallery'][2]}
- Gallery 4: {stock_images['gallery'][3] if len(stock_images['gallery']) > 3 else stock_images['gallery'][0]}

Requirements:
1. Single HTML file with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive design
3. Modern gradients and shadows
4. Sections: Header/Nav, Hero (full-width with image), About, Services (3 cards), Gallery (4 images grid), Contact form, Footer
5. WhatsApp floating button linking to wa.me/60123456789
6. Smooth hover effects and transitions
7. Professional color scheme

Output ONLY the complete HTML code with all placeholders."""

        html_structure = await call_deepseek(deepseek_prompt)

        if not html_structure:
            logger.error("🔷 DEEPSEEK - ❌ Failed to generate HTML structure")
            return JSONResponse(status_code=500, content={"success": False, "error": "DeepSeek failed to generate HTML"})

        html_structure = extract_html(html_structure)

        # ============================================
        # STEP 3: QWEN - Improve Content & Copywriting
        # ============================================
        logger.info("")
        logger.info("🟡 STEP 3: Qwen improving content and copywriting...")

        qwen_prompt = f"""You are a Malaysian copywriter. Improve this website HTML by replacing ALL placeholders with compelling, Malaysian-friendly content.

Business Description: {desc}
Business Type: {business_type}

REPLACE THESE PLACEHOLDERS with real, compelling content:
- [BUSINESS_NAME] → Extract or create business name from description
- [BUSINESS_TAGLINE] → Catchy tagline in English (Malaysian style, warm and friendly)
- [ABOUT_TEXT] → Compelling about us (2-3 sentences, friendly Malaysian tone)
- [SERVICE_1_TITLE], [SERVICE_1_DESC] → First service name and short description
- [SERVICE_2_TITLE], [SERVICE_2_DESC] → Second service name and short description
- [SERVICE_3_TITLE], [SERVICE_3_DESC] → Third service name and short description
- [CTA_TEXT] → Call to action (e.g., "Contact Us Today!", "Book Now!", "Get Started!")
- [FOOTER_TEXT] → Short footer tagline

Guidelines:
- Use Malaysian English (friendly, warm, approachable)
- Keep it professional but personable
- Make it compelling and engaging
- Suitable for local Malaysian audience
- Don't change any HTML structure, only replace the placeholder text

HTML TO IMPROVE:
{html_structure}

Output ONLY the complete improved HTML with all placeholders replaced. No explanations."""

        final_html = await call_qwen(qwen_prompt)

        if final_html:
            final_html = extract_html(final_html)
            logger.info(f"🟡 QWEN [content_improvement] - ✅ Content improved")
        else:
            logger.warning("🟡 QWEN [content_improvement] - ⚠️ Failed, using DeepSeek output")
            final_html = html_structure

        # ============================================
        # STEP 4: Replace stock images with AI images
        # ============================================
        if ai_images:
            logger.info("")
            logger.info("🔄 Replacing stock images with AI-generated images...")
            final_html = final_html.replace(stock_images['hero'], ai_images['hero'])
            for i, stock_url in enumerate(stock_images['gallery']):
                if i < len(ai_images['gallery']):
                    final_html = final_html.replace(stock_url, ai_images['gallery'][i])

        # ============================================
        # COMPLETE!
        # ============================================
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ 3-STEP AI PIPELINE COMPLETE!")
        logger.info(f"   Final HTML: {len(final_html)} chars")
        logger.info("=" * 70)

        return {
            "success": True,
            "html": final_html,
            "styles": [{"style": "modern", "html": final_html}],
            "pipeline": {
                "step1_stability": bool(ai_images),
                "step2_deepseek": True,
                "step3_qwen": final_html != html_structure
            }
        }

    except Exception as e:
        logger.error(f"❌ Pipeline Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/test-ai")
async def test_ai():
    """Test all AI APIs"""
    results = {
        "keys": {
            "deepseek": bool(DEEPSEEK_API_KEY),
            "qwen": bool(QWEN_API_KEY),
            "stability": bool(STABILITY_API_KEY)
        },
        "working": {
            "deepseek": False,
            "qwen": False,
            "stability": False
        }
    }

    # Test DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 10}
                )
                results["working"]["deepseek"] = r.status_code == 200
                results["deepseek_status"] = r.status_code
        except Exception as e:
            results["deepseek_error"] = str(e)

    # Test Qwen
    if QWEN_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "qwen-plus", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 10}
                )
                results["working"]["qwen"] = r.status_code == 200
                results["qwen_status"] = r.status_code
                if r.status_code != 200:
                    results["qwen_error"] = r.text[:200]
        except Exception as e:
            results["qwen_error"] = str(e)

    # Test Stability (just check key format)
    if STABILITY_API_KEY:
        results["working"]["stability"] = STABILITY_API_KEY.startswith("sk-")

    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
