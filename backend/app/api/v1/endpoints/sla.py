"""
BinaApp AI SLA System API Endpoints
Service Level Agreement monitoring and breach tracking.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from loguru import logger

from app.core.security import get_current_user
from app.services.ai_sla_service import sla_service

router = APIRouter(prefix="/sla", tags=["SLA"])


@router.get("/my-sla")
async def get_my_sla(current_user: dict = Depends(get_current_user)):
    """Get user's SLA definition based on their subscription plan."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    sla = await sla_service.get_user_sla(user_id)
    if not sla:
        return {"plan_name": "free", "message": "Tiada SLA untuk pelan percuma"}

    return {"status": "success", "data": sla}


@router.get("/breaches")
async def get_breaches(
    limit: int = Query(default=50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Get user's SLA breach history."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    breaches = await sla_service.get_breaches(user_id, limit=limit)
    return {"status": "success", "data": breaches, "total": len(breaches)}


@router.get("/compliance")
async def get_compliance(current_user: dict = Depends(get_current_user)):
    """Get current month SLA compliance report."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    report = await sla_service.get_compliance_report(user_id)
    return {"status": "success", "data": report}


@router.post("/check")
async def manual_check(current_user: dict = Depends(get_current_user)):
    """Manually trigger SLA compliance check."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Pengesahan diperlukan")

    # Get compliance report as a check result
    report = await sla_service.get_compliance_report(user_id)
    return {
        "status": "success",
        "message": "Semakan SLA selesai",
        "data": report
    }
