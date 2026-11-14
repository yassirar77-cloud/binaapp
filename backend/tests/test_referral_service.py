"""Referral recording against the real tables (referral_history, credit_transactions)."""
import httpx
import pytest

from app.services import referral_service as mod
from app.services.referral_service import ReferralService, is_valid_code

CODE = "BINA-AB12-CD34"


class FakeDB:
    """Stands in for PostgREST: records every request, answers from tables."""

    def __init__(self, codes=None, profiles=None, wallets=None, history_status=201):
        self.codes = codes or []
        self.profiles = profiles or []
        self.wallets = wallets or []
        self.history_status = history_status
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        import json

        table = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content) if request.content else None
        self.calls.append((request.method, table, body))
        if request.method == "GET":
            rows = {"referral_codes": self.codes, "profiles": self.profiles}.get(table)
            if table == "bina_credits":
                uid = request.url.params.get("user_id", "").replace("eq.", "")
                rows = [w for w in self.wallets if w["user_id"] == uid]
            return httpx.Response(200, json=rows or [])
        if request.method == "POST" and table == "referral_history":
            return httpx.Response(self.history_status)
        if request.method == "POST" and table == "bina_credits":
            return httpx.Response(201, json=[{"id": "w-new", "balance": 0, "lifetime_earned": 0}])
        return httpx.Response(204)

    def writes(self, table, method="POST"):
        return [b for m, t, b in self.calls if t == table and m == method]


@pytest.fixture
def service(monkeypatch):
    def make(db: FakeDB) -> ReferralService:
        real = httpx.AsyncClient

        def client(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(db.handler)
            return real(*args, **kwargs)

        monkeypatch.setattr(mod.httpx, "AsyncClient", client)
        svc = ReferralService()
        svc.supabase_url = "http://db.test"
        return svc

    return make


def _db(**kw):
    return FakeDB(
        codes=[{"id": "c1", "user_id": "referrer", "code": CODE,
                "total_referrals": 2, "total_credits_earned": 10}],
        wallets=[{"id": "w-ref", "user_id": "referrer", "balance": 10, "lifetime_earned": 10},
                 {"id": "w-new-user", "user_id": "friend", "balance": 0, "lifetime_earned": 0}],
        **kw,
    )


def test_code_format():
    assert is_valid_code(CODE)
    for bad in ("bina-ab12-cd34", "BINA-AB12", "", None, "BINA-AB12-CD34 "):
        assert not is_valid_code(bad)


@pytest.mark.asyncio
async def test_apply_records_history_and_credits_both(service):
    db = _db()
    result = await service(db).apply_referral("friend", CODE.lower())
    assert result["success"] is True

    (history,) = db.writes("referral_history")
    assert history["referrer_id"] == "referrer"
    assert history["referred_id"] == "friend"
    assert history["referral_code"] == CODE
    assert history["status"] == "completed"

    (code_patch,) = db.writes("referral_codes", "PATCH")
    assert code_patch == {"total_referrals": 3, "total_credits_earned": 15.0}

    ledger = db.writes("credit_transactions")
    assert len(ledger) == 2
    for row in ledger:
        # Real columns and CHECK-allowed values.
        assert row["type"] == "earned" and row["source"] == "referral"
        assert row["wallet_id"] and row["balance_after"] == row["balance_before"] + 5.0
    balances = db.writes("bina_credits", "PATCH")
    assert {"balance": 15.0, "lifetime_earned": 15.0} in balances
    assert {"balance": 5.0, "lifetime_earned": 5.0} in balances


@pytest.mark.asyncio
async def test_second_use_is_refused_and_pays_nothing(service):
    db = _db(history_status=409)  # UNIQUE (referred_id) violation
    result = await service(db).apply_referral("friend", CODE)
    assert result["success"] is False
    assert db.writes("credit_transactions") == []
    assert db.writes("bina_credits", "PATCH") == []


@pytest.mark.asyncio
async def test_self_referral_and_unknown_or_malformed_codes(service):
    db = _db()
    svc = service(db)
    assert (await svc.apply_referral("referrer", CODE))["success"] is False
    assert (await svc.apply_referral("friend", "BINA-ZZZZ"))["success"] is False
    db.codes = []
    assert (await svc.apply_referral("friend", CODE))["success"] is False
    assert db.writes("referral_history") == []


@pytest.mark.asyncio
async def test_signup_referral_uses_the_stored_code(service):
    db = _db(profiles=[{"signup_ref_code": CODE}])
    assert await service(db).apply_signup_referral("friend") is True
    assert len(db.writes("referral_history")) == 1


@pytest.mark.asyncio
async def test_signup_without_a_code_does_nothing(service):
    db = _db(profiles=[{"signup_ref_code": None}])
    assert await service(db).apply_signup_referral("friend") is False
    assert db.writes("referral_history") == []
