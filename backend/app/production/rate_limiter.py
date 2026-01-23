"""
Production-grade rate limiting middleware using token bucket algorithm.

This middleware provides configurable rate limiting per client IP,
with support for different limits per endpoint category.

Usage (additive - register in main.py after existing middleware):
    from app.production.rate_limiter import RateLimitMiddleware, RateLimitConfig

    config = RateLimitConfig(
        default_requests_per_minute=60,
        burst_size=10
    )
    app.add_middleware(RateLimitMiddleware, config=config)
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Set
from functools import lru_cache

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from loguru import logger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting behavior."""

    # Default limits
    default_requests_per_minute: int = 60
    burst_size: int = 10

    # Per-category limits (requests per minute)
    auth_limit: int = 10  # Login/register - strict to prevent brute force
    generation_limit: int = 5  # AI generation - expensive operation
    upload_limit: int = 20  # File uploads
    api_limit: int = 100  # General API calls
    health_limit: int = 300  # Health checks - allow frequent monitoring

    # Paths exempt from rate limiting
    exempt_paths: Set[str] = field(default_factory=lambda: {
        "/health",
        "/health/detailed",
        "/docs",
        "/openapi.json",
        "/redoc",
    })

    # Headers to extract client identifier
    client_id_headers: tuple = (
        "X-Forwarded-For",
        "X-Real-IP",
        "CF-Connecting-IP",  # Cloudflare
    )

    # Response customization
    retry_after_header: bool = True
    include_limit_headers: bool = True

    # Cleanup interval for expired buckets (seconds)
    cleanup_interval: int = 300

    # Redis URL for distributed rate limiting (None = in-memory)
    redis_url: Optional[str] = None


class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Allows burst traffic while maintaining average rate limit.
    Thread-safe for concurrent access.
    """

    __slots__ = ('capacity', 'tokens', 'refill_rate', 'last_refill', '_lock')

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """
        Attempt to consume tokens from bucket.

        Returns:
            Tuple of (success, wait_time_if_failed)
        """
        async with self._lock:
            now = time.monotonic()

            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0

            # Calculate wait time until enough tokens available
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            return False, wait_time

    @property
    def available_tokens(self) -> int:
        """Get current available tokens (approximate)."""
        return int(self.tokens)


class RateLimitStore:
    """
    In-memory store for rate limit buckets with automatic cleanup.

    For production with multiple instances, use Redis-backed store.
    """

    def __init__(self, cleanup_interval: int = 300):
        self._buckets: Dict[str, TokenBucket] = {}
        self._last_access: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.monotonic()

    async def get_bucket(
        self,
        key: str,
        capacity: int,
        refill_rate: float
    ) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        async with self._lock:
            now = time.monotonic()

            # Periodic cleanup of stale buckets
            if now - self._last_cleanup > self._cleanup_interval:
                await self._cleanup_stale_buckets(now)

            if key not in self._buckets:
                self._buckets[key] = TokenBucket(capacity, refill_rate)

            self._last_access[key] = now
            return self._buckets[key]

    async def _cleanup_stale_buckets(self, now: float) -> None:
        """Remove buckets not accessed in cleanup_interval."""
        stale_keys = [
            key for key, last_access in self._last_access.items()
            if now - last_access > self._cleanup_interval
        ]
        for key in stale_keys:
            del self._buckets[key]
            del self._last_access[key]

        self._last_cleanup = now

        if stale_keys:
            logger.debug(f"Rate limiter cleaned up {len(stale_keys)} stale buckets")


@lru_cache(maxsize=128)
def _categorize_path(path: str) -> str:
    """
    Categorize request path for rate limit selection.

    Categories:
    - auth: Authentication endpoints
    - generation: AI/website generation
    - upload: File upload endpoints
    - health: Health check endpoints
    - api: Default API endpoints
    """
    path_lower = path.lower()

    if any(p in path_lower for p in ('/login', '/register', '/auth', '/logout')):
        return 'auth'

    if any(p in path_lower for p in ('/generate', '/ai/', '/stability')):
        return 'generation'

    if any(p in path_lower for p in ('/upload', '/image', '/file')):
        return 'upload'

    if '/health' in path_lower:
        return 'health'

    return 'api'


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-grade rate limiting middleware.

    Features:
    - Token bucket algorithm for burst handling
    - Per-endpoint category limits
    - Client identification via headers
    - Automatic stale bucket cleanup
    - Rate limit headers in response
    - Graceful degradation on errors

    This middleware is additive and does not modify existing code.
    """

    def __init__(self, app: ASGIApp, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.store = RateLimitStore(self.config.cleanup_interval)

        # Pre-compute category limits
        self._category_limits = {
            'auth': (self.config.auth_limit, self.config.burst_size),
            'generation': (self.config.generation_limit, max(2, self.config.burst_size // 5)),
            'upload': (self.config.upload_limit, self.config.burst_size),
            'health': (self.config.health_limit, self.config.burst_size * 3),
            'api': (self.config.api_limit, self.config.burst_size),
        }

        logger.info(
            f"Rate limiter initialized: default={self.config.default_requests_per_minute}/min, "
            f"auth={self.config.auth_limit}/min, generation={self.config.generation_limit}/min"
        )

    def _get_client_id(self, request: Request) -> str:
        """
        Extract client identifier from request.

        Priority: Proxy headers → Direct IP
        """
        for header in self.config.client_id_headers:
            value = request.headers.get(header)
            if value:
                # Handle comma-separated IPs (take first/original)
                return value.split(',')[0].strip()

        # Fallback to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _get_limits_for_path(self, path: str) -> tuple[int, int]:
        """Get (requests_per_minute, burst_size) for path."""
        category = _categorize_path(path)
        return self._category_limits.get(
            category,
            (self.config.default_requests_per_minute, self.config.burst_size)
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request with rate limiting."""
        path = request.url.path

        # Skip exempt paths
        if path in self.config.exempt_paths:
            return await call_next(request)

        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        try:
            client_id = self._get_client_id(request)
            requests_per_minute, burst_size = self._get_limits_for_path(path)

            # Create bucket key combining client and endpoint category
            category = _categorize_path(path)
            bucket_key = f"{client_id}:{category}"

            # Get or create bucket
            bucket = await self.store.get_bucket(
                key=bucket_key,
                capacity=burst_size,
                refill_rate=requests_per_minute / 60.0  # Convert to per-second
            )

            # Attempt to consume token
            allowed, retry_after = await bucket.consume()

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded: client={client_id}, "
                    f"path={path}, category={category}, retry_after={retry_after:.1f}s"
                )

                headers = {
                    "X-RateLimit-Limit": str(requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                }

                if self.config.retry_after_header:
                    headers["Retry-After"] = str(int(retry_after) + 1)

                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Please slow down.",
                        "retry_after_seconds": int(retry_after) + 1
                    },
                    headers=headers
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers to successful responses
            if self.config.include_limit_headers:
                response.headers["X-RateLimit-Limit"] = str(requests_per_minute)
                response.headers["X-RateLimit-Remaining"] = str(bucket.available_tokens)
                response.headers["X-RateLimit-Reset"] = str(
                    int(time.time() + 60)  # Reset in 1 minute
                )

            return response

        except Exception as e:
            # Graceful degradation: allow request on rate limiter failure
            logger.error(f"Rate limiter error (allowing request): {e}")
            return await call_next(request)


# Convenience function for creating configured middleware
def create_rate_limiter(
    requests_per_minute: int = 60,
    burst_size: int = 10,
    auth_limit: int = 10,
    generation_limit: int = 5,
    **kwargs
) -> RateLimitConfig:
    """
    Create rate limit configuration with sensible defaults.

    Example:
        config = create_rate_limiter(
            requests_per_minute=100,
            auth_limit=5  # Strict auth limits
        )
        app.add_middleware(RateLimitMiddleware, config=config)
    """
    return RateLimitConfig(
        default_requests_per_minute=requests_per_minute,
        burst_size=burst_size,
        auth_limit=auth_limit,
        generation_limit=generation_limit,
        **kwargs
    )
