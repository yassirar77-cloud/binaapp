"""Bug 5: overlay hardcoded dark/0.45 — unreadable over a bright clip."""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.services.hero_luminance import (
    FALLBACK_OPACITY, auto_overlay_opacity, luminance_of_image_bytes, opacity_for_luminance,
)


def _png(grey: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 18), (grey, grey, grey)).save(buf, format="PNG")
    return buf.getvalue()


class TestMapping:
    def test_dark_clip_keeps_a_light_scrim(self):
        assert opacity_for_luminance(0.05) == 0.35
        assert opacity_for_luminance(0.20) == 0.35

    def test_bright_clip_gets_a_heavy_scrim(self):
        assert opacity_for_luminance(0.75) == 0.70
        assert opacity_for_luminance(0.95) == 0.70

    def test_monotonic_in_between(self):
        vals = [opacity_for_luminance(x / 100) for x in range(20, 76, 5)]
        assert vals == sorted(vals)
        assert 0.35 <= min(vals) and max(vals) <= 0.70

    def test_unknown_luminance_uses_the_old_default(self):
        assert opacity_for_luminance(None) == FALLBACK_OPACITY == 0.45


class TestMeasurement:
    def test_black_and_white_frames(self):
        assert luminance_of_image_bytes(_png(0)) == pytest.approx(0.0)
        assert luminance_of_image_bytes(_png(255)) == pytest.approx(1.0)

    def test_unreadable_bytes_are_none(self):
        assert luminance_of_image_bytes(b"not an image") is None


class TestAuto:
    @pytest.mark.asyncio
    async def test_bright_poster_yields_heavy_overlay(self):
        resp = MagicMock(status_code=200, content=_png(240))
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value=resp)
        with patch("app.services.hero_luminance.httpx.AsyncClient", return_value=client):
            assert await auto_overlay_opacity("https://res.cloudinary.com/x/poster.jpg") == 0.70

    @pytest.mark.asyncio
    async def test_fetch_failure_falls_back_never_raises(self):
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("app.services.hero_luminance.httpx.AsyncClient", return_value=client):
            assert await auto_overlay_opacity("https://x/p.jpg") == FALLBACK_OPACITY

    @pytest.mark.asyncio
    async def test_no_poster_falls_back(self):
        assert await auto_overlay_opacity(None) == FALLBACK_OPACITY
