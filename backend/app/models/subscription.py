"""
Pydantic schemas for subscription, payment, usage limits, and addon purchases.

BinaApp Pricing:
- Starter: RM5/month
- Basic: RM29/month
- Pro: RM49/month
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class SubscriptionTierEnum(str, Enum):
    """Subscription tier options"""
    STARTER = "starter"
    BASIC = "basic"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    """Subscription status options"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class BillingCycle(str, Enum):
    """Billing cycle options"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PaymentType(str, Enum):
    """Payment type options"""
    SUBSCRIPTION = "subscription"
    ADDON = "addon"
    UPGRADE = "upgrade"


class PaymentStatus(str, Enum):
    """Payment status options"""
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"


class AddonType(str, Enum):
    """Addon type options"""
    WEBSITE = "website"
    DELIVERY_ZONE = "delivery_zone"
    AI_HERO = "ai_hero"
    AI_IMAGE = "ai_image"
    RIDER = "rider"


# ==========================================
# SUBSCRIPTION SCHEMAS
# ==========================================

class SubscriptionBase(BaseModel):
    """Base subscription schema"""
    tier: SubscriptionTierEnum = SubscriptionTierEnum.STARTER
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    price: Decimal = Field(default=Decimal("5.00"), ge=0)
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    auto_renew: bool = True


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription"""
    user_id: str
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None


class SubscriptionUpdate(BaseModel):
    """Schema for updating a subscription"""
    tier: Optional[SubscriptionTierEnum] = None
    status: Optional[SubscriptionStatus] = None
    price: Optional[Decimal] = Field(default=None, ge=0)
    billing_cycle: Optional[BillingCycle] = None
    auto_renew: Optional[bool] = None
    toyyibpay_bill_code: Optional[str] = None
    toyyibpay_subscription_id: Optional[str] = None
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription response"""
    id: int
    user_id: str
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None
    toyyibpay_bill_code: Optional[str] = None
    toyyibpay_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# PAYMENT SCHEMAS
# ==========================================

class PaymentBase(BaseModel):
    """Base payment schema"""
    amount: Decimal = Field(..., ge=0)
    payment_type: PaymentType
    payment_method: str = "toyyibpay"
    status: PaymentStatus = PaymentStatus.PENDING


class PaymentCreate(PaymentBase):
    """Schema for creating a new payment"""
    user_id: str
    subscription_id: Optional[int] = None
    toyyibpay_bill_code: Optional[str] = None


class PaymentUpdate(BaseModel):
    """Schema for updating a payment"""
    status: Optional[PaymentStatus] = None
    toyyibpay_payment_id: Optional[str] = None
    paid_at: Optional[datetime] = None


class PaymentResponse(PaymentBase):
    """Schema for payment response"""
    id: int
    user_id: str
    subscription_id: Optional[int] = None
    toyyibpay_bill_code: Optional[str] = None
    toyyibpay_payment_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# USAGE LIMITS SCHEMAS
# ==========================================

class UsageLimitsBase(BaseModel):
    """Base usage limits schema"""
    websites_count: int = 0
    websites_limit: Optional[int] = None
    menu_items_count: int = 0
    menu_items_limit: Optional[int] = None
    ai_hero_generations: int = 0
    ai_hero_limit: Optional[int] = None
    ai_menu_images: int = 0
    ai_menu_limit: Optional[int] = None
    delivery_zones_count: int = 0
    delivery_zones_limit: Optional[int] = None
    riders_count: int = 0
    riders_limit: Optional[int] = None


class UsageLimitsCreate(UsageLimitsBase):
    """Schema for creating usage limits"""
    user_id: str
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None


class UsageLimitsUpdate(BaseModel):
    """Schema for updating usage limits"""
    websites_count: Optional[int] = None
    websites_limit: Optional[int] = None
    menu_items_count: Optional[int] = None
    menu_items_limit: Optional[int] = None
    ai_hero_generations: Optional[int] = None
    ai_hero_limit: Optional[int] = None
    ai_menu_images: Optional[int] = None
    ai_menu_limit: Optional[int] = None
    delivery_zones_count: Optional[int] = None
    delivery_zones_limit: Optional[int] = None
    riders_count: Optional[int] = None
    riders_limit: Optional[int] = None
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None


class UsageLimitsResponse(UsageLimitsBase):
    """Schema for usage limits response"""
    id: int
    user_id: str
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# ADDON PURCHASE SCHEMAS
# ==========================================

class AddonPurchaseBase(BaseModel):
    """Base addon purchase schema"""
    addon_type: AddonType
    quantity: int = Field(default=1, ge=1)
    price_per_unit: Decimal = Field(..., ge=0)
    total_price: Decimal = Field(..., ge=0)
    is_recurring: bool = False
    status: str = "active"


class AddonPurchaseCreate(AddonPurchaseBase):
    """Schema for creating an addon purchase"""
    user_id: str
    billing_start: Optional[date] = None
    billing_end: Optional[date] = None
    toyyibpay_bill_code: Optional[str] = None


class AddonPurchaseUpdate(BaseModel):
    """Schema for updating an addon purchase"""
    status: Optional[str] = None
    billing_end: Optional[date] = None


class AddonPurchaseResponse(AddonPurchaseBase):
    """Schema for addon purchase response"""
    id: int
    user_id: str
    billing_start: Optional[date] = None
    billing_end: Optional[date] = None
    toyyibpay_bill_code: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# UTILITY SCHEMAS
# ==========================================

class SubscriptionUpgradeRequest(BaseModel):
    """Schema for subscription upgrade request"""
    new_tier: SubscriptionTierEnum
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class UsageCheckResponse(BaseModel):
    """Schema for checking if user can use a resource"""
    can_use: bool
    current_count: int
    limit: Optional[int] = None
    remaining: Optional[int] = None
    message: Optional[str] = None


class SubscriptionPlanInfo(BaseModel):
    """Schema for subscription plan information"""
    tier: SubscriptionTierEnum
    name: str
    price_monthly: Decimal
    price_yearly: Decimal
    websites: Optional[int] = None
    menu_items: Optional[int] = None
    ai_hero_generations: Optional[int] = None
    ai_menu_images: Optional[int] = None
    delivery_zones: Optional[int] = None
    riders: Optional[int] = None
    monthly_reset: bool = False


class IncrementUsageRequest(BaseModel):
    """Schema for incrementing usage count"""
    resource: str = Field(..., description="Resource type: websites, menu_items, ai_hero, ai_menu, delivery_zones, riders")
    amount: int = Field(default=1, ge=1)
