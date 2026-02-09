"""
AI Chatbot Support API Endpoints
Handles AI-powered support conversations with vision capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger
import uuid
import os

from app.core.security import get_current_user
from app.services.ai_chatbot_service import chatbot_service

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])
bearer_scheme = HTTPBearer()


class StartChatRequest(BaseModel):
    website_id: Optional[str] = None
    order_id: Optional[str] = None


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    image_urls: Optional[List[str]] = None


class RateChatRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


@router.post("/start")
async def start_chat(
    request: StartChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start a new support chat."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await chatbot_service.start_chat(
            user_id=user_id,
            website_id=request.website_id,
            order_id=request.order_id,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to start chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to start chat")


@router.post("/{chat_id}/message")
async def send_message(
    chat_id: str,
    request: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Send a message (text + optional images)."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await chatbot_service.chat(
            chat_id=chat_id,
            user_id=user_id,
            user_message=request.message,
            image_urls=request.image_urls,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.get("/{chat_id}/messages")
async def get_messages(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get chat history."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        messages = await chatbot_service.get_chat_messages(chat_id, user_id)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to get messages")


@router.get("/active")
async def get_active_chats(
    current_user: dict = Depends(get_current_user),
):
    """Get user's active chats."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        chats = await chatbot_service.get_active_chats(user_id)
        return {"chats": chats}
    except Exception as e:
        logger.error(f"Failed to get active chats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active chats")


@router.post("/{chat_id}/close")
async def close_chat(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Close a chat."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await chatbot_service.close_chat(chat_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to close chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to close chat")


@router.post("/{chat_id}/rate")
async def rate_chat(
    chat_id: str,
    request: RateChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Rate satisfaction (1-5)."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await chatbot_service.rate_chat(chat_id, user_id, request.rating)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rate chat: {e}")
        raise HTTPException(status_code=500, detail="Failed to rate chat")


@router.post("/{chat_id}/upload-image")
async def upload_chat_image(
    chat_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload an image for the chat support."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, WebP, and GIF are allowed.")

    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    try:
        from app.services.supabase_client import SupabaseService
        svc = SupabaseService()

        ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        file_path = f"ai-support/{user_id}/{chat_id}/{uuid.uuid4()}.{ext}"

        url = await svc.upload_file(
            bucket="dispute-evidence",
            path=file_path,
            file_data=contents,
            content_type=file.content_type or "image/jpeg",
        )

        if not url:
            raise HTTPException(status_code=500, detail="Upload failed")

        return {"url": url, "filename": file.filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(status_code=500, detail="Image upload failed")
