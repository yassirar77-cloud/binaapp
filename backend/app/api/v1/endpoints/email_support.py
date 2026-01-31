"""
AI Email Support API Endpoints
Handles email webhooks, thread management, and admin controls
"""

import httpx
from fastapi import APIRouter, HTTPException, status, Depends, Request, Query, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.core.security import get_current_user
from app.core.config import settings
from app.services.ai_email_support import ai_email_support
from app.services.email_service import email_service

router = APIRouter()

# Database helpers
DB_URL = settings.SUPABASE_URL
DB_KEY = settings.SUPABASE_SERVICE_ROLE_KEY
DB_HEADERS = {
    "apikey": DB_KEY,
    "Authorization": f"Bearer {DB_KEY}",
    "Content-Type": "application/json"
}


async def db_select(table: str, filters: Optional[Dict[str, str]] = None,
                    select: str = "*", order_by: Optional[str] = None,
                    limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict]:
    """Select records from database"""
    try:
        url = f"{DB_URL}/rest/v1/{table}"
        params = {"select": select}
        if filters:
            params.update(filters)
        if order_by:
            params["order"] = order_by
        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=DB_HEADERS, params=params, timeout=30.0)
        if response.status_code == 200:
            return response.json()
        logger.error(f"DB select failed: {response.status_code} - {response.text}")
        return []
    except Exception as e:
        logger.error(f"DB select error: {e}")
        return []


async def db_select_one(table: str, filters: Dict[str, str], select: str = "*") -> Optional[Dict]:
    """Select single record from database"""
    results = await db_select(table, filters, select, limit=1)
    return results[0] if results else None


async def db_update(table: str, filters: Dict[str, str], data: Dict[str, Any]) -> bool:
    """Update records in database"""
    try:
        url = f"{DB_URL}/rest/v1/{table}"
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                headers={**DB_HEADERS, "Prefer": "return=minimal"},
                params=filters,
                json=data,
                timeout=30.0
            )
        return response.status_code in [200, 204]
    except Exception as e:
        logger.error(f"DB update error: {e}")
        return False


async def db_count(table: str, filters: Optional[Dict[str, str]] = None) -> int:
    """Count records in database"""
    try:
        url = f"{DB_URL}/rest/v1/{table}"
        params = {"select": "id"}
        if filters:
            params.update(filters)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={**DB_HEADERS, "Prefer": "count=exact"},
                params=params,
                timeout=30.0
            )
        if response.status_code == 200:
            # Count is in content-range header
            content_range = response.headers.get("content-range", "")
            if "/" in content_range:
                return int(content_range.split("/")[1])
            return len(response.json())
        return 0
    except Exception as e:
        logger.error(f"DB count error: {e}")
        return 0


# =====================================================
# Pydantic Models
# =====================================================

class EmailWebhookPayload(BaseModel):
    """Payload from email forwarding webhook (Zoho/generic)"""
    from_email: EmailStr = Field(..., alias="from")
    from_name: Optional[str] = Field(None, alias="fromName")
    to_email: Optional[EmailStr] = Field(None, alias="to")
    subject: str
    body_text: Optional[str] = Field(None, alias="text")
    body_html: Optional[str] = Field(None, alias="html")
    message_id: Optional[str] = Field(None, alias="messageId")
    date: Optional[str] = None

    class Config:
        populate_by_name = True


class ZohoWebhookPayload(BaseModel):
    """Zoho-specific webhook payload format"""
    fromAddress: EmailStr
    toAddress: Optional[EmailStr] = None
    ccAddress: Optional[str] = None
    subject: str
    content: Optional[str] = None
    htmlContent: Optional[str] = None
    sender: Optional[str] = None
    messageId: Optional[str] = None
    receivedTime: Optional[str] = None


class ManualReplyRequest(BaseModel):
    """Request for admin manual reply"""
    content: str = Field(..., min_length=1)
    mark_resolved: bool = False


class SettingsUpdateRequest(BaseModel):
    """Request to update AI support settings"""
    ai_enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    response_tone: Optional[str] = None
    auto_reply_enabled: Optional[bool] = None
    escalation_email: Optional[EmailStr] = None
    max_ai_turns: Optional[int] = Field(None, ge=1, le=10)


class ThreadResponse(BaseModel):
    """Response model for email thread"""
    id: str
    customer_email: str
    customer_name: Optional[str]
    subject: str
    status: str
    priority: str
    category: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None


class MessageResponse(BaseModel):
    """Response model for email message"""
    id: str
    sender_email: str
    sender_type: str
    content: str
    ai_generated: bool
    ai_confidence: Optional[float]
    created_at: datetime


# =====================================================
# Webhook Endpoints (Public)
# =====================================================

@router.post("/webhook", status_code=status.HTTP_200_OK)
async def receive_email_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receive incoming emails from Zoho forwarding or other email services.

    This endpoint accepts various webhook formats and processes
    the email through the AI support system.

    Setup for Zoho:
    1. Go to Zoho Mail → Settings → Email Forwarding
    2. Add forwarding rule to: https://api.binaapp.my/api/v1/email/webhook
    3. Select "Forward as HTTP POST"
    """
    try:
        # Parse the request body
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            body = await request.json()
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            body = dict(form)
        else:
            body = await request.json()

        logger.info(f"Email webhook received: {list(body.keys())}")

        # Extract email data (handle both generic and Zoho formats)
        sender_email = body.get("from") or body.get("fromAddress") or body.get("from_email")
        sender_name = body.get("fromName") or body.get("sender") or body.get("from_name")
        subject = body.get("subject", "No Subject")
        body_text = body.get("text") or body.get("content") or body.get("body_text") or ""
        body_html = body.get("html") or body.get("htmlContent") or body.get("body_html")

        if not sender_email:
            logger.warning("Webhook received without sender email")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing sender email address"
            )

        # Extract name from email if not provided
        if not sender_name and "<" in str(sender_email):
            # Format: "Name <email@example.com>"
            parts = str(sender_email).split("<")
            sender_name = parts[0].strip().strip('"')
            sender_email = parts[1].rstrip(">")

        # Process email in background to return quickly
        background_tasks.add_task(
            ai_email_support.process_incoming_email,
            sender_email=sender_email,
            sender_name=sender_name,
            subject=subject,
            body=body_text,
            html_body=body_html
        )

        logger.info(f"Email from {sender_email} queued for processing")

        return {
            "status": "received",
            "message": "Email queued for processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing email webhook: {e}")
        # Still return 200 to prevent email service retries
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/webhook/test", status_code=status.HTTP_200_OK)
async def test_email_webhook():
    """
    Test endpoint to verify webhook is accessible.
    Use this to test your Zoho forwarding setup.
    """
    return {
        "status": "ok",
        "message": "Email webhook is working",
        "timestamp": datetime.utcnow().isoformat(),
        "ai_available": ai_email_support.is_available()
    }


# =====================================================
# Thread Management Endpoints (Admin Only)
# =====================================================

@router.get("/threads", response_model=Dict[str, Any])
async def list_email_threads(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    category_filter: Optional[str] = Query(None, alias="category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict = Depends(get_current_user)
):
    """
    List all email support threads.

    Admin only endpoint for viewing customer support threads.
    Supports filtering by status, priority, and category.
    """
    try:
        # Build filters
        filters = {}
        if status_filter:
            filters["status"] = f"eq.{status_filter}"
        if priority_filter:
            filters["priority"] = f"eq.{priority_filter}"
        if category_filter:
            filters["category"] = f"eq.{category_filter}"

        # Pagination
        offset = (page - 1) * page_size

        # Get threads
        threads = await db_select(
            "email_threads",
            filters=filters,
            order_by="created_at.desc",
            limit=page_size,
            offset=offset
        )

        # Get total count
        total = await db_count("email_threads", filters)

        return {
            "threads": threads,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error listing email threads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email threads"
        )


@router.get("/threads/{thread_id}")
async def get_email_thread(
    thread_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get a specific email thread with all messages.

    Includes:
    - Thread metadata
    - All messages in chronological order
    - AI decisions and escalation history
    """
    try:
        # Get thread
        thread = await db_select_one("email_threads", {"id": f"eq.{thread_id}"})

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )

        # Get messages
        messages = await db_select(
            "email_messages",
            filters={"thread_id": f"eq.{thread_id}"},
            order_by="created_at.asc"
        )

        # Get escalations
        escalations = await db_select(
            "ai_escalations",
            filters={"thread_id": f"eq.{thread_id}"},
            order_by="escalated_at.desc"
        )

        return {
            "thread": thread,
            "messages": messages,
            "escalations": escalations
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email thread: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thread"
        )


@router.post("/threads/{thread_id}/reply")
async def send_manual_reply(
    thread_id: str,
    request: ManualReplyRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Send a manual reply to an email thread.

    Admin can compose and send a custom response to the customer.
    Optionally marks the thread as resolved.
    """
    try:
        # Get thread
        thread = await db_select_one("email_threads", {"id": f"eq.{thread_id}"})

        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found"
            )

        # Send email
        sent = await ai_email_support.send_reply(
            to_email=thread["customer_email"],
            to_name=thread["customer_name"] or "Customer",
            subject=thread["subject"],
            content=request.content,
            thread_id=thread_id
        )

        if not sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email"
            )

        # Track the message
        admin_email = current_user.get("email", settings.ADMIN_EMAIL)
        await ai_email_support.track_conversation(
            customer_email=thread["customer_email"],
            customer_name=thread["customer_name"],
            subject=thread["subject"],
            message_content=request.content,
            sender_type="admin",
            thread_id=thread_id
        )

        # Update thread status
        new_status = "resolved" if request.mark_resolved else "in_progress"
        update_data = {
            "status": new_status,
            "assigned_to": admin_email
        }
        if request.mark_resolved:
            update_data["resolved_at"] = datetime.utcnow().isoformat()

        await db_update("email_threads", {"id": f"eq.{thread_id}"}, update_data)

        # Resolve any open escalations
        if request.mark_resolved:
            await db_update(
                "ai_escalations",
                {"thread_id": f"eq.{thread_id}", "resolved_at": "is.null"},
                {
                    "resolved_at": datetime.utcnow().isoformat(),
                    "resolved_by": admin_email
                }
            )

        return {
            "success": True,
            "message": "Reply sent successfully",
            "thread_status": new_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending manual reply: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reply"
        )


@router.put("/threads/{thread_id}/status")
async def update_thread_status(
    thread_id: str,
    new_status: str = Query(..., pattern="^(open|in_progress|resolved|escalated|closed)$"),
    current_user: Dict = Depends(get_current_user)
):
    """Update the status of an email thread."""
    try:
        update_data = {"status": new_status}
        if new_status == "resolved":
            update_data["resolved_at"] = datetime.utcnow().isoformat()

        success = await db_update("email_threads", {"id": f"eq.{thread_id}"}, update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or update failed"
            )

        return {"success": True, "status": new_status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating thread status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update status"
        )


# =====================================================
# Escalation Management
# =====================================================

@router.get("/escalations")
async def list_escalations(
    resolved: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Dict = Depends(get_current_user)
):
    """List AI escalations for review."""
    try:
        filters = {}
        if resolved is not None:
            if resolved:
                filters["resolved_at"] = "not.is.null"
            else:
                filters["resolved_at"] = "is.null"

        offset = (page - 1) * page_size

        escalations = await db_select(
            "ai_escalations",
            filters=filters,
            order_by="escalated_at.desc",
            limit=page_size,
            offset=offset
        )

        # Get thread info for each escalation
        for esc in escalations:
            thread = await db_select_one(
                "email_threads",
                {"id": f"eq.{esc['thread_id']}"},
                select="customer_email,customer_name,subject"
            )
            esc["thread"] = thread

        return {
            "escalations": escalations,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        logger.error(f"Error listing escalations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve escalations"
        )


@router.post("/escalations/{escalation_id}/acknowledge")
async def acknowledge_escalation(
    escalation_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Mark an escalation as acknowledged."""
    try:
        success = await db_update(
            "ai_escalations",
            {"id": f"eq.{escalation_id}"},
            {
                "acknowledged_at": datetime.utcnow().isoformat(),
                "acknowledged_by": current_user.get("email", "admin")
            }
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Escalation not found"
            )

        return {"success": True, "message": "Escalation acknowledged"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging escalation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge escalation"
        )


# =====================================================
# Settings Endpoints
# =====================================================

@router.get("/settings")
async def get_email_support_settings(
    current_user: Dict = Depends(get_current_user)
):
    """Get current AI email support settings."""
    try:
        settings_data = await ai_email_support.get_settings()

        return {
            "settings": settings_data,
            "ai_available": ai_email_support.is_available(),
            "model": ai_email_support.model
        }

    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve settings"
        )


@router.put("/settings")
async def update_email_support_settings(
    request: SettingsUpdateRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Update AI email support settings."""
    try:
        updates = {}

        if request.ai_enabled is not None:
            updates["ai_enabled"] = str(request.ai_enabled).lower()
        if request.confidence_threshold is not None:
            updates["confidence_threshold"] = str(request.confidence_threshold)
        if request.response_tone is not None:
            updates["response_tone"] = request.response_tone
        if request.auto_reply_enabled is not None:
            updates["auto_reply_enabled"] = str(request.auto_reply_enabled).lower()
        if request.escalation_email is not None:
            updates["escalation_email"] = request.escalation_email
        if request.max_ai_turns is not None:
            updates["max_ai_turns"] = str(request.max_ai_turns)

        if updates:
            success = await ai_email_support.update_settings(updates)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update settings"
                )

        return {"success": True, "updated": list(updates.keys())}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )


# =====================================================
# Analytics Endpoints
# =====================================================

@router.get("/analytics")
async def get_email_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict = Depends(get_current_user)
):
    """Get email support analytics for the specified period."""
    try:
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        # Get threads
        threads = await db_select(
            "email_threads",
            filters={"created_at": f"gte.{start_date}"},
            select="status,priority,category"
        )

        # Get messages
        messages = await db_select(
            "email_messages",
            filters={"created_at": f"gte.{start_date}"},
            select="sender_type,ai_generated,ai_confidence"
        )

        # Get escalations
        escalations = await db_select(
            "ai_escalations",
            filters={"escalated_at": f"gte.{start_date}"},
            select="escalation_type,resolved_at"
        )

        # Calculate statistics
        total_threads = len(threads)
        status_breakdown = {}
        priority_breakdown = {}
        category_breakdown = {}

        for t in threads:
            status_breakdown[t["status"]] = status_breakdown.get(t["status"], 0) + 1
            priority_breakdown[t["priority"]] = priority_breakdown.get(t["priority"], 0) + 1
            if t.get("category"):
                category_breakdown[t["category"]] = category_breakdown.get(t["category"], 0) + 1

        total_messages = len(messages)
        ai_messages = sum(1 for m in messages if m.get("ai_generated"))
        customer_messages = sum(1 for m in messages if m.get("sender_type") == "customer")

        ai_confidences = [m["ai_confidence"] for m in messages if m.get("ai_confidence") is not None]
        avg_confidence = sum(ai_confidences) / len(ai_confidences) if ai_confidences else 0

        total_escalations = len(escalations)
        resolved_escalations = sum(1 for e in escalations if e.get("resolved_at"))
        escalation_types = {}
        for e in escalations:
            etype = e.get("escalation_type") or "unknown"
            escalation_types[etype] = escalation_types.get(etype, 0) + 1

        return {
            "period_days": days,
            "threads": {
                "total": total_threads,
                "by_status": status_breakdown,
                "by_priority": priority_breakdown,
                "by_category": category_breakdown
            },
            "messages": {
                "total": total_messages,
                "ai_generated": ai_messages,
                "customer": customer_messages,
                "avg_ai_confidence": round(avg_confidence, 2)
            },
            "escalations": {
                "total": total_escalations,
                "resolved": resolved_escalations,
                "resolution_rate": round(resolved_escalations / total_escalations * 100, 1) if total_escalations > 0 else 0,
                "by_type": escalation_types
            }
        }

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analytics"
        )


# =====================================================
# Health Check
# =====================================================

@router.get("/health")
async def email_support_health():
    """Check health of AI email support service."""
    return {
        "status": "healthy",
        "ai_available": ai_email_support.is_available(),
        "ai_enabled": ai_email_support.enabled,
        "model": ai_email_support.model,
        "knowledge_base_loaded": bool(ai_email_support.knowledge_base),
        "confidence_threshold": ai_email_support.confidence_threshold
    }
