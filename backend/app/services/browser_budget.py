"""Can this process afford to start Chromium right now?

The visual gate (and the freeform design critique) launch headless
Chromium through Playwright. Measured on the composed agp page, the
Playwright driver plus Chromium peaks at roughly 340-410 MB (PSS), and
the Render backend has 512 MB in total, of which the app itself uses
160-255 MB. Starting a browser without room would push the instance
over its limit; Render then restarts it, killing every generation in
flight. So before any launch the caller asks ``can_launch()``, which
reads the container's memory limit and current use from its cgroup.

- ``BROWSER_MIN_FREE_MB`` (default 450): free memory required to launch.
- No cgroup limit (a dev machine, a CI runner): always allowed.
- cgroup unreadable: allowed, and said so (nothing to measure against).

"Used" excludes reclaimable page cache (``inactive_file``), the same
figure ``docker stats`` reports, so a warm file cache does not block.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

UNLIMITED = 1 << 60
DEFAULT_MIN_FREE_MB = 450


@dataclass
class Budget:
    limit_bytes: Optional[int]
    used_bytes: Optional[int]
    source: str

    @property
    def free_bytes(self) -> Optional[int]:
        if self.limit_bytes is None or self.used_bytes is None:
            return None
        return max(0, self.limit_bytes - self.used_bytes)

    def describe(self) -> str:
        mb = lambda b: f"{b / (1 << 20):.0f}MB"  # noqa: E731
        if self.limit_bytes is None:
            return f"no memory limit ({self.source})"
        used = mb(self.used_bytes) if self.used_bytes is not None else "?"
        free = mb(self.free_bytes) if self.free_bytes is not None else "?"
        return f"limit={mb(self.limit_bytes)} used={used} free={free} ({self.source})"


def min_free_bytes() -> int:
    try:
        mb = int(os.getenv("BROWSER_MIN_FREE_MB", str(DEFAULT_MIN_FREE_MB)))
    except (TypeError, ValueError):
        mb = DEFAULT_MIN_FREE_MB
    return max(0, mb) << 20


def _read_int(path: Path) -> Optional[int]:
    try:
        raw = path.read_text().strip()
    except OSError:
        return None
    if raw == "max":
        return UNLIMITED
    try:
        return int(raw)
    except ValueError:
        return None


def _stat(path: Path) -> Dict[str, int]:
    out: Dict[str, int] = {}
    try:
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                out[parts[0]] = int(parts[1])
    except OSError:
        pass
    return out


def read_budget(root: str = "/sys/fs/cgroup") -> Budget:
    """The container's memory limit and working-set use (cgroup v2, then v1)."""
    base = Path(root)
    # cgroup v2
    limit = _read_int(base / "memory.max")
    current = _read_int(base / "memory.current")
    if limit is not None and current is not None:
        inactive = _stat(base / "memory.stat").get("inactive_file", 0)
        if limit >= UNLIMITED:
            return Budget(None, current - inactive, "cgroup v2")
        return Budget(limit, max(0, current - inactive), "cgroup v2")
    # cgroup v1
    v1 = base / "memory"
    limit = _read_int(v1 / "memory.limit_in_bytes")
    usage = _read_int(v1 / "memory.usage_in_bytes")
    if limit is not None and usage is not None:
        inactive = _stat(v1 / "memory.stat").get("total_inactive_file", 0)
        if limit >= UNLIMITED or limit >= (1 << 50):
            return Budget(None, usage - inactive, "cgroup v1")
        return Budget(limit, max(0, usage - inactive), "cgroup v1")
    return Budget(None, None, "cgroup unreadable")


def can_launch(root: str = "/sys/fs/cgroup") -> Tuple[bool, str]:
    """(allowed, reason) for starting a browser now."""
    budget = read_budget(root)
    need = min_free_bytes()
    free = budget.free_bytes
    if free is None:
        return True, budget.describe()
    if free >= need:
        return True, f"{budget.describe()} need={need >> 20}MB"
    return False, f"insufficient memory for Chromium: {budget.describe()} need={need >> 20}MB"


def browsers_dir() -> Path:
    return Path(os.getenv("PLAYWRIGHT_BROWSERS_PATH", "") or Path.home() / ".cache" / "ms-playwright")


def headless_shell_dirs() -> List[Path]:
    """Installed headless-shell builds (what a headless launch uses)."""
    base = browsers_dir()
    try:
        return sorted(d for d in base.iterdir() if d.is_dir() and d.name.startswith("chromium_headless_shell-"))
    except OSError:
        return []


def boot_report() -> str:
    """One line for the startup log: is a browser installed here, and
    would the gate be allowed to launch it right now?"""
    shells = headless_shell_dirs()
    allowed, why = can_launch()
    return (
        f"browsers={browsers_dir()} headless_shell={'present: ' + shells[-1].name if shells else 'MISSING'} "
        f"memory: {why} -> gate {'WILL RUN' if (shells and allowed) else 'will be SKIPPED'}"
    )
