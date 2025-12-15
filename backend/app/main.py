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

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logging()

# -------------------------------------------------------------------
# Lifespan
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting BinaApp API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("API Version: v1")
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