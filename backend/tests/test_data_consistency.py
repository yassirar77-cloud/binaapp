"""
Generate-time data consistency (data_consistency.py), with the Dobi Layan
Diri Seksyen 18 brief as the fixture: the story said Seksyen 18, the
address said Seksyen 7, hours were 24 jam, a price was typed "RM25.oo",
and the address came in as "l7/l, jalan 18/2, seksyen 18, shah alam".
"""

from decimal import Decimal

from app.services.data_consistency import (
    address_lines,
    apply_location_resolution,
    find_bad_prices,
    format_price,
    hours_are_24h,
    location_conflicts,
    location_tokens,
    normalize_address,
    normalize_hours,
    parse_price,
    reformat_prices,
)

DOBI_STORY = (
    "Dobi Layan Diri Seksyen 18 — dobi layan diri 24 jam di Seksyen 18, Shah Alam. "
    "Mesin basuh 10kg dan 20kg, pengering panas, bayar dengan syiling atau QR. Buka setiap hari."
)
DOBI_ADDRESS = "l7/l, jalan 18/2, seksyen 7, shah alam, selangor"


def test_location_tokens_from_story_and_address():
    story = location_tokens(DOBI_STORY)
    assert ("seksyen", "18") in [(t.kind, t.value) for t in story]
    assert ("city", "shah alam") in [(t.kind, t.value) for t in story]
    address = location_tokens(DOBI_ADDRESS)
    assert ("seksyen", "7") in [(t.kind, t.value) for t in address]


def test_location_conflict_fires_and_asks_the_merchant():
    conflicts = location_conflicts(DOBI_STORY, DOBI_ADDRESS)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.kind == "seksyen" and c.story_value == "Seksyen 18" and c.address_value == "Seksyen 7"
    assert c.question_ms == "Cerita sebut Seksyen 18 tapi alamat Seksyen 7 — yang mana betul?"
    assert location_conflicts(DOBI_STORY, "L7/1, Jalan 18/2, Seksyen 18, Shah Alam") == []
    assert location_conflicts("Kedai makan di Kajang", "Jalan 3, Bangi") and location_conflicts("Kedai makan di Kajang", "Jalan 3, Bangi")[0].kind == "city"
    assert location_conflicts("Taman Melawati branch", "12, Jalan 4, Taman Melawati, KL") == []
    assert location_conflicts("", DOBI_ADDRESS) == [] and location_conflicts(DOBI_STORY, "") == []


def test_location_resolution_rewrites_the_losing_side():
    story, address = apply_location_resolution(DOBI_STORY, DOBI_ADDRESS, {"seksyen": "story"})
    assert "seksyen 18" in address.lower() and "seksyen 7" not in address.lower()
    assert location_conflicts(story, address) == []
    story, address = apply_location_resolution(DOBI_STORY, DOBI_ADDRESS, {"seksyen": "address"})
    assert "Seksyen 7" in story and "Seksyen 18" not in story
    assert location_conflicts(story, address) == []


def test_hours_24h_detection_and_normalisation():
    assert hours_are_24h("00:00 - 23:59")
    assert hours_are_24h("00:00-00:00")
    assert hours_are_24h(None, DOBI_STORY)
    assert hours_are_24h("Buka 24/7")
    assert not hours_are_24h("10:00 - 22:00")
    info = normalize_hours("00:00 - 23:59", DOBI_STORY, "ms")
    assert info.is_24h and info.text == "Buka 24 jam" and info.source == "structured"
    assert normalize_hours("", DOBI_STORY, "en").text == "Open 24 hours"
    assert normalize_hours("10am - 10pm", DOBI_STORY).text == "10am - 10pm"
    assert normalize_hours("", "Kedai biasa").text is None


def test_price_parsing_rejects_typos_and_formats_once():
    assert parse_price("RM6") == Decimal("6.00")
    assert parse_price("6.5") == Decimal("6.50")
    assert parse_price("RM 12,50") == Decimal("12.50")
    assert parse_price("RM25.oo") is None
    assert parse_price("dari RM6") is None
    assert parse_price("") is None and parse_price(None) is None
    # A dangling separator is still a number; a bare one is not.
    assert parse_price("24.") == Decimal("24.00")
    assert parse_price(".90") == Decimal("0.90")
    assert parse_price("RM 12,") == Decimal("12.00")
    assert format_price("24./pax") == "RM24.00/pax"
    assert parse_price(".") is None and parse_price("RM") is None and parse_price("RM.") is None
    assert parse_price("1234567") is None  # still not a price
    assert format_price("RM6") == "RM6.00" and format_price(Decimal("12.5")) == "RM12.50" and format_price("abc") is None


def test_price_lint_and_reformat_on_html():
    html = '<span class="price">RM25.oo</span><p>Dari RM6</p><a href="https://wa.me/60?text=RM6">RM12,5</a>'
    assert find_bad_prices(html) == ["RM25.oo"]
    fixed, n = reformat_prices('<p>Dari RM6</p><a href="https://x/RM6">RM12,5</a>')
    assert "RM6.00" in fixed and "RM12.50" in fixed and 'href="https://x/RM6"' in fixed and n == 2
    assert find_bad_prices(fixed) == []


def test_the_currency_pass_stays_out_of_css_and_scripts():
    """mimk shipped `transition: background-color 0.2s ease, transfoRM0.20s
    ease` — twice — in its own <style> block. The pass is case-insensitive,
    so the "rm" ending `transform` read as a currency prefix, and the pass
    walked into <style> because its content sits between tags like any other
    text. Both halves are guarded now."""
    css = (
        "<style>.btn{transition: background-color 0.2s ease, transform 0.2s ease}"
        ".card{transform 0.2s}</style>"
    )
    assert reformat_prices(css) == (css, 0)
    script = '<script>var t="transform 0.2s ease"; var p="RM6";</script>'
    assert reformat_prices(script) == (script, 0)
    # A word ending in "rm" is never a price, wherever it appears.
    assert reformat_prices("<p>Kami transform 0.2s</p>") == ("<p>Kami transform 0.2s</p>", 0)
    assert find_bad_prices("<style>a{transform 0.2s}</style>") == []
    # …and real prose is still rewritten, in the same document.
    fixed, n = reformat_prices(css + "<p>Harga RM6</p>")
    assert n == 1 and "transform 0.2s ease" in fixed and "RM6.00" in fixed


def test_address_normalisation_fixes_lot_typo_and_case():
    assert normalize_address(DOBI_ADDRESS) == "L7/1, Jalan 18/2, Seksyen 7, Shah Alam, Selangor"
    assert normalize_address("no 12, jalan ss2/24, ss2, petaling jaya, 47300 selangor") == "No 12, Jalan SS2/24, SS2, Petaling Jaya, 47300 Selangor"
    assert address_lines(DOBI_ADDRESS)[0] == "L7/1"
    assert normalize_address("") == ""


def test_scrub_location_tokens_rewrites_the_losing_side_in_html():
    from app.services.data_consistency import scrub_location_tokens
    html = '<h1>Dobi Layan Diri Seksyen 18</h1><p>Alamat: L7/1, Jalan 18/2, Seksyen 7, Shah Alam</p><a href="https://maps.google.com/maps?q=Seksyen+7">peta</a>'
    out, n = scrub_location_tokens(html, {"Seksyen 7": "Seksyen 18"})
    assert "Seksyen 7" not in out and out.count("Seksyen 18") == 2 and n == 1
