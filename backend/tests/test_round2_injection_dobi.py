"""Round 2 §D13/§D14: the QR sits inside the footer container and inherits
its background; the fixed floats never overlap each other or the QR at
390px; the single-letter logo badge takes the plan accent and display font."""

import os

import pytest

from app.middleware.subdomain import _inject_qr_block, _inject_widgets, insert_in_footer
from app.services.page_hierarchy import restyle_logo_badge
from app.services.templates import TemplateService

FOOTER_PAGE = """<!DOCTYPE html><html lang="ms"><head></head><body>
<header><nav><span class="w-10 h-10 rounded-lg bg-blue-600 text-white font-sans flex items-center justify-center">D</span><span>Dobi Layan Diri Seksyen 18</span></nav></header>
<main><section id="home"><h1>Dobi Layan Diri Seksyen 18</h1></section></main>
<footer class="bg-slate-900 text-white"><div class="container border-b border-slate-700 pb-8"><p>&copy; Dobi</p></div></footer>
</body></html>"""


def test_qr_block_sits_inside_the_footer_container():
    out = _inject_qr_block(FOOTER_PAGE, "bebe", "ms")
    assert "BinaApp QR Block" in out
    container_close = out.index("</div></footer>")
    assert out.index("BinaApp QR Block") < container_close  # last child of the container
    assert "background:inherit;color:inherit" in out
    assert "</footer>\n<!-- BinaApp QR Block" not in out and out.index("BinaApp QR Block") < out.index("</footer>")
    # Re-serving never stacks a second block.
    again = _inject_qr_block(out, "bebe", "ms")
    assert again.count("BinaApp QR Block") == 1


def test_baked_qr_uses_the_same_placement_and_is_not_a_heading():
    out = TemplateService().inject_qr_code(FOOTER_PAGE, "https://bebe.binaapp.my")
    assert out.index("QR Code Section") < out.index("</div></footer>")
    assert "<h3" not in out.split("QR Code Section")[1]
    no_footer = "<html><body><p>x</p></body></html>"
    assert insert_in_footer(no_footer, "<b>q</b>").index("<b>q</b>") <= no_footer.index("</body>")


def test_float_stack_css_is_injected_with_the_widgets():
    out = _inject_widgets(FOOTER_PAGE, "site-1", "services", "ms", "bebe")
    assert 'id="binaapp-float-stack"' in out
    assert "#whatsapp-button" in out and "bottom:96px!important" in out  # chat present, no delivery → WhatsApp above the bubble
    assert "padding-bottom:132px" in out


@pytest.mark.asyncio
async def test_no_overlapping_floats_at_390():
    try:
        from playwright.async_api import async_playwright
    except Exception:
        pytest.skip("playwright not installed")
    page_html = _inject_widgets(_inject_qr_block(FOOTER_PAGE, "bebe", "ms"), "site-1", "services", "ms", "bebe")
    # Stand-ins for the script-created bubble/badge and the baked WhatsApp float, with their real CSS.
    stubs = (
        '<a id="whatsapp-button" href="https://wa.me/60198765432" style="position:fixed;bottom:20px;right:20px;width:60px;height:60px;z-index:1000;background:#25D366;display:block"></a>'
        '<div id="binaapp-chat-btn" style="position:fixed;bottom:24px;right:24px;width:58px;height:58px;z-index:2147482998;background:#16233F"></div>'
        '<div id="binaapp-open-badge" style="position:fixed;bottom:24px;left:24px;padding:8px 14px;z-index:999998;background:#fff;color:#000">Buka 24 jam</div>'
    )
    page_html = page_html.replace("</body>", stubs + "</body>")
    try:
        async with async_playwright() as pw:
            kwargs = {"headless": True, "args": ["--no-sandbox"]}
            if os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
                kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"]
            browser = await pw.chromium.launch(**kwargs)
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.set_content(page_html)
            await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            boxes = await page.evaluate("""() => {
              const ids = ['whatsapp-button','binaapp-chat-btn','binaapp-open-badge'];
              const out = {};
              for (const id of ids) { const el = document.getElementById(id); if (el) { const r = el.getBoundingClientRect(); out[id] = {x:r.left,y:r.top,w:r.width,h:r.height}; } }
              const qr = document.querySelector('img[alt*="Imbas"]');
              if (qr) { const r = qr.getBoundingClientRect(); out.qr = {x:r.left,y:r.top,w:r.width,h:r.height}; }
              return out;
            }""")
            await browser.close()
    except Exception as err:
        pytest.skip(f"no browser: {err}")

    def overlap(a, b):
        return not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"] or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"])

    keys = list(boxes)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            assert not overlap(boxes[a], boxes[b]), f"{a} overlaps {b}: {boxes}"


def test_logo_badge_takes_the_plan_accent_and_display_font():
    out, n = restyle_logo_badge(FOOTER_PAGE, initial="Dobi Layan Diri Seksyen 18", accent="#0B4F9C", display_font="Rubik")
    assert n == 1
    assert "bg-blue-600" not in out and "font-sans" not in out.split("</nav>")[0]
    assert "background:#0B4F9C;color:#fff;font-family:'Rubik'" in out and "font-heading" in out
    # A different letter is not the logo.
    same, n2 = restyle_logo_badge(FOOTER_PAGE, initial="Kedai", accent="#000", display_font="Rubik")
    assert n2 == 0 and same == FOOTER_PAGE
