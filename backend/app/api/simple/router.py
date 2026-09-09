"""
Simple API Router
Combines all simple API endpoints
"""

from fastapi import APIRouter

# NOTE: app/api/simple/generate.py was deleted — it defined a second,
# never-mounted /api/generate/start. The live one is in app/main.py.
from app.api.simple import publish, projects, screenshot

# Create main router
simple_router = APIRouter()

# Include all endpoint routers
simple_router.include_router(publish.router, tags=["Simple API"])
simple_router.include_router(projects.router, prefix="/projects", tags=["Simple API"])
simple_router.include_router(screenshot.router, prefix="/screenshot", tags=["Screenshots"])
