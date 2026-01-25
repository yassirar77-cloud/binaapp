"""
Subscription Reminder Service
Handles subscription expiry notifications and service suspension
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from app.core.config import settings


class SubscriptionReminderService:
    """
    Service for managing subscription reminders and service suspension

    This service should be called by a scheduled job (e.g., cron, Celery, APScheduler)
    to check for expiring subscriptions and send reminders.
    """

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }

    async def run_daily_checks(self) -> Dict[str, Any]:
        """
        Main method to run all daily subscription checks.
        Should be called by a scheduler daily (e.g., 9 AM).

        Returns a summary of actions taken.
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "reminders_7_days": 0,
            "reminders_3_days": 0,
            "reminders_1_day": 0,
            "suspensions": 0,
            "errors": []
        }

        try:
            # Send 7-day reminders
            results["reminders_7_days"] = await self.send_reminders(days_before=7)

            # Send 3-day reminders
            results["reminders_3_days"] = await self.send_reminders(days_before=3)

            # Send 1-day reminders
            results["reminders_1_day"] = await self.send_reminders(days_before=1)

            # Suspend expired subscriptions
            results["suspensions"] = await self.suspend_expired_subscriptions()

        except Exception as e:
            logger.error(f"Error in daily subscription checks: {e}")
            results["errors"].append(str(e))

        logger.info(f"Daily subscription check completed: {results}")
        return results

    async def get_subscriptions_expiring_on(self, target_date: datetime) -> List[Dict[str, Any]]:
        """Get subscriptions expiring on a specific date"""
        try:
            # Format dates for query
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            url = f"{self.url}/rest/v1/subscriptions"
            params = {
                "status": "eq.active",
                "end_date": f"gte.{start_of_day.isoformat()}",
                "and": f"(end_date.lte.{end_of_day.isoformat()})",
                "select": "id,user_id,tier,end_date,auto_renew"
            }

            # Use a simpler approach with range query
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{url}?status=eq.active&end_date=gte.{start_of_day.isoformat()}&end_date=lte.{end_of_day.isoformat()}",
                    headers=self.headers
                )

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []

    async def get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """Get subscriptions that are expired but still marked as active"""
        try:
            now = datetime.utcnow()

            url = f"{self.url}/rest/v1/subscriptions"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{url}?status=eq.active&end_date=lt.{now.isoformat()}",
                    headers=self.headers
                )

            if response.status_code == 200:
                return response.json()
            return []

        except Exception as e:
            logger.error(f"Error getting expired subscriptions: {e}")
            return []

    async def send_reminders(self, days_before: int) -> int:
        """
        Send expiry reminder emails for subscriptions expiring in X days

        Args:
            days_before: Number of days before expiry (7, 3, or 1)

        Returns:
            Number of reminders sent
        """
        target_date = datetime.utcnow() + timedelta(days=days_before)
        expiring = await self.get_subscriptions_expiring_on(target_date)

        sent_count = 0
        reminder_type = f"{days_before}_days"

        for sub in expiring:
            try:
                user_id = sub.get("user_id")
                subscription_id = sub.get("id")

                # Check if reminder already sent
                if await self._reminder_already_sent(user_id, subscription_id, reminder_type):
                    continue

                # Get user email
                user = await self._get_user(user_id)
                if not user or not user.get("email"):
                    continue

                # Send email (placeholder - integrate with actual email service)
                email_sent = await self._send_reminder_email(
                    email=user.get("email"),
                    user_name=user.get("full_name", "Pelanggan"),
                    plan_name=sub.get("tier", "starter"),
                    end_date=sub.get("end_date"),
                    days_before=days_before
                )

                if email_sent:
                    # Record that reminder was sent
                    await self._record_reminder(user_id, subscription_id, reminder_type)
                    sent_count += 1

            except Exception as e:
                logger.error(f"Error sending reminder for user {sub.get('user_id')}: {e}")

        logger.info(f"Sent {sent_count} reminders for {days_before}-day expiry")
        return sent_count

    async def suspend_expired_subscriptions(self) -> int:
        """
        Suspend subscriptions that have expired.
        Updates status to 'expired' and disables websites.

        Returns:
            Number of subscriptions suspended
        """
        expired = await self.get_expired_subscriptions()
        suspended_count = 0

        for sub in expired:
            try:
                user_id = sub.get("user_id")
                subscription_id = sub.get("id")

                # Update subscription status
                await self._update_subscription_status(subscription_id, "expired")

                # Disable user's websites (set status to 'suspended')
                await self._suspend_user_websites(user_id)

                # Send expiry notification
                user = await self._get_user(user_id)
                if user and user.get("email"):
                    await self._send_expiry_email(
                        email=user.get("email"),
                        user_name=user.get("full_name", "Pelanggan"),
                        plan_name=sub.get("tier", "starter")
                    )

                    # Record the expiry reminder
                    await self._record_reminder(user_id, subscription_id, "expired")

                suspended_count += 1
                logger.info(f"Suspended service for user {user_id}")

            except Exception as e:
                logger.error(f"Error suspending user {sub.get('user_id')}: {e}")

        logger.info(f"Suspended {suspended_count} expired subscriptions")
        return suspended_count

    async def reactivate_subscription(self, user_id: str, new_end_date: datetime) -> bool:
        """
        Reactivate a suspended subscription after payment

        Args:
            user_id: User ID
            new_end_date: New subscription end date

        Returns:
            Success status
        """
        try:
            # Update subscription status
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

            if response.status_code not in [200, 204]:
                return False

            # Re-enable user's websites
            await self._enable_user_websites(user_id)

            # Send welcome back email
            user = await self._get_user(user_id)
            if user and user.get("email"):
                await self._send_reactivation_email(
                    email=user.get("email"),
                    user_name=user.get("full_name", "Pelanggan")
                )

            logger.info(f"Reactivated subscription for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error reactivating subscription for {user_id}: {e}")
            return False

    # =========================================================================
    # Private helper methods
    # =========================================================================

    async def _get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user details from profiles table"""
        try:
            url = f"{self.url}/rest/v1/profiles"
            params = {"id": f"eq.{user_id}"}

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

                if response.status_code != 200:
                    return None

                records = response.json()
                if not records:
                    return None

                profile = records[0]

                # Also get email from auth admin API (service role only)
                auth_url = f"{self.url}/auth/v1/admin/users/{user_id}"
                auth_response = await client.get(auth_url, headers=self.headers)
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    profile["email"] = auth_data.get("email")

                return profile

        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def _reminder_already_sent(
        self, user_id: str, subscription_id: str, reminder_type: str
    ) -> bool:
        """Check if a reminder was already sent"""
        try:
            url = f"{self.url}/rest/v1/subscription_reminders"
            params = {
                "user_id": f"eq.{user_id}",
                "subscription_id": f"eq.{subscription_id}",
                "reminder_type": f"eq.{reminder_type}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                records = response.json()
                return len(records) > 0
            return False

        except Exception as e:
            logger.error(f"Error checking reminder status: {e}")
            return False

    async def _record_reminder(
        self, user_id: str, subscription_id: str, reminder_type: str
    ) -> bool:
        """Record that a reminder was sent"""
        try:
            url = f"{self.url}/rest/v1/subscription_reminders"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    json={
                        "user_id": user_id,
                        "subscription_id": subscription_id,
                        "reminder_type": reminder_type,
                        "email_sent": True
                    }
                )

            return response.status_code in [200, 201]

        except Exception as e:
            logger.error(f"Error recording reminder: {e}")
            return False

    async def _update_subscription_status(self, subscription_id: str, status: str) -> bool:
        """Update subscription status"""
        try:
            url = f"{self.url}/rest/v1/subscriptions"

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{subscription_id}"},
                    json={"status": status}
                )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
            return False

    async def _suspend_user_websites(self, user_id: str) -> bool:
        """Suspend all websites for a user"""
        try:
            url = f"{self.url}/rest/v1/websites"

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}"},
                    json={"status": "suspended"}
                )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error suspending websites for {user_id}: {e}")
            return False

    async def _enable_user_websites(self, user_id: str) -> bool:
        """Re-enable all suspended websites for a user"""
        try:
            url = f"{self.url}/rest/v1/websites"

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={
                        "user_id": f"eq.{user_id}",
                        "status": "eq.suspended"
                    },
                    json={"status": "published"}
                )

            return response.status_code in [200, 204]

        except Exception as e:
            logger.error(f"Error enabling websites for {user_id}: {e}")
            return False

    async def _send_reminder_email(
        self,
        email: str,
        user_name: str,
        plan_name: str,
        end_date: str,
        days_before: int
    ) -> bool:
        """
        Send reminder email.
        Placeholder - integrate with actual email service (SendGrid, SES, etc.)
        """
        logger.info(f"[EMAIL] Reminder ({days_before} days) to {email}")
        logger.info(f"  User: {user_name}")
        logger.info(f"  Plan: {plan_name}")
        logger.info(f"  Expires: {end_date}")

        # TODO: Integrate with email service
        # Example with SendGrid:
        # await sendgrid.send(
        #     to=email,
        #     template="subscription-reminder",
        #     data={
        #         "user_name": user_name,
        #         "plan_name": plan_name,
        #         "days_remaining": days_before,
        #         "renew_url": f"{settings.FRONTEND_URL}/dashboard/billing"
        #     }
        # )

        return True  # Return True for now

    async def _send_expiry_email(
        self, email: str, user_name: str, plan_name: str
    ) -> bool:
        """
        Send subscription expired email.
        Placeholder - integrate with actual email service.
        """
        logger.info(f"[EMAIL] Subscription expired notification to {email}")
        logger.info(f"  User: {user_name}")
        logger.info(f"  Plan: {plan_name}")

        # TODO: Integrate with email service

        return True

    async def _send_reactivation_email(self, email: str, user_name: str) -> bool:
        """
        Send welcome back email after subscription reactivation.
        Placeholder - integrate with actual email service.
        """
        logger.info(f"[EMAIL] Subscription reactivated notification to {email}")
        logger.info(f"  User: {user_name}")

        # TODO: Integrate with email service

        return True


# Singleton instance
subscription_reminder_service = SubscriptionReminderService()
