"""
Anti-template lint (anti_template_lint.py) and the quality floor
(quality_floor.py) — the deterministic side of the §2 / §8 rules.

Covers:
- each lint rule fires on the tell and stays quiet on clean markup
- repairs: AOS stripped, arrows stripped from CTAs, inline heading
  font-size stripped, fake map cards removed (real embeds kept)
- the quality floor adds lang, viewport, reduced-motion, focus-visible and
  lazy-loading idempotently and reports the Tailwind CDN when it remains
"""

from app.services.anti_template_lint import (
    lint_anti_template,
    strip_aos,
    strip_cta_arrows,
    strip_fake_map_cards,
)
from app.services.quality_floor import apply_quality_floor

CLEAN = """<!DOCTYPE html><html lang="ms"><head><meta name="viewport" content="width=device-width"><style>
@media (prefers-reduced-motion: reduce){*{animation:none}} :focus-visible{outline:2px solid red} img{max-width:100%}
</style></head><body>
<header><nav><a href="#menu">Menu</a></nav></header>
<section id="home"><h1>Ayam Goreng Berempah</h1><p>Sejak 2009 di Shah Alam.</p>
<a href="https://wa.me/60198765432">Pesan di WhatsApp</a><a href="#menu">Lihat menu</a></section>
<section id="menu"><h2>Menu</h2><div class="grid"><article><img src="https://res.cloudinary.com/x/image/upload/w_800,h_600,c_fill/a.jpg" alt="Ayam"><h3>Ayam Goreng</h3><span>RM8</span></article></div></section>
<section id="lokasi"><h2>Lokasi</h2><p>12, Jalan Tengku Ampuan, Shah Alam</p><a href="https://www.google.com/maps/search/?api=1&query=x">Buka di Google Maps</a></section>
<footer>&copy; <span id="binaapp-year"></span> Nasi Kandar Crystal</footer>
</body></html>"""


def test_clean_page_passes():
    html, report = lint_anti_template(CLEAN, hours_supplied=False)
    assert report.ok, report.errors
    assert report.warnings == []
    assert html == CLEAN


def test_aos_everywhere_fails_and_is_stripped():
    page = CLEAN.replace("<section id=\"home\">", '<section id="home" data-aos="fade-up">') \
        .replace('<section id="menu">', '<section id="menu" data-aos="fade-up" data-aos-delay="100">') \
        .replace('<section id="lokasi">', '<section id="lokasi" data-aos="fade-up">') \
        .replace("</head>", '<link href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet"></head>') \
        .replace("</body>", '<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script><script>AOS.init({ duration: 800 });</script></body>')
    html, report = lint_anti_template(page)
    assert any("data-aos" in e for e in report.errors)
    assert "data-aos" not in html and "aos.js" not in html and "aos.css" not in html and "AOS.init" not in html
    assert any("removed AOS" in r for r in report.repairs)


def test_two_aos_allowed_when_wanted():
    page = CLEAN.replace('<section id="home">', '<section id="home" data-aos="fade-in">')
    html, report = lint_anti_template(page, allow_aos=True)
    assert report.ok and 'data-aos="fade-in"' in html


def test_eyebrow_on_every_heading_fails():
    eyebrow = '<p class="text-xs uppercase tracking-widest text-primary">Menu</p>'
    page = CLEAN.replace("<h2>Menu</h2>", eyebrow + "<h2>Menu</h2>").replace("<h2>Lokasi</h2>", eyebrow + "<h2>Lokasi</h2>")
    _, report = lint_anti_template(page)
    assert any("eyebrow" in e for e in report.errors)
    one = CLEAN.replace("<h2>Menu</h2>", eyebrow + "<h2>Menu</h2>")
    _, report = lint_anti_template(one)
    assert report.ok


def test_decorated_headline_fails():
    page = CLEAN.replace("<h1>Ayam Goreng Berempah</h1>", '<h1>Ayam Goreng <span class="italic text-primary">Berempah</span></h1>')
    _, report = lint_anti_template(page)
    assert any("italic or recoloured" in e for e in report.errors)
    page = CLEAN.replace("<h1>Ayam Goreng Berempah</h1>", '<h1>Ayam <em>Goreng</em></h1>')
    _, report = lint_anti_template(page)
    assert any("italic or recoloured" in e for e in report.errors)
    page = CLEAN.replace("<h2>Menu</h2>", '<h2>Menu <span class="text-accent">Kami</span></h2>')
    _, report = lint_anti_template(page)
    assert any("italic or recoloured" in e for e in report.errors)


def test_arrow_ctas_fail_and_are_stripped():
    page = CLEAN.replace(">Lihat menu</a>", ">Lihat menu →</a>").replace(">Pesan di WhatsApp</a>", '>Pesan di WhatsApp <i class="fas fa-arrow-right"></i></a>')
    html, report = lint_anti_template(page)
    assert any("arrow" in e for e in report.errors)
    assert "→" not in html and "fa-arrow-right" not in html
    assert ">Lihat menu</a>" in html and ">Pesan di WhatsApp</a>" in html


def test_middle_dot_meta_fails():
    page = CLEAN.replace("<p>Sejak 2009 di Shah Alam.</p>", "<p>Halal · Shah Alam · 24 jam</p>")
    _, report = lint_anti_template(page)
    assert any("middle-dot" in e for e in report.errors)


def test_inline_heading_font_size_is_stripped_with_warning():
    page = CLEAN.replace("<h1>", '<h1 style="font-size: clamp(2rem, 5vw, 4rem); text-wrap: balance">')
    html, report = lint_anti_template(page)
    assert any("inline style" in w for w in report.warnings)
    assert "font-size" not in html.split("<body>")[1]
    assert 'style="text-wrap: balance"' in html


def test_fake_map_card_is_stripped_but_real_embed_kept():
    fake = '<div class="map-card rounded-2xl"><i class="fas fa-map-location-dot"></i><p>Peta</p></div>'
    page = CLEAN.replace("<footer>", fake + "<footer>")
    html, report = lint_anti_template(page)
    assert "map-card" not in html
    assert any("map card" in e for e in report.errors)
    real = '<div class="map-card"><iframe src="https://maps.google.com/maps?q=x&output=embed"></iframe></div>'
    page = CLEAN.replace("<footer>", real + "<footer>")
    html, report = lint_anti_template(page)
    assert "<iframe" in html and report.ok
    slot = '<div class="map-wrapper"><div id="binaapp-maps-slot"></div></div>'
    html, report = lint_anti_template(CLEAN.replace("<footer>", slot + "<footer>"))
    assert "binaapp-maps-slot" in html and report.ok


def test_invented_hours_and_placeholder_copy_fail():
    page = CLEAN.replace("<p>Sejak 2009 di Shah Alam.</p>", "<p>Buka 9am - 10pm setiap hari</p>")
    _, report = lint_anti_template(page, hours_supplied=False)
    assert any("opening hours" in e for e in report.errors)
    _, report = lint_anti_template(page, hours_supplied=True)
    assert report.ok
    page = CLEAN.replace("<p>Sejak 2009 di Shah Alam.</p>", "<p>Gallery coming soon</p>")
    _, report = lint_anti_template(page)
    assert any("placeholder copy" in e for e in report.errors)
    honest = CLEAN.replace("<p>Sejak 2009 di Shah Alam.</p>", "<h2>Menu Akan Datang</h2>")
    _, report = lint_anti_template(honest)
    assert report.ok


def test_helpers_are_idempotent():
    html, n = strip_aos(CLEAN)
    assert html == CLEAN and n == 0
    html, n = strip_cta_arrows(CLEAN)
    assert html == CLEAN and n == 0
    html, n = strip_fake_map_cards(CLEAN)
    assert html == CLEAN and n == 0


# ---- quality floor ---------------------------------------------------------

BARE = """<!DOCTYPE html><html><head><title>x</title><script src="https://cdn.tailwindcss.com"></script></head><body>
<img src="https://res.cloudinary.com/x/image/upload/w_1600,h_900/hero.jpg" alt="Hero dish">
<img src="https://res.cloudinary.com/x/image/upload/w_800,h_600/a.jpg" alt="Ayam">
<img src="https://example.com/b.jpg" alt="B" class="aspect-[4/3] outline-none">
</body></html>"""


def test_quality_floor_adds_the_baseline_idempotently():
    html, report = apply_quality_floor(BARE, language="ms")
    assert '<html lang="ms">' in html
    assert 'name="viewport"' in html
    assert "prefers-reduced-motion" in html and ":focus-visible" in html
    assert html.count('loading="lazy"') == 2 and 'loading="eager"' in html
    assert 'width="1600" height="900"' in html and 'width="800" height="600"' in html and 'width="800" height="600"' in html
    assert any("Tailwind Play CDN still in use" in w for w in report.warnings)
    again, report2 = apply_quality_floor(html, language="ms")
    assert again == html
    assert report2.applied == []


def test_quality_floor_sets_english_lang_and_swaps_cdn_when_css_supplied():
    html, report = apply_quality_floor(BARE.replace("<html>", '<html lang="ms">'), language="en", precompiled_css=".x{color:red}")
    assert '<html lang="en">' in html
    assert "cdn.tailwindcss.com" not in html and '<style id="binaapp-tailwind">.x{color:red}</style>' in html
    assert report.warnings == []
