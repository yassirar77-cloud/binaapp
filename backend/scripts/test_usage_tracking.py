"""
Smoke test for the usage_tracking upsert (Bug 4 fix).

Runs get_or_create_usage_tracking against the live Supabase instance using
credentials from the environment and confirms the upsert returns a populated
row (no 23502 NOT NULL violations).

Usage:
    export SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...
    python backend/scripts/test_usage_tracking.py <user_id>

Default user_id is the one seen in the prod 23502 log; override via CLI arg.
"""

import asyncio
import sys

from app.services.subscription_service import SubscriptionService


DEFAULT_USER_ID = "1b046432-d9a4-4bbc-a999-be62a31b1ab6"


async def main() -> int:
    user_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USER_ID
    service = SubscriptionService()
    print(f"[test] calling get_or_create_usage_tracking user_id={user_id}")
    result = await service.get_or_create_usage_tracking(user_id)
    print(f"[test] got record with keys: {sorted(result.keys())}")

    required = [
        "user_id",
        "billing_period",
        "websites_count",
        "menu_items_count",
        "ai_hero_used",
        "ai_images_used",
        "delivery_zones_count",
        "riders_count",
    ]
    missing = [k for k in required if k not in result]
    if missing:
        print(f"[test] FAIL — missing keys: {missing}")
        return 1

    print(f"[test] PASS — billing_period={result.get('billing_period')} "
          f"websites={result.get('websites_count')} menu={result.get('menu_items_count')}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
