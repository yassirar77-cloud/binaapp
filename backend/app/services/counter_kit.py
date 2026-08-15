"""Counter Kit — loyalty stamp cards, business cards, vouchers, closure notice.

The fourth member of the "everything a shop pins to a wall (or hands over
the counter)" family (see ``qr_service``, ``promo_kit``, ``business_kit``).
Same contract throughout: rendered offline, free, themed with the page's own
palette, and built only from data the merchant already gave us.

* **Kad setia** (loyalty stamp cards) — an A4 sheet of eight wallet-size
  stamp cards: buy N, get the reward. The stamp count and reward line are
  the merchant's choice; the chop/marker pen is theirs too. Loyalty cards
  are the cheapest repeat-visit lever a stall has, and print shops charge
  RM80+ for a design like this.
* **Kad nama** (business cards) — an A4 sheet of ten standard-size
  (90×54 mm) business cards: name, tagline, phone and a QR to the site.
  The phone number comes from the merchant's own page — we never print a
  number their site does not show.
* **Baucar** (voucher sheet) — an A4 sheet of six cut-out vouchers with the
  merchant's offer, an optional code and expiry. Handed out with orders,
  they bring the customer back.
* **Notis bercuti** (closure notice) — an A4 "we are closed for the
  holidays" poster with the return date and a QR to the site. Every kedai
  needs one twice a year; most end up as a biro note taped to the grille.
"""

from __future__ import annotations

import html as _html
import re
from typing import Optional

from app.services.promo_kit import _on_primary, _safe_color
from app.services.qr_service import qr_svg, remote_qr_url


def _is_ms(language: str) -> bool:
    return (language or "ms").lower().startswith("ms")


def _display_url(url: str) -> str:
    return re.sub(r"^https?://", "", url or "").rstrip("/")


def _site_qr(url: str, palette: dict) -> str:
    """A small offline QR block; remote <img> fallback mirrors the other kits."""
    svg = qr_svg(
        url,
        scale=4,
        border=2,
        dark=_safe_color(palette.get("text"), "#111827"),
        light="#FFFFFF",
        standalone=False,
    )
    if not svg:
        svg = (
            f'<img src="{_html.escape(remote_qr_url(url, size=140), quote=True)}" '
            f'alt="QR" width="90" height="90" style="display:block">'
        )
    return svg


_SHEET_TEMPLATE = """<!DOCTYPE html>
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
  .sheet {{
    width: 210mm;
    min-height: 297mm;
    max-width: 100%;
    background: {surface};
    border-radius: 18px;
    box-shadow: 0 24px 60px rgba(0,0,0,.12);
    padding: 10mm;
    display: flex;
    flex-direction: column;
  }}
  .sheet-note {{
    text-align: center;
    font-size: 11px;
    color: {text_muted};
    margin: 0 0 4mm;
  }}
  {extra_css}
  .print-bar {{ position: fixed; top: 16px; right: 16px; }}
  .print-bar button {{
    font: inherit; font-size: 14px; font-weight: 600; cursor: pointer;
    padding: 10px 18px; border-radius: 999px; border: 0;
    background: {primary}; color: {on_primary};
    box-shadow: 0 6px 18px rgba(0,0,0,.18);
  }}
  @media print {{
    body {{ background: #fff; padding: 0; }}
    .sheet {{ box-shadow: none; border-radius: 0; width: 100%; min-height: 100vh; }}
    .print-bar {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="print-bar"><button onclick="window.print()">{print_label}</button></div>
<div class="sheet">
  <p class="sheet-note">{sheet_note}</p>
  {body}
</div>
</body>
</html>
"""


def _sheet(
    title: str,
    body: str,
    extra_css: str,
    palette: dict,
    language: str,
    sheet_note: str,
) -> str:
    primary = _safe_color(palette.get("primary"), "#EA580C")
    return _SHEET_TEMPLATE.format(
        lang="ms" if _is_ms(language) else "en",
        title=_html.escape(title),
        body=body,
        extra_css=extra_css,
        sheet_note=_html.escape(sheet_note),
        print_label="🖨️ Cetak" if _is_ms(language) else "🖨️ Print",
        primary=primary,
        on_primary=_on_primary(primary),
        surface=_safe_color(palette.get("surface"), "#FFFFFF"),
        background=_safe_color(palette.get("background"), "#F8FAFC"),
        text=_safe_color(palette.get("text"), "#111827"),
        text_muted=_safe_color(palette.get("text_muted"), "#6B7280"),
    )


# ---------------------------------------------------------------------------
# 1. Loyalty stamp cards — "kad setia"
# ---------------------------------------------------------------------------

_LOYALTY_CSS = """
  .cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4mm;
  }
  .card {
    border: 1.5px dashed {text_muted};
    border-radius: 12px;
    padding: 6mm 6mm 5mm;
    height: 62mm;
    display: flex;
    flex-direction: column;
    break-inside: avoid;
  }
  .card .shop {
    font-size: 16px;
    font-weight: 800;
    color: {primary};
    line-height: 1.15;
  }
  .card .label {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {text_muted};
    margin-bottom: 3mm;
  }
  .stamps {
    display: flex;
    flex-wrap: wrap;
    gap: 2.6mm;
    margin: auto 0;
  }
  .stamp {
    width: 9.5mm;
    height: 9.5mm;
    border: 2px dashed {primary};
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    font-weight: 800;
    color: {primary};
    opacity: .85;
  }
  .stamp.gift {
    border-style: solid;
    background: {primary};
    color: {on_primary};
    opacity: 1;
    font-size: 13px;
  }
  .card .reward {
    font-size: 11.5px;
    font-weight: 600;
    color: {text};
    margin-top: 3mm;
  }
  .card .url {
    font-size: 9.5px;
    color: {text_muted};
    margin-top: 1mm;
    word-break: break-all;
  }
"""


def build_loyalty_card_html(
    business_name: str,
    url: str,
    stamps: int = 10,
    reward: Optional[str] = None,
    palette: Optional[dict] = None,
    language: str = "ms",
) -> str:
    """An A4 sheet of eight cut-out loyalty stamp cards.

    ``stamps`` is the full count including the reward stamp: buy N-1, the
    Nth is the gift. Any pen or chop marks a visit — no app, no account.
    """
    palette = palette or {}
    is_ms = _is_ms(language)
    stamps = max(4, min(20, int(stamps or 10)))

    if not (reward or "").strip():
        reward = (
            f"Cop penuh — pembelian ke-{stamps} PERCUMA!"
            if is_ms
            else f"Full card — your {_ordinal(stamps)} purchase is FREE!"
        )

    circles = "".join(
        '<span class="stamp gift">🎁</span>'
        if index == stamps - 1
        else f'<span class="stamp">{index + 1}</span>'
        for index in range(stamps)
    )
    card = (
        '<div class="card">'
        f'<div class="shop">{_html.escape(business_name or "")}</div>'
        f'<div class="label">{"Kad Setia" if is_ms else "Loyalty Card"}</div>'
        f'<div class="stamps">{circles}</div>'
        f'<div class="reward">{_html.escape(reward.strip()[:80])}</div>'
        f'<div class="url">{_html.escape(_display_url(url))}</div>'
        "</div>"
    )
    note = (
        "Gunting ikut garisan putus-putus — 8 kad setia setiap helaian A4."
        if is_ms
        else "Cut along the dashed lines — 8 loyalty cards per A4 sheet."
    )
    return _sheet(
        title=f"{business_name} — Kad Setia",
        body=f'<div class="cards">{card * 8}</div>',
        extra_css=_fill_css(_LOYALTY_CSS, palette),
        palette=palette,
        language=language,
        sheet_note=note,
    )


def _ordinal(number: int) -> str:
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _fill_css(css: str, palette: dict) -> str:
    """The per-kit CSS blocks use ``{token}`` placeholders like the shell."""
    primary = _safe_color(palette.get("primary"), "#EA580C")
    return (
        css.replace("{primary}", primary)
        .replace("{on_primary}", _on_primary(primary))
        .replace("{surface}", _safe_color(palette.get("surface"), "#FFFFFF"))
        .replace("{text_muted}", _safe_color(palette.get("text_muted"), "#6B7280"))
        .replace("{text}", _safe_color(palette.get("text"), "#111827"))
    )


# ---------------------------------------------------------------------------
# 2. Business cards — "kad nama"
# ---------------------------------------------------------------------------

_BUSINESS_CARD_CSS = """
  .cards {
    display: grid;
    grid-template-columns: repeat(2, 90mm);
    justify-content: center;
    gap: 4mm;
  }
  .card {
    border: 1.5px dashed {text_muted};
    border-radius: 10px;
    width: 90mm;
    height: 50mm;
    padding: 5mm 6mm;
    display: flex;
    align-items: center;
    gap: 5mm;
    break-inside: avoid;
  }
  .card .info { flex: 1; min-width: 0; }
  .card .shop {
    font-size: 16px;
    font-weight: 800;
    color: {primary};
    line-height: 1.15;
  }
  .card .tagline {
    font-size: 10px;
    color: {text_muted};
    margin-top: 1.5mm;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .card .contact {
    font-size: 10.5px;
    font-weight: 700;
    color: {text};
    margin-top: 2.5mm;
  }
  .card .url {
    font-size: 9.5px;
    font-weight: 600;
    color: {primary};
    word-break: break-all;
  }
  .card .qr {
    background: #fff;
    border: 1.5px solid {primary};
    border-radius: 8px;
    padding: 4px;
    line-height: 0;
    flex-shrink: 0;
  }
  .card .qr svg, .card .qr img { width: 20mm; height: 20mm; display: block; }
"""


def build_business_cards_html(
    business_name: str,
    url: str,
    phone: Optional[str] = None,
    tagline: Optional[str] = None,
    palette: Optional[dict] = None,
    language: str = "ms",
) -> str:
    """An A4 sheet of ten standard-size (90×50 mm) business cards.

    The QR opens the site — the card carries everything a lost customer
    needs to find the shop again. Phone and tagline are optional: a card
    without them is still a card.
    """
    palette = palette or {}
    is_ms = _is_ms(language)
    qr = _site_qr(url, palette)

    contact = (
        f'<div class="contact">{_html.escape(phone.strip())}</div>'
        if (phone or "").strip()
        else ""
    )
    tagline_html = (
        f'<div class="tagline">{_html.escape(tagline.strip()[:120])}</div>'
        if (tagline or "").strip()
        else ""
    )
    card = (
        '<div class="card">'
        '<div class="info">'
        f'<div class="shop">{_html.escape(business_name or "")}</div>'
        f"{tagline_html}{contact}"
        f'<div class="url">{_html.escape(_display_url(url))}</div>'
        "</div>"
        f'<div class="qr">{qr}</div>'
        "</div>"
    )
    note = (
        "Gunting ikut garisan putus-putus — 10 kad nama (90×50mm) setiap helaian A4."
        if is_ms
        else "Cut along the dashed lines — 10 business cards (90×50mm) per A4 sheet."
    )
    return _sheet(
        title=f"{business_name} — Kad Nama",
        body=f'<div class="cards">{card * 10}</div>',
        extra_css=_fill_css(_BUSINESS_CARD_CSS, palette),
        palette=palette,
        language=language,
        sheet_note=note,
    )


# ---------------------------------------------------------------------------
# 3. Voucher sheet — "baucar"
# ---------------------------------------------------------------------------

_VOUCHER_CSS = """
  .vouchers { display: flex; flex-direction: column; gap: 4mm; }
  .voucher {
    border: 1.5px dashed {text_muted};
    border-radius: 12px;
    padding: 5mm 7mm;
    display: flex;
    align-items: center;
    gap: 6mm;
    height: 40mm;
    break-inside: avoid;
    position: relative;
  }
  .voucher .scissors {
    position: absolute;
    top: -3.2mm;
    left: 10mm;
    font-size: 12px;
    color: {text_muted};
    background: {surface};
    padding: 0 2px;
  }
  .voucher .offer-block { flex: 1; min-width: 0; }
  .voucher .shop {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: {text_muted};
  }
  .voucher .offer {
    font-size: 26px;
    font-weight: 800;
    color: {primary};
    line-height: 1.1;
    margin: 1mm 0;
  }
  .voucher .terms { font-size: 9.5px; color: {text_muted}; }
  .voucher .code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px;
    font-weight: 700;
    color: {text};
    border: 1.5px solid {primary};
    border-radius: 8px;
    padding: 2.5mm 4mm;
    letter-spacing: .12em;
    white-space: nowrap;
  }
  .voucher .qr {
    background: #fff;
    border: 1.5px solid {primary};
    border-radius: 8px;
    padding: 4px;
    line-height: 0;
    flex-shrink: 0;
  }
  .voucher .qr svg, .voucher .qr img { width: 20mm; height: 20mm; display: block; }
"""


def build_voucher_sheet_html(
    business_name: str,
    url: str,
    offer: str,
    code: Optional[str] = None,
    expiry: Optional[str] = None,
    palette: Optional[dict] = None,
    language: str = "ms",
) -> str:
    """An A4 sheet of six cut-out vouchers carrying the merchant's offer.

    ``offer`` is printed exactly as the merchant wrote it ("10% OFF",
    "Teh tarik percuma") — we never invent a promotion. ``code`` and
    ``expiry`` are optional decorations; redemption is between the merchant
    and the customer at the counter.
    """
    palette = palette or {}
    is_ms = _is_ms(language)
    qr = _site_qr(url, palette)

    terms_bits = []
    if (expiry or "").strip():
        prefix = "Sah sehingga" if is_ms else "Valid until"
        terms_bits.append(f"{prefix} {expiry.strip()[:40]}")
    terms_bits.append(
        "Satu baucar untuk satu pelanggan. Tunjukkan baucar ini di kaunter."
        if is_ms
        else "One voucher per customer. Show this voucher at the counter."
    )
    code_html = (
        f'<div class="code">{_html.escape(code.strip()[:24].upper())}</div>'
        if (code or "").strip()
        else ""
    )
    voucher = (
        '<div class="voucher">'
        '<span class="scissors">✂</span>'
        '<div class="offer-block">'
        f'<div class="shop">{_html.escape(business_name or "")}</div>'
        f'<div class="offer">{_html.escape(offer.strip()[:60])}</div>'
        f'<div class="terms">{_html.escape(" · ".join(terms_bits))}</div>'
        "</div>"
        f"{code_html}"
        f'<div class="qr">{qr}</div>'
        "</div>"
    )
    note = (
        "Gunting dan edarkan bersama setiap pesanan — 6 baucar setiap helaian A4."
        if is_ms
        else "Cut out and hand one out with every order — 6 vouchers per A4 sheet."
    )
    return _sheet(
        title=f"{business_name} — Baucar",
        body=f'<div class="vouchers">{voucher * 6}</div>',
        extra_css=_fill_css(_VOUCHER_CSS, palette),
        palette=palette,
        language=language,
        sheet_note=note,
    )


# ---------------------------------------------------------------------------
# 4. Closure notice — "notis bercuti"
# ---------------------------------------------------------------------------

_CLOSURE_TEMPLATE = """<!DOCTYPE html>
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
    gap: 7mm;
  }}
  .kicker {{
    display: inline-block;
    margin-top: auto;
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
    font-size: clamp(34px, 7vw, 60px);
    line-height: 1.05;
    font-weight: 800;
    text-wrap: balance;
  }}
  .note {{
    margin: 0;
    font-size: clamp(18px, 3.2vw, 26px);
    color: {text_muted};
    max-width: 34ch;
    text-wrap: balance;
  }}
  .dates {{
    border: 3px solid {primary};
    border-radius: 18px;
    padding: 8mm 14mm;
    display: flex;
    flex-direction: column;
    gap: 3mm;
  }}
  .dates .row small {{
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: {text_muted};
    letter-spacing: .08em;
    text-transform: uppercase;
    margin-bottom: 1mm;
  }}
  .dates .row {{ font-size: 26px; font-weight: 800; color: {primary}; }}
  .qr-line {{
    display: flex;
    align-items: center;
    gap: 6mm;
    margin-top: 2mm;
  }}
  .qr-frame {{
    background: #FFFFFF;
    padding: 10px;
    border-radius: 14px;
    border: 3px solid {primary};
    line-height: 0;
  }}
  .qr-frame svg, .qr-frame img {{ width: 34mm; height: 34mm; display: block; }}
  .qr-copy {{ text-align: left; max-width: 26ch; font-size: 15px; color: {text_muted}; }}
  .qr-copy b {{ display: block; color: {text}; font-size: 17px; margin-bottom: 2px; }}
  .foot {{ margin-top: auto; font-size: 13px; color: {text_muted}; }}
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
  <span class="kicker">{kicker}</span>
  <h1>{headline}</h1>
  <p class="note">{note}</p>
  <div class="dates">{dates}</div>
  <div class="qr-line">
    <div class="qr-frame">{qr_svg}</div>
    <div class="qr-copy"><b>{qr_title}</b>{qr_body}</div>
  </div>
  <p class="foot">{foot}</p>
</div>
</body>
</html>
"""


def build_closure_poster_html(
    business_name: str,
    url: str,
    reopen: str,
    closed_from: Optional[str] = None,
    note: Optional[str] = None,
    palette: Optional[dict] = None,
    language: str = "ms",
) -> str:
    """A4 "we are on holiday" notice: dates, a greeting, a QR to the site.

    Dates are printed exactly as the merchant typed them ("2 Jun", "selepas
    Raya") — a free-text field beats a date picker for the way kedai actually
    announce closures. The QR matters: a closed door is the one time a
    customer genuinely needs the website.
    """
    palette = palette or {}
    is_ms = _is_ms(language)

    rows = []
    if (closed_from or "").strip():
        label = "Tutup mulai" if is_ms else "Closed from"
        rows.append(
            f'<div class="row"><small>{label}</small>'
            f"{_html.escape(closed_from.strip()[:40])}</div>"
        )
    reopen_label = "Buka semula" if is_ms else "Reopening"
    rows.append(
        f'<div class="row"><small>{reopen_label}</small>'
        f"{_html.escape(reopen.strip()[:40])}</div>"
    )

    default_note = (
        "Terima kasih atas sokongan anda — jumpa lagi selepas cuti!"
        if is_ms
        else "Thank you for your support — see you after the break!"
    )
    svg = _site_qr(url, palette)

    primary = _safe_color(palette.get("primary"), "#EA580C")
    return _CLOSURE_TEMPLATE.format(
        lang="ms" if is_ms else "en",
        title=_html.escape(f"{business_name} — Notis"),
        kicker="Notis Cuti" if is_ms else "Holiday Notice",
        headline=_html.escape(business_name or ""),
        note=_html.escape((note or "").strip()[:100] or default_note),
        dates="".join(rows),
        qr_svg=svg,
        qr_title="Kami tetap online" if is_ms else "We're still online",
        qr_body=(
            "Imbas untuk lihat menu, harga dan cara hubungi kami di "
            f"{_html.escape(_display_url(url))}."
            if is_ms
            else "Scan to see our menu, prices and contact details at "
            f"{_html.escape(_display_url(url))}."
        ),
        foot="Dijana oleh BinaApp" if is_ms else "Made with BinaApp",
        print_label="🖨️ Cetak" if is_ms else "🖨️ Print",
        primary=primary,
        on_primary=_on_primary(primary),
        surface=_safe_color(palette.get("surface"), "#FFFFFF"),
        background=_safe_color(palette.get("background"), "#F8FAFC"),
        text=_safe_color(palette.get("text"), "#111827"),
        text_muted=_safe_color(palette.get("text_muted"), "#6B7280"),
    )
