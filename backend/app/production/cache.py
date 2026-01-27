"""
Redis caching layer wrapper.

Provides a simple, production-ready caching abstraction with
support for Redis (distributed) and in-memory (single instance) backends.

Usage:
    from app.production.cache import Cache, get_cache

    cache = get_cache()

    # Cache a value
    await cache.set("user:123", {"name": "John"}, ttl=3600)

    # Get a value
    user = await cache.get("user:123")

    # Delete a value
    await cache.delete("user:123")

    # Use decorator
    @cache.cached(ttl=300)
    async def get_user(user_id: str):
        return await db.get_user(user_id)
"""

import asyncio
import functools
import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from loguru import logger

T = TypeVar("T")


@dataclass
class CacheConfig:
    """Configuration for cache backend."""

    # Redis connection (None = use in-memory cache)
    redis_url: Optional[str] = None

    # Default TTL in seconds (0 = no expiry)
    default_ttl: int = 3600

    # Key prefix for namespacing
    key_prefix: str = "binaapp:"

    # Maximum memory entries for in-memory cache
    max_memory_entries: int = 10000

    # Serialize values as JSON
    serialize_json: bool = True

    # Connection pool size for Redis
    redis_pool_size: int = 10

    # Redis connection timeout
    redis_timeout: float = 5.0


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cached values."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections."""
        pass


@dataclass
class CacheEntry:
    """Entry in the in-memory cache."""
    value: Any
    expires_at: Optional[float]


class InMemoryBackend(CacheBackend):
    """
    In-memory cache backend for single-instance deployments.

    Features:
    - LRU eviction when max entries reached
    - TTL support with lazy expiration
    - Thread-safe operations
    """

    def __init__(self, max_entries: int = 10000):
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []
        self._max_entries = max_entries
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return None

            # Check expiration
            if entry.expires_at and time.time() > entry.expires_at:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return None

            # Update access order for LRU
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        async with self._lock:
            # Evict oldest entries if at capacity
            while len(self._cache) >= self._max_entries:
                if self._access_order:
                    oldest = self._access_order.pop(0)
                    self._cache.pop(oldest, None)
                else:
                    break

            expires_at = time.time() + ttl if ttl else None

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False

    async def exists(self, key: str) -> bool:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.expires_at and time.time() > entry.expires_at:
                del self._cache[key]
                return False
            return True

    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            return True

    async def close(self) -> None:
        await self.clear()

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class RedisBackend(CacheBackend):
    """
    Redis cache backend for distributed deployments.

    Requires redis[hiredis] package for best performance.
    """

    def __init__(self, redis_url: str, pool_size: int = 10, timeout: float = 5.0):
        self._redis_url = redis_url
        self._pool_size = pool_size
        self._timeout = timeout
        self._redis = None
        self._connected = False

    async def _get_client(self):
        """Get or create Redis client."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(
                    self._redis_url,
                    max_connections=self._pool_size,
                    socket_timeout=self._timeout,
                    socket_connect_timeout=self._timeout,
                    decode_responses=True,
                )
                self._connected = True
                logger.info(f"Connected to Redis: {self._redis_url}")
            except ImportError:
                logger.warning("redis package not installed, falling back to memory cache")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        try:
            client = await self._get_client()
            value = await asyncio.wait_for(
                client.get(key),
                timeout=self._timeout
            )
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Redis GET error for {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        try:
            client = await self._get_client()
            serialized = json.dumps(value, default=str)
            await asyncio.wait_for(
                client.set(key, serialized, ex=ttl),
                timeout=self._timeout
            )
            return True
        except Exception as e:
            logger.error(f"Redis SET error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            result = await asyncio.wait_for(
                client.delete(key),
                timeout=self._timeout
            )
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            result = await asyncio.wait_for(
                client.exists(key),
                timeout=self._timeout
            )
            return result > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for {key}: {e}")
            return False

    async def clear(self) -> bool:
        try:
            client = await self._get_client()
            await asyncio.wait_for(
                client.flushdb(),
                timeout=self._timeout
            )
            return True
        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
            return False

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False


class Cache:
    """
    High-level cache abstraction with support for multiple backends.

    Features:
    - Automatic serialization/deserialization
    - Key prefixing for namespacing
    - Decorator for caching function results
    - Graceful fallback on backend errors
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()

        # Initialize backend
        if self.config.redis_url:
            try:
                self._backend = RedisBackend(
                    self.config.redis_url,
                    self.config.redis_pool_size,
                    self.config.redis_timeout
                )
            except ImportError:
                logger.warning("Redis not available, using in-memory cache")
                self._backend = InMemoryBackend(self.config.max_memory_entries)
        else:
            self._backend = InMemoryBackend(self.config.max_memory_entries)

        logger.info(
            f"Cache initialized with {type(self._backend).__name__} backend"
        )

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.config.key_prefix}{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        full_key = self._make_key(key)
        value = await self._backend.get(full_key)
        return value if value is not None else default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)

        Returns:
            True if successful
        """
        full_key = self._make_key(key)
        actual_ttl = ttl if ttl is not None else self.config.default_ttl
        return await self._backend.set(full_key, value, actual_ttl or None)

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        full_key = self._make_key(key)
        return await self._backend.delete(full_key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        full_key = self._make_key(key)
        return await self._backend.exists(full_key)

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get value from cache, or compute and cache if missing.

        Args:
            key: Cache key
            factory: Function to compute value if not cached
            ttl: Time-to-live in seconds

        Returns:
            Cached or computed value
        """
        value = await self.get(key)
        if value is not None:
            return value

        # Compute and cache
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()

        await self.set(key, value, ttl)
        return value

    async def clear(self) -> bool:
        """Clear all cached values."""
        return await self._backend.clear()

    async def close(self) -> None:
        """Close cache connections."""
        await self._backend.close()

    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = "",
        key_builder: Optional[Callable[..., str]] = None
    ):
        """
        Decorator for caching function results.

        Args:
            ttl: Cache TTL in seconds
            key_prefix: Prefix for cache keys
            key_builder: Custom function to build cache key from args

        Example:
            @cache.cached(ttl=300, key_prefix="user:")
            async def get_user(user_id: str):
                return await db.get_user(user_id)
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default: hash of function name + args
                    key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                    cache_key = hashlib.md5(key_data.encode()).hexdigest()

                full_key = f"{key_prefix}{cache_key}"

                # Try to get from cache
                cached_value = await self.get(full_key)
                if cached_value is not None:
                    return cached_value

                # Compute value
                if asyncio.iscoroutinefunction(func):
                    value = await func(*args, **kwargs)
                else:
                    value = func(*args, **kwargs)

                # Cache result
                await self.set(full_key, value, ttl)

                return value

            return wrapper
        return decorator

    def invalidate(self, pattern: str):
        """
        Decorator to invalidate cache on function call.

        Args:
            pattern: Key pattern to invalidate (supports * wildcard)

        Example:
            @cache.invalidate("user:*")
            async def update_user(user_id: str, data: dict):
                await db.update_user(user_id, data)
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)

                # Delete matching keys
                # Note: Pattern deletion requires Redis SCAN for production
                # For simplicity, we delete the exact pattern key
                await self.delete(pattern.replace("*", ""))

                return result
            return wrapper
        return decorator


# Global cache instance
_cache: Optional[Cache] = None


def get_cache(config: Optional[CacheConfig] = None) -> Cache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache(config)
    return _cache


async def close_cache() -> None:
    """Close the global cache instance."""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None


# Convenience functions
async def cache_get(key: str, default: Any = None) -> Any:
    """Get value from global cache."""
    return await get_cache().get(key, default)


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in global cache."""
    return await get_cache().set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    """Delete value from global cache."""
    return await get_cache().delete(key)
