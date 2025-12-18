"""
Preview Endpoint - Serve published websites as HTML
GET /api/preview/{user_id}/{site_id} - Serves HTML with proper Content-Type
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger
import httpx

from app.core.config import settings

router = APIRouter()


@router.get("/preview/{user_id}/{site_id}", response_class=HTMLResponse)
async def preview_site(user_id: str, site_id: str):
    """
    Serve published website HTML with proper Content-Type header.

    This endpoint acts as a proxy to serve HTML files from Supabase Storage
    with the correct Content-Type (text/html) so browsers render them properly.
    """
    try:
        # Construct the Supabase Storage URL
        file_path = f"{user_id}/{site_id}/index.html"
        storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.STORAGE_BUCKET_NAME}/{file_path}"

        logger.info(f"Serving preview: {file_path}")

        # Fetch the HTML content from Supabase Storage
        async with httpx.AsyncClient() as client:
            response = await client.get(storage_url, timeout=30.0)

            if response.status_code == 200:
                html_content = response.text
                logger.info(f"Successfully served preview: {file_path} ({len(html_content)} chars)")
                return HTMLResponse(
                    content=html_content,
                    status_code=200,
                    headers={
                        "Content-Type": "text/html; charset=utf-8",
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            elif response.status_code == 404:
                logger.warning(f"Website not found: {file_path}")
                raise HTTPException(status_code=404, detail="Website not found")
            else:
                logger.error(f"Failed to fetch website: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch website: {response.status_code}"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving preview: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading website: {str(e)}")
