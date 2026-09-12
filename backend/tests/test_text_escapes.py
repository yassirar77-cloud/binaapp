"""Tests for the model-output escape decode (app.utils.text_escapes).

The incident: generated sites shipped with literal backslash escapes in their
visible text — 17 on one live site, including the <title> and the meta
description. The 8-hex capital-U form (`\\U0001f4f1`) is Python source syntax
that JSON cannot produce, which is how we know the MODEL wrote them rather
than a serializer in the pipeline.

Fixtures below use the three character classes that actually broke:
em-dash, emoji, and Malay text carrying an em-dash.
"""

import pytest

from app.utils.text_escapes import (
    decode_html_escapes,
    decode_text_escapes,
    find_escape_leaks,
)

# Written as concatenations so the source of this file contains no real escape
# — the tests are about the two-character sequence backslash + "u".
B = chr(92)
EM_DASH = B + "u2014"
PHONE_EMOJI = B + "U0001f4f1"
SURROGATE_PAIR = B + "ud83d" + B + "udcf1"
E_ACUTE = B + "xe9"


class TestDecodesTheFormsThatShipped:
    def test_em_dash_four_hex_lowercase_u(self):
        assert decode_html_escapes(f"<p>Kedai {EM_DASH} Roti</p>") == (
            "<p>Kedai — Roti</p>",
            1,
        )

    def test_emoji_eight_hex_capital_u(self):
        """The Python-only form. JSON would emit a surrogate pair instead."""
        assert decode_html_escapes(f"<p>Hubungi {PHONE_EMOJI}</p>") == (
            "<p>Hubungi 📱</p>",
            1,
        )

    def test_surrogate_pair_becomes_one_emoji(self):
        decoded, count = decode_html_escapes(f"<p>{SURROGATE_PAIR}</p>")
        assert decoded == "<p>📱</p>"
        assert count == 1

    def test_hex_escape(self):
        assert decode_html_escapes(f"<p>caf{E_ACUTE}</p>") == ("<p>café</p>", 1)

    def test_malay_copy_with_an_em_dash(self):
        html = (
            f"<title>Warung Kak Ropiah {EM_DASH} Nasi Campur Shah Alam</title>"
            f'<meta name="description" content="Masakan rumah {EM_DASH} resipi '
            f'arwah ibu. Tempah melalui WhatsApp {PHONE_EMOJI}">'
        )
        decoded, count = decode_html_escapes(html)
        assert count == 3
        assert "Warung Kak Ropiah — Nasi Campur Shah Alam" in decoded
        assert "Masakan rumah — resipi arwah ibu" in decoded
        assert "WhatsApp 📱" in decoded
        assert find_escape_leaks(decoded) == []


class TestLeavesLegitimateEscapesAlone:
    def test_script_contents_are_untouched(self):
        """Inside <script> a backslash escape is source code. Rewriting one
        changes program behaviour and can smuggle a closing tag through."""
        html = (
            f"<p>a {EM_DASH} b</p>"
            f"<script>var s = '{B}u003cdiv{B}u003e';</script>"
            f"<p>c {EM_DASH} d</p>"
        )
        decoded, count = decode_html_escapes(html)
        assert count == 2
        assert f"'{B}u003cdiv{B}u003e'" in decoded
        assert "<div>" not in decoded
        assert decoded.count("—") == 2

    def test_style_contents_are_untouched(self):
        html = f"<style>.a::after{{content:'{B}u2014';}}</style><p>x {EM_DASH}</p>"
        decoded, count = decode_html_escapes(html)
        assert count == 1
        assert f"'{B}u2014'" in decoded

    def test_doubled_backslash_is_a_literal_backslash(self):
        """`\\\\u2014` is a backslash followed by "u2014", not an escape."""
        html = f"<p>{B}{B}u2014</p>"
        assert decode_html_escapes(html) == (html, 0)

    def test_control_characters_are_not_emitted(self):
        """Decoding a NUL or a form feed into markup corrupts it. Leave the
        sequence written and let the validator report it."""
        for token in ("u0000", "u000c", "u009f"):
            html = f"<p>{B}{token}</p>"
            assert decode_html_escapes(html) == (html, 0)

    def test_lone_surrogate_has_nothing_to_decode_to(self):
        html = f"<p>{B}ud83d alone</p>"
        assert decode_html_escapes(html) == (html, 0)

    def test_clean_html_is_returned_unchanged(self):
        html = "<p>Nasi Lemak — 📱 sedap</p>"
        assert decode_html_escapes(html) == (html, 0)

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_input(self, value):
        assert decode_html_escapes(value) == ("", 0)
        assert decode_text_escapes(value) == ("", 0)


class TestFindEscapeLeaks:
    def test_reports_a_snippet_not_just_the_token(self):
        html = f"<title>Kedai {EM_DASH} Roti</title>"
        leaks = find_escape_leaks(html)
        assert len(leaks) == 1
        assert EM_DASH in leaks[0]
        assert "Kedai" in leaks[0]

    def test_ignores_script_and_style(self):
        assert find_escape_leaks(f"<script>'{B}u2014'</script>") == []
        assert find_escape_leaks(f"<style>content:'{B}u2014'</style>") == []

    def test_reports_sequences_the_decoder_refuses(self):
        """A control-character escape is still a defect — it just cannot be
        repaired by decoding, so it must fail the gate instead."""
        assert find_escape_leaks(f"<p>{B}u0000</p>")

    def test_is_capped(self):
        html = "<p>" + (EM_DASH * 50) + "</p>"
        assert len(find_escape_leaks(html, limit=4)) == 4


class TestPlainTextDecode:
    def test_decodes_a_merchant_supplied_item_name(self):
        assert decode_text_escapes(f"Roti Canai {EM_DASH} Special") == (
            "Roti Canai — Special",
            1,
        )

    def test_leaves_a_clean_name_alone(self):
        assert decode_text_escapes("Nasi Campur Biasa") == ("Nasi Campur Biasa", 0)


class TestExtractHtmlBoundaryDecode:
    """The wiring: AIService._extract_html is the single funnel every
    provider's HTML passes through, so the decode belongs there and nowhere
    else. Without it a model that writes escapes ships them to the browser."""

    @pytest.fixture(scope="class")
    def service(self):
        import os

        os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
        os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
        from app.services.ai_service import AIService

        return AIService()

    def test_model_emitted_escapes_are_decoded(self, service):
        raw = (
            "```html\n"
            "<!DOCTYPE html><html lang=\"ms\"><head>"
            f"<title>Warung Kak Ropiah {EM_DASH} Nasi Campur</title>"
            f'<meta name="description" content="Masakan rumah {EM_DASH} tempah {PHONE_EMOJI}">'
            "</head><body><h1>Warung Kak Ropiah</h1></body></html>\n"
            "```"
        )
        html = service._extract_html(raw)
        assert "Warung Kak Ropiah — Nasi Campur" in html
        assert "Masakan rumah — tempah 📱" in html
        assert find_escape_leaks(html) == []

    def test_script_escapes_survive_extraction(self, service):
        raw = (
            "<!DOCTYPE html><html><head><title>A</title></head><body>"
            f"<script>var s = '{B}u003cbr{B}u003e';</script>"
            "</body></html>"
        )
        html = service._extract_html(raw)
        assert f"'{B}u003cbr{B}u003e'" in html

    def test_clean_output_is_unaffected(self, service):
        raw = (
            '<!DOCTYPE html><html lang="ms"><head><title>Warung — Nasi</title>'
            "</head><body><p>Sedap 📱</p></body></html>"
        )
        assert service._extract_html(raw) == raw
