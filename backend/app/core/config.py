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

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Supabase
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_ANON_KEY: str = Field(..., env="SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")

    # Database
    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")

    # DeepSeek AI
    DEEPSEEK_API_KEY: str = Field(..., env="DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL: str = Field(
        default="https://api.deepseek.com/v1",
        env="DEEPSEEK_API_URL"
    )
    DEEPSEEK_MODEL: str = Field(
        default="deepseek-chat",
        env="DEEPSEEK_MODEL"
    )

    # Supabase Storage
    STORAGE_BUCKET_NAME: str = Field(default="websites", env="STORAGE_BUCKET_NAME")

    # Stripe
    STRIPE_PUBLIC_KEY: str = Field(..., env="STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY: str = Field(..., env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: str = Field(..., env="STRIPE_WEBHOOK_SECRET")

    # Domain Configuration
    MAIN_DOMAIN: str = Field(default="binaapp.my", env="MAIN_DOMAIN")
    SUBDOMAIN_SUFFIX: str = Field(default=".binaapp.my", env="SUBDOMAIN_SUFFIX")

    # Security
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS: int = Field(default=24, env="JWT_EXPIRATION_HOURS")

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


# Create settings instance
settings = Settings()
