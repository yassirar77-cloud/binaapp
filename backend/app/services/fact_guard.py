"""
Fact guard (Round 2, §B8) — no section may state a fact the merchant did
not supply.

"Waktu Paling Lengang" appeared on the Dobi site with quiet-hour times that
exist nowhere in the brief. The guard extracts every checkable fact from
the page — times, numbers with units, counts, percentages, multi-digit
numbers — and looks each up in the merchant's sources (story, name,
address, structured hours, item names and prices, phone). A section that
is not essential and carries an unsupported fact is stripped whole; an
essential section (hero, offerings, about, location, contact, footer) loses
only the element that carries the fact. Navigation links to a stripped
section are removed with it. Generic copy is allowed only where it carries
no fact — CTAs and navigation.

Pure module; ``ai_service`` applies it in the final cleanup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

_TAG_RE = re.compile(r"<[^>]+>")
_SECTION_OPEN_RE = re.compile(r"<(section|article|aside)\b[^>]*>", re.IGNORECASE)
_ID_RE = re.compile(r"\bid=[\"']([^\"']+)[\"']", re.IGNORECASE)
_HEADING_RE = re.compile(r"<h[1-3]\b[^>]*>(.*?)</h[1-3]>", re.IGNORECASE | re.DOTALL)
_NAV_LINK_RE = re.compile(r"<a\b[^>]*href=[\"']#([^\"']+)[\"'][^>]*>.*?</a>\s*", re.IGNORECASE | re.DOTALL)
_LEAF_RE = re.compile(r"<(p|li|h3|h4|h5|h6|span|div|td|dd|dt)\b[^>]*>(?:(?!<(?:p|li|h3|h4|div|section|ul|ol|table)\b).)*?</\1>", re.IGNORECASE | re.DOTALL)

# What counts as a fact in visible text.
_TIME_RE = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*(am|pm|pagi|petang|malam|tengah\s*hari|tgh)?\b|\b(\d{1,2})\s*(am|pm|pagi|petang|malam)\b", re.IGNORECASE)
_UNIT_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(kg|g|jam|hours?|hrs?|minit|min|minutes?|tahun|years?|%|peratus|km|m|orang|pax|hari|days?|kali|unit|mesin|units?|\+)", re.IGNORECASE)
_PLUS_RE = re.compile(r"\b(\d+)\s*\+")
_NUMBER_RE = re.compile(r"(?<![\w/:-])(?<!\d\.)(\d{2,6}(?:[.,]\d{1,2})?)(?![\w/:-]|\.\d)")
_PRICE_RE = re.compile(r"RM\s?(\d+(?:[.,]\d{1,2})?)", re.IGNORECASE)

ESSENTIAL_ID_WORDS = (
    "home", "hero", "utama", "menu", "servis", "service", "perkhidmatan", "produk", "product", "koleksi",
    "harga", "price", "tentang", "about", "lokasi", "location", "hubungi", "contact", "tempah", "book",
    "footer", "cara", "order", "pesan",
)
ESSENTIAL_HEADING_WORDS = (
    "menu", "servis", "perkhidmatan", "produk", "koleksi", "harga", "tentang kami", "about", "lokasi",
    "hubungi", "contact", "tempah", "cara order", "cara tempah",
)


@dataclass
class FactSources:
    numbers: Set[str] = field(default_factory=set)
    minutes: Set[int] = field(default_factory=set)
    is_24h: bool = False

    @classmethod
    def from_texts(cls, texts: Iterable[Optional[str]], *, is_24h: bool = False) -> "FactSources":
        src = cls(is_24h=is_24h)
        for text in texts:
            if not text:
                continue
            for raw in re.findall(r"\d+(?:[.,]\d+)?", str(text)):
                src.numbers.update(_number_forms(raw))
            for m in _TIME_RE.finditer(str(text)):
                minutes = _time_minutes(m)
                if minutes is not None:
                    src.minutes.add(minutes)
        return src


def _number_forms(raw: str) -> Set[str]:
    forms = {raw, raw.replace(",", ".")}
    core = raw.replace(",", ".")
    if "." in core:
        forms.add(core.split(".")[0])
        forms.add(core.rstrip("0").rstrip("."))
    else:
        forms.add(f"{core}.00")
        forms.add(f"{core}.0")
    return {f for f in forms if f}


def _time_minutes(m: "re.Match") -> Optional[int]:
    if m.group(1):
        h, mi, marker = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower()
    else:
        h, mi, marker = int(m.group(4)), 0, (m.group(5) or "").lower()
    if h > 24 or mi > 59:
        return None
    if marker in ("pm", "petang", "malam", "tgh") and h < 12:
        h += 12
    elif marker in ("am", "pagi") and h == 12:
        h = 0
    return h * 60 + mi


@dataclass
class Fact:
    kind: str  # time | unit | price | number
    text: str
    number: str
    minutes: Optional[int] = None


def facts_in(text: str) -> List[Fact]:
    """Every checkable fact in a run of visible text."""
    out: List[Fact] = []
    seen: Set[str] = set()
    for m in _TIME_RE.finditer(text):
        minutes = _time_minutes(m)
        if minutes is None:
            continue
        key = ("time", m.group(0))
        if key not in seen:
            seen.add(key)
            out.append(Fact("time", m.group(0).strip(), (m.group(1) or m.group(4)), minutes))
    stripped_times = _TIME_RE.sub(" ", text)
    for m in _PRICE_RE.finditer(stripped_times):
        out.append(Fact("price", m.group(0), m.group(1)))
    no_prices = _PRICE_RE.sub(" ", stripped_times)
    for m in _UNIT_RE.finditer(no_prices):
        out.append(Fact("unit", m.group(0).strip(), m.group(1)))
    no_units = _UNIT_RE.sub(" ", no_prices)
    for m in _PLUS_RE.finditer(no_units):
        out.append(Fact("unit", m.group(0).strip(), m.group(1)))
    for m in _NUMBER_RE.finditer(_PLUS_RE.sub(" ", no_units)):
        out.append(Fact("number", m.group(1), m.group(1)))
    return out


def unsupported_facts(text: str, sources: FactSources) -> List[Fact]:
    out = []
    for fact in facts_in(text):
        if fact.kind == "time":
            if sources.is_24h and fact.minutes in (0, 23 * 60 + 59):
                continue
            if fact.minutes in sources.minutes:
                continue
            out.append(fact)
            continue
        forms = _number_forms(fact.number.replace(",", "."))
        if forms & sources.numbers:
            continue
        # A count like "24" on a 24-hour business is supported.
        if sources.is_24h and fact.number in ("24",):
            continue
        out.append(fact)
    return out


def _visible(fragment: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", fragment)).strip()


def _find_element_span(html: str, open_match: "re.Match") -> Tuple[int, int]:
    tag = open_match.group(1).lower()
    start, pos, depth = open_match.start(), open_match.end(), 1
    token = re.compile(rf"<(/?)({tag})\b[^>]*>", re.IGNORECASE)
    while depth and pos < len(html):
        m = token.search(html, pos)
        if not m:
            return start, len(html)
        depth += -1 if m.group(1) else 1
        pos = m.end()
    return start, pos


def _section_identity(block: str) -> Tuple[str, str]:
    open_tag = block[: block.find(">") + 1]
    sid = (_ID_RE.search(open_tag) or [None, ""])[1] if _ID_RE.search(open_tag) else ""
    heading = ""
    hm = _HEADING_RE.search(block)
    if hm:
        heading = _visible(hm.group(1))
    return sid, heading


def _is_essential(sid: str, heading: str, index: int, total: int) -> bool:
    if index == 0 or index == total - 1:
        return True
    low_id, low_h = sid.lower(), heading.lower()
    return any(w in low_id for w in ESSENTIAL_ID_WORDS) or any(w in low_h for w in ESSENTIAL_HEADING_WORDS)


def _strip_leaves(block: str, sources: FactSources) -> Tuple[str, int]:
    """Remove the innermost elements carrying unsupported facts."""
    removed = 0
    out = block
    # Iterate until no leaf carries an unsupported fact (elements nest).
    for _ in range(6):
        changed = False
        for m in list(_LEAF_RE.finditer(out)):
            inner = m.group(0)
            # Skip elements that still contain block children (not a leaf).
            if re.search(r"<(p|li|h[1-6]|div|section|ul|ol)\b", inner[1:], re.IGNORECASE):
                continue
            if unsupported_facts(_visible(inner), sources):
                out = out[: m.start()] + out[m.end():]
                removed += 1
                changed = True
                break
        if not changed:
            break
    return out, removed


@dataclass
class FactGuardReport:
    stripped_sections: List[str] = field(default_factory=list)
    stripped_elements: int = 0
    facts: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.stripped_sections or self.stripped_elements)

    def as_dict(self) -> Dict:
        return {"stripped_sections": list(self.stripped_sections), "stripped_elements": self.stripped_elements, "facts": list(self.facts)}


def guard_facts(html: str, sources: FactSources) -> Tuple[str, FactGuardReport]:
    """Apply the guard. Returns (html, report)."""
    report = FactGuardReport()
    if not html:
        return html, report
    body_start = html.lower().find("<body")
    body_end = html.lower().rfind("</body>")
    if body_start == -1 or body_end == -1:
        return html, report
    # Collect top-level sections in body order.
    sections: List[Tuple[int, int]] = []
    pos = body_start
    while True:
        m = _SECTION_OPEN_RE.search(html, pos)
        if not m or m.start() >= body_end:
            break
        start, end = _find_element_span(html, m)
        sections.append((start, end))
        pos = end
    total = len(sections)
    out = html
    stripped_ids: List[str] = []
    # Walk from the end so earlier offsets stay valid.
    for index in range(total - 1, -1, -1):
        start, end = sections[index]
        block = out[start:end]
        sid, heading = _section_identity(block)
        bad = unsupported_facts(_visible(block), sources)
        if not bad:
            continue
        report.facts.extend(f"{sid or heading or 'section'}: {b.text}" for b in bad)
        if _is_essential(sid, heading, index, total):
            new_block, n = _strip_leaves(block, sources)
            if n:
                report.stripped_elements += n
                out = out[:start] + new_block + out[end:]
        else:
            report.stripped_sections.append(sid or heading or f"section-{index + 1}")
            if sid:
                stripped_ids.append(sid)
            out = out[:start] + out[end:]
    for sid in stripped_ids:
        out = re.sub(r"<a\b[^>]*href=[\"']#" + re.escape(sid) + r"[\"'][^>]*>.*?</a>\s*", "", out, flags=re.IGNORECASE | re.DOTALL)
    return out, report
