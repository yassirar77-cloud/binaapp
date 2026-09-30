"""Connected TikTok account storage, OAuth state handling and token refresh.

Tables (migration 058): ``tiktok_accounts``, ``tiktok_oauth_states``.

Tokens are written through ``token_vault`` and decrypted only inside
``get_valid_access_token``; nothing returned to a route handler carries a
token (see ``public_view``).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from loguru import logger

from app.core.config import settings
from app.services.social import tiktok_client
from app.services.social._db import db_delete, db_insert, db_select, db_update
from app.services.social.token_vault import TokenVaultError, decrypt_token, encrypt_token

ACCOUNTS = "tiktok_accounts"
STATES = "tiktok_oauth_states"

STATE_TTL = timedelta(minutes=10)
#: Refresh when the access token has less than this left (TikTok: ~24h life).
REFRESH_LEEWAY = timedelta(minutes=10)


class TikTokNotConfigured(RuntimeError):
    pass


class TikTokAuthRequired(RuntimeError):
    """The stored grant is unusable; the admin has to reconnect."""


class OAuthStateError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def require_config() -> Tuple[str, str, str]:
    key = (settings.TIKTOK_CLIENT_KEY or "").strip()
    secret = (settings.TIKTOK_CLIENT_SECRET or "").strip()
    redirect = (settings.TIKTOK_REDIRECT_URI or "").strip()
    if not key or not secret or not redirect:
        raise TikTokNotConfigured(
            "TikTok is not configured: set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET and TIKTOK_REDIRECT_URI"
        )
    return key, secret, redirect


def is_configured() -> bool:
    try:
        require_config()
        return True
    except TikTokNotConfigured:
        return False


# --------------------------------------------------------------------------
# OAuth state (CSRF)
# --------------------------------------------------------------------------

async def create_oauth_state(user_id: str, redirect_uri: str) -> str:
    state = secrets.token_urlsafe(32)
    now = _now()
    await db_insert(
        STATES,
        {
            "state": state,
            "user_id": user_id,
            "redirect_uri": redirect_uri,
            "created_at": _iso(now),
            "expires_at": _iso(now + STATE_TTL),
        },
    )
    # Opportunistic sweep so the table never grows unbounded.
    try:
        await db_delete(STATES, {}, extra={"expires_at": f"lt.{_iso(now)}"})
    except Exception as exc:  # noqa: BLE001 - sweeping is best-effort
        logger.debug("oauth state sweep skipped: {}", exc)
    return state


def check_oauth_state(row: Optional[Dict[str, Any]], user_id: str, now: Optional[datetime] = None) -> str:
    """Pure check used by ``consume_oauth_state``. Returns the redirect_uri."""
    now = now or _now()
    if not row:
        raise OAuthStateError("Unknown or already-used OAuth state")
    if str(row.get("user_id")) != str(user_id):
        raise OAuthStateError("OAuth state was issued to a different user")
    expires = _parse_ts(row.get("expires_at"))
    if not expires or expires < now:
        raise OAuthStateError("OAuth state expired — start the connection again")
    return str(row.get("redirect_uri") or "")


async def consume_oauth_state(state: str, user_id: str) -> str:
    """Validate and delete the state in one go (single use)."""
    if not state or len(state) > 128:
        raise OAuthStateError("Missing OAuth state")
    rows = await db_select(STATES, filters={"state": state})
    row = rows[0] if rows else None
    try:
        redirect_uri = check_oauth_state(row, user_id)
    finally:
        if row:
            await db_delete(STATES, {"state": state})
    return redirect_uri


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

def public_view(account: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The account as the admin UI sees it — no token material."""
    if not account:
        return None
    return {
        "id": account.get("id"),
        "open_id": account.get("open_id"),
        "username": account.get("username"),
        "display_name": account.get("display_name"),
        "avatar_url": account.get("avatar_url"),
        "scopes": [s for s in (account.get("scopes") or "").split(",") if s],
        "status": account.get("status"),
        "last_error": account.get("last_error"),
        "connected_at": account.get("connected_at"),
        "access_token_expires_at": account.get("access_token_expires_at"),
        "refresh_token_expires_at": account.get("refresh_token_expires_at"),
    }


async def get_account() -> Optional[Dict[str, Any]]:
    """The connected account (BinaApp has one). Revoked rows are ignored."""
    rows = await db_select(
        ACCOUNTS,
        extra={"status": "neq.revoked", "order": "connected_at.desc", "limit": "1"},
    )
    return rows[0] if rows else None


async def get_account_by_id(account_id: str) -> Optional[Dict[str, Any]]:
    rows = await db_select(ACCOUNTS, filters={"id": account_id})
    return rows[0] if rows else None


def _token_fields(token_payload: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    access = token_payload.get("access_token")
    refresh = token_payload.get("refresh_token")
    if not access or not refresh:
        raise TikTokAuthRequired("TikTok did not return a usable token pair")
    expires_in = int(token_payload.get("expires_in") or 86400)
    refresh_expires_in = int(token_payload.get("refresh_expires_in") or 0)
    fields: Dict[str, Any] = {
        "access_token_enc": encrypt_token(str(access)),
        "refresh_token_enc": encrypt_token(str(refresh)),
        "access_token_expires_at": _iso(now + timedelta(seconds=expires_in)),
        "updated_at": _iso(now),
    }
    if refresh_expires_in:
        fields["refresh_token_expires_at"] = _iso(now + timedelta(seconds=refresh_expires_in))
    if token_payload.get("scope"):
        fields["scopes"] = str(token_payload["scope"])
    return fields


async def connect_with_code(code: str, redirect_uri: str, user_id: str) -> Dict[str, Any]:
    """Exchange the code, fetch the profile and upsert the account row."""
    client_key, client_secret, _ = require_config()
    token_payload = await tiktok_client.exchange_code(client_key, client_secret, code, redirect_uri)
    open_id = str(token_payload.get("open_id") or "")
    if not open_id:
        raise TikTokAuthRequired("TikTok did not return an open_id")

    now = _now()
    row: Dict[str, Any] = {
        "open_id": open_id,
        "status": "connected",
        "last_error": None,
        "connected_by": user_id,
        "connected_at": _iso(now),
        **_token_fields(token_payload, now),
    }

    # Profile is best-effort: a hiccup here must not lose the grant.
    try:
        user = await tiktok_client.fetch_user_info(str(token_payload["access_token"]))
        row.update(
            {
                "union_id": user.get("union_id"),
                "display_name": user.get("display_name"),
                "avatar_url": user.get("avatar_large_url") or user.get("avatar_url_100") or user.get("avatar_url"),
            }
        )
    except tiktok_client.TikTokAPIError as exc:
        logger.warning("TikTok user.info failed after connect: {}", exc.code)

    account = await db_insert(ACCOUNTS, row, on_conflict="open_id")
    logger.info("TikTok account connected: open_id={} by user={}", open_id[:8] + "…", user_id)
    return account


async def refresh_profile(account: Dict[str, Any]) -> Dict[str, Any]:
    """Re-fetch display name / avatar (avatar URLs expire) and creator username."""
    token, account = await get_valid_access_token(account)
    patch: Dict[str, Any] = {"updated_at": _iso(_now())}
    try:
        user = await tiktok_client.fetch_user_info(token)
        patch.update(
            {
                "display_name": user.get("display_name") or account.get("display_name"),
                "avatar_url": user.get("avatar_large_url")
                or user.get("avatar_url_100")
                or user.get("avatar_url")
                or account.get("avatar_url"),
                "union_id": user.get("union_id") or account.get("union_id"),
            }
        )
    except tiktok_client.TikTokAPIError as exc:
        if exc.is_auth_error:
            await mark_reauth_required(account, exc.code)
            raise TikTokAuthRequired(exc.code)
        logger.warning("TikTok user.info refresh failed: {}", exc.code)
    rows = await db_update(ACCOUNTS, {"id": account["id"]}, patch)
    return rows[0] if rows else {**account, **patch}


async def mark_reauth_required(account: Dict[str, Any], reason: str) -> None:
    await db_update(
        ACCOUNTS,
        {"id": account["id"]},
        {"status": "reauth_required", "last_error": reason[:200], "updated_at": _iso(_now())},
    )


async def get_valid_access_token(account: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Decrypt the access token, refreshing first when it is (nearly) expired."""
    if account.get("status") == "reauth_required":
        raise TikTokAuthRequired(account.get("last_error") or "reauth_required")

    now = _now()
    expires_at = _parse_ts(account.get("access_token_expires_at"))
    try:
        if expires_at and expires_at - now > REFRESH_LEEWAY:
            return decrypt_token(account["access_token_enc"]), account
        refresh_token = decrypt_token(account["refresh_token_enc"])
    except TokenVaultError as exc:
        await mark_reauth_required(account, "token_vault_unreadable")
        raise TikTokAuthRequired(str(exc)) from exc

    client_key, client_secret, _ = require_config()
    try:
        payload = await tiktok_client.refresh_access_token(client_key, client_secret, refresh_token)
    except tiktok_client.TikTokAPIError as exc:
        logger.warning("TikTok token refresh failed: {}", exc.code)
        await mark_reauth_required(account, exc.code)
        raise TikTokAuthRequired(exc.code) from exc

    fields = _token_fields(payload, now)
    fields["status"] = "connected"
    fields["last_error"] = None
    rows = await db_update(ACCOUNTS, {"id": account["id"]}, fields)
    updated = rows[0] if rows else {**account, **fields}
    logger.info("TikTok access token refreshed for open_id={}…", str(account.get("open_id", ""))[:8])
    return str(payload["access_token"]), updated


async def disconnect(account: Dict[str, Any]) -> Dict[str, bool]:
    """Revoke at TikTok (best effort) then delete the row and its posts (cascade)."""
    revoked = False
    try:
        client_key, client_secret, _ = require_config()
        token = decrypt_token(account["access_token_enc"])
        await tiktok_client.revoke_token(client_key, client_secret, token)
        revoked = True
    except (TikTokNotConfigured, TokenVaultError) as exc:
        logger.warning("TikTok revoke skipped: {}", type(exc).__name__)
    except tiktok_client.TikTokAPIError as exc:
        logger.warning("TikTok revoke failed: {}", exc.code)
    await db_delete(ACCOUNTS, {"id": account["id"]})
    logger.info("TikTok account disconnected (revoked={})", revoked)
    return {"revoked": revoked, "deleted": True}
