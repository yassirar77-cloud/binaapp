# BinaApp V2 Architecture: Component-Recipe Pipeline

**Author:** CTO Agent | **Date:** 2026-04-27 | **Status:** PLAN (no code written)

---

## Executive Summary

Replace the monolithic "one prompt = one HTML blob" generation with a **two-stage pipeline**:

1. **Stage 1 — Design Brief** (fast, cheap): AI reads the business description and outputs a structured JSON plan — what sections to include, what content to write, which style DNA to apply.
2. **Stage 2 — HTML Assembly** (deterministic, zero AI): A renderer picks pre-built React components, injects the content from the Design Brief, and produces final HTML. No AI involved.

**Why this matters:**
- Fix one section without regenerating the whole page
- Predictable output (components are tested, not hallucinated)
- 80-90% cost reduction (one small AI call vs. 8-12K output tokens of HTML)
- Sub-5-second generation (no waiting for 8K tokens to stream)

---

## 1. Two-Stage Pipeline Overview

```
User Input                    Stage 1                        Stage 2
┌─────────────┐    ┌──────────────────────┐    ┌──────────────────────────┐
│ description  │───>│  AI: Design Brief    │───>│  Renderer: HTML Assembly │
│ images       │    │  (structured JSON)   │    │  (no AI, deterministic)  │
│ features     │    │                      │    │                          │
│ style_dna    │    │  ~500 tokens in      │    │  Design Brief + React    │
│ language     │    │  ~1500 tokens out    │    │  Components = HTML       │
└─────────────┘    └──────────────────────┘    └──────────────────────────┘
                          │                              │
                          v                              v
                   design_brief.json              final index.html
                   (stored in DB)                 (stored in Supabase)
```

### Cost Comparison

| | V1 (current) | V2 (recipe) |
|---|---|---|
| AI calls per site | 1-3 (fallback chain) | 1 |
| Input tokens | ~4,000 | ~500 |
| Output tokens | ~8,000-12,000 (raw HTML) | ~1,500 (structured JSON) |
| Cost per generation | $0.03-0.08 | ~$0.005-0.01 |
| Time to result | 15-60 seconds | 3-8 seconds |
| Retry cost (section fix) | Full regeneration ($0.03+) | Re-run Stage 1 for 1 section ($0.002) |

---

## 2. JSON Schemas

### 2.1 Design Brief (Stage 1 Output)

This is what the AI produces. Pydantic-validated on the backend.

```json
{
  "$schema": "design_brief_v1",
  "version": "1.0",
  "language": "ms",
  "business": {
    "name": "Restoran Nasi Kandar Ali",
    "type": "restaurant",
    "tagline": "Rasa Asli Pulau Pinang Sejak 1985",
    "about": "Kami menyajikan nasi kandar autentik dengan rempah pilihan dan lauk segar setiap hari. Terletak di jantung Georgetown, restoran kami telah menjadi destinasi pencinta makanan selama lebih 30 tahun.",
    "address": "45 Jalan Burma, Georgetown, Penang",
    "whatsapp": "60195551234",
    "email": null,
    "social_media": {
      "instagram": "@nasikandarali",
      "facebook": null
    }
  },
  "style_dna": "warm_cozy",
  "color_mode": "light",
  "sections": [
    {
      "type": "hero",
      "variant": "hero-split",
      "content": {
        "headline": "Nasi Kandar Terbaik di Pulau Pinang",
        "subheadline": "Rempah asli, lauk segar, tradisi turun-temurun",
        "cta_text": "Lihat Menu",
        "cta_link": "#menu",
        "image_key": "hero"
      }
    },
    {
      "type": "about",
      "variant": "about-story",
      "content": {
        "heading": "Tentang Kami",
        "paragraphs": [
          "Restoran Nasi Kandar Ali bermula sebagai gerai kecil di pasar malam Georgetown.",
          "Kini, kami bangga menyajikan lebih 20 jenis lauk setiap hari kepada ribuan pelanggan setia."
        ],
        "image_key": "gallery_1"
      }
    },
    {
      "type": "menu",
      "variant": "menu-grid",
      "content": {
        "heading": "Menu Kami",
        "subheading": "Pilihan lauk segar setiap hari",
        "source": "supabase",
        "fallback_items": [
          { "name": "Nasi Kandar Biasa", "description": "Nasi dengan kuah campur dan papadom", "price": "RM 7.00", "image_key": "gallery_2" },
          { "name": "Ayam Goreng Berempah", "description": "Ayam goreng rangup dengan rempah khas Penang", "price": "RM 9.00", "image_key": "gallery_3" },
          { "name": "Ikan Bakar", "description": "Ikan segar bakar dengan sambal petai", "price": "RM 12.00", "image_key": "gallery_4" }
        ]
      }
    },
    {
      "type": "gallery",
      "variant": "gallery-masonry",
      "content": {
        "heading": "Galeri",
        "image_keys": ["gallery_1", "gallery_2", "gallery_3", "gallery_4"]
      }
    },
    {
      "type": "contact",
      "variant": "contact-simple",
      "content": {
        "heading": "Hubungi Kami",
        "whatsapp_cta": "Hubungi via WhatsApp",
        "address_display": "45 Jalan Burma, Georgetown, Penang",
        "hours": "7:00 pagi - 11:00 malam, setiap hari",
        "show_map": true
      }
    },
    {
      "type": "footer",
      "variant": "footer-simple",
      "content": {
        "copyright": "Restoran Nasi Kandar Ali",
        "powered_by": true
      }
    }
  ],
  "image_map": {
    "hero": "https://storage.example.com/uploads/hero-abc123.jpg",
    "gallery_1": "https://storage.example.com/uploads/img-001.jpg",
    "gallery_2": "https://storage.example.com/uploads/img-002.jpg",
    "gallery_3": "https://storage.example.com/uploads/img-003.jpg",
    "gallery_4": "https://storage.example.com/uploads/img-004.jpg"
  },
  "features": {
    "whatsapp": true,
    "google_map": true,
    "delivery_system": false,
    "gallery": true,
    "price_list": true,
    "operating_hours": true
  }
}
```

### 2.2 Page Recipe (Internal — Renderer Input)

The Page Recipe is derived from the Design Brief + the resolved Style DNA. It is never sent to AI — it is the internal contract between backend and renderer.

```json
{
  "$schema": "page_recipe_v1",
  "version": "1.0",
  "meta": {
    "title": "Restoran Nasi Kandar Ali | Nasi Kandar Terbaik Penang",
    "description": "Rasa Asli Pulau Pinang Sejak 1985. Nasi kandar autentik di Georgetown.",
    "language": "ms",
    "favicon": null
  },
  "theme": {
    "fonts": {
      "heading": "Lora",
      "body": "Nunito",
      "cdn_url": "https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap"
    },
    "colors": {
      "primary": "#EA580C",
      "secondary": "#92400E",
      "accent": "#FED7AA",
      "background": "#FFFBF5",
      "surface": "#FFFFFF",
      "text": "#1C1917",
      "text_muted": "#78716C",
      "border": "rgba(0,0,0,0.08)"
    },
    "border_radius": "rounded-2xl",
    "button_style": "bg-primary text-white rounded-2xl px-7 py-3.5 font-semibold",
    "card_style": "bg-surface rounded-3xl shadow-md",
    "nav_style": "bg-white/90 backdrop-blur-xl shadow-sm"
  },
  "sections": [
    {
      "component": "HeroSplit",
      "props": {
        "headline": "Nasi Kandar Terbaik di Pulau Pinang",
        "subheadline": "Rempah asli, lauk segar, tradisi turun-temurun",
        "cta_text": "Lihat Menu",
        "cta_link": "#menu",
        "image_url": "https://storage.example.com/uploads/hero-abc123.jpg",
        "animation": "fade-up"
      }
    },
    {
      "component": "AboutStory",
      "props": {
        "heading": "Tentang Kami",
        "paragraphs": ["..."],
        "image_url": "https://storage.example.com/uploads/img-001.jpg",
        "animation": "fade-up"
      }
    },
    {
      "component": "MenuGrid",
      "props": {
        "heading": "Menu Kami",
        "subheading": "Pilihan lauk segar setiap hari",
        "items": [
          { "name": "Nasi Kandar Biasa", "description": "...", "price": "RM 7.00", "image_url": "..." }
        ],
        "animation": "fade-up"
      }
    },
    {
      "component": "GalleryMasonry",
      "props": {
        "heading": "Galeri",
        "images": ["url1", "url2", "url3", "url4"],
        "animation": "fade-up"
      }
    },
    {
      "component": "ContactSimple",
      "props": {
        "heading": "Hubungi Kami",
        "whatsapp_number": "60195551234",
        "whatsapp_cta": "Hubungi via WhatsApp",
        "address": "45 Jalan Burma, Georgetown, Penang",
        "hours": "7:00 pagi - 11:00 malam, setiap hari",
        "show_map": true
      }
    },
    {
      "component": "FooterSimple",
      "props": {
        "business_name": "Restoran Nasi Kandar Ali",
        "powered_by": true
      }
    }
  ],
  "head_assets": [
    "https://fonts.googleapis.com/css2?family=...",
    "https://unpkg.com/aos@2.3.4/dist/aos.css",
    "https://cdn.tailwindcss.com",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
  ],
  "body_scripts": [
    "https://unpkg.com/aos@2.3.4/dist/aos.js"
  ],
  "init_scripts": [
    "AOS.init({ duration: 800, once: true, offset: 100 });"
  ]
}
```

### 2.3 Pydantic Models (Backend)

These will live in `backend/app/schemas/recipe.py`:

```
DesignBrief
  ├── BusinessInfo (name, type, tagline, about, address, whatsapp, email, social_media)
  ├── SectionSpec[] (type: SectionType enum, variant: str, content: dict)
  ├── image_map: Dict[str, str]
  ├── features: FeatureFlags
  ├── style_dna: StyleDNA enum
  ├── color_mode: Literal["light", "dark"]
  └── language: Literal["ms", "en"]

PageRecipe
  ├── meta: PageMeta (title, description, language, favicon)
  ├── theme: ThemeTokens (fonts, colors, border_radius, button_style, card_style, nav_style)
  ├── sections: RenderedSection[] (component: str, props: dict)
  ├── head_assets: List[str]
  ├── body_scripts: List[str]
  └── init_scripts: List[str]

SectionType = Literal["hero", "about", "menu", "gallery", "testimonial", "contact", "footer"]
StyleDNA = Literal["elegance_dark", "fresh_clean", "warm_cozy", "bold_vibrant",
                    "minimal_luxe", "neon_night", "malay_heritage", "ocean_breeze"]
```

---

## 3. Style DNA (Converted from Current Templates)

Convert 10 templates in `templateGallery.ts` into 8 canonical Style DNAs. Drop `word_explosion` and `ghost_restaurant` (gimmick animations that break in production).

| # | Style DNA Key | Source Template | Mode | Font Pair | Kept Because |
|---|---|---|---|---|---|
| 1 | `elegance_dark` | elegance_dark | dark | Playfair Display + DM Sans | Premium dark theme, proven popular |
| 2 | `fresh_clean` | fresh_clean | light | Plus Jakarta Sans + Inter | Clean green, good for health/organic |
| 3 | `warm_cozy` | warm_cozy | light | Lora + Nunito | Best seller for food businesses |
| 4 | `bold_vibrant` | bold_vibrant | light | Bebas Neue + Roboto | High-energy, good for events/sports |
| 5 | `minimal_luxe` | minimal_luxe | light | Cormorant Garamond + Inter | Fashion/salon/photography |
| 6 | `neon_night` | neon_night | dark | Space Grotesk + Inter | Tech/gaming/nightlife |
| 7 | `malay_heritage` | malay_heritage | light | Playfair Display + Poppins | Cultural businesses, very Malaysia |
| 8 | `ocean_breeze` | ocean_breeze | light | Source Serif 4 + Open Sans | Calm/spa/wellness |

Each Style DNA is a pure data file (JSON + CSS variables). No animation JS, no gimmicks.

**Storage:** `frontend/src/lib/style-dna/{key}.json` + shared `index.ts` exporter.

---

## 4. Component Library

### 4.1 Naming Convention

```
{SectionType}{VariantName}
```

Examples: `HeroSplit`, `HeroCentered`, `MenuGrid`, `MenuCards`, `FooterSimple`

### 4.2 Component Inventory (7 types x 5 variants = 35 components)

| Section | Variant 1 | Variant 2 | Variant 3 | Variant 4 | Variant 5 |
|---------|-----------|-----------|-----------|-----------|-----------|
| **Hero** | `HeroCentered` (text centered over full-bleed image) | `HeroSplit` (image left, text right) | `HeroVideo` (background video/gradient, text overlay) | `HeroMinimal` (text only, large typography, no image) | `HeroSlider` (2-3 images carousel) |
| **About** | `AboutStory` (image + 2 paragraphs side by side) | `AboutStats` (text + 3 stat counters) | `AboutTimeline` (vertical timeline milestones) | `AboutCards` (3 value-prop cards) | `AboutMinimal` (centered text block, no image) |
| **Menu** | `MenuGrid` (3-4 col grid with images) | `MenuCards` (horizontal card with image left) | `MenuList` (text-only price list, no images) | `MenuCategorized` (tabs by category from Supabase) | `MenuFeatured` (hero item + smaller grid) |
| **Gallery** | `GalleryMasonry` (Pinterest-style variable height) | `GalleryGrid` (uniform 2x2 or 3x2 grid) | `GalleryCarousel` (horizontal scroll) | `GalleryLightbox` (grid with click-to-expand) | `GalleryFullWidth` (single row, edge-to-edge) |
| **Testimonial** | `TestimonialCards` (3 cards with avatar + quote) | `TestimonialSlider` (one at a time, auto-rotate) | `TestimonialQuote` (single large quote, centered) | `TestimonialGrid` (2x2 compact cards) | `TestimonialMinimal` (text-only, no avatars) |
| **Contact** | `ContactSimple` (address + WhatsApp + hours) | `ContactForm` (name/email/message form) | `ContactMap` (embedded Google Map + details) | `ContactSplit` (map left, info right) | `ContactCards` (3 cards: call, email, visit) |
| **Footer** | `FooterSimple` (copyright + powered by) | `FooterColumns` (3-4 col with links) | `FooterCTA` (newsletter signup + socials) | `FooterMinimal` (single line, centered) | `FooterBrand` (logo + tagline + socials) |

### 4.3 Component Contract

Every component:

1. Is a standalone `.tsx` file
2. Accepts `props` (content data) + `theme` (ThemeTokens via CSS variables)
3. Uses Tailwind only — references CSS variables like `var(--color-primary)`
4. Is mobile-first responsive (no separate mobile template)
5. Includes `data-aos="fade-up"` for scroll animation
6. Exports a static `renderToHTML(props, theme): string` for SSR/static generation
7. Has zero external dependencies beyond Tailwind + Font Awesome icons

### 4.4 File Structure

```
frontend/src/components/website-sections/
  hero/
    HeroCentered.tsx
    HeroSplit.tsx
    HeroVideo.tsx
    HeroMinimal.tsx
    HeroSlider.tsx
    index.ts              # barrel export + component registry
  about/
    AboutStory.tsx
    AboutStats.tsx
    ...
  menu/
    MenuGrid.tsx
    MenuCards.tsx
    ...
  gallery/
    ...
  testimonial/
    ...
  contact/
    ...
  footer/
    ...
  _shared/
    SectionWrapper.tsx    # common padding, animation, id anchor
    ThemeProvider.tsx      # CSS variable injection from theme tokens
    ComponentRegistry.ts  # maps "HeroSplit" string -> component
  index.ts                # master barrel
```

---

## 5. New Folder Structure

### 5.1 Backend Changes

```
backend/app/
  schemas/
    recipe.py             # NEW — DesignBrief, PageRecipe, SectionSpec Pydantic models
    style_dna.py          # NEW — StyleDNA definitions (colors, fonts, tokens)
  services/
    ai_service.py         # REFACTOR — replace _build_strict_prompt() with brief_prompt()
    brief_generator.py    # NEW — Stage 1: call AI, parse DesignBrief JSON
    recipe_builder.py     # NEW — Stage 2: DesignBrief -> PageRecipe (no AI)
    html_renderer.py      # NEW — PageRecipe -> final HTML string (template engine)
    design_system.py      # KEEP — color palettes, font pairings (refactor to use StyleDNA)
  api/
    simple/
      generate.py         # REFACTOR — wire new pipeline, keep route signatures
    v1/endpoints/
      websites.py         # REFACTOR — wire new pipeline for /v1/websites/generate
```

### 5.2 Frontend Changes

```
frontend/src/
  components/
    website-sections/     # NEW — 35 section components (see 4.4)
  lib/
    style-dna/            # NEW — 8 JSON style definitions
      elegance_dark.json
      fresh_clean.json
      ...
      index.ts
    templateGallery.ts    # DEPRECATE — replaced by style-dna/
  app/
    create/
      page.tsx            # REFACTOR — split into sub-components (see 5.3)
      components/
        CreateForm.tsx         # NEW — extracted form inputs
        StylePicker.tsx        # NEW — style DNA selection grid
        SectionEditor.tsx      # NEW — reorder/toggle sections
        GenerationProgress.tsx # NEW — extracted polling + progress UI
        PublishFlow.tsx        # NEW — extracted publish modal logic
        DevicePreview.tsx      # KEEP — works as-is
        MultiDevicePreview.tsx # KEEP
        VisualImageUpload.tsx  # KEEP
```

### 5.3 create/page.tsx Split Plan

The current 2,283-line god component becomes an orchestrator of ~200 lines:

| Extracted Component | Responsibility | Est. Lines |
|---|---|---|
| `CreateForm.tsx` | Business description, language, business type, feature toggles | ~250 |
| `StylePicker.tsx` | Style DNA grid with preview thumbnails | ~150 |
| `ImageUploadSection.tsx` | Image choice mode + VisualImageUpload wrapper | ~100 |
| `SectionEditor.tsx` | Drag-to-reorder sections, toggle sections on/off | ~200 |
| `GenerationProgress.tsx` | Polling logic, progress bar, stale detection, timeout | ~200 |
| `PreviewPanel.tsx` | DevicePreview + MultiDevicePreview + style variation selector | ~150 |
| `PublishFlow.tsx` | Subdomain input, validation, publish API call, success modal | ~200 |
| `create/page.tsx` (orchestrator) | State coordination, step wizard, layout | ~200 |

---

## 6. Files: Delete vs Keep vs Refactor

### DELETE (after migration complete)

| File | Reason |
|---|---|
| `frontend/src/components/templates/animations/*.tsx` (11 files) | Replaced by Style DNA (pure CSS, no WebGL/canvas) |
| `frontend/src/components/templates/TemplatePreview.tsx` | No longer needed — preview uses real components |
| `backend/app/services/ai_service.py` → `_build_strict_prompt()` | Replaced by `brief_generator.py` prompt |
| `api/simple_generate.py` (top-level duplicate) | Consolidate into single endpoint |

### KEEP (no changes needed)

| File | Reason |
|---|---|
| `public/widgets/delivery-widget.js` | Separate concern, injected post-generation |
| `backend/app/services/ai_chat_responder.py` | Unrelated to website generation |
| `backend/app/services/ai_chatbot_service.py` | Unrelated |
| `backend/app/services/ai_email_support.py` | Unrelated |
| `backend/app/services/ai_order_verifier.py` | Unrelated |
| `backend/app/services/screenshot_service.py` | Still needed for preview thumbnails |
| `backend/app/utils/content_moderation.py` | Still needed pre-generation |
| All Supabase menu tables | Integrated into MenuCategorized component |
| All delivery/order tables | Untouched |

### REFACTOR

| File | What Changes |
|---|---|
| `backend/app/services/ai_service.py` | Remove `_build_strict_prompt()` (250 lines). Add `generate_design_brief()` method (~50 lines). Keep `_call_glm()`, `_call_deepseek()`, `_call_qwen()` as-is. Keep fallback chain. |
| `backend/app/api/simple/generate.py` | Replace monolithic generation call with: `brief = await brief_generator.generate(request)` then `recipe = recipe_builder.build(brief)` then `html = html_renderer.render(recipe)`. Keep all validation, subscription, moderation logic. |
| `frontend/src/app/create/page.tsx` | Extract into 7 sub-components (see 5.3). Orchestrator manages step wizard state. |
| `frontend/src/lib/templateGallery.ts` | Convert 8 templates to `style-dna/*.json`. Add deprecation comment pointing to new location. Remove after migration. |
| `frontend/src/components/templates/TemplateCard.tsx` | Adapt to show Style DNA previews instead of animation previews |
| `backend/app/api/v1/endpoints/websites.py` | Wire to new pipeline (same pattern as generate.py refactor) |
| `backend/app/services/ai_website_doctor.py` | Refactor to score individual sections instead of full HTML blob |

---

## 7. Migration Order

### Phase 1: Foundation (Backend Schemas + Component Library Shell)

**Build first because everything else depends on these contracts.**

| Task | Details | Est. Hours |
|---|---|---|
| Create `schemas/recipe.py` | Pydantic models: DesignBrief, PageRecipe, SectionSpec, ThemeTokens, all enums | 4h |
| Create `schemas/style_dna.py` | 8 Style DNA definitions as dataclasses | 3h |
| Create `_shared/SectionWrapper.tsx` | Wrapper with padding, animation, id anchor | 2h |
| Create `_shared/ThemeProvider.tsx` | CSS variable injection from ThemeTokens | 2h |
| Create `_shared/ComponentRegistry.ts` | String -> Component mapping | 1h |
| Write 7 "Variant 1" components | HeroCentered, AboutStory, MenuGrid, GalleryMasonry, TestimonialCards, ContactSimple, FooterSimple | 14h |
| Unit test each component | Renders correctly, responsive, theme tokens applied | 4h |
| **Phase 1 Total** | | **30h** |

### Phase 2: Pipeline Backend (Stage 1 + Stage 2 + Renderer)

**Build the new pipeline behind a feature flag, parallel to V1.**

| Task | Details | Est. Hours |
|---|---|---|
| Create `brief_generator.py` | Stage 1 prompt (asks AI for DesignBrief JSON), Pydantic validation, retry on invalid JSON | 6h |
| Create `recipe_builder.py` | Merge DesignBrief + StyleDNA -> PageRecipe, resolve image_map keys to URLs, inject menu items from Supabase | 5h |
| Create `html_renderer.py` | PageRecipe -> HTML string using component templates (server-side Jinja2 or string assembly) | 6h |
| Add `?pipeline=v2` flag to `/generate` endpoint | Feature flag: `v1` = old path, `v2` = new path. Both return same response shape. | 3h |
| Supabase migration: add `design_brief` JSONB column to `websites` table | Store the brief alongside html_content for future editing | 1h |
| Integration tests | Generate 10 sites (5 business types x 2 languages), compare quality to V1 | 4h |
| **Phase 2 Total** | | **25h** |

### Phase 3: Remaining Components (28 more variants)

**Expand the library. Can be parallelised across developers.**

| Task | Details | Est. Hours |
|---|---|---|
| Hero variants 2-5 | HeroSplit, HeroVideo, HeroMinimal, HeroSlider | 6h |
| About variants 2-5 | AboutStats, AboutTimeline, AboutCards, AboutMinimal | 6h |
| Menu variants 2-5 | MenuCards, MenuList, MenuCategorized, MenuFeatured | 8h |
| Gallery variants 2-5 | GalleryGrid, GalleryCarousel, GalleryLightbox, GalleryFullWidth | 6h |
| Testimonial variants 2-5 | TestimonialSlider, TestimonialQuote, TestimonialGrid, TestimonialMinimal | 5h |
| Contact variants 2-5 | ContactForm, ContactMap, ContactSplit, ContactCards | 6h |
| Footer variants 2-5 | FooterColumns, FooterCTA, FooterMinimal, FooterBrand | 4h |
| Visual regression tests | Screenshot each component x each Style DNA (35 x 8 = 280 combos) | 6h |
| **Phase 3 Total** | | **47h** |

### Phase 4: Frontend Refactor (Split create/page.tsx)

**Do this last — the new components and pipeline must be stable first.**

| Task | Details | Est. Hours |
|---|---|---|
| Extract `CreateForm.tsx` | Move form fields, validation, example descriptions | 3h |
| Extract `StylePicker.tsx` | Style DNA grid with live preview thumbnails | 3h |
| Extract `SectionEditor.tsx` | Drag-to-reorder, toggle sections, calls DesignBrief schema | 5h |
| Extract `GenerationProgress.tsx` | Polling, progress bar, timeout handling | 3h |
| Extract `PublishFlow.tsx` | Subdomain, publish API, success state | 3h |
| Rewrite `create/page.tsx` orchestrator | Step wizard: Form -> Style -> Sections -> Generate -> Preview -> Publish | 4h |
| Delete old `templateGallery.ts` and animation components | Clean up after new flow is live | 1h |
| Remove duplicate `/api/generate-simple` endpoint in `simple_generate.py` | Consolidate to single entry point | 1h |
| E2E tests | Full flow: create -> generate -> preview -> publish | 4h |
| **Phase 4 Total** | | **27h** |

### Summary

| Phase | Scope | Hours | Can Start After |
|---|---|---|---|
| Phase 1 | Schemas + 7 core components | 30h | Immediately |
| Phase 2 | Pipeline backend + feature flag | 25h | Phase 1 |
| Phase 3 | 28 remaining component variants | 47h | Phase 1 (parallel with Phase 2) |
| Phase 4 | Frontend refactor + cleanup | 27h | Phase 2 |
| **Total** | | **129h** | |

---

## 8. Stage 1 AI Prompt (Design Brief Generation)

This replaces the current ~250-line `_build_strict_prompt()`. The new prompt is ~40 lines and asks for structured JSON, not raw HTML.

```
SYSTEM:
You are a web design planner for Malaysian businesses. Output ONLY valid JSON matching the DesignBrief schema. Do not output HTML. Do not invent facts not present in the input.

USER:
Plan a website for this business.

BUSINESS NAME: {name}
DESCRIPTION: {description}
LANGUAGE: {language}
STYLE: {style_dna}
FEATURES ENABLED: {features_json}
IMAGE KEYS AVAILABLE: {image_keys}

Return a DesignBrief JSON with:
1. business: extract name, type, tagline (creative), about (2-3 sentences from description), address, whatsapp — ONLY use facts from the description
2. sections: choose appropriate section types and variants from this list:
   - hero: centered, split, video, minimal, slider
   - about: story, stats, timeline, cards, minimal
   - menu: grid, cards, list, categorized, featured
   - gallery: masonry, grid, carousel, lightbox, full-width
   - testimonial: cards, slider, quote, grid, minimal
   - contact: simple, form, map, split, cards
   - footer: simple, columns, cta, minimal, brand
3. For each section, write the actual content (headings, paragraphs, CTA text) in {language}
4. Map images to image_keys (hero, gallery_1, gallery_2, gallery_3, gallery_4)

RULES:
- ALL text must be in {"Bahasa Malaysia" if language == "ms" else "English"}
- Do NOT invent addresses, phone numbers, prices, or awards not in the description
- Menu items: if description mentions specific dishes, include them. Otherwise omit menu section.
- Testimonials: ONLY include if description mentions reviews/ratings. Do NOT fabricate testimonials.
- Choose section variants that match the style_dna aesthetic
```

**Token estimate:** ~300 input + ~1,200 output = ~1,500 total (vs. current ~12,000)

---

## 9. Key Architecture Decisions

### 9.1 Server-Side Rendering for Published Sites

Published sites must be static HTML (no React runtime). The `html_renderer.py` will:
1. Load each component's HTML template (pre-compiled from the `.tsx` source)
2. Substitute content placeholders with Design Brief data
3. Inject theme CSS variables into a `<style>` block
4. Concatenate all sections into a single `index.html`

This means each component needs **two representations**:
- `.tsx` for in-app preview (interactive, React)
- `.html.jinja2` (or equivalent) for static published output

**Trade-off:** Some duplication, but published sites load instantly with zero JS framework overhead.

### 9.2 Design Brief Stored in Database

Add `design_brief JSONB` column to the `websites` table. This enables:
- **Section-level editing:** Change one section's content without regenerating the whole site
- **Re-theming:** Apply a different Style DNA to an existing brief (instant, no AI call)
- **Analytics:** Know which section types and variants are most popular
- **Version history:** Store previous briefs for undo

### 9.3 Backward Compatibility

During migration (Phases 1-3), both pipelines coexist:
- `?pipeline=v1` (default): current monolithic path
- `?pipeline=v2`: new recipe path

The response shape is identical — both return `{ html, success, detected_features }`. The frontend doesn't need to know which pipeline produced the HTML.

Flip the default to `v2` after Phase 4 is complete and tested.

### 9.4 Multi-Model Fallback Chain — Reused

The existing GLM -> DeepSeek -> Qwen fallback chain is reused for Stage 1. The only change:
- System prompt changes from "generate HTML" to "generate DesignBrief JSON"
- Max tokens drops from 8,000-12,000 to 2,000
- Output is Pydantic-validated; invalid JSON triggers a retry (not a full fallback)

---

## 10. What This Does NOT Cover

These are explicitly out of scope for V2 and should be separate efforts:

1. **AI image generation** — Stability AI integration stays as-is
2. **Delivery widget** — `delivery-widget.js` is untouched, injected post-render
3. **Website doctor/health scans** — Future: refactor to score per-section
4. **Chat/support AI** — Completely separate service
5. **Subscription/billing** — No changes to limits or pricing
6. **Custom domains** — Separate infrastructure concern
7. **SEO optimization** — Future phase: AI-generated meta tags per section

---

## 11. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AI returns invalid JSON for Design Brief | Medium | Low | Pydantic validation + retry with error message. Max 2 retries before falling back to V1 pipeline. |
| Component variants don't cover all business types | Low | Medium | Start with Variant 1 for each section (Phase 1). The 7 "default" variants handle 90% of cases. |
| Published HTML looks different from React preview | Medium | Medium | Visual regression tests (Phase 3). Jinja templates are generated FROM the React components, not written separately. |
| Migration takes longer than estimated | High | Low | Feature flag means V1 stays live indefinitely. No deadline pressure. |
| Users prefer the "AI-generated" aesthetic variety | Low | Medium | 8 Style DNAs x 5 variants = 40 visual combinations. More consistent but still varied. |

---

## 12. Pre-Phase-1 Clarifications

### Q1. Full Design Brief JSON — "Khulafa Bistro" Example

Khulafa Bistro is a halal Malay-fusion family restaurant in Shah Alam. Below is the **exact** JSON that Stage 1 AI would return, validated by Pydantic.

```json
{
  "$schema": "design_brief_v1",
  "version": "1.0",
  "language": "ms",

  "business": {
    "name": "Khulafa Bistro",
    "type": "restaurant",
    "tagline": "Citarasa Melayu Moden untuk Seluruh Keluarga",
    "about": [
      "Khulafa Bistro menghidangkan masakan Melayu fusion yang menggabungkan resipi tradisional dengan sentuhan moden.",
      "Terletak di jantung Shah Alam, kami menyediakan suasana selesa untuk keluarga menikmati hidangan halal berkualiti tinggi.",
      "Dari nasi kerabu deconstructed hingga rendang burger, setiap hidangan kami diolah dengan bahan segar tempatan."
    ],
    "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, 40000 Shah Alam, Selangor",
    "whatsapp": "60173228899",
    "email": "hello@khulafabistro.my",
    "social_media": {
      "instagram": "@khulafabistro",
      "facebook": "KhulafaBistroShahAlam",
      "tiktok": null
    },
    "operating_hours": "Selasa - Ahad, 11:00 pagi - 10:00 malam. Isnin tutup."
  },

  "style_dna": "teh_tarik_warm",
  "color_mode": "light",

  "sections": [
    {
      "type": "hero",
      "variant": "split",
      "content": {
        "headline": "Masakan Melayu Fusion di Hati Shah Alam",
        "subheadline": "Resipi warisan nenek, dimasak dengan gaya masa kini untuk keluarga anda",
        "cta_text": "Lihat Menu",
        "cta_link": "#menu",
        "cta_secondary_text": "Tempah Meja",
        "cta_secondary_link": "https://wa.me/60173228899?text=Saya%20ingin%20tempah%20meja",
        "image_key": "hero"
      }
    },
    {
      "type": "about",
      "variant": "story",
      "content": {
        "heading": "Kisah Kami",
        "paragraphs": [
          "Bermula dari dapur kecil di rumah pengasas kami, Khulafa Bistro lahir daripada cinta kepada masakan Melayu yang autentik.",
          "Kami percaya makanan tradisional boleh dipersembahkan dengan cara baru tanpa mengorbankan rasa asli. Setiap hidangan kami diolah menggunakan rempah tumbuk segar dan bahan tempatan pilihan."
        ],
        "image_key": "gallery_1"
      }
    },
    {
      "type": "menu",
      "variant": "categorized",
      "content": {
        "heading": "Menu Istimewa",
        "subheading": "Hidangan fusion halal yang memukau",
        "source": "supabase",
        "fallback_items": [
          {
            "name": "Nasi Kerabu Deconstructed",
            "description": "Nasi kerabu dengan bunga telang, ulam segar, dan ikan bakar — disusun gaya moden",
            "price": "RM 18.90",
            "category": "Signature",
            "image_key": "gallery_2",
            "is_popular": true
          },
          {
            "name": "Rendang Burger",
            "description": "Daging rendang juicy dalam roti brioche dengan acar jelatah dan sambal hijau",
            "price": "RM 22.90",
            "category": "Signature",
            "image_key": "gallery_3",
            "is_popular": true
          },
          {
            "name": "Laksa Carbonara",
            "description": "Spaghetti dalam kuah laksa krimi, udang segar, dan taburan kerisik",
            "price": "RM 19.90",
            "category": "Fusion",
            "image_key": null
          },
          {
            "name": "Cendol Panna Cotta",
            "description": "Panna cotta santan dengan gula Melaka, cendol, dan kacang merah",
            "price": "RM 12.90",
            "category": "Pencuci Mulut",
            "image_key": null
          },
          {
            "name": "Teh Tarik Latte",
            "description": "Espresso dicampur teh tarik klasik — perpaduan timur dan barat",
            "price": "RM 9.90",
            "category": "Minuman",
            "image_key": null
          }
        ]
      }
    },
    {
      "type": "gallery",
      "variant": "masonry",
      "content": {
        "heading": "Suasana Kami",
        "image_keys": ["gallery_1", "gallery_2", "gallery_3", "gallery_4"]
      }
    },
    {
      "type": "testimonial",
      "variant": "cards",
      "content": {
        "heading": "Apa Kata Pelanggan",
        "reviews": [
          {
            "name": "Aisha R.",
            "text": "Rendang burger terbaik yang pernah saya rasa! Anak-anak pun suka.",
            "rating": 5
          },
          {
            "name": "Farid M.",
            "text": "Suasana cozy, sesuai untuk family dinner. Laksa carbonara memang unik!",
            "rating": 5
          },
          {
            "name": "Siti N.",
            "text": "Harga berpatutan untuk kualiti fusion macam ni. Mesti datang lagi.",
            "rating": 4
          }
        ]
      }
    },
    {
      "type": "contact",
      "variant": "split",
      "content": {
        "heading": "Hubungi Kami",
        "whatsapp_cta": "WhatsApp Kami",
        "address_display": "No. 12, Jalan Plumbum V7/V, Seksyen 7, Shah Alam",
        "hours": "Selasa - Ahad, 11 pagi - 10 malam",
        "show_map": true,
        "map_query": "Khulafa Bistro Shah Alam"
      }
    },
    {
      "type": "footer",
      "variant": "brand",
      "content": {
        "business_name": "Khulafa Bistro",
        "tagline": "Citarasa Melayu Moden",
        "social_links": {
          "instagram": "https://instagram.com/khulafabistro",
          "facebook": "https://facebook.com/KhulafaBistroShahAlam"
        },
        "copyright_year": 2026,
        "powered_by": true
      }
    }
  ],

  "image_map": {
    "hero": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/hero.jpg",
    "gallery_1": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/interior.jpg",
    "gallery_2": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/nasi-kerabu.jpg",
    "gallery_3": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/rendang-burger.jpg",
    "gallery_4": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/laksa.jpg"
  },

  "features": {
    "whatsapp": true,
    "google_map": true,
    "delivery_system": false,
    "gallery": true,
    "price_list": true,
    "operating_hours": true,
    "testimonials": true,
    "social_media": true
  }
}
```

**Key design decisions visible in this example:**
- `image_map` uses symbolic keys (`hero`, `gallery_1`...) so the AI never touches raw URLs — it just assigns keys. The URL resolution happens deterministically in Stage 2.
- `source: "supabase"` on the menu section means "pull live data from menu_items table at render time." `fallback_items` are only used if the Supabase table is empty (e.g., first-time generation before the owner adds real menu items).
- Testimonials are included because the user description mentioned reviews. If the description had no mention, the AI would omit this section entirely.
- `variant` is a short key (`split`, `story`, `categorized`) — the recipe builder resolves it to a full component name (`HeroSplit`, `AboutStory`, `MenuCategorized`).

---

### Q2. Full Page Recipe JSON — Same "Khulafa Bistro" Example

This is what the **assembler/renderer reads**. It is derived deterministically from the Design Brief + the resolved Style DNA. No AI is involved in producing this.

```json
{
  "$schema": "page_recipe_v1",
  "version": "1.0",

  "meta": {
    "title": "Khulafa Bistro | Masakan Melayu Fusion di Shah Alam",
    "description": "Citarasa Melayu Moden untuk Seluruh Keluarga. Nasi kerabu deconstructed, rendang burger, dan lagi di Shah Alam.",
    "language": "ms",
    "favicon": null,
    "og_image": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/hero.jpg"
  },

  "theme": {
    "style_dna": "teh_tarik_warm",
    "fonts": {
      "heading": "Lora",
      "heading_weight": "700",
      "body": "Nunito",
      "body_weight": "400",
      "cdn_url": "https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap"
    },
    "colors": {
      "primary": "#C2410C",
      "primary_hover": "#9A3412",
      "secondary": "#78350F",
      "accent": "#FED7AA",
      "background": "#FFFBF5",
      "surface": "#FFFFFF",
      "text": "#1C1917",
      "text_muted": "#78716C",
      "border": "rgba(194, 65, 12, 0.1)",
      "gradient_from": "#C2410C",
      "gradient_to": "#78350F"
    },
    "tokens": {
      "border_radius_sm": "0.75rem",
      "border_radius_md": "1rem",
      "border_radius_lg": "1.5rem",
      "shadow": "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)",
      "shadow_lg": "0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04)",
      "spacing_section": "5rem",
      "max_width": "1280px"
    },
    "component_styles": {
      "button_primary": "bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200",
      "button_secondary": "border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200",
      "card": "bg-[var(--color-surface)] rounded-3xl shadow-md hover:shadow-lg transition-shadow duration-200",
      "nav": "bg-white/90 backdrop-blur-xl shadow-sm fixed top-0 w-full z-50",
      "section_padding": "py-20 px-4 sm:px-6 lg:px-8"
    }
  },

  "nav": {
    "logo_text": "Khulafa Bistro",
    "links": [
      { "label": "Laman Utama", "href": "#hero" },
      { "label": "Tentang", "href": "#about" },
      { "label": "Menu", "href": "#menu" },
      { "label": "Galeri", "href": "#gallery" },
      { "label": "Hubungi", "href": "#contact" }
    ],
    "cta": { "label": "Tempah Meja", "href": "https://wa.me/60173228899?text=Saya%20ingin%20tempah%20meja" }
  },

  "sections": [
    {
      "id": "hero",
      "component": "HeroSplit",
      "props": {
        "headline": "Masakan Melayu Fusion di Hati Shah Alam",
        "subheadline": "Resipi warisan nenek, dimasak dengan gaya masa kini untuk keluarga anda",
        "cta_text": "Lihat Menu",
        "cta_link": "#menu",
        "cta_secondary_text": "Tempah Meja",
        "cta_secondary_link": "https://wa.me/60173228899?text=Saya%20ingin%20tempah%20meja",
        "image_url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/hero.jpg",
        "image_alt": "Khulafa Bistro — masakan Melayu fusion",
        "image_position": "right"
      },
      "animation": { "type": "fade-up", "delay": 0 }
    },
    {
      "id": "about",
      "component": "AboutStory",
      "props": {
        "heading": "Kisah Kami",
        "paragraphs": [
          "Bermula dari dapur kecil di rumah pengasas kami, Khulafa Bistro lahir daripada cinta kepada masakan Melayu yang autentik.",
          "Kami percaya makanan tradisional boleh dipersembahkan dengan cara baru tanpa mengorbankan rasa asli. Setiap hidangan kami diolah menggunakan rempah tumbuk segar dan bahan tempatan pilihan."
        ],
        "image_url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/interior.jpg",
        "image_alt": "Suasana dalaman Khulafa Bistro",
        "image_position": "left"
      },
      "animation": { "type": "fade-up", "delay": 100 }
    },
    {
      "id": "menu",
      "component": "MenuCategorized",
      "props": {
        "heading": "Menu Istimewa",
        "subheading": "Hidangan fusion halal yang memukau",
        "categories": [
          {
            "name": "Signature",
            "items": [
              {
                "name": "Nasi Kerabu Deconstructed",
                "description": "Nasi kerabu dengan bunga telang, ulam segar, dan ikan bakar — disusun gaya moden",
                "price": "RM 18.90",
                "image_url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/nasi-kerabu.jpg",
                "badge": "Popular"
              },
              {
                "name": "Rendang Burger",
                "description": "Daging rendang juicy dalam roti brioche dengan acar jelatah dan sambal hijau",
                "price": "RM 22.90",
                "image_url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/rendang-burger.jpg",
                "badge": "Popular"
              }
            ]
          },
          {
            "name": "Fusion",
            "items": [
              {
                "name": "Laksa Carbonara",
                "description": "Spaghetti dalam kuah laksa krimi, udang segar, dan taburan kerisik",
                "price": "RM 19.90",
                "image_url": null,
                "badge": null
              }
            ]
          },
          {
            "name": "Pencuci Mulut",
            "items": [
              {
                "name": "Cendol Panna Cotta",
                "description": "Panna cotta santan dengan gula Melaka, cendol, dan kacang merah",
                "price": "RM 12.90",
                "image_url": null,
                "badge": null
              }
            ]
          },
          {
            "name": "Minuman",
            "items": [
              {
                "name": "Teh Tarik Latte",
                "description": "Espresso dicampur teh tarik klasik — perpaduan timur dan barat",
                "price": "RM 9.90",
                "image_url": null,
                "badge": null
              }
            ]
          }
        ]
      },
      "animation": { "type": "fade-up", "delay": 100 }
    },
    {
      "id": "gallery",
      "component": "GalleryMasonry",
      "props": {
        "heading": "Suasana Kami",
        "images": [
          { "url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/interior.jpg", "alt": "Suasana dalaman" },
          { "url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/nasi-kerabu.jpg", "alt": "Nasi Kerabu Deconstructed" },
          { "url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/rendang-burger.jpg", "alt": "Rendang Burger" },
          { "url": "https://xyzcompqrstuv.supabase.co/storage/v1/object/public/websites/khulafa/laksa.jpg", "alt": "Laksa Carbonara" }
        ]
      },
      "animation": { "type": "fade-up", "delay": 100 }
    },
    {
      "id": "testimonials",
      "component": "TestimonialCards",
      "props": {
        "heading": "Apa Kata Pelanggan",
        "reviews": [
          { "name": "Aisha R.", "text": "Rendang burger terbaik yang pernah saya rasa! Anak-anak pun suka.", "rating": 5, "avatar_fallback": "A" },
          { "name": "Farid M.", "text": "Suasana cozy, sesuai untuk family dinner. Laksa carbonara memang unik!", "rating": 5, "avatar_fallback": "F" },
          { "name": "Siti N.", "text": "Harga berpatutan untuk kualiti fusion macam ni. Mesti datang lagi.", "rating": 4, "avatar_fallback": "S" }
        ]
      },
      "animation": { "type": "fade-up", "delay": 100 }
    },
    {
      "id": "contact",
      "component": "ContactSplit",
      "props": {
        "heading": "Hubungi Kami",
        "whatsapp_number": "60173228899",
        "whatsapp_cta": "WhatsApp Kami",
        "address": "No. 12, Jalan Plumbum V7/V, Seksyen 7, Shah Alam",
        "hours": "Selasa - Ahad, 11 pagi - 10 malam",
        "show_map": true,
        "map_query": "Khulafa+Bistro+Shah+Alam",
        "email": "hello@khulafabistro.my"
      },
      "animation": { "type": "fade-up", "delay": 100 }
    },
    {
      "id": "footer",
      "component": "FooterBrand",
      "props": {
        "business_name": "Khulafa Bistro",
        "tagline": "Citarasa Melayu Moden",
        "social_links": [
          { "platform": "instagram", "url": "https://instagram.com/khulafabistro", "icon": "fa-brands fa-instagram" },
          { "platform": "facebook", "url": "https://facebook.com/KhulafaBistroShahAlam", "icon": "fa-brands fa-facebook" }
        ],
        "copyright_year": 2026,
        "powered_by": true,
        "whatsapp_number": "60173228899"
      },
      "animation": { "type": "fade-up", "delay": 0 }
    }
  ],

  "head_assets": [
    "https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap",
    "https://unpkg.com/aos@2.3.4/dist/aos.css",
    "https://cdn.tailwindcss.com",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"
  ],

  "tailwind_config": {
    "theme": {
      "extend": {
        "colors": {
          "primary": "var(--color-primary)",
          "secondary": "var(--color-secondary)",
          "accent": "var(--color-accent)",
          "surface": "var(--color-surface)"
        },
        "fontFamily": {
          "heading": ["Lora", "serif"],
          "body": ["Nunito", "sans-serif"]
        }
      }
    }
  },

  "body_scripts": [
    "https://unpkg.com/aos@2.3.4/dist/aos.js"
  ],

  "init_scripts": [
    "AOS.init({ duration: 800, once: true, offset: 100 });"
  ]
}
```

**How the assembler uses this:**

```
1. Read recipe.head_assets → emit <link> and <script> tags in <head>
2. Read recipe.theme.colors → emit CSS :root { --color-primary: #C2410C; ... }
3. Read recipe.tailwind_config → emit <script>tailwind.config = {...}</script>
4. Read recipe.nav → render sticky nav bar with links + CTA button
5. FOR EACH section in recipe.sections:
   a. Look up section.component in ComponentRegistry ("HeroSplit" → hero/HeroSplit.html)
   b. Load the HTML template for that component
   c. Substitute all {{props.X}} placeholders with section.props values
   d. Wrap in <section id="{{section.id}}" data-aos="{{section.animation.type}}"
              data-aos-delay="{{section.animation.delay}}">
   e. Append to output
6. Read recipe.body_scripts → emit <script src="..."> before </body>
7. Read recipe.init_scripts → emit <script>...</script> after those
8. Return complete HTML string
```

**The difference between Design Brief and Page Recipe:**

| | Design Brief | Page Recipe |
|---|---|---|
| **Who produces it** | AI (Stage 1) | `recipe_builder.py` (deterministic code) |
| **Image references** | Symbolic keys: `"image_key": "gallery_2"` | Resolved URLs: `"image_url": "https://..."` |
| **Component reference** | Short variant: `"variant": "split"` | Full component name: `"component": "HeroSplit"` |
| **Theme data** | Just `"style_dna": "teh_tarik_warm"` | Fully expanded: all colors, fonts, tokens, component_styles |
| **Menu items** | `"source": "supabase"` + fallback | Fully resolved: items fetched from DB, grouped by category |
| **Stored in DB** | Yes (JSONB, for re-editing) | Not stored — regenerated on each render |

---

### Q3. Why 5 Variants Per Section — Combinatorial Math

**The goal:** "billions of unique sites."

The number of unique visual combinations is the product of variants across all sections. With a site using all 7 section types:

| Variants per section | Combinations (7 sections) | x 8 Style DNAs | x 2 color modes |
|---|---|---|---|
| 3 variants | 3^7 = 2,187 | 17,496 | 34,992 |
| **5 variants** | **5^7 = 78,125** | **625,000** | **1,250,000** |
| 8 variants | 8^7 = 2,097,152 | 16,777,216 | 33,554,432 |

**Why not 3:** 35K combinations sounds like a lot, but Malaysian SMBs in the same niche (e.g., nasi kandar) would visually converge fast. Two nasi kandar sites in the same town choosing the same Style DNA would have only 2,187 layout permutations. Not enough.

**Why not 8:** Diminishing returns. Each variant costs ~3 hours to build and must be tested across all 8 Style DNAs (8 visual regression tests per variant). Going from 5 to 8 variants adds:
- 21 more components to build (+63 hours)
- 168 more visual regression combos to test
- Maintenance burden: 56 components vs. 35

**Why 5 is the sweet spot:**

1. **1.25 million unique combinations** with Style DNA + color mode — enough that no two BinaApp sites in any given town should look alike.
2. **35 total components** is buildable by one developer in Phase 1 + Phase 3 (~77 hours combined).
3. Each section type gets meaningful variety:
   - Every section has a **"minimal" variant** for clean/simple businesses
   - Every section has an **"image-heavy" variant** for visual businesses
   - Every section has a **"text-focused" variant** for businesses without photos
   - Remaining 2 slots cover specific use-cases (categorized menus, map contacts, etc.)
4. Content variation multiplies further — the AI writes unique taglines, about text, and CTA copy per business. Two sites with identical layout but different content still look distinct.

**True uniqueness number with content variation:**

```
5^7 layouts × 8 style DNAs × 2 color modes × ∞ AI-written content
= effectively unlimited unique sites
```

If we need more in the future, adding 1 new variant to each section type (going from 5 to 6) adds 7 components and takes combinations from 1.25M to 4.5M — a cheap upgrade.

---

### Q4. Failure Mode: Stage 1 Returns Invalid JSON

**Three-tier recovery strategy.** Each tier is tried in sequence — we never crash or return an error to the user unless all three tiers fail.

```
┌───────────────────────────────────────────────────────────┐
│  TIER 1: Fix & Retry (same model)                         │
│                                                           │
│  AI returns text that isn't valid JSON or fails Pydantic  │
│  ↓                                                        │
│  Extract JSON from response (strip markdown fences,       │
│  find first { ... } block, fix trailing commas)           │
│  ↓                                                        │
│  If Pydantic still fails:                                 │
│  → Retry ONCE with the validation error appended:         │
│    "Your previous response had these errors:              │
│     - sections[2].variant must be one of: grid, cards..." │
│  → Send to SAME model (not a fallback)                    │
│  → Max 1 retry per model                                  │
│                                                           │
│  Cost: ~$0.005 extra (just the retry call)                │
│  Time: +3-5 seconds                                       │
│  Success rate: ~95% (most JSON errors are minor)          │
├───────────────────────────────────────────────────────────┤
│  TIER 2: Fallback model                                   │
│                                                           │
│  If Tier 1 failed on GLM → try DeepSeek                   │
│  If Tier 1 failed on DeepSeek → try Qwen                  │
│  Same prompt, same retry logic                            │
│                                                           │
│  Uses existing fallback chain from ai_service.py          │
│  _call_glm() → _call_deepseek() → _call_qwen()           │
│                                                           │
│  Cost: ~$0.01 extra                                       │
│  Time: +5-10 seconds                                      │
│  Success rate: ~99% (different model usually succeeds)    │
├───────────────────────────────────────────────────────────┤
│  TIER 3: Default brief (zero AI)                          │
│                                                           │
│  ALL models failed to produce valid JSON (network down,   │
│  all APIs rate-limited, etc.)                             │
│  ↓                                                        │
│  Build a default DesignBrief deterministically:            │
│  - business.name = request.business_name                  │
│  - business.type = detected from keywords in description  │
│  - business.tagline = "{name} — {type} di {location}"     │
│  - business.about = first 2 sentences of description      │
│  - sections = standard set for that business type:        │
│      restaurant → hero + about + menu + gallery + contact │
│      salon → hero + about + gallery + testimonial + contact│
│      etc.                                                 │
│  - All variants set to Variant 1 (the default)            │
│  - style_dna = auto-detected from business type           │
│                                                           │
│  Cost: $0.00                                              │
│  Time: <100ms                                             │
│  Quality: Basic but functional — user can regenerate later│
│                                                           │
│  ⚠️ We do NOT fall back to V1 pipeline.                   │
│     V1 would also fail (same AI APIs are down).           │
│     The default brief gives a working site immediately.   │
└───────────────────────────────────────────────────────────┘
```

**Why NOT fall back to V1:**
V1 uses the same AI models. If GLM + DeepSeek + Qwen all failed for Stage 1, they'll fail for V1's HTML generation too. The default brief is strictly better than a V1 error page.

**Logging:**
Every tier transition is logged with the original error, model used, and time spent. This feeds into a dashboard so we can track AI reliability rates.

---

### Q5. The 8 Style DNAs — Malaysian-Flavored Names

Each Style DNA gets a marketing name in Bahasa Malaysia, a target niche, and full colour palette.

| # | Key | Marketing Name | Target Niche | Primary | Secondary | Accent | Background | Surface | Text | Mode |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `teh_tarik_warm` | **Teh Tarik Warm** | Family restaurants, nasi kandar, bakeries, warung | `#C2410C` | `#78350F` | `#FED7AA` | `#FFFBF5` | `#FFFFFF` | `#1C1917` | light |
| 2 | `pandan_fresh` | **Pandan Fresh** | Health food, organic, salad bars, vegan, grocery | `#16A34A` | `#166534` | `#DCFCE7` | `#FAFFFE` | `#FFFFFF` | `#1A2E1A` | light |
| 3 | `kopi_hitam` | **Kopi Hitam** | Premium cafes, fine dining, exclusive lounges, steakhouse | `#D4AF37` | `#8B7355` | `#2A1F0E` | `#0A0A0A` | `#1A1A1A` | `#F5F5F0` | dark |
| 4 | `sambal_berani` | **Sambal Berani** | Street food, burger joints, mamak, sports bars, events | `#EF4444` | `#F59E0B` | `#FEF3C7` | `#FFFFFF` | `#FFF7ED` | `#18181B` | light |
| 5 | `sutera_putih` | **Sutera Putih** | Bridal, photography, fashion boutique, luxury salon | `#18181B` | `#3F3F46` | `#F4F4F5` | `#FFFFFF` | `#FAFAFA` | `#18181B` | light |
| 6 | `lampu_neon` | **Lampu Neon** | Gaming cafes, nightlife, tech shops, bubble tea, K-pop | `#8B5CF6` | `#06B6D4` | `#1E1B4B` | `#030712` | `#111827` | `#F9FAFB` | dark |
| 7 | `warisan_emas` | **Warisan Emas** | Traditional Malay, kuih shop, batik, cultural centres | `#B45309` | `#78350F` | `#FDE68A` | `#FFFDF5` | `#FFFFFF` | `#292524` | light |
| 8 | `ombak_biru` | **Ombak Biru** | Spa, wellness, seafood, beach cafe, resort, clinic | `#0891B2` | `#164E63` | `#CFFAFE` | `#F8FDFF` | `#FFFFFF` | `#0C1A22` | light |

**Font pairings per Style DNA:**

| Style DNA | Heading Font | Body Font | Vibe |
|---|---|---|---|
| Teh Tarik Warm | Lora | Nunito | Warm serif + soft sans |
| Pandan Fresh | Plus Jakarta Sans | Inter | Modern geometric clean |
| Kopi Hitam | Playfair Display | DM Sans | Luxury serif + neutral |
| Sambal Berani | Bebas Neue | Roboto | Bold condensed + workhorse |
| Sutera Putih | Cormorant Garamond | Inter | Elegant thin serif + minimal |
| Lampu Neon | Space Grotesk | Inter | Techy geometric + neutral |
| Warisan Emas | Playfair Display | Poppins | Traditional serif + friendly |
| Ombak Biru | Source Serif 4 | Open Sans | Calm transitional + readable |

**How the names map from old templates:**

| Old Template Key | New Style DNA Key | Name Change |
|---|---|---|
| `warm_cozy` | `teh_tarik_warm` | Warm & Cozy → Teh Tarik Warm |
| `fresh_clean` | `pandan_fresh` | Fresh & Clean → Pandan Fresh |
| `elegance_dark` | `kopi_hitam` | Elegance → Kopi Hitam |
| `bold_vibrant` | `sambal_berani` | Bold & Vibrant → Sambal Berani |
| `minimal_luxe` | `sutera_putih` | Minimal Luxe → Sutera Putih |
| `neon_night` | `lampu_neon` | Neon Night → Lampu Neon |
| `malay_heritage` | `warisan_emas` | Warisan Melayu → Warisan Emas |
| `ocean_breeze` | `ombak_biru` | Ocean Breeze → Ombak Biru |
| `word_explosion` | *DROPPED* | Gimmick — text animation broke on mobile |
| `ghost_restaurant` | *DROPPED* | Gimmick — content vanishing confused users |

---

### Q6. Phase 1 Breakdown — Exact Hours

**Total: 30 hours.** Here is every task with its estimate and what "done" means.

| # | Task | Hours | Definition of Done |
|---|---|---|---|
| 1 | **Pydantic schemas: `DesignBrief`** | 2.0h | `DesignBrief`, `BusinessInfo`, `SectionSpec`, `FeatureFlags` models. All fields typed. Validators for: whatsapp format, variant must match section type, image_keys reference existing keys in image_map. 10+ unit tests passing. |
| 2 | **Pydantic schemas: `PageRecipe`** | 2.0h | `PageRecipe`, `PageMeta`, `ThemeTokens`, `RenderedSection`, `NavConfig` models. Validator: every `section.component` must exist in `ComponentRegistry`. 10+ unit tests passing. |
| 3 | **Style DNA data files** | 3.0h | 8 JSON files in `frontend/src/lib/style-dna/`. Each contains: colors (11 tokens), fonts (heading, body, weights, CDN URL), tokens (border-radius, shadows, spacing), component_styles (button, card, nav, section). `index.ts` barrel export. Python-side mirror in `backend/app/schemas/style_dna.py` for recipe_builder. |
| 4 | **`SectionWrapper.tsx`** | 1.5h | Shared wrapper: applies `id`, `data-aos`, `data-aos-delay`, section padding, max-width container. Accepts `children`. Used by all 35 section components. |
| 5 | **`ThemeProvider.tsx`** | 1.5h | Reads `ThemeTokens`, injects CSS `:root { --color-primary: ...; --font-heading: ...; }`. Wraps the entire preview. Also exports a `themeToCSS(theme): string` function for the static HTML renderer. |
| 6 | **`ComponentRegistry.ts`** | 1.0h | Maps string names to lazy-loaded components: `{ "HeroSplit": () => import("./hero/HeroSplit") }`. Exports `getComponent(name): Component` and `getAllComponentNames(): string[]`. |
| 7 | **`HeroCentered.tsx`** | 2.0h | Full-bleed image background, centered text overlay with gradient scrim, primary + secondary CTA buttons. Mobile: stacked, image height reduced. Accepts all HeroProps. |
| 8 | **`AboutStory.tsx`** | 2.0h | Image left (or right via prop), heading + paragraphs right. Mobile: image stacks above text. Rounded image with shadow. |
| 9 | **`MenuGrid.tsx`** | 2.5h | 3-column grid (2 on tablet, 1 on mobile). Each card: image top, name, description, price badge. Handles missing images gracefully (shows gradient + icon). Reads from `items[]` prop. |
| 10 | **`GalleryMasonry.tsx`** | 2.0h | CSS columns masonry (2 col mobile, 3 col desktop). Images with rounded corners, hover scale effect. Lazy loading with `loading="lazy"`. |
| 11 | **`TestimonialCards.tsx`** | 1.5h | 3-card grid (1 on mobile). Each card: quote text, reviewer name, star rating (Font Awesome stars), avatar fallback circle with initial. |
| 12 | **`ContactSimple.tsx`** | 1.5h | Centered card with: WhatsApp button (green, with icon), address with map pin icon, operating hours with clock icon, optional email. |
| 13 | **`FooterSimple.tsx`** | 1.0h | Dark bar with: business name, copyright year, "Powered by BinaApp" link, optional social icons row. |
| 14 | **Component unit tests** | 3.5h | Each component: renders without crash, applies theme CSS variables, responsive classes present, required props validated, accessible (alt text, aria labels). 7 components × ~5 tests each = ~35 tests. |
| 15 | **Integration smoke test** | 2.0h | Render the full Khulafa Bistro Page Recipe through all 7 components in sequence. Verify: no missing props warnings, no broken images, mobile viewport renders correctly. Screenshot comparison with manual approval. |
| | **TOTAL** | **30.0h** | |

**Parallel work possible:** Tasks 1-3 (schemas + style DNA) have no dependency on tasks 4-6 (shared components). Tasks 7-13 (section components) depend on tasks 4-6. Tasks 14-15 depend on everything.

```
Week 1:  [1,2,3] in parallel ──────────────── 3h (longest of the three)
         [4,5,6] in parallel ──────────────── 1.5h
         [7,8,9,10] sequentially ──────────── 8.5h
Week 2:  [11,12,13] sequentially ─────────── 4h
         [14] tests ──────────────────────── 3.5h
         [15] smoke test ─────────────────── 2h
```

**Calendar estimate:** ~4 working days at 8h/day if done by one developer.

---

### Q7. Likeliest Way Phase 1 Breaks BinaApp — And Mitigation

**Phase 1 does NOT touch production code.** It only creates new files:
- `backend/app/schemas/recipe.py` (new file)
- `backend/app/schemas/style_dna.py` (new file)
- `frontend/src/components/website-sections/*` (new directory)
- `frontend/src/lib/style-dna/*` (new directory)

The existing generation pipeline (`ai_service.py`, `generate.py`, `create/page.tsx`) is untouched until Phase 2. So Phase 1 **cannot break production** — it's purely additive.

**But here are the realistic risks and mitigations:**

#### Risk 1: Schema Design is Wrong (LIKELIHOOD: HIGH)

The DesignBrief schema locks in the contract between AI output and renderer. If we get the field names, nesting, or variant list wrong, Phase 2 will require a painful schema migration.

**Mitigation:**
- Before writing code, manually write Design Briefs for 5 real BinaApp customer sites (different business types). If the schema can't express all 5, it's wrong.
- Keep the schema versioned (`"$schema": "design_brief_v1"`) so we can evolve it without breaking stored briefs.
- The `content` field inside each `SectionSpec` is a `dict` (not rigidly typed per section type) — this gives us flexibility to add fields later without schema changes.

#### Risk 2: Components Look Bad Across All 8 Style DNAs (LIKELIHOOD: MEDIUM)

A `HeroCentered` component that looks great with Teh Tarik Warm might look terrible with Lampu Neon (dark mode, neon colors, different font weights).

**Mitigation:**
- Task 15 (smoke test) explicitly renders every component with at least 3 Style DNAs.
- Components use CSS variables exclusively (`var(--color-primary)`, not hardcoded hex). This guarantees theme switching works mechanically — only aesthetic issues remain.
- Fix aesthetic issues per-DNA using the `component_styles` object in the Style DNA (e.g., Lampu Neon can specify `"card": "... border border-purple-500/20"` while Teh Tarik Warm uses `"card": "... shadow-md"`).

#### Risk 3: New Dependencies Conflict with Existing Frontend (LIKELIHOOD: LOW)

Adding new components to `frontend/src/components/` could conflict with existing imports, Tailwind class purging, or bundle size.

**Mitigation:**
- New components live in `components/website-sections/` — completely isolated namespace. No existing imports reference this directory.
- No new npm dependencies — components use only Tailwind (already installed) + Font Awesome (already loaded via CDN).
- Components are tree-shaken: only imported when the `ComponentRegistry` resolves them via dynamic `import()`.

#### Risk 4: Scope Creep into Phase 2 (LIKELIHOOD: HIGH)

The temptation to "just wire up" the pipeline while building components. This would create an incomplete, untested V2 path alongside V1.

**Mitigation:**
- Hard rule: Phase 1 PR contains **zero changes** to `generate.py`, `ai_service.py`, or `create/page.tsx`.
- Phase 1 components are tested in isolation (Storybook-style: pass props manually, render in test harness).
- Phase 1 is merged to `main` as a standalone PR. Phase 2 starts from a clean branch.

#### Summary: What Could Actually Go Wrong

| Risk | Likelihood | Impact to Users | Mitigation |
|---|---|---|---|
| Schema design is wrong | High | Zero (no users see it yet) | Test with 5 real customer sites before coding |
| Components look bad with some Style DNAs | Medium | Zero (not live yet) | Smoke test across 3+ DNAs, CSS variable architecture |
| Dependency conflicts | Low | Zero (isolated directory) | No new npm deps, tree-shaken imports |
| Scope creep into Phase 2 | High | Low (could delay timeline) | Hard rule: no production file changes in Phase 1 PR |

**Bottom line:** Phase 1 is the safest possible phase. It ships zero changes to production code. The likeliest problem is getting the schema wrong — which we catch by testing against real customer data before writing a single component.
