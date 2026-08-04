"""
Subdomain Middleware - Routes requests to user websites based on subdomain
Handles: sitename.binaapp.my -> serves user's published website

Includes subscription lock check - locked websites show "Website Tidak Aktif" page

CRITICAL: This middleware has an outermost try/except so that ANY unhandled
exception falls through to call_next() instead of killing the ASGI connection
(which causes Render to return 502 Bad Gateway).
"""

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
import httpx
from loguru import logger
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from app.core.config import settings
from app.services.plan_features import can_publish_subdomain


# Load locked page template once at startup
_LOCKED_PAGE_TEMPLATE = None
_UPGRADE_PAGE_TEMPLATE = None


# =============================================================================
# In-process TTL cache for the subdomain serving path (perf audit follow-up).
#
# SCOPE — deliberately narrow: only two things are cached, both immutable-ish
# within a minute:
#   1. the subdomain -> (website_id, user_id) DB lookup
#   2. the raw published HTML fetched from Supabase Storage (pre-injection)
#
# The SUBSCRIPTION LOCK check and the PLAN (can_publish_subdomain) check are
# NOT cached — they run on every request. Lock state is a billing-integrity
# feature: a locked/expired site must never keep serving because of a cache.
#
# Only positive results are cached (never "not found"), so a just-published
# site becomes visible immediately. Staleness of served HTML is bounded at
# TTL (60s), consistent with the existing Cache-Control: max-age=300 header.
# =============================================================================
_SUBDOMAIN_CACHE_TTL_SECONDS = 60.0
_SUBDOMAIN_CACHE_MAX_ENTRIES = 512

# key: subdomain -> (stored_at_monotonic, value)
_website_lookup_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_storage_html_cache: Dict[str, Tuple[float, str]] = {}


def _cache_get(cache: Dict[str, Tuple[float, Any]], key: str) -> Optional[Any]:
    entry = cache.get(key)
    if entry is None:
        return None
    stored_at, value = entry
    if (time.monotonic() - stored_at) >= _SUBDOMAIN_CACHE_TTL_SECONDS:
        cache.pop(key, None)
        return None
    return value


def _cache_set(cache: Dict[str, Tuple[float, Any]], key: str, value: Any) -> None:
    if len(cache) >= _SUBDOMAIN_CACHE_MAX_ENTRIES:
        # Evict expired entries first; if still full, drop the oldest.
        now = time.monotonic()
        for k in [k for k, (t, _) in cache.items() if now - t >= _SUBDOMAIN_CACHE_TTL_SECONDS]:
            cache.pop(k, None)
        while len(cache) >= _SUBDOMAIN_CACHE_MAX_ENTRIES:
            cache.pop(next(iter(cache)), None)
    cache[key] = (time.monotonic(), value)


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
    # Serve from the in-process cache when fresh (positive results only)
    cached_html = _cache_get(_storage_html_cache, subdomain)
    if cached_html is not None:
        return cached_html

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
                _cache_set(_storage_html_cache, subdomain, response.text)
                return response.text

            # Try legacy path (demo-user/{subdomain}/index.html)
            legacy_url = f"{supabase_url}/storage/v1/object/public/{bucket}/demo-user/{subdomain}/index.html"
            response = await client.get(legacy_url)

            if response.status_code == 200:
                logger.info(f"Fetched HTML from legacy storage: demo-user/{subdomain}/index.html")
                _cache_set(_storage_html_cache, subdomain, response.text)
                return response.text

    except Exception as e:
        logger.error(f"Error fetching HTML from storage for {subdomain}: {e}")

    return None


def _build_published_url(subdomain: str) -> str:
    """The site's real published URL — what the QR code must encode.

    Uses the subdomain host on the main domain. Never the generation-time
    preview URL (preview.binaapp.my) that gets baked into stored HTML.
    """
    return f"https://{subdomain}.{settings.MAIN_DOMAIN}"


# Paths a crawler asks for before it asks for anything else. Served from the
# page we already have rather than 404'd into the SPA.
SEO_FILE_PATHS = ("/robots.txt", "/sitemap.xml")

# The Open Graph image for the site, rendered offline from the merchant's own
# name/palette/description (services/share_card.py). Public by design: the
# WhatsApp/Facebook/Telegram crawlers that unfurl a shared link fetch it
# anonymously, so it must live on the subdomain host, not behind auth.
SHARE_CARD_PATH = "/share-card.png"

# key: subdomain -> (stored_at_monotonic, png_bytes). Same TTL discipline as
# the HTML cache above; the card only changes when the page's palette or
# name does, so 60s staleness is invisible.
_share_card_cache: Dict[str, Tuple[float, bytes]] = {}


def _share_card_response(subdomain: str, business_name: str, html: str):
    """The site's og:image as a PNG response, or a plain 404.

    Every input comes from data already fetched on this request path — no
    extra DB or storage round trip. A render failure (Pillow missing) is a
    404: crawlers treat that as "no preview image", which is exactly the
    pre-feature behaviour.
    """
    png = _cache_get(_share_card_cache, subdomain)
    if png is None:
        try:
            from app.services.promo_kit import extract_tagline
            from app.services.share_card import render_share_card
            from app.services.theme_patcher import detect_palette

            png = render_share_card(
                business_name or subdomain.replace("-", " ").title(),
                _build_published_url(subdomain),
                detect_palette(html),
                extract_tagline(html),
            )
        except Exception as exc:
            logger.error(f"[Subdomain] Share card render failed for {subdomain}: {exc}")
            png = b""
        if png:
            _cache_set(_share_card_cache, subdomain, png)

    if not png:
        return Response(status_code=404)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


_SHARE_CARD_META_MARKER = "<!-- BinaApp Share Card Meta -->"


def _inject_social_meta(html_content: str, subdomain: str) -> str:
    """Point og:image / twitter:image at the served share card.

    Only when the page does not already carry an og:image of its own — a
    generation-time hero image is the merchant's real photo and must win.
    Idempotent: any previously-injected block is stripped first, so a cached
    page re-served through here never stacks meta tags.
    """
    if not subdomain or "</head>" not in html_content:
        return html_content

    html_content = re.sub(
        rf"{re.escape(_SHARE_CARD_META_MARKER)}.*?{re.escape(_SHARE_CARD_META_MARKER)}\n?",
        "",
        html_content,
        flags=re.DOTALL,
    )

    if re.search(r"""<meta\s[^>]*property\s*=\s*["']og:image["']""", html_content):
        return html_content

    card_url = f"{_build_published_url(subdomain)}{SHARE_CARD_PATH}"
    block = (
        f"{_SHARE_CARD_META_MARKER}\n"
        f'<meta property="og:image" content="{card_url}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="630">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:image" content="{card_url}">\n'
        f"{_SHARE_CARD_META_MARKER}\n"
    )
    return html_content.replace("</head>", block + "</head>", 1)


def _seo_file_response(path: str, subdomain: str, html: str = "", indexable: bool = True):
    """robots.txt / sitemap.xml for a subdomain. See services/site_seo_files.py.

    `indexable=False` (locked site, plan downgrade) emits a full disallow and
    an empty sitemap so a temporary error page can never get indexed.
    """
    from app.services.site_seo_files import build_robots_txt, build_sitemap_xml

    site_url = _build_published_url(subdomain)
    headers = {"Cache-Control": "public, max-age=3600"}

    if path == "/robots.txt":
        return PlainTextResponse(
            content=build_robots_txt(site_url, allow_indexing=indexable),
            headers=headers,
        )

    if indexable:
        body = build_sitemap_xml(site_url, html)
    else:
        # A locked/downgraded site advertises nothing at all.
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>\n'
        )
    return Response(content=body, media_type="application/xml", headers=headers)


def _inject_qr_block(html_content: str, subdomain: str, language: str = "ms") -> str:
    """
    Replace the generation-baked "Scan to Visit" QR block with a corrected one.

    Fixes five defects in the baked block (see design-defects goal, P0 #2):
      1. It sat as an orphan strip AFTER </footer> → move it INSIDE the footer.
      2. It was left-aligned (Tailwind preflight sets img{display:block}, so a
         wrapper text-align:center did nothing) → center via the <img> itself
         with margin:0 auto;display:block.
      3. It was in English → localise to the site language.
      4. It encoded preview.binaapp.my → encode the REAL published URL.
      5. It loaded the QR image from api.qrserver.com, putting a third party on
         the render path of every merchant's page (and handing that host every
         visitor's IP). The code is now rendered OFFLINE and inlined as a data
         URI — no external request, no dependency, and crisp when printed.

    Idempotent-ish: strips any prior baked QR block first, so re-serving a
    cached page never stacks two QR blocks.
    """
    if not subdomain:
        return html_content

    # Strip the generation-baked block (templates.inject_qr_code marker) and any
    # previously-injected block from this function.
    html_content = re.sub(
        r'<!-- QR Code Section -->\s*<div\b.*?</div>',
        '', html_content, flags=re.DOTALL
    )
    html_content = re.sub(
        r'<!-- BinaApp QR Block -->\s*<div\b.*?</div>',
        '', html_content, flags=re.DOTALL
    )

    published_url = _build_published_url(subdomain)
    from app.services.qr_service import qr_data_uri, remote_qr_url

    # Offline render first; the remote renderer stays only as a safety net so a
    # missing encoder degrades to the old behaviour instead of a broken image.
    qr_src = qr_data_uri(published_url, scale=6, border=2, dark="#111827")
    if not qr_src:
        qr_src = remote_qr_url(published_url, size=200)

    label = "📱 Imbas untuk Lawat" if language == "ms" else "📱 Scan to Visit"

    # color:inherit so the block adopts the (usually dark) footer's text colour
    # instead of a hardcoded near-black that would vanish on a dark background.
    qr_block = f'''
<!-- BinaApp QR Block -->
<div style="text-align:center;padding:32px 20px;">
  <p style="font-size:1.1rem;font-weight:600;margin:0 0 1rem;color:inherit;">{label}</p>
  <img src="{qr_src}" alt="{label}" width="200" height="200"
       style="margin:0 auto;display:block;width:200px;height:200px;background:#fff;padding:8px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.15);">
</div>
'''

    # Inject INSIDE the footer (before its closing tag) so it never orphans
    # after </footer>. Fall back to before </body> when there's no footer.
    if "</footer>" in html_content:
        html_content = html_content.replace("</footer>", qr_block + "</footer>", 1)
    elif "</body>" in html_content:
        html_content = html_content.replace("</body>", qr_block + "\n</body>", 1)
    else:
        html_content += qr_block

    return html_content


# Inline script injected once per served page. Guards against a blank contact
# card: if the AI-emitted #binaapp-contact-slot never received a widget, drop a
# WhatsApp fallback CTA (using the first wa.me number found on the page) so we
# never lose the conversion surface — or hide the empty card as a last resort.
_CONTACT_SLOT_FALLBACK_SCRIPT = '''
<!-- BinaApp contact-slot fallback -->
<script>
(function(){
  function run(){
    var slot = document.getElementById('binaapp-contact-slot');
    if(!slot) return;
    // Static fallback content (data-binaapp-fallback) is emitted INSIDE the
    // slot by the generator so the page never shows a blank box, even with
    // JS disabled. It must not be mistaken for an injected widget: when a
    // real widget arrives alongside it, drop the fallback; when the slot
    // holds only fallback content, leave it — it is doing its job.
    var fallbacks = slot.querySelectorAll('[data-binaapp-fallback]');
    var realChildren = 0;
    for(var i = 0; i < slot.children.length; i++){
      if(!slot.children[i].hasAttribute('data-binaapp-fallback')) realChildren++;
    }
    if(realChildren > 0){
      for(var j = 0; j < fallbacks.length; j++){
        if(fallbacks[j].parentNode) fallbacks[j].parentNode.removeChild(fallbacks[j]);
      }
      return; // widget injected — fallback cleared
    }
    if(fallbacks.length) return; // static fallback is present and visible
    var waLink = document.querySelector('a[href*="wa.me/"]');
    if(waLink){
      var href = waLink.getAttribute('href');
      var cta = document.createElement('a');
      cta.href = href;
      cta.target = '_blank';
      cta.rel = 'noopener';
      cta.textContent = 'Hubungi Kami di WhatsApp';
      cta.style.cssText = 'display:inline-flex;align-items:center;justify-content:center;gap:8px;background:#25D366;color:#fff;padding:14px 28px;border-radius:999px;text-decoration:none;font-weight:600;font-size:1rem;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
      slot.appendChild(cta);
    } else {
      // Hide the empty contact card — but NEVER a page-level container.
      // When the slot is a direct child of <body> (some generations emit it
      // top-level), slot.closest('[data-aos]') is null and parentElement is
      // <body>: hiding that blanked the ENTIRE page (the ertyu blank-white-
      // page bug). Structural containers are never a "card" — fall back to
      // hiding just the slot itself.
      var card = slot.closest('[data-aos]') || slot.parentElement;
      var isPageContainer = !card
        || card === document.body
        || card === document.documentElement
        || card.tagName === 'MAIN';
      (isPageContainer ? slot : card).style.display = 'none';
    }
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(run, 400); });
  } else {
    setTimeout(run, 400);
  }
})();
</script>
'''


def _inject_widgets(html_content: str, website_id: str, business_type: str = "food", language: str = "ms", subdomain: str = "") -> str:
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

    # TODO(brand): Add brand_primary column to websites table for per-restaurant
    # button color. Until then, fall back to BinaApp orange.
    brand_color = "#E8501F"

    # Only inject the order button if delivery was enabled.
    # TODO(widget): Delete old delivery-widget.js after 30-day rollback window.
    #
    # Button links to the absolute www.{MAIN_DOMAIN} URL: the /order/* flow is a
    # Next.js app served from Vercel on the apex domain. Subdomain hosts (this
    # middleware) only serve stored restaurant HTML, so a relative /order/identify
    # link would be re-intercepted here and serve the homepage again — making the
    # button appear to "do nothing". The ?r=<subdomain> query param carries the
    # restaurant context across the domain hop.
    order_button_html = ""
    if has_delivery:
        order_target = f"https://www.{settings.MAIN_DOMAIN}/order/identify?r={subdomain}"
        order_button_html = f'''
<a href="{order_target}"
   class="binaapp-order-button"
   style="position:fixed;bottom:96px;right:24px;background:{brand_color};color:#fff;padding:14px 24px;border-radius:999px;text-decoration:none;font-family:system-ui,-apple-system,sans-serif;font-weight:500;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:999999;display:inline-flex;align-items:center;gap:8px;">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"></path>
    <path d="M3 6h18"></path>
    <path d="M16 10a4 4 0 0 1-8 0"></path>
  </svg>
  Pesan Delivery
</a>'''

    # The strip above removes any generation-baked chat-widget.js tag (it may
    # carry a stale website_id), so the script MUST be re-injected here or the
    # chat widget never loads on served sites. Chat is not plan-gated — the
    # only gate is the site-level can_publish_subdomain check upstream.
    # EXCEPT when the page carries the inline chat button baked in by
    # inject_ordering_system: that is already a complete chat entry point,
    # and re-injecting chat-widget.js next to it rendered TWO floating chat
    # buttons. One chat entry point per page.
    if "binaapp-inline-chat-btn" in html_content:
        chat_script_html = ""
    else:
        chat_script_html = (
            f'<script src="{settings.BACKEND_URL}/static/widgets/chat-widget.js" '
            f'data-website-id="{website_id}" data-api-url="{settings.BACKEND_URL}" defer></script>'
        )

    widget_injection = f'''
<!-- BinaApp Widgets - Auto-injected with correct website_id -->
<div id="binaapp-widget-container" data-website-id="{website_id}"></div>
<script>window.BINAAPP_WEBSITE_ID = "{website_id}";</script>
{chat_script_html}{order_button_html}
'''

    # Inject before </body> or at end
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", widget_injection + "\n</body>")
    else:
        html_content += widget_injection

    # AOS animation library JS injection
    # Some AI-generated websites load aos.css but not aos.js,
    # causing data-aos elements to stay invisible (opacity:0) forever.
    # The AOS.init call also adds the `aos-initialized` class on <html> which
    # the layout safety CSS below uses to gate its fallback rules.
    if 'aos.css' in html_content.lower() and 'aos.js' not in html_content.lower():
        aos_script = '<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>\n<script>if(typeof AOS!=="undefined"){document.documentElement.classList.add("aos-initialized");AOS.init({once:true,duration:600});}</script>\n'
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', aos_script + '</body>', 1)

    # QR block: replace the generation-baked "Scan to Visit" block (English,
    # left-aligned, encoding preview.binaapp.my, orphaned after </footer>) with
    # a corrected one — centred, localised, inside the footer, encoding the real
    # published URL. Patches already-published sites without republish.
    html_content = _inject_qr_block(html_content, subdomain, language)

    # Contact-slot fallback: if the AI-emitted contact slot renders empty,
    # inject a WhatsApp fallback CTA (or hide the card) so we never show a blank
    # 320px white box. Placed before </body>.
    if 'binaapp-contact-slot' in html_content:
        if '</body>' in html_content:
            html_content = html_content.replace(
                '</body>', _CONTACT_SLOT_FALLBACK_SCRIPT + '\n</body>', 1
            )
        else:
            html_content += _CONTACT_SLOT_FALLBACK_SCRIPT

    # Layout safety guard: inline CSS that survives AOS failures, caps non-hero
    # section heights, equalises menu card heights, and pins the floating
    # WhatsApp button to bottom-right even when surrounding tags are broken.
    # This applies to ALREADY-PUBLISHED sites without requiring republish.
    try:
        from app.services.templates import template_service
        html_content = template_service.apply_layout_safety_guard(html_content)
    except Exception as e:
        logger.warning(f"[Subdomain] Layout safety guard injection failed: {e}")

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

        # /order/* on a subdomain must hop to the Next.js app on www. The order
        # flow is hosted on Vercel under www.{MAIN_DOMAIN}; this middleware only
        # serves stored restaurant HTML. Without this redirect, a click on the
        # injected "Pesan Delivery" button (or any internal /order/* link) would
        # be intercepted here and re-serve the restaurant homepage — visible to
        # the user as "the button did nothing". Carries the subdomain through as
        # ?r=<subdomain> so the Next.js flow can resolve restaurant context.
        path = request.url.path or "/"
        if path.startswith("/order"):
            target = f"https://www.{settings.MAIN_DOMAIN}{path}"
            qs = request.url.query
            if qs:
                target = f"{target}?{qs}&r={subdomain}"
            else:
                target = f"{target}?r={subdomain}"
            logger.info(f"[Subdomain] Redirecting {subdomain}{path} -> {target}")
            return RedirectResponse(url=target, status_code=302)

        # robots.txt / sitemap.xml are answered from the served page further
        # down; this flag lets the lock and plan gates below emit a "crawl
        # nothing" version instead of handing a crawler an error page.
        is_seo_file = path in SEO_FILE_PATHS

        # The og:image the injected meta tags advertise. Locked/gated sites
        # 404 it (below) so a suspended page never unfurls a branded preview.
        is_share_card = path == SHARE_CARD_PATH

        logger.info(f"[Subdomain] Serving: {subdomain}.binaapp.my")

        # STEP 1: Look up website (60s in-process cache; the lookup result is
        # cheap to cache because the id/owner mapping of a subdomain almost
        # never changes — the lock/plan checks below are intentionally NOT
        # cached and run on every request).
        website_id = None
        owner_id = None
        website_name = None
        business_type = "food"
        language = "ms"
        should_try_recovery = False
        supabase = None

        cached_site = _cache_get(_website_lookup_cache, subdomain)
        if cached_site is not None:
            website_id = cached_site["id"]
            owner_id = cached_site.get("user_id")
            website_name = cached_site.get("name")
        else:
            supabase = _get_supabase_client()

            if supabase:
                try:
                    # Only select columns that actually exist in the websites table.
                    # business_type and language do NOT exist as columns.
                    # The Supabase client is sync — run it in the threadpool so
                    # the DB round trip doesn't block the event loop (this
                    # middleware runs on every public pageview).
                    website_result = await run_in_threadpool(
                        supabase.table("websites")
                        .select("id, user_id, name")
                        .eq("subdomain", subdomain)
                        .limit(1)
                        .execute
                    )

                    if website_result.data and len(website_result.data) > 0:
                        website_data = website_result.data[0]
                        website_id = str(website_data["id"])
                        owner_id = website_data.get("user_id")
                        website_name = website_data.get("name")
                        logger.info(f"[Subdomain] Found website_id {website_id} for {subdomain}")
                        # Positive results only — a missing site must stay
                        # uncached so a fresh publish is visible immediately.
                        _cache_set(
                            _website_lookup_cache,
                            subdomain,
                            {"id": website_id, "user_id": owner_id, "name": website_name},
                        )
                    else:
                        logger.warning(f"[Subdomain] Website '{subdomain}' NOT in database")
                        should_try_recovery = True

                except Exception as db_error:
                    logger.error(f"[Subdomain] Database lookup failed for '{subdomain}': {db_error}")
                    # Continue to storage fetch - database being down shouldn't block serving
            else:
                logger.warning("[Subdomain] No Supabase client available, skipping DB lookup")

        if website_id:
            # SUBSCRIPTION LOCK CHECK — REAL-TIME on every request, never
            # cached. Lock state is a billing-integrity feature: a locked or
            # expired site must never stay visible because of a cache.
            if await _check_website_lock(website_id):
                logger.info(f"[Subdomain] Website {subdomain} is locked")
                if is_seo_file:
                    return _seo_file_response(path, subdomain, indexable=False)
                if is_share_card:
                    return Response(status_code=404)
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
            # doesn't include can_publish_subdomain. Fails closed and is
            # REAL-TIME on every request (deliberately not cached).
            if owner_id and not await can_publish_subdomain(owner_id):
                logger.info(f"[Subdomain] Owner {owner_id} cannot publish subdomain — serving upgrade page for {subdomain}")
                if is_seo_file:
                    return _seo_file_response(path, subdomain, indexable=False)
                if is_share_card:
                    return Response(status_code=404)
                return HTMLResponse(
                    content=_get_upgrade_required_html(),
                    status_code=200,
                    headers={
                        "Content-Type": "text/html; charset=utf-8",
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "X-Robots-Tag": "noindex, nofollow"
                    }
                )

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
            # Audit C7: never resurrect a deliberately DELETED site. If a
            # deletion tombstone exists, the surviving HTML is an orphan of an
            # incomplete storage delete — do not mint a ghost DB row from it and
            # do not serve stale content; return 404 as if it were gone.
            try:
                from app.services.storage_service import storage_service
                if await storage_service.tombstone_exists(subdomain):
                    logger.info(f"[Subdomain] '{subdomain}' is tombstoned (deleted) — not auto-recovering")
                    return HTMLResponse(
                        content=_get_not_found_html(subdomain),
                        status_code=404,
                        headers={"Content-Type": "text/html; charset=utf-8"},
                    )
            except Exception as ts_err:
                logger.warning(f"[Subdomain] tombstone check failed for {subdomain}: {ts_err}")

            try:
                import uuid
                from datetime import datetime

                recovery_id = str(uuid.uuid4())
                # Creates orphan row (user_id=NULL). Must only be claimable via
                # simple/publish.py with check_limit enforcement
                # (Phase 3 Mini-Goal 1, issue #656).
                recovery_data = {
                    "id": recovery_id,
                    "subdomain": subdomain,
                    "name": subdomain.replace("-", " ").replace("_", " ").title(),
                    "status": "published",
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }

                await run_in_threadpool(
                    supabase.table("websites").insert(recovery_data).execute
                )
                website_id = recovery_id
                logger.info(f"[Subdomain] Auto-recovered orphan: {subdomain} -> {website_id}")

            except Exception as recovery_error:
                logger.error(f"[Subdomain] Auto-recovery failed for {subdomain}: {recovery_error}")

        # STEP 2.7: robots.txt / sitemap.xml, derived from the page we just
        # fetched — the in-page anchors ARE the structure of a one-pager, so a
        # sitemap can never advertise a section the site does not have.
        if is_seo_file:
            return _seo_file_response(path, subdomain, html=html_content, indexable=True)

        # STEP 2.8: the site's Open Graph image, rendered from the page we
        # just fetched (name, palette, meta description) — nothing extra.
        if is_share_card:
            return _share_card_response(subdomain, website_name, html_content)

        # STEP 3: Inject widgets if we have a website_id
        if website_id:
            html_content = _inject_widgets(html_content, website_id, business_type, language, subdomain)
            logger.info(f"[Subdomain] Injected widgets for {subdomain} (id: {website_id})")

        # STEP 3.5: point og:image / twitter:image at the share card when the
        # page has no preview image of its own — a bare WhatsApp link becomes
        # a branded unfurl. No-op when the page already carries og:image.
        html_content = _inject_social_meta(html_content, subdomain)

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
