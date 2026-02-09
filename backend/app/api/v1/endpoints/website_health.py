"""
AI Website Health API Endpoints
Handles website scanning, fix generation, and fix application.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from app.core.security import get_current_user
from app.services.ai_website_doctor import website_doctor

router = APIRouter(prefix="/website-health", tags=["Website Health"])
bearer_scheme = HTTPBearer()


@router.post("/scan/{website_id}")
async def trigger_scan(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Trigger a manual website health scan."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await website_doctor.scan_website(website_id, user_id, scan_type="manual")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail="Scan failed")


@router.get("/scans/{website_id}")
async def get_scan_history(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get scan history for a website."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        result = supabase.table("website_health_scans").select("*").eq(
            "website_id", website_id
        ).eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()

        return {"scans": result.data or []}
    except Exception as e:
        logger.error(f"Failed to get scan history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scan history")


@router.get("/scan/{scan_id}")
async def get_scan_details(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get single scan details."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        result = supabase.table("website_health_scans").select("*").eq(
            "id", scan_id
        ).eq("user_id", user_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Scan not found")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scan details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scan details")


@router.get("/fixes/{scan_id}")
async def get_fixes(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get fixes for a scan."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        result = supabase.table("website_fixes").select("*").eq(
            "scan_id", scan_id
        ).eq("user_id", user_id).order("severity").execute()

        return {"fixes": result.data or []}
    except Exception as e:
        logger.error(f"Failed to get fixes: {e}")
        raise HTTPException(status_code=500, detail="Failed to get fixes")


@router.post("/fix/{fix_id}/generate")
async def generate_fix(
    fix_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Generate code fix for a specific issue."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await website_doctor.generate_fix(fix_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Fix generation failed: {e}")
        raise HTTPException(status_code=500, detail="Fix generation failed")


@router.post("/fix/{fix_id}/apply")
async def apply_fix(
    fix_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Apply a specific fix (user approved)."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await website_doctor.apply_fix(fix_id, applied_by="user_approved")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Fix application failed: {e}")
        raise HTTPException(status_code=500, detail="Fix application failed")


@router.post("/fix/{fix_id}/reject")
async def reject_fix(
    fix_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Reject a fix."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        from app.core.supabase import get_supabase_client
        supabase = get_supabase_client()

        supabase.table("website_fixes").update({
            "status": "rejected",
        }).eq("id", fix_id).eq("user_id", user_id).execute()

        return {"message": "Fix rejected", "fix_id": fix_id}
    except Exception as e:
        logger.error(f"Fix rejection failed: {e}")
        raise HTTPException(status_code=500, detail="Fix rejection failed")


@router.post("/auto-fix/{scan_id}")
async def auto_fix_safe_issues(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Auto-fix all safe issues for a scan."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await website_doctor.auto_fix_safe_issues(scan_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Auto-fix failed: {e}")
        raise HTTPException(status_code=500, detail="Auto-fix failed")


@router.post("/fix/{fix_id}/revert")
async def revert_fix(
    fix_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Revert an applied fix."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        result = await website_doctor.revert_fix(fix_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Fix revert failed: {e}")
        raise HTTPException(status_code=500, detail="Fix revert failed")
