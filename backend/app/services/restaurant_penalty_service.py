"""
BinaApp Restaurant Penalty Service
Auto-penalizes restaurants with high complaint rates.
Penalty tiers: warning -> fine -> suspension -> permanent ban.
"""
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class RestaurantPenaltyService:
    """Manages restaurant penalties and appeals."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        # Penalty thresholds
        self.thresholds = {
            "warning": 0.20,       # >20% complaint rate
            "fine": 0.30,          # >30%
            "suspension": 0.50,    # >50%
            "permanent_ban": 0.70  # >70%
        }
        self.fine_amount = 10.00

    async def check_and_penalize(self, website_id: str, user_id: str) -> Optional[Dict]:
        """Check complaint rate and apply appropriate penalty."""
        try:
            rate = await self._get_complaint_rate(website_id)
            if rate is None:
                return None

            # Determine penalty level
            penalty_type = None
            if rate > self.thresholds["permanent_ban"]:
                penalty_type = "permanent_ban"
            elif rate > self.thresholds["suspension"]:
                penalty_type = "suspension"
            elif rate > self.thresholds["fine"]:
                penalty_type = "fine"
            elif rate > self.thresholds["warning"]:
                penalty_type = "warning"

            if not penalty_type:
                return None

            # Check if already penalized at this level
            async with httpx.AsyncClient() as client:
                existing = await client.get(
                    f"{self.supabase_url}/rest/v1/restaurant_penalties",
                    headers=self.headers,
                    params={
                        "website_id": f"eq.{website_id}",
                        "penalty_type": f"eq.{penalty_type}",
                        "is_active": "eq.true",
                        "select": "id"
                    }
                )
                if existing.status_code == 200 and existing.json():
                    return None  # Already penalized at this level

            return await self._create_penalty(website_id, user_id, penalty_type, rate)

        except Exception as e:
            logger.error(f"Error checking penalties: {e}")
            return None

    async def _get_complaint_rate(self, website_id: str) -> Optional[float]:
        """Calculate complaint rate for a restaurant."""
        try:
            async with httpx.AsyncClient() as client:
                # Get total orders
                orders_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/delivery_orders",
                    headers={**self.headers, "Prefer": "count=exact"},
                    params={"website_id": f"eq.{website_id}", "select": "id"}
                )

                total_orders = 0
                if orders_resp.status_code == 200:
                    count_header = orders_resp.headers.get("content-range", "")
                    if "/" in count_header:
                        total_str = count_header.split("/")[1]
                        total_orders = int(total_str) if total_str != "*" else len(orders_resp.json())
                    else:
                        total_orders = len(orders_resp.json())

                if total_orders < 10:
                    return None  # Not enough orders to calculate

                # Get disputes count
                disputes_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/order_verifications",
                    headers={**self.headers, "Prefer": "count=exact"},
                    params={
                        "website_id": f"eq.{website_id}",
                        "verification_status": "eq.issues_found",
                        "select": "id"
                    }
                )

                complaints = 0
                if disputes_resp.status_code == 200:
                    count_header = disputes_resp.headers.get("content-range", "")
                    if "/" in count_header:
                        total_str = count_header.split("/")[1]
                        complaints = int(total_str) if total_str != "*" else len(disputes_resp.json())
                    else:
                        complaints = len(disputes_resp.json())

                return complaints / total_orders if total_orders > 0 else 0

        except Exception as e:
            logger.error(f"Error calculating complaint rate: {e}")
            return None

    async def _create_penalty(self, website_id: str, user_id: str, penalty_type: str, rate: float) -> Dict:
        """Create a penalty record."""
        try:
            reasons = {
                "warning": f"Kadar aduan tinggi ({rate*100:.1f}%). Sila perbaiki kualiti perkhidmatan.",
                "fine": f"Kadar aduan sangat tinggi ({rate*100:.1f}%). Denda RM{self.fine_amount:.2f} dikenakan.",
                "suspension": f"Kadar aduan kritikal ({rate*100:.1f}%). Akaun digantung sementara.",
                "permanent_ban": f"Kadar aduan melampau ({rate*100:.1f}%). Akaun diharamkan."
            }

            expires_at = None
            if penalty_type == "suspension":
                expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()

            penalty_data = {
                "website_id": website_id,
                "user_id": user_id,
                "penalty_type": penalty_type,
                "reason": reasons.get(penalty_type, "Pelanggaran dasar"),
                "complaint_rate": rate * 100,
                "fine_amount": self.fine_amount if penalty_type == "fine" else 0,
                "is_active": True,
                "expires_at": expires_at
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/restaurant_penalties",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=penalty_data
                )

            if response.status_code in [200, 201]:
                data = response.json()
                return data[0] if isinstance(data, list) else data

            return penalty_data
        except Exception as e:
            logger.error(f"Error creating penalty: {e}")
            return {"error": str(e)}

    async def get_user_penalties(self, user_id: str) -> List[Dict]:
        """Get penalties for a user."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/restaurant_penalties",
                    headers=self.headers,
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "*",
                        "order": "created_at.desc"
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting penalties: {e}")
            return []

    async def submit_appeal(self, penalty_id: str, user_id: str, reason: str, evidence: str = None) -> Dict:
        """Submit an appeal for a penalty."""
        try:
            # Verify penalty belongs to user
            async with httpx.AsyncClient() as client:
                check = await client.get(
                    f"{self.supabase_url}/rest/v1/restaurant_penalties",
                    headers=self.headers,
                    params={"id": f"eq.{penalty_id}", "user_id": f"eq.{user_id}", "select": "id,is_active"}
                )
                if check.status_code != 200 or not check.json():
                    return {"success": False, "error": "Penalti tidak dijumpai"}

                if not check.json()[0].get("is_active"):
                    return {"success": False, "error": "Penalti sudah tidak aktif"}

                # Check for existing appeal
                existing = await client.get(
                    f"{self.supabase_url}/rest/v1/penalty_appeals",
                    headers=self.headers,
                    params={
                        "penalty_id": f"eq.{penalty_id}",
                        "status": "in.(pending,reviewing)",
                        "select": "id"
                    }
                )
                if existing.status_code == 200 and existing.json():
                    return {"success": False, "error": "Rayuan sudah dikemukakan"}

                # Create appeal
                appeal_data = {
                    "penalty_id": penalty_id,
                    "user_id": user_id,
                    "appeal_reason": reason,
                    "supporting_evidence": evidence,
                    "status": "pending"
                }

                response = await client.post(
                    f"{self.supabase_url}/rest/v1/penalty_appeals",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=appeal_data
                )

            if response.status_code in [200, 201]:
                data = response.json()
                return {"success": True, "appeal": data[0] if isinstance(data, list) else data}

            return {"success": False, "error": "Gagal menghantar rayuan"}
        except Exception as e:
            logger.error(f"Error submitting appeal: {e}")
            return {"success": False, "error": str(e)}

    async def get_all_penalties(self, limit: int = 50) -> List[Dict]:
        """Admin: Get all penalties."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/restaurant_penalties",
                    headers=self.headers,
                    params={
                        "select": "*",
                        "order": "created_at.desc",
                        "limit": str(limit)
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting all penalties: {e}")
            return []

    async def resolve_penalty(self, penalty_id: str, resolved_by: str, note: str = "") -> Dict:
        """Admin: Resolve/revoke a penalty."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.supabase_url}/rest/v1/restaurant_penalties",
                    headers={**self.headers, "Prefer": "return=representation"},
                    params={"id": f"eq.{penalty_id}"},
                    json={
                        "is_active": False,
                        "resolved_at": datetime.utcnow().isoformat(),
                        "resolved_by": resolved_by,
                        "resolution_note": note
                    }
                )
            if response.status_code in [200, 204]:
                return {"success": True}
            return {"success": False}
        except Exception as e:
            logger.error(f"Error resolving penalty: {e}")
            return {"success": False, "error": str(e)}


restaurant_penalty_service = RestaurantPenaltyService()
