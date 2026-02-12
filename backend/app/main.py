from fastapi import FastAPI, Request, BackgroundTasks, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import httpx
import os
import logging
from pathlib import Path
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
from app.data.malaysian_prompts import (
    get_smart_stability_prompt,
    get_hero_prompt,
    get_fallback_image,
    MALAYSIAN_FOOD_PROMPTS
)
from app.services.ai_service import AIService
from app.models.schemas import WebsiteGenerationRequest, Language
from app.api.upload import router as upload_router
from app.api.v1.endpoints.menu_delivery import router as menu_delivery_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.router import api_router as v1_router
from app.api.chatbot import router as chatbot_router
from app.services.templates import template_service
from app.core.security import get_current_user

# Subscription lock system
from app.middleware.subscription_guard import subscription_check_middleware
from app.api.v1.endpoints import subscription_status

# Email polling system
from app.api.v1.endpoints.email_polling import router as email_polling_router

# Initialize AI service
ai_service = AIService()

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

# Include routers
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(menu_delivery_router, prefix="/api/v1", tags=["Menu & Delivery"])
app.include_router(v1_router, prefix="/api/v1")  # New delivery system + all v1 endpoints
app.include_router(health_router, tags=["Health"])  # Health check endpoints
app.include_router(chatbot_router, tags=["Chatbot"])  # Customer support chatbot
app.include_router(subscription_status.router, prefix="/api/v1", tags=["Subscription"])  # Subscription status endpoints
app.include_router(email_polling_router, prefix="/api/v1", tags=["Email Polling"])  # Email polling admin endpoints

# Mount static files for widgets (chat, delivery, etc.)
# Files are accessible at /static/widgets/chat-widget.js, etc.
# Use pathlib for reliable path resolution
static_dir = Path(__file__).parent.parent / "static"
static_dir_str = str(static_dir.resolve())
logger.info(f"📁 Static directory path: {static_dir_str}")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir_str), name="static")
    # Verify widgets exist
    widgets_dir = static_dir / "widgets"
    if widgets_dir.exists():
        widget_files = list(widgets_dir.glob("*.js"))
        logger.info(f"✅ Static directory mounted at /static: {static_dir_str}")
        logger.info(f"📦 Widget files found: {[f.name for f in widget_files]}")
    else:
        logger.warning(f"⚠️ Widgets directory not found at {widgets_dir}")
else:
    # Create the directory structure if it doesn't exist
    widgets_dir = static_dir / "widgets"
    widgets_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir_str), name="static")
    logger.info(f"✅ Static directory created and mounted: {static_dir_str}")

# CORS - explicit origins for security and proper browser handling
ALLOWED_ORIGINS = [
    "https://binaapp.my",
    "https://www.binaapp.my",
    "https://admin.binaapp.my",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
]

# Add any extra origins from environment variable (comma-separated)
_extra_origins = os.getenv("CORS_EXTRA_ORIGINS", "")
if _extra_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in _extra_origins.split(",") if o.strip()])

# Regex to match binaapp.my subdomains and Vercel preview/production deployments
ALLOWED_ORIGIN_REGEX = r"^https://([\w-]+\.binaapp\.my|binaapp\.my|[\w-]+\.vercel\.app)$"

_allowed_origin_pattern = re.compile(ALLOWED_ORIGIN_REGEX)


def is_allowed_origin(origin: str) -> bool:
    """Check if an origin is allowed (explicit list, binaapp.my subdomains, or Vercel pattern)"""
    if origin in ALLOWED_ORIGINS:
        return True
    if _allowed_origin_pattern.match(origin):
        return True
    return False


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Subscription lock check middleware
# Checks if user's subscription is locked and blocks protected routes
app.middleware("http")(subscription_check_middleware)

# Add CORS headers manually for preflight requests and mobile browsers
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    """Add explicit CORS headers for browser compatibility"""
    origin = request.headers.get("origin", "")

    # Check if the origin is allowed (explicit list + Vercel pattern)
    allowed_origin = origin if is_allowed_origin(origin) else ""

    # Handle preflight OPTIONS request
    if request.method == "OPTIONS" and allowed_origin:
        response = JSONResponse(content={"status": "ok"})
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    response = await call_next(request)
    if allowed_origin:
        response.headers["Access-Control-Allow-Origin"] = allowed_origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# ============================================
# SUBDOMAIN ROUTING MIDDLEWARE - CRITICAL
# ============================================
# Uses the improved middleware from app.middleware.subdomain which includes:
# - Subscription lock checking (locked websites show "Website Tidak Aktif")
# - Proper widget injection (removes old widgets, injects correct website_id)
# - Auto-recovery for orphaned websites (exist in storage but not in DB)
# - Outermost try/except to prevent 502 Gateway errors from unhandled exceptions
# - Uses Supabase Python client with .limit(1) instead of .single() to avoid
#   exceptions when website is not found in database
from app.middleware.subdomain import subdomain_middleware as _subdomain_middleware
app.middleware("http")(_subdomain_middleware)

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

    # Initialize email polling scheduler
    try:
        from app.core.scheduler import start_email_polling
        from app.core.config import settings

        if settings.EMAIL_POLLING_ENABLED:
            logger.info("📧 Starting email polling service...")
            polling_started = await start_email_polling()
            if polling_started:
                logger.info("📧 Email polling service started successfully!")
            else:
                logger.warning("📧 Email polling service could not be started (check configuration)")
        else:
            logger.info("📧 Email polling is disabled in settings")
    except Exception as e:
        logger.error(f"📧 Failed to start email polling service: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully shutdown background services"""
    logger.info("🛑 Shutting down BinaApp API...")

    # Stop email polling scheduler
    try:
        from app.core.scheduler import stop_email_polling
        stop_email_polling()
        logger.info("📧 Email polling service stopped")
    except Exception as e:
        logger.error(f"📧 Error stopping email polling service: {e}")

    logger.info("🛑 BinaApp API shutdown complete")

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


def increment_usage(user_id: str = "anonymous", user_email: Optional[str] = None):
    """Increment usage count for non-founder users"""
    # Don't increment for founders (they have unlimited access)
    if user_email and user_email.lower() in [e.lower() for e in UNLIMITED_ACCESS_EMAILS]:
        logger.info(f"🔓 Founder {user_email} - not incrementing usage count")
        return

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


@app.get("/api/generate/status/{job_id}")
async def get_generation_status(job_id: str):
    """Check job status - called by frontend polling"""

    poll_timestamp = datetime.now().isoformat()
    logger.info(f"📊 Status poll for job: {job_id[:8]}... at {poll_timestamp}")

    job = await get_job_from_supabase(job_id)

    # DEBUG: Log raw Supabase response
    logger.info(f"🔍 DEBUG: Raw Supabase response for {job_id[:8]}: status={job.get('status') if job else 'None'}, progress={job.get('progress') if job else 'None'}, updated_at={job.get('updated_at') if job else 'None'}")

    if not job:
        logger.warning(f"❌ Job not found in Supabase: {job_id[:8]}")
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "status": "not_found",
                "error": "Job not found"
            }
        )

    job_status = job.get("status", "unknown")
    job_progress = job.get("progress", 0)
    job_html = job.get("html")
    job_error = job.get("error")

    logger.info(f"   Job {job_id[:8]}: status={job_status}, progress={job_progress}%, html={len(job_html) if job_html else 0} chars")

    # Parse styles/variants JSON if completed
    styles = None
    variants = None

    if job_status == "completed":
        # Try to get styles from job
        if job.get("styles"):
            try:
                styles = json.loads(job["styles"]) if isinstance(job["styles"], str) else job["styles"]
            except:
                styles = None

        # Try to get variants from job
        if job.get("variants"):
            try:
                variants = json.loads(job["variants"]) if isinstance(job["variants"], str) else job["variants"]
            except:
                variants = None

        # CRITICAL FIX: If we have HTML but no variants/styles, create a single variant
        # This ensures the frontend always gets data in the expected format
        if job_html and not variants and not styles:
            variants = [{
                "style": "modern",
                "html": job_html,
                "thumbnail": None,
                "social_preview": None
            }]
            logger.info(f"   Created single variant from HTML for job {job_id[:8]}")

    response = {
        "success": True,
        "status": job_status,
        "progress": job_progress,
        "html": job_html if job_status == "completed" else None,
        "styles": styles if job_status == "completed" else None,
        "variants": variants if job_status == "completed" else None,  # Frontend expects this!
        "error": job_error,
        "job_id": job_id,
        "polled_at": poll_timestamp,  # DEBUG: Track when this was polled
        "updated_at": job.get("updated_at") if job else None  # DEBUG: Track DB update time
    }

    if job_status == "completed":
        logger.info(f"✅ Returning COMPLETED status for job {job_id[:8]} with {len(variants) if variants else 0} variants")
    else:
        logger.info(f"📊 Returning status for job {job_id[:8]}: {job_status}, progress={job_progress}%")

    return response


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


def get_image_prompts_by_business_type(description: str) -> dict:
    """Generate appropriate image prompts based on business type to avoid wrong images"""

    desc_lower = description.lower()

    # PHOTOGRAPHY / PHOTOGRAPHER
    if any(word in desc_lower for word in ["photo", "photographer", "photography", "wedding photo", "gambar", "jurugambar"]):
        return {
            "hero": "Professional wedding photographer capturing couple moment, romantic sunset, DSLR camera, artistic photography",
            "gallery": "Beautiful bride and groom wedding portrait, elegant dress, romantic lighting, professional photography"
        }

    # RESTAURANT / FOOD
    elif any(word in desc_lower for word in ["restaurant", "food", "nasi", "makan", "cafe", "kedai makan", "makanan", "ayam", "ikan", "mee", "roti"]):
        return {
            "hero": "Malaysian restaurant interior, warm lighting, welcoming atmosphere, dining tables",
            "gallery": "Malaysian food nasi kandar with curry, delicious food photography, authentic Malaysian cuisine"
        }

    # FASHION / CLOTHING
    elif any(word in desc_lower for word in ["fashion", "clothing", "baju", "shirt", "boutique", "pakaian", "dress"]):
        return {
            "hero": "Modern fashion boutique interior, clothing displays, elegant design, shopping atmosphere",
            "gallery": "Premium clothing on mannequin, professional fashion product photography, boutique display"
        }

    # SALON / BEAUTY
    elif any(word in desc_lower for word in ["salon", "beauty", "spa", "hair", "kecantikan", "rambut", "haircut"]):
        return {
            "hero": "Modern beauty salon interior, styling chairs, mirrors, professional hair salon equipment",
            "gallery": "Professional hairstylist cutting hair, salon service, beauty treatment"
        }

    # WATCH / JEWELRY
    elif any(word in desc_lower for word in ["watch", "jam", "jewelry", "barang kemas", "timepiece"]):
        return {
            "hero": "Luxury watch store display, elegant showcase, premium timepieces, jewelry store interior",
            "gallery": "Luxury silver wristwatch, professional product photography, elegant timepiece"
        }

    # GYM / FITNESS
    elif any(word in desc_lower for word in ["gym", "fitness", "workout", "exercise", "gim", "senaman"]):
        return {
            "hero": "Modern gym interior, fitness equipment, workout space, professional training facility",
            "gallery": "Person working out at gym, fitness training, exercise equipment, athletic photography"
        }

    # BAKERY / PASTRY
    elif any(word in desc_lower for word in ["bakery", "cake", "pastry", "kek", "roti", "donut", "bread"]):
        return {
            "hero": "Artisan bakery interior, fresh bread display, warm lighting, cozy bakery atmosphere",
            "gallery": "Fresh baked pastries and cakes, food photography, delicious bakery products"
        }

    # DEFAULT / GENERIC BUSINESS
    else:
        business_name = description.split(',')[0].strip()[:30]
        return {
            "hero": f"Professional business interior, modern office, welcoming atmosphere, commercial space",
            "gallery": f"Professional service and products, quality business, commercial photography"
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


async def generate_stability_image(item_name: str, business_type: str = "") -> Optional[str]:
    """
    Generate image using Stability AI with smart Malaysian prompts.
    Upload to Cloudinary and return URL.

    Args:
        item_name: Name of menu item, product, or service
        business_type: Type of business (restaurant, salon, etc.)

    Returns:
        Cloudinary URL of generated image, or None if failed
    """
    if not STABILITY_API_KEY:
        logger.info("🎨 STABILITY - No API key")
        return None

    try:
        # GET SMART PROMPT for Malaysian context
        prompt = get_smart_stability_prompt(item_name, business_type)
        logger.info(f"🎨 STABILITY - Item: {item_name}")
        logger.info(f"🎨 STABILITY - Smart prompt: {prompt[:80]}...")

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Accept": "image/*"
                },
                files={"none": ''},
                data={
                    "prompt": prompt,
                    "negative_prompt": "blurry, low quality, cartoon, anime, sketch, drawing, illustration, 3d render",
                    "output_format": "png",
                    "aspect_ratio": "16:9"
                }
            )

            if response.status_code == 200:
                image_bytes = response.content

                # Upload to Cloudinary
                cloudinary_url = upload_to_cloudinary(image_bytes, folder="binaapp")

                if cloudinary_url:
                    logger.info(f"🎨 STABILITY - ✅ Uploaded: {cloudinary_url[:60]}...")
                    return cloudinary_url
                else:
                    logger.warning("🎨 STABILITY - ⚠️ Cloudinary failed")
                    # Return fallback stock image instead of base64
                    return get_fallback_image(item_name)
            else:
                logger.error(f"🎨 STABILITY - ❌ Failed: {response.status_code}")
                return get_fallback_image(item_name)

    except Exception as e:
        logger.error(f"🎨 STABILITY - ❌ Error: {e}")
        return get_fallback_image(item_name)


async def generate_all_images(desc: str) -> Optional[dict]:
    """
    Generate ONLY 2 images (hero + 1 gallery) to avoid timeout.
    Uses business-type-specific prompts to avoid wrong images (e.g., food for photography).

    REDUCED: 4 images → 2 images for speed
    With 30-second timeout per image = max 60 seconds total

    Args:
        desc: Business description

    Returns:
        Dict with 'hero' and 'gallery' images (gallery will have duplicates of the 1 image)
    """
    business_type = detect_business_type(desc)

    logger.info("=" * 60)
    logger.info("🎨 IMAGE GENERATION START")
    logger.info(f"   Business: {desc[:50]}...")
    logger.info(f"   Type: {business_type}")
    logger.info("=" * 60)

    images = {
        'hero': None,
        'gallery': []
    }

    # 🎯 GET BUSINESS-SPECIFIC PROMPTS (prevents wrong images)
    prompts = get_image_prompts_by_business_type(desc)
    hero_prompt = prompts["hero"]
    gallery_prompt = prompts["gallery"]

    # 🚀 GENERATE ONLY 2 IMAGES IN PARALLEL with 30s timeout each
    logger.info("🚀 Generating 2 images IN PARALLEL (hero + 1 gallery)...")
    logger.info(f"   Hero prompt: {hero_prompt[:60]}...")
    logger.info(f"   Gallery prompt: {gallery_prompt[:60]}...")

    start_time = asyncio.get_event_loop().time()

    try:
        # Wrap each generation with timeout - using BUSINESS-SPECIFIC PROMPTS
        hero_task = asyncio.wait_for(
            generate_stability_image(hero_prompt, business_type),
            timeout=30.0
        )
        gallery_task = asyncio.wait_for(
            generate_stability_image(gallery_prompt, business_type),
            timeout=30.0
        )

        results = await asyncio.gather(
            hero_task,
            gallery_task,
            return_exceptions=True
        )

        elapsed = asyncio.get_event_loop().time() - start_time
        logger.info(f"⏱️  Generation completed in {elapsed:.1f}s")

        hero_image = results[0] if not isinstance(results[0], Exception) else None
        gallery_image = results[1] if not isinstance(results[1], Exception) else None

        # Log results
        if isinstance(results[0], asyncio.TimeoutError):
            logger.warning("⏱️  Hero image TIMEOUT (30s)")
        elif isinstance(results[0], Exception):
            logger.error(f"❌ Hero error: {results[0]}")

        if isinstance(results[1], asyncio.TimeoutError):
            logger.warning("⏱️  Gallery image TIMEOUT (30s)")
        elif isinstance(results[1], Exception):
            logger.error(f"❌ Gallery error: {results[1]}")

    except Exception as e:
        logger.error(f"🚀 Parallel generation failed: {e}")
        hero_image = None
        gallery_image = None

    # Handle hero image
    if hero_image:
        images['hero'] = hero_image
        logger.info("✅ Hero image generated")
    else:
        # Use stock image as fallback
        stock_images = get_stock_images(desc)
        images['hero'] = stock_images['hero']
        logger.warning("⚠️  Hero image - using stock fallback")

    # Handle gallery image - use the 1 image for all 3 slots
    if gallery_image:
        images['gallery'] = [gallery_image, gallery_image, gallery_image]
        logger.info("✅ Gallery image generated (reusing for 3 slots)")
    else:
        # Fallback: reuse hero for all gallery slots
        images['gallery'] = [images['hero'], images['hero'], images['hero']]
        logger.warning("⚠️  Gallery - using hero as fallback for all slots")

    logger.info("=" * 60)
    logger.info(f"🎨 IMAGE GENERATION COMPLETE")
    logger.info(f"   Generated: 1 hero + 1 gallery (reused 3x)")
    logger.info(f"   Total time: {asyncio.get_event_loop().time() - start_time:.1f}s")
    logger.info("=" * 60)

    return images


async def generate_menu_images(menu_items: list, business_type: str = "restaurant") -> dict:
    """
    Generate unique images for each menu item IN PARALLEL with smart Malaysian prompts.
    Returns dict mapping item name to image URL.

    PARALLEL GENERATION = MUCH FASTER

    Args:
        menu_items: List of menu item names or dicts with 'name' key
        business_type: Type of business (restaurant, salon, etc.)

    Returns:
        Dictionary mapping item names to image URLs
    """
    images = {}

    # Extract all item names
    item_names = [
        item.get("name", "") if isinstance(item, dict) else str(item)
        for item in menu_items
    ]

    logger.info(f"🚀 Generating {len(item_names)} menu images IN PARALLEL...")

    # 🚀 GENERATE ALL MENU IMAGES IN PARALLEL
    try:
        results = await asyncio.gather(
            *[generate_stability_image(name, business_type) for name in item_names],
            return_exceptions=True
        )

        # Map results back to item names
        for item_name, result in zip(item_names, results):
            if result and not isinstance(result, Exception):
                images[item_name] = result
                logger.info(f"🎨 ✅ {item_name}")
            else:
                # Fallback to stock image
                images[item_name] = get_fallback_image(item_name)
                logger.warning(f"🎨 ⚠️ {item_name} → Using fallback")

    except Exception as e:
        logger.error(f"🚀 Parallel menu generation failed: {e}")
        # Fallback: use stock images for all
        for item_name in item_names:
            images[item_name] = get_fallback_image(item_name)

    logger.info(f"🚀 Menu images complete IN PARALLEL! Generated {len(images)} items")
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


async def call_qwen_turbo(prompt: str) -> Optional[str]:
    """Call Qwen-Turbo for fast responses (ideal for editor use)"""
    if not QWEN_API_KEY:
        return None

    try:
        logger.info("⚡ QWEN-TURBO - Calling API...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-turbo",  # TURBO = fastest model!
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,  # Lower for more predictable edits
                    "max_tokens": 8000
                }
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                logger.info(f"⚡ QWEN-TURBO - ✅ Success ({len(content)} chars)")
                return content
            else:
                logger.error(f"⚡ QWEN-TURBO - ❌ Failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"⚡ QWEN-TURBO - ❌ Error: {e}")
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

        # Increment usage (founders bypass)
        increment_usage(user_id, user_email)

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


# ==================== SIMPLE ASYNC GENERATION (NO BACKGROUND TASKS) ====================

async def run_generation_task(
    job_id: str,
    description: str,
    user_email: str = "",
    user_id: str = "anonymous",
    images: list = None,
    features: Optional[dict] = None,
    delivery: Optional[dict] = None,
    address: Optional[str] = None,
    social_media: Optional[dict] = None,
    payment: Optional[dict] = None,
    business_name: Optional[str] = None,
    language: str = "ms",
    image_choice: str = "none",
    color_mode: str = "light",
    template_id: Optional[str] = None,
):
    """Generate website - SIMPLE VERSION with guaranteed completion"""

    logger.info(f"🚀 TASK START: {job_id}")

    try:
        # Step 1: Update to 20%
        logger.info(f"📊 Updating progress to 20%")
        if supabase:
            result_20 = supabase.table("generation_jobs").update({
                "progress": 20,
                "updated_at": datetime.now().isoformat()
            }).eq("job_id", job_id).execute()
            logger.info(f"📊 Progress 20% update: {len(result_20.data) if result_20.data else 0} rows affected")

        # Step 2: Generate website using ai_service (4-step flow: Stability AI + Cloudinary + DeepSeek + Qwen)
        logger.info(f"🚀 Using ai_service 4-step generation for: {description[:50]}...")

        # ==================== USER SELECTION ENFORCEMENT ====================
        selected_features = features or {}

        # WhatsApp: default to True only if caller didn't send feature flags
        whatsapp_enabled = True
        if isinstance(selected_features, dict) and "whatsapp" in selected_features:
            whatsapp_enabled = bool(selected_features.get("whatsapp"))

        # Normalize image choice so "upload without uploads" becomes "none"
        user_has_uploaded_images = bool(images and len(images) > 0)
        normalized_image_choice = (image_choice or "none").lower().strip()
        if normalized_image_choice not in ["none", "upload", "ai"]:
            normalized_image_choice = "none"
        if normalized_image_choice == "upload" and not user_has_uploaded_images:
            logger.warning("⚠️ image_choice='upload' but no images provided -> forcing 'none'")
            normalized_image_choice = "none"
        elif user_has_uploaded_images:
            # If user uploaded images, we ALWAYS use them (upload mode)
            normalized_image_choice = "upload"

        # Build AI generation request
        # Respect explicit language selection from the client (no auto-detection).
        lang = (language or "ms").lower().strip()
        if lang in ["bm", "my", "malay", "bahasa", "bahasa melayu", "bahasa malaysia"]:
            lang = "ms"
        if lang not in ["ms", "en"]:
            lang = "ms"

        ai_request = WebsiteGenerationRequest(
            description=description,
            business_name=description.split()[0] if description else "Business",  # Simple extraction
            business_type="business",  # Generic type
            language=Language.MALAY if lang == "ms" else Language.ENGLISH,
            subdomain="preview",
            include_whatsapp=whatsapp_enabled,
            whatsapp_number="+60123456789" if whatsapp_enabled else None,
            include_maps=False,
            location_address="",
            include_ecommerce=False,
            contact_email=None,
            # If user chose "none", do not pass any uploaded images through.
            uploaded_images=(images if (images and normalized_image_choice != "none") else []),
            color_mode=color_mode,
            template_id=template_id,
        )

        # Create progress callback to update Supabase during generation
        async def progress_callback(progress: int, message: str):
            """Update job progress in Supabase during AI generation"""
            logger.info(f"📊 AI Progress: {progress}% - {message}")
            if supabase:
                try:
                    result = supabase.table("generation_jobs").update({
                        "progress": progress,
                        "updated_at": datetime.now().isoformat()
                    }).eq("job_id", job_id).execute()
                    logger.info(f"📊 Progress {progress}% update: {len(result.data) if result.data else 0} rows affected")
                except Exception as e:
                    logger.warning(f"⚠️ Progress update failed: {e}")

        # Call ai_service.generate_website() - This triggers the 4-step flow
        logger.info("🎨 Starting 4-step generation (Stability AI + Cloudinary + DeepSeek + Qwen)...")
        logger.info(f"   ✅ WhatsApp enabled: {whatsapp_enabled}")
        logger.info(f"   🖼️ Image choice: {normalized_image_choice}")
        ai_response = await ai_service.generate_website(
            ai_request,
            image_choice=normalized_image_choice,
            progress_callback=progress_callback  # NEW: Pass progress callback
        )
        html = ai_response.html_content

        logger.info(f"✅ Got HTML: {len(html)} chars")

        # ==================== SAFETY NET (ENFORCE USER CHOICES) ====================
        # Remove unwanted images (even if AI ignores prompt)
        try:
            user_image_urls = []
            for img in (images or []):
                if isinstance(img, dict):
                    url = img.get("url") or img.get("URL") or ""
                    if url:
                        user_image_urls.append(url)
                else:
                    s = str(img)
                    if s:
                        user_image_urls.append(s)

            html = template_service.apply_image_safety_guard(
                html=html,
                image_choice=normalized_image_choice,
                user_images=user_image_urls
            )
        except Exception as guard_err:
            logger.warning(f"⚠️ Image safety guard failed (continuing): {guard_err}")

        # Remove WhatsApp if disabled (AI might still output it)
        if not whatsapp_enabled:
            try:
                html_before = len(html)
                # Remove WhatsApp links/buttons
                html = re.sub(r'<a[^>]*(?:wa\.me|whatsapp)[^>]*>.*?</a>', '', html, flags=re.IGNORECASE | re.DOTALL)
                html = re.sub(r'href="https?://wa\.me[^"]*"', 'href="#"', html, flags=re.IGNORECASE)
                html = re.sub(r'href="https?://(?:api\.)?whatsapp\.com[^"]*"', 'href="#"', html, flags=re.IGNORECASE)
                # Remove common floating button wrappers
                html = re.sub(r'<div[^>]*class="[^"]*(?:whatsapp|wa-float)[^"]*"[^>]*>.*?</div>', '', html, flags=re.IGNORECASE | re.DOTALL)
                logger.info(f"🚫 WhatsApp disabled: removed {max(0, html_before - len(html))} bytes")
            except Exception as wa_err:
                logger.warning(f"⚠️ WhatsApp sanitization failed (continuing): {wa_err}")

        # Step 3: Update progress to 92% after AI generation and customizations
        logger.info(f"📊 Updating progress to 92% - applying customizations")
        if supabase:
            result_92 = supabase.table("generation_jobs").update({
                "progress": 92,
                "updated_at": datetime.now().isoformat()
            }).eq("job_id", job_id).execute()
            logger.info(f"📊 Progress 92% update: {len(result_92.data) if result_92.data else 0} rows affected")

        # OPTIONAL: Inject delivery/ordering system if user requested it via /api/generate/start payload.
        try:
            delivery_cfg = delivery or None

            # Features list for TemplateService (expects "delivery_system" token)
            features_list = []
            if selected_features.get("deliverySystem"):
                features_list.append("delivery_system")
            if selected_features.get("googleMap"):
                features_list.append("maps")
            if selected_features.get("contactForm"):
                features_list.append("contact")
            if selected_features.get("socialMedia"):
                features_list.append("social")
            if whatsapp_enabled:
                features_list.append("whatsapp")

            # Build menu items from uploaded images (matches frontend format: [{url,name,price}, ...])
            # CRITICAL FIX: ONLY use user's uploaded menu items - NEVER extract from AI-generated HTML!
            # The AI was extracting random text like "Get In Touch", "WhatsApp" as menu items.
            menu_items = []

            # Detect business type from description for proper category assignment
            from app.services.business_types import detect_business_type, detect_item_category
            from app.api.simple.generate import is_valid_menu_item_name
            business_type = detect_business_type(description)
            logger.info(f"🏢 Detected business type: {business_type}")

            # ⚠️ REMOVED: Do NOT extract menu items from AI-generated HTML!
            # This was causing "Get In Touch", "OPEN SHOP", "WhatsApp" to appear as menu items.
            # Only use user's uploaded items below.

            # Build menu items ONLY from user-uploaded images
            if images:
                from app.services.business_types import get_business_config
                biz_config = get_business_config(business_type)
                default_desc = biz_config.get("item_description_default", "Produk pilihan kami")
                default_prices = [15, 12, 18, 10, 20, 14, 16, 13]
                logger.info(f"🍽️ Processing {len(images)} user-uploaded images for menu items...")

                for idx, img in enumerate(images):
                    if isinstance(img, dict):
                        img_url = img.get("url", "")
                        img_name = img.get("name", f"Item {idx+1}")
                        # CRITICAL: Use user's price if provided
                        user_price = img.get("price")
                        if user_price:
                            try:
                                img_price = float(str(user_price).replace("RM", "").replace(",", "").strip())
                            except (ValueError, TypeError):
                                img_price = default_prices[idx % len(default_prices)]
                        else:
                            img_price = default_prices[idx % len(default_prices)]
                    else:
                        img_url = str(img)
                        img_name = f"Item {idx+1}"
                        img_price = default_prices[idx % len(default_prices)]

                    # Skip empty names or hero images
                    if not img_name or img_name == "Hero Image" or img_name.strip() == "":
                        continue

                    # CRITICAL: Validate menu item name to prevent hallucinated items
                    if not is_valid_menu_item_name(img_name):
                        logger.warning(f"   ⚠️ Skipping invalid menu item: '{img_name}'")
                        continue

                    # Auto-detect category based on item name and business type
                    category = detect_item_category(img_name, business_type)
                    menu_items.append({
                        "id": f"menu-{idx}",
                        "name": img_name,
                        "description": default_desc,
                        "price": img_price,
                        "image_url": img_url,
                        "category_id": category,
                        "is_available": True
                    })
                    logger.info(f"   ✅ Added menu item: {img_name} - RM{img_price:.2f} [{category}]")

                logger.info(f"🍽️ Created {len(menu_items)} valid menu items from user uploads")

            # Default delivery zone for ordering UI
            delivery_zones = []
            if selected_features.get("deliverySystem") and delivery_cfg:
                try:
                    fee_val = delivery_cfg.get("fee", 5)
                    if isinstance(fee_val, str):
                        fee_val = float(fee_val.replace("RM", "").strip())
                    minimum_val = delivery_cfg.get("minimum", 30)
                    if isinstance(minimum_val, str):
                        minimum_val = float(minimum_val.replace("RM", "").strip())
                except Exception:
                    fee_val = 5
                    minimum_val = 30

                # CRITICAL: Get zone name from multiple possible fields
                zone_name = (
                    delivery_cfg.get("area") or
                    delivery_cfg.get("zone_name") or
                    delivery_cfg.get("delivery_area") or
                    "Kawasan Delivery"
                )
                # Ensure zone_name is not empty
                if not zone_name or zone_name.strip() == "":
                    zone_name = "Kawasan Delivery"

                delivery_zones = [{
                    "id": "default",
                    "zone_name": zone_name,
                    "delivery_fee": float(fee_val),
                    "minimum_order": float(minimum_val),
                    "estimated_time": delivery_cfg.get("hours", "30-45 min"),
                    "estimated_time_min": 30,
                    "estimated_time_max": 45,
                    "is_active": True
                }]
                logger.info(f"📍 Created delivery zone: {zone_name} - RM{fee_val:.2f}")

            # FIXED: Use provided business_name, or extract intelligently from description
            # Don't just use first word - extract meaningful business name
            if business_name:
                actual_business_name = business_name
            elif description:
                # Try to extract meaningful name from description (first 3-4 words that look like a name)
                words = description.split()
                # Take first 3 words if they form a reasonable business name
                if len(words) >= 3:
                    actual_business_name = " ".join(words[:3])
                elif len(words) >= 1:
                    actual_business_name = words[0]
                else:
                    actual_business_name = "Business"
            else:
                actual_business_name = "Business"

            # Get phone number from delivery config if available
            phone_number = "+60123456789"
            if delivery_cfg and delivery_cfg.get("phone"):
                phone_number = delivery_cfg.get("phone")

            # CRITICAL FIX: Generate website_id for delivery widget injection
            # Without website_id, inject_ordering_system raises ValueError and skips delivery widget
            import uuid
            generated_website_id = str(uuid.uuid4())
            logger.info(f"✅ Generated website_id for background job: {generated_website_id}")

            user_data = {
                "phone": phone_number,
                "address": address or "",
                "email": "contact@business.com",
                "url": "https://preview.binaapp.my",
                "whatsapp_message": "Hi, I'm interested",
                "business_name": actual_business_name,
                "business_type": business_type,  # For dynamic categories
                "description": description,  # For business type detection
                "menu_items": menu_items,
                "delivery_zones": delivery_zones,
                "website_id": generated_website_id  # CRITICAL: Required for delivery widget
            }

            # Add delivery config
            if delivery_cfg:
                user_data["delivery"] = delivery_cfg

            # CRITICAL: Add payment data for QR payment support
            if payment:
                user_data["payment"] = payment
                logger.info(f"💳 Payment config: COD={payment.get('cod')}, QR={payment.get('qr')}, QR Image={'Yes' if payment.get('qr_image') else 'No'}")

            if "delivery_system" in features_list or delivery_cfg:
                html = template_service.inject_integrations(html, features_list, user_data)
                logger.info("✅ Injected delivery/ordering system into generated HTML")
        except Exception as inject_err:
            logger.warning(f"⚠️ Delivery injection skipped due to error: {inject_err}")

        # Step 4: Update progress to 95% - delivery system injected
        logger.info(f"📊 Updating progress to 95% - delivery system processed")
        if supabase:
            result_95 = supabase.table("generation_jobs").update({
                "progress": 95,
                "updated_at": datetime.now().isoformat()
            }).eq("job_id", job_id).execute()
            logger.info(f"📊 Progress 95% update: {len(result_95.data) if result_95.data else 0} rows affected")

        # Increment usage (founders bypass)
        increment_usage(user_id, user_email)

        # REPLACE PLACEHOLDERS WITH ACTUAL USER DATA before final save
        try:
            _menu = menu_items
        except NameError:
            _menu = []
        generation_data = {
            "description": description,
            "business_name": business_name or "",
            "project_name": business_name or "",
            "delivery": delivery or {},
            "address": address or "",
            "phone": (delivery or {}).get("phone", "") if isinstance(delivery, dict) else "",
            "menu_items": _menu,
            "payment": payment or {},
            "fulfillment": features or {},
        }
        html = replace_template_placeholders(html, generation_data)
        logger.info(f"📤 HTML after placeholder replacement: {len(html)} chars")

        # Step 5: MARK COMPLETED - THIS IS CRITICAL!
        logger.info(f"💾 Saving completed job to Supabase... (job_id={job_id})")
        logger.info(f"   HTML length: {len(html)} chars")

        if supabase:
            try:
                result = supabase.table("generation_jobs").update({
                    "status": "completed",
                    "progress": 100,
                    "html": html,
                    "updated_at": datetime.now().isoformat()
                }).eq("job_id", job_id).execute()

                # Verify the update actually worked
                if result.data and len(result.data) > 0:
                    logger.info(f"✅ JOB COMPLETED: {job_id}")
                    logger.info(f"📊 Supabase update SUCCESS - rows updated: {len(result.data)}")
                    logger.info(f"   Updated status: {result.data[0].get('status')}")
                    logger.info(f"   Updated progress: {result.data[0].get('progress')}")

                    # CRITICAL: Verify we can read back the completed status
                    verify_job = await get_job_from_supabase(job_id)
                    if verify_job:
                        logger.info(f"🔍 VERIFICATION READ: status={verify_job.get('status')}, progress={verify_job.get('progress')}")
                    else:
                        logger.error(f"❌ VERIFICATION FAILED: Could not read back job {job_id}")
                else:
                    logger.error(f"❌ Supabase update returned empty - job might not exist!")
                    logger.error(f"   job_id: {job_id}")
                    logger.error(f"   result.data: {result.data}")

            except Exception as update_error:
                logger.error(f"❌ Supabase update FAILED: {update_error}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning(f"⚠️ Supabase not available - job completed but not saved")

    except Exception as e:
        logger.error(f"❌ TASK FAILED: {job_id} - {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        # Mark as failed
        if supabase:
            try:
                supabase.table("generation_jobs").update({
                    "status": "failed",
                    "error": str(e)[:500],
                    "updated_at": datetime.now().isoformat()
                }).eq("job_id", job_id).execute()
                logger.info(f"❌ Job marked FAILED in Supabase")
            except Exception as e2:
                logger.error(f"❌ Could not save failure: {e2}")

    logger.info(f"🏁 TASK END: {job_id}")


@app.post("/api/generate/start")
async def start_generation(request: Request):
    """Start async generation using asyncio.create_task"""

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ Invalid JSON: {e}")
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid JSON"})

    # Extract parameters
    description = body.get("description") or body.get("business_description") or ""
    user_id = body.get("user_id", "anonymous")
    user_email = body.get("email", "")
    images = body.get("images", [])  # Extract uploaded images
    features = body.get("features") or {}
    image_choice = body.get("image_choice") or body.get("images_choice") or body.get("imageChoice") or "none"
    delivery = body.get("delivery") or None
    address = body.get("address") or None
    social_media = body.get("social_media") or None
    payment = body.get("payment") or None  # Payment methods (cod, qr, qr_image)
    business_name = body.get("business_name") or body.get("businessName") or None  # Actual business name
    language = body.get("language") or "ms"
    color_mode = body.get("color_mode") or body.get("colorMode") or "light"
    if color_mode not in ("light", "dark"):
        color_mode = "light"

    # Template gallery: optional design template selection
    template_id = body.get("template_id") or body.get("templateId") or None

    # Get dish names from request
    dish_names = body.get("dish_names", [])
    uploaded_images = body.get("uploaded_images", {})

    # Build image info for AI prompt
    image_info = ""
    if uploaded_images:
        # Extract gallery URLs and names
        gallery_urls = []
        gallery_names = []
        for i in range(4):
            key = f"gallery{i+1}"
            name = dish_names[i] if i < len(dish_names) else f"Menu Item {i+1}"
            if uploaded_images.get(key):
                gallery_urls.append(uploaded_images[key])
                gallery_names.append(name)

        # Build CRITICAL gallery instruction
        image_info = "\n\n"

        if uploaded_images.get("hero"):
            image_info += f"HERO IMAGE: {uploaded_images['hero']}\n\n"

        # Respect language selection for menu item descriptions
        lang = str(language or "ms").lower().strip()
        if lang in ["bm", "my", "malay", "bahasa", "bahasa melayu", "bahasa malaysia"]:
            lang = "ms"
        if lang not in ["ms", "en"]:
            lang = "ms"

        if len(gallery_urls) == 4:
            image_info += f"""CRITICAL - GALLERY IMAGES:
You MUST include EXACTLY 4 menu/gallery items using these images:
1. Gallery 1: {gallery_urls[0]} - Name: {gallery_names[0]}
2. Gallery 2: {gallery_urls[1]} - Name: {gallery_names[1]}
3. Gallery 3: {gallery_urls[2]} - Name: {gallery_names[2]}
4. Gallery 4: {gallery_urls[3]} - Name: {gallery_names[3]}

DO NOT skip any image. DO NOT use Unsplash for ANY gallery image.
All 4 images MUST be from the uploaded URLs above.
Each gallery item MUST use the exact name and URL specified.

MANDATORY REQUIREMENTS:
1. Use the dish names provided above as menu item titles (EXACT names)
2. Generate appropriate descriptions IN {"BAHASA MALAYSIA" if lang == "ms" else "ENGLISH"} for each dish
3. Use the EXACT image URLs provided above (DO NOT modify or replace)
4. DO NOT use Unsplash or any placeholder URLs
5. Make sure ALL 4 gallery images are included (not 3, not 2, but ALL 4)
6. Hero section: Use h-[60vh] (NOT h-[90vh])
7. Gallery images: Use h-48 (NOT h-64)
8. Each gallery item must be DIFFERENT - different image, different name, different description
"""
        else:
            # Fallback for partial uploads
            image_info += "USE THESE EXACT IMAGES AND NAMES:\n"
            if uploaded_images.get("hero"):
                image_info += f"- Hero Banner: {uploaded_images['hero']}\n"
            for i in range(4):
                key = f"gallery{i+1}"
                name = dish_names[i] if i < len(dish_names) else f"Menu Item {i+1}"
                if uploaded_images.get(key):
                    image_info += f"- {name}: {uploaded_images[key]}\n"
            image_info += "\nCRITICAL: Use EXACT URLs. DO NOT use Unsplash.\n"

    # Append image info to description
    if image_info:
        description = description + image_info

    if not description:
        return JSONResponse(status_code=400, content={"success": False, "error": "Description required"})

    # Check rate limit (founders bypass)
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

    # Generate job ID
    job_id = str(uuid.uuid4())

    logger.info(f"📝 Creating job: {job_id}")
    logger.info(f"   User: {user_email or user_id}")
    logger.info(f"   Description: {description[:60]}...")
    logger.info(f"   Images: {len(images) if images else 0} uploaded")
    logger.info(f"   Dish names: {dish_names if dish_names else 'None'}")
    logger.info(f"   Uploaded images: {len(uploaded_images)} items" if uploaded_images else "   Uploaded images: None")

    # Create job in Supabase (keep schema minimal to avoid column mismatch)
    if supabase:
        try:
            supabase.table("generation_jobs").insert({
                "job_id": job_id,
                "status": "processing",
                "progress": 0,
                "description": description,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
            logger.info(f"✅ Job created in database")
        except Exception as db_error:
            logger.error(f"❌ Failed to create job: {db_error}")
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": f"Database error: {str(db_error)}"
            })

    # Run generation with asyncio (NOT BackgroundTasks!)
    asyncio.create_task(run_generation_task(
        job_id,
        description,
        user_email,
        user_id,
        images,
        features,
        delivery,
        address,
        social_media,
        payment,
        business_name,
        language,
        image_choice=image_choice,
        color_mode=color_mode,
        template_id=template_id,
    ))

    logger.info(f"🚀 Job started: {job_id}")

    return {
        "success": True,
        "job_id": job_id,
        "status": "processing"
    }


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

def fix_website_id_in_html(html: str, correct_website_id: str) -> str:
    """
    Ensure all website_id references in HTML use the database record ID.
    """
    if not html:
        return html

    # data-website-id attribute (supports single or double quotes)
    html = re.sub(
        r'data-website-id=(["\'])([^"\']*)(["\'])',
        f'data-website-id="{correct_website_id}"',
        html
    )

    # JS initializer: websiteId: '...'
    html = re.sub(
        r"websiteId:\s*['\"]([^'\"]*)['\"]",
        f"websiteId: '{correct_website_id}'",
        html
    )

    # Delivery URL: binaapp.my/delivery/{id}
    html = re.sub(
        r'binaapp\.my/delivery/[a-f0-9-]+',
        f'binaapp.my/delivery/{correct_website_id}',
        html
    )

    # Inline ordering system constant
    html = re.sub(
        r"const WEBSITE_ID = ['\"]([^'\"]*)['\"]",
        f"const WEBSITE_ID = '{correct_website_id}'",
        html
    )

    # Optional global injection if present
    html = re.sub(
        r'window\.BINAAPP_WEBSITE_ID\s*=\s*["\'][^"\']*["\']',
        f'window.BINAAPP_WEBSITE_ID = "{correct_website_id}"',
        html
    )

    # Placeholder replacement if any
    html = html.replace("{{WEBSITE_ID}}", correct_website_id)

    return html


def replace_template_placeholders(html: str, request_data: dict) -> str:
    """
    Replace {{placeholder}} strings in generated HTML with actual user data.
    Must run BEFORE saving HTML to database/storage.
    """
    if not html or not request_data:
        return html or ""

    # === Detect primary color from template (used for menu + hours) ===
    primary_color = '#3B82F6'
    color_patterns = [
        ('#34d399', r'text-\[#34d399\]'),
        ('#D4AF37', r'text-\[#D4AF37\]'),
        ('#C084FC', r'text-\[#C084FC\]'),
        ('#00FFFF', r'text-\[#00FFFF\]'),
        ('#3B82F6', r'text-\[#3B82F6\]'),
        ('#ff6b35', r'text-\[#ff6b35\]'),
    ]
    for color, pattern in color_patterns:
        if re.search(pattern, html):
            primary_color = color
            break

    # === WhatsApp Number ===
    phone = ''
    delivery = request_data.get('delivery', {}) or {}
    if isinstance(delivery, dict):
        phone = delivery.get('whatsapp', '') or delivery.get('phone', '') or ''
    if not phone:
        phone = request_data.get('phone', '') or request_data.get('whatsapp', '') or ''

    if not phone:
        desc = request_data.get('description', '') or ''
        phone_match = re.search(r'(\+?6?0\d[\d\s-]{7,12})', desc)
        if phone_match:
            phone = phone_match.group(1).strip()

    if phone:
        wa_number = re.sub(r'[^0-9]', '', phone)
        if wa_number.startswith('0'):
            wa_number = '60' + wa_number[1:]
        elif not wa_number.startswith('60'):
            wa_number = '60' + wa_number
        html = re.sub(r'wa\.me/\d+', f'wa.me/{wa_number}', html)
        html = html.replace('+60123456789', phone)
        html = html.replace('60123456789', phone)

    # === Address ===
    address = ''
    if isinstance(delivery, dict):
        address = delivery.get('address', '') or delivery.get('location', '') or ''
    if not address:
        address = request_data.get('address', '') or request_data.get('location', '') or ''
    if not address:
        desc = request_data.get('description', '') or ''
        loc_match = re.search(r'(?:[Bb]ased in|[Ll]ocated in|[Dd]i|[Ll]okasi)\s+([^,.!]+)', desc)
        if loc_match:
            address = loc_match.group(1).strip()

    html = html.replace('{{address}}', address or 'Hubungi kami untuk alamat')

    # === Menu Items ===
    menu_items = request_data.get('menu_items', []) or []

    if '{{menu_items_html}}' in html:
        if menu_items and len(menu_items) > 0:
            cards = []
            for item in menu_items:
                if isinstance(item, dict):
                    name = item.get('name', '') or item.get('title', '') or 'Item'
                    price = item.get('price', '')
                    desc = item.get('description', '') or ''
                    image = item.get('image', '') or item.get('image_url', '') or ''
                elif isinstance(item, str):
                    name = item
                    price = ''
                    desc = ''
                    image = ''
                else:
                    continue

                img_html = ''
                if image:
                    img_html = f'<div class="aspect-video overflow-hidden rounded-t-2xl"><img src="{image}" alt="{name}" class="w-full h-full object-cover" loading="lazy"></div>'

                price_str = str(price) if price else ''
                price_display = ''
                if price_str:
                    if not price_str.startswith('RM'):
                        price_str = f'RM{price_str}'
                    price_display = f'<span class="text-lg font-bold" style="color:{primary_color}">{price_str}</span>'

                card = f'''<div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden hover:border-white/20 transition-all duration-500">
                    {img_html}
                    <div class="p-6">
                        <div class="flex justify-between items-start mb-3">
                            <h3 class="text-xl font-bold">{name}</h3>
                            {price_display}
                        </div>
                        {f'<p class="text-gray-400 text-sm">{desc}</p>' if desc else ''}
                    </div>
                </div>'''
                cards.append(card)

            html = html.replace('{{menu_items_html}}', '\n'.join(cards))
        else:
            html = html.replace('{{menu_items_html}}',
                '<div class="col-span-full text-center py-8"><p class="text-gray-500">Menu akan dikemaskini tidak lama lagi.</p></div>')

    # === Operating Hours ===
    hours = request_data.get('operating_hours', []) or request_data.get('hours', []) or []
    fulfillment = request_data.get('fulfillment', {}) or {}
    if not hours and isinstance(fulfillment, dict):
        hours = fulfillment.get('operating_hours', []) or fulfillment.get('hours', []) or []

    if '{{operating_hours_html}}' in html:
        if hours and len(hours) > 0:
            items = []
            for h in hours:
                if isinstance(h, dict):
                    days = h.get('days', '') or h.get('day', '') or h.get('label', '')
                    time_val = h.get('hours', '') or h.get('time', '') or h.get('open', '')
                    if not time_val:
                        open_time = h.get('open_time', '') or h.get('from', '')
                        close_time = h.get('close_time', '') or h.get('to', '')
                        if open_time and close_time:
                            time_val = f'{open_time} - {close_time}'
                elif isinstance(h, str):
                    days = h
                    time_val = ''
                else:
                    continue

                items.append(f'''<li class="flex justify-between items-center pb-4 border-b border-white/10">
                    <span class="text-lg">{days}</span>
                    <span class="font-bold" style="color:{primary_color}">{time_val}</span>
                </li>''')

            html = html.replace('{{operating_hours_html}}', '\n'.join(items))
        else:
            html = html.replace('{{operating_hours_html}}',
                '<li class="text-gray-500">Sila hubungi kami untuk waktu operasi</li>')

    # === Other common placeholders ===
    business_name = request_data.get('project_name', '') or request_data.get('business_name', '') or ''
    html = html.replace('{{business_name}}', business_name)
    html = html.replace('{{tagline}}', request_data.get('tagline', '') or '')
    html = html.replace('{{email}}', request_data.get('email', '') or '')

    # === SAFETY NET: Remove ANY remaining {{placeholders}} ===
    html = re.sub(r'\{\{[a-zA-Z_]+\}\}', '', html)

    return html


@app.post("/api/publish")
async def publish_website(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Publish website to subdomain.

    This endpoint:
    1. Creates/updates website record in database (CRITICAL for dashboard visibility)
    2. Uploads HTML to Supabase Storage for serving
    3. Optionally sets up delivery system (menu, zones, settings)

    The database record MUST be created for the website to appear in user's dashboard.
    """

    logger.info("📤 PUBLISH REQUEST RECEIVED")

    # Get Supabase credentials from environment
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        ""
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Supabase credentials not configured!")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Storage not configured. Check SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
            }
        )

    try:
        body = await request.json()
        logger.info(f"📤 Request body keys: {list(body.keys())}")
    except Exception as e:
        logger.error(f"❌ Failed to parse request: {e}")
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid JSON"})

    # Extract data (support multiple field names)
    html_content = body.get("html_content") or body.get("html_code") or body.get("html") or ""
    subdomain = (body.get("subdomain") or "").lower().strip()
    project_name = body.get("project_name") or body.get("name") or subdomain
    website_id = body.get("website_id")  # Optional: caller can provide stable UUID
    user_id = current_user.get("sub") or current_user.get("id")
    features = body.get("features") or {}
    delivery = body.get("delivery") or None
    menu_items_payload = body.get("menu_items") or []

    logger.info(f"📤 Subdomain: {subdomain}, Name: {project_name}")
    logger.info(f"📤 HTML length: {len(html_content)} chars")

    if not user_id:
        return JSONResponse(status_code=401, content={"success": False, "error": "Unauthorized"})

    # Validate inputs
    if not html_content:
        return JSONResponse(status_code=400, content={"success": False, "error": "No HTML content provided"})

    if not subdomain:
        return JSONResponse(status_code=400, content={"success": False, "error": "No subdomain provided"})

    # Clean subdomain (only lowercase letters, numbers, hyphens)
    subdomain = re.sub(r'[^a-z0-9-]', '', subdomain)
    if len(subdomain) < 2:
        return JSONResponse(status_code=400, content={"success": False, "error": "Subdomain too short (min 2 chars)"})

    try:
        # Ensure we have a stable website UUID for delivery widget + DB rows
        if not website_id:
            website_id = str(uuid.uuid4())

        # Prevent ID collisions across users
        if supabase:
            existing = supabase.table("websites").select("id, user_id").eq("id", website_id).limit(1).execute()
            if existing.data:
                existing_owner = existing.data[0].get("user_id")
                if existing_owner and existing_owner != user_id:
                    return JSONResponse(
                        status_code=403,
                        content={"success": False, "error": "Website ID belongs to another user"}
                    )

        # Ensure HTML uses the database record website_id
        html_content = fix_website_id_in_html(html_content, website_id)

        # REPLACE PLACEHOLDERS WITH ACTUAL USER DATA
        html_content = replace_template_placeholders(html_content, body)
        logger.info(f"📤 HTML after placeholder replacement: {len(html_content)} chars")

        delivery_enabled = bool(features.get("deliverySystem")) or bool(delivery)

        # CRITICAL FIX: ALWAYS create database record BEFORE storage upload
        # Without this, websites appear in storage but NOT in dashboard
        # Previously, DB record was only created when delivery_enabled=True
        published_url = f"https://{subdomain}.binaapp.my"
        if supabase:
            try:
                logger.info(f"💾 Creating database record for website: {website_id}")
                supabase.table("websites").upsert({
                    "id": website_id,
                    "user_id": user_id,
                    "name": project_name,
                    "business_name": project_name,
                    "subdomain": subdomain,
                    "status": "published",
                    "public_url": published_url,
                    "html_content": html_content,
                    "updated_at": datetime.now().isoformat()
                }, on_conflict="id").execute()
                logger.info(f"✅ Database record created/updated: {website_id}")
            except Exception as db_err:
                logger.error(f"❌ CRITICAL: Database insert failed: {db_err}")
                # Don't continue - if DB fails, the website will be orphaned
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": f"Failed to save website record: {str(db_err)}. Please try again."
                    }
                )

        # If delivery enabled, inject widget and persist minimal menu/zones/settings (service role bypasses RLS).
        if delivery_enabled and supabase:
            try:
                api_base = "https://binaapp-backend.onrender.com"
                widget_src = f"{api_base}/widgets/delivery-widget.js"
                widget_init = f"""
<!-- BinaApp Delivery Widget -->
<script
  src="{widget_src}"
  data-website-id="{website_id}"
  data-api-url="{api_base}"
  data-primary-color="#ea580c"
  data-language="ms"
></script>
<div id="binaapp-widget"></div>
"""
                if "</body>" in html_content:
                    html_content = html_content.replace("</body>", widget_init + "\n</body>")
                else:
                    html_content += widget_init

                # Update HTML content with widget
                supabase.table("websites").update({
                    "html_content": html_content,
                    "updated_at": datetime.now().isoformat()
                }).eq("id", website_id).execute()

                # Create a default category if none exists
                cat_resp = supabase.table("menu_categories").select("id").eq("website_id", website_id).limit(1).execute()
                if cat_resp.data:
                    category_id = cat_resp.data[0]["id"]
                else:
                    cat_insert = supabase.table("menu_categories").insert({
                        "website_id": website_id,
                        "name": "Menu",
                        "name_en": "Menu",
                        "icon": "🍽️",
                        "sort_order": 0,
                        "is_active": True
                    }).execute()
                    category_id = cat_insert.data[0]["id"] if cat_insert.data else None

                # Insert menu items (best-effort)
                if menu_items_payload and category_id:
                    items_to_insert = []
                    default_prices = [15, 12, 18, 10, 20, 14, 16, 13]
                    for idx, it in enumerate(menu_items_payload):
                        if not isinstance(it, dict):
                            continue
                        name = it.get("name") or f"Item {idx+1}"
                        img = it.get("image_url") or it.get("url") or None
                        price = it.get("price")
                        if price is None:
                            price = default_prices[idx % len(default_prices)]
                        try:
                            price = float(str(price).replace("RM", "").strip())
                        except Exception:
                            price = float(default_prices[idx % len(default_prices)])
                        items_to_insert.append({
                            "website_id": website_id,
                            "category_id": category_id,
                            "name": name,
                            "description": it.get("description") or "Hidangan istimewa dari dapur kami",
                            "price": price,
                            "image_url": img,
                            "is_available": True,
                            "is_popular": False,
                            "preparation_time": 15,
                            "sort_order": idx
                        })
                    if items_to_insert:
                        supabase.table("menu_items").insert(items_to_insert).execute()

                # Insert a default delivery zone + settings
                if delivery:
                    try:
                        fee_val = delivery.get("fee", 5)
                        if isinstance(fee_val, str):
                            fee_val = float(fee_val.replace("RM", "").strip())
                        minimum_val = delivery.get("minimum", 30)
                        if isinstance(minimum_val, str):
                            minimum_val = float(minimum_val.replace("RM", "").strip())
                    except Exception:
                        fee_val = 5
                        minimum_val = 30

                    zones_existing = supabase.table("delivery_zones").select("id").eq("website_id", website_id).limit(1).execute()
                    if not zones_existing.data:
                        supabase.table("delivery_zones").insert({
                            "website_id": website_id,
                            "zone_name": delivery.get("area") or "Kawasan Delivery",
                            "delivery_fee": float(fee_val),
                            "minimum_order": float(minimum_val),
                            "estimated_time_min": 30,
                            "estimated_time_max": 45,
                            "is_active": True,
                            "sort_order": 0
                        }).execute()

                    # Ensure delivery settings exist
                    supabase.table("delivery_settings").upsert({
                        "website_id": website_id,
                        "minimum_order": float(minimum_val),
                        "whatsapp_number": None,
                        "use_own_riders": True,
                        "updated_at": datetime.now().isoformat()
                    }, on_conflict="website_id").execute()

                logger.info(f"✅ Delivery widget + data prepared for website {website_id}")
            except Exception as delivery_err:
                logger.warning(f"⚠️ Delivery publish enhancements failed (continuing publish): {delivery_err}")

        # Upload HTML to Supabase Storage
        storage_url = f"{SUPABASE_URL}/storage/v1/object/websites/{subdomain}/index.html"
        storage_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "text/html; charset=utf-8",
            "x-upsert": "true"  # Overwrite if exists
        }

        logger.info(f"📤 Uploading to Storage: {subdomain}/index.html")

        async with httpx.AsyncClient(timeout=30.0) as client:
            storage_response = await client.post(
                storage_url,
                headers=storage_headers,
                content=html_content.encode('utf-8')
            )

            if storage_response.status_code in [200, 201]:
                logger.info(f"✅ Published successfully: {subdomain}.binaapp.my")
                return {
                    "success": True,
                    "website_id": website_id,
                    "subdomain": subdomain,
                    "url": f"https://{subdomain}.binaapp.my",
                    "message": "Website published successfully! Visit your site at the URL above.",
                    "status": "live"
                }
            else:
                logger.error(f"❌ Storage upload failed: {storage_response.status_code} - {storage_response.text}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": f"Failed to upload website to storage: {storage_response.text}"
                    }
                )

    except Exception as e:
        logger.error(f"❌ Publish error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Publishing failed: {str(e)}"
            }
        )


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


# ==================== DELIVERY ORDERS & CHAT ENDPOINTS ====================
# These endpoints handle mobile delivery order submission for published websites

class DeliveryOrderRequest(BaseModel):
    """Request model for delivery order - handles mobile browser quirks"""
    website_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_id: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_area: Optional[str] = None
    items: Optional[str] = None  # Can be JSON string or actual list
    notes: Optional[str] = None
    subtotal: Optional[float] = 0
    delivery_fee: Optional[float] = 0
    total_amount: Optional[float] = 0
    payment_method: Optional[str] = "cash"
    delivery_zone_id: Optional[str] = None


class ChatConversationRequest(BaseModel):
    """Request model for chat conversation - handles null values gracefully"""
    website_id: Optional[str] = None
    order_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_id: Optional[str] = None
    initial_message: Optional[str] = None


def generate_customer_id(phone: str) -> str:
    """Generate a customer_id from phone number hash"""
    if not phone:
        return f"cust_{uuid.uuid4().hex[:12]}"
    # Clean phone number and hash it
    phone_clean = re.sub(r'[^\d]', '', str(phone))
    phone_hash = hashlib.md5(phone_clean.encode()).hexdigest()[:12]
    return f"cust_{phone_hash}"


def safe_string(value, default: str = "") -> str:
    """Convert value to string safely, handling None and empty values"""
    if value is None:
        return default
    return str(value).strip()


def safe_float(value, default: float = 0.0) -> float:
    """Convert value to float safely"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


@app.post("/api/delivery/orders")
@app.post("/api/orders")
async def create_delivery_order(request: Request):
    """
    Create a new delivery order - handles mobile browser data format differences

    This endpoint is called by the delivery widget on published websites.
    Mobile browsers may send data differently than desktop, so we handle:
    - null/undefined values converted to empty strings
    - items as JSON string or array
    - numeric values as strings
    """
    logger.info("📦 [Delivery] Creating new order...")

    if not supabase:
        logger.error("❌ [Delivery] Supabase not connected")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Database not connected",
                "error_ms": "Pangkalan data tidak tersambung"
            }
        )

    try:
        # Parse request body
        try:
            body = await request.json()
            logger.info(f"📦 [Delivery] Request body: {list(body.keys())}")
        except Exception as json_error:
            logger.error(f"❌ [Delivery] Invalid JSON: {json_error}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid request format",
                    "error_ms": "Format permintaan tidak sah"
                }
            )

        # Extract and validate required fields with safe conversion
        customer_name = safe_string(body.get("customer_name"))
        customer_phone = safe_string(body.get("customer_phone"))
        delivery_address = safe_string(body.get("delivery_address"))

        # Validate required fields
        missing_fields = []
        if not customer_name:
            missing_fields.append("customer_name (nama)")
        if not customer_phone:
            missing_fields.append("customer_phone (telefon)")
        if not delivery_address:
            missing_fields.append("delivery_address (alamat)")

        if missing_fields:
            logger.warning(f"⚠️ [Delivery] Missing fields: {missing_fields}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}",
                    "error_ms": f"Ruangan yang diperlukan tidak diisi: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields
                }
            )

        # Process items - handle both JSON string and array
        items_raw = body.get("items", [])
        if isinstance(items_raw, str):
            try:
                items = json.loads(items_raw) if items_raw else []
            except json.JSONDecodeError:
                items = []
        else:
            items = items_raw if items_raw else []

        # Generate order number
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # Generate customer_id if not provided
        customer_id = safe_string(body.get("customer_id"))
        if not customer_id:
            customer_id = generate_customer_id(customer_phone)

        # Build order data - only include columns that exist in schema
        # Note: customer_id removed due to PGRST204 schema cache issue
        order_data = {
            "order_number": order_number,
            "website_id": safe_string(body.get("website_id")),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "delivery_address": delivery_address,
            "delivery_area": safe_string(body.get("delivery_area")),
            "items": items if isinstance(items, list) else [],  # JSONB column - pass list directly, not json.dumps
            "notes": safe_string(body.get("notes")),
            "subtotal": safe_float(body.get("subtotal")),
            "delivery_fee": safe_float(body.get("delivery_fee")),
            "total_amount": safe_float(body.get("total_amount")),
            "payment_method": safe_string(body.get("payment_method"), "cash"),
            "status": "pending"
        }

        logger.info(f"📦 [Delivery] Creating order: {order_number}")

        # Insert into database
        result = supabase.table("delivery_orders").insert(order_data).execute()

        if result.data:
            logger.info(f"✅ [Delivery] Order created: {order_number}")

            # Optionally create a chat conversation for this order
            # Skip chat creation to avoid schema cache issues - can be added later
            # try:
            #     chat_data = {
            #         "website_id": order_data["website_id"],
            #         "order_id": order_number,
            #         "customer_name": customer_name,
            #         "customer_phone": customer_phone,
            #         "status": "active"
            #     }
            #     supabase.table("chat_conversations").insert(chat_data).execute()
            #     logger.info(f"✅ [Delivery] Chat conversation created for order: {order_number}")
            # except Exception as chat_error:
            #     logger.warning(f"⚠️ [Delivery] Chat creation failed (non-critical): {chat_error}")

            return {
                "success": True,
                "order_number": order_number,
                "order_id": result.data[0].get("id") if result.data else None,
                "message": "Order created successfully",
                "message_ms": "Pesanan berjaya dibuat"
            }
        else:
            logger.error("❌ [Delivery] No data returned from insert")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Failed to create order",
                    "error_ms": "Gagal membuat pesanan"
                }
            )

    except Exception as e:
        logger.error(f"❌ [Delivery] Error creating order: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Server error: {str(e)}",
                "error_ms": f"Ralat pelayan: {str(e)}"
            }
        )


@app.get("/api/orders/{order_number}")
async def get_order(order_number: str):
    """Get order details by order number"""
    if not supabase:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Database not connected"}
        )

    try:
        result = supabase.table("delivery_orders").select("*").eq("order_number", order_number).execute()

        if result.data:
            return {"success": True, "order": result.data[0]}
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "Order not found",
                    "error_ms": "Pesanan tidak dijumpai"
                }
            )
    except Exception as e:
        logger.error(f"❌ [Delivery] Error getting order: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.put("/api/orders/{order_number}/status")
async def update_order_status(order_number: str, request: Request):
    """Update order status"""
    if not supabase:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Database not connected"}
        )

    try:
        body = await request.json()
        new_status = safe_string(body.get("status"))

        valid_statuses = ["pending", "confirmed", "preparing", "ready", "delivering", "delivered", "cancelled"]
        if new_status not in valid_statuses:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": f"Invalid status. Valid values: {', '.join(valid_statuses)}"
                }
            )

        result = supabase.table("delivery_orders").update({
            "status": new_status,
            "updated_at": datetime.now().isoformat()
        }).eq("order_number", order_number).execute()

        if result.data:
            return {"success": True, "order": result.data[0]}
        else:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Order not found"}
            )
    except Exception as e:
        logger.error(f"❌ [Delivery] Error updating order status: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/chat/conversations")
async def create_chat_conversation(request: Request):
    """
    Create a new chat conversation - handles mobile browser data format differences

    This endpoint auto-generates customer_id from phone if not provided,
    preventing the "customer_id column not found" error.
    """
    logger.info("💬 [Chat] Creating new conversation...")

    if not supabase:
        logger.error("❌ [Chat] Supabase not connected")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Database not connected",
                "error_ms": "Pangkalan data tidak tersambung"
            }
        )

    try:
        # Parse request body
        try:
            body = await request.json()
            logger.info(f"💬 [Chat] Request body keys: {list(body.keys())}")
        except Exception as json_error:
            logger.error(f"❌ [Chat] Invalid JSON: {json_error}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid request format",
                    "error_ms": "Format permintaan tidak sah"
                }
            )

        # Extract fields with safe conversion
        customer_name = safe_string(body.get("customer_name"))
        customer_phone = safe_string(body.get("customer_phone"))

        # Validate required fields
        if not customer_name:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Customer name is required",
                    "error_ms": "Nama pelanggan diperlukan"
                }
            )

        if not customer_phone:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Customer phone is required",
                    "error_ms": "Nombor telefon pelanggan diperlukan"
                }
            )

        # Generate customer_id if not provided (THIS IS THE FIX)
        customer_id = safe_string(body.get("customer_id"))
        if not customer_id:
            customer_id = generate_customer_id(customer_phone)
            logger.info(f"💬 [Chat] Generated customer_id: {customer_id}")

        # Build conversation data
        conversation_data = {
            "website_id": safe_string(body.get("website_id")),
            "order_id": safe_string(body.get("order_id")),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_id": customer_id,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Insert conversation
        result = supabase.table("chat_conversations").insert(conversation_data).execute()

        if result.data:
            conversation_id = result.data[0].get("id")
            logger.info(f"✅ [Chat] Conversation created: {conversation_id}")

            # If there's an initial message, add it
            initial_message = safe_string(body.get("initial_message"))
            if initial_message:
                message_data = {
                    "conversation_id": conversation_id,
                    "sender_type": "customer",
                    "sender_id": customer_id,
                    "message_text": initial_message,
                    "content": initial_message,
                    "created_at": datetime.now().isoformat()
                }
                supabase.table("chat_messages").insert(message_data).execute()
                logger.info(f"✅ [Chat] Initial message added")

            return {
                "success": True,
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "message": "Conversation created successfully",
                "message_ms": "Perbualan berjaya dibuat"
            }
        else:
            logger.error("❌ [Chat] No data returned from insert")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Failed to create conversation",
                    "error_ms": "Gagal membuat perbualan"
                }
            )

    except Exception as e:
        logger.error(f"❌ [Chat] Failed to create conversation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Server error: {str(e)}",
                "error_ms": f"Ralat pelayan: {str(e)}"
            }
        )


@app.get("/api/chat/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation with messages"""
    if not supabase:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Database not connected"}
        )

    try:
        # Get conversation
        conv_result = supabase.table("chat_conversations").select("*").eq("id", conversation_id).execute()

        if not conv_result.data:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Conversation not found"}
            )

        # Get messages
        msg_result = supabase.table("chat_messages").select(
            "id, conversation_id, message_text, sender_type, message_type, media_url, metadata, is_read, created_at"
        ).eq("conversation_id", conversation_id).order("created_at").execute()

        messages = msg_result.data or []
        for msg in messages:
            if not msg.get("message_text"):
                msg["message_text"] = msg.get("message") or msg.get("content") or ""
            if not msg.get("content"):
                msg["content"] = msg.get("message_text") or msg.get("message") or ""

        return {
            "success": True,
            "conversation": conv_result.data[0],
            "messages": messages
        }
    except Exception as e:
        logger.error(f"❌ [Chat] Error getting conversation: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/chat/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: Request):
    """Send a message in a conversation"""
    if not supabase:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Database not connected"}
        )

    try:
        body = await request.json()
        message_text = safe_string(body.get("message_text") or body.get("message") or body.get("content"))
        sender_type = safe_string(body.get("sender_type"), "customer")
        sender_id = safe_string(body.get("sender_id"))

        if not message_text:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Message is required"}
            )

        message_data = {
            "conversation_id": conversation_id,
            "sender_type": sender_type,
            "sender_id": sender_id,
            "message_text": message_text,
            "content": message_text,
            "created_at": datetime.now().isoformat()
        }

        result = supabase.table("chat_messages").insert(message_data).execute()

        # Update conversation timestamp
        supabase.table("chat_conversations").update({
            "updated_at": datetime.now().isoformat()
        }).eq("id", conversation_id).execute()

        if result.data:
            return {"success": True, "message": result.data[0]}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Failed to send message"}
            )
    except Exception as e:
        logger.error(f"❌ [Chat] Error sending message: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/chat/website/{website_id}/conversations")
async def list_website_conversations(website_id: str):
    """List all conversations for a website"""
    if not supabase:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Database not connected"}
        )

    try:
        result = supabase.table("chat_conversations").select("*").eq("website_id", website_id).order("updated_at", desc=True).execute()

        return {
            "success": True,
            "conversations": result.data or []
        }
    except Exception as e:
        logger.error(f"❌ [Chat] Error listing conversations: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ==================== ADMIN/DEBUG ENDPOINT ====================

@app.get("/api/admin/migration-sql")
async def get_migration_sql():
    """Return SQL to create required tables (for manual execution in Supabase)"""
    return {
        "info": "Run this SQL in your Supabase SQL Editor to create the required tables",
        "note": "After running, go to Settings -> API -> Reload Schema",
        "sql": """
-- Create delivery_orders table
CREATE TABLE IF NOT EXISTS public.delivery_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number TEXT UNIQUE NOT NULL,
    website_id TEXT,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_id TEXT,
    delivery_address TEXT NOT NULL,
    delivery_area TEXT,
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes TEXT,
    subtotal DECIMAL(10, 2) DEFAULT 0,
    delivery_fee DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    payment_method TEXT DEFAULT 'cash',
    delivery_zone_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create chat_conversations table
CREATE TABLE IF NOT EXISTS public.chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    website_id TEXT,
    order_id TEXT,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create chat_messages table
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES public.chat_conversations(id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL,
    sender_id TEXT,
    sender_name TEXT,
    message_type TEXT DEFAULT 'text',
    content TEXT,
    message_text TEXT NOT NULL DEFAULT '',
    media_url TEXT,
    metadata JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS with permissive policies
ALTER TABLE public.delivery_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all delivery_orders" ON public.delivery_orders FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all chat_conversations" ON public.chat_conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all chat_messages" ON public.chat_messages FOR ALL USING (true) WITH CHECK (true);
"""
    }


# ==================== AI-POWERED HTML EDITOR ENDPOINT ====================

@app.post("/api/edit-html")
async def edit_html(request: Request):
    """AI-powered HTML editing using DeepSeek"""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ Invalid JSON: {e}")
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid JSON"})

    html = body.get("html", "")
    instruction = body.get("instruction", "")

    logger.info("=" * 50)
    logger.info(f"🤖 AI EDIT REQUEST")
    logger.info(f"   Instruction: {instruction}")
    logger.info(f"   HTML length: {len(html)} chars")
    logger.info("=" * 50)

    if not instruction:
        return {"error": "Missing data", "success": False}

    # Provide default template if HTML is empty
    if not html:
        html = """<!DOCTYPE html>
<html lang="ms">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Laman Web Saya</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
  </style>
</head>
<body>
  <h1>Selamat Datang</h1>
  <p>Ini adalah laman web anda.</p>
</body>
</html>"""
        logger.info("🤖 Using default HTML template")

    # Truncate HTML if too long (DeepSeek supports 64K+ context)
    MAX_HTML = 150000
    if len(html) > MAX_HTML:
        logger.warning(f"🤖 Truncating HTML from {len(html)} to {MAX_HTML}")
        html = html[:MAX_HTML]

    prompt = f"""Edit this HTML based on the instruction. Output ONLY the modified HTML, nothing else.

INSTRUCTION: {instruction}

MALAY WORDS:
- Tukar = Change
- Tambah = Add
- Buang/Padam = Remove/Delete
- Warna = Color
- Tajuk = Title
- Harga = Price
- Telefon = Phone
- Alamat = Address
- Gambar = Image

HTML TO EDIT:
{html}

OUTPUT THE COMPLETE MODIFIED HTML:"""

    # Use DeepSeek
    try:
        api_key = os.getenv("DEEPSEEK_API_KEY")

        if not api_key:
            logger.error("🔷 No DEEPSEEK_API_KEY!")
            return {"error": "No API key", "success": False}

        logger.info("🔷 Calling DeepSeek...")

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 8192,
                    "temperature": 0.3
                }
            )

            logger.info(f"🔷 Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"🔷 Got response: {len(content)} chars")

                # Extract HTML from response
                html_result = extract_html(content)

                if html_result and len(html_result) > 100:
                    logger.info("🔷 ✅ SUCCESS!")
                    return {"html": html_result, "success": True}
                else:
                    logger.error("🔷 HTML extraction failed")
                    logger.error(f"🔷 Raw content preview: {content[:300]}")
                    return {"error": "Failed to extract HTML", "success": False}
            else:
                logger.error(f"🔷 API Error: {response.status_code}")
                logger.error(f"🔷 Response: {response.text[:300]}")
                return {"error": "API error", "success": False}

    except httpx.TimeoutException:
        logger.error("🔷 TIMEOUT!")
        return {"error": "Timeout - cuba lagi", "success": False}
    except Exception as e:
        logger.error(f"🔷 Exception: {type(e).__name__}: {e}")
        return {"error": "Gagal. Cuba lagi.", "success": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
