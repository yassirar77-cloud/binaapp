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

# Setup logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting BinaApp API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: v1")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down BinaApp API...")

# Create FastAPI application
app = FastAPI(
    title="BinaApp API",
    description="AI-Powered No-Code Website Builder for Malaysian SMEs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request Timing Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.ENVIRONMENT == "development" else "An error occurred"
        }
    )

# Health Check Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "BinaApp API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to BinaApp API",
        "description": "AI-Powered No-Code Website Builder for Malaysian SMEs",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

# Include API Routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(simple_router, prefix="/api")  # Simple API without auth
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(menu_designer.router, prefix="/api", tags=["menu"])
app.include_router(server.router, prefix="/api", tags=["projects"])  # NEW LINE

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )