"""Tests for insert_before_body and the duplicate-widget-injection regression.

Production case: the AI emitted a section comment containing the literal text
``</body>`` (``<!-- ===== BEFORE </body> — AOS + init ===== -->``). Injectors
did ``html.replace("</body>", block + "\n</body>")`` which replaces EVERY
occurrence — splicing the WhatsApp button + QR block into the middle of the
comment (breaking it open, so both rendered twice with duplicate ids) and
leaving a stray premature ``</body>`` in the page.
"""

from app.utils.html_inject import insert_before_body
from app.services.templates import TemplateService


CORRUPT_COMMENT_PAGE = (
    "<html><body>\n"
    "<main>content</main>\n"
    "<!-- ===== BEFORE </body> — AOS + init ===== -->\n"
    "<script>AOS.init();</script>\n"
    "</body></html>"
)


def test_inserts_before_last_body_only():
    out = insert_before_body(CORRUPT_COMMENT_PAGE, "<div id='w'>W</div>")
    assert out.count("<div id='w'>W</div>") == 1
    # The comment must stay intact — nothing injected inside it.
    assert "<!-- ===== BEFORE </body> — AOS + init ===== -->" in out
    # Inserted after the AOS script, right before the real closing tag.
    assert out.index("AOS.init") < out.index("<div id='w'>W</div>")
    assert out.rstrip().endswith("</body></html>")


def test_appends_when_no_body_close():
    assert insert_before_body("<html><body>x", "<b>y</b>") == "<html><body>x<b>y</b>"


def test_empty_html_returns_block():
    assert insert_before_body("", "<b>y</b>") == "<b>y</b>"


def test_whatsapp_button_injected_once_despite_body_in_comment():
    svc = TemplateService()
    out = svc.inject_whatsapp_button(CORRUPT_COMMENT_PAGE, "011-23456789")
    assert out.count('id="whatsapp-button"') == 1
    assert "wa.me/+601123456789" in out
    # Button must land after the comment/scripts, not inside the document body text.
    assert out.index("AOS.init") < out.index('id="whatsapp-button"')
    assert "<!-- ===== BEFORE </body> — AOS + init ===== -->" in out
