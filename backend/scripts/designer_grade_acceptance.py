#!/usr/bin/env python
"""
Designer-grade generation — acceptance harness.

Offline (always): ten briefs across five categories are planned with the
library (no model), and the acceptance rules are asserted: no two
consecutive same-category sites share a direction, no cream+serif+gold
without justification, bright by default, dark only for the steakhouse
brief or a Gelap pick, the Doodle Kartun + Gelap + "guna warna pink" case,
non-F&B briefs carry no Menu, features OFF remove sections, and the
anti-template lint passes on the plan-mode fixtures.

Live (``--live``, needs the generation API keys): each brief runs through
``AIService.generate_website``, the anti-template lint, the critique gate
and a Playwright screenshot at 1280 and 390, written to
``docs/design/screenshots/<slug>-{desktop,mobile}.png`` with a JSON report.

Run from backend/:  python scripts/designer_grade_acceptance.py [--live]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import design_directions as dd  # noqa: E402
from app.services.anti_template_lint import lint_anti_template  # noqa: E402
from app.services.design_plan import (  # noqa: E402
    PlanBrief, candidates_for, fallback_plan, parse_plan, resolve_theme, uses_cream_serif_gold,
)

BRIEFS = [
    ("food", "Nasi Kandar Crystal", "Nasi kandar mamak buka 24 jam di Shah Alam. Ayam goreng berempah dan kari kepala ikan.", "light", None, None),
    ("food", "Warung Kak Ros", "Warung sarapan nasi lemak dan roti canai di Kajang, buka pagi sahaja.", "light", None, None),
    ("food", "Steak & Ember", "Steakhouse dan wine lounge di Bangsar, dry-aged ribeye, malam sahaja.", "dark", None, None),
    ("food", "Kopi Tepi Jalan", "Specialty coffee, pour over dan brunch di Petaling Jaya.", "light", None, None),
    ("bakery", "Kek Comel", "Kedai kek dan brownies di Bangi, tempahan hari jadi.", "light", "doodle", None),
    ("bakery", "Roti Pagi", "Bakeri roti segar setiap pagi, croissant dan kuih.", "light", None, None),
    ("salon", "Salon Ayu", "Salon rambut dan spa wanita di Bangi, rawatan muka dan kuku.", "light", None, None),
    ("salon", "Salon Dania", "Salon dan bridal makeup di Seremban.", "light", None, None),
    ("services", "Bengkel Aircond Hafiz", "Servis aircond dan paip, kawasan Klang dan Shah Alam, 24 jam.", "light", None, None),
    ("services", "Studio Lensa", "Studio fotografi perkahwinan dan produk di Ipoh.", "light", None, None),
]

CLEAN_FIXTURE = """<!DOCTYPE html><html lang="ms"><head><meta name="viewport" content="width=device-width"></head><body>
<section id="home"><h1>Ayam Goreng Berempah</h1><p>Sejak 2009 di Shah Alam.</p><a href="https://wa.me/60198765432">Pesan di WhatsApp</a><a href="#menu">Lihat menu</a></section>
<section id="menu"><h2>Menu</h2></section><section id="lokasi"><h2>Lokasi</h2><p>12, Jalan Tengku Ampuan</p></section><footer>&copy; <span id="binaapp-year"></span> X</footer></body></html>"""


DOBI_STORY = (
    "Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. "
    "Mesin basuh 10kg dan 20kg, pengering panas, bayar dengan syiling atau QR. Buka setiap hari."
)


def round2_offline(failures: list) -> None:
    """Round 2 acceptance on the Dobi Layan Diri brief, without models."""
    from app.middleware.subdomain import _inject_qr_block
    from app.services.data_consistency import (
        enforce_24h_copy, find_bad_prices, format_price, location_conflicts, normalize_address, normalize_hours,
    )
    from app.services.fact_guard import FactSources, guard_facts
    from app.services.image_subjects import has_fnb_wording, lock_prompt, subject_for
    from app.services.page_hierarchy import apply_hierarchy_repairs, restyle_logo_badge

    # A1: every Dobi image prompt is laundry-locked with the universal negative.
    subject = subject_for("services", "Dobi Layan Diri Seksyen 18", DOBI_STORY)
    prompts = [lock_prompt("hero", subject, context=DOBI_STORY)] + [
        lock_prompt("item", subject, item=n, context=DOBI_STORY) for n in ("Basuh 10kg", "Basuh 20kg", "Pengering", "Cuci selimut")
    ]
    if subject.key != "laundry" or any(has_fnb_wording(p) or "no people's faces" not in p for p in prompts):
        failures.append("Dobi image prompts are not laundry-locked")
    # B4: the Seksyen 18 / Seksyen 7 conflict blocks.
    conflicts = location_conflicts(DOBI_STORY, "l7/l, jalan 18/2, seksyen 7, shah alam")
    if not conflicts or conflicts[0].question_ms != "Cerita sebut Seksyen 18 tapi alamat Seksyen 7 — yang mana betul?":
        failures.append("location blocker did not fire on Seksyen 18 / Seksyen 7")
    # B5: 24h → Buka 24 jam, never tutup 23:59.
    hours = normalize_hours("00:00 - 23:59", DOBI_STORY, "ms")
    page, _ = enforce_24h_copy("<p>Buka sekarang · tutup 23:59</p>", "ms")
    if not hours.is_24h or hours.text != "Buka 24 jam" or "23:59" in page:
        failures.append("24-hour hours not rendered as Buka 24 jam")
    # B6: prices.
    if format_price("6") != "RM6.00" or format_price("RM25.oo") is not None or find_bad_prices("<p>RM25.oo</p>") != ["RM25.oo"]:
        failures.append("price formatter / lint wrong")
    # B7: address.
    if normalize_address("l7/l, jalan 18/2, seksyen 18, shah alam") != "L7/1, Jalan 18/2, Seksyen 18, Shah Alam":
        failures.append("address normalisation wrong")
    # B8: invented section stripped.
    sources = FactSources.from_texts([DOBI_STORY, "Basuh 10kg RM6.00", "Basuh 20kg RM12.00", "L7/1, Jalan 18/2, Seksyen 18"], is_24h=True)
    html = ('<html><body><section id="home"><h1>Dobi Layan Diri Seksyen 18</h1></section>'
            '<section id="lengang"><h2>Waktu Paling Lengang</h2><p>6 pagi - 9 pagi</p></section>'
            '<section id="servis"><h2>Servis</h2><p>Basuh 10kg RM6.00</p></section><footer></footer></body></html>')
    out, report = guard_facts(html, sources)
    if "Waktu Paling Lengang" in out or "RM6.00" not in out:
        failures.append("fact guard did not strip the invented section")
    # C9–C12 static + D13/D14.
    hier_in = ('<html><head></head><body><nav><a href="#servis">Lihat servis</a></nav>'
               '<section id="home"><h1 class="text-3xl">Dobi</h1><a href="#servis">Lihat servis</a><span class="text-6xl">Dari RM6.00</span></section>'
               '<section id="servis"><h2 class="text-base">Perkhidmatan</h2><a href="#servis">Lihat servis</a></section><footer><div><p>x</p></div></footer></body></html>')
    hier_out, hier = apply_hierarchy_repairs(hier_in)
    if "text-6xl" in hier_out.split("</h1>")[1].split("</section>")[0] or hier.ctas_removed != 1 or 'id="binaapp-hierarchy"' not in hier_out:
        failures.append("hierarchy repairs incomplete")
    qr = _inject_qr_block(hier_out, "bebe", "ms")
    if qr.index("BinaApp QR Block") > qr.index("</div></footer>"):
        failures.append("QR block not inside the footer container")
    badge_html = '<html><body><header><span class="bg-blue-600">D</span></header></body></html>'
    badge_out, n = restyle_logo_badge(badge_html, initial="Dobi", accent="#0B4F9C", display_font="Rubik")
    if n != 1 or "bg-blue-600" in badge_out:
        failures.append("logo badge not restyled")


def offline() -> int:
    failures = []
    round2_offline(failures)
    history = {}
    used = []
    for vertical, name, desc, mode, style, brief_text in BRIEFS:
        theme, source, note = resolve_theme(mode, brief_text)
        brief = PlanBrief(business_name=name, description=desc, vertical=vertical, theme=theme, theme_source=source,
                          theme_note=note, style=style, design_brief=brief_text, menu_item_count=3, has_hero_image=True,
                          address="Shah Alam")
        plan = fallback_plan(brief, history=history.get(vertical, []))
        prev = history.get(vertical, [])
        if prev and prev[0] == plan.direction:
            failures.append(f"{name}: repeated direction {plan.direction} for {vertical}")
        history[vertical] = [plan.direction] + prev
        d = dd.DIRECTION_BY_KEY.get(plan.direction)
        if uses_cream_serif_gold(plan.palette, plan.type["display"]) and not (d and d.cream_allowed):
            failures.append(f"{name}: cream+serif+gold without justification")
        if plan.theme == "dark" and name != "Steak & Ember":
            failures.append(f"{name}: dark direction without Gelap / dark brief")
        if vertical not in dd.FNB_VERTICALS and "menu" in plan.sections:
            failures.append(f"{name}: non-F&B plan carries a Menu section")
        used.append((vertical, name, plan.direction, plan.theme, plan.hero_treatment))
    # Merchant overrides: Doodle Kartun + Gelap + "guna warna pink".
    theme, source, note = resolve_theme("dark", "guna warna pink")
    b = PlanBrief(business_name="Kek Comel", description="Kedai kek", vertical="bakery", theme=theme, theme_source=source,
                  theme_note=note, style="doodle", design_brief="guna warna pink", freedom="designer", menu_item_count=2, has_hero_image=True)
    cands = candidates_for(b)
    raw = json.dumps({"direction": cands[0].key, "why": 'Honours "guna warna pink" with pink chalk accents.', "brief_quotes": ["guna warna pink"],
                      "palette": {"bg": "#1E2A26", "surface": "#27352F", "text": "#FBF7EE", "muted": "#C7C1B3", "accent": "#FF6FA5", "accent_2": "#FFD447"},
                      "type": {"display": "Baloo 2", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 700},
                      "hero_treatment": "pattern", "signature_element": "pink chalk doodles", "layout_notes": "tiles", "motion": "underline draws", "avoid": []})
    p = parse_plan(raw, b, cands)
    if not (p.theme == "dark" and "doodle" in dd.DIRECTION_BY_KEY[p.direction].styles and p.palette["accent"] == "#FF6FA5" and p.brief_quotes == ["guna warna pink"]):
        failures.append("override case: dark + doodle + pink + brief citation not honoured")
    # Features OFF.
    off = PlanBrief(business_name="X", description="Nasi kandar", vertical="food", whatsapp=False, contact_form=False, maps=False, gallery_count=2)
    sections = fallback_plan(off).sections
    if "contact" in sections or "gallery" in sections:
        failures.append(f"features OFF still produced sections: {sections}")
    # Lint on the clean fixture.
    _, report = lint_anti_template(CLEAN_FIXTURE)
    if not report.ok:
        failures.append(f"lint failed on clean fixture: {report.errors}")

    print("Planned briefs (offline, library plans):")
    for row in used:
        print(f"  {row[0]:9s} {row[1]:24s} → {row[2]:16s} {row[3]:6s} {row[4]}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  - " + f)
        return 1
    print("Round 2 (Dobi Layan Diri) offline checks: passed.")
    print("\nOffline acceptance: all checks passed.")
    return 0


async def live(out_dir: Path) -> int:
    from app.models.schemas import Language, MenuItemInput, WebsiteGenerationRequest
    from app.services import design_critique as dc
    from app.services.ai_service import ai_service

    out_dir.mkdir(parents=True, exist_ok=True)
    report = []
    for vertical, name, desc, mode, style, brief_text in BRIEFS:
        req = WebsiteGenerationRequest(
            description=desc, language=Language.MALAY, business_name=name, business_type=vertical,
            subdomain="acceptance", whatsapp_number="0198765432", include_maps=False, location_address="Shah Alam",
            color_mode=mode, design_style=style, design_brief=brief_text, design_freedom="designer",
            menu_items=[MenuItemInput(name="Item Satu", price="RM8"), MenuItemInput(name="Item Dua", price="RM12")],
            include_contact_form=False,
        )
        result = await ai_service.generate_website(req, image_choice="ai")
        html = result.html_content
        _, lint = lint_anti_template(html)
        bundle = await dc.render_screenshots(html)
        slug = name.lower().replace(" ", "-").replace("&", "and")
        if bundle.ok:
            (out_dir / f"{slug}-desktop.png").write_bytes(bundle.desktop_png)
            (out_dir / f"{slug}-mobile.png").write_bytes(bundle.mobile_png)
        row = {"name": name, "vertical": vertical, "plan": ai_service._last_design_plan, "gate": ai_service._last_plan_gate,
               "lint": lint.as_dict(), "mobile_overflow": bundle.mobile_overflow, "screenshots": bundle.ok}
        report.append(row)
        print(json.dumps({k: row[k] for k in ("name", "vertical", "mobile_overflow")}, ensure_ascii=False))
    (out_dir / "acceptance-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Live report written to {out_dir / 'acceptance-report.json'}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="run the full pipeline against the configured API keys")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "design" / "screenshots"))
    args = ap.parse_args()
    code = offline()
    if args.live and code == 0:
        code = asyncio.run(live(Path(args.out)))
    sys.exit(code)
