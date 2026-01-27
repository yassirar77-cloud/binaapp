"""
Production-grade hardening utilities for BinaApp.

This module provides additive production enhancements without modifying
existing code. All components are designed to be optionally integrated.

Components:
- rate_limiter: Token bucket rate limiting middleware
- request_tracking: Distributed request ID tracking
- security_headers: Production security headers middleware
- circuit_breaker: Resilience pattern for external services
- graceful_shutdown: Clean shutdown handling
- logging_production: Structured JSON logging for production
- connection_pool: HTTP client connection pooling
- retry_utils: Exponential backoff retry utilities
- sanitization: Input validation and sanitization
- metrics: Prometheus-compatible metrics collection
- cache: Redis caching layer wrapper
- response_envelope: Consistent API response formatting
- health_extended: Extended health checks with dependencies
"""

__version__ = "1.0.0"
