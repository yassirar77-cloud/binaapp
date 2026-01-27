"""
Production security headers middleware.

Adds essential security headers to all responses for protection against
common web vulnerabilities (XSS, clickjacking, MIME sniffing, etc.).

Usage (additive - register in main.py):
    from app.production.security_headers import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from loguru import logger


@dataclass
class SecurityHeadersConfig:
    """Configuration for security headers."""

    # Strict-Transport-Security (HSTS)
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False  # Enable only if domain is HSTS preload list ready

    # Content-Security-Policy
    csp_enabled: bool = True
    csp_directives: Dict[str, str] = field(default_factory=lambda: {
        "default-src": "'self'",
        "script-src": "'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
        "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com",
        "font-src": "'self' https://fonts.gstatic.com data:",
        "img-src": "'self' data: blob: https: http:",
        "connect-src": "'self' https: wss:",
        "frame-ancestors": "'self'",
        "form-action": "'self'",
        "base-uri": "'self'",
    })
    csp_report_only: bool = False  # Set True to test without enforcing
    csp_report_uri: Optional[str] = None

    # X-Content-Type-Options
    content_type_nosniff: bool = True

    # X-Frame-Options
    frame_options_enabled: bool = True
    frame_options_value: str = "SAMEORIGIN"  # DENY, SAMEORIGIN, or ALLOW-FROM uri

    # X-XSS-Protection (legacy, but still useful for older browsers)
    xss_protection_enabled: bool = True
    xss_protection_value: str = "1; mode=block"

    # Referrer-Policy
    referrer_policy_enabled: bool = True
    referrer_policy_value: str = "strict-origin-when-cross-origin"

    # Permissions-Policy (formerly Feature-Policy)
    permissions_policy_enabled: bool = True
    permissions_policy: Dict[str, str] = field(default_factory=lambda: {
        "geolocation": "(self)",
        "camera": "()",
        "microphone": "()",
        "payment": "(self)",
        "usb": "()",
    })

    # Cache-Control for sensitive responses
    cache_control_enabled: bool = True
    cache_control_value: str = "no-store, no-cache, must-revalidate, private"

    # Paths to exclude from certain headers (e.g., static assets)
    static_paths: Set[str] = field(default_factory=lambda: {
        "/static/",
        "/assets/",
        "/_next/",
        "/favicon.ico",
    })

    # API paths that should have stricter cache control
    api_paths: Set[str] = field(default_factory=lambda: {
        "/api/",
    })


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Production-grade security headers middleware.

    Adds comprehensive security headers to protect against:
    - XSS attacks
    - Clickjacking
    - MIME type sniffing
    - Protocol downgrade attacks
    - Information disclosure

    This middleware is additive and does not modify existing code.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Optional[SecurityHeadersConfig] = None,
    ):
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()

        # Pre-build static headers for performance
        self._static_headers = self._build_static_headers()

        logger.info("Security headers middleware initialized")

    def _build_static_headers(self) -> Dict[str, str]:
        """Pre-compute headers that don't change per request."""
        headers = {}

        # HSTS
        if self.config.hsts_enabled:
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            headers["Strict-Transport-Security"] = hsts_value

        # CSP
        if self.config.csp_enabled:
            csp_value = "; ".join(
                f"{directive} {value}"
                for directive, value in self.config.csp_directives.items()
            )
            if self.config.csp_report_uri:
                csp_value += f"; report-uri {self.config.csp_report_uri}"

            header_name = (
                "Content-Security-Policy-Report-Only"
                if self.config.csp_report_only
                else "Content-Security-Policy"
            )
            headers[header_name] = csp_value

        # X-Content-Type-Options
        if self.config.content_type_nosniff:
            headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        if self.config.frame_options_enabled:
            headers["X-Frame-Options"] = self.config.frame_options_value

        # X-XSS-Protection
        if self.config.xss_protection_enabled:
            headers["X-XSS-Protection"] = self.config.xss_protection_value

        # Referrer-Policy
        if self.config.referrer_policy_enabled:
            headers["Referrer-Policy"] = self.config.referrer_policy_value

        # Permissions-Policy
        if self.config.permissions_policy_enabled:
            policy_value = ", ".join(
                f"{feature}={value}"
                for feature, value in self.config.permissions_policy.items()
            )
            headers["Permissions-Policy"] = policy_value

        return headers

    def _is_static_path(self, path: str) -> bool:
        """Check if path is for static assets."""
        return any(path.startswith(p) for p in self.config.static_paths)

    def _is_api_path(self, path: str) -> bool:
        """Check if path is an API endpoint."""
        return any(path.startswith(p) for p in self.config.api_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and add security headers to response."""
        response = await call_next(request)
        path = request.url.path

        # Add all static headers
        for header, value in self._static_headers.items():
            # Don't override existing headers
            if header not in response.headers:
                response.headers[header] = value

        # Add Cache-Control for API responses
        if self.config.cache_control_enabled and self._is_api_path(path):
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = self.config.cache_control_value

        # For static assets, allow caching
        if self._is_static_path(path):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        return response


def create_relaxed_csp_config() -> SecurityHeadersConfig:
    """
    Create a more relaxed CSP configuration for development.

    Use this when testing to avoid CSP blocking legitimate resources.
    """
    config = SecurityHeadersConfig()
    config.csp_report_only = True  # Only report, don't enforce
    config.hsts_enabled = False  # Disable HSTS in development
    return config


def create_strict_csp_config(
    allowed_scripts: list[str] = None,
    allowed_styles: list[str] = None,
    report_uri: str = None
) -> SecurityHeadersConfig:
    """
    Create a strict CSP configuration for production.

    Args:
        allowed_scripts: Additional script sources to allow
        allowed_styles: Additional style sources to allow
        report_uri: CSP violation report endpoint
    """
    config = SecurityHeadersConfig()

    # Build stricter directives
    script_src = "'self'"
    if allowed_scripts:
        script_src += " " + " ".join(allowed_scripts)

    style_src = "'self'"
    if allowed_styles:
        style_src += " " + " ".join(allowed_styles)

    config.csp_directives = {
        "default-src": "'self'",
        "script-src": script_src,
        "style-src": style_src,
        "font-src": "'self' data:",
        "img-src": "'self' data: https:",
        "connect-src": "'self' https: wss:",
        "frame-ancestors": "'none'",
        "form-action": "'self'",
        "base-uri": "'self'",
        "upgrade-insecure-requests": "",
    }

    if report_uri:
        config.csp_report_uri = report_uri

    config.hsts_preload = True
    config.frame_options_value = "DENY"

    return config
