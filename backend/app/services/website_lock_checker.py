"""
Website Lock Checker Service
Check if a website should be locked before serving to customers

This service is used by the subdomain middleware to determine if a
public-facing website should show the "Website Tidak Aktif" page.

Lock checks are performed in order:
1. Check website_lock_status table (set by cron job)
2. If not found, check owner's subscription status (real-time fallback)
"""

from typing import Optional, Tuple
from datetime import datetime
from loguru import logger
import httpx

from app.core.config import settings


class WebsiteLockChecker:
    """
    Service to check if a website should show the locked page.

    Performs two-level check:
    1. website_lock_status table (fast, set by cron)
    2. Owner's subscription status (fallback for real-time accuracy)
    """

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }

    async def is_website_locked(self, website_id: str) -> bool:
        """
        Check if a website should show the locked page.

        Args:
            website_id: UUID of the website

        Returns:
            True if website should show locked page, False otherwise
        """
        try:
            # Step 1: Check website_lock_status table first (fast check)
            is_locked = await self._check_website_lock_status(website_id)

            if is_locked is not None:
                return is_locked

            # Step 2: Fallback to checking owner's subscription status
            # This handles cases where cron hasn't run yet
            owner_status = await self._get_owner_subscription_status(website_id)

            if owner_status in ["locked", "suspended"]:
                logger.info(f"Website {website_id} locked due to owner subscription status: {owner_status}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking website lock status: {e}")
            # Fail open - don't lock websites if we can't check
            return False

    async def _check_website_lock_status(self, website_id: str) -> Optional[bool]:
        """
        Check the website_lock_status table for this website.

        Returns:
            True if locked, False if explicitly not locked, None if no record
        """
        try:
            url = f"{self.supabase_url}/rest/v1/website_lock_status"
            params = {
                "website_id": f"eq.{website_id}",
                "select": "is_locked,locked_at,lock_reason"
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                # 404 means table doesn't exist yet - not an error, just skip
                if response.status_code == 404:
                    logger.debug(f"website_lock_status table not found (404), skipping")
                else:
                    logger.warning(f"Failed to check website_lock_status: {response.status_code}")
                return None

            records = response.json()

            if not records:
                # No record - need to check subscription status
                return None

            lock_status = records[0]
            is_locked = lock_status.get("is_locked", False)

            if is_locked:
                logger.debug(f"Website {website_id} is locked. Reason: {lock_status.get('lock_reason')}")

            return is_locked

        except httpx.TimeoutException:
            logger.warning(f"Timeout checking website_lock_status for {website_id}")
            return None
        except Exception as e:
            logger.error(f"Error checking website_lock_status: {e}")
            return None

    async def _get_owner_subscription_status(self, website_id: str) -> Optional[str]:
        """
        Get the subscription status of the website owner.

        This is a fallback check for real-time accuracy when the
        website_lock_status table hasn't been updated yet.

        Returns:
            Subscription status string or None if not found
        """
        try:
            # First, get the website's owner (user_id)
            url = f"{self.supabase_url}/rest/v1/websites"
            params = {
                "id": f"eq.{website_id}",
                "select": "user_id"
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                return None

            websites = response.json()
            if not websites:
                return None

            user_id = websites[0].get("user_id")
            if not user_id:
                return None

            # Now get the owner's subscription status
            sub_url = f"{self.supabase_url}/rest/v1/subscriptions"
            sub_params = {
                "user_id": f"eq.{user_id}",
                "select": "status,end_date,grace_period_end"
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                sub_response = await client.get(sub_url, headers=self.headers, params=sub_params)

            # If query fails (e.g. columns don't exist), retry with just status
            if sub_response.status_code == 400:
                logger.debug("Subscription query failed (400), retrying with minimal columns")
                sub_params["select"] = "status"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    sub_response = await client.get(sub_url, headers=self.headers, params=sub_params)

            if sub_response.status_code != 200:
                return None

            subscriptions = sub_response.json()
            if not subscriptions:
                # No subscription record - treat as active (free tier)
                return "active"

            sub = subscriptions[0]
            status = sub.get("status", "active")

            # Additional check: if status is "grace" and grace_period_end has passed
            if status == "grace":
                grace_end = sub.get("grace_period_end")
                if grace_end:
                    try:
                        grace_end_dt = datetime.fromisoformat(grace_end.replace("Z", "+00:00"))
                        if datetime.utcnow().replace(tzinfo=grace_end_dt.tzinfo) > grace_end_dt:
                            # Grace period has ended, should be locked
                            logger.info(f"Website {website_id}: Owner's grace period has ended")
                            return "locked"
                    except Exception:
                        pass

            return status

        except httpx.TimeoutException:
            logger.warning(f"Timeout getting owner subscription for website {website_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting owner subscription status: {e}")
            return None

    async def get_lock_info(self, website_id: str) -> Tuple[bool, Optional[str]]:
        """
        Get detailed lock information for a website.

        Returns:
            Tuple of (is_locked, lock_reason)
        """
        try:
            url = f"{self.supabase_url}/rest/v1/website_lock_status"
            params = {
                "website_id": f"eq.{website_id}",
                "select": "is_locked,lock_reason"
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                records = response.json()
                if records:
                    return (
                        records[0].get("is_locked", False),
                        records[0].get("lock_reason")
                    )

            # Fallback to subscription check
            owner_status = await self._get_owner_subscription_status(website_id)
            if owner_status in ["locked", "suspended"]:
                return (True, "subscription_" + owner_status)

            return (False, None)

        except Exception as e:
            logger.error(f"Error getting lock info: {e}")
            return (False, None)


# Singleton instance
website_lock_checker = WebsiteLockChecker()


# Convenience function for middleware
async def is_website_locked(website_id: str) -> bool:
    """
    Convenience function to check if a website is locked.

    Args:
        website_id: UUID of the website

    Returns:
        True if website should show locked page
    """
    return await website_lock_checker.is_website_locked(website_id)


async def get_website_owner_subscription_status(website_id: str) -> Optional[str]:
    """
    Convenience function to get owner's subscription status.

    Args:
        website_id: UUID of the website

    Returns:
        Subscription status string or None
    """
    return await website_lock_checker._get_owner_subscription_status(website_id)
