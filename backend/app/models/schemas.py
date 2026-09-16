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

    @field_validator("email")
    @classmethod
    def reject_disposable_email(cls, v: str) -> str:
        """
        Block known disposable/temporary email providers at signup.

        EmailStr already enforces RFC format; this adds a domain blocklist so
        throwaway inboxes can't create accounts. Real proof-of-ownership is
        still the 6-digit verification code. Controlled by
        settings.BLOCK_DISPOSABLE_EMAILS so it can be disabled via env.
        """
        # Imported lazily to avoid a circular import (config -> schemas).
        from app.core.config import settings
        from app.core.disposable_emails import is_disposable_email

        if getattr(settings, "BLOCK_DISPOSABLE_EMAILS", True) and is_disposable_email(v):
            raise ValueError(
                "Alamat e-mel sekali guna tidak dibenarkan. "
                "Sila gunakan e-mel kekal. / Disposable email addresses are not allowed."
            )
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    """Payload for confirming a registration with the 6-digit code."""
    code: str = Field(..., min_length=4, max_length=10)


class UserResponse(UserBase):
    id: str
    created_at: datetime
    subscription_tier: SubscriptionTier
    websites_count: int = 0

    class Config:
        from_attributes = True


# Website Generation Schemas
class MenuItemInput(BaseModel):
    """One merchant-supplied menu/product item — the source of truth.

    Prices are strings on purpose: they must reach the page EXACTLY as the
    merchant typed them ("RM7.00", "RM18/pax", "RM5 - RM8"). Parsing them
    into a float would silently reformat or round a business-critical field,
    and Malaysian F&B pricing is full of per-pax and range forms a numeric
    type cannot represent.
    """
    name: str = Field(..., min_length=1, max_length=120)
    price: Optional[str] = Field(default=None, max_length=40)
    description: Optional[str] = Field(default=None, max_length=400)
    category: Optional[str] = Field(default=None, max_length=60)

    @field_validator("name", "price", "description", "category")
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("price")
    @classmethod
    def normalise_price(cls, v):
        """Round 2 (§B6): prices are decimals rendered by one formatter.
        "6" → "RM6.00", "RM 12,50" → "RM12.50"; "RM25.oo" is rejected —
        never coerced, never guessed."""
        if v is None or not str(v).strip():
            return None
        from app.services.data_consistency import format_price
        formatted = format_price(v)
        if formatted is None:
            raise ValueError(f"Harga tidak sah: '{v}'. Masukkan nombor sahaja, contoh 12.50")
        return formatted


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
    color_mode: Optional[str] = Field(default="light", description="Color mode: 'light' or 'dark'")
    design_style: Optional[str] = Field(
        default=None,
        max_length=20,
        description=(
            "Explicit design-style pick from the create-page picker "
            "('doodle', 'elegant', 'minimal', 'playful', 'bold', 'classic'). "
            "None = let the design system choose."
        ),
    )
    template_id: Optional[str] = Field(default=None, description="Design template ID from template gallery (e.g., 'elegance_dark', 'fresh_clean')")
    # Senior Designer mode (design_director.py). The merchant's free-text
    # design direction — "gelap & mewah, aksen emas, ala hotel butik" — is
    # the highest-priority DESIGN input: it steers the AI's own design
    # concept and is repeated in the HTML prompt with an explicit
    # precedence rule (facts > brief > concept > house defaults).
    design_brief: Optional[str] = Field(
        default=None,
        max_length=1500,
        description=(
            "Free-text design direction from the merchant (look, feel, "
            "colours, references, sections). Optional; steers the AI "
            "designer and overrides stylistic defaults, never facts."
        ),
    )
    design_freedom: Optional[str] = Field(
        default=None,
        max_length=20,
        description=(
            "'designer' = the AI writes its own concept and owns the visual "
            "design (default); 'guided' = the pre-upgrade seeded design "
            "system with fixed hero/layout. None = server default."
        ),
    )
    show_prices: bool = Field(
        default=True,
        description=(
            "The create page's 'Senarai Harga' toggle. True renders each "
            "item's price; False renders the items without prices so the "
            "customer asks via WhatsApp. Until now this flag was read into "
            "the request body and then dropped — the only handler for it "
            "lived in a module that is never mounted."
        ),
    )
    hero_image_prompt: Optional[str] = Field(
        default=None,
        max_length=400,
        description=(
            "Merchant's own description of the hero VISUAL (e.g. 'dark luxury "
            "hair salon interior, warm gold lighting, empty styling chair, "
            "cinematic'). When present this REPLACES the auto-built hero "
            "prompt outright — the merchant asked for a specific picture and "
            "must get it. Distinct from the hero VIDEO prompt, which "
            "describes motion applied to this image afterwards."
        ),
    )
    # Designer-grade generation (two-pass). Each of these maps an existing
    # create-page control onto the design plan so the merchant's choice is a
    # hard constraint (see docs/design/DESIGNER_GRADE_GENERATION.md).
    include_contact_form: bool = Field(
        default=True,
        description="'Borang Tempahan' feature. False = no contact-form slot at all.",
    )
    include_social: bool = Field(
        default=False,
        description="'Social Media' feature. False = no social icons/links anywhere.",
    )
    social_media: Optional[dict] = Field(
        default=None,
        description="Social handles {instagram, facebook, tiktok} when the feature is on.",
    )
    payment_methods: Optional[List[str]] = Field(
        default=None,
        description="'Cara terima bayaran': subset of ['cod', 'qr']. Drives checkout copy and the footer payment badges only.",
    )
    hero_video: bool = Field(
        default=False,
        description="'Video latar hero' is on: the hero treatment is forced to photo-full-bleed with the video as the page-load moment.",
    )
    opening_hours: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Opening hours exactly as the merchant wrote them. None = hours are never rendered.",
    )
    multi_style: bool = Field(
        default=False,
        description="'Multi-style preview': Pass 1 returns 3 plans and the merchant picks one.",
    )
    is_24h: bool = Field(
        default=False,
        description="Round 2 (§B5): the business never closes (00:00–23:59, every day, or the story says 24 jam). The page and the open-now pill say 'Buka 24 jam'.",
    )
    preferred_plan: Optional[dict] = Field(
        default=None,
        description=(
            "A design plan (as returned in a multi-style preview) the merchant already picked. "
            "Pass 1 validates it instead of asking the model for a new one, so the full critique loop "
            "runs on exactly the plan they chose."
        ),
    )
    menu_items: Optional[List[MenuItemInput]] = Field(
        default=[],
        description=(
            "Structured menu/product items supplied by the merchant. When "
            "present these are the SOURCE OF TRUTH: names and prices are "
            "rendered verbatim and the generator may not rename, merge, "
            "round, or invent items. When absent the site renders a visible "
            "'add your items' placeholder instead of fabricated items."
        ),
    )

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

    @field_validator("payment_methods")
    @classmethod
    def validate_payment_methods(cls, v):
        if not v:
            return None
        allowed = []
        for item in v:
            key = str(item).strip().lower()
            if key in ("cod", "qr") and key not in allowed:
                allowed.append(key)
        return allowed or None

    @field_validator("design_freedom")
    @classmethod
    def validate_design_freedom(cls, v):
        """Lenient: unknown values mean 'server default', never a 422 — an
        older client or a typo must not block a generation."""
        if v is None:
            return None
        value = str(v).strip().lower()
        return value if value in ("designer", "guided") else None

    @field_validator("design_brief")
    @classmethod
    def validate_design_brief(cls, v):
        if v is None:
            return None
        value = v.strip()
        return value or None


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
    # AI prompt persistence (migration 039) — surfaced so the dashboard
    # can show "regenerated N times" and pre-fill the regenerate textarea
    # with the user's last description.
    description: Optional[str] = None
    generation_count: Optional[int] = None

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


# Regenerate request: PATCH body for /websites/{id}/regenerate.
# All fields optional — when description is omitted the endpoint reuses
# the persisted one stored on the websites row.
class WebsiteRegenerateRequest(BaseModel):
    description: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=5000,
        description=(
            "Updated natural-language prompt. If omitted, the previously "
            "stored description on the website row is reused."
        ),
    )
    # Same semantics as on WebsiteGenerationRequest: an optional design
    # direction for the AI designer, and an optional freedom-mode override.
    design_brief: Optional[str] = Field(default=None, max_length=1500)
    design_freedom: Optional[str] = Field(default=None, max_length=20)

    @field_validator("design_freedom")
    @classmethod
    def validate_design_freedom(cls, v):
        if v is None:
            return None
        value = str(v).strip().lower()
        return value if value in ("designer", "guided") else None

    @field_validator("design_brief")
    @classmethod
    def validate_design_brief(cls, v):
        if v is None:
            return None
        value = v.strip()
        return value or None


# AI Generation Schemas
class AIGenerationResponse(BaseModel):
    html_content: str
    css_content: Optional[str] = None
    js_content: Optional[str] = None
    meta_title: str
    meta_description: str
    sections: List[str]
    integrations_included: List[str]
    ai_images_count: int = 0
    # Truncation diagnostics surfaced from ai_service so callers can persist
    # them on generation_jobs (see Bug 1 fix).
    was_truncated: bool = False
    truncation_retries: int = 0
    needs_manual_review: bool = False
    # Step-by-step timing breakdown for the generation pipeline — used to
    # identify bottlenecks in production (see Bug 3 diagnostic instrumentation).
    step_timings: Dict[str, float] = {}
    # What each step DID, beside how long it took: "success", "skipped",
    # "fallback (error)". A 60.00s duration on a step with a 60s timeout is
    # a timeout, and recording only the duration made it read as a
    # completion (mkl: qwen_refine and qwen_css_refine both timed out and
    # both looked like finished work).
    step_outcomes: Dict[str, str] = {}
    # Post-generation validation result (generation_validator). validation_ok
    # False means the output contradicts the merchant's own brief — callers
    # MUST fail closed and surface validation_errors rather than publishing.
    validation_ok: bool = True
    validation_errors: List[str] = []
    validation_warnings: List[str] = []


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
