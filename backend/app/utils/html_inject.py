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
