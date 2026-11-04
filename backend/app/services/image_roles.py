"""Which uploaded photo may play which role.

A tall menu poster (text-heavy, portrait) was used as the "Tentang Kami"
photo at a 4:3 object-cover crop, which cut it off. An upload's aspect
ratio is probed once (Cloudinary's ``fl_getinfo`` for Cloudinary URLs, the
image header otherwise); a portrait image is a *poster*: it is cropped
with ``c_fit`` instead of ``c_fill``, the prompt is told to keep it out of
the hero/about slots, and any <img> that still shows it outside the menu
is switched to ``object-contain`` after generation. When the vision check
is available, an image it reports as text-heavy is a poster too.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from loguru import logger

_CLOUDINARY_UPLOAD_RE = re.compile(r"^(https?://res\.cloudinary\.com/[^/]+/image/upload/)(.+)$", re.IGNORECASE)
_TRANSFORM_SEGMENT_RE = re.compile(r"^(?:[a-z]{1,3}_[^/]+)(?:,[a-z]{1,3}_[^/]+)*$")
_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_RE = re.compile(r"\bsrc\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
_CLASS_RE = re.compile(r"\bclass\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
_SECTION_OPEN_RE = re.compile(r"<section\b[^>]*>", re.IGNORECASE)
_SECTION_ANY_RE = re.compile(r"<(/?)section\b[^>]*>", re.IGNORECASE)
_MENU_ID_RE = re.compile(r"\bid\s*=\s*[\"'][^\"']*(menu|produk|product|harga|price)[^\"']*[\"']", re.IGNORECASE)

#: height / width from which an image counts as a poster.
POSTER_RATIO = 1.2


@dataclass
class ImageShape:
    url: str
    width: int = 0
    height: int = 0
    text_heavy: bool = False

    @property
    def portrait(self) -> bool:
        return self.width > 0 and self.height >= self.width * POSTER_RATIO

    @property
    def poster(self) -> bool:
        return self.portrait or self.text_heavy


def public_id_url(url: str) -> str:
    """The Cloudinary URL without any transform segment (its identity)."""
    m = _CLOUDINARY_UPLOAD_RE.match((url or "").strip())
    if not m:
        return (url or "").strip()
    rest = m.group(2)
    first = rest.split("/", 1)[0]
    if _TRANSFORM_SEGMENT_RE.match(first) and "/" in rest:
        rest = rest.split("/", 1)[1]
    return m.group(1) + rest


def same_image(a: str, b: str) -> bool:
    return bool(a and b) and public_id_url(a) == public_id_url(b)


async def probe_shape(url: str) -> ImageShape:
    """Width/height of an image: Cloudinary's fl_getinfo JSON for its own
    URLs, the decoded header otherwise. Unknown → 0×0 (never a poster)."""
    shape = ImageShape(url=url)
    m = _CLOUDINARY_UPLOAD_RE.match((url or "").strip())
    try:
        from app.services.image_intelligence import _fetch
        if m:
            data = await _fetch(f"{m.group(1)}fl_getinfo/{public_id_url(url)[len(m.group(1)):]}")
            if data:
                info = json.loads(data.decode("utf-8", "ignore"))
                out = info.get("output") or info.get("input") or {}
                shape.width, shape.height = int(out.get("width") or 0), int(out.get("height") or 0)
                return shape
        data = await _fetch(url)
        if data:
            from io import BytesIO
            from PIL import Image
            with Image.open(BytesIO(data)) as im:
                shape.width, shape.height = im.size
    except Exception as err:
        logger.info(f"🖼️ Shape probe failed ({str(url)[:80]}): {err}")
    return shape


async def classify_uploads(uploaded: Sequence, *, text_check=None) -> Dict[str, ImageShape]:
    """Shapes keyed by the upload's identity URL. ``text_check`` (optional,
    async url → bool) marks a text-heavy image as a poster."""
    shapes: Dict[str, ImageShape] = {}
    for img in uploaded or []:
        url = img.get("url") if isinstance(img, dict) else (img if isinstance(img, str) else "")
        if not url:
            continue
        key = public_id_url(url)
        if key in shapes:
            continue
        shape = await probe_shape(url)
        if text_check is not None and not shape.portrait:
            try:
                shape.text_heavy = bool(await text_check(url))
            except Exception as err:
                logger.info(f"🖼️ Text check failed ({url[:80]}): {err}")
        shapes[key] = shape
        if shape.poster:
            logger.info(f"🖼️ Poster-style upload ({shape.width}x{shape.height}{', text' if shape.text_heavy else ''}): {url[:80]}")
    return shapes


def poster_urls(shapes: Dict[str, ImageShape]) -> List[str]:
    return [k for k, s in shapes.items() if s.poster]


def fit_transform(url: str) -> str:
    """A Cloudinary ``c_fill`` crop on a poster becomes ``c_fit`` so the
    whole image stays visible."""
    m = _CLOUDINARY_UPLOAD_RE.match((url or "").strip())
    if not m:
        return url
    rest = m.group(2)
    first = rest.split("/", 1)[0]
    if _TRANSFORM_SEGMENT_RE.match(first) and "c_fill" in first:
        first = first.replace("c_fill", "c_fit").replace(",g_auto", "")
        first = re.sub(r",?ar_[\d:.]+", "", first)
        return f"{m.group(1)}{first}/{rest.split('/', 1)[1]}"
    return url


def _menu_spans(html: str) -> List[Tuple[int, int]]:
    spans = []
    for m in _SECTION_OPEN_RE.finditer(html):
        if not _MENU_ID_RE.search(m.group(0)):
            continue
        depth = 0
        for mm in _SECTION_ANY_RE.finditer(html, m.start()):
            depth += -1 if mm.group(1) else 1
            if depth == 0:
                spans.append((m.start(), mm.end()))
                break
    return spans


def fix_poster_images(html: str, posters: Iterable[str]) -> Tuple[str, int]:
    """Every <img> showing a poster outside the menu section is shown whole:
    object-cover → object-contain (with a neutral backdrop), and a
    Cloudinary c_fill crop → c_fit. Returns (html, images changed)."""
    keys = {public_id_url(p) for p in posters if p}
    if not html or not keys:
        return html, 0
    menu_spans = _menu_spans(html)
    changed = 0

    def _sub(m: "re.Match") -> str:
        nonlocal changed
        tag = m.group(0)
        sm = _SRC_RE.search(tag)
        if not sm or public_id_url(sm.group(2)) not in keys:
            return tag
        if any(s <= m.start() < e for s, e in menu_spans):
            return tag
        new = tag.replace(sm.group(0), f'src={sm.group(1)}{fit_transform(sm.group(2))}{sm.group(1)}', 1)
        cm = _CLASS_RE.search(new)
        if cm:
            classes = re.sub(r"(?<![\w-])object-cover(?![\w-])", "object-contain", cm.group(2))
            if "object-contain" not in classes:
                classes += " object-contain"
            if not re.search(r"(?<![\w-])bg-", classes):
                classes += " bg-black/5"
            new = new.replace(cm.group(0), f"class={cm.group(1)}{classes.strip()}{cm.group(1)}", 1)
        else:
            new = new[:-1].rstrip("/") + ' class="object-contain bg-black/5">'
        if "data-binaapp-poster" not in new:
            new = new[:-1].rstrip("/") + ' data-binaapp-poster="1">'
        changed += 1
        return new

    out = _IMG_RE.sub(_sub, html)
    return out, changed
