"""Menu Import — read the menu a merchant ALREADY has into structured items.

Typing a 40-line menu one row at a time is the slowest step of the create
page. Most merchants have the menu somewhere already: a PDF from the printer,
a Word file, an Excel sheet, a photo of the menu board, a WhatsApp message.
This module turns any of those into the same ``{name, price, description,
category, is_signature}`` rows the create page collects by hand.

PIPELINE
--------
1. ``extract_source``   file bytes → text (and/or page images for a photo or
                        a scanned PDF). Pure: no network, no AI.
2. ``parse_menu_text``  deterministic line parser: "Set A ..... RM 12.50",
                        section headings → categories, the ingredient line
                        under an item → description, SIGNATURE/★ → flag,
                        "COMING SOON" sections skipped. It is the no-API
                        fallback AND the offline test target, so it has to
                        be good on real Malaysian menus, not perfect.
3. ``extract_with_ai``  the same job done by a text model (DeepSeek / GLM /
                        Qwen) or, for images, a vision model (GLM-4.5V /
                        Qwen-VL). The model callers are injected so tests
                        never touch the network; the defaults read the same
                        env vars as ``ai_service``.
4. ``apply_selection``  the merchant's choice: every item, signature items
                        only, or a free-text instruction ("5 killer menu
                        sahaja", "set ayam dan minuman, kecuali add-on").
5. ``normalise_items``  dedupe, canonical "12.50" prices, the same
                        ``is_valid_menu_item_name`` gate the generator
                        applies (so nothing imported here vanishes later),
                        cap, warnings.

NOTHING HERE WRITES TO THE DATABASE. The result is a DRAFT the merchant
reviews in the UI (tick, untick, fix a price) before it becomes rows — the
human stays in the loop between "the AI read it" and "it is on my site".
"""

from __future__ import annotations

import asyncio
import base64
import csv
import io
import json
import os
import re
import zipfile
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET

import httpx
from loguru import logger

from app.services.menu_validator import is_valid_menu_item_name

# ---------------------------------------------------------------------------
# Limits and knobs (env-overridable where they cost money or memory)
# ---------------------------------------------------------------------------

#: Hard cap on items in one import — a review table longer than this is
#: unusable, and MenuItemInput lists are capped at 60 downstream anyway.
MAX_ITEMS_HARD_CAP = 150
DEFAULT_MAX_ITEMS = 60
#: Pages of a PDF we read (text) or render (scanned). A 40-page catalogue is
#: not a menu.
MAX_PDF_PAGES = 12
#: Below this many characters per page a PDF is treated as a scan and its
#: pages are rendered for the vision model instead.
SCANNED_PDF_CHARS_PER_PAGE = 40
#: Vision calls carry images inline (base64); keep each one small.
VISION_MAX_IMAGES = 6
VISION_IMAGE_MAX_SIDE = 1600
#: Text handed to the text model (characters). Menus are short; this only
#: protects against someone uploading a novel.
MAX_TEXT_CHARS = 60_000

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md",
    ".png", ".jpg", ".jpeg", ".webp",
}
_IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

SELECTION_MODES = ("all", "signature", "custom")


def ai_text_timeout_seconds() -> float:
    try:
        return max(10.0, float(os.getenv("MENU_IMPORT_AI_TIMEOUT_SECONDS", "90")))
    except ValueError:
        return 90.0


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class DraftItem:
    """One imported row, before the merchant has reviewed it."""

    name: str
    #: Canonical decimal string ("12.50") or None when the source gave no
    #: usable price. Never invented.
    price: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_signature: bool = False
    #: 1.0 = read straight off a priced line; lower when inferred (a
    #: section-wide price, a lowest-of-several price). The UI shows a hint.
    confidence: float = 1.0
    #: The price exactly as printed when it could not be reduced to one
    #: decimal ("RM5 - RM8", "S 2.50 / L 3.50") — shown so the merchant can
    #: decide.
    price_raw: Optional[str] = None
    source_line: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedSource:
    """What ``extract_source`` got out of the upload."""

    kind: str
    text: str = ""
    pages: int = 0
    #: (mime, bytes) pairs for the vision model — a photo, or rendered pages
    #: of a scanned PDF.
    images: List[Tuple[str, bytes]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def has_text(self) -> bool:
        return bool(self.text and self.text.strip())

    @property
    def needs_vision(self) -> bool:
        return bool(self.images) and not self.has_text

    def summary(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "pages": self.pages,
            "chars": len(self.text or ""),
            "images": len(self.images),
        }


@dataclass
class MenuImportResult:
    items: List[DraftItem]
    categories: List[str]
    warnings: List[str]
    #: "ai-text" | "ai-vision" | "heuristic"
    engine: str
    mode: str
    source: Dict[str, Any]
    #: Items found before the selection mode narrowed them.
    total_found: int = 0
    truncated: bool = False
    skipped: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "categories": self.categories,
            "warnings": self.warnings,
            "engine": self.engine,
            "mode": self.mode,
            "source": self.source,
            "total_found": self.total_found,
            "truncated": self.truncated,
            "skipped": self.skipped,
        }


class MenuImportError(Exception):
    """A problem the merchant can act on. ``code`` is stable for the UI."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# 1. Extraction — bytes → text / images
# ---------------------------------------------------------------------------

def detect_kind(filename: Optional[str], content_type: Optional[str]) -> Optional[str]:
    """``pdf`` / ``docx`` / ``xlsx`` / ``csv`` / ``text`` / ``image``, or None."""
    ext = os.path.splitext(filename or "")[1].lower()
    ct = (content_type or "").lower().split(";")[0].strip()
    if ext == ".pdf" or ct == "application/pdf":
        return "pdf"
    if ext == ".docx" or ct == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "docx"
    if ext == ".xlsx" or ct == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return "xlsx"
    if ext == ".csv" or ct == "text/csv":
        return "csv"
    if ext in (".txt", ".md") or ct in ("text/plain", "text/markdown"):
        return "text"
    if ext in _IMAGE_MIME or ct in _IMAGE_MIME.values():
        return "image"
    return None


def extract_source(filename: Optional[str], content_type: Optional[str], data: bytes) -> ExtractedSource:
    """Dispatch on the file kind. Raises MenuImportError for unsupported or
    unreadable input; never raises anything else on bad bytes."""
    kind = detect_kind(filename, content_type)
    if kind is None:
        raise MenuImportError(
            "unsupported_type",
            "Format fail tidak disokong. Muat naik PDF, Word (.docx), Excel (.xlsx), CSV, teks atau gambar (JPG/PNG/WebP).",
        )
    try:
        if kind == "pdf":
            return _extract_pdf(data)
        if kind == "docx":
            return _extract_docx(data)
        if kind == "xlsx":
            return _extract_xlsx(data)
        if kind == "csv":
            return _extract_csv(data)
        if kind == "text":
            return ExtractedSource(kind="text", text=_decode(data))
        mime = _IMAGE_MIME.get(os.path.splitext(filename or "")[1].lower()) or (content_type or "image/jpeg")
        return ExtractedSource(kind="image", images=[(mime, data)], pages=1)
    except MenuImportError:
        raise
    except Exception as err:  # corrupt zip, broken PDF, ...
        logger.warning(f"🍽️ Menu import: could not read {kind} upload: {err}")
        raise MenuImportError("unreadable", "Fail ini tidak dapat dibaca. Cuba simpan semula fail atau muat naik gambar menu.")


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> ExtractedSource:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - requirements install it
        raise MenuImportError("pdf_unavailable", "Pembaca PDF tidak tersedia di pelayan. Muat naik gambar menu sebagai alternatif.")

    reader = PdfReader(io.BytesIO(data))
    total_pages = len(reader.pages)
    warnings: List[str] = []
    if total_pages > MAX_PDF_PAGES:
        warnings.append(f"PDF ada {total_pages} muka surat — hanya {MAX_PDF_PAGES} pertama dibaca.")
    page_texts: List[str] = []
    for page in reader.pages[:MAX_PDF_PAGES]:
        try:
            page_texts.append(page.extract_text() or "")
        except Exception as err:  # one bad page must not sink the file
            logger.debug(f"🍽️ pypdf page failed: {err}")
            page_texts.append("")
    read_pages = len(page_texts)
    text = "\n".join(t for t in page_texts if t.strip())
    source = ExtractedSource(kind="pdf", text=text, pages=read_pages, warnings=warnings)

    chars = sum(len(t.strip()) for t in page_texts)
    if read_pages and chars < SCANNED_PDF_CHARS_PER_PAGE * read_pages:
        # A scan (or a designer's outlined-text PDF): no text layer worth
        # using. Render the pages for the vision model.
        images = _render_pdf_pages(data, read_pages)
        if images:
            source.images = images
            source.text = ""  # whatever pypdf found was noise
            source.warnings.append("PDF ini imbasan (tiada teks) — AI membaca muka surat sebagai gambar.")
        else:
            source.warnings.append(
                "PDF ini imbasan dan pelayan tidak dapat menukar muka surat kepada gambar. "
                "Muat naik tangkapan skrin/gambar menu sebagai alternatif."
            )
    return source


def _render_pdf_pages(data: bytes, pages: int) -> List[Tuple[str, bytes]]:
    """Rasterise up to VISION_MAX_IMAGES pages with pypdfium2 (pure wheels,
    no system poppler). Returns [] when the renderer is unavailable."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return []
    out: List[Tuple[str, bytes]] = []
    try:
        doc = pdfium.PdfDocument(io.BytesIO(data))
        for index in range(min(pages, VISION_MAX_IMAGES)):
            page = doc[index]
            bitmap = page.render(scale=1.6)
            pil = bitmap.to_pil()
            buf = io.BytesIO()
            pil.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
            out.append(("image/jpeg", buf.getvalue()))
    except Exception as err:
        logger.warning(f"🍽️ PDF render failed: {err}")
    return out


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_paragraph_text(p: ET.Element) -> str:
    parts: List[str] = []
    for node in p.iter():
        tag = node.tag
        if tag == f"{_W}t":
            parts.append(node.text or "")
        elif tag == f"{_W}tab":
            parts.append("\t")
        elif tag in (f"{_W}br", f"{_W}cr"):
            parts.append("\n")
    return "".join(parts)


def _extract_docx(data: bytes) -> ExtractedSource:
    """Word → lines. Body order is kept; a table row becomes one
    tab-separated line so "name | price" cells stay on one line."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml")
    root = ET.fromstring(xml)
    body = root.find(f"{_W}body")
    lines: List[str] = []
    if body is None:
        return ExtractedSource(kind="docx", text="")

    def walk(container: ET.Element) -> None:
        for child in container:
            if child.tag == f"{_W}p":
                lines.append(_docx_paragraph_text(child))
            elif child.tag == f"{_W}tbl":
                for row in child.iter(f"{_W}tr"):
                    cells = []
                    for cell in row.findall(f"{_W}tc"):
                        cells.append(" ".join(_docx_paragraph_text(p) for p in cell.iter(f"{_W}p")).strip())
                    lines.append("\t".join(c for c in cells if c))
            elif child.tag == f"{_W}sdt":  # content controls wrap paragraphs
                content = child.find(f"{_W}sdtContent")
                if content is not None:
                    walk(content)

    walk(body)
    return ExtractedSource(kind="docx", text="\n".join(lines), pages=1)


_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _extract_xlsx(data: bytes) -> ExtractedSource:
    """Excel → one tab-separated line per row, every sheet, stdlib only."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            sroot = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sroot.findall(f"{_S}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_S}t")))
        sheet_names = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        lines: List[str] = []
        for name in sheet_names:
            root = ET.fromstring(z.read(name))
            for row in root.iter(f"{_S}row"):
                cells: List[str] = []
                for c in row.findall(f"{_S}c"):
                    t = c.get("t")
                    v = c.find(f"{_S}v")
                    if t == "inlineStr":
                        value = "".join(x.text or "" for x in c.iter(f"{_S}t"))
                    elif v is None:
                        value = ""
                    elif t == "s":
                        try:
                            value = shared[int(v.text or "0")]
                        except (ValueError, IndexError):
                            value = ""
                    else:
                        value = v.text or ""
                    cells.append(value.strip())
                if any(cells):
                    lines.append("\t".join(cells))
            lines.append("")
    return ExtractedSource(kind="xlsx", text="\n".join(lines), pages=len(sheet_names))


def _extract_csv(data: bytes) -> ExtractedSource:
    text = _decode(data)
    try:
        dialect = csv.Sniffer().sniff(text[:4000], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = ["\t".join(cell.strip() for cell in row) for row in csv.reader(io.StringIO(text), dialect)]
    return ExtractedSource(kind="csv", text="\n".join(rows), pages=1)


# ---------------------------------------------------------------------------
# 2. Heuristic parser — text → DraftItems
# ---------------------------------------------------------------------------

_PRICE_NUM = r"\d{1,5}(?:[.,]\d{1,2})?"
#: A price with the currency prefix, anywhere in a line.
_RM_PRICE_RE = re.compile(rf"(?<![A-Za-z0-9])(?:RM|MYR)\s?({_PRICE_NUM})(?![\d.])", re.IGNORECASE)
#: "<name> <leader> [RM] <price> [/unit]" — the classic menu line.
_TRAILING_PRICE_RE = re.compile(
    rf"^(?P<name>.*?)(?P<leader>[\s.·…\-–—:]*)(?P<rm>RM|MYR)?\s*(?P<price>{_PRICE_NUM})\s*(?P<unit>/\s*[A-Za-z]{{1,10}})?\s*$",
    re.IGNORECASE,
)
_PRICE_ONLY_RE = re.compile(rf"^\s*(?:RM|MYR)?\s*({_PRICE_NUM})\s*$", re.IGNORECASE)
_RANGE_PRICE_RE = re.compile(rf"(?:RM|MYR)?\s?{_PRICE_NUM}\s*[-–—]\s*(?:RM|MYR)?\s?{_PRICE_NUM}", re.IGNORECASE)
_BULLET_RE = re.compile(r"^[\s•●○◦▪▫■□\-–—*·>]+")
_SIGNATURE_WORD_RE = re.compile(
    r"\(?\[?\b(signature|best[\s-]?seller|bestseller|popular|recommended|must[\s-]?try|wajib cuba|"
    r"terlaris|paling laku|chef'?s?\s+(?:choice|special|pick|recommendation)|hot[\s-]?seller|top[\s-]?seller)\b\]?\)?",
    re.IGNORECASE,
)
_SIGNATURE_SYMBOL_RE = re.compile(r"[★⭐🔥👍💯🌟✨]")
_SKIP_SECTION_RE = re.compile(
    r"\b(coming soon|akan datang|tidak tersedia|not available|sold out|habis|tutup sementara)\b", re.IGNORECASE
)
#: A short note about price that is not an item: "RM 5.00 — semua jenis".
_PRICE_NOTE_WORDS_RE = re.compile(r"^(?:[\-–—:]+\s*)?(semua|all|setiap|each|per|every|any)\b", re.IGNORECASE)
_SIZE_SUFFIX_RE = re.compile(
    r"\s*[\(\[]?\b(S|M|L|XL|XXL|kecil|sederhana|besar|small|medium|large|regular|reg)\b[\)\]]?\s*$", re.IGNORECASE
)
_TIME_RE = re.compile(r"\d{1,2}[:.]\d{2}\s*(am|pm)?|\d{1,2}\s*(am|pm|pagi|petang|malam)\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:\+?6?0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{3,4})")


def canonical_price(raw: Any) -> Optional[str]:
    """``"RM 12,5"`` → ``"12.50"``; None when it is not one number."""
    if raw is None:
        return None
    if isinstance(raw, (int, float, Decimal)):
        try:
            dec = Decimal(str(raw))
        except InvalidOperation:
            return None
    else:
        s = str(raw).strip()
        m = _PRICE_ONLY_RE.match(s)
        if not m:
            return None
        try:
            dec = Decimal(m.group(1).replace(",", "."))
        except InvalidOperation:
            return None
    if dec < 0 or dec > Decimal("100000"):
        return None
    return str(dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _title_case(text: str) -> str:
    """"KID'S MENU" → "Kid's Menu", "TAMBAHAN (ADD ON)" → "Tambahan (Add On)"."""
    words = []
    for word in text.split():
        idx = next((i for i, ch in enumerate(word) if ch.isalpha()), None)
        if idx is None:
            words.append(word)
            continue
        words.append(word[:idx] + word[idx].upper() + word[idx + 1:].lower())
    return " ".join(words)


def _clean_line(raw: str) -> str:
    line = raw.replace(" ", " ").replace("​", "")
    line = _BULLET_RE.sub("", line)
    # Keep tabs (they separate name from price); collapse other runs.
    line = re.sub(r"[ ]{2,}", "  ", line)
    return line.strip()


def _letters(text: str) -> str:
    return re.sub(r"[^A-Za-zÀ-ɏ]", "", text)


def _is_header(line: str) -> bool:
    words = line.split()
    if not words or len(words) > 6 or len(line) > 48:
        return False
    letters = _letters(line)
    if len(letters) < 3:
        return False
    if line.endswith(":"):
        return True
    return letters.isupper()


def _is_description(line: str) -> bool:
    if _is_header(line):
        return False
    words = line.split()
    if not words:
        return False
    first = words[0]
    if len(_letters(first)) >= 3 and _letters(first).isupper():
        return False  # "PERCUMA tambah sambal ..." is a note, not an ingredient line
    if _PHONE_RE.search(line) or _TIME_RE.search(line):
        return False
    if len(words) >= 3 and ("," in line or first[0].islower() or len(words) >= 5):
        return True
    return len(line) > 30


def _is_name_candidate(line: str) -> bool:
    words = line.split()
    if not words or len(words) > 6:
        return False
    if len(_letters(line)) < 2:
        return False
    if _PHONE_RE.search(line) or _TIME_RE.search(line):
        return False
    return not _is_header(line) and not _is_description(line)


def _strip_signature_marks(name: str) -> Tuple[str, bool]:
    flagged = False
    if _SIGNATURE_SYMBOL_RE.search(name):
        flagged = True
        name = _SIGNATURE_SYMBOL_RE.sub(" ", name)
    m = _SIGNATURE_WORD_RE.search(name)
    if m:
        stripped = (name[: m.start()] + " " + name[m.end():]).strip(" -–—:|/")
        stripped = re.sub(r"\s{2,}", " ", stripped).strip()
        if len(_letters(stripped)) >= 2:
            name = stripped
            flagged = True
    return re.sub(r"\s{2,}", " ", name).strip(" -–—:|"), flagged


@dataclass
class _LineParse:
    name: str
    price: Optional[str]
    price_raw: Optional[str] = None
    description: Optional[str] = None
    multi: bool = False
    confidence: float = 1.0


def parse_item_line(line: str) -> Optional[_LineParse]:
    """One line → (name, price) when the line carries a price. ``name`` is
    "" for a price-only line. None when there is no price at all."""
    if not line:
        return None

    # 1. Tab-separated columns ("Set A\tRM 12.50", "Nasi Lemak\t8.50\tnasi, sambal").
    parts = [p.strip() for p in line.split("\t") if p.strip()]
    if len(parts) >= 2:
        for idx in range(len(parts) - 1, 0, -1):
            price = canonical_price(parts[idx])
            if price is not None:
                name = parts[0] if idx > 0 else ""
                desc = " ".join(parts[1:idx] + parts[idx + 1:]).strip() or None
                return _LineParse(name=name, price=price, description=desc)
    flat = " ".join(parts) if parts else line

    # 2. A range ("RM5 - RM8") is not one price: keep the text for the merchant.
    rng = _RANGE_PRICE_RE.search(flat)
    if rng and _RM_PRICE_RE.search(flat):
        name = flat[: rng.start()].strip(" .·…-–—:")
        return _LineParse(name=name, price=None, price_raw=rng.group(0).strip(), confidence=0.5)

    # 3. Several RM prices on one line (sizes) → lowest, flagged for review.
    rm_prices = _RM_PRICE_RE.findall(flat)
    if len(rm_prices) >= 2:
        first = _RM_PRICE_RE.search(flat)
        name = flat[: first.start()].strip(" .·…-–—:|") if first else ""
        # "Teh Tarik S RM2.50 L RM3.50": the size label before the first
        # price belongs to the price, not the name.
        name = _SIZE_SUFFIX_RE.sub("", name).strip(" .·…-–—:|")
        decimals = [Decimal(p.replace(",", ".")) for p in rm_prices]
        return _LineParse(
            name=name,
            price=canonical_price(min(decimals)),
            price_raw=flat[first.start():].strip() if first else flat,
            multi=True,
            confidence=0.6,
        )

    # 4. The classic "name ..... RM 12.50" line.
    m = _TRAILING_PRICE_RE.match(flat)
    if m:
        has_rm = bool(m.group("rm"))
        has_decimals = bool(re.search(r"[.,]\d", m.group("price")))
        has_leader = bool(re.search(r"[.·…\-–—:]", m.group("leader") or "")) or "\t" in line
        # A bare integer at the end ("Nugget 5") is a count more often than a
        # price; only take it as a price with RM, decimals or a dotted leader.
        if has_rm or has_decimals or has_leader:
            name = m.group("name").strip(" .·…-–—:|")
            price = canonical_price(m.group("price"))
            if price is not None and (has_rm or has_decimals or has_leader):
                raw = (m.group("rm") or "") + " " + m.group("price") + (m.group("unit") or "")
                return _LineParse(name=name, price=price, price_raw=raw.strip() if m.group("unit") else None)

    # 5. One RM price in the middle: "Set A RM 12.50 (nasi, ayam, sambal)".
    one = _RM_PRICE_RE.search(flat)
    if one and len(rm_prices) == 1:
        name = flat[: one.start()].strip(" .·…-–—:|")
        tail = flat[one.end():].strip(" .·…-–—:|()")
        return _LineParse(name=name, price=canonical_price(one.group(1)), description=tail or None)
    return None


def parse_menu_text(text: str) -> Tuple[List[DraftItem], List[str], List[str], List[str]]:
    """Deterministic parse. Returns (items, categories, skipped_names, warnings)."""
    items: List[DraftItem] = []
    categories: List[str] = []
    skipped: List[str] = []
    warnings: List[str] = []

    current_category: Optional[str] = None
    skip_section = False
    section_price: Optional[str] = None
    pending_name: Optional[str] = None
    last_item: Optional[DraftItem] = None

    def add_category(name: str) -> str:
        label = _title_case(name.rstrip(":").strip())[:60]
        if label and label not in categories:
            categories.append(label)
        return label

    def emit(name: str, price: Optional[str], *, description=None, price_raw=None, confidence=1.0, source_line=None) -> Optional[DraftItem]:
        nonlocal last_item
        clean_name, flagged = _strip_signature_marks(name)
        clean_name = re.sub(r"\s{2,}", " ", clean_name).strip()
        if len(_letters(clean_name)) < 2:
            return None
        if skip_section:
            skipped.append(clean_name)
            return None
        item = DraftItem(
            name=clean_name[:120],
            price=price,
            description=(description or None),
            category=current_category,
            is_signature=flagged,
            confidence=confidence,
            price_raw=price_raw,
            source_line=(source_line or None),
        )
        items.append(item)
        last_item = item
        return item

    def flush_pending(with_price: Optional[str], confidence: float) -> None:
        nonlocal pending_name
        if pending_name:
            emit(pending_name, with_price, confidence=confidence, source_line=pending_name)
            pending_name = None

    for raw in text.splitlines():
        line = _clean_line(raw)
        if not line:
            # A blank line ends the "description follows the item" window but
            # a name waiting for its price on the next line survives it.
            last_item = None
            continue

        parsed = parse_item_line(line)
        if parsed is not None:
            if not parsed.name:
                # Price-only line: the price of the name above it, or a
                # section-wide price ("RM 5.00 — semua jenis").
                if pending_name:
                    flush_pending(parsed.price, 0.9)
                else:
                    section_price = parsed.price
                continue
            if _PRICE_NOTE_WORDS_RE.match(parsed.name) or (parsed.description and _PRICE_NOTE_WORDS_RE.match(parsed.description or "")):
                section_price = parsed.price
                continue
            if pending_name and section_price:
                flush_pending(section_price, 0.7)
            pending_name = None
            item = emit(
                parsed.name, parsed.price,
                description=parsed.description, price_raw=parsed.price_raw,
                confidence=parsed.confidence, source_line=line,
            )
            if item is not None and parsed.multi:
                warnings.append(f"'{item.name}' ada beberapa harga ({parsed.price_raw}) — harga terendah diambil, semak.")
            if item is not None and parsed.price is None and parsed.price_raw:
                warnings.append(f"'{item.name}' harga berbentuk julat ({parsed.price_raw}) — isi satu harga.")
            continue

        # ---- no price on this line -------------------------------------
        if _SKIP_SECTION_RE.search(line) and len(line.split()) <= 6:
            flush_pending(section_price, 0.7) if section_price else None
            pending_name = None
            skip_section = True
            current_category = None
            last_item = None
            continue
        if skip_section:
            # Names listed under COMING SOON: remember them for the warning.
            for part in re.split(r"[•|,/]+", line):
                part = part.strip(" -–—")
                if len(_letters(part)) >= 2 and not _is_header(part):
                    skipped.append(part)
            continue
        if _is_header(line):
            flush_pending(section_price, 0.7) if section_price else None
            pending_name = None
            current_category = add_category(line)
            section_price = None
            last_item = None
            continue
        if last_item is not None and last_item.description is None and _is_description(line):
            last_item.description = line[:400]
            continue
        if _is_name_candidate(line):
            if pending_name and section_price:
                flush_pending(section_price, 0.7)
            pending_name = line
            last_item = None
            continue
        last_item = None

    if pending_name and section_price:
        flush_pending(section_price, 0.7)

    # Categories that never got an item (the title, the tagline, "MENU").
    used = {i.category for i in items if i.category}
    categories = [c for c in categories if c in used]
    if skipped:
        shown = ", ".join(dict.fromkeys(skipped))
        warnings.append(f"Dilangkau (coming soon / tidak tersedia): {shown[:300]}")
    return items, categories, list(dict.fromkeys(skipped)), warnings


# ---------------------------------------------------------------------------
# 3. AI extraction
# ---------------------------------------------------------------------------

TextModelCall = Callable[[str], Awaitable[Optional[str]]]
VisionModelCall = Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]]

_JSON_SHAPE = (
    '{"items":[{"name":"Set Panglima","price":"15.90","description":"Nasi, ayam, tauhu","category":"Set Ayam","is_signature":true}],'
    '"categories":["Set Ayam","Minuman"],"skipped":["Bakso Daging"],"notes":["one short note, optional"]}'
)


def _selection_instruction(mode: str, instruction: str) -> str:
    if mode == "signature":
        return (
            "SELECTION: return ONLY the signature / best-selling / recommended items — the ones the menu itself marks "
            "(SIGNATURE, SPECIAL, BEST SELLER, RECOMMENDED, CHEF'S, ★, 🔥) or that are clearly its headline dishes. "
            "If nothing is marked, choose the 5–8 most representative items a first-time customer would order (the sets and "
            "mains, not add-ons or drinks) and say in notes that you chose them."
        )
    if mode == "custom" and instruction.strip():
        return (
            "SELECTION: follow the merchant's instruction EXACTLY and return only the items that satisfy it. "
            f"Merchant instruction: «{instruction.strip()[:400]}». If it names a count, return at most that many."
        )
    return "SELECTION: return EVERY orderable item — food, drinks, add-ons, services, products. Do not skip any."


def build_extraction_prompt(mode: str, instruction: str, language: str, max_items: int, *, business_hint: str = "") -> str:
    lang = "Bahasa Malaysia" if (language or "ms").lower().startswith("ms") else "English"
    hint = f"\nBUSINESS TYPE HINT: {business_hint}\n" if business_hint else ""
    return f"""You are the menu data-entry assistant of BinaApp, a website builder for Malaysian small businesses.
Read the merchant's menu / price list and return STRICT JSON only — no markdown, no prose.
{hint}
{_selection_instruction(mode, instruction)}
Hard limit: at most {max_items} items.

RULES
- name: the item exactly as printed (fix obvious OCR glitches, keep the original language and spelling). Strip marker words
  such as SIGNATURE / BEST SELLER / ★ out of the name and set is_signature=true instead.
- price: a plain decimal in Malaysian Ringgit as a STRING, e.g. "12.50" — no "RM", no text. Unknown → null. Never invent a
  price. A price printed once for a whole group ("RM 5.00 — semua jenis") applies to every item in that group.
- Several sizes/prices → one item per size, e.g. "Teh Tarik (S)" 2.50 and "Teh Tarik (L)" 3.50.
- description: the ingredient / portion line printed with the item, or null. Never write marketing copy.
- category: the section heading the item sits under, Title Case, or null.
- is_signature: true only when the menu marks it (signature, special, best seller, recommended, chef's, popular, ★, 🔥).
- SKIP and do not return: the business name, taglines, notes ("percuma tambah nasi"), opening hours, phone numbers,
  addresses, and anything under "coming soon" / "akan datang" — put those item names in "skipped".
- notes: {lang}, at most 3 short items, only when something needs the merchant's attention.

OUTPUT — one JSON object in exactly this shape:
{_JSON_SHAPE}
"""


def build_text_messages(text: str, mode: str, instruction: str, language: str, max_items: int, *, business_hint: str = "") -> str:
    prompt = build_extraction_prompt(mode, instruction, language, max_items, business_hint=business_hint)
    return prompt + "\nMENU TEXT:\n<<<\n" + text[:MAX_TEXT_CHARS] + "\n>>>\n"


def _prepare_image_for_vision(mime: str, data: bytes) -> Tuple[str, bytes]:
    """Downscale big photos so the base64 payload stays reasonable."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img.load()
        w, h = img.size
        if max(w, h) > VISION_IMAGE_MAX_SIDE or mime not in ("image/jpeg", "image/png"):
            scale = min(1.0, VISION_IMAGE_MAX_SIDE / float(max(w, h)))
            if scale < 1.0:
                img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
            return "image/jpeg", buf.getvalue()
    except Exception as err:  # not an image Pillow understands → send as is
        logger.debug(f"🍽️ image prep skipped: {err}")
    return mime, data


def build_vision_messages(images: Sequence[Tuple[str, bytes]], mode: str, instruction: str, language: str, max_items: int, *, business_hint: str = "") -> List[Dict[str, Any]]:
    prompt = build_extraction_prompt(mode, instruction, language, max_items, business_hint=business_hint)
    prompt += (
        "\nThe menu is in the attached image(s): a photo of a menu board, a printed menu, or scanned PDF pages. "
        "Read every item carefully, including small print and the add-on / drinks columns. Return the JSON only.\n"
    )
    content: List[Dict[str, Any]] = []
    for mime, data in list(images)[:VISION_MAX_IMAGES]:
        mime, data = _prepare_image_for_vision(mime, data)
        b64 = base64.b64encode(data).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    content.append({"type": "text", "text": prompt})
    return [{"role": "user", "content": content}]


def parse_ai_payload(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    """Model text → dict. Tolerates ``json`` fences and prose around the
    object; returns None when there is no object to read."""
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    if text.startswith("["):
        start, end = 0, text.rfind("]")
    else:
        start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    candidate = text[start:end + 1]
    for attempt in (candidate, re.sub(r",\s*([}\]])", r"\1", candidate)):
        try:
            data = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"items": data}
    return None


def items_from_ai_payload(payload: Dict[str, Any]) -> Tuple[List[DraftItem], List[str], List[str], List[str]]:
    items: List[DraftItem] = []
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raw_items = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        name, flagged_by_mark = _strip_signature_marks(name)
        price = canonical_price(entry.get("price"))
        price_raw = None
        if price is None and entry.get("price") not in (None, "", "null"):
            price_raw = str(entry.get("price")).strip()[:40]
        desc = entry.get("description")
        cat = entry.get("category")
        items.append(
            DraftItem(
                name=name[:120],
                price=price,
                description=(str(desc).strip()[:400] or None) if desc else None,
                category=(_title_case(str(cat).strip())[:60] or None) if cat else None,
                is_signature=bool(entry.get("is_signature")) or flagged_by_mark,
                confidence=0.9,
                price_raw=price_raw,
            )
        )
    categories: List[str] = []
    for c in payload.get("categories") or []:
        label = _title_case(str(c).strip())[:60]
        if label and label not in categories:
            categories.append(label)
    for item in items:  # a category only seen on an item still counts
        if item.category and item.category not in categories:
            categories.append(item.category)
    skipped = [str(s).strip() for s in (payload.get("skipped") or []) if str(s).strip()][:40]
    notes = [str(n).strip() for n in (payload.get("notes") or []) if str(n).strip()][:3]
    return items, categories, skipped, notes


async def extract_with_ai(
    source: ExtractedSource,
    *,
    mode: str,
    instruction: str,
    language: str,
    max_items: int,
    business_hint: str = "",
    call_text_model: Optional[TextModelCall],
    call_vision_model: Optional[VisionModelCall],
) -> Optional[Tuple[str, List[DraftItem], List[str], List[str], List[str]]]:
    """(engine, items, categories, skipped, notes) or None when no model
    answered usably. Never raises."""
    try:
        if source.has_text and call_text_model is not None:
            prompt = build_text_messages(source.text, mode, instruction, language, max_items, business_hint=business_hint)
            raw = await asyncio.wait_for(call_text_model(prompt), timeout=ai_text_timeout_seconds())
            payload = parse_ai_payload(raw)
            if payload is not None:
                items, cats, skipped, notes = items_from_ai_payload(payload)
                if items:
                    return "ai-text", items, cats, skipped, notes
                logger.info("🍽️ Menu import: text model returned no items")
        if source.images and call_vision_model is not None:
            messages = build_vision_messages(source.images, mode, instruction, language, max_items, business_hint=business_hint)
            raw = await asyncio.wait_for(call_vision_model(messages), timeout=ai_text_timeout_seconds())
            payload = parse_ai_payload(raw)
            if payload is not None:
                items, cats, skipped, notes = items_from_ai_payload(payload)
                if items:
                    return "ai-vision", items, cats, skipped, notes
                logger.info("🍽️ Menu import: vision model returned no items")
    except asyncio.TimeoutError:
        logger.warning("🍽️ Menu import: AI extraction timed out")
    except Exception as err:
        logger.warning(f"🍽️ Menu import: AI extraction failed: {err}")
    return None


# -- default model callers (the same env vars as ai_service) ----------------

def _openai_compatible_attempts() -> List[Tuple[str, str, str]]:
    """(base_url, key, model) for text, cheapest-and-best-at-JSON first."""
    out: List[Tuple[str, str, str]] = []
    if os.getenv("DEEPSEEK_API_KEY"):
        base = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1"
        out.append((base, os.environ["DEEPSEEK_API_KEY"], os.getenv("MENU_IMPORT_TEXT_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")))
    if os.getenv("ZAI_API_KEY"):
        base = os.getenv("ZAI_API_URL") or os.getenv("ZAI_BASE_URL") or "https://api.z.ai/api/paas/v4"
        out.append((base, os.environ["ZAI_API_KEY"], os.getenv("ZAI_MODEL", "glm-5.3")))
    qwen_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if qwen_key:
        base = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        out.append((base, qwen_key, os.getenv("QWEN_MODEL", "qwen-plus")))
    return out


async def default_call_text_model(prompt: str) -> Optional[str]:
    """One OpenAI-style chat completion; provider fallback chain; None on
    total failure. JSON mode is requested where the provider supports it."""
    timeout = ai_text_timeout_seconds()
    for base_url, key, model in _openai_compatible_attempts():
        body: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 6000,
        }
        if "deepseek" in base_url:
            body["response_format"] = {"type": "json_object"}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=body,
                )
            if r.status_code != 200:
                logger.warning(f"🍽️ Menu import text model {model} ❌ {r.status_code}: {r.text[:200]}")
                continue
            payload = r.json()
            content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content", "")
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            if content and content.strip():
                return content
        except (httpx.TimeoutException, asyncio.TimeoutError):
            logger.warning(f"🍽️ Menu import text model {model} timed out")
        except Exception as err:
            logger.warning(f"🍽️ Menu import text model {model} failed: {err}")
    return None


async def default_call_vision_model(messages: List[Dict[str, Any]]) -> Optional[str]:
    """GLM-4.5V on Z.ai first, Qwen-VL on DashScope second — the same chain
    the design critique uses. Imported lazily so this module stays light."""
    try:
        from app.services.ai_service import ai_service

        return await ai_service._call_vision_model(messages)
    except Exception as err:
        logger.warning(f"🍽️ Menu import vision model failed: {err}")
        return None


def ai_available() -> bool:
    return bool(_openai_compatible_attempts())


# ---------------------------------------------------------------------------
# 4. Selection — the merchant's choice applied to the found items
# ---------------------------------------------------------------------------

_STOPWORDS = {
    # ms
    "hanya", "sahaja", "saja", "dan", "atau", "semua", "ambil", "tambah", "masuk", "letak", "nak", "mahu", "mau",
    "tolong", "sila", "untuk", "yang", "ini", "itu", "dengan", "pada", "ke", "di", "je", "jer", "aje", "kat", "dari",
    "menu", "item", "items", "hidangan", "produk", "pilih", "pilihan", "bagi", "buat", "kasi", "boleh",
    # en
    "only", "just", "the", "and", "or", "all", "with", "add", "include", "please", "want", "give", "me", "my", "our",
    "of", "for", "to", "in", "on", "from", "pick", "choose", "select", "take", "put", "show", "list", "items", "item",
    "menu", "dish", "dishes", "product", "products", "a", "an", "some", "few", "top",
}
_SIGNATURE_INTENT = {
    "killer", "signature", "best", "bestseller", "terbaik", "popular", "popula", "famous", "femes", "terkenal",
    "laku", "terlaris", "recommended", "wajib", "must", "highlight", "utama", "hero", "star", "favourite", "favorite",
    "favourit", "feveret", "special", "istimewa",
}
_EXCLUDE_SPLIT_RE = re.compile(r"\b(kecuali|except|excluding|tanpa|without|bukan|exclude|jangan|tak nak|no)\b", re.IGNORECASE)
_NUMBER_WORDS = {
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5, "enam": 6, "tujuh": 7, "lapan": 8, "sembilan": 9, "sepuluh": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


@dataclass
class Instruction:
    limit: Optional[int] = None
    wants_signature: bool = False
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-zA-ZÀ-ɏ][a-zA-ZÀ-ɏ'-]{1,}", text.lower()) if t not in _STOPWORDS]


def interpret_instruction(instruction: str) -> Instruction:
    """"5 killer menu sahaja" → limit 5, signature. "set ayam dan minuman,
    kecuali add-on" → include [set, ayam, minuman], exclude [add-on]."""
    text = (instruction or "").strip()
    result = Instruction()
    if not text:
        return result
    m = re.search(r"\b(\d{1,3})\b", text)
    if m:
        result.limit = max(1, min(int(m.group(1)), MAX_ITEMS_HARD_CAP))
    else:
        for word, value in _NUMBER_WORDS.items():
            if re.search(rf"\b{word}\b", text.lower()):
                result.limit = value
                break
    parts = _EXCLUDE_SPLIT_RE.split(text, maxsplit=1)
    include_text = parts[0]
    exclude_text = parts[2] if len(parts) > 2 else ""
    include_tokens = _tokens(include_text)
    result.wants_signature = any(t in _SIGNATURE_INTENT for t in include_tokens)
    result.include = [t for t in include_tokens if t not in _SIGNATURE_INTENT]
    result.exclude = _tokens(exclude_text)
    return result


def _matches(item: DraftItem, tokens: Sequence[str]) -> bool:
    hay = f"{item.name} {item.category or ''} {item.description or ''}".lower()
    return any(t in hay for t in tokens)


def apply_selection(
    items: List[DraftItem], mode: str, instruction: str, *, engine: str
) -> Tuple[List[DraftItem], List[str]]:
    """Narrow ``items`` to what the merchant asked for. An AI engine has
    already applied the mode in its prompt; this pass is the deterministic
    safety net (and the whole selection when the engine is heuristic)."""
    warnings: List[str] = []
    if mode == "signature":
        flagged = [i for i in items if i.is_signature]
        if flagged:
            return flagged, warnings
        if engine.startswith("ai"):
            # The model picked representative items when nothing was marked.
            return items, warnings
        warnings.append("Tiada item bertanda signature/best seller dalam menu ini — semua item ditunjukkan, tandakan pilihan anda.")
        return items, warnings

    if mode == "custom":
        parsed = interpret_instruction(instruction)
        selected = list(items)
        if engine == "heuristic":
            if parsed.include:
                matched = [i for i in selected if _matches(i, parsed.include)]
                if matched:
                    selected = matched
                else:
                    warnings.append("Tiada item sepadan dengan arahan anda — semua item ditunjukkan untuk anda pilih.")
            if parsed.exclude:
                selected = [i for i in selected if not _matches(i, parsed.exclude)]
            if parsed.wants_signature:
                flagged = [i for i in selected if i.is_signature]
                if flagged:
                    selected = flagged
                elif not parsed.include:
                    warnings.append("Menu ini tidak menandakan item signature — pilih sendiri daripada senarai.")
        if parsed.limit is not None and len(selected) > parsed.limit:
            selected = selected[: parsed.limit]
        return selected, warnings

    return items, warnings


# ---------------------------------------------------------------------------
# 5. Normalisation — what the merchant will actually see
# ---------------------------------------------------------------------------

def _dedupe_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def normalise_items(items: List[DraftItem], max_items: int) -> Tuple[List[DraftItem], List[str], bool]:
    """Returns (items, warnings, truncated)."""
    warnings: List[str] = []
    out: List[DraftItem] = []
    seen: Dict[str, DraftItem] = {}
    dropped: List[str] = []
    duplicates = 0
    for item in items:
        name = re.sub(r"\s{2,}", " ", (item.name or "").strip(" -–—:|.,"))
        if not name:
            continue
        if not is_valid_menu_item_name(name):
            dropped.append(name)
            continue
        key = _dedupe_key(name)
        if key in seen:
            duplicates += 1
            kept = seen[key]
            if kept.price is None and item.price is not None:
                kept.price = item.price
            if not kept.description and item.description:
                kept.description = item.description
            kept.is_signature = kept.is_signature or item.is_signature
            continue
        item.name = name
        item.price = canonical_price(item.price) if item.price is not None else None
        if item.description:
            item.description = re.sub(r"\s{2,}", " ", item.description.strip())[:400] or None
        if item.category:
            item.category = item.category.strip()[:60] or None
        seen[key] = item
        out.append(item)

    truncated = False
    cap = max(1, min(int(max_items or DEFAULT_MAX_ITEMS), MAX_ITEMS_HARD_CAP))
    if len(out) > cap:
        truncated = True
        warnings.append(f"{len(out)} item dijumpai — {cap} pertama ditunjukkan. Naikkan had atau import mengikut kategori.")
        out = out[:cap]
    if dropped:
        shown = ", ".join(dropped[:6]) + (" …" if len(dropped) > 6 else "")
        warnings.append(f"{len(dropped)} baris bukan item dilangkau: {shown}")
    if duplicates:
        warnings.append(f"{duplicates} item berulang digabungkan.")
    missing = sum(1 for i in out if i.price is None)
    if missing:
        warnings.append(f"{missing} item tiada harga — isi sebelum tambah ke menu.")
    return out, warnings, truncated


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def import_menu(
    source: ExtractedSource,
    *,
    mode: str = "all",
    instruction: str = "",
    language: str = "ms",
    max_items: int = DEFAULT_MAX_ITEMS,
    business_hint: str = "",
    use_ai: bool = True,
    call_text_model: Optional[TextModelCall] = None,
    call_vision_model: Optional[VisionModelCall] = None,
) -> MenuImportResult:
    """Extracted source → reviewed-ready draft. AI when available, the
    deterministic parser otherwise (and as the fallback when the model
    fails). Images without a vision model → a clear error."""
    mode = mode if mode in SELECTION_MODES else "all"
    if mode == "custom" and not (instruction or "").strip():
        mode = "all"
    cap = max(1, min(int(max_items or DEFAULT_MAX_ITEMS), MAX_ITEMS_HARD_CAP))
    warnings: List[str] = list(source.warnings)

    engine = "heuristic"
    items: List[DraftItem] = []
    categories: List[str] = []
    skipped: List[str] = []

    if use_ai:
        text_call = call_text_model if call_text_model is not None else (default_call_text_model if ai_available() else None)
        vision_call = call_vision_model if call_vision_model is not None else default_call_vision_model
        ai_result = await extract_with_ai(
            source, mode=mode, instruction=instruction, language=language, max_items=cap,
            business_hint=business_hint, call_text_model=text_call, call_vision_model=vision_call,
        )
        if ai_result is not None:
            engine, items, categories, skipped, notes = ai_result
            warnings.extend(notes)

    if engine == "heuristic":
        if not source.has_text:
            raise MenuImportError(
                "vision_unavailable",
                "Gambar menu memerlukan AI penglihatan yang tidak tersedia sekarang. Cuba lagi sebentar, atau tampal teks menu.",
            )
        items, categories, skipped, parse_warnings = parse_menu_text(source.text)
        warnings.extend(parse_warnings)
        if use_ai:
            warnings.append("AI tidak dapat dihubungi — menu dibaca secara automatik tanpa AI; semak nama dan harga.")

    total_found = len(items)
    items, select_warnings = apply_selection(items, mode, instruction, engine=engine)
    warnings.extend(select_warnings)
    items, norm_warnings, truncated = normalise_items(items, cap)
    warnings.extend(norm_warnings)

    used = [c for c in categories if any(i.category == c for i in items)]
    for item in items:
        if item.category and item.category not in used:
            used.append(item.category)

    if not items:
        warnings.append("Tiada item dengan nama dan harga dijumpai. Cuba fail lain atau tampal teks menu.")

    return MenuImportResult(
        items=items,
        categories=used,
        warnings=list(dict.fromkeys(w for w in warnings if w)),
        engine=engine,
        mode=mode,
        source=source.summary(),
        total_found=total_found,
        truncated=truncated,
        skipped=skipped,
    )


# ---------------------------------------------------------------------------
# Publish helper — the create page's rows → menu_items rows
# ---------------------------------------------------------------------------

def plan_publish_menu_rows(payload: Sequence[Any], website_id: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """The ``menu_items`` list /api/publish receives → rows for the
    ``menu_items`` table (minus ``category_id``, which the caller resolves
    from the ``_category`` name) plus the distinct category names in
    first-seen order.

    Round 2 (§B6) still holds: a row without a readable price is left out
    of the ordering menu rather than priced by us. ``is_popular`` comes from
    the row's ★ (``is_popular`` / ``is_signature``); the default description
    is the same copy publish always used.
    """
    rows: List[Dict[str, Any]] = []
    categories: List[str] = []
    for idx, it in enumerate(payload or []):
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or f"Item {idx + 1}").strip()[:120]
        price = canonical_price(it.get("price"))
        if price is None:
            logger.warning(f"💸 Menu item '{name}' has no valid price — not added to the ordering menu")
            continue
        category = str(it.get("category") or "").strip()[:100] or None
        if category and category.lower() not in {c.lower() for c in categories}:
            categories.append(category)
        rows.append({
            "website_id": website_id,
            "_category": category,
            "name": name,
            "description": (str(it.get("description") or "").strip() or "Hidangan istimewa dari dapur kami")[:400],
            "price": float(price),
            "image_url": it.get("image_url") or it.get("url") or None,
            "is_available": True,
            "is_popular": bool(it.get("is_popular") or it.get("is_signature")),
            "preparation_time": 15,
            "sort_order": idx,
        })
    return rows, categories
