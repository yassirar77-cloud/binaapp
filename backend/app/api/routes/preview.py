"""
Preview Endpoint - Serve published websites with correct Content-Type
GET /api/preview/{user_id}/{site_name} - Fetches HTML from Supabase and serves with text/html
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from loguru import logger
from supabase import create_client

from app.core.config import settings

router = APIRouter(tags=["preview"])


@router.get("/preview/{user_id}/{site_name}")
async def preview_site(user_id: str, site_name: str):
    """
    Serve published website HTML with correct Content-Type header.

    Supabase Storage cannot serve HTML files with proper Content-Type,
    so this endpoint acts as a proxy to fetch and serve with text/html.
    """
    try:
        logger.info(f"Serving preview: {user_id}/{site_name}")

        # Create Supabase client
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        # Try primary path: {user_id}/{site_name}/index.html
        file_path = f"{user_id}/{site_name}/index.html"
        html_content = None

        try:
            response = supabase.storage.from_("websites").download(file_path)
            html_content = response.decode('utf-8')
            logger.info(f"Found HTML at: {file_path}")
        except Exception as e:
            logger.warning(f"Primary path failed: {file_path} - {e}")

            # Try alternative path: {user_id}/{site_name}.html
            try:
                alt_path = f"{user_id}/{site_name}.html"
                response = supabase.storage.from_("websites").download(alt_path)
                html_content = response.decode('utf-8')
                logger.info(f"Found HTML at alternative path: {alt_path}")
            except Exception as e2:
                logger.error(f"Alternative path also failed: {alt_path} - {e2}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Website not found. Tried: {file_path} and {alt_path}"
                )

        if not html_content:
            raise HTTPException(status_code=404, detail="Website content is empty")

        logger.info(f"Successfully serving preview: {user_id}/{site_name} ({len(html_content)} chars)")

        return HTMLResponse(
            content=html_content,
            status_code=200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "public, max-age=3600"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving preview: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading website: {str(e)}")
