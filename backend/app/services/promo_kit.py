"""vCard and Wi-Fi QR payloads + printable posters for a published site.

Two more members of the offline promo kit (see also ``qr_service`` and
``share_card``), built on the same idea: everything a merchant needs is
already on their page or in their head — no AI call, no credit, no third
party.

* **Kad simpan nombor** (vCard QR) — a customer points their camera and
  gets "Add to Contacts" with the business name, WhatsApp number and
  website pre-filled. The number is read from the merchant's own published
  page (``wa.me`` / ``tel:`` links), so the poster can never advertise a
  number the site does not show.
* **Wi-Fi QR** — scan to join the shop's Wi-Fi. The SSID and password are
  request parameters only: they are encoded into the QR and the returned
  HTML, and **never stored or logged** — a shop's Wi-Fi password does not
  belong in our database.

Both posters reuse the site's own palette, exactly like the QR poster.
"""

from __future__ import annotations

import html as _html
import re
from typing import Optional

from app.services.qr_service import qr_svg, remote_qr_url

# ---------------------------------------------------------------------------
# Contact extraction — from the page the merchant actually published
# ---------------------------------------------------------------------------

#: wa.me/60123456789 or api.whatsapp.com/send?phone=60123456789
_WA_LINK_RE = re.compile(
    r"""(?:wa\.me/|api\.whatsapp\.com/send\?(?:[^"'\s>]*&)?phone=)\+?(\d{7,15})"""
)
_TEL_LINK_RE = re.compile(r"""href\s*=\s*["']tel:([+\d][\d\s().-]{5,20})["']""")
_MAILTO_RE = re.compile(
    r"""href\s*=\s*["']mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"""
)
_META_DESC_RE = re.compile(
    r"""<meta\s[^>]*name\s*=\s*["']description["'][^>]*content\s*=\s*["']([^"']{10,300})["']""",
    re.IGNORECASE,
)
_META_DESC_RE_REV = re.compile(
    r"""<meta\s[^>]*content\s*=\s*["']([^"']{10,300})["'][^>]*name\s*=\s*["']description["']""",
    re.IGNORECASE,
)


def extract_phone(page_html: str) -> Optional[str]:
    """The business phone number the page itself advertises, E.164-ish.

    WhatsApp links win over ``tel:`` links because on a BinaApp site the
    wa.me number IS the ordering channel — it is the number the merchant
    actually answers.
    """
    if not page_html:
        return None
    match = _WA_LINK_RE.search(page_html)
    if match:
        return "+" + match.group(1)
    match = _TEL_LINK_RE.search(page_html)
    if match:
        digits = re.sub(r"[^\d+]", "", match.group(1))
        if digits.count("+") <= 1 and len(digits.lstrip("+")) >= 7:
            return digits if digits.startswith("+") else "+" + digits
    return None


def extract_email(page_html: str) -> Optional[str]:
    if not page_html:
        return None
    match = _MAILTO_RE.search(page_html)
    return match.group(1) if match else None


def extract_tagline(page_html: str) -> Optional[str]:
    """The page's own meta description — the only tagline we can trust."""
    if not page_html:
        return None
    match = _META_DESC_RE.search(page_html) or _META_DESC_RE_REV.search(page_html)
    if not match:
        return None
    text = _html.unescape(match.group(1)).strip()
    return text or None


# ---------------------------------------------------------------------------
# QR payloads
# ---------------------------------------------------------------------------

def _vcard_escape(value: str) -> str:
    """RFC 6350 text escaping: backslash first, then separators, then newlines."""
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def build_vcard(
    name: str,
    phone: Optional[str] = None,
    url: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """A minimal, camera-app-friendly vCard 3.0.

    3.0 rather than 4.0 because it is what iOS and Android camera scanners
    both parse without quirks. CRLF line endings per spec.
    """
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{_vcard_escape(name)}",
        f"ORG:{_vcard_escape(name)}",
    ]
    if phone:
        lines.append(f"TEL;TYPE=CELL:{_vcard_escape(phone)}")
    if email:
        lines.append(f"EMAIL:{_vcard_escape(email)}")
    if url:
        lines.append(f"URL:{_vcard_escape(url)}")
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


def _wifi_escape(value: str) -> str:
    """Escaping per the de-facto WIFI: scheme — ``\\``, ``;``, ``,``, ``:``, ``"``."""
    escaped = value or ""
    for ch in ("\\", ";", ",", ":", '"'):
        escaped = escaped.replace(ch, "\\" + ch)
    return escaped


def build_wifi_payload(ssid: str, password: str = "", security: str = "WPA") -> str:
    """The ``WIFI:`` payload both Android and iOS cameras understand.

    ``security`` is one of WPA (covers WPA2/WPA3-personal), WEP or nopass.
    An empty password forces nopass — encoding a blank WPA password would
    produce a code that scans but never connects.
    """
    security = (security or "WPA").upper()
    if security not in ("WPA", "WEP", "NOPASS"):
        security = "WPA"
    if not password:
        security = "NOPASS"
    if security == "NOPASS":
        return f"WIFI:T:nopass;S:{_wifi_escape(ssid)};;"
    return f"WIFI:T:{security};S:{_wifi_escape(ssid)};P:{_wifi_escape(password)};;"


# ---------------------------------------------------------------------------
# Posters — same A4 shell as the QR poster, different payload and copy
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _safe_color(value: Optional[str], fallback: str) -> str:
    candidate = (value or "").strip()
    if candidate and not candidate.startswith("#"):
        candidate = "#" + candidate
    return candidate if _HEX_RE.match(candidate) else fallback


def _on_primary(primary: str) -> str:
    from app.services.theme_patcher import contrast_ratio

    return "#FFFFFF" if contrast_ratio("#FFFFFF", primary) >= 4.5 else "#111827"


_KIT_POSTER_TEMPLATE = """<!DOCTYPE html>
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
  .detail {{
    font-size: 20px;
    font-weight: 700;
    color: {primary};
    word-break: break-all;
    max-width: 32ch;
  }}
  .detail small {{
    display: block;
    font-size: 14px;
    font-weight: 600;
    color: {text_muted};
    letter-spacing: .06em;
    text-transform: uppercase;
    margin-bottom: 2px;
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
  {details}
  <div class="steps">{steps}</div>
  <p class="foot">{foot}</p>
</div>
</body>
</html>
"""


def _poster_shell(
    business_name: str,
    payload: str,
    palette: Optional[dict],
    language: str,
    kicker_ms: str,
    kicker_en: str,
    headline_ms: str,
    headline_en: str,
    steps_ms: list,
    steps_en: list,
    details_html: str,
) -> str:
    palette = palette or {}
    primary = _safe_color(palette.get("primary"), "#EA580C")
    is_ms = (language or "ms").lower().startswith("ms")
    svg = qr_svg(payload, scale=8, border=2, dark=_safe_color(palette.get("text"), "#111827"), light="#FFFFFF", standalone=False)
    if not svg:
        svg = (
            f'<img src="{_html.escape(remote_qr_url(payload, size=400), quote=True)}" '
            f'alt="QR" width="280" height="280" style="display:block">'
        )
    steps = "".join(
        f'<div class="step"><b>{_html.escape(title)}</b>{_html.escape(body)}</div>'
        for title, body in (steps_ms if is_ms else steps_en)
    )
    return _KIT_POSTER_TEMPLATE.format(
        lang="ms" if is_ms else "en",
        title=_html.escape(f"{business_name} — QR"),
        business_name=_html.escape(business_name or ""),
        kicker=_html.escape(kicker_ms if is_ms else kicker_en),
        headline=_html.escape(headline_ms if is_ms else headline_en),
        qr_svg=svg,
        details=details_html,
        steps=steps,
        print_label="🖨️ Cetak" if is_ms else "🖨️ Print",
        foot=_html.escape("Dijana oleh BinaApp" if is_ms else "Made with BinaApp"),
        primary=primary,
        on_primary=_on_primary(primary),
        surface=_safe_color(palette.get("surface"), "#FFFFFF"),
        background=_safe_color(palette.get("background"), "#F8FAFC"),
        text=_safe_color(palette.get("text"), "#111827"),
        text_muted=_safe_color(palette.get("text_muted"), "#6B7280"),
    )


def build_vcard_poster_html(
    business_name: str,
    vcard: str,
    phone: Optional[str],
    palette: Optional[dict] = None,
    language: str = "ms",
) -> str:
    """A4 poster: "scan to save our contact". The QR encodes the vCard itself."""
    is_ms = (language or "ms").lower().startswith("ms")
    details = ""
    if phone:
        label = "WhatsApp / Telefon" if is_ms else "WhatsApp / Phone"
        details = (
            f'<p class="detail"><small>{_html.escape(label)}</small>'
            f"{_html.escape(phone)}</p>"
        )
    return _poster_shell(
        business_name=business_name,
        payload=vcard,
        palette=palette,
        language=language,
        kicker_ms="Simpan Nombor Kami",
        kicker_en="Save Our Contact",
        headline_ms="Imbas sekali — nama, nombor dan laman web kami terus masuk dalam telefon anda.",
        headline_en="One scan saves our name, number and website straight to your phone.",
        steps_ms=[
            ("1. Buka kamera", "Halakan kamera telefon ke kod QR di atas."),
            ("2. Ketik 'Simpan'", "Telefon anda akan tawarkan untuk simpan kenalan."),
            ("3. WhatsApp kami", "Nombor kami sedia dalam kenalan — pesan bila-bila masa."),
        ],
        steps_en=[
            ("1. Open your camera", "Point your phone's camera at the QR code above."),
            ("2. Tap 'Save'", "Your phone offers to add us to your contacts."),
            ("3. Message us", "Our number is saved — order any time on WhatsApp."),
        ],
        details_html=details,
    )


def build_wifi_poster_html(
    business_name: str,
    ssid: str,
    password: str = "",
    security: str = "WPA",
    palette: Optional[dict] = None,
    language: str = "ms",
    show_password: bool = True,
) -> str:
    """A4 poster: "scan to join our Wi-Fi". Credentials live only in this response."""
    is_ms = (language or "ms").lower().startswith("ms")
    payload = build_wifi_payload(ssid, password, security)

    ssid_label = "Nama Wi-Fi" if is_ms else "Wi-Fi name"
    details = (
        f'<p class="detail"><small>{_html.escape(ssid_label)}</small>'
        f"{_html.escape(ssid)}</p>"
    )
    if password and show_password:
        pw_label = "Kata laluan" if is_ms else "Password"
        details += (
            f'<p class="detail"><small>{_html.escape(pw_label)}</small>'
            f"{_html.escape(password)}</p>"
        )

    return _poster_shell(
        business_name=business_name,
        payload=payload,
        palette=palette,
        language=language,
        kicker_ms="Wi-Fi Percuma",
        kicker_en="Free Wi-Fi",
        headline_ms="Imbas untuk sambung terus — tak perlu taip kata laluan.",
        headline_en="Scan to connect instantly — no password typing.",
        steps_ms=[
            ("1. Buka kamera", "Halakan kamera telefon ke kod QR di atas."),
            ("2. Ketik 'Sambung'", "Telefon anda akan sambung ke Wi-Fi kami."),
            ("3. Selesai", "Selamat melayari — jangan lupa follow kami!"),
        ],
        steps_en=[
            ("1. Open your camera", "Point your phone's camera at the QR code above."),
            ("2. Tap 'Join'", "Your phone connects to our Wi-Fi."),
            ("3. Done", "Enjoy browsing — and do follow us!"),
        ],
        details_html=details,
    )
