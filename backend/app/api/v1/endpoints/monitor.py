"""
AI Proactive Monitor API Endpoints
Handles monitoring events, restaurant health, and check triggers.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from loguru import logger
from typing import Optional

from app.core.security import get_current_user
from app.services.ai_proactive_monitor import proactive_monitor

router = APIRouter(prefix="/monitor", tags=["Monitor"])
bearer_scheme = HTTPBearer()

ADMIN_EMAILS = [e.strip() for e in os.getenv("ADMIN_EMAILS", "yassirar77@gmail.com").split(",")]


@router.get("/events")
async def get_monitor_events(
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Get user's monitor events (paginated)."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await proactive_monitor.get_user_events(
            user_id=user_id,
            limit=limit,
            offset=offset,
            event_type=event_type,
            severity=severity,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get monitor events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitor events")


@router.post("/events/{event_id}/acknowledge")
async def acknowledge_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Mark event as acknowledged."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await proactive_monitor.acknowledge_event(event_id, user_id)
        return result
    except Exception as e:
        logger.error(f"Failed to acknowledge event: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge event")


@router.get("/restaurant-health/{website_id}")
async def get_restaurant_health(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get restaurant health metrics."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        result = supabase.table("restaurant_health").select("*").eq(
            "website_id", website_id
        ).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Restaurant health data not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get restaurant health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get restaurant health")


@router.post("/run-checks")
async def run_checks(
    current_user: dict = Depends(get_current_user),
):
    """Manually trigger all monitoring checks (admin only)."""
    user_email = current_user.get("email", "")
    if user_email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        result = await proactive_monitor.run_all_checks()
        return {"status": "completed", "results": result}
    except Exception as e:
        logger.error(f"Monitor checks failed: {e}")
        raise HTTPException(status_code=500, detail="Monitor checks failed")


@router.get("/summary")
async def get_monitoring_summary(
    current_user: dict = Depends(get_current_user),
):
    """Get user's monitoring summary."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await proactive_monitor.get_monitoring_summary(user_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get monitoring summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring summary")
