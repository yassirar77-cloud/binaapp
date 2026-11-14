"""Tests for the booking engine.

What matters:

  1. Slots are in Malaysian time, only exist where the whole service fits
     inside opening hours, and stop being offered when they are full, too
     soon, too far ahead or on a closed day.
  2. A customer can only book a slot the engine itself would offer — and
     when the database says the slot filled up first, that is a 409, not
     a 500 and not a silent double booking.
  3. Merchant endpoints are 401 without a login and 403 on someone else's
     website; a customer needs reference AND phone to see or cancel.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import bookings as api
from app.services import booking_engine as engine
from app.services import booking_store as store

MYT = engine.MYT
WS = "11111111-1111-4111-8111-111111111111"
SVC = "22222222-2222-4222-8222-222222222222"
BK = "33333333-3333-4333-8333-333333333333"

# Monday 16 Nov 2026, 08:00 in Malaysia.
NOW = datetime(2026, 11, 16, 8, 0, tzinfo=MYT)
MONDAY = date(2026, 11, 16)
SUNDAY = date(2026, 11, 22)


def _settings(**overrides):
    base = {
        "enabled": True,
        "slot_interval_min": 30,
        "capacity_per_slot": 1,
        "lead_time_min": 60,
        "max_days_ahead": 30,
        "weekly_hours": {
            d: [{"open": "09:00", "close": "12:00"}]
            for d in ("mon", "tue", "wed", "thu", "fri", "sat")
        },
        "closed_dates": [],
        "note": "",
    }
    base.update(overrides)
    return engine.normalize_settings(base)


def _booking(day, hhmm, minutes=30, status="confirmed"):
    start = datetime.combine(day, datetime.strptime(hhmm, "%H:%M").time(), tzinfo=MYT)
    return {
        "start_at": start.astimezone(timezone.utc).isoformat(),
        "end_at": (start + timedelta(minutes=minutes)).astimezone(timezone.utc).isoformat(),
        "status": status,
    }


# ---------------------------------------------------------------------------
# Slot rules
# ---------------------------------------------------------------------------

class TestSlots:
    def test_slots_step_by_the_interval_and_fit_before_closing(self):
        slots = engine.generate_slots(_settings(), 60, MONDAY, now=NOW)
        # 09:00–12:00, 60-minute service: last start that fits is 11:00.
        assert [s["time"] for s in slots] == ["09:00", "09:30", "10:00", "10:30", "11:00"]

    def test_slot_instants_are_malaysian_time_stored_as_utc(self):
        first = engine.generate_slots(_settings(), 30, MONDAY, now=NOW)[0]
        assert first["start_at"] == "2026-11-16T01:00:00+00:00"  # 09:00 MYT
        assert first["end_at"] == "2026-11-16T01:30:00+00:00"

    def test_lead_time_hides_slots_that_start_too_soon(self):
        now = datetime(2026, 11, 16, 9, 10, tzinfo=MYT)
        slots = {s["time"]: s["available"] for s in engine.generate_slots(_settings(), 30, MONDAY, now=now)}
        assert slots["09:00"] is False
        assert slots["10:00"] is False  # 50 minutes away, needs 60
        assert slots["10:30"] is True

    def test_a_full_slot_is_not_available(self):
        slots = {
            s["time"]: s
            for s in engine.generate_slots(_settings(), 30, MONDAY, [_booking(MONDAY, "10:00")], now=NOW)
        }
        assert slots["10:00"]["available"] is False
        assert slots["10:00"]["remaining"] == 0
        assert slots["10:30"]["available"] is True

    def test_a_long_booking_blocks_every_slot_it_overlaps(self):
        taken = [_booking(MONDAY, "10:00", minutes=60)]
        slots = {s["time"]: s["available"] for s in engine.generate_slots(_settings(), 30, MONDAY, taken, now=NOW)}
        assert slots["09:30"] is True
        assert slots["10:00"] is False and slots["10:30"] is False
        assert slots["11:00"] is True

    def test_a_long_service_cannot_start_into_an_existing_booking(self):
        taken = [_booking(MONDAY, "10:00")]
        slots = {s["time"]: s["available"] for s in engine.generate_slots(_settings(), 60, MONDAY, taken, now=NOW)}
        assert slots["09:30"] is False  # would run 09:30–10:30
        assert slots["10:30"] is True

    def test_capacity_lets_several_customers_share_a_slot(self):
        settings = _settings(capacity_per_slot=2)
        one = engine.generate_slots(settings, 30, MONDAY, [_booking(MONDAY, "10:00")], now=NOW)
        two = engine.generate_slots(settings, 30, MONDAY, [_booking(MONDAY, "10:00")] * 2, now=NOW)
        assert {s["time"]: s for s in one}["10:00"]["remaining"] == 1
        assert {s["time"]: s for s in two}["10:00"]["available"] is False

    def test_cancelled_bookings_free_the_slot(self):
        taken = [_booking(MONDAY, "10:00", status="cancelled"), _booking(MONDAY, "10:00", status="no_show")]
        slots = {s["time"]: s["available"] for s in engine.generate_slots(_settings(), 30, MONDAY, taken, now=NOW)}
        assert slots["10:00"] is True

    def test_a_lunch_break_produces_no_slot_across_the_gap(self):
        settings = _settings(weekly_hours={
            "mon": [{"open": "09:00", "close": "10:00"}, {"open": "14:00", "close": "15:00"}]
        })
        times = [s["time"] for s in engine.generate_slots(settings, 60, MONDAY, now=NOW)]
        assert times == ["09:00", "14:00"]

    @pytest.mark.parametrize(
        "day,code",
        [
            (SUNDAY, "DATE_CLOSED"),
            (MONDAY - timedelta(days=1), "DATE_PAST"),
            (MONDAY + timedelta(days=31), "DATE_TOO_FAR"),
        ],
    )
    def test_unbookable_days_have_no_slots_and_say_why(self, day, code):
        settings = _settings()
        assert engine.generate_slots(settings, 30, day, now=NOW) == []
        assert engine.date_problem(settings, day, NOW).code == code

    def test_closed_dates_override_opening_hours(self):
        settings = _settings(closed_dates=["2026-11-17"])
        assert engine.generate_slots(settings, 30, date(2026, 11, 17), now=NOW) == []

    def test_today_is_decided_in_malaysian_time_not_utc(self):
        # 00:30 Tuesday in Malaysia is still Monday 16:30 in UTC.
        now = datetime(2026, 11, 16, 16, 30, tzinfo=timezone.utc)
        assert engine.date_problem(_settings(), MONDAY, now).code == "DATE_PAST"


class TestResolveSlot:
    def test_an_offered_slot_resolves(self):
        slot = engine.resolve_slot(_settings(), 30, MONDAY, "10:00", now=NOW)
        assert slot["time"] == "10:00"

    @pytest.mark.parametrize("hhmm", ["10:07", "08:00", "12:00", "11:45"])
    def test_a_time_the_engine_would_not_offer_is_refused(self, hhmm):
        with pytest.raises(engine.BookingError) as err:
            engine.resolve_slot(_settings(), 30, MONDAY, hhmm, now=NOW)
        assert err.value.code == "SLOT_INVALID"

    def test_full_and_too_soon_are_distinct(self):
        with pytest.raises(engine.BookingError) as full:
            engine.resolve_slot(_settings(), 30, MONDAY, "10:00", [_booking(MONDAY, "10:00")], now=NOW)
        assert full.value.code == "SLOT_FULL"
        with pytest.raises(engine.BookingError) as soon:
            engine.resolve_slot(_settings(lead_time_min=120), 30, MONDAY, "09:00", now=NOW)
        assert soon.value.code == "SLOT_TOO_SOON"

    def test_nothing_resolves_while_booking_is_switched_off(self):
        with pytest.raises(engine.BookingError) as err:
            engine.resolve_slot(_settings(enabled=False), 30, MONDAY, "10:00", now=NOW)
        assert err.value.code == "BOOKING_DISABLED"


class TestSettingsAndParsers:
    def test_a_site_with_no_row_gets_safe_defaults_with_booking_off(self):
        settings = engine.normalize_settings(None)
        assert settings["enabled"] is False
        assert settings["weekly_hours"]["sun"] == []
        assert settings["weekly_hours"]["mon"] == [{"open": "09:00", "close": "18:00"}]

    def test_strict_mode_rejects_bad_hours(self):
        for hours in (
            {"mon": [{"open": "18:00", "close": "09:00"}]},
            {"mon": [{"open": "9am", "close": "18:00"}]},
            {"mon": [{"open": "09:00", "close": "13:00"}, {"open": "12:00", "close": "18:00"}]},
        ):
            with pytest.raises(engine.BookingError):
                engine.clean_weekly_hours(hours, strict=True)

    def test_lenient_mode_drops_bad_ranges_instead_of_failing(self):
        cleaned = engine.clean_weekly_hours(
            {"mon": [{"open": "bad", "close": "x"}, {"open": "10:00", "close": "11:00"}]}
        )
        assert cleaned["mon"] == [{"open": "10:00", "close": "11:00"}]

    def test_stored_numbers_are_clamped(self):
        settings = engine.normalize_settings({"capacity_per_slot": 0, "slot_interval_min": 9999})
        assert settings["capacity_per_slot"] == 1
        assert settings["slot_interval_min"] == 240

    @pytest.mark.parametrize(
        "raw", ["012-345 6789", "+60 12-345 6789", "60123456789", "123456789"]
    )
    def test_phone_numbers_normalise_to_one_form(self, raw):
        assert engine.normalize_phone(raw) == "60123456789"

    def test_garbage_phone_is_rejected(self):
        with pytest.raises(engine.BookingError):
            engine.normalize_phone("12")

    def test_references_avoid_lookalike_characters_and_round_trip(self):
        ref = engine.make_reference()
        assert engine.clean_reference(ref.lower()) == ref
        assert not set(ref[3:]) & set("01OIL")

    def test_postgrest_timestamps_parse(self):
        parsed = engine.parse_instant("2026-11-16T01:00:00+00")
        assert parsed == datetime(2026, 11, 16, 1, 0, tzinfo=timezone.utc)

    def test_status_transitions(self):
        assert engine.can_transition("pending", "confirmed")
        assert engine.can_transition("confirmed", "no_show")
        assert not engine.can_transition("pending", "completed")
        assert not engine.can_transition("cancelled", "confirmed")

    def test_customer_view_masks_the_phone(self):
        booking = {**_booking(MONDAY, "10:00"), "customer_phone": "60123456789", "reference": "TP-ABC234"}
        view = engine.public_booking_view(booking)
        assert view["customer_phone_masked"] == "*******6789"
        assert "customer_phone" not in view
        assert (view["date"], view["time"]) == ("2026-11-16", "10:00")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _tomorrow():
    """A bookable weekday, far enough ahead that lead time never matters."""
    day = engine.now_myt().date() + timedelta(days=2)
    while day.weekday() == 6:
        day += timedelta(days=1)
    return day


def _stored_booking(**overrides):
    day = _tomorrow()
    row = {
        "id": BK,
        "website_id": WS,
        "service_id": SVC,
        "service_name": "Potong Rambut",
        "duration_min": 30,
        "price": 25.0,
        "reference": "TP-ABC234",
        "booking_date": day.isoformat(),
        **_booking(day, "10:00", status="pending"),
        "customer_name": "Aminah",
        "customer_phone": "60123456789",
        "notes": "",
        "cancelled_by": None,
        "created_at": "2026-11-14T00:00:00+00:00",
    }
    row.update(overrides)
    return row


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(api.router, prefix="/api/v1")
    api.reset_rate_limits()
    yield TestClient(app)
    api.reset_rate_limits()


@pytest.fixture
def db(test_user_id):
    """Every store call the router makes, faked."""
    site = {"id": WS, "user_id": test_user_id, "business_name": "Salon Seri", "status": "published"}
    settings_row = {
        "enabled": True, "slot_interval_min": 30, "capacity_per_slot": 1,
        "lead_time_min": 60, "max_days_ahead": 30,
        "weekly_hours": {d: [{"open": "09:00", "close": "12:00"}] for d in engine.WEEKDAYS[:6]},
        "closed_dates": [], "note": "Deposit RM10",
    }
    service = {
        "id": SVC, "website_id": WS, "name": "Potong Rambut", "description": "",
        "duration_min": 30, "price": 25.0, "active": True, "sort_order": 0,
    }
    targets = {
        "get_site": site,
        "get_settings": settings_row,
        "save_settings": settings_row,
        "list_services": [service],
        "get_service": service,
        "create_service": service,
        "update_service": service,
        "delete_service": True,
        "list_bookings_for_date": [],
        "list_bookings": [_stored_booking()],
        "get_booking": _stored_booking(),
        "get_booking_by_reference": _stored_booking(),
        "insert_booking": _stored_booking(),
        "set_booking_status": _stored_booking(status="confirmed"),
        "notify_owner": None,
        "get_owner_phone": None,
    }
    mocks, patchers = {}, []
    for name, value in targets.items():
        patcher = patch.object(store, name, new=AsyncMock(return_value=value))
        mocks[name] = patcher.start()
        patchers.append(patcher)
    yield mocks
    for patcher in patchers:
        patcher.stop()


def _create_body(**overrides):
    body = {
        "service_id": SVC,
        "date": _tomorrow().isoformat(),
        "time": "10:00",
        "customer_name": "Aminah",
        "customer_phone": "012-345 6789",
    }
    body.update(overrides)
    return body


class TestMerchantGates:
    ADMIN_GETS = ("settings", "services", "bookings")

    def test_no_login_is_refused(self, client, db):
        for path in self.ADMIN_GETS:
            assert client.get(f"/api/v1/bookings/admin/{WS}/{path}").status_code in (401, 403)

    def test_someone_elses_website_is_403(self, client, db, auth_headers):
        db["get_site"].return_value = {"id": WS, "user_id": "another-user"}
        for path in self.ADMIN_GETS:
            resp = client.get(f"/api/v1/bookings/admin/{WS}/{path}", headers=auth_headers)
            assert resp.status_code == 403
        resp = client.put(
            f"/api/v1/bookings/admin/{WS}/bookings/{BK}/status",
            json={"status": "confirmed"}, headers=auth_headers,
        )
        assert resp.status_code == 403
        db["set_booking_status"].assert_not_called()

    def test_unknown_website_is_404(self, client, db, auth_headers):
        db["get_site"].return_value = {}
        resp = client.get(f"/api/v1/bookings/admin/{WS}/settings", headers=auth_headers)
        assert resp.status_code == 404
        assert client.get("/api/v1/bookings/admin/not-a-uuid/settings", headers=auth_headers).status_code == 404

    def test_database_down_is_503_not_an_empty_answer(self, client, db, auth_headers):
        db["get_site"].return_value = None
        assert client.get(f"/api/v1/bookings/admin/{WS}/services", headers=auth_headers).status_code == 503


class TestMerchantEndpoints:
    def test_settings_round_trip(self, client, db, auth_headers):
        body = {
            "enabled": True, "slot_interval_min": 15, "capacity_per_slot": 2,
            "lead_time_min": 0, "max_days_ahead": 14,
            "weekly_hours": {"mon": [{"open": "10:00", "close": "20:00"}]},
            "closed_dates": ["2026-12-25"], "note": "",
        }
        resp = client.put(f"/api/v1/bookings/admin/{WS}/settings", json=body, headers=auth_headers)
        assert resp.status_code == 200
        saved = db["save_settings"].call_args.args[1]
        assert saved["slot_interval_min"] == 15
        assert saved["weekly_hours"]["mon"] == [{"open": "10:00", "close": "20:00"}]
        assert saved["weekly_hours"]["tue"] == []

    def test_bad_hours_are_422_and_nothing_is_saved(self, client, db, auth_headers):
        body = {"enabled": True, "weekly_hours": {"mon": [{"open": "20:00", "close": "10:00"}]}}
        resp = client.put(f"/api/v1/bookings/admin/{WS}/settings", json=body, headers=auth_headers)
        assert resp.status_code == 422
        db["save_settings"].assert_not_called()

    def test_enabling_with_no_open_day_is_refused(self, client, db, auth_headers):
        resp = client.put(
            f"/api/v1/bookings/admin/{WS}/settings",
            json={"enabled": True, "weekly_hours": {}}, headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_create_service(self, client, db, auth_headers):
        resp = client.post(
            f"/api/v1/bookings/admin/{WS}/services",
            json={"name": "  Potong Rambut ", "duration_min": 30, "price": 25},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert db["create_service"].call_args.args[1]["name"] == "Potong Rambut"

    def test_service_duration_out_of_range_is_422(self, client, db, auth_headers):
        resp = client.post(
            f"/api/v1/bookings/admin/{WS}/services",
            json={"name": "X", "duration_min": 2}, headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_owner_sees_the_full_phone(self, client, db, auth_headers):
        resp = client.get(f"/api/v1/bookings/admin/{WS}/bookings", headers=auth_headers)
        booking = resp.json()["bookings"][0]
        assert booking["customer_phone"] == "60123456789"
        assert booking["next_statuses"] == ["cancelled", "confirmed"]

    def test_confirming_a_booking(self, client, db, auth_headers):
        resp = client.put(
            f"/api/v1/bookings/admin/{WS}/bookings/{BK}/status",
            json={"status": "confirmed"}, headers=auth_headers,
        )
        assert resp.status_code == 200
        assert db["set_booking_status"].call_args.kwargs["from_status"] == "pending"

    def test_an_illegal_transition_is_409(self, client, db, auth_headers):
        resp = client.put(
            f"/api/v1/bookings/admin/{WS}/bookings/{BK}/status",
            json={"status": "completed"}, headers=auth_headers,
        )
        assert resp.status_code == 409
        db["set_booking_status"].assert_not_called()

    def test_losing_a_race_on_status_is_409(self, client, db, auth_headers):
        db["set_booking_status"].return_value = None
        resp = client.put(
            f"/api/v1/bookings/admin/{WS}/bookings/{BK}/status",
            json={"status": "confirmed"}, headers=auth_headers,
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "STALE"


class TestCustomerEndpoints:
    def test_info_lists_services_without_internal_fields(self, client, db):
        data = client.get(f"/api/v1/bookings/public/{WS}").json()
        assert data["enabled"] is True and data["business_name"] == "Salon Seri"
        assert set(data["services"][0]) == {"id", "name", "description", "duration_min", "price"}
        assert "sun" not in data["open_weekdays"]

    def test_info_reports_disabled_and_hides_services(self, client, db):
        db["get_settings"].return_value = {}
        data = client.get(f"/api/v1/bookings/public/{WS}").json()
        assert data["enabled"] is False and data["services"] == []

    def test_slots_do_not_leak_how_many_seats_are_left(self, client, db):
        resp = client.get(
            f"/api/v1/bookings/public/{WS}/slots",
            params={"service_id": SVC, "date": _tomorrow().isoformat()},
        )
        slots = resp.json()["slots"]
        assert slots and set(slots[0]) == {"time", "available"}

    def test_slots_for_a_closed_day_explain_why(self, client, db):
        day = engine.now_myt().date()
        while day.weekday() != 6:
            day += timedelta(days=1)
        data = client.get(
            f"/api/v1/bookings/public/{WS}/slots", params={"service_id": SVC, "date": day.isoformat()}
        ).json()
        assert data["slots"] == [] and data["reason"] == "DATE_CLOSED"

    def test_booking_is_created_through_the_locked_insert(self, client, db):
        resp = client.post(f"/api/v1/bookings/public/{WS}", json=_create_body())
        assert resp.status_code == 201
        args = db["insert_booking"].call_args.args[0]
        assert args["p_customer_phone"] == "60123456789"
        assert args["p_capacity"] == 1
        assert args["p_service_name"] == "Potong Rambut"  # snapshot, not client input
        assert args["p_reference"].startswith("TP-")
        body = resp.json()
        assert body["reference"] == "TP-ABC234" and "customer_phone" not in body
        db["notify_owner"].assert_called_once()

    def test_a_time_off_the_grid_is_400_and_never_reaches_the_database(self, client, db):
        resp = client.post(f"/api/v1/bookings/public/{WS}", json=_create_body(time="10:07"))
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "SLOT_INVALID"
        db["insert_booking"].assert_not_called()

    def test_a_slot_already_taken_is_409(self, client, db):
        db["list_bookings_for_date"].return_value = [_booking(_tomorrow(), "10:00")]
        resp = client.post(f"/api/v1/bookings/public/{WS}", json=_create_body())
        assert resp.status_code == 409
        db["insert_booking"].assert_not_called()

    def test_losing_the_race_in_the_database_is_409_not_500(self, client, db):
        db["insert_booking"].side_effect = store.SlotFull()
        resp = client.post(f"/api/v1/bookings/public/{WS}", json=_create_body())
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"] == "SLOT_FULL"
        db["notify_owner"].assert_not_called()

    def test_same_phone_same_time_is_409(self, client, db):
        db["insert_booking"].side_effect = store.DuplicateBooking()
        resp = client.post(f"/api/v1/bookings/public/{WS}", json=_create_body())
        assert resp.json()["detail"]["error"] == "DUPLICATE_BOOKING"

    def test_a_reference_collision_is_retried(self, client, db):
        db["insert_booking"].side_effect = [store.DuplicateReference(), _stored_booking()]
        resp = client.post(f"/api/v1/bookings/public/{WS}", json=_create_body())
        assert resp.status_code == 201
        assert db["insert_booking"].call_count == 2

    def test_booking_while_switched_off_is_409(self, client, db):
        db["get_settings"].return_value = {}
        assert client.post(f"/api/v1/bookings/public/{WS}", json=_create_body()).status_code == 409

    def test_inactive_service_cannot_be_booked(self, client, db):
        db["get_service"].return_value = {"id": SVC, "active": False, "duration_min": 30, "name": "X"}
        assert client.post(f"/api/v1/bookings/public/{WS}", json=_create_body()).status_code == 404

    def test_a_failing_notification_does_not_fail_the_booking(self, client, db):
        db["notify_owner"].side_effect = RuntimeError("bell broke")
        assert client.post(f"/api/v1/bookings/public/{WS}", json=_create_body()).status_code == 201

    def test_bad_phone_is_422(self, client, db):
        resp = client.post(f"/api/v1/bookings/public/{WS}", json=_create_body(customer_phone="1234567"))
        assert resp.status_code == 422

    def test_creation_is_rate_limited_per_ip(self, client, db):
        codes = [
            client.post(f"/api/v1/bookings/public/{WS}", json=_create_body()).status_code
            for _ in range(api._LIMITS["create"] + 1)
        ]
        assert codes[-1] == 429 and set(codes[:-1]) == {201}

    def test_lookup_needs_the_matching_phone(self, client, db):
        ok = client.get(
            f"/api/v1/bookings/public/{WS}/lookup",
            params={"reference": "tp-abc234", "phone": "0123456789"},
        )
        assert ok.status_code == 200 and ok.json()["can_cancel"] is True
        wrong = client.get(
            f"/api/v1/bookings/public/{WS}/lookup",
            params={"reference": "TP-ABC234", "phone": "0199999999"},
        )
        assert wrong.status_code == 404

    def test_customer_cancel(self, client, db):
        db["set_booking_status"].return_value = _stored_booking(status="cancelled")
        resp = client.post(
            f"/api/v1/bookings/public/{WS}/cancel",
            json={"reference": "TP-ABC234", "phone": "0123456789"},
        )
        assert resp.status_code == 200 and resp.json()["status"] == "cancelled"
        kwargs = db["set_booking_status"].call_args.kwargs
        assert kwargs["to_status"] == "cancelled" and kwargs["cancelled_by"] == "customer"

    def test_customer_cannot_cancel_with_the_wrong_phone(self, client, db):
        resp = client.post(
            f"/api/v1/bookings/public/{WS}/cancel",
            json={"reference": "TP-ABC234", "phone": "0199999999"},
        )
        assert resp.status_code == 404
        db["set_booking_status"].assert_not_called()

    def test_a_finished_booking_cannot_be_cancelled(self, client, db):
        db["get_booking_by_reference"].return_value = _stored_booking(status="completed")
        resp = client.post(
            f"/api/v1/bookings/public/{WS}/cancel",
            json={"reference": "TP-ABC234", "phone": "0123456789"},
        )
        assert resp.status_code == 409
