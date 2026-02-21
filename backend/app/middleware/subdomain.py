"""
Subdomain Middleware - Routes requests to user websites based on subdomain
Handles: sitename.binaapp.my -> serves user's published website

Includes subscription lock check - locked websites show "Website Tidak Aktif" page

CRITICAL: This middleware has an outermost try/except so that ANY unhandled
exception falls through to call_next() instead of killing the ASGI connection
(which causes Render to return 502 Bad Gateway).
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
import httpx
from loguru import logger
import re
import os
from pathlib import Path
from typing import Optional

from app.core.config import settings


# Load locked page template once at startup
_LOCKED_PAGE_TEMPLATE = None


def _get_locked_page_html() -> str:
    """Load the locked page template"""
    global _LOCKED_PAGE_TEMPLATE
    if _LOCKED_PAGE_TEMPLATE is None:
        template_path = Path(__file__).parent.parent / "templates" / "website_locked.html"
        try:
            _LOCKED_PAGE_TEMPLATE = template_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load locked page template: {e}")
            # Fallback minimal HTML
            _LOCKED_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Tidak Aktif</title>
    <style>
        body { font-family: sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f5f5f5; }
        .container { text-align: center; padding: 40px; background: white; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        p { color: #666; }
        a { color: #3b82f6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Website Tidak Aktif</h1>
        <p>Pemilik website sedang membuat kemas kini langganan.</p>
        <p><a href="https://binaapp.my/login">Log masuk untuk aktifkan</a></p>
    </div>
</body>
</html>
"""
    return _LOCKED_PAGE_TEMPLATE


def _get_not_found_html(subdomain: str) -> str:
    """Return a friendly 404 page for missing websites"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Not Found - BinaApp</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               display: flex; align-items: center; justify-content: center;
               min-height: 100vh; margin: 0;
               background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; }}
        .container {{ text-align: center; padding: 40px; }}
        h1 {{ font-size: 2rem; margin-bottom: 16px; }}
        p {{ color: #94a3b8; margin: 8px 0; }}
        .subdomain {{ color: #60a5fa; font-weight: 600; }}
        a {{ display: inline-block; margin-top: 24px; background: #2563eb;
             color: white; padding: 12px 32px; border-radius: 8px;
             text-decoration: none; font-weight: 600; }}
        a:hover {{ background: #1d4ed8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Website Not Found</h1>
        <p>The website <span class="subdomain">{subdomain}.binaapp.my</span> doesn't exist yet.</p>
        <p>It may have been removed or the URL is incorrect.</p>
        <a href="https://binaapp.my">Create Your Own Website</a>
    </div>
</body>
</html>"""


def _get_error_html() -> str:
    """Return a generic error page (no internal details exposed)"""
    return """<!DOCTYPE html>
<html>
<head><title>Error</title>
<style>
    body { font-family: sans-serif; text-align: center; padding: 50px; }
    h1 { color: #333; }
    p { color: #666; }
    a { color: #3b82f6; }
</style>
</head>
<body>
    <h1>Something went wrong</h1>
    <p>We couldn't load this website. Please try again later.</p>
    <a href="https://binaapp.my">Go to BinaApp</a>
</body>
</html>"""


# Reserved subdomains that should not be treated as user websites
RESERVED_SUBDOMAINS = frozenset([
    "www", "api", "app", "admin", "mail", "ftp", "staging", "dev", "binaapp"
])


async def get_subdomain(request: Request) -> Optional[str]:
    """Extract subdomain from request host, or None if not a subdomain request."""
    try:
        host = request.headers.get("host", "")

        # Get the main domain from settings
        main_domain = settings.MAIN_DOMAIN  # e.g., "binaapp.my"
        suffix = f".{main_domain}"

        # Check if it's a subdomain of our main domain
        if suffix in host:
            # Extract subdomain part
            subdomain = host.split(suffix)[0]
            # Remove port if present
            subdomain = subdomain.replace(":443", "").replace(":80", "").strip().lower()

            # Ignore reserved subdomains
            if subdomain and subdomain not in RESERVED_SUBDOMAINS:
                return subdomain
    except Exception as e:
        logger.error(f"Error extracting subdomain: {e}")

    return None


def _get_supabase_client():
    """
    Get Supabase client, returning None on failure instead of crashing.
    This allows the middleware to fall back to httpx-based storage fetch.
    """
    try:
        from app.core.database import get_supabase
        return get_supabase()
    except Exception as e:
        logger.warning(f"Could not get Supabase client: {e}")
        return None


async def _check_website_lock(website_id: str) -> bool:
    """Check if a website is locked due to subscription. Fails open (returns False)."""
    try:
        from app.services.website_lock_checker import is_website_locked
        return await is_website_locked(website_id)
    except Exception as e:
        logger.error(f"Error checking website lock status: {e}")
        return False


async def _fetch_html_from_storage(subdomain: str) -> Optional[str]:
    """
    Fetch website HTML from Supabase Storage via public URL.
    Tries the subdomain path first, then legacy demo-user path.
    Returns HTML string or None if not found.
    """
    supabase_url = settings.SUPABASE_URL
    bucket = settings.STORAGE_BUCKET_NAME

    if not supabase_url:
        logger.error("SUPABASE_URL not configured - cannot fetch website from storage")
        return None

    # Try subdomain path first (new structure)
    storage_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{subdomain}/index.html"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(storage_url)

            if response.status_code == 200:
                logger.info(f"Fetched HTML from storage: {subdomain}/index.html")
                return response.text

            # Try legacy path (demo-user/{subdomain}/index.html)
            legacy_url = f"{supabase_url}/storage/v1/object/public/{bucket}/demo-user/{subdomain}/index.html"
            response = await client.get(legacy_url)

            if response.status_code == 200:
                logger.info(f"Fetched HTML from legacy storage: demo-user/{subdomain}/index.html")
                return response.text

    except Exception as e:
        logger.error(f"Error fetching HTML from storage for {subdomain}: {e}")

    return None


def _inject_widgets(html_content: str, website_id: str, business_type: str = "food", language: str = "ms") -> str:
    """
    Remove old widget scripts and inject correct ones with the proper website_id.
    Only re-injects delivery widget if delivery was enabled during generation.
    Always injects chat widget (available for ALL tiers).
    """
    # Detect if delivery was enabled BEFORE stripping widget scripts.
    # These markers come from inject_ordering_system / inject_delivery_section
    # and survive the script stripping below.
    delivery_markers = [
        "binaapp-delivery-btn",   # Inline delivery button
        "showDeliveryPage",       # Delivery page JS function
        "deliveryMenuData",       # Inline ordering system JS variable
        "deliveryCart",           # Inline ordering system JS variable
        "Delivery Button - BinaApp",  # HTML comment from injection
    ]
    # Also check for delivery-widget.js before we strip it
    has_delivery = (
        "delivery-widget.js" in html_content
        or any(marker in html_content for marker in delivery_markers)
    )

    # Remove any existing widget scripts (they might have wrong website_id)
    html_content = re.sub(
        r'<script[^>]*delivery-widget\.js[^>]*>.*?</script>', '', html_content, flags=re.DOTALL
    )
    html_content = re.sub(
        r'<script[^>]*chat-widget\.js[^>]*>.*?</script>', '', html_content, flags=re.DOTALL
    )
    html_content = re.sub(
        r'<div[^>]*binaapp-widget-container[^>]*>.*?</div>', '', html_content, flags=re.DOTALL
    )
    html_content = re.sub(
        r'<script>window\.BINAAPP_WEBSITE_ID\s*=\s*["\'][^"\']*["\'];?</script>', '',
        html_content, flags=re.DOTALL
    )

    # Always inject chat-widget.js - chat is available for ALL tiers
    chat_widget_script = f'''
<script src="https://binaapp-backend.onrender.com/static/widgets/chat-widget.js"
        data-website-id="{website_id}"
        data-api-url="https://binaapp-backend.onrender.com/api/v1"></script>'''

    # Only inject delivery widget if delivery was enabled
    delivery_widget_script = ""
    if has_delivery:
        delivery_widget_script = f'''
<script src="https://binaapp-backend.onrender.com/static/widgets/delivery-widget.js"
        data-website-id="{website_id}"
        data-api-url="https://binaapp-backend.onrender.com/api/v1"
        data-primary-color="#ea580c"
        data-business-type="{business_type}"
        data-language="{language}"></script>'''

    widget_injection = f'''
<!-- BinaApp Widgets - Auto-injected with correct website_id -->
<div id="binaapp-widget-container" data-website-id="{website_id}"></div>
<script>window.BINAAPP_WEBSITE_ID = "{website_id}";</script>{delivery_widget_script}{chat_widget_script}
'''

    # Inject before </body> or at end
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", widget_injection + "\n</body>")
    else:
        html_content += widget_injection

    return html_content


async def subdomain_middleware(request: Request, call_next):
    """
    Middleware to handle subdomain routing for user websites.

    If request comes from sitename.binaapp.my:
    - Look up website in database for metadata and lock status
    - Fetch HTML from Supabase Storage
    - Inject correct widget scripts
    - Return HTML response

    Otherwise, continue to normal API routing.

    CRITICAL: Outermost try/except ensures this middleware NEVER crashes
    the ASGI connection. Any unhandled error falls through to call_next().
    """

    try:
        subdomain = await get_subdomain(request)

        if not subdomain:
            # Not a subdomain request, continue to normal API routing
            return await call_next(request)

        logger.info(f"[Subdomain] Serving: {subdomain}.binaapp.my")

        # STEP 1: Look up website in database
        website_id = None
        business_type = "food"
        language = "ms"
        should_try_recovery = False

        supabase = _get_supabase_client()

        if supabase:
            try:
                # Only select columns that actually exist in the websites table.
                # business_type and language do NOT exist as columns.
                website_result = (
                    supabase.table("websites")
                    .select("id, user_id")
                    .eq("subdomain", subdomain)
                    .limit(1)
                    .execute()
                )

                if website_result.data and len(website_result.data) > 0:
                    website_data = website_result.data[0]
                    website_id = str(website_data["id"])
                    logger.info(f"[Subdomain] Found website_id {website_id} for {subdomain}")

                    # SUBSCRIPTION LOCK CHECK
                    if await _check_website_lock(website_id):
                        logger.info(f"[Subdomain] Website {subdomain} is locked")
                        return HTMLResponse(
                            content=_get_locked_page_html(),
                            status_code=200,
                            headers={
                                "Content-Type": "text/html; charset=utf-8",
                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                "X-Robots-Tag": "noindex, nofollow"
                            }
                        )
                else:
                    logger.warning(f"[Subdomain] Website '{subdomain}' NOT in database")
                    should_try_recovery = True

            except Exception as db_error:
                logger.error(f"[Subdomain] Database lookup failed for '{subdomain}': {db_error}")
                # Continue to storage fetch - database being down shouldn't block serving
        else:
            logger.warning("[Subdomain] No Supabase client available, skipping DB lookup")

        # STEP 2: Fetch HTML from Supabase Storage
        html_content = await _fetch_html_from_storage(subdomain)

        if not html_content:
            logger.warning(f"[Subdomain] Website not found in storage: {subdomain}")
            return HTMLResponse(
                content=_get_not_found_html(subdomain),
                status_code=404,
                headers={"Content-Type": "text/html; charset=utf-8"}
            )

        # STEP 2.5: AUTO-RECOVERY - If HTML exists but no DB record, create one
        if should_try_recovery and not website_id and supabase:
            try:
                import uuid
                from datetime import datetime

                recovery_id = str(uuid.uuid4())
                recovery_data = {
                    "id": recovery_id,
                    "subdomain": subdomain,
                    "name": subdomain.replace("-", " ").replace("_", " ").title(),
                    "status": "published",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }

                supabase.table("websites").insert(recovery_data).execute()
                website_id = recovery_id
                logger.info(f"[Subdomain] Auto-recovered orphan: {subdomain} -> {website_id}")

            except Exception as recovery_error:
                logger.error(f"[Subdomain] Auto-recovery failed for {subdomain}: {recovery_error}")

        # STEP 3: Inject widgets if we have a website_id
        if website_id:
            html_content = _inject_widgets(html_content, website_id, business_type, language)
            logger.info(f"[Subdomain] Injected widgets for {subdomain} (id: {website_id})")

        return HTMLResponse(
            content=html_content,
            status_code=200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "public, max-age=300" if website_id else "public, max-age=3600"
            }
        )

    except Exception as e:
        # CRITICAL: This outermost catch prevents the middleware from crashing
        # the ASGI connection, which would cause Render to return 502.
        logger.error(f"[Subdomain] Middleware crash: {e}")
        import traceback
        traceback.print_exc()

        # Try to return an error page if this was a subdomain request
        try:
            host = request.headers.get("host", "")
            if f".{settings.MAIN_DOMAIN}" in host:
                return HTMLResponse(
                    content=_get_error_html(),
                    status_code=500,
                    headers={"Content-Type": "text/html; charset=utf-8"}
                )
        except Exception:
            pass

        # Fall through to normal routing
        return await call_next(request)
