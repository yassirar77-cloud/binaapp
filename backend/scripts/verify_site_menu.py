#!/usr/bin/env python3
"""Check a generated page against a menu fixture — the acceptance criteria
for the menu-fidelity work, runnable on any HTML file.

    python scripts/verify_site_menu.py page.html tests/fixtures/ayam_gepuk_panglima_menu.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

INVENTED_MARKERS = ("Ayam Goreng Coklat", "Ayam Goreng Keju")
PLACEHOLDER_MARKERS = ("[ISI", "contoh:", "11 pagi – 10 malam", "Nasi Kandar Daging Crystal", "berminat dengan perkhidmatan")


def _visible(html: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def _display_conflicts(html: str) -> list:
    """Elements the page hides on phones (custom class in a max-width media
    query) that a Tailwind display class shows again (agp: desktop nav on a
    phone, 632px-wide page)."""
    import sys as _sys
    from pathlib import Path as _P
    _sys.path.insert(0, str(_P(__file__).resolve().parents[1]))
    from app.services.display_conflicts import fix_hidden_display_conflicts
    fixed, n = fix_hidden_display_conflicts(html)
    return [n] if n else []


def verify_map(html: str) -> Dict[str, bool]:
    """The map renders: a Google Maps iframe, the Google Maps AND Waze
    buttons beside it in the same widget, and no fixed-height / clipping
    box around it (agp: an 'aspect-[16/9] overflow-hidden' slot hid both
    buttons)."""
    widget = re.search(r'<div class="binaapp-map-widget".*?</div>\s*</div>', html, flags=re.S)
    w = widget.group(0) if widget else ""
    actions = re.search(r'<div class="binaapp-map-actions".*?</div>', w, flags=re.S)
    a = actions.group(0) if actions else ""
    slot = re.search(r'<div\b[^>]*\bid="binaapp-maps-slot"[^>]*>', html)
    slot_classes = re.search(r'class="([^"]*)"', slot.group(0)).group(1).split() if slot and 'class="' in slot.group(0) else []
    clipped = any(c.startswith(("aspect-", "h-", "max-h-")) for c in slot_classes) and any(
        c.startswith("overflow-") and c != "overflow-visible" for c in slot_classes
    )
    return {
        "map_iframe": bool(re.search(r'<iframe\b[^>]*src="https://www\.google\.com/maps\?q=[^"]+"', w)),
        "map_google_maps_button": "google.com/maps/" in a and ("Buka di Google Maps" in a or "Open in Google Maps" in a),
        "map_waze_button": "waze.com/ul" in a,
        "map_not_clipped": bool(w) and not clipped,
    }


def verify(html: str, fixture: Dict[str, Any]) -> Dict[str, Any]:
    text = _visible(html)
    items = fixture["menu_items"]
    missing = [i["name"] for i in items if i["name"] not in text]
    wrong_price = [i["name"] for i in items if f"RM{i['price']}" not in text]
    invented = [m for m in INVENTED_MARKERS if m in text]
    placeholders = [m for m in PLACEHOLDER_MARKERS if m in text or m in html]
    categories = [c for c in dict.fromkeys(i.get("category", "") for i in items) if c]
    cat_missing = [c for c in categories if c not in text]
    empty_sections = len(re.findall(r"<section\b[^>]*>(?:\s|<!--.*?-->)*</section>", html, flags=re.S | re.I))
    orphan_dividers = len(re.findall(r'class="[^"]*divider[^"]*"[^>]*>\s*</div>\s*(?:<!--.*?-->\s*)*<div[^>]*class="[^"]*divider', html, flags=re.S | re.I))
    map_checks = verify_map(html)
    checks = {
        "all_items_present": not missing,
        "all_prices_present": not wrong_price,
        "no_invented_items": not invented,
        "categories_present": not cat_missing,
        "no_placeholder_text": not placeholders,
        "no_empty_sections": empty_sections == 0,
        "no_orphan_dividers": orphan_dividers == 0,
        "tel_link": 'href="tel:+60' in html,
        "waze_and_maps_buttons": "waze.com/ul" in html and ("Buka di Google Maps" in html or "Open in Google Maps" in html),
        **map_checks,
        "no_mobile_display_conflict": not _display_conflicts(html),
        "fnb_whatsapp_prefill": "saya%20nak%20order" in html or "saya nak order" in html,
        "theme_color_not_default": bool(re.search(r'name="theme-color" content="(?!#111827)', html)),
        "logo_or_initial_favicon": 'rel="icon"' in html,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "missing_items": missing,
        "missing_prices": wrong_price,
        "invented_found": invented,
        "placeholders_found": placeholders,
        "categories_missing": cat_missing,
    }


if __name__ == "__main__":
    html = Path(sys.argv[1]).read_text(encoding="utf-8")
    fixture = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    report = verify(html, fixture)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    sys.exit(0 if report["ok"] else 1)
