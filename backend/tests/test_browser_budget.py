"""The memory guard in front of every Chromium launch, and the build-time
self-test's reading of a failed launch.

Chromium plus Playwright's driver peaks at ~340-410 MB; the Render backend
has 512 MB in total. A launch without room would get the instance
restarted mid-generation, so the gate checks the container first.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from app.services import browser_budget as bb
from app.services import visual_gate as vg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gate_selftest import missing_libraries  # noqa: E402

MB = 1 << 20


def _cg2(tmp_path, limit, current, inactive=0):
    (tmp_path / "memory.max").write_text(str(limit))
    (tmp_path / "memory.current").write_text(str(current))
    (tmp_path / "memory.stat").write_text(f"anon 1\ninactive_file {inactive}\nactive_file 5\n")
    return str(tmp_path)


def _cg1(tmp_path, limit, usage, inactive=0):
    d = tmp_path / "memory"
    d.mkdir()
    (d / "memory.limit_in_bytes").write_text(str(limit))
    (d / "memory.usage_in_bytes").write_text(str(usage))
    (d / "memory.stat").write_text(f"cache 9\ntotal_inactive_file {inactive}\n")
    return str(tmp_path)


def test_render_starter_instance_is_refused(tmp_path, monkeypatch):
    """512 MB limit, app at 190 MB: 322 MB free < 450 MB needed."""
    monkeypatch.delenv("BROWSER_MIN_FREE_MB", raising=False)
    root = _cg2(tmp_path, 512 * MB, 190 * MB)
    ok, why = bb.can_launch(root)
    assert not ok and why.startswith("insufficient memory") and "free=322MB" in why and "need=450MB" in why


def test_two_gigabyte_instance_is_allowed(tmp_path, monkeypatch):
    monkeypatch.delenv("BROWSER_MIN_FREE_MB", raising=False)
    ok, why = bb.can_launch(_cg2(tmp_path, 2048 * MB, 300 * MB))
    assert ok and "free=1748MB" in why


def test_page_cache_does_not_count_as_used(tmp_path):
    b = bb.read_budget(_cg2(tmp_path, 512 * MB, 500 * MB, inactive=300 * MB))
    assert b.used_bytes == 200 * MB and b.free_bytes == 312 * MB


def test_cgroup_v1(tmp_path):
    b = bb.read_budget(_cg1(tmp_path, 512 * MB, 250 * MB, inactive=50 * MB))
    assert b.source == "cgroup v1" and b.limit_bytes == 512 * MB and b.used_bytes == 200 * MB


def test_unlimited_and_unreadable_are_allowed(tmp_path):
    assert bb.can_launch(_cg2(tmp_path, "max", 900 * MB))[0]
    v1 = tmp_path / "v1"
    v1.mkdir()
    assert bb.read_budget(_cg1(v1, 9223372036854771712, 100 * MB)).limit_bytes is None
    empty = tmp_path / "none"
    empty.mkdir()
    ok, why = bb.can_launch(str(empty))
    assert ok and "unreadable" in why


def test_threshold_is_tunable(tmp_path, monkeypatch):
    root = _cg2(tmp_path, 512 * MB, 190 * MB)
    monkeypatch.setenv("BROWSER_MIN_FREE_MB", "300")
    assert bb.can_launch(root)[0]
    monkeypatch.setenv("BROWSER_MIN_FREE_MB", "nonsense")
    assert not bb.can_launch(root)[0]  # falls back to 450


def test_boot_report_says_what_will_happen(tmp_path, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    assert "headless_shell=MISSING" in bb.boot_report() and "will be SKIPPED" in bb.boot_report()
    (tmp_path / "chromium_headless_shell-1248").mkdir()
    monkeypatch.setattr(bb, "can_launch", lambda root="/sys/fs/cgroup": (False, "insufficient memory for Chromium: x"))
    line = bb.boot_report()
    assert "present: chromium_headless_shell-1248" in line and "will be SKIPPED" in line
    monkeypatch.setattr(bb, "can_launch", lambda root="/sys/fs/cgroup": (True, "limit=2048MB"))
    assert "WILL RUN" in bb.boot_report()


# ---------------------------------------------------------------------------
# The gate honours the guard
# ---------------------------------------------------------------------------

def test_render_does_not_launch_without_memory(monkeypatch):
    monkeypatch.setattr(bb, "can_launch", lambda root="/sys/fs/cgroup": (False, "insufficient memory for Chromium: free=300MB need=450MB"))
    launched = []
    import playwright.async_api as pa
    monkeypatch.setattr(pa, "async_playwright", lambda: launched.append(1))
    m, d, mpng, dpng, err = asyncio.run(vg.render("<html></html>"))
    assert launched == [] and mpng is None and err.startswith("insufficient memory")


def test_gate_with_recovery_ships_the_page_and_logs_the_skip(monkeypatch):
    monkeypatch.setenv("VISUAL_GATE_MODE", "enforce")
    monkeypatch.setattr(bb, "can_launch", lambda root="/sys/fs/cgroup": (False, "insufficient memory for Chromium: free=300MB need=450MB"))
    html, rep = asyncio.run(vg.gate_with_recovery("<html>page</html>", expect_map=False, expect_whatsapp=False, job_id="job12345"))
    assert html == "<html>page</html>" and not rep.rendered and rep.error.startswith("insufficient memory")


def test_launch_args_are_low_memory_and_extendable(monkeypatch):
    args = vg.launch_args()
    for flag in ("--no-sandbox", "--disable-dev-shm-usage", "--renderer-process-limit=1", "--no-zygote"):
        assert flag in args
    monkeypatch.setenv("VISUAL_GATE_CHROMIUM_ARGS", "--foo --bar=1")
    assert vg.launch_args()[-2:] == ["--foo", "--bar=1"]


@pytest.mark.parametrize("error,libs", [
    ("chrome-headless-shell: error while loading shared libraries: libnss3.so: cannot open shared object file", ["libnss3.so"]),
    ("BrowserType.launch: Host system is missing dependencies to run browsers. Missing libraries:\n"
     "    libatk-1.0.so.0\n    libatk-bridge-2.0.so.0\n    libgbm.so.1\n\n╔═══", ["libatk-1.0.so.0", "libatk-bridge-2.0.so.0", "libgbm.so.1"]),
    ("Executable doesn't exist at /x/chrome-headless-shell", []),
    ("", []),
])
def test_selftest_names_missing_libraries(error, libs):
    assert missing_libraries(error) == libs
