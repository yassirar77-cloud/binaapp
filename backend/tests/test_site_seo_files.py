"""Tests for per-subdomain robots.txt and sitemap.xml.

A sitemap is a promise to a crawler. The rule these tests enforce is that the
promise is derived from the page actually being served — never from a
template's idea of what sections a site "should" have — so it can't advertise
a URL that isn't there.
"""

from xml.etree import ElementTree

from app.services.site_seo_files import (
    build_robots_txt,
    build_sitemap_xml,
    extract_section_anchors,
)


PAGE = """<!DOCTYPE html><html><head><title>Kedai Ali</title></head><body>
<nav>
  <a href="#home">Utama</a>
  <a href="#menu">Menu</a>
  <a href="#tentang">Tentang</a>
  <a href="#hubungi">Hubungi</a>
  <a href="#tempahan">Tempahan</a>
  <a href="https://wa.me/60123">WhatsApp</a>
</nav>
<section id="home">hero</section>
<section id="menu">menu</section>
<div id="tentang">about</div>
<section id="hubungi">contact</section>
<footer>foot</footer>
</body></html>"""


class TestAnchorExtraction:
    def test_lists_sections_the_page_actually_contains(self):
        assert extract_section_anchors(PAGE) == ["menu", "tentang", "hubungi"]

    def test_drops_nav_links_to_sections_that_do_not_exist(self):
        # "#tempahan" is linked but the section was never generated — listing
        # it would send a crawler to a dead anchor.
        assert "tempahan" not in extract_section_anchors(PAGE)

    def test_skips_the_hero_and_other_chrome_anchors(self):
        assert "home" not in extract_section_anchors(PAGE)

    def test_ignores_external_links(self):
        assert not any(a.startswith("http") for a in extract_section_anchors(PAGE))

    def test_deduplicates(self):
        html = PAGE + '<a href="#menu">Menu lagi</a>'
        assert extract_section_anchors(html).count("menu") == 1

    def test_is_capped(self):
        many = "".join(f'<a href="#s{i}">x</a><section id="s{i}"></section>' for i in range(60))
        assert len(extract_section_anchors(many, limit=25)) == 25

    def test_empty_html_is_safe(self):
        assert extract_section_anchors("") == []


class TestSitemap:
    NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

    def _locs(self, xml):
        root = ElementTree.fromstring(xml)
        return [u.find(f"{self.NS}loc").text for u in root.findall(f"{self.NS}url")]

    def test_is_well_formed_xml(self):
        xml = build_sitemap_xml("https://kedaiali.binaapp.my", PAGE)
        root = ElementTree.fromstring(xml)
        assert root.tag == f"{self.NS}urlset"

    def test_homepage_is_always_first(self):
        locs = self._locs(build_sitemap_xml("https://kedaiali.binaapp.my", PAGE))
        assert locs[0] == "https://kedaiali.binaapp.my/"

    def test_sections_are_listed_as_anchors(self):
        locs = self._locs(build_sitemap_xml("https://kedaiali.binaapp.my", PAGE))
        assert "https://kedaiali.binaapp.my/#menu" in locs

    def test_anchors_can_be_turned_off(self):
        locs = self._locs(
            build_sitemap_xml("https://kedaiali.binaapp.my", PAGE, include_anchors=False)
        )
        assert locs == ["https://kedaiali.binaapp.my/"]

    def test_valid_lastmod_is_included(self):
        xml = build_sitemap_xml(
            "https://kedaiali.binaapp.my", PAGE, last_modified="2026-01-15T09:30:00Z"
        )
        assert "<lastmod>2026-01-15</lastmod>" in xml

    def test_unparseable_lastmod_is_omitted_never_guessed(self):
        xml = build_sitemap_xml(
            "https://kedaiali.binaapp.my", PAGE, last_modified="semalam"
        )
        assert "<lastmod>" not in xml

    def test_no_site_url_yields_nothing(self):
        assert build_sitemap_xml("", PAGE) == ""

    def test_trailing_slash_is_normalised(self):
        locs = self._locs(build_sitemap_xml("https://kedaiali.binaapp.my/", PAGE))
        assert locs[0] == "https://kedaiali.binaapp.my/"


class TestRobots:
    def test_allows_crawling_and_points_at_the_sitemap(self):
        txt = build_robots_txt("https://kedaiali.binaapp.my")
        assert "User-agent: *" in txt
        assert "Allow: /" in txt
        assert "Sitemap: https://kedaiali.binaapp.my/sitemap.xml" in txt

    def test_locked_site_disallows_everything(self):
        txt = build_robots_txt("https://kedaiali.binaapp.my", allow_indexing=False)
        assert "Disallow: /" in txt
        assert "Sitemap:" not in txt

    def test_ends_with_a_newline(self):
        assert build_robots_txt("https://kedaiali.binaapp.my").endswith("\n")


class TestMiddlewareResponses:
    """The subdomain middleware serves both files for a published site."""

    def test_robots_response_is_plain_text(self):
        from app.middleware.subdomain import _seo_file_response

        resp = _seo_file_response("/robots.txt", "kedaiali", html=PAGE)
        assert resp.media_type.startswith("text/plain")
        assert b"Sitemap: https://kedaiali.binaapp.my/sitemap.xml" in resp.body

    def test_sitemap_response_is_xml_built_from_the_served_page(self):
        from app.middleware.subdomain import _seo_file_response

        resp = _seo_file_response("/sitemap.xml", "kedaiali", html=PAGE)
        assert resp.media_type == "application/xml"
        assert b"/#menu" in resp.body

    def test_locked_site_advertises_nothing(self):
        from app.middleware.subdomain import _seo_file_response

        robots = _seo_file_response("/robots.txt", "kedaiali", indexable=False)
        sitemap = _seo_file_response("/sitemap.xml", "kedaiali", indexable=False)
        assert b"Disallow: /" in robots.body
        assert b"<loc>" not in sitemap.body
