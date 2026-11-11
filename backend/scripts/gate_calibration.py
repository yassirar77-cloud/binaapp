#!/usr/bin/env python3
"""Does the visual gate catch what it claims to catch?

A good page (the composed agp page with a hero photo, card photos and the
worker's widgets) gets ONE known design defect planted at a time; the gate
is run on each and must fail the check named for that defect. The clean
page must pass with no failing check at all.

    python scripts/gate_calibration.py            # table + exit 1 on a miss
    python scripts/gate_calibration.py --json     # machine-readable

This is the gate's own test: a check that never fires on its planted
defect is decoration, and a check that fires on the clean page is a false
alarm. Run by tests/test_gate_calibration.py (and so by CI) wherever a
headless browser is installed. Measured checks only: no vision model.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(HERE))


def _photo(colour, size=(800, 600), noise: bool = True) -> str:
    """A photo-like image as a data URI (a soft gradient with speckle, so
    it is not a flat colour block)."""
    from PIL import Image
    im = Image.new("RGB", size, colour)
    if noise:
        px = im.load()
        w, h = size
        for y in range(0, h, 4):
            for x in range(0, w, 4):
                d = ((x * 7 + y * 13) % 23) - 11
                r, g, b = colour
                c = (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)))
                for yy in range(y, min(y + 4, h)):
                    for xx in range(x, min(x + 4, w)):
                        px[xx, yy] = c
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=70)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def base_page() -> str:
    """The composed agp page with a dark hero photo and three card photos."""
    from gate_selftest import agp_page
    html = agp_page()
    hero = _photo((70, 45, 25), (1600, 900))
    html = html.replace('class="bs-hero bs-hero-solid"', 'class="bs-hero"', 1)
    html = re.sub(
        r'(<section class="bs-hero"[^>]*>)',
        r'\1<div class="bs-hero-media"><img src="' + hero + '" alt="Ayam Gepuk Panglima" width="1600" height="900" '
        r'fetchpriority="high"></div><div class="bs-hero-scrim"></div>', html, count=1)
    # A photo hero's ghost button is white (the composer adds bs-on-dark).
    html = html.replace('class="bs-btn bs-btn-ghost"', 'class="bs-btn bs-btn-ghost bs-on-dark"', 1)
    cards = re.findall(r'<li class="bmf-card bmf-text-only[^"]*">', html)
    for card, colour in zip(cards[:3], ((150, 90, 40), (40, 120, 70), (60, 80, 150))):
        html = html.replace(card, card.replace(" bmf-text-only", "") + (
            f'<div class="bmf-media"><img src="{_photo(colour)}" alt="" loading="lazy" decoding="async">'
            '<span class="bmf-ai-label">Gambar hiasan</span></div>'), 1)
    return html


def _css(html: str, css: str) -> str:
    return html.replace("</head>", f"<style>{css}</style></head>", 1)


def _after_hero(html: str, block: str) -> str:
    return html.replace('<section class="bs-banners"', block + '<section class="bs-banners"', 1)


def _first_card_img(html: str, new_img: str) -> str:
    return re.sub(r'(<div class="bmf-media">)<img[^>]*>', r"\1" + new_img, html, count=1)


@dataclass
class Defect:
    name: str
    check: str  # the gate check that must fail
    plant: Callable[[str], str]
    what: str


def defects() -> List[Defect]:
    d: List[Defect] = []
    add = lambda *a: d.append(Defect(*a))  # noqa: E731

    # ---- what the gate has measured since stage 2 ----
    add("wide_block", "no_horizontal_overflow",
        lambda h: _after_hero(h, '<div style="width:640px;background:#eee">lebar</div>'),
        "a 640px block on a 390px phone")
    add("strip_over_hero_cta", "hero_cta_unobstructed",
        lambda h: _css(h, ".bs-hero .bs-wrap{position:relative}.x-strip{position:absolute;left:0;right:0;bottom:6.5rem;"
                          "height:9rem;background:#fff;color:#000;z-index:5}")
        .replace('<div class="bs-cta-row">', '<div class="x-strip">Level 1 Level 2 Level 3</div><div class="bs-cta-row">', 1),
        "a strip drawn over the hero buttons")
    add("clipped_text", "no_clipped_text",
        lambda h: _after_hero(h, '<p style="width:120px;white-space:nowrap;overflow:hidden;text-overflow:clip">'
                                 "Sambal digiling segar setiap pagi tanpa pengawet</p>"),
        "a line cut by its own box")
    add("faint_text", "contrast_aa",
        lambda h: _after_hero(h, '<p style="color:#c4c4c4;background:#fff;padding:1rem">Buka setiap hari dari pagi hingga malam.</p>'),
        "light grey text on white (1.7:1)")
    add("broken_image", "images_load",
        lambda h: _first_card_img(h, '<img src="http://127.0.0.1:9/tiada.jpg" alt="">'),
        "a card photo that does not load")
    add("cta_without_icon", "cta_icon_and_label",
        lambda h: re.sub(r'(<a[^>]*class="bs-btn bs-btn-wa"[^>]*>)<svg.*?</svg>', r"\1", h, count=1, flags=re.S),
        "the WhatsApp button without its icon")
    add("map_squashed", "map_visible",
        lambda h: _css(h, 'iframe[src*="google.com/maps"]{height:40px!important;min-height:0!important}'),
        "the map 40px tall")

    # ---- what the first audit found it did not measure ----
    add("hero_text_on_bright_photo", "hero_text_legible",
        lambda h: h.replace('<div class="bs-hero-scrim"></div>', "", 1).replace(
            re.search(r'<div class="bs-hero-media"><img src="([^"]+)"', h).group(1), _photo((245, 240, 225), (1600, 900)), 1),
        "white hero text on a pale photo with no scrim")
    add("tiny_text", "text_readable_size",
        lambda h: _after_hero(h, '<p style="font-size:9px;padding:1rem">Harga termasuk nasi, sambal dan ulam. Tambah RM2 untuk bungkus.</p>'),
        "a paragraph at 9px")
    add("small_tap_target", "tap_targets",
        lambda h: _css(h, ".bmf-order{padding:0 .3rem!important;font-size:.6rem!important;line-height:1.1!important}"),
        "order buttons about 13px tall")
    add("text_over_text", "no_overlapping_text",
        lambda h: _after_hero(h, '<div style="padding:1rem"><p style="margin:0">Free refill nasi dan sambal untuk makan di kedai.</p>'
                                 '<p style="margin:-1.2em 0 0 0">Take away caj tambahan dua ringgit sahaja.</p></div>'),
        "two lines printed on top of each other")
    add("squashed_photo", "images_not_distorted",
        lambda h: _css(h, ".binaapp-menu-block .bmf-card img{aspect-ratio:auto!important;height:70px!important;object-fit:fill!important}"),
        "card photos squashed to 70px, not cropped")
    add("same_photo_three_cards", "no_duplicate_photos",
        lambda h: (lambda src: re.sub(r'(<div class="bmf-media"><img src=")[^"]+', lambda m: m.group(1) + src, h, count=3))(
            re.search(r'<div class="bmf-media"><img src="([^"]+)"', h).group(1)),
        "one photo on three different dishes")
    add("empty_section", "no_empty_sections",
        lambda h: h.replace('<section class="bs-banners"', '<section class="bs-section" id="galeri"><div class="bs-wrap">'
                            '<h2 class="bs-h2">Galeri</h2></div></section><section class="bs-banners"', 1),
        "a section with a heading and nothing under it")
    add("junk_text", "no_junk_text",
        lambda h: _after_hero(h, '<p style="padding:1rem">Harga bermula RMundefined. Hubungi {{whatsapp_number}} hari ini.</p>'),
        "'RMundefined' and an unfilled {{placeholder}}")
    add("dead_anchor", "links_work",
        lambda h: h.replace('href="#menu"', 'href="#senarai-harga"'),
        "'Lihat menu' pointing at a section that does not exist")
    add("desktop_strip_over_cta", "hero_cta_unobstructed",
        lambda h: _css(h, "@media (min-width:1024px){.bs-hero .bs-wrap{position:relative}.x-strip{position:absolute;left:0;"
                          "right:0;bottom:2rem;height:9rem;background:#fff;color:#000;z-index:5}}"
                          "@media (max-width:1023px){.x-strip{display:none}}")
        .replace('<div class="bs-cta-row">', '<div class="x-strip">Level 1 Level 2 Level 3</div><div class="bs-cta-row">', 1),
        "the hero buttons covered on desktop only")
    add("desktop_faint_text", "contrast_aa",
        lambda h: _css(h, "@media (min-width:1024px){.x-faint{color:#c9c9c9!important}}")
        .replace('<section class="bs-banners"', '<p class="x-faint" style="color:#222;background:#fff;padding:1rem">'
                 'Buka setiap hari dari pagi hingga malam.</p><section class="bs-banners"', 1),
        "text that is faint on desktop only")
    add("blank_band", "no_blank_bands",
        lambda h: _after_hero(h, '<div style="height:1100px"></div>'),
        "1100px of nothing in the middle of the page")
    add("blurry_photo", "images_sharp",
        lambda h: _first_card_img(h, f'<img src="{_photo((150, 90, 40), (48, 36), noise=False)}" alt="">'),
        "a 48px image stretched across a card")
    add("two_h1", "heading_structure",
        lambda h: _after_hero(h, '<h1 style="padding:1rem">Selamat Datang</h1>'),
        "a second H1")
    add("cta_below_fold", "primary_action_above_fold",
        lambda h: _css(h, ".bs-hero .bs-wrap{padding-top:1100px!important}"),
        "headline and buttons pushed below the first screen")
    return d


#: Planted defects the gate must also REPAIR: after auto_fix the named
#: check passes again. The rest are reported (soft) or have no safe fix
#: (junk text, a broken photo is dropped rather than repaired).
REPAIRED = {
    "wide_block", "strip_over_hero_cta", "clipped_text", "faint_text", "broken_image", "cta_without_icon",
    "hero_text_on_bright_photo", "tiny_text", "small_tap_target", "text_over_text", "squashed_photo",
    "same_photo_three_cards", "empty_section",
}


async def calibrate() -> Dict:
    os.environ["BROWSER_MIN_FREE_MB"] = "0"
    os.environ.setdefault("VISUAL_GATE_MODE", "enforce")
    # No network here: do not wait six seconds for a map that cannot load.
    os.environ.setdefault("VISUAL_GATE_NETWORK_IDLE_MS", "700")
    from app.services.visual_gate import auto_fix, run_gate
    base = base_page()
    kw = dict(expect_map=True, expect_whatsapp=True)
    clean = await run_gate(base, **kw)
    if not clean.rendered:
        return {"rendered": False, "error": clean.error}
    # The map iframe cannot load without network; map_visible is exempt on
    # the clean page only when that is the reason.
    clean_failing = [c.name for c in clean.checks if not c.ok]
    rows = []
    for defect in defects():
        rep = await run_gate(defect.plant(base), **kw)
        failing = [c.name for c in rep.checks if not c.ok]
        row = {"defect": defect.name, "expects": defect.check, "caught": defect.check in failing, "what": defect.what,
               "hard": next((c.hard for c in rep.checks if c.name == defect.check), None),
               "also": [f for f in failing if f != defect.check and f not in clean_failing], "repaired": None, "fixes": []}
        if row["caught"] and defect.name in REPAIRED:
            fixed, fixes = auto_fix(defect.plant(base), rep)
            rep2 = await run_gate(fixed, **kw)
            row["fixes"] = fixes
            row["repaired"] = bool(fixes) and defect.check not in [c.name for c in rep2.checks if not c.ok]
            before = {c.name: c.count for c in rep.checks if not c.ok}
            row["broke"] = [c.name for c in rep2.checks if not c.ok and c.name not in clean_failing
                            and (c.name not in failing or c.count > before.get(c.name, 0))]
        rows.append(row)
    return {"rendered": True, "clean_failing": clean_failing, "rows": rows,
            "caught": sum(1 for r in rows if r["caught"]), "total": len(rows),
            "repaired": sum(1 for r in rows if r["repaired"]), "repairable": len(REPAIRED),
            "fix_broke_something": [r["defect"] for r in rows if r.get("broke")]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = asyncio.run(calibrate())
    if args.json:
        print(json.dumps(res, indent=1, ensure_ascii=False))
    elif not res.get("rendered"):
        print(f"GATE_CALIBRATION could not render: {res.get('error')}")
    else:
        print(f"clean page failing checks: {res['clean_failing'] or 'none'}")
        for r in res["rows"]:
            fix = {True: "repaired", False: "NOT REPAIRED", None: "reported" if r["hard"] is False else "no auto-fix"}[r["repaired"]]
            print(f"  {'CAUGHT' if r['caught'] else 'MISSED':7} {r['defect']:28} -> {r['expects']:28} "
                  f"{'hard' if r['hard'] else 'soft':5} {fix:13} {r['what']}"
                  + (f"  (also: {', '.join(r['also'])})" if r["also"] else "")
                  + (f"  (FIX BROKE: {', '.join(r['broke'])})" if r.get("broke") else ""))
        print(f"GATE_CALIBRATION caught={res['caught']}/{res['total']} repaired={res['repaired']}/{res['repairable']} "
              f"clean_failing={len(res['clean_failing'])} fix_broke={len(res['fix_broke_something'])}")
    if not res.get("rendered"):
        return 0
    ok = (res["caught"] == res["total"] and not res["clean_failing"] and res["repaired"] == res["repairable"]
          and not res["fix_broke_something"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
