"""
Subdomain Middleware - Routes requests to user websites based on subdomain
Handles: sitename.binaapp.my → serves user's published website
"""

from fastapi import Request
from fastapi.responses import HTMLResponse
import httpx
from loguru import logger
import re

from app.core.config import settings
from app.core.database import get_supabase


async def get_subdomain(request: Request) -> str | None:
    """Extract subdomain from request host"""
    host = request.headers.get("host", "")

    # Get the main domain from settings
    main_domain = settings.MAIN_DOMAIN  # e.g., "binaapp.my"

    # Check if it's a subdomain of our main domain
    if f".{main_domain}" in host:
        # Extract subdomain part
        subdomain = host.split(f".{main_domain}")[0]
        # Remove port if present
        subdomain = subdomain.replace(":443", "").replace(":80", "").strip()

        # Ignore reserved subdomains
        reserved = ["www", "api", "app", "admin", "mail", "ftp", "staging", "dev"]
        if subdomain and subdomain not in reserved:
            return subdomain

    return None


async def subdomain_middleware(request: Request, call_next):
    """
    Middleware to handle subdomain routing for user websites.

    If request comes from sitename.binaapp.my:
    - Fetch the user's website HTML from Supabase storage
    - Return it with correct Content-Type

    Otherwise, continue to normal API routing.
    """

    subdomain = await get_subdomain(request)

    if subdomain:
        logger.info(f"Subdomain request detected: {subdomain}")

        try:
            # STEP 1: Get correct website_id from database
            supabase = get_supabase()
            website_result = supabase.table("websites").select("id, business_type, language").eq("subdomain", subdomain).single().execute()

            if not website_result.data:
                logger.warning(f"Website not found in database for subdomain: {subdomain}")
                # Continue to storage check below
                website_id = None
            else:
                website_id = str(website_result.data["id"])
                business_type = website_result.data.get("business_type", "food")
                language = website_result.data.get("language", "ms")
                logger.info(f"Found website_id {website_id} for subdomain {subdomain}")

            # STEP 2: Try to fetch HTML from Supabase storage
            # First try: subdomain/index.html (new structure)
            storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.STORAGE_BUCKET_NAME}/{subdomain}/index.html"

            async with httpx.AsyncClient() as client:
                response = await client.get(storage_url, timeout=10.0)
                html_content = None

                if response.status_code == 200:
                    html_content = response.text
                    logger.info(f"Fetched HTML from storage for subdomain: {subdomain}")
                else:
                    # Second try: search in user folders (legacy structure)
                    legacy_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.STORAGE_BUCKET_NAME}/demo-user/{subdomain}/index.html"
                    response = await client.get(legacy_url, timeout=10.0)

                    if response.status_code == 200:
                        html_content = response.text
                        logger.info(f"Fetched HTML from legacy storage for subdomain: {subdomain}")

                # STEP 3: If we have HTML and website_id, inject correct widget scripts
                if html_content and website_id:
                    # Remove any existing widget scripts (they might have wrong website_id)
                    html_content = re.sub(r'<script[^>]*delivery-widget\.js[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
                    html_content = re.sub(r'<script[^>]*chat-widget\.js[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
                    html_content = re.sub(r'<div[^>]*binaapp-widget-container[^>]*>.*?</div>', '', html_content, flags=re.DOTALL)
                    html_content = re.sub(r'<script>window\.BINAAPP_WEBSITE_ID\s*=\s*["\'][^"\']*["\'];?</script>', '', html_content, flags=re.DOTALL)

                    # Inject correct widget scripts with proper website_id
                    # Only inject chat-widget.js if inline chat button doesn't exist (avoid duplicates)
                    has_inline_chat = "binaapp-inline-chat-btn" in html_content

                    chat_widget_script = "" if has_inline_chat else f'''
<script src="https://binaapp-backend.onrender.com/static/widgets/chat-widget.js"
        data-website-id="{website_id}"
        data-api-url="https://binaapp-backend.onrender.com/api/v1"></script>'''

                    widget_injection = f'''
<!-- BinaApp Widgets - Auto-injected with correct website_id -->
<div id="binaapp-widget-container" data-website-id="{website_id}"></div>
<script>window.BINAAPP_WEBSITE_ID = "{website_id}";</script>
<script src="https://binaapp-backend.onrender.com/static/widgets/delivery-widget.js"
        data-website-id="{website_id}"
        data-api-url="https://binaapp-backend.onrender.com/api/v1"
        data-primary-color="#ea580c"
        data-business-type="{business_type if website_id else 'food'}"
        data-language="{language if website_id else 'ms'}"></script>{chat_widget_script}
'''

                    # Inject before </body> or at end
                    if "</body>" in html_content:
                        html_content = html_content.replace("</body>", widget_injection + "\n</body>")
                    else:
                        html_content += widget_injection

                    logger.info(f"✅ Injected widgets with website_id {website_id} for subdomain {subdomain}")

                    return HTMLResponse(
                        content=html_content,
                        status_code=200,
                        headers={
                            "Content-Type": "text/html; charset=utf-8",
                            "Cache-Control": "public, max-age=300"  # 5 min cache
                        }
                    )
                elif html_content:
                    # Have HTML but no website_id - serve as-is
                    return HTMLResponse(
                        content=html_content,
                        status_code=200,
                        headers={
                            "Content-Type": "text/html; charset=utf-8",
                            "Cache-Control": "public, max-age=3600"
                        }
                    )

                # Website not found - show friendly error page
                logger.warning(f"Website not found for subdomain: {subdomain}")
                error_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Not Found - BinaApp</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Poppins', sans-serif; }}</style>
</head>
<body class="bg-gradient-to-br from-gray-900 to-gray-800 min-h-screen flex items-center justify-center">
    <div class="text-center text-white p-8">
        <div class="text-6xl mb-4">🔍</div>
        <h1 class="text-4xl font-bold mb-4">Website Not Found</h1>
        <p class="text-gray-400 mb-2">The website <span class="text-blue-400 font-semibold">{subdomain}.binaapp.my</span> doesn't exist yet.</p>
        <p class="text-gray-500 mb-8">It may have been removed or the URL is incorrect.</p>
        <a href="https://binaapp.my"
           class="inline-block bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-3 rounded-lg transition-colors">
            Create Your Own Website →
        </a>
        <p class="text-gray-600 text-sm mt-8">Powered by BinaApp - AI Website Builder</p>
    </div>
</body>
</html>
"""
                return HTMLResponse(content=error_html, status_code=404)

        except Exception as e:
            logger.error(f"Error serving subdomain {subdomain}: {e}")
            return HTMLResponse(
                content=f"""
<!DOCTYPE html>
<html>
<head><title>Error</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1>Something went wrong</h1>
    <p>We couldn't load this website. Please try again later.</p>
    <a href="https://binaapp.my">Go to BinaApp</a>
</body>
</html>
""",
                status_code=500
            )

    # Not a subdomain request, continue to normal API routing
    return await call_next(request)
