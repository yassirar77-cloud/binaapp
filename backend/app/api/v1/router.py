"""
Main API Router
Combines all API endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, websites, payments, templates, delivery, delivery_zones, menu_delivery, chat, subscription, scheduled_tasks, email_support, moderation, template_gallery, disputes, customers, penghantar_live
from app.api.admin import repair as admin_repair
from app.api.admin import unstick_generation as admin_unstick

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(websites.router, prefix="/websites", tags=["Websites"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(templates.router, prefix="/templates", tags=["Templates"])
api_router.include_router(delivery.router, tags=["Delivery System"])
api_router.include_router(delivery_zones.router, tags=["Delivery Zones (Owner)"])
api_router.include_router(penghantar_live.router, tags=["Penghantar Live (Owner)"])
api_router.include_router(menu_delivery.router, prefix="/menu", tags=["Menu Management"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat System"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["Subscription Management"])
api_router.include_router(scheduled_tasks.router, prefix="/tasks", tags=["Scheduled Tasks"])
api_router.include_router(email_support.router, prefix="/email", tags=["AI Email Support"])
api_router.include_router(moderation.router, tags=["Image Moderation"])
api_router.include_router(template_gallery.router, prefix="/templates", tags=["Template Gallery"])
api_router.include_router(disputes.router, tags=["Dispute Resolution"])
api_router.include_router(customers.router, tags=["Customer Lookup"])
# Admin: structural repair of stored HTML (Item 5 follow-up). Endpoint
# enforces role='admin' internally — mounted under the v1 prefix so the
# full path is POST /api/v1/admin/repair-websites.
api_router.include_router(admin_repair.router, tags=["Admin: Repair"])
# Admin: manual escape hatch for websites stuck on status='generating'.
# Path is POST /api/v1/admin/websites/{id}/unstick-generation. The
# scheduled sweeper in core/scheduler.py handles the common case
# automatically; this endpoint is for the long tail.
api_router.include_router(admin_unstick.router, tags=["Admin: Unstick"])
