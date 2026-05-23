"""Tests for app.services.html_repair.

Covers the publish-flow auto-repair pass that runs before is_html_balanced.
Stacked behaviour: this module is the "permissive parse + re-serialize" step;
the existing html_balance scrub still runs inside the validator and after the
repair the validator should accept the output.
"""

from __future__ import annotations

import os
import re
from unittest.mock import patch

import pytest

from app.services.html_repair import repair_html
from app.utils.html_balance import is_html_balanced


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_validates(html: str) -> None:
    ok, unbalanced = is_html_balanced(html)
    assert ok, f"Validator still rejects repaired HTML: {unbalanced}"


# ---------------------------------------------------------------------------
# Basic repair behaviour
# ---------------------------------------------------------------------------

def test_unclosed_div_gets_closed():
    raw = "<html><body><div><p>hello</p></body></html>"
    repaired, info = repair_html(raw)
    assert info["skipped"] is False
    assert "</div>" in repaired
    _assert_validates(repaired)


def test_extra_section_closing_gets_removed():
    raw = (
        "<html><body><section><p>hi</p></section></section>"
        "</body></html>"
    )
    repaired, info = repair_html(raw)
    assert info["skipped"] is False
    # html5lib silently drops the stray </section>; net result must validate.
    _assert_validates(repaired)


def test_missing_body_opening_gets_added():
    raw = (
        "<!DOCTYPE html><html><head><title>x</title></head>"
        "<div>floating content</div></html>"
    )
    repaired, info = repair_html(raw)
    assert info["skipped"] is False
    assert info["added_missing_body"] is True
    assert "<body" in repaired.lower()
    _assert_validates(repaired)


def test_missing_html_wrapper_gets_added():
    raw = "<div>no wrapper at all</div>"
    repaired, info = repair_html(raw)
    assert info["skipped"] is False
    assert info["added_missing_html"] is True
    assert "<html" in repaired.lower()
    assert "<body" in repaired.lower()
    _assert_validates(repaired)


# ---------------------------------------------------------------------------
# Script/style content must be left alone
# ---------------------------------------------------------------------------

def test_style_with_unbalanced_braces_in_css_not_touched():
    css_body = "\n.foo { color: red;\n.bar:before { content: '<span>'; }\n"
    raw = (
        f"<html><head><style>{css_body}</style></head>"
        "<body><div>x</div></body></html>"
    )
    repaired, info = repair_html(raw)
    style_out = re.search(r"<style[^>]*>(.*?)</style>", repaired, re.DOTALL)
    assert style_out is not None, "Style block dropped by repair"
    assert style_out.group(1) == css_body, (
        "Style body was modified by repair pass"
    )


def test_script_with_angle_brackets_in_strings_not_touched():
    js_body = (
        '\nconst x = "<div>not real html</div>";\n'
        "if (a < b && c > d) { console.log('ok'); }\n"
        'const tag = "<script>nested</script>";\n'
    )
    raw = (
        "<html><body><div>x</div>"
        f"<script>{js_body}</script></body></html>"
    )
    repaired, info = repair_html(raw)
    # html5lib's raw-data handling stops <script> at the first literal
    # </script>, which is the HTML5 spec behaviour. We assert the JS that
    # comes before that boundary is preserved verbatim.
    boundary = js_body.find("</script>")
    expected_prefix = js_body[:boundary] if boundary >= 0 else js_body
    script_out = re.search(r"<script[^>]*>(.*?)</script>", repaired, re.DOTALL)
    assert script_out is not None, "Script block dropped by repair"
    assert script_out.group(1).startswith(expected_prefix), (
        "Script body diverged before the first </script> token"
    )


def test_inline_event_handlers_and_data_attrs_preserved():
    raw = (
        '<html><body>'
        '<div id="binaapp-maps-slot" class="map-wrapper" data-widget="maps">'
        '<a href="#x" onclick="track(\'cta\')" data-track="cta">Buy</a>'
        '<button id="binaapp-contact-slot" onmouseover="this.foo=1">B</button>'
        '</div></body></html>'
    )
    repaired, _ = repair_html(raw)
    assert 'id="binaapp-maps-slot"' in repaired
    assert 'id="binaapp-contact-slot"' in repaired
    assert 'class="map-wrapper"' in repaired
    assert 'data-widget="maps"' in repaired
    assert 'data-track="cta"' in repaired
    assert "onclick=" in repaired
    assert "onmouseover=" in repaired


# ---------------------------------------------------------------------------
# Idempotence and feature flag
# ---------------------------------------------------------------------------

def test_already_valid_html_is_idempotent():
    raw = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/>"
        "<title>X</title></head><body><div class=\"a\">"
        "<p>hello</p></div></body></html>"
    )
    repaired_once, info = repair_html(raw)
    repaired_twice, _ = repair_html(repaired_once)
    assert repaired_once == repaired_twice
    assert info["closed_unclosed_tags"] == 0
    assert info["removed_extra_closings"] == 0
    _assert_validates(repaired_once)


def test_feature_flag_off_returns_input_unchanged():
    raw = "<html><body><div><p>oops"  # very broken
    with patch.dict(os.environ, {"HTML_AUTO_REPAIR_ENABLED": "false"}):
        repaired, info = repair_html(raw)
    assert info["skipped"] is True
    assert info["skipped_reason"] == "feature_flag_off"
    assert repaired == raw


def test_feature_flag_off_variants():
    raw = "<html><body><div><p>oops"
    for v in ("0", "false", "no", "off", "False", "OFF"):
        with patch.dict(os.environ, {"HTML_AUTO_REPAIR_ENABLED": v}):
            _, info = repair_html(raw)
            assert info["skipped"] is True, f"Flag '{v}' should disable repair"


def test_feature_flag_default_on():
    raw = "<html><body><div><p>x</p></body></html>"  # unclosed div
    env = {k: v for k, v in os.environ.items() if k != "HTML_AUTO_REPAIR_ENABLED"}
    with patch.dict(os.environ, env, clear=True):
        repaired, info = repair_html(raw)
    assert info["skipped"] is False
    _assert_validates(repaired)


# ---------------------------------------------------------------------------
# Catastrophic input — must NOT be silently "fixed" into valid HTML
# ---------------------------------------------------------------------------

def test_random_text_no_tags_is_left_for_validator():
    raw = "Just some text with no markup at all"
    repaired, info = repair_html(raw)
    assert info["skipped"] is True
    assert info["skipped_reason"] == "no_html_tags"
    assert repaired == raw
    # Validator still rejects it — the spec requirement.
    ok, _ = is_html_balanced(repaired)
    assert ok is False


def test_empty_input_skipped():
    repaired, info = repair_html("")
    assert info["skipped"] is True
    assert repaired == ""


# ---------------------------------------------------------------------------
# Real-world malformed sample (the failure mode that motivated PR #668)
# ---------------------------------------------------------------------------

# Captures the recurring failure mode: AI emits multiple nested <section>/<div>
# blocks but drops several intermediate closers. Validator surfaces 6 unclosed
# tags (section, div, section, div, div, div). The repair pass must
# auto-close them while preserving CSS, JS, and the binaapp-*-slot id.
MALFORMED_PRODUCTION_SAMPLE = """<!DOCTYPE html>
<html lang="ms">
<head>
<meta charset="utf-8">
<title>Kedai Burger Rizal</title>
<style>
body { font-family: sans-serif; margin: 0; }
.hero { background: #ea580c; padding: 40px;
.menu-item:before { content: '<>'; }
</style>
</head>
<body>
<section class="hero">
<h1>Burger Sedap</h1>
<div class="container">
<p>Selamat datang</p>
<section id="menu">
<h2>Menu Kami</h2>
<div class="menu-grid">
<div class="menu-item"><h3>Cheese Burger</h3><p>RM 12</p></div>
<div class="menu-item"><h3>Beef Burger</h3><p>RM 15</p>
<div class="menu-item"><h3>Chicken Burger</h3>
<section id="binaapp-contact-slot">
<a href="#" onclick="alert('hi')">Hubungi</a>
</section>
<script>
const items = ["<div>", "</div>"];
if (1 < 2 && 3 > 0) console.log("ok");
</script>
</body>
</html>"""


def test_real_malformed_sample_repairs_to_valid():
    raw = MALFORMED_PRODUCTION_SAMPLE
    ok_before, unbalanced_before = is_html_balanced(raw)
    assert not ok_before, (
        "Fixture is supposed to be malformed; got balanced. "
        "Update the fixture to reflect a real failing case."
    )
    repaired, info = repair_html(raw, context="kedai-burger-rizal")
    assert info["skipped"] is False
    _assert_validates(repaired)
    # Spot-check: ID we care about (widget slot from PR #665) is preserved.
    assert 'id="binaapp-contact-slot"' in repaired
    # Script and style bodies still present.
    assert 'console.log("ok")' in repaired
    assert "font-family: sans-serif" in repaired


# ---------------------------------------------------------------------------
# Reporting shape
# ---------------------------------------------------------------------------

def test_repairs_dict_has_expected_keys():
    raw = "<html><body><div><p>hi</p></body></html>"
    _, info = repair_html(raw)
    for key in (
        "skipped",
        "closed_unclosed_tags",
        "removed_extra_closings",
        "added_missing_body",
        "added_missing_html",
        "size_delta_pct",
        "before_length",
        "after_length",
    ):
        assert key in info, f"Repair dict missing key: {key}"


def test_size_delta_warning_threshold_logged(caplog):
    # Tiny input that html5lib will wrap aggressively — >30% growth.
    raw = "<div>x</div>"
    with caplog.at_level("WARNING", logger="app.services.html_repair"):
        _, info = repair_html(raw, context="tiny")
    assert info["size_delta_pct"] > 30.0
    assert any("size delta" in rec.message.lower() for rec in caplog.records)
