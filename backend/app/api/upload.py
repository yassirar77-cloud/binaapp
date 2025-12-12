"""
File Upload API
Handles image and document uploads to Supabase Storage
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import httpx
import os
from app.core.config import settings

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/gif", 
    "image/webp", "image/svg+xml", "image/bmp",
    "application/pdf"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload multiple files to Supabase Storage"""
    
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
        
        # Generate unique filename
        import uuid
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Upload to Supabase Storage using REST API
        try:
            url = f"{settings.SUPABASE_URL}/storage/v1/object/menu-images/{unique_filename}"
            
            headers = {
                "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": file.content_type
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    content=content,
                    timeout=30.0
                )
            
            if response.status_code in [200, 201]:
                # Return public URL
                public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/menu-images/{unique_filename}"
                uploaded_urls.append(public_url)
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Upload failed: {response.text}"
                )
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Upload error: {str(e)}"
            )
    
    return {
        "success": True,
        "files": uploaded_urls,
        "count": len(uploaded_urls)
    }