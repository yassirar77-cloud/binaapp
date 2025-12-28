"""
File Upload API
Handles image and document uploads to Cloudinary
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Optional
import httpx
import os
import cloudinary
import cloudinary.uploader
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    logger.info("☁️ Cloudinary configured for uploads")
else:
    logger.warning("☁️ Cloudinary not configured - uploads will fail")

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif", 
    "image/webp", "image/svg+xml", "image/bmp",
    "application/pdf"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload multiple files to Cloudinary"""

    # Check if Cloudinary is configured
    if not CLOUDINARY_CLOUD_NAME:
        raise HTTPException(
            status_code=503,
            detail="Cloudinary not configured"
        )

    uploaded_urls = []

    for file in files:
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not allowed"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds 10MB limit"
            )

        # Upload to Cloudinary
        try:
            import uuid
            file_ext = os.path.splitext(file.filename)[1] if file.filename else ''
            unique_filename = f"{uuid.uuid4()}{file_ext}"

            # Upload to Cloudinary with menu images folder
            result = cloudinary.uploader.upload(
                content,
                folder="binaapp/menu_images",
                public_id=unique_filename.replace(file_ext, ''),
                resource_type="image",
                overwrite=True
            )

            cloudinary_url = result.get('secure_url')

            if not cloudinary_url:
                raise HTTPException(
                    status_code=500,
                    detail=f"Cloudinary upload succeeded but no URL returned for {file.filename}"
                )

            uploaded_urls.append(cloudinary_url)
            logger.info(f"☁️ Uploaded to Cloudinary: {cloudinary_url[:60]}...")

        except Exception as e:
            logger.error(f"☁️ Upload error for {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Upload error for {file.filename}: {str(e)}"
            )

    return {
        "success": True,
        "files": uploaded_urls,
        "urls": uploaded_urls,  # Alias for compatibility
        "count": len(uploaded_urls)
    }


@router.post("/upload-image")
async def upload_single_image(file: UploadFile = File(...)):
    """Upload a single image file to Cloudinary - returns secure URL"""

    # Check if Cloudinary is configured
    if not CLOUDINARY_CLOUD_NAME:
        raise HTTPException(
            status_code=503,
            detail="Cloudinary not configured"
        )

    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File {file.filename} exceeds 10MB limit"
        )

    # Upload to Cloudinary
    try:
        import uuid
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ''
        unique_filename = f"{uuid.uuid4()}{file_ext}"

        # Upload to Cloudinary with user uploads folder
        result = cloudinary.uploader.upload(
            content,
            folder="binaapp/user_uploads",
            public_id=unique_filename.replace(file_ext, ''),  # Remove extension, Cloudinary adds it
            resource_type="image",
            overwrite=True
        )

        # Get secure URL
        cloudinary_url = result.get('secure_url')

        if not cloudinary_url:
            raise HTTPException(
                status_code=500,
                detail="Cloudinary upload succeeded but no URL returned"
            )

        logger.info(f"☁️ Uploaded to Cloudinary: {cloudinary_url[:60]}...")

        return {
            "success": True,
            "url": cloudinary_url,
            "filename": unique_filename,
            "cloudinary_public_id": result.get('public_id')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"☁️ Cloudinary upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload error: {str(e)}"
        )


@router.post("/upload-images")
async def upload_images(
    hero: UploadFile = File(None),
    gallery1: UploadFile = File(None),
    gallery2: UploadFile = File(None),
    gallery3: UploadFile = File(None),
    gallery4: UploadFile = File(None),
):
    """Upload user images to Cloudinary (hero + gallery images)"""

    # Check if Cloudinary is configured
    if not CLOUDINARY_CLOUD_NAME:
        raise HTTPException(
            status_code=503,
            detail="Cloudinary not configured"
        )

    uploaded_urls = {}

    files = {
        "hero": hero,
        "gallery1": gallery1,
        "gallery2": gallery2,
        "gallery3": gallery3,
        "gallery4": gallery4,
    }

    for key, file in files.items():
        if file and file.filename:
            try:
                # Validate file type
                if file.content_type not in ALLOWED_TYPES:
                    logger.warning(f"☁️ Skipping {key}: invalid type {file.content_type}")
                    continue

                # Read file content
                contents = await file.read()

                # Validate file size
                if len(contents) > MAX_FILE_SIZE:
                    logger.warning(f"☁️ Skipping {key}: file too large ({len(contents)} bytes)")
                    continue

                # Upload to Cloudinary
                import uuid
                file_ext = os.path.splitext(file.filename)[1] if file.filename else ''
                unique_filename = f"{uuid.uuid4()}{file_ext}"

                result = cloudinary.uploader.upload(
                    contents,
                    folder="binaapp/user-uploads",
                    public_id=unique_filename.replace(file_ext, ''),
                    resource_type="image",
                    overwrite=True
                )

                cloudinary_url = result.get('secure_url')

                if cloudinary_url:
                    uploaded_urls[key] = cloudinary_url
                    logger.info(f"☁️ Uploaded {key}: {cloudinary_url[:50]}...")
                else:
                    logger.error(f"☁️ Upload succeeded for {key} but no URL returned")

            except Exception as e:
                logger.error(f"☁️ Upload failed for {key}: {e}")

    return {
        "success": True,
        "uploaded_urls": uploaded_urls,
        "count": len(uploaded_urls)
    }