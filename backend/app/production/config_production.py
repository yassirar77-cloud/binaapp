"""
Production configuration template and environment validation.

Provides secure defaults and validates configuration for production deployment.
This module wraps existing configuration without modifying it.

Usage:
    from app.production.config_production import (
        get_production_config,
        validate_production_environment,
        ProductionConfig
    )

    # Validate on startup
    validate_production_environment()

    # Get production-specific settings
    config = get_production_config()
"""

import os
import secrets
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from loguru import logger


@dataclass
class ProductionConfig:
    """
    Production-specific configuration with secure defaults.

    This configuration layer adds production hardening without
    modifying the existing Settings class.
    """

    # Environment
    environment: str = "production"
    debug: bool = False

    # Security
    min_password_length: int = 8
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    # Rate limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10
    auth_rate_limit_per_minute: int = 10
    generation_rate_limit_per_minute: int = 5

    # Timeouts (seconds)
    request_timeout: float = 30.0
    database_timeout: float = 10.0
    external_api_timeout: float = 60.0
    ai_generation_timeout: float = 120.0

    # Connection pooling
    max_http_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry_seconds: float = 30.0

    # Logging
    log_level: str = "INFO"
    log_format_json: bool = True
    log_retention_days: int = 30
    mask_sensitive_data: bool = True

    # Circuit breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 30.0

    # Cache
    cache_default_ttl_seconds: int = 3600
    cache_max_memory_entries: int = 10000

    # Graceful shutdown
    shutdown_timeout_seconds: float = 30.0
    shutdown_cleanup_timeout_seconds: float = 10.0

    # CORS (restrictive for production)
    cors_allowed_origins: List[str] = field(default_factory=list)
    cors_allow_credentials: bool = False

    # File upload limits
    max_upload_size_mb: int = 10
    allowed_upload_types: Set[str] = field(default_factory=lambda: {
        "image/jpeg", "image/png", "image/gif", "image/webp"
    })

    # Database
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20

    # Feature flags
    enable_metrics: bool = True
    enable_rate_limiting: bool = True
    enable_security_headers: bool = True
    enable_request_tracking: bool = True


# Environment variables that MUST be set in production
REQUIRED_ENV_VARS = [
    "JWT_SECRET_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
]

# Environment variables that should NOT use default values
SENSITIVE_ENV_VARS = [
    "JWT_SECRET_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "DEEPSEEK_API_KEY",
    "STRIPE_SECRET_KEY",
    "TOYYIBPAY_SECRET_KEY",
]

# Unsafe default values to detect
UNSAFE_DEFAULTS = [
    "dev-secret-key-change-in-production",
    "change-me",
    "secret",
    "password",
    "test",
    "development",
]


class ConfigurationError(Exception):
    """Raised when production configuration is invalid."""
    pass


def validate_production_environment() -> List[str]:
    """
    Validate that all required environment variables are properly configured.

    Returns:
        List of warning messages (empty if all OK)

    Raises:
        ConfigurationError: If critical configuration is missing
    """
    warnings = []
    errors = []

    # Check required variables
    for var in REQUIRED_ENV_VARS:
        value = os.environ.get(var)
        if not value:
            errors.append(f"Missing required environment variable: {var}")

    # Check for unsafe default values
    for var in SENSITIVE_ENV_VARS:
        value = os.environ.get(var, "")
        if value:
            value_lower = value.lower()
            for unsafe in UNSAFE_DEFAULTS:
                if unsafe in value_lower:
                    warnings.append(
                        f"Environment variable {var} appears to use an unsafe "
                        f"default value. Please set a secure production value."
                    )
                    break

    # Check JWT secret strength
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
    if jwt_secret and len(jwt_secret) < 32:
        warnings.append(
            "JWT_SECRET_KEY should be at least 32 characters for production"
        )

    # Check environment setting
    env = os.environ.get("ENVIRONMENT", "development")
    if env == "production":
        debug = os.environ.get("DEBUG", "").lower()
        if debug in ("true", "1", "yes"):
            warnings.append(
                "DEBUG is enabled in production environment. "
                "This may expose sensitive information."
            )

    # Log results
    for warning in warnings:
        logger.warning(f"Configuration warning: {warning}")

    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ConfigurationError(
            f"Production configuration invalid: {'; '.join(errors)}"
        )

    if not warnings:
        logger.info("Production configuration validated successfully")

    return warnings


def generate_secure_secret(length: int = 64) -> str:
    """
    Generate a cryptographically secure secret key.

    Use this to generate values for JWT_SECRET_KEY and similar.
    """
    return secrets.token_urlsafe(length)


def get_production_config() -> ProductionConfig:
    """
    Get production configuration with environment overrides.

    Values are read from environment variables with sensible defaults.
    """
    config = ProductionConfig()

    # Override from environment
    env_overrides = {
        "ENVIRONMENT": ("environment", str),
        "DEBUG": ("debug", lambda x: x.lower() in ("true", "1", "yes")),
        "LOG_LEVEL": ("log_level", str),
        "LOG_FORMAT_JSON": ("log_format_json", lambda x: x.lower() in ("true", "1", "yes")),
        "RATE_LIMIT_RPM": ("rate_limit_requests_per_minute", int),
        "RATE_LIMIT_BURST": ("rate_limit_burst_size", int),
        "REQUEST_TIMEOUT": ("request_timeout", float),
        "DATABASE_TIMEOUT": ("database_timeout", float),
        "MAX_UPLOAD_SIZE_MB": ("max_upload_size_mb", int),
        "CACHE_TTL": ("cache_default_ttl_seconds", int),
        "ENABLE_METRICS": ("enable_metrics", lambda x: x.lower() in ("true", "1", "yes")),
        "ENABLE_RATE_LIMITING": ("enable_rate_limiting", lambda x: x.lower() in ("true", "1", "yes")),
    }

    for env_var, (attr, converter) in env_overrides.items():
        value = os.environ.get(env_var)
        if value is not None:
            try:
                setattr(config, attr, converter(value))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid value for {env_var}: {e}")

    return config


# Pre-built secure configurations

def get_strict_security_config() -> Dict[str, Any]:
    """
    Get strict security settings for high-security deployments.

    Use when handling sensitive data or for compliance requirements.
    """
    return {
        "jwt_expiration_hours": 8,
        "session_timeout_minutes": 15,
        "max_login_attempts": 3,
        "lockout_duration_minutes": 30,
        "rate_limit_requests_per_minute": 30,
        "auth_rate_limit_per_minute": 5,
        "cors_allow_credentials": False,
        "log_format_json": True,
        "mask_sensitive_data": True,
    }


def get_development_overrides() -> Dict[str, Any]:
    """
    Get development-friendly configuration overrides.

    Only use in development environment!
    """
    return {
        "debug": True,
        "log_level": "DEBUG",
        "log_format_json": False,
        "rate_limit_requests_per_minute": 1000,
        "auth_rate_limit_per_minute": 100,
        "enable_rate_limiting": False,
    }


class ProductionStartupCheck:
    """
    Performs comprehensive startup checks for production readiness.

    Usage:
        checker = ProductionStartupCheck()
        checker.run_all_checks()
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def check_environment(self):
        """Check environment configuration."""
        try:
            warnings = validate_production_environment()
            self.warnings.extend(warnings)
        except ConfigurationError as e:
            self.errors.append(str(e))

    def check_secrets(self):
        """Check that secrets are properly configured."""
        jwt_secret = os.environ.get("JWT_SECRET_KEY", "")

        # Check entropy (simple heuristic)
        if jwt_secret:
            unique_chars = len(set(jwt_secret))
            if unique_chars < 10:
                self.warnings.append(
                    "JWT_SECRET_KEY has low entropy. Consider using a more random value."
                )

    def check_cors(self):
        """Check CORS configuration."""
        cors_origins = os.environ.get("CORS_ORIGINS", "*")
        if cors_origins == "*":
            self.warnings.append(
                "CORS allows all origins (*). Consider restricting to specific domains."
            )

    def check_debug_mode(self):
        """Check debug mode is disabled."""
        debug = os.environ.get("DEBUG", "").lower()
        env = os.environ.get("ENVIRONMENT", "development")

        if env == "production" and debug in ("true", "1", "yes"):
            self.errors.append(
                "DEBUG mode is enabled in production. This is a security risk."
            )

    def run_all_checks(self) -> bool:
        """
        Run all startup checks.

        Returns:
            True if no errors (warnings are OK), False if errors found

        Raises:
            ConfigurationError: If critical errors found
        """
        self.check_environment()
        self.check_secrets()
        self.check_cors()
        self.check_debug_mode()

        # Log results
        for warning in self.warnings:
            logger.warning(f"Startup check warning: {warning}")

        if self.errors:
            for error in self.errors:
                logger.error(f"Startup check error: {error}")
            raise ConfigurationError(
                f"Production startup checks failed: {'; '.join(self.errors)}"
            )

        logger.info(
            f"Production startup checks passed "
            f"({len(self.warnings)} warnings)"
        )
        return True


def run_production_startup_checks():
    """
    Convenience function to run all production startup checks.

    Call this during application startup in production.
    """
    checker = ProductionStartupCheck()
    return checker.run_all_checks()
