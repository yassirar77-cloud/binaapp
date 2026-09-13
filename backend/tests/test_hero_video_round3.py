"""Round 3 (bji.binaapp.my, light full-bleed): the CTA, the scrim, the guard.

Bug 4: the text-recolour exclusion matched class names, so a CTA whose
background lives in the page's own <style> (.btn-whatsapp) was recoloured
navy on pink, 3.66:1. The stamp is now made at RUNTIME from the computed
background, and every recolour rule is scoped by it.

Scrim: a bright clip under a LIGHT scrim got the dark-scrim opacity (0.52)
and the flowers vanished. The luminance is stored; the opacity is derived
per scrim colour at apply time.

Finding 7: a video hero was exempt from the no-image height guard by
accident (the layer's poster background defeated :has()). Now explicit.
"""

from app.services.business_identity import localities_in
from app.services.generation_validator import GenerationBrief, validate_generated_site
from app.services.hero_video_patcher import (
    DARK_SCRIM_MAP,
    KEEP_COLOR_ATTR,
    LIGHT_SCRIM_MAP,
    STYLE_ID,
    apply_hero_video,
    build_settings,
    detect_hero_video,
    opacity_for,
    remove_hero_video,
)
from app.services.templates import TemplateService

LIGHT = (
    "<html><head><style>:root{--bg-color:#FFFFFF}.btn-whatsapp{background:#CE3560;color:#fff}</style></head><body>"
    '<section class="hero-min-height flex items-center justify-center bg-white" id="home">'
    '<div class="text-center"><h1>Kedai Bunga Seri Melur</h1>'
    '<a class="btn-whatsapp inline-flex px-8 py-4 rounded-full" href="https://wa.me/60193456781">WhatsApp</a>'
    '<a class="btn-whatsapp-outline">Lihat</a></div></section></body></html>'
)
DARK = LIGHT.replace("#FFFFFF", "#111111")


def _settings(**kw):
    base = {"video_url": "https://v.test/a.mp4", "poster_url": "https://v.test/a.jpg"}
    base.update(kw)
    return build_settings(**base)


def _style(html):
    i = html.index(f'<style id="{STYLE_ID}">')
    return html[i:html.index("</style>", i)]


class TestKeepColour:
    def test_every_recolour_rule_is_scoped_by_the_runtime_stamp(self):
        style = _style(apply_hero_video(LIGHT, _settings()).html)
        colour_rules = [r for r in style.split("}") if "color:#0F172A !important" in r or "border-color:currentColor" in r]
        assert colour_rules, "expected recolour rules on a full-bleed light hero"
        for rule in colour_rules:
            for selector in rule.split("{")[0].split(","):
                assert f":not([{KEEP_COLOR_ATTR}])" in selector, selector

    def test_no_rule_keys_on_class_names_any_more(self):
        style = _style(apply_hero_video(LIGHT, _settings()).html)
        assert '[class*="bg-"]' not in style and '[class*="border-"]' not in style

    def test_the_bootstrap_stamps_from_the_computed_background(self):
        html = apply_hero_video(LIGHT, _settings()).html
        assert f"var K='{KEEP_COLOR_ATTR}'" in html
        assert "getComputedStyle(e).backgroundColor" in html
        assert "parseFloat(m[1])>=0.1" in html          # alpha ≥ 0.1 keeps its colour
        assert "d[j].setAttribute(K,'')" in html         # …and so do its descendants
        assert "if(l.contains(e)||e.hasAttribute(K))continue" in html  # never our layer

    def test_stamping_runs_before_play(self):
        html = apply_hero_video(LIGHT, _settings()).html
        assert html.index("var K='data-binaapp-keep-color'") < html.index("go();")


class TestScrimFromLuminance:
    def test_dark_scrim_map_is_the_historical_one(self):
        assert DARK_SCRIM_MAP == ((0.20, 0.35), (0.75, 0.70))
        assert opacity_for("dark", 0.9) == 0.70 and opacity_for("dark", 0.1) == 0.35

    def test_light_scrim_is_the_inverse(self):
        # A bright clip under a light scrim needs LESS white, not more.
        assert LIGHT_SCRIM_MAP == ((0.20, 0.50), (0.75, 0.25))
        assert opacity_for("light", 0.9) == 0.25 and opacity_for("light", 0.1) == 0.50
        assert opacity_for("light", 0.475) == 0.38  # midpoint, rounded

    def test_unknown_luminance_keeps_the_fixed_default(self):
        assert opacity_for("light", None) == 0.45 == opacity_for("dark", None)

    def test_a_bright_clip_on_a_light_page_is_barely_veiled(self):
        style = _style(apply_hero_video(LIGHT, _settings(poster_luminance=0.9)).html)
        assert "rgba(255,255,255,0.25)" in style
        assert "rgba(255,255,255,0.52)" not in style

    def test_the_same_clip_on_a_dark_page_gets_the_heavy_dark_scrim(self):
        style = _style(apply_hero_video(DARK, _settings(poster_luminance=0.9)).html)
        assert "rgba(0,0,0,0.7)" in style

    def test_an_explicit_opacity_is_used_as_is(self):
        style = _style(apply_hero_video(LIGHT, _settings(poster_luminance=0.9, overlay_opacity=0.6)).html)
        assert "rgba(255,255,255,0.6)" in style

    def test_luminance_and_unset_opacity_round_trip_through_detect(self):
        html = apply_hero_video(LIGHT, _settings(poster_luminance=0.9)).html
        state = detect_hero_video(html)
        assert state["poster_luminance"] == 0.9 and state["overlay_opacity"] is None
        # …so a re-apply after a theme change re-derives, rather than freezing 0.25.
        assert build_settings(**state).overlay_opacity is None

    def test_remove_is_still_byte_exact(self):
        assert remove_hero_video(apply_hero_video(LIGHT, _settings(poster_luminance=0.9)).html).html == LIGHT


class TestGuardExemptsVideoHeroExplicitly:
    def test_the_no_image_guard_names_the_marker(self):
        css = TemplateService.LAYOUT_SAFETY_CSS
        for hero_id in ("home", "hero", "laman-utama"):
            assert f'section[id="{hero_id}"]:not([data-binaapp-hero-video]):not(:has(img))' in css


class TestLocalityConflict:
    def test_reads_the_town_not_the_section_number(self):
        assert localities_in("Kedai bunga di Seksyen 9, Shah Alam") == {"alam"}
        assert localities_in("No 1 jalan cecawi 4/78, kota damansara") == {"damansara"}

    def test_a_qualifier_alone_is_not_a_place(self):
        assert localities_in("Jalan Sungai Besi") == frozenset()
        assert localities_in("Selangor sahaja") == frozenset()

    def test_conflict_is_a_warning_with_both_sides_named(self):
        brief = GenerationBrief(
            business_name="Seri Melur",
            description="Kedai bunga di Seksyen 9, Shah Alam",
            location_address="No 1 Jalan Cecawi 4/78, Kota Damansara",
        )
        page = '<html><body><h1>Seri Melur</h1><a href="https://wa.me/60193456781">w</a></body></html>'
        result = validate_generated_site(page, brief)
        hit = [w for w in result.warnings if w.code == "address_locality_conflict"]
        assert hit and "alam" in hit[0].detail and "damansara" in hit[0].detail
        assert not [e for e in result.errors if e.code == "address_locality_conflict"]

    def test_a_shared_town_is_silent(self):
        brief = GenerationBrief(business_name="X", description="di Shah Alam",
                                location_address="Seksyen 7, Shah Alam")
        page = '<html><body><h1>X</h1><a href="https://wa.me/60193456781">w</a></body></html>'
        assert not [w for w in validate_generated_site(page, brief).warnings if w.code == "address_locality_conflict"]

    def test_no_address_is_silent(self):
        brief = GenerationBrief(business_name="X", description="di Shah Alam")
        page = '<html><body><h1>X</h1><a href="https://wa.me/60193456781">w</a></body></html>'
        assert not [w for w in validate_generated_site(page, brief).warnings if w.code == "address_locality_conflict"]


class TestServedPageIsFetchableByTheApp:
    """Bug 6: the export fell back to the generation-time copy silently. The
    served page is now the export's first source, so the middleware must let
    the app's origin read it — and nobody else's."""

    def _headers(self, origin):
        from types import SimpleNamespace
        from app.middleware.subdomain import _page_response

        request = SimpleNamespace(headers={"origin": origin} if origin else {})
        return _page_response("<html><body>x</body></html>", request, "ws-1").headers

    def test_the_app_origin_may_read_the_body(self):
        headers = self._headers("https://binaapp.my")
        assert headers["access-control-allow-origin"] == "https://binaapp.my"
        assert headers["vary"] == "Origin"

    def test_a_foreign_origin_gets_nothing(self):
        assert "access-control-allow-origin" not in self._headers("https://evil.example")

    def test_no_origin_header_gets_nothing(self):
        assert "access-control-allow-origin" not in self._headers("")
