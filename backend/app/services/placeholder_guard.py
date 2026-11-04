"""Placeholders never reach the page.

The brief for Ayam Gepuk Panglima ended with
``Waktu operasi: [ISI — contoh: 11 pagi – 10 malam, setiap hari]`` — a
fill-in prompt the merchant pasted from a template and never filled — and
the site published "11 pagi – 10 malam, setiap hari" as the opening hours.
Two rules close that:

* ``strip_brief_placeholders``: bracketed fill-ins, "contoh:" examples and
  "(cth. ...)" asides are removed from the brief BEFORE generation. A line
  whose whole value was a placeholder ("Waktu operasi: [...]") goes with
  it, so the field reads as not supplied and the page shows the honest
  fallback ("Hubungi kami untuk waktu operasi") instead of a guess.
* ``scrub_placeholder_echo``: the create form's own example texts (input
  placeholders) and every example removed from the brief are removed from
  the generated page if the model echoed them anyway.

Pure functions; no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

#: Square-bracket fill-ins: "[ISI — contoh: 11 pagi – 10 malam]",
#: "[isi di sini]", "[TODO]", "[Nama kedai]", "[your address]".
_BRACKET_RE = re.compile(r"\[(?:[^\[\]]{0,200})\]")
_BRACKET_WORDS_RE = re.compile(
    r"\b(isi|contoh|cth|example|e\.g\.|eg\b|todo|tbd|tba|xxx|placeholder|masukkan|sila isi|fill|insert|your )",
    re.IGNORECASE,
)
#: "(contoh: ...)", "(cth. ...)", "(e.g. ...)", "(example: ...)" asides.
_PAREN_EXAMPLE_RE = re.compile(r"\((?:contoh|cth|e\.?g\.?|example|misalnya)\s*[:.\-–—]?\s*[^()]{0,200}\)", re.IGNORECASE)
#: A trailing "contoh: ..." clause on a line.
_TRAILING_EXAMPLE_RE = re.compile(r"(?:^|[\s,;—–-])(?:contoh|cth|e\.?g\.?|example|misalnya)\s*[:.]\s*(.{0,200})$", re.IGNORECASE)
_LABEL_LINE_RE = re.compile(r"^\s*([A-Za-z][\w /&]{1,40}?)\s*[:：]\s*(.*)$")

#: Example texts the create form shows inside its inputs. Any of these on
#: a published page came from a placeholder, not from the merchant.
FORM_PLACEHOLDER_EXAMPLES: Tuple[str, ...] = (
    "Nasi Kandar Daging Crystal",
    "cth: Nasi Kandar Daging Crystal",
    "123, Jalan Sultan, Shah Alam, Selangor",
    "No. 123, Jalan ABC, Shah Alam",
    "Jalan ABC",
    "012-345 6789",
    "0123456789",
    "kedai-yassir",
    "kedai-anda.binaapp.my",
    "My Restaurant",
    "Shah Alam, Klang, Subang",
    "Facebook: page name or URL",
    "Instagram: @username",
    "TikTok: @username",
    "kopi dituang perlahan, asap sate, kain dilipat",
)

#: What the page says when no opening hours were supplied.
HOURS_FALLBACK = {"ms": "Hubungi kami untuk waktu operasi", "en": "Contact us for opening hours"}


@dataclass
class PlaceholderReport:
    removed: List[str] = field(default_factory=list)   # the placeholder fragments taken out
    examples: List[str] = field(default_factory=list)  # example values that must not appear on the page
    dropped_lines: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.removed or self.dropped_lines)

    def as_dict(self):
        return {"removed": list(self.removed), "examples": list(self.examples), "dropped_lines": list(self.dropped_lines)}


def _example_values(fragment: str) -> List[str]:
    """The example text inside a placeholder ("contoh: 11 pagi – 10 malam,
    setiap hari" → that value), so it can be scrubbed from the page."""
    inner = fragment.strip("[]() ")
    m = re.search(r"(?:contoh|cth|e\.?g\.?|example|misalnya)\s*[:.\-–—]?\s*(.+)$", inner, re.IGNORECASE)
    if not m:
        return []
    value = m.group(1).strip(" .;")
    out = [value] if len(value) >= 4 else []
    # Also each comma/pipe-separated part that is long enough to be meaningful on its own.
    for part in re.split(r"\s*[,|/]\s*", value):
        part = part.strip(" .;")
        # A part is worth scrubbing on its own when it is specific (carries
        # a number) or long; "setiap hari" alone is ordinary copy.
        if part not in out and (re.search(r"\d", part) or len(part) >= 14):
            out.append(part)
    return out


def hours_fallback(language: Optional[str] = "ms") -> str:
    return HOURS_FALLBACK["en" if str(language or "ms").lower().startswith("en") else "ms"]


def strip_brief_placeholders(text: Optional[str]) -> Tuple[str, PlaceholderReport]:
    """Remove fill-in placeholders and example asides from a brief."""
    report = PlaceholderReport()
    if not text:
        return text or "", report
    lines = str(text).split("\n")
    out_lines: List[str] = []
    for line in lines:
        original = line

        def _take(m: "re.Match") -> str:
            frag = m.group(0)
            inner = frag.strip("[]")
            # Only a bracket that READS as a fill-in is a placeholder;
            # "[Halal]" or "[2019]" is content.
            if frag.startswith("[") and not (
                _BRACKET_WORDS_RE.search(inner) or "—" in inner or not inner.strip()
                or (inner.isupper() and " " in inner.strip())  # "[NAMA KEDAI]", not "[JAKIM]"
            ):
                return frag
            report.removed.append(frag)
            report.examples.extend(v for v in _example_values(frag) if v not in report.examples)
            return " "

        line = _BRACKET_RE.sub(_take, line)
        line = _PAREN_EXAMPLE_RE.sub(_take, line)
        m = _TRAILING_EXAMPLE_RE.search(line)
        if m and m.group(1).strip():
            frag = m.group(0)
            report.removed.append(frag.strip())
            report.examples.extend(v for v in _example_values("contoh: " + m.group(1)) if v not in report.examples)
            line = line[: m.start()].rstrip(" ,;—–-")
        line = re.sub(r"[ \t]{2,}", " ", line)
        line = re.sub(r"\s+([.,;:!?])", r"\1", line).rstrip()
        if line != original.rstrip():
            lm = _LABEL_LINE_RE.match(line)
            if lm and not lm.group(2).strip():
                # "Waktu operasi:" with nothing left → not supplied.
                report.dropped_lines.append(original.strip())
                continue
        out_lines.append(line)
    cleaned = "\n".join(out_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, report


_LEAF_RE = re.compile(r"<(p|li|span|div|td|dd|dt|h[1-6]|small|em|strong|a|time)\b[^>]*>(?:(?!<(?:p|li|div|section|ul|ol|table|h[1-6])\b).)*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[–—]", "-", str(s or ""))).strip().lower()


def scrub_placeholder_echo(html: str, examples: Iterable[str] = (), *, language: Optional[str] = "ms") -> Tuple[str, List[str]]:
    """Remove the smallest element whose visible text contains a placeholder
    example (or a bracketed fill-in the model copied). Returns (html, hits)."""
    if not html:
        return html, []
    needles = [_norm(e) for e in list(examples) + list(FORM_PLACEHOLDER_EXAMPLES) if e and len(_norm(e)) >= 4]
    hits: List[str] = []
    out = html

    def _sub(m: "re.Match") -> str:
        text = _norm(_TAG_RE.sub(" ", m.group(0)))
        if not text:
            return m.group(0)
        if _BRACKET_RE.search(text) and _BRACKET_WORDS_RE.search(text):
            hits.append(text[:80])
            return ""
        for n in needles:
            if n in text:
                hits.append(n)
                # A line that only carried the example is removed; a line
                # with its own copy loses just the example.
                rest = text.replace(n, "").strip(" ,.:;-")
                if len(rest) < 12:
                    return ""
                return re.sub(re.escape(n), "", m.group(0), flags=re.IGNORECASE)
        return m.group(0)

    # Several passes so a wrapper that only held a removed leaf is seen too.
    for _ in range(3):
        before = out
        out = _LEAF_RE.sub(_sub, out)
        if out == before:
            break
    # Any bare bracketed fill-in left in text nodes.
    def _bare(m: "re.Match") -> str:
        inner = m.group(0).strip("[]")
        if _BRACKET_WORDS_RE.search(inner) or "—" in inner:
            hits.append(m.group(0)[:80])
            return ""
        return m.group(0)
    out = re.sub(r"(?<=>)[^<]*?(\[[^\[\]<>]{1,200}\])", lambda m: m.group(0).replace(m.group(1), _bare(re.match(r"\[.*\]", m.group(1)))), out)
    return out, hits
