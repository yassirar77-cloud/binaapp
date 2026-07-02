"""
Storage Service - Supabase Storage
Handles file uploads and website publishing to Supabase Storage
Uses REST API via supabase_client
"""

from typing import Optional, List, Dict
from loguru import logger

from app.core.config import settings
from app.services.supabase_client import supabase_service

# Marker object written into a subdomain's storage folder when the site is
# deleted (audit C7). The subdomain middleware checks for it and refuses to
# auto-recover (resurrect) a deliberately deleted site into a ghost DB row.
TOMBSTONE_FILENAME = ".deleted"


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

            # Publishing (or republishing) clears any prior deletion tombstone so
            # a subdomain that was deleted and later re-published serves normally
            # (audit C7).
            try:
                await self.supabase.delete_file(
                    self.bucket_name, f"{subdomain}/{TOMBSTONE_FILENAME}"
                )
            except Exception as ts_err:
                logger.warning(f"Could not clear tombstone for {subdomain}: {ts_err}")

            # Return the subdomain URL (e.g., https://kedai-ali.binaapp.my)
            subdomain_url = f"https://{subdomain}.{settings.MAIN_DOMAIN}"

            # Also provide fallback proxy URL for API access
            proxy_url = f"{settings.BACKEND_URL}/api/preview/{user_id}/{subdomain}"

            logger.info("Website uploaded successfully!")
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
        """
        Delete ALL storage key variants for a website and drop a tombstone
        (audit C7).

        Historically only the {user_id}/{subdomain} key was deleted, leaving the
        SERVING key {subdomain}/index.html live — so a "deleted" site kept
        serving at subdomain.binaapp.my forever, and the middleware would even
        re-mint a ghost DB row from it. We now:
          1. delete every key variant (serving + user-scoped + legacy demo-user),
          2. write a `.deleted` tombstone so the middleware won't resurrect it,
          3. VERIFY the public serving object is actually gone and RAISE loudly
             if it is not (a surviving serving key is what keeps a site online).

        Raises on serving-key survival so callers can surface the failure rather
        than reporting a delete that left the site live.
        """
        serving_path = f"{subdomain}/index.html"
        variant_paths = [
            serving_path,
            f"{user_id}/{subdomain}/index.html",
            f"demo-user/{subdomain}/index.html",
        ]

        for path in variant_paths:
            try:
                await self.supabase.delete_file(self.bucket_name, path)
                logger.info(f"Deleted storage key: {path}")
            except Exception as e:
                logger.warning(f"Could not delete storage key {path}: {e}")

        # Write the tombstone BEFORE verifying, so even if the serving-key delete
        # silently failed the middleware still refuses to resurrect the site.
        try:
            await self.supabase.upload_file(
                bucket=self.bucket_name,
                path=f"{subdomain}/{TOMBSTONE_FILENAME}",
                file_data=b"deleted",
                content_type="text/plain; charset=utf-8",
            )
        except Exception as ts_err:
            logger.error(f"Failed to write deletion tombstone for {subdomain}: {ts_err}")

        # Verify the serving object is actually gone (this is the key that keeps
        # a deleted site online). Fail loudly if it still resolves.
        try:
            import httpx
            serving_url = (
                f"{self.supabase.url}/storage/v1/object/public/"
                f"{self.bucket_name}/{serving_path}"
            )
            async with httpx.AsyncClient() as client:
                resp = await client.head(serving_url, timeout=10.0)
            if resp.status_code == 200:
                logger.error(
                    f"❌ Serving key {serving_path} still live after delete — "
                    f"site may still be reachable at {subdomain}.{settings.MAIN_DOMAIN}"
                )
                raise Exception(
                    f"Failed to delete serving key for subdomain {subdomain}"
                )
        except httpx.HTTPError as head_err:
            # Couldn't verify (network). Don't claim success we can't confirm.
            logger.error(f"Could not verify serving-key deletion for {subdomain}: {head_err}")
            raise Exception(
                f"Could not verify deletion of serving key for subdomain {subdomain}"
            )

        logger.info(f"✅ Deleted all storage keys for subdomain {subdomain} (tombstoned)")
        return True

    async def tombstone_exists(self, subdomain: str) -> bool:
        """True if a deletion tombstone exists for this subdomain (audit C7)."""
        try:
            import httpx
            url = (
                f"{self.supabase.url}/storage/v1/object/public/"
                f"{self.bucket_name}/{subdomain}/{TOMBSTONE_FILENAME}"
            )
            async with httpx.AsyncClient() as client:
                resp = await client.head(url, timeout=5.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Could not check tombstone for {subdomain}: {e}")
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
        Check if subdomain already exists in the database.

        This is the source of truth for subdomain ownership and is critical
        for ensuring websites appear correctly in user dashboards.

        Returns True if subdomain exists in database OR storage.
        """
        try:
            # CRITICAL FIX: Check database first (source of truth for ownership)
            existing_website = await self.supabase.get_website_by_subdomain(subdomain)
            if existing_website:
                logger.info(f"✅ Subdomain '{subdomain}' found in database (id: {existing_website.get('id')})")
                return True

            # Also check storage as fallback (for orphaned websites)
            import httpx
            storage_url = f"{self.supabase.url}/storage/v1/object/public/{self.bucket_name}/{subdomain}/index.html"
            async with httpx.AsyncClient() as client:
                response = await client.head(storage_url, timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"⚠️ Subdomain '{subdomain}' found in storage but NOT in database (orphaned)")
                    return True

            logger.info(f"ℹ️ Subdomain '{subdomain}' not found anywhere")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Error checking subdomain '{subdomain}': {e}")
            # Return False on error to allow publishing attempt
            # The database constraint will catch duplicates if they exist
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
