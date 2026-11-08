"""Stage 1 of the quality system: deterministic sections.

Every structural section is rendered by code from the merchant's data; the
model contributes only the theme (through the plan) and the copy. These
tests pin the contract: the page carries every fact, every CTA has an icon
and a label, the theme is contrast-repaired, invented copy is rejected and
the freeform pipeline stays behind the flag.
"""

from __future__ import annotations

import asyncio
import json
import os
import re

import pytest

from app.models.schemas import WebsiteGenerationRequest
from app.services import menu_fidelity as mf
from app.services.sections import build_spec, compose_page, fallback_copy, theme_from_plan
from app.services.sections.compose import is_composed, section_order
from app.services.sections.copy import LIMITS, build_copy_prompt, parse_copy, suspicious
from app.services.sections.render import town_of
from app.services.sections.theme import default_theme, render_css, variant_for
from app.services.theme_patcher import contrast_ratio

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ayam_gepuk_panglima_menu.json")
AGP_BRIEF = (
    "Ayam Gepuk Panglima di Klang. Ayam gepuk sambal pedas, dihidang dengan nasi, tauhu, tempe. "
    "Spice Level 1 Spicy / Level 2 Hot / Level 3 Extra Hot. FREE refill nasi & sambal (dine-in sahaja). "
    "Take away caj RM2.00.\nComing soon: Bakso Daging, Nasi Lemak, Kangkung Goreng."
)
ADDRESS = "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor"


@pytest.fixture(scope="module")
def panglima():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)


def _request(panglima, **over):
    base = dict(
        description=AGP_BRIEF, business_name="Ayam Gepuk Panglima", business_type="food", subdomain="agp",
        whatsapp_number="0126973105", location_address=ADDRESS, menu_items=panglima["menu_items"],
        opening_hours="11 pagi - 10 malam", payment_methods=["cod", "qr"],
    )
    base.update(over)
    return WebsiteGenerationRequest(**base)


def _visible(html: str) -> str:
    import html as _h
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", text)))


def _compose(panglima, **over):
    req = _request(panglima, **over)
    spec = build_spec(req, image_urls={"hero": "https://res.cloudinary.com/x/image/upload/hero.jpg"},
                      ai_image_urls={"https://res.cloudinary.com/x/image/upload/hero.jpg"})
    theme = theme_from_plan(None)
    copy = fallback_copy(spec)
    html = compose_page(spec, theme, copy)
    block = mf.render_menu_block(spec.items, language="ms", wa_digits=spec.wa_digits, order_prefill="saya nak order")
    html, filled = mf.fill_menu_slot(html, block)
    assert filled
    return spec, theme, copy, html


# ---------------------------------------------------------------------------
# Spec: the merchant's facts become structured sections
# ---------------------------------------------------------------------------

def test_spec_extracts_levels_banners_and_coming_soon(panglima):
    spec = build_spec(_request(panglima))
    assert [c.label for c in spec.option_chips] == ["Level 1 · Spicy", "Level 2 · Hot", "Level 3 · Extra Hot"]
    assert [b.kind for b in spec.banners] == ["refill", "charge"]
    assert spec.banners[1].title == "Bungkus"
    assert spec.coming_soon == ["Bakso Daging", "Nasi Lemak", "Kangkung Goreng"]
    assert spec.wa_digits == "60126973105" and spec.phone_display == "012-697 3105"
    assert spec.is_food and len(spec.items) == 32


def test_spec_poster_upload_never_becomes_hero(panglima):
    poster = "https://res.cloudinary.com/x/image/upload/board.jpg"
    spec = build_spec(_request(panglima), image_urls={"hero": poster}, poster_urls=[poster])
    assert spec.hero_url == ""


def test_town_of_address():
    assert town_of(ADDRESS) == "Klang"
    assert town_of("12 Jalan SS2/24, 47300 Petaling Jaya, Selangor") == "Petaling Jaya"
    assert town_of("Klang") == ""


# ---------------------------------------------------------------------------
# Composed page
# ---------------------------------------------------------------------------

def test_composed_page_carries_every_fact_and_item(panglima):
    spec, theme, copy, html = _compose(panglima)
    text = _visible(html)
    assert is_composed(html)
    for it in panglima["menu_items"]:
        assert it["name"] in text, it["name"]
        assert f"RM{it['price']}" in text
    for cat in ("Set Ayam", "Set Seafood Krispy", "Tambahan", "Minuman", "Special Drink", "Kid's Menu"):
        assert cat in text
    assert "Level 1 · Spicy" in text and "Level 3 · Extra Hot" in text
    assert "FREE refill nasi & sambal" in text and "Take away caj RM2.00" in text
    assert "Bakso Daging" in text and "Akan datang" in text
    assert ADDRESS in text and "11 pagi - 10 malam" in text
    assert 'href="tel:+60126973105"' in html
    assert "wa.me/60126973105" in html
    assert 'id="binaapp-maps-slot"' in html and 'id="binaapp-contact-slot"' in html
    assert "{{" not in html and "[ISI" not in html
    # Section order for a restaurant
    assert section_order(spec) == ["nav", "hero", "options", "banners", "menu", "coming_soon", "about", "location", "contact", "footer"]
    for sec_id in ("home", "options", "info", "menu", "coming-soon", "about", "location", "contact", "footer"):
        assert f'id="{sec_id}"' in html, sec_id


def test_every_cta_has_icon_and_label(panglima):
    _, _, _, html = _compose(panglima)
    buttons = re.findall(r'<a class="bs-btn[^"]*"[^>]*>(.*?)</a>', html, flags=re.S)
    assert len(buttons) >= 5
    for inner in buttons:
        assert "<svg" in inner, inner[:80]
        assert re.sub(r"<[^>]+>", "", inner).strip(), "button without a label"


def test_about_text_does_not_repeat_rendered_facts(panglima):
    spec, _, copy, _ = _compose(panglima)
    about = " ".join(copy.about_paragraphs)
    assert "refill" not in about.lower() and "RM2.00" not in about and "Coming soon" not in about
    assert "nasi" in about


def test_hero_image_and_ai_label(panglima):
    _, _, _, html = _compose(panglima)
    hero = re.search(r'<section class="bs-hero"[^>]*>(.*?)</section>', html, flags=re.S).group(1)
    assert "bs-hero-media" in hero and "Gambar hiasan" in hero
    assert "Pesan di WhatsApp" in hero and "Lihat menu" in hero


def test_no_hero_image_gives_solid_hero(panglima):
    req = _request(panglima)
    spec = build_spec(req)
    html = compose_page(spec, theme_from_plan(None), fallback_copy(spec))
    assert 'class="bs-hero bs-hero-solid"' in html and 'class="bs-hero-media"' not in html


def test_non_food_vertical_order_and_words(panglima):
    req = _request(panglima, business_type="salon", description="Salon rambut wanita di Shah Alam. Gunting, warna, rebonding.",
                   menu_items=[{"name": "Gunting Rambut", "price": "35"}, {"name": "Rebonding", "price": "180"}])
    spec = build_spec(req)
    assert spec.vertical == "salon" and not spec.option_chips and not spec.banners
    html = compose_page(spec, theme_from_plan(None), fallback_copy(spec))
    assert section_order(spec)[:3] == ["nav", "hero", "banners"]
    text = _visible(html)
    assert "Servis & Harga" in text and "Lihat servis" in text and "WhatsApp Kami" in text


def test_english_strings(panglima):
    req = _request(panglima, language="en")
    spec = build_spec(req)
    html = compose_page(spec, theme_from_plan(None), fallback_copy(spec))
    assert 'lang="en"' in html and "Order on WhatsApp" in html and "Coming soon" in html and "Spice level" in html


# ---------------------------------------------------------------------------
# Theme: contrast repaired once, variants from the plan
# ---------------------------------------------------------------------------

def test_theme_primary_is_the_plan_accent_not_the_darkened_secondary():
    plan = {"palette": {"bg": "#FFF7E6", "surface": "#FFFFFF", "text": "#1A120B", "muted": "#6B5F55",
                        "accent": "#C81E1E", "accent_2": "#F5B700"}, "type": {"display": "Anton", "body": "Inter"},
            "direction": "halal_street", "theme": "bright"}
    theme = theme_from_plan(plan)
    assert theme.primary.upper() == "#C81E1E"          # chilli red, never mustard
    assert theme.variant == "outline" and theme.display_font == "Anton"
    css = render_css(theme)
    assert "--primary-color:#C81E1E" in css and "--font-heading:'Anton'" in css


def test_theme_contrast_repair_on_every_surface():
    plan = {"palette": {"bg": "#FFFFFF", "surface": "#F5F5F5", "text": "#BBBBBB", "muted": "#CCCCCC",
                        "accent": "#FFD700", "accent_2": "#FFEE88"}, "type": {}, "direction": "warung_cerah"}
    theme = theme_from_plan(plan)
    for fg in (theme.text, theme.muted, theme.primary):
        for bg in (theme.bg, theme.surface):
            assert contrast_ratio(fg, bg) >= 4.5, (fg, bg)
    assert contrast_ratio(theme.on_primary, theme.primary) >= 4.5
    assert theme.repairs


def test_theme_dark_mode_rejects_a_cream_page():
    plan = {"palette": {"bg": "#FFF7E6", "surface": "#FFFFFF", "text": "#1A120B", "muted": "#6B5F55",
                        "accent": "#C81E1E", "accent_2": "#F5B700"}, "type": {}, "direction": "malam_bandar", "theme": "dark"}
    theme = theme_from_plan(plan, color_mode="dark")
    assert theme.dark and theme.bg == "#141210" and "dark mode: neutrals replaced" in theme.repairs


def test_variant_from_style_and_direction():
    assert variant_for("", "bold") == "outline"
    assert variant_for("", "elegant") == "editorial"
    assert variant_for("coret_ceria") == "outline"
    assert variant_for("mewah_cerah") == "editorial"
    assert variant_for("warung_cerah") == "soft"
    assert default_theme().variant == "soft"


def test_css_has_no_horizontal_overflow_risks():
    css = render_css(default_theme())
    assert "overflow-x:hidden" in css and "max-width:100%" in css and "overflow-wrap:anywhere" in css
    assert "flex-wrap:wrap" in css


# ---------------------------------------------------------------------------
# Copy: validated, capped, never invented
# ---------------------------------------------------------------------------

def test_copy_parse_rejects_invented_facts_and_strips_html(panglima):
    spec = build_spec(_request(panglima))
    raw = json.dumps({
        "kicker": "Restoran · Klang", "headline": "Pedas Sampai Nangis", "subheadline": "Sejak 2015 kami hidang ayam gepuk.",
        "about_paragraphs": ["Harga dari RM99.90 sahaja.", "Dinilai 4.9/5 oleh 2000 pelanggan.", "Kami buka di Klang setiap hari."],
        "tagline": "Pedas <b>betul</b>", "contact_lead": "Hubungi 013-9999999 sekarang", "menu_lead": "Pilih set anda",
    })
    copy = parse_copy(raw, spec)
    assert copy.headline == "Pedas Sampai Nangis"
    assert copy.subheadline != "Sejak 2015 kami hidang ayam gepuk."           # invented year → fallback
    assert copy.about_paragraphs == ["Kami buka di Klang setiap hari."]        # invented price + rating dropped
    assert copy.tagline == "Pedas betul"
    assert "013" not in copy.contact_lead                                      # invented phone → fallback
    assert copy.source == "mixed" and len(copy.rejected) >= 4


def test_copy_caps_length_and_handles_garbage(panglima):
    spec = build_spec(_request(panglima))
    long = json.dumps({"headline": "x" * 500, "about_paragraphs": "one paragraph as a string"})
    copy = parse_copy(long, spec)
    assert len(copy.headline) <= LIMITS["headline"] + 1 and copy.about_paragraphs == ["one paragraph as a string"]
    assert parse_copy("not json at all", spec).source == "fallback"
    assert parse_copy(None, spec).source == "fallback"
    assert suspicious("Take away caj RM2.00", spec) is None                    # the brief's own amount is fine
    assert suspicious("{{BUSINESS_NAME}}", spec) == "placeholder"


def test_copy_prompt_carries_only_merchant_facts(panglima):
    spec = build_spec(_request(panglima))
    prompt = build_copy_prompt(spec)
    assert "Ayam Gepuk Panglima" in prompt and "Set A – Ayam Gepuk" in prompt
    assert "the only source of facts" in prompt
    assert "RM" not in prompt.split("Merchant's brief")[0]  # no prices are fed to the copywriter


# ---------------------------------------------------------------------------
# Pipeline: the flag, the composed path, composed previews
# ---------------------------------------------------------------------------

def test_page_mode_flag(monkeypatch):
    from app.services import ai_service as svc
    monkeypatch.delenv("BINAAPP_PAGE_MODE", raising=False)
    assert svc.page_mode() == svc.PAGE_MODE_DETERMINISTIC
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "freeform")
    assert svc.page_mode() == svc.PAGE_MODE_FREEFORM
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "nonsense")
    assert svc.page_mode() == svc.PAGE_MODE_DETERMINISTIC


def test_generate_website_composes_without_any_model(panglima, monkeypatch):
    """No API keys: plan falls back to the library, copy to the fallback,
    and the page still carries every item, validates clean and never
    calls the HTML model."""
    from app.services import ai_service as svc
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "deterministic")
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "false")
    service = svc.AIService()
    service.deepseek_api_key = service.zai_api_key = service.qwen_api_key = ""

    async def _boom(*a, **k):  # the HTML model must never be asked
        raise AssertionError("freeform HTML model called in deterministic mode")
    monkeypatch.setattr(service, "_call_deepseek", _boom)
    monkeypatch.setattr(service, "_call_glm", _boom)
    monkeypatch.setattr(service, "_call_qwen", _boom)

    progress = []

    async def _p(pct, msg):
        progress.append((pct, msg))

    resp = asyncio.run(service.generate_website(_request(panglima), image_choice="none", progress_callback=_p))
    html = resp.html_content
    assert is_composed(html) and resp.validation_ok, resp.validation_errors
    assert resp.menu_fidelity["composed"] and resp.menu_fidelity["matched"] == 32
    assert "Writing the copy" in [m for _, m in progress] and "Composing the page" in [m for _, m in progress]
    text = _visible(html)
    assert "Set Panglima Signature – Ayam Gepuk Telur Mata" in text and "SIGNATURE" in text
    assert "Take away caj RM2.00" in text and "Level 2 · Hot" in text
    assert 'name="theme-color"' in html and 'rel="icon"' in html          # branding ran
    assert "application/ld+json" in html                                  # SEO ran
    assert service._last_copy["source"] == "fallback" and service._last_theme["source"] == "fallback"


def test_generate_plan_variants_composes_each_theme(panglima, monkeypatch):
    from app.services import ai_service as svc
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "deterministic")
    service = svc.AIService()
    service.deepseek_api_key = service.zai_api_key = service.qwen_api_key = ""
    variants = asyncio.run(service.generate_plan_variants(_request(panglima), image_choice="none"))
    assert len(variants) == 3
    assert len({v["style"] for v in variants}) == 3
    for v in variants:
        assert is_composed(v["html"]) and v["lint"]["composed"] and "theme" in v
        assert "Set A – Ayam Gepuk" in _visible(v["html"])


def test_freeform_mode_still_builds_the_prompt(panglima, monkeypatch):
    """The pre-stage-1 pipeline is intact behind the flag: with
    BINAAPP_PAGE_MODE=freeform the HTML model IS asked."""
    from app.services import ai_service as svc
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "freeform")
    monkeypatch.setenv("DESIGN_CRITIQUE_ENABLED", "false")
    service = svc.AIService()
    service.deepseek_api_key, service.zai_api_key, service.qwen_api_key = "k", "", ""
    calls = []

    async def _html(prompt, *a, **k):
        calls.append(prompt)
        return "<!DOCTYPE html><html><head><title>t</title></head><body><section id='home'><h1>Ayam Gepuk Panglima</h1></section><section id='menu'><div id='binaapp-menu-slot'></div></section><footer>f</footer></body></html>"
    monkeypatch.setattr(service, "_call_deepseek", _html)
    resp = asyncio.run(service.generate_website(_request(panglima), image_choice="none"))
    assert calls, "freeform mode must call the HTML model"
    assert not is_composed(resp.html_content)


@pytest.mark.skipif(not os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE") and not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")), reason="no browser")
def test_composed_page_has_no_mobile_overflow(panglima):
    from app.services.design_critique import render_screenshots
    _, _, _, html = _compose(panglima)
    bundle = asyncio.run(render_screenshots(html))
    if bundle.error:
        pytest.skip(bundle.error)
    assert not bundle.mobile_overflow, bundle.mobile_scroll_width
    assert bundle.hero_font_px >= 28
