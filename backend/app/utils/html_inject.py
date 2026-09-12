"""Safe insertion of widget/script blocks before the closing </body> tag.

Every injector used to do ``html.replace("</body>", block + "\n</body>")``.
That replaces EVERY occurrence of the string — and generated pages can carry
the literal text ``</body>`` in places that are not the real closing tag
(observed in production: a section comment ``<!-- ===== BEFORE </body> — AOS
+ init ===== -->``). The replace-all then splices the widget block into the
middle of the document, breaking the comment open, rendering the block twice
(duplicate ids included) and leaving a stray premature ``</body>`` in the
page.

``insert_before_body`` inserts exactly once, before the LAST ``</body>`` —
the only occurrence that can be the document's real closing tag.
"""

from __future__ import annotations

import re


def insert_before_body(html: str, block: str) -> str:
    """Insert ``block`` immediately before the final ``</body>`` in ``html``.

    Falls back to appending when the document has no ``</body>`` at all,
    matching the old injectors' behavior.
    """
    if not html:
        return block
    idx = html.rfind("</body>")
    if idx == -1:
        return html + block
    return html[:idx] + block + "\n" + html[idx:]


def insert_before_footer(html: str, block: str) -> str:
    """Insert ``block`` immediately before the page's ``<footer>`` element.

    A content section appended before ``</body>`` lands AFTER the footer,
    which is how the Google Maps block ended up rendering below a published
    site's footer: a full-width map stranded under the copyright line, with
    nothing but page background beneath it.

    Falls back to ``insert_before_body`` when the document has no footer.
    """
    if not html:
        return block
    # The FIRST <footer> — a page footer is never nested inside content, and
    # matching the last one would sit the block inside a footer-in-footer.
    match = re.search(r"<footer\b", html, re.IGNORECASE)
    if not match:
        return insert_before_body(html, block)
    return html[:match.start()] + block + "\n" + html[match.start():]
