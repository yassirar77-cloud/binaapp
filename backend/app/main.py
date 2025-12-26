from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import logging
import base64
import re
import cloudinary
import cloudinary.uploader
from datetime import datetime, timedelta, date
from collections import defaultdict
from user_agents import parse as parse_user_agent
import hashlib
from supabase import create_client, Client
from urllib.parse import urlparse
import uuid
import asyncio
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# SUPABASE INITIALIZATION - CRITICAL SECTION
# ============================================

supabase = None

def init_supabase():
    """Initialize Supabase client with multiple env var name support"""
    global supabase

    # Get URL
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")

    # Try multiple possible key names
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        ""
    )

    logger.info(f"🔧 SUPABASE_URL: {SUPABASE_URL[:50] if SUPABASE_URL else 'NOT SET'}...")
    logger.info(f"🔧 SUPABASE_KEY: {'SET (' + str(len(SUPABASE_KEY)) + ' chars)' if SUPABASE_KEY else 'NOT SET'}")

    if not SUPABASE_URL:
        logger.error("❌ SUPABASE_URL environment variable not set!")
        return None

    if not SUPABASE_KEY:
        logger.error("❌ No Supabase key found! Tried: SUPABASE_SERVICE_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_KEY, SUPABASE_ANON_KEY")
        return None

    try:
        from supabase import create_client, Client
        client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client created successfully!")

        # Test connection by making a simple query
        try:
            test = client.table("websites").select("id").limit(1).execute()
            logger.info(f"✅ Supabase connection verified! Websites table accessible.")
        except Exception as test_error:
            logger.warning(f"⚠️ Websites table test failed (might not exist yet): {test_error}")

        return client

    except Exception as e:
        logger.error(f"❌ Failed to create Supabase client: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Initialize on startup
supabase = init_supabase()

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(title="BinaApp Backend", version="4.0")

# CORS - CRITICAL: allow_credentials must be False when using wildcard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow ALL origins for mobile compatibility
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Add CORS headers manually for preflight requests and mobile browsers
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    """Add explicit CORS headers for mobile browser compatibility"""
    # Handle preflight OPTIONS request
    if request.method == "OPTIONS":
        response = JSONResponse(content={"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.on_event("startup")
async def startup_event():
    global supabase
    if supabase is None:
        logger.info("🔄 Retrying Supabase initialization on startup...")
        supabase = init_supabase()

    if supabase:
        logger.info("🚀 BinaApp API started with Supabase connected!")
    else:
        logger.error("🚀 BinaApp API started but Supabase NOT connected!")

# API Keys from environment
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    logger.info("☁️ Cloudinary configured successfully")
else:
    logger.warning("☁️ Cloudinary not configured - will use base64 fallback")

# Rate limiting
user_usage = defaultdict(lambda: {"count": 0, "reset_time": datetime.now()})
FREE_LIMIT = 3  # 3 generations per day

# Founder/Admin emails with unlimited access
UNLIMITED_ACCESS_EMAILS = [
    "yassirarafat33@yahoo.com",
    # Add more admin emails here if needed
]

# Store generation progress
generation_progress = {}


# Request models
class GenerateRequest(BaseModel):
    description: Optional[str] = None
    business_description: Optional[str] = None
    style: Optional[str] = "modern"
    user_id: Optional[str] = None
    email: Optional[str] = None


# Analytics request model
class TrackEventRequest(BaseModel):
    project_id: str
    visitor_id: Optional[str] = None
    referrer: Optional[str] = None
    page_path: Optional[str] = "/"


@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Fast health check endpoint to wake up service and verify it's running"""
    return {
        "status": "ok",
        "service": "BinaApp API",
        "version": "4.0-production",
        "healthy": True
    }


@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle preflight OPTIONS requests for all paths"""
    return JSONResponse(
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )


@app.get("/api/keys")
async def check_keys():
    return {
        "deepseek": bool(DEEPSEEK_API_KEY),
        "qwen": bool(QWEN_API_KEY),
        "stability": bool(STABILITY_API_KEY),
        "cloudinary": bool(CLOUDINARY_CLOUD_NAME)
    }


@app.get("/api/usage")
async def get_usage(user_id: str = "anonymous"):
    """Get user's current usage"""
    return check_rate_limit(user_id)


@app.get("/api/generate/progress/{session_id}")
async def get_progress(session_id: str):
    """Get generation progress"""
    progress = generation_progress.get(session_id, {
        "percent": 0,
        "step": "Waiting...",
        "steps_completed": []
    })
    return progress


def check_rate_limit(user_id: str = "anonymous", user_email: Optional[str] = None) -> dict:
    """Check if user has exceeded daily limit"""

    # Founders have unlimited access - bypass limit check
    if user_email and user_email.lower() in [e.lower() for e in UNLIMITED_ACCESS_EMAILS]:
        logger.info(f"🔓 Founder access granted: {user_email} - bypassing limit")
        return {
            "allowed": True,
            "remaining": 999,  # Unlimited
            "limit": FREE_LIMIT,
            "reset_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "is_founder": True
        }

    # Regular users have daily limit
    now = datetime.now()
    user = user_usage[user_id]

    if now - user["reset_time"] > timedelta(days=1):
        user["count"] = 0
        user["reset_time"] = now

    remaining = FREE_LIMIT - user["count"]

    return {
        "allowed": remaining > 0,
        "remaining": max(0, remaining),
        "limit": FREE_LIMIT,
        "reset_time": (user["reset_time"] + timedelta(days=1)).isoformat()
    }


def increment_usage(user_id: str = "anonymous"):
    user_usage[user_id]["count"] += 1


# ==================== ASYNC JOB MANAGEMENT (SUPABASE) ====================

async def save_job_to_supabase(job_id: str, data: dict):
    """Save job data to Supabase generation_jobs table"""
    if not supabase:
        logger.error("❌ Cannot save job - Supabase not connected")
        return

    try:
        job_data = {
            "job_id": job_id,
            "updated_at": datetime.now().isoformat(),
            **data
        }

        # Upsert (insert or update)
        supabase.table("generation_jobs").upsert(job_data, on_conflict="job_id").execute()
        logger.info(f"💾 Job {job_id[:8]} saved to Supabase")
    except Exception as e:
        logger.error(f"❌ Failed to save job {job_id[:8]}: {e}")


async def get_job_from_supabase(job_id: str) -> Optional[dict]:
    """Retrieve job data from Supabase"""
    if not supabase:
        logger.error("❌ Cannot retrieve job - Supabase not connected")
        return None

    try:
        result = supabase.table("generation_jobs").select("*").eq("job_id", job_id).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]

        return None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve job {job_id[:8]}: {e}")
        return None


async def run_website_generation(job_id: str, description: str, language: str, user_id: str):
    """Background task to generate website - runs async"""
    try:
        logger.info(f"🚀 Starting background generation for job {job_id[:8]}")

        # Update progress: 10%
        await save_job_to_supabase(job_id, {
            "status": "processing",
            "progress": 10,
            "description": description,
            "language": language,
            "user_id": user_id
        })

        # Detect business type
        business_type = detect_business_type(description)
        logger.info(f"📋 Detected: {business_type}")

        # Get stock images
        stock_images = get_stock_images(description)

        # Update progress: 20%
        await save_job_to_supabase(job_id, {
            "status": "processing",
            "progress": 20
        })

        # STEP 1: Generate AI Images (if available)
        logger.info("🎨 STEP 1: Generating images...")
        ai_images = None

        if STABILITY_API_KEY:
            ai_images = await generate_all_images(description)

        hero_img = ai_images['hero'] if ai_images else stock_images['hero']
        gallery_imgs = ai_images['gallery'] if ai_images else stock_images['gallery']

        # Update progress: 30%
        await save_job_to_supabase(job_id, {
            "status": "processing",
            "progress": 30
        })

        # Define 3 style variations
        styles_config = [
            {
                "name": "modern",
                "display_name": "Modern",
                "description": "Vibrant gradients (purple to blue), glassmorphism effects, rounded corners",
                "colors": "purple-600, blue-500, gradient backgrounds",
                "font": "bold, modern sans-serif",
                "progress_percent": 40
            },
            {
                "name": "minimal",
                "display_name": "Minimal",
                "description": "Clean white background, lots of whitespace, simple black text",
                "colors": "white, black, gray-100, one accent color",
                "font": "thin, elegant, light weight",
                "progress_percent": 65
            },
            {
                "name": "bold",
                "display_name": "Bold",
                "description": "Dark theme with black/dark gray background, large impactful typography",
                "colors": "black, dark gray, neon cyan/pink accents",
                "font": "extra bold, uppercase headings",
                "progress_percent": 90
            }
        ]

        generated_styles = []

        # STEP 2 & 3: Generate each style variation
        for style in styles_config:
            logger.info(f"🎨 Generating {style['display_name']} style...")

            # Update progress
            await save_job_to_supabase(job_id, {
                "status": "processing",
                "progress": style["progress_percent"]
            })

            gallery_urls = gallery_imgs if isinstance(gallery_imgs, list) else [gallery_imgs] * 4

            # DeepSeek generates HTML structure
            deepseek_prompt = f"""Create a stunning {style['display_name']} website for: {description}

DESIGN STYLE: {style['description']}
COLORS: {style['colors']}
TYPOGRAPHY: {style['font']}

Business Type: {business_type}

Use these placeholders:
- [BUSINESS_NAME], [BUSINESS_TAGLINE], [ABOUT_TEXT]
- [SERVICE_1_TITLE], [SERVICE_1_DESC]
- [SERVICE_2_TITLE], [SERVICE_2_DESC]
- [SERVICE_3_TITLE], [SERVICE_3_DESC]
- [CTA_TEXT], [FOOTER_TEXT]

IMAGES (use these EXACT URLs - each gallery image is DIFFERENT):
- Hero: {hero_img}
- Gallery 1: {gallery_urls[0] if len(gallery_urls) > 0 else hero_img}
- Gallery 2: {gallery_urls[1] if len(gallery_urls) > 1 else hero_img}
- Gallery 3: {gallery_urls[2] if len(gallery_urls) > 2 else hero_img}
- Gallery 4: {gallery_urls[3] if len(gallery_urls) > 3 else hero_img}

Requirements:
1. <!DOCTYPE html> with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive
3. Sections: Header, Hero, About, Services (3 cards), Gallery (4 DIFFERENT images), Contact, Footer
4. WhatsApp button: <a href="https://wa.me/60123456789">WhatsApp</a>

Output ONLY complete HTML."""

            html_structure = await call_deepseek(deepseek_prompt)

            if not html_structure:
                logger.warning(f"🔷 DeepSeek failed for {style['name']}, skipping...")
                continue

            html_structure = extract_html(html_structure)

            # Qwen improves content
            qwen_prompt = f"""Replace ALL placeholders with {'Malaysian-friendly' if language == 'ms' else 'English'} content.

Business: {description}
Style: {style['display_name']}

REPLACE:
- [BUSINESS_NAME] → Business name
- [BUSINESS_TAGLINE] → Catchy tagline
- [ABOUT_TEXT] → About us (2-3 sentences)
- [SERVICE_1_TITLE], [SERVICE_1_DESC] → Service 1
- [SERVICE_2_TITLE], [SERVICE_2_DESC] → Service 2
- [SERVICE_3_TITLE], [SERVICE_3_DESC] → Service 3
- [CTA_TEXT] → Call to action
- [FOOTER_TEXT] → Footer tagline

DO NOT change image URLs. Keep them exactly as they are.

HTML:
{html_structure}

Output ONLY improved HTML."""

            final_html = await call_qwen(qwen_prompt)

            if final_html:
                final_html = extract_html(final_html)
            else:
                final_html = html_structure

            # Add analytics script
            tracking_script = '''
<!-- BinaApp Analytics -->
<script>
(function() {
    const PROJECT_ID = 'PENDING';
    const API_URL = 'https://binaapp-backend.onrender.com/api/analytics/track';
    let visitorId = localStorage.getItem('binaapp_visitor');
    if (!visitorId) {
        visitorId = 'v_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('binaapp_visitor', visitorId);
    }
    fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: PROJECT_ID,
            visitor_id: visitorId,
            referrer: document.referrer,
            page_path: window.location.pathname
        })
    }).catch(function() {});
})();
</script>
'''
            if '</body>' in final_html:
                final_html = final_html.replace('</body>', f'{tracking_script}</body>')

            generated_styles.append({
                "style": style['name'],
                "name": style['display_name'],
                "description": style['description'],
                "html": final_html
            })

            logger.info(f"✅ {style['display_name']} style complete!")

        # Save completed job
        await save_job_to_supabase(job_id, {
            "status": "completed",
            "progress": 100,
            "html": generated_styles[0]["html"] if generated_styles else None,
            "styles": json.dumps(generated_styles)  # Store as JSON
        })

        # Increment usage
        increment_usage(user_id)

        logger.info(f"✅ Job {job_id[:8]} COMPLETE! {len(generated_styles)} styles")

    except Exception as e:
        logger.error(f"❌ Job {job_id[:8]} FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Save error to Supabase
        await save_job_to_supabase(job_id, {
            "status": "failed",
            "error": str(e)
        })


@app.post("/api/generate/start")
async def start_generation(request: Request, background_tasks: BackgroundTasks):
    """Start async website generation - returns immediately with job_id"""

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ Invalid JSON: {e}")
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid JSON"})

    description = body.get("description") or body.get("business_description") or ""
    language = body.get("language", "ms")
    user_id = body.get("user_id", "anonymous")

    if not description:
        return JSONResponse(status_code=400, content={"success": False, "error": "Description required"})

    # Check rate limit
    rate_limit = check_rate_limit(user_id)
    if not rate_limit["allowed"]:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": "Daily limit reached",
                "message": f"You've used all {FREE_LIMIT} free generations today!",
                "usage": rate_limit
            }
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    logger.info("=" * 70)
    logger.info("🌐 ASYNC GENERATION STARTED")
    logger.info(f"   Job ID: {job_id[:8]}...")
    logger.info(f"   Description: {description[:60]}...")
    logger.info("=" * 70)

    # Save initial job to Supabase
    await save_job_to_supabase(job_id, {
        "status": "processing",
        "progress": 0,
        "description": description,
        "language": language,
        "user_id": user_id
    })

    # Start background generation task
    background_tasks.add_task(run_website_generation, job_id, description, language, user_id)

    # Return immediately
    return {
        "success": True,
        "job_id": job_id,
        "status": "processing",
        "message": "Generation started. Poll /api/generate/status/{job_id} for updates."
    }


@app.get("/api/generate/status/{job_id}")
async def get_generation_status(job_id: str):
    """Check job status - called by frontend polling"""

    job = await get_job_from_supabase(job_id)

    if not job:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "status": "not_found",
                "error": "Job not found"
            }
        )

    # Parse styles JSON if completed
    styles = None
    if job.get("status") == "completed" and job.get("styles"):
        try:
            styles = json.loads(job["styles"]) if isinstance(job["styles"], str) else job["styles"]
        except:
            styles = None

    return {
        "success": True,
        "status": job["status"],
        "progress": job["progress"],
        "html": job.get("html") if job["status"] == "completed" else None,
        "styles": styles if job["status"] == "completed" else None,
        "error": job.get("error"),
        "job_id": job_id
    }


def detect_business_type(desc: str) -> str:
    desc_lower = desc.lower()

    if any(word in desc_lower for word in ['salon', 'hair', 'beauty', 'spa', 'nail', 'makeup']):
        return 'beauty_salon'
    elif any(word in desc_lower for word in ['restaurant', 'cafe', 'food', 'makan', 'nasi', 'kedai makan', 'catering']):
        return 'restaurant'
    elif any(word in desc_lower for word in ['pet', 'kucing', 'cat', 'dog', 'anjing', 'haiwan']):
        return 'pet_shop'
    elif any(word in desc_lower for word in ['gym', 'fitness', 'workout']):
        return 'fitness'
    elif any(word in desc_lower for word in ['clinic', 'doctor', 'medical', 'klinik']):
        return 'clinic'
    elif any(word in desc_lower for word in ['photo', 'photographer', 'photography', 'wedding']):
        return 'photography'
    elif any(word in desc_lower for word in ['shop', 'store', 'kedai', 'boutique']):
        return 'retail'
    else:
        return 'general_business'


def get_stock_images(desc: str) -> dict:
    business_type = detect_business_type(desc)

    image_keywords = {
        'beauty_salon': 'salon',
        'restaurant': 'restaurant',
        'pet_shop': 'pet-store',
        'fitness': 'gym',
        'clinic': 'clinic',
        'photography': 'photography-studio',
        'retail': 'retail-store',
        'general_business': 'office'
    }

    keyword = image_keywords.get(business_type, 'business')

    return {
        'hero': f'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=1200&h=600&fit=crop',
        'gallery': [
            f'https://source.unsplash.com/600x400/?{keyword},1',
            f'https://source.unsplash.com/600x400/?{keyword},2',
            f'https://source.unsplash.com/600x400/?{keyword},3',
            f'https://source.unsplash.com/600x400/?{keyword},4'
        ]
    }


def upload_to_cloudinary(image_bytes: bytes, folder: str = "binaapp") -> Optional[str]:
    """Upload image bytes to Cloudinary, return URL"""
    if not CLOUDINARY_CLOUD_NAME:
        return None

    try:
        result = cloudinary.uploader.upload(
            image_bytes,
            folder=folder,
            resource_type="image"
        )
        url = result.get('secure_url')
        logger.info(f"☁️ Cloudinary uploaded: {url[:60]}...")
        return url
    except Exception as e:
        logger.error(f"☁️ Cloudinary upload failed: {e}")
        return None


async def generate_stability_image(prompt: str) -> Optional[str]:
    """Generate image using Stability AI and upload to Cloudinary"""
    if not STABILITY_API_KEY:
        logger.info("🎨 STABILITY - No API key")
        return None

    try:
        logger.info(f"🎨 STABILITY - Generating: {prompt[:50]}...")

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": f"{prompt}, professional photography, high quality, commercial",
                    "negative_prompt": "blurry, low quality, cartoon, anime, sketch",
                    "output_format": "png",
                    "aspect_ratio": "16:9"
                }
            )

            if response.status_code == 200:
                image_bytes = response.content

                # Try to upload to Cloudinary
                cloudinary_url = upload_to_cloudinary(image_bytes)

                if cloudinary_url:
                    logger.info("🎨 STABILITY - ✅ Uploaded to Cloudinary")
                    return cloudinary_url
                else:
                    # Fallback to base64 (not recommended for production)
                    logger.warning("🎨 STABILITY - ⚠️ Cloudinary failed, using base64")
                    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                    return f"data:image/png;base64,{image_base64}"
            else:
                logger.error(f"🎨 STABILITY - ❌ Failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"🎨 STABILITY - ❌ Error: {e}")
        return None


async def generate_all_images(desc: str) -> Optional[dict]:
    """Generate hero image and 4 different gallery images"""
    business_type = detect_business_type(desc)

    images = {
        'hero': None,
        'gallery': []
    }

    # Generate Hero Image
    hero_prompt = f"Modern {business_type.replace('_', ' ')} storefront exterior, professional photography, daytime, welcoming entrance, {desc}"
    hero_image = await generate_stability_image(hero_prompt)

    if hero_image:
        images['hero'] = hero_image
        logger.info("🎨 Hero image generated")
    else:
        return None

    # Generate 4 Different Gallery Images with unique prompts
    gallery_prompts = [
        f"Interior view of {business_type.replace('_', ' ')}, modern design, customers browsing, warm lighting, {desc}",
        f"Product display showcase at {business_type.replace('_', ' ')}, close-up, professional arrangement, {desc}",
        f"Staff working at {business_type.replace('_', ' ')}, friendly service, professional environment, {desc}",
        f"Cozy seating area in {business_type.replace('_', ' ')}, comfortable atmosphere, modern furniture, {desc}"
    ]

    for i, prompt in enumerate(gallery_prompts):
        logger.info(f"🎨 Generating gallery image {i+1}/4...")
        gallery_image = await generate_stability_image(prompt)

        if gallery_image:
            images['gallery'].append(gallery_image)
            logger.info(f"🎨 Gallery image {i+1} - ✅")
        else:
            # Fallback: reuse hero if generation fails
            images['gallery'].append(images['hero'])
            logger.warning(f"🎨 Gallery image {i+1} - ⚠️ Using hero as fallback")

    # Ensure we have 4 gallery images
    while len(images['gallery']) < 4:
        images['gallery'].append(images['hero'])

    logger.info(f"🎨 All images generated: 1 hero + {len(images['gallery'])} gallery")
    return images


async def call_deepseek(prompt: str) -> Optional[str]:
    """Call DeepSeek V3.2 API"""
    if not DEEPSEEK_API_KEY:
        return None

    try:
        logger.info("🔷 DEEPSEEK - Calling API...")

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
                        {"role": "system", "content": "You are an expert web developer. Output only valid HTML code."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 8000,
                    "temperature": 0.8
                }
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                logger.info(f"🔷 DEEPSEEK - ✅ Success ({len(content)} chars)")
                return content
            else:
                logger.error(f"🔷 DEEPSEEK - ❌ Failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"🔷 DEEPSEEK - ❌ Error: {e}")
        return None


async def call_qwen(prompt: str) -> Optional[str]:
    """Call Qwen API"""
    if not QWEN_API_KEY:
        return None

    try:
        logger.info("🟡 QWEN - Calling API...")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-plus",
                    "messages": [
                        {"role": "system", "content": "You are a Malaysian copywriter. Output only valid HTML code."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 8000,
                    "temperature": 0.7
                }
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                logger.info(f"🟡 QWEN - ✅ Success ({len(content)} chars)")
                return content
            else:
                logger.error(f"🟡 QWEN - ❌ Failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"🟡 QWEN - ❌ Error: {e}")
        return None


def extract_html(text: str) -> str:
    if not text:
        return ""

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

    if '<' in text and '>' in text:
        return text.strip()

    return text


@app.post("/api/generate-simple")
async def generate_simple(request: GenerateRequest):
    """3-Step AI Pipeline with 3 Style Variations"""

    session_id = str(uuid.uuid4())[:8]

    desc = request.business_description or request.description or ""
    user_id = request.user_id or "anonymous"
    user_email = request.email

    if not desc:
        return JSONResponse(status_code=400, content={"success": False, "error": "Description required"})

    # Check rate limit (founders bypass limit)
    rate_limit = check_rate_limit(user_id, user_email)
    if not rate_limit["allowed"]:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": "Daily limit reached",
                "message": f"You've used all {FREE_LIMIT} free generations today!",
                "usage": rate_limit
            }
        )

    # Initialize progress
    generation_progress[session_id] = {
        "percent": 5,
        "step": "Analyzing your business description...",
        "steps_completed": []
    }

    logger.info("=" * 70)
    logger.info("🌐 WEBSITE GENERATION - 3 STYLE VARIATIONS")
    logger.info(f"   Session: {session_id}")
    logger.info(f"   Business: {desc[:60]}...")
    logger.info("=" * 70)

    try:
        business_type = detect_business_type(desc)
        logger.info(f"📋 Detected: {business_type}")

        stock_images = get_stock_images(desc)

        # Update progress
        generation_progress[session_id] = {
            "percent": 10,
            "step": "Generating AI images...",
            "steps_completed": ["Analyzing your business description..."]
        }

        # STEP 1: Generate AI Images (once, reuse for all styles)
        logger.info("")
        logger.info("🎨 STEP 1: Stability AI + Cloudinary...")
        ai_images = None

        if STABILITY_API_KEY:
            ai_images = await generate_all_images(desc)
            if ai_images:
                logger.info("🎨 STEP 1 - ✅ Complete")

        hero_img = ai_images['hero'] if ai_images else stock_images['hero']
        gallery_imgs = ai_images['gallery'] if ai_images else stock_images['gallery']

        # Update progress
        generation_progress[session_id] = {
            "percent": 25,
            "step": "Generating Modern style...",
            "steps_completed": [
                "Analyzing your business description...",
                "Generating AI images..."
            ]
        }

        # Define 3 style variations
        styles_config = [
            {
                "name": "modern",
                "display_name": "Modern",
                "description": "Vibrant gradients (purple to blue), glassmorphism effects, rounded corners, bold shadows, smooth animations",
                "colors": "purple-600, blue-500, gradient backgrounds",
                "font": "bold, modern sans-serif",
                "progress_percent": 25
            },
            {
                "name": "minimal",
                "display_name": "Minimal",
                "description": "Clean white background, lots of whitespace, simple black text, thin borders, subtle shadows, elegant simplicity",
                "colors": "white, black, gray-100, one accent color",
                "font": "thin, elegant, light weight",
                "progress_percent": 50
            },
            {
                "name": "bold",
                "display_name": "Bold",
                "description": "Dark theme with black/dark gray background, large impactful typography, neon accent colors, strong contrast",
                "colors": "black, dark gray, neon cyan/pink accents",
                "font": "extra bold, uppercase headings",
                "progress_percent": 75
            }
        ]

        generated_styles = []

        # STEP 2 & 3: Generate each style variation
        for style in styles_config:
            # Update progress for each style
            generation_progress[session_id]["percent"] = style["progress_percent"]
            generation_progress[session_id]["step"] = f"Generating {style['display_name']} style..."
            logger.info(f"🎨 Generating {style['display_name'].upper()} style...")

            # Use actual gallery images (not all same)
            gallery_urls = gallery_imgs if isinstance(gallery_imgs, list) else [gallery_imgs] * 4

            # STEP 2: DeepSeek generates HTML structure
            logger.info(f"🔷 DeepSeek generating {style['name']} HTML...")

            deepseek_prompt = f"""Create a stunning {style['display_name']} website for: {desc}

DESIGN STYLE: {style['description']}
COLORS: {style['colors']}
TYPOGRAPHY: {style['font']}

Business Type: {business_type}

Use these placeholders:
- [BUSINESS_NAME], [BUSINESS_TAGLINE], [ABOUT_TEXT]
- [SERVICE_1_TITLE], [SERVICE_1_DESC]
- [SERVICE_2_TITLE], [SERVICE_2_DESC]
- [SERVICE_3_TITLE], [SERVICE_3_DESC]
- [CTA_TEXT], [FOOTER_TEXT]

IMAGES (use these EXACT URLs - each gallery image is DIFFERENT):
- Hero: {hero_img}
- Gallery 1: {gallery_urls[0] if len(gallery_urls) > 0 else hero_img}
- Gallery 2: {gallery_urls[1] if len(gallery_urls) > 1 else hero_img}
- Gallery 3: {gallery_urls[2] if len(gallery_urls) > 2 else hero_img}
- Gallery 4: {gallery_urls[3] if len(gallery_urls) > 3 else hero_img}

CRITICAL: Each gallery image URL is DIFFERENT. Do NOT use the same URL for all images.

Requirements:
1. <!DOCTYPE html> with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive
3. Sections: Header, Hero, About, Services (3 cards), Gallery (4 DIFFERENT images), Contact, Footer
4. WhatsApp button: <a href="https://wa.me/60123456789">WhatsApp</a>

Output ONLY complete HTML."""

            html_structure = await call_deepseek(deepseek_prompt)

            if not html_structure:
                logger.warning(f"🔷 DeepSeek failed for {style['name']}, skipping...")
                continue

            html_structure = extract_html(html_structure)

            # Update progress
            generation_progress[session_id]["step"] = f"Improving {style['display_name']} content..."

            # STEP 3: Qwen improves content
            logger.info(f"🟡 Qwen improving {style['name']} content...")

            qwen_prompt = f"""Replace ALL placeholders with Malaysian-friendly content.

Business: {desc}
Style: {style['display_name']}

REPLACE:
- [BUSINESS_NAME] → Business name
- [BUSINESS_TAGLINE] → Catchy tagline
- [ABOUT_TEXT] → About us (2-3 sentences)
- [SERVICE_1_TITLE], [SERVICE_1_DESC] → Service 1
- [SERVICE_2_TITLE], [SERVICE_2_DESC] → Service 2
- [SERVICE_3_TITLE], [SERVICE_3_DESC] → Service 3
- [CTA_TEXT] → Call to action
- [FOOTER_TEXT] → Footer tagline

DO NOT change image URLs. Keep them exactly as they are.

HTML:
{html_structure}

Output ONLY improved HTML."""

            final_html = await call_qwen(qwen_prompt)

            if final_html:
                final_html = extract_html(final_html)
            else:
                final_html = html_structure

            # Add analytics script
            tracking_script = '''
<!-- BinaApp Analytics -->
<script>
(function() {
    const PROJECT_ID = 'PENDING';
    const API_URL = 'https://binaapp-backend.onrender.com/api/analytics/track';
    let visitorId = localStorage.getItem('binaapp_visitor');
    if (!visitorId) {
        visitorId = 'v_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('binaapp_visitor', visitorId);
    }
    fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: PROJECT_ID,
            visitor_id: visitorId,
            referrer: document.referrer,
            page_path: window.location.pathname
        })
    }).catch(function() {});
})();
</script>
'''
            if '</body>' in final_html:
                final_html = final_html.replace('</body>', f'{tracking_script}</body>')

            generated_styles.append({
                "style": style['name'],
                "name": style['display_name'],
                "description": style['description'],
                "html": final_html
            })

            # Update completed steps
            generation_progress[session_id]["steps_completed"].append(f"Generating {style['display_name']} style...")

            logger.info(f"✅ {style['display_name']} style complete!")

        # Final progress update
        generation_progress[session_id] = {
            "percent": 100,
            "step": "Complete!",
            "steps_completed": [
                "Analyzing your business description...",
                "Generating AI images...",
                "Generating Modern style...",
                "Generating Minimal style...",
                "Generating Bold style..."
            ]
        }

        # Increment usage
        increment_usage(user_id)

        # Clean up progress after a delay
        async def cleanup_progress():
            await asyncio.sleep(60)
            generation_progress.pop(session_id, None)

        asyncio.create_task(cleanup_progress())

        logger.info(f"✅ GENERATION COMPLETE! {len(generated_styles)} styles")

        if not generated_styles:
            return JSONResponse(status_code=500, content={"success": False, "error": "Failed to generate"})

        return {
            "success": True,
            "session_id": session_id,
            "html": generated_styles[0]["html"],
            "styles": generated_styles,
            "usage": check_rate_limit(user_id, user_email),
            "business_type": business_type
        }

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        generation_progress.pop(session_id, None)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ==================== NEW GENERATION ENDPOINTS WITH SUPABASE TRACKING ====================

async def generate_style_variation(description: str, language: str, style_config: dict, hero_image: str, gallery_images: list) -> str:
    """Generate a single style variation HTML"""

    # Use actual gallery images (not all same)
    gallery_urls = gallery_images if isinstance(gallery_images, list) else [gallery_images] * 4

    # STEP 1: DeepSeek generates HTML structure
    logger.info(f"🔷 DeepSeek generating {style_config['name']} HTML...")

    deepseek_prompt = f"""Create a stunning {style_config['display_name']} website for: {description}

DESIGN STYLE: {style_config['description']}
COLORS: {style_config['colors']}
TYPOGRAPHY: {style_config['font']}

Use these placeholders:
- [BUSINESS_NAME], [BUSINESS_TAGLINE], [ABOUT_TEXT]
- [SERVICE_1_TITLE], [SERVICE_1_DESC]
- [SERVICE_2_TITLE], [SERVICE_2_DESC]
- [SERVICE_3_TITLE], [SERVICE_3_DESC]
- [CTA_TEXT], [FOOTER_TEXT]

IMAGES (use these EXACT URLs - each gallery image is DIFFERENT):
- Hero: {hero_image}
- Gallery 1: {gallery_urls[0] if len(gallery_urls) > 0 else hero_image}
- Gallery 2: {gallery_urls[1] if len(gallery_urls) > 1 else hero_image}
- Gallery 3: {gallery_urls[2] if len(gallery_urls) > 2 else hero_image}
- Gallery 4: {gallery_urls[3] if len(gallery_urls) > 3 else hero_image}

CRITICAL: Each gallery image URL is DIFFERENT. Do NOT use the same URL for all images.

Requirements:
1. <!DOCTYPE html> with <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive
3. Sections: Header, Hero, About, Services (3 cards), Gallery (4 DIFFERENT images), Contact, Footer
4. WhatsApp button: <a href="https://wa.me/60123456789">WhatsApp</a>

Output ONLY complete HTML."""

    html_structure = await call_deepseek(deepseek_prompt)

    if not html_structure:
        logger.warning(f"🔷 DeepSeek failed for {style_config['name']}")
        return None

    html_structure = extract_html(html_structure)

    # STEP 2: Qwen improves content
    logger.info(f"🟡 Qwen improving {style_config['name']} content...")

    qwen_prompt = f"""Replace ALL placeholders with Malaysian-friendly content.

Business: {description}
Style: {style_config['display_name']}

REPLACE:
- [BUSINESS_NAME] → Business name
- [BUSINESS_TAGLINE] → Catchy tagline
- [ABOUT_TEXT] → About us (2-3 sentences)
- [SERVICE_1_TITLE], [SERVICE_1_DESC] → Service 1
- [SERVICE_2_TITLE], [SERVICE_2_DESC] → Service 2
- [SERVICE_3_TITLE], [SERVICE_3_DESC] → Service 3
- [CTA_TEXT] → Call to action
- [FOOTER_TEXT] → Footer tagline

DO NOT change image URLs. Keep them exactly as they are.

HTML:
{html_structure}

Output ONLY improved HTML."""

    final_html = await call_qwen(qwen_prompt)

    if final_html:
        final_html = extract_html(final_html)
    else:
        final_html = html_structure

    # Add analytics script
    tracking_script = '''
<!-- BinaApp Analytics -->
<script>
(function() {
  const projectId = window.location.hostname;
  const visitorId = localStorage.getItem('bina_visitor') || 'v_' + Math.random().toString(36).substr(2, 9);
  localStorage.setItem('bina_visitor', visitorId);

  fetch('https://binaapp-backend.onrender.com/api/analytics/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      visitor_id: visitorId,
      referrer: document.referrer,
      page_path: window.location.pathname
    })
  }).catch(() => {});
})();
</script>
'''

    if '</body>' in final_html:
        final_html = final_html.replace('</body>', f'{tracking_script}</body>')
    else:
        final_html += tracking_script

    return final_html


@app.post("/api/generate/start")
async def start_generation(request: Request):
    """Start generation - runs synchronously with Supabase tracking"""

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ Invalid JSON: {e}")
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid JSON"})

    # Extract request parameters
    description = body.get("description") or body.get("business_description") or ""
    language = body.get("language", "en")
    user_id = body.get("user_id", "anonymous")
    user_email = body.get("email")

    if not description:
        return JSONResponse(status_code=400, content={"success": False, "error": "Description required"})

    # Check rate limit (founders bypass limit)
    rate_limit = check_rate_limit(user_id, user_email)
    if not rate_limit["allowed"]:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": "Daily limit reached",
                "message": f"You've used all {FREE_LIMIT} free generations today!",
                "usage": rate_limit
            }
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    logger.info("=" * 70)
    logger.info("🚀 NEW GENERATION JOB STARTED (SYNC)")
    logger.info(f"   Job ID: {job_id}")
    logger.info(f"   User: {user_email or user_id}")
    logger.info(f"   Description: {description[:60]}...")
    logger.info("=" * 70)

    # Create job record in Supabase
    if supabase:
        try:
            supabase.table("generation_jobs").insert({
                "job_id": job_id,
                "status": "processing",
                "progress": 10,
                "description": description,
                "language": language,
                "user_id": user_id,
                "email": user_email,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
            logger.info(f"✅ Job {job_id} created in database")
        except Exception as db_error:
            logger.error(f"❌ Failed to create job in database: {db_error}")
            # Continue anyway - we can still generate

    # Run generation SYNCHRONOUSLY
    try:
        logger.info(f"🔄 Starting AI generation for job: {job_id}")

        # Update progress to 20%
        if supabase:
            try:
                supabase.table("generation_jobs").update({
                    "progress": 20,
                    "updated_at": datetime.now().isoformat()
                }).eq("job_id", job_id).execute()
            except:
                pass

        # Detect business type
        business_type = detect_business_type(description)
        logger.info(f"📋 Detected business type: {business_type}")

        # Get stock images
        stock_images = get_stock_images(description)

        # Update progress to 30%
        if supabase:
            try:
                supabase.table("generation_jobs").update({
                    "progress": 30,
                    "updated_at": datetime.now().isoformat()
                }).eq("job_id", job_id).execute()
            except:
                pass

        # STEP 1: Generate AI Images (if Stability AI is available)
        logger.info("🎨 STEP 1: Generating images...")
        ai_images = None

        if STABILITY_API_KEY:
            ai_images = await generate_all_images(description)
            if ai_images:
                logger.info("✅ AI images generated successfully")

        hero_img = ai_images['hero'] if ai_images else stock_images['hero']
        gallery_imgs = ai_images['gallery'] if ai_images else stock_images['gallery']

        # Update progress to 40%
        if supabase:
            try:
                supabase.table("generation_jobs").update({
                    "progress": 40,
                    "updated_at": datetime.now().isoformat()
                }).eq("job_id", job_id).execute()
            except:
                pass

        # Define 3 style variations
        styles_config = [
            {
                "name": "modern",
                "display_name": "Modern",
                "description": "Vibrant gradients (purple to blue), glassmorphism effects, rounded corners",
                "colors": "purple-600, blue-500, gradient backgrounds",
                "font": "bold, modern sans-serif",
                "progress_percent": 50
            },
            {
                "name": "minimal",
                "display_name": "Minimal",
                "description": "Clean white background, lots of whitespace, simple black text",
                "colors": "white, black, gray-100",
                "font": "thin, elegant",
                "progress_percent": 70
            },
            {
                "name": "bold",
                "display_name": "Bold",
                "description": "Dark background, bright accent colors, large bold typography",
                "colors": "gray-900, yellow-400, bold contrasts",
                "font": "heavy, impactful",
                "progress_percent": 90
            }
        ]

        logger.info(f"🎨 STEP 2: Generating {len(styles_config)} style variations...")
        generated_styles = []

        for idx, style in enumerate(styles_config, 1):
            logger.info(f"   Generating {style['display_name']} ({idx}/{len(styles_config)})...")

            # Update progress
            if supabase:
                try:
                    supabase.table("generation_jobs").update({
                        "progress": style['progress_percent'],
                        "updated_at": datetime.now().isoformat()
                    }).eq("job_id", job_id).execute()
                except:
                    pass

            # Generate HTML for this style
            html = await generate_style_variation(
                description=description,
                language=language,
                style_config=style,
                hero_image=hero_img,
                gallery_images=gallery_imgs
            )

            if html:
                generated_styles.append({
                    "style": style["name"],
                    "html": html,
                    "display_name": style["display_name"]
                })
                logger.info(f"   ✅ {style['display_name']} generated ({len(html)} chars)")

        logger.info(f"✅ AI generation complete for job: {job_id} - Generated {len(generated_styles)} styles")

        # Increment usage (founders bypass)
        increment_usage(user_id, user_email)

        # Update progress to 100% and save result
        if supabase:
            try:
                supabase.table("generation_jobs").update({
                    "status": "completed",
                    "progress": 100,
                    "html": generated_styles[0]["html"] if generated_styles else None,
                    "styles": json.dumps(generated_styles),
                    "business_type": business_type,
                    "updated_at": datetime.now().isoformat()
                }).eq("job_id", job_id).execute()
                logger.info(f"✅ Job {job_id} completed and saved to database")
            except db_error:
                logger.error(f"⚠️ Failed to save completed job: {db_error}")

        # Return success with job_id
        return {
            "success": True,
            "job_id": job_id,
            "status": "completed",
            "html": generated_styles[0]["html"] if generated_styles else None,
            "styles": generated_styles,
            "business_type": business_type
        }

    except Exception as e:
        logger.error(f"❌ Generation failed for job {job_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Save error to database
        if supabase:
            try:
                supabase.table("generation_jobs").update({
                    "status": "failed",
                    "error": str(e),
                    "updated_at": datetime.now().isoformat()
                }).eq("job_id", job_id).execute()
            except:
                pass

        return JSONResponse(status_code=500, content={
            "success": False,
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        })


@app.get("/api/generate/status/{job_id}")
async def get_generation_status(job_id: str):
    """Check job status from Supabase"""

    logger.info(f"📊 Checking status for job: {job_id}")

    if not supabase:
        logger.error("❌ Supabase not configured")
        return JSONResponse(status_code=500, content={
            "status": "error",
            "error": "Database not configured"
        })

    try:
        result = supabase.table("generation_jobs").select("*").eq("job_id", job_id).execute()

        if not result.data:
            logger.warning(f"⚠️ Job not found: {job_id}")
            return JSONResponse(status_code=404, content={
                "status": "not_found",
                "error": "Job not found"
            })

        job = result.data[0]
        logger.info(f"📊 Job {job_id}: status={job['status']}, progress={job.get('progress', 0)}%")

        # Parse styles if available
        styles = None
        if job.get("styles"):
            try:
                styles = json.loads(job["styles"]) if isinstance(job["styles"], str) else job["styles"]
            except:
                styles = None

        return {
            "status": job["status"],
            "progress": job.get("progress", 0),
            "html": job.get("html") if job["status"] == "completed" else None,
            "styles": styles if job["status"] == "completed" else None,
            "business_type": job.get("business_type"),
            "error": job.get("error")
        }

    except Exception as e:
        logger.error(f"❌ Failed to retrieve job {job_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={
            "status": "error",
            "error": str(e)
        })


@app.get("/api/test-ai")
async def test_ai():
    """Test all services"""
    return {
        "keys": {
            "deepseek": bool(DEEPSEEK_API_KEY),
            "qwen": bool(QWEN_API_KEY),
            "stability": bool(STABILITY_API_KEY),
            "cloudinary": bool(CLOUDINARY_CLOUD_NAME)
        }
    }


# ==================== ANALYTICS ENDPOINTS ====================

@app.post("/api/analytics/track")
async def track_pageview(request: TrackEventRequest, req: Request):
    """Track a pageview event - called from published websites"""
    if not supabase:
        return {"success": False, "error": "Database not connected"}

    try:
        # Get visitor info from request
        ip_address = req.client.host if req.client else "unknown"
        user_agent_string = req.headers.get("user-agent", "")

        # Parse user agent
        user_agent = parse_user_agent(user_agent_string)
        device_type = "mobile" if user_agent.is_mobile else "tablet" if user_agent.is_tablet else "desktop"
        browser = user_agent.browser.family
        os = user_agent.os.family

        # Generate visitor ID if not provided (hash of IP + user agent for privacy)
        visitor_id = request.visitor_id
        if not visitor_id:
            hash_input = f"{ip_address}{user_agent_string}"
            visitor_id = hashlib.md5(hash_input.encode()).hexdigest()[:16]

        # Insert analytics event
        supabase.table("analytics").insert({
            "project_id": request.project_id,
            "visitor_id": visitor_id,
            "ip_address": ip_address[:50],  # Truncate for privacy
            "user_agent": user_agent_string[:500],
            "device_type": device_type,
            "browser": browser,
            "os": os,
            "referrer": request.referrer,
            "page_path": request.page_path
        }).execute()

        # Update project total views
        supabase.rpc("increment_project_views", {"p_id": request.project_id}).execute()

        # Update daily stats
        today = date.today().isoformat()

        # Try to update existing daily record, or insert new one
        existing = supabase.table("analytics_daily").select("*").eq("project_id", request.project_id).eq("date", today).execute()

        if existing.data:
            # Update existing
            record = existing.data[0]
            update_data = {
                "total_views": record["total_views"] + 1,
            }
            if device_type == "mobile":
                update_data["mobile_views"] = record.get("mobile_views", 0) + 1
            else:
                update_data["desktop_views"] = record.get("desktop_views", 0) + 1

            supabase.table("analytics_daily").update(update_data).eq("id", record["id"]).execute()
        else:
            # Insert new daily record
            supabase.table("analytics_daily").insert({
                "project_id": request.project_id,
                "date": today,
                "total_views": 1,
                "unique_visitors": 1,
                "mobile_views": 1 if device_type == "mobile" else 0,
                "desktop_views": 0 if device_type == "mobile" else 1
            }).execute()

        logger.info(f"📊 Tracked pageview for project {request.project_id[:8]}...")
        return {"success": True}

    except Exception as e:
        logger.error(f"📊 Analytics error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/analytics/{project_id}")
async def get_project_analytics(project_id: str, days: int = 30):
    """Get analytics for a project"""
    if not supabase:
        return {"success": False, "error": "Database not connected"}

    try:
        # Get date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Get daily stats
        daily_stats = supabase.table("analytics_daily").select("*").eq(
            "project_id", project_id
        ).gte("date", start_date.isoformat()).lte("date", end_date.isoformat()).order("date").execute()

        # Get total stats
        project = supabase.table("websites").select("total_views, unique_visitors").eq("id", project_id).single().execute()

        # Get device breakdown
        device_stats = supabase.table("analytics").select("device_type").eq("project_id", project_id).execute()

        mobile_count = sum(1 for d in device_stats.data if d.get("device_type") == "mobile")
        desktop_count = sum(1 for d in device_stats.data if d.get("device_type") == "desktop")

        # Get top referrers
        referrer_stats = supabase.table("analytics").select("referrer").eq("project_id", project_id).not_.is_("referrer", "null").execute()

        referrer_counts = {}
        for r in referrer_stats.data:
            ref = r.get("referrer", "Direct")
            if ref:
                # Extract domain from referrer
                try:
                    domain = urlparse(ref).netloc or "Direct"
                except:
                    domain = ref[:50]
                referrer_counts[domain] = referrer_counts.get(domain, 0) + 1

        top_referrers = sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Get browser breakdown
        browser_stats = supabase.table("analytics").select("browser").eq("project_id", project_id).execute()

        browser_counts = {}
        for b in browser_stats.data:
            browser = b.get("browser", "Unknown")
            browser_counts[browser] = browser_counts.get(browser, 0) + 1

        top_browsers = sorted(browser_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "success": True,
            "analytics": {
                "total_views": project.data.get("total_views", 0) if project.data else 0,
                "unique_visitors": project.data.get("unique_visitors", 0) if project.data else 0,
                "daily_stats": daily_stats.data,
                "device_breakdown": {
                    "mobile": mobile_count,
                    "desktop": desktop_count
                },
                "top_referrers": [{"source": r[0], "count": r[1]} for r in top_referrers],
                "top_browsers": [{"browser": b[0], "count": b[1]} for b in top_browsers]
            }
        }

    except Exception as e:
        logger.error(f"📊 Analytics fetch error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/analytics/{project_id}/realtime")
async def get_realtime_analytics(project_id: str):
    """Get realtime visitors (last 5 minutes)"""
    if not supabase:
        return {"success": False, "error": "Database not connected"}

    try:
        five_minutes_ago = (datetime.now() - timedelta(minutes=5)).isoformat()

        recent = supabase.table("analytics").select("visitor_id").eq(
            "project_id", project_id
        ).gte("created_at", five_minutes_ago).execute()

        # Count unique visitors
        unique_recent = len(set(r.get("visitor_id") for r in recent.data))

        return {
            "success": True,
            "realtime": {
                "active_visitors": unique_recent,
                "last_5_minutes": len(recent.data)
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== SUBDOMAIN PUBLISHING ENDPOINTS ====================

@app.post("/api/publish")
async def publish_website(request: Request):
    """Publish website to subdomain"""
    global supabase

    logger.info("📤 PUBLISH REQUEST RECEIVED")

    # Check Supabase connection
    if supabase is None:
        logger.error("❌ Supabase is None - trying to reinitialize...")
        supabase = init_supabase()

        if supabase is None:
            logger.error("❌ Supabase reinitialization failed!")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Database not connected. Check SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
                }
            )

    try:
        body = await request.json()
        logger.info(f"📤 Request body keys: {list(body.keys())}")
    except Exception as e:
        logger.error(f"❌ Failed to parse request: {e}")
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid JSON"})

    # Extract data
    html_content = body.get("html_content") or body.get("html_code") or body.get("html") or ""
    subdomain = (body.get("subdomain") or "").lower().strip()
    project_name = body.get("project_name") or body.get("name") or subdomain
    user_id = body.get("user_id") or "anonymous"

    logger.info(f"📤 Subdomain: {subdomain}, Name: {project_name}, User: {user_id}")
    logger.info(f"📤 HTML length: {len(html_content)} chars")

    if not html_content:
        return JSONResponse(status_code=400, content={"success": False, "error": "No HTML content"})

    if not subdomain:
        return JSONResponse(status_code=400, content={"success": False, "error": "No subdomain"})

    # Clean subdomain
    subdomain = re.sub(r'[^a-z0-9-]', '', subdomain)
    if len(subdomain) < 2:
        return JSONResponse(status_code=400, content={"success": False, "error": "Subdomain too short"})

    try:
        # Check if subdomain exists
        existing = supabase.table("websites").select("id, user_id").eq("subdomain", subdomain).execute()

        project_id = None
        if existing.data:
            if existing.data[0].get("user_id") != user_id and existing.data[0].get("user_id") != "anonymous":
                return JSONResponse(status_code=400, content={"success": False, "error": "Subdomain taken"})
            project_id = existing.data[0]["id"]

        # Prepare data
        project_data = {
            "user_id": user_id,
            "name": project_name,
            "subdomain": subdomain,
            "html_code": html_content,
            "is_published": True,
            "published_url": f"https://{subdomain}.binaapp.my",
            "updated_at": datetime.now().isoformat()
        }

        # Save to database
        if project_id:
            result = supabase.table("websites").update(project_data).eq("id", project_id).execute()
            logger.info(f"✅ Updated project: {project_id}")
        else:
            result = supabase.table("websites").insert(project_data).execute()
            project_id = result.data[0]["id"] if result.data else None
            logger.info(f"✅ Created project: {project_id}")

        # Try storage upload (optional)
        try:
            file_path = f"{subdomain}/index.html"
            supabase.storage.from_("websites").upload(file_path, html_content.encode(), {"content-type": "text/html", "upsert": "true"})
            logger.info(f"✅ Uploaded to storage: {file_path}")
        except Exception as storage_err:
            logger.warning(f"⚠️ Storage upload failed (non-critical): {storage_err}")

        return {
            "success": True,
            "subdomain": subdomain,
            "url": f"https://{subdomain}.binaapp.my",
            "project_id": str(project_id) if project_id else None
        }

    except Exception as e:
        logger.error(f"❌ Publish error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/api/site/{subdomain}")
async def serve_published_site(subdomain: str):
    """Serve a published website by subdomain"""

    if not supabase:
        return HTMLResponse(content="<h1>Service unavailable</h1>", status_code=500)

    subdomain = subdomain.lower().strip()
    logger.info(f"🌐 Serving site: {subdomain}")

    try:
        # Try to get HTML from database first (faster)
        result = supabase.table("websites").select("html_code").eq("subdomain", subdomain).eq("is_published", True).execute()

        if result.data and result.data[0].get("html_code"):
            logger.info(f"✅ Serving from database")
            return HTMLResponse(content=result.data[0]["html_code"])

        # Fallback: get from storage
        file_path = f"{subdomain}/index.html"
        try:
            html_bytes = supabase.storage.from_("websites").download(file_path)
            logger.info(f"✅ Serving from storage")
            return HTMLResponse(content=html_bytes.decode('utf-8'))
        except Exception as storage_error:
            logger.warning(f"⚠️ Storage download failed: {storage_error}")

        # Not found
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Site Not Found</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🔍 Site Not Found</h1>
                <p>The site <strong>{subdomain}.binaapp.my</strong> does not exist.</p>
                <p><a href="https://binaapp.my">Create your own website with BinaApp</a></p>
            </body>
            </html>
            """,
            status_code=404
        )

    except Exception as e:
        logger.error(f"❌ Serve site error: {e}")
        return HTMLResponse(content=f"<h1>Error loading site</h1><p>{str(e)}</p>", status_code=500)


@app.get("/api/subdomain/check/{subdomain}")
async def check_subdomain(subdomain: str):
    """Check if subdomain is available"""

    if not supabase:
        return {"available": False, "error": "Database not connected"}

    subdomain = re.sub(r'[^a-z0-9-]', '', subdomain.lower())

    if len(subdomain) < 2:
        return {"available": False, "error": "Subdomain too short (min 2 characters)"}

    try:
        existing = supabase.table("websites").select("id").eq("subdomain", subdomain).execute()
        return {"available": len(existing.data) == 0, "subdomain": subdomain}
    except Exception as e:
        return {"available": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
