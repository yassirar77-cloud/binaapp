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
