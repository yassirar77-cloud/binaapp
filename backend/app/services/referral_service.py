"""
BinaApp Referral Service
Generates referral codes, validates usage, awards credits.
"""
import httpx
import secrets
import string
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class ReferralService:
    """Manages referral codes and credit awards."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        self.referrer_credit = 5.00
        self.referred_credit = 5.00

    def _generate_code(self) -> str:
        """Generate unique referral code in BINA-xxxx-xxxx format."""
        chars = string.ascii_uppercase + string.digits
        part1 = ''.join(secrets.choice(chars) for _ in range(4))
        part2 = ''.join(secrets.choice(chars) for _ in range(4))
        return f"BINA-{part1}-{part2}"

    async def get_or_create_code(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get existing referral code or create new one."""
        try:
            async with httpx.AsyncClient() as client:
                # Check existing
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/referral_codes",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "*"}
                )

                if response.status_code == 200 and response.json():
                    return response.json()[0]

                # Generate new unique code
                code = self._generate_code()
                for _ in range(5):  # Retry if code collision
                    check = await client.get(
                        f"{self.supabase_url}/rest/v1/referral_codes",
                        headers=self.headers,
                        params={"code": f"eq.{code}", "select": "id"}
                    )
                    if check.status_code == 200 and not check.json():
                        break
                    code = self._generate_code()

                # Create code
                create_resp = await client.post(
                    f"{self.supabase_url}/rest/v1/referral_codes",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json={"user_id": user_id, "code": code}
                )

                if create_resp.status_code in [200, 201]:
                    data = create_resp.json()
                    return data[0] if isinstance(data, list) else data

            return None
        except Exception as e:
            logger.error(f"Error getting/creating referral code: {e}")
            return None

    async def apply_referral(self, referred_user_id: str, code: str) -> Dict[str, Any]:
        """Apply a referral code during signup."""
        try:
            async with httpx.AsyncClient() as client:
                # Find the referral code
                code_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/referral_codes",
                    headers=self.headers,
                    params={"code": f"eq.{code}", "is_active": "eq.true", "select": "*"}
                )

                if code_resp.status_code != 200 or not code_resp.json():
                    return {"success": False, "error": "Kod rujukan tidak sah atau tidak aktif"}

                referral_code = code_resp.json()[0]
                referrer_id = referral_code["user_id"]

                # Prevent self-referral
                if referrer_id == referred_user_id:
                    return {"success": False, "error": "Tidak boleh menggunakan kod rujukan sendiri"}

                # Check if referred user already used a code
                used_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/referral_uses",
                    headers=self.headers,
                    params={"referred_id": f"eq.{referred_user_id}", "select": "id"}
                )

                if used_resp.status_code == 200 and used_resp.json():
                    return {"success": False, "error": "Anda sudah menggunakan kod rujukan"}

                # Record the referral use
                use_resp = await client.post(
                    f"{self.supabase_url}/rest/v1/referral_uses",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json={
                        "referral_code_id": referral_code["id"],
                        "referrer_id": referrer_id,
                        "referred_id": referred_user_id,
                        "referrer_credit": self.referrer_credit,
                        "referred_credit": self.referred_credit
                    }
                )

                if use_resp.status_code not in [200, 201]:
                    return {"success": False, "error": "Gagal merekod rujukan"}

                # Update referral code stats
                new_total = referral_code.get("total_referrals", 0) + 1
                new_credits = float(referral_code.get("total_credits_earned", 0)) + self.referrer_credit
                await client.patch(
                    f"{self.supabase_url}/rest/v1/referral_codes",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{referral_code['id']}"},
                    json={"total_referrals": new_total, "total_credits_earned": new_credits}
                )

                # Award credits to both parties
                await self._award_credit(referrer_id, self.referrer_credit, f"Bonus rujukan - rakan baru mendaftar")
                await self._award_credit(referred_user_id, self.referred_credit, f"Bonus pendaftaran dengan kod rujukan")

            return {
                "success": True,
                "message": f"Kod rujukan berjaya! Anda menerima RM{self.referred_credit:.2f} BinaCredit",
                "referrer_credit": self.referrer_credit,
                "referred_credit": self.referred_credit
            }

        except Exception as e:
            logger.error(f"Error applying referral: {e}")
            return {"success": False, "error": "Ralat sistem"}

    async def _award_credit(self, user_id: str, amount: float, description: str):
        """Award BinaCredit to a user."""
        try:
            async with httpx.AsyncClient() as client:
                # Insert transaction
                await client.post(
                    f"{self.supabase_url}/rest/v1/credit_transactions",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    json={
                        "user_id": user_id,
                        "amount": amount,
                        "transaction_type": "referral_bonus",
                        "description": description,
                        "status": "completed"
                    }
                )

                # Update balance
                balance_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/bina_credits",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "id,balance"}
                )

                if balance_resp.status_code == 200:
                    data = balance_resp.json()
                    if data:
                        new_bal = float(data[0].get("balance", 0)) + amount
                        await client.patch(
                            f"{self.supabase_url}/rest/v1/bina_credits",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            params={"user_id": f"eq.{user_id}"},
                            json={"balance": new_bal}
                        )
                    else:
                        await client.post(
                            f"{self.supabase_url}/rest/v1/bina_credits",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            json={"user_id": user_id, "balance": amount}
                        )

            logger.info(f"Awarded RM{amount} referral credit to {user_id}")
        except Exception as e:
            logger.error(f"Error awarding referral credit: {e}")

    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get referral stats for a user."""
        try:
            code = await self.get_or_create_code(user_id)
            if not code:
                return {"code": None, "total_referrals": 0, "total_credits_earned": 0, "referrals": []}

            async with httpx.AsyncClient() as client:
                uses_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/referral_uses",
                    headers=self.headers,
                    params={
                        "referrer_id": f"eq.{user_id}",
                        "select": "id,referred_id,referrer_credit,status,created_at",
                        "order": "created_at.desc",
                        "limit": "50"
                    }
                )

                referrals = uses_resp.json() if uses_resp.status_code == 200 else []

            return {
                "code": code.get("code"),
                "total_referrals": code.get("total_referrals", 0),
                "total_credits_earned": float(code.get("total_credits_earned", 0)),
                "is_active": code.get("is_active", True),
                "referrals": referrals
            }
        except Exception as e:
            logger.error(f"Error getting referral stats: {e}")
            return {"code": None, "total_referrals": 0, "total_credits_earned": 0, "referrals": []}


referral_service = ReferralService()
