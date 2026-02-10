"""
Admin Dashboard API Endpoints
Platform management for escalated disputes, AI monitoring, and user management.
All endpoints require admin auth check.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from loguru import logger

from app.core.security import get_current_user
from app.core.supabase import get_supabase_client

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])
bearer_scheme = HTTPBearer()

ADMIN_EMAILS = [e.strip() for e in os.getenv("ADMIN_EMAILS", "yassirar77@gmail.com").split(",")]


def _verify_admin(current_user: dict) -> str:
    """Verify the user is an admin. Returns user_id."""
    user_email = current_user.get("email", "")
    user_id = current_user.get("sub", "")
    if user_email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


class OverrideDisputeRequest(BaseModel):
    resolution_type: str
    notes: Optional[str] = None
    credit_amount: Optional[float] = None


class ResolveDisputeRequest(BaseModel):
    resolution_type: str
    notes: Optional[str] = None
    credit_amount: Optional[float] = None


class AdminChatResponse(BaseModel):
    message: str = Field(..., min_length=1)


class AdjustCreditsRequest(BaseModel):
    amount: float
    reason: str


class AdminNoteRequest(BaseModel):
    notes: str


# =====================================================
# DASHBOARD OVERVIEW
# =====================================================

@router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    """Platform stats summary."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        today = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()

        # Total users
        users_result = supabase.table("profiles").select("id", count="exact").execute()
        total_users = users_result.count if hasattr(users_result, "count") and users_result.count else len(users_result.data or [])

        # Active subscriptions
        subs_result = supabase.table("profiles").select("id", count="exact").neq("plan", "free").execute()
        active_subs = subs_result.count if hasattr(subs_result, "count") and subs_result.count else len(subs_result.data or [])

        # Disputes today
        disputes_today_result = supabase.table("ai_disputes").select("id", count="exact").gt("created_at", today).execute()
        disputes_today = disputes_today_result.count if hasattr(disputes_today_result, "count") and disputes_today_result.count else len(disputes_today_result.data or [])

        # Escalated disputes
        escalated_result = supabase.table("ai_disputes").select("id", count="exact").eq("status", "escalated").execute()
        escalated_disputes = escalated_result.count if hasattr(escalated_result, "count") and escalated_result.count else len(escalated_result.data or [])

        # AI resolution rate
        total_disputes_result = supabase.table("ai_disputes").select("id, status").execute()
        total_all = len(total_disputes_result.data or [])
        resolved_by_ai = sum(1 for d in (total_disputes_result.data or []) if d.get("status") in ("resolved", "closed"))
        ai_resolution_rate = round((resolved_by_ai / total_all * 100), 1) if total_all > 0 else 0.0

        # Credits awarded today
        credits_result = supabase.table("credit_transactions").select("amount").eq("type", "earned").gt("created_at", today).execute()
        credits_today = sum(float(c.get("amount", 0)) for c in (credits_result.data or []))

        # Active support chats
        active_chats_result = supabase.table("ai_support_chats").select("id", count="exact").eq("status", "active").execute()
        active_chats = active_chats_result.count if hasattr(active_chats_result, "count") and active_chats_result.count else len(active_chats_result.data or [])

        # Escalated chats
        escalated_chats_result = supabase.table("ai_support_chats").select("id", count="exact").eq("status", "escalated").execute()
        escalated_chats = escalated_chats_result.count if hasattr(escalated_chats_result, "count") and escalated_chats_result.count else len(escalated_chats_result.data or [])

        # Unhealthy websites
        unhealthy_result = supabase.table("restaurant_health").select("id", count="exact").neq("health_status", "healthy").execute()
        unhealthy_count = unhealthy_result.count if hasattr(unhealthy_result, "count") and unhealthy_result.count else len(unhealthy_result.data or [])

        # Unacknowledged monitor events
        unack_result = supabase.table("ai_monitor_events").select("id", count="exact").eq("acknowledged", False).execute()
        unack_count = unack_result.count if hasattr(unack_result, "count") and unack_result.count else len(unack_result.data or [])

        return {
            "total_users": total_users,
            "active_subscriptions": active_subs,
            "total_disputes_today": disputes_today,
            "escalated_disputes": escalated_disputes,
            "ai_resolution_rate": ai_resolution_rate,
            "total_credits_awarded_today": round(credits_today, 2),
            "active_support_chats": active_chats,
            "escalated_chats": escalated_chats,
            "websites_unhealthy": unhealthy_count,
            "monitor_events_unacknowledged": unack_count,
        }
    except Exception as e:
        logger.error(f"Dashboard stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


# =====================================================
# DISPUTES MANAGEMENT
# =====================================================

@router.get("/disputes")
async def get_all_disputes(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """All disputes (filterable by status)."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        query = supabase.table("ai_disputes").select("*")
        if status_filter:
            query = query.eq("status", status_filter)
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        return {"disputes": result.data or []}
    except Exception as e:
        logger.error(f"Get disputes failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get disputes")


@router.get("/disputes/escalated")
async def get_escalated_disputes(current_user: dict = Depends(get_current_user)):
    """Escalated disputes only."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        result = supabase.table("ai_disputes").select("*").eq(
            "status", "escalated"
        ).order("created_at", desc=True).execute()
        return {"disputes": result.data or []}
    except Exception as e:
        logger.error(f"Get escalated disputes failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get escalated disputes")


@router.post("/disputes/{dispute_id}/override")
async def override_dispute(
    dispute_id: str,
    request: OverrideDisputeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Override AI decision on a dispute."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        # Get current state
        dispute_result = supabase.table("ai_disputes").select("*").eq("id", dispute_id).execute()
        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        previous_state = dispute_result.data[0]

        # Update dispute
        update_data = {
            "status": "resolved",
            "resolution_type": request.resolution_type,
            "admin_notes": request.notes,
            "resolved_by": "admin_override",
        }
        supabase.table("ai_disputes").update(update_data).eq("id", dispute_id).execute()

        # Award credits if specified
        if request.credit_amount and request.credit_amount > 0:
            user_id = previous_state.get("user_id")
            if user_id:
                wallet_result = supabase.table("bina_credits").select("balance").eq("user_id", user_id).execute()
                if wallet_result.data:
                    new_balance = float(wallet_result.data[0].get("balance", 0)) + request.credit_amount
                    supabase.table("bina_credits").update({"balance": new_balance}).eq("user_id", user_id).execute()
                else:
                    supabase.table("bina_credits").insert({"user_id": user_id, "balance": request.credit_amount}).execute()

                supabase.table("credit_transactions").insert({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "type": "earned",
                    "amount": request.credit_amount,
                    "description": f"Admin override: {request.notes or 'Dispute resolved'}",
                    "source": "admin",
                }).execute()

        # Log admin action
        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "dispute",
            "target_id": dispute_id,
            "action": "override_decision",
            "details": {"resolution_type": request.resolution_type, "credit_amount": request.credit_amount},
            "notes": request.notes,
            "previous_state": previous_state,
            "new_state": update_data,
        }).execute()

        return {"message": "Dispute overridden", "dispute_id": dispute_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Override dispute failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to override dispute")


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    request: ResolveDisputeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Manually resolve a dispute."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        dispute_result = supabase.table("ai_disputes").select("*").eq("id", dispute_id).execute()
        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        previous_state = dispute_result.data[0]

        update_data = {
            "status": "resolved",
            "resolution_type": request.resolution_type,
            "admin_notes": request.notes,
            "resolved_by": "admin",
        }
        supabase.table("ai_disputes").update(update_data).eq("id", dispute_id).execute()

        # Log admin action
        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "dispute",
            "target_id": dispute_id,
            "action": "approve_dispute",
            "notes": request.notes,
            "previous_state": previous_state,
            "new_state": update_data,
        }).execute()

        return {"message": "Dispute resolved", "dispute_id": dispute_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve dispute failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve dispute")


# =====================================================
# AI CHAT MANAGEMENT
# =====================================================

@router.get("/chats/escalated")
async def get_escalated_chats(current_user: dict = Depends(get_current_user)):
    """Escalated chats."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        result = supabase.table("ai_support_chats").select("*").eq(
            "status", "escalated"
        ).order("updated_at", desc=True).execute()
        return {"chats": result.data or []}
    except Exception as e:
        logger.error(f"Get escalated chats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get escalated chats")


@router.get("/chats/{chat_id}/messages")
async def get_chat_messages(
    chat_id: str,
    current_user: dict = Depends(get_current_user),
):
    """View full chat history."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        result = supabase.table("ai_support_messages").select("*").eq(
            "chat_id", chat_id
        ).order("created_at").execute()
        return {"messages": result.data or []}
    except Exception as e:
        logger.error(f"Get chat messages failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chat messages")


@router.post("/chats/{chat_id}/respond")
async def admin_respond(
    chat_id: str,
    request: AdminChatResponse,
    current_user: dict = Depends(get_current_user),
):
    """Admin responds in chat."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        # Insert admin message as system
        supabase.table("ai_support_messages").insert({
            "id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "role": "system",
            "content": f"[Admin] {request.message}",
            "action_taken": "admin_response",
        }).execute()

        # Update chat
        supabase.table("ai_support_chats").update({
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", chat_id).execute()

        # Log action
        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "chat",
            "target_id": chat_id,
            "action": "resolve_chat",
            "notes": request.message,
        }).execute()

        return {"message": "Response sent"}
    except Exception as e:
        logger.error(f"Admin respond failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send response")


# =====================================================
# USER MANAGEMENT
# =====================================================

@router.get("/users")
async def get_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """User list."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        result = supabase.table("profiles").select("*").order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        return {"users": result.data or []}
    except Exception as e:
        logger.error(f"Get users failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    request: AdminNoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Suspend user."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        supabase.table("profiles").update({"suspended": True}).eq("id", user_id).execute()

        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "user",
            "target_id": user_id,
            "action": "suspend_user",
            "notes": request.notes,
        }).execute()

        return {"message": "User suspended"}
    except Exception as e:
        logger.error(f"Suspend user failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to suspend user")


@router.post("/users/{user_id}/adjust-credits")
async def adjust_credits(
    user_id: str,
    request: AdjustCreditsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Manually add/remove credits."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        wallet_result = supabase.table("bina_credits").select("balance").eq("user_id", user_id).execute()
        if wallet_result.data:
            current_balance = float(wallet_result.data[0].get("balance", 0))
            new_balance = max(0, current_balance + request.amount)
            supabase.table("bina_credits").update({"balance": new_balance}).eq("user_id", user_id).execute()
        else:
            new_balance = max(0, request.amount)
            supabase.table("bina_credits").insert({"user_id": user_id, "balance": new_balance}).execute()

        txn_type = "earned" if request.amount > 0 else "deducted"
        supabase.table("credit_transactions").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": txn_type,
            "amount": abs(request.amount),
            "description": f"Admin: {request.reason}",
            "source": "admin",
        }).execute()

        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "user",
            "target_id": user_id,
            "action": "award_credit" if request.amount > 0 else "revoke_credit",
            "details": {"amount": request.amount, "new_balance": new_balance},
            "notes": request.reason,
        }).execute()

        return {"message": "Credits adjusted", "new_balance": new_balance}
    except Exception as e:
        logger.error(f"Adjust credits failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to adjust credits")


# =====================================================
# RESTAURANT HEALTH
# =====================================================

@router.get("/restaurants")
async def get_restaurants(current_user: dict = Depends(get_current_user)):
    """All restaurants with health status."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        result = supabase.table("restaurant_health").select(
            "*, websites(business_name, subdomain)"
        ).order("health_status").execute()
        return {"restaurants": result.data or []}
    except Exception as e:
        logger.error(f"Get restaurants failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get restaurants")


@router.post("/restaurants/{website_id}/suspend")
async def suspend_restaurant(
    website_id: str,
    request: AdminNoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Suspend restaurant."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        supabase.table("restaurant_health").update({
            "health_status": "suspended",
            "auto_suspended": False,
            "suspension_reason": request.notes,
            "suspension_sent_at": datetime.utcnow().isoformat(),
        }).eq("website_id", website_id).execute()

        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "restaurant",
            "target_id": website_id,
            "action": "suspend_restaurant",
            "notes": request.notes,
        }).execute()

        return {"message": "Restaurant suspended"}
    except Exception as e:
        logger.error(f"Suspend restaurant failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to suspend restaurant")


@router.post("/restaurants/{website_id}/unsuspend")
async def unsuspend_restaurant(
    website_id: str,
    request: AdminNoteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Unsuspend restaurant."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        supabase.table("restaurant_health").update({
            "health_status": "healthy",
            "auto_suspended": False,
            "suspension_reason": None,
        }).eq("website_id", website_id).execute()

        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "restaurant",
            "target_id": website_id,
            "action": "unsuspend_restaurant",
            "notes": request.notes,
        }).execute()

        return {"message": "Restaurant unsuspended"}
    except Exception as e:
        logger.error(f"Unsuspend restaurant failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to unsuspend restaurant")


# =====================================================
# MONITOR & AI PERFORMANCE
# =====================================================

@router.get("/monitor/events")
async def get_all_monitor_events(
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """All platform monitor events."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        query = supabase.table("ai_monitor_events").select("*")
        if severity:
            query = query.eq("severity", severity)
        if event_type:
            query = query.eq("event_type", event_type)
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        return {"events": result.data or []}
    except Exception as e:
        logger.error(f"Get monitor events failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitor events")


@router.get("/ai-performance")
async def get_ai_performance(current_user: dict = Depends(get_current_user)):
    """AI decision accuracy stats."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        # Disputes stats
        disputes_result = supabase.table("ai_disputes").select("status, resolved_by").execute()
        disputes = disputes_result.data or []

        total = len(disputes)
        resolved = sum(1 for d in disputes if d.get("status") in ("resolved", "closed"))
        admin_overridden = sum(1 for d in disputes if d.get("resolved_by") == "admin_override")

        # Chat stats
        chats_result = supabase.table("ai_support_chats").select("status, satisfaction_rating").execute()
        chats = chats_result.data or []

        total_chats = len(chats)
        resolved_chats = sum(1 for c in chats if c.get("status") in ("resolved", "closed"))
        ratings = [c["satisfaction_rating"] for c in chats if c.get("satisfaction_rating")]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

        return {
            "disputes": {
                "total": total,
                "resolved": resolved,
                "resolution_rate": round((resolved / total * 100), 1) if total > 0 else 0.0,
                "admin_overridden": admin_overridden,
                "override_rate": round((admin_overridden / total * 100), 1) if total > 0 else 0.0,
            },
            "chats": {
                "total": total_chats,
                "resolved": resolved_chats,
                "avg_satisfaction": avg_rating,
            },
        }
    except Exception as e:
        logger.error(f"Get AI performance failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI performance")


@router.get("/actions")
async def get_admin_actions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Admin action history."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        result = supabase.table("admin_actions").select("*").order(
            "created_at", desc=True
        ).range(offset, offset + limit - 1).execute()
        return {"actions": result.data or []}
    except Exception as e:
        logger.error(f"Get admin actions failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin actions")


# =====================================================
# ADMIN DISPUTE CHAT (Owner Complaints)
# =====================================================

class AdminDisputeMessage(BaseModel):
    message: str = Field(..., min_length=1)


class AdminAwardCredit(BaseModel):
    amount: float = Field(..., gt=0)
    reason: Optional[str] = None


@router.get("/disputes/{dispute_id}/messages")
async def get_dispute_messages(
    dispute_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get all messages for a specific dispute (admin view)."""
    _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        result = supabase.table("dispute_messages").select("*").eq(
            "dispute_id", dispute_id
        ).eq("is_internal", False).order("created_at").execute()
        return {"messages": result.data or []}
    except Exception as e:
        logger.error(f"Get dispute messages failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dispute messages")


@router.post("/disputes/{dispute_id}/message")
async def admin_send_dispute_message(
    dispute_id: str,
    request: AdminDisputeMessage,
    current_user: dict = Depends(get_current_user),
):
    """Admin sends a message in an owner dispute. Disables AI auto-reply for this dispute."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        # Verify dispute exists
        dispute_result = supabase.table("ai_disputes").select("id, dispute_number").eq(
            "id", dispute_id
        ).execute()
        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        # Save admin message
        supabase.table("dispute_messages").insert({
            "dispute_id": dispute_id,
            "sender_type": "admin",
            "sender_name": "BinaApp Admin",
            "message": request.message,
            "is_internal": False,
            "metadata": {"admin_user_id": admin_id},
        }).execute()

        # Disable AI auto-reply — admin is handling this dispute
        supabase.table("ai_disputes").update({
            "ai_auto_reply_disabled": True,
        }).eq("id", dispute_id).execute()

        # Log admin action
        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "dispute",
            "target_id": dispute_id,
            "action": "dispute_message",
            "notes": request.message[:200],
        }).execute()

        logger.info(f"Admin sent message in dispute {dispute_id}, AI disabled")
        return {"status": "sent", "dispute_id": dispute_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin send dispute message failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.post("/disputes/{dispute_id}/credit")
async def admin_award_dispute_credit(
    dispute_id: str,
    request: AdminAwardCredit,
    current_user: dict = Depends(get_current_user),
):
    """Award BinaCredit to the dispute owner as compensation."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        # Get dispute to find the owner
        dispute_result = supabase.table("ai_disputes").select(
            "id, dispute_number, website_id"
        ).eq("id", dispute_id).execute()
        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        dispute_data = dispute_result.data[0]

        # Find the website owner
        website_result = supabase.table("websites").select("user_id").eq(
            "id", dispute_data["website_id"]
        ).execute()
        if not website_result.data:
            raise HTTPException(status_code=404, detail="Website owner not found")

        user_id = website_result.data[0]["user_id"]

        # Update credit balance
        wallet_result = supabase.table("bina_credits").select("balance").eq(
            "user_id", user_id
        ).execute()
        if wallet_result.data:
            new_balance = float(wallet_result.data[0].get("balance", 0)) + request.amount
            supabase.table("bina_credits").update({"balance": new_balance}).eq(
                "user_id", user_id
            ).execute()
        else:
            new_balance = request.amount
            supabase.table("bina_credits").insert({
                "user_id": user_id, "balance": new_balance
            }).execute()

        # Record transaction
        supabase.table("credit_transactions").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": "earned",
            "amount": request.amount,
            "description": request.reason or f"Pampasan aduan #{dispute_data.get('dispute_number', '')}",
            "source": "admin",
        }).execute()

        # Add system message in dispute chat
        supabase.table("dispute_messages").insert({
            "dispute_id": dispute_id,
            "sender_type": "system",
            "sender_name": "System",
            "message": f"Admin telah memberi pampasan BinaCredit RM{request.amount:.2f} kepada pemilik.",
            "is_internal": False,
        }).execute()

        # Log admin action
        supabase.table("admin_actions").insert({
            "id": str(uuid.uuid4()),
            "admin_user_id": admin_id,
            "target_type": "dispute",
            "target_id": dispute_id,
            "action": "award_dispute_credit",
            "details": {"amount": request.amount, "user_id": user_id},
            "notes": request.reason,
        }).execute()

        logger.info(f"Admin awarded RM{request.amount} BinaCredit for dispute {dispute_id}")
        return {
            "status": "credited",
            "amount": request.amount,
            "new_balance": new_balance,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin award dispute credit failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to award credit")


@router.post("/disputes/{dispute_id}/toggle-ai")
async def admin_toggle_dispute_ai(
    dispute_id: str,
    enabled: bool = Query(..., description="Enable or disable AI auto-reply"),
    current_user: dict = Depends(get_current_user),
):
    """Admin re-enables or disables AI auto-reply for a dispute."""
    admin_id = _verify_admin(current_user)
    supabase = get_supabase_client()

    try:
        dispute_result = supabase.table("ai_disputes").select("id").eq(
            "id", dispute_id
        ).execute()
        if not dispute_result.data:
            raise HTTPException(status_code=404, detail="Dispute not found")

        supabase.table("ai_disputes").update({
            "ai_auto_reply_disabled": not enabled,
        }).eq("id", dispute_id).execute()

        state = "enabled" if enabled else "disabled"
        logger.info(f"Admin {state} AI auto-reply for dispute {dispute_id}")
        return {"status": "success", "ai_auto_reply_enabled": enabled}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin toggle dispute AI failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle AI")
