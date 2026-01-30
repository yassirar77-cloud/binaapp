"""
Email Polling API Endpoints
Admin endpoints to control and monitor the email polling service
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger

from app.core.security import get_current_user

router = APIRouter(prefix="/email/polling", tags=["Email Polling"])


class PollingStatusResponse(BaseModel):
    """Response model for polling status"""
    service_available: bool
    scheduler_running: bool
    last_poll_time: str | None
    last_poll_status: str
    emails_processed_today: int
    errors_today_count: int
    recent_errors: list
    polling_interval_seconds: int
    next_scheduled_run: str | None
    imap_server: str
    email_account: str


class PollingActionResponse(BaseModel):
    """Response model for polling actions"""
    success: bool
    message: str
    timestamp: str


class ManualPollResponse(BaseModel):
    """Response model for manual poll trigger"""
    success: bool
    message: str
    emails_found: int
    emails_processed: int
    emails_escalated: int
    errors: list


class ConnectionTestResponse(BaseModel):
    """Response model for connection test"""
    success: bool
    message: str
    server: str
    port: int
    email: str
    inbox_messages: int | None = None
    inbox_unseen: int | None = None


@router.get("/status", response_model=PollingStatusResponse)
async def get_polling_status(current_user: dict = Depends(get_current_user)):
    """
    Get the current status of the email polling service

    Returns:
        - Service availability
        - Whether scheduler is running
        - Last poll time and status
        - Emails processed today
        - Error counts and recent errors
        - Next scheduled run time
    """
    from app.services.email_polling_service import email_polling_service
    from app.core.scheduler import email_polling_scheduler

    service_status = email_polling_service.get_status()
    scheduler_status = email_polling_scheduler.get_status()

    return PollingStatusResponse(
        service_available=service_status["is_available"],
        scheduler_running=scheduler_status["is_running"],
        last_poll_time=service_status["last_poll_time"],
        last_poll_status=service_status["last_poll_status"],
        emails_processed_today=service_status["emails_processed_today"],
        errors_today_count=service_status["errors_today_count"],
        recent_errors=service_status["recent_errors"],
        polling_interval_seconds=service_status["polling_interval_seconds"],
        next_scheduled_run=scheduler_status.get("next_run_time"),
        imap_server=service_status["imap_server"],
        email_account=service_status["email_account"]
    )


@router.post("/start", response_model=PollingActionResponse)
async def start_polling(current_user: dict = Depends(get_current_user)):
    """
    Start the email polling scheduler

    Admin only - starts periodic polling of the support inbox
    """
    from app.core.scheduler import email_polling_scheduler, start_email_polling

    # Check if already running
    if email_polling_scheduler.is_running:
        return PollingActionResponse(
            success=True,
            message="Email polling scheduler is already running",
            timestamp=datetime.utcnow().isoformat()
        )

    # Start polling
    success = await start_email_polling()

    if success:
        logger.info(f"Email polling started by user: {current_user.get('email', 'unknown')}")
        return PollingActionResponse(
            success=True,
            message="Email polling scheduler started successfully",
            timestamp=datetime.utcnow().isoformat()
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to start email polling. Check logs and configuration."
        )


@router.post("/stop", response_model=PollingActionResponse)
async def stop_polling(current_user: dict = Depends(get_current_user)):
    """
    Stop the email polling scheduler

    Admin only - stops periodic polling
    """
    from app.core.scheduler import email_polling_scheduler

    if not email_polling_scheduler.is_running:
        return PollingActionResponse(
            success=True,
            message="Email polling scheduler is not running",
            timestamp=datetime.utcnow().isoformat()
        )

    success = email_polling_scheduler.stop()

    if success:
        logger.info(f"Email polling stopped by user: {current_user.get('email', 'unknown')}")
        return PollingActionResponse(
            success=True,
            message="Email polling scheduler stopped successfully",
            timestamp=datetime.utcnow().isoformat()
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to stop email polling scheduler"
        )


@router.post("/restart", response_model=PollingActionResponse)
async def restart_polling(current_user: dict = Depends(get_current_user)):
    """
    Restart the email polling scheduler

    Admin only - stops and starts the polling scheduler
    """
    from app.core.scheduler import email_polling_scheduler

    success = email_polling_scheduler.restart()

    if success:
        logger.info(f"Email polling restarted by user: {current_user.get('email', 'unknown')}")
        return PollingActionResponse(
            success=True,
            message="Email polling scheduler restarted successfully",
            timestamp=datetime.utcnow().isoformat()
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to restart email polling scheduler"
        )


@router.post("/trigger", response_model=ManualPollResponse)
async def trigger_poll(current_user: dict = Depends(get_current_user)):
    """
    Manually trigger an immediate poll

    Admin only - useful for testing or processing emails immediately
    """
    from app.core.scheduler import email_polling_scheduler

    logger.info(f"Manual poll triggered by user: {current_user.get('email', 'unknown')}")

    result = await email_polling_scheduler.trigger_now()

    if result.get("success"):
        poll_result = result.get("result", {})
        return ManualPollResponse(
            success=True,
            message="Manual poll completed successfully",
            emails_found=poll_result.get("emails_found", 0),
            emails_processed=poll_result.get("emails_processed", 0),
            emails_escalated=poll_result.get("emails_escalated", 0),
            errors=poll_result.get("errors", [])
        )
    else:
        return ManualPollResponse(
            success=False,
            message=result.get("message", "Manual poll failed"),
            emails_found=0,
            emails_processed=0,
            emails_escalated=0,
            errors=[{"error": result.get("error", "Unknown error")}]
        )


@router.get("/test-connection", response_model=ConnectionTestResponse)
async def test_imap_connection(current_user: dict = Depends(get_current_user)):
    """
    Test the IMAP connection without processing emails

    Admin only - verifies IMAP server connectivity and credentials
    """
    from app.services.email_polling_service import email_polling_service

    logger.info(f"IMAP connection test requested by user: {current_user.get('email', 'unknown')}")

    result = await email_polling_service.test_connection()

    return ConnectionTestResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        server=result.get("server", ""),
        port=result.get("port", 0),
        email=result.get("email", ""),
        inbox_messages=result.get("inbox_messages"),
        inbox_unseen=result.get("inbox_unseen")
    )


@router.get("/health")
async def polling_health_check():
    """
    Health check endpoint for the email polling service

    Public endpoint - useful for monitoring systems
    """
    from app.services.email_polling_service import email_polling_service
    from app.core.scheduler import email_polling_scheduler

    service_available = email_polling_service.is_available()
    scheduler_running = email_polling_scheduler.is_running
    last_poll = email_polling_service.last_poll_time
    last_status = email_polling_service.last_poll_status

    # Determine health status
    health_status = "healthy"
    issues = []

    if not service_available:
        health_status = "degraded"
        issues.append("Email polling service not available")

    if not scheduler_running:
        health_status = "degraded"
        issues.append("Scheduler not running")

    if last_status == "error":
        health_status = "unhealthy"
        issues.append("Last poll resulted in error")

    # Check if last poll was too long ago (more than 2x the interval)
    if last_poll:
        from datetime import timedelta
        max_age = timedelta(seconds=email_polling_service.polling_interval * 2)
        if datetime.utcnow() - last_poll > max_age:
            health_status = "unhealthy"
            issues.append("Last poll was too long ago")

    return {
        "status": health_status,
        "service_available": service_available,
        "scheduler_running": scheduler_running,
        "last_poll_time": last_poll.isoformat() if last_poll else None,
        "last_poll_status": last_status,
        "issues": issues
    }
