"""
BinaApp User Trust Score Service
Calculates user trust score (0-1000) based on behavior.
Affects credit multiplier in disputes.
"""
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class TrustScoreService:
    """Manages user trust scores and credit multipliers."""

    # Trust levels and their multipliers
    TRUST_LEVELS = {
        "low": {"min": 0, "max": 199, "multiplier": 0.5},
        "new": {"min": 200, "max": 399, "multiplier": 0.8},
        "standard": {"min": 400, "max": 599, "multiplier": 1.0},
        "trusted": {"min": 600, "max": 799, "multiplier": 1.2},
        "premium": {"min": 800, "max": 1000, "multiplier": 1.5}
    }

    # Score factors
    POSITIVE_FACTORS = {
        "successful_order": 5,
        "subscription_month": 10,
        "referral": 15,
        "legitimate_dispute": 8,
        "account_age_month": 3
    }

    NEGATIVE_FACTORS = {
        "fraudulent_dispute": -50,
        "rejected_dispute": -20,
        "payment_failure": -15,
        "terms_violation": -30
    }

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }

    def _get_trust_level(self, score: int) -> str:
        """Get trust level from score."""
        for level, config in self.TRUST_LEVELS.items():
            if config["min"] <= score <= config["max"]:
                return level
        return "new"

    def _get_multiplier(self, score: int) -> float:
        """Get credit multiplier from score."""
        level = self._get_trust_level(score)
        return self.TRUST_LEVELS[level]["multiplier"]

    async def get_user_score(self, user_id: str) -> Dict[str, Any]:
        """Get user's trust score with breakdown."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/user_trust_scores",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "*"}
                )

            if response.status_code == 200 and response.json():
                score_data = response.json()[0]
                score = score_data.get("score", 400)
                level = self._get_trust_level(score)
                multiplier = self._get_multiplier(score)

                # Get score history
                history = await self._get_history(user_id)

                return {
                    **score_data,
                    "trust_level": level,
                    "credit_multiplier": multiplier,
                    "level_config": self.TRUST_LEVELS[level],
                    "all_levels": self.TRUST_LEVELS,
                    "history": history[:20]
                }

            # No score yet - calculate and create
            return await self.calculate_score(user_id)

        except Exception as e:
            logger.error(f"Error getting trust score: {e}")
            return {
                "score": 400,
                "trust_level": "new",
                "credit_multiplier": 0.8,
                "error": str(e)
            }

    async def get_trust_level(self, user_id: str) -> Dict[str, Any]:
        """Get just the trust level and multiplier."""
        score_data = await self.get_user_score(user_id)
        return {
            "score": score_data.get("score", 400),
            "trust_level": score_data.get("trust_level", "new"),
            "credit_multiplier": score_data.get("credit_multiplier", 0.8)
        }

    async def calculate_score(self, user_id: str) -> Dict[str, Any]:
        """Calculate or recalculate trust score for a user."""
        try:
            factors = {
                "successful_orders": 0,
                "subscription_months": 0,
                "referral_count": 0,
                "legitimate_disputes": 0,
                "fraudulent_disputes": 0,
                "rejected_disputes": 0,
                "payment_failures": 0,
                "terms_violations": 0
            }

            async with httpx.AsyncClient() as client:
                # Count successful orders
                orders_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/delivery_orders",
                    headers={**self.headers, "Prefer": "count=exact"},
                    params={
                        "select": "id",
                        "or": f"(customer_id.eq.{user_id},user_id.eq.{user_id})",
                        "status": "eq.delivered"
                    }
                )
                if orders_resp.status_code == 200:
                    count_h = orders_resp.headers.get("content-range", "")
                    if "/" in count_h:
                        c = count_h.split("/")[1]
                        factors["successful_orders"] = int(c) if c != "*" else len(orders_resp.json())
                    else:
                        factors["successful_orders"] = len(orders_resp.json())

                # Check subscription months
                sub_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/subscriptions",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "created_at,status"}
                )
                if sub_resp.status_code == 200 and sub_resp.json():
                    sub = sub_resp.json()[0]
                    if sub.get("status") == "active":
                        created = datetime.fromisoformat(sub["created_at"].replace("Z", "+00:00"))
                        months = max(1, (datetime.now(created.tzinfo) - created).days // 30)
                        factors["subscription_months"] = months

                # Count referrals
                ref_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/referral_codes",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "total_referrals"}
                )
                if ref_resp.status_code == 200 and ref_resp.json():
                    factors["referral_count"] = ref_resp.json()[0].get("total_referrals", 0)

                # Account age
                profile_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/profiles",
                    headers=self.headers,
                    params={"id": f"eq.{user_id}", "select": "created_at"}
                )
                account_months = 1
                if profile_resp.status_code == 200 and profile_resp.json():
                    created = datetime.fromisoformat(
                        profile_resp.json()[0]["created_at"].replace("Z", "+00:00")
                    )
                    account_months = max(1, (datetime.now(created.tzinfo) - created).days // 30)

            # Calculate score
            score = 400  # Base score for new users

            # Positive
            score += factors["successful_orders"] * self.POSITIVE_FACTORS["successful_order"]
            score += factors["subscription_months"] * self.POSITIVE_FACTORS["subscription_month"]
            score += factors["referral_count"] * self.POSITIVE_FACTORS["referral"]
            score += factors["legitimate_disputes"] * self.POSITIVE_FACTORS["legitimate_dispute"]
            score += account_months * self.POSITIVE_FACTORS["account_age_month"]

            # Negative
            score += factors["fraudulent_disputes"] * abs(self.NEGATIVE_FACTORS["fraudulent_dispute"])
            score += factors["rejected_disputes"] * abs(self.NEGATIVE_FACTORS["rejected_dispute"])
            score += factors["payment_failures"] * abs(self.NEGATIVE_FACTORS["payment_failure"])
            score += factors["terms_violations"] * abs(self.NEGATIVE_FACTORS["terms_violation"])

            # Clamp
            score = max(0, min(1000, score))
            level = self._get_trust_level(score)
            multiplier = self._get_multiplier(score)

            # Upsert trust score
            score_data = {
                "user_id": user_id,
                "score": score,
                "trust_level": level,
                "credit_multiplier": multiplier,
                **factors,
                "last_calculated_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            async with httpx.AsyncClient() as client:
                # Check if exists
                existing = await client.get(
                    f"{self.supabase_url}/rest/v1/user_trust_scores",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "id,score"}
                )

                if existing.status_code == 200 and existing.json():
                    old_score = existing.json()[0].get("score", 400)
                    await client.patch(
                        f"{self.supabase_url}/rest/v1/user_trust_scores",
                        headers={**self.headers, "Prefer": "return=minimal"},
                        params={"user_id": f"eq.{user_id}"},
                        json=score_data
                    )
                    # Record history if changed
                    if old_score != score:
                        await self._record_history(user_id, old_score, score, "Pengiraan semula")
                else:
                    score_data["created_at"] = datetime.utcnow().isoformat()
                    await client.post(
                        f"{self.supabase_url}/rest/v1/user_trust_scores",
                        headers={**self.headers, "Prefer": "return=minimal"},
                        json=score_data
                    )
                    await self._record_history(user_id, 0, score, "Skor awal")

            return {
                **score_data,
                "level_config": self.TRUST_LEVELS[level],
                "all_levels": self.TRUST_LEVELS,
                "history": []
            }

        except Exception as e:
            logger.error(f"Error calculating trust score: {e}")
            return {"score": 400, "trust_level": "new", "credit_multiplier": 0.8}

    async def _record_history(self, user_id: str, old_score: int, new_score: int, reason: str):
        """Record score change in history."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.supabase_url}/rest/v1/trust_score_history",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    json={
                        "user_id": user_id,
                        "old_score": old_score,
                        "new_score": new_score,
                        "change_reason": reason,
                        "change_amount": new_score - old_score
                    }
                )
        except Exception as e:
            logger.error(f"Error recording trust history: {e}")

    async def _get_history(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get trust score history."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/trust_score_history",
                    headers=self.headers,
                    params={
                        "user_id": f"eq.{user_id}",
                        "select": "*",
                        "order": "created_at.desc",
                        "limit": str(limit)
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting trust history: {e}")
            return []

    async def batch_recalculate(self) -> Dict[str, int]:
        """Batch recalculate trust scores for all users."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/profiles",
                    headers=self.headers,
                    params={"select": "id", "limit": "1000"}
                )

            if response.status_code != 200:
                return {"processed": 0, "errors": 0}

            users = response.json()
            processed = 0
            errors = 0

            for user in users:
                try:
                    await self.calculate_score(user["id"])
                    processed += 1
                except Exception:
                    errors += 1

            logger.info(f"Trust score batch: {processed} processed, {errors} errors")
            return {"processed": processed, "errors": errors}

        except Exception as e:
            logger.error(f"Error in batch recalculate: {e}")
            return {"processed": 0, "errors": 1}

    async def get_all_scores(self, limit: int = 100) -> List[Dict]:
        """Admin: Get all trust scores."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/user_trust_scores",
                    headers=self.headers,
                    params={
                        "select": "*",
                        "order": "score.desc",
                        "limit": str(limit)
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting all scores: {e}")
            return []


trust_score_service = TrustScoreService()
