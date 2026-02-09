"""
BinaApp Smart Notifications API Endpoints
In-app notifications and web push subscription management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict
from loguru import logger

from app.core.security import get_current_user
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: Dict[str, str]


@router.get("")
async def get_notifications(
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    type_filter: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user)
):
    """Get paginated notifications."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    notifications = await notification_service.get_notifications(
        user_id, limit=limit, offset=offset, type_filter=type_filter
    )
    return {"status": "success", "data": notifications, "total": len(notifications)}


@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get unread notification count for badge display."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    count = await notification_service.get_unread_count(user_id)
    return {"status": "success", "data": {"count": count}}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    success = await notification_service.mark_read(notification_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pemberitahuan tidak dijumpai")

    return {"status": "success", "message": "Ditandakan sebagai dibaca"}


@router.post("/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    await notification_service.mark_all_read(user_id)
    return {"status": "success", "message": "Semua pemberitahuan ditandakan sebagai dibaca"}


@router.post("/push-subscribe")
async def push_subscribe(
    request: PushSubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Register a push notification subscription."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    success = await notification_service.register_push_subscription(
        user_id,
        {"endpoint": request.endpoint, "keys": request.keys}
    )

    if not success:
        raise HTTPException(status_code=500, detail="Gagal mendaftar langganan push")

    return {"status": "success", "message": "Langganan push berjaya didaftarkan"}
