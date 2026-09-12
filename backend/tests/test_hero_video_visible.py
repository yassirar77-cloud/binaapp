"""The hero video must be SEEN, not merely playing.

soon.binaapp.my: the clip was generated, injected and reported playing, and
the visitor saw a still image. The injected layer sits at z-index:-1 inside
the hero's own stacking context — which paints it below any POSITIONED
sibling with z-index:auto, and the generator makes the hero's photo exactly
that: ``<div class="absolute inset-0"><img …></div>``. The rules meant to
hide that photo keyed on the POSTER url, so they matched nothing.

The fix is structural: find the hero's full-cover media at injection time,
stamp it, hide it with one static rule. z-index:-1 stays — it is what keeps
the clip under in-flow copy the generator never positioned, and the
alternative (force every child to position:relative) is the reverted
LEGACY_CHILD_RULE that pushed hero copy off-screen.
"""

from app.services.hero_video_patcher import (
    HERO_MARKER_ATTR,
    HERO_MEDIA_ATTR,
    STYLE_ID,
    apply_hero_video,
    build_settings,
    cloudinary_public_id,
    detect_hero_video,
    ensure_hero_id,
    find_hero_media,
    needs_style_upgrade,
    remove_hero_video,
)

VIDEO = "https://res.cloudinary.com/dx/video/upload/q_auto:eco,w_1280,c_limit,ac_none/v1789223622/binaapp/hero-videos/f628155182d64764bbe8715153cd4d31-7684234a.mp4"
POSTER = "https://res.cloudinary.com/dx/video/upload/f_auto,q_auto,c_limit,w_1920/v1789223622/binaapp/hero-videos/f628155182d64764bbe8715153cd4d31-7684234a.jpg"
HERO_IMG = "https://res.cloudinary.com/dx/image/upload/f_auto,q_auto,c_limit,w_1920/v1789223430/binaapp/oooz0uilzwo8xkchc478.jpg"

#: The attribute as it appears IN A TAG. The bare name also appears inside
#: the injected <style> rule, so ``HERO_MEDIA_ATTR in html`` proves nothing.
TAG = f' {HERO_MEDIA_ATTR}="replaced"'
HIDE_RULE = f'[{HERO_MARKER_ATTR}] [{HERO_MEDIA_ATTR}="replaced"]{{display:none !important;}}'

# The served hero from the report, as generated (pre-injection).
SOON = (
    "<html><head><title>Soon</title></head><body>"
    '<section class="relative min-h-screen flex items-end overflow-hidden">'
    '<div class="absolute inset-0 overflow-hidden">'
    f'<img class="w-full h-full object-cover hero-slow-zoom" src="{HERO_IMG}" '
    'style="filter: brightness(0.55) saturate(1.1) contrast(1.05);">'
    '<div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-black/30"></div>'
    "</div>"
    '<div class="relative z-10 max-w-7xl"><h1>Soon</h1>'
    '<a href="https://wa.me/60193456781">WhatsApp</a></div>'
    "</section>"
    f'<section id="menu"><img src="{HERO_IMG}" class="w-full h-full object-cover"><h2>Menu</h2></section>'
    "</body></html>"
)


def _settings(**overrides):
    kwargs = {"video_url": VIDEO, "poster_url": POSTER}
    kwargs.update(overrides)
    return build_settings(**kwargs)


def _style(html):
    start = html.index(f'<style id="{STYLE_ID}">')
    return html[start:html.index("</style>", start)]


class TestReportedPage:
    """Test 1 from the report: a hero with its own <img> background."""

    def test_the_photo_wrapper_is_tagged_and_nothing_else(self):
        out = apply_hero_video(SOON, _settings()).html
        assert out.count(TAG) == 1
        assert f'<div class="absolute inset-0 overflow-hidden"{TAG}>' in out

    def test_the_gallery_copy_of_the_same_photo_is_left_alone(self):
        out = apply_hero_video(SOON, _settings()).html
        assert TAG not in out[out.index('id="menu"'):]

    def test_one_static_rule_hides_it(self):
        assert HIDE_RULE in _style(apply_hero_video(SOON, _settings()).html)

    def test_the_hide_rule_does_not_depend_on_any_url(self):
        # Cloudinary rewrites the transformation segment at delivery; the
        # rule that finally works must not care.
        rule = HIDE_RULE
        assert "res.cloudinary.com" not in rule and "http" not in rule

    def test_the_layer_stays_at_negative_z(self):
        # NOT fix A from the report: z-index:0 plus forcing children to
        # position:relative is LEGACY_CHILD_RULE, reverted for pushing
        # hero copy off-screen. With the photo hidden, -1 is correct.
        style = _style(apply_hero_video(SOON, _settings()).html)
        assert "z-index:-1" in style
        assert "*:not(.binaapp-hero-video-layer){position:relative" not in style

    def test_the_hero_copy_is_never_tagged(self):
        out = apply_hero_video(SOON, _settings()).html
        assert f'<div class="relative z-10 max-w-7xl"{TAG}>' not in out

    def test_reported_as_replaced(self):
        assert "hero_media_replaced:1" in apply_hero_video(SOON, _settings()).notes


class TestOtherHeroShapes:
    def test_inline_background_image_wrapper(self):
        # Test 2: the photo as an inline background-image, no <img>.
        page = (
            '<html><body><section class="relative h-screen">'
            '<div class="absolute inset-0" style="background-image:url(https://x/bg.jpg)"></div>'
            "<h1>Hi</h1></section></body></html>"
        )
        out = apply_hero_video(page, _settings()).html
        assert out.count(TAG) == 1 and 'style="background-image' in out

    def test_a_full_cover_img_directly_in_the_hero(self):
        page = (
            '<html><body><section class="relative h-screen">'
            '<img src="https://x/bg.jpg" class="absolute inset-0 w-full h-full object-cover">'
            "<h1>Hi</h1></section></body></html>"
        )
        out = apply_hero_video(page, _settings()).html
        assert f'object-cover"{TAG}>' in out

    def test_a_wrapper_one_level_down(self):
        page = (
            '<html><body><section class="relative h-screen">'
            '<div class="hero-bg"><div class="absolute inset-0"><img src="https://x/bg.jpg" class="object-cover"></div></div>'
            "<h1>Hi</h1></section></body></html>"
        )
        out = apply_hero_video(page, _settings()).html
        assert out.count(TAG) == 1
        assert f'<div class="absolute inset-0"{TAG}>' in out

    def test_a_hero_with_no_image_is_untouched_and_still_gets_the_video(self):
        # Test 3: nothing to hide, nothing hidden, video still injected.
        page = '<html><body><section class="relative h-screen bg-gray-900"><h1>Hi</h1></section></body></html>'
        result = apply_hero_video(page, _settings())
        assert result.changed and TAG not in result.html
        assert not any(n.startswith("hero_media_replaced") for n in result.notes)

    def test_a_positioned_copy_container_is_not_media(self):
        # `absolute inset-0 flex items-center` holding the headline and a
        # logo <img> is the COPY. Hiding it would blank the hero.
        page = (
            '<html><body><section class="relative h-screen">'
            '<div class="absolute inset-0 flex items-center"><img src="https://x/logo.png" class="h-8"><h1>Hi</h1></div>'
            "</section></body></html>"
        )
        assert TAG not in apply_hero_video(page, _settings()).html

    def test_a_decorative_blob_without_media_is_not_media(self):
        page = (
            '<html><body><section class="relative h-screen">'
            '<div class="absolute inset-0 bg-gradient-to-t from-black/60"></div>'
            "<h1>Hi</h1></section></body></html>"
        )
        assert TAG not in apply_hero_video(page, _settings()).html

    def test_the_injected_layer_is_never_a_candidate(self):
        once = apply_hero_video(SOON, _settings()).html
        twice = apply_hero_video(once, _settings()).html
        assert twice == once and twice.count(TAG) == 1


class TestContracts:
    def test_remove_restores_the_exact_original_bytes(self):
        assert remove_hero_video(apply_hero_video(SOON, _settings()).html).html == SOON

    def test_a_page_published_with_the_old_css_is_upgraded(self):
        # What soon.binaapp.my is serving today: same block, no media tag.
        current = apply_hero_video(SOON, _settings()).html
        legacy = current.replace(TAG, "")
        assert needs_style_upgrade(legacy) is True
        assert needs_style_upgrade(current) is False
        healed = apply_hero_video(legacy, build_settings(**detect_hero_video(legacy))).html
        assert healed.count(TAG) == 1

    def test_find_hero_media_returns_the_outermost_element(self):
        hero_start = SOON.index("<section")
        found = find_hero_media(SOON, hero_start)
        assert len(found) == 1
        start, end = found[0]
        assert SOON[start:].startswith('<div class="absolute inset-0 overflow-hidden">')
        assert "</div></div>" in SOON[start:end]


class TestReducedMotion:
    """Test 4: the poster must be what shows, never a black band."""

    def test_css_hides_the_frame_only(self):
        style = _style(apply_hero_video(SOON, _settings()).html)
        assert "@media (prefers-reduced-motion:reduce)" in style
        assert ".binaapp-hero-video{display:none;}" in style
        # The layer itself (poster background) is not hidden.
        assert ".binaapp-hero-video-layer{display:none" not in style

    def test_the_layer_carries_the_poster_as_its_own_background(self):
        out = apply_hero_video(SOON, _settings()).html
        assert f"background-image:url('{POSTER}')" in out

    def test_the_bootstrap_pauses_and_stops_the_download(self):
        out = apply_hero_video(SOON, _settings()).html
        assert "prefers-reduced-motion: reduce" in out
        assert "v.pause();v.removeAttribute('autoplay');v.preload='none';" in out
        assert "'data-binaapp-video-playing','reduced-motion'" in out


class TestPlayingMeansVisible:
    """Test 5 / fix D: the stamp must not say '1' behind an opaque image."""

    def test_the_bootstrap_probes_before_stamping(self):
        out = apply_hero_video(SOON, _settings()).html
        assert "document.elementFromPoint(" in out
        assert "'data-binaapp-video-playing','covered'" in out
        assert "'data-binaapp-video-playing','1'" in out

    def test_the_probe_ignores_our_own_layer_and_gradients(self):
        out = apply_hero_video(SOON, _settings()).html
        assert "l.contains(t))continue" in out
        # A gradient is background-image too; only url() counts as cover.
        assert "bg.indexOf('url(')>=0" in out


class TestPosterUrlNet:
    """The URL rules stay as the second net for a pinned cut-out (ikan) —
    now also by Cloudinary public id, since the transformation segment
    changes between generation and delivery."""

    def test_public_id_survives_transformation_rewrites(self):
        assert cloudinary_public_id(HERO_IMG) == "binaapp/oooz0uilzwo8xkchc478"
        assert cloudinary_public_id(POSTER) == cloudinary_public_id(
            POSTER.replace("f_auto,q_auto,c_limit,w_1920/", "")
        )

    def test_non_cloudinary_and_short_ids_yield_nothing(self):
        assert cloudinary_public_id("https://x.test/a.jpg") is None
        assert cloudinary_public_id("https://res.cloudinary.com/d/image/upload/v1/ab.jpg") is None
        assert cloudinary_public_id(None) is None

    def test_a_substring_rule_is_emitted_for_a_cloudinary_poster(self):
        style = _style(apply_hero_video(SOON, _settings()).html)
        pid = cloudinary_public_id(POSTER)
        assert f'img[src*="{pid}"]{{display:none !important;}}' in style


class TestHeroId:
    """Secondary finding 3: an id-less hero is found by sibling order."""

    def test_stamps_home_on_an_id_less_hero(self):
        html, changed = ensure_hero_id('<body><section class="relative"><h1>x</h1></section></body>')
        assert changed and '<section class="relative" id="home">' in html

    def test_leaves_an_existing_id_alone(self):
        assert ensure_hero_id('<body><section id="hero"><h1>x</h1></section></body>')[1] is False

    def test_never_duplicates_an_id_already_on_the_page(self):
        assert ensure_hero_id('<body><div id="home">n</div><section><h1>x</h1></section></body>')[1] is False

    def test_no_hero_no_change(self):
        assert ensure_hero_id("<body><p>just text</p></body>") == ("<body><p>just text</p></body>", False)

    def test_the_stamped_hero_is_what_the_patcher_then_finds(self):
        html, _ = ensure_hero_id(SOON)
        result = apply_hero_video(html, _settings())
        assert result.hero_match == "id"
