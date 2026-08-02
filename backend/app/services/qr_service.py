"""Offline QR generation for published sites — codes and printable posters.

WHY THIS EXISTS
---------------
Every published BinaApp page carried a QR image loaded from
``api.qrserver.com``. That put a third-party request on the critical render
path of every merchant's site: their footer QR breaks when that service is
slow, rate-limits, or disappears, and every visitor's IP plus the merchant's
URL is handed to an unrelated host on every pageview.

QR encoding is a solved, offline problem. This module renders the code
locally as an SVG (crisp at any print size, a few hundred bytes) so the
footer QR becomes a self-contained part of the page.

It also builds the thing merchants actually asked for: a **printable
poster** — the shop-counter standee / table tent / flyer insert, themed with
the site's own palette, in Bahasa Melayu, ready for A4.

DEGRADATION
-----------
``segno`` is a pure-Python, zero-dependency encoder. If it is somehow absent
at runtime, :func:`qr_svg` returns ``""`` and callers fall back to the old
remote-image URL via :func:`remote_qr_url` — a missing QR must never take a
merchant's page down with it.
"""

from __future__ import annotations

import base64
import html as _html
import io
import logging
import re
from functools import lru_cache
from typing import Optional
from urllib.parse import quote, urlencode, urlparse, urlunparse, parse_qsl

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised by the ImportError branch in tests
    import segno

    SEGNO_AVAILABLE = True
except ImportError:  # pragma: no cover
    segno = None
    SEGNO_AVAILABLE = False
    logger.warning("⚠️ segno not installed — QR codes fall back to the remote renderer")

#: Error-correction level. 'm' (~15% recoverable) is the sweet spot for a
#: printed poster: it survives a scuffed corner without inflating the module
#: count enough to hurt scanning from across a shop.
_ERROR_LEVEL = "m"

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _safe_color(value: Optional[str], fallback: str) -> str:
    """Only real hex colours reach the SVG — never caller-controlled text."""
    candidate = (value or "").strip()
    if candidate and not candidate.startswith("#"):
        candidate = "#" + candidate
    return candidate if _HEX_RE.match(candidate) else fallback


def build_site_url(
    subdomain: str,
    main_domain: str,
    table: Optional[str] = None,
    campaign: Optional[str] = None,
) -> str:
    """The URL a QR should encode for ``subdomain``.

    ``table`` and ``campaign`` are carried as query markers (``?meja=5``,
    ``?kempen=raya``). They make each printed code a DISTINCT URL, which is
    the point: one QR per table or per flyer batch. The page itself ignores
    unknown params, so this is always safe.
    """
    if not subdomain:
        return ""
    base = f"https://{subdomain}.{main_domain}".rstrip("/")
    params = []
    if table:
        params.append(("meja", str(table)))
    if campaign:
        params.append(("kempen", str(campaign)))
    if not params:
        return base
    return f"{base}/?{urlencode(params)}"


def with_query(url: str, **params: str) -> str:
    """Add query params to an arbitrary URL without dropping existing ones."""
    if not url:
        return ""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update({k: str(v) for k, v in params.items() if v not in (None, "")})
    return urlunparse(parsed._replace(query=urlencode(query)))


def remote_qr_url(data: str, size: int = 200) -> str:
    """The legacy remote renderer — only used when segno is unavailable."""
    return (
        f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data="
        + quote(data or "", safe="")
    )


def qr_svg(
    data: str,
    scale: int = 6,
    border: int = 2,
    dark: str = "#111827",
    light: str = "#FFFFFF",
    standalone: bool = True,
) -> str:
    """Render ``data`` as an SVG QR code.

    ``standalone=True`` includes the ``xmlns`` attribute (needed when the SVG
    is served as its own file or used in ``<img src>``); ``False`` returns the
    inline form for embedding directly in an HTML document.

    Returns ``""`` when the payload is empty or segno is unavailable — callers
    must treat an empty string as "no QR available".
    """
    if not data or not SEGNO_AVAILABLE:
        return ""

    dark_color = _safe_color(dark, "#111827")
    light_color = _safe_color(light, "#FFFFFF")
    scale = max(1, min(int(scale or 6), 40))
    border = max(0, min(int(border or 0), 16))

    try:
        code = segno.make(data, error=_ERROR_LEVEL)
        if not standalone:
            return code.svg_inline(
                scale=scale, border=border, dark=dark_color, light=light_color
            )
        buffer = io.BytesIO()
        code.save(
            buffer,
            kind="svg",
            scale=scale,
            border=border,
            dark=dark_color,
            light=light_color,
            xmldecl=False,
            svgclass=None,
            lineclass=None,
        )
        return buffer.getvalue().decode("utf-8")
    except Exception as exc:  # pragma: no cover - encoder should not fail
        logger.error(f"QR render failed for payload of {len(data)} chars: {exc}")
        return ""


@lru_cache(maxsize=512)
def qr_data_uri(
    data: str,
    scale: int = 6,
    border: int = 2,
    dark: str = "#111827",
    light: str = "#FFFFFF",
) -> str:
    """Base64 ``data:`` URI of the SVG, for use in ``<img src>``.

    Base64 (rather than segno's percent-encoded form) so the URI is safe to
    drop into an HTML attribute without any further escaping.

    Cached: the subdomain serve path inlines this on EVERY pageview, and the
    payload only changes when the subdomain does. Pure function of its
    arguments, so the cache can never serve someone else's code.
    """
    svg = qr_svg(data, scale=scale, border=border, dark=dark, light=light)
    if not svg:
        return ""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


# ---------------------------------------------------------------------------
# Printable poster
# ---------------------------------------------------------------------------

_POSTER_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", sans-serif;
    background: {background};
    color: {text};
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 24px;
  }}
  .poster {{
    width: 210mm;
    min-height: 297mm;
    max-width: 100%;
    background: {surface};
    border-radius: 18px;
    box-shadow: 0 24px 60px rgba(0,0,0,.12);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 18mm 14mm;
    gap: 6mm;
  }}
  .kicker {{
    display: inline-block;
    padding: 8px 20px;
    border-radius: 999px;
    background: {primary};
    color: {on_primary};
    font-size: 15px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
  }}
  h1 {{
    margin: 0;
    font-size: clamp(30px, 6vw, 54px);
    line-height: 1.08;
    font-weight: 800;
    text-wrap: balance;
  }}
  .headline {{
    margin: 0;
    font-size: clamp(18px, 3.2vw, 26px);
    color: {text_muted};
    max-width: 34ch;
    text-wrap: balance;
  }}
  .qr-frame {{
    background: #FFFFFF;
    padding: 18px;
    border-radius: 20px;
    border: 3px solid {primary};
    line-height: 0;
  }}
  .qr-frame svg {{ width: 74mm; height: 74mm; display: block; }}
  .url {{
    font-size: 20px;
    font-weight: 700;
    color: {primary};
    word-break: break-all;
    max-width: 32ch;
  }}
  .steps {{
    display: flex;
    gap: 10mm;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 2mm;
  }}
  .step {{ max-width: 22ch; font-size: 15px; color: {text_muted}; }}
  .step b {{ display: block; color: {text}; font-size: 17px; margin-bottom: 4px; }}
  .foot {{ margin-top: auto; font-size: 13px; color: {text_muted}; }}
  .print-bar {{
    position: fixed; top: 16px; right: 16px; display: flex; gap: 8px;
  }}
  .print-bar button {{
    font: inherit; font-size: 14px; font-weight: 600; cursor: pointer;
    padding: 10px 18px; border-radius: 999px; border: 0;
    background: {primary}; color: {on_primary};
    box-shadow: 0 6px 18px rgba(0,0,0,.18);
  }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .poster {{ box-shadow: none; border-radius: 0; width: 100%; min-height: 100vh; }}
    .print-bar {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="print-bar"><button onclick="window.print()">{print_label}</button></div>
<div class="poster">
  <span class="kicker">{kicker}</span>
  <h1>{business_name}</h1>
  <p class="headline">{headline}</p>
  <div class="qr-frame">{qr_svg}</div>
  <p class="url">{display_url}</p>
  <div class="steps">{steps}</div>
  <p class="foot">{foot}</p>
</div>
</body>
</html>
"""

_STEPS_MS = [
    ("1. Buka kamera", "Halakan kamera telefon ke kod QR di atas."),
    ("2. Ketik pautan", "Laman web kami akan terbuka terus — tiada app perlu dipasang."),
    ("3. Terus pesan", "Lihat menu, harga dan hubungi kami melalui WhatsApp."),
]

_STEPS_EN = [
    ("1. Open your camera", "Point your phone's camera at the QR code above."),
    ("2. Tap the link", "Our website opens straight away — no app to install."),
    ("3. Order away", "Browse the menu and prices, then message us on WhatsApp."),
]


def _on_primary(primary: str) -> str:
    """Black or white text, whichever stays readable on ``primary``."""
    from app.services.theme_patcher import contrast_ratio

    return "#FFFFFF" if contrast_ratio("#FFFFFF", primary) >= 4.5 else "#111827"


def build_poster_html(
    business_name: str,
    url: str,
    palette: Optional[dict] = None,
    language: str = "ms",
    table: Optional[str] = None,
    headline: Optional[str] = None,
) -> str:
    """A print-ready A4 poster carrying the site's QR, in the site's colours.

    Everything on it comes from the merchant's own data — business name, real
    published URL, real palette. No invented taglines, ratings or badges.
    """
    palette = palette or {}
    primary = _safe_color(palette.get("primary"), "#EA580C")
    surface = _safe_color(palette.get("surface"), "#FFFFFF")
    background = _safe_color(palette.get("background"), "#F8FAFC")
    text = _safe_color(palette.get("text"), "#111827")
    text_muted = _safe_color(palette.get("text_muted"), "#6B7280")

    is_ms = (language or "ms").lower().startswith("ms")
    svg = qr_svg(url, scale=8, border=2, dark=text, light="#FFFFFF", standalone=False)
    if not svg:
        svg = (
            f'<img src="{_html.escape(remote_qr_url(url, size=400), quote=True)}" '
            f'alt="QR" width="280" height="280" style="display:block">'
        )

    if table:
        kicker = f"Imbas & Pesan · Meja {table}" if is_ms else f"Scan & Order · Table {table}"
        default_headline = (
            "Lihat menu penuh dan buat pesanan terus dari telefon anda."
            if is_ms
            else "See the full menu and order straight from your phone."
        )
    else:
        kicker = "Imbas Untuk Lawat" if is_ms else "Scan To Visit"
        default_headline = (
            "Menu, harga dan cara hubungi kami — semua di satu tempat."
            if is_ms
            else "Menu, prices and how to reach us — all in one place."
        )

    steps = "".join(
        f'<div class="step"><b>{_html.escape(title)}</b>{_html.escape(body)}</div>'
        for title, body in (_STEPS_MS if is_ms else _STEPS_EN)
    )

    display_url = re.sub(r"^https?://", "", url or "").rstrip("/")

    return _POSTER_TEMPLATE.format(
        lang="ms" if is_ms else "en",
        title=_html.escape(f"{business_name} — QR"),
        business_name=_html.escape(business_name or ""),
        headline=_html.escape(headline or default_headline),
        kicker=_html.escape(kicker),
        display_url=_html.escape(display_url),
        qr_svg=svg,
        steps=steps,
        print_label="🖨️ Cetak" if is_ms else "🖨️ Print",
        foot=_html.escape(
            "Dijana oleh BinaApp" if is_ms else "Made with BinaApp"
        ),
        primary=primary,
        on_primary=_on_primary(primary),
        surface=surface,
        background=background,
        text=text,
        text_muted=text_muted,
    )
