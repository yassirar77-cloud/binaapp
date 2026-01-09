"""
Website Endpoints
Handles website generation, management, and publishing
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import List
from loguru import logger
from datetime import datetime
import uuid

from app.models.schemas import (
    WebsiteGenerationRequest,
    WebsiteResponse,
    WebsiteListResponse,
    PublishRequest,
    PublishResponse,
    WebsiteStatus
)
from app.services.supabase_client import supabase_service
from app.services.ai_service import ai_service
from app.services.storage_service import storage_service
from app.services.templates import TemplateService
from app.core.security import get_current_user
from app.core.config import settings

router = APIRouter()


@router.post("/generate", response_model=WebsiteResponse, status_code=status.HTTP_201_CREATED)
async def generate_website(
    request: WebsiteGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a new website using AI
    """
    try:
        user_id = current_user.get("sub")

        # Check subdomain availability
        subdomain_available = await supabase_service.check_subdomain_available(request.subdomain)
        if not subdomain_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subdomain already taken"
            )

        # Check if storage also has this subdomain
        storage_exists = await storage_service.check_subdomain_exists(request.subdomain)
        if storage_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subdomain already exists in storage"
            )

        # Create website record
        website_id = str(uuid.uuid4())
        website_data = {
            "id": website_id,
            "user_id": user_id,
            "business_name": request.business_name,
            "business_type": request.business_type,
            "subdomain": request.subdomain,
            "status": WebsiteStatus.GENERATING,
            "language": request.language,
            "include_whatsapp": request.include_whatsapp,
            "whatsapp_number": request.whatsapp_number,
            "include_maps": request.include_maps,
            "location_address": request.location_address,
            "include_ecommerce": request.include_ecommerce,
            "contact_email": request.contact_email,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        website = await supabase_service.create_website(website_data)

        # Generate website in background
        background_tasks.add_task(
            generate_website_content,
            website_id,
            request
        )

        logger.info(f"Website generation started: {website_id}")

        return WebsiteResponse(
            id=website["id"],
            user_id=website["user_id"],
            business_name=website["business_name"],
            subdomain=website["subdomain"],
            full_url=f"https://{request.subdomain}{settings.SUBDOMAIN_SUFFIX}",
            status=WebsiteStatus.GENERATING,
            created_at=datetime.fromisoformat(website["created_at"]),
            updated_at=datetime.fromisoformat(website["updated_at"]),
            published_at=None,
            html_content=None,
            preview_url=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate website"
        )


async def generate_website_content(website_id: str, request: WebsiteGenerationRequest):
    """
    Background task to generate website content using AI
    """
    try:
        # Generate HTML using AI
        ai_response = await ai_service.generate_website(request)

        html_content = ai_response.html_content
        integrations = ai_response.integrations_included

        # CRITICAL: Inject delivery widget if ecommerce/delivery is enabled
        if request.include_ecommerce:
            logger.info(f"🛒 Delivery mode enabled - injecting delivery widget for website {website_id}")

            # Initialize template service
            template_service = TemplateService()

            # Inject delivery widget with website_id
            html_content = template_service.inject_delivery_widget(
                html=html_content,
                website_id=website_id,
                whatsapp_number=request.whatsapp_number or "+60123456789",
                primary_color="#ea580c",  # Default orange color
                business_type=request.business_type,
                description=request.description,
                language=request.language.value if hasattr(request, 'language') and request.language else "ms"
            )

            # Update integrations list to include delivery
            integrations = ["BinaApp Delivery", "WhatsApp Contact", "Mobile Responsive", "Cloudinary Images"]
            logger.info(f"✅ Delivery widget injected successfully for website {website_id}")

        # Update website with generated content
        update_data = {
            "html_content": html_content,
            "status": WebsiteStatus.DRAFT,
            "meta_title": ai_response.meta_title,
            "meta_description": ai_response.meta_description,
            "sections": ai_response.sections,
            "integrations": integrations,
            "updated_at": datetime.utcnow().isoformat()
        }

        await supabase_service.update_website(website_id, update_data)

        logger.info(f"Website content generated successfully: {website_id}")

    except Exception as e:
        logger.error(f"Error in background generation: {e}")

        # Mark website as failed
        await supabase_service.update_website(website_id, {
            "status": WebsiteStatus.FAILED,
            "error_message": str(e),
            "updated_at": datetime.utcnow().isoformat()
        })


@router.get("/", response_model=List[WebsiteListResponse])
async def list_websites(current_user: dict = Depends(get_current_user)):
    """
    Get all websites for the current user
    """
    try:
        user_id = current_user.get("sub")
        websites = await supabase_service.get_user_websites(user_id)

        return [
            WebsiteListResponse(
                id=w["id"],
                business_name=w["business_name"],
                subdomain=w["subdomain"],
                full_url=f"https://{w['subdomain']}{settings.SUBDOMAIN_SUFFIX}",
                status=w["status"],
                created_at=datetime.fromisoformat(w["created_at"]),
                published_at=datetime.fromisoformat(w["published_at"]) if w.get("published_at") else None
            )
            for w in websites
        ]

    except Exception as e:
        logger.error(f"Error listing websites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve websites"
        )


@router.get("/{website_id}", response_model=WebsiteResponse)
async def get_website(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific website by ID
    """
    try:
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        # Check ownership
        if website["user_id"] != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this website"
            )

        return WebsiteResponse(
            id=website["id"],
            user_id=website["user_id"],
            business_name=website["business_name"],
            subdomain=website["subdomain"],
            full_url=f"https://{website['subdomain']}{settings.SUBDOMAIN_SUFFIX}",
            status=website["status"],
            created_at=datetime.fromisoformat(website["created_at"]),
            updated_at=datetime.fromisoformat(website["updated_at"]),
            published_at=datetime.fromisoformat(website["published_at"]) if website.get("published_at") else None,
            html_content=website.get("html_content"),
            preview_url=website.get("preview_url")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve website"
        )


@router.post("/{website_id}/publish", response_model=PublishResponse)
async def publish_website(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Publish website to subdomain
    """
    try:
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        # Check ownership
        if website["user_id"] != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to publish this website"
            )

        # Check if website is ready to publish
        if website["status"] != WebsiteStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Website is not ready to publish"
            )

        if not website.get("html_content"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Website has no content to publish"
            )

        # Publish to Supabase Storage
        public_url = await storage_service.publish_website(
            subdomain=website["subdomain"],
            html_content=website["html_content"],
            website_id=website_id,
            user_id=current_user.get("sub")
        )

        # Update website status
        published_at = datetime.utcnow()
        await supabase_service.update_website(website_id, {
            "status": WebsiteStatus.PUBLISHED,
            "published_at": published_at.isoformat(),
            "public_url": public_url,
            "updated_at": published_at.isoformat()
        })

        logger.info(f"Website published: {website_id} -> {public_url}")

        full_url = f"https://{website['subdomain']}{settings.SUBDOMAIN_SUFFIX}"

        return PublishResponse(
            success=True,
            url=full_url,
            message="Website published successfully",
            published_at=published_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish website"
        )


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_website(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a website
    """
    try:
        website = await supabase_service.get_website(website_id)

        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found"
            )

        # Check ownership
        if website["user_id"] != current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this website"
            )

        # Delete from storage if published
        if website["status"] == WebsiteStatus.PUBLISHED:
            await storage_service.delete_website(
                user_id=current_user.get("sub"),
                subdomain=website["subdomain"]
            )

        # Delete from database
        await supabase_service.delete_website(website_id)

        logger.info(f"Website deleted: {website_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete website"
        )
