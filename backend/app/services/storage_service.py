"""
Storage Service - Cloudflare R2
Handles file uploads and website publishing to R2
"""

import boto3
from botocore.client import Config
from typing import Optional
from loguru import logger
import mimetypes
from datetime import datetime

from app.core.config import settings


class StorageService:
    """Service for Cloudflare R2 storage operations"""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        self.bucket_name = settings.R2_BUCKET_NAME
        logger.info("Cloudflare R2 storage client initialized")

    async def publish_website(
        self,
        subdomain: str,
        html_content: str,
        website_id: str
    ) -> str:
        """
        Publish website HTML to R2
        Returns the public URL
        """
        try:
            # Create file path: subdomain/index.html
            file_path = f"{subdomain}/index.html"

            # Upload to R2
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=html_content.encode('utf-8'),
                ContentType='text/html',
                CacheControl='public, max-age=3600',
                Metadata={
                    'website-id': website_id,
                    'published-at': datetime.utcnow().isoformat()
                }
            )

            # Make it public (if needed)
            # Note: R2 bucket should be configured with public access
            # or you can set ACL here if supported

            # Generate public URL
            public_url = f"{settings.R2_PUBLIC_URL}/{file_path}"

            logger.info(f"Website published to: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Error publishing website: {e}")
            raise

    async def upload_asset(
        self,
        subdomain: str,
        file_name: str,
        file_content: bytes,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload additional assets (images, CSS, JS)
        """
        try:
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_name)
                content_type = content_type or 'application/octet-stream'

            file_path = f"{subdomain}/assets/{file_name}"

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=content_type,
                CacheControl='public, max-age=31536000'
            )

            asset_url = f"{settings.R2_PUBLIC_URL}/{file_path}"
            logger.info(f"Asset uploaded: {asset_url}")
            return asset_url

        except Exception as e:
            logger.error(f"Error uploading asset: {e}")
            raise

    async def delete_website(self, subdomain: str) -> bool:
        """
        Delete all files for a subdomain
        """
        try:
            # List all objects with subdomain prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{subdomain}/"
            )

            if 'Contents' in response:
                # Delete all objects
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )

                logger.info(f"Deleted website files for subdomain: {subdomain}")

            return True

        except Exception as e:
            logger.error(f"Error deleting website: {e}")
            return False

    async def get_website_content(self, subdomain: str) -> Optional[str]:
        """
        Retrieve published website HTML
        """
        try:
            file_path = f"{subdomain}/index.html"

            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )

            html_content = response['Body'].read().decode('utf-8')
            return html_content

        except Exception as e:
            logger.error(f"Error retrieving website: {e}")
            return None

    async def check_subdomain_exists(self, subdomain: str) -> bool:
        """
        Check if subdomain is already published
        """
        try:
            file_path = f"{subdomain}/index.html"

            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )

            return True

        except self.s3_client.exceptions.ClientError:
            return False


# Create singleton instance
storage_service = StorageService()
