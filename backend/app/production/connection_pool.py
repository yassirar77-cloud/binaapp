"""
HTTP client connection pooling configuration for efficient external API calls.

Provides properly configured httpx clients with connection pooling,
timeouts, and retry capabilities for production use.

Usage:
    from app.production.connection_pool import get_http_client, HttpClientConfig

    # Get a shared, pooled client
    async with get_http_client() as client:
        response = await client.get("https://api.example.com")

    # Or create a dedicated client for specific service
    config = HttpClientConfig(base_url="https://api.supabase.co")
    client = create_http_client(config)
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx
from loguru import logger


@dataclass
class HttpClientConfig:
    """Configuration for HTTP client with connection pooling."""

    # Base URL for relative requests
    base_url: Optional[str] = None

    # Connection pool limits
    max_connections: int = 100  # Total connections in pool
    max_keepalive_connections: int = 20  # Keep-alive connections
    keepalive_expiry: float = 30.0  # Seconds before closing idle connections

    # Timeouts (seconds)
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    pool_timeout: float = 10.0  # Time to wait for connection from pool

    # HTTP/2 support
    http2: bool = True

    # Retry configuration
    max_retries: int = 3
    retry_on_status: tuple = (502, 503, 504)  # Gateway errors

    # Headers
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "BinaApp/1.0",
        "Accept": "application/json",
    })

    # SSL verification
    verify_ssl: bool = True

    # Follow redirects
    follow_redirects: bool = True
    max_redirects: int = 5


class PooledHttpClient:
    """
    HTTP client wrapper with connection pooling and automatic retry.

    Features:
    - Connection pooling for efficient reuse
    - Configurable timeouts per operation type
    - Automatic retry for transient failures
    - HTTP/2 support
    - Proper resource cleanup
    """

    def __init__(self, config: Optional[HttpClientConfig] = None):
        self.config = config or HttpClientConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client = await self._create_client()
        return self._client

    async def _create_client(self) -> httpx.AsyncClient:
        """Create a new configured HTTP client."""
        timeout = httpx.Timeout(
            connect=self.config.connect_timeout,
            read=self.config.read_timeout,
            write=self.config.write_timeout,
            pool=self.config.pool_timeout,
        )

        limits = httpx.Limits(
            max_connections=self.config.max_connections,
            max_keepalive_connections=self.config.max_keepalive_connections,
            keepalive_expiry=self.config.keepalive_expiry,
        )

        client = httpx.AsyncClient(
            base_url=self.config.base_url or "",
            timeout=timeout,
            limits=limits,
            http2=self.config.http2,
            headers=self.config.default_headers,
            verify=self.config.verify_ssl,
            follow_redirects=self.config.follow_redirects,
            max_redirects=self.config.max_redirects,
        )

        logger.info(
            f"HTTP client created: max_connections={self.config.max_connections}, "
            f"http2={self.config.http2}, base_url={self.config.base_url}"
        )

        return client

    async def request(
        self,
        method: str,
        url: str,
        retry_count: int = 0,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with automatic retry.

        Args:
            method: HTTP method
            url: URL or path (relative if base_url configured)
            retry_count: Current retry attempt (internal use)
            **kwargs: Additional arguments passed to httpx

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPError: On request failure after retries
        """
        client = await self._get_client()

        try:
            response = await client.request(method, url, **kwargs)

            # Check if we should retry on status
            if (
                response.status_code in self.config.retry_on_status
                and retry_count < self.config.max_retries
            ):
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(
                    f"Retrying {method} {url} after status {response.status_code}, "
                    f"attempt {retry_count + 1}/{self.config.max_retries}"
                )
                await asyncio.sleep(wait_time)
                return await self.request(
                    method, url, retry_count=retry_count + 1, **kwargs
                )

            return response

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if retry_count < self.config.max_retries:
                wait_time = 2 ** retry_count
                logger.warning(
                    f"Retrying {method} {url} after {type(e).__name__}, "
                    f"attempt {retry_count + 1}/{self.config.max_retries}"
                )
                await asyncio.sleep(wait_time)
                return await self.request(
                    method, url, retry_count=retry_count + 1, **kwargs
                )
            raise

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """Make a PATCH request."""
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    async def close(self) -> None:
        """Close the HTTP client and release connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("HTTP client closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False


# Global client pool for different services
_client_pool: Dict[str, PooledHttpClient] = {}
_pool_lock = asyncio.Lock()


async def get_http_client(
    name: str = "default",
    config: Optional[HttpClientConfig] = None
) -> PooledHttpClient:
    """
    Get or create a pooled HTTP client by name.

    Clients are cached by name for reuse across requests.

    Args:
        name: Client identifier (e.g., "supabase", "deepseek")
        config: Optional configuration (only used on first creation)

    Returns:
        PooledHttpClient instance
    """
    async with _pool_lock:
        if name not in _client_pool:
            _client_pool[name] = PooledHttpClient(config)
            logger.debug(f"Created HTTP client pool: {name}")
        return _client_pool[name]


async def close_all_clients() -> None:
    """Close all pooled HTTP clients (call during shutdown)."""
    async with _pool_lock:
        for name, client in _client_pool.items():
            try:
                await client.close()
                logger.debug(f"Closed HTTP client: {name}")
            except Exception as e:
                logger.error(f"Error closing HTTP client {name}: {e}")
        _client_pool.clear()


# Pre-configured client factories
def create_supabase_client(
    base_url: str,
    api_key: str,
    service_role_key: Optional[str] = None
) -> PooledHttpClient:
    """
    Create an HTTP client configured for Supabase REST API.

    Args:
        base_url: Supabase project URL
        api_key: Anon key or service role key
        service_role_key: Optional service role key for admin operations
    """
    config = HttpClientConfig(
        base_url=f"{base_url}/rest/v1",
        default_headers={
            "apikey": api_key,
            "Authorization": f"Bearer {service_role_key or api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        max_connections=50,
        read_timeout=60.0,
    )
    return PooledHttpClient(config)


def create_ai_service_client(
    base_url: str,
    api_key: str,
    timeout: float = 120.0
) -> PooledHttpClient:
    """
    Create an HTTP client configured for AI service APIs.

    Longer timeouts for AI generation operations.
    """
    config = HttpClientConfig(
        base_url=base_url,
        default_headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        read_timeout=timeout,  # AI operations can be slow
        write_timeout=timeout,
        max_retries=2,  # Fewer retries for expensive operations
    )
    return PooledHttpClient(config)


# Convenience context manager
@asynccontextmanager
async def http_client(
    name: str = "default",
    config: Optional[HttpClientConfig] = None
):
    """
    Context manager for getting a pooled HTTP client.

    Usage:
        async with http_client("supabase") as client:
            response = await client.get("/users")
    """
    client = await get_http_client(name, config)
    yield client
    # Note: Don't close here as client is pooled for reuse
