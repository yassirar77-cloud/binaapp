from fastapi import APIRouter, File, UploadFile, HTTPException
from supabase import create_client
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        # Read file data
        file_data = await file.read()

        # Generate unique filename
        file_ext = file.filename.split('.')[-1]
        filename = f"{uuid.uuid4()}.{file_ext}"

        # Upload to Supabase Storage
        result = supabase.storage.from_('menu-images').upload(
            filename,
            file_data,
            {"content-type": file.content_type}
        )

        # Get public URL
        url = supabase.storage.from_('menu-images').get_public_url(filename)

        return {
            "success": True,
            "url": url,
            "filename": filename
        }

    except Exception as e:
        print(f"Upload error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
