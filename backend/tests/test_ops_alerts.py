"""Operator alerts: a build blocked by the visual gate or refused with the
location question reaches the owner on Telegram; a weekly summary counts
builds, gate results and dropped photos."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
from fastapi.testclient import TestClient

from app.services import ops_alerts as oa
from tests.conftest import generation_auth


def test_alert_text_names_merchant_website_and_reason():
    text = oa.format_alert("gate_failed", business_name="Ayam Gepuk Panglima", email="a@b.my", user_id="u-1",
                           website_id="w-1", job_id="j-1", reason="FAIL vision_review(1) — overlap at hero",
                           details={"Fixes tried": "dropped_mismatched_photos(1)", "Screenshot": ""})
    assert text.splitlines()[0] == "BinaApp 🚨 Build blocked by the visual gate"
    assert "Merchant: Ayam Gepuk Panglima (a@b.my, u-1)" in text and "Website: w-1  Job: j-1" in text
    assert "Reason: FAIL vision_review(1) — overlap at hero" in text and "Fixes tried: dropped" in text and "Screenshot" not in text
    refused = oa.format_alert("location_conflict", business_name="Kek Mak Teh", reason="Cerita sebut Melaka ...")
    assert "Website: none yet" in refused and "location question" in refused


def test_send_telegram_needs_configuration(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_ALERT_CHAT_ID", raising=False)
    assert asyncio.run(oa.send_telegram("hi")) is False


def test_send_telegram_posts_plain_text(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_ALERT_CHAT_ID", "-1001")
    seen = []

    def handler(request):
        seen.append((str(request.url), json.loads(request.content)))
        return httpx.Response(200, json={"ok": True})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await oa.send_telegram("Merchant: *Kedai_Ali*", client=c)
    assert asyncio.run(run()) is True
    url, payload = seen[0]
    assert url == "https://api.telegram.org/bot123:abc/sendMessage"
    assert payload == {"chat_id": "-1001", "text": "Merchant: *Kedai_Ali*", "disable_web_page_preview": True}  # no parse_mode

    async def refused():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(400, text="bad chat"))) as c:
            return await oa.send_telegram("x", client=c)
    assert asyncio.run(refused()) is False


def test_alert_dedupes_and_skips_ignored_accounts(monkeypatch, _no_ops_alert_delivery):
    delivered = _no_ops_alert_delivery
    monkeypatch.setenv("OPS_ALERT_IGNORE_USERS", "tester@binaapp.my, 7feab79a-6937")

    async def run():
        r1 = oa.alert("gate_failed", business_name="A", email="m@x.my", user_id="u1", reason="FAIL x")
        r2 = oa.alert("gate_failed", business_name="A", email="m@x.my", user_id="u1", reason="FAIL x")
        r3 = oa.alert("gate_failed", business_name="A", email="m@x.my", user_id="u1", reason="FAIL other")
        r4 = oa.alert("gate_failed", business_name="T", email="Tester@binaapp.my", user_id="u9", reason="FAIL x")
        await asyncio.sleep(0)
        return r1, r2, r3, r4
    assert asyncio.run(run()) == (True, False, True, False)
    assert [d[0] for d in delivered] == ["gate_failed", "gate_failed"]
    row = delivered[0][2]
    assert row["kind"] == "gate_failed" and row["email"] == "m@x.my" and row["reason"] == "FAIL x"


def test_weekly_summary_counts():
    jobs = [
        {"status": "completed", "validation": {"visual_gate": {"rendered": True, "passed": True, "fixes": []}}},
        {"status": "completed", "validation": {"visual_gate": {"rendered": True, "passed": True,
                                                               "fixes": ["dropped_mismatched_photos(3)", "photo_free_hero"]}}},
        {"status": "failed", "validation": {"visual_gate": {"rendered": True, "passed": False,
                                                            "fixes": ["dropped_mismatched_photos(1)", "regenerated"]}}},
        {"status": "completed", "validation": {}},
        {"status": "processing", "validation": None},
    ]
    events = [{"kind": "location_conflict"}, {"kind": "location_conflict"}, {"kind": "gate_failed"}]
    since, until = datetime(2026, 11, 2, tzinfo=timezone.utc), datetime(2026, 11, 9, tzinfo=timezone.utc)
    s = oa.summarize(jobs, events, since=since, until=until)
    assert (s["builds"], s["completed"], s["failed"], s["processing"]) == (5, 3, 1, 1)
    assert (s["gate_passed"], s["gate_failed"], s["gate_not_run"]) == (2, 1, 2)
    assert (s["auto_fixed"], s["photos_dropped"], s["photo_free_hero"], s["regenerated"]) == (2, 4, 1, 1)
    assert (s["location_refusals"], s["gate_alerts"]) == (2, 1)
    text = oa.format_summary(s)
    assert "02 Nov – 09 Nov 2026" in text and "Builds: 5 — completed 3, failed 1, still running 1" in text
    assert "2 passed, 1 failed (67% pass), not run on 2" in text and "photos dropped 4" in text


def test_weekly_summary_leaves_out_ignored_accounts(monkeypatch):
    monkeypatch.setenv("OPS_ALERT_IGNORE_USERS", "test-user")
    monkeypatch.setattr(oa, "_fetch_week", lambda since: (
        [{"status": "completed", "user_id": "test-user", "validation": {}}, {"status": "completed", "user_id": "real", "validation": {}}],
        [{"kind": "location_conflict", "user_id": "test-user"}],
    ))
    monkeypatch.setattr(oa, "send_telegram", AsyncMock(return_value=True))
    text = asyncio.run(oa.send_weekly_summary(datetime(2026, 11, 9, tzinfo=timezone.utc)))
    assert "Builds: 1 —" in text and "location question): 0" in text
    oa.send_telegram.assert_awaited_once()


def test_location_refusal_sends_an_alert(monkeypatch):
    import app.main as main_module
    from unittest.mock import MagicMock
    monkeypatch.setattr(main_module.sub_service, "_is_admin", AsyncMock(return_value=True))
    monkeypatch.setattr(main_module.asyncio, "create_task", MagicMock())
    sent = []
    monkeypatch.setattr(oa, "alert", lambda kind, **kw: sent.append((kind, kw)) or True)
    body = {"description": "Dobi di Seksyen 18, Shah Alam.", "business_name": "Dobi Seksyen 18", "business_type": "services",
            "address": "jalan 18/2, seksyen 7, shah alam", "language": "ms", "features": {}, "subdomain": "dobi18"}
    r = TestClient(main_module.app, headers=generation_auth("merchant-1", "m@x.my")).post("/api/generate/start", json=body)
    assert r.status_code == 409
    kind, kw = sent[0]
    assert kind == "location_conflict" and kw["business_name"] == "Dobi Seksyen 18" and "Seksyen 18" in kw["reason"]
    assert kw["details"]["Subdomain"] == "dobi18"


def test_phone_shop_images_are_unbranded():
    from app.services import image_subjects as s
    sub = s.subject_for("general", "Mobile Hub Seremban: new and used phones, screen and battery repairs")
    assert sub.key == "phone_shop" and "unbranded" in sub.hero_clause and "no brand logos" in sub.hero_clause
    prompt = s.lock_prompt("item", sub, item="Screen Replacement (iPhone 11-13)")
    assert "iPhone" not in prompt and "Screen Replacement (smartphone)" in prompt and "no brand logos" in prompt
    assert s.scrub_brands("Used Samsung Galaxy S23") == "Used smartphone"
    assert s.scrub_brands("Kek Pandan Gula Melaka") == "Kek Pandan Gula Melaka"
    # A plumber is still a workshop, a laundry still a laundry.
    assert s.subject_for("services", "Paip bocor, plumbing repair").key == "workshop"
    assert s.subject_for("services", "Dobi layan diri").key == "laundry"


def test_event_row_keeps_uuid_columns_valid(_no_ops_alert_delivery):
    async def run():
        oa.alert("location_conflict", business_name="Anon", user_id="anonymous", reason="Cerita sebut Melaka")
        oa.alert("gate_failed", business_name="Real", user_id="7feab79a-6937-4c59-a883-3a2f7609b734",
                 website_id="b2737dfd-959a-4d6e-8b80-87b32217ce04", reason="FAIL")
        await asyncio.sleep(0)
    asyncio.run(run())
    anon, real = (d[2] for d in _no_ops_alert_delivery)
    assert anon["user_id"] is None and anon["details"]["user_id"] == "anonymous" and anon["website_id"] is None
    assert real["user_id"] == "7feab79a-6937-4c59-a883-3a2f7609b734" and real["website_id"].startswith("b2737dfd")
