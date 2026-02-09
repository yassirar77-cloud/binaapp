"""
BinaApp AI Chat Settings API Endpoints
Configure AI auto-respond for customer chats.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from app.core.security import get_current_user
from app.services.ai_chat_responder import ai_chat_responder

router = APIRouter(prefix="/ai-chat-settings", tags=["AI Chat Settings"])


class ChatSettingsUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    delay_seconds: Optional[int] = None
    custom_greeting: Optional[str] = None
    personality: Optional[str] = None
    auto_respond_hours: Optional[dict] = None


@router.get("/{website_id}")
async def get_settings(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get AI chat settings for a website."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    settings = await ai_chat_responder.get_chat_settings(website_id)
    if not settings:
        # Return defaults
        settings = {
            "website_id": website_id,
            "is_enabled": False,
            "delay_seconds": 120,
            "custom_greeting": "Salam! Saya BinaBot, pembantu AI kedai ini. Ada apa yang boleh saya bantu?",
            "personality": "friendly",
            "auto_respond_hours": {"start": 0, "end": 24}
        }

    return {"status": "success", "data": settings}


@router.post("/{website_id}")
async def update_settings(
    website_id: str,
    request: ChatSettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update AI chat settings for a website."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    update_data = request.dict(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Tiada data untuk dikemaskini")

    result = await ai_chat_responder.update_chat_settings(website_id, user_id, update_data)
    if not result:
        raise HTTPException(status_code=500, detail="Gagal mengemaskini tetapan")

    return {"status": "success", "data": result}


@router.get("/{website_id}/responses")
async def get_responses(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get AI response history for a website."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    responses = await ai_chat_responder.get_response_history(website_id)
    return {"status": "success", "data": responses, "total": len(responses)}


@router.post("/process-pending")
async def process_pending(current_user: dict = Depends(get_current_user)):
    """Trigger batch processing of pending messages."""
    results = await ai_chat_responder.process_pending_messages()
    return {"status": "success", "data": results}
