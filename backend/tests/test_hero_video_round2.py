"""Round 2 (maka.binaapp.my): a split hero keeps its split.

The first fix hid the hero's <img>; its wrapper — position:relative, an
opaque cream background, a reserved 50% column — survived and covered half
the full-bleed clip. And even with the wrapper gone, a full-bleed clip is
the wrong geometry for a hero the merchant asked to be split: text over
the left half, a dead right column.

So when the media sits in a plain wrapper occupying its own region, the
clip is HOSTED in that wrapper and replaces the photo in place (option (a)
from the report). No scrim there, no text recolouring: nothing of the
merchant's sits on top of it. The full-bleed path is unchanged for
full-cover media, and gains the inline-text and ghost-button rules, a
page-aware ``auto`` overlay, and a probe that counts a large opaque block
as a cover.
"""

from app.services.hero_video_patcher import (
    BLOCK_START,
    DEFAULT_OVERLAY,
    HERO_MEDIA_ATTR,
    OVERLAY_MODES,
    STYLE_ID,
    apply_hero_video,
    build_settings,
    detect_hero_video,
    find_hero_media,
    needs_style_upgrade,
    remove_hero_video,
)
from app.services import hero_video_patcher as hp

IMG = "https://res.cloudinary.com/dx/image/upload/v1789228300/binaapp/butik.jpg"
HOST_TAG = f' {HERO_MEDIA_ATTR}="host"'
REPLACED_TAG = f' {HERO_MEDIA_ATTR}="replaced"'

# maka's hero as generated: light page, split hero, photo in a 50% column.
MAKA = (
    "<html><head><style>:root{--bg-color:#FAF8F3;--surface-color:#F5F2EB;"
    "--text-color:#2A2A24}</style></head><body>"
    '<section class="hero-split flex" id="home">'
    '<div class="flex-1 hero-text"><h1>Butik Nurin Kasturi</h1>'
    '<span class="text-sm text-[#7A7A6E]">Bandar Baru Bangi</span>'
    '<a class="px-5 py-3 text-[#2A2A24] border border-[#B89B6E]">Lihat Koleksi</a>'
    '<a class="bg-[#25D366] text-white px-5">WhatsApp</a></div>'
    '<div class="hero-image-container relative overflow-hidden bg-[#F5F2EB]" data-aos="fade-left">'
    f'<img src="{IMG}" class="w-full h-full object-cover" alt="model"></div>'
    '</section><section id="koleksi"><h2>Koleksi</h2></section></body></html>'
)

# soon's hero: full-cover photo wrapper on a dark page.
SOON = (
    "<html><head><style>:root{--bg-color:#111111}</style></head><body>"
    '<section class="relative min-h-screen"><div class="absolute inset-0">'
    f'<img src="{IMG}" class="object-cover"></div>'
    '<div class="relative z-10"><h1>Soon</h1><span class="text-[#777]">x</span>'
    '<a class="border-[#fff]">Ghost</a><a class="bg-[#25D366]">WA</a></div>'
    "</section></body></html>"
)


def _settings(**overrides):
    kwargs = {"video_url": "https://v.test/a.mp4", "poster_url": "https://v.test/a.jpg"}
    kwargs.update(overrides)
    return build_settings(**kwargs)


def _style(html):
    start = html.index(f'<style id="{STYLE_ID}">')
    return html[start:html.index("</style>", start)]


class TestHostedInTheMediaColumn:
    def test_the_layer_lands_inside_the_column_before_the_photo(self):
        html = apply_hero_video(MAKA, _settings()).html
        host = html.index('class="hero-image-container')
        layer = html.index(BLOCK_START)
        img = html.index("<img src=")
        assert host < layer < img
        # …and NOT as the hero's first child.
        assert layer > html.index("<h1>")

    def test_column_and_photo_are_both_stamped(self):
        html = apply_hero_video(MAKA, _settings()).html
        assert html.count(HOST_TAG) == 1 and html.count(REPLACED_TAG) == 1
        assert HOST_TAG in html[html.index('class="hero-image-container'):html.index(BLOCK_START)]

    def test_the_text_column_is_untouched(self):
        html = apply_hero_video(MAKA, _settings()).html
        assert HOST_TAG not in html[:html.index('class="hero-image-container')]

    def test_host_rules_position_the_clip_in_the_column(self):
        style = _style(apply_hero_video(MAKA, _settings()).html)
        assert '[data-binaapp-hero-media="host"]{position:relative;overflow:hidden;}' in style
        assert '[data-binaapp-hero-media="host"] > .binaapp-hero-video-layer{position:absolute;inset:0;z-index:0;' in style

    def test_no_scrim_and_no_text_recolour_when_hosted(self):
        # The merchant's copy is on the page background, not over the clip.
        style = _style(apply_hero_video(MAKA, _settings()).html)
        assert '.binaapp-hero-video-scrim{display:none;}' in style
        assert "color:#FFFFFF !important" not in style
        assert "color:#0F172A !important" not in style

    def test_reported_in_notes(self):
        notes = apply_hero_video(MAKA, _settings()).notes
        assert "layer_hosted_in_media_column" in notes and "hero_media_replaced:1" in notes

    def test_remove_restores_the_exact_original_bytes(self):
        assert remove_hero_video(apply_hero_video(MAKA, _settings()).html).html == MAKA

    def test_idempotent(self):
        once = apply_hero_video(MAKA, _settings()).html
        assert apply_hero_video(once, _settings()).html == once

    def test_the_page_maka_serves_today_is_upgraded(self):
        # Round-1 output: full-bleed layer as the hero's first child, <img>
        # stamped, wrapper untouched. Must be detected as stale.
        base = MAKA.replace('<section class="hero-split flex" id="home">',
                            '<section class="hero-split flex" id="home" data-binaapp-hero-video="1">')
        i = base.index('data-binaapp-hero-video="1">') + len('data-binaapp-hero-video="1">')
        legacy = base[:i] + hp._build_layer(_settings()) + base[i:]
        legacy = legacy.replace('class="w-full h-full object-cover" alt="model">',
                                f'class="w-full h-full object-cover" alt="model"{REPLACED_TAG}>')
        assert needs_style_upgrade(legacy) is True
        healed = apply_hero_video(legacy, build_settings(**detect_hero_video(legacy))).html
        assert healed.count(HOST_TAG) == 1

    def test_find_hero_media_reports_the_host(self):
        found = find_hero_media(MAKA, MAKA.index("<section"))
        assert len(found) == 1
        _start, _end, host = found[0]
        assert host is not None
        assert MAKA[host[0]:].startswith('<div class="hero-image-container')

    def test_a_column_with_copy_in_it_is_not_a_host(self):
        page = MAKA.replace('alt="model"></div>', 'alt="model"><p>Koleksi baru</p></div>')
        result = apply_hero_video(page, _settings())
        assert HOST_TAG not in result.html
        assert "layer_hosted_in_media_column" not in result.notes

    def test_two_media_columns_fall_back_to_full_bleed(self):
        page = MAKA.replace(
            "</section><section id=", (
                '<div class="hero-image-container relative overflow-hidden">'
                f'<img src="{IMG}" class="w-full h-full object-cover"></div>'
                "</section><section id="
            ), 1)
        result = apply_hero_video(page, _settings())
        assert HOST_TAG not in result.html
        assert result.html.count(REPLACED_TAG) == 2
        assert result.html.index(BLOCK_START) < result.html.index("<h1>")


class TestOverlayAuto:
    def test_auto_is_the_default_and_a_valid_mode(self):
        assert DEFAULT_OVERLAY == "auto" and "auto" in OVERLAY_MODES
        assert build_settings(video_url="https://v.test/a.mp4").overlay == "auto"

    def test_light_page_gets_light_scrim_and_dark_text(self):
        light = SOON.replace("#111111", "#FAF8F3")
        style = _style(apply_hero_video(light, _settings()).html)
        assert "rgba(255,255,255," in style and "color:#0F172A !important" in style
        assert "rgba(0,0,0," not in style

    def test_dark_page_gets_dark_scrim_and_light_text(self):
        style = _style(apply_hero_video(SOON, _settings()).html)
        assert "rgba(0,0,0," in style and "color:#FFFFFF !important" in style

    def test_an_explicit_pick_beats_the_page(self):
        light = SOON.replace("#111111", "#FAF8F3")
        style = _style(apply_hero_video(light, _settings(overlay="dark")).html)
        assert "rgba(0,0,0," in style

    def test_auto_round_trips_through_detect(self):
        html = apply_hero_video(SOON, _settings()).html
        assert detect_hero_video(html)["overlay"] == "auto"
        assert build_settings(**detect_hero_video(html)).overlay == "auto"

    def test_unknown_page_resolves_dark(self):
        assert _settings().resolved_overlay("") == "dark"


class TestFullBleedTextRules:
    def test_inline_text_is_recoloured_unless_it_paints_a_background(self):
        style = _style(apply_hero_video(SOON, _settings()).html)
        assert 'span:not([class*="bg-"]):not([style*="background"])' in style
        assert 'a:not([class*="bg-"]):not([style*="background"])' in style

    def test_ghost_buttons_take_the_text_colour_for_their_border(self):
        style = _style(apply_hero_video(SOON, _settings()).html)
        assert 'a[class*="border-"]:not([class*="bg-"])' in style
        assert "border-color:currentColor !important" in style

    def test_text_mode_keep_still_recolours_nothing(self):
        style = _style(apply_hero_video(SOON, _settings(text_mode="keep")).html)
        assert "color:" not in style.replace("background-color", "").replace("border-color", "")


class TestProbeCountsOpaqueBlocks:
    def test_a_large_opaque_background_colour_is_a_cover(self):
        html = apply_hero_video(MAKA, _settings()).html
        assert "cs.backgroundColor" in html
        assert "parseFloat(m[1])>=0.9" in html
        # …but only when it spans most of the frame: a badge is design.
        assert "b.width*b.height>=0.4*r.width*r.height" in html
