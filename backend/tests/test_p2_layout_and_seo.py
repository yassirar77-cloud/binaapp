"""P2: layout guard additions, light hero, mobile CTA, JSON-LD address."""

import json

from app.services.hero_scrim import panel_classes_for, soften_light_hero
from app.services.mobile_nav import ensure_mobile_nav_cta
from app.services.seo_metadata import SeoMeta, build_json_ld, postal_address
from app.services.templates import TemplateService


def test_layout_guard_centres_paragraphs_fixes_footer_text_and_menu_orphans_and_judges_the_footer():
    css = TemplateService.LAYOUT_SAFETY_CSS
    assert ".text-center p, p.text-center, [class*=\"text-center\"] > p" in css
    assert "margin-left: auto; margin-right: auto;" in css
    assert "footer p, footer li, footer dd, footer dt, footer small, footer address { color: inherit; }" in css
    assert ':last-child:nth-child(3n+1) { grid-column: 2 / 3; }' in css
    assert "querySelectorAll('header,body>nav,footer')" in TemplateService.NAV_CONTRAST_GUARD_JS
    out = TemplateService().apply_layout_safety_guard("<html><head></head><body></body></html>")
    assert out.count("binaapp-layout-safety") == 1


HERO = (
    '<section id="hero" class="relative min-h-[70vh]"><img src="h.jpg" class="absolute inset-0 object-cover">'
    '<div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/60 to-transparent"></div>'
    '<div class="absolute inset-0" style="background:linear-gradient(to top, rgba(0,0,0,0.85), transparent)"></div>'
    '<div class="relative bg-black p-8 rounded-2xl"><h1 class="text-white">Ayam Gepuk Panglima</h1><p class="text-white/80">Makin pedas</p></div>'
    '</section><section id="menu"><div class="bg-black text-white">stays</div></section>'
)


def test_light_hero_caps_the_scrim_and_recolours_the_panel():
    out, rep = soften_light_hero(HERO, "#C8321A")  # red: white text passes AA
    hero = out[: out.index('<section id="menu"')]
    assert "from-black/45" in hero and "via-black/45" in hero and "from-black/90" not in hero
    assert "rgba(0,0,0,0.45)" in hero and "0.85" not in hero
    assert 'class="relative bg-[#C8321A]/90 backdrop-blur-sm p-8 rounded-2xl"' in hero
    assert 'class="text-white">Ayam' in hero  # light text kept on the brand panel
    assert rep.scrims_capped == 3 and rep.panels_recoloured == 1
    assert 'class="bg-black text-white">stays' in out  # outside the hero: untouched


def test_light_hero_uses_a_white_panel_with_dark_text_for_a_pale_brand():
    assert panel_classes_for("#FBEB02") == ("bg-white/90 backdrop-blur-sm", False)
    out, rep = soften_light_hero(HERO, "#FBEB02")
    hero = out[: out.index('<section id="menu"')]
    assert "bg-white/90 backdrop-blur-sm" in hero and "text-neutral-900" in hero and 'class="text-white"' not in hero


def test_already_light_hero_is_untouched():
    html = '<section id="hero"><div class="bg-gradient-to-t from-black/40 to-transparent"></div><div class="bg-white/90"><h1>x</h1></div></section>'
    out, rep = soften_light_hero(html, "#C8321A")
    assert out == html and not rep.changed


MOBILE = (
    '<header><nav><a href="#home">Home</a><a href="https://wa.me/60126973105?text=Assalamualaikum%2C%20saya%20nak%20order" class="btn-primary hidden md:inline-flex">Pesan</a>'
    '<button id="mobile-menu-button">≡</button></nav>'
    '<div class="mobile-menu-panel md:hidden" id="mobile-menu-panel"><a href="#home">Home</a><a href="#menu">Menu</a></div></header>'
)


def test_mobile_panel_gets_the_header_cta_when_it_has_none():
    out, added = ensure_mobile_nav_cta(MOBILE, "60126973105")
    assert added
    panel = out[out.index('id="mobile-menu-panel"'):]
    assert "wa.me/60126973105" in panel and 'class="block w-full text-center mt-3 btn-primary hidden md:inline-flex"' in panel
    again, added2 = ensure_mobile_nav_cta(out, "60126973105")
    assert not added2 and again == out


def test_mobile_panel_builds_a_cta_when_the_header_has_no_whatsapp_link():
    html = '<header><nav><a href="#home">Home</a></nav><ul id="mobile-nav"><li><a href="#menu">Menu</a></li></ul></header>'
    out, added = ensure_mobile_nav_cta(html, "60126973105", label="Pesan di WhatsApp", prefill="Assalamualaikum, saya nak order")
    assert added and "<li><a href=\"https://wa.me/60126973105?text=Assalamualaikum%2C%20saya%20nak%20order\"" in out
    assert "Pesan di WhatsApp</a></li>" in out


def test_postal_address_is_structured_and_description_ends_at_a_sentence():
    addr = postal_address("No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor")
    assert addr == {
        "@type": "PostalAddress", "addressCountry": "MY", "postalCode": "41200", "addressLocality": "Klang",
        "streetAddress": "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas", "addressRegion": "Selangor",
    }
    assert postal_address("Seksyen 13, Shah Alam, Selangor") == {"@type": "PostalAddress", "addressCountry": "MY", "streetAddress": "Seksyen 13, Shah Alam, Selangor", "addressRegion": "Selangor"}
    meta = SeoMeta(
        business_name="Ayam Gepuk Panglima", business_type="food",
        description=("Ayam Gepuk Panglima ialah restoran ayam gepuk di Kota Bayu Emas, Klang. Resepi Panglima — ayam goreng rangup digepuk "
                     "atas sambal pedas buatan sendiri, dihidang dengan nasi putih panas, tauhu, tempe, kubis dan timun. Slogan kami: Makin Pedas, "
                     "Rasa Makin Padu. Pilih tahap kepedasan anda: Level 1 (Spicy), Level 2 (Hot) atau Level 3 (Extra Hot). Set bermula RM12.50."),
        address="No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor",
        menu_items=[{"name": "Sup", "price": "RM1.00"}, {"name": "Set Udang Krispy", "price": "RM22.90"}],
    )
    node = build_json_ld(meta)
    assert node["@type"] == "Restaurant" and node["address"]["postalCode"] == "41200"
    assert node["description"].endswith(".") and len(node["description"]) <= 300
    assert node["priceRange"] == "RM1 - RM22.90" and "openingHoursSpecification" not in node
    json.dumps(node)
