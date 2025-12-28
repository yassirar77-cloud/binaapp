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
BLOCKED_WORDS = [
    # English offensive
    "fuck", "shit", "ass", "bitch", "dick", "porn", "sex", "xxx",
    "nude", "naked", "kill", "murder", "terrorist", "bomb", "drug",
    "cocaine", "heroin", "weed", "gambling", "casino", "scam", "fraud",

    # Malay offensive
    "babi", "bodoh", "sial", "pukimak", "kimak", "lancau", "pantat",
    "sundal", "jalang", "pelacur", "haram", "celaka", "bangang",
    "bengap", "tolol", "goblok", "anjing", "asu",

    # Religious/Political sensitive (Malaysia)
    "allah", "nabi", "rasul", "agong", "sultan", "kerajaan",

    # Brand/Trademark issues
    "google", "facebook", "instagram", "tiktok", "twitter", "amazon",
    "apple", "microsoft", "netflix", "shopee", "lazada", "grab",

    # Government/Official
    "gov", "government", "polis", "police", "tentera", "army",
    "kementerian", "jabatan", "official", "rasmi",
]


def is_subdomain_allowed(subdomain: str) -> tuple[bool, str]:
    """
    Check if subdomain is allowed based on content policy.

    Returns:
        tuple[bool, str]: (is_allowed, error_message)
    """
    subdomain_lower = subdomain.lower().strip()

    # Check minimum length
    if len(subdomain_lower) < 3:
        return False, "Subdomain mesti sekurang-kurangnya 3 aksara"

    # Check maximum length
    if len(subdomain_lower) > 30:
        return False, "Subdomain terlalu panjang (maksimum 30 aksara)"

    # Check for valid characters only
    if not re.match(r'^[a-z0-9-]+$', subdomain_lower):
        return False, "Subdomain hanya boleh mengandungi huruf kecil, nombor dan tanda sempang (-)"

    # Check if starts/ends with hyphen
    if subdomain_lower.startswith('-') or subdomain_lower.endswith('-'):
        return False, "Subdomain tidak boleh bermula atau berakhir dengan tanda sempang"

    # Check blocked words
    for word in BLOCKED_WORDS:
        if word in subdomain_lower:
            return False, "Subdomain mengandungi perkataan tidak dibenarkan"

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

        # Check if subdomain is allowed (content policy)
        is_allowed, error_message = is_subdomain_allowed(request.subdomain)
        if not is_allowed:
            logger.error(f"❌ Subdomain blocked by content policy: {request.subdomain}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        logger.info("✓ Subdomain passes content policy check")

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


def validate_subdomain(subdomain: str) -> bool:
    """Validate subdomain format"""
    # Must be 3-63 characters
    if not (3 <= len(subdomain) <= 63):
        return False

    # Must contain only lowercase letters, numbers, and hyphens
    # Cannot start or end with hyphen
    pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
    return bool(re.match(pattern, subdomain))
