"""Brand assets on the generated page: logo, favicon, theme colour.

The header on ayamgepukpaglima showed a fallback letter "A" box although
the merchant had a logo; the favicon was the same letter on a default
#111827 square, and the theme-color meta was #111827 too — the colour of
nothing on the page. Deterministic, idempotent, applied after generation:

* ``theme-color`` is the page's own primary colour.
* The favicon is the logo (Cloudinary-sized to 64px) when one was
  supplied, otherwise the brand primary with the business initial.
* When a logo was supplied it replaces the letter badge in the header and
  joins the brand text in the footer.

Pure string transforms; no I/O.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import quote

_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
_THEME_COLOR_RE = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']theme-color[\"'][^>]*>\s*", re.IGNORECASE)
_ICON_LINK_RE = re.compile(r"<link\b[^>]*\brel\s*=\s*[\"'](?:shortcut )?icon[\"'][^>]*>\s*|<link\b[^>]*\brel\s*=\s*[\"']apple-touch-icon[\"'][^>]*>\s*", re.IGNORECASE)
_HEADER_RE = re.compile(r"<(header|nav)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_FOOTER_RE = re.compile(r"<footer\b[^>]*>.*?</footer>", re.IGNORECASE | re.DOTALL)
_BADGE_RE = re.compile(r"<(span|div|a)\b([^>]*)>\s*([A-Za-z0-9])\s*</\1>", re.IGNORECASE)
_BRAND_LINK_RE = re.compile(r"<a\b[^>]*>(?:(?!</a>).)*?</a>", re.IGNORECASE | re.DOTALL)
_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_CLOUDINARY_UPLOAD_RE = re.compile(r"^(https?://res\.cloudinary\.com/[^/]+/image/upload/)(.+)$", re.IGNORECASE)
_TRANSFORM_SEGMENT_RE = re.compile(r"^(?:[a-z]{1,3}_[^/]+)(?:,[a-z]{1,3}_[^/]+)*$")


@dataclass
class BrandingReport:
    theme_color: str = ""
    favicon: str = ""   # "logo" | "initial" | ""
    logo_header: bool = False
    logo_footer: bool = False
    notes: List[str] = field(default_factory=list)

    def as_dict(self):
        return {"theme_color": self.theme_color, "favicon": self.favicon, "logo_header": self.logo_header, "logo_footer": self.logo_footer, "notes": list(self.notes)}


def _esc(s: str) -> str:
    return _html.escape(str(s or ""), quote=True)


def favicon_from_logo(logo_url: str, size: int = 64) -> str:
    """A square, PNG favicon rendering of the logo (Cloudinary transform);
    any other host's URL is used as-is."""
    m = _CLOUDINARY_UPLOAD_RE.match((logo_url or "").strip())
    if not m:
        return (logo_url or "").strip()
    rest = m.group(2)
    first = rest.split("/", 1)[0]
    if _TRANSFORM_SEGMENT_RE.match(first):
        rest = rest.split("/", 1)[1] if "/" in rest else rest
    return f"{m.group(1)}c_pad,w_{size},h_{size},b_auto,q_auto,f_png/{rest}"


def favicon_from_initial(business_name: str, primary: str) -> str:
    """An SVG data URI: the brand primary with the business initial, white
    or near-black text according to the primary's luminance."""
    initial = (business_name or "B").strip()[:1].upper() or "B"
    fill = primary if _HEX_RE.match(primary or "") else "#111827"
    text = "#ffffff" if _luminance(fill) < 0.55 else "#111827"
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
        f"<rect width='64' height='64' rx='14' fill='{fill}'/>"
        f"<text x='32' y='44' font-family='system-ui,sans-serif' font-size='36' font-weight='700' fill='{text}' text-anchor='middle'>{_esc(initial)}</text>"
        "</svg>"
    )
    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")


def _luminance(hex_value: str) -> float:
    h = hex_value.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 0.0

    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _logo_img(logo_url: str, business_name: str, height_class: str) -> str:
    return (
        f'<img src="{_esc(logo_url)}" alt="{_esc(business_name)}" '
        f'class="{height_class} w-auto object-contain" style="max-width:180px" decoding="async" data-binaapp-logo="1">'
    )


def _already_shows_logo(block: str, logo_url: str, business_name: str) -> bool:
    """The model rendered the logo itself (the prompt asks it to): an <img>
    with the logo's Cloudinary identity, or alt text = the business name."""
    from app.services.image_roles import same_image
    name_key = re.sub(r"\s+", " ", (business_name or "").strip().lower())
    for img in _IMG_RE.findall(block):
        src = re.search(r"\bsrc\s*=\s*([\"'])(.*?)\1", img, re.IGNORECASE)
        alt = re.search(r"\balt\s*=\s*([\"'])(.*?)\1", img, re.IGNORECASE)
        if src and same_image(src.group(2), logo_url):
            return True
        if alt and name_key and re.sub(r"\s+", " ", alt.group(2).strip().lower()) == name_key:
            return True
    return False


def _place_logo(block: str, logo_url: str, business_name: str, height_class: str) -> Tuple[str, bool]:
    """Replace a letter badge with the logo, else put the logo before the
    brand text inside the first link that carries the business name."""
    if "data-binaapp-logo" in block or _already_shows_logo(block, logo_url, business_name):
        return block, False
    initial = (business_name or "").strip()[:1].upper()
    img = _logo_img(logo_url, business_name, height_class)
    done = False

    def _badge(m: "re.Match") -> str:
        nonlocal done
        if done or m.group(3).upper() != initial:
            return m.group(0)
        done = True
        return img

    out = _BADGE_RE.sub(_badge, block)
    if done:
        return out, True
    name_key = re.sub(r"\s+", " ", (business_name or "").strip().lower())

    def _link(m: "re.Match") -> str:
        nonlocal done
        if done:
            return m.group(0)
        text = re.sub(r"\s+", " ", _TAG_RE.sub(" ", m.group(0))).strip().lower()
        if name_key and name_key in text and not _IMG_RE.search(m.group(0)):
            done = True
            open_end = m.group(0).index(">") + 1
            return m.group(0)[:open_end] + img + m.group(0)[open_end:]
        return m.group(0)

    out = _BRAND_LINK_RE.sub(_link, out)
    return out, done


def apply_branding(
    html: str,
    *,
    business_name: str,
    primary: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> Tuple[str, BrandingReport]:
    report = BrandingReport()
    if not html:
        return html, report
    out = html
    primary = (primary or "").strip()
    if not _HEX_RE.match(primary):
        primary = ""
    logo_url = (logo_url or "").strip()

    head_bits: List[str] = []
    if primary:
        out = _THEME_COLOR_RE.sub("", out)
        head_bits.append(f'<meta name="theme-color" content="{_esc(primary)}">')
        report.theme_color = primary
    if logo_url or primary:
        out = _ICON_LINK_RE.sub("", out)
        if logo_url:
            fav = favicon_from_logo(logo_url)
            head_bits.append(f'<link rel="icon" href="{_esc(fav)}">')
            head_bits.append(f'<link rel="apple-touch-icon" href="{_esc(favicon_from_logo(logo_url, 180))}">')
            report.favicon = "logo"
        else:
            head_bits.append(f'<link rel="icon" href="{favicon_from_initial(business_name, primary)}">')
            report.favicon = "initial"
    if head_bits:
        m = _HEAD_CLOSE_RE.search(out)
        inject = "\n".join(head_bits) + "\n"
        out = out[: m.start()] + inject + out[m.start():] if m else inject + out

    if logo_url:
        hm = _HEADER_RE.search(out)
        if hm:
            block, placed = _place_logo(hm.group(0), logo_url, business_name, "h-10 md:h-12")
            if placed:
                out = out[: hm.start()] + block + out[hm.end():]
                report.logo_header = True
            else:
                report.notes.append("header: no badge or brand link found for the logo")
        fm = _FOOTER_RE.search(out)
        if fm and "data-binaapp-logo" not in fm.group(0) and not _already_shows_logo(fm.group(0), logo_url, business_name):
            block, placed = _place_logo(fm.group(0), logo_url, business_name, "h-8")
            if not placed:
                # No brand link in the footer: put the logo before the first
                # element that carries the business name.
                name_key = re.sub(r"\s+", " ", business_name.strip().lower())
                # Leaf elements only (no nested block inside), so the logo
                # lands beside the brand text, not before the whole grid.
                for lm in re.finditer(r"<(p|span|h[1-6]|div)\b[^>]*>(?:(?!<(?:div|p|ul|section)\b).)*?</\1>", block, re.IGNORECASE | re.DOTALL):
                    text = re.sub(r"\s+", " ", _TAG_RE.sub(" ", lm.group(0))).strip().lower()
                    if name_key and name_key in text:
                        block = block[: lm.start()] + _logo_img(logo_url, business_name, "h-8") + "\n" + block[lm.start():]
                        placed = True
                        break
            if placed:
                out = out[: fm.start()] + block + out[fm.end():]
                report.logo_footer = True
    return out, report
