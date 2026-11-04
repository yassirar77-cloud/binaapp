"""Nothing empty ships: empty sections and orphan dividers are removed."""

from app.services.section_hygiene import clean_sections, is_empty_block


def test_section_with_only_comments_and_whitespace_is_removed():
    html = """<body><section id="hero"><h1>Hi</h1></section>
<!-- SEAFOOD KRISPY -->
<section id="seafood" class="py-16">
  <!-- stripped by the fact guard -->
  <div class="grid">   </div>
</section>
<section id="menu"><h2>Menu</h2></section><footer>f</footer></body>"""
    out, rep = clean_sections(html)
    assert rep.removed_sections == ["seafood"]
    assert 'id="seafood"' not in out and 'id="menu"' in out


def test_nav_link_to_a_removed_section_goes_with_it():
    html = '<nav><a href="#seafood">Seafood</a><a href="#menu">Menu</a></nav><section id="seafood"></section><section id="menu"><p>x</p></section>'
    out, rep = clean_sections(html)
    assert rep.removed_nav_links == 1 and 'href="#seafood"' not in out and 'href="#menu"' in out


def test_two_dividers_framing_nothing_are_removed():
    html = """<section id="about"><p>About</p></section>
    <!-- SIGNATURE BAND -->
    <div class="wavy-divider-top bg-[#C8321A] h-8"></div>

    <div class="wavy-divider-bottom bg-[#C8321A] h-8"></div>

    <!-- MENU -->
    <section id="menu"><h2>Menu</h2></section>"""
    out, rep = clean_sections(html)
    assert rep.removed_dividers == 2
    assert "wavy-divider" not in out and "<!-- MENU -->" in out


def test_divider_against_real_content_stays():
    html = '<div class="wavy-divider-top h-8"></div><section id="band"><p>Signature</p></section><div class="wavy-divider-bottom h-8"></div><section id="menu"><p>m</p></section>'
    out, rep = clean_sections(html)
    assert out == html and not rep.changed


def test_hero_slots_and_media_are_never_judged_empty():
    assert not is_empty_block('<section id="x"><img src="a.jpg"></section>')
    assert not is_empty_block('<section id="x"><div id="binaapp-maps-slot"></div></section>')
    assert not is_empty_block('<section id="x"><iframe src="m"></iframe></section>')
    html = '<section id="hero" class="min-h-screen"></section><section id="menu"><p>m</p></section>'
    out, rep = clean_sections(html)
    assert out == html
