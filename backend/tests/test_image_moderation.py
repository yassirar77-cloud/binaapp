"""Image moderation (Qwen-VL): the default model exists, and a check that
cannot run does not let the image through. No network."""

from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import moderation as ep
from app.services import image_moderation_service as svc


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


def fake_client(response=None, exc=None):
    calls = []

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def post(self, url, headers=None, json=None):
            calls.append({"url": url, "headers": headers, "json": json})
            if exc:
                raise exc
            return response

    return _Client, calls


def verdict_body(text):
    return {"output": {"choices": [{"message": {"content": [{"text": text}]}}]}}


SAFE = '{"is_safe": true, "reason": "food photo", "confidence": 95, "detected_categories": []}'
UNSAFE = '{"is_safe": false, "reason": "x", "confidence": 90, "detected_categories": ["adult"]}'


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setattr(svc, "QWEN_API_KEY", "test-key")


def test_default_model_is_one_dashscope_still_serves(monkeypatch):
    # qwen-vl-plus answers "Model not exist"; with the old fail-open handling
    # that silently approved every image.
    assert svc.QWEN_VL_MODEL == "qwen3-vl-plus"


async def test_safe_image_is_allowed_and_sent_to_the_configured_model():
    client, calls = fake_client(FakeResponse(200, verdict_body(SAFE)))
    with patch.object(svc.httpx, "AsyncClient", client):
        result = await svc.moderate_uploaded_image(b"img", "a.jpg")
    assert result == {"allowed": True, "message": "Gambar diluluskan"}
    assert calls[0]["json"]["model"] == svc.QWEN_VL_MODEL


async def test_unsafe_image_is_rejected_with_a_reason():
    client, _ = fake_client(FakeResponse(200, verdict_body(UNSAFE)))
    with patch.object(svc.httpx, "AsyncClient", client):
        result = await svc.moderate_uploaded_image(b"img", "a.jpg")
    assert result["allowed"] is False and not result.get("unavailable")
    assert "dewasa" in result["message"]


@pytest.mark.parametrize(
    "response, exc",
    [
        (FakeResponse(404, text='{"code":"InvalidParameter","message":"Model not exist."}'), None),
        (FakeResponse(500), None),
        (FakeResponse(401), None),
        (None, httpx.ReadTimeout("slow")),
        (None, httpx.ConnectError("down")),
    ],
)
async def test_a_check_that_cannot_run_fails_closed(response, exc):
    client, _ = fake_client(response, exc)
    with patch.object(svc.httpx, "AsyncClient", client):
        verdict = await svc.check_image_safety(image_data=b"img")
        upload = await svc.moderate_uploaded_image(b"img", "a.jpg")
    assert verdict["is_safe"] is False and verdict["unavailable"] is True
    assert upload == {"allowed": False, "unavailable": True, "message": svc.UNAVAILABLE_MESSAGE}


async def test_no_key_still_skips_moderation(monkeypatch):
    # Not configured at all (local development) is not an API error.
    monkeypatch.setattr(svc, "QWEN_API_KEY", None)
    assert (await svc.check_image_safety(image_data=b"img"))["is_safe"] is True


def _app():
    app = FastAPI()
    app.include_router(ep.router, prefix="/api/v1")
    return TestClient(app)


def test_check_image_endpoint_returns_503_when_moderation_is_down():
    client, _ = fake_client(FakeResponse(404))
    with patch.object(svc.httpx, "AsyncClient", client):
        response = _app().post(
            "/api/v1/moderation/check-image", files={"file": ("a.jpg", b"img", "image/jpeg")}
        )
    assert response.status_code == 503
    assert response.json()["detail"] == svc.UNAVAILABLE_MESSAGE


def test_check_url_endpoint_returns_503_when_moderation_is_down():
    client, _ = fake_client(FakeResponse(500))
    with patch.object(svc.httpx, "AsyncClient", client):
        response = _app().post("/api/v1/moderation/check-url", params={"image_url": "https://x/a.jpg"})
    assert response.status_code == 503


def test_check_image_endpoint_still_allows_a_safe_image():
    client, _ = fake_client(FakeResponse(200, verdict_body(SAFE)))
    with patch.object(svc.httpx, "AsyncClient", client):
        response = _app().post(
            "/api/v1/moderation/check-image", files={"file": ("a.jpg", b"img", "image/jpeg")}
        )
    assert response.status_code == 200 and response.json()["allowed"] is True
