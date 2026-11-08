"""The map slot renders the iframe AND both buttons — nothing clipped.

agp's slot was 'w-full aspect-[16/9] rounded-lg ... overflow-hidden': the
widget's address line, 16:9 map and Google Maps / Waze buttons did not fit,
and both buttons were cut off."""

import os
import re
import sys

from app.services.templates import TemplateService

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from verify_site_menu import verify_map  # noqa: E402

FULL = "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor"
SLOT_PAGE = (
    '<html><body><section id="location"><div><h2>Lokasi &amp; Waktu</h2><div class="grid md:grid-cols-2">'
    f'<div><h3>Alamat</h3><p>{FULL}.</p></div>'
    '<div id="binaapp-maps-slot" class="w-full aspect-[16/9] md:h-80 rounded-lg border-2 border-black overflow-hidden bg-gray-100" '
    'style="height:320px"></div></div></div></section><footer></footer></body></html>'
)


def _inject(page):
    return TemplateService().inject_google_maps(page, FULL, business_name="Ayam Gepuk Panglima")


def test_slot_loses_its_fixed_size_and_clipping_but_keeps_its_look():
    out = _inject(SLOT_PAGE)
    tag = re.search(r'<div id="binaapp-maps-slot"[^>]*>', out).group(0)
    assert 'class="w-full rounded-lg border-2 border-black bg-gray-100"' in tag
    assert "320px" not in tag  # the fixed height is gone
    assert "aspect-ratio:auto;height:auto;max-height:none;overflow:visible" in tag


def test_iframe_and_both_buttons_render_and_verify_passes():
    out = _inject(SLOT_PAGE)
    assert verify_map(out) == {"map_iframe": True, "map_google_maps_button": True, "map_waze_button": True, "map_not_clipped": True}


def test_address_not_repeated_when_the_section_shows_it():
    out = _inject(SLOT_PAGE)
    assert "📍" not in out
    bare = SLOT_PAGE.replace(f"<p>{FULL}.</p>", "<p>Kota Bayu Emas</p>")
    assert "📍" in _inject(bare)


def test_verify_catches_the_agp_regression():
    clipped = (
        '<div id="binaapp-maps-slot" class="w-full aspect-[16/9] overflow-hidden"><div class="binaapp-map-widget">'
        '<div><iframe src="https://www.google.com/maps?q=x&output=embed"></iframe></div>'
        '<div class="binaapp-map-actions"><a href="https://www.google.com/maps/search/?api=1">Buka di Google Maps</a>'
        '<a href="https://waze.com/ul?q=x">Waze</a></div>\n  </div>\n</div>'
    )
    assert verify_map(clipped)["map_not_clipped"] is False
    no_buttons = clipped.replace("aspect-[16/9] overflow-hidden", "").replace(
        '<div class="binaapp-map-actions"><a href="https://www.google.com/maps/search/?api=1">Buka di Google Maps</a>'
        '<a href="https://waze.com/ul?q=x">Waze</a></div>', "")
    res = verify_map(no_buttons)
    assert res["map_google_maps_button"] is False and res["map_waze_button"] is False
