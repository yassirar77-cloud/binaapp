"""Encryption at rest for third-party OAuth tokens.

Fernet (AES-128-CBC + HMAC-SHA256) from the ``cryptography`` package. The key
comes from ``TIKTOK_TOKEN_ENCRYPTION_KEY`` when set (a standard Fernet key),
otherwise it is derived from the TikTok client secret with SHA-256. The
derived path keeps the env-var list short for the first deployment; the
trade-off is that rotating the client secret invalidates stored tokens and
the account has to be reconnected, which the account endpoint reports as
``reauth_required`` rather than crashing.

Nothing in this module logs a plaintext or ciphertext token.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class TokenVaultError(RuntimeError):
    """Raised when the vault is not configured or a ciphertext is unreadable."""


_DERIVATION_SALT = b"binaapp-social-token-vault:v1:"


def _fernet() -> Fernet:
    explicit = (settings.TIKTOK_TOKEN_ENCRYPTION_KEY or "").strip()
    if explicit:
        try:
            return Fernet(explicit.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise TokenVaultError(
                "TIKTOK_TOKEN_ENCRYPTION_KEY is not a valid Fernet key "
                "(generate one with Fernet.generate_key())"
            ) from exc

    secret = (settings.TIKTOK_CLIENT_SECRET or "").strip()
    if not secret:
        raise TokenVaultError(
            "Token vault not configured: set TIKTOK_TOKEN_ENCRYPTION_KEY or TIKTOK_CLIENT_SECRET"
        )
    digest = hashlib.sha256(_DERIVATION_SALT + secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_token(plaintext: str) -> str:
    """Return the Fernet ciphertext (URL-safe text) for ``plaintext``."""
    if not isinstance(plaintext, str) or not plaintext:
        raise TokenVaultError("Refusing to encrypt an empty token")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_token(ciphertext: str) -> str:
    """Return the plaintext for a ciphertext produced by ``encrypt_token``."""
    if not ciphertext:
        raise TokenVaultError("Empty ciphertext")
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise TokenVaultError(
            "Stored token cannot be decrypted (encryption key changed?) — reconnect the account"
        ) from exc
