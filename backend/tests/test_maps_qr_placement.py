"""Injected blocks belong to the design, not stuck on the end of it.

Report item #6: the map and QR blocks were pasted after </footer> with their
own inline palette (#f9fafb ground, #2D4A3E text, system font), so the QR
read as a white sticker floating in a dark green footer and the map rendered
BELOW the footer. The map heading also carried the raw typed address,
"NO.41 JALAN KRISTAL L7/L, 40000, shah alam".
"""

from app.services.templates import TemplateService, normalize_display_address
from app.utils.html_inject import insert_before_body, insert_before_footer

PAGE = (
    "<html><body><main><section id='menu'>menu</section></main>"
    "<footer><p>&copy; 2026</p></footer></body></html>"
)
ADDRESS = "NO.41 JALAN KRISTAL L7/L, 40000, shah alam"


class TestAddressDisplay:
    def test_shouted_and_lowercase_parts_are_normalised(self):
        assert normalize_display_address(ADDRESS) == (
            "No.41 Jalan Kristal L7/L, 40000, Shah Alam"
        )

    def test_codes_and_postcodes_are_left_alone(self):
        assert "40000" in normalize_display_address(ADDRESS)
        assert "L7/L" in normalize_display_address(ADDRESS)

    def test_abbreviations_stay_upper(self):
        assert normalize_display_address("jalan ss2, petaling jaya, KL").endswith("KL")

    def test_empty_is_empty(self):
        assert normalize_display_address("") == ""
        assert normalize_display_address(None) == ""


class TestMapPlacement:
    def _inject(self, html=PAGE):
        return TemplateService().inject_google_maps(html, ADDRESS)

    def test_the_map_lands_above_the_footer_not_below_it(self):
        out = self._inject()
        assert out.index('id="location"') < out.index("<footer")

    def test_the_heading_uses_the_normalised_address(self):
        out = self._inject()
        assert "No.41 Jalan Kristal L7/L, 40000, Shah Alam" in out
        assert "shah alam" not in out

    def test_it_paints_with_the_page_tokens_not_its_own_palette(self):
        out = self._inject()
        assert "var(--surface-color" in out and "var(--text-color" in out
        assert "#f9fafb" not in out
        assert "#1f2937" not in out

    def test_a_page_without_a_footer_still_gets_the_map(self):
        out = self._inject("<html><body><main>x</main></body></html>")
        assert 'id="location"' in out

    def test_the_embed_still_encodes_the_raw_address(self):
        # Display is normalised; the query Google receives is not touched.
        assert "NO.41+JALAN+KRISTAL" in self._inject()


class TestQrBlockTheming:
    def test_it_inherits_its_surroundings(self):
        out = TemplateService().inject_qr_code(PAGE, "https://ali.binaapp.my")
        assert "color:inherit" in out
        assert "background:#f9fafb" not in out
        # The code itself keeps a white plate — a QR on a dark ground
        # does not scan.
        assert "background:#fff" in out


class TestInsertHelpers:
    def test_before_footer_falls_back_to_before_body(self):
        html = "<body><main>x</main></body>"
        assert insert_before_footer(html, "<b/>") == insert_before_body(html, "<b/>")

    def test_before_footer_uses_the_first_footer(self):
        html = "<body><footer>a</footer><footer>b</footer></body>"
        out = insert_before_footer(html, "<b/>")
        assert out.index("<b/>") < out.index("<footer>a")

    def test_empty_document(self):
        assert insert_before_footer("", "<b/>") == "<b/>"
