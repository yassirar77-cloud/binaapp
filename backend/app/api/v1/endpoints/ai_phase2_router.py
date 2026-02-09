"""
AI Control System Phase 2 - Self-contained router setup.

TO ACTIVATE: Add these 2 lines to main.py (AFTER Phase 1 activation):
    from app.api.v1.endpoints.ai_phase2_router import setup_phase2_routes
    setup_phase2_routes(app)

That's it. No other changes needed.
"""

from fastapi import FastAPI
from app.api.v1.endpoints import website_health, monitor, ai_chat, admin_dashboard


def setup_phase2_routes(app: FastAPI):
    """Register all Phase 2 routes. Call this from main.py."""
    app.include_router(website_health.router, prefix="/api/v1", tags=["website-health"])
    app.include_router(monitor.router, prefix="/api/v1", tags=["monitor"])
    app.include_router(ai_chat.router, prefix="/api/v1", tags=["ai-chat"])
    app.include_router(admin_dashboard.router, prefix="/api/v1", tags=["admin"])
    print("[AI Phase 2] Website Health, Monitor, AI Chat, Admin routes registered")
