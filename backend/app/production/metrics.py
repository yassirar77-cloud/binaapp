"""
Prometheus-compatible metrics collection.

Provides application metrics for monitoring, alerting, and observability.
Exposes metrics in Prometheus text format for scraping.

Usage:
    from app.production.metrics import MetricsCollector, get_metrics

    metrics = get_metrics()
    metrics.inc_counter("requests_total", labels={"method": "GET"})
    metrics.observe_histogram("request_duration_seconds", 0.5)

    # In endpoint handler
    @app.get("/metrics")
    async def metrics_endpoint():
        return Response(
            content=get_metrics().export(),
            media_type="text/plain"
        )
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from loguru import logger


@dataclass
class MetricDefinition:
    """Definition of a metric."""
    name: str
    metric_type: str  # counter, gauge, histogram, summary
    help_text: str
    labels: List[str] = field(default_factory=list)


class Counter:
    """Thread-safe counter metric."""

    def __init__(self):
        self._values: Dict[Tuple, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def inc(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Increment counter."""
        key = self._labels_to_key(labels)
        async with self._lock:
            self._values[key] += value

    def inc_sync(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Synchronous increment (for non-async contexts)."""
        key = self._labels_to_key(labels)
        self._values[key] += value

    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> Tuple:
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    def get_values(self) -> Dict[Tuple, float]:
        return dict(self._values)


class Gauge:
    """Thread-safe gauge metric."""

    def __init__(self):
        self._values: Dict[Tuple, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        key = self._labels_to_key(labels)
        async with self._lock:
            self._values[key] = value

    async def inc(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Increment gauge."""
        key = self._labels_to_key(labels)
        async with self._lock:
            self._values[key] += value

    async def dec(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0):
        """Decrement gauge."""
        key = self._labels_to_key(labels)
        async with self._lock:
            self._values[key] -= value

    def set_sync(self, value: float, labels: Optional[Dict[str, str]] = None):
        key = self._labels_to_key(labels)
        self._values[key] = value

    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> Tuple:
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    def get_values(self) -> Dict[Tuple, float]:
        return dict(self._values)


class Histogram:
    """
    Thread-safe histogram metric.

    Default buckets are suitable for HTTP request latencies.
    """

    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
        0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf")
    )

    def __init__(self, buckets: Optional[Tuple[float, ...]] = None):
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._bucket_counts: Dict[Tuple, Dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: Dict[Tuple, float] = defaultdict(float)
        self._counts: Dict[Tuple, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an observation."""
        key = self._labels_to_key(labels)
        async with self._lock:
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[key][bucket] += 1
            self._sums[key] += value
            self._counts[key] += 1

    def observe_sync(self, value: float, labels: Optional[Dict[str, str]] = None):
        key = self._labels_to_key(labels)
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[key][bucket] += 1
        self._sums[key] += value
        self._counts[key] += 1

    def _labels_to_key(self, labels: Optional[Dict[str, str]]) -> Tuple:
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    def get_values(self) -> Dict[str, Any]:
        return {
            "buckets": dict(self._bucket_counts),
            "sums": dict(self._sums),
            "counts": dict(self._counts),
        }


class MetricsCollector:
    """
    Central metrics collector.

    Manages all application metrics and exports in Prometheus format.
    """

    def __init__(self, prefix: str = "binaapp"):
        self.prefix = prefix
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._definitions: Dict[str, MetricDefinition] = {}

        # Register default metrics
        self._register_default_metrics()

    def _register_default_metrics(self):
        """Register commonly used metrics."""
        # HTTP request metrics
        self.register_counter(
            "http_requests_total",
            "Total HTTP requests",
            labels=["method", "endpoint", "status"]
        )
        self.register_histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            labels=["method", "endpoint"]
        )
        self.register_gauge(
            "http_requests_in_progress",
            "Number of HTTP requests currently in progress",
            labels=["method"]
        )

        # Application metrics
        self.register_gauge(
            "active_connections",
            "Number of active connections"
        )
        self.register_counter(
            "errors_total",
            "Total errors",
            labels=["type", "endpoint"]
        )

        # Business metrics
        self.register_counter(
            "websites_generated_total",
            "Total websites generated"
        )
        self.register_counter(
            "orders_created_total",
            "Total orders created"
        )
        self.register_gauge(
            "active_users",
            "Number of currently active users"
        )

    def register_counter(
        self,
        name: str,
        help_text: str,
        labels: Optional[List[str]] = None
    ) -> Counter:
        """Register a new counter metric."""
        full_name = f"{self.prefix}_{name}"
        self._definitions[full_name] = MetricDefinition(
            name=full_name,
            metric_type="counter",
            help_text=help_text,
            labels=labels or []
        )
        self._counters[full_name] = Counter()
        return self._counters[full_name]

    def register_gauge(
        self,
        name: str,
        help_text: str,
        labels: Optional[List[str]] = None
    ) -> Gauge:
        """Register a new gauge metric."""
        full_name = f"{self.prefix}_{name}"
        self._definitions[full_name] = MetricDefinition(
            name=full_name,
            metric_type="gauge",
            help_text=help_text,
            labels=labels or []
        )
        self._gauges[full_name] = Gauge()
        return self._gauges[full_name]

    def register_histogram(
        self,
        name: str,
        help_text: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[Tuple[float, ...]] = None
    ) -> Histogram:
        """Register a new histogram metric."""
        full_name = f"{self.prefix}_{name}"
        self._definitions[full_name] = MetricDefinition(
            name=full_name,
            metric_type="histogram",
            help_text=help_text,
            labels=labels or []
        )
        self._histograms[full_name] = Histogram(buckets)
        return self._histograms[full_name]

    async def inc_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        value: float = 1.0
    ):
        """Increment a counter."""
        full_name = f"{self.prefix}_{name}"
        if full_name in self._counters:
            await self._counters[full_name].inc(labels, value)

    async def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Set a gauge value."""
        full_name = f"{self.prefix}_{name}"
        if full_name in self._gauges:
            await self._gauges[full_name].set(value, labels)

    async def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Record a histogram observation."""
        full_name = f"{self.prefix}_{name}"
        if full_name in self._histograms:
            await self._histograms[full_name].observe(value, labels)

    def _format_labels(self, labels: Tuple) -> str:
        """Format labels tuple as Prometheus label string."""
        if not labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in labels]
        return "{" + ",".join(parts) + "}"

    def export(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []

        # Export counters
        for name, counter in self._counters.items():
            defn = self._definitions.get(name)
            if defn:
                lines.append(f"# HELP {name} {defn.help_text}")
                lines.append(f"# TYPE {name} counter")

            for labels, value in counter.get_values().items():
                label_str = self._format_labels(labels)
                lines.append(f"{name}{label_str} {value}")

        # Export gauges
        for name, gauge in self._gauges.items():
            defn = self._definitions.get(name)
            if defn:
                lines.append(f"# HELP {name} {defn.help_text}")
                lines.append(f"# TYPE {name} gauge")

            for labels, value in gauge.get_values().items():
                label_str = self._format_labels(labels)
                lines.append(f"{name}{label_str} {value}")

        # Export histograms
        for name, histogram in self._histograms.items():
            defn = self._definitions.get(name)
            if defn:
                lines.append(f"# HELP {name} {defn.help_text}")
                lines.append(f"# TYPE {name} histogram")

            values = histogram.get_values()
            for labels, buckets in values["buckets"].items():
                label_str = self._format_labels(labels)
                cumulative = 0
                for bucket, count in sorted(buckets.items()):
                    cumulative += count
                    bucket_label = f'+Inf' if bucket == float("inf") else str(bucket)
                    if labels:
                        full_labels = label_str[:-1] + f',le="{bucket_label}"' + "}"
                    else:
                        full_labels = f'{{le="{bucket_label}"}}'
                    lines.append(f"{name}_bucket{full_labels} {cumulative}")

                lines.append(f"{name}_sum{label_str} {values['sums'].get(labels, 0)}")
                lines.append(f"{name}_count{label_str} {values['counts'].get(labels, 0)}")

        return "\n".join(lines) + "\n"


# Global metrics instance
_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic HTTP request metrics collection.

    Tracks:
    - Request counts by method, endpoint, status
    - Request duration histograms
    - In-progress request gauges
    """

    def __init__(self, app: ASGIApp, metrics: Optional[MetricsCollector] = None):
        super().__init__(app)
        self.metrics = metrics or get_metrics()
        logger.info("Metrics middleware initialized")

    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality."""
        import re
        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE
        )
        # Replace numeric IDs
        path = re.sub(r"/\d+", "/{id}", path)
        return path

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        method = request.method
        path = self._normalize_path(request.url.path)

        # Skip metrics endpoint to avoid recursion
        if path == "/metrics":
            return await call_next(request)

        # Track in-progress requests
        await self.metrics.set_gauge(
            "http_requests_in_progress",
            1,
            labels={"method": method}
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time

            # Record request count
            await self.metrics.inc_counter(
                "http_requests_total",
                labels={"method": method, "endpoint": path, "status": status}
            )

            # Record duration
            await self.metrics.observe_histogram(
                "http_request_duration_seconds",
                duration,
                labels={"method": method, "endpoint": path}
            )

            # Decrement in-progress
            gauge = self.metrics._gauges.get(f"{self.metrics.prefix}_http_requests_in_progress")
            if gauge:
                await gauge.dec(labels={"method": method})

        return response


# Context manager for timing operations
class Timer:
    """
    Context manager for timing operations and recording to histogram.

    Usage:
        async with Timer(metrics, "database_query_seconds"):
            await db.query()
    """

    def __init__(
        self,
        metrics: MetricsCollector,
        histogram_name: str,
        labels: Optional[Dict[str, str]] = None
    ):
        self.metrics = metrics
        self.histogram_name = histogram_name
        self.labels = labels
        self.start_time: Optional[float] = None

    async def __aenter__(self):
        self.start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            await self.metrics.observe_histogram(
                self.histogram_name,
                duration,
                self.labels
            )
        return False
