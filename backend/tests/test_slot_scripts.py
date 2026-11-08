"""Page scripts must not refill the server-owned menu / map slots.

agp: the photo menu was in the HTML, but the model's script rebuilt
'#binaapp-menu-slot' on load from its own list (invented descriptions, no
photos). In a browser the page showed 32 photo-less cards."""

import os
import sys

from app.services.slot_scripts import DECOY_SUFFIX, neutralize_slot_scripts, scripts_touching_slots

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from verify_site_menu import _slot_scripts  # noqa: E402

PAGE = """<html><head><script type="application/ld+json">{"menu":"binaapp-menu-slot"}</script></head><body>
<div id="binaapp-menu-slot"><div class="binaapp-menu-block">photo menu</div></div>
<script>
document.getElementById('binaapp-year').textContent = new Date().getFullYear();
const btn = document.getElementById('hamburger-btn');
const menuSlot = document.getElementById('binaapp-menu-slot');
if (menuSlot) { menuSlot.innerHTML = '<div class="menu-item-card">Set A</div>'; }
document.querySelector("#binaapp-maps-slot").innerHTML = 'x';
</script></body></html>"""


def test_slot_references_point_at_a_hidden_decoy_and_other_code_is_untouched():
    out, n = neutralize_slot_scripts(PAGE)
    assert n == 1
    assert f"getElementById('binaapp-menu-slot{DECOY_SUFFIX}')" in out
    assert f'querySelector("#binaapp-maps-slot{DECOY_SUFFIX}")' in out
    assert "getElementById('binaapp-year')" in out and "getElementById('hamburger-btn')" in out
    assert f'<div id="binaapp-menu-slot{DECOY_SUFFIX}" hidden' in out and f'<div id="binaapp-maps-slot{DECOY_SUFFIX}" hidden' in out
    # The real slot and the JSON-LD are untouched.
    assert '<div id="binaapp-menu-slot"><div class="binaapp-menu-block">photo menu</div></div>' in out
    assert '{"menu":"binaapp-menu-slot"}' in out
    assert neutralize_slot_scripts(out) == (out, 0)


def test_verify_flags_a_slot_refilling_script():
    assert scripts_touching_slots(PAGE) == 1 and _slot_scripts(PAGE) == 1
    out, _ = neutralize_slot_scripts(PAGE)
    assert scripts_touching_slots(out) == 0 and _slot_scripts(out) == 0


def test_page_without_slot_scripts_unchanged():
    page = "<html><body><script>console.log('hi')</script></body></html>"
    assert neutralize_slot_scripts(page) == (page, 0)
