"""Brand palette, heading font and the bold/outline menu block.

agp.binaapp.my: the brief named yellow / chilli red / black ("KUNING TERANG
+ MERAH CILI", thick black outlines) and the plan shipped accent_2 #203808
(dark green "from the photos"); the menu block's titles fell back to the
body font because --font-heading was never declared; and its rounded,
soft-shadow cards sat on a page of square 3px-outlined cards.
"""


import pytest

from app.services import brand_palette as bp
from app.services import menu_fidelity as mf

AGP_BRIEF = (
    "Ayam Gepuk Panglima di Kota Bayu Emas. Nasi putih panas dengan sambal merah.\n"
    "Cari kedai kuning terang dengan signboard Ayam Gepuk Panglima!"
)
AGP_DESIGN = "Warna jenama: KUNING TERANG + MERAH CILI, outline hitam tebal 3px. Berani, pedas, ceria — jangan gelap."
AGP_PLAN_PALETTE = {"bg": "#FFF200", "surface": "#FFFFFF", "text": "#1A1208", "muted": "#4A3A12", "accent": "#D7261E", "accent_2": "#203808"}


class TestNamedColours:
    def test_colour_words_only_count_in_a_colour_context(self):
        assert bp.named_colours("Nasi putih dengan sambal merah dan sayur hijau.") == []
        # A descriptive signboard mention is not a palette (see TestExplicitOnly).
        assert bp.named_colours(AGP_BRIEF) == []

    def test_design_brief_order_and_multiword(self):
        assert bp.named_colours(AGP_DESIGN) == ["#FACC15", "#D7261E", "#111111"]
        assert bp.named_colours("Tema warna merah jambu dan putih") == ["#EC4899", "#FFFFFF"]

    def test_allowed(self):
        named = ["#FACC15", "#D7261E", "#111111"]
        assert bp.allowed("#FFF200", named) and bp.allowed("#B91C1C", named) and bp.allowed("#FAFAFA", named)
        assert not bp.allowed("#203808", named) and not bp.allowed("#2563EB", named)


class TestConstrain:
    def test_agp_plan_palette(self):
        named = bp.brief_colour_set((AGP_BRIEF, AGP_DESIGN))
        out, notes = bp.constrain_palette(
            AGP_PLAN_PALETTE, named, accent_keys=("accent", "accent_2"),
            neutral_keys={"bg": "bg", "surface": "surface", "text": "text", "muted": "muted"}, background_key="bg",
        )
        assert out["accent_2"] != "#203808" and bp.allowed(out["accent_2"], named)
        assert out["accent"] == "#D7261E" and out["bg"] == "#FFF200"
        assert any("#203808" in n for n in notes)

    def test_off_brand_background_becomes_neutral(self):
        out, _ = bp.constrain_palette(
            {"bg": "#E0F2FE", "surface": "#FFFFFF", "text": "#111111", "muted": "#555555", "accent": "#DC2626"},
            ["#DC2626"], accent_keys=("accent",), neutral_keys={"bg": "bg", "surface": "surface", "text": "text", "muted": "muted"},
            background_key="bg",
        )
        assert out["bg"] == "#FFFFFF"

    def test_no_named_colours_no_change(self):
        assert bp.brief_colour_set(("Kedai makan biasa.",)) == []


def test_design_plan_validator_applies_the_constraint():
    from app.services import design_directions as dd
    from app.services.design_plan import PlanBrief, _validate_palette

    brief = PlanBrief(business_name="AGP", description=AGP_BRIEF, design_brief=AGP_DESIGN, theme="bright",
                      image_colours=["#203808"])
    direction = dd.DIRECTIONS[0]
    adjustments = []
    pal = _validate_palette(AGP_PLAN_PALETTE, direction, brief, adjustments)
    named = bp.brief_colour_set((AGP_BRIEF, AGP_DESIGN))
    assert all(bp.allowed(pal[k], named) for k in ("accent", "accent_2")), pal
    assert "#203808" not in pal.values()


def test_concept_validator_applies_the_constraint():
    from app.services.design_director import _validate_palette

    raw = {"primary": "#203808", "secondary": "#D7261E", "accent": "#FACC15", "background": "#FFFFFF",
           "surface": "#FFFFFF", "text": "#111111", "text_muted": "#4B5563"}
    pal = _validate_palette(raw, raw, "light", [], brief_texts=(AGP_DESIGN,))
    assert not pal["primary"].upper().startswith("#2038")
    hue_ok = bp.allowed(pal["primary"], bp.named_colours(AGP_DESIGN))
    assert hue_ok, pal["primary"]


class TestHeadingFont:
    def test_plan_head_declares_font_heading(self):
        from types import SimpleNamespace
        from app.services.designer_prompt_blocks import head_block

        plan = SimpleNamespace(type={"display": "Archivo Black"})
        pal = {"background": "#FFF200", "surface": "#FFF", "text": "#111", "text_muted": "#444"}
        out = head_block(plan, "", "", pal, "#D7261E", "#B91C1C", "Source Sans 3", "sans-serif")
        assert "--font-heading: 'Archivo Black'" in out

    def test_missing_var_is_declared_from_the_page(self):
        html = ("<html><head><script>tailwind.config={theme:{extend:{fontFamily:{display:['Archivo Black','sans-serif'],"
                "body:['Source Sans 3']}}}}</script></head><body></body></html>")
        out, done = mf.ensure_font_heading_var(html)
        assert done and ":root{--font-heading:'Archivo Black'" in out and out.index("binaapp-font-heading") < out.index("</head>")
        assert mf.ensure_font_heading_var(out) == (out, False)

    def test_google_fonts_fallback(self):
        html = '<head><link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap"></head>'
        assert mf.heading_font_of(html) == "Bebas Neue"


class TestOutlineVariant:
    OUTLINED = "".join(f'<div class="rounded-none border-[3px] border-black shadow-[4px_4px_0_#000]">{i}</div>' for i in range(3))

    def test_detection(self):
        assert mf.detect_outline_style(self.OUTLINED)
        assert mf.detect_outline_style("<style>.c{border:3px solid #000}.b{border: 3px solid black}.x{border:4px solid #111}</style>")
        assert not mf.detect_outline_style('<div class="border border-gray-200 rounded-xl"></div>' * 5)

    def test_block_variant(self):
        items = mf.normalize_items([{"name": f"Set {c}", "price": "10", "category": "Set"} for c in "ABCDEFGHI"])
        block = mf.render_menu_block(items, variant="outline")
        assert 'class="binaapp-menu-block bmf-outline"' in block
        assert ".binaapp-menu-block.bmf-outline .bmf-card{border-radius:0;border:3px solid #000" in block
        assert 'class="binaapp-menu-block"' in mf.render_menu_block(items)

    def test_pipeline_picks_the_outline_variant(self):
        import json
        import os
        from types import SimpleNamespace
        from app.services.ai_service import AIService

        with open(os.path.join(os.path.dirname(__file__), "fixtures", "ayam_gepuk_panglima_menu.json"), encoding="utf-8") as fh:
            raw = json.load(fh)["menu_items"]
        svc = AIService.__new__(AIService)
        req = SimpleNamespace(menu_items=raw, description="", business_name="AGP", show_prices=True, uploaded_images=[])
        html = f'<html><head></head><body>{self.OUTLINED}<section id="menu"><div id="binaapp-menu-slot"></div></section></body></html>'
        out = svc._enforce_menu_fidelity(html, req, image_urls=None)
        assert "binaapp-menu-block bmf-outline" in out


class TestExplicitOnly:
    """Lock the palette only when the brief explicitly lists brand colours."""

    @pytest.mark.parametrize("brief", [
        "Cari kedai kuning terang dengan signboard Ayam Gepuk Panglima!",
        "Logo kami merah dan hitam, kedai berwarna kuning.",
        "Papan tanda kuning dengan tulisan merah.",
        "Nasi putih panas dengan sambal merah.",
        "Tema: ceria dan mesra keluarga.",
    ])
    def test_descriptive_mentions_do_not_lock(self, brief):
        assert bp.named_colours(brief) == []
        assert bp.brief_colour_set((brief,)) == []

    @pytest.mark.parametrize("brief,expected", [
        ("Warna jenama: kuning terang, merah cili dan hitam.", ["#FACC15", "#D7261E", "#111111"]),
        ("Brand colours: red & black", ["#DC2626", "#111111"]),
        ("Colours: yellow, red, black", ["#FACC15", "#DC2626", "#111111"]),
        ("Skema warna kedai kuning dan hijau", ["#FACC15", "#16A34A"]),
    ])
    def test_explicit_lists_lock(self, brief, expected):
        assert bp.named_colours(brief) == expected

    def test_kedai_kuning_terang_keeps_the_red_and_black(self):
        """agp's own description, with no explicit colour list: the plan's red
        accent and black outline ink survive untouched."""
        from app.services import design_directions as dd
        from app.services.design_plan import PlanBrief, _validate_palette

        brief = PlanBrief(business_name="AGP", description=AGP_BRIEF, design_brief="Berani, pedas, ceria — jangan gelap.",
                          theme="bright")
        raw = {"bg": "#FFF7D6", "surface": "#FFFFFF", "text": "#1A120B", "muted": "#5C4A3A", "accent": "#D62E12", "accent_2": "#111111"}
        adjustments = []
        pal = _validate_palette(raw, dd.DIRECTIONS[0], brief, adjustments)
        assert pal["accent"] == "#D62E12" and pal["accent_2"] == "#111111"
        assert not any("not a merchant colour" in a for a in adjustments)


class TestShadesNotOtherColours:
    """agp: a dark brick-brown passed as 'red' on hue alone; every price and
    Pesan button came out #5D2310."""

    NAMED = bp.named_colours("Warna jenama: kuning terang, merah cili dan hitam.")

    def test_brown_is_not_chilli_red(self):
        assert not bp.allowed("#5D2310", self.NAMED)

    def test_real_shades_of_the_brand_red_still_pass(self):
        for shade in ("#D7261E", "#C81E1E", "#B32019", "#A01818", "#E63946"):
            assert bp.allowed(shade, self.NAMED), shade

    def test_brown_accent_is_replaced_by_the_named_red(self):
        out, notes = bp.constrain_palette(
            {"bg": "#FFF8E1", "surface": "#FFFFFF", "text": "#1A120B", "muted": "#5C4A3A", "accent": "#5D2310", "accent_2": "#FFD23F"},
            self.NAMED, accent_keys=("accent", "accent_2"),
            neutral_keys={"bg": "bg", "surface": "surface", "text": "text", "muted": "muted"}, background_key="bg",
        )
        assert out["accent"] == "#D7261E" and out["accent_2"] == "#FFD23F"
        assert any("#5D2310" in n for n in notes)
