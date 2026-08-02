"""
Main API Router
Combines all API endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, websites, payments, templates, delivery, delivery_zones, menu_delivery, chat, subscription, scheduled_tasks, email_support, moderation, template_gallery, disputes, customers, penghantar_live, analytics, issue_reports, design_studio, site_qr
from app.api.admin import repair as admin_repair
from app.api.admin import make_good as admin_make_good
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
# Merchant analytics (Analitik tab). Full paths are /api/v1/analytics/* —
# a prefix subscription_check_middleware already lock-protects. Ownership
# and per-tier history clamping are enforced inside the router.
api_router.include_router(analytics.router, tags=["Analytics"])
# Admin: structural repair of stored HTML (Item 5 follow-up). Endpoint
# enforces role='admin' internally — mounted under the v1 prefix so the
# full path is POST /api/v1/admin/repair-websites.
api_router.include_router(admin_repair.router, tags=["Admin: Repair"])
# Admin: guarded make-good rewrite (regenerate product-card images with
# business context + strip biased food icons; quota is never charged).
# Full path is POST /api/v1/admin/make-good-regen.
api_router.include_router(admin_make_good.router, tags=["Admin: Make-good"])
# Admin: manual escape hatch for websites stuck on status='generating'.
# Path is POST /api/v1/admin/websites/{id}/unstick-generation. The
# scheduled sweeper in core/scheduler.py handles the common case
# automatically; this endpoint is for the long tail.
api_router.include_router(admin_unstick.router, tags=["Admin: Unstick"])
# Report Issue → Free Regeneration (flag-gated: ISSUE_REPORT_ENABLED).
# User endpoint shares the /websites prefix (POST /websites/{id}/report-issue);
# admin endpoints live at /admin/issue-reports. With the flag off, every
# route in both routers returns 404.
api_router.include_router(issue_reports.router, prefix="/websites", tags=["Issue Reports"])
api_router.include_router(issue_reports.admin_router, tags=["Admin: Issue Reports"])
# Design Studio — credit-free palette/typography control. Shares the /websites
# prefix (GET /websites/design/options, PATCH /websites/{id}/theme). None of
# its paths collide with the routes above: /{website_id} only ever matches a
# single segment, and no existing two-segment route ends in /theme.
api_router.include_router(design_studio.router, prefix="/websites", tags=["Design Studio"])
# QR toolkit — offline QR codes and printable posters for a published site.
api_router.include_router(site_qr.router, prefix="/websites", tags=["QR Toolkit"])
