"""
BinaApp Referral Service
Generates referral codes, validates usage, awards credits.
"""
import httpx
import re
import secrets
import string
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from loguru import logger

from app.core.config import settings


CODE_RE = re.compile(r"^BINA-[A-Z0-9]{4}-[A-Z0-9]{4}$")


def is_valid_code(code: Any) -> bool:
    """True for a well-formed BINA-XXXX-XXXX code (already upper-cased)."""
    return isinstance(code, str) and bool(CODE_RE.match(code))


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
        """Record that `referred_user_id` joined through `code` and credit both sides.

        referral_history has UNIQUE (referred_id), so an account can only ever
        be referred once: a second attempt (or a race between two requests)
        fails on the insert, before any credit is awarded.
        """
        try:
            code = (code or "").strip().upper()
            if not is_valid_code(code):
                return {"success": False, "error": "Kod rujukan tidak sah atau tidak aktif"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                code_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/referral_codes",
                    headers=self.headers,
                    params={"code": f"eq.{code}", "is_active": "eq.true", "select": "*"}
                )
                if code_resp.status_code != 200 or not code_resp.json():
                    return {"success": False, "error": "Kod rujukan tidak sah atau tidak aktif"}

                referral_code = code_resp.json()[0]
                referrer_id = referral_code["user_id"]

                if referrer_id == referred_user_id:
                    return {"success": False, "error": "Tidak boleh menggunakan kod rujukan sendiri"}

                use_resp = await client.post(
                    f"{self.supabase_url}/rest/v1/referral_history",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    json={
                        "referrer_id": referrer_id,
                        "referred_id": referred_user_id,
                        "referral_code": code,
                        "referrer_credit": self.referrer_credit,
                        "referred_credit": self.referred_credit,
                        "status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                if use_resp.status_code == 409:
                    return {"success": False, "error": "Anda sudah menggunakan kod rujukan"}
                if use_resp.status_code not in [200, 201, 204]:
                    logger.error(f"referral_history insert failed: {use_resp.status_code}")
                    return {"success": False, "error": "Gagal merekod rujukan"}

                new_total = int(referral_code.get("total_referrals") or 0) + 1
                new_credits = float(referral_code.get("total_credits_earned") or 0) + self.referrer_credit
                await client.patch(
                    f"{self.supabase_url}/rest/v1/referral_codes",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{referral_code['id']}"},
                    json={"total_referrals": new_total, "total_credits_earned": new_credits}
                )

            await self._award_credit(referrer_id, self.referrer_credit, "Bonus rujukan - rakan baru mendaftar")
            await self._award_credit(referred_user_id, self.referred_credit, "Bonus pendaftaran dengan kod rujukan")

            return {
                "success": True,
                "message": f"Kod rujukan berjaya! Anda menerima RM{self.referred_credit:.2f} BinaCredit",
                "referrer_credit": self.referrer_credit,
                "referred_credit": self.referred_credit
            }
        except Exception as e:
            logger.error(f"Error applying referral: {e}")
            return {"success": False, "error": "Ralat sistem"}

    async def apply_signup_referral(self, user_id: str) -> bool:
        """Apply the referral code a new account signed up with, if any.

        Called once the account's email is verified (not at registration), so
        a referral only pays out for an account with a real inbox. The code
        was stored on profiles.signup_ref_code by the register endpoint.
        Never raises: a referral problem must not fail email verification.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.supabase_url}/rest/v1/profiles",
                    headers=self.headers,
                    params={"id": f"eq.{user_id}", "select": "signup_ref_code"}
                )
            if resp.status_code != 200 or not resp.json():
                return False
            code = (resp.json()[0].get("signup_ref_code") or "").strip().upper()
            if not is_valid_code(code):
                return False
            result = await self.apply_referral(user_id, code)
            if result.get("success"):
                logger.info(f"Signup referral applied for {user_id}")
            return bool(result.get("success"))
        except Exception as e:
            logger.warning(f"Signup referral not applied for {user_id}: {type(e).__name__}")
            return False

    async def _award_credit(self, user_id: str, amount: float, description: str):
        """Add BinaCredit to a user's wallet and write the ledger row."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                wallet_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/bina_credits",
                    headers=self.headers,
                    params={"user_id": f"eq.{user_id}", "select": "id,balance,lifetime_earned"}
                )
                wallet = None
                if wallet_resp.status_code == 200 and wallet_resp.json():
                    wallet = wallet_resp.json()[0]
                else:
                    create_resp = await client.post(
                        f"{self.supabase_url}/rest/v1/bina_credits",
                        headers={**self.headers, "Prefer": "return=representation"},
                        json={"user_id": user_id, "balance": 0, "lifetime_earned": 0}
                    )
                    if create_resp.status_code in [200, 201] and create_resp.json():
                        data = create_resp.json()
                        wallet = data[0] if isinstance(data, list) else data
                if not wallet:
                    logger.error(f"No BinaCredit wallet for {user_id}; referral credit not awarded")
                    return

                before = float(wallet.get("balance") or 0)
                after = before + amount
                await client.patch(
                    f"{self.supabase_url}/rest/v1/bina_credits",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{wallet['id']}"},
                    json={
                        "balance": after,
                        "lifetime_earned": float(wallet.get("lifetime_earned") or 0) + amount,
                    }
                )
                # Columns and allowed values per credit_transactions' CHECKs:
                # type in (earned, spent, ...), source in (referral, ...).
                await client.post(
                    f"{self.supabase_url}/rest/v1/credit_transactions",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    json={
                        "user_id": user_id,
                        "wallet_id": wallet["id"],
                        "amount": amount,
                        "type": "earned",
                        "source": "referral",
                        "description": description,
                        "balance_before": before,
                        "balance_after": after,
                    }
                )

            logger.info(f"Awarded RM{amount} referral credit to {user_id}")
        except Exception as e:
            logger.error(f"Error awarding referral credit: {e}")

    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get referral stats for a user."""
        empty = {"code": None, "total_referrals": 0, "total_credits_earned": 0, "referrals": []}
        try:
            code = await self.get_or_create_code(user_id)
            if not code:
                return empty

            async with httpx.AsyncClient(timeout=10.0) as client:
                uses_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/referral_history",
                    headers=self.headers,
                    params={
                        "referrer_id": f"eq.{user_id}",
                        "select": "id,referrer_credit,status,created_at",
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
            return empty


referral_service = ReferralService()
