"""The golden suite, offline, as a pytest: every fixture merchant composes,
passes the structural checks and the visual gate's measured checks.
Browser tests skip where no Chromium is installed; the structural checks
always run. The CI workflow runs the same thing through scripts/golden_run.py
and keeps the screenshots."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from golden_run import build_site, list_fixtures, structural_checks  # noqa: E402

HAS_BROWSER = bool(os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")) or bool(__import__("app.services.browser_budget", fromlist=["x"]).headless_shell_dirs())
FIXTURES = list_fixtures()


@pytest.fixture(autouse=True)
def _composed_mode(monkeypatch):
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "deterministic")
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "false")
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")


def test_five_fixtures_present():
    assert sorted(f["name"] for f in FIXTURES) == ["agp", "kedai_telefon", "kek", "mamak", "salon"]


@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["name"] for f in FIXTURES])
def test_golden_site_builds_and_passes_structural_checks(fixture):
    html, info = asyncio.run(build_site(fixture, mode="offline"))
    assert info["composed"] and info["validation_ok"], info["validation_errors"]
    report = structural_checks(html, fixture)
    assert report["ok"], {k: v for k, v in report["checks"].items() if not v} | {"missing": report["missing_items"], "prices": report["missing_prices"]}
    expect = fixture.get("expect", {})
    if expect.get("language"):
        assert f'<html lang="{expect["language"]}"' in html


@pytest.mark.skipif(not HAS_BROWSER, reason="no headless browser")
@pytest.mark.parametrize("fixture", FIXTURES, ids=[f["name"] for f in FIXTURES])
def test_golden_site_passes_visual_gate(fixture):
    from app.services.visual_gate import run_gate
    html, _ = asyncio.run(build_site(fixture, mode="offline"))
    req = fixture["request"]
    rep = asyncio.run(run_gate(
        html, expect_map=bool(req.get("include_maps", True) and req.get("location_address")),
        expect_whatsapp=bool(req.get("whatsapp_number")), language=req.get("language", "ms"),
    ))
    if not rep.rendered:
        pytest.skip(rep.error)
    assert rep.passed, rep.summary() + " :: " + "; ".join(c.detail for c in rep.failed)
