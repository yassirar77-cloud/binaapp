"""
Tests for auth API endpoints (register, login, me, logout, refresh).

Uses mocked supabase_service to avoid real database calls.
"""

import pytest
from unittest.mock import patch
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
        mock_supabase_service.delete_auth_user.assert_not_called()

    def test_registration_fails_when_user_creation_fails(self, auth_client, mock_supabase_service):
        mock_supabase_service.create_user.return_value = None

        response = auth_client.post("/api/v1/register", json={
            "email": "fail@example.com",
            "password": "securepass123",
            "full_name": "Fail User",
        })

        assert response.status_code == 400

    def test_registration_does_not_insert_profile_or_rollback(self, auth_client, mock_supabase_service):
        # The handle_new_user trigger owns profile + subscription creation, so
        # the backend must never insert a profile or roll back the auth user.
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
        mock_supabase_service.delete_auth_user.assert_not_called()

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
