"""Printable menu/price-list, review QR and WhatsApp-order QR for a site.

The rest of the "everything a shop pins to a wall" family (see
``qr_service``, ``promo_kit``, ``share_card``). Same rules throughout:
rendered offline, free, themed with the page's own palette, and built only
from data the merchant already gave us.

* **Menu poster** — an A4 price list from the merchant's real menu. Items
  come from the ``menu_items`` table when the site manages its menu there,
  falling back to the ``deliveryMenuData`` array baked into the published
  page. When a price changes, the next print is already correct — no
  designer, no regeneration.
* **Review poster** — "beri kami 5 bintang": a QR pointing at the
  merchant's own Google review link. Reviews are the cheapest growth lever
  a local business has, and the poster is how you ask without asking.
* **WhatsApp order poster** — a QR that opens WhatsApp with the order
  message already typed, optionally tagged with a table number. The phone
  number is read from the merchant's own page (same rule as the vCard
  poster): we never print a number their site does not show.
"""

from __future__ import annotations

import html as _html
import json
import re
from typing import Dict, List, Optional
from urllib.parse import quote

from app.services.promo_kit import _poster_shell, _safe_color, _on_primary
from app.services.qr_service import qr_svg, remote_qr_url

# ---------------------------------------------------------------------------
# Menu sources
# ---------------------------------------------------------------------------

_MENU_VAR_RE = re.compile(r"deliveryMenuData\s*=\s*\[")


def _scan_json_array(text: str, start: int) -> Optional[str]:
    """The complete ``[...]`` starting at ``start``, respecting strings.

    A regex with a lazy ``\\]`` would stop at the first ``]`` inside a
    description; depth-tracking cannot.
    """
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def parse_menu_from_html(page_html: str) -> List[Dict]:
    """Menu items from the ``deliveryMenuData`` array baked into the page.

    Returns ``[]`` rather than guessing when the array is absent or broken.
    """
    if not page_html:
        return []
    match = _MENU_VAR_RE.search(page_html)
    if not match:
        return []
    raw = _scan_json_array(page_html, match.end() - 1)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    items: List[Dict] = []
    for entry in data if isinstance(data, list) else []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        items.append(
            {
                "name": name,
                "price": entry.get("price"),
                "description": str(entry.get("description") or "").strip(),
                "category": str(entry.get("category") or "").strip(),
                "is_popular": bool(entry.get("is_popular") or entry.get("popular")),
            }
        )
    return items


def normalize_db_menu(rows: Optional[List[Dict]]) -> List[Dict]:
    """``menu_items`` table rows in the same shape ``parse_menu_from_html`` emits.

    Unavailable items are dropped — a printed menu advertising something the
    kitchen stopped serving is worse than a shorter menu.
    """
    items: List[Dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if row.get("is_available") is False:
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        items.append(
            {
                "name": name,
                "price": row.get("price"),
                "description": str(row.get("description") or "").strip(),
                "category": str(row.get("category_name") or row.get("category") or "").strip(),
                "is_popular": bool(row.get("is_popular")),
            }
        )
    return items


def format_price(value) -> str:
    """``12.5`` / ``"12.50"`` / ``"RM 12.50"`` → ``"RM 12.50"``; unparseable → as-is."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    match = re.search(r"(\d+(?:[.,]\d{1,2})?)", text)
    if not match:
        return _html.escape(text)
    try:
        amount = float(match.group(1).replace(",", "."))
    except ValueError:
        return _html.escape(text)
    return f"RM {amount:,.2f}"


def group_by_category(items: List[Dict]) -> List[tuple]:
    """``[(category, [items...]), ...]`` preserving first-seen order."""
    grouped: Dict[str, List[Dict]] = {}
    order: List[str] = []
    for item in items:
        key = item.get("category") or ""
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(item)
    return [(key, grouped[key]) for key in order]


# ---------------------------------------------------------------------------
# Menu poster
# ---------------------------------------------------------------------------

_MENU_POSTER_TEMPLATE = """<!DOCTYPE html>
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
    justify-content: center;
    padding: 24px;
  }}
  .poster {{
    width: 210mm;
    min-height: 297mm;
    max-width: 100%;
    background: {surface};
    border-radius: 18px;
    box-shadow: 0 24px 60px rgba(0,0,0,.12);
    padding: 16mm 14mm;
    display: flex;
    flex-direction: column;
  }}
  header {{ text-align: center; margin-bottom: 8mm; }}
  .kicker {{
    display: inline-block;
    padding: 7px 18px;
    border-radius: 999px;
    background: {primary};
    color: {on_primary};
    font-size: 14px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
  }}
  h1 {{
    margin: 6mm 0 0;
    font-size: clamp(28px, 5vw, 44px);
    line-height: 1.1;
    font-weight: 800;
  }}
  .menu {{ columns: 2; column-gap: 12mm; }}
  .category {{ break-inside: avoid; margin-bottom: 7mm; }}
  .category h2 {{
    font-size: 19px;
    font-weight: 800;
    color: {primary};
    border-bottom: 2px solid {primary};
    padding-bottom: 2mm;
    margin: 0 0 3mm;
    letter-spacing: .02em;
    text-transform: uppercase;
  }}
  .item {{ margin-bottom: 3.2mm; break-inside: avoid; }}
  .row {{
    display: flex;
    align-items: baseline;
    gap: 6px;
    font-size: 15.5px;
    font-weight: 600;
  }}
  .row .dots {{
    flex: 1;
    border-bottom: 2px dotted {text_muted};
    opacity: .45;
    transform: translateY(-3px);
  }}
  .row .price {{ font-weight: 800; color: {primary}; white-space: nowrap; }}
  .desc {{ font-size: 12.5px; color: {text_muted}; margin-top: 1px; }}
  .star {{ color: {primary}; }}
  footer {{
    margin-top: auto;
    padding-top: 6mm;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8mm;
    border-top: 1px solid {text_muted}33;
  }}
  .site {{ font-size: 15px; font-weight: 700; color: {primary}; word-break: break-all; }}
  .foot-note {{ font-size: 11.5px; color: {text_muted}; }}
  .qr {{ background: #fff; padding: 6px; border-radius: 10px; border: 2px solid {primary}; line-height: 0; }}
  .qr svg {{ width: 24mm; height: 24mm; display: block; }}
  .print-bar {{ position: fixed; top: 16px; right: 16px; }}
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
  <header>
    <span class="kicker">{kicker}</span>
    <h1>{business_name}</h1>
  </header>
  <div class="menu">{sections}</div>
  <footer>
    <div>
      <div class="site">{display_url}</div>
      <div class="foot-note">{foot}</div>
    </div>
    <div class="qr">{qr_svg}</div>
  </footer>
</div>
</body>
</html>
"""


def build_menu_poster_html(
    business_name: str,
    items: List[Dict],
    url: str,
    palette: Optional[dict] = None,
    language: str = "ms",
) -> str:
    """A print-ready A4 menu / price list in the site's own colours.

    Works for any business: a cafe's menu and a salon's service list are the
    same shape — name, optional description, price.
    """
    palette = palette or {}
    is_ms = (language or "ms").lower().startswith("ms")
    primary = _safe_color(palette.get("primary"), "#EA580C")

    sections_html = []
    default_label = "Menu" if is_ms else "Menu"
    for category, group in group_by_category(items):
        rows = []
        for item in group:
            star = ' <span class="star">★</span>' if item.get("is_popular") else ""
            price = format_price(item.get("price"))
            desc = (
                f'<div class="desc">{_html.escape(item["description"][:140])}</div>'
                if item.get("description")
                else ""
            )
            rows.append(
                '<div class="item"><div class="row">'
                f"<span>{_html.escape(item['name'])}{star}</span>"
                '<span class="dots"></span>'
                f'<span class="price">{price}</span>'
                f"</div>{desc}</div>"
            )
        sections_html.append(
            '<section class="category">'
            f"<h2>{_html.escape(category or default_label)}</h2>"
            f"{''.join(rows)}</section>"
        )

    display_url = re.sub(r"^https?://", "", url or "").rstrip("/")
    svg = qr_svg(url, scale=4, border=2, dark=_safe_color(palette.get("text"), "#111827"), light="#FFFFFF", standalone=False)
    if not svg:
        svg = (
            f'<img src="{_html.escape(remote_qr_url(url, size=140), quote=True)}" '
            f'alt="QR" width="90" height="90" style="display:block">'
        )

    return _MENU_POSTER_TEMPLATE.format(
        lang="ms" if is_ms else "en",
        title=_html.escape(f"{business_name} — Menu"),
        business_name=_html.escape(business_name or ""),
        kicker="Menu &amp; Harga" if is_ms else "Menu &amp; Prices",
        sections="".join(sections_html),
        display_url=_html.escape(display_url),
        qr_svg=svg,
        print_label="🖨️ Cetak" if is_ms else "🖨️ Print",
        foot=_html.escape(
            "Imbas QR untuk menu terkini · Dijana oleh BinaApp"
            if is_ms
            else "Scan the QR for the latest menu · Made with BinaApp"
        ),
        primary=primary,
        on_primary=_on_primary(primary),
        surface=_safe_color(palette.get("surface"), "#FFFFFF"),
        background=_safe_color(palette.get("background"), "#F8FAFC"),
        text=_safe_color(palette.get("text"), "#111827"),
        text_muted=_safe_color(palette.get("text_muted"), "#6B7280"),
    )


# ---------------------------------------------------------------------------
# Review poster
# ---------------------------------------------------------------------------

#: Hosts a Google review/business link legitimately lives on. The poster is
#: owner-only, but a printed QR is trusted by whoever scans it — restricting
#: the target keeps "beri kami 5 bintang" posters pointing at review pages,
#: not at arbitrary URLs wearing our layout.
_REVIEW_URL_RE = re.compile(
    r"^https://("
    # google.com / google.com.my / google.co.uk — TLD labels anchored so
    # google.evil.com can never pass as a "google" host.
    r"(www\.)?google(\.[a-z]{2,3}){1,2}/|"
    r"g\.page/|"
    r"g\.co/|"
    r"maps\.app\.goo\.gl/|"
    r"search\.google\.com/"
    r")",
    re.IGNORECASE,
)


def is_valid_review_url(url: str) -> bool:
    return bool(url) and len(url) <= 500 and bool(_REVIEW_URL_RE.match(url.strip()))


def build_review_poster_html(
    business_name: str,
    review_url: str,
    palette: Optional[dict] = None,
    language: str = "ms",
) -> str:
    """A4 poster asking for a Google review, QR straight to the review page."""
    return _poster_shell(
        business_name=business_name,
        payload=review_url,
        palette=palette,
        language=language,
        kicker_ms="Beri Kami 5 Bintang",
        kicker_en="Rate Us 5 Stars",
        headline_ms="Suka pengalaman anda? Ulasan Google anda membantu kedai kecil seperti kami berkembang.",
        headline_en="Enjoyed your visit? Your Google review helps a small business like ours grow.",
        steps_ms=[
            ("1. Buka kamera", "Halakan kamera telefon ke kod QR di atas."),
            ("2. Ketik pautan", "Halaman ulasan Google kami akan terbuka."),
            ("3. Beri bintang", "Tulis satu-dua ayat — 30 saat sahaja. Terima kasih!"),
        ],
        steps_en=[
            ("1. Open your camera", "Point your phone's camera at the QR code above."),
            ("2. Tap the link", "Our Google review page opens."),
            ("3. Leave a rating", "A sentence or two — 30 seconds. Thank you!"),
        ],
        details_html="",
    )


# ---------------------------------------------------------------------------
# WhatsApp order poster
# ---------------------------------------------------------------------------

def build_wa_link(phone: str, message: str) -> str:
    """``https://wa.me/<digits>?text=<encoded>`` from an E.164-ish number."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    link = f"https://wa.me/{digits}"
    if message:
        link += f"?text={quote(message, safe='')}"
    return link


def default_order_message(
    business_name: str, table: Optional[str] = None, language: str = "ms"
) -> str:
    is_ms = (language or "ms").lower().startswith("ms")
    if is_ms:
        base = f"Hai {business_name}! Saya nak buat pesanan."
        return f"{base} (Meja {table})" if table else base
    base = f"Hi {business_name}! I'd like to place an order."
    return f"{base} (Table {table})" if table else base


def build_whatsapp_poster_html(
    business_name: str,
    phone: str,
    palette: Optional[dict] = None,
    language: str = "ms",
    table: Optional[str] = None,
    message: Optional[str] = None,
) -> str:
    """A4 poster: scan → WhatsApp opens with the order message already typed.

    The table variant is the dine-in flow: one poster per table, and every
    incoming chat says which table it came from.
    """
    is_ms = (language or "ms").lower().startswith("ms")
    text = (message or "").strip() or default_order_message(
        business_name, table, language
    )
    link = build_wa_link(phone, text)

    if table:
        kicker_ms, kicker_en = f"Pesan · Meja {table}", f"Order · Table {table}"
    else:
        kicker_ms, kicker_en = "Pesan Melalui WhatsApp", "Order on WhatsApp"

    phone_label = "WhatsApp" if is_ms else "WhatsApp"
    details = (
        f'<p class="detail"><small>{phone_label}</small>{_html.escape(phone)}</p>'
    )

    return _poster_shell(
        business_name=business_name,
        payload=link,
        palette=palette,
        language=language,
        kicker_ms=kicker_ms,
        kicker_en=kicker_en,
        headline_ms="Imbas — WhatsApp terbuka dengan mesej pesanan siap ditaip.",
        headline_en="Scan — WhatsApp opens with your order message already typed.",
        steps_ms=[
            ("1. Buka kamera", "Halakan kamera telefon ke kod QR di atas."),
            ("2. Ketik pautan", "WhatsApp terbuka — mesej sudah siap ditaip."),
            ("3. Hantar", "Tambah pesanan anda dan tekan hantar. Siap!"),
        ],
        steps_en=[
            ("1. Open your camera", "Point your phone's camera at the QR code above."),
            ("2. Tap the link", "WhatsApp opens with the message pre-typed."),
            ("3. Send", "Add your order and hit send. Done!"),
        ],
        details_html=details,
    )
