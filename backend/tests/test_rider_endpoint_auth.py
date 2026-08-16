"""
Auth regression tests for the previously-unauthenticated rider endpoints.

GET /delivery/riders/{id}/orders, PUT /delivery/riders/{id}/location and
GET /delivery/riders/{id}/today used to be public — any UUID enumerated a
rider's order list (customer PII) or spoofed their GPS. The owner-side rider
CRUD trio (PUT /riders/{id}, PUT /riders/{id}/status, DELETE /riders/{id})
had no auth dependency at all. These tests pin the new contracts:

* rider-facing endpoints require the rider's OWN JWT (role=rider, sub match)
* owner-facing rider CRUD requires a merchant JWT owning the rider's website
* the new PUT /riders/{id}/online self-service presence toggle works
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.core.supabase import get_supabase_client
from app.main import app

RIDER_ID = "11111111-1111-1111-1111-111111111111"
WEBSITE_ID = "33333333-3333-3333-3333-333333333333"
OWNER_ID = "44444444-4444-4444-4444-444444444444"


def _chainable_table(data):
    response = MagicMock()
    response.data = data
    response.error = None
    table = MagicMock()
    for method in ("select", "insert", "update", "delete", "eq", "is_", "order", "limit", "gte"):
        getattr(table, method).return_value = table
    table.execute.return_value = response
    return table


def _make_supabase(tables: dict):
    """Supabase mock routing .table(name) to per-table chainables."""
    supabase = MagicMock()
    default = _chainable_table([])
    supabase.table.side_effect = lambda name: tables.get(name, default)
    return supabase


@pytest.fixture
def rider_row():
    return {
        "id": RIDER_ID,
        "name": "Ali",
        "phone": "0123456789",
        "email": None,
        "photo_url": None,
        "vehicle_type": "motorcycle",
        "vehicle_plate": "WXY 1234",
        "vehicle_model": None,
        "website_id": WEBSITE_ID,
        "is_active": True,
        "is_online": True,
        "current_latitude": None,
        "current_longitude": None,
        "last_location_update": None,
        "total_deliveries": 0,
        "rating": 5.0,
        "total_ratings": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def client(rider_row):
    supabase = _make_supabase(
        {
            "riders": _chainable_table([rider_row]),
            "websites": _chainable_table([{"id": WEBSITE_ID}]),
            "delivery_orders": _chainable_table([]),
            "rider_locations": _chainable_table([]),
        }
    )
    app.dependency_overrides[get_supabase_client] = lambda: supabase
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_supabase_client, None)


@pytest.fixture
def rider_headers():
    token = create_access_token(data={"sub": RIDER_ID, "role": "rider"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_rider_headers():
    token = create_access_token(data={"sub": "someone-else", "role": "rider"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner_headers():
    token = create_access_token(data={"sub": OWNER_ID, "email": "owner@x.my"})
    return {"Authorization": f"Bearer {token}"}


class TestRiderOrdersAuth:
    URL = f"/api/v1/delivery/riders/{RIDER_ID}/orders"

    def test_no_token_rejected(self, client):
        resp = client.get(self.URL)
        assert resp.status_code in (401, 403), resp.text

    def test_other_rider_token_rejected(self, client, other_rider_headers):
        resp = client.get(self.URL, headers=other_rider_headers)
        assert resp.status_code == 403, resp.text

    def test_own_token_ok(self, client, rider_headers):
        resp = client.get(self.URL, headers=rider_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["rider_id"] == RIDER_ID
        assert "orders" in body and "available" in body


class TestRiderLocationAuth:
    URL = f"/api/v1/delivery/riders/{RIDER_ID}/location"
    BODY = {"latitude": 3.139, "longitude": 101.6869}

    def test_no_token_rejected(self, client):
        resp = client.put(self.URL, json=self.BODY)
        assert resp.status_code in (401, 403), resp.text

    def test_other_rider_token_rejected(self, client, other_rider_headers):
        resp = client.put(self.URL, json=self.BODY, headers=other_rider_headers)
        assert resp.status_code == 403, resp.text

    def test_own_token_ok_with_order_id_in_body(self, client, rider_headers):
        resp = client.put(
            self.URL,
            json={**self.BODY, "order_id": "22222222-2222-2222-2222-222222222222"},
            headers=rider_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True


class TestRiderTodayAuth:
    URL = f"/api/v1/delivery/riders/{RIDER_ID}/today"

    def test_no_token_rejected(self, client):
        resp = client.get(self.URL)
        assert resp.status_code in (401, 403), resp.text

    def test_own_token_ok(self, client, rider_headers):
        resp = client.get(self.URL, headers=rider_headers)
        assert resp.status_code == 200, resp.text
        assert set(resp.json().keys()) == {"count", "earnings"}


class TestRiderOnlineToggle:
    URL = f"/api/v1/delivery/riders/{RIDER_ID}/online"

    def test_no_token_rejected(self, client):
        resp = client.put(self.URL, json={"is_online": True})
        assert resp.status_code in (401, 403), resp.text

    def test_own_token_sets_online(self, client, rider_headers):
        resp = client.put(self.URL, json={"is_online": True}, headers=rider_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"success": True, "is_online": True}

    def test_merchant_token_rejected(self, client, owner_headers):
        resp = client.put(self.URL, json={"is_online": False}, headers=owner_headers)
        assert resp.status_code == 403, resp.text


class TestOwnerRiderCrudAuth:
    UPDATE_URL = f"/api/v1/delivery/riders/{RIDER_ID}"
    STATUS_URL = f"/api/v1/delivery/riders/{RIDER_ID}/status"

    def test_update_requires_token(self, client):
        resp = client.put(self.UPDATE_URL, json={"name": "Abu"})
        assert resp.status_code in (401, 403), resp.text

    def test_status_requires_token(self, client):
        resp = client.put(self.STATUS_URL, json={"status": "inactive"})
        assert resp.status_code in (401, 403), resp.text

    def test_delete_requires_token(self, client):
        resp = client.delete(self.UPDATE_URL)
        assert resp.status_code in (401, 403), resp.text

    def test_owner_can_update(self, client, owner_headers, rider_row):
        resp = client.put(
            self.UPDATE_URL, json={"name": "Abu"}, headers=owner_headers
        )
        assert resp.status_code == 200, resp.text

    def test_non_owner_rejected(self, rider_row, owner_headers):
        # websites lookup returns no rows -> ownership check must 403.
        supabase = _make_supabase(
            {
                "riders": _chainable_table([rider_row]),
                "websites": _chainable_table([]),
            }
        )
        app.dependency_overrides[get_supabase_client] = lambda: supabase
        try:
            client = TestClient(app)
            resp = client.put(
                self.UPDATE_URL, json={"name": "Abu"}, headers=owner_headers
            )
            assert resp.status_code == 403, resp.text
            resp = client.delete(self.UPDATE_URL, headers=owner_headers)
            assert resp.status_code == 403, resp.text
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)


class TestOwnerPresenceEndpoint:
    URL = f"/api/v1/live/riders/{RIDER_ID}/presence"

    def test_requires_token(self, client):
        resp = client.patch(self.URL, json={"is_online": False})
        assert resp.status_code in (401, 403), resp.text

    def test_owner_can_force_offline(self, client, owner_headers):
        resp = client.patch(
            self.URL, json={"is_online": False}, headers=owner_headers
        )
        assert resp.status_code == 204, resp.text
