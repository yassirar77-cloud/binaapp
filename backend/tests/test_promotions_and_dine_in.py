"""Tests for voucher codes, loyalty points and dine-in (table QR) orders.

What matters:

  1. Money is decided on the server. A voucher or points the customer asked
     for either reduces the stored total, or the order is refused — the
     customer is never charged a total they did not see.
  2. A claimed voucher use / spent points are handed back when the order
     then fails to save.
  3. A plain delivery order writes none of the new columns and touches none
     of the promo tables, so it keeps working on a database that has not
     run migrations 063/064 yet.
  4. A dine-in order needs a table and nothing else: no coordinates, no
     zone lookup, no fee — and it can be completed straight from 'ready'.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.supabase import get_supabase_client
from app.main import app
from app.models.delivery_schemas import (
    OrderCreate,
    normalize_customer_phone,
    normalize_table_number,
    parse_dine_in_label,
)
from app.services import promo_engine as pe

WEBSITE_ID = "33333333-3333-3333-3333-333333333333"
OTHER_WEBSITE_ID = "44444444-4444-4444-4444-444444444444"
OWNER_ID = "test-user-id-12345"
ITEM_ID = "55555555-5555-5555-5555-555555555555"
PHONE = "+60123456789"


# ---------------------------------------------------------------------------
# In-memory Supabase fake (tables + the SQL functions from migration 063)
# ---------------------------------------------------------------------------

class _Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.op, self.payload = "select", None
        self.filters, self._limit, self._single = [], None, False
        self._order = None

    def select(self, *a, **k):
        self.op = "select"
        return self

    def insert(self, payload, **k):
        self.op, self.payload = "insert", payload
        return self

    def update(self, payload, **k):
        self.op, self.payload = "update", payload
        return self

    def upsert(self, payload, **k):
        self.op, self.payload = "upsert", payload
        return self

    def delete(self, **k):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append(lambda r, c=col, v=val: r.get(c) == v)
        return self

    def in_(self, col, vals):
        self.filters.append(lambda r, c=col, v=tuple(vals): r.get(c) in v)
        return self

    def order(self, col, desc=False, **k):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, *a):
        return self

    def single(self):
        self._single = True
        return self

    def _match(self, row):
        return all(f(row) for f in self.filters)

    def execute(self):
        self.db.touched.append((self.table, self.op))
        if self.table in self.db.fail_on.get(self.op, ()):
            raise RuntimeError(f"simulated {self.op} failure on {self.table}")
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "insert":
            payloads = self.payload if isinstance(self.payload, list) else [self.payload]
            out = []
            for p in payloads:
                row = dict(p)
                row.setdefault("id", str(uuid.uuid4()))
                if self.table == "delivery_orders":
                    row.setdefault("order_number", f"BNA-{len(rows) + 1:04d}")
                    row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                    for k in ("customer_email", "delivery_notes", "payment_reference",
                              "confirmed_at", "preparing_at", "ready_at", "picked_up_at",
                              "delivered_at", "completed_at", "cancelled_at", "rider_id",
                              "actual_delivery_time"):
                        row.setdefault(k, None)
                if self.table == "vouchers":
                    row.setdefault("used_count", 0)
                    row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                rows.append(row)
                out.append(dict(row))
            return SimpleNamespace(data=out, count=len(out))
        if self.op == "upsert":
            for row in rows:
                if row.get("website_id") == self.payload.get("website_id"):
                    row.update(self.payload)
                    return SimpleNamespace(data=[dict(row)], count=1)
            rows.append(dict(self.payload))
            return SimpleNamespace(data=[dict(self.payload)], count=1)
        matched = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in matched:
                r.update(self.payload)
        elif self.op == "delete":
            self.db.tables[self.table] = [r for r in rows if not self._match(r)]
        if self._order:
            col, desc = self._order
            matched = sorted(matched, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        if self._limit is not None:
            matched = matched[: self._limit]
        if self._single:
            return SimpleNamespace(data=dict(matched[0]) if matched else None, count=len(matched))
        return SimpleNamespace(data=[dict(r) for r in matched], count=len(matched))


class _Rpc:
    def __init__(self, db, name, params):
        self.db, self.name, self.params = db, name, params

    def execute(self):
        self.db.rpc_calls.append(self.name)
        return SimpleNamespace(data=getattr(self.db, f"_rpc_{self.name}")(**self.params))


class FakeDb:
    """Just enough PostgREST to run the order and promotions endpoints."""

    def __init__(self):
        self.tables = {
            "websites": [
                {"id": WEBSITE_ID, "user_id": OWNER_ID, "business_name": "Kedai Ali"},
                {"id": OTHER_WEBSITE_ID, "user_id": "someone-else", "business_name": "Lain"},
            ],
            "menu_items": [{"id": ITEM_ID, "name": "Nasi Lemak", "price": 10.0}],
            "profiles": [],
        }
        self.touched, self.rpc_calls = [], []
        self.fail_on = {}
        self.zone = {"id": "zone-1", "fee_cents": 500, "min_order_cents": 0,
                     "estimated_delivery_min": 30}

    def table(self, name):
        if name == "loyalty_balances":
            return _Query(self, "loyalty_balances")._with_rows(self._balances())
        return _Query(self, name)

    def rpc(self, name, params):
        return _Rpc(self, name, params)

    def _balances(self):
        totals = {}
        for row in self.tables.get("loyalty_ledger", []):
            key = (row["website_id"], row["customer_phone"])
            totals[key] = totals.get(key, 0) + row["points"]
        return [
            {"website_id": w, "customer_phone": p, "balance": b,
             "lifetime_earned": b, "last_activity_at": None}
            for (w, p), b in totals.items()
        ]

    # --- SQL functions -----------------------------------------------------
    def _rpc_find_zone_for_point(self, **params):
        return [self.zone] if self.zone else []

    def _rpc_claim_voucher(self, p_voucher_id, p_phone, p_discount):
        voucher = next((v for v in self.tables.get("vouchers", []) if v["id"] == p_voucher_id), None)
        if not voucher or not voucher.get("is_active", True):
            return None
        limit = voucher.get("usage_limit")
        if limit is not None and voucher["used_count"] >= limit:
            return None
        redemptions = self.tables.setdefault("voucher_redemptions", [])
        per_customer = voucher.get("per_customer_limit")
        if per_customer is not None:
            used = sum(1 for r in redemptions
                       if r["voucher_id"] == p_voucher_id and r["customer_phone"] == p_phone)
            if used >= per_customer:
                return None
        voucher["used_count"] += 1
        rid = str(uuid.uuid4())
        redemptions.append({"id": rid, "voucher_id": p_voucher_id,
                            "website_id": voucher["website_id"], "order_id": None,
                            "customer_phone": p_phone, "discount_amount": p_discount})
        return rid

    def _rpc_release_voucher(self, p_redemption_id):
        redemptions = self.tables.setdefault("voucher_redemptions", [])
        row = next((r for r in redemptions if r["id"] == p_redemption_id), None)
        if not row:
            return False
        redemptions.remove(row)
        for v in self.tables.get("vouchers", []):
            if v["id"] == row["voucher_id"]:
                v["used_count"] = max(v["used_count"] - 1, 0)
        return True

    def _rpc_redeem_loyalty_points(self, p_website_id, p_phone, p_points):
        ledger = self.tables.setdefault("loyalty_ledger", [])
        balance = sum(r["points"] for r in ledger
                      if r["website_id"] == p_website_id and r["customer_phone"] == p_phone)
        if p_points <= 0 or balance < p_points:
            return None
        lid = str(uuid.uuid4())
        ledger.append({"id": lid, "website_id": p_website_id, "customer_phone": p_phone,
                       "order_id": None, "points": -p_points, "reason": "redeem"})
        return lid

    # --- seeding helpers ---------------------------------------------------
    def add_voucher(self, **overrides):
        row = {
            "id": str(uuid.uuid4()), "website_id": WEBSITE_ID, "code": "JIMAT10",
            "description": "", "discount_type": "percent", "discount_value": 10,
            "max_discount": None, "min_order": 0, "starts_at": None, "expires_at": None,
            "usage_limit": None, "per_customer_limit": None, "used_count": 0,
            "is_active": True,
        }
        row.update(overrides)
        self.tables.setdefault("vouchers", []).append(row)
        return row

    def add_points(self, points, phone=PHONE):
        self.tables.setdefault("loyalty_ledger", []).append({
            "id": str(uuid.uuid4()), "website_id": WEBSITE_ID, "customer_phone": phone,
            "order_id": None, "points": points, "reason": "earn",
        })

    def enable_loyalty(self, **overrides):
        row = {"website_id": WEBSITE_ID, "enabled": True, "points_per_rm": 1,
               "redeem_points": 100, "redeem_value": 5}
        row.update(overrides)
        self.tables.setdefault("loyalty_settings", []).append(row)


def _with_rows(self, rows):
    """Point a query at computed rows (the loyalty_balances view)."""
    self.db.tables["loyalty_balances"] = rows
    return self


_Query._with_rows = _with_rows


@pytest.fixture
def db(monkeypatch):
    fake = FakeDb()
    app.dependency_overrides[get_supabase_client] = lambda: fake
    # No WhatsApp traffic from tests.
    from app.api.v1.endpoints import delivery, promotions
    for name in ("notify_owner_new_order", "notify_customer_order_placed",
                 "notify_customer_status_update"):
        monkeypatch.setattr(delivery, name, lambda *a, **k: True)
    promotions.reset_rate_limits()
    yield fake
    app.dependency_overrides.pop(get_supabase_client, None)
    promotions.reset_rate_limits()


@pytest.fixture
def api(db):
    return TestClient(app)


def _order_body(**overrides):
    body = {
        "website_id": WEBSITE_ID,
        "customer_name": "Aisyah",
        "customer_phone": "0123456789",
        "delivery_address": "12 Jalan Mawar, Shah Alam",
        "delivery_latitude": 3.07,
        "delivery_longitude": 101.5,
        "items": [{"menu_item_id": ITEM_ID, "quantity": 3}],  # RM30.00
        "payment_method": "cod",
    }
    body.update(overrides)
    return body


def _stored_order(db):
    orders = db.tables.get("delivery_orders", [])
    assert len(orders) == 1
    return orders[0]


# ---------------------------------------------------------------------------
# Pure logic
# ---------------------------------------------------------------------------

class TestVoucherMaths:
    def test_percent_voucher_respects_its_cap(self):
        voucher = {"discount_type": "percent", "discount_value": 10, "max_discount": 5}
        assert pe.voucher_discount(voucher, Decimal("30")) == Decimal("3.00")
        assert pe.voucher_discount(voucher, Decimal("200")) == Decimal("5.00")

    def test_fixed_voucher_never_exceeds_the_subtotal(self):
        voucher = {"discount_type": "fixed", "discount_value": 15}
        assert pe.voucher_discount(voucher, Decimal("40")) == Decimal("15.00")
        assert pe.voucher_discount(voucher, Decimal("9.50")) == Decimal("9.50")

    def test_discount_is_rounded_to_the_cent(self):
        voucher = {"discount_type": "percent", "discount_value": 15}
        assert pe.voucher_discount(voucher, Decimal("9.99")) == Decimal("1.50")

    def test_codes_are_normalised_the_way_customers_type_them(self):
        assert pe.normalize_code(" jimat-10 ") == "JIMAT10"
        assert pe.normalize_code(None) == ""


class TestVoucherEligibility:
    NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)

    def _voucher(self, **overrides):
        row = {"is_active": True, "min_order": 0, "used_count": 0}
        row.update(overrides)
        return row

    def test_usable_voucher_has_no_problem(self):
        assert pe.voucher_problem(self._voucher(), Decimal("10"), now=self.NOW) is None

    def test_unknown_and_inactive_codes_read_the_same(self):
        # Neither message tells a guesser that a paused code exists.
        assert pe.voucher_problem(None, Decimal("10")) == "Kod promo tidak sah"
        assert pe.voucher_problem(self._voucher(is_active=False), Decimal("10")) == "Kod promo tidak sah"

    def test_date_window(self):
        early = self._voucher(starts_at=(self.NOW + timedelta(days=1)).isoformat())
        late = self._voucher(expires_at=(self.NOW - timedelta(seconds=1)).isoformat())
        assert "belum bermula" in pe.voucher_problem(early, Decimal("10"), now=self.NOW)
        assert "tamat tempoh" in pe.voucher_problem(late, Decimal("10"), now=self.NOW)

    def test_expiry_accepts_the_z_suffix_supabase_returns(self):
        voucher = self._voucher(expires_at="2026-11-14T11:59:59Z")
        assert "tamat tempoh" in pe.voucher_problem(voucher, Decimal("10"), now=self.NOW)

    def test_usage_limits(self):
        spent = self._voucher(usage_limit=5, used_count=5)
        assert "habis ditebus" in pe.voucher_problem(spent, Decimal("10"), now=self.NOW)
        once = self._voucher(per_customer_limit=1)
        assert pe.voucher_problem(once, Decimal("10"), now=self.NOW, customer_uses=0) is None
        assert "telah menggunakan" in pe.voucher_problem(
            once, Decimal("10"), now=self.NOW, customer_uses=1)

    def test_minimum_order(self):
        voucher = self._voucher(min_order=25)
        assert "RM25.00" in pe.voucher_problem(voucher, Decimal("24.99"), now=self.NOW)
        assert pe.voucher_problem(voucher, Decimal("25"), now=self.NOW) is None


class TestLoyaltyMaths:
    SETTINGS = {"enabled": True, "points_per_rm": 1, "redeem_points": 100, "redeem_value": 5}

    def test_points_are_spent_in_whole_blocks(self):
        assert pe.loyalty_redemption(self.SETTINGS, 250, Decimal("30")) == (200, Decimal("10.00"))
        assert pe.loyalty_redemption(self.SETTINGS, 99, Decimal("30")) == (0, Decimal("0"))

    def test_no_more_blocks_are_spent_than_the_bill_needs(self):
        # RM12 bill: three RM5 blocks cover it, the third only partly. A
        # fourth block would be points thrown away.
        points, discount = pe.loyalty_redemption(self.SETTINGS, 1000, Decimal("12"))
        assert (points, discount) == (300, Decimal("12.00"))

    def test_disabled_programme_redeems_and_earns_nothing(self):
        off = {**self.SETTINGS, "enabled": False}
        assert pe.loyalty_redemption(off, 500, Decimal("30")) == (0, Decimal("0"))
        assert pe.points_for(off, Decimal("30")) == 0

    def test_earning_rounds_down(self):
        assert pe.points_for(self.SETTINGS, Decimal("29.99")) == 29
        assert pe.points_for({**self.SETTINGS, "points_per_rm": 2.5}, Decimal("10")) == 25

    def test_missing_settings_row_means_off(self):
        assert pe.clean_loyalty_settings(None)["enabled"] is False


class TestDineInSchema:
    def test_table_labels_are_short_and_plain(self):
        assert normalize_table_number(" 5 ") == "5"
        assert normalize_table_number("a-12") == "A-12"
        assert normalize_table_number("<script>") == ""
        assert normalize_table_number("123456789") == ""
        assert normalize_table_number(None) == ""

    def test_dine_in_order_gets_its_table_as_the_address(self):
        order = OrderCreate(**_order_body(
            order_type="dine_in", table_number="7",
            delivery_address="", delivery_latitude=None, delivery_longitude=None))
        assert order.delivery_address == "Makan di kedai · Meja 7"
        assert parse_dine_in_label(order.delivery_address) == "7"

    def test_dine_in_without_a_table_is_refused(self):
        with pytest.raises(ValueError, match="Nombor meja"):
            OrderCreate(**_order_body(order_type="dine_in", table_number=""))

    def test_a_real_address_is_not_mistaken_for_a_table(self):
        assert parse_dine_in_label("12 Jalan Meja 5") is None

    def test_phone_format_is_shared_with_orders(self):
        assert normalize_customer_phone("012-345 6789") == PHONE
        assert OrderCreate(**_order_body()).customer_phone == PHONE


# ---------------------------------------------------------------------------
# Order endpoint
# ---------------------------------------------------------------------------

class TestPlainDeliveryOrder:
    def test_writes_no_new_columns_and_touches_no_promo_tables(self, api, db):
        resp = api.post("/api/v1/delivery/orders", json=_order_body())
        assert resp.status_code == 200, resp.text
        order = _stored_order(db)
        for column in ("order_type", "table_number", "discount_amount",
                       "voucher_code", "loyalty_points_redeemed", "loyalty_discount"):
            assert column not in order
        promo_tables = {"vouchers", "voucher_redemptions", "loyalty_settings",
                        "loyalty_ledger", "loyalty_balances"}
        assert not promo_tables & {t for t, _ in db.touched}
        assert order["total_amount"] == 35.0  # RM30 food + RM5 delivery

    def test_still_requires_coordinates(self, api, db):
        resp = api.post("/api/v1/delivery/orders", json=_order_body(
            delivery_latitude=None, delivery_longitude=None))
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "MISSING_COORDINATES"


class TestDineInOrder:
    def _body(self, **overrides):
        body = _order_body(order_type="dine_in", table_number="5")
        for key in ("delivery_address", "delivery_latitude", "delivery_longitude"):
            body.pop(key)
        body.update(overrides)
        return body

    def test_needs_no_coordinates_zone_or_fee(self, api, db):
        resp = api.post("/api/v1/delivery/orders", json=self._body())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["order_type"] == "dine_in"
        assert body["table_number"] == "5"
        order = _stored_order(db)
        assert order["delivery_fee"] == 0
        assert order["total_amount"] == 30.0
        assert order["delivery_zone_id"] is None
        assert order["delivery_address"] == "Makan di kedai · Meja 5"
        assert "find_zone_for_point" not in db.rpc_calls

    def test_works_even_where_delivery_would_be_out_of_coverage(self, api, db):
        db.zone = None
        assert api.post("/api/v1/delivery/orders", json=self._body()).status_code == 200

    def test_a_tampered_table_label_is_refused(self, api, db):
        resp = api.post("/api/v1/delivery/orders", json=self._body(table_number="<img src=x>"))
        assert resp.status_code == 422
        assert not db.tables.get("delivery_orders")

    def test_can_use_a_voucher(self, api, db):
        db.add_voucher()
        resp = api.post("/api/v1/delivery/orders", json=self._body(voucher_code="jimat10"))
        assert resp.status_code == 200, resp.text
        assert _stored_order(db)["total_amount"] == 27.0


class TestVoucherAtCheckout:
    def test_discount_comes_off_the_food_not_the_delivery_fee(self, api, db):
        voucher = db.add_voucher()
        resp = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        assert resp.status_code == 200, resp.text
        order = _stored_order(db)
        assert order["subtotal"] == 30.0
        assert order["discount_amount"] == 3.0
        assert order["voucher_code"] == "JIMAT10"
        assert order["total_amount"] == 32.0  # 30 − 3 + 5
        assert voucher["used_count"] == 1
        redemption = db.tables["voucher_redemptions"][0]
        assert redemption["order_id"] == order["id"]
        assert redemption["customer_phone"] == PHONE

    def test_an_invalid_code_refuses_the_order_instead_of_charging_full_price(self, api, db):
        resp = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="TIADA"))
        assert resp.status_code == 400
        assert resp.json()["detail"] == {"error": "VOUCHER_INVALID", "message": "Kod promo tidak sah"}
        assert not db.tables.get("delivery_orders")

    def test_another_shops_code_is_not_valid_here(self, api, db):
        db.add_voucher(website_id=OTHER_WEBSITE_ID)
        resp = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        assert resp.status_code == 400

    def test_exhausted_voucher_is_refused(self, api, db):
        db.add_voucher(usage_limit=1, used_count=1)
        resp = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        assert resp.status_code == 400
        assert "habis" in resp.json()["detail"]["message"]

    def test_per_customer_limit_is_keyed_on_the_phone(self, api, db):
        db.add_voucher(per_customer_limit=1)
        first = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        again = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        other = api.post("/api/v1/delivery/orders", json=_order_body(
            voucher_code="JIMAT10", customer_phone="0198887777"))
        assert (first.status_code, again.status_code, other.status_code) == (200, 400, 200)

    def test_minimum_order_uses_the_server_side_subtotal(self, api, db):
        db.add_voucher(min_order=50)
        resp = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        assert resp.status_code == 400
        assert "RM50.00" in resp.json()["detail"]["message"]

    def test_the_use_is_handed_back_when_the_order_fails_to_save(self, api, db):
        voucher = db.add_voucher(usage_limit=1)
        db.fail_on = {"insert": {"delivery_orders"}}
        resp = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        assert resp.status_code == 500
        assert voucher["used_count"] == 0
        assert db.tables["voucher_redemptions"] == []

    def test_the_use_is_handed_back_when_the_items_fail_to_save(self, api, db):
        voucher = db.add_voucher()
        db.fail_on = {"insert": {"order_items"}}
        resp = api.post("/api/v1/delivery/orders", json=_order_body(voucher_code="JIMAT10"))
        assert resp.status_code == 500
        assert voucher["used_count"] == 0


class TestLoyaltyAtCheckout:
    def test_points_are_spent_and_tied_to_the_order(self, api, db):
        db.enable_loyalty()
        db.add_points(250)
        resp = api.post("/api/v1/delivery/orders", json=_order_body(redeem_points=True))
        assert resp.status_code == 200, resp.text
        order = _stored_order(db)
        assert order["loyalty_points_redeemed"] == 200
        assert order["loyalty_discount"] == 10.0
        assert order["total_amount"] == 25.0  # 30 − 10 + 5
        spend = [r for r in db.tables["loyalty_ledger"] if r["reason"] == "redeem"]
        assert [(r["points"], r["order_id"]) for r in spend] == [(-200, order["id"])]

    def test_voucher_and_points_stack_without_going_below_zero(self, api, db):
        db.add_voucher(discount_type="fixed", discount_value=25)
        db.enable_loyalty()
        db.add_points(1000)
        resp = api.post("/api/v1/delivery/orders", json=_order_body(
            voucher_code="JIMAT10", redeem_points=True))
        assert resp.status_code == 200, resp.text
        order = _stored_order(db)
        # RM30 − RM25 voucher leaves RM5: exactly one block of points.
        assert order["loyalty_points_redeemed"] == 100
        assert order["total_amount"] == 5.0  # only the delivery fee remains

    def test_asking_to_redeem_with_too_few_points_refuses_and_frees_the_voucher(self, api, db):
        voucher = db.add_voucher()
        db.enable_loyalty()
        db.add_points(40)
        resp = api.post("/api/v1/delivery/orders", json=_order_body(
            voucher_code="JIMAT10", redeem_points=True))
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "LOYALTY_INSUFFICIENT"
        assert voucher["used_count"] == 0
        assert not db.tables.get("delivery_orders")

    def test_points_come_back_when_the_order_fails_to_save(self, api, db):
        db.enable_loyalty()
        db.add_points(100)
        db.fail_on = {"insert": {"delivery_orders"}}
        resp = api.post("/api/v1/delivery/orders", json=_order_body(redeem_points=True))
        assert resp.status_code == 500
        assert sum(r["points"] for r in db.tables["loyalty_ledger"]) == 100


class TestOrderStatusByType:
    def _order(self, db, **overrides):
        row = {"id": "o-1", "order_number": "BNA-0001", "website_id": WEBSITE_ID,
               "status": "ready", "customer_name": "A", "customer_phone": PHONE,
               "customer_email": None, "delivery_address": "x", "delivery_latitude": None,
               "delivery_longitude": None, "delivery_notes": None, "delivery_zone_id": None,
               "delivery_fee": 0, "subtotal": 10, "total_amount": 10, "payment_method": "cod",
               "payment_status": "pending", "payment_reference": None,
               "created_at": datetime.now(timezone.utc).isoformat(), "confirmed_at": None,
               "preparing_at": None, "ready_at": None, "picked_up_at": None,
               "delivered_at": None, "completed_at": None, "cancelled_at": None,
               "rider_id": None, "estimated_prep_time": 30, "estimated_delivery_time": None,
               "actual_delivery_time": None}
        row.update(overrides)
        db.tables["delivery_orders"] = [row]
        return row

    def test_dine_in_is_completed_straight_from_ready(self, api, db, auth_headers):
        self._order(db, order_type="dine_in", table_number="5")
        resp = api.put("/api/v1/delivery/orders/o-1/status",
                       json={"status": "completed"}, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "completed"

    def test_delivery_still_has_to_be_delivered_first(self, api, db, auth_headers):
        self._order(db)
        resp = api.put("/api/v1/delivery/orders/o-1/status",
                       json={"status": "completed"}, headers=auth_headers)
        assert resp.status_code == 409

    def test_dine_in_never_goes_out_with_a_rider(self, api, db, auth_headers):
        self._order(db, order_type="dine_in", table_number="5")
        resp = api.put("/api/v1/delivery/orders/o-1/status",
                       json={"status": "delivering"}, headers=auth_headers)
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Promotions API
# ---------------------------------------------------------------------------

VOUCHERS_URL = f"/api/v1/promotions/websites/{WEBSITE_ID}/vouchers"
VOUCHER = {"code": "raya-15", "discount_type": "percent", "discount_value": 15,
           "max_discount": 8, "min_order": 20}


class TestVoucherManagement:
    def test_requires_login(self, api):
        assert api.get(VOUCHERS_URL).status_code in (401, 403)
        assert api.post(VOUCHERS_URL, json=VOUCHER).status_code in (401, 403)

    def test_only_the_owner_may_manage_a_sites_vouchers(self, api, auth_headers):
        url = f"/api/v1/promotions/websites/{OTHER_WEBSITE_ID}/vouchers"
        assert api.get(url, headers=auth_headers).status_code == 403
        assert api.post(url, json=VOUCHER, headers=auth_headers).status_code == 403

    def test_create_normalises_the_code_and_lists_it(self, api, auth_headers):
        created = api.post(VOUCHERS_URL, json=VOUCHER, headers=auth_headers)
        assert created.status_code == 201, created.text
        assert created.json()["code"] == "RAYA15"
        assert created.json()["summary"] == "15% diskaun (maks RM8.00) · min. RM20.00"
        listed = api.get(VOUCHERS_URL, headers=auth_headers).json()["vouchers"]
        assert [v["code"] for v in listed] == ["RAYA15"]

    def test_duplicate_code_is_a_conflict(self, api, auth_headers):
        api.post(VOUCHERS_URL, json=VOUCHER, headers=auth_headers)
        assert api.post(VOUCHERS_URL, json=VOUCHER, headers=auth_headers).status_code == 409

    @pytest.mark.parametrize("bad", [
        {"code": "A"},
        {"code": "KOD PROMO!"},
        {"discount_value": 0},
        {"discount_value": 150},
        {"expires_at": "2026-01-01T00:00:00Z", "starts_at": "2026-02-01T00:00:00Z"},
    ])
    def test_bad_vouchers_are_rejected(self, api, auth_headers, bad):
        resp = api.post(VOUCHERS_URL, json={**VOUCHER, **bad}, headers=auth_headers)
        assert resp.status_code == 422

    def test_a_cap_is_dropped_from_a_fixed_voucher(self, api, auth_headers):
        resp = api.post(VOUCHERS_URL, headers=auth_headers, json={
            "code": "RM5OFF", "discount_type": "fixed", "discount_value": 5, "max_discount": 3})
        assert resp.status_code == 201
        assert resp.json()["max_discount"] is None

    def test_pause_then_clear_a_limit(self, api, db, auth_headers):
        voucher = db.add_voucher(usage_limit=10)
        url = f"/api/v1/promotions/vouchers/{voucher['id']}"
        assert api.patch(url, json={"is_active": False}, headers=auth_headers).json()["is_active"] is False
        assert voucher["usage_limit"] == 10  # untouched by an unrelated patch
        assert api.patch(url, json={"usage_limit": None}, headers=auth_headers).json()["usage_limit"] is None

    def test_a_patch_is_validated_against_the_whole_voucher(self, api, db, auth_headers):
        voucher = db.add_voucher()  # percent
        url = f"/api/v1/promotions/vouchers/{voucher['id']}"
        assert api.patch(url, json={"discount_value": 150}, headers=auth_headers).status_code == 422

    def test_someone_elses_voucher_cannot_be_edited_or_deleted(self, api, db, auth_headers):
        voucher = db.add_voucher(website_id=OTHER_WEBSITE_ID)
        url = f"/api/v1/promotions/vouchers/{voucher['id']}"
        assert api.patch(url, json={"is_active": False}, headers=auth_headers).status_code == 403
        assert api.delete(url, headers=auth_headers).status_code == 403
        assert voucher in db.tables["vouchers"]

    def test_delete(self, api, db, auth_headers):
        voucher = db.add_voucher()
        resp = api.delete(f"/api/v1/promotions/vouchers/{voucher['id']}", headers=auth_headers)
        assert resp.status_code == 204
        assert db.tables["vouchers"] == []


class TestLoyaltyManagement:
    URL = f"/api/v1/promotions/websites/{WEBSITE_ID}/loyalty"

    def test_off_by_default(self, api, auth_headers):
        assert api.get(self.URL, headers=auth_headers).json()["enabled"] is False

    def test_owner_turns_it_on(self, api, auth_headers):
        resp = api.put(self.URL, headers=auth_headers, json={
            "enabled": True, "points_per_rm": 2, "redeem_points": 50, "redeem_value": 3})
        assert resp.status_code == 200, resp.text
        assert api.get(self.URL, headers=auth_headers).json() == {
            "enabled": True, "points_per_rm": 2.0, "redeem_points": 50, "redeem_value": 3.0}

    def test_not_for_other_peoples_sites(self, api, auth_headers):
        url = f"/api/v1/promotions/websites/{OTHER_WEBSITE_ID}/loyalty"
        assert api.get(url, headers=auth_headers).status_code == 403
        assert api.put(url, json={"enabled": True}, headers=auth_headers).status_code == 403

    def test_manual_adjustment_cannot_overdraw(self, api, db, auth_headers):
        db.add_points(30)
        url = f"{self.URL}/adjust"
        ok = api.post(url, json={"customer_phone": "0123456789", "points": 20}, headers=auth_headers)
        assert ok.json() == {"customer_phone": PHONE, "balance": 50}
        over = api.post(url, json={"customer_phone": "0123456789", "points": -80}, headers=auth_headers)
        assert over.status_code == 409

    def test_members_are_listed_for_the_owner(self, api, db, auth_headers):
        db.add_points(120)
        members = api.get(f"{self.URL}/members", headers=auth_headers).json()["members"]
        assert members[0]["customer_phone"] == PHONE
        assert members[0]["balance"] == 120


class TestQuote:
    URL = "/api/v1/promotions/quote"

    def test_valid_code(self, api, db):
        db.add_voucher(max_discount=2)
        body = api.post(self.URL, json={
            "website_id": WEBSITE_ID, "subtotal": 30, "voucher_code": "jimat10"}).json()
        assert body["voucher"]["valid"] is True
        assert body["voucher"]["discount"] == 2.0
        assert body["discount_total"] == 2.0
        assert body["payable_subtotal"] == 28.0

    def test_invalid_code_explains_itself_and_discounts_nothing(self, api, db):
        db.add_voucher(min_order=50)
        body = api.post(self.URL, json={
            "website_id": WEBSITE_ID, "subtotal": 30, "voucher_code": "JIMAT10"}).json()
        assert body["voucher"]["valid"] is False
        assert "RM50.00" in body["voucher"]["message"]
        assert body["discount_total"] == 0

    def test_a_quote_changes_nothing(self, api, db):
        voucher = db.add_voucher()
        db.enable_loyalty()
        db.add_points(300)
        api.post(self.URL, json={
            "website_id": WEBSITE_ID, "subtotal": 30, "voucher_code": "JIMAT10",
            "customer_phone": "0123456789", "redeem_points": True})
        assert voucher["used_count"] == 0
        assert db.rpc_calls == []
        assert sum(r["points"] for r in db.tables["loyalty_ledger"]) == 300

    def test_loyalty_preview(self, api, db):
        db.enable_loyalty()
        db.add_points(250)
        req = {"website_id": WEBSITE_ID, "subtotal": 30, "customer_phone": "0123456789"}
        offered = api.post(self.URL, json=req).json()["loyalty"]
        assert offered == {
            "enabled": True, "balance": 250, "redeemable_points": 200,
            "redeem_discount": 10.0, "will_earn": 30, "redeem_points": 100,
            "redeem_value": 5.0, "applied": False}
        applied = api.post(self.URL, json={**req, "redeem_points": True}).json()
        assert applied["loyalty"]["applied"] is True
        assert applied["loyalty"]["will_earn"] == 20  # earned on what is paid
        assert applied["discount_total"] == 10.0

    def test_works_before_the_promo_tables_exist(self, api, db):
        db.fail_on = {"select": {"vouchers", "loyalty_settings"}}
        resp = api.post(self.URL, json={
            "website_id": WEBSITE_ID, "subtotal": 30, "voucher_code": "JIMAT10"})
        assert resp.status_code == 200
        assert resp.json()["voucher"]["valid"] is False
        assert resp.json()["loyalty"]["enabled"] is False

    def test_code_guessing_is_rate_limited(self, api, db):
        req = {"website_id": WEBSITE_ID, "subtotal": 30, "voucher_code": "AAA"}
        codes = [api.post(self.URL, json=req).status_code for _ in range(31)]
        assert codes[:30] == [200] * 30
        assert codes[30] == 429


# ---------------------------------------------------------------------------
# Table QR → order flow hand-off on the served site
# ---------------------------------------------------------------------------

class TestTableQrHandOff:
    def _inject(self, html):
        from app.middleware.subdomain import _inject_widgets
        return _inject_widgets(html, WEBSITE_ID, subdomain="kedaiali")

    def test_served_pages_carry_the_table_script_even_without_delivery(self):
        # A dine-in-only restaurant never enabled delivery, so there is no
        # static order button; the script creates one when ?meja is present.
        html = self._inject("<html><body><p>Kedai Ali</p></body></html>")
        assert 'id="binaapp-table-order"' in html
        assert "/order/identify?r=kedaiali&meja=" in html
        assert 'class="binaapp-order-button"' not in html

    def test_the_table_value_is_validated_and_never_written_as_markup(self):
        html = self._inject("<html><body></body></html>")
        script = html[html.index('id="binaapp-table-order"'):]
        script = script[: script.index("</script>")]
        assert "/^[A-Z0-9-]{1,8}$/.test(meja)" in script
        assert "encodeURIComponent(meja)" in script
        assert "innerHTML" not in script
