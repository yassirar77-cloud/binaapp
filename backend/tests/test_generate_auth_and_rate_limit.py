"""/api/generate/start: the merchant comes from the verified token, never
the body, and starts are rate limited before any model is called.

Before this, the endpoint read user_id/email from the JSON body: anyone
could start builds charged to another merchant's plan, and an email from
UNLIMITED_ACCESS_EMAILS in the body unlocked the founder bypass.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.services import generation_access as ga
from tests.conftest import generation_auth

BODY = {
    "description": "Salon Seri Ayu di Seksyen 7 Shah Alam: salon muslimah, gunting, warna, rebonding dan rawatan rambut. "
                   "Tempahan melalui WhatsApp, walk-in dialu-alukan.",
    "business_name": "Salon Seri Ayu",
    "business_type": "salon",
    "language": "ms",
    "whatsapp_number": "0112293445",
    "features": {"whatsapp": True, "priceList": True},
    "menu_items": [{"name": "Gunting & Blow", "price": "35"}],
}


def _quota_client():
    """Answers the website count (0) and the subscription lookup (Pro, room to spare)."""
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"content-range": "0-0/0"}
    resp.json.return_value = [{"plan_id": "plan-pro", "subscription_plans": {"websites_limit": 10, "plan_name": "Pro"}}]
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=resp)
    return client


@pytest.fixture
def started(monkeypatch):
    """Every run_generation_task call, by keyword (the endpoint calls it
    positionally; we capture positionals too)."""
    calls = []

    def _fake_task(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

        async def _noop():
            return None
        return _noop()

    monkeypatch.setattr(main_module, "supabase", None)
    monkeypatch.setattr(main_module, "run_generation_task", _fake_task)
    monkeypatch.setattr(main_module.httpx, "AsyncClient", lambda *a, **k: _quota_client())
    monkeypatch.setattr(main_module.sub_service, "_is_admin", AsyncMock(return_value=False))
    return calls


@pytest.fixture
def client():
    return TestClient(main_module.app)


def _who(call):
    """(user_email, user_id) as handed to run_generation_task."""
    a = call["args"]
    return a[2], a[3]


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def test_no_token_is_401_and_nothing_starts(client, started):
    r = client.post("/api/generate/start", json={**BODY, "user_id": "victim-uuid"})
    assert r.status_code == 401
    assert r.json()["error"] == "auth_required" and "log masuk" in r.json()["message"]
    assert r.headers.get("www-authenticate") == "Bearer"
    assert started == []


@pytest.mark.parametrize("header", ["Bearer not-a-jwt", "Bearer undefined", "Bearer ", "Basic dXNlcjpwYXNz", "token abc"])
def test_forged_or_malformed_token_is_401(client, started, header):
    r = client.post("/api/generate/start", json=BODY, headers={"Authorization": header})
    assert r.status_code == 401 and started == []


def test_expired_token_is_401(client, started, expired_token):
    r = client.post("/api/generate/start", json=BODY, headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401 and started == []


def test_body_identity_is_ignored_the_token_wins(client, started):
    """An attacker with their own valid token names a victim and a founder
    email in the body: the job is theirs, and no founder bypass applies."""
    founder = (main_module.UNLIMITED_ACCESS_EMAILS or ["founder@binaapp.my"])[0]
    r = client.post(
        "/api/generate/start",
        json={**BODY, "user_id": "victim-uuid", "email": founder},
        headers=generation_auth("attacker-uuid", "attacker@example.com"),
    )
    assert r.status_code == 200, r.text
    assert len(started) == 1
    email, user_id = _who(started[0])
    assert user_id == "attacker-uuid" and email == "attacker@example.com"


def test_supabase_signed_token_is_accepted(client, started, valid_supabase_token, test_user_id, test_user_email):
    r = client.post("/api/generate/start", json=BODY, headers={"Authorization": f"Bearer {valid_supabase_token}"})
    assert r.status_code == 200, r.text
    email, user_id = _who(started[0])
    assert user_id == test_user_id and email == test_user_email


def test_emergency_anonymous_switch_still_ignores_the_body(client, started, monkeypatch):
    monkeypatch.setenv("GENERATE_ALLOW_ANONYMOUS", "true")
    founder = (main_module.UNLIMITED_ACCESS_EMAILS or ["founder@binaapp.my"])[0]
    r = client.post("/api/generate/start", json={**BODY, "user_id": "victim-uuid", "email": founder})
    assert r.status_code == 200, r.text
    email, user_id = _who(started[0])
    assert user_id == "anonymous" and email == ""


def test_job_row_and_input_payload_carry_the_verified_user(client, started, monkeypatch):
    rows = []
    table = MagicMock()
    table.insert.side_effect = lambda row: rows.append(row) or MagicMock(execute=MagicMock())
    # debounce + concurrency selects return nothing
    sel = MagicMock()
    sel.eq.return_value = sel
    sel.gte.return_value = sel
    sel.order.return_value = sel
    sel.limit.return_value = sel
    sel.execute.return_value = MagicMock(data=[])
    table.select.return_value = sel
    sb = MagicMock()
    sb.table.return_value = table
    monkeypatch.setattr(main_module, "supabase", sb)
    r = client.post("/api/generate/start", json={**BODY, "user_id": "victim-uuid"}, headers=generation_auth("u-1"))
    assert r.status_code == 200, r.text
    assert rows and rows[0]["user_id"] == "u-1"


# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------

def test_per_user_window(client, started, monkeypatch):
    monkeypatch.setenv("GENERATE_RATE_USER_PER_10MIN", "3")
    auth = generation_auth("u-1")
    for _ in range(3):
        assert client.post("/api/generate/start", json=BODY, headers=auth).status_code == 200
    r = client.post("/api/generate/start", json=BODY, headers=auth)
    assert r.status_code == 429
    body = r.json()
    assert body["error"] == "rate_limited" and "minit" in body["message"] and body["retry_after"] > 0
    assert int(r.headers["retry-after"]) == body["retry_after"]
    assert len(started) == 3
    # another merchant is not affected
    assert client.post("/api/generate/start", json=BODY, headers=generation_auth("u-2")).status_code == 200


def test_admin_skips_the_user_window(client, started, monkeypatch):
    monkeypatch.setenv("GENERATE_RATE_USER_PER_10MIN", "1")
    monkeypatch.setattr(main_module.sub_service, "_is_admin", AsyncMock(return_value=True))
    auth = generation_auth("admin-1")
    for _ in range(3):
        assert client.post("/api/generate/start", json=BODY, headers=auth).status_code == 200


def test_per_ip_window_across_accounts(client, started, monkeypatch):
    monkeypatch.setenv("GENERATE_RATE_IP_PER_HOUR", "2")
    assert client.post("/api/generate/start", json=BODY, headers=generation_auth("a")).status_code == 200
    assert client.post("/api/generate/start", json=BODY, headers=generation_auth("b")).status_code == 200
    r = client.post("/api/generate/start", json=BODY, headers=generation_auth("c"))
    assert r.status_code == 429 and r.json()["error"] == "rate_limited"


def test_rejected_input_does_not_burn_the_allowance(client, started, monkeypatch):
    monkeypatch.setenv("GENERATE_RATE_USER_PER_10MIN", "1")
    auth = generation_auth("u-1")
    bad = {**BODY, "business_name": "", "description": "x" * 40}
    for _ in range(3):
        assert client.post("/api/generate/start", json=bad, headers=auth).status_code == 400
    assert client.post("/api/generate/start", json=BODY, headers=auth).status_code == 200


def test_concurrency_cap(client, started, monkeypatch):
    monkeypatch.setattr(ga, "count_processing_jobs", lambda sb, uid, **k: 2)
    r = client.post("/api/generate/start", json=BODY, headers=generation_auth("u-1"))
    assert r.status_code == 429 and r.json()["error"] == "too_many_running"
    assert started == []


def test_debounced_duplicate_is_not_rate_limited(client, started, monkeypatch):
    """A double-click within the debounce window gets the in-flight job back
    even when the window is full."""
    monkeypatch.setenv("GENERATE_RATE_USER_PER_10MIN", "1")
    sel = MagicMock()
    sel.eq.return_value = sel
    sel.gte.return_value = sel
    sel.order.return_value = sel
    sel.limit.return_value = sel
    sel.execute.return_value = MagicMock(data=[{"job_id": "inflight", "created_at": datetime.now().isoformat(), "status": "processing"}])
    sb = MagicMock()
    sb.table.return_value.select.return_value = sel
    monkeypatch.setattr(main_module, "supabase", sb)
    auth = generation_auth("u-1")
    for _ in range(3):
        r = client.post("/api/generate/start", json=BODY, headers=auth)
        assert r.status_code == 200 and r.json()["job_id"] == "inflight" and r.json()["deduplicated"]


# ---------------------------------------------------------------------------
# generate-simple (legacy, same hole)
# ---------------------------------------------------------------------------

def test_generate_simple_requires_a_token(client):
    founder = (main_module.UNLIMITED_ACCESS_EMAILS or ["founder@binaapp.my"])[0]
    r = client.post("/api/generate-simple", json={"description": "Kedai makan", "user_id": "anonymous", "email": founder})
    assert r.status_code == 401 and r.json()["error"] == "auth_required"


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

def test_sliding_window_counts_and_expires():
    w = ga.SlidingWindow()
    for t in (0, 10, 20):
        assert w.check("k", 60, 3, now=t)[0]
        w.record("k", now=t)
    ok, retry = w.check("k", 60, 3, now=30)
    assert not ok and retry == 31          # the first hit (t=0) leaves at t=60
    assert w.check("k", 60, 3, now=61)[0]  # it left
    assert w.check("k", 60, 0, now=30)[0]  # cap 0 = no limit


def test_client_ip_prefers_edge_headers_and_the_last_forwarded_hop():
    assert ga.client_ip({"x-forwarded-for": "6.6.6.6, 203.0.113.9"}) == "203.0.113.9"
    assert ga.client_ip({"cf-connecting-ip": "198.51.100.4", "x-forwarded-for": "6.6.6.6"}) == "198.51.100.4"
    assert ga.client_ip({}, "10.0.0.1") == "10.0.0.1"
    assert ga.client_ip({}) == "unknown"


def test_count_processing_jobs_ignores_stale_rows_and_survives_errors():
    sel = MagicMock()
    sel.eq.return_value = sel
    sel.gte.return_value = sel
    sel.limit.return_value = sel
    sel.execute.return_value = MagicMock(data=[{"job_id": "a"}, {"job_id": "b"}])
    sb = MagicMock()
    sb.table.return_value.select.return_value = sel
    assert ga.count_processing_jobs(sb, "u-1") == 2
    cutoff = sel.gte.call_args[0][1]
    assert datetime.fromisoformat(cutoff) > datetime.now() - timedelta(seconds=1900)
    sb.table.side_effect = RuntimeError("db down")
    assert ga.count_processing_jobs(sb, "u-1") == 0
    assert ga.count_processing_jobs(None, "u-1") == 0
    assert ga.count_processing_jobs(sb, "anonymous") == 0
