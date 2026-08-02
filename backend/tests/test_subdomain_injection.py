"""Tests for subdomain injection-layer fixes (QR block + contact fallback)."""

from app.middleware.subdomain import _build_published_url, _inject_qr_block
from app.services.qr_service import qr_data_uri


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
    # The served QR is the offline render of the REAL published URL.
    assert qr_data_uri("https://ali.binaapp.my", scale=6, border=2, dark="#111827") in out
    # Exactly one QR image survives (no stacked blocks).
    assert out.count("BinaApp QR Block") == 1


def test_qr_is_rendered_offline_not_fetched_from_a_third_party():
    # Every pageview used to hit api.qrserver.com for this image. It must not.
    out = _inject_qr_block("<footer></footer>", "ali", "ms")
    assert "api.qrserver.com" not in out
    assert "data:image/svg+xml;base64," in out


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
    assert twice.count("BinaApp QR Block") == 1
    assert twice.count("data:image/svg+xml;base64,") == 1


def test_qr_falls_back_to_body_when_no_footer():
    out = _inject_qr_block("<body>content</body>", "ali", "ms")
    assert "BinaApp QR Block" in out
    assert out.index("BinaApp QR Block") < out.index("</body>")


# ── blank-page regression (ertyu.binaapp.my) ─────────────────────────────────
# A published site rendered as a completely blank white page: the contact-slot
# fallback resolved the "card to hide" to <body> (slot emitted as a direct
# body child + no wa.me link on the page) and set body.style.display='none'.
# Secondarily, the AOS guard armed opacity-0 rules immediately after AOS.init
# with !important, so a stalled AOS pipeline (slow connections) kept sections
# invisible with no possible CSS rescue.

def test_contact_slot_fallback_never_hides_page_container():
    """The hide branch must special-case body/html/main and hide only the
    slot itself — hiding the resolved 'card' blanked the whole page."""
    from app.middleware.subdomain import _CONTACT_SLOT_FALLBACK_SCRIPT
    script = _CONTACT_SLOT_FALLBACK_SCRIPT
    assert "isPageContainer" in script
    assert "document.body" in script and "document.documentElement" in script
    # the old unconditional hide must be gone
    assert "if(card) card.style.display = 'none';" not in script


def test_aos_guard_has_rescue_and_no_important_trap():
    """The AOS block must (a) carry the 2.5s rescue animation that forces
    stalled elements visible, and (b) avoid !important — a keyframe animation
    can never override an author !important declaration, so the old
    opacity:0 !important rule made the rescue impossible."""
    from app.services.templates import TemplateService
    css = TemplateService.LAYOUT_SAFETY_CSS
    aos_block = css.split("/* (a) AOS fallback")[1].split("/* (b1)")[0]
    assert "binaapp-aos-rescue" in aos_block
    assert "@keyframes binaapp-aos-rescue" in aos_block
    assert "!important" not in aos_block
    # tripled attribute selector out-specifies aos.css 2.x and 3.x hide rules
    assert "[data-aos][data-aos][data-aos]" in aos_block


def test_layout_safety_guard_self_upgrades_served_pages():
    """apply_layout_safety_guard must replace an OLD baked guard block so the
    AOS fix reaches already-published sites at serve time."""
    from app.services.templates import TemplateService
    svc = TemplateService()
    old_page = (
        "<html><head><!-- BinaApp Layout Safety Guard -->"
        '<style id="binaapp-layout-safety">html [data-aos] '
        "{ opacity: 1 !important; }</style></head>"
        '<body><section data-aos="fade-up">hi</section></body></html>'
    )
    out = svc.apply_layout_safety_guard(old_page)
    assert out.count('id="binaapp-layout-safety"') == 1
    assert "binaapp-aos-rescue" in out
    assert "{ opacity: 1 !important; }" not in out
