"""A signature/featured item gets a SIGNATURE badge and a highlighted card
in the deterministic menu block — by flag, or because its name says so."""

import re

from app.services import menu_fidelity as mf


def _card_for(block, name):
    m = re.search(r'<li class="([^"]+)">((?:(?!</li>).)*' + re.escape(name) + r".*?)</li>", block, re.DOTALL)
    assert m, name
    return m.group(1), m.group(2)


def test_name_containing_signature_is_signature():
    items = mf.normalize_items([
        {"name": "Set Panglima Signature – Ayam Gepuk Telur Mata", "price": "15.90", "category": "Set Ayam"},
        {"name": "Set A – Ayam Gepuk", "price": "12.50", "category": "Set Ayam"},
    ])
    assert [it.signature for it in items] == [True, False]


def test_featured_flag_is_signature():
    (it,) = mf.normalize_items([{"name": "Nasi Kerabu", "price": "9", "featured": True}])
    assert it.signature


def test_signature_card_is_badged_and_highlighted():
    items = mf.normalize_items([
        {"name": "Set Panglima Signature – Ayam Gepuk Telur Mata", "price": "15.90", "category": "Set Ayam"},
        {"name": "Set A – Ayam Gepuk", "price": "12.50", "category": "Set Ayam", "image_url": "https://x/a.png"},
        {"name": "Set B", "price": "13.50", "category": "Set Ayam", "image_url": "https://x/b.png", "featured": True},
    ])
    block = mf.render_menu_block(items)
    cls, body = _card_for(block, "Set Panglima Signature")
    assert "bmf-signature" in cls.split() and '<span class="bmf-badge">SIGNATURE</span>' in body
    cls, body = _card_for(block, "Set A – Ayam Gepuk")
    assert "bmf-signature" not in cls and "bmf-badge" not in body
    cls, body = _card_for(block, "Set B")
    assert "bmf-signature" in cls.split() and "SIGNATURE" in body and '<img src="https://x/b.png"' in body
    assert ".bmf-card.bmf-signature{" in block  # the highlight style ships with the block


def test_signature_ranks_first_within_the_set_tier():
    items = mf.normalize_items([
        {"name": "Set A", "price": "12.50", "category": "Set Ayam"},
        {"name": "Set Signature", "price": "15", "category": "Set Ayam"},
        {"name": "Ayam Signature", "price": "9", "category": "Lauk"},
    ])
    # Every set item before anything else; the signature set leads them.
    assert [it.name for it in mf.image_priority(items)] == ["Set Signature", "Set A", "Ayam Signature"]
