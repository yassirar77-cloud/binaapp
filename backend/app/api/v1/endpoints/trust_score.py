"""
BinaApp User Trust Score API Endpoints
Trust score retrieval, level checking, and admin recalculation.
"""
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.core.security import get_current_user
from app.services.trust_score_service import trust_score_service

router = APIRouter(prefix="/trust", tags=["Trust Score"])

ADMIN_EMAIL = "yassirar77@gmail.com"


@router.get("/my-score")
async def get_my_score(current_user: dict = Depends(get_current_user)):
    """Get user's trust score with full breakdown."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    score_data = await trust_score_service.get_user_score(user_id)
    return {"status": "success", "data": score_data}


@router.get("/level")
async def get_level(current_user: dict = Depends(get_current_user)):
    """Get just the trust level and multiplier."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    level = await trust_score_service.get_trust_level(user_id)
    return {"status": "success", "data": level}


@router.get("/admin/all")
async def admin_get_all(current_user: dict = Depends(get_current_user)):
    """Admin: Get all trust scores."""
    email = current_user.get("email", "")
    if email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    scores = await trust_score_service.get_all_scores()
    return {"status": "success", "data": scores, "total": len(scores)}


@router.post("/admin/recalculate")
async def admin_recalculate(current_user: dict = Depends(get_current_user)):
    """Admin: Trigger batch recalculation of all trust scores."""
    email = current_user.get("email", "")
    if email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Akses ditolak")

    result = await trust_score_service.batch_recalculate()
    return {
        "status": "success",
        "message": "Pengiraan semula selesai",
        "data": result
    }
