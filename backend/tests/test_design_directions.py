"""
Direction library (design_directions.py) — the seed catalogue Pass 1 picks
from.

Covers:
- every style × theme (6 picker styles × bright/dark) has ≥ 2 directions
- every direction ships a readable palette (text ≥ 4.5:1, accent ≥ 3:1) and
  a valid pairing from the curated allowlist
- bright is the default: only theme="dark" rows are dark, and the picker's
  Gelap/Cerah toggle is a hard wall in candidate selection
- the picker style narrows candidates; vertical widens when it would empty
- non-F&B verticals never get a Menu section
- the rolling-history exclusion rotates and can never empty the pool
"""

from app.services import design_directions as dd
from app.services.design_director import contrast_ratio, is_dark, is_light


def test_every_style_theme_has_two_directions():
    matrix = dd.coverage_matrix()
    for style in dd.STYLE_TAGS:
        for theme in dd.THEMES:
            assert len(matrix[(style, theme)]) >= 2, (style, theme, matrix[(style, theme)])


def test_direction_palettes_are_readable_and_theme_true():
    for d in dd.DIRECTIONS:
        p = d.palette
        assert contrast_ratio(p["text"], p["bg"]) >= 4.5, d.key
        assert contrast_ratio(p["text"], p["surface"]) >= 4.5, d.key
        assert contrast_ratio(p["muted"], p["bg"]) >= 3.0, d.key
        assert contrast_ratio(p["accent"], p["bg"]) >= 3.0, d.key
        if d.theme == "dark":
            assert is_dark(p["bg"]), d.key
        else:
            assert is_light(p["bg"]), d.key


def test_direction_type_uses_allowlist_and_valid_pairing():
    for d in dd.DIRECTIONS:
        assert d.type["display"] in dd.DISPLAY_FONTS, d.key
        assert d.type["body"] in dd.ALLOWED_FONTS, d.key
        assert dd.is_valid_pairing(d.type["display"], d.type["body"]), d.key
        assert d.type["scale"] in dd.TYPE_SCALES, d.key
        assert d.hero_treatment in dd.HERO_TREATMENTS, d.key
        assert d.signature_element and d.layout_notes and d.motion, d.key


def test_similar_sans_pairing_is_rejected():
    assert not dd.is_valid_pairing("Bricolage Grotesque", "DM Sans")
    assert dd.is_valid_pairing("Fraunces", "Manrope")
    assert dd.is_valid_pairing("Rubik", "Rubik")
    assert dd.is_valid_pairing("Archivo Black", "Rubik")


def test_font_resolution_is_tolerant_and_role_aware():
    assert dd.resolve_allowed_font("playfair display") == "Playfair Display"
    assert dd.resolve_allowed_font("'Fraunces', serif", role="display") == "Fraunces"
    assert dd.resolve_allowed_font("Fraunces", role="body") is None
    assert dd.resolve_allowed_font("Comic Sans MS") is None


def test_type_scale_snaps():
    assert dd.nearest_type_scale("1.25 major third") == "1.25 major third"
    assert dd.nearest_type_scale("major third") == "1.25 major third"
    assert dd.nearest_type_scale(1.3) == "1.333 perfect fourth"
    assert dd.nearest_type_scale("nonsense") == "1.25 major third"


def test_theme_is_a_hard_wall():
    bright = dd.candidate_directions("food", theme="bright")
    dark = dd.candidate_directions("food", theme="dark")
    assert bright and all(d.theme == "bright" for d in bright)
    assert dark and all(d.theme == "dark" for d in dark)
    # The merchant's toggle words work too.
    assert all(d.theme == "dark" for d in dd.candidate_directions("food", theme="gelap"))
    assert all(d.theme == "bright" for d in dd.candidate_directions("food", theme="cerah"))


def test_style_pick_narrows_candidates():
    doodle = dd.candidate_directions("food", theme="bright", style="doodle")
    assert doodle and all("doodle" in d.styles for d in doodle)
    # A doodle pick on a salon widens past the vertical rather than returning nothing.
    salon_doodle = dd.candidate_directions("salon", theme="dark", style="doodle")
    assert salon_doodle and all("doodle" in d.styles and d.theme == "dark" for d in salon_doodle)


def test_keyword_fit_picks_the_closest_direction():
    assert dd.pick_direction("food", text="Nasi kandar mamak buka 24 jam", theme="bright").key == "warung_cerah"
    assert dd.pick_direction("food", text="Specialty coffee, pour over, brunch", theme="bright").key == "kopi_moden"
    assert dd.pick_direction("food", text="Steakhouse and wine lounge", theme="dark").key == "malam_bandar"
    assert dd.pick_direction("salon", text="Salon rambut dan spa", theme="bright").key == "salon_lembut"
    assert dd.pick_direction("services", text="Bengkel aircond dan paip", theme="bright").key == "bengkel_yakin"


def test_rolling_history_rotates_and_never_empties():
    first = dd.pick_direction("food", text="Nasi kandar mamak", theme="bright", seed="a")
    second = dd.pick_direction("food", text="Nasi kandar mamak", theme="bright", seed="a", exclude=[first.key])
    assert second.key != first.key
    everything = [d.key for d in dd.DIRECTIONS]
    still = dd.candidate_directions("food", theme="bright", exclude=everything)
    assert still  # exclusion can shrink the pool but never empty it


def test_non_fnb_section_sets_have_no_menu():
    for vertical in ("clothing", "salon", "services", "general"):
        sections = dd.section_set_for(vertical)
        assert "menu" not in sections["required"] + sections["optional"], vertical
    assert "menu" in dd.section_set_for("food")["required"]
    assert "servis_harga" in dd.section_set_for("salon")["required"]
    assert "kawasan_liputan" in dd.section_set_for("services")["required"]
    assert "koleksi" in dd.section_set_for("clothing")["required"]


def test_cream_serif_gold_only_where_allowed():
    cream_keys = {d.key for d in dd.DIRECTIONS if d.cream_allowed}
    assert cream_keys == {"dapur_keluarga", "warisan_malam"}


def test_google_fonts_link_dedupes_single_family():
    link = dd.google_fonts_link("Rubik", "Rubik")
    assert link.count("family=") == 1
    link2 = dd.google_fonts_link("Fraunces", "Manrope")
    assert "Fraunces" in link2 and "Manrope" in link2
