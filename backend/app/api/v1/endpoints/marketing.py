"""
Marketing attribution endpoints for binaapp.my (migration 067).

  POST /api/v1/marketing/visit    public, fire-and-forget visit counter
  GET  /api/v1/marketing/summary  admin only: visits and signups by source
"""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from loguru import logger
from pydantic import BaseModel, Field

from app.core.admin import require_admin
from app.services.analytics_tracking import is_bot_user_agent
from app.services.marketing_attribution import load_summary, record_visit

router = APIRouter(prefix="/marketing", tags=["Marketing"])


class VisitPayload(BaseModel):
    utm_source: Optional[str] = Field(None, max_length=200)
    utm_medium: Optional[str] = Field(None, max_length=200)
    utm_campaign: Optional[str] = Field(None, max_length=200)
    utm_content: Optional[str] = Field(None, max_length=200)
    ref: Optional[str] = Field(None, max_length=200)
    referrer: Optional[str] = Field(None, max_length=500)
    landing_path: Optional[str] = Field(None, max_length=500)


@router.post("/visit", status_code=204)
async def track_visit(
    payload: VisitPayload, request: Request, background_tasks: BackgroundTasks
):
    """Count one visit to binaapp.my. Always 204; the write happens after
    the response. Bots and DNT / Global Privacy Control visitors are dropped."""
    headers = request.headers
    if headers.get("dnt") == "1" or headers.get("sec-gpc") == "1":
        return Response(status_code=204)
    if is_bot_user_agent(headers.get("user-agent", "")):
        return Response(status_code=204)
    background_tasks.add_task(record_visit, payload.model_dump())
    return Response(status_code=204)


@router.get("/summary")
async def marketing_summary(
    days: int = Query(30, ge=1, le=365),
    _admin: dict = Depends(require_admin),
):
    """Visits, signups and paying signups per source for the last N days."""
    try:
        return {"success": True, "data": await load_summary(days)}
    except Exception as e:
        logger.error(f"marketing summary failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Gagal memuatkan data marketing")
