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
