"""
Shared pytest fixtures and mocks for BinaApp backend tests.

Provides:
- Mock Supabase client (intercepts all .table() calls)
- FastAPI TestClient fixture
- Fake JWT tokens for authenticated requests
- Mock environment variables
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Set test environment variables BEFORE any app imports
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")
os.environ.setdefault("DEEPSEEK_API_KEY", "test-deepseek-key")
os.environ.setdefault("APP_ENV", "testing")


@pytest.fixture
def mock_settings():
    """Provide test settings without touching real config."""
    from app.core.config import settings
    return settings


@pytest.fixture
def jwt_secret():
    """The JWT secret used in tests."""
    return os.environ["JWT_SECRET_KEY"]


@pytest.fixture
def supabase_jwt_secret():
    """The Supabase JWT secret used in tests."""
    return os.environ["SUPABASE_JWT_SECRET"]


@pytest.fixture
def test_user_id():
    return "test-user-id-12345"


@pytest.fixture
def test_user_email():
    return "testuser@example.com"


@pytest.fixture
def valid_token(test_user_id, test_user_email):
    """Create a valid JWT token for testing."""
    from app.core.security import create_access_token
    return create_access_token(data={"sub": test_user_id, "email": test_user_email})


@pytest.fixture
def expired_token(test_user_id, test_user_email):
    """Create an expired JWT token for testing."""
    from app.core.security import create_access_token
    return create_access_token(
        data={"sub": test_user_id, "email": test_user_email},
        expires_delta=timedelta(seconds=-1),
    )


@pytest.fixture
def valid_supabase_token(test_user_id, test_user_email, supabase_jwt_secret):
    """Create a valid Supabase-style JWT token."""
    from jose import jwt

    payload = {
        "sub": test_user_id,
        "email": test_user_email,
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, supabase_jwt_secret, algorithm="HS256")


@pytest.fixture
def auth_headers(valid_token):
    """HTTP headers with a valid Bearer token."""
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def mock_supabase_table():
    """
    Mock Supabase table operations.

    Returns a factory that creates chainable mock table objects.
    Usage in tests:
        table = mock_supabase_table(data=[{"id": "1", "name": "test"}])
        with patch("app.core.supabase.get_supabase_client") as mock_client:
            mock_client.return_value.table.return_value = table
    """

    def _factory(data=None, error=None):
        mock_response = MagicMock()
        mock_response.data = data or []
        mock_response.error = error

        # Create a chainable mock
        table_mock = MagicMock()
        for method in [
            "select", "insert", "update", "delete", "upsert",
            "eq", "neq", "gt", "gte", "lt", "lte",
            "like", "ilike", "is_", "in_",
            "order", "limit", "offset", "range",
            "single", "maybeSingle",
        ]:
            getattr(table_mock, method).return_value = table_mock

        table_mock.execute.return_value = mock_response
        return table_mock

    return _factory


@pytest.fixture
def mock_supabase_service():
    """Mock the supabase_service used in auth endpoints."""
    mock = AsyncMock()
    mock.create_user = AsyncMock()
    mock.create_user_profile = AsyncMock()
    mock.delete_auth_user = AsyncMock()
    mock.sign_in = AsyncMock()
    mock.get_user = AsyncMock()
    mock.get_user_subscription = AsyncMock()
    mock.get_user_websites = AsyncMock()
    mock.update_subscription = AsyncMock()
    return mock


@pytest.fixture
def client():
    """FastAPI TestClient for integration tests."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)
