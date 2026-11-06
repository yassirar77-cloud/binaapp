"""Item photos and about/gallery photos go through the same no-text check.

agp.binaapp.my shipped an about image with garbled baked-in text. On Render
the gate was on and keys were set, but qwen-vl-max answered 404 "Model not
exist" on every call and GLM-4.5V answered 200 with empty content (its
300-token budget spent thinking) — so every image "passed (unchecked)".
"""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import image_text_gate as gate
from app.services.ai_service import AIService
from app.services.image_vision_check import VisionVerdict

TEXTY = "https://res.cloudinary.com/demo/image/upload/v1/texty.png"
CLEAN = "https://res.cloudinary.com/demo/image/upload/v1/clean.png"
UPLOAD = "https://res.cloudinary.com/demo/image/upload/v1/signboard.jpg"


def _page(*imgs, menu_img=""):
    tags = "".join(f'<img src="{u}" alt="Set A – Ayam Gepuk">' for u in imgs)
    return (
        f'<html><body><section id="hero"><img src="{TEXTY}" alt="hero"></section>'
        f'<section id="about" class="py-16"><div><h2>Tentang</h2>{tags}</div></section>'
        f'<section id="menu"><img src="{menu_img or TEXTY}" alt="m"></section></body></html>'
    )


def _verdicts(**by_url):
    return {u: VisionVerdict(has_text=t, has_food=True, has_face=False, matches_category=True, reason="r") for u, t in by_url.items()}


class TestGate:
    @pytest.mark.asyncio
    async def test_texty_about_image_is_swapped_for_a_clean_one(self):
        checks = []

        async def check(url):
            checks.append(url)
            return VisionVerdict(has_text=(url == TEXTY), reason="garbled text")

        out, rep = await gate.gate_section_images(_page(TEXTY), check=check, clean_pool=[TEXTY, CLEAN], alt_fallback="AGP")
        about = out[out.index('id="about"'):out.index('id="menu"')]
        assert TEXTY not in about and f'src="{CLEAN}" alt="AGP"' in about
        assert rep.replaced == [(TEXTY, CLEAN)]
        # Hero and menu sections are not this pass's business.
        assert out.count(TEXTY) == 2

    @pytest.mark.asyncio
    async def test_cached_verdicts_are_reused_and_no_clean_image_means_removal(self):
        async def check(url):  # pragma: no cover - must not be called
            raise AssertionError("cached verdict should be used")

        out, rep = await gate.gate_section_images(
            _page(TEXTY + "?w=800"), check=check, verdicts=_verdicts(**{TEXTY: True}), clean_pool=[TEXTY],
        )
        assert rep.removed == [TEXTY + "?w=800"]
        about = out[out.index('id="about"'):out.index('id="menu"')]
        assert "<img" not in about and "<h2>Tentang</h2>" in about

    @pytest.mark.asyncio
    async def test_uploads_are_never_touched(self):
        async def check(url):  # pragma: no cover
            raise AssertionError("uploads are not checked")

        html = _page(UPLOAD)
        out, rep = await gate.gate_section_images(html, check=check, uploads=[UPLOAD])
        assert out == html and not rep.changed

    @pytest.mark.asyncio
    async def test_unchecked_verdict_leaves_the_image_and_is_reported(self):
        async def check(url):
            return VisionVerdict(checked=False)

        html = _page(TEXTY)
        out, rep = await gate.gate_section_images(html, check=check)
        assert out == html and rep.unchecked == [TEXTY]

    def test_gallery_and_galeri_sections_are_gated(self):
        html = '<section id="galeri"></section><section class="gallery-grid x"></section><section id="contact"></section>'
        assert len(gate.gated_section_spans(html)) == 2


class _FakeResp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, responses, sent):
        self._responses, self._sent = responses, sent

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        self._sent.append((url, json))
        return self._responses.pop(0)


def _svc():
    svc = AIService.__new__(AIService)
    svc.qwen_api_key, svc.qwen_base_url = "q", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    svc.zai_api_key, svc.zai_base_url = "z", "https://api.z.ai/api/paas/v4"
    AIService._missing_vision_models = set()
    return svc


VERDICT = '{"has_text": true, "has_food": true, "has_face": false, "matches_category": true, "reason": "garbled words"}'


class TestModelCall:
    @pytest.mark.asyncio
    async def test_missing_qwen_model_is_skipped_and_glm_runs_without_thinking(self, monkeypatch):
        sent = []
        responses = [
            _FakeResp(404, text='{"error":{"message":"Model not exist.","code":"model_not_found"}}'),
            _FakeResp(200, {"choices": [{"message": {"content": VERDICT}}]}),
            _FakeResp(200, {"choices": [{"message": {"content": VERDICT}}]}),
        ]
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _FakeClient(responses, sent))
        svc = _svc()
        assert await svc._call_image_check_model([{"role": "user", "content": "x"}]) == VERDICT
        glm_body = sent[1][1]
        assert glm_body["thinking"] == {"type": "disabled"} and glm_body["max_tokens"] >= 1024
        # Second image: the missing Qwen model is not called again.
        assert await svc._call_image_check_model([{"role": "user", "content": "x"}]) == VERDICT
        assert [u for u, _ in sent].count(sent[0][0]) == 1 and len(sent) == 3

    @pytest.mark.asyncio
    async def test_verdict_left_in_reasoning_content_is_used(self, monkeypatch):
        sent = []
        responses = [_FakeResp(200, {"choices": [{"finish_reason": "length", "message": {"content": "", "reasoning_content": "Looking... " + VERDICT}}]})]
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _FakeClient(responses, sent))
        svc = _svc()
        svc.qwen_api_key = None
        out = await svc._call_image_check_model([])
        from app.services.image_vision_check import parse_verdict
        assert parse_verdict(out).has_text is True

    @pytest.mark.asyncio
    async def test_thinking_rejection_retries_without_the_field(self, monkeypatch):
        sent = []
        responses = [
            _FakeResp(400, text='{"error":{"message":"thinking cannot be disabled"}}'),
            _FakeResp(200, {"choices": [{"message": {"content": VERDICT}}]}),
        ]
        monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _FakeClient(responses, sent))
        svc = _svc()
        svc.qwen_api_key = None
        assert await svc._call_image_check_model([]) == VERDICT
        assert "thinking" not in sent[1][1]


@pytest.mark.asyncio
async def test_pipeline_gate_uses_the_build_pool(monkeypatch):
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "true")
    svc = _svc()

    async def fake_model(messages):
        url = next(p["image_url"]["url"] for m in messages if isinstance(m.get("content"), list) for p in m["content"] if p.get("type") == "image_url")
        return VERDICT if url == TEXTY else VERDICT.replace('"has_text": true', '"has_text": false')

    svc._call_image_check_model = fake_model
    req = SimpleNamespace(uploaded_images=[], business_name="Ayam Gepuk Panglima")
    out = await svc._gate_about_gallery_images(_page(TEXTY), req, {"hero": CLEAN, "gallery1": TEXTY})
    about = out[out.index('id="about"'):out.index('id="menu"')]
    assert f'src="{CLEAN}"' in about and TEXTY not in about
