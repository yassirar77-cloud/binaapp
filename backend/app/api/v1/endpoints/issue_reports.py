"""
"Report Issue → Free Regeneration" endpoints.

User-facing:
    POST /api/v1/websites/{website_id}/report-issue   (owner-only)

Admin (same role='admin' check as unstick_generation/repair):
    GET   /api/v1/admin/issue-reports?status=escalated
    PATCH /api/v1/admin/issue-reports/{report_id}

Everything here is gated behind ISSUE_REPORT_ENABLED (env, default false,
read per-request): with the flag off every endpoint 404s and the rest of
the system behaves exactly as before.

Quota note: this module GRANTS make-good entitlements; it never reads or
writes usage_tracking, subscriptions, payments, or addon rows. The actual
quota bypass at regeneration time lives in websites.py and is keyed off
the report row created here.
"""

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services.issue_report_service import (
    MAX_REPORTS_PER_SITE_24H,
    MAX_REPORTS_PER_USER_24H,
    build_diagnostics,
    issue_free_regen_cap,
    issue_report_enabled,
    issue_report_service,
)
from app.services.subscription_service import subscription_service
from app.services.supabase_client import supabase_service

# Mounted under /websites in router.py so the public path matches the
# regenerate endpoint's shape: POST /api/v1/websites/{id}/report-issue.
router = APIRouter()

# Mounted at the v1 root: /api/v1/admin/issue-reports.
admin_router = APIRouter()


class ReportIssueRequest(BaseModel):
    category: Literal[
        "images_wrong", "text_wrong", "page_broken", "sensitive_content", "other"
    ]
    description: Optional[str] = Field(default=None, max_length=500)


class AdminUpdateReportRequest(BaseModel):
    status: Literal["resolved", "rejected"]
    admin_note: Optional[str] = Field(default=None, max_length=2000)


def _feature_gate() -> None:
    """404 when the flag is off — the feature does not exist."""
    if not issue_report_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )


@router.post("/{website_id}/report-issue")
async def report_issue(
    website_id: str,
    request: ReportIssueRequest,
    current_user: dict = Depends(get_current_user),
):
    """File an issue report on a generated website (owner-only).

    Within the per-site grant cap the report auto-grants one free
    regeneration; beyond it the report escalates to admin review.
    """
    _feature_gate()

    user_id = current_user.get("sub")

    # 1. Ownership — same order as the regenerate endpoint: resolve the
    # row first, 404 if missing, 403 before any other work happens.
    website = await supabase_service.get_website(website_id)
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )
    if website["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to report issues on this website",
        )

    # 2. The site must have at least one completed generation — there is
    # nothing to report (or regenerate for free) otherwise. Legacy rows
    # pre-dating generation_count carry 0 but have html_content.
    has_completed_generation = bool(website.get("html_content")) or (
        (website.get("generation_count") or 0) > 0
    )
    if not has_completed_generation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "no_completed_generation",
                "message": "This website has no completed generation to report an issue on.",
            },
        )

    # 3. Duplicate check BEFORE rate limiting: re-submitting the same
    # complaint returns the existing report and must not eat into (or be
    # blocked by) the 24h budget.
    existing = await issue_report_service.find_existing_open_report(
        website_id, request.category
    )
    if existing:
        logger.info(
            f"📋 Issue report: site={website_id} category={request.category} "
            f"status={existing.get('status')} (duplicate — returning existing "
            f"report {existing.get('id')})"
        )
        return _report_response(existing, website, duplicate=True)

    # 4. Rate limits (DB-counted, 24h fixed windows). Counting failures
    # reject the request — this path mints quota-bypassing grants, so we
    # fail closed rather than risk unlimited grants during an outage.
    try:
        site_count = await issue_report_service.count_recent_reports(
            website_id=website_id
        )
        user_count = await issue_report_service.count_recent_reports(user_id=user_id)
    except Exception as e:
        logger.error(f"[ISSUE REPORT] rate-limit count failed for site={website_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not process the report right now. Please try again shortly.",
        )
    if site_count >= MAX_REPORTS_PER_SITE_24H:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limited",
                "message": f"Maximum {MAX_REPORTS_PER_SITE_24H} reports per site per 24 hours.",
            },
        )
    if user_count >= MAX_REPORTS_PER_USER_24H:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limited",
                "message": f"Maximum {MAX_REPORTS_PER_USER_24H} reports per user per 24 hours.",
            },
        )

    # 5. Auto-grant rule: free_regens_granted < cap → grant; else escalate.
    cap = issue_free_regen_cap()
    granted_so_far = website.get("free_regens_granted") or 0
    report_status = "auto_regen_granted" if granted_so_far < cap else "escalated"

    report_data = {
        "website_id": website_id,
        "user_id": user_id,
        "category": request.category,
        "description": request.description,
        "status": report_status,
        "regen_used": False,
        "diagnostics": build_diagnostics(website),
        "created_at": datetime.utcnow().isoformat(),
    }
    report = await issue_report_service.create_report(report_data)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create issue report",
        )

    if report_status == "auto_regen_granted":
        # Bump the per-site grant counter. If the bump fails we keep the
        # report but demote it to escalated — never hand out an untracked
        # grant (that would let a site exceed the cap).
        bumped = await issue_report_service.increment_free_regens_granted(
            website_id, granted_so_far
        )
        if not bumped:
            logger.error(
                f"[ISSUE REPORT] grant counter bump failed for site={website_id} — "
                f"demoting report {report.get('id')} to escalated"
            )
            await issue_report_service.update_report(
                report["id"], {"status": "escalated"}
            )
            report["status"] = "escalated"
            report_status = "escalated"
        else:
            website = {**website, "free_regens_granted": granted_so_far + 1}

    logger.info(
        f"📋 Issue report: site={website_id} category={request.category} "
        f"status={report_status}"
    )
    return _report_response(report, website)


def _report_response(report: dict, website: dict, duplicate: bool = False) -> dict:
    """Shape the API response for a (possibly pre-existing) report."""
    cap = issue_free_regen_cap()
    regens_remaining = max(0, cap - (website.get("free_regens_granted") or 0))
    if report.get("status") == "auto_regen_granted":
        return {
            "status": "regen_granted",
            "report_id": report.get("id"),
            "regens_remaining": regens_remaining,
            "duplicate": duplicate,
            "message": (
                "Sorry about that — your next regeneration for this site is on us. "
                "Regenerate the website to apply it."
            ),
        }
    return {
        "status": "escalated" if report.get("status") == "escalated" else report.get("status"),
        "report_id": report.get("id"),
        "duplicate": duplicate,
        "message": (
            "Thanks for the report — our team will review this site and get back to you."
        ),
    }


# =====================================================
# ADMIN
# =====================================================


async def _require_admin(current_user: dict) -> str:
    """Same role='admin' check as admin/unstick_generation.py."""
    user_id = current_user.get("sub") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if not await subscription_service._is_admin(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation.",
        )
    return user_id


@admin_router.get("/admin/issue-reports")
async def admin_list_issue_reports(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Issue reports (filterable by status, e.g. ?status=escalated),
    newest first, with embedded site + user + diagnostics metadata."""
    _feature_gate()
    await _require_admin(current_user)
    try:
        reports = await issue_report_service.list_reports(
            status_filter=status_filter, limit=limit, offset=offset
        )
        return {"reports": reports}
    except Exception as e:
        logger.error(f"[ISSUE REPORT] admin list failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list issue reports",
        )


@admin_router.patch("/admin/issue-reports/{report_id}")
async def admin_update_issue_report(
    report_id: str,
    request: AdminUpdateReportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Resolve or reject a report (+ optional admin note)."""
    _feature_gate()
    admin_id = await _require_admin(current_user)

    report = await issue_report_service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue report not found",
        )

    update_data = {
        "status": request.status,
        "admin_note": request.admin_note,
        "resolved_at": datetime.utcnow().isoformat(),
    }
    ok = await issue_report_service.update_report(report_id, update_data)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update issue report",
        )

    logger.info(
        f"📋 Issue report {report_id} set to {request.status} by admin {admin_id}"
    )
    return {"success": True, "report_id": report_id, "status": request.status}
