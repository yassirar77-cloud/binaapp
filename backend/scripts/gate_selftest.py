#!/usr/bin/env python3
"""Can the visual gate run on this machine? One gate run on the agp page.

    python scripts/gate_selftest.py            # report, always exits 0
    python scripts/gate_selftest.py --strict   # exit 1 when Chromium cannot run

Run by build.sh on every Render build: it proves (or disproves) that the
installed Chromium launches with the machine's system libraries, without
touching the live instance's memory. It composes the agp golden page from
its fixture (no model call, no network needed), injects the widgets the
job worker injects, runs the gate's measurements, and prints one line:

    GATE_SELFTEST chromium=launched gate=pass peak_mb=372 seconds=4.8 browsers=/opt/render/...
    GATE_SELFTEST chromium=FAILED missing_libs=libnss3.so,libatk-1.0.so.0 browsers=...

``peak_mb`` is the Playwright driver plus Chromium at their highest (PSS,
from /proc): compare it with the free memory the live instance has.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import List

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(HERE))

_LIB_RE = re.compile(r"error while loading shared libraries: ([^\s:]+)")
_MISSING_BLOCK_RE = re.compile(r"Host system is missing dependencies to run browsers\.(.*?)(?:\n\s*\n|╚|$)", re.S)
_LIB_NAME_RE = re.compile(r"\b(lib[\w.+-]+\.so(?:\.[\d.]+)?)\b")


def missing_libraries(error: str) -> List[str]:
    """System libraries a failed launch names, in order, without repeats."""
    text = str(error or "")
    found: List[str] = []
    for m in _LIB_RE.finditer(text):
        found.append(m.group(1))
    block = _MISSING_BLOCK_RE.search(text)
    if block:
        found += _LIB_NAME_RE.findall(block.group(1))
    out: List[str] = []
    for lib in found:
        if lib not in out:
            out.append(lib)
    return out


def _pss_kb(pid: int) -> int:
    try:
        for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
            if line.startswith("Pss:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _descendants(root: int) -> List[int]:
    children = {}
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            ppid = int(Path(d, "stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            continue
        children.setdefault(ppid, []).append(int(d.name))
    out, stack = [], [root]
    while stack:
        for c in children.get(stack.pop(), []):
            out.append(c)
            stack.append(c)
    return out


class PeakSampler:
    """Highest summed PSS of this process's descendants (driver + Chromium)."""

    def __init__(self) -> None:
        self.peak_kb = 0
        self._stop = False
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        me = os.getpid()
        while not self._stop:
            try:
                self.peak_kb = max(self.peak_kb, sum(_pss_kb(p) for p in _descendants(me)))
            except Exception:
                pass
            time.sleep(0.05)

    def __enter__(self) -> "PeakSampler":
        self._t.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop = True
        self._t.join(timeout=2)


def agp_page() -> str:
    """The composed agp page with the worker's widgets, built offline."""
    from golden_run import FIXTURES_DIR, load_fixture

    from app.models.schemas import WebsiteGenerationRequest
    from app.services import menu_fidelity as mf
    from app.services.sections import build_spec, compose_page, fallback_copy, theme_from_plan
    from app.services.templates import TemplateService

    fx = load_fixture(FIXTURES_DIR / "agp.json")
    req = WebsiteGenerationRequest(**fx["request"])
    spec = build_spec(req)
    html = compose_page(spec, theme_from_plan(None, design_style=req.design_style), fallback_copy(spec))
    html, _ = mf.fill_menu_slot(html, mf.render_menu_block(spec.items, language="ms", wa_digits=spec.wa_digits,
                                                           order_prefill="Assalamualaikum, saya nak order"))
    ts = TemplateService()
    html = ts.inject_google_maps(html, req.location_address, business_name=req.business_name, language="ms")
    html = ts.inject_whatsapp_button(html, req.whatsapp_number, language="ms", business_type="food")
    return html


def headless_shell_status() -> str:
    """Whether a headless-shell build (what the gate launches) is installed
    under PLAYWRIGHT_BROWSERS_PATH (or Playwright's default)."""
    from app.services.browser_budget import headless_shell_dirs
    dirs = headless_shell_dirs()
    return ("present: " + ", ".join(d.name for d in dirs)) if dirs else "MISSING"


async def run_once() -> dict:
    # The self-test machine is not the live instance: do not let the live
    # instance's memory guard skip the one launch we came to test.
    os.environ["BROWSER_MIN_FREE_MB"] = "0"
    from app.services.visual_gate import run_gate
    html = agp_page()
    t0 = time.time()
    with PeakSampler() as sampler:
        rep = await run_gate(html, expect_map=True, expect_whatsapp=True)
    return {
        "rendered": rep.rendered,
        "passed": rep.passed,
        "summary": rep.summary(),
        "error": rep.error,
        "failed": [c.name for c in rep.failed],
        "seconds": round(time.time() - t0, 1),
        "peak_mb": round(sampler.peak_kb / 1024),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="exit 1 when Chromium cannot run")
    ap.add_argument("--json", action="store_true", help="also print the full result as JSON")
    args = ap.parse_args()

    browsers = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "(unset: ~/.cache/ms-playwright)")
    print(f"GATE_SELFTEST browsers={browsers} headless_shell={headless_shell_status()}", flush=True)
    try:
        result = asyncio.run(run_once())
    except Exception as err:
        result = {"rendered": False, "passed": False, "summary": "crashed", "error": f"{type(err).__name__}: {err}",
                  "failed": [], "seconds": 0, "peak_mb": 0}
    if result["rendered"]:
        line = (f"GATE_SELFTEST chromium=launched gate={'pass' if result['passed'] else 'FAIL'} "
                f"peak_mb={result['peak_mb']} seconds={result['seconds']}"
                + (f" failed={','.join(result['failed'])}" if result["failed"] else ""))
    else:
        libs = missing_libraries(result.get("error") or "")
        line = ("GATE_SELFTEST chromium=FAILED "
                + (f"missing_libs={','.join(libs)} " if libs else "")
                + f"error={str(result.get('error') or '')[:400]!r}")
    print(line, flush=True)
    if args.json:
        print(json.dumps(result, indent=1), flush=True)
    if args.strict and not result["rendered"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
