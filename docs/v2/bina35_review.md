# BINA-35 — Review of 15 Unsampled V2 Variants

**Reviewer:** BinaApp CTO Agent  
**Date:** 2026-05-05  
**Branch:** `feat/v2-bina35-review`  
**Method:** Read each HTML file, grep for issues, cross-verified image URLs against `backend/app/data/malaysian_food_images.py` `DISH_POOL_MAP`

---

## menu_grid_classic — 6/10

### Halal compliance
- ⚠️ **Informal usage** (not RED FLAG by grep criteria): Line 222 contains `Hidangan fusion halal yang memukau selera` (marketing description text). No formal "halal certified", "sijil halal", or "JAKIM" found.

```html
<p class="mt-4 text-lg leading-relaxed" style="color: var(--color-text-muted);">Hidangan fusion halal yang memukau selera</p>
```

### Image/dish match
- Card "Nasi Kerabu Deconstructed" → `photo-1770966485209-e20d97337f1a` → ✅ in `nasi_kerabu_deconstructed` pool ("Nasi with herb garnish and sambal")
- Card "Rendang Burger" → `photo-1568901346375-23c9450c58cd` → ✅ in `rendang_burger` pool ("Gourmet beef burger with brioche bun and toppings")
- Card "Laksa Carbonara" → `photo-1768703321878-564507eae1f6` → ✅ in `laksa_carbonara` / `laksa` pool ("Bowls of laksa noodle soup")
- Card "Nasi Lemak Bistro" → `photo-1666239308347-4292ea2ff777` → ✅ in `nasi_lemak` pool ("Nasi lemak plate with sides")
- Card "Satay Khulafa 10pc" → `photo-1696385793103-71f51f6fd3b7` → ✅ in `satay` pool ("Satay plate with peanut sauce")

### Off-brand imagery
- ✅ None found

### Layout integrity
- ✅ Pass — `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`, standard padding, no excessive whitespace. All sections present.

### Editorial tier evidence
- Display font: Lora (serif, weights 400/600/700)
- Body font: Nunito (sans-serif)
- Editorial moments present: accent-line (3px × 48px gradient bar). No pull quotes, no ghost type, no asymmetric breakout, no oversize numerals.
- HTML quote of weakest section:

```html
<p class="mt-2 text-sm leading-relaxed" style="color: var(--color-text-muted);">
    Nasi kerabu dengan bunga telang, ulam segar, dan ikan bakar — disusun gaya moden
</p>
```

### Verdict
- Bugs to fix: 1 (informal "halal" in tagline — confirm if intentional marketing copy)
- Tier: 6/10 (1 criterion met: font hierarchy; no editorial moments)
- Ready to ship: **yes** (bug is minor copy review, not structural)

---

## menu_editorial_list — 7/10

### Halal compliance
- ✅ Pass — no matches for "halal certified", "sijil halal", "jakim"

### Image/dish match
- ⚠️ **No dish images in this file.** Variant uses editorial text-only list format with no `<img>` tags for menu items. By design or omission — confirm intent.

### Off-brand imagery
- ✅ None found (no product images present)

### Layout integrity
- ✅ Pass — vertical editorial list with dashed separators, `max-w-3xl mx-auto`, price alignment via `tabular-nums`. All menu category sections present (Nasi & Lauk, Fusion, Pembuka Selera, Minuman, Manisan).

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present:
  1. Category labels: `text-xs font-bold uppercase tracking-widest` with `letter-spacing: 0.15em` ✓
  2. Price alignment: `text-xl font-bold tabular-nums` with right-alignment ✓
- HTML quote of most default section:

```html
<h3 class="text-xl leading-tight flex items-center flex-wrap gap-1"
    style="font-family: var(--font-heading); color: var(--color-text); font-weight: 600;">
    Nasi Kerabu Deconstructed<span class="ml-3 text-xs font-bold uppercase tracking-widest
    px-2 py-0.5 rounded-full text-white" style="background-color: var(--color-primary);
    letter-spacing: 0.08em;">Popular</span>
</h3>
```

### Verdict
- Bugs to fix: 0
- Tier: 7/10 (2 criteria: font hierarchy + letter-spacing/tabular-nums micro-spacing intent)
- Ready to ship: **yes** (flag: no dish photos — intentional for editorial list?)

---

## menu_category_tabs — 6/10

### Halal compliance
- ✅ Pass

### Image/dish match
- Card "Nasi Kerabu Deconstructed" → `photo-1770966485209-e20d97337f1a` → ✅ in `nasi_kerabu_deconstructed` pool
- Card "Rendang Burger" → `photo-1568901346375-23c9450c58cd` → ✅ in `rendang_burger` pool
- Card "Laksa Carbonara" → `photo-1768703321878-564507eae1f6` → ✅ in `laksa_carbonara` pool
- Card "Nasi Lemak Bistro" → `photo-1666239308347-4292ea2ff777` → ✅ in `nasi_lemak` pool
- Card "Satay Khulafa 10pc" → `photo-1696385793103-71f51f6fd3b7` → ✅ in `satay` pool
- Cards "Teh Tarik", "Es Cendol" → ⚠️ gradient placeholder, no images (probably intentional for drink items)

### Off-brand imagery
- ✅ None found

### Layout integrity
- ✅ Pass — tabs with JS `filterMenu()`, `data-cat` attributes, grid cards. All 5 category tabs (Nasi & Lauk, Fusion, Pembuka Selera, Minuman, Manisan) functional. No empty whitespace.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present: Tab UI with transitions (`transition-all duration-200`). No distinct editorial moments — tabs are functional UX, not design.
- HTML quote of weakest section:

```html
<div class="menu-card rounded-2xl overflow-hidden" data-cat="Nasi &amp; Lauk"
     style="background-color: var(--color-surface); box-shadow: var(--shadow);">
    <div class="relative overflow-hidden h-44">
```

### Verdict
- Bugs to fix: 0
- Tier: 6/10 (1 criterion: font hierarchy; tab transitions are UX, not editorial)
- Ready to ship: **yes**

---

## gallery_mosaic_asymmetric — 7/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — gallery variant)
- Hero: `photo-1775986501486-380ea9539e07` → in `laksa`/`nasi_kerabu` pool (hero category) ✓
- Gallery main (col-span-2 row-span-2): `photo-1767429013002-69b35cb45395` → in `modern_fusion` pool ("Fish with creamy sauce and bok choy") ✓ Malaysian food
- Gallery small 1: `photo-1617694455303-59af55af7e58` → in `kuih` pool ("Kuih sliced on pan") ✓
- Gallery small 2: `photo-1768703321878-564507eae1f6` → in `laksa` pool ✓
- Gallery small 3: `photo-1707270686195-7415251cc9c0` → in `nasi_kerabu` pool ✓

### Off-brand imagery
- ✅ None found — all images are Malaysian food

### Layout integrity
- ✅ Pass — `grid grid-cols-2 md:grid-cols-3 auto-rows-[190px] gap-2`. Main image: `col-span-2 row-span-2 min-height:400px`. Small images: `min-height: 190px`. Asymmetric layout functioning correctly.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present:
  1. Asymmetric breakout: first image spans `col-span-2 row-span-2` vs uniform small tiles ✓
  2. Font hierarchy (Lora display + Nunito body) ✓
- HTML quote of weakest section:

```html
<div class="col-span-2 row-span-2 overflow-hidden rounded-2xl group">
    <img src="..." alt="Khulafa Bistro"
         class="w-full h-full object-cover transition-all duration-500 group-hover:scale-105"
```

### Verdict
- Bugs to fix: 0
- Tier: 7/10 (2 criteria: font hierarchy + asymmetric breakout layout)
- Ready to ship: **yes**

---

## gallery_carousel_immersive — 7/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — gallery variant)
- Same 4 gallery images as mosaic variant, all Malaysian food ✓
- All 4 carousel slides use same pool as mosaic: modern_fusion, kuih, laksa, nasi_kerabu

### Off-brand imagery
- ✅ None found

### Layout integrity
- ✅ Pass — full-bleed carousel with `padding-bottom: 56.25%` (correct 16:9 AR). 4 slides, dot indicators, 6000ms autoplay, prev/next buttons. All carousel mechanics present.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present:
  1. Full-bleed image treatment: `padding-bottom: 56.25%` wrapper with `position: absolute` slides ✓ (image scales beyond default placement)
  2. Caption overlay: `bg-gradient-to-t from-black/60 to-transparent` ✓ (intentional framing)
- HTML quote of weakest section:

```html
<div class="carousel-slide absolute inset-0 transition-opacity duration-700" style="opacity: 1; z-index: 1;">
    <img src="..." alt="Khulafa Bistro"
         class="w-full h-full object-cover" loading="eager"
```

### Verdict
- Bugs to fix: 0
- Tier: 7/10 (2 criteria: full-bleed image treatment + font hierarchy)
- Ready to ship: **yes**

---

## gallery_grid_uniform — 5/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — gallery variant)
- Same 4 Malaysian food images as other gallery variants ✓
- All from appropriate pools (modern_fusion, kuih, laksa, nasi_kerabu)

### Off-brand imagery
- ✅ None found

### Layout integrity
- ✅ Pass — 3-col uniform grid `grid grid-cols-3 gap-[2px]`, all items `aspect-ratio: 1` (square). Hover captions via opacity transition. Functional but minimal.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present: **none** — pure uniform square grid with hover captions. Lora+Nunito font hierarchy is the only criterion met.
- HTML quote of weakest section:

```html
<div class="relative overflow-hidden group" style="aspect-ratio: 1;">
    <img src="..." alt="Khulafa Bistro"
         class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
```

### Verdict
- Bugs to fix: 0
- Tier: 5/10 (1 criterion: font hierarchy only; no breakout, no varied scales/ratios, no editorial framing)
- Ready to ship: **yes** (but editorial quality is low — consider adding 1+ editorial element)

---

## contact_split_map — 5/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — contact variant)
- Hero: `photo-1775986501486-380ea9539e07` → in food pool ✓
- No other images (Google Maps iframe, no img tags)

### Off-brand imagery
- ✅ None found

### Layout integrity
- ✅ Pass — 2-col `lg:grid-cols-2`, left: contact info + hours, right: Google Maps iframe. All contact data present. Icons from Font Awesome. No whitespace issues.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present: **none** — standard flex column layout with icons and text.
- HTML quote of weakest section:

```html
<div class="flex items-start gap-3">
    <i class="fa-solid fa-location-dot mt-1" style="color: var(--color-primary);"></i>
    <p style="color: var(--color-text-muted);">No. 12, Jalan Plumbum V7/V, Seksyen 7, Shah Alam</p>
</div>
```

### Verdict
- Bugs to fix: 0
- Tier: 5/10 (functional, 1 criterion: font hierarchy)
- Ready to ship: **yes**

---

## contact_form_centered — 5/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — contact variant)
- Hero only ✓

### Off-brand imagery
- ✅ None found

### Layout integrity
- ✅ Pass — `max-w-2xl mx-auto`, form grid `grid-cols-1 sm:grid-cols-2 gap-5`, guest counter with +/- buttons, Google Maps iframe below. Form submits via WhatsApp URL (JS). All booking form fields present.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present: **none** — standard form with rounded inputs and a map.
- HTML quote of weakest section:

```html
<div>
    <label class="block text-sm font-semibold mb-1.5" style="color: var(--color-text);">Nama</label>
    <input type="text" id="bk-name" placeholder="Nama penuh" required
           class="w-full rounded-xl px-4 py-3 text-sm outline-none transition-shadow focus:ring-2"
```

### Verdict
- Bugs to fix: 0
- Tier: 5/10 (1 criterion: font hierarchy)
- Ready to ship: **yes**

---

## contact_minimal_essential — 5/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A)
- Hero only ✓

### Off-brand imagery
- ✅ None found

### Layout integrity
- ✅ Pass — `max-w-lg mx-auto text-center`. Single centered column. Large WhatsApp CTA (`px-10 py-5 text-lg`). Hours card. Location info. Matches "minimal_essential" naming (intentionally stripped down).

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present: **none** — minimal by design. Single CTA button.
- HTML quote of weakest section:

```html
<div class="rounded-2xl p-6" style="background-color: var(--color-surface); box-shadow: var(--shadow);">
    <div class="flex items-center gap-2 mb-4">
        <i class="fa-solid fa-clock" style="color: var(--color-primary);"></i>
        <p class="font-bold" style="color: var(--color-text);">Waktu Operasi</p>
    </div>
```

### Verdict
- Bugs to fix: 0
- Tier: 5/10 (minimal by design, 1 criterion)
- Ready to ship: **yes**

---

## contact_card_overlay — 7/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — contact variant)
- Hero: `photo-1775986501486-380ea9539e07` → in food pool ✓
- ❌ **Background image: `photo-1771830916721-c8da5d52e50f` — NOT in any DISH_POOL_MAP entry.** Used as CSS `background-image` on the contact section wrapper. Cannot verify content without loading URL.

```css
background-image: url('https://images.unsplash.com/photo-1771830916721-c8da5d52e50f?w=800&h=600&fit=crop&q=80')
```

### Off-brand imagery
- ⚠️ **Unverified** — background image `photo-1771830916721-c8da5d52e50f` is not in any pool. If it's a restaurant interior or ambience photo it's fine; if it contains any off-brand element it needs replacement.

### Layout integrity
- ✅ Pass — full-bleed background with `rgba(0,0,0,0.45)` overlay, glassmorphic card (`backdrop-filter: blur(16px); background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.25)`). Layout is clean with appropriate `z-index`.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present:
  1. Glassmorphic overlay design ✓ (distinctly non-default image treatment — blur, translucent card, shadow)
  2. Font hierarchy (Lora + Nunito) ✓
- HTML quote of most default section:

```html
<div class="relative z-10 w-full max-w-md rounded-2xl p-8 text-white"
     style="background: rgba(255,255,255,0.12); backdrop-filter: blur(16px);
     border: 1px solid rgba(255,255,255,0.25); box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
```

### Verdict
- Bugs to fix: 1 (verify background image `photo-1771830916721-c8da5d52e50f` — not in pool, content unknown)
- Tier: 7/10
- Ready to ship: **no** — background image needs visual verification first

---

## footer_minimal — 5/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — footer, no images)
- ✅ No images

### Off-brand imagery
- ✅ None

### Layout integrity
- ✅ Pass — `py-8 flex flex-col sm:flex-row items-center justify-between gap-4`. Brand name, tagline "Citarasa Melayu Moden", social icons (Instagram, Facebook), copyright. Minimal and functional.

### Editorial tier evidence
- Display font: Lora (brand name)
- Body font: Nunito
- Editorial moments present: **none** — brand name + tagline + icons row.
- HTML quote of weakest section:

```html
<div class="flex flex-col sm:flex-row items-center justify-between gap-4">
    <div class="text-center sm:text-left">
        <p class="font-bold text-lg" style="font-family: var(--font-heading);">Khulafa Bistro</p>
        <p class="text-xs opacity-50 mt-0.5">Citarasa Melayu Moden</p>
    </div>
```

### Verdict
- Bugs to fix: 0
- Tier: 5/10 (1 criterion; footer is intentionally compact)
- Ready to ship: **yes**

---

## footer_rich — 7/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — footer, no images)
- ✅ No images

### Off-brand imagery
- ✅ None

### Layout integrity
- ✅ Pass — `grid grid-cols-1 lg:grid-cols-5`. Brand col spans `lg:col-span-2`, link cols span `grid-cols-2 sm:grid-cols-3`. Newsletter form in brand section. Border separator. All sections present (Menu, Tentang, Hubungi).

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present:
  1. Section headers: `text-sm font-bold uppercase tracking-widest` (intentional micro-spacing) ✓
  2. Newsletter CTA embedded in brand column — non-default structural choice ✓
- HTML quote of weakest section:

```html
<div>
    <p class="text-sm font-bold uppercase tracking-widest mb-4 text-white/60">Menu</p>
    <ul class="space-y-2">
        <li><a href='#menu' class='text-sm text-white/60 hover:text-white transition-colors'>Nasi &amp; Lauk</a></li>
```

### Verdict
- Bugs to fix: 0
- Tier: 7/10 (2 criteria: font hierarchy + uppercase tracking-widest micro-spacing + newsletter breakout)
- Ready to ship: **yes**

---

## reviews_carousel — 6/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A — reviews variant)
- Hero only ✓. No product images in testimonial section.

### Off-brand imagery
- ✅ None

### Layout integrity
- ✅ Pass — carousel section `min-height: 260px`, 4 testimonial slides, dot indicators, 6000ms autoplay (pause on hover). Star ratings (5 ✦), italic quotes, avatar initials. All review content present.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present: italic `text-xl sm:text-2xl` quotes. Borderline — italic pull-quote-style rendering counts as 1, but the implementation is still a default carousel wrapper.
- HTML quote of weakest section:

```html
<div class="review-slide absolute inset-0 flex items-center justify-center px-4 transition-opacity duration-500" style="opacity: 1; z-index: 1;">
    <div class="max-w-xl w-full mx-auto text-center">
        <div class="flex justify-center gap-1 mb-5">
```

### Verdict
- Bugs to fix: 0
- Tier: 6/10 (italic quotes lean toward editorial but fall short of a second distinct criterion)
- Ready to ship: **yes**

---

## hours_simple_table — 4/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A)
- Hero only ✓

### Off-brand imagery
- ✅ None

### Layout integrity
- ✅ Pass — `max-w-sm mx-auto`, HTML `<table>`, `border-bottom: 1px solid var(--color-border)`, `td.py-3.5`. Hours: "Selasa - Jumaat: 11:00 pg - 10:00 mlm". Present and correct. No whitespace issues.

### Editorial tier evidence
- Display font: Lora (section heading)
- Body font: Nunito (table content)
- Editorial moments present: **none** — a plain table. No special typography, no framing, no hierarchy beyond basic font differentiation.
- HTML quote of weakest section:

```html
<table class="w-full">
    <tbody>
<tr style="border-bottom: 1px solid var(--color-border);">
    <td class="py-3.5 font-medium pr-8" style="color: var(--color-text);">Selasa - Jumaat</td>
    <td class="py-3.5 text-right" style="color: var(--color-text-muted);">11:00 pg - 10:00 mlm</td>
</tr>
```

### Verdict
- Bugs to fix: 0
- Tier: 4/10 (functional, 0 editorial criteria beyond basic font assignment — even the font hierarchy is minimal in a table)
- Ready to ship: **yes** (but weakest editorial entry in this batch)

---

## cta_whatsapp_first — 5/10

### Halal compliance
- ✅ Pass

### Image/dish match (N/A)
- Hero only ✓

### Off-brand imagery
- ✅ None (WhatsApp brand color #25D366 is expected here)

### Layout integrity
- ✅ Pass — `max-w-lg mx-auto text-center`, oversized WhatsApp button `text-2xl px-12 py-7 rounded-3xl`. Feature row (clock, calendar, users icons). Section heading "Bercakap Terus dengan Kami". All CTA content present.

### Editorial tier evidence
- Display font: Lora
- Body font: Nunito
- Editorial moments present: The large oversized button is a deliberate scale choice, but it serves functional CTA purposes — not an editorial design moment per Check 5 criteria.
- HTML quote of weakest section:

```html
<a href="https://wa.me/60173228899?text=Salam Khulafa Bistro, saya nak tempah meja..."
   class="inline-flex items-center justify-center gap-4 font-bold text-2xl text-white
   rounded-3xl px-12 py-7 transition-transform hover:scale-105 active:scale-95 w-full sm:w-auto"
   style="background-color: #25D366; box-shadow: 0 16px 40px -8px rgba(37,211,102,0.45);">
```

### Verdict
- Bugs to fix: 0
- Tier: 5/10 (1 criterion: font hierarchy; large button is functional not editorial)
- Ready to ship: **yes**

---

## Summary

- Total bugs found: **3**
- Variants ready to ship as-is: **14/15** (contact_card_overlay blocked pending image verification)
- Variants needing fixes before ship: **1/15**
- Variants below 7/10 tier: **10/15**

### Bugs grouped by type
- Image/dish mismatches: **0** (all menu variant dish images verified against DISH_POOL_MAP — prior fixes in PR #610 appear to have been applied correctly to pool mappings)
- Off-brand imagery: **0 confirmed**, **1 unverified** (contact_card_overlay background `photo-1771830916721-c8da5d52e50f`)
- Layout integrity: **0**
- Halal compliance (formal): **0** (1 informal usage in menu_grid_classic tagline text)
- Editorial tier failures (below 7/10): **10**

### Top 5 fixes recommended (priority order)

1. **contact_card_overlay.html — verify background image** (`photo-1771830916721-c8da5d52e50f` not in any DISH_POOL_MAP entry; must load URL and confirm it's a restaurant interior/ambience shot, not off-brand). File: `docs/previews/contact_card_overlay.html`.

2. **menu_grid_classic.html — review informal "halal" copy** (line 222: "Hidangan fusion halal yang memukau selera" — confirm if intentional marketing text; if not, remove the word "halal" to avoid implying uncertified claims). File: `docs/previews/menu_grid_classic.html:222`.

3. **gallery_grid_uniform.html — add 1 editorial moment** (currently 5/10; the 3-col uniform grid is too default — add varied aspect ratios or one oversized hero tile to reach 7/10). File: `docs/previews/gallery_grid_uniform.html`.

4. **hours_simple_table.html — elevate typography** (currently 4/10; a plain HTML table with no editorial framing — add section subheading, visual separator, or icon treatment to reach 5-6/10). File: `docs/previews/hours_simple_table.html`.

5. **reviews_carousel.html — add pull-quote treatment** (currently 6/10; italic text-2xl is close to editorial but not there — add oversize opening quote glyph or ghost typography to reach 7/10). File: `docs/previews/reviews_carousel.html`.

### Data inconsistency note (for separate ticket)
`backend/app/data/malaysian_food_images.py` has 4+ CDN IDs appearing in multiple pools with **different** dish descriptions for the same URL (e.g., `photo-1770966485209-e20d97337f1a` = "Nasi lemak on banana leaf with spoon" in NASI_LEMAK but "Nasi with herb garnish and sambal" in NASI_KERABU). Pool assignment to HTML is correct, but the contradictory descriptions are a data hygiene issue worth filing separately.
