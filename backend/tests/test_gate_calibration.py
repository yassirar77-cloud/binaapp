"""The gate's own test, in a real browser: 22 known design defects are
planted one at a time on a good page (scripts/gate_calibration.py). Every
one must be caught by its named check, the 13 with a fix must be repaired
by auto_fix without breaking anything else, and the clean page must raise
nothing. Skipped where no headless browser is installed (the golden CI
workflow runs the script directly)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gate_calibration  # noqa: E402

HAS_BROWSER = bool(os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE")) or bool(__import__("app.services.browser_budget", fromlist=["x"]).headless_shell_dirs())


def test_every_check_has_a_planted_defect():
    from app.services.visual_gate import HARD_CHECKS, SOFT_CHECKS
    planted = {d.check for d in gate_calibration.defects()}
    # Vision checks and the two "is it there" checks have no planted page.
    exempt = {"vision_review", "floating_button_unobstructed", "photo_matches_name", "hero_matches_business",
              "images_drawn", "floating_whatsapp_present"}
    assert (set(HARD_CHECKS) | set(SOFT_CHECKS)) - exempt == planted
    assert gate_calibration.REPAIRED <= {d.name for d in gate_calibration.defects()}


@pytest.mark.skipif(not HAS_BROWSER, reason="no headless browser")
def test_planted_defects_are_caught_and_repaired(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")
    res = asyncio.run(gate_calibration.calibrate())
    if not res.get("rendered"):
        pytest.skip(res.get("error"))
    assert res["clean_failing"] == [], "a check fires on a good page"
    missed = [r["defect"] for r in res["rows"] if not r["caught"]]
    assert not missed, f"planted but not caught: {missed}"
    not_repaired = [r["defect"] for r in res["rows"] if r["repaired"] is False]
    assert not not_repaired, f"caught but auto_fix did not repair: {not_repaired}"
    assert res["fix_broke_something"] == []
    assert (res["caught"], res["repaired"]) == (22, 13)
