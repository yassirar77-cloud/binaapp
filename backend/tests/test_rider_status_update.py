"""
Tests for PUT /delivery/riders/{rider_id}/orders/{order_id}/status.

Regression coverage for the C4-hardened rider status update: the enum
validation added in the audit hardening referenced ``OrderStatus`` without
importing it, so every authenticated rider status update died with a
NameError (surfaced to the rider as HTTP 500) before reaching Supabase.
These tests drive the endpoint through the real FastAPI app with a real
rider JWT — only the Supabase client is mocked — so that line actually
executes.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.core.supabase import get_supabase_client
from app.main import app

RIDER_ID = "11111111-1111-1111-1111-111111111111"
ORDER_ID = "22222222-2222-2222-2222-222222222222"
STATUS_URL = f"/api/v1/delivery/riders/{RIDER_ID}/orders/{ORDER_ID}/status"


def _chainable_table(data):
    """Chainable Supabase table mock whose execute() returns ``data``."""
    response = MagicMock()
    response.data = data
    response.error = None
    table = MagicMock()
    for method in ("select", "insert", "update", "delete", "eq", "order", "limit"):
        getattr(table, method).return_value = table
    table.execute.return_value = response
    return table


@pytest.fixture
def cod_order():
    return {
        "id": ORDER_ID,
        "order_number": "D-1001",
        "rider_id": RIDER_ID,
        "status": "ready",
        "payment_method": "cod",
    }


@pytest.fixture
def client(cod_order):
    """TestClient with only the Supabase client mocked out."""
    supabase = MagicMock()
    supabase.table.return_value = _chainable_table([cod_order])
    app.dependency_overrides[get_supabase_client] = lambda: supabase
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_supabase_client, None)


@pytest.fixture
def rider_headers():
    """Bearer token shaped like the ones POST /delivery/riders/login mints."""
    token = create_access_token(data={"sub": RIDER_ID, "role": "rider"})
    return {"Authorization": f"Bearer {token}"}


class TestRiderStatusUpdate:
    def test_valid_status_update_succeeds(self, client, rider_headers):
        # Regression: this used to 500 with
        # "Failed to update order status: name 'OrderStatus' is not defined".
        resp = client.put(
            STATUS_URL, json={"status": "picked_up"}, headers=rider_headers
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["new_status"] == "picked_up"
        assert body["order_number"] == "D-1001"

    def test_delivered_with_cod_payment_received(self, client, rider_headers):
        resp = client.put(
            STATUS_URL,
            json={"status": "delivered", "payment_received": True},
            headers=rider_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["new_status"] == "delivered"

    def test_unknown_status_rejected_400(self, client, rider_headers):
        # Exercises the OrderStatus enum validation branch directly.
        resp = client.put(
            STATUS_URL, json={"status": "teleported"}, headers=rider_headers
        )
        assert resp.status_code == 400, resp.text
        assert "Invalid status" in resp.json()["detail"]

    def test_valid_enum_but_rider_forbidden_status_403(self, client, rider_headers):
        # "cancelled" is a real OrderStatus value but not rider-permitted, so
        # it must pass enum validation and fail the allow-list check.
        resp = client.put(
            STATUS_URL, json={"status": "cancelled"}, headers=rider_headers
        )
        assert resp.status_code == 403, resp.text
        assert "may not set" in resp.json()["detail"]

    def test_token_rider_mismatch_403(self, client):
        other = create_access_token(data={"sub": "someone-else", "role": "rider"})
        resp = client.put(
            STATUS_URL,
            json={"status": "picked_up"},
            headers={"Authorization": f"Bearer {other}"},
        )
        assert resp.status_code == 403, resp.text

    def test_non_rider_token_403(self, client):
        merchant = create_access_token(data={"sub": RIDER_ID, "email": "x@y.my"})
        resp = client.put(
            STATUS_URL,
            json={"status": "picked_up"},
            headers={"Authorization": f"Bearer {merchant}"},
        )
        assert resp.status_code == 403, resp.text
