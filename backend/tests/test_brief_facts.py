"""Key facts from the merchant's brief reach the page.

agp.binaapp.my: spice levels, "FREE refill nasi & sambal (dine-in sahaja)",
"Take away caj RM2.00" and a Coming Soon list were in the brief and none
was rendered once the deterministic menu block replaced the model's menu.
"""

import json
import os

import pytest

from app.services import brief_facts as bf
from app.services import menu_fidelity as mf

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ayam_gepuk_panglima_menu.json")

BRIEF = """Ayam Gepuk Panglima ialah restoran ayam gepuk di Kota Bayu Emas, Klang. Set bermula RM12.50.

Tahap kepedasan: Level 1 (Spicy), Level 2 (Hot) atau Level 3 (Extra Hot).

Makan di kedai: FREE refill nasi & sambal (dine-in sahaja). Take away caj RM2.00.

Coming Soon:
- Bakso Daging
- Nasi Lemak
- Kangkung Goreng, Kaki Ayam

Alamat: No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor."""


@pytest.fixture(scope="module")
def items():
    with open(FIXTURE, encoding="utf-8") as fh:
        return json.load(fh)["menu_items"]


def _page(items, extra=""):
    block = mf.render_menu_block(mf.normalize_items(items), wa_digits="60126973105")
    return (
        '<html><body><section id="hero"><h1>AGP</h1><p>Set bermula RM12.50</p></section>'
        f'<section id="menu"><div class="container"><h2>Menu</h2><div id="binaapp-menu-slot">{block}</div></div></section>'
        f"{extra}<footer><p>No. 44-1, Jalan Bayu Impian 4A/KS9</p></footer>"
        '<script>var x = "Level 1 refill Coming Soon take away RM2.00";</script></body></html>'
    )


class TestExtract:
    def test_the_agp_brief(self):
        facts = bf.extract_key_facts(BRIEF)
        kinds = [f.kind for f in facts]
        assert kinds == ["level", "refill", "charge", "coming_soon"]
        assert facts[0].levels == ["1", "2", "3"]
        assert facts[1].text == "Makan di kedai: FREE refill nasi & sambal (dine-in sahaja)."
        assert facts[2].text == "Take away caj RM2.00." and facts[2].amount == "2.00"
        assert facts[3].items == ["Bakso Daging", "Nasi Lemak", "Kangkung Goreng", "Kaki Ayam"]

    def test_a_menu_price_is_not_a_charge(self):
        assert bf.extract_key_facts("Set bermula RM12.50. Nasi lemak RM5.") == []

    def test_inline_coming_soon(self):
        (f,) = bf.extract_key_facts("Akan datang: Bakso, Mee Rebus dan Laksa.")
        assert f.kind == "coming_soon" and f.items == ["Bakso", "Mee Rebus", "Laksa"]


class TestCheck:
    def test_menu_price_with_the_same_amount_does_not_satisfy_the_charge(self, items):
        # "Telur Mata RM2.00" is on the page; the take-away charge is not.
        html = _page(items)
        assert "RM2.00" in html
        missing = bf.missing_facts(html, bf.extract_key_facts(BRIEF))
        assert [f.kind for f in missing] == ["level", "refill", "charge", "coming_soon"]  # script text doesn't count

    def test_rendered_facts_are_recognised(self, items):
        extra = (
            '<section id="info"><p>Pilih Level 1, Level 2 atau Level 3.</p><p>FREE refill nasi &amp; sambal.</p>'
            "<p>Take away: caj RM2</p><h3>Coming Soon</h3><p>Bakso Daging · Nasi Lemak · Kangkung Goreng · Kaki Ayam</p></section>"
        )
        assert bf.missing_facts(_page(items, extra), bf.extract_key_facts(BRIEF)) == []

    def test_notes_block_goes_under_the_menu_and_is_idempotent(self, items):
        html = _page(items)
        facts = bf.missing_facts(html, bf.extract_key_facts(BRIEF))
        out, done = bf.inject_notes_block(html, facts, "ms", items=items)
        assert done
        menu_end = out.index("</section>", out.index('id="menu"'))
        notes_at = out.index(bf.NOTES_BLOCK_CLASS)
        assert out.index("binaapp-menu-slot") < notes_at < menu_end
        assert bf.missing_facts(out, bf.extract_key_facts(BRIEF)) == []
        again, done2 = bf.inject_notes_block(out, facts, "ms", items=items)
        assert not done2 and again == out


def test_pipeline_step_injects_and_records(items):
    from types import SimpleNamespace
    from app.services.ai_service import AIService

    svc = AIService.__new__(AIService)
    req = SimpleNamespace(description=BRIEF, design_brief=None, menu_items=items)
    out = svc._enforce_brief_facts(_page(items), req, "ms")
    assert "Take away caj RM2.00." in out and "Kaki Ayam" in out
    assert len(svc._last_brief_facts["missing"]) == 4


def test_deterministic_prompts_still_require_the_other_sections():
    from app.services.designer_prompt_blocks import _menu_rules

    rules = _menu_rules({}, True, 32, False, True, "60126973105", "x", deterministic=True)
    assert "Coming Soon" in rules and "Level 1/2/3" in rules and "exact RM amounts" in rules
