"""Backslash-escape decoding for model-produced text.

Why this exists
---------------
Generated sites shipped with literal `\\u2014` and `\\U0001f4f1` in the visible
page — 17 occurrences on one live site, including the `<title>` and the meta
description. Nothing in the pipeline escapes them: every provider call decodes
with `httpx`'s `r.json()`, every JSON envelope goes through `json.loads`, and
the HTML itself never travels inside a JSON field. The escapes are written by
the MODEL, verbatim, into its HTML output — and `\\U0001f4f1` proves it, because
the 8-hex-digit capital-U form is Python source syntax that JSON cannot produce
(JSON would emit the surrogate pair `\\ud83d\\udcf1`).

So the missing step is not an un-escape of something we escaped; it is the
decode that was never applied to untrusted model output in the first place.
This module is that decode, applied once at the model-output boundary
(`AIService._extract_html`) and to merchant-supplied strings before they enter
a prompt, so an escape can neither be copied out of the input nor survive out
of the output.

Scope rules
-----------
* Only text OUTSIDE `<script>` and `<style>` is decoded. Inside them a
  backslash escape is legitimate source code — `"\\u003c"` in a JS string is
  correct and rewriting it would change program behaviour (and can smuggle a
  `</script>` through). Those blocks are passed through untouched.
* `\\uXXXX`, `\\UXXXXXXXX`, `\\xXX` and surrogate PAIRS are decoded. A lone
  surrogate is left alone — it has no character to decode to.
* A doubled backslash (`\\\\u2014`) means a literal backslash followed by "u2014"
  and is NOT a character escape, so it is left alone. Runs of backslashes are
  counted to get this right.
* Control characters (anything below U+0020 other than tab/newline) are NOT
  emitted: decoding `\\u0000` or `\\u000c` into the markup would corrupt it.
  Such a sequence is left as written and the validator reports it.
"""

from __future__ import annotations

import re
from typing import Tuple

#: A backslash escape carrying a code point. The leading `(?<!\\)` plus the
#: even-backslash guard in `_decode_fragment` keeps `\\u2014` (escaped
#: backslash) out of scope.
_ESCAPE_RE = re.compile(r"\\(?:U[0-9a-fA-F]{8}|u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})")

#: Same shape, used by callers that only need to KNOW whether text carries an
#: escape (the validator) rather than rewrite it.
ESCAPE_DETECT_RE = _ESCAPE_RE

#: `<script>`/`<style>` blocks, whose contents are never decoded.
_RAW_TEXT_BLOCK_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)

#: UTF-16 surrogate halves — `📱` is one emoji, not two characters.
_HIGH_SURROGATE = range(0xD800, 0xDC00)
_LOW_SURROGATE = range(0xDC00, 0xE000)


def _is_escapable_codepoint(cp: int) -> bool:
    """True when `cp` is safe to emit as a literal character in markup.

    Control characters are rejected: turning `\\u0000` into a real NUL (or
    `\\u000c` into a form feed) would corrupt the document rather than repair
    it. Tab, newline and carriage return are ordinary whitespace and allowed.
    """
    if cp in _HIGH_SURROGATE or cp in _LOW_SURROGATE:
        return False
    if cp > 0x10FFFF:
        return False
    if cp < 0x20 and cp not in (0x09, 0x0A, 0x0D):
        return False
    if 0x7F <= cp <= 0x9F:
        return False
    return True


def _codepoint(token: str) -> int:
    """Code point for a matched `\\uXXXX` / `\\UXXXXXXXX` / `\\xXX` token."""
    return int(token[2:], 16)


def _preceding_backslashes(text: str, idx: int) -> int:
    """How many backslashes run backwards from (and excluding) `idx`."""
    n = 0
    while idx - n - 1 >= 0 and text[idx - n - 1] == "\\":
        n += 1
    return n


def _decode_fragment(text: str) -> Tuple[str, int]:
    """Decode every character escape in one escape-free-context fragment.

    Returns (decoded, count). Surrogate pairs are joined before decoding, so
    `\\ud83d\\udcf1` becomes a single 📱 rather than two unusable halves.
    """
    out: list[str] = []
    pos = 0
    decoded = 0

    while True:
        match = _ESCAPE_RE.search(text, pos)
        if not match:
            out.append(text[pos:])
            break

        start, end = match.span()
        # An ODD number of preceding backslashes means the backslash that
        # opens this match is itself escaped ("\\u2014" = literal backslash +
        # "u2014"), so there is no character escape here.
        if _preceding_backslashes(text, start) % 2 == 1:
            out.append(text[pos:end])
            pos = end
            continue

        cp = _codepoint(match.group())

        # Surrogate pair: consume the low half too and emit the real character.
        if cp in _HIGH_SURROGATE:
            nxt = _ESCAPE_RE.match(text, end)
            if nxt and _codepoint(nxt.group()) in _LOW_SURROGATE:
                low = _codepoint(nxt.group())
                combined = 0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00)
                out.append(text[pos:start])
                out.append(chr(combined))
                pos = nxt.end()
                decoded += 1
                continue
            # Lone high surrogate — nothing valid to decode to.
            out.append(text[pos:end])
            pos = end
            continue

        if not _is_escapable_codepoint(cp):
            out.append(text[pos:end])
            pos = end
            continue

        out.append(text[pos:start])
        out.append(chr(cp))
        pos = end
        decoded += 1

    return "".join(out), decoded


def decode_text_escapes(text: str) -> Tuple[str, int]:
    """Decode backslash character escapes in plain text (no markup awareness).

    Use for values that are not HTML — a business name, a menu item, a meta
    description read out of a brief. Returns (decoded, count).
    """
    if not text or "\\" not in text:
        return text or "", 0
    return _decode_fragment(text)


def decode_html_escapes(html: str) -> Tuple[str, int]:
    """Decode backslash character escapes in HTML, skipping script/style.

    This is the boundary decode for model output. Returns (decoded, count);
    `count` is 0 and the input is returned unchanged when there is nothing to
    do, so callers can log only when the repair actually fired.
    """
    if not html or "\\" not in html:
        return html or "", 0

    parts: list[str] = []
    total = 0
    cursor = 0

    for block in _RAW_TEXT_BLOCK_RE.finditer(html):
        fragment, n = _decode_fragment(html[cursor:block.start()])
        parts.append(fragment)
        total += n
        # script/style contents pass through verbatim — a backslash escape in
        # there is source code, not a leaked escape.
        parts.append(block.group())
        cursor = block.end()

    fragment, n = _decode_fragment(html[cursor:])
    parts.append(fragment)
    total += n

    return "".join(parts), total


def find_escape_leaks(html: str, limit: int = 10) -> list[str]:
    """Escape sequences still present in HTML outside script/style.

    Returns short surrounding snippets (not just the token) so a failure
    message can show where the leak is. Used by the pre-publish gate.
    """
    html = html or ""
    leaks: list[str] = []
    cursor = 0
    spans: list[Tuple[int, int]] = []

    for block in _RAW_TEXT_BLOCK_RE.finditer(html):
        spans.append((cursor, block.start()))
        cursor = block.end()
    spans.append((cursor, len(html)))

    for start, end in spans:
        for match in _ESCAPE_RE.finditer(html, start, end):
            if _preceding_backslashes(html, match.start()) % 2 == 1:
                continue
            lo = max(start, match.start() - 30)
            hi = min(end, match.end() + 30)
            leaks.append(re.sub(r"\s+", " ", html[lo:hi]).strip())
            if len(leaks) >= limit:
                return leaks
    return leaks
