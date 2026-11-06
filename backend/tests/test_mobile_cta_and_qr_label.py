"""Small layout fixes from agp.binaapp.my: the mobile panel's WhatsApp CTA
("w-full ml-4") overflowed the viewport, and the QR label sat off-centre."""

import re

from app.services.generation_linter import lint_html, lint_tailwind_classes


def test_w_full_with_side_margin_drops_the_margin():
    html = ('<div id="mobile-menu" class="md:hidden"><a href="https://wa.me/60126973105" '
            'class="w-full ml-4 inline-flex justify-center rounded-full bg-red-600 px-5 py-3">WhatsApp</a></div>')
    out, rewrites = lint_tailwind_classes(html)
    assert 'class="w-full inline-flex justify-center rounded-full bg-red-600 px-5 py-3"' in out
    assert ("ml-4", "(removed: w-full + side margin overflows)") in rewrites


def test_other_margins_and_prefixed_variants_are_left_alone():
    html = ('<a class="ml-4 px-3">x</a><a class="w-full mt-4 mx-auto">y</a>'
            '<a class="w-full md:ml-4">z</a><a class="md:w-full ml-4">w</a><a class="w-full ml-0">v</a>')
    out, rewrites = lint_tailwind_classes(html)
    assert out == html and rewrites == []


def test_mx_and_arbitrary_values_and_full_linter():
    out, _ = lint_html('<button class="w-full mx-6 mr-[12px] block">Pesan</button>')
    assert re.search(r'class="w-full block"', out)


def test_qr_label_is_centred():
    from app.middleware.subdomain import _inject_qr_block

    html = "<html><body><main></main><footer><div class='container'><p>&copy;</p></div></footer></body></html>"
    out = _inject_qr_block(html, "agp", "ms")
    label = re.search(r"<p style=\"([^\"]*)\">📱 Imbas untuk Lawat</p>", out)
    assert label and "margin:0 auto 1rem" in label.group(1) and "text-align:center" in label.group(1)
    assert "margin:0 0 1rem" not in out
