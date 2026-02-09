"""
BinaApp AI Website Rebuild API Endpoints
Trigger, preview, approve/reject website rebuilds.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from app.core.security import get_current_user
from app.services.ai_website_rebuilder import ai_website_rebuilder

router = APIRouter(prefix="/website-rebuild", tags=["Website Rebuild"])


class RejectRequest(BaseModel):
    reason: Optional[str] = ""


@router.post("/{website_id}")
async def trigger_rebuild(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Trigger a website rebuild."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    result = await ai_website_rebuilder.trigger_rebuild(website_id, user_id, "manual")

    if not result:
        raise HTTPException(status_code=500, detail="Bina semula gagal")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "success", "data": result}


@router.get("/{website_id}")
async def get_history(
    website_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get rebuild history for a website."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    history = await ai_website_rebuilder.get_rebuild_history(website_id, user_id)
    return {"status": "success", "data": history, "total": len(history)}


@router.get("/preview/{rebuild_id}")
async def get_preview(
    rebuild_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get before/after preview for a rebuild."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    preview = await ai_website_rebuilder.get_preview(rebuild_id, user_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Pratonton tidak dijumpai")

    return {"status": "success", "data": preview}


@router.post("/{rebuild_id}/approve")
async def approve_rebuild(
    rebuild_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Approve and apply a rebuild."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    result = await ai_website_rebuilder.approve_rebuild(rebuild_id, user_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Gagal meluluskan"))

    return {"status": "success", "message": result.get("message")}


@router.post("/{rebuild_id}/reject")
async def reject_rebuild(
    rebuild_id: str,
    request: RejectRequest,
    current_user: dict = Depends(get_current_user)
):
    """Reject a rebuild."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    result = await ai_website_rebuilder.reject_rebuild(rebuild_id, user_id, request.reason)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Gagal menolak"))

    return {"status": "success", "message": "Bina semula ditolak"}
