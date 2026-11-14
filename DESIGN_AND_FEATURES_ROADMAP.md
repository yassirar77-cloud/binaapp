# BinaApp — Design Freedom Upgrade & Feature Roadmap

This document covers two things:

1. **What shipped in this branch** — the design-freedom + pro-design upgrades to the
   website generation pipeline.
2. **A prioritized feature roadmap** — what BinaApp should build next, based on a full
   audit of the codebase (generation pipeline, design system, widget catalogue,
   frontend builder UX) compared against what Malaysian SMEs get from Wix / Shopify /
   GoDaddy-class builders.

---

## Part 1 — What shipped in this branch

### The problem

Every generated site of the same business type looked identical: exactly **one** font
pairing, **one** colour palette, **one** layout, and **one** hero per business type
("every food business in Malaysia gets Playfair Display + orange #EA580C on cream").
Users had *no* design input: the request schema accepted `colors` / `fonts` / `theme`
but generation never read them, and typing "saya nak warna biru" did nothing.

### What changed (backend/app/services/design_system.py + ai_service.py)

1. **Seeded design variety** — every business type now has **3 font pairings**,
   **3 colour palettes** (light + dark each), and multiple hero designs. A
   deterministic seed from the business name picks the combination:
   different businesses look different; regenerating the same business stays stable.

2. **User colour requests are honoured** — `extract_design_preferences()` detects
   explicit colour asks in Malay or English ("warna biru", "tema emas", "gold theme",
   "navy blue design") and swaps in a matching full palette from 12 named palettes
   (blue, navy, green, red, maroon, purple, pink, gold, orange, teal, brown,
   black/mono). Detection is conservative: colour words only count next to design
   words, so "kek pandan hijau" never hijacks the palette.

3. **Style adjectives are honoured** — "mewah/elegant", "minimal/ringkas",
   "ceria/playful", "berani/bold", "klasik/vintage" in the description force a
   matching design personality. New style presets `elegant`, `playful`, `classic`
   join `modern` / `minimal` / `bold`.

4. **Merchant brand colours are wired in** — the previously dead
   `WebsiteGenerationRequest.colors` field now flows into generation
   (validated hex only) and beats every other palette pick.

5. **Design personalities** — six art-direction voices (Editorial Magazine,
   Soft Organic, Refined Luxe, Bold Contrast, Modern Minimal, Warm Crafted),
   seeded per business from a per-type pool, so pages differ in *feel*, not just colour.

6. **Hero blueprints now actually reach the AI** — `hero_variant` was computed but
   never injected into the prompt (dead code). It is now injected with placeholder
   token rules, and fabricated marketing badges that were hardcoded in the hero
   snippets ("Est. 2024 · Pengusaha Muslim", "Healthcare You Can Trust") were replaced
   with a factual-only TAGLINE_KICKER token.

7. **Pro-design prompt upgrades** — fluid type via `clamp()`, layout flexibility
   (section reordering/merging within a required content checklist), section
   background rhythm + one full-width colour band, an explicit CREATIVE FREEDOM
   clause, and a MOBILE & POLISH block: mandatory hamburger nav on mobile,
   `scroll-padding-top` for anchor jumps, `loading="lazy"` images,
   `text-wrap: balance` headings, visible focus states, `aria-label`s.

8. **User request overrides generic bans** — e.g. asking for purple lifts the
   anti-purple-SaaS rule with proper contrast guidance instead.

Backwards compatible: calling the old methods without a business name returns the
classic (variant 0) design; all 136 existing generation-related tests pass.

---

## Part 1b — Shipped since: Design Studio, QR Toolkit, SEO files

Full write-up: **[docs/DESIGN_STUDIO_AND_QR.md](docs/DESIGN_STUDIO_AND_QR.md)**.

1. **Design Studio — credit-free recolour & typography.** The design variety
   built above was invisible to merchants: the only way to change a colour was a
   full AI regenerate that cost a credit and moved the copy. `PATCH
   /websites/{id}/theme` now rewrites the colour/typography tokens *in the page
   that already exists* — 12 palettes, 27 font pairings, light/dark, and a
   reproducible shuffle. No AI call, no quota, no content drift; a test asserts
   the page's word list is unchanged by a repaint. Publish safety mirrors the
   contact-edit path (live-snapshot base, balanced-HTML gate, honest reporting).
   Shipped with a picker in the editor.

2. **`design_system.build(variant=…, palette_override=…, style_override=…)`** —
   the generation-time half of the same idea. `variant=0` reproduces every
   existing site exactly; each increment walks all four pools forward one step.

3. **QR Toolkit.** Published pages fetched their footer QR from
   `api.qrserver.com` on every pageview — a third party on the render path of
   every merchant's site. It is now rendered offline and inlined. Added
   owner-only `qr.svg` and a print-ready A4 `qr-poster.html` in the site's own
   palette, with per-table codes for dine-in.

4. **Per-site `robots.txt` and `sitemap.xml`**, generated from the page actually
   being served, so the sitemap can never advertise a section the generator
   dropped. Locked sites serve `Disallow: /`.

---

## Part 1c — Shipped since: promotions, bookings, table ordering, version history

All four need their migration run before they do anything; until then every
existing flow behaves exactly as before (plain delivery orders write none of
the new columns).

| Feature | Migration | Backend | Merchant UI | Customer UI |
|---|---|---|---|---|
| **Voucher codes + loyalty points** | `063_vouchers_and_loyalty.sql` | `services/promo_engine.py`, `endpoints/promotions.py`, `POST /delivery/orders` | `/dashboard/promosi` | promo row in the cart, points switch at checkout |
| **QR table ordering (dine-in)** | `064_dine_in_table_orders.sql` | `order_type` / `table_number` on `POST /delivery/orders`, dine-in status transitions | "Meja N" badge and kitchen buttons in `/pesanan` | `?meja=N` on the site → `/order/identify?r=…&meja=N` → table checkout and tracking |
| **Booking engine** | `065_booking_engine.sql` | `services/booking_engine.py`, `booking_store.py`, `endpoints/bookings.py` | `/dashboard/tempahan` | `/tempah/{websiteId}` |
| **Version history & undo** | `066_website_versions.sql` | `services/website_versions.py`, `endpoints/website_versions.py`, snapshot hooks in every page-write path | "Sejarah Versi" panel in the editor | — |

Rules worth knowing before changing any of it:

- **The server prices everything.** The cart used to show a hardcoded
  `BINAAPP10` discount that the order endpoint never applied. Discounts now come
  from `POST /promotions/quote` (a preview) and are recomputed by
  `POST /delivery/orders`, which refuses the order with `VOUCHER_INVALID` /
  `LOYALTY_INSUFFICIENT` rather than charge a total the customer was not shown.
- **Limited things are claimed in SQL.** `claim_voucher`, `redeem_loyalty_points`
  and `create_booking` lock before they count, so two simultaneous checkouts
  cannot both take the last voucher use, the same points, or the last slot.
- **Points are earned in a trigger** (`promo_on_order_status_change`) because
  order status is written from several endpoints. Cancelling or rejecting an
  order returns its points and its voucher use.
- **A table marker expires.** The dine-in context is bound to one restaurant and
  to three hours, and is dropped when the customer arrives without `?meja`, so
  an old scan can never send a delivery customer's food to a table.

Still open from these four: no per-site switch to turn dine-in off, no link from
a published site to its booking page (the merchant shares it), no customer
confirmation/reminder message for bookings, and voucher edit is limited to
pause / resume / delete in the UI (the API accepts full edits).

---

## Part 2 — Feature roadmap (prioritized)

### NOW — highest ROI, mostly unlocking things that already half-exist

| Feature | Why | Existing hooks |
|---|---|---|
| ~~**"Shuffle design" button + style picker**~~ ✅ **SHIPPED** | Merchants can now pick any of 12 palettes / 27 font pairings, toggle light-dark, or re-roll — instantly and credit-free. See [docs/DESIGN_STUDIO_AND_QR.md](docs/DESIGN_STUDIO_AND_QR.md) | `theme_patcher.py`, `design_studio.py`, `DesignStudioPanel.tsx` |
| **Brand kit UI** (logo upload → palette extraction) | `PATCH /websites/{id}/theme` already accepts explicit brand hexes and the picker is live; what remains is **logo upload → auto-extract a palette from it** | Design Studio panel, `request.colors` |
| **Real online payments at customer checkout** — ToyyibPay/Billplz FPX, DuitNow QR, TNG/GrabPay/Boost/ShopeePay | Orders currently settle by WhatsApp message + manual payment-screenshot verification; this is the single biggest conversion upgrade for merchants | ToyyibPay service already used for BinaApp subscriptions |
| **Custom domains** (+ automated DNS guidance + SSL) | Hard credibility ceiling vs Wix/Shopify; already on the README roadmap and a `custom_domain` column exists | publish flow, `custom_domain` column |
| **SEO pack** — *partially shipped:* ✅ per-site `robots.txt` + `sitemap.xml`, ✅ OG/JSON-LD. Still open: **editable** meta/OG, GA4 + Meta/TikTok pixel fields | Generated sites had no crawler-facing files at all; the editable/analytics half is still the discoverability differentiator | `site_seo_files.py`, `seo_metadata.py`, publish pipeline |

### NEXT — the editor & vertical depth

- **Section-level editor**: drag-to-reorder/hide sections, inline WYSIWYG text/image
  edits in the preview iframe (saved via existing `PUT /websites/{id}`), per-section
  regenerate — so a typo or price fix never costs an AI credit or risks a redesign.
  ~~Undo/version history~~ ✅ **SHIPPED** (Part 1c).
- ~~**Cheap theme patches instead of full regenerates**~~ ✅ **SHIPPED** as the
  Design Studio: `PATCH /websites/{id}/theme` rewrites the colour/typography
  tokens in the live page — no AI call, no credit, no content drift. What
  remains is routing the *typed* request ("tukar warna jadi merah" in the AI
  assistant box) into this path instead of the regenerate path, so the saving
  applies without the merchant having to find the picker.
- ~~**Real booking engine**~~ ✅ **SHIPPED** (services, opening hours, slot
  capacity, customer booking page — see Part 1c). Still open: staff calendars,
  deposits, WhatsApp/SMS reminders.
- **Multi-page sites** (Home/Menu/About/Gallery/Policies with shared nav) — escapes
  the one-pager ceiling that caps perceived professionalism.
- **Marketing suite**: voucher/discount engine, post-order review requests, Google
  Reviews + Instagram embeds, newsletter capture with broadcast, simple loyalty
  points for repeat F&B customers.
- **QR table-ordering mode** for dine-in restaurants — reuses the existing
  menu/ordering/rider stack with no delivery leg. The **physical half is
  shipped**: per-table QR codes and print-ready A4 posters
  (`GET /websites/{id}/qr-poster.html?table=5`). What remains is the ordering
  side — reading `?meja=N` in the order flow and routing a dine-in order to the
  kitchen with no delivery leg.
- **Courier integrations**: Lalamove/GrabExpress dispatch as an alternative to own
  riders; J&T/Pos Laju rate lookup + tracking numbers for parcel businesses
  (shipping is currently a hardcoded flat-fee list).

### LATER — scale & compliance

- **Inventory management**: stock counts, variant matrix (size/colour), sold-out
  auto-hide, low-stock alerts.
- **Multi-language sites**: BM + EN + Chinese switcher, including translated
  ordering-widget strings (README roadmap item).
- **Malaysian compliance**: SST-ready receipts and LHDN **MyInvois e-invoice**
  generation for orders — a near-term legal need no low-cost competitor serves well.
- **More business types** (property, tuition, automotive workshop, events/wedding,
  homestay/travel) with matching design types; replace keyword detection with a
  cheap LLM classification that also emits a style brief.
- **White-label / agency mode** (README roadmap item).

### Design-quality backlog (from the designer critique of generated output)

- Replace the **Tailwind Play CDN** in published sites with a compiled/purged CSS
  bundle (faster loads, no silent class drops, better Lighthouse).
- Re-theme the **pre-built animated templates** to CSS variables — today they
  hardcode hexes (`text-[#34d399]`) so they can't be recoloured, and every one is
  restaurant-shaped (Menu nav) even for salons.
- Add **mobile hamburger navigation** to the pre-built `designs/*.html` templates
  (currently `hidden md:flex` with no drawer — phone users get no nav).
- Gate or tone down **gimmick templates** (Ghost hides the whole site for 4s every
  60s; Word Explosion scatters all text) — flag as "playful", exclude from
  professional categories.
- Make **template animations deterministic and palette-aware** (pre-written CSS/JS
  with colour hooks) instead of a runtime qwen-max call with hardcoded purple/cyan.
- Finish **widget theming**: cart blue, delivery-page purple gradient, and chat
  colours still ignore the site palette beyond the orange substitutions.
- Fix `restaurant-example.html` (flagship demo has a literal CSS bug
  `text-center;`, emoji-for-photos, alert()-based cart).
