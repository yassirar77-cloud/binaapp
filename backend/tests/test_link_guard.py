"""A control that does nothing is worse than no control.

Regression cover for report items #3 and #7: a live wa.me link to an example
number, two buttons pointing at each other, and dead footer social icons.
"""

from app.services.link_guard import (
    document_anchor_ids,
    page_whatsapp_link,
    remove_empty_floating_slots,
    strip_dead_links,
)
from app.services.templates import TemplateService

REAL = "60193456781"

SHIPPED = (
    '<html><body>'
    '<section id="lawati"><a href="#hubungi" class="btn">WhatsApp Kami</a></section>'
    '<section id="hubungi"><a href="#lawati">Lihat Lokasi Kami</a></section>'
    '<footer>'
    '<a href="#" class="fab fa-facebook"><i></i></a>'
    '<a href="#" aria-label="Instagram"><i class="fa-instagram"></i></a>'
    '<a href="#">Polisi Privasi</a>'
    '<a href="#tiada-seksyen">Menu</a>'
    '<a href="/terma">Terma</a>'
    '</footer></body></html>'
)


class TestWhatsappLabelledControls:
    def test_removed_when_the_page_has_no_real_number(self):
        out, report = strip_dead_links(SHIPPED)
        assert "WhatsApp Kami" not in out
        assert "WhatsApp Kami" in report.removed

    def test_repointed_when_the_page_does_have_one(self):
        html = SHIPPED.replace(
            "</footer>", f'<a href="https://wa.me/{REAL}">Chat</a></footer>'
        )
        out, report = strip_dead_links(html)
        assert f'href="https://wa.me/{REAL}"' in out.split("WhatsApp Kami")[0]
        assert "WhatsApp Kami" in report.repointed

    def test_a_placeholder_number_is_not_a_destination(self):
        # wa.me/60123456789 was this pipeline's own default. Re-pointing a
        # button at it would be the bug wearing a fix's clothes.
        html = SHIPPED.replace(
            "</footer>", '<a href="https://wa.me/60123456789">Chat</a></footer>'
        )
        assert page_whatsapp_link(html) == ""
        out, report = strip_dead_links(html)
        assert "WhatsApp Kami" in report.removed


class TestSocialIcons:
    def test_dead_icons_are_removed_entirely(self):
        out, report = strip_dead_links(SHIPPED)
        assert "fa-facebook" not in out and "fa-instagram" not in out
        assert len([r for r in report.removed if "social" in r or "Instagram" in r]) >= 1

    def test_icons_with_a_real_url_survive(self):
        html = '<footer><a href="https://instagram.com/kedai" class="fab fa-instagram"></a></footer>'
        out, report = strip_dead_links(html)
        assert out == html and not report.changed


class TestOtherDeadLinks:
    def test_href_hash_is_unwrapped_keeping_its_words(self):
        out, _ = strip_dead_links(SHIPPED)
        assert "Polisi Privasi" in out
        assert '<a href="#">Polisi Privasi</a>' not in out

    def test_anchor_to_an_undefined_id_is_unwrapped(self):
        out, report = strip_dead_links(SHIPPED)
        assert "#tiada-seksyen" not in out
        assert "Menu" in report.unwrapped

    def test_anchor_to_a_defined_id_survives(self):
        out, _ = strip_dead_links(SHIPPED)
        assert 'href="#lawati"' in out

    def test_real_urls_are_untouched(self):
        out, _ = strip_dead_links(SHIPPED)
        assert '<a href="/terma">Terma</a>' in out

    def test_anchors_inside_script_are_code_not_controls(self):
        html = '<body><script>var t = \'<a href="#">x</a>\';</script></body>'
        out, report = strip_dead_links(html)
        assert out == html and not report.changed

    def test_idempotent(self):
        once, _ = strip_dead_links(SHIPPED)
        twice, report = strip_dead_links(once)
        assert twice == once and not report.changed

    def test_document_anchor_ids(self):
        assert document_anchor_ids(SHIPPED) == {"lawati", "hubungi"}


class TestNoPlaceholderWhatsappButton:
    """The floating button is rendered only for a number that exists."""

    def _inject(self, number):
        return TemplateService().inject_whatsapp_button(
            "<html><body><p>hi</p></body></html>", number
        )

    def test_placeholder_number_renders_nothing(self):
        for number in ("+60123456789", "60123456789", "0123456789", "", "abc"):
            assert 'id="whatsapp-button"' not in self._inject(number)

    def test_a_real_number_renders_the_button(self):
        out = self._inject("019-345 6781")
        assert 'id="whatsapp-button"' in out
        assert f"wa.me/+{REAL}" in out


class TestEmptyFloatingSlots:
    """A floating widget positions itself; a slot left for one is a stray box.

    The reported page stacked three of them in the bottom-right corner.
    """

    PAGE = (
        '<body><div class="sticky-whatsapp-zone"></div>'
        '<div id="binaapp-whatsapp-slot">  </div>'
        '<div id="binaapp-chat-slot"><button>Chat</button></div>'
        '<a id="whatsapp-button" href="https://wa.me/60193456781"></a></body>'
    )

    def test_empty_slots_are_removed(self):
        out, removed = remove_empty_floating_slots(self.PAGE)
        assert "sticky-whatsapp-zone" not in out
        assert "binaapp-whatsapp-slot" not in out
        assert set(removed) == {"sticky-whatsapp-zone", "binaapp-whatsapp-slot"}

    def test_a_filled_slot_survives(self):
        out, _ = remove_empty_floating_slots(self.PAGE)
        assert 'id="binaapp-chat-slot"' in out

    def test_the_real_button_survives(self):
        out, _ = remove_empty_floating_slots(self.PAGE)
        assert 'id="whatsapp-button"' in out

    def test_idempotent(self):
        once, _ = remove_empty_floating_slots(self.PAGE)
        twice, removed = remove_empty_floating_slots(once)
        assert twice == once and not removed

    def test_pages_without_slots_are_untouched(self):
        html = "<body><p>hello</p></body>"
        assert remove_empty_floating_slots(html) == (html, [])
