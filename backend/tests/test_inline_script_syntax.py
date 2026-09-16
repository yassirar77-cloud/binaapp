"""An inline <script> that cannot parse must not ship (mkl, 2026-09-16).

The page emitted:

    'sans': ['Source Sans 3', 'system-ui, -apple-system, 'Segoe UI', sans-serif'],

A single-quoted string with single-quoted content inside it. The whole
`tailwind.config` block is a SyntaxError, so it never runs, so `primary`,
`secondary`, `accent` and `surface` were never registered — and the page
still LOOKED right, because the model also wrote literal hex classes
everywhere. Invisible and total: the combination worth blocking on.

The cause was ours, not the model's: FONT_FALLBACKS handed it
``system-ui, -apple-system, 'Segoe UI', sans-serif`` and it did the obvious
thing with it. Those stacks carry no quotes now (a multi-word family name
is legal CSS unquoted), so neither quote character can break the file the
stack lands in.
"""

from __future__ import annotations

from app.services.design_director import FONT_FALLBACKS
from app.services.design_directions import FONT_FALLBACKS_FOR
from app.services.generation_validator import (
    GenerationBrief,
    _unbalanced_string_literal,
    validate_generated_site,
)

BROKEN = """<!DOCTYPE html><html><head><script>
    tailwind.config = {
      theme: { extend: {
          colors: { 'primary': '#D46A2A' },
          fontFamily: {
            'sans': ['Source Sans 3', 'system-ui, -apple-system, 'Segoe UI', sans-serif'],
            'heading': ['Archivo Black', 'Impact, 'Arial Black', sans-serif'],
          }
      } }
    }
</script></head><body><p>hi</p></body></html>"""

GOOD = BROKEN.replace(
    "'system-ui, -apple-system, 'Segoe UI', sans-serif'",
    '\'system-ui, -apple-system, "Segoe UI", sans-serif\'',
).replace(
    "'Impact, 'Arial Black', sans-serif'",
    '\'Impact, "Arial Black", sans-serif\'',
)

UNQUOTED = BROKEN.replace(
    "'system-ui, -apple-system, 'Segoe UI', sans-serif'",
    "'system-ui, -apple-system, Segoe UI, sans-serif'",
).replace(
    "'Impact, 'Arial Black', sans-serif'",
    "'Impact, Arial Black, sans-serif'",
)


def _codes(html: str):
    return [e.code for e in validate_generated_site(html, GenerationBrief()).errors]


class TestTheBrokenConfigIsCaught:
    def test_it_is_an_error(self):
        assert "invalid_inline_script" in _codes(BROKEN)

    def test_the_detail_shows_the_literal_that_breaks(self):
        issue = next(
            e for e in validate_generated_site(BROKEN, GenerationBrief()).errors
            if e.code == "invalid_inline_script"
        )
        assert "system-ui" in issue.detail
        assert "tailwind.config" in issue.message


class TestValidScriptsAreSilent:
    def test_double_quoted_inner_family(self):
        assert "invalid_inline_script" not in _codes(GOOD)

    def test_unquoted_family(self):
        assert "invalid_inline_script" not in _codes(UNQUOTED)

    def test_a_script_with_regexes_and_escapes_is_not_flagged(self):
        # The hero-video playback bootstrap: regex literals, escaped quotes,
        # nested functions. It must not read as broken.
        page = (
            "<html><body><script>(function(){var m=/rgba?\\(\\s*\\d+\\s*,/.exec("
            "getComputedStyle(document.body).backgroundColor||'');"
            "var s=\"a'b\";var t='c\\'d';if(!m)return;})();</script></body></html>"
        )
        assert "invalid_inline_script" not in _codes(page)

    def test_template_literals_are_allowed_to_span_lines(self):
        page = (
            "<html><body><script>var msg = `line one\n"
            "line two`;</script></body></html>"
        )
        assert "invalid_inline_script" not in _codes(page)

    def test_external_scripts_are_not_inspected(self):
        page = '<html><head><script src="https://cdn.tailwindcss.com"></script></head><body>x</body></html>'
        assert "invalid_inline_script" not in _codes(page)


class TestTheCauseIsGone:
    def test_no_font_fallback_carries_a_quote(self):
        # A stack with a quote in it becomes a SyntaxError the moment the
        # model wraps it in the same quote — which is exactly what happened.
        for name, stack in {**FONT_FALLBACKS, **FONT_FALLBACKS_FOR}.items():
            assert "'" not in stack, f"{name}: {stack}"
            assert '"' not in stack, f"{name}: {stack}"

    def test_a_stack_survives_being_embedded_in_either_quote(self):
        for stack in {**FONT_FALLBACKS, **FONT_FALLBACKS_FOR}.values():
            for quote in ("'", '"'):
                assert _unbalanced_string_literal(f"var a = [{quote}{stack}{quote}];") == ""
