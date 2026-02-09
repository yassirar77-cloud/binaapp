"""
BinaApp Webhook Service
HMAC-SHA256 signed webhook delivery with retry logic.
"""
import httpx
import hmac
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


# Supported webhook events
WEBHOOK_EVENTS = [
    "dispute.created", "dispute.resolved",
    "credit.awarded", "credit.spent",
    "order.delivered", "order.issue_detected",
    "website.scanned", "website.rebuilt",
    "sla.breach", "penalty.created",
    "subscription.created", "subscription.expired"
]


class WebhookService:
    """Manages webhook endpoints and delivery."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        self.max_retries = 3
        self.max_failures = 10
        self.delivery_timeout = 10.0

    def generate_secret(self) -> str:
        """Generate a webhook signing secret."""
        return f"whsec_{secrets.token_urlsafe(32)}"

    def sign_payload(self, payload: str, secret: str) -> str:
        """Sign a payload with HMAC-SHA256."""
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def create_endpoint(self, user_id: str, url: str, events: List[str], description: str = "") -> Dict:
        """Create a webhook endpoint."""
        try:
            # Validate events
            invalid = [e for e in events if e not in WEBHOOK_EVENTS]
            if invalid:
                return {"success": False, "error": f"Event tidak sah: {', '.join(invalid)}"}

            secret = self.generate_secret()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/webhook_endpoints",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json={
                        "user_id": user_id,
                        "url": url,
                        "secret": secret,
                        "events": json.dumps(events),
                        "description": description
                    }
                )

            if response.status_code in [200, 201]:
                data = response.json()
                endpoint = data[0] if isinstance(data, list) else data
                return {"success": True, "endpoint": endpoint, "secret": secret}

            return {"success": False, "error": "Gagal mencipta webhook"}
        except Exception as e:
            logger.error(f"Error creating webhook endpoint: {e}")
            return {"success": False, "error": str(e)}

    async def update_endpoint(self, endpoint_id: str, user_id: str, update_data: Dict) -> Dict:
        """Update a webhook endpoint."""
        try:
            if "events" in update_data and isinstance(update_data["events"], list):
                update_data["events"] = json.dumps(update_data["events"])

            update_data["updated_at"] = datetime.utcnow().isoformat()

            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/webhook_endpoints",
                    headers={**self.headers, "Prefer": "return=representation"},
                    params={"id": f"eq.{endpoint_id}", "user_id": f"eq.{user_id}"},
                    json=update_data
                )
            if response.status_code in [200, 204]:
                return {"success": True}
            return {"success": False, "error": "Gagal mengemaskini webhook"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_endpoint(self, endpoint_id: str, user_id: str) -> Dict:
        """Delete a webhook endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.supabase_url}/rest/v1/webhook_endpoints",
                    headers=self.headers,
                    params={"id": f"eq.{endpoint_id}", "user_id": f"eq.{user_id}"}
                )
            return {"success": response.status_code in [200, 204]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_endpoints(self, user_id: str) -> List[Dict]:
        """Get all webhook endpoints for a user."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/webhook_endpoints",
                    headers=self.headers,
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "id,url,events,is_active,failure_count,last_triggered_at,description,created_at",
                        "order": "created_at.desc"
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting webhooks: {e}")
            return []

    async def get_delivery_logs(self, endpoint_id: str, user_id: str, limit: int = 50) -> List[Dict]:
        """Get delivery logs for a webhook endpoint."""
        try:
            # Verify ownership
            async with httpx.AsyncClient() as client:
                check = await client.get(
                    f"{self.supabase_url}/rest/v1/webhook_endpoints",
                    headers=self.headers,
                    params={"id": f"eq.{endpoint_id}", "user_id": f"eq.{user_id}", "select": "id"}
                )
                if check.status_code != 200 or not check.json():
                    return []

                response = await client.get(
                    f"{self.supabase_url}/rest/v1/webhook_deliveries",
                    headers=self.headers,
                    params={
                        "webhook_endpoint_id": f"eq.{endpoint_id}",
                        "select": "id,event_type,response_status,delivered,attempt_count,error_message,created_at",
                        "order": "created_at.desc",
                        "limit": str(limit)
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting delivery logs: {e}")
            return []

    async def trigger_event(self, event_type: str, payload: Dict, user_id: str = None):
        """Trigger a webhook event for all matching endpoints."""
        try:
            params = {
                "is_active": "eq.true",
                "select": "*"
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/webhook_endpoints",
                    headers=self.headers,
                    params=params
                )

            if response.status_code != 200:
                return

            endpoints = response.json()

            for endpoint in endpoints:
                events = endpoint.get("events", [])
                if isinstance(events, str):
                    events = json.loads(events)

                if event_type in events:
                    # If user_id specified, only trigger for that user's endpoints
                    if user_id and endpoint.get("user_id") != user_id:
                        continue
                    await self._deliver(endpoint, event_type, payload)

        except Exception as e:
            logger.error(f"Error triggering webhook event: {e}")

    async def _deliver(self, endpoint: Dict, event_type: str, payload: Dict):
        """Deliver a webhook to an endpoint with retry."""
        try:
            secret = endpoint.get("secret", "")
            url = endpoint.get("url", "")
            endpoint_id = endpoint["id"]

            full_payload = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload
            }
            payload_str = json.dumps(full_payload, default=str)
            signature = self.sign_payload(payload_str, secret)

            # Create delivery record
            delivery_data = {
                "webhook_endpoint_id": endpoint_id,
                "event_type": event_type,
                "payload": payload_str,
                "attempt_count": 0,
                "delivered": False
            }

            async with httpx.AsyncClient() as client:
                create_resp = await client.post(
                    f"{self.supabase_url}/rest/v1/webhook_deliveries",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=delivery_data
                )

                delivery_id = None
                if create_resp.status_code in [200, 201]:
                    d = create_resp.json()
                    delivery_id = (d[0] if isinstance(d, list) else d).get("id")

            # Attempt delivery
            delivered = False
            response_status = None
            response_body = None
            error_message = None

            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=self.delivery_timeout) as client:
                        resp = await client.post(
                            url,
                            headers={
                                "Content-Type": "application/json",
                                "X-BinaApp-Signature": signature,
                                "X-BinaApp-Event": event_type,
                                "X-BinaApp-Delivery": delivery_id or ""
                            },
                            content=payload_str
                        )
                        response_status = resp.status_code
                        response_body = resp.text[:1000]

                        if 200 <= resp.status_code < 300:
                            delivered = True
                            break

                except Exception as deliver_err:
                    error_message = str(deliver_err)

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(2 ** attempt)

            # Update delivery record
            if delivery_id:
                async with httpx.AsyncClient() as client:
                    await client.patch(
                        f"{self.supabase_url}/rest/v1/webhook_deliveries",
                        headers={**self.headers, "Prefer": "return=minimal"},
                        params={"id": f"eq.{delivery_id}"},
                        json={
                            "delivered": delivered,
                            "response_status": response_status,
                            "response_body": response_body,
                            "attempt_count": self.max_retries if not delivered else 1,
                            "error_message": error_message
                        }
                    )

            # Update endpoint failure count
            if not delivered:
                new_failures = endpoint.get("failure_count", 0) + 1
                update = {"failure_count": new_failures, "last_triggered_at": datetime.utcnow().isoformat()}

                if new_failures >= self.max_failures:
                    update["is_active"] = False
                    logger.warning(f"Webhook endpoint {endpoint_id} deactivated after {new_failures} failures")

                async with httpx.AsyncClient() as client:
                    await client.patch(
                        f"{self.supabase_url}/rest/v1/webhook_endpoints",
                        headers={**self.headers, "Prefer": "return=minimal"},
                        params={"id": f"eq.{endpoint_id}"},
                        json=update
                    )
            else:
                async with httpx.AsyncClient() as client:
                    await client.patch(
                        f"{self.supabase_url}/rest/v1/webhook_endpoints",
                        headers={**self.headers, "Prefer": "return=minimal"},
                        params={"id": f"eq.{endpoint_id}"},
                        json={"last_triggered_at": datetime.utcnow().isoformat(), "failure_count": 0}
                    )

        except Exception as e:
            logger.error(f"Error delivering webhook: {e}")

    async def send_test(self, endpoint_id: str, user_id: str) -> Dict:
        """Send a test webhook event."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.supabase_url}/rest/v1/webhook_endpoints",
                    headers=self.headers,
                    params={"id": f"eq.{endpoint_id}", "user_id": f"eq.{user_id}", "select": "*"}
                )

            if resp.status_code != 200 or not resp.json():
                return {"success": False, "error": "Webhook tidak dijumpai"}

            endpoint = resp.json()[0]

            test_payload = {
                "test": True,
                "message": "Ini adalah webhook ujian dari BinaApp",
                "timestamp": datetime.utcnow().isoformat()
            }

            await self._deliver(endpoint, "test.ping", test_payload)
            return {"success": True, "message": "Webhook ujian dihantar"}

        except Exception as e:
            return {"success": False, "error": str(e)}


webhook_service = WebhookService()
