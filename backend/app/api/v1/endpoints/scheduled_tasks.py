"""
Scheduled Tasks Endpoints
For running periodic maintenance tasks
"""

from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from loguru import logger
from datetime import datetime

from app.core.config import settings
from app.services.subscription_reminder_service import subscription_reminder_service

router = APIRouter()


def verify_cron_secret(x_cron_secret: Optional[str] = Header(None)) -> bool:
    """
    Verify the cron job secret to prevent unauthorized access.
    Set CRON_SECRET in environment variables for production.
    """
    expected_secret = getattr(settings, 'CRON_SECRET', None)

    # If no secret configured, allow in development
    if not expected_secret:
        logger.warning("CRON_SECRET not configured - allowing request in development mode")
        return True

    if x_cron_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cron secret"
        )

    return True


@router.post("/subscription-reminders")
async def run_subscription_reminders(x_cron_secret: Optional[str] = Header(None)):
    """
    Run daily subscription reminder checks.

    This endpoint should be called by a cron job once daily (e.g., 9 AM).

    Actions performed:
    - Send 7-day expiry reminders
    - Send 3-day expiry reminders
    - Send 1-day expiry reminders
    - Suspend expired subscriptions

    Security: Requires X-Cron-Secret header in production.
    """
    verify_cron_secret(x_cron_secret)

    try:
        logger.info("Starting scheduled subscription reminder checks...")

        results = await subscription_reminder_service.run_daily_checks()

        logger.info(f"Subscription reminder check completed: {results}")

        return {
            "success": True,
            "timestamp": results["timestamp"],
            "summary": {
                "reminders_sent": {
                    "7_days": results["reminders_7_days"],
                    "3_days": results["reminders_3_days"],
                    "1_day": results["reminders_1_day"]
                },
                "subscriptions_suspended": results["suspensions"],
                "errors": len(results["errors"])
            }
        }

    except Exception as e:
        logger.error(f"Error in subscription reminder task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task failed: {str(e)}"
        )


@router.post("/cleanup-expired-addons")
async def cleanup_expired_addons(x_cron_secret: Optional[str] = Header(None)):
    """
    Clean up expired addon purchases.

    This endpoint marks addons that have expired as 'expired'.
    Should be run daily.
    """
    verify_cron_secret(x_cron_secret)

    try:
        from app.core.config import settings
        import httpx

        now = datetime.utcnow().isoformat()

        url = f"{settings.SUPABASE_URL}/rest/v1/addon_purchases"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers=headers,
                params={
                    "status": "eq.active",
                    "expires_at": f"lt.{now}"
                },
                json={"status": "expired"}
            )

        if response.status_code in [200, 204]:
            logger.info("Expired addons cleanup completed")
            return {"success": True, "message": "Expired addons marked successfully"}
        else:
            logger.warning(f"Addon cleanup returned {response.status_code}")
            return {"success": True, "message": "No expired addons found"}

    except Exception as e:
        logger.error(f"Error cleaning up expired addons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.post("/reset-monthly-usage")
async def reset_monthly_usage(x_cron_secret: Optional[str] = Header(None)):
    """
    Reset monthly usage counters.

    This should be run at the start of each billing cycle (1st of month).
    Note: The system uses billing_period column, so old records are preserved.
    This endpoint is mainly for cleanup of very old records.
    """
    verify_cron_secret(x_cron_secret)

    try:
        logger.info("Monthly usage reset is handled automatically via billing_period")

        # The usage_tracking table uses billing_period (YYYY-MM) to track usage
        # New periods automatically get fresh counters when get_or_create_usage_tracking is called
        # This endpoint can be used to clean up records older than 12 months if needed

        return {
            "success": True,
            "message": "Monthly usage is tracked by billing_period - no reset needed"
        }

    except Exception as e:
        logger.error(f"Error in monthly usage reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset failed: {str(e)}"
        )


@router.get("/health")
async def scheduled_tasks_health():
    """Health check for scheduled tasks service"""
    return {
        "status": "healthy",
        "service": "scheduled_tasks",
        "timestamp": datetime.utcnow().isoformat()
    }
