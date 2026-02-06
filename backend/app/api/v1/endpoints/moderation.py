"""
Image Moderation API Endpoints
Created: 2026-02-06
Purpose: Provide moderation endpoints that can be called before/after upload

This is a NEW endpoint file - does not modify any existing code.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from loguru import logger
from app.services.image_moderation_service import moderate_uploaded_image, check_image_safety

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.post("/check-image")
async def check_image_moderation(file: UploadFile = File(...)):
    """
    Check if an image is safe before uploading

    Use this endpoint to pre-check images before uploading to storage.

    Returns:
        - allowed: True if image is safe
        - message: Malay message explaining result
    """
    try:
        # Read file content
        file_content = await file.read()

        # Check file size (max 10MB)
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Fail terlalu besar. Maksimum 10MB."
            )

        # Check file type
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Jenis fail tidak disokong. Gunakan JPEG, PNG, WebP atau GIF."
            )

        # Run moderation
        result = await moderate_uploaded_image(file_content, file.filename)

        if not result["allowed"]:
            raise HTTPException(
                status_code=400,
                detail=result["message"]
            )

        return {
            "success": True,
            "allowed": True,
            "message": result["message"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MODERATION] Endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ralat moderasi: {str(e)}")


@router.post("/check-url")
async def check_image_url_moderation(image_url: str):
    """
    Check if an image URL contains safe content

    Use this for images already uploaded to check them.
    """
    try:
        result = await check_image_safety(image_url=image_url)

        return {
            "is_safe": result["is_safe"],
            "reason": result["reason"],
            "confidence": result["confidence"],
            "detected_categories": result.get("detected_categories", [])
        }

    except Exception as e:
        logger.error(f"[MODERATION] URL check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ralat moderasi: {str(e)}")
