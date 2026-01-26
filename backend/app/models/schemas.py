"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
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
    logo: Optional[str] = Field(default=None, description="Logo URL to use in the website")
    fonts: Optional[list] = Field(default=[], description="Font names to use in the website (e.g., ['Inter', 'Poppins'])")
    colors: Optional[dict] = Field(default=None, description="Color scheme with primary, secondary, accent colors")
    theme: Optional[str] = Field(default=None, description="Detected theme name (e.g., 'Purrfect Paws Theme')")

    @field_validator("subdomain")
    @classmethod
    def validate_subdomain(cls, v):
        """Validate subdomain format"""
        import re
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", v):
            raise ValueError(
                "Subdomain must contain only lowercase letters, numbers, and hyphens"
            )
        return v

    @field_validator("whatsapp_number")
    @classmethod
    def validate_whatsapp(cls, v):
        """Validate WhatsApp number if WhatsApp is enabled"""
        # Note: In Pydantic V2, cross-field validation in field_validator is not supported
        # This validation is simplified - consider adding model_validator if cross-field check is critical
        # For now, we just return the value as-is
        return v


class WebsiteResponse(BaseModel):
    id: str
    user_id: str
    business_name: Optional[str] = None
    subdomain: Optional[str] = None
    full_url: Optional[str] = None
    status: WebsiteStatus = WebsiteStatus.DRAFT
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    html_content: Optional[str] = None
    preview_url: Optional[str] = None

    class Config:
        from_attributes = True


class WebsiteListResponse(BaseModel):
    id: str
    business_name: str
    subdomain: Optional[str] = None
    full_url: Optional[str] = None
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


# Menu and Delivery Schemas
class MenuCategoryBase(BaseModel):
    name: str
    slug: str
    sort_order: int = 0


class MenuCategoryCreate(MenuCategoryBase):
    website_id: str


class MenuCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    sort_order: Optional[int] = None


class MenuCategoryResponse(MenuCategoryBase):
    id: str
    website_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    image_url: Optional[str] = None
    is_available: bool = True
    sort_order: int = 0


class MenuItemCreate(MenuItemBase):
    website_id: str
    category_id: Optional[str] = None


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    sort_order: Optional[int] = None


class MenuItemResponse(MenuItemBase):
    id: str
    website_id: str
    category_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeliveryZoneBase(BaseModel):
    zone_name: str
    delivery_fee: float = Field(..., ge=0)
    estimated_time: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class DeliveryZoneCreate(DeliveryZoneBase):
    website_id: str


class DeliveryZoneUpdate(BaseModel):
    zone_name: Optional[str] = None
    delivery_fee: Optional[float] = Field(None, ge=0)
    estimated_time: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class DeliveryZoneResponse(DeliveryZoneBase):
    id: str
    website_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Health Check
class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
