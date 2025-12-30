"""
Simple Publish Endpoint
POST /api/publish - Publish website to Supabase Storage
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator
from typing import Optional
from loguru import logger
from datetime import datetime
import uuid
import re
import asyncio

from app.services.storage_service import storage_service
from app.services.supabase_client import supabase_service

router = APIRouter()

# Blocked subdomain words - offensive, sensitive, trademarked terms
# IMPORTANT: Include ALL spelling variations to catch attempts to bypass filters
BLOCKED_WORDS = [
    # Malay offensive - with spelling variations
    "bodo", "bodoh", "bodow", "bodo", "bhodoh",  # stupid
    "babi", "bab1", "bbabi", "babii",  # pig
    "sial", "cial", "siol", "syal", "siol",  # damn
    "pukimak", "puki", "kimak", "pkimak", "pukima",  # vulgar
    "lancau", "lanjiao", "lncau", "lancaw",  # vulgar
    "pantat", "pntat", "pantet", "pntet",  # vulgar
    "sundal", "sndal", "sundel", "sndel",  # prostitute
    "jalang", "jlang", "jaláng",  # slut
    "pelacur", "plcur", "pelacor",  # prostitute
    "haram", "harom", "harem", "haraam",  # forbidden (offensive context)
    "celaka", "claka", "celake", "clake",  # cursed
    "bangang", "bangng", "bnggang", "bangang",  # idiot
    "bengap", "bngap", "bengep", "bngep",  # stupid
    "tolol", "tlol", "tol0l", "tolool",  # idiot
    "goblok", "goblog", "gblok", "gobloq",  # stupid
    "anjing", "anjng", "ajg", "anjig", "anying",  # dog (offensive)
    "asu", "assu", "asuw",  # dog
    "mampus", "mampos", "mampuss", "mampoos",  # die
    "taik", "tahi", "taek", "taiek",  # shit
    "palat", "palet", "plat",  # vulgar
    "pukul", "pkul", "pukol",  # hit (violence context)
    "bunuh", "bnuh", "bunoh",  # kill
    "pepek", "ppek", "memek", "mmek",  # vulgar
    "kontol", "kntol", "kontl",  # vulgar

    # English offensive - with leetspeak variations
    "fuck", "fck", "fuk", "f4ck", "fvck", "phuck", "fxck",
    "shit", "sh1t", "sht", "shyt", "shite",
    "ass", "a55", "azz", "arse",
    "bitch", "b1tch", "btch", "biatch", "bytch",
    "dick", "d1ck", "dik", "dck",
    "porn", "p0rn", "pron", "pr0n", "porno",
    "sex", "s3x", "sexx", "s3xx",
    "xxx", "xxxx",
    "nude", "nud3", "nood", "n00d",
    "naked", "nak3d", "nakey",
    "kill", "k1ll", "kil", "kll",
    "murder", "murd3r", "mrder",
    "drug", "drugs", "drg", "drugz", "dadah",
    "gambling", "gambl1ng", "judi", "judii",
    "casino", "cas1no", "kasino", "casin0",
    "scam", "sc4m", "scamm", "sc@m",
    "terrorist", "terror1st", "terrori5t",
    "bomb", "b0mb", "bomm",
    "cocaine", "coke", "c0caine",
    "heroin", "her0in", "hero1n",
    "weed", "w33d", "w3ed",
    "fraud", "fr4ud", "frawd",

    # Religious/Political sensitive (Malaysia)
    "allah", "al1ah", "alloh",
    "nabi", "nab1", "nabii",
    "rasul", "rasool", "rasol",
    "agong", "ag0ng", "aggong",
    "sultan", "sult4n", "sulton",
    "kerajaan", "krajaaan", "kerajaan",

    # Brand/Trademark issues
    "google", "g00gle", "googl", "gogle",
    "facebook", "faceb00k", "fb", "facbook",
    "instagram", "insta", "1nstagram", "instagr4m",
    "tiktok", "t1ktok", "tikt0k", "tik-tok",
    "twitter", "tw1tter", "twiter", "twtr",
    "amazon", "amaz0n", "amazn",
    "apple", "appl", "app1e", "apel",
    "microsoft", "micr0soft", "microsfot",
    "netflix", "netfl1x", "netflex",
    "shopee", "sh0pee", "shope", "shopi",
    "lazada", "laz4da", "lazadaa",
    "grab", "gr4b", "grabb",
    "foodpanda", "f00dpanda", "food-panda",

    # Government/Official
    "gov", "govt", "government", "g0v",
    "kerajaan", "krjaan",
    "polis", "police", "p0lis", "pol1ce",
    "tentera", "army", "milit4ry",
    "kementerian", "ministry", "kemen",
    "jabatan", "department", "dept",
    "official", "0fficial", "ofisial",
    "rasmi", "r4smi", "rasmii",
]


def is_subdomain_allowed(subdomain: str) -> tuple[bool, str]:
    """
    Check if subdomain is allowed based on content policy.
    Catches leetspeak variations and spelling tricks.

    Returns:
        tuple[bool, str]: (is_allowed, error_message)
    """
    subdomain_lower = subdomain.lower().strip()

    # Normalize leetspeak - convert common number/symbol substitutions
    normalized = subdomain_lower
    normalized = normalized.replace("0", "o")
    normalized = normalized.replace("1", "i")
    normalized = normalized.replace("3", "e")
    normalized = normalized.replace("4", "a")
    normalized = normalized.replace("5", "s")
    normalized = normalized.replace("@", "a")
    normalized = normalized.replace("$", "s")
    normalized = normalized.replace("7", "t")
    normalized = normalized.replace("8", "b")

    logger.info("=" * 50)
    logger.info(f"🔒 SUBDOMAIN CHECK: '{subdomain_lower}'")
    if normalized != subdomain_lower:
        logger.info(f"   Normalized: '{normalized}'")
    logger.info("=" * 50)

    # Check minimum length
    if len(subdomain_lower) < 3:
        logger.warning(f"❌ BLOCKED: Too short ({len(subdomain_lower)} chars)")
        return False, "Subdomain mesti sekurang-kurangnya 3 aksara / Minimum 3 characters"

    # Check maximum length
    if len(subdomain_lower) > 30:
        logger.warning(f"❌ BLOCKED: Too long ({len(subdomain_lower)} chars)")
        return False, "Subdomain terlalu panjang / Subdomain too long (max 30 characters)"

    # Check for valid characters only
    if not re.match(r'^[a-z0-9-]+$', subdomain_lower):
        logger.warning(f"❌ BLOCKED: Invalid characters")
        return False, "Hanya huruf kecil, nombor dan (-) dibenarkan / Only lowercase, numbers and hyphens"

    # Check if starts/ends with hyphen
    if subdomain_lower.startswith('-') or subdomain_lower.endswith('-'):
        logger.warning(f"❌ BLOCKED: Starts/ends with hyphen")
        return False, "Tidak boleh bermula/berakhir dengan (-) / Cannot start/end with hyphen"

    # Check blocked words - check both original AND normalized version
    for word in BLOCKED_WORDS:
        # Check if blocked word is IN the subdomain (substring match)
        if word in subdomain_lower or word in normalized:
            logger.warning(f"🚫 BLOCKED: Contains '{word}' (original: '{subdomain_lower}', normalized: '{normalized}')")
            return False, "Nama ini tidak dibenarkan / This name is not allowed"

    logger.info(f"✅ ALLOWED: '{subdomain_lower}'")
    return True, "OK"


class PublishRequest(BaseModel):
    """Publish request - supports multiple field names for HTML content"""
    html_content: Optional[str] = Field(None, description="HTML code to publish")
    html_code: Optional[str] = Field(None, description="HTML code to publish (alternative field)")
    html: Optional[str] = Field(None, description="HTML code to publish (alternative field)")
    subdomain: str = Field(
        ...,
        min_length=3,
        max_length=63,
        description="Chosen subdomain name"
    )
    project_name: str = Field(..., min_length=2, max_length=100, description="Project name")
    user_id: str = Field(default="demo-user", description="User ID")

    @validator('html_content', always=True)
    def set_html_content(cls, v, values):
        """Automatically handle multiple field names for HTML content"""
        if v:
            return v
        if values.get('html_code'):
            return values.get('html_code')
        if values.get('html'):
            return values.get('html')
        return None

    class Config:
        # Allow extra fields without error
        extra = "allow"


class PublishResponse(BaseModel):
    """Publish response"""
    url: str
    subdomain: str
    project_id: str
    success: bool = True


async def retry_with_backoff(func, max_retries=3, initial_delay=1.0):
    """Retry a function with exponential backoff"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed")
    raise last_error


@router.post("/publish", response_model=PublishResponse)
async def publish_website(request: PublishRequest):
    """
    Publish website to Supabase Storage - ROBUST VERSION

    This endpoint:
    - Supports multiple field names (html_content, html_code, html)
    - Uploads HTML to Supabase Storage (bucket: websites)
    - File path: {user_id}/{subdomain}/index.html
    - Saves project metadata to database (creates table if missing)
    - Returns public URL
    - Handles errors with retry logic and reconnection
    """
    try:
        logger.info("=" * 80)
        logger.info(f"🚀 PUBLISH REQUEST RECEIVED")
        logger.info(f"   Project: {request.project_name}")
        logger.info(f"   Subdomain: {request.subdomain}")
        logger.info(f"   User ID: {request.user_id}")
        logger.info("=" * 80)

        # Get HTML content from any of the supported fields
        html_content = request.html_content
        if not html_content:
            logger.error("❌ No HTML content provided in any field (html_content, html_code, html)")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tiada kod HTML ditemui. Sila berikan html_content, html_code, atau html."
            )

        logger.info(f"✓ HTML content received: {len(html_content)} characters")

        # CRITICAL: Check if subdomain is allowed BEFORE anything else
        logger.info("")
        logger.info("🛡️ STEP 1: CONTENT POLICY CHECK")
        logger.info(f"   Checking subdomain: '{request.subdomain}'")

        is_allowed, error_message = is_subdomain_allowed(request.subdomain)

        if not is_allowed:
            logger.error("=" * 80)
            logger.error(f"❌ SUBDOMAIN BLOCKED BY CONTENT POLICY")
            logger.error(f"   Requested subdomain: '{request.subdomain}'")
            logger.error(f"   Reason: {error_message}")
            logger.error("=" * 80)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        logger.info(f"✅ Subdomain passes content policy check: '{request.subdomain}'")

        # Validate subdomain format
        if not validate_subdomain(request.subdomain):
            logger.error(f"❌ Invalid subdomain format: {request.subdomain}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format subdomain tidak sah. Gunakan huruf kecil, nombor, dan tanda sempang sahaja."
            )

        logger.info("✓ Subdomain format valid")

        # Check if subdomain is already taken (with retry)
        async def check_subdomain():
            return await storage_service.check_subdomain_exists(request.subdomain)

        try:
            subdomain_exists = await retry_with_backoff(check_subdomain, max_retries=2)
            if subdomain_exists:
                logger.warning(f"⚠️ Subdomain already taken: {request.subdomain}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Subdomain '{request.subdomain}' sudah digunakan. Sila pilih yang lain."
                )
            logger.info("✓ Subdomain available")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"⚠️ Could not check subdomain availability: {e}")
            # Continue anyway - will fail later if subdomain is actually taken

        # Generate project ID
        project_id = str(uuid.uuid4())
        logger.info(f"✓ Generated project ID: {project_id}")

        # CRITICAL FIX: Inject delivery widget if delivery features are detected
        html_content = inject_delivery_widget_if_needed(
            html_content,
            project_id,
            request.project_name
        )

        # Upload to Supabase Storage with retry logic
        logger.info(f"📤 Uploading to Supabase Storage: {request.user_id}/{request.subdomain}/index.html")

        async def upload_html():
            return await storage_service.upload_website(
                user_id=request.user_id,
                subdomain=request.subdomain,
                html_content=html_content
            )

        try:
            public_url = await retry_with_backoff(upload_html, max_retries=3, initial_delay=2.0)
            if not public_url:
                raise Exception("Upload returned no URL")
            logger.info(f"✅ Upload successful: {public_url}")
        except Exception as e:
            logger.error(f"❌ Failed to upload after retries: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal memuat naik website: {str(e)}"
            )

        # Save project metadata to database with retry
        logger.info("💾 Saving project metadata to database...")

        async def save_metadata():
            # Actual schema columns: id, user_id, name, description, html_code, subdomain,
            # is_published, published_url, total_views, created_at, updated_at
            project_data = {
                "id": project_id,
                "user_id": request.user_id,
                "name": request.project_name,  # Column name is 'name' not 'business_name'
                "subdomain": request.subdomain,
                "html_code": html_content,  # Column name is 'html_code' not 'html_content'
                "is_published": True,  # Column name is 'is_published' not 'status'
                "published_url": public_url,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            result = await supabase_service.create_website(project_data)
            if not result:
                raise Exception("Database insert returned None")
            return result

        try:
            await retry_with_backoff(save_metadata, max_retries=3, initial_delay=1.0)
            logger.info(f"✅ Metadata saved successfully: {project_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save metadata after retries: {e}")
            logger.warning("⚠️ Website uploaded but metadata save failed - continuing anyway")
            # Don't fail the entire request - user can still access the website

        logger.info("=" * 80)
        logger.info(f"✅ WEBSITE PUBLISHED SUCCESSFULLY")
        logger.info(f"   URL: {public_url}")
        logger.info(f"   Project ID: {project_id}")
        logger.info("=" * 80)

        return PublishResponse(
            url=public_url,
            subdomain=request.subdomain,
            project_id=project_id,
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error("=" * 80)
        logger.error("❌ PUBLISH ERROR")
        logger.error(f"   Error type: {type(e).__name__}")
        logger.error(f"   Error message: {str(e)}")
        logger.error("   Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal menerbitkan website: {str(e)}"
        )


def inject_delivery_widget_if_needed(html: str, website_id: str, business_name: str) -> str:
    """
    Inject BinaApp Delivery Widget if delivery features are detected in the HTML.

    This is the CRITICAL FIX for the delivery widget not being injected.
    The widget enables customers to place delivery orders directly from the website.

    Detection: Checks for ANY delivery-related content in the HTML
    """
    # Check if widget is already injected
    if 'delivery-widget.js' in html:
        logger.info("📦 Delivery widget already present - skipping injection")
        return html

    # More robust detection - check for ANY delivery-related markers
    delivery_markers = [
        # Page structure markers
        'id="page-order"',
        "id='page-order'",
        'id="delivery"',
        "id='delivery'",
        'id="delivery-zones"',
        "id='delivery-zones'",
        # Button/text markers
        'Pesan Delivery',
        'pesan delivery',
        'Delivery Sendiri',
        'delivery sendiri',
        'Order Delivery',
        'order delivery',
        # Navigation markers
        "showPage('order')",
        'showPage("order")',
        "showPage('delivery')",
        # Emoji markers
        '🛵',
        # Class markers
        'delivery-section',
        'delivery-zone',
        'delivery-order',
        # WhatsApp order markers
        'nak order delivery',
        'Saya nak order',
        # Menu ordering markers
        'Pilih Kawasan Delivery',
        'Bakul Pesanan',
        'Troli Pesanan',
    ]

    has_delivery = any(marker in html for marker in delivery_markers)

    # Log detection status
    logger.info(f"🔍 Delivery widget detection for website {website_id}:")
    logger.info(f"   - HTML length: {len(html)} chars")
    logger.info(f"   - Delivery features detected: {has_delivery}")

    if has_delivery:
        # Log which markers were found
        found_markers = [m for m in delivery_markers if m in html]
        logger.info(f"   - Found markers: {found_markers[:3]}...")  # Show first 3

    if not has_delivery:
        logger.info("📦 No delivery features detected - skipping widget injection")
        return html

    logger.info("📦 Delivery features detected - injecting delivery widget")

    # Try to extract WhatsApp number from existing links in the HTML
    whatsapp_number = "+60123456789"  # Default
    wa_match = re.search(r'wa\.me/(\+?\d+)', html)
    if wa_match:
        whatsapp_number = wa_match.group(1)
        if not whatsapp_number.startswith('+'):
            whatsapp_number = '+' + whatsapp_number
        logger.info(f"📱 Extracted WhatsApp: {whatsapp_number}")

    # Escape business name for JavaScript
    safe_business_name = business_name.replace("'", "\\'").replace('"', '\\"')

    # Create the delivery widget script
    delivery_script = f'''
<!-- BinaApp Delivery Widget -->
<script src="https://binaapp-backend.onrender.com/widgets/delivery-widget.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    if (typeof BinaAppDelivery !== 'undefined') {{
        BinaAppDelivery.init({{
            websiteId: '{website_id}',
            apiUrl: 'https://binaapp-backend.onrender.com',
            whatsapp: '{whatsapp_number}',
            businessName: '{safe_business_name}',
            primaryColor: '#ea580c'
        }});
    }}
}});
</script>
'''

    # Inject before </body>
    if '</body>' in html:
        html = html.replace('</body>', delivery_script + '\n</body>')
        logger.info(f"✅ Delivery widget injected for website {website_id}")
    elif '</BODY>' in html:
        html = html.replace('</BODY>', delivery_script + '\n</BODY>')
        logger.info(f"✅ Delivery widget injected for website {website_id} (uppercase)")
    else:
        # Fallback: append to end
        html += delivery_script
        logger.info(f"✅ Delivery widget appended for website {website_id} (no body tag)")

    return html


def validate_subdomain(subdomain: str) -> bool:
    """Validate subdomain format"""
    # Must be 3-63 characters
    if not (3 <= len(subdomain) <= 63):
        return False

    # Must contain only lowercase letters, numbers, and hyphens
    # Cannot start or end with hyphen
    pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
    return bool(re.match(pattern, subdomain))
