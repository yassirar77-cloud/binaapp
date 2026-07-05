"""Tests for wa.me link normalization (digits-only, no '+')."""

from app.services.ai_service import AIService


def test_strips_leading_plus():
    out = AIService._normalize_wa_links('<a href="https://wa.me/+60123456789">chat</a>')
    assert "wa.me/60123456789" in out
    assert "wa.me/+" not in out


def test_preserves_query_string():
    src = '<a href="https://wa.me/+60123456789?text=Hi%20there">x</a>'
    out = AIService._normalize_wa_links(src)
    assert "wa.me/60123456789?text=Hi%20there" in out


def test_strips_spaces_and_dashes():
    out = AIService._normalize_wa_links('<a href="https://wa.me/60 12-345 6789">x</a>')
    assert "wa.me/60123456789" in out


def test_mixed_forms_all_normalized():
    src = 'a wa.me/+60123456789 b https://wa.me/60123456789 c'
    out = AIService._normalize_wa_links(src)
    assert out.count("wa.me/60123456789") == 2
    assert "+" not in out


def test_no_wa_link_untouched():
    src = "<p>no whatsapp here</p>"
    assert AIService._normalize_wa_links(src) == src


def test_stops_at_quote_boundary():
    src = '<a href="https://wa.me/60123456789"><span>1</span></a>'
    out = AIService._normalize_wa_links(src)
    assert 'wa.me/60123456789"' in out
    # The '1' inside the span must not be absorbed into the phone number.
    assert "601234567891" not in out
