"""Hero spice chips straight, in their columns, clear of the floating
WhatsApp button; 'WhatsApp Kami' keeps its WhatsApp icon."""

from app.services.contact_links import WA_ICON, ensure_whatsapp_icons
from app.services.spice_levels import HERO_ROW_CLASS, ROW_CLASS, SPICE_CSS, compact_spice_levels

HERO = """<html><head></head><body>
<section id="hero" class="relative"><div class="hero-panel"><h1>Makin Pedas</h1></div>
<div class="flex flex-wrap gap-3 mt-6">
<span class="sticker-badge sticker-drop sticker-drop-1"><i class="fa-solid fa-fire"></i> Level 1 Spicy</span>
<span class="sticker-badge sticker-drop sticker-drop-2"><i class="fa-solid fa-fire"></i><i class="fa-solid fa-fire"></i> Level 2 Hot</span>
<span class="sticker-badge sticker-drop sticker-drop-3"><i class="fa-solid fa-fire"></i><i class="fa-solid fa-fire"></i><i class="fa-solid fa-fire"></i> Level 3 Extra Hot</span>
</div></section><section id="menu"></section></body></html>"""


class TestHeroChips:
    def test_row_in_the_hero_is_marked_and_kept_clear_of_the_floating_button(self):
        out, changed = compact_spice_levels(HERO)
        assert changed and f'class="flex flex-wrap gap-3 mt-6 {ROW_CLASS} {HERO_ROW_CLASS}"' in out
        assert f"@media (max-width:767px){{.{ROW_CLASS}.{HERO_ROW_CLASS}{{padding-right:4.75rem!important}}}}" in SPICE_CSS

    def test_chips_are_straight_and_wrap_inside_their_column(self):
        for rule in ("transform:none!important", "rotate:none!important", "animation:none!important",
                     "opacity:1!important", "white-space:normal!important", "display:block!important", "min-width:0!important"):
            assert rule in SPICE_CSS, rule

    def test_a_row_outside_the_hero_gets_no_clearance(self):
        page = HERO.replace('<section id="hero" class="relative"><div class="hero-panel"><h1>Makin Pedas</h1></div>',
                            '<section id="hero"><h1>x</h1></section><section id="info">')
        out, _ = compact_spice_levels(page)
        assert ROW_CLASS in out and f"{ROW_CLASS} {HERO_ROW_CLASS}" not in out


class TestWhatsAppIcon:
    def test_bare_whatsapp_buttons_get_the_icon(self):
        html = ('<a href="https://wa.me/60126973105?text=x" class="btn-primary">WhatsApp Kami</a>'
                '<a href="https://wa.me/60126973105" class="btn"><i class="fa-brands fa-whatsapp"></i> Pesan di WhatsApp</a>'
                '<a href="https://wa.me/60126973105?text=Set%20A" class="bmf-order">Pesan</a>'
                '<a href="https://wa.me/60126973105" class="float"><svg></svg></a>')
        out, n = ensure_whatsapp_icons(html)
        assert n == 1
        assert f'<a href="https://wa.me/60126973105?text=x" class="btn-primary">{WA_ICON} WhatsApp Kami</a>' in out
        assert '<a href="https://wa.me/60126973105?text=Set%20A" class="bmf-order">Pesan</a>' in out
        assert ensure_whatsapp_icons(out) == (out, 0)
