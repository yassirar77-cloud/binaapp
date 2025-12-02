"""
Storage Service - Supabase Storage
Handles file uploads and website publishing to Supabase Storage
"""

from typing import Optional, List, Dict
from loguru import logger
from datetime import datetime

from app.core.config import settings
from app.services.supabase_client import supabase_service


class StorageService:
    """Service for Supabase Storage operations"""

    def __init__(self):
        self.bucket_name = settings.STORAGE_BUCKET_NAME
        self.supabase = supabase_service.client
        logger.info(f"Supabase Storage client initialized with bucket: {self.bucket_name}")

    async def upload_website(
        self,
        user_id: str,
        subdomain: str,
        html_content: str
    ) -> str:
        """
        Upload website HTML to Supabase Storage
        File structure: {user_id}/{subdomain}/index.html
        Returns the public URL
        """
        try:
            # Create file path
            file_path = f"{user_id}/{subdomain}/index.html"

            # Upload to Supabase Storage (upsert - will overwrite if exists)
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=html_content.encode('utf-8'),
                file_options={
                    "content-type": "text/html",
                    "cache-control": "3600",
                    "upsert": "true"  # Allow overwriting existing files
                }
            )

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)

            logger.info(f"Website uploaded successfully: {file_path} -> {public_url}")
            return public_url

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
        This method maintains compatibility with existing code
        """
        try:
            # If user_id not provided, extract from website_id or use subdomain
            if not user_id:
                user_id = website_id.split('-')[0] if '-' in website_id else subdomain

            return await self.upload_website(user_id, subdomain, html_content)

        except Exception as e:
            logger.error(f"Error publishing website: {e}")
            raise

    async def get_website_url(self, user_id: str, subdomain: str) -> Optional[str]:
        """
        Get the public URL for an existing website
        """
        try:
            file_path = f"{user_id}/{subdomain}/index.html"

            # Check if file exists
            try:
                files = self.supabase.storage.from_(self.bucket_name).list(f"{user_id}/{subdomain}")
                if not any(f['name'] == 'index.html' for f in files):
                    return None
            except Exception:
                return None

            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)
            return public_url

        except Exception as e:
            logger.error(f"Error getting website URL: {e}")
            return None

    async def delete_website(self, user_id: str, subdomain: str) -> bool:
        """
        Delete all files for a website
        """
        try:
            # List all files in the subdomain directory
            file_path_prefix = f"{user_id}/{subdomain}"

            try:
                # List files
                files = self.supabase.storage.from_(self.bucket_name).list(file_path_prefix)

                if files:
                    # Delete each file
                    file_paths = [f"{file_path_prefix}/{f['name']}" for f in files]
                    self.supabase.storage.from_(self.bucket_name).remove(file_paths)

                    logger.info(f"Deleted website files for: {file_path_prefix}")

                # Also try to delete the index.html directly
                self.supabase.storage.from_(self.bucket_name).remove([f"{file_path_prefix}/index.html"])

            except Exception as e:
                logger.warning(f"Error listing/deleting files: {e}")
                # Try direct deletion
                try:
                    self.supabase.storage.from_(self.bucket_name).remove([f"{file_path_prefix}/index.html"])
                except Exception:
                    pass

            return True

        except Exception as e:
            logger.error(f"Error deleting website: {e}")
            return False

    async def list_user_websites(self, user_id: str) -> List[Dict]:
        """
        List all websites for a user
        Returns list of website info dictionaries
        """
        try:
            # List all folders under user_id
            folders = self.supabase.storage.from_(self.bucket_name).list(user_id)

            websites = []
            for folder in folders:
                if folder.get('name'):
                    subdomain = folder['name']
                    url = await self.get_website_url(user_id, subdomain)
                    if url:
                        websites.append({
                            'subdomain': subdomain,
                            'url': url,
                            'updated_at': folder.get('updated_at')
                        })

            return websites

        except Exception as e:
            logger.error(f"Error listing user websites: {e}")
            return []

    async def get_website_content(self, user_id: str, subdomain: str) -> Optional[str]:
        """
        Retrieve website HTML content
        """
        try:
            file_path = f"{user_id}/{subdomain}/index.html"

            # Download file
            response = self.supabase.storage.from_(self.bucket_name).download(file_path)

            if response:
                html_content = response.decode('utf-8')
                return html_content

            return None

        except Exception as e:
            logger.error(f"Error retrieving website content: {e}")
            return None

    async def check_subdomain_exists(self, subdomain: str) -> bool:
        """
        Check if subdomain is already published (across all users)
        Note: This is less efficient with new structure but maintains compatibility
        """
        try:
            # List all top-level folders (user IDs)
            folders = self.supabase.storage.from_(self.bucket_name).list()

            for folder in folders:
                user_id = folder.get('name')
                if user_id:
                    try:
                        # Check if this subdomain exists for this user
                        subfolders = self.supabase.storage.from_(self.bucket_name).list(user_id)
                        if any(sf.get('name') == subdomain for sf in subfolders):
                            return True
                    except Exception:
                        continue

            return False

        except Exception as e:
            logger.error(f"Error checking subdomain: {e}")
            return False

    async def upload_asset(
        self,
        user_id: str,
        subdomain: str,
        file_name: str,
        file_content: bytes,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload additional assets (images, CSS, JS)
        """
        try:
            file_path = f"{user_id}/{subdomain}/assets/{file_name}"

            # Upload asset
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": content_type or "application/octet-stream",
                    "cache-control": "31536000",
                    "upsert": "true"
                }
            )

            # Get public URL
            asset_url = self.supabase.storage.from_(self.bucket_name).get_public_url(file_path)

            logger.info(f"Asset uploaded: {file_path}")
            return asset_url

        except Exception as e:
            logger.error(f"Error uploading asset: {e}")
            raise


# Create singleton instance
storage_service = StorageService()
