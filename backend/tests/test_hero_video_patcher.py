"""Tests for the hero video background HTML patch.

The patch is a credit-free, deterministic string edit, so the properties
that matter are the theme_patcher ones: finds the hero the generator emits,
adds ONLY its own markup, is idempotent under re-apply, removes itself
byte-exactly, and never lets a URL break out of an attribute.
"""

import pytest

from app.services.hero_video_patcher import (
    BLOCK_END,
    BLOCK_START,
    HERO_MARKER_ATTR,
    LEGACY_CHILD_RULE,
    STYLE_ID,
    apply_hero_video,
    build_settings,
    detect_hero_video,
    find_hero_open_tag,
    needs_style_upgrade,
    remove_hero_video,
)

VIDEO = "https://res.cloudinary.com/demo/video/upload/q_auto:eco,w_1280,c_limit,ac_none/v1/binaapp/hero-videos/ws-1-abc.mp4"
POSTER = "https://res.cloudinary.com/demo/video/upload/v1/binaapp/hero-videos/ws-1-abc.jpg"

TEMPLATE_PAGE = (
    "<!DOCTYPE html><html><head><title>Kedai Ali</title>"
    "<style>:root{--primary-color:#EA580C}</style></head>"
    "<body>"
    '<header class="fixed top-0"><nav><a href="#home">Utama</a></nav></header>'
    '<section id="home" class="pt-32 min-h-screen flex items-center bg-gradient-to-br">'
    '<div class="max-w-7xl relative z-10"><h1 class="text-[#0F172A]">Kedai Ali</h1>'
    "<p>Nasi lemak terbaik</p>"
    '<a href="#menu" class="bg-[#EA580C] text-white">Pesan</a></div>'
    "</section>"
    '<section id="menu"><h2>Menu</h2></section>'
    "<footer>foot</footer></body></html>"
)

GENERATED_PAGE = (
    "<html><head></head><body>"
    "<nav>nav</nav>"
    '<section class="hero-section relative overflow-hidden"><h1>Hai</h1></section>'
    "<section><h2>Tentang</h2></section>"
    "</body></html>"
)

NO_ID_PAGE = (
    "<html><head></head><body><div>wrap"
    "<section><h1>First</h1></section><section><h2>Second</h2></section>"
    "</div></body></html>"
)


def _settings(**overrides):
    kwargs = {"video_url": VIDEO, "poster_url": POSTER}
    kwargs.update(overrides)
    return build_settings(**kwargs)


class TestFindHero:
    def test_id_home_wins(self):
        match, how = find_hero_open_tag(TEMPLATE_PAGE)
        assert how == "id"
        assert 'id="home"' in match.group(0)

    def test_hero_class_is_second_choice(self):
        match, how = find_hero_open_tag(GENERATED_PAGE)
        assert how == "class"
        assert "hero-section" in match.group(0)

    def test_first_section_is_the_fallback(self):
        match, how = find_hero_open_tag(NO_ID_PAGE)
        assert how == "first-section"
        assert "<h1>First</h1>" in NO_ID_PAGE[match.end():match.end() + 20]

    def test_nothing_to_match(self):
        match, how = find_hero_open_tag("<html><body><p>hi</p></body></html>")
        assert match is None and how == ""

    def test_a_hero_id_inside_head_is_ignored(self):
        # The search starts at <body>; a style hook in <head> must not win.
        html = '<html><head><style>#home{}</style></head><body><section id="home">x</section></body></html>'
        match, how = find_hero_open_tag(html)
        assert how == "id"
        assert match.start() > html.index("<body")


class TestApply:
    def test_injects_layer_style_and_marker(self):
        result = apply_hero_video(TEMPLATE_PAGE, _settings())
        assert result.changed and result.hero_match == "id"
        html = result.html
        assert f'<section id="home" class="pt-32 min-h-screen flex items-center bg-gradient-to-br" {HERO_MARKER_ATTR}="1">' in html
        assert html.count(BLOCK_START) == 1 and html.count(BLOCK_END) == 1
        assert html.count(f'id="{STYLE_ID}"') == 1
        # Style lands in <head>, the layer is the hero's FIRST child.
        assert html.index(STYLE_ID) < html.index("<body")
        assert html.index(BLOCK_START) < html.index("<h1")

    def test_video_element_shape_is_autoplay_safe(self):
        html = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        video_tag = html[html.index("<video"):html.index("</video>")]
        for attr in ("autoplay", "muted", "loop", "playsinline", 'preload="auto"', 'tabindex="-1"'):
            assert attr in video_tag
        assert f'<source src="{VIDEO}" type="video/mp4">' in video_tag
        assert f'poster="{POSTER}"' in video_tag
        assert 'aria-hidden="true"' in html[html.index(BLOCK_START):html.index(BLOCK_END)]

    def test_merchant_markup_is_untouched(self):
        html = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        for fragment in (
            '<h1 class="text-[#0F172A]">Kedai Ali</h1>',
            "<p>Nasi lemak terbaik</p>",
            '<a href="#menu" class="bg-[#EA580C] text-white">Pesan</a>',
            '<section id="menu"><h2>Menu</h2></section>',
            "<footer>foot</footer>",
        ):
            assert fragment in html

    def test_css_is_scoped_to_the_marker_only(self):
        html = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        style = html[html.index(f'<style id="{STYLE_ID}">'):html.index("</style>", html.index(STYLE_ID))]
        assert f"[{HERO_MARKER_ATTR}]" in style
        # Never depends on the merchant's ids or classes.
        assert "#home" not in style and ".pt-32" not in style
        assert "prefers-reduced-motion" in style
        # Dark overlay → light text on headings/paragraphs (auto mode).
        assert "color:#FFFFFF !important" in style

    def test_light_overlay_flips_text_dark_and_none_keeps(self):
        light = apply_hero_video(TEMPLATE_PAGE, _settings(overlay="light")).html
        assert "color:#0F172A !important" in light
        assert "rgba(255,255,255,0.45)" in light
        none = apply_hero_video(TEMPLATE_PAGE, _settings(overlay="none")).html
        assert "!important" not in none[none.index(STYLE_ID):none.index("</style>")]
        assert "background:transparent" in none

    def test_explicit_text_mode_keep_never_forces_colour(self):
        html = apply_hero_video(TEMPLATE_PAGE, _settings(text_mode="keep")).html
        assert "!important" not in html

    def test_poster_only_on_mobile_adds_media_query(self):
        html = apply_hero_video(TEMPLATE_PAGE, _settings(show_on_mobile=False)).html
        assert "@media (max-width:640px)" in html
        assert 'data-binaapp-mobile="poster"' in html
        default = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        assert "@media (max-width:640px)" not in default

    def test_works_on_generated_page_with_hero_class(self):
        result = apply_hero_video(GENERATED_PAGE, _settings())
        assert result.changed and result.hero_match == "class"
        assert f'class="hero-section relative overflow-hidden" {HERO_MARKER_ATTR}="1"' in result.html

    def test_no_head_inlines_the_style_before_the_layer(self):
        fragment = '<section id="home"><h1>x</h1></section>'
        result = apply_hero_video(fragment, _settings())
        assert result.changed
        assert "style_inlined_without_head" in result.notes
        assert result.html.index(STYLE_ID) < result.html.index(BLOCK_START)

    def test_missing_hero_changes_nothing(self):
        result = apply_hero_video("<html><body><p>hi</p></body></html>", _settings())
        assert not result.changed and "hero_not_found" in result.notes
        assert result.html == "<html><body><p>hi</p></body></html>"

    def test_empty_html_changes_nothing(self):
        assert not apply_hero_video("", _settings()).changed


class TestIdempotence:
    def test_reapply_replaces_rather_than_stacks(self):
        once = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        twice = apply_hero_video(once, _settings(overlay="light", overlay_opacity=0.3)).html
        assert twice.count(BLOCK_START) == 1
        assert twice.count(STYLE_ID) == 1
        assert twice.count(f'{HERO_MARKER_ATTR}="1"') == 1
        assert 'data-binaapp-overlay="light"' in twice
        assert 'data-binaapp-overlay="dark"' not in twice

    def test_same_settings_twice_is_a_fixed_point(self):
        once = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        again = apply_hero_video(once, _settings()).html
        assert once == again

    def test_remove_restores_the_exact_original_bytes(self):
        patched = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        restored = remove_hero_video(patched)
        assert restored.changed
        assert restored.html == TEMPLATE_PAGE

    def test_remove_on_a_clean_page_is_a_noop(self):
        result = remove_hero_video(TEMPLATE_PAGE)
        assert not result.changed and result.html == TEMPLATE_PAGE


class TestDetect:
    def test_reads_back_what_was_written(self):
        patched = apply_hero_video(
            TEMPLATE_PAGE,
            _settings(overlay="light", overlay_opacity=0.25, text_mode="keep", show_on_mobile=False),
        ).html
        state = detect_hero_video(patched)
        assert state == {
            "video_url": VIDEO,
            "poster_url": POSTER,
            "overlay": "light",
            "overlay_opacity": 0.25,
            "text_mode": "keep",
            "show_on_mobile": False,
        }

    def test_clean_page_has_no_video(self):
        assert detect_hero_video(TEMPLATE_PAGE) is None
        assert detect_hero_video("") is None

    def test_poster_is_optional(self):
        patched = apply_hero_video(TEMPLATE_PAGE, build_settings(video_url=VIDEO)).html
        assert "poster=" not in patched
        assert detect_hero_video(patched)["poster_url"] is None


class TestSettingsValidation:
    def test_rejects_non_https_video(self):
        for bad in ("http://x/y.mp4", "javascript:alert(1)", "", '  https://x/"onload="'):
            with pytest.raises(ValueError):
                build_settings(video_url=bad)

    def test_bad_poster_is_dropped_not_fatal(self):
        s = build_settings(video_url=VIDEO, poster_url='https://x/"><script>')
        assert s.poster_url is None

    def test_unknown_modes_fall_back_to_defaults(self):
        s = build_settings(video_url=VIDEO, overlay="neon", text_mode="rainbow", overlay_opacity=7)
        assert s.overlay == "dark" and s.text_mode == "auto" and s.overlay_opacity == 0.9

    def test_url_is_escaped_in_attributes(self):
        url = "https://res.cloudinary.com/x/v.mp4?a=1&b=2"
        html = apply_hero_video(TEMPLATE_PAGE, build_settings(video_url=url)).html
        assert 'data-binaapp-video-url="https://res.cloudinary.com/x/v.mp4?a=1&amp;b=2"' in html
        assert detect_hero_video(html)["video_url"] == url

    def test_output_stays_balanced(self):
        from app.utils.html_balance import is_html_balanced

        html = apply_hero_video(TEMPLATE_PAGE, _settings()).html
        assert is_html_balanced(html)[0]


# ---------------------------------------------------------------------------
# Stacking: the layer sits BELOW the hero's children without restyling them
# ---------------------------------------------------------------------------

# A hero in the shape the generator actually emits for premium designs:
# absolutely-positioned decorative layers (a dot grid, two blurred blobs)
# ahead of the real content. The first release forced these to
# position:relative, which turned the blobs into in-flow 480px/280px blocks
# and pushed the headline below the fold.
DECORATED_HERO_HTML = (
    "<!DOCTYPE html><html><head><title>Kedai Emas</title></head><body>"
    '<section id="home" class="relative overflow-hidden bg-charcoal">'
    '<div aria-hidden="true" class="absolute inset-0 bg-dot-grid opacity-60"></div>'
    '<div aria-hidden="true" class="absolute -top-40 right-[-10%] w-[480px] h-[480px] blur-3xl"></div>'
    '<div class="relative max-w-7xl mx-auto"><h1>Keindahan Emas</h1><p>Damansara</p></div>'
    "</section><footer>foot</footer></body></html>"
)


def _style_of(html: str) -> str:
    start = html.index(f'<style id="{STYLE_ID}">')
    return html[start:html.index("</style>", start)]


class TestStackingKeepsChildrenUntouched:
    def test_layer_sits_at_negative_z_inside_an_isolated_hero(self):
        html = apply_hero_video(DECORATED_HERO_HTML, _settings()).html
        style = _style_of(html)
        assert f"[{HERO_MARKER_ATTR}]{{position:relative;isolation:isolate;overflow:hidden;}}" in style
        assert "binaapp-hero-video-layer{position:absolute;inset:0;z-index:-1;" in style

    def test_no_rule_targets_the_heros_children(self):
        html = apply_hero_video(DECORATED_HERO_HTML, _settings()).html
        style = _style_of(html)
        assert LEGACY_CHILD_RULE not in style
        assert "> *:not(" not in style
        # The decorative markup itself is byte-identical.
        assert 'class="absolute inset-0 bg-dot-grid opacity-60"' in html
        assert 'class="absolute -top-40 right-[-10%] w-[480px] h-[480px] blur-3xl"' in html

    def test_fresh_output_needs_no_upgrade(self):
        html = apply_hero_video(DECORATED_HERO_HTML, _settings()).html
        assert needs_style_upgrade(html) is False

    def test_clean_page_needs_no_upgrade(self):
        assert needs_style_upgrade(DECORATED_HERO_HTML) is False
        assert needs_style_upgrade("") is False

    def test_legacy_page_is_detected_and_reapply_clears_it(self):
        fresh = apply_hero_video(DECORATED_HERO_HTML, _settings()).html
        # Splice the first release's rule into the page's own style block.
        legacy = fresh.replace("</style>", LEGACY_CHILD_RULE + "</style>", 1)
        assert needs_style_upgrade(legacy) is True

        current = detect_hero_video(legacy)
        assert current and current["video_url"] == _settings().video_url
        upgraded = apply_hero_video(legacy, build_settings(**current)).html
        assert needs_style_upgrade(upgraded) is False
        assert LEGACY_CHILD_RULE not in upgraded
        assert upgraded == fresh

    def test_legacy_rule_outside_our_style_block_is_not_ours(self):
        # A merchant stylesheet that happens to contain the text is not a
        # reason to rewrite their page.
        html = DECORATED_HERO_HTML.replace(
            "</head>", "<style>" + LEGACY_CHILD_RULE + "</style></head>", 1
        )
        assert needs_style_upgrade(html) is False


class TestPlaybackBootstrap:
    def test_layer_carries_the_bootstrap_inside_the_fence(self):
        html = apply_hero_video(DECORATED_HERO_HTML, _settings()).html
        block = html[html.index(BLOCK_START):html.index(BLOCK_END)]
        assert "<script>" in block and "v.play()" in block
        assert "prefers-reduced-motion" in block
        assert "data-binaapp-video-playing" in block
        assert 'preload="auto"' in block
        # One script per page, and nothing of it survives removal.
        assert html.count("v.play()") == 1
        assert remove_hero_video(html).html == DECORATED_HERO_HTML

    def test_bootstrap_never_touches_merchant_scripts(self):
        page = DECORATED_HERO_HTML.replace("</body>", "<script>AOS.init()</script></body>")
        html = apply_hero_video(page, _settings()).html
        assert "AOS.init()" in html
        assert remove_hero_video(html).html == page

    def test_block_without_the_bootstrap_needs_an_upgrade(self):
        fresh = apply_hero_video(DECORATED_HERO_HTML, _settings()).html
        start = fresh.index("<script>", fresh.index(BLOCK_START))
        end = fresh.index("</script>", start) + len("</script>")
        older = fresh[:start] + fresh[end:]
        assert needs_style_upgrade(older) is True
        current = detect_hero_video(older)
        upgraded = apply_hero_video(older, build_settings(**current)).html
        assert needs_style_upgrade(upgraded) is False
        assert upgraded == fresh



# ── delivery URL ─────────────────────────────────────────────────────────────
# Regression: wan3.0-video returned a 12.9 MB, 20.7 Mbit/s clip for a
# five-second hero. Every visitor downloaded it before a frame moved; on a
# phone the hero sat on the poster (the merchant's own photo) for the whole
# visit, and the merchant reported "no video". The same asset through
# Cloudinary's delivery transform is ~620 KB.

from app.services.hero_video_patcher import (  # noqa: E402
    HERO_VIDEO_DELIVERY_TRANSFORM,
    hero_video_delivery_url,
)

RAW = "https://res.cloudinary.com/demo/video/upload/v1789037467/binaapp/hero-videos/ws-1-af.mp4"
SLIM = f"https://res.cloudinary.com/demo/video/upload/{HERO_VIDEO_DELIVERY_TRANSFORM}/v1789037467/binaapp/hero-videos/ws-1-af.mp4"


class TestDeliveryUrl:
    def test_inserts_the_transform_after_video_upload(self):
        assert hero_video_delivery_url(RAW) == SLIM
        assert HERO_VIDEO_DELIVERY_TRANSFORM == "q_auto:eco,w_1280,c_limit,ac_none"

    def test_idempotent(self):
        assert hero_video_delivery_url(SLIM) == SLIM
        already = "https://res.cloudinary.com/demo/video/upload/w_640,q_auto/v1/a/b.mp4"
        assert hero_video_delivery_url(already) == already

    def test_versionless_folder_first_url_is_still_transformed(self):
        url = "https://res.cloudinary.com/demo/video/upload/binaapp/hero-videos/x.mp4"
        assert hero_video_delivery_url(url) == (
            f"https://res.cloudinary.com/demo/video/upload/{HERO_VIDEO_DELIVERY_TRANSFORM}/binaapp/hero-videos/x.mp4"
        )

    def test_leaves_everything_else_alone(self):
        for url in (
            "https://res.cloudinary.com/demo/image/upload/v1/binaapp/user_uploads/p.jpg",
            "https://res.cloudinary.com/x/v.mp4?a=1&b=2",
            "https://cdn.example.com/video/upload/v1/clip.mp4",
            "",
            None,
        ):
            assert hero_video_delivery_url(url) == url

    def test_build_settings_normalises_the_video_url(self):
        assert build_settings(video_url=RAW).video_url == SLIM
        # And embeds the slim URL, so a look tweak on an old page upgrades it.
        html = apply_hero_video(TEMPLATE_PAGE, build_settings(video_url=RAW)).html
        assert SLIM in html and RAW not in html
