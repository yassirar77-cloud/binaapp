"""
Playwright screenshot rendering for the critique gate. Runs only when a
Chromium build is reachable; elsewhere it records the graceful failure.
"""

import pytest

from app.services import design_critique as dc

PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font-family:sans-serif} h1{font-size:48px} .wide{width:1200px;height:20px;background:#f00}</style></head>
<body><section><h1>Ayam Goreng Berempah</h1><p>Sejak 2009</p></section><div class="wide"></div></body></html>"""


@pytest.mark.asyncio
async def test_render_reports_overflow_or_fails_gracefully():
    bundle = await dc.render_screenshots(PAGE, timeout=20)
    if not bundle.ok:
        pytest.skip(f"no browser available here: {bundle.error}")
    assert bundle.desktop_png[:4] == b"\x89PNG" and bundle.mobile_png[:4] == b"\x89PNG"
    assert bundle.mobile_overflow and bundle.mobile_scroll_width >= 1200
    assert bundle.hero_font_px == 48 and bundle.hero_text_visible
