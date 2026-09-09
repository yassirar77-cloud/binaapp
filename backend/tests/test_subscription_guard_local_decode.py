"""Backend A: the stray GET /auth/v1/user 403 on every poll.

It was not an auth bypass on the route (three checks stand). It WAS a
network call per request that (1) logged a 403 for every BinaApp-issued
token and (2) on that 403 made the middleware skip the subscription-lock
check. The user id is now read from the token locally, with the same
secrets the route dependency uses.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token
from app.middleware.subscription_guard import get_user_id_from_request


def _req(auth: str | None):
    r = MagicMock()
    r.headers = {"Authorization": auth} if auth is not None else {}
    return r


@pytest.mark.asyncio
async def test_binaapp_token_resolves_locally_without_any_http(monkeypatch):
    # If anything tried the network here it would blow up.
    import app.middleware.subscription_guard as guard
    monkeypatch.setattr(guard.httpx, "AsyncClient", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network!")))
    token = create_access_token({"sub": "user-123"})
    assert await get_user_id_from_request(_req(f"Bearer {token}")) == "user-123"


@pytest.mark.asyncio
async def test_supabase_signed_token_also_resolves(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "sb-secret")
    token = jwt.encode(
        {"sub": "sb-user", "aud": "authenticated", "exp": datetime.utcnow() + timedelta(hours=1)},
        "sb-secret", algorithm="HS256",
    )
    assert await get_user_id_from_request(_req(f"Bearer {token}")) == "sb-user"


@pytest.mark.asyncio
async def test_garbage_and_missing_headers_are_none():
    assert await get_user_id_from_request(_req(None)) is None
    assert await get_user_id_from_request(_req("Bearer undefined")) is None
    assert await get_user_id_from_request(_req("Bearer not.a.jwt")) is None
    assert await get_user_id_from_request(_req("Basic abc")) is None
