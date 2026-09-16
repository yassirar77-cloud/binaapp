"""Borang Tempahan: the form a merchant switches on has to work.

The report said it "renders nothing". The injector does always inject —
into the AI-emitted `binaapp-contact-slot` when there is one, appended
before `</body>` when there is not — so an empty page means the feature
arrived switched off. What the injector produced when it DID run was its
own set of defects:

  * the submit handler did not parse, so `handleContactSubmit` was
    undefined, `preventDefault()` never ran and the browser did a native
    GET submit: the page reloaded with the answers in the query string and
    nothing reached the merchant. A form that silently discards a booking
    is indistinguishable, to a merchant, from no form at all;
  * no PHONE field on the slot path — on a feature called "booking" —
    so a booking arrived with no number to call back;
  * English labels on a Malay page, next to a Malay WhatsApp button;
  * #f9fafb panel and #374151 labels, i.e. a white sticker on a dark site.

`check_feature_markup` covers the other half: a feature that is on and
renders nothing is now an error on the job row rather than something the
merchant finds.
"""

from __future__ import annotations

import pytest

from app.services.generation_validator import (
    _unbalanced_string_literal,
    check_feature_markup,
)
from app.services.templates import TemplateService

SLOT_PAGE = (
    '<html><body><section id="hubungi"><h2>Hubungi</h2>'
    '<div id="binaapp-contact-slot"></div></section>'
    '<a href="https://wa.me/60176119872">WhatsApp</a></body></html>'
)
BARE_PAGE = '<html><body><section id="hubungi"><h2>Hubungi</h2></section></body></html>'
TOKENS = {"primary": "#D46A2A", "accent": "#8D1608"}


@pytest.fixture
def svc():
    return TemplateService()


def _script(html: str) -> str:
    return html[html.index("<script>") + len("<script>"): html.index("</script>")]


class TestTheFormAlwaysArrives:
    @pytest.mark.parametrize("page", [SLOT_PAGE, BARE_PAGE])
    def test_both_paths_produce_a_form(self, svc, page):
        out = svc.inject_contact_form(page, "a@b.com", theme_tokens=TOKENS, language="ms")
        assert "<form" in out and 'name="name"' in out and 'name="message"' in out

    def test_the_slot_is_preferred_over_appending(self, svc):
        out = svc.inject_contact_form(SLOT_PAGE, "", theme_tokens=TOKENS)
        assert out.index("<form") < out.index("</section>")


class TestTheSubmitHandlerRuns:
    @pytest.mark.parametrize("page", [SLOT_PAGE, BARE_PAGE])
    @pytest.mark.parametrize("language", ["ms", "en"])
    def test_the_script_parses(self, svc, page, language):
        # The bug: a literal newline inside a JS string literal. The whole
        # block was a SyntaxError, so the handler never existed.
        out = svc.inject_contact_form(page, "a@b.com", theme_tokens=TOKENS, language=language)
        assert _unbalanced_string_literal(_script(out)) == ""

    def test_the_handler_is_defined_and_wired(self, svc):
        out = svc.inject_contact_form(SLOT_PAGE, "a@b.com", theme_tokens=TOKENS)
        assert "function handleContactSubmit" in out
        assert 'onsubmit="return handleContactSubmit(event)"' in out

    def test_no_raw_newline_survives_into_the_script(self, svc):
        out = svc.inject_contact_form(SLOT_PAGE, "a@b.com", theme_tokens=TOKENS)
        for line in _script(out).splitlines():
            assert line.count("'") % 2 == 0, line


class TestABookingCarriesAPhoneNumber:
    @pytest.mark.parametrize("page", [SLOT_PAGE, BARE_PAGE])
    def test_the_phone_field_exists(self, svc, page):
        out = svc.inject_contact_form(page, "", theme_tokens=TOKENS, language="ms")
        assert 'name="phone"' in out and 'type="tel"' in out

    def test_the_whatsapp_message_carries_who_how_and_what(self, svc):
        script = _script(svc.inject_contact_form(SLOT_PAGE, "", theme_tokens=TOKENS))
        for part in ("encodeURIComponent(name)", "encodeURIComponent(reply)",
                     "encodeURIComponent(message)"):
            assert part in script
        # `reply` is the phone on a WhatsApp page, the email without one.
        assert "data.get('phone') || data.get('email')" in script

    def test_it_asks_for_the_channel_the_merchant_can_answer_on(self, svc):
        with_wa = svc.inject_contact_form(SLOT_PAGE, "", theme_tokens=TOKENS, language="ms")
        assert 'name="phone"' in with_wa and 'name="email"' not in with_wa
        # No WhatsApp anywhere: the booking goes to mailto, so an email
        # address is the only way the merchant can reply.
        no_wa = svc.inject_contact_form(
            SLOT_PAGE.replace('<a href="https://wa.me/60176119872">WhatsApp</a>', ""),
            "kedai@example.com", theme_tokens=TOKENS, language="ms",
        )
        assert 'name="email"' in no_wa and 'name="phone"' in no_wa


class TestItSpeaksThePagesLanguage:
    def test_malay_by_default(self, svc):
        out = svc.inject_contact_form(SLOT_PAGE, "", theme_tokens=TOKENS)
        assert "Nama" in out and "Nombor telefon" in out and "Hantar tempahan" in out
        assert "Send Message" not in out

    def test_english_when_the_page_is_english(self, svc):
        out = svc.inject_contact_form(SLOT_PAGE, "", theme_tokens=TOKENS, language="en")
        assert "Phone number" in out and "Send booking" in out
        assert "Nombor telefon" not in out

    def test_the_alert_follows_too(self, svc):
        assert "Terima kasih" in svc.inject_contact_form(SLOT_PAGE, "", language="ms")
        assert "Thank you" in svc.inject_contact_form(SLOT_PAGE, "", language="en")


class TestItReadsOnADarkPage:
    @pytest.mark.parametrize("page", [SLOT_PAGE, BARE_PAGE])
    def test_it_paints_no_light_panel_of_its_own(self, svc, page):
        # The QR block was fixed for exactly this; the form never was.
        out = svc.inject_contact_form(page, "", theme_tokens=TOKENS, language="ms")
        form = out[out.index("<form"):out.index("</form>")]
        assert "#f9fafb" not in form and "#ffffff" not in form.lower()
        assert "color:inherit" in form

    def test_the_button_wears_the_sites_palette(self, svc):
        out = svc.inject_contact_form(SLOT_PAGE, "", theme_tokens=TOKENS)
        assert "#D46A2A" in out and "#8D1608" in out


class TestTheFeatureContract:
    def test_a_page_with_the_form_meets_it(self, svc):
        out = svc.inject_contact_form(SLOT_PAGE, "", theme_tokens=TOKENS)
        assert check_feature_markup(out, {"contact_form": True}) == []

    def test_a_page_without_it_does_not(self):
        issues = check_feature_markup(BARE_PAGE, {"contact_form": True})
        assert [i.code for i in issues] == ["feature_rendered_nothing"]
        assert "Borang Tempahan" in issues[0].message

    def test_a_feature_that_is_off_is_not_checked(self):
        assert check_feature_markup(BARE_PAGE, {"contact_form": False}) == []

    def test_every_feature_a_merchant_can_switch_on_has_a_marker(self):
        # The point of the contract: adding a toggle without a marker means
        # the next feature that quietly does nothing is invisible again.
        from app.services.generation_validator import FEATURE_MARKERS

        for key in ("contact_form", "whatsapp", "maps", "social",
                    "delivery_system", "qr_payment"):
            assert key in FEATURE_MARKERS
            label, needles = FEATURE_MARKERS[key]
            assert label and needles
