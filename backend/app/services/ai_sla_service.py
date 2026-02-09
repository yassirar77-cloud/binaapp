"""
BinaApp AI SLA Service
Monitors SLA compliance and auto-compensates breaches.
"""
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class SLAService:
    """Monitors SLA compliance and auto-compensates breaches."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

    async def get_sla_for_plan(self, plan_name: str) -> Optional[Dict[str, Any]]:
        """Get SLA definition for a subscription plan."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/sla_definitions",
                    headers=self.headers,
                    params={"plan_name": f"eq.{plan_name}", "select": "*"}
                )
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            return None
        except Exception as e:
            logger.error(f"Error getting SLA for plan {plan_name}: {e}")
            return None

    async def get_user_plan(self, user_id: str) -> str:
        """Get user's subscription plan from subscriptions table."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/subscriptions",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "tier,status"}
                )
            if response.status_code == 200:
                data = response.json()
                if data and data[0].get("status") == "active":
                    return data[0].get("tier", "free")
            return "free"
        except Exception as e:
            logger.error(f"Error getting user plan: {e}")
            return "free"

    async def get_user_sla(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's SLA based on their subscription plan."""
        plan = await self.get_user_plan(user_id)
        if plan == "free":
            return {
                "plan_name": "free",
                "max_response_time_hours": 48,
                "max_downtime_minutes": 240,
                "max_build_time_minutes": 60,
                "uptime_guarantee_percent": 90.0,
                "credit_compensation_amount": 0,
                "description": "Pelan Percuma - Tiada jaminan SLA"
            }
        return await self.get_sla_for_plan(plan)

    async def get_breaches(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's SLA breach history."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/sla_breaches",
                    headers=self.headers,
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "*,sla_definitions(plan_name)",
                        "order": "created_at.desc",
                        "limit": str(limit)
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting SLA breaches: {e}")
            return []

    async def get_compliance_report(self, user_id: str) -> Dict[str, Any]:
        """Get current month SLA compliance report."""
        now = datetime.utcnow()
        month_year = now.strftime("%Y-%m")

        sla = await self.get_user_sla(user_id)
        breaches = await self.get_breaches(user_id)

        # Filter current month breaches
        current_breaches = [b for b in breaches if b.get("month_year") == month_year]

        # Calculate compliance
        total_checks = max(len(current_breaches) + 10, 10)  # Estimate total checks
        compliance_rate = ((total_checks - len(current_breaches)) / total_checks) * 100

        total_credits = sum(float(b.get("credit_awarded", 0)) for b in current_breaches)

        return {
            "month": month_year,
            "sla_definition": sla,
            "compliance_rate": round(compliance_rate, 2),
            "total_breaches": len(current_breaches),
            "breaches_by_type": self._group_breaches_by_type(current_breaches),
            "total_credits_awarded": total_credits,
            "breaches": current_breaches[:10]
        }

    def _group_breaches_by_type(self, breaches: list) -> Dict[str, int]:
        """Group breaches by type."""
        groups = {}
        for b in breaches:
            t = b.get("breach_type", "unknown")
            groups[t] = groups.get(t, 0) + 1
        return groups

    async def check_and_record_breach(
        self,
        user_id: str,
        breach_type: str,
        expected_value: float,
        actual_value: float,
        description: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Check if a metric breaches SLA and record if so."""
        try:
            sla = await self.get_user_sla(user_id)
            if not sla or sla.get("plan_name") == "free":
                return None

            now = datetime.utcnow()
            month_year = now.strftime("%Y-%m")

            # Check if already breached for this type this month
            async with httpx.AsyncClient() as client:
                existing = await client.get(
                    f"{self.supabase_url}/rest/v1/sla_breaches",
                    headers=self.headers,
                    params={
                        "user_id": f"eq.{user_id}",
                        "breach_type": f"eq.{breach_type}",
                        "month_year": f"eq.{month_year}",
                        "select": "id"
                    }
                )

            if existing.status_code == 200 and len(existing.json()) > 0:
                logger.info(f"SLA breach already recorded for {user_id}/{breach_type}/{month_year}")
                return None

            credit_amount = float(sla.get("credit_compensation_amount", 0))

            breach_data = {
                "user_id": user_id,
                "sla_definition_id": sla.get("id"),
                "breach_type": breach_type,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "credit_awarded": credit_amount,
                "description": description or f"SLA breach: {breach_type}",
                "month_year": month_year,
                "auto_compensated": credit_amount > 0
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/sla_breaches",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=breach_data
                )

            if response.status_code in [200, 201]:
                breach = response.json()
                result = breach[0] if isinstance(breach, list) else breach

                # Auto-compensate with BinaCredit
                if credit_amount > 0:
                    await self._award_sla_credit(user_id, credit_amount, breach_type)

                logger.info(f"SLA breach recorded for {user_id}: {breach_type}")
                return result
            return None

        except Exception as e:
            logger.error(f"Error recording SLA breach: {e}")
            return None

    async def _award_sla_credit(self, user_id: str, amount: float, breach_type: str):
        """Award BinaCredit for SLA breach."""
        try:
            # Insert credit transaction
            transaction = {
                "user_id": user_id,
                "amount": amount,
                "transaction_type": "sla_compensation",
                "description": f"Pampasan SLA: {breach_type}",
                "status": "completed"
            }
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.supabase_url}/rest/v1/credit_transactions",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    json=transaction
                )

                # Update bina_credits balance
                # First get current balance
                balance_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/bina_credits",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "id,balance"}
                )

                if balance_resp.status_code == 200:
                    data = balance_resp.json()
                    if data:
                        new_balance = float(data[0].get("balance", 0)) + amount
                        await client.patch(
                            f"{self.supabase_url}/rest/v1/bina_credits",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            params={"user_id": f"eq.{user_id}"},
                            json={"balance": new_balance}
                        )
                    else:
                        await client.post(
                            f"{self.supabase_url}/rest/v1/bina_credits",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            json={"user_id": user_id, "balance": amount}
                        )

            logger.info(f"Awarded RM{amount} BinaCredit to {user_id} for SLA breach")
        except Exception as e:
            logger.error(f"Error awarding SLA credit: {e}")


sla_service = SLAService()
