"""
Preview Endpoint - Serve published websites with correct Content-Type
GET /api/preview/{user_id}/{site_name} - Fetches HTML from Supabase and serves with text/html
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import httpx

from app.core.config import settings

router = APIRouter(tags=["preview"])


@router.get("/preview/{user_id}/{site_name}")
async def preview_site(user_id: str, site_name: str):
    """Serve published website HTML with correct content-type"""
    try:
        # Build the Supabase storage URL
        storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/websites/{user_id}/{site_name}/index.html"

        # Fetch HTML content using httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(storage_url)

            if response.status_code == 200:
                html_content = response.text
                return HTMLResponse(content=html_content, status_code=200)
            else:
                # Try alternative path without /index.html
                alt_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/websites/{user_id}/{site_name}.html"
                response = await client.get(alt_url)

                if response.status_code == 200:
                    html_content = response.text
                    return HTMLResponse(content=html_content, status_code=200)
                else:
                    raise HTTPException(status_code=404, detail="Website not found")

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching website: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading website: {str(e)}")
