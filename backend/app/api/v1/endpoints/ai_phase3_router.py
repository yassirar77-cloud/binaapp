"""
AI Control System Phase 3 - Self-contained router setup.

TO ACTIVATE: Add these 2 lines to main.py:
    from app.api.v1.endpoints.ai_phase3_router import setup_phase3_routes
    setup_phase3_routes(app)
"""

from fastapi import FastAPI
from app.api.v1.endpoints import (
    sla, referrals, ai_chat_settings, order_verification,
    notifications, website_rebuild, founder_dashboard,
    restaurant_penalties, trust_score, webhooks
)


def setup_phase3_routes(app: FastAPI):
    """Register all Phase 3 routes with the FastAPI app."""
    app.include_router(sla.router, prefix="/api/v1", tags=["sla"])
    app.include_router(referrals.router, prefix="/api/v1", tags=["referrals"])
    app.include_router(ai_chat_settings.router, prefix="/api/v1", tags=["ai-chat-settings"])
    app.include_router(order_verification.router, prefix="/api/v1", tags=["order-verification"])
    app.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])
    app.include_router(website_rebuild.router, prefix="/api/v1", tags=["website-rebuild"])
    app.include_router(founder_dashboard.router, prefix="/api/v1", tags=["founder"])
    app.include_router(restaurant_penalties.router, prefix="/api/v1", tags=["penalties"])
    app.include_router(trust_score.router, prefix="/api/v1", tags=["trust-score"])
    app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])
    print("[AI Phase 3] All 10 Phase 3 routes registered")
