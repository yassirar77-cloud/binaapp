"""
Storage Service - Supabase Storage
Handles file uploads and website publishing to Supabase Storage
Uses REST API via supabase_client
"""

from typing import Optional, List, Dict
from loguru import logger

from app.core.config import settings
from app.services.supabase_client import supabase_service


class StorageService:
    """Service for Supabase Storage operations using REST API"""

    def __init__(self):
        self.bucket_name = settings.STORAGE_BUCKET_NAME
        self.supabase = supabase_service
        logger.info(f"Storage service initialized with bucket: {self.bucket_name}")

    async def upload_website(
        self,
        user_id: str,
        subdomain: str,
        html_content: str
    ) -> str:
        """
        Upload website HTML to Supabase Storage

        Uploads to TWO paths for maximum compatibility:
        1. {subdomain}/index.html - for subdomain routing (sitename.binaapp.my)
        2. {user_id}/{subdomain}/index.html - for API preview (/api/preview/...)

        Returns the subdomain URL (e.g., https://kedai-ali.binaapp.my)
        """
        try:
            html_bytes = html_content.encode('utf-8')

            # Path 1: Subdomain-based path for subdomain routing
            subdomain_path = f"{subdomain}/index.html"
            storage_url_1 = await self.supabase.upload_file(
                bucket=self.bucket_name,
                path=subdomain_path,
                file_data=html_bytes,
                content_type="text/html; charset=utf-8"
            )
            logger.info(f"Uploaded to subdomain path: {subdomain_path}")

            # Path 2: User-based path for API preview (backward compatibility)
            user_path = f"{user_id}/{subdomain}/index.html"
            storage_url_2 = await self.supabase.upload_file(
                bucket=self.bucket_name,
                path=user_path,
                file_data=html_bytes,
                content_type="text/html; charset=utf-8"
            )
            logger.info(f"Uploaded to user path: {user_path}")

            if not storage_url_1 and not storage_url_2:
                raise Exception("Upload failed - no URL returned")

            # Return the subdomain URL (e.g., https://kedai-ali.binaapp.my)
            subdomain_url = f"https://{subdomain}.{settings.MAIN_DOMAIN}"

            # Also provide fallback proxy URL for API access
            proxy_url = f"{settings.BACKEND_URL}/api/preview/{user_id}/{subdomain}"

            logger.info(f"Website uploaded successfully!")
            logger.info(f"  Subdomain URL: {subdomain_url}")
            logger.info(f"  Fallback URL: {proxy_url}")

            return subdomain_url

        except Exception as e:
            logger.error(f"Error uploading website: {e}")
            raise

    async def publish_website(
        self,
        subdomain: str,
        html_content: str,
        website_id: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Publish website HTML to Supabase Storage
        Compatibility wrapper for upload_website
        """
        if not user_id:
            user_id = website_id.split('-')[0] if '-' in website_id else subdomain

        return await self.upload_website(user_id, subdomain, html_content)

    async def get_website_url(self, user_id: str, subdomain: str) -> Optional[str]:
        """Get the subdomain URL for an existing website"""
        # Return subdomain URL (e.g., https://kedai-ali.binaapp.my)
        return f"https://{subdomain}.{settings.MAIN_DOMAIN}"

    async def delete_website(self, user_id: str, subdomain: str) -> bool:
        """Delete website files"""
        try:
            file_path = f"{user_id}/{subdomain}/index.html"
            return await self.supabase.delete_file(self.bucket_name, file_path)
        except Exception as e:
            logger.error(f"Error deleting website: {e}")
            return False

    async def get_website_content(self, user_id: str, subdomain: str) -> Optional[str]:
        """Retrieve website HTML content"""
        try:
            file_path = f"{user_id}/{subdomain}/index.html"
            url = await self.supabase.get_file_url(self.bucket_name, file_path)

            if url:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=30.0)
                    if response.status_code == 200:
                        return response.text

            return None
        except Exception as e:
            logger.error(f"Error retrieving website content: {e}")
            return None

    async def check_subdomain_exists(self, subdomain: str) -> bool:
        """
        Check if subdomain already exists
        For now, always return False to allow publishing
        (Real check would require listing all storage folders)
        """
        # TODO: Implement proper subdomain check via database
        return False

    async def list_user_websites(self, user_id: str) -> List[Dict]:
        """List all websites for a user (from database)"""
        try:
            websites = await self.supabase.get_user_websites(user_id)
            return websites or []
        except Exception as e:
            logger.error(f"Error listing user websites: {e}")
            return []


# Create singleton instance
storage_service = StorageService()
