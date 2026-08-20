"""Regression tests for replace_template_placeholders' WhatsApp handling.

The floating WhatsApp button is injected BEFORE replace_template_placeholders
runs, using the '+60123456789' fallback when the delivery config has no phone.
The old normalization only matched wa.me/<digits>, so the '+60...' link slipped
through and the plain default-number replaces swapped in the RAW user phone —
publishing links like wa.me/019-5551234, which WhatsApp rejects (it requires
the international digits-only form).
"""

import pytest

from app.main import replace_template_placeholders


def test_injected_plus_default_becomes_international_digits():
    """The exact production bug: '+60...' default in the injected button plus a
    raw local phone extracted from the description."""
    html = (
        '<html><body>'
        '<a href="https://wa.me/+60123456789?text=Assalamualaikum,%20saya%20berminat" '
        'id="whatsapp-button">WA</a>'
        '</body></html>'
    )
    out = replace_template_placeholders(
        html, {"description": "Telefon 019-5551234. Buka 7am-11pm."}
    )
    assert 'wa.me/60195551234?text=' in out
    assert 'wa.me/+' not in out
    assert 'wa.me/019' not in out


def test_digits_only_default_still_rewritten():
    html = '<a href="https://wa.me/60123456789?text=hi">Pesan</a>'
    out = replace_template_placeholders(html, {"phone": "0195551234"})
    assert 'wa.me/60195551234?text=hi' in out


def test_phone_with_spaces_and_plus_normalized():
    html = '<a href="https://wa.me/+60123456789">Pesan</a>'
    out = replace_template_placeholders(html, {"phone": "+60 19-555 1234"})
    assert 'wa.me/60195551234' in out


def test_display_text_keeps_raw_phone():
    """Visible text should show the user's own formatting; only the wa.me
    path segment is forced to digits."""
    html = '<p>Hubungi +60123456789</p><a href="https://wa.me/+60123456789">WA</a>'
    out = replace_template_placeholders(html, {"phone": "019-5551234"})
    assert 'Hubungi 019-5551234' in out
    assert 'wa.me/60195551234' in out


def test_no_phone_leaves_links_untouched():
    html = '<a href="https://wa.me/+60123456789">WA</a>'
    out = replace_template_placeholders(html, {"description": "Kedai makan di Penang"})
    assert 'wa.me/+60123456789' in out
