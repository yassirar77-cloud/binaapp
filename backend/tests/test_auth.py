"""
Tests for auth API endpoints (register, login, me, logout, refresh).

Uses mocked supabase_service to avoid real database calls.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_email_service():
    """Mock the email_service used in auth endpoints (verification sends OK)."""
    from unittest.mock import AsyncMock
    m = AsyncMock()
    m.send_verification_code = AsyncMock(return_value=True)
    return m


@pytest.fixture
def auth_client(mock_supabase_service, mock_email_service):
    """TestClient with supabase_service and email_service mocked out."""
    with patch("app.api.v1.endpoints.auth.supabase_service", mock_supabase_service), \
         patch("app.api.v1.endpoints.auth.email_service", mock_email_service):
        from app.main import app
        yield TestClient(app)


class TestRegister:
    def test_successful_registration(self, auth_client, mock_supabase_service):
        mock_supabase_service.create_user.return_value = {
            "user": {"id": "new-user-id", "email": "new@example.com"}
        }

        response = auth_client.post("/api/v1/register", json={
            "email": "new@example.com",
            "password": "securepass123",
            "full_name": "Test User",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "new@example.com"
        # Profile + subscription are created by the DB trigger, not the backend.
        mock_supabase_service.create_user_profile.assert_not_called()
        # Email sent fine, so no rollback.
        mock_supabase_service.delete_user.assert_not_called()

    def test_registration_fails_when_user_creation_fails(self, auth_client, mock_supabase_service):
        mock_supabase_service.create_user.return_value = None

        response = auth_client.post("/api/v1/register", json={
            "email": "fail@example.com",
            "password": "securepass123",
            "full_name": "Fail User",
        })

        assert response.status_code == 400

    def test_registration_does_not_insert_profile_on_success(self, auth_client, mock_supabase_service):
        # The handle_new_user trigger owns profile + subscription creation, so
        # the backend must never insert a profile. On the happy path (email
        # sent) it also must not roll back the auth user.
        mock_supabase_service.create_user.return_value = {
            "user": {"id": "trigger-id", "email": "trigger@example.com"}
        }

        response = auth_client.post("/api/v1/register", json={
            "email": "trigger@example.com",
            "password": "securepass123",
            "full_name": "Trigger User",
        })

        assert response.status_code == 201
        mock_supabase_service.create_user_profile.assert_not_called()
        mock_supabase_service.delete_user.assert_not_called()

    def test_registration_fails_fast_when_verification_email_unsendable(
        self, auth_client, mock_supabase_service, mock_email_service
    ):
        # If the verification code can't be emailed (e.g. SMTP misconfigured),
        # registration must NOT silently succeed with a stuck account. It rolls
        # back the just-created auth user and returns 503 so the user can retry.
        mock_supabase_service.create_user.return_value = {
            "user": {"id": "stuck-id", "email": "stuck@example.com"}
        }
        mock_email_service.send_verification_code.return_value = False

        response = auth_client.post("/api/v1/register", json={
            "email": "stuck@example.com",
            "password": "securepass123",
            "full_name": "Stuck User",
        })

        assert response.status_code == 503
        mock_supabase_service.delete_user.assert_awaited_once_with("stuck-id")

    def test_short_password_rejected(self, auth_client):
        response = auth_client.post("/api/v1/register", json={
            "email": "short@example.com",
            "password": "short",
            "full_name": "Short Pass",
        })

        assert response.status_code == 422  # Pydantic validation

    def test_invalid_email_rejected(self, auth_client):
        response = auth_client.post("/api/v1/register", json={
            "email": "not-an-email",
            "password": "securepass123",
            "full_name": "Bad Email",
        })

        assert response.status_code == 422

    def test_disposable_email_rejected(self, auth_client):
        # Known disposable provider -> blocked by the schema validator (422).
        response = auth_client.post("/api/v1/register", json={
            "email": "throwaway@mailinator.com",
            "password": "securepass123",
            "full_name": "Disposable",
        })

        assert response.status_code == 422

    def test_registration_returns_unverified(self, auth_client, mock_supabase_service):
        mock_supabase_service.create_user.return_value = {
            "user": {"id": "unverified-id", "email": "unverified@example.com"}
        }

        response = auth_client.post("/api/v1/register", json={
            "email": "unverified@example.com",
            "password": "securepass123",
            "full_name": "Unverified User",
        })

        assert response.status_code == 201
        data = response.json()
        # Account is created UNVERIFIED; the JWT is still issued so the user
        # can use the builder immediately.
        assert data["email_verified"] is False
        assert data["access_token"]
        assert data["user"]["email_verified"] is False


class TestLogin:
    def test_successful_login(self, auth_client, mock_supabase_service):
        mock_supabase_service.sign_in.return_value = {
            "user": {"id": "login-user-id", "email": "login@example.com"}
        }

        response = auth_client.post("/api/v1/login", json={
            "email": "login@example.com",
            "password": "securepass123",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["user"]["id"] == "login-user-id"

    def test_invalid_credentials(self, auth_client, mock_supabase_service):
        mock_supabase_service.sign_in.return_value = None

        response = auth_client.post("/api/v1/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass",
        })

        assert response.status_code == 401

    def test_sign_in_returns_no_user_id(self, auth_client, mock_supabase_service):
        mock_supabase_service.sign_in.return_value = {"user": {"email": "noid@example.com"}}

        response = auth_client.post("/api/v1/login", json={
            "email": "noid@example.com",
            "password": "somepass123",
        })

        assert response.status_code == 401


class TestEmailVerification:
    def test_verify_requires_auth(self, auth_client):
        response = auth_client.post("/api/v1/verify-email", json={"code": "123456"})
        assert response.status_code in (401, 403)

    def test_verify_success(self, auth_client, mock_supabase_service, valid_token, test_user_id):
        from app.core.verification import hash_code

        mock_supabase_service.is_email_verified.return_value = False
        mock_supabase_service.get_active_verification_code.return_value = {
            "id": "code-1",
            "code_hash": hash_code(test_user_id, "654321"),
            "expires_at": "2999-01-01T00:00:00",
            "attempts": 0,
        }
        mock_supabase_service.consume_verification_code.return_value = True
        mock_supabase_service.mark_email_verified.return_value = True

        response = auth_client.post(
            "/api/v1/verify-email",
            json={"code": "654321"},
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        assert response.status_code == 200
        assert response.json()["email_verified"] is True
        mock_supabase_service.mark_email_verified.assert_awaited()

    def test_verify_wrong_code(self, auth_client, mock_supabase_service, valid_token, test_user_id):
        from app.core.verification import hash_code

        mock_supabase_service.is_email_verified.return_value = False
        mock_supabase_service.get_active_verification_code.return_value = {
            "id": "code-2",
            "code_hash": hash_code(test_user_id, "111111"),
            "expires_at": "2999-01-01T00:00:00",
            "attempts": 0,
        }

        response = auth_client.post(
            "/api/v1/verify-email",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        assert response.status_code == 400
        mock_supabase_service.increment_verification_attempts.assert_awaited()
        mock_supabase_service.mark_email_verified.assert_not_awaited()

    def test_verify_no_active_code(self, auth_client, mock_supabase_service, valid_token):
        mock_supabase_service.is_email_verified.return_value = False
        mock_supabase_service.get_active_verification_code.return_value = None

        response = auth_client.post(
            "/api/v1/verify-email",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        assert response.status_code == 400

    def test_verify_already_verified_is_idempotent(self, auth_client, mock_supabase_service, valid_token):
        mock_supabase_service.is_email_verified.return_value = True

        response = auth_client.post(
            "/api/v1/verify-email",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {valid_token}"},
        )

        assert response.status_code == 200
        assert response.json()["email_verified"] is True

    def test_resend_requires_auth(self, auth_client):
        response = auth_client.post("/api/v1/resend-verification")
        assert response.status_code in (401, 403)


class TestLogout:
    def test_logout_requires_auth(self, auth_client):
        response = auth_client.post("/api/v1/logout")
        assert response.status_code in (401, 403)  # No token

    def test_logout_with_valid_token(self, auth_client, valid_token):
        response = auth_client.post(
            "/api/v1/logout",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"


class TestRefreshToken:
    def test_refresh_valid_expired_token(self, auth_client, expired_token):
        response = auth_client.post(
            "/api/v1/refresh",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["access_token"] != expired_token

    def test_refresh_with_valid_token(self, auth_client, valid_token):
        response = auth_client.post(
            "/api/v1/refresh",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200

    def test_refresh_missing_auth_header(self, auth_client):
        response = auth_client.post("/api/v1/refresh")
        assert response.status_code == 401

    def test_refresh_tampered_token(self, auth_client, valid_token):
        tampered = valid_token[:-5] + "XXXXX"
        response = auth_client.post(
            "/api/v1/refresh",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert response.status_code == 401
