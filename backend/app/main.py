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
import cloudinary
import cloudinary.uploader
from datetime import datetime, timedelta, date
from collections import defaultdict
from user_agents import parse as parse_user_agent
import hashlib
from supabase import create_client, Client
from urllib.parse import urlparse
import uuid

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

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Initialize Supabase client
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("🗄️ Supabase connected successfully")
    except Exception as e:
        logger.error(f"🗄️ Supabase connection failed: {e}")
        supabase = None
else:
    logger.warning("🗄️ Supabase not configured - analytics will be disabled")

# Rate limiting
user_usage = defaultdict(lambda: {"count": 0, "reset_time": datetime.now()})
FREE_LIMIT = 3  # 3 generations per day


# Request models
class GenerateRequest(BaseModel):
    description: Optional[str] = None
    business_description: Optional[str] = None
    style: Optional[str] = "modern"
    user_id: Optional[str] = None


# Analytics request model
class TrackEventRequest(BaseModel):
    project_id: str
    visitor_id: Optional[str] = None
    referrer: Optional[str] = None
    page_path: Optional[str] = "/"


@app.get("/")
async def root():
    return {"status": "BinaApp Backend Running", "version": "4.0-production"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


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


def check_rate_limit(user_id: str = "anonymous") -> dict:
    """Check if user has exceeded daily limit"""
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
    """Generate hero image"""
    business_type = detect_business_type(desc)
    hero_prompt = f"Modern {business_type.replace('_', ' ')} interior, professional, luxurious, {desc}"
    hero_image = await generate_stability_image(hero_prompt)

    if hero_image:
        return {
            'hero': hero_image,
            'gallery': [hero_image] * 4  # Reuse hero for gallery
        }
    return None


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
    """3-Step AI Pipeline with Cloudinary images"""

    desc = request.business_description or request.description or ""
    user_id = request.user_id or "anonymous"

    if not desc:
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

    logger.info("=" * 70)
    logger.info("🌐 WEBSITE GENERATION - 3-STEP AI PIPELINE")
    logger.info(f"   Business: {desc[:60]}...")
    logger.info(f"   User: {user_id}")
    logger.info("=" * 70)

    try:
        business_type = detect_business_type(desc)
        logger.info(f"📋 Detected: {business_type}")

        stock_images = get_stock_images(desc)

        # STEP 1: Generate AI Images (upload to Cloudinary)
        logger.info("")
        logger.info("🎨 STEP 1: Stability AI + Cloudinary...")
        ai_images = None

        if STABILITY_API_KEY:
            ai_images = await generate_all_images(desc)
            if ai_images:
                logger.info("🎨 STEP 1 - ✅ Complete")

        hero_img = ai_images['hero'] if ai_images else stock_images['hero']
        gallery_imgs = ai_images['gallery'] if ai_images else stock_images['gallery']

        # STEP 2: DeepSeek generates HTML
        logger.info("")
        logger.info("🔷 STEP 2: DeepSeek generating HTML...")

        deepseek_prompt = f"""Create a modern website for: {desc}

Business Type: {business_type}

Use these placeholders:
- [BUSINESS_NAME], [BUSINESS_TAGLINE], [ABOUT_TEXT]
- [SERVICE_1_TITLE], [SERVICE_1_DESC]
- [SERVICE_2_TITLE], [SERVICE_2_DESC]
- [SERVICE_3_TITLE], [SERVICE_3_DESC]
- [CTA_TEXT], [FOOTER_TEXT]

IMAGES:
- Hero: {stock_images['hero']}
- Gallery: {', '.join(stock_images['gallery'][:4])}

Requirements:
1. <script src="https://cdn.tailwindcss.com"></script>
2. Mobile responsive, modern gradients, shadows
3. Sections: Header, Hero, About, Services, Gallery, Contact, Footer
4. WhatsApp button: wa.me/60123456789
5. Smooth animations

Output ONLY complete HTML code."""

        html_structure = await call_deepseek(deepseek_prompt)

        if not html_structure:
            return JSONResponse(status_code=500, content={"success": False, "error": "DeepSeek failed"})

        html_structure = extract_html(html_structure)
        logger.info(f"🔷 STEP 2 - ✅ Complete ({len(html_structure)} chars)")

        # STEP 3: Qwen improves content
        logger.info("")
        logger.info("🟡 STEP 3: Qwen improving content...")

        qwen_prompt = f"""Replace ALL placeholders with Malaysian-friendly content.

Business: {desc}

REPLACE:
- [BUSINESS_NAME] → Business name
- [BUSINESS_TAGLINE] → Catchy tagline
- [ABOUT_TEXT] → About us (2-3 sentences)
- [SERVICE_1_TITLE], [SERVICE_1_DESC] → Service 1
- [SERVICE_2_TITLE], [SERVICE_2_DESC] → Service 2
- [SERVICE_3_TITLE], [SERVICE_3_DESC] → Service 3
- [CTA_TEXT] → Call to action
- [FOOTER_TEXT] → Footer tagline

HTML:
{html_structure}

Output ONLY improved HTML."""

        final_html = await call_qwen(qwen_prompt)

        if final_html:
            final_html = extract_html(final_html)
            logger.info(f"🟡 STEP 3 - ✅ Complete ({len(final_html)} chars)")
        else:
            final_html = html_structure
            logger.warning("🟡 STEP 3 - ⚠️ Using DeepSeek output")

        # STEP 4: Replace stock images with AI/Cloudinary images
        if ai_images:
            logger.info("")
            logger.info("🔄 STEP 4: Replacing images...")
            final_html = final_html.replace(stock_images['hero'], ai_images['hero'])
            for i, stock_url in enumerate(stock_images['gallery']):
                if i < len(ai_images['gallery']):
                    final_html = final_html.replace(stock_url, ai_images['gallery'][i])

        # STEP 5: Generate project ID and inject analytics tracking script
        project_id = str(uuid.uuid4())
        logger.info("")
        logger.info("📊 STEP 5: Injecting analytics tracking...")

        tracking_script = f'''
<!-- BinaApp Analytics -->
<script>
(function() {{
    const PROJECT_ID = '{project_id}';
    const API_URL = 'https://binaapp-backend.onrender.com/api/analytics/track';
    let visitorId = localStorage.getItem('binaapp_visitor');
    if (!visitorId) {{
        visitorId = 'v_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('binaapp_visitor', visitorId);
    }}
    fetch(API_URL, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
            project_id: PROJECT_ID,
            visitor_id: visitorId,
            referrer: document.referrer,
            page_path: window.location.pathname
        }})
    }}).catch(function() {{}});
}})();
</script>
'''

        # Insert before </body>
        if '</body>' in final_html:
            final_html = final_html.replace('</body>', f'{tracking_script}</body>')
            logger.info(f"📊 Analytics tracking injected (Project ID: {project_id[:8]}...)")
        else:
            logger.warning("📊 No </body> tag found, appending tracking script")
            final_html += tracking_script

        # Increment usage
        increment_usage(user_id)

        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ GENERATION COMPLETE!")
        logger.info(f"   Final HTML: {len(final_html)} chars")
        logger.info(f"   Project ID: {project_id}")
        logger.info("=" * 70)

        return {
            "success": True,
            "html": final_html,
            "project_id": project_id,
            "styles": [{"style": "modern", "html": final_html}],
            "usage": check_rate_limit(user_id)
        }

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


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
        project = supabase.table("projects").select("total_views, unique_visitors").eq("id", project_id).single().execute()

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
