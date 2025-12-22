"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class WebsiteStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    PUBLISHED = "published"
    FAILED = "failed"


class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Language(str, Enum):
    ENGLISH = "en"
    MALAY = "ms"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: str
    created_at: datetime
    subscription_tier: SubscriptionTier
    websites_count: int = 0

    class Config:
        from_attributes = True


# Website Generation Schemas
class WebsiteGenerationRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Description of the website to generate in Bahasa or English"
    )
    language: Language = Language.MALAY
    business_name: str = Field(..., min_length=2, max_length=100)
    business_type: Optional[str] = Field(None, max_length=50)
    subdomain: str = Field(
        ...,
        min_length=3,
        max_length=63,
        description="Desired subdomain (e.g., 'kedairuncit' for kedairuncit.binaapp.my)"
    )
    include_whatsapp: bool = True
    whatsapp_number: Optional[str] = None
    include_maps: bool = True
    location_address: Optional[str] = None
    include_ecommerce: bool = False
    contact_email: Optional[EmailStr] = None
    uploaded_images: Optional[list] = Field(default=[], description="List of uploaded image URLs to use in the website")

    @validator("subdomain")
    def validate_subdomain(cls, v):
        """Validate subdomain format"""
        import re
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", v):
            raise ValueError(
                "Subdomain must contain only lowercase letters, numbers, and hyphens"
            )
        return v

    @validator("whatsapp_number")
    def validate_whatsapp(cls, v, values):
        """Validate WhatsApp number if WhatsApp is enabled"""
        if values.get("include_whatsapp") and not v:
            raise ValueError("WhatsApp number is required when WhatsApp is enabled")
        return v


class WebsiteResponse(BaseModel):
    id: str
    user_id: str
    business_name: str
    subdomain: str
    full_url: str
    status: WebsiteStatus
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    html_content: Optional[str] = None
    preview_url: Optional[str] = None

    class Config:
        from_attributes = True


class WebsiteListResponse(BaseModel):
    id: str
    business_name: str
    subdomain: str
    full_url: str
    status: WebsiteStatus
    created_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# AI Generation Schemas
class AIGenerationResponse(BaseModel):
    html_content: str
    css_content: Optional[str] = None
    js_content: Optional[str] = None
    meta_title: str
    meta_description: str
    sections: List[str]
    integrations_included: List[str]


# Publishing Schemas
class PublishRequest(BaseModel):
    website_id: str


class PublishResponse(BaseModel):
    success: bool
    url: str
    message: str
    published_at: datetime


# Payment Schemas
class SubscriptionPlan(BaseModel):
    tier: SubscriptionTier
    name: str
    price_monthly: float
    price_yearly: float
    features: List[str]
    max_websites: int
    custom_domain: bool


class CheckoutSessionRequest(BaseModel):
    tier: SubscriptionTier
    billing_period: str = Field(..., pattern="^(monthly|yearly)$")


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str


class WebhookEvent(BaseModel):
    type: str
    data: Dict[str, Any]


# Template Schemas
class TemplateCategory(str, Enum):
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    SERVICES = "services"
    PORTFOLIO = "portfolio"
    LANDING = "landing"


class TemplateResponse(BaseModel):
    id: str
    name: str
    category: TemplateCategory
    description: str
    thumbnail_url: str
    preview_url: str


# Analytics Schemas
class WebsiteAnalytics(BaseModel):
    website_id: str
    total_views: int
    unique_visitors: int
    whatsapp_clicks: int
    form_submissions: int
    last_updated: datetime


# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# Health Check
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
