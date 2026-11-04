"""Menu Import — reading a merchant's existing menu into draft rows.

    services/menu_import.py           extraction, heuristic parser, AI glue, selection, normalisation
    api/v1/endpoints/menu_import.py   POST /menu/import/extract, POST /menu/websites/{id}/menu-items/bulk

What matters:

  1. A real Malaysian menu (the Ayam Gepuk Panglima sample this feature was
     built against) parses WITHOUT any model: every priced item, its
     section, the ingredient line, the SIGNATURE flag, and nothing from the
     "COMING SOON" list.
  2. The AI path is a drop-in for the same result shape, degrades to the
     parser when the model fails, and never invents a price.
  3. The merchant's selection ("signature only", "5 killer menu sahaja",
     "kecuali minuman") narrows the rows deterministically.
  4. ``extract`` saves nothing and is rate-limited; ``bulk`` checks the plan
     once for the batch and creates categories by name.
"""

from __future__ import annotations

import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import menu_import as mi

# ---------------------------------------------------------------------------
# Fixtures: the sample menu as text (what the .docx extractor produces)
# ---------------------------------------------------------------------------

AYAM_GEPUK = """AYAM GEPUK PANGLIMA
MAKIN PEDAS MAKIN PADU
MENU
 SET AYAM
Semua set dihidang bersama nasi, sambal & timun
Set A\tRM 12.50
Nasi, ayam, kubis, timun, sambal
Set B\tRM 13.50
Nasi, ayam, kubis, sambal, tauhu, tempe, timun
Set Panglima Krispy\tRM 14.90
Nasi, ayam krispy, kubis goreng, tauhu, tempe, timun, sambal
Set Panglima   SIGNATURE \tRM 15.90
Nasi, ayam, tauhu, tempe, kubis goreng, timun, sambal, telur mata
 SET SEAFOOD KRISPY
Set Sotong Krispy\tRM 20.90
Nasi, sotong krispy, tauhu, tempe, kubis, timun, sambal
 TAMBAHAN (ADD ON)
Ayam Ori\tRM 7.00
Pedal (3 pcs)\tRM 3.00
Telur Mata\tRM 2.00
Sup\tRM 1.00
PERCUMA tambah sambal & nasi untuk makan di kedai (DINE IN)
 MINUMAN
Teh O Ice\tRM 3.00
Air Mineral (1.5L)\tRM 3.50
 SPECIAL DRINK
RM 5.00 — semua jenis
Bali Blues
Es Jeruk
 KID'S MENU
Fries + Tender Chicken  (3 pcs)\tRM 9.90
 COMING SOON
Bakso Daging  •  Nasi Lemak  •  Bayam Goreng
Kaki Ayam  •  Chicken Wing
"""


def _docx(paragraphs, table_rows=()):
    """A minimal .docx: paragraphs (tab = \\t) and an optional table."""
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = []
    for p in paragraphs:
        runs = []
        for i, part in enumerate(p.split("\t")):
            if i:
                runs.append("<w:r><w:tab/></w:r>")
            runs.append(f"<w:r><w:t xml:space=\"preserve\">{part}</w:t></w:r>")
        body.append(f"<w:p>{''.join(runs)}</w:p>")
    if table_rows:
        rows = "".join(
            "<w:tr>" + "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in row) + "</w:tr>"
            for row in table_rows
        )
        body.append(f"<w:tbl>{rows}</w:tbl>")
    xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document {w}><w:body>{"".join(body)}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def _xlsx(rows):
    s = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    strings = []

    def sref(text):
        strings.append(text)
        return len(strings) - 1

    row_xml = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, value in enumerate(row):
            col = chr(ord("A") + c)
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{col}{r}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{col}{r}" t="s"><v>{sref(value)}</v></c>')
        row_xml.append(f'<row r="{r}">{"".join(cells)}</row>')
    sheet = f'<worksheet {s}><sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    sst = f'<sst {s}>' + "".join(f"<si><t>{t}</t></si>" for t in strings) + "</sst>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", sst)
    return buf.getvalue()


def _pdf_with_text(lines):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Heuristic parser on the real menu
# ---------------------------------------------------------------------------

class TestHeuristicParserOnRealMenu:
    def setup_method(self):
        self.items, self.categories, self.skipped, self.warnings = mi.parse_menu_text(AYAM_GEPUK)
        self.by_name = {i.name: i for i in self.items}

    def test_every_priced_item_is_found_and_nothing_else(self):
        assert sorted(self.by_name) == sorted([
            "Set A", "Set B", "Set Panglima Krispy", "Set Panglima", "Set Sotong Krispy",
            "Ayam Ori", "Pedal (3 pcs)", "Telur Mata", "Sup",
            "Teh O Ice", "Air Mineral (1.5L)", "Bali Blues", "Es Jeruk",
            "Fries + Tender Chicken (3 pcs)",
        ])

    def test_prices_are_canonical_decimals(self):
        assert self.by_name["Set A"].price == "12.50"
        assert self.by_name["Sup"].price == "1.00"
        assert self.by_name["Fries + Tender Chicken (3 pcs)"].price == "9.90"

    def test_section_headings_become_title_case_categories_in_order(self):
        assert self.categories == [
            "Set Ayam", "Set Seafood Krispy", "Tambahan (Add On)", "Minuman", "Special Drink", "Kid's Menu",
        ]
        # The title, tagline and bare "MENU" heading never had an item → dropped.
        assert "Ayam Gepuk Panglima" not in self.categories
        assert "Menu" not in self.categories

    def test_items_carry_their_section(self):
        assert self.by_name["Set A"].category == "Set Ayam"
        assert self.by_name["Set Sotong Krispy"].category == "Set Seafood Krispy"
        assert self.by_name["Teh O Ice"].category == "Minuman"
        assert self.by_name["Fries + Tender Chicken (3 pcs)"].category == "Kid's Menu"

    def test_ingredient_line_under_an_item_is_its_description(self):
        assert self.by_name["Set A"].description == "Nasi, ayam, kubis, timun, sambal"
        # The section note above the first set is NOT a description.
        assert all("Semua set" not in (i.description or "") for i in self.items)
        # The all-caps "PERCUMA ..." note is not glued onto "Sup".
        assert self.by_name["Sup"].description is None

    def test_signature_marker_is_stripped_from_the_name_and_flagged(self):
        item = self.by_name["Set Panglima"]
        assert item.is_signature is True
        assert sum(1 for i in self.items if i.is_signature) == 1

    def test_section_wide_price_applies_to_unpriced_names_under_it(self):
        assert self.by_name["Bali Blues"].price == "5.00"
        assert self.by_name["Es Jeruk"].price == "5.00"
        assert self.by_name["Bali Blues"].confidence < 1.0
        assert self.by_name["Bali Blues"].category == "Special Drink"

    def test_coming_soon_items_are_skipped_and_reported(self):
        assert "Bakso Daging" not in self.by_name
        assert self.skipped == ["Bakso Daging", "Nasi Lemak", "Bayam Goreng", "Kaki Ayam", "Chicken Wing"]
        assert any("Dilangkau" in w and "Bakso Daging" in w for w in self.warnings)


class TestLineParser:
    @pytest.mark.parametrize("line,name,price", [
        ("Nasi Lemak ........ RM 8.50", "Nasi Lemak", "8.50"),
        ("Nasi Lemak\tRM8", "Nasi Lemak", "8.00"),
        ("Teh Tarik 2.50", "Teh Tarik", "2.50"),
        ("Roti Canai RM 1,50", "Roti Canai", "1.50"),
        ("Set A RM 12.50 (nasi, ayam, sambal)", "Set A", "12.50"),
        ("- Mee Goreng Mamak — RM7.00", "Mee Goreng Mamak", "7.00"),
        ("Nasi Ayam | RM 9.90 | nasi, ayam, sup", "Nasi Ayam", "9.90"),
    ])
    def test_classic_lines(self, line, name, price):
        parsed = mi.parse_item_line(mi._clean_line(line))
        assert parsed is not None
        assert parsed.name == name
        assert parsed.price == price

    def test_mid_line_price_keeps_the_tail_as_description(self):
        parsed = mi.parse_item_line("Set A RM 12.50 (nasi, ayam, sambal)")
        assert parsed.description == "nasi, ayam, sambal"

    def test_a_bare_trailing_integer_is_not_a_price(self):
        # "Nugget 5" is five nuggets, not RM5 — a price needs RM, decimals or a leader.
        assert mi.parse_item_line("Nugget 5") is None
        assert mi.parse_item_line("Air Mineral (1.5L)") is None
        assert mi.parse_item_line("Pedal (3 pcs)") is None

    def test_a_price_range_is_kept_as_text_not_guessed(self):
        parsed = mi.parse_item_line("Ikan Bakar RM15 - RM25")
        assert parsed.name == "Ikan Bakar"
        assert parsed.price is None
        assert parsed.price_raw == "RM15 - RM25"

    def test_several_prices_take_the_lowest_and_flag_for_review(self):
        parsed = mi.parse_item_line("Teh Tarik S RM2.50 L RM3.50")
        assert parsed.name == "Teh Tarik"
        assert parsed.price == "2.50"
        assert parsed.multi is True

    def test_price_only_line_has_an_empty_name(self):
        parsed = mi.parse_item_line("RM 8.50")
        assert parsed.name == ""
        assert parsed.price == "8.50"

    def test_name_then_price_on_the_next_line(self):
        items, _, _, _ = mi.parse_menu_text("MAKANAN\nNasi Lemak\nRM 8.50\nMee Goreng\nRM 7.00\n")
        assert [(i.name, i.price) for i in items] == [("Nasi Lemak", "8.50"), ("Mee Goreng", "7.00")]

    def test_phone_and_hours_lines_never_become_items(self):
        items, _, _, _ = mi.parse_menu_text(
            "Buka 10.00 pagi - 10.00 malam\nTel 012-345 6789\nNasi Lemak RM 8.50\n"
        )
        assert [i.name for i in items] == ["Nasi Lemak"]


class TestSignatureMarks:
    @pytest.mark.parametrize("raw,clean", [
        ("Set Panglima   SIGNATURE ", "Set Panglima"),
        ("★ Nasi Kandar Daging", "Nasi Kandar Daging"),
        ("Ayam Percik (Best Seller)", "Ayam Percik"),
        ("Laksa Johor - Chef's Special", "Laksa Johor"),
        ("Mee Rebus 🔥", "Mee Rebus"),
    ])
    def test_marks_are_removed_and_flagged(self, raw, clean):
        name, flagged = mi._strip_signature_marks(raw)
        assert (name, flagged) == (clean, True)

    def test_plain_names_are_untouched(self):
        assert mi._strip_signature_marks("Nasi Lemak Special") == ("Nasi Lemak Special", False)


# ---------------------------------------------------------------------------
# 2. Extraction
# ---------------------------------------------------------------------------

class TestExtraction:
    def test_docx_paragraphs_keep_tabs_and_tables_become_rows(self):
        data = _docx(["MINUMAN", "Teh Tarik\tRM 2.50"], table_rows=[("Kopi O", "RM 2.00"), ("Milo Ais", "RM 3.50")])
        src = mi.extract_source("menu.docx", None, data)
        assert src.kind == "docx"
        items, cats, _, _ = mi.parse_menu_text(src.text)
        assert [(i.name, i.price) for i in items] == [("Teh Tarik", "2.50"), ("Kopi O", "2.00"), ("Milo Ais", "3.50")]
        assert cats == ["Minuman"]

    def test_xlsx_rows_become_tab_lines(self):
        data = _xlsx([("Item", "Harga"), ("Nasi Lemak", 8.5), ("Mee Goreng", "RM 7")])
        src = mi.extract_source("menu.xlsx", None, data)
        items, _, _, _ = mi.parse_menu_text(src.text)
        assert [(i.name, i.price) for i in items] == [("Nasi Lemak", "8.50"), ("Mee Goreng", "7.00")]

    def test_csv_with_semicolons(self):
        src = mi.extract_source("menu.csv", "text/csv", b"Nama;Harga\nNasi Lemak;8.50\nTeh Tarik;2.50\n")
        items, _, _, _ = mi.parse_menu_text(src.text)
        assert [i.name for i in items] == ["Nasi Lemak", "Teh Tarik"]

    def test_text_pdf_is_read_through_its_text_layer(self):
        data = _pdf_with_text(["MAKANAN", "Nasi Lemak ........ RM 8.50", "Mee Goreng ........ RM 7.00"])
        src = mi.extract_source("menu.pdf", "application/pdf", data)
        assert src.kind == "pdf" and src.pages == 1 and src.has_text
        items, _, _, _ = mi.parse_menu_text(src.text)
        assert [(i.name, i.price) for i in items] == [("Nasi Lemak", "8.50"), ("Mee Goreng", "7.00")]

    def test_blank_pdf_is_treated_as_a_scan_and_rendered_for_vision(self):
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.showPage()
        c.save()
        src = mi.extract_source("scan.pdf", None, buf.getvalue())
        assert not src.has_text
        # pypdfium2 is installed → pages rendered; otherwise an actionable warning.
        assert src.images or any("imbasan" in w for w in src.warnings)

    def test_images_pass_through_for_the_vision_model(self):
        src = mi.extract_source("board.jpg", "image/jpeg", b"\xff\xd8fake")
        assert src.kind == "image" and src.images == [("image/jpeg", b"\xff\xd8fake")] and src.needs_vision

    def test_unsupported_and_corrupt_files_raise_actionable_errors(self):
        with pytest.raises(mi.MenuImportError) as e:
            mi.extract_source("menu.pptx", None, b"x")
        assert e.value.code == "unsupported_type"
        with pytest.raises(mi.MenuImportError) as e:
            mi.extract_source("menu.docx", None, b"not a zip")
        assert e.value.code == "unreadable"

    def test_kind_detection_falls_back_to_content_type(self):
        assert mi.detect_kind("upload", "application/pdf") == "pdf"
        assert mi.detect_kind("x.PNG", None) == "image"
        assert mi.detect_kind("x.exe", "application/octet-stream") is None


# ---------------------------------------------------------------------------
# 3. AI glue
# ---------------------------------------------------------------------------

class TestAiPayloadParsing:
    def test_tolerates_fences_prose_and_trailing_commas(self):
        raw = 'Here you go:\n```json\n{"items":[{"name":"Set A","price":"12.50",},],"categories":["Set Ayam"],}\n```'
        payload = mi.parse_ai_payload(raw)
        assert payload["items"][0]["name"] == "Set A"

    def test_a_bare_list_is_accepted_as_items(self):
        assert mi.parse_ai_payload('[{"name":"Teh","price":2}]') == {"items": [{"name": "Teh", "price": 2}]}

    def test_garbage_is_none(self):
        assert mi.parse_ai_payload("Sorry, I cannot read this.") is None
        assert mi.parse_ai_payload(None) is None

    def test_items_from_payload_never_invent_a_price(self):
        items, cats, skipped, notes = mi.items_from_ai_payload({
            "items": [
                {"name": "Set Panglima ★", "price": "15.90", "category": "set ayam", "is_signature": False},
                {"name": "Ikan Bakar", "price": "ikut saiz", "description": "", "category": None},
                {"name": "Teh Tarik", "price": 2.5},
                {"name": "", "price": "1.00"},
            ],
            "categories": ["Set Ayam", "Minuman"],
            "skipped": ["Bakso Daging"],
            "notes": ["Harga ikan ikut saiz"],
        })
        assert [(i.name, i.price) for i in items] == [("Set Panglima", "15.90"), ("Ikan Bakar", None), ("Teh Tarik", "2.50")]
        assert items[0].is_signature is True  # the ★ in the name counts
        assert items[0].category == "Set Ayam"
        assert items[1].price_raw == "ikut saiz"
        assert cats == ["Set Ayam", "Minuman"]
        assert skipped == ["Bakso Daging"] and notes == ["Harga ikan ikut saiz"]

    def test_prompt_carries_the_selection_mode(self):
        assert "EVERY orderable item" in mi.build_extraction_prompt("all", "", "ms", 60)
        assert "signature" in mi.build_extraction_prompt("signature", "", "ms", 60).lower()
        custom = mi.build_extraction_prompt("custom", "5 killer menu sahaja", "en", 60)
        assert "5 killer menu sahaja" in custom

    def test_vision_messages_inline_images_as_data_urls(self):
        messages = mi.build_vision_messages([("image/png", b"\x89PNGfake")], "all", "", "ms", 60)
        parts = messages[0]["content"]
        assert parts[0]["type"] == "image_url"
        assert parts[0]["image_url"]["url"].startswith("data:image/png;base64,")
        assert parts[-1]["type"] == "text"


class TestImportMenuOrchestration:
    AI_JSON = (
        '{"items":[{"name":"Set Panglima","price":"15.90","category":"Set Ayam","is_signature":true},'
        '{"name":"Teh O Ice","price":"3.00","category":"Minuman"}],"categories":["Set Ayam","Minuman"],'
        '"skipped":["Bakso Daging"],"notes":[]}'
    )

    @pytest.mark.asyncio
    async def test_text_model_result_wins_when_it_answers(self):
        src = mi.ExtractedSource(kind="text", text=AYAM_GEPUK)
        text_model = AsyncMock(return_value=self.AI_JSON)
        result = await mi.import_menu(src, call_text_model=text_model, call_vision_model=AsyncMock(return_value=None))
        assert result.engine == "ai-text"
        assert [i.name for i in result.items] == ["Set Panglima", "Teh O Ice"]
        assert result.categories == ["Set Ayam", "Minuman"]
        assert result.skipped == ["Bakso Daging"]
        text_model.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_the_parser_when_the_model_fails(self):
        src = mi.ExtractedSource(kind="text", text=AYAM_GEPUK)
        result = await mi.import_menu(src, call_text_model=AsyncMock(return_value=None), call_vision_model=AsyncMock(return_value=None))
        assert result.engine == "heuristic"
        assert len(result.items) == 14
        assert any("tanpa AI" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_model_exceptions_never_escape(self):
        src = mi.ExtractedSource(kind="text", text="Nasi Lemak RM 8.50")
        result = await mi.import_menu(src, call_text_model=AsyncMock(side_effect=RuntimeError("boom")), call_vision_model=None)
        assert result.engine == "heuristic" and [i.name for i in result.items] == ["Nasi Lemak"]

    @pytest.mark.asyncio
    async def test_images_go_to_the_vision_model(self):
        src = mi.ExtractedSource(kind="image", images=[("image/jpeg", b"fake")])
        vision = AsyncMock(return_value=self.AI_JSON)
        result = await mi.import_menu(src, call_text_model=AsyncMock(return_value=None), call_vision_model=vision)
        assert result.engine == "ai-vision" and len(result.items) == 2
        vision.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_an_image_with_no_vision_model_is_a_clear_error(self):
        src = mi.ExtractedSource(kind="image", images=[("image/jpeg", b"fake")])
        with pytest.raises(mi.MenuImportError) as e:
            await mi.import_menu(src, call_text_model=None, call_vision_model=AsyncMock(return_value=None))
        assert e.value.code == "vision_unavailable"

    @pytest.mark.asyncio
    async def test_use_ai_false_is_pure_and_quiet(self):
        src = mi.ExtractedSource(kind="text", text=AYAM_GEPUK)
        result = await mi.import_menu(src, use_ai=False)
        assert result.engine == "heuristic"
        assert not any("AI" in w for w in result.warnings)
        assert result.total_found == 14

    @pytest.mark.asyncio
    async def test_signature_mode_narrows_to_flagged_items(self):
        src = mi.ExtractedSource(kind="text", text=AYAM_GEPUK)
        result = await mi.import_menu(src, mode="signature", use_ai=False)
        assert [i.name for i in result.items] == ["Set Panglima"]
        assert result.total_found == 14

    @pytest.mark.asyncio
    async def test_custom_instruction_filters_and_caps(self):
        src = mi.ExtractedSource(kind="text", text=AYAM_GEPUK)
        result = await mi.import_menu(src, mode="custom", instruction="minuman sahaja, 2 item", use_ai=False)
        assert [i.name for i in result.items] == ["Teh O Ice", "Air Mineral (1.5L)"]

    @pytest.mark.asyncio
    async def test_max_items_caps_and_flags_truncation(self):
        src = mi.ExtractedSource(kind="text", text=AYAM_GEPUK)
        result = await mi.import_menu(src, max_items=5, use_ai=False)
        assert len(result.items) == 5 and result.truncated is True


# ---------------------------------------------------------------------------
# 4. Selection
# ---------------------------------------------------------------------------

class TestInstructionInterpretation:
    def test_count_and_signature_intent(self):
        parsed = mi.interpret_instruction("5 killer menu sahaja")
        assert parsed.limit == 5 and parsed.wants_signature is True and parsed.include == []

    def test_number_words(self):
        assert mi.interpret_instruction("tiga item signature je").limit == 3
        assert mi.interpret_instruction("top five best sellers").limit == 5

    def test_include_and_exclude_tokens(self):
        parsed = mi.interpret_instruction("set ayam dan minuman, kecuali add-on")
        assert parsed.include == ["set", "ayam", "minuman"]
        assert parsed.exclude == ["add-on"]
        assert parsed.wants_signature is False

    def test_english_exclusion(self):
        parsed = mi.interpret_instruction("everything except drinks")
        assert parsed.include == ["everything"] and parsed.exclude == ["drinks"]


class TestApplySelection:
    def _items(self):
        return [
            mi.DraftItem("Set Panglima", "15.90", category="Set Ayam", is_signature=True),
            mi.DraftItem("Set A", "12.50", category="Set Ayam"),
            mi.DraftItem("Teh O Ice", "3.00", category="Minuman"),
            mi.DraftItem("Ayam Ori", "7.00", category="Tambahan (Add On)"),
        ]

    def test_all_returns_everything(self):
        items, warnings = mi.apply_selection(self._items(), "all", "", engine="heuristic")
        assert len(items) == 4 and warnings == []

    def test_signature_returns_flagged_only(self):
        items, _ = mi.apply_selection(self._items(), "signature", "", engine="heuristic")
        assert [i.name for i in items] == ["Set Panglima"]

    def test_signature_with_nothing_marked_shows_all_with_a_warning(self):
        plain = [i for i in self._items() if not i.is_signature]
        items, warnings = mi.apply_selection(plain, "signature", "", engine="heuristic")
        assert len(items) == 3 and any("signature" in w.lower() for w in warnings)

    def test_signature_from_an_ai_engine_trusts_the_model_pick(self):
        plain = [i for i in self._items() if not i.is_signature]
        items, warnings = mi.apply_selection(plain, "signature", "", engine="ai-text")
        assert len(items) == 3 and warnings == []

    def test_custom_include_exclude_and_limit(self):
        items, _ = mi.apply_selection(self._items(), "custom", "set kecuali panglima", engine="heuristic")
        assert [i.name for i in items] == ["Set A"]
        items, _ = mi.apply_selection(self._items(), "custom", "2 item", engine="heuristic")
        assert len(items) == 2

    def test_custom_killer_menu_prefers_flagged_items(self):
        items, _ = mi.apply_selection(self._items(), "custom", "killer menu sahaja", engine="heuristic")
        assert [i.name for i in items] == ["Set Panglima"]

    def test_custom_with_no_match_shows_all_and_warns(self):
        items, warnings = mi.apply_selection(self._items(), "custom", "dessert sahaja", engine="heuristic")
        assert len(items) == 4 and warnings


# ---------------------------------------------------------------------------
# 5. Normalisation
# ---------------------------------------------------------------------------

class TestNormalisation:
    def test_dedupes_case_insensitively_and_merges_missing_fields(self):
        items, warnings, truncated = mi.normalise_items([
            mi.DraftItem("Nasi Lemak", None, description=None),
            mi.DraftItem("nasi  lemak", "8.50", description="sambal, telur"),
        ], 60)
        assert len(items) == 1
        assert items[0].price == "8.50" and items[0].description == "sambal, telur"
        assert any("berulang" in w for w in warnings)

    def test_drops_rows_the_generator_would_refuse(self):
        items, warnings, _ = mi.normalise_items([
            mi.DraftItem("Hubungi Kami", "0.00"),
            mi.DraftItem("WhatsApp", "1.00"),
            mi.DraftItem("Nasi Lemak", "8.50"),
        ], 60)
        assert [i.name for i in items] == ["Nasi Lemak"]
        assert any("bukan item" in w for w in warnings)

    def test_counts_missing_prices(self):
        items, warnings, _ = mi.normalise_items([mi.DraftItem("Ikan Bakar", None, price_raw="ikut saiz")], 60)
        assert items[0].price is None
        assert any("tiada harga" in w for w in warnings)

    def test_caps_to_the_hard_limit(self):
        many = [mi.DraftItem(f"Nasi Goreng {i}", "1.00") for i in range(200)]
        items, _, truncated = mi.normalise_items(many, 1000)
        assert len(items) == mi.MAX_ITEMS_HARD_CAP and truncated

    @pytest.mark.parametrize("raw,expected", [
        ("RM 12.50", "12.50"), ("12,5", "12.50"), (7, "7.00"), ("RM8", "8.00"), ("ikut pasaran", None), ("", None), (None, None),
    ])
    def test_canonical_price(self, raw, expected):
        assert mi.canonical_price(raw) == expected


# ---------------------------------------------------------------------------
# 6. Endpoints
# ---------------------------------------------------------------------------

@pytest.fixture
def import_env(monkeypatch):
    from app.api.v1.endpoints import menu_import as ep

    ep._reset_rate_limits()
    monkeypatch.setenv("MENU_IMPORT_ENABLED", "true")
    monkeypatch.setenv("MENU_IMPORT_MAX_PER_HOUR", "3")
    with (
        patch("app.services.menu_import.default_call_text_model", new=AsyncMock(return_value=None)) as text_model,
        patch("app.services.menu_import.default_call_vision_model", new=AsyncMock(return_value=None)) as vision_model,
        patch(
            "app.api.v1.endpoints.menu_import.subscription_service.check_limit",
            new=AsyncMock(return_value={"allowed": True, "current_usage": 3, "limit": 20, "unlimited": False}),
        ) as check_limit,
    ):
        yield {"text_model": text_model, "vision_model": vision_model, "check_limit": check_limit}
    ep._reset_rate_limits()


class TestExtractEndpoint:
    URL = "/api/v1/menu/import/extract"

    def test_requires_auth(self, client, import_env):
        assert client.post(self.URL, data={"text": "Nasi Lemak RM 8.50"}).status_code in (401, 403)

    def test_needs_a_file_or_text(self, client, auth_headers, import_env):
        resp = client.post(self.URL, data={"mode": "all"}, headers=auth_headers)
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"] == "no_input"

    def test_pasted_text_returns_a_draft_and_the_plan_snapshot(self, client, auth_headers, import_env):
        resp = client.post(self.URL, data={"text": AYAM_GEPUK, "mode": "all"}, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["engine"] == "heuristic"  # the model mock returned None
        assert len(body["items"]) == 14
        assert body["categories"][0] == "Set Ayam"
        assert body["plan"] == {
            "menu_items_limit": 20, "menu_items_used": 3, "remaining": 17,
            "unlimited": False, "allowed": True, "requires_renewal": False,
        }
        assert body["items"][0] == {
            "name": "Set A", "price": "12.50", "description": "Nasi, ayam, kubis, timun, sambal",
            "category": "Set Ayam", "is_signature": False, "confidence": 1.0, "price_raw": None,
            "source_line": "Set A\tRM 12.50",
        }

    def test_ai_answer_is_used_when_the_model_replies(self, client, auth_headers, import_env):
        import_env["text_model"].return_value = (
            '{"items":[{"name":"Set Panglima","price":"15.90","category":"Set Ayam","is_signature":true}],"categories":["Set Ayam"]}'
        )
        resp = client.post(self.URL, data={"text": AYAM_GEPUK, "mode": "signature"}, headers=auth_headers)
        body = resp.json()
        assert resp.status_code == 200 and body["engine"] == "ai-text"
        assert [i["name"] for i in body["items"]] == ["Set Panglima"]
        prompt = import_env["text_model"].await_args.args[0]
        assert "signature" in prompt.lower() and "Set A\tRM 12.50" in prompt

    def test_docx_upload(self, client, auth_headers, import_env):
        data = _docx(["MINUMAN", "Teh Tarik\tRM 2.50", "Kopi O\tRM 2.00"])
        resp = client.post(
            self.URL,
            files={"file": ("menu.docx", data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"mode": "all"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["source"]["kind"] == "docx"
        assert [i["name"] for i in body["items"]] == ["Teh Tarik", "Kopi O"]

    def test_unsupported_file_is_415(self, client, auth_headers, import_env):
        resp = client.post(self.URL, files={"file": ("deck.pptx", b"x", "application/octet-stream")}, headers=auth_headers)
        assert resp.status_code == 415
        assert resp.json()["detail"]["error"] == "unsupported_type"

    def test_image_without_a_vision_model_is_422(self, client, auth_headers, import_env):
        resp = client.post(self.URL, files={"file": ("board.jpg", b"\xff\xd8fake", "image/jpeg")}, headers=auth_headers)
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "vision_unavailable"

    def test_bad_mode_is_400(self, client, auth_headers, import_env):
        resp = client.post(self.URL, data={"text": "x RM 1.00", "mode": "random"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_rate_limited_after_the_hourly_cap(self, client, auth_headers, import_env):
        for _ in range(3):
            assert client.post(self.URL, data={"text": "Nasi Lemak RM 8.50"}, headers=auth_headers).status_code == 200
        resp = client.post(self.URL, data={"text": "Nasi Lemak RM 8.50"}, headers=auth_headers)
        assert resp.status_code == 429

    def test_feature_flag_off_hides_the_route(self, client, auth_headers, import_env, monkeypatch):
        monkeypatch.setenv("MENU_IMPORT_ENABLED", "false")
        resp = client.post(self.URL, data={"text": "Nasi Lemak RM 8.50"}, headers=auth_headers)
        assert resp.status_code == 404


class _FakeSupabase:
    """Just enough of the supabase-py chain for the bulk endpoint."""

    def __init__(self, owner_id, existing_items=(), categories=()):
        self.owner_id = owner_id
        self.existing_items = [{"name": n} for n in existing_items]
        self.categories = [{"id": f"cat-{i}", "name": n, "sort_order": i} for i, n in enumerate(categories)]
        self.inserted_items = []
        self.inserted_categories = []

    def table(self, name):
        return _FakeTable(self, name)


class _FakeTable:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload = db, name, "select", None

    def select(self, *_):
        self.op = "select"
        return self

    def eq(self, *_):
        return self

    def insert(self, payload):
        self.op, self.payload = "insert", payload
        return self

    def execute(self):
        resp = MagicMock()
        if self.name == "websites":
            resp.data = [{"user_id": self.db.owner_id}]
        elif self.name == "menu_items" and self.op == "select":
            resp.data = list(self.db.existing_items) + [{"id": f"it-{i}", "name": r["name"]} for i, r in enumerate(self.db.inserted_items)]
        elif self.name == "menu_items":
            rows = [{"id": f"new-{len(self.db.inserted_items) + i}", **r} for i, r in enumerate(self.payload)]
            self.db.inserted_items.extend(rows)
            resp.data = rows
        elif self.name == "menu_categories" and self.op == "select":
            resp.data = list(self.db.categories)
        elif self.name == "menu_categories":
            row = {"id": f"cat-new-{len(self.db.inserted_categories)}", **self.payload}
            self.db.inserted_categories.append(row)
            self.db.categories.append(row)
            resp.data = [row]
        else:
            resp.data = []
        return resp


@pytest.fixture
def bulk_db(test_user_id):
    from app.core.supabase import get_supabase_client
    from app.main import app

    db = _FakeSupabase(owner_id=test_user_id, existing_items=["Teh O Ice"], categories=["Minuman"])
    app.dependency_overrides[get_supabase_client] = lambda: db
    yield db
    app.dependency_overrides.pop(get_supabase_client, None)


class TestBulkEndpoint:
    URL = "/api/v1/menu/websites/ws-1/menu-items/bulk"
    ITEMS = [
        {"name": "Set Panglima", "price": "15.90", "category": "Set Ayam", "is_signature": True, "description": "Nasi, ayam"},
        {"name": "Set A", "price": "12.50", "category": "Set Ayam"},
        {"name": "Teh O Ice", "price": "3.00", "category": "Minuman"},        # already on the site
        {"name": "Limau Ice", "price": "3.50", "category": "Minuman"},        # existing category
        {"name": "Ikan Bakar", "price": None, "category": "Lauk"},            # no price → skipped
        {"name": "set a", "price": "12.50"},                                   # duplicate in request
    ]

    def test_requires_auth(self, client, import_env, bulk_db):
        assert client.post(self.URL, json={"items": self.ITEMS}).status_code in (401, 403)

    def test_inserts_reviewed_rows_creates_categories_and_counts_usage(self, client, auth_headers, import_env, bulk_db):
        with patch("app.api.v1.endpoints.menu_import.subscription_service.increment_usage", new=AsyncMock(return_value=True)) as inc:
            resp = client.post(self.URL, json={"items": self.ITEMS}, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["created"] == 3
        assert sorted(s["reason"] for s in body["skipped"]) == ["already_exists", "duplicate_in_request", "no_price"]
        assert body["categories_created"] == ["Set Ayam"]
        rows = bulk_db.inserted_items
        assert [r["name"] for r in rows] == ["Set Panglima", "Set A", "Limau Ice"]
        assert rows[0]["is_popular"] is True and rows[0]["price"] == 15.9 and rows[0]["description"] == "Nasi, ayam"
        assert rows[0]["category_id"] == rows[1]["category_id"] == "cat-new-0"
        assert rows[2]["category_id"] == "cat-0"  # the existing "Minuman"
        inc.assert_awaited_once()
        assert inc.await_args.kwargs.get("count") == 3

    def test_refuses_more_rows_than_the_plan_has_left(self, client, auth_headers, import_env, bulk_db):
        import_env["check_limit"].return_value = {"allowed": True, "current_usage": 19, "limit": 20, "unlimited": False}
        resp = client.post(self.URL, json={"items": self.ITEMS}, headers=auth_headers)
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["error"] == "menu_item_limit" and detail["remaining"] == 1 and detail["requested"] == 3
        assert bulk_db.inserted_items == []

    def test_rejects_a_site_owned_by_someone_else(self, client, auth_headers, import_env, bulk_db):
        bulk_db.owner_id = "someone-else"
        resp = client.post(self.URL, json={"items": self.ITEMS}, headers=auth_headers)
        assert resp.status_code == 403

    def test_nothing_to_insert_is_a_quiet_201(self, client, auth_headers, import_env, bulk_db):
        resp = client.post(self.URL, json={"items": [{"name": "Teh O Ice", "price": "3.00"}]}, headers=auth_headers)
        assert resp.status_code == 201 and resp.json()["created"] == 0
        import_env["check_limit"].assert_not_awaited()


# ---------------------------------------------------------------------------
# 7. Publish helper
# ---------------------------------------------------------------------------

class TestPlanPublishMenuRows:
    def test_rows_keep_category_star_and_description_and_drop_unpriced(self):
        rows, cats = mi.plan_publish_menu_rows([
            {"name": "Set Panglima", "price": 15.9, "category": "Set Ayam", "is_popular": True, "description": "Nasi, ayam", "image_url": None},
            {"name": "Set A", "price": "12.50", "category": "set ayam"},
            {"name": "Teh O Ice", "price": "3.00", "category": "Minuman", "url": "https://img/teh.jpg"},
            {"name": "Ikan Bakar", "price": None, "category": "Lauk"},
            {"name": "Keropok", "price": "2.00"},
            "junk",
        ], "ws-1")
        assert [r["name"] for r in rows] == ["Set Panglima", "Set A", "Teh O Ice", "Keropok"]
        assert cats == ["Set Ayam", "Minuman"]  # case-insensitive, first-seen order; unpriced row's category not created
        assert rows[0]["is_popular"] is True and rows[0]["_category"] == "Set Ayam" and rows[0]["description"] == "Nasi, ayam"
        assert rows[1]["is_popular"] is False and rows[1]["price"] == 12.5
        assert rows[2]["image_url"] == "https://img/teh.jpg"
        assert rows[3]["_category"] is None and rows[3]["description"] == "Hidangan istimewa dari dapur kami"
        assert all(r["website_id"] == "ws-1" and r["is_available"] is True for r in rows)
