"""
Retry utilities with exponential backoff and jitter.

Provides robust retry mechanisms for handling transient failures
in external service calls.

Usage:
    from app.production.retry_utils import retry, RetryConfig

    @retry(max_attempts=3, exceptions=(TimeoutError, ConnectionError))
    async def call_external_api():
        ...

    # Or with context manager
    async with Retry(max_attempts=5) as r:
        result = await r.execute(some_async_function, arg1, arg2)
"""

import asyncio
import functools
import random
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Tuple, Type, TypeVar, Union

from loguru import logger


T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    # Number of attempts (including initial)
    max_attempts: int = 3

    # Base delay between retries (seconds)
    base_delay: float = 1.0

    # Maximum delay cap (seconds)
    max_delay: float = 60.0

    # Exponential backoff multiplier
    exponential_base: float = 2.0

    # Add random jitter to prevent thundering herd
    jitter: bool = True
    jitter_factor: float = 0.1  # ±10% randomization

    # Exceptions to retry on (None = retry on all exceptions)
    retry_exceptions: Optional[Tuple[Type[Exception], ...]] = None

    # Exceptions to NOT retry on
    exclude_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (KeyboardInterrupt, SystemExit, GeneratorExit)
    )

    # Callback called before each retry
    on_retry: Optional[Callable[[Exception, int], None]] = None

    # Callback called on final failure
    on_failure: Optional[Callable[[Exception, int], None]] = None

    # Whether to log retry attempts
    log_retries: bool = True


def calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool,
    jitter_factor: float
) -> float:
    """
    Calculate delay for next retry attempt.

    Uses exponential backoff with optional jitter.
    """
    # Exponential backoff: base_delay * exponential_base^attempt
    delay = base_delay * (exponential_base ** attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter if enabled
    if jitter:
        jitter_range = delay * jitter_factor
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay)  # Ensure non-negative

    return delay


def should_retry(
    exception: Exception,
    retry_exceptions: Optional[Tuple[Type[Exception], ...]],
    exclude_exceptions: Tuple[Type[Exception], ...]
) -> bool:
    """Determine if exception should trigger a retry."""
    # Never retry excluded exceptions
    if isinstance(exception, exclude_exceptions):
        return False

    # If specific exceptions listed, only retry those
    if retry_exceptions is not None:
        return isinstance(exception, retry_exceptions)

    # Default: retry all non-excluded exceptions
    return True


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(
            f"Retry exhausted after {attempts} attempts. "
            f"Last error: {last_exception}"
        )


async def execute_with_retry(
    func: Callable[..., Awaitable[T]],
    config: RetryConfig,
    *args,
    **kwargs
) -> T:
    """
    Execute an async function with retry logic.

    Args:
        func: Async function to execute
        config: Retry configuration
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of successful function call

    Raises:
        RetryExhaustedError: If all retries fail
        Exception: Non-retryable exceptions are re-raised
    """
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # Check if we should retry
            if not should_retry(e, config.retry_exceptions, config.exclude_exceptions):
                raise

            # Check if we have attempts left
            if attempt + 1 >= config.max_attempts:
                if config.log_retries:
                    logger.error(
                        f"Retry exhausted for {func.__name__} after "
                        f"{attempt + 1} attempts: {e}"
                    )
                if config.on_failure:
                    config.on_failure(e, attempt + 1)
                raise RetryExhaustedError(e, attempt + 1) from e

            # Calculate delay
            delay = calculate_delay(
                attempt,
                config.base_delay,
                config.max_delay,
                config.exponential_base,
                config.jitter,
                config.jitter_factor
            )

            if config.log_retries:
                logger.warning(
                    f"Retry {attempt + 1}/{config.max_attempts} for "
                    f"{func.__name__} after {delay:.2f}s: {e}"
                )

            if config.on_retry:
                config.on_retry(e, attempt + 1)

            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    raise RetryExhaustedError(last_exception, config.max_attempts)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    exclude: Optional[Tuple[Type[Exception], ...]] = None,
    log: bool = True,
) -> Callable:
    """
    Decorator for adding retry logic to async functions.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay cap (seconds)
        exponential_base: Backoff multiplier
        jitter: Add random jitter to delays
        exceptions: Only retry on these exception types
        exclude: Never retry on these exception types
        log: Log retry attempts

    Example:
        @retry(max_attempts=3, exceptions=(TimeoutError, ConnectionError))
        async def call_api():
            return await httpx.get("https://api.example.com")
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retry_exceptions=exceptions,
        exclude_exceptions=exclude or (KeyboardInterrupt, SystemExit, GeneratorExit),
        log_retries=log,
    )

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await execute_with_retry(func, config, *args, **kwargs)
        return wrapper

    return decorator


class Retry:
    """
    Context manager for retry operations.

    Provides more control over retry behavior than the decorator.

    Usage:
        async with Retry(max_attempts=5) as r:
            result = await r.execute(async_function, arg1, arg2)

        # Check metrics
        print(f"Succeeded after {r.attempts} attempts")
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        **kwargs
    ):
        self.config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            **kwargs
        )
        self.attempts = 0
        self.last_exception: Optional[Exception] = None
        self._succeeded = False

    @property
    def succeeded(self) -> bool:
        """Check if last execution succeeded."""
        return self._succeeded

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs
    ) -> T:
        """Execute function with retry."""
        self.attempts = 0
        self.last_exception = None
        self._succeeded = False

        try:
            result = await execute_with_retry(func, self.config, *args, **kwargs)
            self._succeeded = True
            return result
        except RetryExhaustedError as e:
            self.attempts = e.attempts
            self.last_exception = e.last_exception
            raise

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


# Pre-configured retry decorators for common use cases
def retry_database(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """
    Retry decorator optimized for database operations.

    Quick retries with small delays for transient database issues.
    """
    return retry(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        jitter=True,
    )(func)


def retry_external_api(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """
    Retry decorator optimized for external API calls.

    Longer delays to allow external services to recover.
    """
    return retry(
        max_attempts=3,
        base_delay=2.0,
        max_delay=30.0,
        jitter=True,
    )(func)


def retry_network(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """
    Retry decorator for network operations.

    Handles timeout and connection errors specifically.
    """
    import httpx

    return retry(
        max_attempts=4,
        base_delay=1.0,
        max_delay=15.0,
        jitter=True,
        exceptions=(
            TimeoutError,
            ConnectionError,
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        ),
    )(func)


# Synchronous retry support
def execute_sync_with_retry(
    func: Callable[..., T],
    config: RetryConfig,
    *args,
    **kwargs
) -> T:
    """Execute a synchronous function with retry logic."""
    last_exception: Optional[Exception] = None

    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if not should_retry(e, config.retry_exceptions, config.exclude_exceptions):
                raise

            if attempt + 1 >= config.max_attempts:
                if config.log_retries:
                    logger.error(
                        f"Retry exhausted for {func.__name__} after "
                        f"{attempt + 1} attempts: {e}"
                    )
                raise RetryExhaustedError(e, attempt + 1) from e

            delay = calculate_delay(
                attempt,
                config.base_delay,
                config.max_delay,
                config.exponential_base,
                config.jitter,
                config.jitter_factor
            )

            if config.log_retries:
                logger.warning(
                    f"Retry {attempt + 1}/{config.max_attempts} for "
                    f"{func.__name__} after {delay:.2f}s: {e}"
                )

            time.sleep(delay)

    raise RetryExhaustedError(last_exception, config.max_attempts)
