from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# API Keys
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
QWEN_API_KEY = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

class GenerateRequest(BaseModel):
    business_description: str
    description: Optional[str] = None
    language: str = "ms"
    multi_style: bool = False

# ==================== STABILITY AI ====================
async def generate_image(prompt: str) -> Optional[str]:
    if not STABILITY_API_KEY:
        return None
    try:
        logger.info(f"🎨 Generating: {prompt[:40]}...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "text_prompts": [
                        {"text": f"{prompt}, professional photography, high quality, realistic", "weight": 1},
                        {"text": "blurry, bad quality, cartoon, illustration, anime", "weight": -1}
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
                logger.info("🎨 ✅ Image generated")
                return f"data:image/png;base64,{data['artifacts'][0]['base64']}"
            logger.error(f"🎨 ❌ Failed: {response.status_code}")
    except Exception as e:
        logger.error(f"🎨 ❌ Error: {e}")
    return None

def get_image_prompts(description: str) -> Dict:
    d = description.lower()

    if "teddy" in d or "bear" in d or "plush" in d:
        return {
            "hero": "Cute teddy bear shop with soft plush toys on wooden shelves, warm lighting",
            "gallery": ["Adorable brown teddy bear plush toy", "Colorful teddy bears collection", "Giant pink teddy bear", "Small cute teddy bears with ribbons"]
        }
    if "ikan" in d or "fish" in d or "seafood" in d:
        return {
            "hero": "Fresh fish market with seafood on crushed ice display",
            "gallery": ["Fresh red snapper on ice", "Fresh prawns and shrimp", "Fresh salmon fillets", "Variety of tropical fish"]
        }
    if "salon" in d or "rambut" in d or "hair" in d or "beauty" in d:
        return {
            "hero": "Modern luxury hair salon interior with styling chairs and mirrors",
            "gallery": ["Hairstylist cutting hair", "Hair coloring treatment", "Hair washing station", "Hair styling products"]
        }
    if "makan" in d or "restoran" in d or "food" in d or "nasi" in d:
        return {
            "hero": "Modern Malaysian restaurant interior with warm lighting",
            "gallery": ["Delicious nasi lemak", "Chef cooking in kitchen", "Restaurant table setting", "Malaysian cuisine dishes"]
        }
    if "kucing" in d or "cat" in d or "pet" in d:
        return {
            "hero": "Modern pet shop with cute cats",
            "gallery": ["Adorable orange tabby cat", "Cat food and supplies", "Playful kittens", "Cat grooming service"]
        }
    if "bakery" in d or "roti" in d or "kek" in d or "cake" in d:
        return {
            "hero": "Artisan bakery with fresh bread and pastries",
            "gallery": ["Fresh baked bread", "Decorated birthday cakes", "Croissants and pastries", "Baker preparing dough"]
        }
    if "kereta" in d or "car" in d or "bengkel" in d or "workshop" in d:
        return {
            "hero": "Modern car workshop garage",
            "gallery": ["Mechanic working on engine", "Car tire service", "Auto repair shop", "Service center"]
        }
    return {
        "hero": f"{description} professional business",
        "gallery": [f"{description} products", f"{description} service", f"Customer at {description}", f"{description} interior"]
    }

async def generate_business_images(description: str) -> Optional[Dict]:
    if not STABILITY_API_KEY:
        return None
    prompts = get_image_prompts(description)
    logger.info("🎨 GENERATING CUSTOM IMAGES...")

    hero = await generate_image(prompts["hero"])
    if not hero:
        return None

    gallery = []
    for i, prompt in enumerate(prompts["gallery"]):
        logger.info(f"🎨 Gallery {i+1}/4...")
        img = await generate_image(prompt)
        if img:
            gallery.append(img)
        await asyncio.sleep(0.3)

    if len(gallery) < 3:
        return None

    logger.info(f"🎨 ✅ Generated {len(gallery) + 1} images")
    return {"hero": hero, "gallery": gallery}

# ==================== FALLBACK IMAGES ====================
def get_fallback_images(description: str) -> Dict:
    d = description.lower()

    if "teddy" in d or "bear" in d:
        return {"hero": "https://images.unsplash.com/photo-1558679908-541bcf1249ff?w=1920&q=80", "gallery": ["https://images.unsplash.com/photo-1562040506-a9b32cb51b94?w=800&q=80", "https://images.unsplash.com/photo-1559454403-b8fb88521f11?w=800&q=80", "https://images.unsplash.com/photo-1530325553241-4f6e7690cf36?w=800&q=80", "https://images.unsplash.com/photo-1566669437687-7040a6926753?w=800&q=80"]}
    if "salon" in d or "hair" in d or "rambut" in d:
        return {"hero": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920&q=80", "gallery": ["https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&q=80", "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=800&q=80", "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=800&q=80", "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=800&q=80"]}
    if "ikan" in d or "fish" in d:
        return {"hero": "https://images.unsplash.com/photo-1534043464124-3be32fe000c9?w=1920&q=80", "gallery": ["https://images.unsplash.com/photo-1510130387422-82bed34b37e9?w=800&q=80", "https://images.unsplash.com/photo-1498654200943-1088dd4438ae?w=800&q=80", "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=800&q=80", "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&q=80"]}
    return {"hero": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920&q=80", "gallery": ["https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80", "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&q=80", "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800&q=80", "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&q=80"]}

# ==================== AI CALLS ====================
async def call_deepseek(prompt: str) -> Optional[str]:
    if not DEEPSEEK_API_KEY:
        return None
    try:
        logger.info("🔷 Calling DeepSeek...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You generate production-ready HTML only. Follow constraints exactly. Do not invent facts. Output ONLY HTML.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 8000,
                    "temperature": 0.2,
                },
            )
            if response.status_code == 200:
                logger.info("🔷 ✅ DeepSeek success")
                return response.json()["choices"][0]["message"]["content"]
            logger.error(f"🔷 ❌ Failed: {response.status_code}")
    except Exception as e:
        logger.error(f"🔷 ❌ Error: {e}")
    return None

async def call_qwen(prompt: str) -> Optional[str]:
    if not QWEN_API_KEY:
        return None
    try:
        logger.info("🟡 Calling Qwen...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "qwen-max",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You generate production-ready HTML only. Follow constraints exactly. Do not invent facts. Output ONLY HTML.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 8000,
                    "temperature": 0.2,
                },
            )
            if response.status_code == 200:
                logger.info("🟡 ✅ Qwen success")
                return response.json()["choices"][0]["message"]["content"]
            logger.error(f"🟡 ❌ Failed: {response.status_code}")
    except Exception as e:
        logger.error(f"🟡 ❌ Error: {e}")
    return None

def extract_html(text: str) -> str:
    if not text:
        return ""
    if "```html" in text:
        return text.split("```html")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()

# ==================== MAIN ENDPOINT ====================
@router.post("/api/generate-simple")
async def generate_simple(request: GenerateRequest):
    desc = request.business_description or request.description or ""

    if not desc:
        return JSONResponse(status_code=400, content={"success": False, "error": "Description required"})

    logger.info("")
    logger.info("=" * 60)
    logger.info("🚀 GENERATE-SIMPLE ENDPOINT")
    logger.info(f"   Description: {desc[:50]}...")
    logger.info(f"   🔑 DeepSeek: {'✅' if DEEPSEEK_API_KEY else '❌'}")
    logger.info(f"   🔑 Qwen: {'✅' if QWEN_API_KEY else '❌'}")
    logger.info(f"   🔑 Stability: {'✅' if STABILITY_API_KEY else '❌'}")
    logger.info("=" * 60)

    try:
        # Step 1: Images
        images = get_fallback_images(desc)
        if STABILITY_API_KEY:
            logger.info("🎨 Step 1: Generating custom images...")
            custom = await generate_business_images(desc)
            if custom:
                images = custom
                logger.info("🎨 ✅ Using AI images")
            else:
                logger.info("🎨 ⚠️ Using fallback images")

        # Step 2: HTML
        logger.info("🔷 Step 2: Generating HTML...")
        is_malay = any(w in desc.lower() for w in ['saya', 'kami', 'kedai', 'jual'])

        prompt = f"""Create a complete HTML website for: {desc}

USE THESE EXACT IMAGE URLs:
- Hero: {images['hero']}
- Gallery 1: {images['gallery'][0]}
- Gallery 2: {images['gallery'][1]}
- Gallery 3: {images['gallery'][2]}
- Gallery 4: {images['gallery'][3] if len(images['gallery']) > 3 else images['gallery'][2]}

REQUIREMENTS:
1. Single HTML with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive
3. Modern design with gradients
4. Sections: Header, Hero, About, Services (3 cards), Gallery (4 images), Contact, Footer
5. WhatsApp floating button (60123456789)
6. {'Bahasa Malaysia' if is_malay else 'English'} content
7. Use EXACT image URLs above

Output ONLY the HTML code."""

        html = await call_deepseek(prompt)
        if not html:
            html = await call_qwen(prompt)

        if not html:
            return JSONResponse(status_code=500, content={"success": False, "error": "AI generation failed"})

        html = extract_html(html)

        # Validate that the model actually used the required image URLs; retry once if not.
        required_urls = [
            images.get("hero"),
            images.get("gallery", [None])[0],
            images.get("gallery", [None, None])[1],
            images.get("gallery", [None, None, None])[2],
            (images.get("gallery", [None, None, None, None])[3] if len(images.get("gallery", [])) > 3 else None),
        ]
        missing = [u for u in required_urls if u and u not in html]
        forbidden = any(x in html.lower() for x in ["via.placeholder.com", "placeholder.com", "example.com", "["])
        if missing or forbidden:
            issues = []
            for u in missing[:10]:
                issues.append(f"Missing required image URL: {u}")
            if forbidden:
                issues.append("Contains forbidden placeholder patterns (placeholder/example/brackets)")
            retry_prompt = (
                prompt
                + "\n\n=== VALIDATION FAILURES (MUST FIX) ===\n"
                + "\n".join(f"- {i}" for i in issues)
                + "\nRegenerate the FULL HTML from scratch. Output ONLY HTML."
            )
            retry = await call_deepseek(retry_prompt) or await call_qwen(retry_prompt)
            if retry:
                html = extract_html(retry)

        logger.info("✅ WEBSITE GENERATED")
        logger.info(f"📄 HTML: {len(html)} chars")

        return {"success": True, "html": html, "styles": [{"style": "modern", "html": html}]}

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@router.get("/api/generate-simple/health")
async def health():
    return {"status": "ok", "deepseek": bool(DEEPSEEK_API_KEY), "qwen": bool(QWEN_API_KEY), "stability": bool(STABILITY_API_KEY)}
