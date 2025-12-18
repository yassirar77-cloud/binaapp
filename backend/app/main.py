"""
BinaApp - AI-Powered No-Code Website Builder
Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import time

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.router import api_router
from app.api.simple.router import simple_router
from app.api import upload, menu_designer, server
from app.api.routes.preview import router as preview_router
from app.middleware.subdomain import subdomain_middleware

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logging()

# -------------------------------------------------------------------
# Lifespan
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 80)
    logger.info("🚀 Starting BinaApp API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Frontend URL: {settings.FRONTEND_URL}")
    logger.info("API Version: v1")
    logger.info("=" * 80)

    # Validate critical environment variables
    logger.info("Checking environment variables...")
    env_checks = {
        "QWEN_API_KEY": bool(settings.QWEN_API_KEY),
        "DEEPSEEK_API_KEY": bool(settings.DEEPSEEK_API_KEY),
        "SUPABASE_URL": bool(settings.SUPABASE_URL),
        "SUPABASE_ANON_KEY": bool(settings.SUPABASE_ANON_KEY),
        "JWT_SECRET_KEY": bool(settings.JWT_SECRET_KEY),
    }

    for key, is_set in env_checks.items():
        status = "✓ SET" if is_set else "✗ MISSING"
        logger.info(f"  {key}: {status}")

    missing = [k for k, v in env_checks.items() if not v]
    if missing:
        logger.warning(f"⚠️  Missing environment variables: {', '.join(missing)}")
    else:
        logger.info("✓ All critical environment variables are set")

    logger.info("=" * 80)
    yield
    logger.info("👋 Shutting down BinaApp API...")

# -------------------------------------------------------------------
# App
# -------------------------------------------------------------------
app = FastAPI(
    title="BinaApp API",
    description="AI-Powered No-Code Website Builder for Malaysian SMEs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# -------------------------------------------------------------------
# CORS (CRITICAL – FIXES FAILED TO FETCH)
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://binaapp.my",
        "https://www.binaapp.my",
        "https://binaapp.vercel.app",
        "https://binaapp-backend.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# GZip
# -------------------------------------------------------------------
app.add_middleware(GZipMiddleware, minimum_size=1000)

# -------------------------------------------------------------------
# Subdomain routing (for sitename.binaapp.my)
# -------------------------------------------------------------------
app.middleware("http")(subdomain_middleware)

# -------------------------------------------------------------------
# Request timing
# -------------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start_time)
    return response

# -------------------------------------------------------------------
# Global error handler
# -------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.ENVIRONMENT == "development" else "An error occurred"
        },
    )

# -------------------------------------------------------------------
# Health & Root
# -------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "BinaApp API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to BinaApp API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }

# -------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------
app.include_router(api_router, prefix="/api/v1")
app.include_router(simple_router, prefix="/api")
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(menu_designer.router, prefix="/api", tags=["menu"])
app.include_router(server.router, prefix="/api", tags=["projects"])
app.include_router(preview_router, prefix="/api")

# -------------------------------------------------------------------
# Local run
# -------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )