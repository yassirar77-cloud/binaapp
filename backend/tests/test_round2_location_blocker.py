"""Round 2 §B4: the Seksyen 18 / Seksyen 7 conflict blocks generation until
the merchant answers, and the losing token never reaches the page."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import app.main as main_module

DOBI_BODY = {
    "description": "Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. Mesin basuh 10kg dan 20kg.",
    "business_name": "Dobi Layan Diri Seksyen 18",
    "business_type": "services",
    "address": "l7/l, jalan 18/2, seksyen 7, shah alam",
    "language": "ms",
    "user_id": "anonymous",
    "features": {"whatsapp": True, "googleMap": True},
    "whatsapp_number": "0198765432",
}


@pytest.fixture
def client():
    return TestClient(main_module.app)


def test_listen_reports_the_conflict(client):
    data = client.post("/api/generate/listen", json=DOBI_BODY).json()
    assert data["location_conflicts"] == [{
        "kind": "seksyen", "story": "Seksyen 18", "address": "Seksyen 7",
        "question": "Cerita sebut Seksyen 18 tapi alamat Seksyen 7 — yang mana betul?",
        "question_en": "The story says Seksyen 18 but the address says Seksyen 7 — which is correct?",
    }]


def test_start_refuses_until_resolved(client, monkeypatch):
    monkeypatch.setattr(main_module.asyncio, "create_task", MagicMock())
    r = client.post("/api/generate/start", json=DOBI_BODY)
    assert r.status_code == 409
    assert r.json()["error"] == "location_conflict" and "Seksyen 18" in r.json()["message"]
    main_module.asyncio.create_task.assert_not_called()


def _capture_task(monkeypatch):
    """Replace the background task with a recorder; create_task just closes the coroutine."""
    recorder = AsyncMock()
    monkeypatch.setattr(main_module, "run_generation_task", recorder)
    monkeypatch.setattr(main_module.asyncio, "create_task", lambda coro: (coro.close(), MagicMock())[1])
    monkeypatch.setattr(main_module, "supabase", None)
    return recorder


def test_start_applies_the_resolution_and_scrubs_the_loser(client, monkeypatch):
    recorder = _capture_task(monkeypatch)
    r = client.post("/api/generate/start", json={**DOBI_BODY, "location_resolution": {"seksyen": "story"}})
    assert r.status_code == 200, r.text
    call = recorder.call_args
    assert call.kwargs["location_fixups"] == {"Seksyen 7": "Seksyen 18"}
    description, address = call.args[1], call.args[7]
    assert "seksyen 18" in address.lower() and "seksyen 7" not in address.lower()
    assert "Seksyen 18" in description


def test_resolution_the_other_way_rewrites_the_story(client, monkeypatch):
    recorder = _capture_task(monkeypatch)
    r = client.post("/api/generate/start", json={**DOBI_BODY, "location_resolution": {"seksyen": "address"}})
    assert r.status_code == 200, r.text
    call = recorder.call_args
    assert call.kwargs["location_fixups"] == {"Seksyen 18": "Seksyen 7"}
    description = call.args[1]
    assert "Seksyen 18" not in description and "Seksyen 7" in description
