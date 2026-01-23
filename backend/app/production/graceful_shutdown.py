"""
Graceful shutdown handler for clean connection cleanup.

Ensures in-flight requests complete and resources are properly released
during application shutdown, preventing data loss and connection leaks.

Usage:
    from app.production.graceful_shutdown import GracefulShutdown

    shutdown_handler = GracefulShutdown()

    @app.on_event("startup")
    async def startup():
        await shutdown_handler.startup()

    @app.on_event("shutdown")
    async def shutdown():
        await shutdown_handler.shutdown()

    # Register resources
    shutdown_handler.register_cleanup(db_pool.close)
    shutdown_handler.register_cleanup(redis_client.close)
"""

import asyncio
import signal
import sys
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Union

from loguru import logger


@dataclass
class ShutdownConfig:
    """Configuration for graceful shutdown behavior."""

    # Maximum time to wait for in-flight requests (seconds)
    request_timeout: float = 30.0

    # Maximum time to wait for cleanup tasks (seconds)
    cleanup_timeout: float = 10.0

    # Signals to handle for shutdown
    signals: tuple = (signal.SIGTERM, signal.SIGINT)

    # Whether to force exit after timeouts
    force_exit: bool = True

    # Delay before starting cleanup (allows health checks to fail)
    pre_shutdown_delay: float = 1.0


class GracefulShutdown:
    """
    Manages graceful shutdown of the application.

    Features:
    - Tracks in-flight requests
    - Waits for requests to complete before shutdown
    - Executes cleanup callbacks in order
    - Handles shutdown signals
    - Timeout protection for hung operations

    This utility is additive and does not modify existing code.
    """

    def __init__(self, config: Optional[ShutdownConfig] = None):
        self.config = config or ShutdownConfig()

        self._is_shutting_down = False
        self._active_requests: Set[str] = set()
        self._cleanup_callbacks: List[tuple[int, Callable[[], Awaitable[None]]]] = []
        self._request_counter = 0
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

        # Resources registered for cleanup
        self._resources: Dict[str, Any] = {}

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._is_shutting_down

    @property
    def active_request_count(self) -> int:
        """Get number of active requests."""
        return len(self._active_requests)

    async def startup(self) -> None:
        """
        Initialize shutdown handler.

        Call this during application startup.
        """
        # Register signal handlers
        loop = asyncio.get_event_loop()

        for sig in self.config.signals:
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_signal(s))
                )
                logger.info(f"Registered signal handler for {sig.name}")
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                logger.warning(f"Signal handler not supported for {sig.name}")

        logger.info("Graceful shutdown handler initialized")

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signal."""
        logger.warning(f"Received {sig.name}, initiating graceful shutdown")
        await self.shutdown()

    async def shutdown(self) -> None:
        """
        Initiate graceful shutdown.

        1. Mark as shutting down (health checks will fail)
        2. Wait for in-flight requests to complete
        3. Execute cleanup callbacks
        4. Exit if configured
        """
        if self._is_shutting_down:
            logger.warning("Shutdown already in progress")
            return

        async with self._lock:
            self._is_shutting_down = True

        logger.info("Starting graceful shutdown")

        # Pre-shutdown delay (allows load balancer health checks to fail)
        if self.config.pre_shutdown_delay > 0:
            logger.info(
                f"Pre-shutdown delay: {self.config.pre_shutdown_delay}s"
            )
            await asyncio.sleep(self.config.pre_shutdown_delay)

        # Wait for in-flight requests
        await self._wait_for_requests()

        # Execute cleanup callbacks
        await self._run_cleanup()

        # Signal shutdown complete
        self._shutdown_event.set()

        logger.info("Graceful shutdown complete")

        if self.config.force_exit:
            sys.exit(0)

    async def _wait_for_requests(self) -> None:
        """Wait for in-flight requests to complete."""
        if not self._active_requests:
            logger.info("No active requests to wait for")
            return

        logger.info(
            f"Waiting for {len(self._active_requests)} active requests "
            f"(timeout: {self.config.request_timeout}s)"
        )

        start_time = asyncio.get_event_loop().time()

        while self._active_requests:
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed >= self.config.request_timeout:
                logger.warning(
                    f"Request timeout exceeded, {len(self._active_requests)} "
                    f"requests still active"
                )
                break

            await asyncio.sleep(0.1)

        if not self._active_requests:
            logger.info("All requests completed")

    async def _run_cleanup(self) -> None:
        """Execute cleanup callbacks in priority order."""
        if not self._cleanup_callbacks:
            logger.info("No cleanup callbacks registered")
            return

        # Sort by priority (lower = higher priority)
        sorted_callbacks = sorted(self._cleanup_callbacks, key=lambda x: x[0])

        logger.info(f"Running {len(sorted_callbacks)} cleanup callbacks")

        for priority, callback in sorted_callbacks:
            try:
                await asyncio.wait_for(
                    callback(),
                    timeout=self.config.cleanup_timeout
                )
                logger.debug(f"Cleanup callback completed (priority={priority})")
            except asyncio.TimeoutError:
                logger.error(f"Cleanup callback timed out (priority={priority})")
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")

    def register_cleanup(
        self,
        callback: Union[Callable[[], None], Callable[[], Awaitable[None]]],
        priority: int = 100,
    ) -> None:
        """
        Register a cleanup callback.

        Args:
            callback: Function to call during shutdown (sync or async)
            priority: Execution priority (lower = earlier, default=100)
        """
        async def async_wrapper():
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()

        self._cleanup_callbacks.append((priority, async_wrapper))
        logger.debug(f"Registered cleanup callback with priority={priority}")

    def register_resource(self, name: str, resource: Any) -> None:
        """
        Register a resource for tracking and potential cleanup.

        Args:
            name: Unique identifier for the resource
            resource: The resource object
        """
        self._resources[name] = resource
        logger.debug(f"Registered resource: {name}")

    def get_resource(self, name: str) -> Optional[Any]:
        """Get a registered resource by name."""
        return self._resources.get(name)

    async def track_request(self, request_id: str) -> None:
        """
        Start tracking a request.

        Call this at the beginning of request processing.
        """
        async with self._lock:
            self._active_requests.add(request_id)

    async def untrack_request(self, request_id: str) -> None:
        """
        Stop tracking a request.

        Call this when request processing completes.
        """
        async with self._lock:
            self._active_requests.discard(request_id)

    def request_tracker(self):
        """
        Context manager for tracking requests.

        Usage:
            async with shutdown_handler.request_tracker():
                # Process request
                ...
        """
        return RequestTracker(self)

    async def wait_for_shutdown(self) -> None:
        """Wait until shutdown is complete."""
        await self._shutdown_event.wait()


class RequestTracker:
    """Context manager for tracking individual requests."""

    def __init__(self, shutdown_handler: GracefulShutdown):
        self._handler = shutdown_handler
        self._request_id: Optional[str] = None

    async def __aenter__(self):
        self._handler._request_counter += 1
        self._request_id = f"req-{self._handler._request_counter}"
        await self._handler.track_request(self._request_id)
        return self._request_id

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._request_id:
            await self._handler.untrack_request(self._request_id)
        return False


# Middleware for automatic request tracking
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class GracefulShutdownMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks requests and rejects new ones during shutdown.

    Usage:
        shutdown_handler = GracefulShutdown()
        app.add_middleware(GracefulShutdownMiddleware, handler=shutdown_handler)
    """

    def __init__(self, app: ASGIApp, handler: GracefulShutdown):
        super().__init__(app)
        self.handler = handler

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Reject new requests during shutdown (except health checks)
        if self.handler.is_shutting_down:
            if not request.url.path.startswith("/health"):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "Service is shutting down",
                        "retry_after": 30
                    },
                    headers={"Retry-After": "30"}
                )

        # Track this request
        async with self.handler.request_tracker() as request_id:
            request.state.tracking_id = request_id
            return await call_next(request)


# Global instance for convenience
_global_shutdown_handler: Optional[GracefulShutdown] = None


def get_shutdown_handler() -> GracefulShutdown:
    """Get the global shutdown handler instance."""
    global _global_shutdown_handler
    if _global_shutdown_handler is None:
        _global_shutdown_handler = GracefulShutdown()
    return _global_shutdown_handler
