"""
Helpers for the email-verification 6-digit code flow.

Codes are random 6-digit numbers. We never store the code itself — only a
SHA-256 hash salted with the user id and the app's JWT secret. Brute force
is mitigated by: short TTL, a per-code attempt limit, and the fact that the
verify endpoint requires the user's own authenticated session.
"""

import hashlib
import hmac
import secrets

from app.core.config import settings


def generate_code() -> str:
    """Return a zero-padded 6-digit verification code (e.g. '042913')."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(user_id: str, code: str) -> str:
    """Deterministically hash a code bound to a specific user id."""
    secret = (settings.JWT_SECRET_KEY or "binaapp-verify").encode()
    msg = f"{user_id}:{code}".encode()
    return hashlib.sha256(secret + msg).hexdigest()


def verify_code(user_id: str, code: str, stored_hash: str) -> bool:
    """Constant-time check of a submitted code against the stored hash."""
    candidate = hash_code(user_id, (code or "").strip())
    return hmac.compare_digest(candidate, stored_hash or "")
