"""Third agp regeneration review.

- Prices and 'Pesan' buttons came out mustard (#8C6B00): --primary-color was
  set to accent_strong (the darkened SECONDARY yellow), not the plan's
  primary accent (chilli red #C81E1E).
- The tap-to-call link in 'Hubungi Kami' rendered as bare highlighted
  text: every class containing 'whatsapp' was stripped, including the
  .btn-whatsapp that carries the button's padding and radius.
- The hero's spice-level strip was 'absolute bottom-0 z-20' and covered the
  hero CTA buttons on a phone.
- The generation-time QR block read 'Scan to Visit' on a Malay page, with
  margin:0 0 1rem.
"""

from types import SimpleNamespace

from app.services.contact_links import add_call_links
from app.services.designer_prompt_blocks import _primary_colour, head_block
from app.services.hero_strip import dock_hero_bottom_strip
from app.services.templates import TemplateService

PAL = {"primary": "#C81E1E", "secondary": "#A01818", "accent": "#FFD23F", "accent_strong": "#8C6B00",
       "background": "#FFF8E1", "surface": "#FFFFFF", "text": "#141414", "text_muted": "#5A4A2A"}


class TestPrimaryColour:
    def test_plan_primary_drives_prices_and_buttons(self):
        out = head_block(SimpleNamespace(type={"display": "Archivo Black"}), "", "", PAL, "#FFD23F", "#8C6B00", "Nunito", "sans-serif")
        assert "--primary-color: #C81E1E" in out and "--accent-color: #FFD23F" in out

    def test_unreadable_primary_falls_back_to_accent_strong(self):
        assert _primary_colour({**PAL, "primary": "#FFE680"}, "#8C6B00") == "#8C6B00"


class TestCallButton:
    PAGE = (
        '<section id="contact"><div><a href="https://wa.me/60126973105?text=x" '
        'class="btn-whatsapp bg-white text-[#141414] border-black hover:bg-gray-100">WhatsApp Kami</a></div></section>'
        '<footer><a href="https://wa.me/60126973105" class="footer-link">012-697 3105</a></footer>'
    )

    def test_button_shape_class_kept_and_colour_neutralised(self):
        out, n = add_call_links(self.PAGE, "60126973105")
        assert n == 2
        assert ('<a href="tel:+60126973105" class="btn-whatsapp bg-white text-[#141414] border-black hover:bg-gray-100 binaapp-call" '
                'style="background:#FFFFFF;color:#141414;border-color:#141414"') in out
        assert '<a href="tel:+60126973105" class="footer-link binaapp-call" aria-label' in out

    def test_only_green_colour_utilities_are_dropped(self):
        page = ('<section id="contact"><a href="https://wa.me/60126973105" '
                'class="inline-flex px-6 py-3 rounded-full bg-[#25D366] hover:bg-green-600 text-white md:bg-emerald-500">WA</a></section>')
        out, _ = add_call_links(page, "60126973105")
        assert 'class="inline-flex px-6 py-3 rounded-full text-white binaapp-call"' in out


HERO = (
    '<section id="hero" class="relative w-full min-h-[60vh] flex items-end overflow-hidden">'
    '<img src="x.jpg" class="absolute inset-0 w-full h-full object-cover">'
    '<div class="absolute inset-0 bg-gradient-to-t from-black/45 to-transparent"></div>'
    '<div class="relative z-10 w-full pb-8"><h1>AGP</h1><a href="https://wa.me/1">Pesan</a></div>'
    '<div class="absolute bottom-0 left-0 right-0 z-20 bg-[#FFD23F] py-3"><span>LEVEL 1 SPICY</span></div>'
    '</section><section id="menu"></section>'
)


class TestHeroStrip:
    def test_strip_is_docked_under_the_copy(self):
        out, n = dock_hero_bottom_strip(HERO)
        assert n == 1
        assert '<section id="hero" class="relative w-full min-h-[60vh] flex flex-col justify-end overflow-hidden">' in out
        assert '<div class="relative w-full z-20 bg-[#FFD23F] py-3">' in out
        # The scrim and image stay absolute; the menu is untouched.
        assert 'class="absolute inset-0 bg-gradient-to-t' in out and '<section id="menu"></section>' in out
        assert dock_hero_bottom_strip(out) == (out, 0)

    def test_empty_decorative_bottom_bar_is_left_alone(self):
        page = HERO.replace('<span>LEVEL 1 SPICY</span>', '')
        assert dock_hero_bottom_strip(page) == (page, 0)

    def test_no_hero_no_change(self):
        assert dock_hero_bottom_strip('<section id="menu"></section>') == ('<section id="menu"></section>', 0)


def test_generation_time_qr_label_is_malay_and_centred():
    svc = TemplateService()
    out = svc.inject_qr_code("<html><body><footer><div><p>x</p></div></footer></body></html>", "https://agp.binaapp.my")
    assert "📱 Imbas untuk Lawat" in out and "margin:0 auto 1rem" in out and "Scan to Visit" not in out
    out_en = svc.inject_qr_code("<html><body><footer></footer></body></html>", "https://x", language="en")
    assert "📱 Scan to Visit" in out_en
