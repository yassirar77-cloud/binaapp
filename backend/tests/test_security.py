"""
Tests for app.core.security — JWT creation, verification, password hashing, API keys.

Covers:
- create_access_token / decode_access_token round-trip
- Expired token handling
- Tampered token detection
- Dual-secret (custom + Supabase) verification in get_current_user
- decode_token_for_refresh allows expired, rejects tampered
- verify_password / get_password_hash round-trip
- verify_api_key with various inputs
- get_current_user edge cases (undefined, null, empty, missing sub)
"""

import pytest
from datetime import timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from jose import jwt
from fastapi import HTTPException


class TestPasswordHashing:
    def test_hash_and_verify(self):
        from app.core.security import get_password_hash, verify_password

        password = "secureP@ssw0rd!"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        from app.core.security import get_password_hash, verify_password

        hashed = get_password_hash("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_for_same_password(self):
        from app.core.security import get_password_hash

        h1 = get_password_hash("same-password")
        h2 = get_password_hash("same-password")
        assert h1 != h2  # bcrypt uses random salt


class TestCreateAccessToken:
    def test_creates_valid_token(self, jwt_secret):
        from app.core.security import create_access_token

        token = create_access_token(data={"sub": "user-123", "email": "a@b.com"})
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == "user-123"
        assert payload["email"] == "a@b.com"
        assert "exp" in payload
        assert "iat" in payload

    def test_custom_expiry(self, jwt_secret):
        from app.core.security import create_access_token

        token = create_access_token(
            data={"sub": "user-123"},
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == "user-123"

    def test_default_expiry_is_set(self, jwt_secret):
        from app.core.security import create_access_token

        token = create_access_token(data={"sub": "user-123"})
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        # exp should be in the future
        from datetime import datetime
        assert payload["exp"] > datetime.utcnow().timestamp()


class TestDecodeAccessToken:
    def test_decode_valid_token(self, valid_token, test_user_id):
        from app.core.security import decode_access_token

        payload = decode_access_token(valid_token)
        assert payload["sub"] == test_user_id

    def test_expired_token_raises_401(self, expired_token):
        from app.core.security import decode_access_token

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(expired_token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_tampered_token_raises_401(self, valid_token):
        from app.core.security import decode_access_token

        tampered = valid_token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(tampered)
        assert exc_info.value.status_code == 401

    def test_garbage_token_raises_401(self):
        from app.core.security import decode_access_token

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not.a.valid.jwt")
        assert exc_info.value.status_code == 401


class TestDecodeTokenForRefresh:
    def test_accepts_expired_token(self, expired_token, test_user_id):
        from app.core.security import decode_token_for_refresh

        payload = decode_token_for_refresh(expired_token)
        assert payload is not None
        assert payload["sub"] == test_user_id

    def test_accepts_valid_token(self, valid_token, test_user_id):
        from app.core.security import decode_token_for_refresh

        payload = decode_token_for_refresh(valid_token)
        assert payload is not None
        assert payload["sub"] == test_user_id

    def test_rejects_tampered_signature(self, valid_token):
        from app.core.security import decode_token_for_refresh

        tampered = valid_token[:-5] + "XXXXX"
        result = decode_token_for_refresh(tampered)
        assert result is None

    def test_rejects_garbage(self):
        from app.core.security import decode_token_for_refresh

        result = decode_token_for_refresh("garbage-token")
        assert result is None

    def test_accepts_expired_supabase_token(self, test_user_id, supabase_jwt_secret):
        from app.core.security import decode_token_for_refresh
        from datetime import datetime

        payload = {
            "sub": test_user_id,
            "email": "test@example.com",
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=2),
        }
        token = jwt.encode(payload, supabase_jwt_secret, algorithm="HS256")
        result = decode_token_for_refresh(token)
        assert result is not None
        assert result["sub"] == test_user_id


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_custom_jwt(self, valid_token, test_user_id):
        from app.core.security import get_current_user

        credentials = MagicMock()
        credentials.credentials = valid_token
        user = await get_current_user(credentials)
        assert user["sub"] == test_user_id

    @pytest.mark.asyncio
    async def test_valid_supabase_jwt(self, valid_supabase_token, test_user_id):
        from app.core.security import get_current_user

        credentials = MagicMock()
        credentials.credentials = valid_supabase_token
        user = await get_current_user(credentials)
        assert user["sub"] == test_user_id

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, expired_token):
        from app.core.security import get_current_user

        credentials = MagicMock()
        credentials.credentials = expired_token
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_undefined_token_raises_401(self):
        from app.core.security import get_current_user

        for invalid in ["undefined", "null", "None", ""]:
            credentials = MagicMock()
            credentials.credentials = invalid
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_token_missing_sub_claim(self, jwt_secret):
        from app.core.security import get_current_user
        from datetime import datetime

        token = jwt.encode(
            {"email": "no-sub@test.com", "exp": datetime.utcnow() + timedelta(hours=1), "iat": datetime.utcnow()},
            jwt_secret,
            algorithm="HS256",
        )
        credentials = MagicMock()
        credentials.credentials = token
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)
        assert exc_info.value.status_code == 401


class TestVerifyApiKey:
    def test_valid_key(self, monkeypatch):
        from app.core.security import verify_api_key
        monkeypatch.setattr("app.core.config.settings.BINAAPP_API_KEYS", "bina_key1,bina_key2")
        assert verify_api_key("bina_key1") is True
        assert verify_api_key("bina_key2") is True

    def test_invalid_key(self, monkeypatch):
        from app.core.security import verify_api_key
        monkeypatch.setattr("app.core.config.settings.BINAAPP_API_KEYS", "bina_key1")
        assert verify_api_key("wrong_key") is False

    def test_empty_key(self, monkeypatch):
        from app.core.security import verify_api_key
        monkeypatch.setattr("app.core.config.settings.BINAAPP_API_KEYS", "bina_key1")
        assert verify_api_key("") is False

    def test_no_keys_configured(self, monkeypatch):
        from app.core.security import verify_api_key
        monkeypatch.setattr("app.core.config.settings.BINAAPP_API_KEYS", None)
        assert verify_api_key("any_key") is False


class TestGenerateApiKey:
    def test_generates_prefixed_key(self):
        from app.core.security import generate_api_key

        key = generate_api_key()
        assert key.startswith("bina_")
        assert len(key) > 10

    def test_generates_unique_keys(self):
        from app.core.security import generate_api_key

        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100


class TestOptionalCurrentUser:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_credentials(self):
        from app.core.security import get_optional_current_user

        result = await get_optional_current_user(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_with_valid_token(self, valid_token, test_user_id):
        from app.core.security import get_optional_current_user

        credentials = MagicMock()
        credentials.credentials = valid_token
        result = await get_optional_current_user(credentials)
        assert result is not None
        assert result["sub"] == test_user_id

    @pytest.mark.asyncio
    async def test_returns_none_with_invalid_token(self):
        from app.core.security import get_optional_current_user

        credentials = MagicMock()
        credentials.credentials = "invalid-token"
        result = await get_optional_current_user(credentials)
        assert result is None
