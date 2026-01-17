"""
Application Configuration
Loads environment variables and provides settings
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "BinaApp"
    ENVIRONMENT: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=True, env="APP_DEBUG")
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
        default="deepseek-chat",
        env="DEEPSEEK_MODEL"
    )

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
    
    # Supabase Storage
    STORAGE_BUCKET_NAME: str = Field(default="websites", env="STORAGE_BUCKET_NAME")
    
    # Stripe
    STRIPE_PUBLIC_KEY: str = Field(default="", env="STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY: str = Field(default="", env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(default="", env="STRIPE_WEBHOOK_SECRET")
    
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

    # API Keys for external integrations (comma-separated)
    # Example: BINAAPP_API_KEYS="bina_abc123...,bina_xyz789..."
    BINAAPP_API_KEYS: Optional[str] = Field(None, env="BINAAPP_API_KEYS")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Email
    SMTP_HOST: Optional[str] = Field(None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    
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