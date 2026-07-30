"""
Application Configuration
Loads environment variables and provides settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "BinaApp"
    ENVIRONMENT: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=False, env="APP_DEBUG")
    API_VERSION: str = "v1"
    
    # URLs
    BASE_URL: str = Field(default="http://localhost:3000", env="BASE_URL")
    API_URL: str = Field(default="http://localhost:8000", env="API_URL")
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    BACKEND_URL: str = Field(
        default="https://binaapp-backend.onrender.com",
        env="BACKEND_URL",
        description="Production backend URL for preview endpoints"
    )
    
    # CORS
    # SECURITY: Removed "*" and "null" which allow requests from ANY origin
    # In production, set CORS_ORIGINS environment variable with actual domains
    # Example: CORS_ORIGINS="https://binaapp.my,https://www.binaapp.my,https://dashboard.binaapp.my"
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        # Production domains - override via environment variable
        "https://binaapp.my",
        "https://www.binaapp.my",
        "https://dashboard.binaapp.my",
        "https://binaapp-backend.onrender.com"
    ]
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Supabase
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_ANON_KEY: str = Field(default="", env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", env="SUPABASE_SERVICE_ROLE_KEY")
    
    # Database
    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")
    
    # AI APIs
    DEEPSEEK_API_KEY: str = Field(default="", env="DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL: str = Field(
        default="https://api.deepseek.com",  # No /v1 - OpenAI client adds it
        env="DEEPSEEK_API_URL"
    )
    DEEPSEEK_MODEL: str = Field(
        default="deepseek-v4-flash",
        env="DEEPSEEK_MODEL"
    )
    DEEPSEEK_MODEL_PRO: str = Field(
        default="deepseek-v4-pro",
        env="DEEPSEEK_MODEL_PRO"
    )

    # GLM / Z.ai (primary HTML generator when USE_GLM_FOR_HTML is on).
    # NOTE: the Render env var for the base URL is named ZAI_BASE_URL —
    # ai_service.py accepts either name (ZAI_API_URL wins if both are set).
    ZAI_API_KEY: str = Field(default="", env="ZAI_API_KEY")
    ZAI_API_URL: str = Field(
        default="https://api.z.ai/api/paas/v4",
        env="ZAI_API_URL"
    )
    ZAI_MODEL: str = Field(
        default="glm-5.2",
        env="ZAI_MODEL"
    )
    # Z.ai IMAGE model for the /images/generations endpoint (separate from
    # the HTML chat model above). Valid model codes are 'glm-image' and
    # 'cogview-4-250304' — plain 'cogview-4' is rejected by the API with
    # error 1211 "Unknown Model".
    ZAI_IMAGE_MODEL: str = Field(default="glm-image", env="ZAI_IMAGE_MODEL")
    # Output-token cap for GLM HTML generation (mirrors AI_DEEPSEEK_MAX_TOKENS).
    AI_GLM_MAX_TOKENS: int = Field(default=16000, env="AI_GLM_MAX_TOKENS")
    # Per-call timeout for the GLM primary generation — tighter than the
    # 300s primary budget so a hung Z.ai can't double total latency before
    # the DeepSeek fallback gets its turn.
    AI_GLM_TIMEOUT_SECONDS: float = Field(default=240, env="AI_GLM_TIMEOUT_SECONDS")
    # Feature flag: try GLM first for HTML generation, falling back to the
    # untouched DeepSeek path on any failure. Flip off in Render for an
    # instant rollback to pure DeepSeek — no code change needed.
    USE_GLM_FOR_HTML: bool = Field(default=False, env="USE_GLM_FOR_HTML")
    # Feature flag: premium design critique loop. When on, a successful GLM
    # generation is reviewed once by DeepSeek against the 8 hard rules and,
    # if the critique reports issues, GLM gets exactly one revision request.
    # Ships dark (default OFF); any review failure falls back to the
    # original HTML. See ai_service.PREMIUM_DESIGN_LOOP.
    PREMIUM_DESIGN_LOOP: bool = Field(default=False, env="PREMIUM_DESIGN_LOOP")
    # Sensitive-claim sanitizer pattern overrides (see
    # app.services.claim_sanitizer). Both are JSON arrays of
    # {"label", "pattern", "verify"} entries and are read at call time by
    # the sanitizer, so the list can be extended in Render without a code
    # change or redeploy. SENSITIVE_CLAIM_PATTERNS replaces the built-in
    # defaults entirely; SENSITIVE_CLAIM_PATTERNS_EXTRA appends to whichever
    # list is active.
    SENSITIVE_CLAIM_PATTERNS: Optional[str] = Field(None, env="SENSITIVE_CLAIM_PATTERNS")
    SENSITIVE_CLAIM_PATTERNS_EXTRA: Optional[str] = Field(None, env="SENSITIVE_CLAIM_PATTERNS_EXTRA")

    # Qwen AI (Optional)
    QWEN_API_KEY: Optional[str] = Field(None, env="QWEN_API_KEY")
    QWEN_API_URL: str = Field(
        default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",  # International/Singapore region
        env="QWEN_API_URL"
    )
    QWEN_MODEL: str = Field(
        default="qwen-max",  # Qwen Max model (use qwen-plus for faster/cheaper)
        env="QWEN_MODEL"
    )

    # Anthropic Claude AI (for AI Email Support)
    ANTHROPIC_API_KEY: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-5-sonnet-20241022",
        env="ANTHROPIC_MODEL"
    )
    AI_EMAIL_SUPPORT_ENABLED: bool = Field(default=True, env="AI_EMAIL_SUPPORT_ENABLED")
    AI_CONFIDENCE_THRESHOLD: float = Field(default=0.7, env="AI_CONFIDENCE_THRESHOLD")
    
    # Supabase Storage
    STORAGE_BUCKET_NAME: str = Field(default="websites", env="STORAGE_BUCKET_NAME")
    
    # Stripe
    STRIPE_PUBLIC_KEY: str = Field(default="", env="STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY: str = Field(default="", env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(default="", env="STRIPE_WEBHOOK_SECRET")

    # ToyyibPay
    TOYYIBPAY_SECRET_KEY: str = Field(default="", env="TOYYIBPAY_SECRET_KEY")
    TOYYIBPAY_CATEGORY_CODE: str = Field(default="", env="TOYYIBPAY_CATEGORY_CODE")
    TOYYIBPAY_SANDBOX: bool = Field(default=False, env="TOYYIBPAY_SANDBOX")
    TOYYIBPAY_CALLBACK_URL: str = Field(default="", env="TOYYIBPAY_CALLBACK_URL")
    TOYYIBPAY_RETURN_URL: str = Field(default="", env="TOYYIBPAY_RETURN_URL")
    
    # Domain Configuration
    MAIN_DOMAIN: str = Field(default="binaapp.my", env="MAIN_DOMAIN")
    SUBDOMAIN_SUFFIX: str = Field(default=".binaapp.my", env="SUBDOMAIN_SUFFIX")
    
    # Security
    JWT_SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")

    # Supabase JWT Secret (for verifying Supabase-signed tokens)
    SUPABASE_JWT_SECRET: Optional[str] = Field(None, env="SUPABASE_JWT_SECRET")

    # Supabase JWT Audience (for enhanced JWT verification)
    # Set to "authenticated" to enable audience verification
    # Increases security by preventing token reuse across services
    SUPABASE_JWT_AUDIENCE: Optional[str] = Field(None, env="SUPABASE_JWT_AUDIENCE")

    # Salt for the daily-rotating visitor hash used by PDPA-safe analytics.
    # Falls back to JWT_SECRET_KEY when unset (see analytics_tracking service).
    ANALYTICS_HASH_SALT: Optional[str] = Field(None, env="ANALYTICS_HASH_SALT")

    # API Keys for external integrations (comma-separated)
    # Example: BINAAPP_API_KEYS="bina_abc123...,bina_xyz789..."
    BINAAPP_API_KEYS: Optional[str] = Field(None, env="BINAAPP_API_KEYS")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Email (Zoho SMTP)
    SMTP_HOST: Optional[str] = Field(default="smtp.zoho.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    FROM_EMAIL: Optional[str] = Field(default="info@binaapp.my", env="FROM_EMAIL")
    FROM_NAME: str = Field(default="BinaApp", env="FROM_NAME")
    SUPPORT_EMAIL: str = Field(default="support.team@binaapp.my", env="SUPPORT_EMAIL")
    ADMIN_EMAIL: str = Field(default="admin@binaapp.my", env="ADMIN_EMAIL")
    NOREPLY_EMAIL: str = Field(default="info@binaapp.my", env="NOREPLY_EMAIL")
    UNLIMITED_ACCESS_EMAILS: List[str] = Field(default=[], env="UNLIMITED_ACCESS_EMAILS")

    # Email verification (6-digit code sent on registration; gates publish + pay)
    EMAIL_VERIFICATION_ENABLED: bool = Field(default=True, env="EMAIL_VERIFICATION_ENABLED")
    EMAIL_VERIFICATION_CODE_TTL_MINUTES: int = Field(default=15, env="EMAIL_VERIFICATION_CODE_TTL_MINUTES")
    EMAIL_VERIFICATION_MAX_ATTEMPTS: int = Field(default=5, env="EMAIL_VERIFICATION_MAX_ATTEMPTS")
    BLOCK_DISPOSABLE_EMAILS: bool = Field(default=True, env="BLOCK_DISPOSABLE_EMAILS")

    @validator("UNLIMITED_ACCESS_EMAILS", pre=True)
    def parse_unlimited_access_emails(cls, v):
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        return v

    # Email Polling (IMAP) - for support.team@binaapp.my
    SUPPORT_EMAIL_PASSWORD: Optional[str] = Field(None, env="SUPPORT_EMAIL_PASSWORD")
    SUPPORT_SMTP_HOST: str = Field(default="smtppro.zoho.com", env="SUPPORT_SMTP_HOST")
    SUPPORT_SMTP_PORT: int = Field(default=465, env="SUPPORT_SMTP_PORT")
    SUPPORT_SMTP_USER: Optional[str] = Field(None, env="SUPPORT_SMTP_USER")
    SUPPORT_SMTP_PASSWORD: Optional[str] = Field(None, env="SUPPORT_SMTP_PASSWORD")
    EMAIL_POLLING_ENABLED: bool = Field(default=True, env="EMAIL_POLLING_ENABLED")
    EMAIL_POLLING_INTERVAL_SECONDS: int = Field(default=120, env="EMAIL_POLLING_INTERVAL_SECONDS")
    IMAP_SERVER: str = Field(default="imap.zoho.com", env="IMAP_SERVER")
    IMAP_PORT: int = Field(default=993, env="IMAP_PORT")
    
    # WhatsApp
    WHATSAPP_BUSINESS_PHONE: Optional[str] = Field(None, env="WHATSAPP_BUSINESS_PHONE")
    
    # Google Maps
    GOOGLE_MAPS_API_KEY: Optional[str] = Field(None, env="GOOGLE_MAPS_API_KEY")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    # Feature Flags
    ENABLE_PAYMENTS: bool = Field(default=True, env="ENABLE_PAYMENTS")
    ENABLE_CUSTOM_DOMAINS: bool = Field(default=False, env="ENABLE_CUSTOM_DOMAINS")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

# Create settings instance
settings = Settings()