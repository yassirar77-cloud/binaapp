# Promo Kit — share card, story poster, vCard QR, Wi-Fi QR

Four growth surfaces generated **free and offline** from data the merchant
already has — their business name, their published URL, the palette their
page is wearing, and the phone number their page advertises. Same philosophy
as the Design Studio and QR toolkit: *the page already exists — stop
regenerating it.* No AI call, no credit, no third-party service.

| Surface | What it is | Who fetches it |
|---|---|---|
| Share card | 1200×630 `og:image` PNG — the WhatsApp/Facebook link preview | Crawlers (public) + owner (preview) |
| Story poster | 1080×1920 PNG with the site QR — WhatsApp Status / IG Story | Owner |
| vCard poster | A4 "scan to save our contact" — QR encodes a vCard 3.0 | Owner |
| Wi-Fi poster | A4 "scan to join our Wi-Fi" — QR encodes a `WIFI:` payload | Owner |

---

## 1. Share card — branded WhatsApp link previews, automatically

### The problem

Malaysian SMEs market by pasting their link into WhatsApp. A bare
`kedaiali.binaapp.my` with no unfurl image looks like spam; a link that
unfurls into a branded card looks like a business. Big brands have a
designer make an `og:image`; nobody makes one for a warung.

### How it works

The card is **rendered server-side with Pillow** (`services/share_card.py`)
from the site's own name, palette (`theme_patcher.detect_palette`) and meta
description — and served publicly on the subdomain host:

```
GET https://<subdomain>.binaapp.my/share-card.png
```

Public by necessity: the WhatsApp/Facebook/Telegram crawlers that unfurl a
shared link fetch it anonymously. The subdomain middleware serves it from the
same request path as `robots.txt` (no extra DB round trip), caches the PNG
in-process for 60 s, and **404s it for locked or plan-gated sites** so a
suspended page never unfurls a branded preview.

At serve time the middleware also injects into every served page (idempotent,
marker-delimited):

```html
<meta property="og:image" content="https://<sub>.binaapp.my/share-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="...">
```

**Only when the page has no `og:image` of its own** — a generation-time hero
photo is the merchant's real food and must win over our generated card.

The owner-facing copy of the same image (for preview/download in the editor):

```
GET /api/v1/websites/{id}/share-card.png     (owner-only)
```

### Degradation

Pillow missing → the renderer returns `b""` → the public path 404s, which
is exactly the pre-feature behaviour (no preview image). A missing share
card can never take the serve path down.

## 2. Story poster

```
GET /api/v1/websites/{id}/story.png?language=ms|en&campaign=...   (owner-only)
```

1080×1920 — the site QR in a white frame (always white behind a QR, for scan
contrast), business name fitted, URL, one-line instruction. `campaign` is
carried into the encoded URL as `?kempen=` exactly like the QR poster's
flyer batches. Merchants post it as a WhatsApp Status; followers screenshot
and scan — the offline equivalent of a swipe-up link.

## 3. vCard poster — "scan to save our number"

```
GET /api/v1/websites/{id}/vcard-qr.svg?phone=...      (owner-only)
GET /api/v1/websites/{id}/vcard-poster.html?language= (owner-only)
```

The QR encodes a **vCard 3.0** (the version iOS and Android cameras both
parse without quirks): FN/ORG = business name, TEL = the WhatsApp number,
URL = the published site, EMAIL when the page has a `mailto:`.

The phone number is **extracted from the merchant's own published page** —
`wa.me`/`api.whatsapp.com` links first (that's the number they actually
answer), `tel:` links as fallback — so the poster can never advertise a
number the site does not show. No number anywhere → a clear
`409 no_phone_found` telling the merchant to add their WhatsApp link first
(or pass `?phone=` explicitly). RFC 6350 escaping prevents a hostile
business name from smuggling extra vCard fields.

## 4. Wi-Fi poster — "scan to join"

```
GET /api/v1/websites/{id}/wifi-poster.html?ssid=...&password=...
      &security=WPA|WEP|nopass&show_password=true|false&language=ms|en
```

The QR encodes the `WIFI:T:...;S:...;P:...;;` payload both camera apps
understand, with spec escaping for `\ ; , : "`. SSID capped at 32 chars and
password at 63 (802.11 limits — anything longer cannot be a real network).
Empty password forces `nopass` (encoding a blank WPA password produces a
code that scans but never connects).

**Credentials are never stored and never logged.** They exist only in the
request/response pair, and the response carries `Cache-Control: private,
no-store` so a page containing a Wi-Fi password can never enter a shared
cache.

---

## UI

`frontend/src/components/PromoKitPanel.tsx`, mounted in the editor under the
Design Studio panel. Posters open via the same synchronous-tab +
authenticated-fetch pattern as the QR poster (owner-only endpoints cannot be
`window.open`ed directly — a navigation carries no bearer token, and putting
the token in the URL would leak it into history and access logs). Images
download via object URLs.

## Quota

Protected zone, same as the Design Studio: no endpoint here touches
`check_limit`, `subscription_service` or any usage counter.

## Tests

`backend/tests/test_promo_kit.py` — renderer dimensions and offline-ness
(network calls are patched to explode), palette/name edge cases, vCard and
`WIFI:` escaping, extraction rules, endpoint gates (401/403/404/409), the
public serve path (cache, 404-on-failure) and og:image injection
(idempotent, never overrides an existing image).
