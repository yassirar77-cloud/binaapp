"""POST /api/image/role — the create page's poster / menu-board check for
the hero upload (quality system, stage 4)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services import image_roles


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def _shape(w, h, text=False):
    async def _probe(url):
        return image_roles.ImageShape(url=url, width=w, height=h, text_heavy=text)
    return _probe


def test_portrait_upload_is_a_poster(client, monkeypatch):
    monkeypatch.setattr(image_roles, "probe_shape", _shape(800, 1400))
    r = client.post("/api/image/role", json={"image_url": "https://res.cloudinary.com/x/image/upload/board.jpg"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] and body["poster"] and body["portrait"] and body["width"] == 800


def test_landscape_upload_is_not_a_poster_without_a_vision_model(client, monkeypatch):
    monkeypatch.setattr(image_roles, "probe_shape", _shape(1600, 900))
    from app.services.ai_service import ai_service
    monkeypatch.setattr(ai_service, "qwen_api_key", "")
    monkeypatch.setattr(ai_service, "zai_api_key", "")
    r = client.post("/api/image/role", json={"image_url": "https://example.com/hero.jpg"})
    body = r.json()
    assert body["success"] and not body["poster"] and not body["text_checked"]


def test_text_heavy_landscape_is_a_poster(client, monkeypatch):
    monkeypatch.setattr(image_roles, "probe_shape", _shape(1600, 900))
    from app.services import image_vision_check
    from app.services.ai_service import ai_service
    monkeypatch.setattr(ai_service, "qwen_api_key", "k")

    class _V:
        has_text = True
        checked = True

    async def _check(url, label, *, call_model):
        return _V()
    monkeypatch.setattr(image_vision_check, "check_image", _check)
    r = client.post("/api/image/role", json={"image_url": "https://example.com/menu-board.jpg"})
    body = r.json()
    assert body["poster"] and body["text_heavy"] and body["text_checked"]


def test_rejects_non_http(client):
    r = client.post("/api/image/role", json={"image_url": "data:image/png;base64,AAAA"})
    assert r.status_code == 400
