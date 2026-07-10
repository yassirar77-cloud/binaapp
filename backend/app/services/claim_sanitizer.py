"""Deterministic post-generation sanitizer for sensitive, trust-regulated claims.

The HTML generators (GLM primary, DeepSeek fallback) have occasionally invented
claims a merchant never made — e.g. an "Est. 2024 · Pengusaha Muslim" badge.
In Malaysia, Muslim-ownership and halal claims are regulated and trust-sensitive
(JAKIM); publishing an invented claim of that kind on a merchant's behalf is a
serious problem, and prompt rules alone cannot guarantee it never happens.

This module is the deterministic protection layer: after generation, the HTML
is scanned for a configurable list of sensitive-claim patterns (BM + English,
case-insensitive). Any match NOT backed by the merchant-provided source data
is removed — the whole element when the claim sits in a small badge/pill, or
just the claim text when it sits inside longer prose. Claims the merchant DID
state themselves are always kept.

Pattern list is configurable without code changes via the
SENSITIVE_CLAIM_PATTERNS env var (JSON array replacing the defaults) and/or
SENSITIVE_CLAIM_PATTERNS_EXTRA (JSON array appended to the active list).
Each entry: {"label": str, "pattern": regex-str, "verify": "pattern"|"year"}.
- verify="pattern": the claim is kept iff the same pattern matches the
  merchant source data (so "Halal" survives when the description says halal).
- verify="year": the claim is kept iff the 4-digit year captured from the
  match appears anywhere in the merchant source data (so "Est. 2024" survives
  only when the merchant actually provided 2024).
"""

import json
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

from loguru import logger

# Default sensitive-claim patterns (case-insensitive; BM + English).
# Kept deliberately narrow: these are claims that are regulated or
# trust-sensitive in the Malaysian market, plus establishment-year claims
# the generators have been observed to invent.
DEFAULT_SENSITIVE_CLAIM_PATTERNS: List[Dict[str, str]] = [
    {"label": "pengusaha-muslim", "pattern": r"pengusaha\s+muslim", "verify": "pattern"},
    {"label": "muslim-owned", "pattern": r"muslim[\s-]+owned", "verify": "pattern"},
    {"label": "milik-muslim", "pattern": r"milik\s+(?:orang\s+)?muslim", "verify": "pattern"},
    {"label": "bumiputera", "pattern": r"\bbumiputer?a\b", "verify": "pattern"},
    {"label": "halal", "pattern": r"\bhalal\b", "verify": "pattern"},
    {"label": "jakim", "pattern": r"\bjakim\b", "verify": "pattern"},
    {"label": "no-pork", "pattern": r"\bno\s+pork(?:[,\s]+no\s+lard)?\b", "verify": "pattern"},
    {"label": "tanpa-babi", "pattern": r"\btanpa\s+babi\b", "verify": "pattern"},
    {"label": "pork-free", "pattern": r"\bpork[\s-]+free\b", "verify": "pattern"},
    {"label": "est-year", "pattern": r"\best\.?\s*(\d{4})\b", "verify": "year"},
    {"label": "sejak-year", "pattern": r"\bsejak\s+(\d{4})\b", "verify": "year"},
    {"label": "established-year", "pattern": r"\bestablished\s+(?:in\s+)?(\d{4})\b", "verify": "year"},
]


def _parse_pattern_env(raw: Optional[str], env_name: str) -> Optional[List[Dict[str, str]]]:
    if not raw or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
        entries = []
        for e in parsed:
            if isinstance(e, dict) and e.get("pattern"):
                entries.append({
                    "label": str(e.get("label", e["pattern"])),
                    "pattern": str(e["pattern"]),
                    "verify": str(e.get("verify", "pattern")),
                })
        return entries
    except (ValueError, TypeError) as err:
        logger.warning(f"🛡 Ignoring malformed {env_name}: {err}")
        return None


def sensitive_claim_patterns() -> List[Dict[str, str]]:
    """Active pattern list. Read at call time so an env change (Render) takes
    effect without a redeploy — same contract as image_provider() etc."""
    base = _parse_pattern_env(os.getenv("SENSITIVE_CLAIM_PATTERNS"), "SENSITIVE_CLAIM_PATTERNS")
    patterns = list(base) if base is not None else list(DEFAULT_SENSITIVE_CLAIM_PATTERNS)
    extra = _parse_pattern_env(
        os.getenv("SENSITIVE_CLAIM_PATTERNS_EXTRA"), "SENSITIVE_CLAIM_PATTERNS_EXTRA"
    )
    if extra:
        patterns.extend(extra)
    return patterns


# Every tag in the document, opening or closing, for the innermost-element scan.
_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)(?:\s[^<>]*)?>")
# Tags that never contain a text claim / never close.
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})
# Structural tags never removed wholesale, however short their text — a claim
# inside them is always prose-stripped instead.
_STRUCTURAL_TAGS = frozenset({
    "html", "head", "body", "main", "section", "article", "header",
    "footer", "nav", "aside", "ul", "ol", "table",
})
# A badge/pill is a small element: visible text at most this long.
_BADGE_TEXT_MAX_CHARS = 80
# Separators that badge text strings claims together with ("Est. 2024 · Halal").
_SEPARATOR_AFTER_RE = re.compile(r"^(?:\s*[·•|,;]+\s*|\s+[-–—]\s+)")
_SEPARATOR_BEFORE_RE = re.compile(r"(?:\s*[·•|,;]+\s*|\s+[-–—]\s+)$")


def _is_inside_tag_markup(html: str, pos: int) -> bool:
    """True when pos sits inside <...> markup (tag name/attributes)."""
    lt = html.rfind("<", 0, pos)
    if lt == -1:
        return False
    gt = html.rfind(">", 0, pos)
    return lt > gt


def _is_inside_raw_text_block(html_lower: str, pos: int) -> bool:
    """True when pos sits inside a <script> or <style> block — stripping text
    there risks breaking JS/CSS, and nothing in those blocks renders as a
    visible claim anyway."""
    for tag in ("script", "style"):
        open_idx = html_lower.rfind(f"<{tag}", 0, pos)
        if open_idx == -1:
            continue
        close_idx = html_lower.rfind(f"</{tag}", 0, pos)
        if close_idx < open_idx:
            return True
    return False


def _innermost_element_span(html: str, start: int, end: int) -> Optional[Tuple[int, int, str]]:
    """Locate the innermost element enclosing [start, end).

    Returns (element_start, element_end, tag_name) spanning the full
    <tag ...>...</tag>, or None when no well-formed enclosing element is found.
    """
    # Walk backwards over tags before the match, balancing close tags, to find
    # the innermost still-open element.
    pending_closes: Dict[str, int] = {}
    open_match = None
    for m in reversed(list(_TAG_RE.finditer(html, 0, start))):
        tag = m.group(2).lower()
        if tag in _VOID_TAGS or html[m.start():m.end()].rstrip(">").endswith("/"):
            continue
        if m.group(1):  # closing tag
            pending_closes[tag] = pending_closes.get(tag, 0) + 1
        elif pending_closes.get(tag, 0) > 0:
            pending_closes[tag] -= 1
        else:
            open_match = m
            break
    if open_match is None:
        return None
    tag = open_match.group(2).lower()
    # Find the matching close tag after the claim, balancing same-tag nesting.
    depth = 0
    for m in _TAG_RE.finditer(html, end):
        if m.group(2).lower() != tag:
            continue
        if m.group(1):
            if depth == 0:
                return open_match.start(), m.end(), tag
            depth -= 1
        else:
            depth += 1
    return None


def _visible_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", fragment)).strip()


def _strip_claim_text(html: str, start: int, end: int) -> str:
    """Remove just the claim text, tidying one adjacent list separator so a
    badge like 'Est. 2024 · Halal' doesn't leave a dangling '·'."""
    before, after = html[:start], html[end:]
    m_after = _SEPARATOR_AFTER_RE.match(after)
    if m_after:
        after = after[m_after.end():]
    else:
        m_before = _SEPARATOR_BEFORE_RE.search(before)
        if m_before:
            before = before[:m_before.start()]
    # Collapse a doubled space left at the splice point.
    if before.endswith(" ") and after.startswith(" "):
        after = after.lstrip(" ")
    return before + after


def _claim_is_verified(entry: Dict[str, str], compiled: "re.Pattern", match: "re.Match", source_blob: str) -> bool:
    if entry.get("verify") == "year":
        year_m = re.search(r"\d{4}", match.group(0))
        return bool(year_m) and year_m.group(0) in source_blob
    return bool(compiled.search(source_blob))


def sanitize_sensitive_claims(
    html: str, source_texts: Iterable[Optional[str]]
) -> Tuple[str, List[str]]:
    """Remove sensitive claims not present in the merchant-provided data.

    Args:
        html: generated website HTML (GLM, DeepSeek, or template path).
        source_texts: every merchant-provided text field (business name,
            description, address, menu/item names, badges) — the ground truth
            a claim must appear in to survive.

    Returns:
        (sanitized_html, list_of_removed_claim_texts). Every removal is also
        logged as "🛡 Removed unverified claim: '...'".
    """
    if not html:
        return html, []

    source_blob = " ".join(str(t) for t in source_texts if t).lower()
    removed: List[str] = []

    compiled_entries = []
    for entry in sensitive_claim_patterns():
        try:
            compiled_entries.append((entry, re.compile(entry["pattern"], re.IGNORECASE)))
        except re.error as err:
            logger.warning(f"🛡 Skipping invalid sensitive-claim pattern '{entry.get('label')}': {err}")

    # Each removal invalidates match offsets, so rescan after every edit.
    # The guard bounds pathological inputs; real pages carry a handful of
    # claims at most.
    for _ in range(200):
        edited = False
        for entry, compiled in compiled_entries:
            for match in compiled.finditer(html):
                if _is_inside_tag_markup(html, match.start()):
                    continue
                if _is_inside_raw_text_block(html.lower(), match.start()):
                    continue
                if _claim_is_verified(entry, compiled, match, source_blob):
                    continue

                claim_text = match.group(0)
                element = _innermost_element_span(html, match.start(), match.end())
                if (
                    element
                    and element[2] not in _STRUCTURAL_TAGS
                    and len(_visible_text(html[element[0]:element[1]])) <= _BADGE_TEXT_MAX_CHARS
                ):
                    # Small badge/pill — drop the whole element.
                    html = html[:element[0]] + html[element[1]:]
                else:
                    # Longer prose — strip only the claim text.
                    html = _strip_claim_text(html, match.start(), match.end())

                removed.append(claim_text)
                logger.info(f"🛡 Removed unverified claim: '{claim_text}'")
                edited = True
                break
            if edited:
                break
        if not edited:
            break

    return html, removed
