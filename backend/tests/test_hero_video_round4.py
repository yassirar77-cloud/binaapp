"""Round 4 (runcit-label-test.binaapp.my, Run 1 site A).

Bug 7: the keep-colour pass stamped nothing — ``data-binaapp-keep-color``
appeared zero times on the whole page while ``data-binaapp-video-playing="1"``
was there, so the bootstrap ran and the pass found no elements. It could not:
the bootstrap is the hero's FIRST child and executed while the parser was
still inside the hero, before the copy and the buttons existed.

Bug 8: the hero was designed dark — ``text-white`` headline over its own
``from-black/40 … to-black/70`` gradient — on a light (Cerah) page. ``auto``
read the PAGE, painted a white veil under the hero's black one and forced the
white copy to navy. The scrim now follows what the HERO paints, an ``auto``
scrim never rewrites the copy, and a scrim the hero already has is counted
instead of doubled.
"""

from app.services.color_tone import alpha_over, text_tone, tint, tone_of_color
from app.services.hero_video_patcher import (
    KEEP_COLOR_ATTR,
    STYLE_ID,
    apply_hero_video,
    build_settings,
    detect_hero_tone,
    hero_own_veil,
    needs_style_upgrade,
    remove_hero_video,
)

#: Site A as published: a light page carrying a dark editorial hero, with a
#: bare <img> as a direct child of the section (the third media shape).
SITE_A = (
    "<!DOCTYPE html><html><head>"
    "<style>:root{--bg-color:#FFFBF5;--primary-color:#EA580C}</style></head>"
    '<body class="bg-[#FFFBF5]">'
    '<section id="home" class="relative h-screen min-h-[600px] flex items-center">'
    '<img src="https://res.cloudinary.com/d/image/upload/v1/binaapp/kedai.jpg"'
    ' class="absolute inset-0 w-full h-full object-cover" alt="">'
    '<div class="absolute inset-0 bg-gradient-to-b from-black/40 via-black/25 to-black/70"></div>'
    '<div class="relative z-10 max-w-5xl">'
    '<h1 class="text-5xl font-bold text-white">Kedai Runcit Pak Din</h1>'
    '<p class="text-white/80">Seksyen 7, Shah Alam · Buka Setiap Hari</p>'
    '<a class="inline-flex bg-primary text-white rounded-full px-8 py-4" href="#kontak">Hubungi</a>'
    '<a class="bg-white/10 backdrop-blur border border-white/30 text-white px-8 py-4" href="#produk">Produk</a>'
    "</div></section>"
    "<section id=\"produk\"><h2>Produk</h2></section>"
    "<footer>Kedai Runcit Pak Din</footer></body></html>"
)

VIDEO = "https://res.cloudinary.com/d/video/upload/v1789273876/binaapp/hero-videos/a.mp4"
POSTER = "https://res.cloudinary.com/d/video/upload/v1789273876/binaapp/hero-videos/a.jpg"


def _settings(**kw):
    base = {"video_url": VIDEO, "poster_url": POSTER, "poster_luminance": 0.463}
    base.update(kw)
    return build_settings(**base)


def _style(html):
    i = html.index(f'<style id="{STYLE_ID}">')
    return html[i:html.index("</style>", i)]


class TestTheHeroDecidesNotThePage:
    def test_a_dark_hero_on_a_light_page_reads_dark(self):
        assert detect_hero_tone(SITE_A) == "dark"

    def test_the_scrim_follows_the_hero(self):
        assert _settings().resolved_overlay(SITE_A) == "dark"

    def test_no_white_veil_is_painted_over_the_clip(self):
        style = _style(apply_hero_video(SITE_A, _settings()).html)
        assert "rgba(255,255,255," not in style

    def test_the_white_copy_is_not_repainted_navy(self):
        html = apply_hero_video(SITE_A, _settings()).html
        assert "color:rgb(15, 23, 42)" not in html
        assert "color:#0F172A !important" not in _style(html)
        assert _settings().resolved_text_mode(SITE_A) == "keep"

    def test_the_page_still_decides_when_the_hero_says_nothing(self):
        quiet = (
            "<html><head><style>:root{--bg-color:#FFFBF5}</style></head><body>"
            '<section id="home"><div><span>Hai</span></div></section>'
            "<footer>f</footer></body></html>"
        )
        assert detect_hero_tone(quiet) == ""
        assert _settings().resolved_overlay(quiet) == "light"

    def test_an_explicit_pick_still_beats_everything(self):
        settings = _settings(overlay="light")
        assert settings.resolved_overlay(SITE_A) == "light"
        # …and a scrim that fights the hero is the one case that recolours.
        assert settings.resolved_text_mode(SITE_A) == "dark"


class TestOneScrimNotTwo:
    def test_the_heros_own_gradient_is_found(self):
        assert hero_own_veil(SITE_A) == ("dark", 0.7)

    def test_our_scrim_gives_way_to_it(self):
        result = apply_hero_video(SITE_A, _settings())
        assert "background:transparent;" in _style(result.html)
        assert "scrim_shared_with_hero_veil:dark:0.7" in result.notes

    def test_a_thin_veil_is_topped_up_not_replaced(self):
        thin = SITE_A.replace(
            "bg-gradient-to-b from-black/40 via-black/25 to-black/70", "bg-black/20"
        )
        assert hero_own_veil(thin) == ("dark", 0.2)
        style = _style(apply_hero_video(thin, _settings()).html)
        # 0.52 wanted over 0.20 already there -> 0.40 on top composites back
        # to 0.52, instead of stacking to 0.62.
        assert "rgba(0,0,0,0.4)" in style

    def test_alpha_over_composites_to_the_target(self):
        added = alpha_over(0.52, 0.20)
        assert added == 0.4
        assert round(1 - (1 - 0.20) * (1 - added), 2) == 0.52
        assert alpha_over(0.52, 0.70) == 0.0

    def test_a_veil_holding_content_is_not_a_scrim(self):
        # The copy block is `absolute inset-0` in some layouts; hiding behind
        # it or counting it as a scrim would both be wrong.
        copy_block = (
            '<section id="home" class="relative">'
            '<div class="absolute inset-0 bg-black/50"><h1 class="text-white">Hai</h1></div>'
            "</section>"
        )
        assert hero_own_veil(f"<html><body>{copy_block}</body></html>") is None


class TestKeepColourActuallyStamps:
    def test_the_pass_is_deferred_to_a_parsed_document(self):
        html = apply_hero_video(SITE_A, _settings()).html
        assert "document.addEventListener('DOMContentLoaded',stamp);else stamp();" in html

    def test_the_bootstrap_really_does_run_before_the_copy_exists(self):
        # The structural reason the old pass found nothing, asserted rather
        # than remembered: the script is emitted ahead of the hero's copy.
        html = apply_hero_video(SITE_A, _settings()).html
        assert html.index("function stamp()") < html.index("Kedai Runcit Pak Din</h1>")

    def test_the_count_is_left_in_the_dom(self):
        html = apply_hero_video(SITE_A, _settings()).html
        assert "data-binaapp-keep-color-count" in html

    def test_a_tenth_of_a_veil_does_not_keep_its_colour(self):
        # `bg-white/10` is not a background, it is a hint of one: the label on
        # it sits on whatever is behind, so it takes the scrim's colour.
        html = apply_hero_video(SITE_A, _settings()).html
        assert "parseFloat(m[1])>=0.5" in html


class TestStillWellBehaved:
    def test_remove_is_byte_exact(self):
        patched = apply_hero_video(SITE_A, _settings()).html
        assert remove_hero_video(patched).html == SITE_A

    def test_re_applying_changes_nothing(self):
        once = apply_hero_video(SITE_A, _settings()).html
        assert apply_hero_video(once, _settings()).html == once
        assert needs_style_upgrade(once) is False

    def test_the_bare_img_is_still_the_hero_media(self):
        html = apply_hero_video(SITE_A, _settings()).html
        assert ' data-binaapp-hero-media="replaced"' in html

    def test_the_height_floor_survives(self):
        style = _style(apply_hero_video(SITE_A, _settings()).html)
        assert "min-height:max(100vh,600px) !important" in style

    def test_nothing_is_scoped_outside_the_hero(self):
        style = _style(apply_hero_video(SITE_A, _settings()).html)
        assert "#home" not in style
        assert f"[{KEEP_COLOR_ATTR}]" not in style or ":not([" in style


class TestColourTokens:
    def test_tailwind_text_colours(self):
        assert text_tone("text-5xl font-bold text-white") == "light"
        assert text_tone("text-white/80") == "light"
        assert text_tone("text-slate-900") == "dark"
        assert text_tone("text-slate-100") == "light"
        assert text_tone("text-[#0F172A]") == "dark"

    def test_a_size_is_not_a_colour(self):
        assert text_tone("text-5xl text-center text-balance") == ""

    def test_a_breakpoint_or_state_colour_is_not_the_resting_one(self):
        assert text_tone("md:text-white hover:text-black") == ""

    def test_the_middle_of_a_family_states_nothing(self):
        assert text_tone("text-slate-500") == ""

    def test_an_inline_colour_wins(self):
        assert text_tone("text-slate-900", "color:#FFFFFF") == "light"

    def test_gradient_stops_report_the_strongest(self):
        assert tint("bg-gradient-to-b from-black/40 via-black/25 to-black/70") == ("dark", 0.7)
        assert tint("bg-white/30") == ("light", 0.3)
        assert tint("bg-slate-900") == ("dark", 1.0)

    def test_an_inline_gradient_is_read_too(self):
        tone, alpha = tint("", "background:linear-gradient(180deg,rgba(0,0,0,.2),rgba(0,0,0,.65))")
        assert (tone, alpha) == ("dark", 0.65)

    def test_colours_with_no_opinion(self):
        assert tone_of_color("") == ""
        assert tone_of_color("transparent") == ""
        assert tone_of_color("#B0B0B0") == ""  # mid-band: readable either way
        assert tone_of_color("rgb(255,255,255)") == "light"
        assert tone_of_color("#0F172A") == "dark"
