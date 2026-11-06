"""Key facts from the merchant's brief must reach the page.

agp.binaapp.my: the brief listed spice levels (Level 1/2/3), "FREE refill
nasi & sambal (dine-in sahaja)", "Take away caj RM2.00" and a Coming Soon
list. The deterministic menu block replaced the model's menu section, and
with it every one of those lines — none was rendered.

``extract_key_facts`` pulls the operational facts out of the brief (spice
levels, free refills, charges, a Coming Soon list), ``missing_facts`` checks
the page's VISIBLE text for each, and ``inject_notes_block`` adds the
merchant's own sentences as a simple notes block under the menu for any
that are missing. The text is the merchant's, verbatim — nothing invented.
Pure functions; no I/O.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

NOTES_BLOCK_CLASS = "binaapp-brief-notes"

_AMOUNT_RE = re.compile(r"RM\s?(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
_LEVEL_RE = re.compile(r"\blevel\s*(\d)\b", re.IGNORECASE)
_REFILL_RE = re.compile(r"\brefill\b|\btambah\s+(?:nasi|sambal)\s+percuma\b|\bpercuma\s+tambah\b", re.IGNORECASE)
_COMING_RE = re.compile(r"\b(coming\s+soon|akan\s+datang|bakal\s+datang|segera\s+hadir|menu\s+baru\s+akan)\b", re.IGNORECASE)

#: Words that make an RM amount a CHARGE (not a menu price). Specific ones
#: are checked on the page when the sentence has any; the generic ones only
#: when it has nothing else ("Tambahan" is also a menu category).
_CHARGE_SPECIFIC = (
    r"take[\s-]*away", r"bungkus", r"tapau", r"delivery", r"penghantaran", r"servis", r"service",
    r"deposit", r"caj", r"charge", r"surcharge", r"cas\b", r"pos\b", r"postage",
)
_CHARGE_GENERIC = (r"tambahan", r"extra", r"\+\s*RM")
_WINDOW = 120


@dataclass
class KeyFact:
    kind: str                      # "level" | "refill" | "charge" | "coming_soon"
    text: str                      # the merchant's sentence, verbatim
    levels: List[str] = field(default_factory=list)
    amount: str = ""
    keywords: List[str] = field(default_factory=list)
    items: List[str] = field(default_factory=list)


def _sentences(brief: str) -> List[str]:
    out: List[str] = []
    for line in re.split(r"[\r\n]+", str(brief or "")):
        line = line.strip(" \t•-*")
        if not line:
            continue
        out.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", line) if s.strip())
    return out


_BULLET_RE = re.compile(r"^\s*(?:[-•*·]|\d+[.)])\s+")


def _split_list(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\s*(?:,|;|/|•|\||\bdan\b|\band\b)\s*", text) if p.strip()]


def _coming_soon(brief: str) -> Optional[KeyFact]:
    """A "Coming Soon" / "Akan datang" list: items on the same line after
    the phrase, or the bullet / short lines that follow it."""
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", str(brief or ""))]
    for i, line in enumerate(lines):
        m = _COMING_RE.search(line)
        if not m:
            continue
        parts = _split_list(line[m.end():].strip(" :-–—()"))
        if not parts:
            for ln in lines[i + 1:]:
                if not ln:
                    if parts:
                        break
                    continue
                if _BULLET_RE.match(ln):
                    parts.extend(_split_list(_BULLET_RE.sub("", ln)))
                elif not parts and len(ln) <= 120:
                    parts.extend(_split_list(ln))
                    break
                else:
                    break
        items = [re.sub(r"[.!]+$", "", p).strip() for p in parts]
        items = [p for p in items if 1 < len(p) <= 60]
        if items:
            phrase = re.sub(r"\s+", " ", m.group(1)).strip()
            return KeyFact("coming_soon", f"{phrase[:1].upper()}{phrase[1:]}: {', '.join(items)}", items=items)
    return None


def extract_key_facts(*texts: Optional[str]) -> List[KeyFact]:
    """Operational facts the brief states, each with the merchant's own
    sentence as its display text. Order: levels, refill, charges, coming
    soon. De-duplicated by sentence."""
    facts: List[KeyFact] = []
    seen = set()
    for brief in texts:
        if not brief:
            continue
        for sent in _sentences(brief):
            if _COMING_RE.search(sent):
                continue
            levels = sorted(set(_LEVEL_RE.findall(sent)))
            if levels and sent not in seen:
                seen.add(sent)
                facts.append(KeyFact("level", sent, levels=levels))
                continue
            if _REFILL_RE.search(sent) and sent not in seen:
                seen.add(sent)
                facts.append(KeyFact("refill", _clause(sent, _REFILL_RE)))
            for am in _AMOUNT_RE.finditer(sent):
                specific = [k for k in _CHARGE_SPECIFIC if re.search(k, sent, re.IGNORECASE)]
                generic = [k for k in _CHARGE_GENERIC if re.search(k, sent, re.IGNORECASE)]
                kws = specific or generic
                if not kws:
                    continue
                key = (am.group(1), tuple(kws))
                if key in seen:
                    continue
                seen.add(key)
                facts.append(KeyFact("charge", _clause(sent, _AMOUNT_RE, at=am.start()), amount=am.group(1), keywords=kws))
        cs = _coming_soon(brief)
        if cs is not None and cs.text not in seen:
            seen.add(cs.text)
            facts.append(cs)
    return facts


def _clause(sentence: str, pattern: "re.Pattern", at: Optional[int] = None) -> str:
    """The clause of ``sentence`` that carries the fact: a sentence like
    "Makan di kedai: FREE refill nasi & sambal. Take away: caj RM2.00."
    is already split; this trims a trailing unrelated clause after ";"."""
    parts = re.split(r"\s*;\s*", sentence)
    if len(parts) == 1:
        return sentence
    pos = 0
    for p in parts:
        end = pos + len(p)
        if (at is not None and pos <= at <= end) or (at is None and pattern.search(p)):
            return p
        pos = end + 1
    return sentence


def visible_text(html: str) -> str:
    t = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", str(html or ""), flags=re.IGNORECASE | re.DOTALL)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", _html.unescape(t))


def _amount_variants(amount: str) -> List[str]:
    a = amount.replace(",", "")
    try:
        v = float(a)
    except ValueError:
        return [a]
    out = {f"{v:.2f}", a}
    if v == int(v):
        out.add(str(int(v)))
    return sorted(out, key=len, reverse=True)


def fact_present(fact: KeyFact, text: str) -> bool:
    low = text.lower()
    if fact.kind == "level":
        return all(re.search(rf"\blevel\s*{lv}\b", low) for lv in fact.levels)
    if fact.kind == "refill":
        return bool(_REFILL_RE.search(text))
    if fact.kind == "coming_soon":
        return bool(_COMING_RE.search(text)) and all(it.lower() in low for it in fact.items)
    if fact.kind == "charge":
        for v in _amount_variants(fact.amount):
            for m in re.finditer(rf"RM\s?{re.escape(v)}(?!\d|\.\d)", text, re.IGNORECASE):
                window = text[max(0, m.start() - _WINDOW): m.end() + _WINDOW]
                if any(re.search(k, window, re.IGNORECASE) for k in fact.keywords):
                    return True
        return False
    return True


def missing_facts(html: str, facts: Sequence[KeyFact]) -> List[KeyFact]:
    text = visible_text(html)
    return [f for f in facts if not fact_present(f, text)]


def render_notes_block(facts: Sequence[KeyFact], language: str = "ms") -> str:
    if not facts:
        return ""
    en = str(language or "ms").lower().startswith("en")
    title = "Good to know" if en else "Maklumat Penting"
    rows = []
    for f in facts:
        if f.kind == "coming_soon":
            head, _, _ = f.text.partition(":")
            rows.append(
                f'<li><strong>{_html.escape(head.strip() or "Coming Soon")}:</strong> '
                + ", ".join(_html.escape(it) for it in f.items) + "</li>"
            )
        else:
            rows.append(f"<li>{_html.escape(f.text)}</li>")
    return (
        f'<div class="{NOTES_BLOCK_CLASS}" style="max-width:48rem;margin:2.5rem auto 0;padding:1.25rem 1.5rem;'
        'border:2px solid var(--accent-color,var(--primary-color,#B91C1C));border-radius:var(--bmf-radius,1rem);'
        'background:var(--surface-color,#fff);color:var(--text-color,#1C1917)">'
        f'<h3 style="font-family:var(--font-heading,inherit);font-size:1.25rem;font-weight:800;margin:0 0 .6rem">{title}</h3>'
        '<ul style="margin:0;padding-left:1.2rem;line-height:1.7">' + "".join(rows) + "</ul></div>"
    )


def inject_notes_block(html: str, facts: Sequence[KeyFact], language: str = "ms", items: Sequence = ()) -> Tuple[str, bool]:
    """Add the notes block at the end of the menu section (before its
    closing tag), else before the footer. Idempotent."""
    if not html or not facts or NOTES_BLOCK_CLASS in html:
        return html, False
    from app.services import menu_fidelity as _mf

    block = render_notes_block(facts, language)
    span = _mf.find_menu_section(html, _mf.normalize_items(items))
    if span is not None:
        start, end = span
        close = html.rfind("</section>", start, end)
        if close != -1:
            # Inside the section's content container when there is one: the
            # last closing </div> before </section>.
            inner = html.rfind("</div>", start, close)
            at = inner if inner != -1 and not html[inner + 6:close].strip() else close
            return html[:at] + block + html[at:], True
    return _mf._insert_before_footer(html, block), True
