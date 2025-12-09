"""
Simple API Router
Combines all simple API endpoints
"""

from fastapi import APIRouter

from app.api.simple import generate, publish, projects, screenshot

# Create main router
simple_router = APIRouter()

# Include all endpoint routers
simple_router.include_router(generate.router, tags=["Simple API"])
simple_router.include_router(publish.router, tags=["Simple API"])
simple_router.include_router(projects.router, prefix="/projects", tags=["Simple API"])
simple_router.include_router(screenshot.router, prefix="/screenshot", tags=["Screenshots"])
