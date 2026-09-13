"""Round 5 (Gerai Burger Malam Adik, Run 1 site B).

Bug 9: publishing site B onto the subdomain site A was live on replaced it.
The row kept its id and created_at, took the new business name and HTML, and
Kedai Runcit Pak Din ceased to exist — while still carrying site A's address.
Owning a subdomain is not the same as this being the same site.

Bug 8, second shape: the hero reader could not see colours written as
``var(--text-color)``, which is how this generator writes them. Every step of
the chain hit the same wall, the tone came back unknown, and a hero declaring
``--bg-color:#0F0A0A`` got a white scrim under near-white copy. The reader now
resolves the document's own custom properties — and ignores copy inside a box
that paints its own surface, so a floating white price card can no longer
speak for the hero.

Split hero: that same card excluded the media column from hosting the clip, so
a split hero fell back to full-bleed with an empty image column. Copy that
floats OVER the picture is part of the picture.
"""

from app.services.color_tone import css_variables, resolve_vars, text_tone, tint
from app.services.hero_video_patcher import (
    STYLE_ID,
    apply_hero_video,
    build_settings,
    detect_hero_tone,
    find_hero_media,
    find_hero_open_tag,
    remove_hero_video,
)
from app.services.publish_guard import (
    is_live,
    is_same_site,
    replaces_other_site,
    subdomain_conflict,
)

#: Site B as published: a dark page whose colours are custom properties, a
#: split grid hero, and a floating price card over the photo.
SITE_B = (
    "<!DOCTYPE html><html><head><style>:root{--bg-color:#0F0A0A;"
    "--text-color:#FEF2F2;--primary-color:#DC2626}</style></head><body>"
    '<section id="home" class="relative min-h-screen grid md:grid-cols-2 items-center"'
    ' style="background-color: var(--bg-color)">'
    '<div class="order-2 md:order-1 px-8">'
    '<h1 class="text-5xl font-bold" style="color: var(--text-color)">Gerai Burger Malam Adik</h1>'
    '<p style="color: var(--text-color)">Seksyen 13, Shah Alam</p>'
    '<a class="inline-flex bg-primary text-white rounded-full px-8 py-4" href="#menu">Lihat Menu</a>'
    "</div>"
    '<div class="relative order-1 md:order-2 min-h-[320px]">'
    '<img src="https://res.cloudinary.com/d/image/upload/v1/binaapp/burger.jpg"'
    ' class="w-full h-full object-cover" alt="">'
    '<div class="hidden md:block absolute bottom-6 right-6 bg-white/95 backdrop-blur rounded-2xl p-4">'
    '<p style="color: #1C1917">Burger Daging Special</p>'
    '<p style="color: #1C1917">RM8.00</p></div>'
    "</div></section><footer>Gerai Burger Malam Adik</footer></body></html>"
)


def _settings(**kw):
    base = {
        "video_url": "https://res.cloudinary.com/d/video/upload/v1/c.mp4",
        "poster_url": "https://res.cloudinary.com/d/image/upload/v1/p.jpg",
        "poster_luminance": 0.354,
    }
    base.update(kw)
    return build_settings(**base)


def _style(html):
    i = html.index(f'<style id="{STYLE_ID}">')
    return html[i:html.index("</style>", i)]


class TestCustomPropertiesAreResolved:
    def test_the_document_declares_them(self):
        assert css_variables(SITE_B)["--text-color"] == "#FEF2F2"
        assert css_variables(SITE_B)["--bg-color"] == "#0F0A0A"

    def test_a_var_becomes_its_value(self):
        variables = {"--text-color": "#FEF2F2"}
        assert resolve_vars("var(--text-color)", variables) == "#FEF2F2"
        assert text_tone("", "color: var(--text-color)", variables) == "light"
        assert tint("", "background-color: var(--bg-color)", {"--bg-color": "#0F0A0A"}) == ("dark", 1.0)

    def test_an_undeclared_var_falls_back_to_what_the_author_wrote(self):
        assert resolve_vars("var(--nope, #FFFFFF)", {}) == "#FFFFFF"
        assert text_tone("", "color: var(--nope, #FFFFFF)", {}) == "light"

    def test_an_undeclared_var_with_no_fallback_states_nothing(self):
        assert text_tone("", "color: var(--nope)", {}) == ""

    def test_the_base_declaration_wins_over_a_later_override(self):
        # The dark-mode block is written after :root; reporting its colours
        # would describe a mode the visitor may not be in.
        page = (
            "<html><head><style>:root{--bg-color:#FFFFFF}"
            "@media (prefers-color-scheme: dark){:root{--bg-color:#000000}}"
            "</style></head><body></body></html>"
        )
        assert css_variables(page)["--bg-color"] == "#FFFFFF"

    def test_a_var_cannot_spin_forever(self):
        assert resolve_vars("var(--a)", {"--a": "var(--a)"}) == "var(--a)"


class TestTheHeroIsReadCorrectly:
    def test_a_hero_written_in_variables_reads_dark(self):
        assert detect_hero_tone(SITE_B) == "dark"

    def test_the_scrim_is_dark_and_no_white_is_painted(self):
        settings = _settings()
        assert settings.resolved_overlay(SITE_B) == "dark"
        assert "rgba(255,255,255," not in _style(apply_hero_video(SITE_B, settings).html)

    def test_the_near_white_copy_is_left_alone(self):
        assert _settings().resolved_text_mode(SITE_B) == "keep"

    def test_a_card_with_its_own_surface_does_not_speak_for_the_hero(self):
        # The price card's #1C1917 is what the WHITE CARD needs, not what the
        # hero is. Reading it made a dark hero light.
        assert "#1C1917" in SITE_B
        assert detect_hero_tone(SITE_B) == "dark"

    def test_copy_on_the_heros_own_backdrop_still_counts(self):
        light_hero = SITE_B.replace("--text-color:#FEF2F2", "--text-color:#1C1917").replace(
            "--bg-color:#0F0A0A", "--bg-color:#FFFBF5"
        )
        assert detect_hero_tone(light_hero) == "light"


class TestTheSplitHeroKeepsItsSplit:
    def test_the_media_column_hosts_the_clip(self):
        result = apply_hero_video(SITE_B, _settings())
        assert "layer_hosted_in_media_column" in result.notes
        assert 'data-binaapp-hero-media="host"' in result.html

    def test_the_floating_card_is_untouched(self):
        html = apply_hero_video(SITE_B, _settings()).html
        assert "Burger Daging Special" in html and "RM8.00" in html

    def test_a_column_whose_copy_does_not_float_is_not_a_host(self):
        inline_copy = SITE_B.replace(
            '<div class="hidden md:block absolute bottom-6 right-6 bg-white/95 backdrop-blur rounded-2xl p-4">',
            '<div class="mt-4">',
        )
        hero, _how = find_hero_open_tag(inline_copy)
        assert all(host is None for _s, _e, host in find_hero_media(inline_copy, hero.start()))

    def test_a_column_with_no_picture_is_not_a_host(self):
        no_photo = SITE_B.replace(
            '<img src="https://res.cloudinary.com/d/image/upload/v1/binaapp/burger.jpg"'
            ' class="w-full h-full object-cover" alt="">',
            "",
        )
        hero, _how = find_hero_open_tag(no_photo)
        assert all(host is None for _s, _e, host in find_hero_media(no_photo, hero.start()))

    def test_remove_is_still_byte_exact(self):
        assert remove_hero_video(apply_hero_video(SITE_B, _settings()).html).html == SITE_B

    def test_re_applying_changes_nothing(self):
        once = apply_hero_video(SITE_B, _settings()).html
        assert apply_hero_video(once, _settings()).html == once


class TestASubdomainWithALiveSiteIsNotFreeToTake:
    LIVE = {
        "id": "row-1",
        "business_name": "Kedai Runcit Pak Din",
        "name": "Test",
        "status": "published",
    }

    def test_a_different_site_is_refused(self):
        conflict = subdomain_conflict(self.LIVE, "Gerai Burger Malam Adik", "runcit-label-test")
        assert conflict is not None
        assert conflict["error"] == "subdomain_in_use"
        assert conflict["existing_business_name"] == "Kedai Runcit Pak Din"
        assert "runcit-label-test.binaapp.my" in conflict["message"]

    def test_the_same_site_republishes_as_before(self):
        assert subdomain_conflict(self.LIVE, "Kedai Runcit Pak Din", "runcit-label-test") is None
        assert subdomain_conflict(self.LIVE, "  kedai runcit pak din  ", "x") is None

    def test_a_confirmed_replacement_goes_through(self):
        assert subdomain_conflict(
            self.LIVE, "Gerai Burger Malam Adik", "runcit-label-test", replace_existing=True
        ) is None

    def test_a_draft_of_your_own_is_not_a_live_site(self):
        draft = dict(self.LIVE, status="draft")
        assert is_live(draft) is False
        assert subdomain_conflict(draft, "Gerai Burger Malam Adik", "x") is None

    def test_is_published_counts_as_live_too(self):
        assert is_live({"status": "", "is_published": True}) is True

    def test_a_row_we_cannot_name_is_never_blocked(self):
        assert is_same_site({"status": "published"}, "Gerai Burger") is True
        assert subdomain_conflict({"status": "published"}, "Gerai Burger", "x") is None

    def test_a_publish_with_no_name_is_never_blocked(self):
        assert subdomain_conflict(self.LIVE, "", "x") is None

    def test_replacement_is_reported_so_the_old_fields_can_be_cleared(self):
        assert replaces_other_site(self.LIVE, "Gerai Burger Malam Adik") is True
        assert replaces_other_site(self.LIVE, "Kedai Runcit Pak Din") is False
        assert replaces_other_site(None, "Gerai Burger Malam Adik") is False
