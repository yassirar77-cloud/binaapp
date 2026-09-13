"""Tailwind precompile (§8): optional, bounded, and honest about absence."""

import shutil

import pytest

from app.services import tailwind_precompile as twp

PAGE = ('<html><head><script src="https://cdn.tailwindcss.com"></script>'
        '<script>tailwind.config = { theme: { extend: { colors: { primary: "#E8541E" } } } }</script></head>'
        '<body><div class="bg-primary p-4 text-white">x</div></body></html>')


def test_extract_config_and_flag(monkeypatch):
    assert twp.extract_config(PAGE).startswith("{ theme")
    assert twp.extract_config("<html></html>") == "{}"
    monkeypatch.delenv("TAILWIND_PRECOMPILE", raising=False)
    assert not twp.enabled()
    monkeypatch.setenv("TAILWIND_PRECOMPILE", "true")
    assert twp.enabled()


@pytest.mark.asyncio
async def test_compile_returns_none_without_npx(monkeypatch):
    monkeypatch.setattr(twp.shutil, "which", lambda name: None)
    assert await twp.compile_css(PAGE) is None


@pytest.mark.asyncio
async def test_compile_produces_css_when_cli_available():
    if not shutil.which("npx"):
        pytest.skip("npx not available")
    css = await twp.compile_css(PAGE, timeout=180)
    if css is None:
        pytest.skip("tailwindcss CLI not reachable (offline)")
    assert ".p-4{padding:1rem}" in css and "cdn.tailwindcss" not in css
    assert ("232 84 30" in css) or ("#e8541e" in css.lower())  # the page's own primary colour
