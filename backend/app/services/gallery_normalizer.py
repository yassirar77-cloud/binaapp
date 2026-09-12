"""Deterministic post-pass for AI-generated gallery HTML.

The generation prompt asks the model to (a) give every gallery/menu card
image the same height and (b) never repeat a category tag, but a prompt is
guidance, not a guarantee. This module enforces both deterministically on
the final HTML so the result is consistent regardless of what the model
emitted.

Pure stdlib (regex) — adds no dependency and runs in any generation path.
Every transform is wrapped so it can never raise into the pipeline; on any
error the original HTML is returned unchanged.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1) Uniform gallery/menu card image heights
# ---------------------------------------------------------------------------
# Numeric Tailwind heights typical of a CARD image area (a tall block).
# Deliberately starts at 40 so small images — avatars, logos, icons
# (h-8..h-32) — are never touched.
_CARD_HEIGHTS = {40, 44, 48, 52, 56, 60, 64, 72, 80, 96}

# If an <img>'s class carries any of these, it is NOT a uniform card image
# (hero/full-bleed/arbitrary/already-aspect/avatar) — leave it alone.
_SKIP_HEIGHT_MARKERS = ("h-screen", "h-[", "min-h-", "aspect-", "rounded-full", "h-full")

_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_CLASS_ATTR = re.compile(r"(\bclass\s*=\s*)(['\"])(.*?)\2", re.IGNORECASE | re.DOTALL)
_HEIGHT_TOKEN = re.compile(r"^(?:(?:sm|md|lg|xl|2xl):)?h-(\d+)$")


def _normalize_img_classes(class_value: str) -> str:
    low = class_value.lower()
    # Only normalize images that crop to fill (object-cover); normalizing a
    # contain/letterboxed image would distort it.
    if "object-cover" not in low:
        return class_value
    if any(marker in low for marker in _SKIP_HEIGHT_MARKERS):
        return class_value

    tokens = class_value.split()
    kept = []
    found_card_height = False
    for tok in tokens:
        m = _HEIGHT_TOKEN.match(tok)
        if m and int(m.group(1)) in _CARD_HEIGHTS:
            found_card_height = True
            continue  # drop this per-card height utility (base + responsive)
        kept.append(tok)

    if not found_card_height:
        return class_value

    if "aspect-[4/3]" not in kept:
        kept.append("aspect-[4/3]")
    if "w-full" not in kept:
        kept.insert(0, "w-full")
    return " ".join(kept)


def normalize_gallery_heights(html: str) -> str:
    """Replace per-card pixel heights on card images with a uniform aspect ratio."""
    def _img_sub(img_match):
        tag = img_match.group(0)

        def _class_sub(cm):
            new_cls = _normalize_img_classes(cm.group(3))
            return f"{cm.group(1)}{cm.group(2)}{new_cls}{cm.group(2)}"

        return _CLASS_ATTR.sub(_class_sub, tag, count=1)

    return _IMG_TAG.sub(_img_sub, html)


# ---------------------------------------------------------------------------
# 2) De-duplicate repeated gallery category tags
# ---------------------------------------------------------------------------
# A "tag" is a small badge/chip <span>, identified by badge-like classes.
_BADGE_HINTS = (
    "rounded-full", "uppercase", "tracking-", "text-xs",
    "text-[10px]", "text-[11px]", "badge", "chip",
)
# Short labels that legitimately repeat across cards (promo/status badges) and
# must NOT be de-duplicated. Matched case-insensitively.
_ALLOW_REPEAT = {
    "new", "baru", "popular", "populer", "terlaris", "best seller", "bestseller",
    "hot", "sale", "promo", "promosi", "diskaun", "discount", "halal", "viral",
    "signature", "recommended", "disyorkan", "sold out", "habis", "featured",
    "pilihan", "special", "istimewa", "trending", "limited",
}
_SPAN_BADGE = re.compile(
    r"<span\b([^>]*\bclass\s*=\s*['\"][^'\"]*['\"][^>]*)>([^<>]{1,24})</span>",
    re.IGNORECASE,
)


def dedupe_gallery_tags(html: str) -> str:
    """Remove a repeated non-promo category tag's later occurrences.

    Keeps the first instance; drops subsequent identical badge tags so the same
    label can't appear on two cards. Promo/status badges (NEW, HALAL, …) are
    allowed to repeat.
    """
    seen = set()

    def _sub(m):
        attrs_low = m.group(1).lower()
        if not any(hint in attrs_low for hint in _BADGE_HINTS):
            return m.group(0)  # not a badge — leave body text alone
        key = re.sub(r"\s+", " ", m.group(2).strip()).lower()
        if not key or key in _ALLOW_REPEAT:
            return m.group(0)
        if key in seen:
            return ""  # duplicate category tag — drop it
        seen.add(key)
        return m.group(0)

    return _SPAN_BADGE.sub(_sub, html)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 3) Omit gallery sections that have nothing in them
# ---------------------------------------------------------------------------
# A generated page keeps its "Galeri / Hasil Kerja Kami" section and nav link
# even when no image ever landed in it — the model emitted PHOTO_SLOT tokens
# for slots that had no URL, and those resolve to nothing. The result on a
# customer's live site is a titled section of empty cards, which reads as
# broken. This pass drops the section AND every nav link pointing at it.
_GALLERY_ID_WORDS = ("galeri", "gallery", "portfolio", "portofolio", "hasil-kerja", "hasil_kerja", "showcase")
_SECTION_RE = re.compile(r"<section\b([^>]*)>(.*?)</section\s*>", re.IGNORECASE | re.DOTALL)
_ID_ATTR = re.compile(r"""\bid\s*=\s*(['"])(.*?)\1""", re.IGNORECASE)
# Anything that actually paints a picture inside the section.
_REAL_MEDIA_RE = re.compile(
    r"""<img\b[^>]*\bsrc\s*=\s*['"]\s*(?:https?:)?//[^'"\s]+|"""
    r"""<img\b[^>]*\bsrc\s*=\s*['"]\s*/[^/'"][^'"\s]*|"""
    r"""<img\b[^>]*\bsrc\s*=\s*['"]\s*data:image/|"""
    r"""<(?:video|picture|source)\b|"""
    r"""url\(\s*['"]?\s*(?:https?:)?//""",
    re.IGNORECASE,
)


def _looks_like_gallery(open_attrs: str) -> bool:
    low = open_attrs.lower()
    return any(w in low for w in _GALLERY_ID_WORDS)


def omit_empty_gallery_sections(html: str) -> str:
    """Remove gallery/portfolio <section>s with no real media, plus their
    in-page nav links. Nested sections are left alone (a non-greedy match
    across a nested <section> would cut the outer one short)."""
    removed_ids = []

    def _sub(m: "re.Match") -> str:
        attrs, body = m.group(1), m.group(2)
        if not _looks_like_gallery(attrs):
            return m.group(0)
        if "<section" in body.lower():
            return m.group(0)
        if _REAL_MEDIA_RE.search(body):
            return m.group(0)
        id_m = _ID_ATTR.search(attrs)
        if id_m:
            removed_ids.append(id_m.group(2).strip())
        return ""

    out = _SECTION_RE.sub(_sub, html)
    if out == html:
        return html

    for sec_id in removed_ids:
        if not sec_id:
            continue
        # <a ... href="#galeri">Galeri</a>, in any nav, either quote style.
        link_re = re.compile(
            r"""<a\b[^>]*\bhref\s*=\s*['"]#""" + re.escape(sec_id) + r"""['"][^>]*>.*?</a\s*>""",
            re.IGNORECASE | re.DOTALL,
        )
        out = link_re.sub("", out)
    # Nav items that only wrapped a removed link.
    out = re.sub(r"<li\b[^>]*>\s*</li\s*>", "", out, flags=re.IGNORECASE)
    logger.info(
        "🖼️ Omitted %d empty gallery section(s) and their nav links: %s",
        len(removed_ids) or 1, removed_ids or ["(no id)"],
    )
    return out



# ---------------------------------------------------------------------------
# 3) Grid spans that do not add up
# ---------------------------------------------------------------------------
# A "Suasana" gallery shipped as `md:grid-cols-3` with three children spanning
# 2 + 1 + 1. That is four columns of content in a three-column grid, so the
# first row filled, the second row held one small image, and an empty white
# container sat beside it where the fourth cell would have been.
#
# The rule is arithmetic, not taste: if the children's spans do not add up to
# a whole number of rows, the layout has a hole in it. When that happens the
# span utilities are dropped and every child takes one equal cell — the
# layout the merchant would have got if the model had simply not reached for
# a feature span it did not have the images to finish.

_VOID_ELEMENTS = frozenset({
    "img", "br", "hr", "input", "meta", "link", "source", "area", "base",
    "col", "embed", "param", "track", "wbr",
})
_GRID_COLS_RE = re.compile(r"(?:^|\s)(?:(?:sm|md|lg|xl|2xl):)?grid-cols-(\d+)")
_COL_SPAN_RE = re.compile(r"(?:^|\s)(?:(?:sm|md|lg|xl|2xl):)?col-span-(\d+)")
_SPAN_TOKEN_RE = re.compile(r"^(?:(?:sm|md|lg|xl|2xl):)?(?:col|row)-span-(?:\d+|full)$")
_OPEN_TAG_RE = re.compile(r"<([a-zA-Z][\w-]*)\b[^>]*?(/?)>")


def _tag_classes(tag: str) -> str:
    match = _CLASS_ATTR.search(tag)
    return match.group(3) if match else ""


def _element_end(html: str, start: int) -> int:
    """Index just past the element that opens at ``start``, or -1.

    A small balanced scanner: regex cannot match nested divs, and a gallery
    grid is always nested.
    """
    open_match = _OPEN_TAG_RE.match(html, start)
    if not open_match:
        return -1
    name = open_match.group(1).lower()
    if open_match.group(2) == "/" or name in _VOID_ELEMENTS:
        return open_match.end()

    depth = 0
    pos = start
    pattern = re.compile(rf"<(/?){re.escape(name)}\b[^>]*?(/?)>", re.IGNORECASE)
    while True:
        match = pattern.search(html, pos)
        if not match:
            return -1
        if match.group(1) == "/":
            depth -= 1
            if depth == 0:
                return match.end()
        elif match.group(2) != "/":
            depth += 1
        pos = match.end()


def _direct_children(html: str, inner_start: int, inner_end: int) -> list:
    """(start, end) of every direct child element in [inner_start, inner_end)."""
    children = []
    pos = inner_start
    while pos < inner_end:
        nxt = html.find("<", pos)
        if nxt == -1 or nxt >= inner_end:
            break
        if not _OPEN_TAG_RE.match(html, nxt):
            pos = nxt + 1
            continue
        end = _element_end(html, nxt)
        if end == -1 or end > inner_end:
            break
        children.append((nxt, end))
        pos = end
    return children


def _strip_span_classes(class_value: str) -> str:
    return " ".join(t for t in class_value.split() if not _SPAN_TOKEN_RE.match(t))


def even_out_grid_spans(html: str) -> str:
    """Drop col/row spans from any grid whose children leave a hole."""
    out = html
    searched_from = 0
    fixed = 0

    while True:
        match = re.compile(r"<div\b[^>]*\bclass\s*=\s*([\'\"])(?=[^\'\"]*\bgrid\b)[^\'\"]*\1[^>]*>",
                           re.IGNORECASE).search(out, searched_from)
        if not match:
            break
        searched_from = match.end()
        classes = _tag_classes(match.group(0))
        columns = [int(c) for c in _GRID_COLS_RE.findall(classes)]
        if not columns:
            continue
        # The widest breakpoint is the desktop layout, which is where the
        # hole is visible.
        column_count = max(columns)
        if column_count < 2:
            continue

        element_end = _element_end(out, match.start())
        if element_end == -1:
            continue
        inner_start, inner_end = match.end(), element_end - len("</div>")
        children = _direct_children(out, inner_start, inner_end)
        if len(children) < 2:
            continue

        spans = []
        for start, end in children:
            child_tag = out[start:out.find(">", start) + 1]
            found = _COL_SPAN_RE.findall(_tag_classes(child_tag))
            spans.append(max((int(s) for s in found), default=1))
        if sum(spans) % column_count == 0 or all(s == 1 for s in spans):
            continue

        # Rewrite children back-to-front so earlier offsets stay valid.
        for start, end in reversed(children):
            tag_end = out.find(">", start) + 1
            tag = out[start:tag_end]

            def _rewrite(m):
                kept = _strip_span_classes(m.group(3))
                # A class attribute emptied by the strip is dropped, not
                # left as class="".
                return f"{m.group(1)}{m.group(2)}{kept}{m.group(2)}" if kept else ""

            new_tag = _CLASS_ATTR.sub(_rewrite, tag, count=1)
            new_tag = re.sub(r"\s+>", ">", new_tag)
            out = out[:start] + new_tag + out[tag_end:]
        fixed += 1
        searched_from = match.end()

    if fixed:
        logger.info(
            "🖼️ Evened out %d grid(s) whose column spans left an empty cell", fixed
        )
    return out


def normalize_gallery_html(html: str) -> str:
    """Apply all deterministic gallery fixes. Never raises."""
    try:
        html = omit_empty_gallery_sections(html)
    except Exception as exc:  # never raise into the pipeline
        logger.warning("omit_empty_gallery_sections skipped: %s", exc)
    if not html or "<img" not in html.lower():
        return html
    try:
        html = normalize_gallery_heights(html)
    except Exception as e:  # pragma: no cover - safety net
        logger.warning(f"gallery height normalize skipped: {e}")
    try:
        html = dedupe_gallery_tags(html)
    except Exception as e:  # pragma: no cover - safety net
        logger.warning(f"gallery tag dedupe skipped: {e}")
    try:
        html = even_out_grid_spans(html)
    except Exception as e:  # pragma: no cover - safety net
        logger.warning(f"grid span evening skipped: {e}")
    return html
