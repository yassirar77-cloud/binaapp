"""
Main API Router
Combines all API endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, websites, payments, templates

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(websites.router, prefix="/websites", tags=["Websites"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
