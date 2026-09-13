"""
Tailwind precompile (§8) — replace the Play CDN with compiled CSS at
publish time, when the tooling exists.

The generated pages load `cdn.tailwindcss.com`, which compiles classes in
the browser on every visit (slow, and flagged by Lighthouse). When node and
the Tailwind CLI are reachable (``npx tailwindcss``), this module compiles
the classes the page actually uses into one stylesheet so the quality
floor can inline it and drop the CDN script. Everything is optional and
bounded: no node, a timeout or a CLI error returns None and the page keeps
the CDN.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = float(os.getenv("TAILWIND_PRECOMPILE_TIMEOUT_SECONDS", "45"))
_CONFIG_RE = re.compile(r"tailwind\.config\s*=\s*(\{.*?\})\s*</script>", re.DOTALL)


def enabled() -> bool:
    return os.getenv("TAILWIND_PRECOMPILE", "false").strip().lower() in ("1", "true", "yes", "on")


def available() -> bool:
    return shutil.which("npx") is not None


def extract_config(html: str) -> str:
    """The page's inline tailwind.config object literal, or '{}'."""
    m = _CONFIG_RE.search(html or "")
    return m.group(1) if m else "{}"


async def compile_css(html: str, *, timeout: float = TIMEOUT_SECONDS) -> Optional[str]:
    """Compile the Tailwind classes used in ``html`` into CSS. None when
    unavailable or on any failure."""
    if not html or not available():
        return None
    tmp = Path(tempfile.mkdtemp(prefix="binaapp-tw-"))
    try:
        content = tmp / "page.html"
        content.write_text(html, encoding="utf-8")
        config = tmp / "tailwind.config.js"
        config.write_text(
            "module.exports = Object.assign(" + extract_config(html) + ", { content: [" + json.dumps(str(content)) + "] });\n",
            encoding="utf-8",
        )
        source = tmp / "in.css"
        source.write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n", encoding="utf-8")
        out = tmp / "out.css"
        proc = await asyncio.create_subprocess_exec(
            "npx", "--yes", "tailwindcss@3", "-c", str(config), "-i", str(source), "-o", str(out), "--minify",
            cwd=str(tmp), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("🎨 Tailwind precompile timed out")
            return None
        if proc.returncode != 0 or not out.exists():
            logger.warning(f"🎨 Tailwind precompile failed: {err.decode(errors='ignore')[:300]}")
            return None
        css = out.read_text(encoding="utf-8").strip()
        return css or None
    except Exception as exc:
        logger.warning(f"🎨 Tailwind precompile error: {exc}")
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
