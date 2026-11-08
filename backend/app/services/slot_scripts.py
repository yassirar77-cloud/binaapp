"""The server fills the menu / map slots; page scripts must not refill them.

agp (regeneration after #836): the deterministic menu block was in the
HTML — every server-side check passed — but the model ALSO wrote a script
that rebuilt '#binaapp-menu-slot' on page load (``menuSlot.innerHTML =
...``) from its own list, with invented descriptions and no photos. In a
browser the photo menu was replaced by the model's cards.

``neutralize_slot_scripts`` points every reference to a server-owned slot
id inside a <script> at a hidden decoy element appended to the body: the
model's code still runs (no TypeError stops the mobile-menu toggle or the
footer year that share its script), but it writes into the decoy. Inline
JSON-LD is left alone. Idempotent.
"""

from __future__ import annotations

import re
from typing import Iterable, Tuple

SERVER_SLOTS = ("binaapp-menu-slot", "binaapp-maps-slot")
DECOY_SUFFIX = "-script-decoy"

_SCRIPT_RE = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.IGNORECASE | re.DOTALL)


def scripts_touching_slots(html: str, slots: Iterable[str] = SERVER_SLOTS) -> int:
    """How many executable <script> blocks reference a server-owned slot."""
    n = 0
    for m in _SCRIPT_RE.finditer(html or ""):
        if "ld+json" in m.group(1).lower():
            continue
        if any(re.search(rf"(['\"#]){re.escape(s)}(['\"\]\s)])", m.group(2)) for s in slots):
            n += 1
    return n


def neutralize_slot_scripts(html: str, slots: Iterable[str] = SERVER_SLOTS) -> Tuple[str, int]:
    """(html, scripts changed)."""
    slots = tuple(slots)
    if not html:
        return html, 0
    changed = 0
    used = set()

    def _sub(m: "re.Match") -> str:
        nonlocal changed
        if "ld+json" in m.group(1).lower():
            return m.group(0)
        body = m.group(2)
        new = body
        for s in slots:
            new, k = re.subn(rf"(['\"#]){re.escape(s)}(?=['\"\]\s)])", rf"\g<1>{s}{DECOY_SUFFIX}", new)
            if k:
                used.add(s)
        if new == body:
            return m.group(0)
        changed += 1
        return m.group(1) + new + m.group(3)

    out = _SCRIPT_RE.sub(_sub, html)
    if used:
        decoys = "".join(
            f'<div id="{s}{DECOY_SUFFIX}" hidden aria-hidden="true" style="display:none"></div>'
            for s in sorted(used) if f'id="{s}{DECOY_SUFFIX}"' not in out
        )
        m = re.search(r"</body>", out, re.IGNORECASE)
        out = (out[: m.start()] + decoys + out[m.start():]) if m else out + decoys
    return out, changed
