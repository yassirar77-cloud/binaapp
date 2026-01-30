"""
Daily Subscription Status Cron Job
Run daily at midnight Malaysia time (UTC+8) = 16:00 UTC previous day

TASKS:
1. Check all subscriptions for upcoming expiry
2. Update status based on dates (active -> expired -> grace -> locked)
3. Send reminder emails at appropriate intervals
4. Lock websites when grace period ends

This cron job handles the complete subscription lifecycle:
- 5 days before expiry: Send reminder email
- 3 days before expiry: Send urgent reminder email
- Day of expiry: Update status to 'expired', start grace period, send notice
- During grace period: Send daily warnings
- End of grace period: Update status to 'locked', lock all websites
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
import httpx

from app.core.config import settings
from app.services.email_service import email_service
from app.cron.email_templates import (
    render_reminder_5_days,
    render_reminder_3_days,
    render_expired_notice,
    render_lock_warning,
    render_locked_notice,
)


class SubscriptionCronJob:
    """
    Handles daily subscription status updates and email notifications.

    Run schedule: Daily at 00:00 Malaysia Time (UTC+8)
    Which is 16:00 UTC the previous day
    """

    GRACE_PERIOD_DAYS = 5  # Days between expiry and lock

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.frontend_url = settings.FRONTEND_URL or settings.BASE_URL
        self.support_email = settings.SUPPORT_EMAIL or "support@binaapp.com"

    # =========================================================================
    # DATABASE HELPERS
    # =========================================================================

    async def _fetch_subscriptions(self, filters: Dict[str, str]) -> List[Dict[str, Any]]:
        """Fetch subscriptions from database with filters"""
        try:
            url = f"{self.supabase_url}/rest/v1/subscriptions"
            params = {
                "select": "id,user_id,tier,status,end_date,grace_period_end,locked_at,lock_reason,price,profiles(email,full_name)"
            }
            params.update(filters)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch subscriptions: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error fetching subscriptions: {e}")
            return []

    async def _update_subscription(self, subscription_id: str, updates: Dict[str, Any]) -> bool:
        """Update a subscription record"""
        try:
            url = f"{self.supabase_url}/rest/v1/subscriptions"
            params = {"id": f"eq.{subscription_id}"}

            updates["updated_at"] = datetime.utcnow().isoformat()

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(
                    url,
                    headers=self.headers,
                    params=params,
                    json=updates
                )

            if response.status_code in [200, 204]:
                logger.info(f"Updated subscription {subscription_id}: {updates}")
                return True
            else:
                logger.error(f"Failed to update subscription {subscription_id}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error updating subscription {subscription_id}: {e}")
            return False

    async def _log_email_sent(
        self,
        user_id: str,
        subscription_id: str,
        email_type: str,
        email_address: str
    ) -> bool:
        """Log email to subscription_email_logs table"""
        try:
            url = f"{self.supabase_url}/rest/v1/subscription_email_logs"

            data = {
                "user_id": user_id,
                "subscription_id": subscription_id,
                "email_type": email_type,
                "email_address": email_address,
                "sent_at": datetime.utcnow().isoformat(),
                "metadata": {"cron_run": datetime.utcnow().isoformat()}
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=self.headers, json=data)

            return response.status_code in [200, 201]

        except Exception as e:
            logger.error(f"Error logging email: {e}")
            return False

    async def _was_email_sent_recently(
        self,
        user_id: str,
        email_type: str,
        hours: int = 24
    ) -> bool:
        """Check if an email of this type was sent recently"""
        try:
            url = f"{self.supabase_url}/rest/v1/subscription_email_logs"
            cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

            params = {
                "user_id": f"eq.{user_id}",
                "email_type": f"eq.{email_type}",
                "sent_at": f"gte.{cutoff}",
                "select": "id",
                "limit": "1"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                return len(response.json()) > 0

            return False

        except Exception as e:
            logger.error(f"Error checking email history: {e}")
            return False

    async def _lock_user_websites(self, user_id: str, lock_reason: str) -> int:
        """Lock all websites for a user"""
        locked_count = 0

        try:
            # First, get all websites for the user
            url = f"{self.supabase_url}/rest/v1/websites"
            params = {"user_id": f"eq.{user_id}", "select": "id"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                logger.error(f"Failed to get websites for user {user_id}")
                return 0

            websites = response.json()

            # Lock each website
            for website in websites:
                website_id = website["id"]

                # Check if lock status record exists
                lock_url = f"{self.supabase_url}/rest/v1/website_lock_status"
                check_params = {"website_id": f"eq.{website_id}"}

                async with httpx.AsyncClient(timeout=30.0) as client:
                    check_response = await client.get(lock_url, headers=self.headers, params=check_params)

                lock_data = {
                    "website_id": website_id,
                    "user_id": user_id,
                    "is_locked": True,
                    "locked_at": datetime.utcnow().isoformat(),
                    "lock_reason": lock_reason,
                    "updated_at": datetime.utcnow().isoformat()
                }

                if check_response.status_code == 200 and len(check_response.json()) > 0:
                    # Update existing record
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        update_response = await client.patch(
                            lock_url,
                            headers=self.headers,
                            params=check_params,
                            json=lock_data
                        )
                    if update_response.status_code in [200, 204]:
                        locked_count += 1
                else:
                    # Insert new record
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        insert_response = await client.post(
                            lock_url,
                            headers=self.headers,
                            json=lock_data
                        )
                    if insert_response.status_code in [200, 201]:
                        locked_count += 1

            logger.info(f"Locked {locked_count} websites for user {user_id}")
            return locked_count

        except Exception as e:
            logger.error(f"Error locking websites for user {user_id}: {e}")
            return 0

    def _get_user_info(self, subscription: Dict[str, Any]) -> tuple:
        """Extract user info from subscription record"""
        profiles = subscription.get("profiles") or {}
        if isinstance(profiles, list) and len(profiles) > 0:
            profiles = profiles[0]

        email = profiles.get("email", "")
        name = profiles.get("full_name") or email.split("@")[0] if email else "Pengguna"

        return email, name

    def _get_payment_url(self) -> str:
        """Get the payment URL"""
        return f"{self.frontend_url}/dashboard/billing"

    # =========================================================================
    # STEP 1: REMINDER EMAILS (5 DAYS BEFORE EXPIRY)
    # =========================================================================

    async def send_5_day_reminders(self) -> Dict[str, int]:
        """Send reminder emails to users whose subscription expires in 5 days"""
        logger.info("Step 1: Checking for subscriptions expiring in 5 days...")

        results = {"found": 0, "sent": 0, "skipped": 0, "failed": 0}

        # Calculate target date (5 days from now)
        target_date = (datetime.utcnow() + timedelta(days=5)).date()
        target_start = datetime.combine(target_date, datetime.min.time()).isoformat()
        target_end = datetime.combine(target_date, datetime.max.time()).isoformat()

        subscriptions = await self._fetch_subscriptions({
            "status": "eq.active",
            "end_date": f"gte.{target_start}",
            "and": f"(end_date.lte.{target_end})"
        })

        results["found"] = len(subscriptions)
        logger.info(f"Found {len(subscriptions)} subscriptions expiring in 5 days")

        for sub in subscriptions:
            user_id = sub.get("user_id")
            subscription_id = sub.get("id")
            email, name = self._get_user_info(sub)

            if not email:
                logger.warning(f"No email for user {user_id}, skipping")
                results["skipped"] += 1
                continue

            # Check if email was already sent
            if await self._was_email_sent_recently(user_id, "reminder_5_days", hours=24):
                logger.debug(f"5-day reminder already sent to {email}")
                results["skipped"] += 1
                continue

            # Generate email
            end_date_str = sub.get("end_date", "")[:10]
            tier = sub.get("tier", "starter")
            price = sub.get("price", 0) or 5.0

            template = render_reminder_5_days(
                name=name,
                end_date=end_date_str,
                plan_name=tier.title(),
                price=price,
                payment_url=self._get_payment_url(),
                support_email=self.support_email
            )

            # Send email
            sent = await email_service._send_email(
                to_email=email,
                subject=template["subject"],
                html_content=template["html"],
                text_content=template["text"]
            )

            if sent:
                await self._log_email_sent(user_id, subscription_id, "reminder_5_days", email)
                results["sent"] += 1
                logger.info(f"Sent 5-day reminder to {email}")
            else:
                results["failed"] += 1
                logger.error(f"Failed to send 5-day reminder to {email}")

        return results

    # =========================================================================
    # STEP 2: REMINDER EMAILS (3 DAYS BEFORE EXPIRY)
    # =========================================================================

    async def send_3_day_reminders(self) -> Dict[str, int]:
        """Send urgent reminder emails to users whose subscription expires in 3 days"""
        logger.info("Step 2: Checking for subscriptions expiring in 3 days...")

        results = {"found": 0, "sent": 0, "skipped": 0, "failed": 0}

        target_date = (datetime.utcnow() + timedelta(days=3)).date()
        target_start = datetime.combine(target_date, datetime.min.time()).isoformat()
        target_end = datetime.combine(target_date, datetime.max.time()).isoformat()

        subscriptions = await self._fetch_subscriptions({
            "status": "eq.active",
            "end_date": f"gte.{target_start}",
            "and": f"(end_date.lte.{target_end})"
        })

        results["found"] = len(subscriptions)
        logger.info(f"Found {len(subscriptions)} subscriptions expiring in 3 days")

        for sub in subscriptions:
            user_id = sub.get("user_id")
            subscription_id = sub.get("id")
            email, name = self._get_user_info(sub)

            if not email:
                results["skipped"] += 1
                continue

            if await self._was_email_sent_recently(user_id, "reminder_3_days", hours=24):
                results["skipped"] += 1
                continue

            end_date_str = sub.get("end_date", "")[:10]
            tier = sub.get("tier", "starter")
            price = sub.get("price", 0) or 5.0

            template = render_reminder_3_days(
                name=name,
                end_date=end_date_str,
                plan_name=tier.title(),
                price=price,
                payment_url=self._get_payment_url(),
                support_email=self.support_email
            )

            sent = await email_service._send_email(
                to_email=email,
                subject=template["subject"],
                html_content=template["html"],
                text_content=template["text"]
            )

            if sent:
                await self._log_email_sent(user_id, subscription_id, "reminder_3_days", email)
                results["sent"] += 1
                logger.info(f"Sent 3-day reminder to {email}")
            else:
                results["failed"] += 1

        return results

    # =========================================================================
    # STEP 3: PROCESS EXPIRED SUBSCRIPTIONS (START GRACE PERIOD)
    # =========================================================================

    async def process_expired_subscriptions(self) -> Dict[str, int]:
        """
        Process subscriptions that just expired.
        Update status to 'expired' and start grace period.
        """
        logger.info("Step 3: Processing expired subscriptions...")

        results = {"found": 0, "updated": 0, "emails_sent": 0, "failed": 0}

        # Find active subscriptions where end_date has passed
        now = datetime.utcnow().isoformat()

        subscriptions = await self._fetch_subscriptions({
            "status": "eq.active",
            "end_date": f"lt.{now}"
        })

        results["found"] = len(subscriptions)
        logger.info(f"Found {len(subscriptions)} expired subscriptions to process")

        for sub in subscriptions:
            user_id = sub.get("user_id")
            subscription_id = sub.get("id")
            email, name = self._get_user_info(sub)

            # Calculate grace period end (5 days from now)
            grace_end = datetime.utcnow() + timedelta(days=self.GRACE_PERIOD_DAYS)

            # Update subscription status
            updated = await self._update_subscription(subscription_id, {
                "status": "expired",
                "grace_period_end": grace_end.isoformat()
            })

            if updated:
                results["updated"] += 1

                # Send expired notice email
                if email and not await self._was_email_sent_recently(user_id, "expired", hours=24):
                    tier = sub.get("tier", "starter")

                    template = render_expired_notice(
                        name=name,
                        plan_name=tier.title(),
                        grace_end_date=grace_end.strftime("%d/%m/%Y"),
                        payment_url=self._get_payment_url(),
                        support_email=self.support_email
                    )

                    sent = await email_service._send_email(
                        to_email=email,
                        subject=template["subject"],
                        html_content=template["html"],
                        text_content=template["text"]
                    )

                    if sent:
                        await self._log_email_sent(user_id, subscription_id, "expired", email)
                        results["emails_sent"] += 1
                        logger.info(f"Sent expiry notice to {email}")
            else:
                results["failed"] += 1

        return results

    # =========================================================================
    # STEP 4: TRANSITION TO GRACE PERIOD
    # =========================================================================

    async def transition_to_grace_period(self) -> Dict[str, int]:
        """
        Transition expired subscriptions to grace status after initial notification.
        """
        logger.info("Step 4: Transitioning expired subscriptions to grace period...")

        results = {"found": 0, "updated": 0}

        # Find subscriptions in 'expired' status with grace_period_end set
        subscriptions = await self._fetch_subscriptions({
            "status": "eq.expired",
            "grace_period_end": "not.is.null"
        })

        results["found"] = len(subscriptions)

        for sub in subscriptions:
            subscription_id = sub.get("id")

            # Update to grace status
            updated = await self._update_subscription(subscription_id, {
                "status": "grace"
            })

            if updated:
                results["updated"] += 1

        logger.info(f"Transitioned {results['updated']} subscriptions to grace period")
        return results

    # =========================================================================
    # STEP 5: SEND LOCK WARNINGS (GRACE PERIOD ENDING TODAY)
    # =========================================================================

    async def send_lock_warnings(self) -> Dict[str, int]:
        """Send final warning to users whose grace period ends today"""
        logger.info("Step 5: Sending lock warnings...")

        results = {"found": 0, "sent": 0, "skipped": 0, "failed": 0}

        # Find subscriptions where grace period ends today
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time()).isoformat()
        today_end = datetime.combine(today, datetime.max.time()).isoformat()

        subscriptions = await self._fetch_subscriptions({
            "status": "eq.grace",
            "grace_period_end": f"gte.{today_start}",
            "and": f"(grace_period_end.lte.{today_end})"
        })

        results["found"] = len(subscriptions)
        logger.info(f"Found {len(subscriptions)} subscriptions with grace period ending today")

        for sub in subscriptions:
            user_id = sub.get("user_id")
            subscription_id = sub.get("id")
            email, name = self._get_user_info(sub)

            if not email:
                results["skipped"] += 1
                continue

            if await self._was_email_sent_recently(user_id, "lock_warning", hours=12):
                results["skipped"] += 1
                continue

            template = render_lock_warning(
                name=name,
                payment_url=self._get_payment_url(),
                support_email=self.support_email
            )

            sent = await email_service._send_email(
                to_email=email,
                subject=template["subject"],
                html_content=template["html"],
                text_content=template["text"]
            )

            if sent:
                await self._log_email_sent(user_id, subscription_id, "lock_warning", email)
                results["sent"] += 1
                logger.info(f"Sent lock warning to {email}")
            else:
                results["failed"] += 1

        return results

    # =========================================================================
    # STEP 6: LOCK SUBSCRIPTIONS (GRACE PERIOD ENDED)
    # =========================================================================

    async def lock_expired_subscriptions(self) -> Dict[str, int]:
        """Lock subscriptions where grace period has ended"""
        logger.info("Step 6: Locking subscriptions with ended grace period...")

        results = {"found": 0, "locked": 0, "websites_locked": 0, "emails_sent": 0, "failed": 0}

        # Find subscriptions where grace period has ended
        now = datetime.utcnow().isoformat()

        subscriptions = await self._fetch_subscriptions({
            "status": "eq.grace",
            "grace_period_end": f"lt.{now}"
        })

        results["found"] = len(subscriptions)
        logger.info(f"Found {len(subscriptions)} subscriptions to lock")

        for sub in subscriptions:
            user_id = sub.get("user_id")
            subscription_id = sub.get("id")
            email, name = self._get_user_info(sub)

            # Update subscription to locked
            updated = await self._update_subscription(subscription_id, {
                "status": "locked",
                "locked_at": datetime.utcnow().isoformat(),
                "lock_reason": "subscription_expired"
            })

            if updated:
                results["locked"] += 1

                # Lock all user's websites
                websites_locked = await self._lock_user_websites(user_id, "subscription_expired")
                results["websites_locked"] += websites_locked

                # Send locked notice email
                if email and not await self._was_email_sent_recently(user_id, "locked", hours=24):
                    template = render_locked_notice(
                        name=name,
                        lock_reason="subscription_expired",
                        payment_url=self._get_payment_url(),
                        support_email=self.support_email
                    )

                    sent = await email_service._send_email(
                        to_email=email,
                        subject=template["subject"],
                        html_content=template["html"],
                        text_content=template["text"]
                    )

                    if sent:
                        await self._log_email_sent(user_id, subscription_id, "locked", email)
                        results["emails_sent"] += 1
                        logger.info(f"Sent lock notice to {email}")
            else:
                results["failed"] += 1

        return results

    # =========================================================================
    # MAIN RUN METHOD
    # =========================================================================

    async def run(self) -> Dict[str, Any]:
        """
        Execute all cron job steps in order.

        Returns a summary of all operations performed.
        """
        start_time = datetime.utcnow()
        logger.info("=" * 60)
        logger.info("SUBSCRIPTION CRON JOB STARTED")
        logger.info(f"Time: {start_time.isoformat()}")
        logger.info("=" * 60)

        results = {
            "start_time": start_time.isoformat(),
            "steps": {}
        }

        try:
            # Step 1: 5-day reminders
            results["steps"]["5_day_reminders"] = await self.send_5_day_reminders()

            # Step 2: 3-day reminders
            results["steps"]["3_day_reminders"] = await self.send_3_day_reminders()

            # Step 3: Process newly expired subscriptions
            results["steps"]["expired_processing"] = await self.process_expired_subscriptions()

            # Step 4: Transition to grace
            results["steps"]["grace_transition"] = await self.transition_to_grace_period()

            # Step 5: Lock warnings
            results["steps"]["lock_warnings"] = await self.send_lock_warnings()

            # Step 6: Lock subscriptions
            results["steps"]["locking"] = await self.lock_expired_subscriptions()

            results["success"] = True

        except Exception as e:
            logger.error(f"Cron job failed with error: {e}")
            results["success"] = False
            results["error"] = str(e)

        end_time = datetime.utcnow()
        results["end_time"] = end_time.isoformat()
        results["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info("SUBSCRIPTION CRON JOB COMPLETED")
        logger.info(f"Duration: {results['duration_seconds']:.2f} seconds")
        logger.info(f"Success: {results['success']}")
        logger.info("=" * 60)

        return results


# Create singleton instance
subscription_cron = SubscriptionCronJob()


# Async entry point for running the cron job
async def run_subscription_cron():
    """Entry point for running the subscription cron job"""
    return await subscription_cron.run()


# Synchronous wrapper for cron runners
def run_subscription_cron_sync():
    """Synchronous wrapper for running the cron job"""
    return asyncio.run(run_subscription_cron())


if __name__ == "__main__":
    # Allow running directly for testing
    result = run_subscription_cron_sync()
    print(f"Cron job completed: {result}")
