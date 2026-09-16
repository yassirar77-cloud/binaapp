"""The merchant's own items must survive the pipeline (mkl, 2026-09-16).

Four items went in:

    1 Ikan Siakap Bakar (per kg)   RM48.00
    2 Ikan Kembung Bakar (3 ekor)  RM18.00
    3 Sotong Bakar (per kg)        RM42.00
    4 Udang Bakar (per kg)         RM55.00

Card 4 shipped carrying item 3's NAME and DESCRIPTION with item 4's PRICE:
"Sotong Bakar (per kg) … RM55.00", repeated in the JSON-LD. Udang appeared
nowhere on the page. A customer orders sotong; the kitchen grills udang.

Every check that existed passed. `_check_price_integrity` passed because
RM55.00 *was* on the page. `_check_derived_item_names` passed because
"Sotong Bakar (per kg)" *is* a name the merchant supplied — just not for
that item. Nothing checked that a name appears, that it appears once, or
that a price sits under its own name.

Same class as the katering run, where "Pakej Doa Selamat" simply vanished:
that is the first check below.
"""

from __future__ import annotations

from app.services.generation_validator import (
    GenerationBrief,
    validate_generated_site,
)

ITEMS = [
    {"name": "Ikan Siakap Bakar (per kg)", "price": "RM48.00"},
    {"name": "Ikan Kembung Bakar (3 ekor)", "price": "RM18.00"},
    {"name": "Sotong Bakar (per kg)", "price": "RM42.00"},
    {"name": "Udang Bakar (per kg)", "price": "RM55.00"},
]


def _card(name: str, desc: str, price: str) -> str:
    return (
        '<article class="menu-card">'
        f'<img alt="{name}" src="https://res.cloudinary.com/d/image/upload/v1/x.jpg">'
        f"<div><h3>{name}</h3><p>{desc}</p>"
        f'<span>{price}</span>'
        f'<a href="https://wa.me/60176119872?text=pesan">Pesan</a></div></article>'
    )


def _page(cards: str, band: str = "") -> str:
    return (
        "<!DOCTYPE html><html><head><title>Ikan Bakar</title></head><body>"
        '<section id="home"><h1>Ikan Bakar Tepi Sungai Pak Long</h1></section>'
        f"{band}"
        f'<section id="menu"><h2>Menu</h2>{cards}</section>'
        '<footer><a href="https://wa.me/60176119872">WhatsApp</a></footer>'
        "</body></html>"
    )


CORRECT = _page(
    _card("Ikan Siakap Bakar (per kg)", "Siakap segar dari Port Klang.", "RM48.00")
    + _card("Ikan Kembung Bakar (3 ekor)", "Tiga ekor kembung segar.", "RM18.00")
    + _card("Sotong Bakar (per kg)", "Sotong segar dibakar atas bara.", "RM42.00")
    + _card("Udang Bakar (per kg)", "Udang besar dibakar atas bara.", "RM55.00")
)

#: What actually shipped: card 4 wears card 3's name and description.
SHIPPED = _page(
    _card("Ikan Siakap Bakar (per kg)", "Siakap segar dari Port Klang.", "RM48.00")
    + _card("Ikan Kembung Bakar (3 ekor)", "Tiga ekor kembung segar.", "RM18.00")
    + _card("Sotong Bakar (per kg)", "Sotong segar dibakar atas bara.", "RM42.00")
    + _card("Sotong Bakar (per kg)", "Sotong segar dibakar atas bara.", "RM55.00")
)


def _codes(html, items=ITEMS, **kw):
    brief = GenerationBrief(
        business_name="Ikan Bakar Tepi Sungai Pak Long", menu_items=items, **kw
    )
    return [e.code for e in validate_generated_site(html, brief).errors]


class TestTheShippedPageIsCaught:
    def test_the_swapped_card_is_an_error(self):
        codes = _codes(SHIPPED)
        assert "item_price_name_mismatch" in codes

    def test_the_vanished_item_is_an_error(self):
        assert "missing_item_name" in _codes(SHIPPED)

    def test_the_repeated_name_is_an_error(self):
        assert "duplicate_item_name" in _codes(SHIPPED)

    def test_the_detail_names_both_sides_of_the_swap(self):
        brief = GenerationBrief(menu_items=ITEMS)
        detail = next(
            e.detail for e in validate_generated_site(SHIPPED, brief).errors
            if e.code == "item_price_name_mismatch"
        )
        assert "Udang Bakar (per kg)" in detail and "RM55.00" in detail
        assert "Sotong Bakar (per kg)" in detail

    def test_the_old_checks_really_did_pass_it(self):
        # The point of the new check: price integrity and derived-name both
        # saw nothing wrong with this page.
        codes = _codes(SHIPPED)
        assert "missing_price" not in codes
        assert "fabricated_item_name" not in codes


class TestACorrectPageIsSilent:
    def test_no_item_errors(self):
        codes = _codes(CORRECT)
        for code in ("missing_item_name", "duplicate_item_name", "item_price_name_mismatch"):
            assert code not in codes

    def test_a_summary_band_repeating_prices_is_not_a_mismatch(self):
        # The orange band above the menu repeats the same prices under short
        # labels. That is a summary, not a second claim about an item, and
        # it must not be read as one.
        band = (
            '<section aria-label="Ikan dan harga"><div>Siakap</div><div>RM48.00</div>'
            "<div>Sotong</div><div>RM42.00</div></section>"
        )
        codes = _codes(_page(
            _card("Ikan Siakap Bakar (per kg)", "a", "RM48.00")
            + _card("Ikan Kembung Bakar (3 ekor)", "b", "RM18.00")
            + _card("Sotong Bakar (per kg)", "c", "RM42.00")
            + _card("Udang Bakar (per kg)", "d", "RM55.00"),
            band=band,
        ))
        assert "item_price_name_mismatch" not in codes

    def test_a_brief_with_no_items_says_nothing(self):
        assert _codes(CORRECT, items=[]) == _codes(CORRECT, items=[])
        codes = _codes("<html><body><p>hi</p></body></html>", items=[])
        for code in ("missing_item_name", "duplicate_item_name", "item_price_name_mismatch"):
            assert code not in codes

    def test_an_item_with_no_price_is_still_required_to_appear(self):
        items = [{"name": "Pakej Doa Selamat", "price": ""}]
        assert "missing_item_name" in _codes("<html><body><h3>Nasi Minyak</h3></body></html>", items=items)
        assert "missing_item_name" not in _codes(
            "<html><body><h3>Pakej Doa Selamat</h3></body></html>", items=items
        )


class TestTheKateringShape:
    """An item that simply vanished — the run before this one."""

    def test_a_dropped_item_is_reported_with_its_price(self):
        items = [
            {"name": "Pakej Kahwin", "price": "RM4000.00"},
            {"name": "Pakej Doa Selamat", "price": "RM800.00"},
        ]
        html = _page(_card("Pakej Kahwin", "400 orang.", "RM4000.00"))
        errors = validate_generated_site(html, GenerationBrief(menu_items=items)).errors
        missing = [e for e in errors if e.code == "missing_item_name"]
        assert len(missing) == 1
        assert "Pakej Doa Selamat" in missing[0].detail
        assert "RM800.00" in missing[0].detail
