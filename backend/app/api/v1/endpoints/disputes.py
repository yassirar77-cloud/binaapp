"""
BinaApp AI Dispute Resolution API Endpoints
Handles dispute creation, AI analysis, resolution workflow, and messaging.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from typing import Optional
from loguru import logger
from datetime import datetime
import os
import traceback
from supabase import create_client

from app.core.supabase import get_supabase_client
from app.core.security import get_current_user
from app.models.dispute_schemas import (
    DisputeCreate,
    DisputeResponse,
    DisputeListResponse,
    DisputeStatusUpdate,
    DisputeResolve,
    OwnerResponse,
    DisputeMessageCreate,
    DisputeMessageResponse,
    DisputeStatusHistoryResponse,
    DisputeSummary,
)
from app.services.dispute_service import dispute_ai_service

router = APIRouter(prefix="/disputes", tags=["Dispute Resolution"])
bearer_scheme = HTTPBearer()


# =====================================================
# AUTHENTICATED SUPABASE CLIENT (RLS)
# =====================================================

def get_supabase_rls_client(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Client:
    """Create a Supabase client with the caller's JWT for RLS."""
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    )

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase not configured",
        )

    client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    client.postgrest.auth(credentials.credentials)
    return client


# =====================================================
# CUSTOMER ENDPOINTS (Public - no auth required)
# =====================================================

@router.post("/create", response_model=DisputeResponse)
async def create_dispute(dispute: DisputeCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new dispute for an order or a subscriber complaint.
    Triggers AI analysis automatically.
    """
    user_id = current_user.get("sub")
    supabase = get_supabase_client()

    try:
        order = None
        order_amount = 0.0

        if dispute.order_id:
            # 1. Verify the order exists and get order details
            order_result = supabase.table("delivery_orders").select(
                "*, order_items(*)"
            ).eq("id", dispute.order_id).execute()

            if not order_result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Order not found",
                )

            order = order_result.data[0]
            order_amount = float(order.get("total_amount", 0))

            # 2. Check if a dispute already exists for this order
            existing = supabase.table("ai_disputes").select("id, dispute_number").eq(
                "order_id", dispute.order_id
            ).in_("status", ["open", "under_review", "awaiting_response"]).execute()

            if existing.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An active dispute (#{existing.data[0]['dispute_number']}) already exists for this order",
                )

        # 3. Run AI analysis
        order_details = {}
        if order:
            order_details = {
                "order_number": order.get("order_number"),
                "items": [
                    {
                        "name": item.get("item_name"),
                        "quantity": item.get("quantity"),
                        "price": float(item.get("unit_price", 0)),
                    }
                    for item in order.get("order_items", [])
                ],
                "payment_method": order.get("payment_method"),
                "status": order.get("status"),
                "created_at": order.get("created_at"),
                "delivered_at": order.get("delivered_at"),
            }

        ai_analysis = await dispute_ai_service.analyze_dispute(
            category=dispute.category.value,
            description=dispute.description,
            order_amount=order_amount,
            disputed_amount=dispute.disputed_amount,
            order_details=order_details,
        )

        # 4. Create the dispute record
        customer_name = dispute.customer_name or "Subscriber"
        website_id = dispute.website_id or (order.get("website_id") if order else None)

        dispute_data = {
            "user_id": user_id,
            "order_id": dispute.order_id,
            "website_id": website_id,
            "category": dispute.category.value,
            "description": dispute.description,
            "evidence_urls": dispute.evidence_urls or [],
            "evidence_analysis": ai_analysis,
            "severity": dispute_ai_service._map_severity_score_to_level(
                ai_analysis.get("severity_score", 5)
            ),
            "ai_decision": ai_analysis.get("recommended_resolution"),
            "ai_reasoning": ai_analysis.get("reasoning"),
            "ai_confidence": ai_analysis.get("category_confidence"),
            "status": "open",
        }

        # Safety: ensure ai_decision is always valid before insert
        valid_decisions = {'approved', 'rejected', 'partial', 'escalated'}
        if dispute_data.get('ai_decision') not in valid_decisions:
            dispute_data['ai_decision'] = 'escalated'

        # Safety: ensure severity is always a valid text level before insert
        valid_severities = {'minor', 'medium', 'major', 'critical'}
        if dispute_data.get('severity') not in valid_severities:
            dispute_data['severity'] = 'medium'

        result = supabase.table("ai_disputes").insert(dispute_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create dispute",
            )

        dispute_record = result.data[0]

        # 5. Create initial system message
        order_ref = f" for order #{order.get('order_number', 'N/A')}" if order else ""
        supabase.table("dispute_messages").insert({
            "dispute_id": dispute_record["id"],
            "sender_type": "system",
            "sender_name": "System",
            "message": f"Dispute #{dispute_record['dispute_number']} created{order_ref}. Category: {dispute.category.value.replace('_', ' ').title()}.",
        }).execute()

        # 6. Generate AI auto-reply message
        try:
            ai_reply = await dispute_ai_service.generate_ai_reply(
                dispute_id=dispute_record["id"],
                trigger_type="creation",
                dispute_data=dispute_record,
            )
            if ai_reply:
                supabase.table("dispute_messages").insert({
                    "dispute_id": dispute_record["id"],
                    "sender_type": "ai_system",
                    "sender_name": "BinaApp AI",
                    "message": ai_reply,
                    "metadata": {
                        "trigger_type": "creation",
                        "severity_score": ai_analysis.get("severity_score"),
                        "recommended_resolution": ai_analysis.get("recommended_resolution"),
                        "reasoning": ai_analysis.get("reasoning"),
                    },
                }).execute()
        except Exception as e:
            logger.warning(f"Failed to generate AI auto-reply on creation: {e}")

        order_info = f"for order {order.get('order_number')}" if order else "(subscriber complaint)"
        logger.info(
            f"Dispute created: #{dispute_record['dispute_number']} "
            f"{order_info} "
            f"(severity: {ai_analysis.get('severity_score')}, "
            f"recommendation: {ai_analysis.get('recommended_resolution')})"
        )

        return DisputeResponse(**dispute_record)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Disputes] CREATE ERROR: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dispute: {str(e)}",
        )


@router.get("/track/{dispute_number}", response_model=DisputeResponse)
async def track_dispute(dispute_number: str):
    """
    Track a dispute by its dispute number.
    Public endpoint for customers.
    """
    supabase = get_supabase_client()

    try:
        result = supabase.table("ai_disputes").select("*").eq(
            "dispute_number", dispute_number
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        return DisputeResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking dispute: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track dispute: {str(e)}",
        )


@router.get("/track/{dispute_number}/messages")
async def get_dispute_messages_public(dispute_number: str):
    """
    Get messages for a dispute by dispute number.
    Public endpoint - only shows non-internal messages.
    """
    supabase = get_supabase_client()

    try:
        # Get dispute ID
        dispute = supabase.table("ai_disputes").select("id").eq(
            "dispute_number", dispute_number
        ).execute()

        if not dispute.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        dispute_id = dispute.data[0]["id"]

        # Get non-internal messages
        messages = supabase.table("dispute_messages").select("*").eq(
            "dispute_id", dispute_id
        ).eq("is_internal", False).order("created_at").execute()

        return {
            "messages": messages.data or [],
            "total": len(messages.data or []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dispute messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        )


@router.post("/track/{dispute_number}/messages")
async def add_customer_message(dispute_number: str, message: DisputeMessageCreate):
    """
    Add a message from the customer to the dispute.
    Triggers AI auto-reply if not disabled.
    """
    supabase = get_supabase_client()

    try:
        # Get full dispute data (needed for AI reply context)
        dispute = supabase.table("ai_disputes").select("*").eq(
            "dispute_number", dispute_number
        ).execute()

        if not dispute.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        dispute_data = dispute.data[0]

        if dispute_data["status"] in ("closed", "rejected"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add messages to a closed dispute",
            )

        msg_data = {
            "dispute_id": dispute_data["id"],
            "sender_type": "customer",
            "sender_name": message.sender_name or "Customer",
            "message": message.message,
            "attachments": message.attachments or [],
            "is_internal": False,
        }

        result = supabase.table("dispute_messages").insert(msg_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message",
            )

        # Trigger AI auto-reply if not disabled
        if not dispute_data.get("ai_auto_reply_disabled", False):
            try:
                # Fetch conversation history for context
                history = supabase.table("dispute_messages").select("*").eq(
                    "dispute_id", dispute_data["id"]
                ).eq("is_internal", False).order("created_at").execute()

                ai_reply = await dispute_ai_service.generate_ai_reply(
                    dispute_id=dispute_data["id"],
                    trigger_type="customer_message",
                    dispute_data=dispute_data,
                    conversation_history=history.data or [],
                    customer_message=message.message,
                )

                if ai_reply:
                    supabase.table("dispute_messages").insert({
                        "dispute_id": dispute_data["id"],
                        "sender_type": "ai_system",
                        "sender_name": "BinaApp AI",
                        "message": ai_reply,
                        "metadata": {
                            "trigger_type": "customer_message",
                        },
                    }).execute()
            except Exception as e:
                logger.warning(f"Failed to generate AI auto-reply for customer message: {e}")

        return DisputeMessageResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding customer message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )


@router.get("/order/{order_id}")
async def get_disputes_for_order(order_id: str):
    """
    Get all disputes for a specific order.
    Public endpoint for customers.
    """
    supabase = get_supabase_client()

    try:
        result = supabase.table("ai_disputes").select("*").eq(
            "order_id", order_id
        ).order("created_at", desc=True).execute()

        return {
            "disputes": result.data or [],
            "total": len(result.data or []),
        }

    except Exception as e:
        logger.error(f"Error getting disputes for order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get disputes: {str(e)}",
        )


# =====================================================
# BUSINESS OWNER ENDPOINTS (Auth required)
# =====================================================

@router.get("/owner/list", response_model=DisputeListResponse)
async def list_owner_disputes(
    current_user: dict = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """
    List all disputes for the business owner's websites.
    Requires authentication.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Get owner's website IDs
        websites = supabase.table("websites").select("id").eq(
            "user_id", user_id
        ).execute()

        if not websites.data:
            return DisputeListResponse(
                disputes=[], total=0, page=page, per_page=per_page
            )

        website_ids = [w["id"] for w in websites.data]

        # Build query
        query = supabase.table("ai_disputes").select(
            "*", count="exact"
        ).in_("website_id", website_ids)

        if status_filter:
            query = query.eq("status", status_filter)
        if category:
            query = query.eq("category", category)
        if priority:
            query = query.eq("priority", priority)

        # Pagination
        offset = (page - 1) * per_page
        query = query.order("created_at", desc=True).range(
            offset, offset + per_page - 1
        )

        result = query.execute()

        total = result.count if result.count is not None else len(result.data or [])

        return DisputeListResponse(
            disputes=[DisputeResponse(**d) for d in (result.data or [])],
            total=total,
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(f"Error listing owner disputes: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list disputes: {str(e)}",
        )


@router.get("/owner/summary", response_model=DisputeSummary)
async def get_dispute_summary(
    current_user: dict = Depends(get_current_user),
):
    """
    Get dispute summary/analytics for the business owner.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Get owner's website IDs
        websites = supabase.table("websites").select("id").eq(
            "user_id", user_id
        ).execute()

        if not websites.data:
            return DisputeSummary()

        website_ids = [w["id"] for w in websites.data]

        # Get all disputes for these websites
        disputes = supabase.table("ai_disputes").select("*").in_(
            "website_id", website_ids
        ).execute()

        all_disputes = disputes.data or []

        if not all_disputes:
            return DisputeSummary()

        # Calculate summary
        total = len(all_disputes)
        open_count = sum(
            1
            for d in all_disputes
            if d["status"] in ("open", "under_review", "awaiting_response")
        )
        resolved_count = sum(
            1 for d in all_disputes if d["status"] in ("resolved", "closed")
        )
        escalated_count = sum(
            1 for d in all_disputes if d["status"] == "escalated"
        )

        total_refunded = sum(
            float(d.get("refund_amount") or 0) for d in all_disputes
        )

        resolution_rate = (resolved_count / total * 100) if total > 0 else 0

        # Count by category
        by_category = {}
        for d in all_disputes:
            cat = d.get("category", "other")
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by priority
        by_priority = {}
        for d in all_disputes:
            pri = d.get("priority", "medium")
            by_priority[pri] = by_priority.get(pri, 0) + 1

        # Calculate average resolution time
        resolution_times = []
        for d in all_disputes:
            if d.get("resolved_at") and d.get("created_at"):
                try:
                    created = datetime.fromisoformat(
                        d["created_at"].replace("Z", "+00:00")
                    )
                    resolved = datetime.fromisoformat(
                        d["resolved_at"].replace("Z", "+00:00")
                    )
                    hours = (resolved - created).total_seconds() / 3600
                    resolution_times.append(hours)
                except (ValueError, TypeError):
                    pass

        avg_time = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times
            else None
        )

        return DisputeSummary(
            total_disputes=total,
            open_disputes=open_count,
            resolved_disputes=resolved_count,
            escalated_disputes=escalated_count,
            avg_resolution_time_hours=round(avg_time, 1) if avg_time else None,
            total_refunded=total_refunded,
            resolution_rate=round(resolution_rate, 1),
            by_category=by_category,
            by_priority=by_priority,
        )

    except Exception as e:
        logger.error(f"Error getting dispute summary: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get summary: {str(e)}",
        )


@router.get("/owner/{dispute_id}", response_model=DisputeResponse)
async def get_owner_dispute_detail(
    dispute_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get full dispute details for the business owner.
    Includes AI analysis.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Verify ownership
        result = supabase.table("ai_disputes").select("*").eq(
            "id", dispute_id
        ).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        dispute = result.data[0]

        # Verify the owner owns this website
        website = supabase.table("websites").select("id").eq(
            "id", dispute["website_id"]
        ).eq("user_id", user_id).execute()

        if not website.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this dispute",
            )

        return DisputeResponse(**dispute)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dispute detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dispute: {str(e)}",
        )


@router.get("/owner/{dispute_id}/messages")
async def get_owner_dispute_messages(
    dispute_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get all messages for a dispute (including internal notes).
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Verify ownership
        dispute = supabase.table("ai_disputes").select("website_id").eq(
            "id", dispute_id
        ).execute()

        if not dispute.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        website = supabase.table("websites").select("id").eq(
            "id", dispute.data[0]["website_id"]
        ).eq("user_id", user_id).execute()

        if not website.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this dispute",
            )

        # Get all messages (including internal)
        messages = supabase.table("dispute_messages").select("*").eq(
            "dispute_id", dispute_id
        ).order("created_at").execute()

        return {
            "messages": messages.data or [],
            "total": len(messages.data or []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dispute messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        )


@router.post("/owner/{dispute_id}/respond")
async def owner_respond_to_dispute(
    dispute_id: str,
    response: OwnerResponse,
    current_user: dict = Depends(get_current_user),
):
    """
    Business owner responds to a dispute.
    Can accept fault, propose resolution, and send a message.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Verify ownership
        dispute_result = supabase.table("ai_disputes").select("*").eq(
            "id", dispute_id
        ).execute()

        if not dispute_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        dispute = dispute_result.data[0]

        website = supabase.table("websites").select("id").eq(
            "id", dispute["website_id"]
        ).eq("user_id", user_id).execute()

        if not website.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this dispute",
            )

        if dispute["status"] in ("closed", "rejected"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot respond to a closed dispute",
            )

        # Add owner message
        supabase.table("dispute_messages").insert({
            "dispute_id": dispute_id,
            "sender_type": "owner",
            "sender_id": user_id,
            "sender_name": "Business Owner",
            "message": response.message,
        }).execute()

        # Update dispute status
        update_data = {
            "status": "awaiting_response" if not response.accept_fault else "under_review",
            "reviewed_at": datetime.utcnow().isoformat(),
        }

        if response.accept_fault and response.proposed_resolution:
            update_data["resolution_type"] = response.proposed_resolution.value
            update_data["resolved_by"] = "owner"

            if response.proposed_refund_amount is not None:
                update_data["refund_amount"] = response.proposed_refund_amount

        supabase.table("ai_disputes").update(update_data).eq(
            "id", dispute_id
        ).execute()

        # Add system message about the response
        if response.accept_fault:
            system_msg = (
                f"Business owner has accepted responsibility and proposed: "
                f"{response.proposed_resolution.value.replace('_', ' ').title() if response.proposed_resolution else 'resolution pending'}."
            )
        else:
            system_msg = "Business owner has responded. Awaiting customer review."

        supabase.table("dispute_messages").insert({
            "dispute_id": dispute_id,
            "sender_type": "system",
            "sender_name": "System",
            "message": system_msg,
        }).execute()

        logger.info(
            f"Owner responded to dispute {dispute['dispute_number']}: "
            f"accept_fault={response.accept_fault}"
        )

        return {"status": "success", "message": "Response sent successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in owner response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send response: {str(e)}",
        )


@router.post("/owner/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    resolution: DisputeResolve,
    current_user: dict = Depends(get_current_user),
):
    """
    Resolve a dispute with a specific resolution.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Verify ownership
        dispute_result = supabase.table("ai_disputes").select("*").eq(
            "id", dispute_id
        ).execute()

        if not dispute_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        dispute = dispute_result.data[0]

        website = supabase.table("websites").select("id").eq(
            "id", dispute["website_id"]
        ).eq("user_id", user_id).execute()

        if not website.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this dispute",
            )

        if dispute["status"] in ("closed", "resolved"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dispute is already resolved or closed",
            )

        # Update dispute with resolution
        update_data = {
            "status": "resolved",
            "resolution_type": resolution.resolution_type.value,
            "resolution_notes": resolution.resolution_notes,
            "resolved_by": "owner",
            "resolved_at": datetime.utcnow().isoformat(),
        }

        if resolution.refund_amount is not None:
            update_data["refund_amount"] = resolution.refund_amount

        supabase.table("ai_disputes").update(update_data).eq(
            "id", dispute_id
        ).execute()

        # Add resolution message
        resolution_label = resolution.resolution_type.value.replace('_', ' ').title()
        resolution_msg = f"Aduan diselesaikan: {resolution_label}."
        if resolution.resolution_notes:
            resolution_msg += f" Nota: {resolution.resolution_notes}"

        supabase.table("dispute_messages").insert({
            "dispute_id": dispute_id,
            "sender_type": "system",
            "sender_name": "System",
            "message": resolution_msg,
        }).execute()

        logger.info(
            f"Dispute {dispute['dispute_number']} resolved: "
            f"{resolution.resolution_type.value}"
        )

        return {"status": "success", "message": "Dispute resolved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving dispute: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve dispute: {str(e)}",
        )


@router.get("/owner/{dispute_id}/history")
async def get_dispute_history(
    dispute_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get status change history for a dispute.
    """
    supabase = get_supabase_client()

    try:
        history = supabase.table("dispute_status_history").select("*").eq(
            "dispute_id", dispute_id
        ).order("created_at").execute()

        return {
            "history": history.data or [],
            "total": len(history.data or []),
        }

    except Exception as e:
        logger.error(f"Error getting dispute history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}",
        )


@router.post("/owner/{dispute_id}/escalate")
async def escalate_dispute(
    dispute_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Escalate a dispute to platform admin.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        dispute_result = supabase.table("ai_disputes").select("*").eq(
            "id", dispute_id
        ).execute()

        if not dispute_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        dispute = dispute_result.data[0]

        # Update status to escalated
        supabase.table("ai_disputes").update({
            "status": "escalated",
            "priority": "urgent",
        }).eq("id", dispute_id).execute()

        # Add system message
        supabase.table("dispute_messages").insert({
            "dispute_id": dispute_id,
            "sender_type": "system",
            "sender_name": "System",
            "message": "This dispute has been escalated to the BinaApp platform team for review.",
        }).execute()

        # Generate AI escalation notification to customer
        try:
            history = supabase.table("dispute_messages").select("*").eq(
                "dispute_id", dispute_id
            ).eq("is_internal", False).order("created_at").execute()

            ai_reply = await dispute_ai_service.generate_ai_reply(
                dispute_id=dispute_id,
                trigger_type="escalation",
                dispute_data=dispute,
                conversation_history=history.data or [],
            )

            if ai_reply:
                supabase.table("dispute_messages").insert({
                    "dispute_id": dispute_id,
                    "sender_type": "ai_system",
                    "sender_name": "BinaApp AI",
                    "message": ai_reply,
                    "metadata": {
                        "trigger_type": "escalation",
                    },
                }).execute()
        except Exception as e:
            logger.warning(f"Failed to generate AI escalation reply: {e}")

        logger.info(f"Dispute {dispute['dispute_number']} escalated to admin")

        return {"status": "success", "message": "Dispute escalated to platform admin"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error escalating dispute: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to escalate dispute: {str(e)}",
        )


@router.post("/owner/{dispute_id}/message")
async def add_owner_message(
    dispute_id: str,
    message: DisputeMessageCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Add a message from the business owner to the dispute.
    Supports internal notes visible only to the owner.
    When owner sends a public (non-internal) message, AI auto-reply is paused.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Verify ownership
        dispute = supabase.table("ai_disputes").select("website_id, status").eq(
            "id", dispute_id
        ).execute()

        if not dispute.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        website = supabase.table("websites").select("id").eq(
            "id", dispute.data[0]["website_id"]
        ).eq("user_id", user_id).execute()

        if not website.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this dispute",
            )

        msg_data = {
            "dispute_id": dispute_id,
            "sender_type": "owner",
            "sender_id": user_id,
            "sender_name": message.sender_name or "Business Owner",
            "message": message.message,
            "attachments": message.attachments or [],
            "is_internal": message.is_internal,
        }

        result = supabase.table("dispute_messages").insert(msg_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message",
            )

        # Pause AI auto-reply when owner sends a public message (takes over conversation)
        if not message.is_internal:
            supabase.table("ai_disputes").update({
                "ai_auto_reply_disabled": True,
            }).eq("id", dispute_id).execute()

            logger.info(
                f"AI auto-reply disabled for dispute {dispute_id} - owner took over"
            )

        return DisputeMessageResponse(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding owner message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}",
        )


@router.post("/owner/{dispute_id}/ai-auto-reply")
async def toggle_ai_auto_reply(
    dispute_id: str,
    enabled: bool = Query(..., description="Set to true to enable AI auto-reply, false to disable"),
    current_user: dict = Depends(get_current_user),
):
    """
    Toggle AI auto-reply for a specific dispute.
    Owner can re-enable AI replies after taking over, or disable them.
    """
    supabase = get_supabase_client()
    user_id = current_user.get("sub")

    try:
        # Verify ownership
        dispute = supabase.table("ai_disputes").select("website_id, dispute_number").eq(
            "id", dispute_id
        ).execute()

        if not dispute.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dispute not found",
            )

        website = supabase.table("websites").select("id").eq(
            "id", dispute.data[0]["website_id"]
        ).eq("user_id", user_id).execute()

        if not website.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this dispute",
            )

        # Update the ai_auto_reply_disabled flag (inverted: enabled=True means disabled=False)
        supabase.table("ai_disputes").update({
            "ai_auto_reply_disabled": not enabled,
        }).eq("id", dispute_id).execute()

        state = "enabled" if enabled else "disabled"
        logger.info(
            f"AI auto-reply {state} for dispute {dispute.data[0]['dispute_number']} by owner"
        )

        return {
            "status": "success",
            "message": f"AI auto-reply {state} for this dispute",
            "ai_auto_reply_enabled": enabled,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling AI auto-reply: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle AI auto-reply: {str(e)}",
        )
