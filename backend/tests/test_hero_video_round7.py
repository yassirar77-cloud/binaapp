"""Round 7 (jojokitchen.binaapp.my — 2026-10-29): the video did not look clear.

What shipped: a light page (`--bg-color:#FAFAF9`, copy `#1C1917`) whose hero
copy is written dark, a mid-tone clip (poster_luminance 0.5), and ``auto``
resolving to a LIGHT scrim — rgba(255,255,255,0.36 → 0.51) laid flat over
the whole frame. Dark copy was readable; the film behind it was a milky
wash. Two fixes, both pinned here:

1. A clip that is not bright gets the DARK gradient even on a light hero,
   and the hero's copy is recoloured light to sit on it (the pattern every
   film hero uses). Bright clips (≥ LIGHT_CLIP_MIN) keep the light scrim,
   which they wear well; unmeasured clips keep the page's own choice.
2. The scrim is SHAPED to the copy's band (`items-end` → heaviest at the
   foot of the hero), so the rest of the frame stays footage.
"""

from app.services.hero_video_patcher import (
    STYLE_ID,
    apply_hero_video,
    build_settings,
    hero_copy_anchor,
    hero_copy_tone,
    scrim_gradient,
)

VIDEO = "https://res.cloudinary.com/d/video/upload/v1/binaapp/hero-videos/jojo.mp4"
POSTER = "https://res.cloudinary.com/d/video/upload/v1/binaapp/hero-videos/jojo.jpg"

#: jojokitchen as it shipped, cut to the parts the scrim reads.
JOJO = (
    "<!DOCTYPE html><html lang=\"ms\"><head>"
    "<style>:root{--bg-color:#FAFAF9;--surface-color:#FFFFFF;--text-color:#1C1917;}"
    "body{background-color:var(--bg-color);color:var(--text-color);}"
    ".hero-scrim{background:linear-gradient(to top,rgba(26,18,16,0.85) 0%,rgba(26,18,16,0.2) 100%);}"
    "</style></head><body class=\"antialiased\">"
    '<header class="sticky top-0 z-50"><nav><a href="#hero">khulafa best onwe</a></nav></header>'
    "<main>"
    '<section class="relative min-h-[70vh] md:min-h-[80vh] flex items-end overflow-hidden" id="hero">'
    '<div class="absolute inset-0">'
    '<img alt="" class="w-full h-full object-cover" src="https://res.cloudinary.com/d/image/upload/v1/binaapp/ruzmtx.jpg">'
    '<div class="absolute inset-0 hero-scrim"></div>'
    "</div>"
    '<div class="relative z-10 max-w-6xl mx-auto px-4 pb-16 md:pb-24 pt-32 w-full">'
    '<h1 class="text-[#1C1917] mb-4 max-w-3xl">Kari Masak Kepala Pari Ikan</h1>'
    '<p class="text-[#1C1917] text-lg">Kedai mamak terkenal sejak 1988.</p>'
    '<a class="btn-whatsapp px-6 py-3 rounded-full" href="https://wa.me/60176119872">Pesan di WhatsApp</a>'
    '<a class="btn-outline-light px-6 py-3 rounded-full text-[#1C1917]" href="#menu">Lihat menu</a>'
    "</div></section>"
    '<section class="py-16" id="menu"><h2>Menu</h2></section>'
    "</main><footer>khulafa best onwe</footer></body></html>"
)


def _settings(**kw):
    base = {"video_url": VIDEO, "poster_url": POSTER, "poster_luminance": 0.5}
    base.update(kw)
    return build_settings(**base)


def _style(html):
    i = html.index(f'<style id="{STYLE_ID}">')
    return html[i:html.index("</style>", i)]


class TestTheClipOverrulesALightHero:
    def test_what_shipped_is_read_as_a_light_hero(self):
        assert hero_copy_tone(JOJO) == "dark"

    def test_a_mid_tone_clip_gets_the_dark_gradient_not_a_white_wash(self):
        settings = _settings()
        assert settings.clip_needs_dark_scrim()
        assert settings.resolved_overlay(JOJO) == "dark"
        style = _style(apply_hero_video(JOJO, settings).html)
        assert "rgba(255,255,255," not in style
        assert "rgba(0,0,0," in style

    def test_the_dark_copy_is_made_light_to_sit_on_it(self):
        settings = _settings()
        assert settings.resolved_text_mode(JOJO) == "light"
        style = _style(apply_hero_video(JOJO, settings).html)
        assert "color:#FFFFFF !important" in style
        assert "text-shadow" in style

    def test_a_dark_clip_is_treated_the_same(self):
        assert _settings(poster_luminance=0.2).resolved_overlay(JOJO) == "dark"
        assert _settings(poster_luminance=0.2).resolved_text_mode(JOJO) == "light"

    def test_a_bright_clip_keeps_the_light_scrim_and_the_copy_it_was_written_with(self):
        settings = _settings(poster_luminance=0.85)
        assert not settings.clip_needs_dark_scrim()
        assert settings.resolved_overlay(JOJO) == "light"
        assert settings.resolved_text_mode(JOJO) == "keep"
        style = _style(apply_hero_video(JOJO, settings).html)
        assert "color:#FFFFFF !important" not in style

    def test_an_unmeasured_clip_changes_nothing(self):
        settings = _settings(poster_luminance=None)
        assert settings.resolved_overlay(JOJO) == "light"
        assert settings.resolved_text_mode(JOJO) == "keep"

    def test_a_merchants_explicit_light_scrim_is_still_theirs(self):
        settings = _settings(overlay="light")
        assert settings.resolved_overlay(JOJO) == "light"
        assert settings.resolved_text_mode(JOJO) == "keep"

    def test_a_merchants_explicit_keep_is_honoured_even_under_the_dark_gradient(self):
        settings = _settings(text_mode="keep")
        assert settings.resolved_overlay(JOJO) == "dark"
        assert "color:#FFFFFF !important" not in _style(apply_hero_video(JOJO, settings).html)

    def test_a_dark_hero_is_untouched_by_the_rule(self):
        # mimk-shaped: white copy on a dark page. Dark scrim, copy kept.
        dark = JOJO.replace("#FAFAF9", "#141518").replace("#1C1917", "#F5F3EE")
        settings = _settings()
        assert settings.resolved_overlay(dark) == "dark"
        assert settings.resolved_text_mode(dark) == "keep"

    def test_round_trips_through_detect_and_reapply(self):
        from app.services.hero_video_patcher import detect_hero_video, needs_style_upgrade

        once = apply_hero_video(JOJO, _settings()).html
        state = detect_hero_video(once)
        assert state["poster_luminance"] == 0.5 and state["overlay"] == "auto"
        assert not needs_style_upgrade(once)
        twice = apply_hero_video(once, build_settings(**state)).html
        assert twice == once


class TestTheScrimIsShapedToTheCopy:
    def test_items_end_puts_the_weight_at_the_foot(self):
        assert hero_copy_anchor(JOJO) == "bottom"
        style = _style(apply_hero_video(JOJO, _settings()).html)
        # 0.54 is what the luminance map asks for at 0.5; the foot gets it
        # plus the lift, the head of the frame a third of it.
        assert scrim_gradient("dark", 0.54, "bottom") in style
        assert "rgba(0,0,0,0.16) 0%" in style
        assert "rgba(0,0,0,0.74) 100%" in style

    def test_items_center_weights_the_middle(self):
        centred = JOJO.replace("flex items-end", "flex items-center")
        assert hero_copy_anchor(centred) == "center"
        assert scrim_gradient("dark", 0.54, "center") in _style(apply_hero_video(centred, _settings()).html)

    def test_items_start_weights_the_head(self):
        top = JOJO.replace("flex items-end", "flex items-start")
        assert hero_copy_anchor(top) == "top"
        g = scrim_gradient("dark", 0.54, "top")
        assert g.startswith("linear-gradient(180deg,rgba(0,0,0,0.74) 0%")

    def test_a_hero_that_states_nothing_is_centred(self):
        quiet = JOJO.replace("flex items-end", "block")
        assert hero_copy_anchor(quiet) == "center"

    def test_the_shape_reads_the_content_wrapper_too(self):
        moved = JOJO.replace("flex items-end", "grid").replace(
            'class="relative z-10 max-w-6xl', 'class="self-end relative z-10 max-w-6xl'
        )
        assert hero_copy_anchor(moved) == "bottom"

    def test_the_gradient_never_goes_opaque(self):
        assert "0.92) 50%" in scrim_gradient("dark", 0.9, "center")
        assert "rgba(255,255,255,0.92) 100%" in scrim_gradient("light", 0.95, "bottom")

    def test_every_stop_is_at_or_below_the_band(self):
        g = scrim_gradient("dark", 0.5, "bottom")
        assert g == "linear-gradient(180deg,rgba(0,0,0,0.15) 0%,rgba(0,0,0,0.3) 45%,rgba(0,0,0,0.7) 100%)"
