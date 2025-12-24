from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from dotenv import load_dotenv
import os
import httpx
import asyncio
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BinaApp API", version="2.0.0")

# CORS - Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        import base64
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": f"{prompt}, professional photography, high quality, realistic",
                    "negative_prompt": "blurry, cartoon, anime, drawing, low quality",
                    "output_format": "png",
                    "aspect_ratio": "16:9"
                }
            )
            if response.status_code == 200:
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                logger.info("🎨 ✅ Image generated")
                return f"data:image/png;base64,{image_base64}"
            else:
                logger.error(f"🎨 ❌ Failed: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        logger.error(f"🎨 ❌ Error: {e}")
    return None

def get_image_prompts(desc: str) -> Dict:
    d = desc.lower()
    if "teddy" in d or "bear" in d: return {"hero": "Cute teddy bear shop with plush toys", "gallery": ["Brown teddy bear", "Colorful teddy bears", "Giant pink teddy", "Small teddy bears"]}
    if "salon" in d or "hair" in d or "rambut" in d: return {"hero": "Modern luxury hair salon interior", "gallery": ["Hairstylist cutting hair", "Hair coloring", "Hair washing", "Hair products"]}
    if "ikan" in d or "fish" in d: return {"hero": "Fresh fish market with seafood on ice", "gallery": ["Fresh fish on ice", "Prawns and shrimp", "Salmon fillets", "Tropical fish"]}
    if "makan" in d or "restoran" in d or "food" in d: return {"hero": "Modern restaurant interior", "gallery": ["Nasi lemak", "Chef cooking", "Table setting", "Malaysian dishes"]}
    if "kucing" in d or "cat" in d or "pet" in d: return {"hero": "Pet shop with cute cats", "gallery": ["Orange tabby cat", "Cat food", "Playful kittens", "Cat grooming"]}
    return {"hero": f"{desc} business", "gallery": [f"{desc} products", f"{desc} service", f"{desc} customer", f"{desc} interior"]}

async def generate_all_images(desc: str) -> Optional[Dict]:
    if not STABILITY_API_KEY:
        return None
    prompts = get_image_prompts(desc)
    hero = await generate_image(prompts["hero"])
    if not hero:
        return None
    gallery = []
    for p in prompts["gallery"]:
        img = await generate_image(p)
        if img: gallery.append(img)
        await asyncio.sleep(0.3)
    if len(gallery) < 3:
        return None
    return {"hero": hero, "gallery": gallery}

def get_stock_images(desc: str) -> Dict:
    d = desc.lower()
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
            r = await client.post("https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 8000})
            if r.status_code == 200:
                logger.info("🔷 ✅ Success")
                return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"🔷 Error: {e}")
    return None

async def call_qwen(prompt: str) -> Optional[str]:
    if not QWEN_API_KEY:
        logger.info("🟡 No Qwen API key")
        return None
    try:
        logger.info("🟡 Calling Qwen...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-plus",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8000,
                    "temperature": 0.7
                }
            )
            logger.info(f"🟡 Qwen response: {r.status_code}")
            if r.status_code == 200:
                logger.info("🟡 ✅ Qwen Success")
                return r.json()["choices"][0]["message"]["content"]
            else:
                logger.error(f"🟡 ❌ Qwen Failed: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        logger.error(f"🟡 ❌ Qwen Error: {e}")
    return None

def extract_html(text: str) -> str:
    if "```html" in text: return text.split("```html")[1].split("```")[0].strip()
    if "```" in text: return text.split("```")[1].split("```")[0].strip()
    return text.strip()

# ==================== ENDPOINTS ====================
@app.get("/")
async def root():
    return {"status": "running", "service": "BinaApp API", "version": "2.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "BinaApp API", "version": "2.0.0", "environment": "production"}

@app.get("/api/keys")
async def check_keys():
    return {"deepseek": bool(DEEPSEEK_API_KEY), "qwen": bool(QWEN_API_KEY), "stability": bool(STABILITY_API_KEY)}

@app.get("/api/test-ai")
async def test_ai():
    """Test both AI APIs"""
    results = {"deepseek": False, "qwen": False, "stability": False}

    # Test DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 10}
                )
                results["deepseek"] = r.status_code == 200
        except:
            pass

    # Test Qwen
    if QWEN_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                    headers={"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"},
                    json={"model": "qwen-plus", "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 10}
                )
                results["qwen"] = r.status_code == 200
        except:
            pass

    # Test Stability
    if STABILITY_API_KEY:
        results["stability"] = True  # Just check key exists

    return {
        "keys": {"deepseek": bool(DEEPSEEK_API_KEY), "qwen": bool(QWEN_API_KEY), "stability": bool(STABILITY_API_KEY)},
        "working": results
    }

@app.post("/api/generate-simple")
async def generate_simple(request: GenerateRequest):
    desc = request.business_description or request.description or ""
    if not desc:
        return JSONResponse(status_code=400, content={"success": False, "error": "Description required"})

    logger.info("=" * 60)
    logger.info("🚀 /api/generate-simple CALLED")
    logger.info(f"   Desc: {desc[:50]}...")
    logger.info("=" * 60)

    try:
        # Step 1: Try to generate AI images, but use stock URLs for the prompt
        stock_images = get_stock_images(desc)
        ai_images = None

        if STABILITY_API_KEY:
            logger.info("🎨 Generating AI images...")
            ai_images = await generate_all_images(desc)
            if ai_images:
                logger.info("🎨 ✅ AI images ready")
            else:
                logger.info("🎨 ⚠️ Using stock images")

        # Step 2: Generate HTML using STOCK image URLs (not base64)
        # This keeps the prompt small for the AI
        prompt = f"""Create HTML website for: {desc}

IMAGES (use these URLs):
- Hero: {stock_images['hero']}
- Gallery 1: {stock_images['gallery'][0]}
- Gallery 2: {stock_images['gallery'][1]}
- Gallery 3: {stock_images['gallery'][2]}
- Gallery 4: {stock_images['gallery'][3] if len(stock_images['gallery']) > 3 else stock_images['gallery'][0]}

Requirements:
1. Single HTML with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive, modern design with gradients
3. Sections: Header, Hero (full-width image), About, Services (3 cards), Gallery (4 images grid), Contact, Footer
4. WhatsApp floating button linking to wa.me/60123456789
5. Smooth hover effects and shadows

Output ONLY the complete HTML code."""

        logger.info("🔷 Calling DeepSeek...")
        html = await call_deepseek(prompt)

        if not html:
            logger.info("🟡 DeepSeek failed, trying Qwen...")
            html = await call_qwen(prompt)

        if not html:
            return JSONResponse(status_code=500, content={"success": False, "error": "AI generation failed"})

        html = extract_html(html)

        # Step 3: Replace stock images with AI images if available
        if ai_images:
            logger.info("🔄 Replacing stock images with AI images...")
            html = html.replace(stock_images['hero'], ai_images['hero'])
            for i, stock_url in enumerate(stock_images['gallery']):
                if i < len(ai_images['gallery']):
                    html = html.replace(stock_url, ai_images['gallery'][i])

        logger.info(f"✅ Generated {len(html)} chars")
        return {"success": True, "html": html, "styles": [{"style": "modern", "html": html}]}

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

# Keep existing routers if they exist
try:
    from app.api.simple.generate import router as simple_router
    app.include_router(simple_router)
except: pass

try:
    from app.api.generate import router as gen_router
    app.include_router(gen_router)
except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
