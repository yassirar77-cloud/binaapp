"""
Production-grade structured JSON logging configuration.

Provides structured logging suitable for log aggregation systems
(ELK, Datadog, CloudWatch, etc.) while maintaining human readability.

Usage:
    from app.production.logging_production import configure_production_logging

    configure_production_logging(
        json_output=True,
        log_level="INFO"
    )
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from loguru import logger


@dataclass
class LoggingConfig:
    """Configuration for production logging."""

    # Output format
    json_output: bool = True  # True for production, False for development
    include_timestamps: bool = True
    include_level: bool = True
    include_module: bool = True
    include_function: bool = True
    include_line: bool = False  # Usually too verbose for production

    # Log level
    log_level: str = "INFO"

    # File output
    log_to_file: bool = True
    log_file_path: str = "logs/binaapp.log"
    error_log_path: str = "logs/binaapp_error.log"

    # Rotation
    rotation: str = "00:00"  # Rotate at midnight
    retention: str = "30 days"
    compression: str = "zip"

    # Sensitive data masking
    mask_sensitive: bool = True
    sensitive_keys: tuple = (
        "password", "token", "secret", "api_key", "apikey",
        "authorization", "auth", "key", "credential", "credit_card",
        "card_number", "cvv", "ssn", "private_key"
    )

    # Maximum message length (truncate long messages)
    max_message_length: int = 10000

    # Service identification
    service_name: str = "binaapp"
    environment: str = "production"


class SensitiveDataFilter:
    """
    Filter for masking sensitive data in log messages.

    Recursively masks values for sensitive keys in dictionaries.
    """

    MASK = "***REDACTED***"

    def __init__(self, sensitive_keys: tuple):
        self.sensitive_keys = {k.lower() for k in sensitive_keys}

    def mask_value(self, obj: Any, depth: int = 0) -> Any:
        """Recursively mask sensitive values."""
        if depth > 10:  # Prevent infinite recursion
            return obj

        if isinstance(obj, dict):
            return {
                k: self.MASK if k.lower() in self.sensitive_keys
                else self.mask_value(v, depth + 1)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self.mask_value(item, depth + 1) for item in obj]
        elif isinstance(obj, str):
            # Check if string contains sensitive patterns
            for key in self.sensitive_keys:
                if key in obj.lower():
                    # Mask potential key-value pairs in strings
                    return self._mask_string_patterns(obj)
            return obj
        return obj

    def _mask_string_patterns(self, text: str) -> str:
        """Mask patterns like 'key=value' or 'key: value' in strings."""
        import re
        for key in self.sensitive_keys:
            # Match patterns like: api_key=abc123 or token: xyz
            pattern = rf'({key})\s*[=:]\s*\S+'
            text = re.sub(pattern, rf'\1={self.MASK}', text, flags=re.IGNORECASE)
        return text


def json_formatter(record: Dict) -> str:
    """
    Format log record as JSON for structured logging.

    Output format compatible with ELK, Datadog, and CloudWatch.
    """
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "logger": record["name"],
    }

    # Add location info
    if record.get("module"):
        log_entry["module"] = record["module"]
    if record.get("function"):
        log_entry["function"] = record["function"]
    if record.get("line"):
        log_entry["line"] = record["line"]

    # Add exception info
    if record.get("exception"):
        log_entry["exception"] = {
            "type": str(record["exception"].type.__name__) if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
            "traceback": record["exception"].traceback if record["exception"].traceback else None,
        }

    # Add extra fields
    extra = record.get("extra", {})
    if extra:
        log_entry["extra"] = extra

    return json.dumps(log_entry, default=str) + "\n"


def human_formatter(record: Dict) -> str:
    """
    Format log record for human readability in development.
    """
    timestamp = record["time"].strftime("%Y-%m-%d %H:%M:%S")
    level = record["level"].name.ljust(8)
    module = record.get("module", "")
    message = record["message"]

    formatted = f"{timestamp} | {level} | {module} | {message}"

    if record.get("exception"):
        formatted += f"\n{record['exception'].traceback}"

    return formatted + "\n"


def configure_production_logging(config: Optional[LoggingConfig] = None) -> None:
    """
    Configure loguru for production use.

    This function configures logging additively without modifying
    existing logging behavior in the codebase.
    """
    config = config or LoggingConfig()

    # Remove default handler
    logger.remove()

    # Create sensitive data filter
    sensitive_filter = SensitiveDataFilter(config.sensitive_keys)

    def filter_sensitive(record):
        """Filter function to mask sensitive data."""
        if config.mask_sensitive:
            record["message"] = sensitive_filter.mask_value(record["message"])
            if "extra" in record:
                record["extra"] = sensitive_filter.mask_value(record["extra"])
        return True

    # Console output
    console_format = json_formatter if config.json_output else human_formatter

    logger.add(
        sys.stdout,
        format=console_format,
        level=config.log_level,
        filter=filter_sensitive,
        colorize=not config.json_output,
    )

    # File output
    if config.log_to_file:
        # Main log file
        logger.add(
            config.log_file_path,
            format=json_formatter,
            level=config.log_level,
            rotation=config.rotation,
            retention=config.retention,
            compression=config.compression,
            filter=filter_sensitive,
        )

        # Error-only log file
        logger.add(
            config.error_log_path,
            format=json_formatter,
            level="ERROR",
            rotation=config.rotation,
            retention=config.retention,
            compression=config.compression,
            filter=filter_sensitive,
        )

    logger.info(
        f"Production logging configured: "
        f"level={config.log_level}, json={config.json_output}, "
        f"service={config.service_name}, env={config.environment}"
    )


def create_request_logger(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    **extra_context
) -> Any:
    """
    Create a logger with request context bound.

    Usage:
        req_logger = create_request_logger(
            request_id="abc-123",
            user_id="user-456"
        )
        req_logger.info("Processing payment")
    """
    context = {}
    if request_id:
        context["request_id"] = request_id
    if user_id:
        context["user_id"] = user_id
    context.update(extra_context)

    return logger.bind(**context)


class LogContext:
    """
    Context manager for adding context to all logs within a block.

    Usage:
        with LogContext(order_id="ORD-123", customer="john"):
            logger.info("Processing order")  # Will include order_id and customer
    """

    def __init__(self, **context):
        self.context = context
        self._token = None

    def __enter__(self):
        self._token = logger.contextualize(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            self._token.__exit__(exc_type, exc_val, exc_tb)
        return False


# Performance logging utilities
class PerformanceLogger:
    """
    Utility for logging performance metrics.

    Usage:
        perf = PerformanceLogger()

        with perf.timer("database_query"):
            result = db.query()

        perf.log_metrics()
    """

    def __init__(self, operation_name: str = "operation"):
        self.operation_name = operation_name
        self._timings: Dict[str, float] = {}

    def timer(self, name: str):
        """Context manager for timing operations."""
        import time

        class Timer:
            def __init__(self, perf_logger, timer_name):
                self.perf_logger = perf_logger
                self.timer_name = timer_name
                self.start_time = None

            def __enter__(self):
                self.start_time = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                elapsed = (time.perf_counter() - self.start_time) * 1000
                self.perf_logger._timings[self.timer_name] = elapsed
                return False

        return Timer(self, name)

    def log_metrics(self, log_level: str = "INFO"):
        """Log all recorded performance metrics."""
        getattr(logger, log_level.lower())(
            f"Performance metrics for {self.operation_name}",
            extra={"metrics": self._timings, "type": "performance"}
        )

    def get_metrics(self) -> Dict[str, float]:
        """Get recorded metrics."""
        return self._timings.copy()


# Convenience function for one-liner setup
def setup_logging(
    json_output: bool = True,
    log_level: str = "INFO",
    service_name: str = "binaapp",
    environment: str = "production"
) -> None:
    """
    Quick setup for production logging.

    Args:
        json_output: Use JSON format (True for production)
        log_level: Minimum log level
        service_name: Service identifier in logs
        environment: Environment name
    """
    config = LoggingConfig(
        json_output=json_output,
        log_level=log_level,
        service_name=service_name,
        environment=environment,
    )
    configure_production_logging(config)
