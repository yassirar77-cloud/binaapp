"""Admin endpoint to manually unstick a website stuck on 'generating'.

The scheduled sweeper in core/scheduler.py handles the common case (worker
restart leaves a row dangling), but operators occasionally need a manual
escape hatch — e.g. when the sweeper hasn't run yet, or when a row's
updated_at is artificially fresh because someone else touched it.

Endpoint: POST /api/v1/admin/websites/{website_id}/unstick-generation
Auth:     role='admin' in public.users (same check as repair-websites).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.core.security import get_current_user
from app.services.subscription_service import subscription_service
from app.services.supabase_client import supabase_service


router = APIRouter()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/admin/websites/{website_id}/unstick-generation")
async def unstick_generation(
    website_id: str,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Force a website off status='generating' into 'failed'.

    Behaviour:
      - 401 if no user.
      - 403 if caller is not admin.
      - 404 if website doesn't exist.
      - 400 if status is anything other than 'generating'
            (the response payload includes the current status so the
            operator can confirm what they were about to clobber).
      - 200 with the updated row otherwise.
    """
    user_id = current_user.get("sub") or current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    is_admin = await subscription_service._is_admin(user_id)
    if not is_admin:
        logger.warning(
            f"🛑 unstick-generation called by non-admin user_id={user_id} "
            f"website_id={website_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation.",
        )

    website = await supabase_service.get_website(website_id)
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )

    current_status = website.get("status")
    if current_status != "generating":
        # Don't silently 200 on a no-op: if the operator thought it was
        # stuck and it isn't, they need to know what they actually saw.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "not_generating",
                "message": (
                    "Website is not in 'generating' status — nothing to "
                    "unstick."
                ),
                "current_status": current_status,
            },
        )

    update_payload = {
        "status": "failed",
        "error_message": (
            "Generation manually unstuck by admin — worker likely "
            "restarted mid-generation. Please regenerate."
        ),
        "last_heartbeat_at": None,
        "updated_at": _utcnow_iso(),
    }
    ok = await supabase_service.update_website(website_id, update_payload)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update website status",
        )

    logger.warning(
        f"[admin-unstick] user_id={user_id} flipped website_id={website_id} "
        f"from 'generating' to 'failed' (subdomain={website.get('subdomain')})"
    )

    refreshed = await supabase_service.get_website(website_id) or {}
    return {
        "ok": True,
        "website_id": website_id,
        "previous_status": "generating",
        "new_status": refreshed.get("status", "failed"),
        "subdomain": refreshed.get("subdomain"),
        "error_message": refreshed.get("error_message"),
        "updated_at": refreshed.get("updated_at"),
    }
