"""
Tests for subscription guard middleware — route protection based on subscription status.

Covers:
- Protected vs allowed route classification
- Subscription status enum values
- Grace period read-only access logic
- Route configuration completeness
"""

import pytest
from app.middleware.subscription_guard import (
    SubscriptionStatus,
    PROTECTED_ROUTE_PREFIXES,
    ALLOWED_ROUTE_PREFIXES,
    ALLOWED_METHODS_WHEN_GRACE,
)


class TestSubscriptionStatus:
    def test_all_statuses_defined(self):
        expected = {"active", "expired", "grace", "locked", "cancelled", "pending"}
        actual = {s.value for s in SubscriptionStatus}
        assert expected == actual

    def test_string_comparison(self):
        assert SubscriptionStatus.ACTIVE == "active"
        assert SubscriptionStatus.LOCKED == "locked"
        assert SubscriptionStatus.GRACE == "grace"


class TestRouteConfiguration:
    def test_protected_routes_include_key_paths(self):
        key_paths = ["/api/v1/websites", "/api/v1/menu", "/api/v1/delivery"]
        for path in key_paths:
            assert path in PROTECTED_ROUTE_PREFIXES, f"{path} should be protected"

    def test_payment_routes_always_allowed(self):
        """Users must be able to pay even when locked."""
        assert "/api/v1/payments" in ALLOWED_ROUTE_PREFIXES

    def test_subscription_routes_always_allowed(self):
        """Users must be able to check subscription status even when locked."""
        assert "/api/v1/subscription" in ALLOWED_ROUTE_PREFIXES

    def test_auth_routes_always_allowed(self):
        assert "/api/v1/auth" in ALLOWED_ROUTE_PREFIXES

    def test_health_routes_always_allowed(self):
        assert any("/health" in r for r in ALLOWED_ROUTE_PREFIXES)

    def test_no_overlap_between_protected_and_allowed(self):
        overlap = set(PROTECTED_ROUTE_PREFIXES) & set(ALLOWED_ROUTE_PREFIXES)
        assert len(overlap) == 0, f"Routes should not be both protected and allowed: {overlap}"


class TestGracePeriodMethods:
    def test_read_methods_allowed_in_grace(self):
        assert "GET" in ALLOWED_METHODS_WHEN_GRACE
        assert "HEAD" in ALLOWED_METHODS_WHEN_GRACE
        assert "OPTIONS" in ALLOWED_METHODS_WHEN_GRACE

    def test_write_methods_not_allowed_in_grace(self):
        assert "POST" not in ALLOWED_METHODS_WHEN_GRACE
        assert "PUT" not in ALLOWED_METHODS_WHEN_GRACE
        assert "DELETE" not in ALLOWED_METHODS_WHEN_GRACE
        assert "PATCH" not in ALLOWED_METHODS_WHEN_GRACE


class TestRouteMatching:
    """Test that route prefix matching logic works correctly."""

    def _is_protected(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in PROTECTED_ROUTE_PREFIXES)

    def _is_allowed(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in ALLOWED_ROUTE_PREFIXES)

    def test_website_crud_is_protected(self):
        assert self._is_protected("/api/v1/websites")
        assert self._is_protected("/api/v1/websites/123")
        assert self._is_protected("/api/v1/websites/123/publish")

    def test_menu_is_protected(self):
        assert self._is_protected("/api/v1/menu")
        assert self._is_protected("/api/v1/menu/items")

    def test_delivery_is_protected(self):
        assert self._is_protected("/api/v1/delivery")
        assert self._is_protected("/api/v1/delivery/orders/123")

    def test_payment_is_allowed(self):
        assert self._is_allowed("/api/v1/payments")
        assert self._is_allowed("/api/v1/payments/checkout")

    def test_auth_is_allowed(self):
        assert self._is_allowed("/api/v1/auth")
        assert self._is_allowed("/api/v1/auth/login")

    def test_unknown_route_neither(self):
        assert not self._is_protected("/api/v1/unknown")
        assert not self._is_allowed("/api/v1/unknown")
