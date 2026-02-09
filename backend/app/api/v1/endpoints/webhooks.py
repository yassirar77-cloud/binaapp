"""
BinaApp Webhook API Endpoints
Webhook endpoint management, testing, and delivery logs.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from app.core.security import get_current_user
from app.services.webhook_service import webhook_service, WEBHOOK_EVENTS

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class CreateWebhookRequest(BaseModel):
    url: str
    events: List[str]
    description: Optional[str] = ""


class UpdateWebhookRequest(BaseModel):
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


@router.get("")
async def list_webhooks(current_user: dict = Depends(get_current_user)):
    """List all webhook endpoints."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    endpoints = await webhook_service.get_endpoints(user_id)
    return {
        "status": "success",
        "data": endpoints,
        "available_events": WEBHOOK_EVENTS
    }


@router.post("")
async def create_webhook(
    request: CreateWebhookRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new webhook endpoint."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    if not request.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL mesti bermula dengan https://")

    if not request.events:
        raise HTTPException(status_code=400, detail="Sila pilih sekurang-kurangnya satu event")

    result = await webhook_service.create_endpoint(
        user_id, request.url, request.events, request.description
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Gagal"))

    return {"status": "success", "data": result.get("endpoint"), "secret": result.get("secret")}


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    request: UpdateWebhookRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a webhook endpoint."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    update_data = request.dict(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Tiada data untuk dikemaskini")

    result = await webhook_service.update_endpoint(webhook_id, user_id, update_data)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Gagal"))

    return {"status": "success", "message": "Webhook dikemaskini"}


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a webhook endpoint."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    result = await webhook_service.delete_endpoint(webhook_id, user_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Gagal memadam webhook")

    return {"status": "success", "message": "Webhook dipadam"}


@router.get("/{webhook_id}/logs")
async def get_logs(
    webhook_id: str,
    limit: int = Query(default=50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get delivery logs for a webhook endpoint."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    logs = await webhook_service.get_delivery_logs(webhook_id, user_id, limit)
    return {"status": "success", "data": logs, "total": len(logs)}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Send a test webhook event."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    result = await webhook_service.send_test(webhook_id, user_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Gagal"))

    return {"status": "success", "message": result.get("message")}
