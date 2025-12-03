"""
Simple Publish Endpoint
POST /api/publish - Publish website to Supabase Storage
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger
from datetime import datetime
import uuid
import re

from app.services.storage_service import storage_service
from app.services.supabase_client import supabase_service

router = APIRouter()


class PublishRequest(BaseModel):
    """Publish request"""
    html_content: str = Field(..., description="HTML code to publish")
    subdomain: str = Field(
        ...,
        min_length=3,
        max_length=63,
        description="Chosen subdomain name"
    )
    project_name: str = Field(..., min_length=2, max_length=100, description="Project name")
    user_id: str = Field(default="demo-user", description="User ID")


class PublishResponse(BaseModel):
    """Publish response"""
    url: str
    subdomain: str
    project_id: str
    success: bool = True


@router.post("/publish", response_model=PublishResponse)
async def publish_website(request: PublishRequest):
    """
    Publish website to Supabase Storage

    This endpoint:
    - Uploads HTML to Supabase Storage (bucket: websites)
    - File path: {user_id}/{subdomain}/index.html
    - Saves project metadata to database
    - Returns public URL
    - Handles errors (subdomain taken, upload failed)
    """
    try:
        logger.info(f"Publishing website: {request.project_name} ({request.subdomain})")

        # Validate subdomain format
        if not validate_subdomain(request.subdomain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subdomain format. Use only lowercase letters, numbers, and hyphens."
            )

        # Check if subdomain is already taken
        subdomain_exists = await storage_service.check_subdomain_exists(request.subdomain)
        if subdomain_exists:
            logger.warning(f"Subdomain already taken: {request.subdomain}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subdomain '{request.subdomain}' is already taken. Please choose another one."
            )

        # Generate project ID
        project_id = str(uuid.uuid4())

        # Upload to Supabase Storage
        logger.info(f"Uploading to Supabase Storage: {request.user_id}/{request.subdomain}/index.html")
        try:
            public_url = await storage_service.upload_website(
                user_id=request.user_id,
                subdomain=request.subdomain,
                html_content=request.html_content
            )
        except Exception as e:
            logger.error(f"Failed to upload to storage: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload website: {str(e)}"
            )

        # Save project metadata to database
        try:
            project_data = {
                "id": project_id,
                "user_id": request.user_id,
                "business_name": request.project_name,
                "subdomain": request.subdomain,
                "status": "published",
                "html_content": request.html_content,
                "public_url": public_url,
                "published_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            await supabase_service.create_website(project_data)
            logger.info(f"Project metadata saved to database: {project_id}")

        except Exception as e:
            logger.error(f"Failed to save project metadata: {e}")
            # Don't fail the request if metadata save fails
            logger.warning("Website uploaded but metadata save failed")

        logger.info(f"Website published successfully: {public_url}")

        return PublishResponse(
            url=public_url,
            subdomain=request.subdomain,
            project_id=project_id,
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing website: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish website: {str(e)}"
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
