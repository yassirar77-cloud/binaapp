"""agp regeneration after #837: four things the screenshots showed.

- The map slot was clipped by the page's OWN stylesheet
  (.map-slot{aspect-ratio:16/9;overflow:hidden}) — both buttons hidden.
- The footer's 'WhatsApp: 012-697 3105' became a tel: (phone call) link.
- 'saya nak tanya waktu operasi' got the order blanks '(Level: _, ...)'.
- Tilted 'Level 1/2/3' stickers piled on the hero photo, duplicating the
  straight level row in the hero panel."""

import os
import sys
from urllib.parse import unquote

from app.services.contact_links import add_call_links, linkify_phones
from app.services.spice_levels import CHIP_CLASS, compact_spice_levels
from app.services.templates import TemplateService
from app.services.whatsapp_prefill import enrich_order_links

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from verify_site_menu import verify_map  # noqa: E402

FULL = "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor"


class TestMapSlotStylesheet:
    PAGE = ("<html><head><style>.map-slot { aspect-ratio: 16 / 9; background:#eee; overflow: hidden; }</style></head><body>"
            '<section id="location"><h2>Lokasi</h2><div id="binaapp-maps-slot" class="map-slot"></div></section><footer></footer></body></html>')

    def test_verify_sees_the_stylesheet_clip(self):
        bad = TemplateService().inject_google_maps(self.PAGE, FULL).replace(
            'style="aspect-ratio:auto;height:auto;max-height:none;overflow:visible"', "")
        assert verify_map(bad)["map_not_clipped"] is False

    def test_injection_overrides_it_inline(self):
        out = TemplateService().inject_google_maps(self.PAGE, FULL)
        assert 'class="map-slot" style="aspect-ratio:auto;height:auto;max-height:none;overflow:visible"' in out
        assert verify_map(out) == {"map_iframe": True, "map_google_maps_button": True, "map_waze_button": True, "map_not_clipped": True}


def test_whatsapp_labelled_number_opens_whatsapp_and_telefon_line_follows():
    footer = '<footer><p>WhatsApp: 012-697 3105</p><p>Hubungi: 012-697 3105</p></footer>'
    out, n = linkify_phones(footer)
    assert n == 2
    assert 'WhatsApp: <a href="https://wa.me/60126973105" class="binaapp-wa"' in out
    assert 'Hubungi: <a href="tel:+60126973105" class="binaapp-tel"' in out
    only_wa = '<footer><p>WhatsApp: 012-697 3105</p></footer>'
    out2, _ = add_call_links(linkify_phones(only_wa)[0], "60126973105")
    assert 'Telefon: 012-697 3105</a>' in out2


def test_a_question_gets_no_order_blanks():
    q = '<a href="https://wa.me/60126973105?text=Assalamualaikum%2C%20saya%20nak%20tanya%20waktu%20operasi">WhatsApp Kami</a>'
    out, n = enrich_order_links(q, "Level 1 Spicy. Take away caj RM2", "ms")
    assert n == 0 and out == q
    order = '<a href="https://wa.me/60126973105?text=Assalamualaikum%2C%20saya%20nak%20order%20Set%20A">Pesan</a>'
    out2, n2 = enrich_order_links(order, "Level 1 Spicy. Take away", "ms")
    assert n2 == 1 and "(Level: _, Dine-in/Take away: _)" in unquote(out2)


def test_duplicate_tilted_level_stickers_on_the_hero_photo_are_dropped():
    hero = (
        '<html><head></head><body><section id="hero"><div class="panel"><h1>AGP</h1>'
        '<div class="mt-6 flex gap-2"><span class="chip">Level 1 Spicy</span><span class="chip">Level 2 Hot</span>'
        '<span class="chip">Level 3 Extra Hot</span></div></div>'
        '<div class="hero-photo"><img src="x.jpg"><div class="hero-sticker-row">'
        '<div class="sticker-badge">Set Panglima<br>RM12.50</div>'
        '<div class="sticker-badge">Level 1<br>Spicy</div><div class="sticker-badge">Level 2<br>Hot</div>'
        '<div class="sticker-badge">Level 3<br>Extra Hot</div></div></div></section>'
        '<section id="menu"><div>Level 1</div></section></body></html>'
    )
    out, changed = compact_spice_levels(hero)
    assert changed
    assert out.count(CHIP_CLASS + '"') == 3  # the panel row
    assert '<div class="hero-sticker-row"><div class="sticker-badge">Set Panglima<br>RM12.50</div></div>' in out
    assert '<section id="menu"><div>Level 1</div></section>' in out  # outside the hero: untouched
