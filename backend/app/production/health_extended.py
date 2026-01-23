"""
Extended health check with dependency monitoring.

Provides comprehensive health checks for all service dependencies,
suitable for Kubernetes liveness/readiness probes.

Usage:
    from app.production.health_extended import HealthChecker, get_health_checker

    checker = get_health_checker()
    checker.register_check("supabase", check_supabase_health)

    # In endpoint
    @app.get("/health/ready")
    async def readiness_check():
        return await checker.check_readiness()
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx
from loguru import logger


class HealthStatus(Enum):
    """Health check result status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    latency_ms: float
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HealthReport:
    """Aggregated health report."""
    status: HealthStatus
    checks: List[CheckResult]
    version: str
    uptime_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "timestamp": self.timestamp.isoformat(),
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""

    # Timeout for individual checks (seconds)
    check_timeout: float = 5.0

    # Parallel vs sequential execution
    run_parallel: bool = True

    # Cache results for this many seconds (0 = no cache)
    cache_ttl: float = 5.0

    # Which checks are required for readiness
    required_checks: List[str] = field(default_factory=lambda: [
        "database", "storage"
    ])

    # Application version
    version: str = "1.0.0"


HealthCheckFunc = Callable[[], Awaitable[CheckResult]]


class HealthChecker:
    """
    Comprehensive health checker with dependency monitoring.

    Features:
    - Register custom health checks
    - Parallel execution with timeouts
    - Result caching to prevent overload
    - Separate liveness and readiness endpoints
    - Degraded state support
    """

    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config or HealthCheckConfig()
        self._checks: Dict[str, HealthCheckFunc] = {}
        self._start_time = time.time()
        self._last_report: Optional[HealthReport] = None
        self._last_check_time: float = 0

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self):
        """Register built-in health checks."""
        self.register_check("self", self._check_self)

    async def _check_self(self) -> CheckResult:
        """Basic self-check (always healthy if responding)."""
        return CheckResult(
            name="self",
            status=HealthStatus.HEALTHY,
            latency_ms=0,
            message="Application is responding"
        )

    def register_check(
        self,
        name: str,
        check_func: HealthCheckFunc,
        required: bool = False
    ):
        """
        Register a health check function.

        Args:
            name: Unique name for this check
            check_func: Async function returning CheckResult
            required: If True, this check is required for readiness
        """
        self._checks[name] = check_func

        if required and name not in self.config.required_checks:
            self.config.required_checks.append(name)

        logger.debug(f"Registered health check: {name}")

    async def _run_check(
        self,
        name: str,
        check_func: HealthCheckFunc
    ) -> CheckResult:
        """Run a single health check with timeout."""
        start = time.perf_counter()

        try:
            result = await asyncio.wait_for(
                check_func(),
                timeout=self.config.check_timeout
            )
            return result
        except asyncio.TimeoutError:
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Check timed out after {self.config.check_timeout}s"
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.error(f"Health check '{name}' failed: {e}")
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=str(e)
            )

    async def _run_all_checks(self) -> List[CheckResult]:
        """Run all registered health checks."""
        if self.config.run_parallel:
            tasks = [
                self._run_check(name, func)
                for name, func in self._checks.items()
            ]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for name, func in self._checks.items():
                result = await self._run_check(name, func)
                results.append(result)
            return results

    def _aggregate_status(self, results: List[CheckResult]) -> HealthStatus:
        """Determine overall status from individual check results."""
        statuses = [r.status for r in results]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY

        # Check if any required checks are unhealthy
        for result in results:
            if (
                result.name in self.config.required_checks
                and result.status == HealthStatus.UNHEALTHY
            ):
                return HealthStatus.UNHEALTHY

        # Some checks degraded but required checks OK
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    async def check_health(self, force: bool = False) -> HealthReport:
        """
        Run all health checks and return aggregated report.

        Args:
            force: Bypass cache and run fresh checks

        Returns:
            HealthReport with all check results
        """
        now = time.time()

        # Return cached result if valid
        if (
            not force
            and self._last_report
            and (now - self._last_check_time) < self.config.cache_ttl
        ):
            return self._last_report

        # Run all checks
        results = await self._run_all_checks()

        # Aggregate status
        overall_status = self._aggregate_status(results)

        # Create report
        report = HealthReport(
            status=overall_status,
            checks=results,
            version=self.config.version,
            uptime_seconds=now - self._start_time,
        )

        # Cache result
        self._last_report = report
        self._last_check_time = now

        return report

    async def check_liveness(self) -> Dict[str, Any]:
        """
        Simple liveness check for Kubernetes.

        Returns 200 if application is alive, regardless of dependencies.
        """
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def check_readiness(self) -> Dict[str, Any]:
        """
        Readiness check for Kubernetes.

        Returns 200 only if all required dependencies are healthy.
        """
        report = await self.check_health()

        # Determine if ready
        is_ready = report.status != HealthStatus.UNHEALTHY

        return {
            "ready": is_ready,
            "status": report.status.value,
            "checks": {
                r.name: r.status.value
                for r in report.checks
                if r.name in self.config.required_checks
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


# Pre-built health check functions

async def create_supabase_check(
    supabase_url: str,
    api_key: str,
    timeout: float = 5.0
) -> HealthCheckFunc:
    """Create a health check for Supabase."""

    async def check_supabase() -> CheckResult:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(
                    f"{supabase_url}/rest/v1/",
                    headers={
                        "apikey": api_key,
                        "Authorization": f"Bearer {api_key}",
                    }
                )
                latency = (time.perf_counter() - start) * 1000

                if response.status_code == 200:
                    return CheckResult(
                        name="supabase",
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message="Supabase REST API is accessible"
                    )
                else:
                    return CheckResult(
                        name="supabase",
                        status=HealthStatus.UNHEALTHY,
                        latency_ms=latency,
                        message=f"Supabase returned status {response.status_code}"
                    )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(
                name="supabase",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Failed to connect to Supabase: {str(e)}"
            )

    return check_supabase


async def create_redis_check(redis_url: str, timeout: float = 2.0) -> HealthCheckFunc:
    """Create a health check for Redis."""

    async def check_redis() -> CheckResult:
        start = time.perf_counter()
        try:
            import redis.asyncio as redis_async

            client = redis_async.from_url(
                redis_url,
                socket_timeout=timeout,
                socket_connect_timeout=timeout,
            )
            await client.ping()
            await client.close()

            latency = (time.perf_counter() - start) * 1000
            return CheckResult(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Redis is responding to PING"
            )
        except ImportError:
            return CheckResult(
                name="redis",
                status=HealthStatus.DEGRADED,
                latency_ms=0,
                message="Redis client not installed"
            )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Redis connection failed: {str(e)}"
            )

    return check_redis


async def create_external_api_check(
    name: str,
    url: str,
    timeout: float = 5.0,
    expected_status: int = 200
) -> HealthCheckFunc:
    """Create a health check for an external API."""

    async def check_api() -> CheckResult:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                latency = (time.perf_counter() - start) * 1000

                if response.status_code == expected_status:
                    return CheckResult(
                        name=name,
                        status=HealthStatus.HEALTHY,
                        latency_ms=latency,
                        message=f"{name} is accessible"
                    )
                else:
                    return CheckResult(
                        name=name,
                        status=HealthStatus.DEGRADED,
                        latency_ms=latency,
                        message=f"{name} returned status {response.status_code}"
                    )
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"{name} unreachable: {str(e)}"
            )

    return check_api


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker(config: Optional[HealthCheckConfig] = None) -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker(config)
    return _health_checker


def configure_health_checks(
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    redis_url: Optional[str] = None,
    version: str = "1.0.0"
) -> HealthChecker:
    """
    Configure health checker with common dependencies.

    Call this during application startup.
    """
    checker = get_health_checker(HealthCheckConfig(version=version))

    # Register Supabase check
    if supabase_url and supabase_key:
        async def supabase_check():
            check_func = await create_supabase_check(supabase_url, supabase_key)
            return await check_func()
        checker.register_check("supabase", supabase_check, required=True)

    # Register Redis check
    if redis_url:
        async def redis_check():
            check_func = await create_redis_check(redis_url)
            return await check_func()
        checker.register_check("redis", redis_check, required=False)

    logger.info(f"Health checker configured with {len(checker._checks)} checks")
    return checker
