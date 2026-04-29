# V2 Component Variant Batch Spec

**Target:** 24 variants across 6 sections (About, Menu, Gallery, Testimonial, Contact, Footer)
**Quality bar:** 8.5/10 polish, pass blink test, mobile-first, theme tokens only
**Approval gate:** Commit after each batch of 4 variants
**Test data:** Khulafa Bistro brief (malay_fusion, teh_tarik_warm, light mode)

---

## Completed (Phase 1)

| # | Section | Variant | Component | Status |
|---|---------|---------|-----------|--------|
| 1 | Hero | centered | HeroCentered | Done |
| 2 | Hero | fullscreen-image | HeroFullscreenImage | Done |
| 3 | Hero | split-reverse | HeroSplitReverse | Done |
| 4 | Hero | asymmetric-card | HeroAsymmetricCard | Done |

---

## Batch 2 — About Variants (4 variants)

| # | Variant | Component | Description | Key Differentiator | Reference | Mobile |
|---|---------|-----------|-------------|--------------------|-----------|--------|
| 5 | story | AboutStory | Split layout: image left, founder narrative right with signature | Emotional connection through personal origin story | Warung-style "dari dapur ke hati" storytelling | Image stacks above text, signature stays |
| 6 | stats | AboutStats | Metrics row (years, dishes served, ratings) with brief text below | Data-driven trust — numbers speak louder | F&B sites that lead with "15 tahun berkhidmat" | Stats become 2x2 grid, counters animate on scroll |
| 7 | timeline | AboutTimeline | Vertical timeline of business milestones with alternating sides | Heritage restaurants showing evolution from 1985 to today | Mamak chain "Sejarah Kami" pages | Single-column timeline, dots on left edge |
| 8 | cards | AboutCards | 3 value-proposition cards (Halal, Fresh, Family) with icons | Quick-scan values for busy users who skip paragraphs | Franchise sites with "Mengapa Kami" grid | Cards stack vertically, full-width |

---

## Batch 3 — Menu Variants (4 variants)

| # | Variant | Component | Description | Key Differentiator | Reference | Mobile |
|---|---------|-----------|-------------|--------------------|-----------|--------|
| 9 | grid | MenuGrid | Photo cards in responsive grid, price + popular badge | Visual menu — food photos sell dishes | Instagram-style food grid layouts | 1-column cards with large images |
| 10 | cards | MenuCards | Horizontal card: image left, name/desc/price right | Detailed descriptions for fusion dishes that need explaining | Fine dining menu card layouts | Card flips to vertical (image top) |
| 11 | list | MenuList | Clean text list grouped by category, no images | Fast scanning for regulars who know what they want | Kopitiam paper menu aesthetic | Full-width list, larger touch targets |
| 12 | categorized | MenuCategorized | Tab/pill navigation by category (Mains, Drinks, Dessert) | Large menus with 20+ items need filtering | Grab Food category tabs | Horizontal scrollable pills |

---

## Batch 4 — Gallery Variants (4 variants)

| # | Variant | Component | Description | Key Differentiator | Reference | Mobile |
|---|---------|-----------|-------------|--------------------|-----------|--------|
| 13 | masonry | GalleryMasonry | Pinterest-style varied-height grid, hover zoom | Organic feel for diverse photo sizes (food + ambience) | Instagram Explore grid | 2-column masonry |
| 14 | grid | GalleryGrid | Uniform square grid, clean and symmetrical | Professional portfolio look for upscale venues | Restaurant photography portfolios | 2x2 then "see more" |
| 15 | carousel | GalleryCarousel | Full-width swipeable carousel with dots/arrows | Immersive one-at-a-time viewing, great for ambience | Hotel/resort gallery sliders | Touch-swipe native, arrows hidden |
| 16 | lightbox | GalleryLightbox | Thumbnail grid that opens full-screen overlay on click | Detailed photo viewing without leaving page | Photography portfolio lightboxes | Pinch-zoom in lightbox overlay |

---

## Batch 5 — Testimonial Variants (4 variants)

| # | Variant | Component | Description | Key Differentiator | Reference | Mobile |
|---|---------|-----------|-------------|--------------------|-----------|--------|
| 17 | cards | TestimonialCards | 3-column cards with star rating, name, avatar initial | Scannable social proof — 3 reviews at a glance | Google Reviews embed style | Stack to 1-column, swipe hint |
| 18 | slider | TestimonialSlider | Auto-rotating single testimonial with nav dots | Spotlight effect — one powerful review at a time | Booking.com review slider | Full-width, larger text, swipe |
| 19 | quote | TestimonialQuote | Large quote marks, centered italic text, attribution below | Editorial/premium feel for fine dining | Magazine pull-quote style | Quote fills viewport width |
| 20 | grid | TestimonialGrid | 2x2 compact grid with truncated text + "read more" | High density — shows volume of positive reviews | App Store review grids | 1-column, expand-on-tap |

---

## Batch 6 — Contact Variants (4 variants)

| # | Variant | Component | Description | Key Differentiator | Reference | Mobile |
|---|---------|-----------|-------------|--------------------|-----------|--------|
| 21 | split | ContactSplit | Left: info/hours/WhatsApp, Right: embedded Google Map | Most complete — everything visible at once | Standard restaurant contact pages | Map moves below info, full-width |
| 22 | simple | ContactSimple | Centered stack: address, phone, hours, WhatsApp button | Minimalist — just the essentials, no map | Warung/small business contact | Already mobile-optimized by design |
| 23 | form | ContactForm | Contact form (name, email, message) + sidebar info | Lead capture for catering/event inquiries | Corporate restaurant sites | Form goes full-width, info below |
| 24 | cards | ContactCards | 3 cards: Location, Hours, Connect (WhatsApp + social) | Quick-scan cards instead of wall of text | Service business contact pages | Cards stack vertically |

---

## Batch 7 — Footer Variants (4 variants)

| # | Variant | Component | Description | Key Differentiator | Reference | Mobile |
|---|---------|-----------|-------------|--------------------|-----------|--------|
| 25 | brand | FooterBrand | Centered: logo, tagline, social icons, copyright | Clean brand sign-off, good for single-page sites | Minimal portfolio footers | Already centered, works as-is |
| 26 | columns | FooterColumns | 3-4 columns: brand, nav links, hours, contact | Information-rich for sites with many sections | Multi-page restaurant footers | Columns stack to 1, accordion optional |
| 27 | cta | FooterCta | Dark banner with "Jom Makan!" CTA + WhatsApp button, then footer | Final conversion push before page ends | SaaS footer CTAs ("Start free trial") | CTA button full-width |
| 28 | minimal | FooterMinimal | Single line: copyright left, social icons right | Unobtrusive — lets last section breathe | Developer portfolio footers | Center-aligned single line |

---

## Implementation Rules

1. **Theme tokens only** — all colors via `var(--color-*)`, fonts via `var(--font-*)`, spacing via design tokens
2. **No hardcoded colors** — must work across all 6 StyleDNA presets (teh_tarik_warm, neon_mamak, kopitiam_nostalgia, etc.)
3. **Mobile-first** — write mobile layout first, then `md:` and `lg:` breakpoints
4. **Blink test** — user must "get it" within 1 second of seeing the section
5. **AOS animations** — each section gets `data-aos` attribute, stagger children with `data-aos-delay`
6. **Image fallbacks** — every `<img>` gets `onerror` handler showing gradient placeholder
7. **Accessibility** — semantic HTML, proper heading hierarchy, alt text, aria-labels on interactive elements
8. **Bahasa-first** — all placeholder text in Malay (Khulafa Bistro test data)

## Execution Order

```
Batch 2 (About)       → commit → preview check → GO
Batch 3 (Menu)        → commit → preview check → GO
Batch 4 (Gallery)     → commit → preview check → GO
Batch 5 (Testimonial) → commit → preview check → GO
Batch 6 (Contact)     → commit → preview check → GO
Batch 7 (Footer)      → commit → preview check → GO
```

~15 min per variant = ~6 hours total for 24 variants.
