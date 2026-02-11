"""
Simple Publish Endpoint
POST /api/publish - Publish website to Supabase Storage

IMPORTANT: This endpoint now requires authentication OR a valid user_id.
- If Bearer token is provided, user_id is taken from the authenticated user
- If no token, user_id from request body must be a valid UUID (not "demo-user")
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any
from loguru import logger
from datetime import datetime
import uuid
import re
import asyncio

from app.services.storage_service import storage_service
from app.services.supabase_client import supabase_service
from app.core.security import get_optional_current_user
from app.services.subscription_service import subscription_service

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
    description: Optional[str] = Field(default=None, description="Business description for type detection")
    business_type: Optional[str] = Field(default=None, description="Business type: food, clothing, services, general")
    language: Optional[str] = Field(default="ms", description="Language: ms or en")

    @model_validator(mode='before')
    @classmethod
    def set_html_content(cls, values):
        """Automatically handle multiple field names for HTML content"""
        # In Pydantic V2, model_validator receives all values
        if isinstance(values, dict):
            html_content = values.get('html_content')
            if html_content:
                return values
            # Try alternate field names
            html_content = values.get('html_code') or values.get('html')
            if html_content:
                values['html_content'] = html_content
        return values

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
async def publish_website(
    request: PublishRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
):
    """
    Publish website to Supabase Storage - ROBUST VERSION

    SECURITY: Supports optional authentication.
    - If Bearer token provided: uses authenticated user_id (secure)
    - If no token: validates user_id from request body

    CRITICAL: Database record is REQUIRED for website to appear in dashboard.
    If DB insert fails, the entire request fails.
    """
    try:
        logger.info("=" * 80)
        logger.info(f"🚀 PUBLISH REQUEST RECEIVED")
        logger.info(f"   Project: {request.project_name}")
        logger.info(f"   Subdomain: {request.subdomain}")

        # SECURITY: Determine user_id from authentication or request
        if current_user:
            # Authenticated user - use their ID
            user_id = current_user.get("sub") or current_user.get("id")
            logger.info(f"   User ID: {user_id} (from authenticated token ✅)")
        else:
            # Not authenticated via token - check if request has valid user_id
            user_id = request.user_id
            logger.info(f"   User ID: {user_id} (from request body - NOT AUTHENTICATED via token ⚠️)")

            # Validate user_id - MUST be a valid UUID, not a placeholder
            if user_id in ["demo-user", "anonymous", "guest", "", None]:
                # CRITICAL FIX: Instead of generating random UUID, reject the request
                # Random UUIDs create orphaned websites that don't appear in user's dashboard
                logger.error(f"   ❌ Invalid user_id: '{user_id}' - authentication required")
                logger.error(f"   ❌ Website would be orphaned if published with random UUID")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sila log masuk untuk menerbitkan website / Please log in to publish website",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Check if user_id is a valid UUID format
            try:
                uuid.UUID(user_id)
                logger.info(f"   User ID is valid UUID format ✅")
            except ValueError:
                logger.error(f"   ❌ Invalid user_id format: '{user_id}' - not a valid UUID")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sila log masuk untuk menerbitkan website / Please log in to publish website",
                    headers={"WWW-Authenticate": "Bearer"}
                )

        # Update request.user_id for downstream use
        request.user_id = user_id
        logger.info("=" * 80)

        # NOTE: Subscription limit check is moved AFTER is_republish is determined
        # This allows users to republish/update their existing websites even when at limit
        limit_result = None

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

        # Check if subdomain is already taken and handle ownership
        is_republish = False
        existing_website = None
        project_id = None

        async def check_subdomain():
            return await storage_service.check_subdomain_exists(request.subdomain)

        try:
            subdomain_exists = await retry_with_backoff(check_subdomain, max_retries=2)
            if subdomain_exists:
                logger.info(f"🔍 Subdomain exists in storage: {request.subdomain}")

                # Check if there's a database record for this subdomain
                existing_website = await supabase_service.get_website_by_subdomain(request.subdomain)

                if existing_website:
                    existing_user_id = existing_website.get("user_id")
                    logger.info(f"   Database record found. Owner: {existing_user_id}")

                    # Case 1: User owns this website - allow republish
                    if existing_user_id == user_id:
                        logger.info(f"✅ User owns this website - allowing republish")
                        is_republish = True
                        project_id = existing_website.get("id")

                    # Case 2: Check if the owner is an orphaned/random UUID
                    # An orphaned UUID is one that doesn't match any real user in auth.users
                    # We can detect this by checking if it's a valid UUID but user can't access it
                    elif current_user:
                        # If authenticated user is trying to publish to a subdomain owned by different user
                        # Check if that user_id looks like a random UUID (orphaned website)
                        # For now, allow authenticated users to claim ANY existing subdomain
                        # since orphaned websites were created with random UUIDs
                        logger.info(f"🔄 Authenticated user claiming orphaned website")
                        logger.info(f"   Old user_id: {existing_user_id}")
                        logger.info(f"   New user_id: {user_id}")
                        is_republish = True
                        project_id = existing_website.get("id")
                    else:
                        # Unauthenticated user cannot claim existing subdomain
                        logger.warning(f"⚠️ Subdomain owned by another user: {request.subdomain}")
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Subdomain '{request.subdomain}' sudah digunakan. Sila pilih yang lain."
                        )
                else:
                    # Website exists in storage but NOT in database - orphaned storage
                    # Allow authenticated user to claim it by creating a new DB record
                    logger.info(f"🔄 Website exists in storage but not in database - will create record")
                    if not current_user:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Sila log masuk untuk menuntut website ini / Please log in to claim this website",
                            headers={"WWW-Authenticate": "Bearer"}
                        )
            else:
                logger.info("✓ Subdomain available")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"⚠️ Could not check subdomain availability: {e}")
            # Continue anyway - will fail later if subdomain is actually taken

        # Generate project ID if not republishing
        if not project_id:
            project_id = str(uuid.uuid4())
        logger.info(f"✓ Project ID: {project_id} ({'existing' if is_republish else 'new'})")

        # CRITICAL: Check subscription limit for authenticated users ONLY for NEW websites
        # Republishing existing websites should always be allowed (user already owns them)
        if current_user and not is_republish:
            logger.info("")
            logger.info("🔒 SUBSCRIPTION CHECK: Verifying website limit for NEW website...")
            limit_result = await subscription_service.check_limit(user_id, "create_website")

            if not limit_result.get("allowed"):
                logger.error(f"❌ LIMIT REACHED: User {user_id} has reached website limit")
                logger.error(f"   Current: {limit_result.get('current_usage')}, Limit: {limit_result.get('limit')}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "limit_reached",
                        "message": limit_result.get("message", "Had website tercapai. Sila naik taraf pelan anda."),
                        "current_usage": limit_result.get("current_usage"),
                        "limit": limit_result.get("limit"),
                        "can_buy_addon": limit_result.get("can_buy_addon", False),
                        "upgrade_url": "/dashboard/billing"
                    }
                )
            logger.info(f"✅ Subscription check passed: {limit_result.get('current_usage')}/{limit_result.get('limit')} websites used")
        elif is_republish:
            logger.info("✅ Republishing existing website - skipping limit check")

        # CRITICAL FIX: Replace any wrong website_id in HTML with the correct project_id
        # This fixes the bug where generate.py creates a random UUID that doesn't match database
        html_content = fix_website_id_in_html(html_content, project_id)

        # CRITICAL FIX: Inject delivery widget with dynamic label based on business type
        html_content = inject_delivery_widget_if_needed(
            html_content,
            project_id,
            request.project_name,
            description=request.description or request.project_name,
            language=request.language or "ms"
        )

        # Ensure customer chat widget is available on published websites
        html_content = inject_chat_widget_if_needed(
            html_content,
            project_id,
            api_url="https://binaapp-backend.onrender.com"
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
        # CRITICAL: Database record MUST be saved - without it, website won't appear in dashboard
        logger.info("💾 STEP 3: Saving website record to database...")
        logger.info(f"   Website ID: {project_id}")
        logger.info(f"   User ID: {request.user_id}")
        logger.info(f"   Subdomain: {request.subdomain}")
        logger.info(f"   Mode: {'UPDATE (republish/claim)' if is_republish else 'INSERT (new)'}")

        async def save_metadata():
            # Helper function to INSERT a new record
            async def do_insert():
                project_data = {
                    "id": project_id,
                    "user_id": request.user_id,
                    "name": request.project_name,
                    "business_name": request.project_name,
                    "subdomain": request.subdomain,
                    "html_content": html_content,
                    "status": "published",
                    "public_url": public_url,
                    "published_at": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                logger.info(f"   Inserting new record with columns: {list(project_data.keys())}")
                result = await supabase_service.create_website(project_data)
                if not result:
                    raise Exception("Database insert returned None - check Supabase logs for RLS/permission errors")
                logger.info(f"   ✅ Database insert successful: {result}")
                return result

            if is_republish:
                # UPDATE existing record - this handles republishing AND claiming orphaned websites
                update_data = {
                    "user_id": request.user_id,  # Update ownership (important for claiming)
                    "name": request.project_name,
                    "business_name": request.project_name,
                    "html_content": html_content,
                    "status": "published",
                    "public_url": public_url,
                    "published_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                logger.info(f"   Attempting UPDATE on existing record: {project_id}")
                success = await supabase_service.update_website(project_id, update_data)
                if success:
                    logger.info(f"   ✅ Database update successful")
                    return {"id": project_id, "updated": True}
                else:
                    # CRITICAL FIX: UPDATE failed (0 rows affected) - record may have been deleted
                    # Fall back to INSERT to ensure the database record is created
                    logger.warning(f"   ⚠️ UPDATE failed for {project_id} - falling back to INSERT")
                    logger.warning(f"   This can happen when claiming orphaned storage or if record was deleted")
                    return await do_insert()
            else:
                # INSERT new record
                return await do_insert()

        try:
            db_result = await retry_with_backoff(save_metadata, max_retries=3, initial_delay=1.0)
            logger.info(f"✅ Database record saved successfully: {project_id}")

            # CRITICAL: Track usage for authenticated users ONLY for NEW websites
            # Republishing should NOT increment usage (user is updating, not creating)
            if current_user and not is_republish:
                try:
                    if limit_result and limit_result.get("using_addon"):
                        await subscription_service.use_addon_credit(user_id, "website")
                        logger.info(f"🧾 Consumed website addon credit for user {user_id}")

                    await subscription_service.increment_usage(user_id, "create_website")
                    logger.info(f"📊 Incremented websites_count for user {user_id}")
                except Exception as usage_err:
                    logger.warning(f"⚠️ Usage tracking failed for user {user_id}: {usage_err}")
            elif is_republish:
                logger.info(f"📊 Republishing existing website - usage count unchanged for user {user_id}")
        except Exception as e:
            # CRITICAL FIX: DO NOT silently ignore database errors!
            # Without database record, website won't appear in dashboard
            logger.error(f"❌ CRITICAL: Failed to save database record: {e}")
            logger.error(f"   Website uploaded to storage but NOT saved to database!")
            logger.error(f"   This means website will load at {public_url} but NOT appear in dashboard!")
            # Raise the error - this is a critical failure
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Website uploaded but database save failed: {str(e)}. Please try again."
            )

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


def fix_website_id_in_html(html: str, correct_website_id: str) -> str:
    """
    CRITICAL FIX: Replace any incorrect website_id in HTML with the correct one.

    This ensures the data-website-id attribute matches the actual database website ID.
    The delivery widget reads from data-website-id, so it must be correct.
    """
    # Pattern to match data-website-id="..." with any UUID or value
    # This catches: data-website-id="99ff9cae-418d-4f29-a2ec-e5a36f2209a8"
    pattern = r'data-website-id="[^"]*"'
    replacement = f'data-website-id="{correct_website_id}"'

    # Replace all occurrences
    fixed_html = re.sub(pattern, replacement, html)

    # Also fix any BinaAppDelivery.init({ websiteId: '...' }) calls
    init_pattern = r"websiteId:\s*['\"]([^'\"]*)['\"]"
    init_replacement = f"websiteId: '{correct_website_id}'"
    fixed_html = re.sub(init_pattern, init_replacement, fixed_html)

    # Also fix delivery button URLs: /delivery/OLD_ID -> /delivery/CORRECT_ID
    # Pattern: binaapp.my/delivery/UUID
    delivery_url_pattern = r'binaapp\.my/delivery/[a-f0-9-]+'
    delivery_url_replacement = f'binaapp.my/delivery/{correct_website_id}'
    fixed_html = re.sub(delivery_url_pattern, delivery_url_replacement, fixed_html)

    # CRITICAL FIX: Replace const WEBSITE_ID = '...' in JavaScript
    # This pattern is injected by templates.py line 1404 during integration injection
    const_pattern = r"const WEBSITE_ID = ['\"]([^'\"]*)['\"]"
    const_replacement = f"const WEBSITE_ID = '{correct_website_id}'"
    fixed_html = re.sub(const_pattern, const_replacement, fixed_html)

    # Also fix localStorage keys that use the old website_id
    # Pattern: binaapp_customer_id_{OLD_UUID} or similar
    # This ensures customer data persists with the correct website_id
    localstorage_pattern = r"binaapp_customer_(?:id|name|phone)_['\"]?\s*\+\s*WEBSITE_ID"
    # This pattern doesn't need replacement as it uses the WEBSITE_ID variable

    logger.info(f"✅ Fixed all website_id references to: {correct_website_id}")
    return fixed_html


def inject_delivery_widget_if_needed(html: str, website_id: str, business_name: str, description: str = "", language: str = "ms") -> str:
    """ALWAYS inject delivery widget script - auto-initializes with data attributes"""
    from app.services.business_types import detect_business_type

    # Detect business type from description or business name
    business_type = detect_business_type(description or business_name)

    # Inject the actual widget script tag with data attributes
    # The widget JavaScript will auto-initialize from these attributes
    delivery_widget = f'''
<!-- BinaApp Delivery Widget Script -->
<script src="https://binaapp-backend.onrender.com/static/widgets/delivery-widget.js"
        data-website-id="{website_id}"
        data-api-url="https://binaapp-backend.onrender.com/api/v1"
        data-primary-color="#ea580c"
        data-business-type="{business_type}"
        data-language="{language}"></script>'''

    if "</body>" in html:
        return html.replace("</body>", delivery_widget + "\n</body>")
    return html + delivery_widget


def inject_chat_widget_if_needed(html: str, website_id: str, api_url: str = "https://binaapp-backend.onrender.com") -> str:
    """Inject chat widget script if missing to enable customer chat."""
    # Skip if inline chat button already exists (avoid duplicate chat widgets)
    # The inline chat button is added by inject_delivery_ui and has full chat functionality
    if "binaapp-inline-chat-btn" in html:
        return html
    if "chat-widget.js" in html or "binaapp-chat-widget" in html:
        return html

    chat_widget = f'''
<!-- BinaApp Chat Widget - Customer to Owner Chat -->
<script src="{api_url}/static/widgets/chat-widget.js"
        data-website-id="{website_id}"
        data-api-url="{api_url}"></script>'''

    if "</body>" in html:
        return html.replace("</body>", chat_widget + "\n</body>")
    return html + chat_widget


def validate_subdomain(subdomain: str) -> bool:
    """Validate subdomain format"""
    # Must be 3-63 characters
    if not (3 <= len(subdomain) <= 63):
        return False

    # Must contain only lowercase letters, numbers, and hyphens
    # Cannot start or end with hyphen
    pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
    return bool(re.match(pattern, subdomain))
