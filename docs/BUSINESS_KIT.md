# Business Kit — menu poster, review QR, WhatsApp order QR, open-now badge

Four features restaurant and business owners keep asking for, delivered the
BinaApp way: **free, offline, in the site's own palette, from data the
merchant already has**. Companion to [PROMO_KIT.md](PROMO_KIT.md) — same
contract (owner-only, published-only, no AI call, no credit).

| Surface | What it is |
|---|---|
| Menu poster | A4 menu / price list from the merchant's real menu data |
| Review poster | "beri kami 5 bintang" QR → the merchant's Google review page |
| WhatsApp poster | scan → WhatsApp opens with the order message pre-typed |
| Open badge | live "Buka sekarang / Tutup" pill on the served site |

---

## 1. Menu / price-list poster

```
GET /api/v1/websites/{id}/menu-poster.html?language=ms|en   (owner-only)
```

A print-ready A4 menu: categories grouped, dotted price leaders, ★ on
popular items, footer QR to the live site ("imbas QR untuk menu terkini").
Prices are normalised to `RM 12.50`; unparseable prices (e.g. *ikut
pasaran*) are printed as written.

**Menu sources, in order:**
1. the `menu_items` table (the delivery-flow menu manager), with category
   names joined from `menu_categories` and `is_available=false` rows dropped
   — a printed menu advertising something the kitchen stopped serving is
   worse than a shorter menu;
2. fallback: the `deliveryMenuData` array baked into the published page,
   extracted with a string-aware bracket scanner (a regex would truncate at
   the first `]` inside a description);
3. neither → clear `409 no_menu_found`.

Change a price in the dashboard → the next print is already correct. Works
for any business: a salon's service list is the same shape.

## 2. Google review poster

```
GET /api/v1/websites/{id}/review-poster.html?review_url=...&language=   (owner-only)
```

Reviews are the cheapest growth lever a local business has; this poster is
how you ask without asking. The QR points at the merchant's own review link.

**Only Google-family URLs are accepted** (`google.<tld>`, `g.page`, `g.co`,
`maps.app.goo.gl`, `search.google.com`, https only, ≤500 chars) — a printed
QR is trusted by whoever scans it, so the poster must not be usable as a
frame for arbitrary links. The host check anchors TLD labels, so
`google.evil.com` cannot pass as a Google host.

## 3. WhatsApp order poster

```
GET /api/v1/websites/{id}/whatsapp-poster.html?table=&message=&phone=&language=
```

The QR encodes `https://wa.me/<digits>?text=<pre-typed message>`. Default
message: *"Hai {kedai}! Saya nak buat pesanan."* — with `?table=5` it
becomes *"… (Meja 5)"* and the poster kicker reads **Pesan · Meja 5**: one
poster per table, and every incoming chat announces where it came from.

The number is read from the merchant's own page (`wa.me` first, `tel:`
fallback — the same rule as the vCard poster), overridable with `?phone=`.
No number anywhere → `409 no_phone_found`.

## 4. Open-now badge

Generated pages carry the merchant's hours as schema.org
`openingHoursSpecification` JSON-LD (`services/seo_metadata.py`). The
subdomain middleware injects a small script that reads **that** — so the
badge can never disagree with the hours printed on the page — and renders a
floating pill, bottom-left (bottom-right belongs to chat/delivery buttons):

- 🟢 `Buka sekarang · tutup 22:00`
- 🔴 `Tutup · buka 20:00` / `Tutup · buka esok 09:00`

Everything is computed client-side in `Asia/Kuala_Lumpur`, including
overnight ranges (`18:00–02:00` is open at midnight via the
previous-day-spill rule). Localised from the page's own `lang` attribute.

Gated on the JSON-LD marker (pages without structured hours pay nothing),
idempotent server-side (marker check) and client-side (element id check),
and silent on any parse failure — no badge is the failure mode, never a
broken page.

---

## UI

Three new sections in the editor's **Kit Promosi** panel
(`PromoKitPanel.tsx`): open menu A4, WhatsApp QR (with table input), review
QR (with link input). Same synchronous-tab + authenticated-fetch pattern as
every other owner-only poster. The badge needs no UI — it appears
automatically on sites whose pages carry hours.

## Tests

`backend/tests/test_business_kit.py` — menu extraction (both sources,
hostile input, bracket/quote edge cases, unavailable-item filtering), price
formatting, poster escaping, review URL allow-list (including the
`google.evil.com` spoof), wa.me link building, endpoint gates
(401/403/404/409/422), badge gating and idempotency.
