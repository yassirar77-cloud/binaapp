"""
AI Proactive Monitor Service
Background monitoring that checks for platform issues proactively.
Designed to be called by cron jobs or manual admin triggers.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from app.core.supabase import get_supabase_client


class AIProactiveMonitor:
    """
    Background monitoring service that checks for issues proactively.
    Designed to be called by a cron job or Supabase Edge Function.
    """

    async def run_all_checks(self) -> dict:
        """Master function - runs all monitoring checks."""
        results = {}
        checks = [
            ("stalled_orders", self.check_stalled_orders),
            ("payment_webhooks", self.check_payment_webhooks),
            ("website_uptime", self.check_website_uptime),
            ("restaurant_health", self.check_restaurant_health),
            ("subscription_expiry", self.check_subscription_expiry),
            ("credit_expiry", self.check_credit_expiry),
        ]

        for name, check_fn in checks:
            try:
                result = await check_fn()
                results[name] = {"status": "ok", "data": result}
            except Exception as e:
                logger.error(f"Monitor check '{name}' failed: {e}")
                results[name] = {"status": "error", "message": str(e)}

        return results

    async def check_stalled_orders(self) -> dict:
        """
        Find orders stuck in 'preparing' or 'ready' for too long.
        """
        supabase = get_supabase_client()
        events_created = 0

        try:
            # Orders stuck in 'preparing' for > 45 minutes
            cutoff_preparing = (datetime.utcnow() - timedelta(minutes=45)).isoformat()
            preparing_result = supabase.table("delivery_orders").select(
                "id, website_id, status, updated_at, customer_name, customer_phone"
            ).eq("status", "preparing").lt("updated_at", cutoff_preparing).execute()

            for order in (preparing_result.data or []):
                # Get website owner
                website_result = supabase.table("websites").select("user_id").eq("id", order["website_id"]).execute()
                user_id = website_result.data[0]["user_id"] if website_result.data else None

                if user_id:
                    await self._create_event(
                        user_id=user_id,
                        website_id=order.get("website_id"),
                        order_id=order["id"],
                        event_type="order_stuck",
                        description=f"Pesanan masih dalam status 'preparing' lebih 45 minit",
                        severity="warning",
                        details={"order_id": order["id"], "status": order["status"]},
                        action_taken="notified",
                    )
                    events_created += 1

            # Orders 'ready' with no rider for > 15 minutes
            cutoff_ready = (datetime.utcnow() - timedelta(minutes=15)).isoformat()
            ready_result = supabase.table("delivery_orders").select(
                "id, website_id, status, updated_at, rider_id"
            ).eq("status", "ready").is_("rider_id", "null").lt("updated_at", cutoff_ready).execute()

            for order in (ready_result.data or []):
                website_result = supabase.table("websites").select("user_id").eq("id", order["website_id"]).execute()
                user_id = website_result.data[0]["user_id"] if website_result.data else None

                if user_id:
                    await self._create_event(
                        user_id=user_id,
                        website_id=order.get("website_id"),
                        order_id=order["id"],
                        event_type="delivery_no_rider",
                        description=f"Pesanan siap tetapi tiada rider ditugaskan lebih 15 minit",
                        severity="warning",
                        details={"order_id": order["id"]},
                        action_taken="notified",
                    )
                    events_created += 1

        except Exception as e:
            logger.error(f"check_stalled_orders error: {e}")

        return {"events_created": events_created}

    async def check_payment_webhooks(self) -> dict:
        """
        Find orders where payment may have been made but webhook wasn't received.
        """
        supabase = get_supabase_client()
        events_created = 0

        try:
            cutoff = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
            pending_result = supabase.table("delivery_orders").select(
                "id, website_id, total_amount, created_at"
            ).eq("status", "pending_payment").lt("created_at", cutoff).execute()

            for order in (pending_result.data or []):
                website_result = supabase.table("websites").select("user_id").eq("id", order["website_id"]).execute()
                user_id = website_result.data[0]["user_id"] if website_result.data else None

                if user_id:
                    await self._create_event(
                        user_id=user_id,
                        website_id=order.get("website_id"),
                        order_id=order["id"],
                        event_type="payment_webhook_missing",
                        description=f"Pesanan menunggu pembayaran lebih 30 minit - mungkin webhook gagal",
                        severity="warning",
                        details={
                            "order_id": order["id"],
                            "total_amount": str(order.get("total_amount", 0)),
                        },
                        action_taken="notified",
                    )
                    events_created += 1

        except Exception as e:
            logger.error(f"check_payment_webhooks error: {e}")

        return {"events_created": events_created}

    async def check_website_uptime(self) -> dict:
        """
        Check that active websites have valid HTML content.
        """
        supabase = get_supabase_client()
        events_created = 0

        try:
            websites_result = supabase.table("websites").select(
                "id, user_id, html_content, subdomain, business_name"
            ).not_.is_("user_id", "null").execute()

            for website in (websites_result.data or []):
                html = website.get("html_content", "")
                is_broken = False
                reason = ""

                if not html or len(html.strip()) < 100:
                    is_broken = True
                    reason = "Kandungan HTML kosong atau terlalu pendek"
                elif "<body></body>" in html.replace(" ", "") or "<body/>" in html:
                    is_broken = True
                    reason = "Body HTML kosong"

                if is_broken:
                    # Check if event already exists in last 24h
                    since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
                    existing = supabase.table("ai_monitor_events").select("id").eq(
                        "website_id", website["id"]
                    ).eq("event_type", "website_down").gt("created_at", since).execute()

                    if not existing.data:
                        await self._create_event(
                            user_id=website["user_id"],
                            website_id=website["id"],
                            event_type="website_down",
                            description=f"Laman web '{website.get('business_name', '')}' tidak berfungsi: {reason}",
                            severity="critical",
                            details={"subdomain": website.get("subdomain", ""), "reason": reason},
                            action_taken="notified",
                        )
                        events_created += 1

        except Exception as e:
            logger.error(f"check_website_uptime error: {e}")

        return {"events_created": events_created}

    async def check_restaurant_health(self) -> dict:
        """Calculate and update health metrics for each restaurant."""
        supabase = get_supabase_client()
        updated = 0

        try:
            health_records = supabase.table("restaurant_health").select(
                "id, website_id, user_id"
            ).execute()

            since_30d = (datetime.utcnow() - timedelta(days=30)).isoformat()

            for record in (health_records.data or []):
                website_id = record["website_id"]
                user_id = record["user_id"]

                # Get order stats for last 30 days
                orders_result = supabase.table("delivery_orders").select(
                    "id, status, created_at, updated_at"
                ).eq("website_id", website_id).gt("created_at", since_30d).execute()

                orders = orders_result.data or []
                total_orders = len(orders)

                if total_orders == 0:
                    continue

                completed = sum(1 for o in orders if o.get("status") == "delivered")
                cancelled = sum(1 for o in orders if o.get("status") == "cancelled")

                # Check for disputes
                disputes_result = supabase.table("ai_disputes").select("id").eq(
                    "website_id", website_id
                ).gt("created_at", since_30d).execute()
                disputed = len(disputes_result.data or []) if disputes_result.data else 0

                fulfillment_rate = round((completed / total_orders) * 100, 2) if total_orders > 0 else 100.0
                complaint_rate = round((disputed / total_orders) * 100, 2) if total_orders > 0 else 0.0

                # Determine health status
                health_status = "healthy"
                if fulfillment_rate < 70 or complaint_rate > 30:
                    health_status = "warning"
                if fulfillment_rate < 50 or complaint_rate > 50:
                    health_status = "critical"

                update_data = {
                    "total_orders": total_orders,
                    "completed_orders": completed,
                    "cancelled_orders": cancelled,
                    "disputed_orders": disputed,
                    "fulfillment_rate": fulfillment_rate,
                    "complaint_rate": complaint_rate,
                    "health_status": health_status,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                supabase.table("restaurant_health").update(update_data).eq("id", record["id"]).execute()

                # Create events for unhealthy restaurants
                if health_status == "warning":
                    prev = record.get("health_status", "healthy")
                    if prev == "healthy":
                        await self._create_event(
                            user_id=user_id,
                            website_id=website_id,
                            event_type="high_complaint_rate",
                            description=f"Kadar aduan restoran meningkat ({complaint_rate}%). Sila semak pesanan anda.",
                            severity="warning",
                            details={
                                "fulfillment_rate": fulfillment_rate,
                                "complaint_rate": complaint_rate,
                            },
                            action_taken="notified",
                        )

                if health_status == "critical" and complaint_rate > 50 and fulfillment_rate < 50:
                    supabase.table("restaurant_health").update({
                        "auto_suspended": True,
                        "suspension_reason": f"Auto-suspended: fulfillment {fulfillment_rate}%, complaints {complaint_rate}%",
                        "suspension_sent_at": datetime.utcnow().isoformat(),
                    }).eq("id", record["id"]).execute()

                    await self._create_event(
                        user_id=user_id,
                        website_id=website_id,
                        event_type="high_complaint_rate",
                        description="Restoran digantung secara automatik kerana kadar aduan terlalu tinggi.",
                        severity="critical",
                        action_taken="escalated",
                    )

                updated += 1

        except Exception as e:
            logger.error(f"check_restaurant_health error: {e}")

        return {"restaurants_updated": updated}

    async def check_subscription_expiry(self) -> dict:
        """Find users whose subscription expires soon."""
        supabase = get_supabase_client()
        events_created = 0

        try:
            # Users expiring in 7 days
            in_7_days = (datetime.utcnow() + timedelta(days=7)).isoformat()
            now = datetime.utcnow().isoformat()

            profiles_result = supabase.table("profiles").select(
                "id, email, subscription_end"
            ).neq("plan", "free").gt("subscription_end", now).lt("subscription_end", in_7_days).execute()

            for profile in (profiles_result.data or []):
                # Check if already notified
                since = (datetime.utcnow() - timedelta(days=3)).isoformat()
                existing = supabase.table("ai_monitor_events").select("id").eq(
                    "user_id", profile["id"]
                ).eq("event_type", "subscription_expiring").gt("created_at", since).execute()

                if not existing.data:
                    await self._create_event(
                        user_id=profile["id"],
                        event_type="subscription_expiring",
                        description="Langganan anda akan tamat tempoh dalam masa 7 hari. Sila perbaharui untuk terus menggunakan semua ciri.",
                        severity="warning",
                        details={"subscription_end": profile.get("subscription_end", "")},
                        action_taken="notified",
                    )
                    events_created += 1

        except Exception as e:
            logger.error(f"check_subscription_expiry error: {e}")

        return {"events_created": events_created}

    async def check_credit_expiry(self) -> dict:
        """Process expired credits."""
        supabase = get_supabase_client()
        processed = 0

        try:
            now = datetime.utcnow().isoformat()

            # Find expired earned credits
            expired_result = supabase.table("credit_transactions").select(
                "id, user_id, amount"
            ).eq("type", "earned").lt("expires_at", now).eq("status", "active").execute()

            # Aggregate by user
            user_totals: dict[str, float] = {}
            for txn in (expired_result.data or []):
                uid = txn["user_id"]
                user_totals[uid] = user_totals.get(uid, 0) + float(txn.get("amount", 0))

            for user_id, total_expired in user_totals.items():
                if total_expired <= 0:
                    continue

                # Deduct from wallet
                wallet_result = supabase.table("bina_credits").select("balance").eq("user_id", user_id).execute()
                if wallet_result.data:
                    current_balance = float(wallet_result.data[0].get("balance", 0))
                    new_balance = max(0, current_balance - total_expired)
                    supabase.table("bina_credits").update({"balance": new_balance}).eq("user_id", user_id).execute()

                    # Create expired transaction
                    supabase.table("credit_transactions").insert({
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "type": "expired",
                        "amount": -total_expired,
                        "description": f"Kredit tamat tempoh: -RM{total_expired:.2f}",
                    }).execute()

                    await self._create_event(
                        user_id=user_id,
                        event_type="unusual_activity",
                        description=f"RM{total_expired:.2f} BinaCredit telah tamat tempoh.",
                        severity="info",
                        details={"expired_amount": total_expired},
                        action_taken="notified",
                    )
                    processed += 1

        except Exception as e:
            logger.error(f"check_credit_expiry error: {e}")

        return {"users_processed": processed}

    async def _create_event(
        self,
        user_id: str,
        event_type: str,
        description: str,
        severity: str = "info",
        website_id: Optional[str] = None,
        order_id: Optional[str] = None,
        details: Optional[dict] = None,
        action_taken: str = "notified",
        action_details: Optional[str] = None,
        credit_awarded: float = 0.0,
    ) -> dict:
        """Create a monitor event record."""
        supabase = get_supabase_client()
        event_data = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": event_type,
            "description": description,
            "severity": severity,
            "details": details,
            "action_taken": action_taken,
            "action_details": action_details,
            "credit_awarded": credit_awarded,
        }
        if website_id:
            event_data["website_id"] = website_id
        if order_id:
            event_data["order_id"] = order_id

        result = supabase.table("ai_monitor_events").insert(event_data).execute()
        return result.data[0] if result.data else event_data

    async def get_user_events(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> dict:
        """Get monitor events for a user."""
        supabase = get_supabase_client()

        query = supabase.table("ai_monitor_events").select("*").eq("user_id", user_id)

        if event_type:
            query = query.eq("event_type", event_type)
        if severity:
            query = query.eq("severity", severity)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        # Get total count
        count_query = supabase.table("ai_monitor_events").select("id", count="exact").eq("user_id", user_id)
        if event_type:
            count_query = count_query.eq("event_type", event_type)
        if severity:
            count_query = count_query.eq("severity", severity)
        count_result = count_query.execute()

        return {
            "events": result.data or [],
            "total": count_result.count if hasattr(count_result, "count") else len(result.data or []),
        }

    async def acknowledge_event(self, event_id: str, user_id: str) -> dict:
        """Mark an event as acknowledged."""
        supabase = get_supabase_client()
        supabase.table("ai_monitor_events").update({
            "acknowledged": True,
            "acknowledged_at": datetime.utcnow().isoformat(),
        }).eq("id", event_id).eq("user_id", user_id).execute()
        return {"message": "Event acknowledged"}

    async def get_monitoring_summary(self, user_id: str) -> dict:
        """Get monitoring summary for a user."""
        supabase = get_supabase_client()

        # Unacknowledged counts by severity
        events_result = supabase.table("ai_monitor_events").select(
            "severity"
        ).eq("user_id", user_id).eq("acknowledged", False).execute()

        events = events_result.data or []
        summary = {
            "total_unread": len(events),
            "critical": sum(1 for e in events if e.get("severity") == "critical"),
            "warning": sum(1 for e in events if e.get("severity") == "warning"),
            "info": sum(1 for e in events if e.get("severity") == "info"),
        }

        # Restaurant health
        health_result = supabase.table("restaurant_health").select("*").eq("user_id", user_id).execute()
        summary["restaurant_health"] = health_result.data or []

        return summary


# Singleton instance
proactive_monitor = AIProactiveMonitor()
