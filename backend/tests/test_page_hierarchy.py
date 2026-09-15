"""Round 2 §C9–§C12 with the Dobi page: the H1 becomes the largest text
(the "Dari RM6" side card is capped), section headings become real H2s,
hero text gets a panel when the photo behind it is too bright, the inset
duplicate hero photo goes, and a third "Lihat servis" repeat is removed."""

import io

import pytest

from app.services import page_hierarchy as ph

DOBI = """<!DOCTYPE html><html lang="ms"><head><title>Dobi</title></head><body>
<nav><a href="#servis">Lihat servis</a><a href="https://wa.me/60198765432">WhatsApp</a></nav>
<section id="home" style="background-image:url('https://res.cloudinary.com/demo/image/upload/v1/hero.jpg')">
  <div class="hero-text"><h1 class="text-3xl font-bold">Dobi Layan Diri Seksyen 18</h1><p class="text-gray-300">Dobi 24 jam di Seksyen 18</p>
  <a href="https://wa.me/60198765432">WhatsApp</a><a href="#servis">Lihat servis</a></div>
  <img src="https://res.cloudinary.com/demo/image/upload/v1/hero.jpg" alt="Dobi">
  <div class="card"><span class="text-6xl font-black">Dari RM6.00</span></div>
</section>
<section id="servis"><h2 class="text-base">Perkhidmatan</h2><ul><li>Basuh 10kg RM6.00</li></ul><a href="#servis">Lihat servis</a></section>
<section id="tentang"><h2>Tentang Kami</h2><p>Dobi layan diri.</p></section>
<footer><a href="#servis">Lihat servis</a></footer>
</body></html>"""


def test_static_repairs_cap_the_side_card_and_lift_h2s():
    out, report = ph.static_type_repairs(DOBI)
    assert 'text-6xl' not in out.split('<section id="servis">')[0].split("<div class=\"card\">")[1]
    assert "text-4xl md:text-5xl lg:text-6xl" in out.split("</h1>")[0]  # H1 lifted from text-3xl
    assert '<h2 class="text-3xl md:text-4xl">Perkhidmatan</h2>' in out
    assert '<h2 class="text-3xl md:text-4xl">Tentang Kami</h2>' in out
    assert report.class_rewrites == 4


def test_measured_repairs_inject_paths_and_floors():
    measured = {
        "bodyFontPx": 16, "h1FontPx": 30,
        "largerThanH1": [{"path": "section#home > div:nth-of-type(2) > span", "px": 60, "text": "Dari RM6.00"}],
        "smallH2": [{"path": "section#servis > h2", "px": 16, "text": "Perkhidmatan"}],
    }
    out, report = ph.measured_type_repairs(DOBI, measured)
    assert 'id="binaapp-hierarchy"' in out
    assert "section#home > div:nth-of-type(2) > span{font-size:" in out
    assert "section#servis > h2{font-size:1.600rem!important" in out
    assert "h1{font-size:max(var(--step-5" in out and "h2{font-size:max(var(--step-3" in out
    assert any("capped" in n for n in report.notes) and any("lifted" in n for n in report.notes)


def test_hero_readability_panel_when_photo_is_bright():
    PIL = pytest.importorskip("PIL")
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), (225, 226, 230)).save(buf, format="PNG")  # bright silver
    measured = {"heroText": {"path": "section#home > div", "color": "rgb(156, 163, 175)", "box": {"x": 20, "y": 20, "width": 200, "height": 100}}}
    out, report = ph.hero_readability_repair(DOBI, buf.getvalue(), measured)
    assert report.hero_panel and report.hero_contrast < 4.5
    assert "section#home > div{background:rgba(0,0,0,.58)!important" in out
    dark = io.BytesIO()
    Image.new("RGB", (400, 300), (20, 20, 24)).save(dark, format="PNG")
    measured["heroText"]["color"] = "rgb(255,255,255)"
    out, report = ph.hero_readability_repair(DOBI, dark.getvalue(), measured)
    assert not report.hero_panel and report.hero_contrast >= 4.5


def test_inset_duplicate_hero_image_is_removed():
    out, report = ph.remove_duplicate_hero_image(DOBI)
    assert report.inset_removed
    assert out.count("hero.jpg") == 1  # only the background remains


def test_third_cta_repeat_is_removed_but_nav_hero_footer_keep_theirs():
    out, report = ph.dedupe_ctas(DOBI)
    assert report.ctas_removed == 1
    assert '<section id="servis">' in out and '<a href="#servis">Lihat servis</a></section>' not in out
    assert out.count("Lihat servis") == 3  # nav + hero + footer


def test_apply_all_without_a_render_injects_the_floor():
    out, report = ph.apply_hierarchy_repairs(DOBI)
    assert report.changed and 'id="binaapp-hierarchy"' in out and report.inset_removed and report.ctas_removed == 1


@pytest.mark.asyncio
async def test_browser_measures_offenders_and_hero_text():
    import os
    from app.services import design_critique as dc
    page = DOBI.replace("<head>", '<head><style>body{font-size:16px} h1{font-size:30px} .text-6xl{font-size:60px} .text-base{font-size:16px}</style>')
    bundle = await dc.render_screenshots(page, timeout=20)
    if not bundle.ok:
        pytest.skip(f"no browser: {bundle.error}")
    m = bundle.desktop_measured
    assert m["h1FontPx"] == 30 and m["bodyFontPx"] == 16
    assert any("Dari RM6" in o["text"] for o in m["largerThanH1"])
    assert any(o["text"] == "Perkhidmatan" for o in m["smallH2"])
    assert m["heroText"]["path"].startswith("section#home")
    out, report = ph.apply_hierarchy_repairs(page, measured=m, hero_png=bundle.desktop_png)
    again = await dc.render_screenshots(out, timeout=20)
    assert again.desktop_measured["largerThanH1"] == [] and again.desktop_measured["smallH2"] == []
    assert again.desktop_measured["h1FontPx"] >= 32
