"""Tests for the post-generation HTML linter (FA icons + Tailwind classes)."""

from app.services.generation_linter import (
    lint_fontawesome_icons,
    lint_tailwind_classes,
    lint_html,
)


# ---------------------------------------------------------------------------
# Font Awesome icon linting
# ---------------------------------------------------------------------------

def test_pro_icon_replaced_with_food_fallback():
    html = '<i class="fa-solid fa-pot-food"></i>'
    out, repl = lint_fontawesome_icons(html, context="Kedai Tomyam food")
    assert "fa-pot-food" not in out
    assert "fa-utensils" in out or "fa-bowl-food" in out
    assert repl and repl[0][0] == "pot-food"


def test_known_free_icons_untouched():
    html = '<i class="fa-solid fa-utensils fa-2x fa-fw"></i><i class="fab fa-whatsapp"></i>'
    out, repl = lint_fontawesome_icons(html, context="food")
    assert out == html
    assert repl == []


def test_style_and_size_modifiers_never_replaced():
    # fa-spin / fa-3x / fa-brands must not be treated as glyphs
    html = '<i class="fa-brands fa-instagram fa-3x fa-spin"></i>'
    out, repl = lint_fontawesome_icons(html, context="shop")
    assert out == html
    assert repl == []


def test_non_class_fa_text_untouched():
    html = "<p>The word fa-pot-food appears in prose, not a class.</p>"
    out, repl = lint_fontawesome_icons(html, context="food")
    assert out == html
    assert repl == []


def test_multiple_unknown_icons_all_replaced():
    html = (
        '<i class="fa-solid fa-pot-food"></i>'
        '<i class="fa-solid fa-pan-frying"></i>'
        '<i class="fa-solid fa-utensils"></i>'
    )
    out, repl = lint_fontawesome_icons(html, context="restoran food")
    assert "fa-pot-food" not in out
    assert "fa-pan-frying" not in out
    assert "fa-utensils" in out
    assert len(repl) == 2


# ---------------------------------------------------------------------------
# Tailwind opacity linting
# ---------------------------------------------------------------------------

def test_invalid_opacity_rewritten():
    html = '<div class="bg-amber-300/8"></div>'
    out, rw = lint_tailwind_classes(html)
    assert "bg-amber-300/[0.08]" in out
    assert rw and rw[0][1] == "bg-amber-300/[0.08]"


def test_valid_opacity_untouched():
    html = '<div class="bg-black/50 text-white/90"></div>'
    out, rw = lint_tailwind_classes(html)
    assert out == html
    assert rw == []


def test_opacity_33_rewritten():
    html = '<div class="text-slate-900/33"></div>'
    out, _ = lint_tailwind_classes(html)
    assert "text-slate-900/[0.33]" in out


# ---------------------------------------------------------------------------
# Tailwind spacing linting
# ---------------------------------------------------------------------------

def test_negative_out_of_scale_spacing_rewritten():
    html = '<div class="absolute -right-30 top-10"></div>'
    out, rw = lint_tailwind_classes(html)
    assert "right-[-7.5rem]" in out
    assert "top-10" in out  # 10 is a valid scale step, untouched
    assert any(o == "-right-30" for o, _ in rw)


def test_valid_spacing_untouched():
    html = '<div class="p-4 mt-8 gap-6 left-0 inset-0"></div>'
    out, rw = lint_tailwind_classes(html)
    assert out == html
    assert rw == []


def test_fractions_and_keywords_untouched():
    html = '<div class="w-1/2 h-screen min-h-screen top-1/2"></div>'
    out, rw = lint_tailwind_classes(html)
    assert out == html
    assert rw == []


def test_positive_out_of_scale_spacing_rewritten():
    html = '<div class="mt-30"></div>'
    out, _ = lint_tailwind_classes(html)
    assert "mt-[7.5rem]" in out


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

def test_lint_html_combines_both_passes():
    html = (
        '<i class="fa-solid fa-pot-food"></i>'
        '<div class="bg-amber-300/8 -right-30"></div>'
    )
    out, report = lint_html(html, context="Kedai Tomyam")
    assert report.changed
    assert report.fa_replacements
    assert report.tw_rewrites
    assert "fa-pot-food" not in out
    assert "bg-amber-300/[0.08]" in out
    assert "right-[-7.5rem]" in out


def test_lint_html_clean_input_unchanged():
    html = '<i class="fa-solid fa-utensils"></i><div class="p-4 bg-black/50"></div>'
    out, report = lint_html(html)
    assert out == html
    assert not report.changed


# ---------------------------------------------------------------------------
# Icon-bias fixes (the gogoo phone-shop bug)
# ---------------------------------------------------------------------------
# "kedai" just means "shop" in Malay — it used to map unknown glyphs to
# fa-bowl-food, which stamped food icons onto a phone shop's feature cards.

from app.services.generation_linter import lint_food_icon_bias

PHONE_CTX = "Kedai Phone & Smart Line kedai phone, jual smartphone di Shah Alam"


def test_kedai_context_no_longer_maps_unknown_glyphs_to_food():
    html = '<i class="fa-solid fa-signal-bars"></i>'  # Pro-only glyph
    out, repl = lint_fontawesome_icons(html, context="kedai runcit Pak Mat")
    assert "bowl-food" not in out
    assert repl and repl[0] == ("signal-bars", "store")


def test_phone_context_unknown_glyph_falls_back_to_mobile_screen():
    html = '<i class="fa-solid fa-signal-bars"></i>'
    out, repl = lint_fontawesome_icons(html, context=PHONE_CTX)
    assert "fa-mobile-screen" in out
    assert repl == [("signal-bars", "mobile-screen")]


def test_recommended_electronics_glyphs_survive_linting():
    html = (
        '<i class="fa-solid fa-mobile-screen"></i>'
        '<i class="fa-solid fa-signal"></i>'
        '<i class="fa-solid fa-sim-card"></i>'
    )
    out, repl = lint_fontawesome_icons(html, context=PHONE_CTX)
    assert out == html
    assert repl == []


class TestFoodIconBiasPass:
    def test_bowl_food_replaced_on_phone_shop(self):
        # The exact gogoo defect: fa-bowl-food on the "Smart Line" feature
        # of a phone shop (business type detected as 'general').
        html = '<i class="fa-solid fa-bowl-food text-3xl"></i>'
        out, repl = lint_food_icon_bias(html, "general", PHONE_CTX)
        assert "fa-bowl-food" not in out
        assert "fa-mobile-screen" in out
        assert repl == [("bowl-food", "mobile-screen")]
        # Style/size tokens untouched.
        assert "fa-solid" in out and "text-3xl" in out

    def test_nonfood_nonphone_business_gets_circle_check(self):
        html = '<i class="fa-solid fa-utensils"></i>'
        out, repl = lint_food_icon_bias(html, "clothing", "Butik Aisyah tudung")
        assert "fa-circle-check" in out
        assert repl == [("utensils", "circle-check")]

    def test_food_business_keeps_food_icons(self):
        html = '<i class="fa-solid fa-bowl-food"></i><i class="fa-solid fa-utensils"></i>'
        out, repl = lint_food_icon_bias(html, "food", "Restoran Tomyam")
        assert out == html
        assert repl == []

    def test_bakery_keeps_food_icons(self):
        html = '<i class="fa-solid fa-cake-candles"></i>'
        out, repl = lint_food_icon_bias(html, "bakery", "Bakeri Kek Sedap")
        assert out == html
        assert repl == []

    def test_unknown_business_type_is_noop(self):
        html = '<i class="fa-solid fa-bowl-food"></i>'
        out, repl = lint_food_icon_bias(html, "", PHONE_CTX)
        assert out == html
        assert repl == []

    def test_dual_use_glyphs_left_alone(self):
        # fish (aquarium/pet), leaf/seedling (eco) are legitimate non-food uses.
        html = (
            '<i class="fa-solid fa-fish"></i>'
            '<i class="fa-solid fa-leaf"></i>'
            '<i class="fa-solid fa-seedling"></i>'
        )
        out, repl = lint_food_icon_bias(html, "general", "aquarium pet shop")
        assert out == html
        assert repl == []

    def test_non_class_text_untouched(self):
        html = "<p>Kami serve fa-bowl-food quality!</p>"
        out, repl = lint_food_icon_bias(html, "general", PHONE_CTX)
        assert out == html
        assert repl == []


def test_lint_html_runs_food_bias_when_business_type_given():
    html = '<i class="fa-solid fa-bowl-food"></i>'
    out, report = lint_html(html, context=PHONE_CTX, business_type="general")
    assert "fa-mobile-screen" in out
    assert report.food_icon_replacements == [("bowl-food", "mobile-screen")]
    assert report.changed


def test_lint_html_without_business_type_skips_food_bias():
    # Callers that can't supply a business type keep the old behaviour.
    html = '<i class="fa-solid fa-bowl-food"></i>'
    out, report = lint_html(html, context="some shop")
    assert out == html
    assert report.food_icon_replacements == []


def test_lint_html_food_bias_corrects_unknown_glyph_fallback_too():
    # Unknown glyph on a non-food site whose context still picks a food
    # fallback (e.g. "tomyam" in the name of a general store) — the bias
    # pass runs after and corrects it.
    html = '<i class="fa-solid fa-pot-food"></i>'
    out, report = lint_html(html, context="tomyam merchandise store", business_type="general")
    assert "fa-pot-food" not in out
    assert "fa-bowl-food" not in out
