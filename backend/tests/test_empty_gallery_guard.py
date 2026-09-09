"""Bug 4: "Galeri / Hasil Kerja Kami" rendered with nothing inside it.

The model emitted the section, the heading, four styled cards and a nav
link — and no <img> in any card, because no gallery image was ever
generated. On a customer's live site that reads as broken. When a gallery
section has no real media, the section AND its nav links are omitted.
"""
from app.services.gallery_normalizer import normalize_gallery_html, omit_empty_gallery_sections

NAV = (
    '<nav><a class="nav-link" href="#tentang">Tentang Kami</a>'
    '<a class="nav-link" href="#perkhidmatan">Perkhidmatan</a>'
    '<a class="nav-link" href="#galeri">Galeri</a>'
    '<a class="nav-link" href="#hubungi">Hubungi</a></nav>'
    '<nav class="mobile"><a href="#galeri">Galeri</a></nav>'
)
EMPTY_GALLERY = (
    '<section class="py-24" id="galeri" style="background-color:#1C1917;">'
    '<span class="kicker">Galeri</span><h2>Hasil Kerja Kami</h2>'
    '<div class="grid"><div class="gallery-image"><div class="relative">'
    '<span class="tag">Balayage</span></div></div>'
    '<div class="gallery-image"><div class="relative"><span class="tag">Korean Perm</span></div></div>'
    '</div></section>'
)
FULL_GALLERY = EMPTY_GALLERY.replace(
    '<span class="tag">Balayage</span>',
    '<img src="https://res.cloudinary.com/x/image/upload/a.jpg" alt=""><span class="tag">Balayage</span>',
)
OTHER = '<section id="perkhidmatan"><h2>Perkhidmatan</h2></section>'
PAGE = "<html><body>{nav}{gallery}{other}</body></html>"


class TestOmitEmptyGallery:
    def test_empty_gallery_and_its_nav_links_are_removed(self):
        out = omit_empty_gallery_sections(PAGE.format(nav=NAV, gallery=EMPTY_GALLERY, other=OTHER))
        assert 'id="galeri"' not in out
        assert "Hasil Kerja Kami" not in out
        assert 'href="#galeri"' not in out
        # everything else survives
        assert 'href="#perkhidmatan"' in out and 'id="perkhidmatan"' in out
        assert 'href="#hubungi"' in out

    def test_gallery_with_a_real_image_is_kept(self):
        page = PAGE.format(nav=NAV, gallery=FULL_GALLERY, other=OTHER)
        assert omit_empty_gallery_sections(page) == page

    def test_css_background_image_counts_as_media(self):
        gallery = EMPTY_GALLERY.replace(
            '<div class="relative">', '<div class="relative" style="background-image:url(https://cdn/x.jpg)">', 1
        )
        page = PAGE.format(nav=NAV, gallery=gallery, other=OTHER)
        assert omit_empty_gallery_sections(page) == page

    def test_unresolved_photo_slot_is_not_a_real_image(self):
        gallery = EMPTY_GALLERY.replace(
            '<span class="tag">Balayage</span>', '<img src="PHOTO_SLOT_2" alt=""><span class="tag">Balayage</span>'
        )
        out = omit_empty_gallery_sections(PAGE.format(nav=NAV, gallery=gallery, other=OTHER))
        assert 'id="galeri"' not in out

    def test_non_gallery_sections_without_images_are_never_touched(self):
        page = PAGE.format(nav=NAV, gallery="", other=OTHER)
        assert omit_empty_gallery_sections(page) == page

    def test_english_ids_and_classes_are_recognised(self):
        gallery = EMPTY_GALLERY.replace('id="galeri"', 'id="portfolio"')
        nav = NAV.replace("#galeri", "#portfolio")
        out = omit_empty_gallery_sections(PAGE.format(nav=nav, gallery=gallery, other=OTHER))
        assert 'id="portfolio"' not in out and 'href="#portfolio"' not in out

    def test_runs_inside_the_combined_post_pass(self):
        out = normalize_gallery_html(PAGE.format(nav=NAV, gallery=EMPTY_GALLERY, other=OTHER))
        assert 'id="galeri"' not in out and 'href="#galeri"' not in out

    def test_never_raises_on_garbage(self):
        assert omit_empty_gallery_sections("") == ""
        assert omit_empty_gallery_sections("<section id='galeri'>unclosed") == "<section id='galeri'>unclosed"
