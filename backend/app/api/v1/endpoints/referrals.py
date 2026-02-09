"""
BinaApp Referral System API Endpoints
Referral code generation, application, and statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.core.security import get_current_user
from app.services.referral_service import referral_service

router = APIRouter(prefix="/referrals", tags=["Referrals"])


class ApplyReferralRequest(BaseModel):
    code: str


@router.get("/my-code")
async def get_my_code(current_user: dict = Depends(get_current_user)):
    """Get or generate user's referral code."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    code = await referral_service.get_or_create_code(user_id)
    if not code:
        raise HTTPException(status_code=500, detail="Gagal menjana kod rujukan")

    return {"status": "success", "data": code}


@router.post("/apply")
async def apply_referral(
    request: ApplyReferralRequest,
    current_user: dict = Depends(get_current_user)
):
    """Apply a referral code."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    if not request.code or len(request.code) < 5:
        raise HTTPException(status_code=400, detail="Kod rujukan tidak sah")

    result = await referral_service.apply_referral(user_id, request.code.strip().upper())

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Gagal"))

    return {"status": "success", "data": result}


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Get referral statistics and history."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    stats = await referral_service.get_stats(user_id)
    return {"status": "success", "data": stats}
