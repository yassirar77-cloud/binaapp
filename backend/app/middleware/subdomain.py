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
from app.services.plan_features import can_publish_subdomain


# Load locked page template once at startup
_LOCKED_PAGE_TEMPLATE = None
_UPGRADE_PAGE_TEMPLATE = None


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


def _get_upgrade_required_html() -> str:
    """Load the free-tier upgrade-required template."""
    global _UPGRADE_PAGE_TEMPLATE
    if _UPGRADE_PAGE_TEMPLATE is None:
        template_path = Path(__file__).parent.parent / "templates" / "website_upgrade_required.html"
        try:
            _UPGRADE_PAGE_TEMPLATE = template_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load upgrade-required template: {e}")
            _UPGRADE_PAGE_TEMPLATE = (
                "<!DOCTYPE html><html><head><title>Upgrade Required</title></head>"
                "<body style='font-family:sans-serif;text-align:center;padding:50px;'>"
                "<h1>Upgrade Required</h1>"
                "<p>The owner needs to upgrade to publish this site.</p>"
                "<a href='https://binaapp.my/dashboard/billing'>Upgrade</a>"
                "</body></html>"
            )
    return _UPGRADE_PAGE_TEMPLATE


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
    For delivery-enabled sites, injects a "Pesan Delivery" button that links to
    the new /order/identify flow (replaces the old delivery-widget.js popup).
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

    # Strip the inline old-flow delivery button baked into published HTML by
    # templates.py (id="binaapp-delivery-btn"). Without this, customers would
    # see both the old bottom-left button and the new bottom-right button.
    html_content = re.sub(
        r'<button[^>]*id=["\']binaapp-delivery-btn["\'][^>]*>.*?</button>',
        '', html_content, flags=re.DOTALL
    )

    # Strip dead inline ordering system + empty widget placeholder. The
    # ~1500-line <script> block (templates.py:inject_ordering_system) is
    # unreachable from the new /order/* flow but still loads and spams the
    # console; the empty <div id="binaapp-widget"> is leftover from when
    # delivery-widget.js used to populate it.
    #
    # Does NOT touch <body><div class="delivery-page"> wrapper (would nuke
    # the homepage), the chat widget (separate, always-on by design), or any
    # AI-generated content.
    html_content = re.sub(
        r'<script\b[^>]*>[^<]*?BinaApp Delivery System - Complete Implementation.*?</script>',
        '', html_content, flags=re.DOTALL
    )
    html_content = re.sub(
        r'<div\s+id=["\']binaapp-widget["\'][^>]*>\s*</div>',
        '', html_content
    )

    # TODO(brand): Add brand_primary column to websites table for per-restaurant
    # button color. Until then, fall back to BinaApp orange.
    brand_color = "#E8501F"

    # Only inject the order button if delivery was enabled.
    # TODO(widget): Delete old delivery-widget.js after 30-day rollback window.
    order_button_html = ""
    if has_delivery:
        order_button_html = f'''
<a href="/order/identify"
   class="binaapp-order-button"
   style="position:fixed;bottom:24px;right:24px;background:{brand_color};color:#fff;padding:14px 24px;border-radius:999px;text-decoration:none;font-family:system-ui,-apple-system,sans-serif;font-weight:500;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:9999;display:inline-flex;align-items:center;gap:8px;">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"></path>
    <path d="M3 6h18"></path>
    <path d="M16 10a4 4 0 0 1-8 0"></path>
  </svg>
  Pesan Delivery
</a>'''

    widget_injection = f'''
<!-- BinaApp Widgets - Auto-injected with correct website_id -->
<div id="binaapp-widget-container" data-website-id="{website_id}"></div>
<script>window.BINAAPP_WEBSITE_ID = "{website_id}";</script>{order_button_html}
'''

    # Inject before </body> or at end
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", widget_injection + "\n</body>")
    else:
        html_content += widget_injection

    # AOS animation library JS injection
    # Some AI-generated websites load aos.css but not aos.js,
    # causing data-aos elements to stay invisible (opacity:0) forever.
    if 'aos.css' in html_content.lower() and 'aos.js' not in html_content.lower():
        aos_script = '<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>\n<script>if(typeof AOS!=="undefined"){AOS.init({once:true,duration:600});}</script>\n'
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', aos_script + '</body>', 1)

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
                    owner_id = website_data.get("user_id")
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

                    # FREE-TIER GATE: refuse to serve sites whose owner's plan
                    # doesn't include can_publish_subdomain. Fails closed.
                    # TODO: per-owner LRU cache (60s TTL) deferred until request
                    # metrics show this lookup is hot. One extra REST hop per
                    # subdomain hit is acceptable while traffic is small.
                    if owner_id and not await can_publish_subdomain(owner_id):
                        logger.info(f"[Subdomain] Owner {owner_id} cannot publish subdomain — serving upgrade page for {subdomain}")
                        return HTMLResponse(
                            content=_get_upgrade_required_html(),
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
