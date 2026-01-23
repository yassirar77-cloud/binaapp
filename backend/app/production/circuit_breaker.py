"""
Circuit breaker pattern implementation for external service resilience.

Prevents cascade failures by failing fast when external services are down,
allowing them time to recover before resuming normal operations.

Usage:
    from app.production.circuit_breaker import CircuitBreaker, circuit_breaker

    # As a decorator
    @circuit_breaker(name="supabase", failure_threshold=5, recovery_timeout=30)
    async def call_supabase():
        ...

    # As a context manager
    cb = CircuitBreaker(name="deepseek")
    async with cb:
        await call_deepseek_api()
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

from loguru import logger


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing fast, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    # Number of failures before opening circuit
    failure_threshold: int = 5

    # Consecutive successes needed to close circuit from half-open
    success_threshold: int = 2

    # Seconds to wait before attempting recovery (half-open)
    recovery_timeout: float = 30.0

    # Seconds after which failure count resets (sliding window)
    failure_window: float = 60.0

    # Exceptions that count as failures (None = all exceptions)
    failure_exceptions: Optional[tuple] = None

    # Exceptions that should NOT count as failures
    excluded_exceptions: tuple = field(default_factory=lambda: (
        KeyboardInterrupt,
        SystemExit,
    ))

    # Maximum time to wait for a call (0 = no timeout)
    call_timeout: float = 30.0

    # Callback when circuit opens
    on_open: Optional[Callable[[], None]] = None

    # Callback when circuit closes
    on_close: Optional[Callable[[], None]] = None

    # Callback when circuit half-opens
    on_half_open: Optional[Callable[[], None]] = None


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, name: str, remaining_time: float):
        self.name = name
        self.remaining_time = remaining_time
        super().__init__(
            f"Circuit '{name}' is open. "
            f"Retry after {remaining_time:.1f} seconds."
        )


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.

    States:
    - CLOSED: Normal operation. Failures are counted.
    - OPEN: Circuit tripped. All requests fail immediately.
    - HALF_OPEN: Testing recovery. Limited requests allowed.

    Transitions:
    - CLOSED → OPEN: When failure_threshold exceeded
    - OPEN → HALF_OPEN: After recovery_timeout expires
    - HALF_OPEN → CLOSED: After success_threshold consecutive successes
    - HALF_OPEN → OPEN: On any failure
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig(**kwargs)

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._lock = asyncio.Lock()

        # Metrics for monitoring
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejections = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics for monitoring."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "total_rejections": self._total_rejections,
        }

    async def _check_state_transition(self) -> None:
        """Check and perform state transitions based on current conditions."""
        now = time.monotonic()

        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._opened_at and (now - self._opened_at) >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(f"Circuit '{self.name}' entering half-open state")
                if self.config.on_half_open:
                    self.config.on_half_open()

        elif self._state == CircuitState.CLOSED:
            # Reset failure count if outside failure window
            if self._last_failure_time and (now - self._last_failure_time) > self.config.failure_window:
                self._failure_count = 0

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._total_successes += 1

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._opened_at = None
                    logger.info(f"Circuit '{self.name}' closed after recovery")
                    if self.config.on_close:
                        self.config.on_close()

            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            now = time.monotonic()
            self._total_failures += 1
            self._last_failure_time = now

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                self._state = CircuitState.OPEN
                self._opened_at = now
                logger.warning(
                    f"Circuit '{self.name}' reopened after failure in half-open: {exception}"
                )

            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._opened_at = now
                    logger.error(
                        f"Circuit '{self.name}' opened after {self._failure_count} failures"
                    )
                    if self.config.on_open:
                        self.config.on_open()

    def _should_count_failure(self, exception: Exception) -> bool:
        """Determine if exception should count as a circuit failure."""
        # Never count excluded exceptions
        if isinstance(exception, self.config.excluded_exceptions):
            return False

        # If failure_exceptions specified, only count those
        if self.config.failure_exceptions:
            return isinstance(exception, self.config.failure_exceptions)

        # By default, count all exceptions
        return True

    async def __aenter__(self):
        """Async context manager entry."""
        await self._check_state_transition()

        async with self._lock:
            self._total_calls += 1

            if self._state == CircuitState.OPEN:
                self._total_rejections += 1
                remaining = self.config.recovery_timeout
                if self._opened_at:
                    remaining = max(
                        0,
                        self.config.recovery_timeout - (time.monotonic() - self._opened_at)
                    )
                raise CircuitOpenError(self.name, remaining)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_val is None:
            await self._record_success()
        elif self._should_count_failure(exc_val):
            await self._record_failure(exc_val)
        # Don't suppress exceptions
        return False

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async or sync function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitOpenError: If circuit is open
            TimeoutError: If call exceeds timeout
        """
        async with self:
            if asyncio.iscoroutinefunction(func):
                if self.config.call_timeout > 0:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.config.call_timeout
                    )
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = asyncio.Lock()


async def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    **kwargs
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.

    Circuit breakers are cached globally by name.
    """
    async with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                config=config,
                **kwargs
            )
        return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    success_threshold: int = 2,
    call_timeout: float = 30.0,
    failure_exceptions: Optional[tuple] = None,
    fallback: Optional[Callable] = None,
) -> Callable:
    """
    Decorator to protect a function with circuit breaker.

    Args:
        name: Unique name for this circuit breaker
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before trying recovery
        success_threshold: Successes to close from half-open
        call_timeout: Maximum call duration
        failure_exceptions: Only these exception types count as failures
        fallback: Function to call when circuit is open

    Example:
        @circuit_breaker(name="external_api", failure_threshold=3)
        async def call_external_api():
            return await httpx.get("https://api.example.com")
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        success_threshold=success_threshold,
        call_timeout=call_timeout,
        failure_exceptions=failure_exceptions,
    )

    def decorator(func: Callable) -> Callable:
        cb = CircuitBreaker(name=name, config=config)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await cb.call(func, *args, **kwargs)
            except CircuitOpenError:
                if fallback:
                    return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def get_all_circuit_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics for all registered circuit breakers."""
    return {
        name: cb.get_metrics()
        for name, cb in _circuit_breakers.items()
    }
