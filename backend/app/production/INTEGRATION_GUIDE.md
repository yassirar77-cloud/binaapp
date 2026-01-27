# Production Hardening Integration Guide

This guide explains how to integrate the production-grade utilities into BinaApp
without modifying existing code. All integrations are **additive-only**.

## Quick Start

Add the following to your `main.py` after the existing middleware:

```python
from app.production.rate_limiter import RateLimitMiddleware, RateLimitConfig
from app.production.request_tracking import RequestTrackingMiddleware
from app.production.security_headers import SecurityHeadersMiddleware
from app.production.graceful_shutdown import GracefulShutdown, GracefulShutdownMiddleware
from app.production.metrics import MetricsMiddleware, get_metrics
from app.production.config_production import run_production_startup_checks
from app.production.logging_production import setup_logging
from app.production.health_extended import configure_health_checks

# Run startup checks (will raise if critical config missing)
if os.environ.get("ENVIRONMENT") == "production":
    run_production_startup_checks()

# Configure structured logging
setup_logging(
    json_output=os.environ.get("ENVIRONMENT") == "production",
    log_level=os.environ.get("LOG_LEVEL", "INFO")
)

# Initialize graceful shutdown
shutdown_handler = GracefulShutdown()

# Add middleware (order matters - first added = last executed)
app.add_middleware(MetricsMiddleware)  # Outermost - collects all metrics
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, config=RateLimitConfig(
    default_requests_per_minute=60,
    auth_limit=10,
    generation_limit=5
))
app.add_middleware(GracefulShutdownMiddleware, handler=shutdown_handler)

# Configure health checks
configure_health_checks(
    supabase_url=os.environ.get("SUPABASE_URL"),
    supabase_key=os.environ.get("SUPABASE_ANON_KEY"),
    redis_url=os.environ.get("REDIS_URL"),  # Optional
    version="1.0.0"
)

# Startup/shutdown events
@app.on_event("startup")
async def startup():
    await shutdown_handler.startup()

@app.on_event("shutdown")
async def shutdown():
    await shutdown_handler.shutdown()
```

## Component Integration Details

### 1. Rate Limiting

Protects API endpoints from abuse with configurable limits per endpoint type.

```python
from app.production.rate_limiter import RateLimitMiddleware, RateLimitConfig

config = RateLimitConfig(
    default_requests_per_minute=60,
    auth_limit=10,           # Login/register - strict for brute force protection
    generation_limit=5,      # AI generation - expensive operation
    upload_limit=20,
    exempt_paths={"/health", "/docs"}
)

app.add_middleware(RateLimitMiddleware, config=config)
```

### 2. Request ID Tracking

Enables distributed tracing with correlation IDs.

```python
from app.production.request_tracking import RequestTrackingMiddleware, get_request_id

app.add_middleware(RequestTrackingMiddleware)

# In your endpoint handlers:
from app.production.request_tracking import get_request_id, ctx_logger

@app.get("/api/example")
async def example():
    request_id = get_request_id()  # Access current request ID
    ctx_logger.info("Processing request")  # Auto-includes request ID
    return {"request_id": request_id}
```

### 3. Security Headers

Adds production security headers to all responses.

```python
from app.production.security_headers import SecurityHeadersMiddleware, SecurityHeadersConfig

# Use defaults (recommended)
app.add_middleware(SecurityHeadersMiddleware)

# Or customize
config = SecurityHeadersConfig(
    hsts_enabled=True,
    csp_enabled=True,
    frame_options_value="DENY"
)
app.add_middleware(SecurityHeadersMiddleware, config=config)
```

### 4. Circuit Breaker

Protects against cascade failures when external services are down.

```python
from app.production.circuit_breaker import circuit_breaker, CircuitBreaker

# As a decorator
@circuit_breaker(name="deepseek", failure_threshold=5, recovery_timeout=30)
async def call_deepseek_api(prompt: str):
    async with httpx.AsyncClient() as client:
        return await client.post("https://api.deepseek.com/v1/chat/completions", ...)

# As a context manager
cb = CircuitBreaker(name="supabase")
async with cb:
    result = await supabase_client.query(...)
```

### 5. Retry Utilities

Automatic retry with exponential backoff for transient failures.

```python
from app.production.retry_utils import retry, retry_external_api, retry_database

# General retry
@retry(max_attempts=3, base_delay=1.0, exceptions=(TimeoutError, ConnectionError))
async def fetch_data():
    ...

# Pre-configured for external APIs
@retry_external_api
async def call_external_service():
    ...

# Pre-configured for database operations
@retry_database
async def query_database():
    ...
```

### 6. Input Sanitization

Secure input handling to protect against injection attacks.

```python
from app.production.sanitization import (
    sanitize_string,
    validate_email,
    validate_phone_malaysia,
    Sanitizer
)

# Direct functions
clean_name = sanitize_string(user_input, max_length=100)
is_valid = validate_email(email_input)
phone = validate_phone_malaysia(phone_input)

# Using Sanitizer class
email = Sanitizer.email(request.email)  # Returns None if invalid
subdomain = Sanitizer.subdomain(request.subdomain)
amount = Sanitizer.decimal(request.amount, min_value=0, precision=2)
```

### 7. Caching

Redis-backed caching with in-memory fallback.

```python
from app.production.cache import get_cache, Cache, CacheConfig

# Get global cache instance
cache = get_cache()

# Cache operations
await cache.set("user:123", user_data, ttl=3600)
user = await cache.get("user:123")
await cache.delete("user:123")

# Decorator for caching function results
@cache.cached(ttl=300, key_prefix="user:")
async def get_user(user_id: str):
    return await db.get_user(user_id)
```

### 8. Metrics Collection

Prometheus-compatible metrics for monitoring.

```python
from app.production.metrics import get_metrics, MetricsMiddleware

# Add middleware for automatic HTTP metrics
app.add_middleware(MetricsMiddleware)

# Custom metrics
metrics = get_metrics()
await metrics.inc_counter("websites_generated_total")
await metrics.observe_histogram("ai_generation_duration_seconds", duration)

# Expose metrics endpoint
@app.get("/metrics")
async def metrics_endpoint():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(get_metrics().export())
```

### 9. Extended Health Checks

Comprehensive health monitoring with dependency checks.

```python
from app.production.health_extended import get_health_checker, configure_health_checks

# Configure on startup
checker = configure_health_checks(
    supabase_url=settings.SUPABASE_URL,
    supabase_key=settings.SUPABASE_ANON_KEY,
    version="1.0.0"
)

# Health endpoints
@app.get("/health/live")
async def liveness():
    return await checker.check_liveness()

@app.get("/health/ready")
async def readiness():
    result = await checker.check_readiness()
    status_code = 200 if result["ready"] else 503
    return JSONResponse(content=result, status_code=status_code)

@app.get("/health/detailed")
async def detailed_health():
    report = await checker.check_health()
    return report.to_dict()
```

### 10. Response Envelope

Consistent API response formatting.

```python
from app.production.response_envelope import (
    success_response,
    error_response,
    paginated_response,
    not_found_response,
    APIError
)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await find_user(user_id)
    if not user:
        return not_found_response("User", user_id)
    return success_response(data=user)

@app.get("/users")
async def list_users(page: int = 1, limit: int = 20):
    users, total = await get_users_paginated(page, limit)
    return paginated_response(data=users, page=page, limit=limit, total=total)

# Raise structured errors
raise APIError(
    status_code=400,
    code="INVALID_EMAIL",
    message="Email format is invalid",
    details={"field": "email"}
)
```

### 11. Connection Pooling

Efficient HTTP client management.

```python
from app.production.connection_pool import (
    get_http_client,
    create_supabase_client,
    create_ai_service_client,
    close_all_clients
)

# Get pooled client
client = await get_http_client("default")
response = await client.get("https://api.example.com")

# Pre-configured clients
supabase = create_supabase_client(
    base_url=settings.SUPABASE_URL,
    api_key=settings.SUPABASE_ANON_KEY,
    service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY
)

ai_client = create_ai_service_client(
    base_url="https://api.deepseek.com",
    api_key=settings.DEEPSEEK_API_KEY,
    timeout=120.0
)

# Close all clients on shutdown
@app.on_event("shutdown")
async def shutdown():
    await close_all_clients()
```

### 12. Graceful Shutdown

Clean shutdown with request draining.

```python
from app.production.graceful_shutdown import GracefulShutdown, GracefulShutdownMiddleware

shutdown_handler = GracefulShutdown()

# Add middleware
app.add_middleware(GracefulShutdownMiddleware, handler=shutdown_handler)

# Register cleanup callbacks
shutdown_handler.register_cleanup(db_pool.close, priority=10)
shutdown_handler.register_cleanup(redis_client.close, priority=20)
shutdown_handler.register_cleanup(close_all_clients, priority=30)

# Startup/shutdown hooks
@app.on_event("startup")
async def startup():
    await shutdown_handler.startup()

@app.on_event("shutdown")
async def shutdown():
    await shutdown_handler.shutdown()
```

## Database Indexes

Apply production indexes for optimal query performance:

```bash
# Connect to your Supabase/PostgreSQL database and run:
psql -d your_database -f database/migrations/production_indexes.sql
```

## Frontend Integration

### Error Boundary

Wrap components with error boundaries:

```tsx
import { ErrorBoundary, PageErrorFallback } from '@/components/production';

// In your layout or page
export default function Layout({ children }) {
  return (
    <ErrorBoundary fallback={<PageErrorFallback />}>
      {children}
    </ErrorBoundary>
  );
}

// Or use the HOC
import { withErrorBoundary } from '@/components/production';

export default withErrorBoundary(MyComponent);
```

## Environment Variables

Ensure these are set in production:

```env
# Required
JWT_SECRET_KEY=<secure-random-64-char-string>
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Recommended
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
REDIS_URL=redis://localhost:6379  # Optional, for distributed caching

# Rate limiting (optional overrides)
RATE_LIMIT_RPM=60
RATE_LIMIT_BURST=10
```

## Monitoring Checklist

After integration, verify:

1. [ ] `/health/live` returns 200
2. [ ] `/health/ready` returns 200 with all checks passing
3. [ ] `/metrics` returns Prometheus-formatted metrics
4. [ ] Rate limiting is active (test with rapid requests)
5. [ ] Security headers present in responses (check with browser dev tools)
6. [ ] Request IDs appear in logs and response headers
7. [ ] Database queries use indexes (check query plans)

## Performance Tuning

Adjust these settings based on your load:

```python
# For high traffic (1000+ RPM)
RateLimitConfig(
    default_requests_per_minute=120,
    burst_size=20,
    auth_limit=20,
)

# For connection pooling under load
HttpClientConfig(
    max_connections=200,
    max_keepalive_connections=50,
)

# For caching
CacheConfig(
    default_ttl=1800,  # 30 minutes
    max_memory_entries=50000,
)
```
