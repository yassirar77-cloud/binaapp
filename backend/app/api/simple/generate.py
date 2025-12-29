"""
Simple Generate Endpoint
POST /api/generate - Generate website from description
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger
import asyncio
import json

from app.services.ai_service import ai_service
from app.services.templates import template_service
from app.services.screenshot_service import screenshot_service
from app.services.job_service import job_service, JobStatus
from app.models.schemas import WebsiteGenerationRequest, Language
from app.utils.content_moderation import is_content_allowed, log_blocked_attempt

router = APIRouter()


class SimpleGenerateRequest(BaseModel):
    """Simplified generation request"""
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="User's description in Malay or English"
    )
    user_id: Optional[str] = Field(default="demo-user", description="Optional user ID")
    images: Optional[List] = Field(default=[], description="Optional list of uploaded image URLs or image metadata objects with url and name")
    gallery_metadata: Optional[List] = Field(default=[], description="Gallery images with metadata (url, name)")
    business_description: Optional[str] = Field(default=None, description="Business description for context")
    language: Optional[str] = Field(default="ms", description="Language for generation (ms or en)")
    email: Optional[str] = Field(default=None, description="User email")
    logo: Optional[str] = Field(default=None, description="Logo URL")
    fonts: Optional[List[str]] = Field(default=[], description="Font names to use (e.g., ['Inter', 'Poppins'])")
    colors: Optional[dict] = Field(default=None, description="Color scheme (primary, secondary, accent)")
    theme: Optional[str] = Field(default=None, description="Detected theme name (e.g., 'Purrfect Paws Theme')")
    multi_style: Optional[bool] = Field(default=False, description="Generate multiple style variations")
    generate_previews: Optional[bool] = Field(default=False, description="Generate preview thumbnails (slower)")
    mode: Optional[str] = Field(default="single", description="Generation mode: 'single', 'dual', 'best', or 'strategic'")
    features: Optional[dict] = Field(default=None, description="Selected features (whatsapp, googleMap, deliverySystem, etc.)")
    delivery: Optional[dict] = Field(default=None, description="Delivery system settings (area, fee, minimum, hours)")
    address: Optional[str] = Field(default=None, description="Full address for Google Map")
    social_media: Optional[dict] = Field(default=None, description="Social media handles (instagram, facebook, tiktok)")


class SimpleGenerateResponse(BaseModel):
    """Simplified generation response"""
    html: str
    detected_features: List[str]
    template_used: str
    success: bool = True


class StyleVariation(BaseModel):
    """Single style variation"""
    style: str
    html: str
    preview_image: Optional[str] = None
    thumbnail: Optional[str] = None
    social_preview: Optional[str] = None


class MultiStyleResponse(BaseModel):
    """Multi-style generation response"""
    variations: List[StyleVariation]
    detected_features: List[str]
    template_used: str
    success: bool = True


class DualGenerateResponse(BaseModel):
    """Dual AI generation response"""
    qwen_html: Optional[str] = None
    deepseek_html: Optional[str] = None
    detected_features: List[str]
    template_used: str
    success: bool = True


@router.post("/generate")
async def generate_website(request: SimpleGenerateRequest):
    """
    Generate complete website from description

    This endpoint:
    - Accepts description in Bahasa Malaysia or English
    - Detects website type automatically
    - Auto-injects integrations based on detected features
    - Returns complete, functional HTML
    - Supports multi-style generation (Modern, Minimal, Bold)
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 NEW GENERATION REQUEST RECEIVED")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Description length: {len(request.description)} chars")
        logger.info(f"Description preview: {request.description[:100]}...")
        logger.info(f"Multi-style: {request.multi_style}")
        logger.info(f"Generate previews: {request.generate_previews}")
        logger.info(f"Generation mode: {request.mode}")
        logger.info(f"Images: {len(request.images) if request.images else 0}")
        logger.info("=" * 80)

        # ==================== CONTENT MODERATION ====================
        # Check for illegal/harmful content BEFORE generation
        is_allowed, block_reason = is_content_allowed(request.description)
        if not is_allowed:
            log_blocked_attempt(
                description=request.description,
                reason=block_reason,
                user_id=request.user_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=block_reason
            )
        logger.info("✅ Content moderation check passed")

        # Detect website type
        logger.info("Step 1: Detecting website type...")
        website_type = template_service.detect_website_type(request.description)
        logger.info(f"✓ Detected website type: {website_type}")

        # Detect required features
        logger.info("Step 2: Detecting features...")
        features = template_service.detect_features(request.description)
        logger.info(f"✓ Detected features: {features}")

        # Extract business name from description (simple extraction)
        logger.info("Step 3: Extracting business information...")
        business_name = extract_business_name(request.description)
        logger.info(f"✓ Business name: {business_name}")

        # Detect language
        language = detect_language(request.description)
        logger.info(f"✓ Language: {language}")

        # Extract phone number if mentioned
        phone_number = extract_phone_number(request.description)
        logger.info(f"✓ Phone: {phone_number or 'Not found'}")

        # Extract address if mentioned
        address = extract_address(request.description)
        logger.info(f"✓ Address: {address or 'Not found'}")

        # Log assets
        if request.logo:
            logger.info(f"✓ Logo: {request.logo}")
        if request.fonts and len(request.fonts) > 0:
            logger.info(f"✓ Fonts: {', '.join(request.fonts)}")
        if request.colors:
            logger.info(f"✓ Colors: {request.colors}")
        if request.theme:
            logger.info(f"✓ Theme: {request.theme}")

        # Build AI generation request
        ai_request = WebsiteGenerationRequest(
            description=request.description,
            business_name=business_name,
            business_type=website_type,
            language=language,
            subdomain="preview",  # Placeholder
            include_whatsapp=("whatsapp" in features),
            whatsapp_number=phone_number if phone_number else "+60123456789",
            include_maps=("maps" in features),
            location_address=address if address else "",
            include_ecommerce=("cart" in features),
            contact_email=None,
            uploaded_images=request.images if request.images else [],
            logo=request.logo,
            fonts=request.fonts if request.fonts else [],
            colors=request.colors,
            theme=request.theme
        )

        # Log uploaded images
        if request.images and len(request.images) > 0:
            logger.info(f"✓ User uploaded {len(request.images)} images:")
            for i, img in enumerate(request.images):
                logger.info(f"   Image {i+1}: {img}")

        # User data for integrations
        user_data = {
            "phone": phone_number if phone_number else "+60123456789",
            "address": address if address else "",
            "email": "contact@business.com",
            "url": "https://preview.binaapp.my",
            "whatsapp_message": "Hi, I'm interested"
        }

        # Dual AI generation mode - return both designs
        if request.mode == "dual":
            logger.info("=" * 80)
            logger.info("Step 4: DUAL AI GENERATION")
            logger.info("Calling both Qwen and DeepSeek in parallel...")
            logger.info("=" * 80)

            dual_results = await ai_service.generate_website_dual(ai_request)

            # Inject integrations into both designs
            qwen_html = None
            deepseek_html = None

            if dual_results["qwen"]:
                qwen_html = template_service.inject_integrations(
                    dual_results["qwen"],
                    features,
                    user_data
                )

            if dual_results["deepseek"]:
                deepseek_html = template_service.inject_integrations(
                    dual_results["deepseek"],
                    features,
                    user_data
                )

            logger.info(f"✓ Dual generation complete")

            return DualGenerateResponse(
                qwen_html=qwen_html,
                deepseek_html=deepseek_html,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Best-of-both mode - combine best parts
        elif request.mode == "best":
            logger.info("=" * 80)
            logger.info("Step 4: BEST-OF-BOTH GENERATION")
            logger.info("Generating with both AIs and combining best parts...")
            logger.info("=" * 80)

            html_content = await ai_service.generate_website_best(ai_request)

            # Inject integrations
            html_content = template_service.inject_integrations(
                html_content,
                features,
                user_data
            )

            logger.info("✓ Best-of-both generation complete")

            return SimpleGenerateResponse(
                html=html_content,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Strategic mode - task-based routing (DeepSeek for code, Qwen for content)
        elif request.mode == "strategic":
            logger.info("=" * 80)
            logger.info("Step 4: STRATEGIC TASK-BASED GENERATION")
            logger.info("Using DeepSeek for code structure, Qwen for content...")
            logger.info("=" * 80)

            ai_response = await ai_service.generate_website_strategic(ai_request)

            # Get the generated HTML
            html_content = ai_response.html_content

            # Inject additional integrations
            html_content = template_service.inject_integrations(
                html_content,
                features,
                user_data
            )

            logger.info("✓ Strategic generation complete")

            return SimpleGenerateResponse(
                html=html_content,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Multi-style generation
        elif request.multi_style:
            logger.info("=" * 80)
            logger.info("Step 4: MULTI-STYLE GENERATION")
            logger.info("Calling AI service to generate 3 style variations...")
            logger.info("=" * 80)
            variations_dict = await ai_service.generate_multi_style(ai_request)
            logger.info(f"✓ Received {len(variations_dict)} variations from AI service")

            # Process each variation
            variations = []
            for style, ai_response in variations_dict.items():
                html_content = ai_response.html_content

                # Inject integrations
                html_content = template_service.inject_integrations(
                    html_content,
                    features,
                    user_data
                )

                variations.append({
                    "style": style,
                    "html": html_content
                })

            logger.info(f"Generated {len(variations)} style variations successfully!")

            # Generate previews if requested
            if request.generate_previews:
                logger.info("Generating preview thumbnails...")
                try:
                    variations = await screenshot_service.generate_variation_previews(variations)
                    logger.info("Preview thumbnails generated successfully")
                except Exception as e:
                    logger.warning(f"Failed to generate previews: {e}")
                    # Continue without previews

            # Convert to StyleVariation objects
            variations = [
                StyleVariation(
                    style=v.get("style"),
                    html=v.get("html"),
                    thumbnail=v.get("thumbnail"),
                    social_preview=v.get("social_preview")
                )
                for v in variations
            ]

            return MultiStyleResponse(
                variations=variations,
                detected_features=features,
                template_used=website_type,
                success=True
            )

        # Single style generation (original behavior)
        else:
            logger.info("=" * 80)
            logger.info("Step 4: SINGLE-STYLE GENERATION")
            logger.info("Calling AI service to generate website...")
            logger.info("=" * 80)
            ai_response = await ai_service.generate_website(ai_request)
            logger.info("✓ Received response from AI service")

            # Get the generated HTML
            html_content = ai_response.html_content

            # Inject additional integrations
            html_content = template_service.inject_integrations(
                html_content,
                features,
                user_data
            )

            logger.info("Website generated successfully!")

            return SimpleGenerateResponse(
                html=html_content,
                detected_features=features,
                template_used=website_type,
                success=True
            )

    except Exception as e:
        import traceback
        logger.error("=" * 80)
        logger.error("❌ ERROR GENERATING WEBSITE")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate website: {type(e).__name__}: {str(e)}"
        )


def extract_business_name(description: str) -> str:
    """Extract business name from description"""
    import re

    # Look for patterns like "Kedai X", "Restoran X", "X Cafe", etc.
    patterns = [
        r'(?:kedai|restoran|cafe|salon|butik|toko)\s+([A-Za-z\s]+?)(?:\s+yang|\s+di|\s+untuk|\.|\,|$)',
        r'([A-Z][A-Za-z\s]+?)(?:\s+adalah|\s+merupakan|\s+ialah)',
        r'^([A-Z][A-Za-z\s]+?)(?:\s+-|\s+:)',
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 3 <= len(name) <= 50:
                return name

    # Fallback: use first few words
    words = description.split()[:3]
    return " ".join(words) if words else "My Business"


def detect_language(description: str) -> Language:
    """Detect if description is in Malay or English"""
    malay_keywords = ['saya', 'kami', 'yang', 'untuk', 'adalah', 'dengan', 'ini', 'dan', 'di', 'ke']

    description_lower = description.lower()
    malay_count = sum(1 for keyword in malay_keywords if keyword in description_lower)

    return Language.MALAY if malay_count >= 2 else Language.ENGLISH


def extract_phone_number(description: str) -> Optional[str]:
    """Extract phone number from description"""
    import re

    # Malaysian phone patterns
    patterns = [
        r'\+60\s?1[0-9]{1,2}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}',  # +60 format
        r'01[0-9]{1,2}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}',  # 01X format
        r'60\s?1[0-9]{1,2}[-\s]?[0-9]{3,4}[-\s]?[0-9]{3,4}',  # 60 format
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            phone = match.group(0)
            # Clean and format
            phone = re.sub(r'[-\s]', '', phone)
            if not phone.startswith('+'):
                if phone.startswith('60'):
                    phone = '+' + phone
                elif phone.startswith('0'):
                    phone = '+6' + phone
            return phone

    return None


def extract_address(description: str) -> Optional[str]:
    """Extract address from description"""
    import re

    # Look for address keywords
    patterns = [
        r'(?:alamat|address|lokasi|location|terletak|located)[\s:]+([^.!?]+)',
        r'(?:di|at)\s+([^.!?]+?(?:kuala lumpur|kl|selangor|penang|johor|melaka|perak|pahang|[0-9]{5}))',
    ]

    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            if 10 <= len(address) <= 200:
                return address

    return None


# ==================== ASYNC GENERATION ENDPOINTS ====================

class AsyncGenerateStartResponse(BaseModel):
    """Response when starting async generation"""
    job_id: str
    status: str
    message: str


class AsyncGenerateStatusResponse(BaseModel):
    """Response for job status check"""
    job_id: str
    status: str
    progress: int
    variants: List[dict] = []
    error: Optional[str] = None
    detected_features: List[str] = []
    template_used: str = ""


def build_feature_instructions(features: dict, delivery: dict, address: str, social_media: dict) -> str:
    """Build feature instructions for AI based on user selections"""
    if not features:
        return ""

    feature_instructions = "\n\n=== REQUIRED FEATURES ===\n"

    # WhatsApp
    if features.get("whatsapp", True):
        feature_instructions += "- WhatsApp button (floating and in contact section)\n"
    else:
        feature_instructions += "- DO NOT include WhatsApp button\n"

    # Google Map
    if features.get("googleMap") and address:
        feature_instructions += f"- Google Map embed showing: {address}\n"
        feature_instructions += f"  Use iframe: <iframe src='https://maps.google.com/maps?q={address}&output=embed'>\n"

    # Delivery System
    if features.get("deliverySystem") and delivery:
        area = delivery.get('area', 'Dalam 5km')
        fee = delivery.get('fee', 'RM5')
        minimum = delivery.get('minimum', 'RM20')
        hours = delivery.get('hours', '11am-9pm')

        feature_instructions += f"""- DELIVERY SECTION with:
  - Kawasan: {area}
  - Caj: {fee}
  - Minimum order: {minimum}
  - Waktu: {hours}
  - Order button that sends WhatsApp with delivery request
  - Simple order form: Name, Phone, Address, Items, Total
"""

    # Contact Form
    if features.get("contactForm"):
        feature_instructions += "- Contact form with Name, Email, Phone, Message fields\n"

    # Social Media
    if features.get("socialMedia") and social_media:
        feature_instructions += "- Social media icons in footer"
        social_links = []
        if social_media.get('instagram'):
            social_links.append(f"Instagram ({social_media['instagram']})")
        if social_media.get('facebook'):
            social_links.append(f"Facebook ({social_media['facebook']})")
        if social_media.get('tiktok'):
            social_links.append(f"TikTok ({social_media['tiktok']})")
        if social_links:
            feature_instructions += f": {', '.join(social_links)}\n"
        else:
            feature_instructions += "\n"

    # Price List
    if features.get("priceList", True):
        feature_instructions += "- Show prices for each menu item\n"
    else:
        feature_instructions += "- DO NOT show prices (customer will ask via WhatsApp)\n"

    # Operating Hours
    if features.get("operatingHours", True):
        feature_instructions += "- Show operating hours\n"

    # Gallery
    if features.get("gallery", True):
        feature_instructions += "- Include photo gallery section\n"

    feature_instructions += "=== END FEATURES ===\n\n"

    return feature_instructions


async def generate_variants_background(job_id: str, request: SimpleGenerateRequest):
    """Background task to generate 3 website variants"""
    try:
        logger.info(f"🚀 Starting background generation for job {job_id}")
        job_service.update_status(job_id, JobStatus.PROCESSING)
        job_service.update_progress(job_id, 0)

        # Step 1: Detect website type and features
        logger.info(f"Job {job_id}: Detecting website type and features...")
        website_type = template_service.detect_website_type(request.description)
        features = template_service.detect_features(request.description)
        business_name = extract_business_name(request.description)
        language = detect_language(request.description)
        phone_number = extract_phone_number(request.description)
        address = request.address if request.address else extract_address(request.description)

        # Build feature instructions from user selections
        feature_instructions = ""
        if request.features:
            feature_instructions = build_feature_instructions(
                request.features,
                request.delivery or {},
                address or "",
                request.social_media or {}
            )
            logger.info(f"Job {job_id}: User-selected features:")
            logger.info(feature_instructions)

        # Update job metadata
        job_service.set_metadata(job_id, features, website_type)
        job_service.update_progress(job_id, 10)
        logger.info(f"Job {job_id}: Type={website_type}, Features={features}")

        # Build enhanced description with feature instructions
        enhanced_description = request.description
        if feature_instructions:
            enhanced_description = f"{request.description}\n{feature_instructions}"

        # Build AI generation request
        ai_request = WebsiteGenerationRequest(
            description=enhanced_description,
            business_name=business_name,
            business_type=website_type,
            language=language,
            subdomain="preview",
            include_whatsapp=("whatsapp" in features) or (request.features and request.features.get("whatsapp", True)),
            whatsapp_number=phone_number if phone_number else "+60123456789",
            include_maps=("maps" in features) or (request.features and request.features.get("googleMap", False)),
            location_address=address if address else "",
            include_ecommerce=("cart" in features),
            contact_email=None,
            uploaded_images=request.images if request.images else [],
            logo=request.logo,
            fonts=request.fonts if request.fonts else [],
            colors=request.colors,
            theme=request.theme
        )

        # User data for integrations
        user_data = {
            "phone": phone_number if phone_number else "+60123456789",
            "address": address if address else "",
            "email": "contact@business.com",
            "url": "https://preview.binaapp.my",
            "whatsapp_message": "Hi, I'm interested"
        }

        # Add social media to user_data if provided
        if request.social_media:
            user_data["social_media"] = request.social_media

        # Add delivery info to user_data if provided
        if request.delivery:
            user_data["delivery"] = request.delivery

        # Step 2: Generate 3 style variations
        job_service.update_progress(job_id, 20)
        logger.info(f"Job {job_id}: Generating 3 style variations...")
        variations_dict = await ai_service.generate_multi_style(ai_request)
        job_service.update_progress(job_id, 30)
        logger.info(f"Job {job_id}: Received {len(variations_dict)} variations from AI")

        # Process each variation
        for idx, (style, ai_response) in enumerate(variations_dict.items()):
            try:
                logger.info(f"Job {job_id}: Processing variant {idx+1}/3 ({style})...")

                html_content = ai_response.html_content

                # Inject integrations
                html_content = template_service.inject_integrations(
                    html_content,
                    features,
                    user_data
                )

                variant = {
                    "style": style,
                    "html": html_content,
                    "thumbnail": None,
                    "social_preview": None
                }

                # Add variant to job
                job_service.add_variant(job_id, variant)

                # Update progress: 50%, 70%, 90% (we already hit 30% before AI generation)
                # Progress formula: 30% + (variant_number / 3) * 60%
                progress = 30 + int(((idx + 1) / 3) * 60)
                job_service.update_progress(job_id, progress)
                logger.info(f"Job {job_id}: Progress {progress}% - Variant {idx+1} completed")

            except Exception as e:
                logger.error(f"Job {job_id}: Error processing variant {idx+1}: {e}")
                # Continue with other variants even if one fails

        # Step 3: Mark as completed
        job_service.update_status(job_id, JobStatus.COMPLETED)
        job_service.update_progress(job_id, 100)
        logger.info(f"✅ Job {job_id} completed successfully with {len(variations_dict)} variants")

    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.error(f"❌ Job {job_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        job_service.update_status(job_id, JobStatus.FAILED, error=error_msg)
        job_service.update_progress(job_id, 0)


@router.post("/generate/start", response_model=AsyncGenerateStartResponse)
async def start_async_generation(request: SimpleGenerateRequest, background_tasks: BackgroundTasks):
    """
    Start async website generation (returns immediately)

    This endpoint:
    - Creates a generation job
    - Returns job_id immediately (< 1 second)
    - Generates 3 design variants in the background
    - Client polls /generate/status/{job_id} for updates
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 ASYNC GENERATION START")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Description: {request.description[:100]}...")
        logger.info("=" * 80)

        # ==================== CONTENT MODERATION ====================
        # Check for illegal/harmful content BEFORE generation
        is_allowed, block_reason = is_content_allowed(request.description)
        if not is_allowed:
            log_blocked_attempt(
                description=request.description,
                reason=block_reason,
                user_id=request.user_id
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=block_reason
            )
        logger.info("✅ Content moderation check passed")

        # Create job
        request_data = request.dict()
        job_id = job_service.create_job(
            user_id=request.user_id or "demo-user",
            description=request.description,
            request_data=request_data
        )

        # Start background task
        background_tasks.add_task(generate_variants_background, job_id, request)

        logger.info(f"✅ Job {job_id} created and queued for processing")

        return AsyncGenerateStartResponse(
            job_id=job_id,
            status="pending",
            message="Generation started. Poll /generate/status/{job_id} for updates."
        )

    except Exception as e:
        import traceback
        logger.error(f"Failed to start async generation: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start generation: {str(e)}"
        )


@router.get("/generate/status/{job_id}", response_model=AsyncGenerateStatusResponse)
async def get_generation_status(job_id: str):
    """
    Get status of async generation job

    Returns:
    - status: pending, processing, completed, failed
    - progress: 0-100
    - variants: List of completed variants (populated as they're generated)
    """
    try:
        job_status = job_service.get_job_status(job_id)

        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        return AsyncGenerateStatusResponse(**job_status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/generate/result/{job_id}")
async def get_generation_result(job_id: str):
    """
    Get completed generation result

    Returns full result when job is completed
    Throws 404 if job not found
    Throws 425 (Too Early) if job not completed yet
    """
    try:
        job = job_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        if job.status == JobStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation failed: {job.error}"
            )

        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=425,  # Too Early
                detail=f"Job not completed yet. Status: {job.status.value}, Progress: {job.progress}%"
            )

        # Convert variants to StyleVariation format
        variations = [
            StyleVariation(
                style=v.get("style"),
                html=v.get("html"),
                thumbnail=v.get("thumbnail"),
                social_preview=v.get("social_preview")
            )
            for v in job.variants
        ]

        return MultiStyleResponse(
            variations=variations,
            detected_features=job.detected_features,
            template_used=job.template_used,
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job result: {str(e)}"
        )


@router.post("/generate/stream")
async def generate_stream(request: SimpleGenerateRequest):
    """
    Generate website with Server-Sent Events (SSE)

    This endpoint:
    - Uses SSE to stream real-time progress updates
    - No background tasks (works on Render!)
    - No polling required
    - Single persistent connection
    - Returns final HTML when complete
    """
    async def event_generator():
        try:
            logger.info("=" * 80)
            logger.info("🚀 SSE GENERATION REQUEST")
            logger.info(f"User ID: {request.user_id}")
            logger.info(f"Description: {request.description[:100]}...")
            logger.info(f"Multi-style: {request.multi_style}")
            logger.info("=" * 80)

            # ==================== CONTENT MODERATION ====================
            # Check for illegal/harmful content BEFORE generation
            is_allowed, block_reason = is_content_allowed(request.description)
            if not is_allowed:
                log_blocked_attempt(
                    description=request.description,
                    reason=block_reason,
                    user_id=request.user_id
                )
                yield f"data: {json.dumps({'progress': 0, 'status': 'failed', 'error': block_reason, 'message': 'Kandungan disekat / Content blocked'})}\n\n"
                return
            logger.info("✅ Content moderation check passed")

            # Progress 10% - Starting
            yield f"data: {json.dumps({'progress': 10, 'status': 'processing', 'message': 'Menganalisis perniagaan anda...'})}\n\n"
            await asyncio.sleep(0.1)

            # Detect website type and features
            logger.info("Step 1: Detecting website type and features...")
            website_type = template_service.detect_website_type(request.description)
            features = template_service.detect_features(request.description)
            business_name = extract_business_name(request.description)
            language = detect_language(request.description)
            phone_number = extract_phone_number(request.description)
            address = extract_address(request.description)

            logger.info(f"✓ Type={website_type}, Features={features}")

            # Progress 20%
            yield f"data: {json.dumps({'progress': 20, 'status': 'processing', 'message': 'Menyediakan reka bentuk...', 'detected_features': features, 'template_used': website_type})}\n\n"
            await asyncio.sleep(0.1)

            # Build AI generation request
            ai_request = WebsiteGenerationRequest(
                description=request.description,
                business_name=business_name,
                business_type=website_type,
                language=language,
                subdomain="preview",
                include_whatsapp=("whatsapp" in features),
                whatsapp_number=phone_number if phone_number else "+60123456789",
                include_maps=("maps" in features),
                location_address=address if address else "",
                include_ecommerce=("cart" in features),
                contact_email=None,
                uploaded_images=request.images if request.images else [],
                logo=request.logo,
                fonts=request.fonts if request.fonts else [],
                colors=request.colors,
                theme=request.theme
            )

            # User data for integrations
            user_data = {
                "phone": phone_number if phone_number else "+60123456789",
                "address": address if address else "",
                "email": "contact@business.com",
                "url": "https://preview.binaapp.my",
                "whatsapp_message": "Hi, I'm interested"
            }

            # Multi-style generation
            if request.multi_style:
                logger.info("Generating 3 style variations with SSE...")

                # Progress 30%
                yield f"data: {json.dumps({'progress': 30, 'status': 'processing', 'message': 'AI sedang menjana 3 reka bentuk...'})}\n\n"

                # Generate all 3 styles
                variations_dict = await ai_service.generate_multi_style(ai_request)
                logger.info(f"✓ Received {len(variations_dict)} variations from AI")

                # Process each variation
                variations = []
                for idx, (style, ai_response) in enumerate(variations_dict.items()):
                    logger.info(f"Processing {style} variant ({idx+1}/3)...")

                    html_content = ai_response.html_content

                    # Inject integrations
                    html_content = template_service.inject_integrations(
                        html_content,
                        features,
                        user_data
                    )

                    variant = {
                        "style": style,
                        "html": html_content,
                        "thumbnail": None,
                        "social_preview": None
                    }

                    variations.append(variant)

                    # Update progress: 40%, 70%, 100%
                    progress = 40 + int(((idx + 1) / 3) * 60)
                    message = f"Reka bentuk {style.upper()} siap! ({idx+1}/3)"
                    yield f"data: {json.dumps({'progress': progress, 'status': 'processing', 'message': message})}\n\n"
                    await asyncio.sleep(0.1)

                # Progress 100% - Completed
                logger.info(f"✅ SSE generation completed with {len(variations)} variants")
                yield f"data: {json.dumps({'progress': 100, 'status': 'completed', 'message': 'Siap!', 'variants': variations, 'detected_features': features, 'template_used': website_type})}\n\n"

            else:
                # Single style generation
                logger.info("Generating single style with SSE...")

                # Progress 50%
                yield f"data: {json.dumps({'progress': 50, 'status': 'processing', 'message': 'AI sedang menulis kod...'})}\n\n"

                # Generate website
                ai_response = await ai_service.generate_website(ai_request)
                html_content = ai_response.html_content

                # Inject integrations
                html_content = template_service.inject_integrations(
                    html_content,
                    features,
                    user_data
                )

                # Progress 100% - Completed
                logger.info("✅ SSE generation completed")
                yield f"data: {json.dumps({'progress': 100, 'status': 'completed', 'message': 'Siap!', 'html': html_content, 'detected_features': features, 'template_used': website_type})}\n\n"

        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error(f"❌ SSE generation failed: {error_msg}")
            logger.error(traceback.format_exc())
            yield f"data: {json.dumps({'progress': 0, 'status': 'failed', 'error': error_msg, 'message': 'Ralat berlaku'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/api/generate-simple")
async def generate_website_simple(request: SimpleGenerateRequest):
    """
    Simple JSON endpoint - No SSE, returns complete result

    This endpoint:
    - Returns regular JSON (not SSE)
    - Uses Stability AI for custom images (if STABILITY_API_KEY is set)
    - Falls back to stock images if Stability unavailable
    - Works perfectly with Render backend
    """
    try:
        logger.info("=" * 80)
        logger.info("🚀 SIMPLE JSON GENERATION REQUEST")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Description: {request.description[:100]}...")
        logger.info("=" * 80)

        # ==================== CONTENT MODERATION ====================
        # Check for illegal/harmful content BEFORE generation
        is_allowed, block_reason = is_content_allowed(request.description)
        if not is_allowed:
            log_blocked_attempt(
                description=request.description,
                reason=block_reason,
                user_id=request.user_id
            )
            return {
                "success": False,
                "error": block_reason,
                "blocked": True,
                "html": "",
                "styles": []
            }
        logger.info("✅ Content moderation check passed")

        # Detect website type
        website_type = template_service.detect_website_type(request.description)
        features = template_service.detect_features(request.description)
        business_name = extract_business_name(request.description)
        language = detect_language(request.description)
        phone_number = extract_phone_number(request.description)
        address = extract_address(request.description)

        logger.info(f"✓ Type={website_type}, Features={features}")

        # Try to generate custom images with Stability AI
        images = None
        if ai_service.stability_api_key:
            logger.info("🎨 Attempting Stability AI image generation...")
            images = await ai_service.generate_business_images(request.description)
            if images:
                logger.info("🎨 ✅ Using Stability AI custom images")
            else:
                logger.info("🎨 ⚠️ Stability AI failed, using fallback")

        # Fallback to stock images
        if not images:
            images = ai_service.get_fallback_images(request.description)
            logger.info("📸 Using stock images")

        # Build AI generation request
        ai_request = WebsiteGenerationRequest(
            description=request.description,
            business_name=business_name,
            business_type=website_type,
            language=language,
            subdomain="preview",
            include_whatsapp=("whatsapp" in features),
            whatsapp_number=phone_number if phone_number else "+60123456789",
            include_maps=("maps" in features),
            location_address=address if address else "",
            include_ecommerce=("cart" in features),
            contact_email=None,
            uploaded_images=images.get("gallery", []),  # Use generated images
            logo=request.logo,
            fonts=request.fonts if request.fonts else [],
            colors=request.colors,
            theme=request.theme
        )

        # User data for integrations
        user_data = {
            "phone": phone_number if phone_number else "+60123456789",
            "address": address if address else "",
            "email": "contact@business.com",
            "url": "https://preview.binaapp.my",
            "whatsapp_message": "Hi, I'm interested"
        }

        # Generate website
        logger.info("🔷 Generating HTML with AI...")
        ai_response = await ai_service.generate_website(ai_request)
        html_content = ai_response.html_content

        # Inject integrations
        html_content = template_service.inject_integrations(
            html_content,
            features,
            user_data
        )

        logger.info("✅ Simple generation complete")

        return {
            "success": True,
            "html": html_content,
            "styles": [{"style": "modern", "html": html_content}],
            "detected_features": features,
            "template_used": website_type
        }

    except Exception as e:
        import traceback
        logger.error("=" * 80)
        logger.error("❌ ERROR IN SIMPLE GENERATION")
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        return {
            "success": False,
            "error": str(e),
            "html": "",
            "styles": []
        }


@router.get("/test-ai")
async def test_ai_connectivity():
    """
    Test AI API connectivity

    This endpoint tests connection to Qwen and DeepSeek APIs
    and returns detailed status information for debugging.
    """
    try:
        logger.info("=" * 80)
        logger.info("🧪 AI CONNECTIVITY TEST REQUESTED")
        logger.info("=" * 80)

        results = await ai_service.test_api_connectivity()

        return {
            "success": True,
            "message": "AI connectivity test completed",
            "results": results
        }
    except Exception as e:
        import traceback
        logger.error(f"AI connectivity test failed: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"Test failed: {str(e)}",
            "results": {}
        }
