"""
Plan-feature lookup for subscription gating.

Reads subscription_plans.features (JSONB) for a user's active subscription.
Source of truth: the database — not the hardcoded TIER_LIMITS in
subscription_service.py.

If the lookup fails for any reason (network, missing row, etc.) we FAIL CLOSED:
the requested feature is denied. This matches the existing limit-check
behaviour in main.py:/api/publish.
"""

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
            "order": "created_at.desc",
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


async def can_publish_subdomain(user_id: str) -> bool:
    """
    True if the user's plan permits publishing to *.binaapp.my.
    Fails closed — returns False on any error.
    """
    features = await get_plan_features(user_id)
    if features is None:
        return False
    return bool(features.get("can_publish_subdomain", False))
