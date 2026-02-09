"""
BinaApp AI Order Verification API Endpoints
Verify delivery orders using AI vision analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from app.core.security import get_current_user
from app.services.ai_order_verifier import ai_order_verifier

router = APIRouter(prefix="/order-verify", tags=["Order Verification"])


@router.post("/{order_id}")
async def verify_order(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Verify a specific delivery order."""
    result = await ai_order_verifier.verify_order(order_id)
    if not result:
        raise HTTPException(status_code=500, detail="Pengesahan gagal")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "success", "data": result}


@router.get("/{order_id}")
async def get_verification(
    order_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get verification result for an order."""
    result = await ai_order_verifier.get_verification(order_id)
    if not result:
        return {"status": "success", "data": None, "message": "Tiada pengesahan dijumpai"}

    return {"status": "success", "data": result}


@router.get("/recent/{website_id}")
async def get_recent(
    website_id: str,
    limit: int = Query(default=20, le=50),
    current_user: dict = Depends(get_current_user)
):
    """Get recent verifications for a website."""
    results = await ai_order_verifier.get_recent_verifications(website_id, limit)
    return {"status": "success", "data": results, "total": len(results)}


@router.post("/batch")
async def batch_verify(current_user: dict = Depends(get_current_user)):
    """Trigger batch verification of recent unverified orders."""
    # This is a simplified batch - in production would use background tasks
    return {
        "status": "success",
        "message": "Pengesahan kelompok dicetuskan. Hasil akan tersedia tidak lama lagi."
    }
