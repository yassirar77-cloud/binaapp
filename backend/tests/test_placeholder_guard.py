"""Placeholders never reach the page."""

from app.services.generation_validator import GenerationBrief, validate_generated_site
from app.services.placeholder_guard import (
    FORM_PLACEHOLDER_EXAMPLES, hours_fallback, scrub_placeholder_echo, strip_brief_placeholders,
)

PANGLIMA_TAIL = (
    "Alamat: No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor.\n"
    "WhatsApp: 012-697 3105\n"
    "Waktu operasi: [ISI — contoh: 11 pagi – 10 malam, setiap hari]"
)


def test_bracketed_fill_in_is_stripped_and_its_line_dropped():
    clean, rep = strip_brief_placeholders(PANGLIMA_TAIL)
    assert "Waktu operasi" not in clean and "11 pagi" not in clean
    assert clean.endswith("WhatsApp: 012-697 3105")
    assert rep.dropped_lines == ["Waktu operasi: [ISI — contoh: 11 pagi – 10 malam, setiap hari]"]
    assert "11 pagi – 10 malam, setiap hari" in rep.examples


def test_content_in_brackets_is_kept():
    clean, rep = strip_brief_placeholders("Kami halal [JAKIM] sejak 2019. Pakej [2 pax] RM30.")
    assert clean == "Kami halal [JAKIM] sejak 2019. Pakej [2 pax] RM30."
    assert not rep.changed


def test_contoh_aside_and_trailing_example_are_stripped():
    clean, rep = strip_brief_placeholders("Menu: nasi lemak, ayam goreng (contoh: tambah item anda di sini)\nSlogan: contoh: Makin Pedas Makin Padu")
    assert clean == "Menu: nasi lemak, ayam goreng"
    assert "Slogan" not in clean
    assert "tambah item anda di sini" in rep.examples


def test_hours_fallback_copy():
    assert hours_fallback("ms") == "Hubungi kami untuk waktu operasi"
    assert hours_fallback("en") == "Contact us for opening hours"


def test_echoed_example_hours_and_form_placeholders_are_scrubbed_from_the_page():
    _, rep = strip_brief_placeholders(PANGLIMA_TAIL)
    html = (
        '<section id="contact"><p class="hours">Buka 11 pagi – 10 malam, setiap hari</p>'
        '<p>Alamat: Kota Bayu Emas</p><li>Waktu operasi: [ISI — contoh: 9 pagi]</li>'
        '<h3>Nasi Kandar Daging Crystal</h3><p>Hubungi 012-345 6789 untuk tempahan.</p></section>'
    )
    out, hits = scrub_placeholder_echo(html, rep.examples)
    assert "11 pagi" not in out and "[ISI" not in out and "Nasi Kandar Daging Crystal" not in out
    assert "012-345 6789" not in out and "untuk tempahan" in out
    assert "Alamat: Kota Bayu Emas" in out
    assert len(hits) >= 4


def test_validator_flags_a_placeholder_echo_as_an_error():
    brief = GenerationBrief(business_name="Ayam Gepuk Panglima", description="Restoran.", language="ms", whatsapp_number="0126973105")
    html = '<html><body><h1>Ayam Gepuk Panglima</h1><a href="https://wa.me/60126973105">WA</a><p>Waktu: [ISI — contoh: 9 pagi]</p></body></html>'
    result = validate_generated_site(html, brief)
    assert "placeholder_echo" in {e.code for e in result.errors}
    clean = '<html><body><h1>Ayam Gepuk Panglima</h1><a href="https://wa.me/60126973105">WA</a><p>Hubungi kami untuk waktu operasi</p></body></html>'
    assert "placeholder_echo" not in {e.code for e in validate_generated_site(clean, brief).errors}
    assert all(len(e) >= 4 for e in FORM_PLACEHOLDER_EXAMPLES)
