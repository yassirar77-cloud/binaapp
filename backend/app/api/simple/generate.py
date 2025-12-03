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


class SimpleGenerateResponse(BaseModel):
    """Simplified generation response"""
    html: str
    detected_features: List[str]
    template_used: str
    success: bool = True


@router.post("/generate", response_model=SimpleGenerateResponse)
async def generate_website(request: SimpleGenerateRequest):
    """
    Generate complete website from description

    This endpoint:
    - Accepts description in Bahasa Malaysia or English
    - Detects website type automatically
    - Auto-injects integrations based on detected features
    - Returns complete, functional HTML
    """
    try:
        logger.info(f"Generating website for user: {request.user_id}")
        logger.info(f"Description: {request.description[:100]}...")

        # Detect website type
        website_type = template_service.detect_website_type(request.description)
        logger.info(f"Detected website type: {website_type}")

        # Detect required features
        features = template_service.detect_features(request.description)
        logger.info(f"Detected features: {features}")

        # Extract business name from description (simple extraction)
        business_name = extract_business_name(request.description)

        # Detect language
        language = detect_language(request.description)

        # Extract phone number if mentioned
        phone_number = extract_phone_number(request.description)

        # Extract address if mentioned
        address = extract_address(request.description)

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
            contact_email=None
        )

        # Generate website using AI
        logger.info("Calling AI service to generate website...")
        ai_response = await ai_service.generate_website(ai_request)

        # Get the generated HTML
        html_content = ai_response.html_content

        # Inject additional integrations
        user_data = {
            "phone": phone_number if phone_number else "+60123456789",
            "address": address if address else "",
            "email": "contact@business.com",
            "url": "https://preview.binaapp.my",
            "whatsapp_message": "Hi, I'm interested"
        }

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
        logger.error(f"Error generating website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate website: {str(e)}"
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
