"""Tests for subdomain injection-layer fixes (QR block + contact fallback)."""

from urllib.parse import quote

from app.middleware.subdomain import _build_published_url, _inject_qr_block


def test_published_url_is_real_subdomain_not_preview():
    url = _build_published_url("ali")
    assert url == "https://ali.binaapp.my"
    assert "preview" not in url


def test_qr_encodes_real_published_url_not_preview():
    # Simulate stored HTML that baked the preview URL into the QR block.
    stored = (
        "<html><body><footer>"
        '<!-- QR Code Section -->'
        '<div style="text-align:left;background:#f9fafb;">'
        "<h3>Scan to Visit</h3>"
        '<img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://preview.binaapp.my" alt="QR Code">'
        "</div>"
        "</footer></body></html>"
    )
    out = _inject_qr_block(stored, "ali", "ms")

    # Old preview-URL block is gone.
    assert "preview.binaapp.my" not in out
    # New block encodes the real published URL (URL-encoded).
    assert quote("https://ali.binaapp.my", safe="") in out
    # Exactly one QR image survives (no stacked blocks).
    assert out.count("api.qrserver.com") == 1


def test_qr_block_injected_inside_footer():
    out = _inject_qr_block("<body><footer>links</footer></body>", "ali", "ms")
    # Block must sit BEFORE the closing footer tag, never after it.
    footer_close = out.index("</footer>")
    qr_marker = out.index("BinaApp QR Block")
    assert qr_marker < footer_close


def test_qr_block_localized_bahasa():
    out_ms = _inject_qr_block("<footer></footer>", "ali", "ms")
    out_en = _inject_qr_block("<footer></footer>", "ali", "en")
    assert "Imbas untuk Lawat" in out_ms
    assert "Scan to Visit" in out_en


def test_qr_image_centered_via_margin_auto():
    out = _inject_qr_block("<footer></footer>", "ali", "ms")
    # Tailwind preflight sets img{display:block}; centering must be on the img.
    assert "margin:0 auto;display:block" in out


def test_qr_block_idempotent_no_stacking():
    html = "<footer></footer>"
    once = _inject_qr_block(html, "ali", "ms")
    twice = _inject_qr_block(once, "ali", "ms")
    assert twice.count("api.qrserver.com") == 1


def test_qr_falls_back_to_body_when_no_footer():
    out = _inject_qr_block("<body>content</body>", "ali", "ms")
    assert "BinaApp QR Block" in out
    assert out.index("BinaApp QR Block") < out.index("</body>")
