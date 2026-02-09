"""
Pydantic schemas for BinaApp AI Dispute Resolution System
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =====================================================
# ENUMS
# =====================================================

class DisputeCategory(str, Enum):
    WRONG_ITEMS = "wrong_items"
    MISSING_ITEMS = "missing_items"
    QUALITY_ISSUE = "quality_issue"
    LATE_DELIVERY = "late_delivery"
    DAMAGED_ITEMS = "damaged_items"
    OVERCHARGED = "overcharged"
    NEVER_DELIVERED = "never_delivered"
    RIDER_ISSUE = "rider_issue"
    OTHER = "other"


class DisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    AWAITING_RESPONSE = "awaiting_response"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"
    REJECTED = "rejected"


class DisputeResolutionType(str, Enum):
    FULL_REFUND = "full_refund"
    PARTIAL_REFUND = "partial_refund"
    REPLACEMENT = "replacement"
    CREDIT = "credit"
    APOLOGY = "apology"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class DisputePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DisputeMessageSender(str, Enum):
    CUSTOMER = "customer"
    OWNER = "owner"
    ADMIN = "admin"
    AI = "ai"
    SYSTEM = "system"


# =====================================================
# DISPUTE SCHEMAS
# =====================================================

class DisputeCreate(BaseModel):
    """Schema for creating a new dispute"""
    order_id: str
    category: DisputeCategory
    description: str = Field(..., min_length=10, max_length=2000)
    evidence_urls: Optional[List[str]] = None
    disputed_amount: Optional[float] = None
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None


class DisputeResponse(BaseModel):
    """Schema for dispute response"""
    id: str
    dispute_number: str
    order_id: str
    website_id: str
    customer_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    category: str
    description: str
    evidence_urls: Optional[List[str]] = None
    order_amount: float
    disputed_amount: Optional[float] = None
    refund_amount: Optional[float] = None
    ai_category_confidence: Optional[float] = None
    ai_severity_score: Optional[int] = None
    ai_recommendation: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    status: str
    resolution_type: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    priority: str
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DisputeListResponse(BaseModel):
    """Schema for listing disputes"""
    disputes: List[DisputeResponse]
    total: int
    page: int
    per_page: int


class DisputeStatusUpdate(BaseModel):
    """Schema for updating dispute status"""
    status: DisputeStatus
    notes: Optional[str] = None


class DisputeResolve(BaseModel):
    """Schema for resolving a dispute"""
    resolution_type: DisputeResolutionType
    resolution_notes: Optional[str] = None
    refund_amount: Optional[float] = None


class OwnerResponse(BaseModel):
    """Schema for business owner responding to a dispute"""
    message: str = Field(..., min_length=1, max_length=2000)
    accept_fault: bool = False
    proposed_resolution: Optional[DisputeResolutionType] = None
    proposed_refund_amount: Optional[float] = None


# =====================================================
# DISPUTE MESSAGE SCHEMAS
# =====================================================

class DisputeMessageCreate(BaseModel):
    """Schema for creating a dispute message"""
    message: str = Field(..., min_length=1, max_length=2000)
    sender_type: DisputeMessageSender
    sender_name: Optional[str] = None
    attachments: Optional[List[str]] = None
    is_internal: bool = False


class DisputeMessageResponse(BaseModel):
    """Schema for dispute message response"""
    id: str
    dispute_id: str
    sender_type: str
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    message: str
    attachments: Optional[List[str]] = None
    is_internal: bool = False
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# DISPUTE STATUS HISTORY SCHEMAS
# =====================================================

class DisputeStatusHistoryResponse(BaseModel):
    """Schema for dispute status history"""
    id: str
    dispute_id: str
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =====================================================
# AI ANALYSIS SCHEMAS
# =====================================================

class AIDisputeAnalysis(BaseModel):
    """Schema for AI analysis of a dispute"""
    category_confidence: float = Field(..., ge=0, le=1)
    severity_score: int = Field(..., ge=1, le=10)
    recommended_resolution: DisputeResolutionType
    recommended_refund_percentage: Optional[float] = Field(None, ge=0, le=100)
    priority: DisputePriority
    reasoning: str
    suggested_response: str
    risk_flags: List[str] = []
    similar_dispute_pattern: bool = False


class DisputeSummary(BaseModel):
    """Schema for dispute dashboard summary"""
    total_disputes: int = 0
    open_disputes: int = 0
    resolved_disputes: int = 0
    escalated_disputes: int = 0
    avg_resolution_time_hours: Optional[float] = None
    total_refunded: float = 0
    resolution_rate: float = 0
    by_category: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}
