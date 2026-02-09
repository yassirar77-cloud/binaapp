"""
BinaApp Notification Service
Central hub for in-app notifications and web push.
All other services call this to notify users.
"""
import httpx
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class NotificationService:
    """Central notification hub for BinaApp."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

    async def send(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "system",
        priority: str = "normal",
        action_url: str = None,
        metadata: Dict = None,
        deduplicate: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Send a notification to a user."""
        try:
            # Dedup check - prevent same notification within 5 minutes
            if deduplicate:
                dedup_key = hashlib.md5(
                    f"{user_id}:{notification_type}:{title}".encode()
                ).hexdigest()

                async with httpx.AsyncClient() as client:
                    check = await client.get(
                        f"{self.supabase_url}/rest/v1/notifications",
                        headers=self.headers,
                        params={
                            "user_id": f"eq.{user_id}",
                            "title": f"eq.{title}",
                            "notification_type": f"eq.{notification_type}",
                            "order": "created_at.desc",
                            "limit": "1",
                            "select": "id,created_at"
                        }
                    )
                    if check.status_code == 200 and check.json():
                        last = check.json()[0]
                        last_time = datetime.fromisoformat(last["created_at"].replace("Z", "+00:00"))
                        if (datetime.now(last_time.tzinfo) - last_time).total_seconds() < 300:
                            logger.debug(f"Notification deduplicated: {title}")
                            return last

            notification_data = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
                "priority": priority,
                "action_url": action_url,
                "metadata": json.dumps(metadata) if metadata else "{}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/notifications",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=notification_data
                )

            if response.status_code in [200, 201]:
                result = response.json()
                notif = result[0] if isinstance(result, list) else result

                # Try to send push notification
                await self._send_push(user_id, title, message)

                logger.info(f"Notification sent to {user_id}: {title}")
                return notif

            return None
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return None

    async def send_bulk(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        notification_type: str = "announcement",
        priority: str = "normal"
    ) -> int:
        """Send notification to multiple users."""
        sent = 0
        for user_id in user_ids:
            result = await self.send(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                deduplicate=True
            )
            if result:
                sent += 1
        return sent

    async def get_notifications(self, user_id: str, limit: int = 20, offset: int = 0, type_filter: str = None) -> List[Dict]:
        """Get notifications for a user."""
        try:
            params = {
                "user_id": f"eq.{user_id}",
                "select": "*",
                "order": "created_at.desc",
                "limit": str(limit),
                "offset": str(offset)
            }
            if type_filter:
                params["notification_type"] = f"eq.{type_filter}"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/notifications",
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []

    async def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for badge."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/notifications",
                    headers={**self.headers, "Prefer": "count=exact"},
                    params={
                        "user_id": f"eq.{user_id}",
                        "is_read": "eq.false",
                        "select": "id"
                    }
                )

            if response.status_code == 200:
                count_header = response.headers.get("content-range", "")
                if "/" in count_header:
                    total = count_header.split("/")[1]
                    return int(total) if total != "*" else len(response.json())
                return len(response.json())
            return 0
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/notifications",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{notification_id}", "user_id": f"eq.{user_id}"},
                    json={"is_read": True, "read_at": datetime.utcnow().isoformat()}
                )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error marking notification read: {e}")
            return False

    async def mark_all_read(self, user_id: str) -> bool:
        """Mark all notifications as read for a user."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/notifications",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"user_id": f"eq.{user_id}", "is_read": "eq.false"},
                    json={"is_read": True, "read_at": datetime.utcnow().isoformat()}
                )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error marking all read: {e}")
            return False

    async def register_push_subscription(self, user_id: str, subscription: Dict) -> bool:
        """Register a push notification subscription."""
        try:
            sub_data = {
                "user_id": user_id,
                "endpoint": subscription.get("endpoint"),
                "p256dh": subscription.get("keys", {}).get("p256dh", ""),
                "auth_key": subscription.get("keys", {}).get("auth", "")
            }

            async with httpx.AsyncClient() as client:
                # Upsert
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/push_subscriptions",
                    headers={
                        **self.headers,
                        "Prefer": "return=minimal,resolution=merge-duplicates"
                    },
                    json=sub_data
                )
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Error registering push subscription: {e}")
            return False

    async def _send_push(self, user_id: str, title: str, body: str):
        """Send web push notification (best effort)."""
        try:
            # Check for VAPID keys
            vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', None) or ''
            vapid_public = getattr(settings, 'VAPID_PUBLIC_KEY', None) or ''
            vapid_email = getattr(settings, 'VAPID_CLAIM_EMAIL', 'yassirar77@gmail.com')

            if not vapid_private or not vapid_public:
                return  # Push not configured

            try:
                from pywebpush import webpush
            except ImportError:
                logger.debug("pywebpush not installed, skipping push notification")
                return

            # Get user's push subscriptions
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/push_subscriptions",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "is_active": "eq.true", "select": "*"}
                )

            if response.status_code != 200:
                return

            subscriptions = response.json()
            payload = json.dumps({"title": title, "body": body, "icon": "/icon.png"})

            for sub in subscriptions:
                try:
                    webpush(
                        subscription_info={
                            "endpoint": sub["endpoint"],
                            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth_key"]}
                        },
                        data=payload,
                        vapid_private_key=vapid_private,
                        vapid_claims={"sub": f"mailto:{vapid_email}"}
                    )
                except Exception as push_err:
                    logger.debug(f"Push notification failed for subscription: {push_err}")
                    # Deactivate failed subscription
                    async with httpx.AsyncClient() as client:
                        await client.patch(
                            f"{self.supabase_url}/rest/v1/push_subscriptions",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            params={"id": f"eq.{sub['id']}"},
                            json={"is_active": False}
                        )

        except Exception as e:
            logger.debug(f"Push notification error: {e}")


notification_service = NotificationService()
