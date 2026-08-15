# Counter Kit — loyalty cards, business cards, vouchers, closure notice

Four things a merchant hands over the counter (or tapes to the door),
delivered the BinaApp way: **free, offline, in the site's own palette, from
data the merchant already has**. Companion to [PROMO_KIT.md](PROMO_KIT.md)
and [BUSINESS_KIT.md](BUSINESS_KIT.md) — same contract (owner-only,
published-only, no AI call, no credit).

| Surface | What it is |
|---|---|
| Kad setia | A4 sheet of 8 wallet-size loyalty stamp cards |
| Kad nama | A4 sheet of 10 standard-size (90×50 mm) business cards |
| Baucar | A4 sheet of 6 cut-out vouchers with the merchant's offer |
| Notis bercuti | A4 "closed for the holidays" poster with a reopen date |

---

## 1. Loyalty stamp cards

```
GET /api/v1/websites/{id}/loyalty-cards.html?stamps=&reward=&language=ms|en
```

Eight cut-out cards per sheet, each with a numbered stamp grid whose last
circle is the 🎁 reward stamp — buy N-1, the Nth is free. `stamps` (4–20,
default 10) counts the reward stamp too; `reward` overrides the default
"Cop penuh — pembelian ke-N PERCUMA!" line. Any chop or marker pen stamps
a visit: no app, no account, no printing bill — a print shop charges RM80+
for this design.

## 2. Business cards

```
GET /api/v1/websites/{id}/business-cards.html?tagline=&language=
```

Ten standard-size cards per sheet: business name, tagline, phone, URL and
a QR straight to the site. The phone number is read from the merchant's own
page (`wa.me` first, `tel:` fallback — the same rule as the vCard poster):
we never print a number their site does not show. The default tagline is
the page's own meta description, overridable with `?tagline=`. Both are
optional — a card without them is still a card.

## 3. Voucher sheet

```
GET /api/v1/websites/{id}/voucher-sheet.html?offer=&code=&expiry=&language=
```

Six cut-out vouchers per sheet. `offer` (required, ≤60 chars) is printed
exactly as the merchant wrote it — "10% OFF", "Teh tarik percuma" — BinaApp
never invents a promotion. `code` (uppercased, ≤24) and `expiry` (free
text, ≤40) are optional decorations; redemption is between the merchant and
the customer at the counter. Every voucher carries a small QR to the site
and a one-per-customer fine-print line.

## 4. Closure notice

```
GET /api/v1/websites/{id}/closure-poster.html?reopen=&closed_from=&note=&language=
```

The "kami bercuti" poster every kedai needs twice a year and usually
solves with a biro note taped to the grille. `reopen` (required) and
`closed_from` (optional) are **free text printed as typed** — "5 Jun",
"selepas Raya" — because a date picker fights the way closures are actually
announced. `note` (optional) replaces the default thank-you line, e.g.
"Selamat Hari Raya Aidilfitri". The QR earns its place here: a closed door
is the one time a customer genuinely needs the website.

---

## Escaping and trust

Offers, rewards, dates and notes are merchant-typed and rendered into a
page the merchant will open and print — everything is HTML-escaped, printed
verbatim, and never interpreted. All QR codes point at the merchant's own
published site URL (built server-side from the subdomain), so unlike the
review poster there is no user-supplied link to validate.

## UI

Four new sections in the editor's **Kit Promosi** panel
(`PromoKitPanel.tsx`): kad setia (stamp-count + reward inputs), kad nama
(one click), baucar (offer/code/expiry inputs), notis cuti (dates inputs).
Same synchronous-tab + authenticated-fetch pattern as every other
owner-only poster.

## Tests

`backend/tests/test_counter_kit.py` — card/voucher counts per sheet, stamp
clamping and reward-stamp placement, bilingual copy, hostile-input escaping
on every free-text field, page-sourced phone/tagline with override, endpoint
gates (401/403/409/422 for missing offer, missing reopen date and
out-of-range stamps).
