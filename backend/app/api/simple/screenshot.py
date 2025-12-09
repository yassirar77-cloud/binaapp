"""
Screenshot API Endpoint
Handles screenshot generation and export functionality
"""

from fastapi import APIRouter, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger
from io import BytesIO

from app.services.screenshot_service import screenshot_service

router = APIRouter()


class ScreenshotRequest(BaseModel):
    """Screenshot generation request"""
    html_content: str = Field(..., description="HTML content to render")
    width: Optional[int] = Field(default=1200, description="Screenshot width")
    height: Optional[int] = Field(default=800, description="Screenshot height")
    device: Optional[str] = Field(default="desktop", description="Device type: desktop, tablet, mobile")
    full_page: Optional[bool] = Field(default=False, description="Capture full page")


class ThumbnailRequest(BaseModel):
    """Thumbnail generation request"""
    html_content: str = Field(..., description="HTML content to render")
    width: Optional[int] = Field(default=400, description="Thumbnail width")
    height: Optional[int] = Field(default=300, description="Thumbnail height")
    device: Optional[str] = Field(default="desktop", description="Device type")


class SocialPreviewRequest(BaseModel):
    """Social media preview generation request"""
    html_content: str = Field(..., description="HTML content to render")
    business_name: str = Field(..., description="Business name")
    style: Optional[str] = Field(default="modern", description="Design style")


class MultiDeviceRequest(BaseModel):
    """Multi-device screenshot request"""
    html_content: str = Field(..., description="HTML content to render")


class VariationPreviewsRequest(BaseModel):
    """Generate previews for multiple variations"""
    variations: List[dict] = Field(..., description="List of style variations with html")


@router.post("/screenshot")
async def generate_screenshot(request: ScreenshotRequest):
    """
    Generate screenshot from HTML content

    Returns PNG image as response
    """
    try:
        logger.info(f"Generating screenshot: {request.device}, {request.width}x{request.height}")

        screenshot_bytes = await screenshot_service.generate_screenshot(
            html_content=request.html_content,
            width=request.width,
            height=request.height,
            full_page=request.full_page,
            device=request.device
        )

        if not screenshot_bytes:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Screenshot generation not available (Playwright not installed)"
            )

        return Response(
            content=screenshot_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=screenshot-{request.device}.png"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating screenshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate screenshot: {str(e)}"
        )


@router.post("/screenshot/thumbnail")
async def generate_thumbnail(request: ThumbnailRequest):
    """
    Generate thumbnail preview

    Returns PNG image as response
    """
    try:
        logger.info(f"Generating thumbnail: {request.width}x{request.height}")

        thumbnail_bytes = await screenshot_service.generate_thumbnail(
            html_content=request.html_content,
            width=request.width,
            height=request.height,
            device=request.device
        )

        if not thumbnail_bytes:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Thumbnail generation not available"
            )

        return Response(
            content=thumbnail_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=thumbnail.png"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate thumbnail: {str(e)}"
        )


@router.post("/screenshot/social-preview")
async def generate_social_preview(request: SocialPreviewRequest):
    """
    Generate social media preview card (1200x630)

    Returns PNG image as response
    """
    try:
        logger.info(f"Generating social preview for {request.business_name}")

        preview_bytes = await screenshot_service.generate_social_preview(
            html_content=request.html_content,
            business_name=request.business_name,
            style=request.style
        )

        if not preview_bytes:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Social preview generation not available"
            )

        return Response(
            content=preview_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=social-preview-{request.business_name.lower().replace(' ', '-')}.png"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating social preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate social preview: {str(e)}"
        )


@router.post("/screenshot/multi-device")
async def generate_multi_device_screenshots(request: MultiDeviceRequest):
    """
    Generate screenshots for all devices (desktop, tablet, mobile)

    Returns JSON with base64-encoded images
    """
    try:
        logger.info("Generating multi-device screenshots")

        screenshots = await screenshot_service.generate_multi_device_screenshots(
            html_content=request.html_content
        )

        # Convert to base64
        result = {}
        for device, screenshot_bytes in screenshots.items():
            if screenshot_bytes:
                result[device] = screenshot_service.screenshot_to_base64(screenshot_bytes)
            else:
                result[device] = None

        return {
            "success": True,
            "screenshots": result
        }

    except Exception as e:
        logger.error(f"Error generating multi-device screenshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate screenshots: {str(e)}"
        )


@router.post("/screenshot/variation-previews")
async def generate_variation_previews(request: VariationPreviewsRequest):
    """
    Generate preview images for multiple style variations

    Returns variations with added thumbnail and social_preview fields (base64)
    """
    try:
        logger.info(f"Generating previews for {len(request.variations)} variations")

        variations_with_previews = await screenshot_service.generate_variation_previews(
            variations=request.variations
        )

        return {
            "success": True,
            "variations": variations_with_previews
        }

    except Exception as e:
        logger.error(f"Error generating variation previews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate variation previews: {str(e)}"
        )


@router.get("/screenshot/health")
async def screenshot_health():
    """
    Check if screenshot service is available
    """
    try:
        # Check if Playwright is available
        from playwright.async_api import async_playwright

        # Try to initialize browser
        if not screenshot_service.browser:
            await screenshot_service.initialize()

        available = screenshot_service.browser is not None

        return {
            "available": available,
            "service": "playwright",
            "status": "healthy" if available else "unavailable"
        }

    except ImportError:
        return {
            "available": False,
            "service": "playwright",
            "status": "not_installed",
            "message": "Run: pip install playwright && playwright install chromium"
        }
    except Exception as e:
        logger.error(f"Screenshot health check failed: {e}")
        return {
            "available": False,
            "service": "playwright",
            "status": "error",
            "message": str(e)
        }
