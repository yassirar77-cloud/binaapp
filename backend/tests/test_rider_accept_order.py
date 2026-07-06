"""
Tests for POST /delivery/riders/{rider_id}/orders/{order_id}/accept.

The rider "accept" endpoint is the claim step of the broadcast dispatch path:
a newly-placed order is inserted unassigned (rider_id NULL, status 'pending')
and surfaces in every same-website rider's available feed; accepting it
atomically assigns the order to the claiming rider. These tests drive the real
FastAPI app with a real rider JWT and a table-aware Supabase fake so the auth,
website-scoping, and atomic-claim branches actually execute.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.core.supabase import get_supabase_client
from app.main import app

RIDER_ID = "11111111-1111-1111-1111-111111111111"
ORDER_ID = "22222222-2222-2222-2222-222222222222"
WEBSITE_ID = "33333333-3333-3333-3333-333333333333"
ACCEPT_URL = f"/api/v1/delivery/riders/{RIDER_ID}/orders/{ORDER_ID}/accept"


class _FakeTable:
    """Chainable Supabase table fake that returns per-operation data.

    execute() resolves to responses[<last op>] (select/insert/update/delete),
    falling back to responses['default']. Supports the .is_() filter used by
    the atomic claim.
    """

    def __init__(self, responses):
        self._responses = responses
        self._op = None

    def select(self, *a, **k):
        self._op = "select"
        return self

    def insert(self, *a, **k):
        self._op = "insert"
        return self

    def update(self, *a, **k):
        self._op = "update"
        return self

    def delete(self, *a, **k):
        self._op = "delete"
        return self

    def eq(self, *a, **k):
        return self

    def is_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        resp = MagicMock()
        resp.error = None
        resp.data = self._responses.get(
            self._op, self._responses.get("default", [])
        )
        self._op = None
        return resp


def _make_client(*, rider, order_select, claim_result):
    """Build a TestClient whose Supabase fake routes by table name."""
    tables = {
        "riders": _FakeTable({"select": [rider] if rider else []}),
        "delivery_orders": _FakeTable(
            {"select": [order_select] if order_select else [], "update": claim_result}
        ),
        "order_status_history": _FakeTable({"insert": []}),
        # Empty conversation lookup short-circuits the chat/system-message branch.
        "chat_conversations": _FakeTable({"select": []}),
    }
    supabase = MagicMock()
    supabase.table.side_effect = lambda name: tables[name]
    app.dependency_overrides[get_supabase_client] = lambda: supabase
    return TestClient(app)


@pytest.fixture
def rider_headers():
    token = create_access_token(data={"sub": RIDER_ID, "role": "rider"})
    return {"Authorization": f"Bearer {token}"}


ACTIVE_RIDER = {
    "id": RIDER_ID,
    "name": "Ali",
    "phone": "0123456789",
    "website_id": WEBSITE_ID,
    "is_active": True,
}
PENDING_ORDER = {
    "id": ORDER_ID,
    "order_number": "D-1001",
    "website_id": WEBSITE_ID,
    "rider_id": None,
    "status": "pending",
}


def _teardown():
    app.dependency_overrides.pop(get_supabase_client, None)


class TestRiderAcceptOrder:
    def test_accept_unassigned_order_succeeds(self, rider_headers):
        claimed = {**PENDING_ORDER, "rider_id": RIDER_ID, "status": "confirmed"}
        client = _make_client(
            rider=ACTIVE_RIDER, order_select=PENDING_ORDER, claim_result=[claimed]
        )
        try:
            resp = client.post(ACCEPT_URL, headers=rider_headers)
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["success"] is True
            assert body["new_status"] == "confirmed"
            assert body["order_number"] == "D-1001"
        finally:
            _teardown()

    def test_already_assigned_order_409(self, rider_headers):
        taken = {**PENDING_ORDER, "rider_id": "99999999-9999-9999-9999-999999999999"}
        client = _make_client(
            rider=ACTIVE_RIDER, order_select=taken, claim_result=[]
        )
        try:
            resp = client.post(ACCEPT_URL, headers=rider_headers)
            assert resp.status_code == 409, resp.text
        finally:
            _teardown()

    def test_lost_race_returns_409(self, rider_headers):
        # Order looks claimable on read, but the atomic update matches no rows
        # because another rider won between the read and the write.
        client = _make_client(
            rider=ACTIVE_RIDER, order_select=PENDING_ORDER, claim_result=[]
        )
        try:
            resp = client.post(ACCEPT_URL, headers=rider_headers)
            assert resp.status_code == 409, resp.text
        finally:
            _teardown()

    def test_order_from_other_website_403(self, rider_headers):
        other_ws_order = {**PENDING_ORDER, "website_id": "44444444-4444-4444-4444-444444444444"}
        client = _make_client(
            rider=ACTIVE_RIDER, order_select=other_ws_order, claim_result=[]
        )
        try:
            resp = client.post(ACCEPT_URL, headers=rider_headers)
            assert resp.status_code == 403, resp.text
        finally:
            _teardown()

    def test_token_rider_mismatch_403(self):
        other = create_access_token(data={"sub": "someone-else", "role": "rider"})
        client = _make_client(
            rider=ACTIVE_RIDER, order_select=PENDING_ORDER, claim_result=[]
        )
        try:
            resp = client.post(
                ACCEPT_URL, headers={"Authorization": f"Bearer {other}"}
            )
            assert resp.status_code == 403, resp.text
        finally:
            _teardown()

    def test_inactive_rider_403(self, rider_headers):
        inactive = {**ACTIVE_RIDER, "is_active": False}
        client = _make_client(
            rider=inactive, order_select=PENDING_ORDER, claim_result=[]
        )
        try:
            resp = client.post(ACCEPT_URL, headers=rider_headers)
            assert resp.status_code == 403, resp.text
        finally:
            _teardown()
