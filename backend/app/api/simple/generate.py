"""
Simple Generate Endpoint
POST /api/generate - Generate website from description
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from app.services.ai_service import ai_service
from app.services.templates import template_service
from app.services.screenshot_service import screenshot_service
from app.models.schemas import WebsiteGenerationRequest, Language

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
    images: Optional[List[str]] = Field(default=[], description="Optional list of uploaded image URLs")
    logo: Optional[str] = Field(default=None, description="Logo URL")
    fonts: Optional[List[str]] = Field(default=[], description="Font names to use (e.g., ['Inter', 'Poppins'])")
    colors: Optional[dict] = Field(default=None, description="Color scheme (primary, secondary, accent)")
    theme: Optional[str] = Field(default=None, description="Detected theme name (e.g., 'Purrfect Paws Theme')")
    multi_style: Optional[bool] = Field(default=False, description="Generate multiple style variations")
    generate_previews: Optional[bool] = Field(default=False, description="Generate preview thumbnails (slower)")
    mode: Optional[str] = Field(default="single", description="Generation mode: 'single', 'dual', 'best', or 'strategic'")


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
