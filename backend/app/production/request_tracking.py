"""
Request ID tracking middleware for distributed tracing.

Provides correlation IDs for tracking requests across services,
enabling efficient debugging and log aggregation.

Usage (additive - register in main.py):
    from app.production.request_tracking import RequestTrackingMiddleware

    app.add_middleware(RequestTrackingMiddleware)

Access request ID in handlers:
    from app.production.request_tracking import get_request_id
    request_id = get_request_id()
"""

import contextvars
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from loguru import logger


# Context variable for request ID propagation
_request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'request_id', default=None
)


def get_request_id() -> Optional[str]:
    """
    Get the current request ID from context.

    Returns None if called outside of a request context.
    Thread-safe via contextvars.
    """
    return _request_id_ctx.get()


def generate_request_id() -> str:
    """Generate a unique request ID using UUID4."""
    return str(uuid.uuid4())


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request ID tracking and propagation.

    Features:
    - Generates unique request IDs for each request
    - Accepts incoming X-Request-ID header (for distributed tracing)
    - Adds request ID to response headers
    - Sets request ID in context for logging
    - Tracks request timing for performance monitoring

    This middleware is additive and does not modify existing code.
    """

    # Standard headers for request ID (checked in order)
    REQUEST_ID_HEADERS = (
        "X-Request-ID",
        "X-Correlation-ID",
        "X-Trace-ID",
    )

    RESPONSE_HEADER = "X-Request-ID"

    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Request-ID",
        generate_if_missing: bool = True,
        log_requests: bool = True,
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generate_if_missing = generate_if_missing
        self.log_requests = log_requests

        logger.info("Request tracking middleware initialized")

    def _extract_request_id(self, request: Request) -> Optional[str]:
        """Extract request ID from incoming headers."""
        for header in self.REQUEST_ID_HEADERS:
            request_id = request.headers.get(header)
            if request_id:
                # Validate format (basic sanitization)
                if len(request_id) <= 128 and request_id.replace('-', '').isalnum():
                    return request_id
        return None

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request with ID tracking."""
        import time

        # Extract or generate request ID
        request_id = self._extract_request_id(request)

        if not request_id and self.generate_if_missing:
            request_id = generate_request_id()

        # Set in context for logging and access in handlers
        token = _request_id_ctx.set(request_id)

        # Store in request state for access via request object
        request.state.request_id = request_id

        start_time = time.perf_counter()

        try:
            if self.log_requests:
                logger.bind(request_id=request_id).info(
                    f"Request started: {request.method} {request.url.path}"
                )

            response = await call_next(request)

            # Add request ID to response headers
            if request_id:
                response.headers[self.RESPONSE_HEADER] = request_id

            # Log completion with timing
            if self.log_requests:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.bind(request_id=request_id).info(
                    f"Request completed: {request.method} {request.url.path} "
                    f"status={response.status_code} duration={duration_ms:.2f}ms"
                )

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.bind(request_id=request_id).error(
                f"Request failed: {request.method} {request.url.path} "
                f"duration={duration_ms:.2f}ms error={str(e)}"
            )
            raise

        finally:
            # Reset context
            _request_id_ctx.reset(token)


class RequestContextLogger:
    """
    Logger wrapper that automatically includes request context.

    Usage:
        from app.production.request_tracking import ctx_logger

        ctx_logger.info("Processing order")
        # Output: [request_id=abc-123] Processing order
    """

    def _format_message(self, message: str) -> str:
        """Add request context to message."""
        request_id = get_request_id()
        if request_id:
            return f"[request_id={request_id}] {message}"
        return message

    def debug(self, message: str, **kwargs):
        logger.debug(self._format_message(message), **kwargs)

    def info(self, message: str, **kwargs):
        logger.info(self._format_message(message), **kwargs)

    def warning(self, message: str, **kwargs):
        logger.warning(self._format_message(message), **kwargs)

    def error(self, message: str, **kwargs):
        logger.error(self._format_message(message), **kwargs)

    def exception(self, message: str, **kwargs):
        logger.exception(self._format_message(message), **kwargs)


# Global context-aware logger instance
ctx_logger = RequestContextLogger()
