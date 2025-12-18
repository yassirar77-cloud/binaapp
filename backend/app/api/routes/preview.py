"""
Preview Endpoint - Serve published websites with correct Content-Type
GET /api/preview/{user_id}/{site_name} - Fetches HTML from Supabase and serves with text/html
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import httpx
from loguru import logger

from app.core.config import settings

router = APIRouter(tags=["preview"])


@router.get("/preview/{user_id}/{site_name}")
async def preview_site(user_id: str, site_name: str):
    """Serve published website HTML with correct content-type"""
    try:
        logger.info(f"Preview requested for: {user_id}/{site_name}")

        # Build the Supabase storage URL
        storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/websites/{user_id}/{site_name}/index.html"

        # Fetch HTML content using httpx with timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"Fetching from: {storage_url}")
            response = await client.get(storage_url)

            logger.info(f"Storage response status: {response.status_code}")

            if response.status_code == 200:
                html_content = response.text
                return HTMLResponse(content=html_content, status_code=200)
            else:
                # Try alternative paths
                alt_paths = [
                    f"{settings.SUPABASE_URL}/storage/v1/object/public/websites/{user_id}/{site_name}.html",
                    f"{settings.SUPABASE_URL}/storage/v1/object/public/websites/{site_name}/index.html",
                ]

                for alt_url in alt_paths:
                    logger.info(f"Trying alternative: {alt_url}")
                    alt_response = await client.get(alt_url)
                    if alt_response.status_code == 200:
                        return HTMLResponse(content=alt_response.text, status_code=200)

                # Return user-friendly 404 page
                return HTMLResponse(
                    content=f"""
                    <!DOCTYPE html>
                    <html lang="ms">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Website Tidak Dijumpai</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f9fafb; }}
                            .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                            h1 {{ color: #333; }}
                            p {{ color: #666; }}
                            a {{ color: #667eea; text-decoration: none; font-weight: bold; }}
                            a:hover {{ text-decoration: underline; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Website Tidak Dijumpai</h1>
                            <p>Website '<strong>{site_name}</strong>' tidak wujud atau belum diterbitkan.</p>
                            <p><a href="https://binaapp.my">← Kembali ke BinaApp</a></p>
                        </div>
                    </body>
                    </html>
                    """,
                    status_code=404
                )

    except httpx.TimeoutException:
        logger.error("Timeout fetching website")
        raise HTTPException(status_code=504, detail="Timeout loading website")
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching website: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading website: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading website: {str(e)}")
