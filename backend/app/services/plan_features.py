"""
Plan-feature lookup for subscription gating.

Reads subscription_plans.features (JSONB) for a user's active subscription.
Source of truth: the database — not the hardcoded TIER_LIMITS in
subscription_service.py.

If the lookup fails for any reason (network, missing row, etc.) we FAIL CLOSED:
the requested feature is denied. This matches the existing limit-check
behaviour in main.py:/api/publish.
"""

import os
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from app.core.config import settings


_SVC_HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


async def get_plan_features(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Return the user's active subscription_plans.features dict, or None on
    error. The dict may be empty for legacy plans that haven't been backfilled.
    """
    try:
        url = f"{settings.SUPABASE_URL}/rest/v1/subscriptions"
        params = {
            "user_id": f"eq.{user_id}",
            "status": "eq.active",
            "select": "tier,plan_id,subscription_plans(plan_name,features)",
            "order": "current_period_end.desc.nullslast,end_date.desc.nullslast",
            "limit": "1",
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=_SVC_HEADERS, params=params)
        if resp.status_code != 200:
            logger.warning(f"[plan_features] non-200 for user {user_id}: {resp.status_code}")
            return None
        rows = resp.json()
        if not rows:
            return None
        sp = rows[0].get("subscription_plans") or {}
        return sp.get("features") or {}
    except Exception as e:
        logger.error(f"[plan_features] lookup failed for {user_id}: {e}")
        return None


async def _is_admin_user(user_id: str) -> bool:
    """Check public.users.role == 'admin'. Fails closed (False) on error."""
    try:
        url = f"{settings.SUPABASE_URL}/rest/v1/users"
        params = {"id": f"eq.{user_id}", "select": "role", "limit": "1"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=_SVC_HEADERS, params=params)
        if resp.status_code == 200:
            rows = resp.json()
            return bool(rows) and rows[0].get("role") == "admin"
    except Exception as e:
        logger.warning(f"[plan_features] admin check failed for {user_id}: {e}")
    return False


async def can_publish_subdomain(user_id: str) -> bool:
    """
    True if the user's plan permits publishing to *.binaapp.my.
    Admin (founder) accounts always pass.
    Fails closed — returns False on any error.
    """
    if await _is_admin_user(user_id):
        return True
    features = await get_plan_features(user_id)
    if features is None:
        return False
    return bool(features.get("can_publish_subdomain", False))


#: Either key unlocks the hero video background; ``can_use_hero_video`` is
#: the canonical one, the second is accepted so a plan row written with the
#: descriptive name still works.
HERO_VIDEO_FEATURE_KEYS = ("can_use_hero_video", "can_use_video_background")


def hero_video_open_to_all_plans() -> bool:
    """HERO_VIDEO_ALLOW_ALL_PLANS=true skips the plan check (launch/testing).
    The HERO_VIDEO_ENABLED master flag still applies."""
    return os.getenv("HERO_VIDEO_ALLOW_ALL_PLANS", "false").strip().lower() in (
        "1", "true", "yes", "on",
    )


async def can_use_hero_video(user_id: str) -> bool:
    """
    True if the user's plan permits generating a hero video background.
    Admin (founder) accounts always pass; HERO_VIDEO_ALLOW_ALL_PLANS opens it
    to every active plan. Otherwise fails closed like can_publish_subdomain.
    """
    if await _is_admin_user(user_id):
        return True
    if hero_video_open_to_all_plans():
        return True
    features = await get_plan_features(user_id)
    if features is None:
        return False
    return any(bool(features.get(key, False)) for key in HERO_VIDEO_FEATURE_KEYS)


# ---------------------------------------------------------------------------
# Hero video: paid per clip
# ---------------------------------------------------------------------------

#: addon_purchases.addon_type for one hero video clip (migration 008).
HERO_VIDEO_ADDON_TYPE = "hero_video"
#: Shown in the UI; the charge itself is one addon credit.
HERO_VIDEO_PRICE_RM = 5.0

#: Add-ons that only make sense on a plan that can publish to a subdomain.
#: The Free plan is preview-only, so an extra website slot or a hero video
#: clip bought there can never be used — refuse the sale and point at the
#: Starter upgrade instead (a founder paid RM5 for a slot on a Free account
#: and read it as the RM5/month plan).
PAID_PLAN_ADDONS = ("website", HERO_VIDEO_ADDON_TYPE)
PAID_PLAN_ADDON_MESSAGE = (
    "Addon ini memerlukan pelan berbayar. Pelan Percuma hanya untuk pratonton — "
    "naik taraf ke Starter (RM5/bulan) dahulu untuk terbit laman web anda."
)


async def addon_requires_paid_plan(user_id: str, addon_type: str) -> bool:
    """True when ``addon_type`` is a paid-plan add-on and this user's plan
    cannot publish (Free / no active plan). Admin accounts never trip it."""
    if addon_type not in PAID_PLAN_ADDONS:
        return False
    return not await can_publish_subdomain(user_id)


async def hero_video_access(user_id: str) -> Dict[str, Any]:
    """How this user may generate a hero video.

    ``free``   — admin, HERO_VIDEO_ALLOW_ALL_PLANS, or a plan feature: no
                 credit is consumed.
    ``credits`` — prepaid hero_video add-on credits available.
    ``allowed`` — free or at least one credit.
    """
    free = await can_use_hero_video(user_id)
    credits = 0
    requires_upgrade = False
    if not free:
        # Preview-only plans cannot buy a clip; existing credits stay usable.
        requires_upgrade = not await can_publish_subdomain(user_id)
        try:
            from app.services.subscription_service import subscription_service

            available = await subscription_service.get_available_addon_credits(
                user_id, HERO_VIDEO_ADDON_TYPE
            )
            credits = int(available.get(HERO_VIDEO_ADDON_TYPE, 0) or 0)
        except Exception as exc:  # fail closed: no credit, no clip
            logger.warning(f"[plan_features] hero video credit lookup failed for {user_id}: {exc}")
            credits = 0
    return {
        "free": free,
        "credits": credits,
        "allowed": free or credits > 0,
        "price_rm": HERO_VIDEO_PRICE_RM,
        "addon_type": HERO_VIDEO_ADDON_TYPE,
        # Free plan: no purchase offered — upgrade to Starter first.
        "requires_upgrade": requires_upgrade,
    }

