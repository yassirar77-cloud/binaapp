"""HTML auto-repair using html5lib via BeautifulSoup.

The publish gate in `app.utils.html_balance` blocks publish when the HTML has
unclosed mid-body tags or is missing `</html>`. AI-generated HTML hits that
gate often enough that users get stuck unable to publish. This module runs a
permissive HTML5 parser over the input and re-emits balanced HTML so the
validator only fires for genuinely catastrophic input.

Stacked with the regex scrub in `app.utils.html_balance` (script/style bodies
blanked before tag-scanning), the pipeline is:
    raw HTML
      → repair_html (this module: parse-and-re-emit via html5lib)
      → is_html_balanced (validator: refuse if still unbalanced)

The html5lib parser is HTML5-spec compliant and preserves <script>/<style>
bodies verbatim as raw character data, so CSS/JS containing characters that
look like tags ("<div>" inside a string literal, "<" in a comparison) is
untouched. All attributes — including data-*, on*, id, class — are preserved.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Match an HTML-looking tag opener: `<word` or `</word`. Used only to detect
# "input has zero HTML tags" — actual parsing is done by html5lib.
_ANY_TAG_RE = re.compile(r"<\s*/?\s*[a-zA-Z][a-zA-Z0-9]*\b")
_HTML_OPEN_RE = re.compile(r"<\s*html\b", re.IGNORECASE)
_BODY_OPEN_RE = re.compile(r"<\s*body\b", re.IGNORECASE)
_HEAD_OPEN_RE = re.compile(r"<\s*head\b", re.IGNORECASE)
_DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)

# HTML5 void elements — never need a closing tag.
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

def _scan_imbalance(html: str) -> Tuple[List[str], List[str]]:
    """Return (unclosed_tags, extra_closings) for the given HTML.

    Reuses the validator's mid-body scanner so this module's repair count
    matches what `is_html_balanced` reports. The validator only tracks
    unclosed tags (not extra closings, since its stack-pop algorithm
    silently discards stray close tags) — we surface those counts as
    `closed_unclosed_tags` in the repair report.

    `extra_closings` is approximated by counting close tags whose name has
    no matching opening anywhere in the strip-for-scan view of the source.
    """
    # Late import: html_balance is a sibling utility module, and importing
    # at module level would create a cycle if html_balance ever starts
    # using this module.
    from app.utils.html_balance import (
        find_mid_body_unclosed_tags,
        _scrub_script_and_style_bodies,
        _COMMENT_RE,
        _DOCTYPE_RE,
        _TAG_RE,
    )

    if not html:
        return [], []
    unclosed = find_mid_body_unclosed_tags(html)

    # Extra-closings approximation: tags where the close-tag count exceeds
    # the open-tag count after scrubbing script/style bodies.
    cleaned = _COMMENT_RE.sub("", html)
    cleaned = _DOCTYPE_RE.sub("", cleaned)
    cleaned = _scrub_script_and_style_bodies(cleaned)
    opens: dict = {}
    closes: dict = {}
    for m in _TAG_RE.finditer(cleaned):
        is_close = m.group(1) == "/"
        name = m.group(2).lower()
        self_closing = m.group(3) == "/"
        if name in _VOID_TAGS or self_closing:
            continue
        bucket = closes if is_close else opens
        bucket[name] = bucket.get(name, 0) + 1
    extra: List[str] = []
    for name, count in closes.items():
        diff = count - opens.get(name, 0)
        if diff > 0:
            extra.extend([name] * diff)
    return unclosed, extra


def _is_truly_empty_html(raw: str) -> bool:
    """True if the input contains no HTML-looking tags at all.

    Used to keep the validator's existing behaviour for catastrophic input:
    random plain text with zero HTML should still fail publish, not be
    silently wrapped in <html><body> by html5lib.
    """
    if not raw or not raw.strip():
        return True
    return _ANY_TAG_RE.search(raw) is None


def _feature_flag_enabled() -> bool:
    """Read HTML_AUTO_REPAIR_ENABLED from env. Default True; set to '0',
    'false', 'no', or 'off' (case-insensitive) to disable.
    """
    val = os.getenv("HTML_AUTO_REPAIR_ENABLED", "true").strip().lower()
    return val not in ("0", "false", "no", "off", "")


def repair_html(raw_html: str, *, context: str = "") -> Tuple[str, Dict]:
    """Parse `raw_html` with html5lib and re-emit balanced HTML.

    Args:
        raw_html: Possibly-malformed HTML from the AI generator.
        context: Optional identifier (e.g. subdomain) included in log lines.

    Returns:
        (repaired_html, repairs)
        repairs is a dict with at least these keys:
          - skipped: bool — repair did not run (flag off or catastrophic input)
          - skipped_reason: str — only present when skipped=True
          - closed_unclosed_tags: int
          - removed_extra_closings: int
          - added_missing_body: bool
          - added_missing_html: bool
          - size_delta_pct: float — (after - before) / before * 100
          - before_length: int
          - after_length: int

    When skipped, repaired_html is the input unchanged.
    """
    repairs: Dict = {
        "skipped": False,
        "closed_unclosed_tags": 0,
        "removed_extra_closings": 0,
        "added_missing_body": False,
        "added_missing_html": False,
        "size_delta_pct": 0.0,
        "before_length": len(raw_html or ""),
        "after_length": len(raw_html or ""),
    }

    if not _feature_flag_enabled():
        repairs["skipped"] = True
        repairs["skipped_reason"] = "feature_flag_off"
        return raw_html or "", repairs

    if not raw_html:
        repairs["skipped"] = True
        repairs["skipped_reason"] = "empty_input"
        return raw_html or "", repairs

    if _is_truly_empty_html(raw_html):
        # No HTML tags at all — defer to the validator so the user sees the
        # existing structural-failure message. Wrapping random text in
        # <html><body> would hide the real problem.
        repairs["skipped"] = True
        repairs["skipped_reason"] = "no_html_tags"
        return raw_html, repairs

    before_unclosed, before_extra = _scan_imbalance(raw_html)
    had_html_tag = bool(_HTML_OPEN_RE.search(raw_html))
    had_body_tag = bool(_BODY_OPEN_RE.search(raw_html))

    try:
        soup = BeautifulSoup(raw_html, "html5lib")
    except Exception as exc:
        # html5lib should never raise on real-world HTML, but if it does
        # we fall back to the original input so the validator can take over.
        logger.error(
            f"❌ html5lib parse failed for {context or '<unknown>'}: {exc}",
            exc_info=True,
        )
        repairs["skipped"] = True
        repairs["skipped_reason"] = f"parse_error:{type(exc).__name__}"
        return raw_html, repairs

    repaired = str(soup)

    # html5lib emits "<!DOCTYPE html>" only when one is present in the source.
    # The validator checks for trailing </html>; html5lib always emits that
    # when it produces a document, so we don't need to force it.

    after_unclosed, after_extra = _scan_imbalance(repaired)
    has_html_tag_after = bool(_HTML_OPEN_RE.search(repaired))
    has_body_tag_after = bool(_BODY_OPEN_RE.search(repaired))

    closed = max(0, len(before_unclosed) - len(after_unclosed))
    removed = max(0, len(before_extra) - len(after_extra))

    repairs["closed_unclosed_tags"] = closed
    repairs["removed_extra_closings"] = removed
    repairs["added_missing_html"] = (not had_html_tag) and has_html_tag_after
    repairs["added_missing_body"] = (not had_body_tag) and has_body_tag_after
    repairs["after_length"] = len(repaired)
    if repairs["before_length"]:
        delta = (len(repaired) - repairs["before_length"]) / repairs["before_length"]
        repairs["size_delta_pct"] = round(delta * 100, 2)

    summary_parts: List[str] = []
    if closed:
        summary_parts.append(
            f"closed {closed} unclosed tag{'s' if closed != 1 else ''} "
            f"({', '.join(before_unclosed[:5])})"
        )
    if removed:
        summary_parts.append(
            f"removed {removed} extra closing{'s' if removed != 1 else ''} "
            f"({', '.join(before_extra[:5])})"
        )
    if repairs["added_missing_html"]:
        summary_parts.append("added missing <html>")
    if repairs["added_missing_body"]:
        summary_parts.append("added missing <body>")

    label = f"for {context}" if context else ""
    if summary_parts:
        logger.info(
            f"🔧 Repaired HTML {label}: " + ", ".join(summary_parts)
        )
    else:
        logger.debug(
            f"🔧 HTML repair pass {label}: no changes "
            f"(size_delta={repairs['size_delta_pct']}%)"
        )

    if abs(repairs["size_delta_pct"]) > 30.0:
        logger.warning(
            f"⚠️ HTML repair size delta {repairs['size_delta_pct']}% "
            f"{label} (before={repairs['before_length']}, "
            f"after={repairs['after_length']}) — possible parser "
            f"misinterpretation, review output"
        )

    return repaired, repairs
