"""
Anti-template lint — the server-side check behind the Pass 2 prompt's
ANTI-TEMPLATE RULES (§2).

The generator's output converged on one look no matter the prompt. Rules in
a prompt are advisory; this lint is not. It runs on the raw HTML before the
critique gate, returns the failures that feed the regeneration prompt, and
applies the mechanical repairs it can make safely so that whatever is
finally served is free of the tells even after the retry budget runs out.

Failures (each feeds the regeneration prompt):
- ``aos``            more than 2 ``data-aos`` attributes
- ``eyebrows``       more than 1 tracked ALL-CAPS eyebrow label
- ``headline_span``  an italic / recoloured word inside an h1 or h2
- ``arrow_cta``      "→" (or an arrow icon) appended to a button/link
- ``middle_dot``     "A · B · C" meta strings
- ``inline_heading_size`` inline style="font-size" on a heading
- ``fake_map``       a map card with no iframe (also stripped)
- ``placeholder_ui`` "coming soon" / invented-hours placeholder copy

Repairs (applied to the returned html):
- fake map cards removed
- inline font-size stripped from h1/h2/h3
- arrow glyphs stripped from button/link text
- when AOS is not wanted (plan mode), the AOS link/script and every
  data-aos attribute are removed so nothing stays hidden on load

Pure module — regex over the HTML, no network.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

AOS_MAX = 2
EYEBROW_MAX = 1

_ARROW_GLYPHS = "→➜➔⟶➝➞⇒»›"
_ARROW_RE = re.compile(r"\s*[" + _ARROW_GLYPHS + r"]+\s*")
_ARROW_ICON_RE = re.compile(r"<i\b[^>]*\bfa-(?:arrow-right|arrow-right-long|chevron-right|angle-right|circle-arrow-right)\b[^>]*>\s*</i>", re.IGNORECASE)
_CTA_RE = re.compile(r"<(a|button)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
_HEADLINE_RE = re.compile(r"<(h1|h2)\b[^>]*>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
_ITALIC_SPAN_RE = re.compile(r"<(span|em|i)\b[^>]*\b(?:class=[\"'][^\"']*\bitalic\b[^\"']*[\"']|style=[\"'][^\"']*font-style\s*:\s*italic)", re.IGNORECASE)
_EM_RE = re.compile(r"<(em|i)\b[^>]*>", re.IGNORECASE)
_COLOUR_SPAN_RE = re.compile(
    r"<span\b[^>]*\b(?:class=[\"'][^\"']*\btext-(?:primary|secondary|accent|\[|[a-z]+-[1-9]00)|style=[\"'][^\"']*\bcolor\s*:)",
    re.IGNORECASE,
)
_EYEBROW_RE = re.compile(
    r"<(?:p|span|div|small|h[3-6])\b[^>]*class=[\"'][^\"']*\buppercase\b[^\"']*\btracking-(?:wide|wider|widest|\[)[^\"']*[\"']",
    re.IGNORECASE,
)
_EYEBROW_RE_2 = re.compile(
    r"<(?:p|span|div|small|h[3-6])\b[^>]*class=[\"'][^\"']*\btracking-(?:wide|wider|widest|\[)[^\"']*\buppercase\b[^\"']*[\"']",
    re.IGNORECASE,
)
_EYEBROW_STYLE_RE = re.compile(r"style=[\"'][^\"']*text-transform\s*:\s*uppercase[^\"']*letter-spacing", re.IGNORECASE)
_DATA_AOS_RE = re.compile(r"\sdata-aos(?:-[a-z-]+)?=[\"'][^\"']*[\"']", re.IGNORECASE)
_AOS_LINK_RE = re.compile(r"<link\b[^>]*aos(?:\.min)?\.css[^>]*>\s*", re.IGNORECASE)
_AOS_SCRIPT_RE = re.compile(r"<script\b[^>]*aos(?:\.min)?\.js[^>]*>\s*</script>\s*", re.IGNORECASE)
_AOS_INIT_RE = re.compile(r"<script\b[^>]*>\s*(?:[^<]*?)AOS\.init\([^<]*?</script>\s*", re.IGNORECASE | re.DOTALL)
_MIDDLE_DOT_RE = re.compile(r">[^<]*\S\s*·\s*\S[^<]*·\s*\S[^<]*<")
_HEADING_INLINE_SIZE_RE = re.compile(r"(<h[1-3]\b[^>]*\bstyle=[\"'])([^\"']*)([\"'])", re.IGNORECASE)
_FONT_SIZE_DECL_RE = re.compile(r"font-size\s*:[^;\"']*;?\s*", re.IGNORECASE)
_MAP_CARD_OPEN_RE = re.compile(r"<(div|section|article|aside)\b[^>]*\b(?:class|id)=[\"'][^\"']*\bmap[-_ ]?(?:card|placeholder|box|preview|wrapper|container)\b[^\"']*[\"'][^>]*>", re.IGNORECASE)
_MAP_ICON_RE = re.compile(r"fa-(?:map|map-location-dot|map-marked|map-marked-alt|location-dot|map-pin)\b", re.IGNORECASE)
_PLACEHOLDER_COPY_RE = re.compile(
    r"\b(?:coming soon|akan datang|lorem ipsum|placeholder|\[[A-Z _]{3,}\]|to be announced|tba\b)",
    re.IGNORECASE,
)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class AntiTemplateReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    repairs: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> Dict:
        return {"ok": self.ok, "errors": list(self.errors), "warnings": list(self.warnings), "repairs": list(self.repairs), "counts": dict(self.counts)}

    def feedback_lines(self) -> List[str]:
        return [f"- LINT FAIL: {e}" for e in self.errors] + [f"- LINT WARN: {w}" for w in self.warnings]


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", fragment)).strip()


def _find_element_span(html: str, open_match: "re.Match") -> Tuple[int, int]:
    """Span of a balanced element starting at ``open_match`` (same tag name)."""
    tag = open_match.group(1).lower()
    start = open_match.start()
    pos = open_match.end()
    depth = 1
    token = re.compile(rf"<(/?)({tag})\b[^>]*>", re.IGNORECASE)
    while depth and pos < len(html):
        m = token.search(html, pos)
        if not m:
            return start, len(html)
        depth += -1 if m.group(1) else 1
        pos = m.end()
    return start, pos


def strip_fake_map_cards(html: str) -> Tuple[str, int]:
    """Remove map cards that carry no iframe. A real embed (widget slot or
    Google iframe) is left alone."""
    removed = 0
    out = html
    pos = 0
    while True:
        m = _MAP_CARD_OPEN_RE.search(out, pos)
        if not m:
            break
        start, end = _find_element_span(out, m)
        block = out[start:end]
        if "<iframe" in block.lower() or "binaapp-maps-slot" in block:
            pos = m.end()
            continue
        out = out[:start] + out[end:]
        removed += 1
        pos = start
    return out, removed


def strip_aos(html: str) -> Tuple[str, int]:
    """Remove the AOS library and every data-aos attribute. Returns the
    number of attributes removed."""
    out, n_attr = _DATA_AOS_RE.subn("", html)
    out = _AOS_LINK_RE.sub("", out)
    out = _AOS_SCRIPT_RE.sub("", out)
    out = _AOS_INIT_RE.sub("", out)
    out = re.sub(r"\s*document\.documentElement\.classList\.add\('aos-initialized'\);?", "", out)
    return out, n_attr


def strip_heading_inline_font_size(html: str) -> Tuple[str, int]:
    n = 0

    def _sub(m: "re.Match") -> str:
        nonlocal n
        style = m.group(2)
        cleaned, k = _FONT_SIZE_DECL_RE.subn("", style)
        n += k
        cleaned = cleaned.strip().strip(";").strip()
        return f"{m.group(1)}{cleaned}{m.group(3)}"

    return _HEADING_INLINE_SIZE_RE.sub(_sub, html), n


def strip_cta_arrows(html: str) -> Tuple[str, int]:
    n = 0

    def _sub(m: "re.Match") -> str:
        nonlocal n
        tag, inner = m.group(1), m.group(2)
        cleaned, k1 = _ARROW_ICON_RE.subn("", inner)
        # Only touch glyphs in the visible text, not inside attributes.
        cleaned, k2 = _ARROW_RE.subn(" ", cleaned) if re.search(r"[" + _ARROW_GLYPHS + r"]", _text(cleaned)) else (cleaned, 0)
        n += k1 + k2
        if k1 or k2:
            cleaned = re.sub(r"\s+(?=</)", "", cleaned).rstrip()
            head = m.group(0)[: m.start(2) - m.start(0)]
            return f"{head}{cleaned}</{tag}>"
        return m.group(0)

    return _CTA_RE.sub(_sub, html), n


def lint_anti_template(
    html: str,
    *,
    allow_aos: bool = False,
    hours_supplied: bool = False,
    repair: bool = True,
) -> Tuple[str, AntiTemplateReport]:
    """Check ``html`` against the anti-template rules and apply the safe
    repairs. Returns (html, report)."""
    report = AntiTemplateReport()
    out = html or ""

    # --- data-aos ----------------------------------------------------------
    aos_count = len(_DATA_AOS_RE.findall(out))
    report.counts["data_aos"] = aos_count
    if aos_count > AOS_MAX:
        report.errors.append(
            f"{aos_count} data-aos attributes — animation on every section. Allowed: one page-load moment on the hero, written as a CSS keyframe; no data-aos."
        )
    if repair and not allow_aos and (aos_count or "aos.js" in out.lower() or "aos.css" in out.lower()):
        out, n = strip_aos(out)
        report.repairs.append(f"removed AOS library and {n} data-aos attribute(s)")

    # --- eyebrows ----------------------------------------------------------
    eyebrows = len(_EYEBROW_RE.findall(out)) + len(_EYEBROW_RE_2.findall(out)) + len(_EYEBROW_STYLE_RE.findall(out))
    report.counts["eyebrows"] = eyebrows
    if eyebrows > EYEBROW_MAX:
        report.errors.append(
            f"{eyebrows} tracked ALL-CAPS eyebrow labels above headings. Allowed: at most one on the whole page, and only when it carries information."
        )

    # --- decorated headlines -----------------------------------------------
    decorated = 0
    for m in _HEADLINE_RE.finditer(out):
        inner = m.group(2)
        if _ITALIC_SPAN_RE.search(inner) or _EM_RE.search(inner) or _COLOUR_SPAN_RE.search(inner):
            decorated += 1
    report.counts["decorated_headlines"] = decorated
    if decorated:
        report.errors.append(
            f"{decorated} headline(s) with an italic or recoloured word (span/em inside h1/h2). Headlines are set whole: one colour, one style."
        )

    # --- arrows in CTAs ----------------------------------------------------
    arrows = 0
    for m in _CTA_RE.finditer(out):
        inner = m.group(2)
        if _ARROW_ICON_RE.search(inner) or re.search(r"[" + _ARROW_GLYPHS + r"]", _text(inner)):
            arrows += 1
    report.counts["arrow_ctas"] = arrows
    if arrows:
        report.errors.append(f"{arrows} button/link(s) end in an arrow glyph or arrow icon. Buttons carry plain text.")
        if repair:
            out, n = strip_cta_arrows(out)
            if n:
                report.repairs.append(f"stripped {n} arrow(s) from button/link text")

    # --- middle-dot meta ---------------------------------------------------
    dots = len(_MIDDLE_DOT_RE.findall(out))
    report.counts["middle_dot"] = dots
    if dots:
        report.errors.append(f"{dots} middle-dot meta string(s) (\"A · B · C\"). Write facts as sentences or a structured list.")

    # --- inline heading font-size ------------------------------------------
    inline_sizes = sum(1 for m in _HEADING_INLINE_SIZE_RE.finditer(out) if _FONT_SIZE_DECL_RE.search(m.group(2)))
    report.counts["inline_heading_size"] = inline_sizes
    if inline_sizes:
        report.warnings.append(f"{inline_sizes} heading(s) with inline style=\"font-size\" — sizes belong in the stylesheet scale.")
        if repair:
            out, n = strip_heading_inline_font_size(out)
            report.repairs.append(f"stripped inline font-size from {n} heading(s)")

    # --- fake map cards ----------------------------------------------------
    if repair:
        out, removed = strip_fake_map_cards(out)
        report.counts["fake_map_cards"] = removed
        if removed:
            report.errors.append(f"{removed} decorative map card(s) with no map embed — removed. Location is address text plus a real embed or a Google Maps link.")
    else:
        report.counts["fake_map_cards"] = len(_MAP_CARD_OPEN_RE.findall(out))

    # --- placeholder copy ----------------------------------------------------
    placeholders = [m.group(0) for m in _PLACEHOLDER_COPY_RE.finditer(_TAG_RE.sub(" ", out))]
    # "Akan Datang" is the honest menu placeholder the prompt itself asks for
    # when the merchant supplied no items; only flag the English filler and
    # bracket tokens as invented.
    invented = [p for p in placeholders if p.lower() not in ("akan datang",)]
    report.counts["placeholder_copy"] = len(invented)
    if invented:
        report.errors.append(f"placeholder copy on the page ({', '.join(sorted(set(invented))[:4])}). Only real merchant data may appear.")
    if not hours_supplied:
        hours_hits = re.findall(r"\b(?:[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm|pagi|petang|malam))\s*[-–]\s*(?:[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm|pagi|petang|malam))", _TAG_RE.sub(" ", out), re.IGNORECASE)
        if hours_hits:
            report.errors.append(f"opening hours on the page ({hours_hits[0]}) but the merchant supplied none — invented hours are forbidden.")
            report.counts["invented_hours"] = len(hours_hits)

    return out, report
