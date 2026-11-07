"""Tap-to-call beside WhatsApp in the contact section and footer.

The regenerated agp page had WhatsApp only: the footer printed the number
inside the wa.me link, so no tel: link existed anywhere on the page."""

import re

from app.services.contact_links import add_call_links, display_phone

PAGE = (
    '<html><body><section id="hero"><a href="https://wa.me/60126973105?text=x" class="btn">Pesan</a></section>'
    '<section id="contact" class="py-16"><div class="flex gap-4">'
    '<a href="https://wa.me/60126973105?text=Assalamualaikum" class="inline-flex px-6 py-3 rounded-full bg-[#25D366] hover:bg-green-600 text-white font-bold">'
    '<i class="fa-brands fa-whatsapp"></i> WhatsApp Kami</a></div></section>'
    '<footer><p class="text-sm">WhatsApp: <a href="https://wa.me/60126973105" class="footer-link">012-697 3105</a></p></footer>'
    '</body></html>'
)


def test_display_phone():
    assert display_phone("60126973105") == "012-697 3105"
    assert display_phone("601123456789") == "011-2345 6789"
    assert display_phone("60333231234") == "03-3323 1234"


def test_contact_and_footer_get_a_call_link_next_to_whatsapp():
    out, n = add_call_links(PAGE, "60126973105")
    assert n == 2
    contact = out[out.index('id="contact"'):out.index("</section>", out.index('id="contact"'))]
    call = re.search(r'<a href="tel:\+60126973105" class="([^"]*)"[^>]*>(.*?)</a>', contact)
    assert call and "Telefon 012-697 3105" in call.group(2)
    assert "inline-flex px-6 py-3 rounded-full" in call.group(1) and "25D366" not in call.group(1) and "green" not in call.group(1)
    assert contact.index("WhatsApp Kami") < contact.index("tel:+60126973105")
    footer = out[out.index("<footer"):]
    # Its own line, number shown, no "·" separator.
    assert '012-697 3105</a><br><a href="tel:+60126973105" class="footer-link binaapp-call"' in footer
    assert re.search(r'tel:\+60126973105[^>]*>.*?Telefon: 012-697 3105</a>', footer)
    assert " · " not in footer
    # Hero is neither contact nor footer.
    assert "tel:" not in out[:out.index('id="contact"')]


def test_idempotent_and_existing_tel_respected():
    out, _ = add_call_links(PAGE, "60126973105")
    again, n = add_call_links(out, "60126973105")
    assert n == 0 and again == out
    has_tel = PAGE.replace("</footer>", '<a href="tel:+60126973105">Call</a></footer>')
    _, n2 = add_call_links(has_tel, "60126973105")
    assert n2 == 1  # only the contact section


def test_english_label_and_local_digits():
    out, n = add_call_links(PAGE, "0126973105", language="en")
    assert n == 2 and "Call 012-697 3105" in out and 'href="tel:+60126973105"' in out


def test_footer_block_level_link_gets_its_own_line_without_a_dot():
    page = ('<footer><div><h3>Hubungi</h3><a href="https://wa.me/60126973105" class="text-gray-300 flex items-center gap-2">'
            '<i class="fa-brands fa-whatsapp"></i> 012-697 3105</a><h3>Cara bayaran</h3></div></footer>')
    out, n = add_call_links(page, "60126973105")
    assert n == 1 and "·" not in out and "<br>" not in out
    assert ('</a><a href="tel:+60126973105" class="text-gray-300 flex items-center gap-2 binaapp-call" '
            'aria-label="Telefon 012-697 3105" style="margin-top:.5rem"><i class="fa-solid fa-phone" aria-hidden="true"></i> '
            'Telefon: 012-697 3105</a><h3>') in out


def test_footer_list_item_gets_its_own_list_item():
    page = ('<footer><ul class="space-y-2"><li class="text-sm"><a href="https://wa.me/60126973105">WhatsApp</a></li>'
            '<li>Klang</li></ul></footer>')
    out, _ = add_call_links(page, "60126973105")
    assert ('<li class="text-sm"><a href="https://wa.me/60126973105">WhatsApp</a></li><li class="text-sm">'
            '<a href="tel:+60126973105" class="binaapp-call" aria-label="Telefon 012-697 3105">'
            '<i class="fa-solid fa-phone" aria-hidden="true"></i> Telefon: 012-697 3105</a></li><li>Klang</li>') in out
