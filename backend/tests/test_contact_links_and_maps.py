"""tel: links for printed numbers; the address read from the brief; map
direction buttons."""

from app.services.contact_links import linkify_phones
from app.services.data_consistency import address_from_brief
from app.services.templates import TemplateService

PANGLIMA_BRIEF = (
    "Ayam Gepuk Panglima ialah restoran ayam gepuk di Kota Bayu Emas, Klang.\n\n"
    "Alamat: No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor.\n"
    "WhatsApp: 012-697 3105"
)


def test_printed_numbers_become_tel_links_but_links_scripts_and_attributes_are_untouched():
    html = (
        '<p>Hubungi kami: 012-697 3105 atau 03-3323 1234.</p>'
        '<a href="https://wa.me/60126973105">0126973105</a>'
        '<script>var p="0126973105";</script>'
        '<img alt="012-697 3105" src="x.jpg">'
        '<script type="application/ld+json">{"telephone":"60126973105"}</script>'
    )
    out, n = linkify_phones(html)
    assert n == 2
    assert '<a href="tel:+60126973105" class="binaapp-tel" style="text-decoration:inherit;color:inherit">012-697 3105</a>' in out
    assert 'href="tel:+60333231234"' in out
    assert out.count("<a ") == 3 and 'var p="0126973105"' in out and 'alt="012-697 3105"' in out


def test_known_digits_limit_linking_to_the_merchants_number():
    out, n = linkify_phones("<p>012-697 3105 dan 019-000 0000</p>", known_digits=["60126973105"])
    assert n == 1 and "tel:+60190000000" not in out
    again, n2 = linkify_phones(out, known_digits=["60126973105"])
    assert n2 == 0 and again == out


def test_address_is_read_from_a_labelled_line_in_the_brief():
    assert address_from_brief(PANGLIMA_BRIEF) == "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor"
    assert address_from_brief("Kedai kami di Lot 12, Jalan Tun Razak, 50400 Kuala Lumpur sejak 2010") == "Kedai kami di Lot 12, Jalan Tun Razak, 50400 Kuala Lumpur sejak 2010"
    assert address_from_brief("Warung nasi lemak sedap, area Klang.") == ""
    assert address_from_brief("") == ""


def test_map_block_carries_google_maps_and_waze_buttons():
    svc = TemplateService()
    html = '<html><body><section id="hero">h</section><footer>f</footer></body></html>'
    out = svc.inject_google_maps(html, "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor", language="ms")
    assert "maps?q=" in out and "output=embed" in out
    assert "maps/search/?api=1&amp;query=No.+44-1" in out
    assert "waze.com/ul?q=" in out and "Buka di Google Maps</a>" in out and "Waze</a>" in out
    buttons = svc.map_direction_buttons("x", language="en", lat=3.0421, lng=101.4454)
    assert "destination=3.042100,101.445400" in buttons and "ll=3.042100,101.445400" in buttons and "Open in Google Maps" in buttons
    assert svc.map_direction_buttons("", language="ms") == ""
