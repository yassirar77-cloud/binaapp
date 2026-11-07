"""Spice levels: one compact row of chips, not three full-width blocks."""

from app.services.spice_levels import CHIP_CLASS, ROW_CLASS, compact_spice_levels

CARDS = """<html><head><title>t</title></head><body>
<section class="spice-band py-8" aria-label="Tahap kepedasan"><div class="max-w-7xl mx-auto">
<div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
<div class="spice-level-block rounded-lg p-6 text-center"><span class="text-3xl block">Level 1</span><span>Spicy</span></div>
<div class="spice-level-block rounded-lg p-6 text-center"><span class="text-3xl block">Level 2</span><span>Hot</span></div>
<div class="spice-level-block rounded-lg p-6 text-center"><span class="text-3xl block">Level 3</span><span>Extra Hot</span></div>
</div></div></section>
<section id="menu"><p>Pilih tahap kepedasan anda — Level 1, Level 2 atau Level 3.</p></section></body></html>"""


def test_cards_become_one_row():
    out, changed = compact_spice_levels(CARDS)
    assert changed
    assert f'<div class="grid grid-cols-1 sm:grid-cols-3 gap-6 {ROW_CLASS}">' in out
    assert out.count(f'p-6 text-center {CHIP_CLASS}"') == 3
    assert '<style id="binaapp-spice-css">' in out and out.index("binaapp-spice-css") < out.index("</head>")
    assert "grid-template-columns:repeat(var(--binaapp-spice-n,3),minmax(0,1fr))" in out
    # The menu sentence that mentions the levels is untouched.
    assert "<p>Pilih tahap kepedasan anda — Level 1, Level 2 atau Level 3.</p>" in out


def test_idempotent_and_rest_of_document_byte_identical():
    out, _ = compact_spice_levels(CARDS)
    assert compact_spice_levels(out) == (out, False)
    stripped = out.replace(f" {ROW_CLASS}", "").replace(f" {CHIP_CLASS}", "")
    stripped = stripped[: stripped.index('<style id="binaapp-spice-css">')] + stripped[stripped.index("</style>", stripped.index("binaapp-spice-css")) + 8:]
    assert stripped == CARDS


def test_inline_chips_in_a_flex_strip():
    page = ('<div class="flex flex-wrap gap-3"><span class="chip">🔥 LEVEL 1 SPICY</span>'
            '<span class="chip">🔥 LEVEL 2 HOT</span><span class="chip">🔥 LEVEL 3 EXTRA HOT</span></div>')
    out, changed = compact_spice_levels(page)
    assert changed and f'class="flex flex-wrap gap-3 {ROW_CLASS}"' in out and out.count(CHIP_CLASS) == 3 + 4


def test_a_sentence_or_two_levels_is_not_a_row():
    assert compact_spice_levels("<p>Level 1, Level 2 atau Level 3</p>") == ("<p>Level 1, Level 2 atau Level 3</p>", False)
    two = '<div><div>Level 1 Spicy</div><div>Level 2 Hot</div></div>'
    assert compact_spice_levels(two) == (two, False)
