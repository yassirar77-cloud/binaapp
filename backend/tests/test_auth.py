"""
Tests for auth API endpoints (register, login, me, logout, refresh).

Uses mocked supabase_service to avoid real database calls.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def auth_client(mock_supabase_service):
    """TestClient with supabase_service mocked out."""
    with patch("app.api.v1.endpoints.auth.supabase_service", mock_supabase_service):
        from app.main import app
        yield TestClient(app)


class TestRegister:
    def test_successful_registration(self, auth_client, mock_supabase_service):
        mock_supabase_service.create_user.return_value = {
            "user": {"id": "new-user-id", "email": "new@example.com"}
        }
        mock_supabase_service.create_user_profile.return_value = True

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

    def test_registration_fails_when_user_creation_fails(self, auth_client, mock_supabase_service):
        mock_supabase_service.create_user.return_value = None

        response = auth_client.post("/api/v1/register", json={
            "email": "fail@example.com",
            "password": "securepass123",
            "full_name": "Fail User",
        })

        assert response.status_code == 400

    def test_registration_rollback_on_profile_failure(self, auth_client, mock_supabase_service):
        mock_supabase_service.create_user.return_value = {
            "user": {"id": "rollback-id", "email": "rollback@example.com"}
        }
        mock_supabase_service.create_user_profile.return_value = None

        response = auth_client.post("/api/v1/register", json={
            "email": "rollback@example.com",
            "password": "securepass123",
            "full_name": "Rollback User",
        })

        assert response.status_code == 500
        mock_supabase_service.delete_auth_user.assert_awaited_once_with("rollback-id")

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
