"""
BinaApp Restaurant Penalty System API Endpoints
Penalty management, appeals, and admin resolution.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from loguru import logger

from app.core.security import get_current_user
from app.services.restaurant_penalty_service import restaurant_penalty_service

router = APIRouter(tags=["Penalties"])

ADMIN_EMAIL = "yassirar77@gmail.com"


class AppealRequest(BaseModel):
    reason: str
    evidence: Optional[str] = None


class ResolveRequest(BaseModel):
    note: Optional[str] = ""


@router.get("/penalties/my-penalties")
async def get_my_penalties(current_user: dict = Depends(get_current_user)):
    """Get user's penalties."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    penalties = await restaurant_penalty_service.get_user_penalties(user_id)
    return {"status": "success", "data": penalties, "total": len(penalties)}


@router.post("/penalties/{penalty_id}/appeal")
async def submit_appeal(
    penalty_id: str,
    request: AppealRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit appeal for a penalty."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    result = await restaurant_penalty_service.submit_appeal(
        penalty_id, user_id, request.reason, request.evidence
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Gagal"))

    return {"status": "success", "data": result.get("appeal")}


@router.get("/admin/penalties")
async def admin_get_all(current_user: dict = Depends(get_current_user)):
    """Admin: Get all penalties."""
    email = current_user.get("email", "")
    if email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    penalties = await restaurant_penalty_service.get_all_penalties()
    return {"status": "success", "data": penalties, "total": len(penalties)}


@router.post("/admin/penalties/{penalty_id}/resolve")
async def admin_resolve(
    penalty_id: str,
    request: ResolveRequest,
    current_user: dict = Depends(get_current_user)
):
    """Admin: Resolve/revoke a penalty."""
    email = current_user.get("email", "")
    if email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    result = await restaurant_penalty_service.resolve_penalty(
        penalty_id, email, request.note
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail="Gagal menyelesaikan penalti")

    return {"status": "success", "message": "Penalti berjaya diselesaikan"}
