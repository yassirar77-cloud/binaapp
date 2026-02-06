"""
Subscription Management Service
Handles subscription status, usage tracking, limits, and addons
"""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
from app.core.config import settings
import secrets


class SubscriptionService:
    """Service for managing subscriptions, usage tracking, and limits"""

    # Subscription tier pricing (RM)
    TIER_PRICES = {
        "starter": 5.00,
        "basic": 29.00,
        "pro": 49.00
    }

    # Addon pricing (RM)
    ADDON_PRICES = {
        "ai_image": 1.00,
        "ai_hero": 2.00,
        "website": 5.00,
        "rider": 3.00,
        "zone": 2.00
    }

    # Tier limits
    TIER_LIMITS = {
        "starter": {
            "websites_limit": 1,
            "menu_items_limit": 20,
            "ai_hero_limit": 1,
            "ai_images_limit": 5,
            "delivery_zones_limit": 1,
            "riders_limit": 0
        },
        "basic": {
            "websites_limit": 5,
            "menu_items_limit": None,  # Unlimited
            "ai_hero_limit": 10,
            "ai_images_limit": 30,
            "delivery_zones_limit": 5,
            "riders_limit": 0
        },
        "pro": {
            "websites_limit": None,  # Unlimited
            "menu_items_limit": None,
            "ai_hero_limit": None,
            "ai_images_limit": None,
            "delivery_zones_limit": None,
            "riders_limit": 10
        }
    }

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }

    def get_current_billing_period(self) -> str:
        """Get current billing period in YYYY-MM format"""
        return datetime.now().strftime("%Y-%m")

    async def generate_invoice_number(self) -> str:
        """
        Generate an invoice number in format: INV-YYYYMMDD-XXXX

        Prefers the DB function `generate_invoice_number()` if available.
        Falls back to a local generator if RPC is unavailable.
        """
        # 1) Try Supabase RPC (if migration created the function)
        try:
            url = f"{self.url}/rest/v1/rpc/generate_invoice_number"
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=self.headers, json={})
            if resp.status_code == 200:
                data = resp.json()
                # Supabase may return a scalar JSON string, e.g. "INV-20260125-0001"
                if isinstance(data, str) and data.startswith("INV-"):
                    return data
        except Exception as e:
            logger.debug(f"Invoice RPC generation failed, using fallback: {e}")

        # 2) Fallback (best-effort uniqueness)
        date_part = datetime.utcnow().strftime("%Y%m%d")
        suffix = secrets.randbelow(10000)
        return f"INV-{date_part}-{suffix:04d}"

    async def get_subscription_plans(self) -> List[Dict[str, Any]]:
        """Get all active subscription plans"""
        try:
            url = f"{self.url}/rest/v1/subscription_plans"
            params = {"is_active": "eq.true", "order": "sort_order.asc"}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                return response.json()

            # Fallback to hardcoded plans
            return [
                {
                    "plan_name": "starter",
                    "display_name": "Starter",
                    "price": 5.00,
                    **self.TIER_LIMITS["starter"]
                },
                {
                    "plan_name": "basic",
                    "display_name": "Basic",
                    "price": 29.00,
                    **self.TIER_LIMITS["basic"]
                },
                {
                    "plan_name": "pro",
                    "display_name": "Pro",
                    "price": 49.00,
                    **self.TIER_LIMITS["pro"]
                }
            ]
        except Exception as e:
            logger.error(f"Error getting subscription plans: {e}")
            return []

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current subscription"""
        try:
            url = f"{self.url}/rest/v1/subscriptions"
            params = {"user_id": f"eq.{user_id}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                records = response.json()
                if records:
                    sub = records[0]
                    # Check if expired
                    if sub.get("end_date"):
                        end_date = datetime.fromisoformat(sub["end_date"].replace("Z", "+00:00"))
                        if end_date < datetime.now(end_date.tzinfo):
                            sub["status"] = "expired"
                    return sub
            return None
        except Exception as e:
            logger.error(f"Error getting user subscription: {e}")
            return None

    async def get_subscription_status(self, user_id: str) -> Dict[str, Any]:
        """Get detailed subscription status for a user"""
        subscription = await self.get_user_subscription(user_id)

        if not subscription:
            return {
                "plan_name": "starter",
                "status": "active",
                "start_date": None,
                "end_date": None,
                "days_remaining": 30,
                "auto_renew": True,
                "is_expired": False
            }

        # Calculate days remaining
        days_remaining = 0
        is_expired = False
        if subscription.get("end_date"):
            end_date = datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
            now = datetime.now(end_date.tzinfo)
            days_remaining = max(0, (end_date - now).days)
            is_expired = end_date < now

        return {
            "plan_name": subscription.get("tier", "starter"),
            "status": "expired" if is_expired else subscription.get("status", "active"),
            "start_date": subscription.get("start_date"),
            "end_date": subscription.get("end_date"),
            "days_remaining": days_remaining,
            "auto_renew": subscription.get("auto_renew", True),
            "is_expired": is_expired
        }

    async def get_user_limits(self, user_id: str) -> Dict[str, Any]:
        """Get user's subscription limits"""
        subscription = await self.get_user_subscription(user_id)
        tier = subscription.get("tier", "starter") if subscription else "starter"
        return self.TIER_LIMITS.get(tier, self.TIER_LIMITS["starter"])

    async def get_actual_resource_counts(self, user_id: str) -> Dict[str, int]:
        """
        Count actual persistent resources from their respective tables.
        This ensures we always have accurate counts regardless of billing period.
        """
        counts = {
            "websites_count": 0,
            "menu_items_count": 0,
            "delivery_zones_count": 0,
            "riders_count": 0
        }

        try:
            async with httpx.AsyncClient() as client:
                # Count websites
                response = await client.get(
                    f"{self.url}/rest/v1/websites",
                    headers={**self.headers, "Prefer": "count=exact"},
                    params={"user_id": f"eq.{user_id}", "select": "id"}
                )
                if response.status_code == 200:
                    count_header = response.headers.get("content-range", "")
                    if "/" in count_header:
                        counts["websites_count"] = int(count_header.split("/")[1])
                    else:
                        counts["websites_count"] = len(response.json())

                # Count menu items, delivery zones, and riders across all user's websites
                # First get user's website IDs
                websites_response = await client.get(
                    f"{self.url}/rest/v1/websites",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "id"}
                )
                if websites_response.status_code == 200:
                    website_ids = [w["id"] for w in websites_response.json()]
                    if website_ids:
                        # Count menu items for these websites
                        menu_response = await client.get(
                            f"{self.url}/rest/v1/menu_items",
                            headers={**self.headers, "Prefer": "count=exact"},
                            params={"website_id": f"in.({','.join(website_ids)})", "select": "id"}
                        )
                        if menu_response.status_code == 200:
                            count_header = menu_response.headers.get("content-range", "")
                            if "/" in count_header:
                                counts["menu_items_count"] = int(count_header.split("/")[1])
                            else:
                                counts["menu_items_count"] = len(menu_response.json())

                        # Count delivery zones for these websites
                        zones_response = await client.get(
                            f"{self.url}/rest/v1/delivery_zones",
                            headers={**self.headers, "Prefer": "count=exact"},
                            params={"website_id": f"in.({','.join(website_ids)})", "select": "id"}
                        )
                        if zones_response.status_code == 200:
                            count_header = zones_response.headers.get("content-range", "")
                            if "/" in count_header:
                                counts["delivery_zones_count"] = int(count_header.split("/")[1])
                            else:
                                counts["delivery_zones_count"] = len(zones_response.json())

                        # Count riders for these websites (riders linked via website_id, not user_id)
                        riders_response = await client.get(
                            f"{self.url}/rest/v1/riders",
                            headers={**self.headers, "Prefer": "count=exact"},
                            params={"website_id": f"in.({','.join(website_ids)})", "select": "id"}
                        )
                        if riders_response.status_code == 200:
                            count_header = riders_response.headers.get("content-range", "")
                            if "/" in count_header:
                                counts["riders_count"] = int(count_header.split("/")[1])
                            else:
                                counts["riders_count"] = len(riders_response.json())

        except Exception as e:
            logger.error(f"Error counting actual resources for user {user_id}: {e}")

        logger.info(f"📊 Actual resource counts for user {user_id}: {counts}")
        return counts

    async def get_or_create_usage_tracking(self, user_id: str) -> Dict[str, Any]:
        """Get or create usage tracking for current billing period"""
        billing_period = self.get_current_billing_period()

        try:
            # Try to get existing record
            url = f"{self.url}/rest/v1/usage_tracking"
            params = {
                "user_id": f"eq.{user_id}",
                "billing_period": f"eq.{billing_period}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

            existing_record = None
            if response.status_code == 200:
                records = response.json()
                if records:
                    existing_record = records[0]

            # IMPORTANT: Always get actual counts for persistent resources
            # This ensures limits are enforced correctly even if usage_tracking is stale
            actual_counts = await self.get_actual_resource_counts(user_id)

            if existing_record:
                # Update with actual counts for persistent resources
                # Keep AI usage from the tracking table (those reset each billing period)
                existing_record["websites_count"] = actual_counts["websites_count"]
                existing_record["menu_items_count"] = actual_counts["menu_items_count"]
                existing_record["delivery_zones_count"] = actual_counts["delivery_zones_count"]
                existing_record["riders_count"] = actual_counts["riders_count"]
                return existing_record

            # Create new record with actual counts
            # Note: usage_tracking table only has: usage_id, user_id, billing_period,
            # websites_count, menu_items_count, ai_hero_used, ai_images_used
            # delivery_zones_count and riders_count are NOT columns in this table
            usage_data = {
                "user_id": user_id,
                "billing_period": billing_period,
                "websites_count": actual_counts["websites_count"],
                "menu_items_count": actual_counts["menu_items_count"],
                "ai_hero_used": 0,
                "ai_images_used": 0
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=usage_data
                )

            if response.status_code in [200, 201]:
                records = response.json()
                result = records[0] if records else usage_data
            else:
                result = usage_data

            # Add computed counts that aren't in the DB table but are needed by callers
            result["delivery_zones_count"] = actual_counts["delivery_zones_count"]
            result["riders_count"] = actual_counts["riders_count"]
            return result

        except Exception as e:
            logger.error(f"Error getting usage tracking: {e}")
            # On error, still try to get actual counts
            try:
                actual_counts = await self.get_actual_resource_counts(user_id)
                return {
                    "websites_count": actual_counts["websites_count"],
                    "menu_items_count": actual_counts["menu_items_count"],
                    "ai_hero_used": 0,
                    "ai_images_used": 0,
                    "delivery_zones_count": actual_counts["delivery_zones_count"],
                    "riders_count": actual_counts["riders_count"]
                }
            except:
                return {
                    "websites_count": 0,
                    "menu_items_count": 0,
                    "ai_hero_used": 0,
                    "ai_images_used": 0,
                    "delivery_zones_count": 0,
                    "riders_count": 0
                }

    async def get_usage_with_limits(self, user_id: str) -> Dict[str, Any]:
        """Get user's usage alongside their limits"""
        subscription_status = await self.get_subscription_status(user_id)
        limits = await self.get_user_limits(user_id)
        usage = await self.get_or_create_usage_tracking(user_id)
        addons = await self.get_available_addon_credits(user_id)

        def calc_usage(used: int, limit: Optional[int], addon_credits: int = 0) -> Dict[str, Any]:
            if limit is None:
                return {"used": used, "limit": None, "percentage": 0, "unlimited": True, "addon_credits": addon_credits}
            total_available = limit + addon_credits
            percentage = min(100, int((used / total_available) * 100)) if total_available > 0 else 0
            return {"used": used, "limit": limit, "percentage": percentage, "unlimited": False, "addon_credits": addon_credits}

        return {
            "plan": {
                "name": subscription_status["plan_name"],
                "status": subscription_status["status"],
                "days_remaining": subscription_status["days_remaining"],
                "end_date": subscription_status["end_date"],
                "is_expired": subscription_status["is_expired"]
            },
            "usage": {
                "websites": calc_usage(
                    usage.get("websites_count", 0),
                    limits.get("websites_limit"),
                    addons.get("website", 0)
                ),
                "menu_items": calc_usage(
                    usage.get("menu_items_count", 0),
                    limits.get("menu_items_limit")
                ),
                "ai_hero": calc_usage(
                    usage.get("ai_hero_used", 0),
                    limits.get("ai_hero_limit"),
                    addons.get("ai_hero", 0)
                ),
                "ai_images": calc_usage(
                    usage.get("ai_images_used", 0),
                    limits.get("ai_images_limit"),
                    addons.get("ai_image", 0)
                ),
                "delivery_zones": calc_usage(
                    usage.get("delivery_zones_count", 0),
                    limits.get("delivery_zones_limit"),
                    addons.get("zone", 0)
                ),
                "riders": calc_usage(
                    usage.get("riders_count", 0),
                    limits.get("riders_limit"),
                    addons.get("rider", 0)
                )
            },
            "addon_prices": self.ADDON_PRICES
        }

    async def check_limit(self, user_id: str, action: str) -> Dict[str, Any]:
        """
        Check if user can perform a specific action based on their limits

        Actions: 'create_website', 'add_menu_item', 'generate_ai_hero',
                 'generate_ai_image', 'add_zone', 'add_rider'
        """
        limits = await self.get_user_limits(user_id)
        usage = await self.get_or_create_usage_tracking(user_id)
        subscription_status = await self.get_subscription_status(user_id)

        # Check if subscription is expired
        if subscription_status.get("is_expired"):
            return {
                "allowed": False,
                "current_usage": 0,
                "limit": 0,
                "can_buy_addon": False,
                "addon_price": None,
                "message": "Langganan anda telah tamat. Sila perbaharui untuk meneruskan.",
                "requires_renewal": True
            }

        # Map action to usage and limit fields
        action_mapping = {
            "create_website": ("websites_count", "websites_limit", "website"),
            "add_menu_item": ("menu_items_count", "menu_items_limit", None),
            "generate_ai_hero": ("ai_hero_used", "ai_hero_limit", "ai_hero"),
            "generate_ai_image": ("ai_images_used", "ai_images_limit", "ai_image"),
            "add_zone": ("delivery_zones_count", "delivery_zones_limit", "zone"),
            "add_rider": ("riders_count", "riders_limit", "rider")
        }

        if action not in action_mapping:
            return {
                "allowed": False,
                "message": f"Tindakan tidak dikenali: {action}"
            }

        usage_field, limit_field, addon_type = action_mapping[action]
        current = usage.get(usage_field, 0)
        limit = limits.get(limit_field)

        # Check for unlimited
        if limit is None:
            return {
                "allowed": True,
                "current_usage": current,
                "limit": None,
                "unlimited": True,
                "message": "Tiada had"
            }

        # Check if within limit
        if current < limit:
            return {
                "allowed": True,
                "current_usage": current,
                "limit": limit,
                "remaining": limit - current,
                "message": f"Dalam had ({current}/{limit})"
            }

        # Check for addon credits
        if addon_type:
            addon_credits = await self.get_available_addon_credits(user_id, addon_type)
            addon_count = addon_credits.get(addon_type, 0)

            if addon_count > 0:
                return {
                    "allowed": True,
                    "current_usage": current,
                    "limit": limit,
                    "using_addon": True,
                    "addon_credits": addon_count,
                    "message": f"Menggunakan kredit addon ({addon_count} baki)"
                }

            # Limit reached, offer addon purchase
            return {
                "allowed": False,
                "current_usage": current,
                "limit": limit,
                "can_buy_addon": True,
                "addon_type": addon_type,
                "addon_price": self.ADDON_PRICES.get(addon_type),
                "message": f"Had tercapai ({current}/{limit}). Naik taraf atau beli addon."
            }

        # Limit reached, no addon available (like menu items)
        return {
            "allowed": False,
            "current_usage": current,
            "limit": limit,
            "can_buy_addon": False,
            "message": f"Had tercapai ({current}/{limit}). Sila naik taraf pelan anda."
        }

    async def increment_usage(self, user_id: str, action: str, count: int = 1) -> bool:
        """Increment usage counter for a specific action"""
        billing_period = self.get_current_billing_period()

        # Ensure usage record exists
        await self.get_or_create_usage_tracking(user_id)

        # Map action to field name in usage_tracking table
        # Note: delivery_zones and riders counts are computed from their actual tables
        # via get_actual_resource_counts(), so they don't need tracking here
        field_mapping = {
            "create_website": "websites_count",
            "add_menu_item": "menu_items_count",
            "generate_ai_hero": "ai_hero_used",
            "generate_ai_image": "ai_images_used"
        }

        field = field_mapping.get(action)
        if not field:
            return False

        try:
            # Get current value first
            url = f"{self.url}/rest/v1/usage_tracking"
            params = {
                "user_id": f"eq.{user_id}",
                "billing_period": f"eq.{billing_period}",
                "select": field
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    records = response.json()
                    current_value = records[0].get(field, 0) if records else 0
                else:
                    current_value = 0

            # Update with incremented value
            update_data = {field: current_value + count}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}", "billing_period": f"eq.{billing_period}"},
                    json=update_data
                )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
            return False

    async def decrement_usage(self, user_id: str, action: str, count: int = 1) -> bool:
        """Decrement usage counter (for deletions)"""
        billing_period = self.get_current_billing_period()

        # Note: delivery_zones and riders counts are computed from their actual tables
        # via get_actual_resource_counts(), so they don't need tracking here
        field_mapping = {
            "create_website": "websites_count",
            "delete_website": "websites_count",
            "add_menu_item": "menu_items_count",
            "delete_menu_item": "menu_items_count"
        }

        field = field_mapping.get(action)
        if not field:
            return False

        try:
            url = f"{self.url}/rest/v1/usage_tracking"
            params = {
                "user_id": f"eq.{user_id}",
                "billing_period": f"eq.{billing_period}",
                "select": field
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)
                if response.status_code == 200:
                    records = response.json()
                    current_value = records[0].get(field, 0) if records else 0
                else:
                    return False

            # Update with decremented value (minimum 0)
            new_value = max(0, current_value - count)
            update_data = {field: new_value}

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}", "billing_period": f"eq.{billing_period}"},
                    json=update_data
                )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error decrementing usage: {e}")
            return False

    async def get_available_addon_credits(self, user_id: str, addon_type: Optional[str] = None) -> Dict[str, int]:
        """Get available addon credits for a user.

        Schema (actual table):
        id, user_id, addon_type, quantity, price_per_unit, total_price,
        status, used (boolean), used_at, expires_at, toyyibpay_bill_code, created_at

        Status 'active' means credits are available.
        Available credits = quantity WHERE used=false
        """
        try:
            url = f"{self.url}/rest/v1/addon_purchases"
            params = {
                "user_id": f"eq.{user_id}",
                "status": "eq.active",
                "used": "eq.false",
                "select": "addon_type,quantity,used"
            }

            if addon_type:
                params["addon_type"] = f"eq.{addon_type}"

            logger.debug(f"🔍 Querying addon credits for user {user_id[:8]}... status=active, used=false")

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                records = response.json()
                logger.debug(f"📦 Found {len(records)} addon_purchases records with status=active, used=false")

                credits = {}
                for record in records:
                    atype = record.get("addon_type")
                    quantity = record.get("quantity", 0)
                    # used=false means all credits in this record are available
                    available = quantity

                    if atype in credits:
                        credits[atype] += available
                    else:
                        credits[atype] = available

                logger.info(f"✅ Addon credits for user {user_id[:8]}...: {credits}")
                return credits

            logger.warning(f"⚠️ Failed to query addon_purchases: {response.status_code}")
            return {}

        except Exception as e:
            logger.error(f"Error getting addon credits: {e}")
            return {}

    async def use_addon_credit(self, user_id: str, addon_type: str) -> bool:
        """Use one addon credit.

        With boolean 'used' column, we mark the entire addon_purchase as used.
        Each addon_purchase record represents a single purchase that can be used once.
        """
        try:
            url = f"{self.url}/rest/v1/addon_purchases"
            params = {
                "user_id": f"eq.{user_id}",
                "addon_type": f"eq.{addon_type}",
                "status": "eq.active",
                "used": "eq.false",
                "order": "created_at.asc",
                "limit": 1
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                return False

            records = response.json()
            if not records:
                return False

            addon = records[0]
            addon_id = addon.get("id")

            # Mark the addon purchase as used
            from datetime import datetime
            update_url = f"{self.url}/rest/v1/addon_purchases"
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    update_url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{addon_id}"},
                    json={
                        "used": True,
                        "used_at": datetime.utcnow().isoformat(),
                        "status": "depleted"
                    }
                )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error using addon credit: {e}")
            return False

    async def create_subscription(self, user_id: str, tier: str, toyyibpay_bill_code: str = None) -> bool:
        """Create or update user subscription"""
        try:
            price = self.TIER_PRICES.get(tier, 5.00)
            now = datetime.utcnow()
            end_date = now + timedelta(days=30)

            subscription_data = {
                "user_id": user_id,
                "tier": tier,
                "status": "active",
                "price": price,
                "start_date": now.isoformat(),
                "end_date": end_date.isoformat(),
                "auto_renew": True,
                "toyyibpay_bill_code": toyyibpay_bill_code
            }

            # Check if subscription exists
            existing = await self.get_user_subscription(user_id)

            url = f"{self.url}/rest/v1/subscriptions"

            if existing:
                # Update existing
                async with httpx.AsyncClient() as client:
                    response = await client.patch(
                        url,
                        headers={**self.headers, "Prefer": "return=minimal"},
                        params={"user_id": f"eq.{user_id}"},
                        json=subscription_data
                    )
            else:
                # Create new
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers={**self.headers, "Prefer": "return=representation"},
                        json=subscription_data
                    )

            success = response.status_code in [200, 201, 204]
            if success:
                logger.info(f"Subscription created/updated for user {user_id}: {tier}")
            return success

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return False

    async def renew_subscription(self, user_id: str) -> Dict[str, Any]:
        """Renew user's current subscription"""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return {"success": False, "message": "No subscription found"}

        tier = subscription.get("tier", "starter")
        price = self.TIER_PRICES.get(tier, 5.00)

        now = datetime.utcnow()
        # If current subscription is still valid, extend from end date
        current_end = subscription.get("end_date")
        if current_end:
            try:
                end_dt = datetime.fromisoformat(current_end.replace("Z", "+00:00"))
                if end_dt > now.replace(tzinfo=end_dt.tzinfo):
                    now = end_dt.replace(tzinfo=None)
            except:
                pass

        new_end_date = now + timedelta(days=30)

        try:
            url = f"{self.url}/rest/v1/subscriptions"
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}"},
                    json={
                        "status": "active",
                        "end_date": new_end_date.isoformat()
                    }
                )

            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "new_end_date": new_end_date.isoformat(),
                    "amount": price
                }

            return {"success": False, "message": "Failed to renew subscription"}

        except Exception as e:
            logger.error(f"Error renewing subscription: {e}")
            return {"success": False, "message": str(e)}

    async def suspend_service(self, user_id: str) -> bool:
        """Suspend user's service (when subscription expires)"""
        try:
            url = f"{self.url}/rest/v1/subscriptions"
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}"},
                    json={"status": "suspended"}
                )

            success = response.status_code in [200, 204]
            if success:
                logger.info(f"Service suspended for user: {user_id}")
                # TODO: Disable user's websites
            return success

        except Exception as e:
            logger.error(f"Error suspending service: {e}")
            return False

    async def reactivate_service(self, user_id: str) -> bool:
        """Reactivate user's service after renewal"""
        try:
            url = f"{self.url}/rest/v1/subscriptions"
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}"},
                    json={"status": "active"}
                )

            success = response.status_code in [200, 204]
            if success:
                logger.info(f"Service reactivated for user: {user_id}")
                # TODO: Enable user's websites
            return success

        except Exception as e:
            logger.error(f"Error reactivating service: {e}")
            return False

    async def get_expiring_subscriptions(self, days: int) -> List[Dict[str, Any]]:
        """Get subscriptions expiring in the specified number of days"""
        try:
            target_date = (datetime.utcnow() + timedelta(days=days)).date()
            url = f"{self.url}/rest/v1/subscriptions"
            # Use an explicit range query (avoid duplicate dict keys)
            query_url = (
                f"{url}"
                f"?status=eq.active"
                f"&end_date=gte.{target_date}T00:00:00"
                f"&end_date=lt.{target_date}T23:59:59"
            )

            async with httpx.AsyncClient() as client:
                response = await client.get(query_url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []


# Singleton instance
subscription_service = SubscriptionService()
