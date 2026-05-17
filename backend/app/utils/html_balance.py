"""HTML tag-balance utilities.

Shared by:
  - ai_service._extract_html (detects mid-body truncation in AI output and
    auto-inserts missing closers).
  - publish endpoints (refuse to publish unbalanced HTML — see Option B of the
    truncation-investigation follow-up).

Lightweight regex-based scan. Not a full HTML parser, but good enough for the
specific failure mode we keep seeing: LLMs emitting </body></html> at the tail
while having dropped one or more intermediate </section>/</div> closers.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# HTML5 void elements — never on the open-tag stack.
VOID_HTML_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

_TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)
_TRAILING_HTML_CLOSE_RE = re.compile(r"</\s*html\s*>\s*$", re.IGNORECASE)
_TRAILING_BODY_CLOSE_RE = re.compile(r"</\s*body\s*>\s*$", re.IGNORECASE)
# Match a complete <script>...</script> or <style>...</style> block and let us
# blank out the body. JS template literals routinely contain text that LOOKS
# like HTML tags (e.g. `<NumParticles>`, `<span>` inside a string, even literal
# "<script>" in tracking-snippet strings) — without this scrub the forward
# tag-scanner treats them as real HTML and reports phantom unclosed tags.
# Discovered in production: dry-run on `doop` proposed inserting </numparticles>
# and </script>; on `vevo`, </span>. Both bogus, both from JS-string contents.
# Body is .*? (non-greedy) + DOTALL so it spans newlines but stops at the
# first matching close. The opening tag itself is preserved so the
# outer scanner still sees a matched <script>...</script> pair.
_SCRIPT_BLOCK_RE = re.compile(
    r"(<script\b[^>]*>)(.*?)(</script\s*>)", re.DOTALL | re.IGNORECASE
)
_STYLE_BLOCK_RE = re.compile(
    r"(<style\b[^>]*>)(.*?)(</style\s*>)", re.DOTALL | re.IGNORECASE
)
# Fallback for truncated documents: <script> or <style> that opens but never
# closes through end-of-document. Blank everything after the opener so the
# tag-scanner still sees the open tag (correctly unclosed) without parsing
# the JS/CSS body as if it were HTML.
_UNCLOSED_SCRIPT_TAIL_RE = re.compile(
    r"(<script\b[^>]*>)(?:(?!</script\s*>).)*\Z", re.DOTALL | re.IGNORECASE
)
_UNCLOSED_STYLE_TAIL_RE = re.compile(
    r"(<style\b[^>]*>)(?:(?!</style\s*>).)*\Z", re.DOTALL | re.IGNORECASE
)


def _scrub_script_and_style_bodies(html: str) -> str:
    """Replace the body of every <script>...</script> and <style>...</style>
    block with an empty string. The opening and closing tags are preserved
    so the forward tag-scanner still counts them as a balanced pair. The
    body text — which may legitimately contain `<` and `>` characters inside
    JS strings, CSS selectors, or template literals — is removed so the
    regex tag-finder can't mistake it for HTML markup.

    Two passes:
      1. Paired blocks <script>...</script> / <style>...</style> — body blanked.
      2. Trailing unclosed blocks (truncated source) — body blanked but the
         opener kept on the stack so balance scan still reports it as unclosed.

    Idempotent: a second pass over already-scrubbed HTML is a no-op.
    """
    if not html:
        return html
    html = _SCRIPT_BLOCK_RE.sub(lambda m: m.group(1) + m.group(3), html)
    html = _STYLE_BLOCK_RE.sub(lambda m: m.group(1) + m.group(3), html)
    # Handle truncated tails — only the opener survives.
    html = _UNCLOSED_SCRIPT_TAIL_RE.sub(lambda m: m.group(1), html)
    html = _UNCLOSED_STYLE_TAIL_RE.sub(lambda m: m.group(1), html)
    return html


def find_unclosed_tags(html: str) -> List[str]:
    """Return the list of tag names still open at the end of `html`.

    Forgiving on close-tag mismatch: pops down to the matching open tag if
    present in the stack, so mild nesting errors don't blow up the scan. The
    flip side is that a trailing </body></html> can consume intermediate open
    tags by popping back to them — see `find_mid_body_unclosed_tags` for the
    workaround when that's a problem.

    Pre-scrub: <script> and <style> block bodies are blanked before scanning,
    because JS/CSS routinely contain text that looks like HTML markup
    (template literals, snippets in strings) and the regex scanner can't
    distinguish those from real tags otherwise.
    """
    if not html:
        return []
    cleaned = _COMMENT_RE.sub("", html)
    cleaned = _DOCTYPE_RE.sub("", cleaned)
    cleaned = _scrub_script_and_style_bodies(cleaned)
    stack: List[str] = []
    for m in _TAG_RE.finditer(cleaned):
        is_close = m.group(1) == "/"
        name = m.group(2).lower()
        self_closing = m.group(3) == "/"
        if name in VOID_HTML_TAGS or self_closing:
            continue
        if is_close:
            if name in stack:
                while stack and stack.pop() != name:
                    pass
        else:
            stack.append(name)
    return stack


def strip_trailing_wrapper_closers(text: str) -> str:
    """Strip a trailing </body></html> (with optional whitespace) so a re-scan
    of the remainder exposes mid-document tag imbalance that the forgiving
    stack-pop loop would otherwise hide."""
    stripped = text.rstrip()
    m = _TRAILING_HTML_CLOSE_RE.search(stripped)
    if m:
        stripped = stripped[: m.start()].rstrip()
    m = _TRAILING_BODY_CLOSE_RE.search(stripped)
    if m:
        stripped = stripped[: m.start()].rstrip()
    return stripped


def find_mid_body_unclosed_tags(text: str) -> List[str]:
    """Return the list of mid-document tags still open inside <body>, ignoring
    the <html> and <body> openers themselves.

    This is the check the publish gate uses: if it returns a non-empty list,
    the HTML has the silent-truncation failure mode that caused jiwa/huil/juio
    to render with broken layout (an open <section> nested <div id="page-order">
    inside the testimonials block at splice time).
    """
    if not text:
        return []
    raw = find_unclosed_tags(strip_trailing_wrapper_closers(text))
    return [t for t in raw if t not in ("html", "body")]


def is_html_balanced(text: str) -> Tuple[bool, List[str]]:
    """Convenience for the publish gate.

    Returns (is_balanced, unbalanced_tags). is_balanced is False if either:
      - the text doesn't end with </html> (classic end-of-stream truncation), or
      - find_mid_body_unclosed_tags returns a non-empty list (silent mid-body
        imbalance — </html> present but inner tags dropped).
    """
    if not text:
        return True, []
    ends_with_html = text.rstrip().endswith("</html>")
    mid_body = find_mid_body_unclosed_tags(text)
    if not ends_with_html:
        return False, find_unclosed_tags(text)
    if mid_body:
        return False, mid_body
    return True, []
