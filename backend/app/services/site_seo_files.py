"""`/sitemap.xml` and `/robots.txt` for a published site.

Generated pages carry Open Graph tags and JSON-LD (services/seo_metadata.py)
but the two files a crawler asks for FIRST did not exist: a request for
`kedaiali.binaapp.my/robots.txt` fell through to the SPA and a request for
`/sitemap.xml` 404'd. Google treats a missing robots.txt as "crawl anything"
and a missing sitemap as "discover what you can" — survivable, but it leaves
the merchant's own section anchors undiscovered and gives them nothing to
paste into Search Console.

Both files are derived from the page that is already being served — the
in-page anchors ARE the site structure for a one-pager — so nothing here can
advertise a URL that does not exist.
"""

from __future__ import annotations

import re
from typing import List
from xml.sax.saxutils import escape as _xml_escape

#: Anchors that are navigation chrome, not content worth listing.
_SKIP_ANCHOR_IDS = frozenset(
    {
        "",
        "top",
        "home",
        "utama",
        "main",
        "content",
        "body",
        "root",
        "app",
        "binaapp-contact-slot",
    }
)

#: id="..." on a section/div that the page's own nav links to.
_NAV_ANCHOR_RE = re.compile(r"""<a\b[^>]*\bhref\s*=\s*["']#([A-Za-z][\w-]*)["']""")

_ID_RE_TEMPLATE = r"""<(?:section|div|main|article)\b[^>]*\bid\s*=\s*["']{anchor}["']"""


def extract_section_anchors(html: str, limit: int = 25) -> List[str]:
    """The in-page sections a crawler should know about.

    An anchor only counts when the page BOTH links to it and actually contains
    a section with that id — a nav link to a section the generator dropped
    would otherwise become a sitemap entry pointing at nothing.
    """
    if not html:
        return []

    seen: List[str] = []
    for anchor in _NAV_ANCHOR_RE.findall(html):
        key = anchor.lower()
        if key in _SKIP_ANCHOR_IDS or anchor in seen:
            continue
        if not re.search(_ID_RE_TEMPLATE.format(anchor=re.escape(anchor)), html):
            continue
        seen.append(anchor)
        if len(seen) >= limit:
            break
    return seen


def build_sitemap_xml(
    site_url: str, html: str = "", last_modified: str = "", include_anchors: bool = True
) -> str:
    """A valid urlset for the site.

    `last_modified` should be an ISO-8601 date (YYYY-MM-DD); anything else is
    omitted rather than guessed — a wrong lastmod is worse than none.
    """
    base = (site_url or "").rstrip("/")
    if not base:
        return ""

    urls = [(base + "/", 1.0)]
    if include_anchors:
        for anchor in extract_section_anchors(html):
            urls.append((f"{base}/#{anchor}", 0.6))

    lastmod = ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", (last_modified or "")[:10] or ""):
        lastmod = f"    <lastmod>{last_modified[:10]}</lastmod>\n"

    entries = []
    for loc, priority in urls:
        entries.append(
            "  <url>\n"
            f"    <loc>{_xml_escape(loc)}</loc>\n"
            f"{lastmod}"
            f"    <priority>{priority}</priority>\n"
            "  </url>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )


def build_robots_txt(site_url: str, allow_indexing: bool = True) -> str:
    """robots.txt pointing at the sitemap.

    `allow_indexing=False` emits a full disallow — used for sites that are not
    in a servable state, so a locked or unpublished page never gets indexed and
    then outranked-by-its-own-error-page later.
    """
    base = (site_url or "").rstrip("/")
    if not allow_indexing:
        return "User-agent: *\nDisallow: /\n"

    lines = ["User-agent: *", "Allow: /"]
    if base:
        lines.append("")
        lines.append(f"Sitemap: {base}/sitemap.xml")
    return "\n".join(lines) + "\n"
