# Generation Upgrade Plan — Lovable-Tier AI Website Generation

> ## ⏸️ PARKED (2026-07-04)
> M0 (quality harness: output lint, golden prompts, side-by-side screenshot
> gallery) and M1 (intent extraction → DesignBrief brief generator → recipe
> pipeline, flag-gated with auto-fallback) are **built and working** on branch
> `claude/generation-upgrade-m0-m1` — 383 tests passing, ruff clean, verified
> end-to-end. **Not merged; old pipeline stays default and serves everyone**
> (`GENERATION_RECIPE_PIPELINE_ENABLED` defaults OFF, no Render env vars set).
>
> Why parked: M1 output skewed **too dark for Malaysian F&B** — the DNA
> selection favors the dark Style DNAs (pasar_malam_neon, fine_dining_obsidian,
> kopi_hitam) too often, while the target market mostly wants bright, warm,
> family-friendly sites. Before M1 can beat the old pipeline it needs
> bright-default tuning (bias DNA selection to light DNAs unless the user
> clearly asks for dark) plus the M3 recipe widening (palette derivation,
> layout tokens, more editorial variants). Revisit later; everything below
> remains the plan of record when we do.

**Status:** AUDIT + PLAN ONLY — no production code written in this session.
**Date:** 2026-07-04
**Scope:** Upgrade BinaApp's AI website generation so that a Malaysian F&B SME describing their business gets output that looks designer-built, not templated.
**Branch:** `claude/generation-upgrade-audit-fr913t` (this document is the only change).

---

## Executive Summary

BinaApp today runs a **monolithic-prompt pipeline**: one giant instruction string is sent to DeepSeek, which writes an entire HTML page (up to 24,000 output tokens) in one shot. Quality depends entirely on how well a general-purpose LLM follows a very long prose prompt — and it follows it inconsistently.

Meanwhile, a second, much better-architected system already exists in the repo and is **dormant**: the V2 component-recipe pipeline (`DesignBrief → recipe_builder → html_renderer`) with 13 hand-tuned Style DNAs, ~31 implemented section variants, per-DNA animation choreography, and a deterministic assembler. Its planned "Stage 1" — the LLM that turns a user description into a `DesignBrief` — **was never built**. The only thing between BinaApp and a categorically better pipeline is that missing stage plus a quality pass on the recipes.

**Honest verdict (short version):** the current architecture *can* reach Lovable-tier for this product's domain without a rebuild — because the domain is narrow (single-page Malaysian F&B sites), the deterministic assembler already exists, and the gap is composition/wiring, not fundamentals. The full verdict is at the end of this document.

---

# PHASE 1 — AUDIT

## 1.1 The four pipelines (critical framing)

| # | Pipeline | Status | Entry point |
|---|----------|--------|-------------|
| 1 | **Async job pipeline in `main.py`** | **LIVE / DEFAULT** — what the `/create` UI drives | `POST /api/generate/start` → poll `GET /api/generate/status/{job_id}` → `POST /api/publish` |
| 2 | `simple/` router (`/api/generate`, dual/best/strategic/multi-style modes) | **DEAD** — `simple_router` is never mounted in `main.py`; its modules survive only as imported helper libraries | `backend/app/api/simple/router.py` |
| 3 | v1 authenticated CRUD | Mounted, alternate surface (editor / AI-rebuild flows, not `/create`) | `POST /api/v1/websites/generate`, `/api/v1/websites/{id}/publish` |
| 4 | **V2 component-recipe pipeline** | **NOT LIVE** — deterministic test endpoint only; Stage-1 AI unbuilt | `POST /api/v2/generate-test` (hand-written `DesignBrief` JSON in) |

Pipelines 1 and 3 share the same AI core: `AIService.generate_website()` in `backend/app/services/ai_service.py`. The docs (`AI_WEBSITE_GENERATION_IMPLEMENTATION.md`, `docs/V2_ARCHITECTURE.md`) are stale: they describe the unmounted `simple/` endpoints as the API and V2 as in-progress. The multi-style / dual / strategic generation modes are **unreachable from the UI**.

## 1.2 End-to-end flow map (live pipeline) — every file involved

### The flow

1. **Frontend** — `frontend/src/app/create/page.tsx` (~2,790 lines). Collects description, business name, features (WhatsApp / map / delivery / contact / social), `image_choice` (`none`/`upload`/`ai`), uploaded images, dish names, `language` (`ms`/`en`), `color_mode`, optional `template_id`. Sends to `/api/generate/start` (L746), polls `/api/generate/status/{jobId}` (L843), publishes via `/api/publish` (L1105).
2. **Job start** — `backend/app/main.py::start_generation()` @2373: rate limit + duplicate-build debounce, inserts a `generation_jobs` row, dispatches `asyncio.create_task(run_generation_task(...))` @2672.
3. **Generation task** — `main.py::run_generation_task()` (~L1820–2372): builds `WebsiteGenerationRequest`, calls `ai_service.generate_website()` @1928 with a progress callback, applies image/WhatsApp safety guards, builds `menu_items` from **user uploads only** (never scraped from AI HTML), calls `template_service.inject_integrations`, mints a website UUID and persists a **`pending_payment` draft** row in `websites` (so the widget's `data-website-id` resolves pre-publish), marks the job `completed` with the HTML.
4. **AI core** — `ai_service.py::generate_website()` @4495:
   - Step 0: `extract_menu_item_names` (DeepSeek `deepseek-chat`) @2124
   - Step 1: Stability AI images in parallel (hero + one per menu item) @4655 — skipped when user uploads or `image_choice=none`
   - Step 2: `_build_strict_prompt()` @2688 → `_call_deepseek(model=deepseek-reasoner)` @4972, max_tokens 24,000, temp 0.2, 300 s timeout
   - Step 3: validation + truncation retry (temp 0.1) @5057; Qwen fallback if DeepSeek dies
   - Step 4: optional Qwen copy refine @5081 (non-blocking, 60 s); Qwen CSS refine exists behind `AI_QWEN_CSS_REFINE_ENABLED` (default **off**)
   - Alternate: `template_id` short-circuits to `_generate_website_from_template()` @4724 (copywriter-JSON prompt + `{{placeholder}}` fill)
5. **Publish** — `main.py::publish_website()` @3103: `repair_html` + `is_html_balanced` gate (422), email-verification gate, draft promotion by re-extracting the embedded `data-website-id`, quota gate, chat + delivery widget injection, upsert `websites` row, upload HTML to Supabase Storage `websites/{subdomain}/index.html`, `increment_usage("create_website")`.
6. **Serving** — `backend/app/middleware/subdomain.py::subdomain_middleware` @396: subdomain lookup (60 s TTL cache) → lock check → free-tier gate → fetch HTML from Storage (60 s cache) → `_inject_widgets` @287 → `HTMLResponse` with `Cache-Control`.

### File inventory (live path)

| File | ~Lines | Role |
|---|---|---|
| `frontend/src/app/create/page.tsx` | 2,790 | Builder UI, job polling, publish call |
| `backend/app/main.py` | 4,555 | Live endpoints: `start_generation` @2373, `run_generation_task` @~1820, `get_generation_status` @905, `publish_website` @3103 |
| `backend/app/services/ai_service.py` | 5,396 | AI core: prompts, DeepSeek/Qwen calls, validation, retries, template fill |
| `backend/app/services/design_system.py` | 762 | 9 business-type palettes + font pairings + `LAYOUT_TEMPLATES` injected into the prompt |
| `backend/app/services/stability_service.py` | 425 | Stability AI image generation |
| `backend/app/services/templates.py` | 3,742 | Feature detection, widget/integration injection, image & layout safety guards |
| `backend/app/services/template_gallery.py` | 1,030 | Prebuilt animated templates + prompt injections |
| `backend/app/services/menu_service.py` | 634 | Menu items from user uploads |
| `backend/app/services/html_repair.py`, `backend/app/utils/html_balance.py` | — | Publish-time structural gates |
| `backend/app/services/storage_service.py` | 263 | Storage upload/delete/tombstone |
| `backend/app/middleware/subdomain.py` | 614 | Subdomain serving + widget injection |
| `backend/app/data/malaysian_food_images.py` | — | 14 curated dish-image pools (~110 images) |
| `backend/app/data/malaysian_prompts.py` | 294 | Curated Stability prompts per dish |

### File inventory (dormant V2 recipe system)

| File | ~Lines | Role |
|---|---|---|
| `backend/app/schemas/recipe.py` | 328 | `DesignBrief` / `PageRecipe` Pydantic schemas, `VALID_VARIANTS`, enums |
| `backend/app/schemas/style_dna.py` | 451 | 13 hardcoded Style DNA definitions (fonts, 11 colors, Tailwind class strings, radii, shadows) |
| `backend/app/data/animation_tokens.py` | 122 | Per-DNA animation personality (duration/easing/stagger/hover-lift) |
| `backend/app/services/recipe_builder.py` | 279 | `DesignBrief → PageRecipe` (deterministic) |
| `backend/app/services/html_renderer.py` | 2,358 | 31 `@_component` renderers → single HTML string |
| `backend/app/api/v2/generate_test.py` | 91 | Test-only endpoint (mounted in `main.py` @131–132) |
| `backend/tests/test_recipe_schemas.py`, `test_assembler_e2e.py` | — | Existing test coverage |
| `frontend/src/types/recipe.ts`, `frontend/src/components/website-sections/**` | — | React mirrors of the schema/components (unused in live flow) |
| `docs/previews/*.html` | 33 files | Rendered variant + Style-DNA demos |

## 1.3 Prompt quality audit

**Providers:** DeepSeek (`deepseek-chat` utility, `deepseek-reasoner` for main HTML) + Qwen (`qwen-plus-latest` refine/fallback, `qwen-vl-max` image analysis). No Anthropic/OpenAI in the live path. All raw `httpx` calls to OpenAI-compatible endpoints.

### The main prompt: `_build_strict_prompt()` (`ai_service.py:2688–3064`)

What it does well — it already contains real art direction:
- A 5-step modular type scale with exact px/rem ranges
- "ONE dominant colour + ONE accent" rule, explicit ban on purple-on-white SaaS look
- Font lock (no Inter/Roboto/system-ui; only the fonts injected in HEAD)
- Strict 8px spacing system
- Card-readability-if-image-fails rule
- Hard BM/EN language branch (`ai_service.py:2811–2827`) with ✅/❌ examples ("Laman Utama", "Pesan Sekarang", "JANGAN gunakan Bahasa Inggeris")
- "Pengusaha Muslim" badge wording enforced via `design_system.py:331` ("never use 'Halal' or 'Halal Certified'")

### Where user design intent gets lost (the core problem)

1. **Bucketing destroys nuance.** The free-text description is collapsed by `_detect_type`/`detect_business_type` (`ai_service.py:2707–2716`) into ~9 business-type buckets, which then **override** layout, fonts, palette, and hero variant (`:2721–2728`). "A moody late-night mamak with neon signs and 90s kopitiam tiles" and "a bright family mamak" both become `food` → same `LAYOUT_TEMPLATES["food"]` fixed section order labelled "MUST FOLLOW".
2. **Palette ignores adjectives.** `get_color_palette(design_type, color_mode)` picks from 9 canned palettes by bucket + light/dark. Only two style adjectives are honored ("minimal"/"bold" via `style_note` @2932–2943). "Playful", "luxurious", "retro", "pastel", "earthy" — all silently dropped.
3. **One shot, 24k tokens, no structure.** The model must simultaneously be copywriter, art director, and front-end dev across ~15k output tokens. Failure modes observed in the code's own defenses: truncation retries, `was_truncated` / `needs_manual_review` diagnostics persisted to `generation_jobs`, html balance repair at publish. The guardrails exist *because* the output is unreliable.
4. **Design guidance is prose, not tokens.** The prompt asks for an 8px system and a type scale but nothing verifies the output followed them. There is no post-hoc design lint.
5. **`color_mode` can be silently overridden** by a selected template (`ai_service.py:4790–4801`).
6. **The Halal-wording rule is not global.** Enforced in `design_system.py` and the V2 renderer (`html_renderer.py:353–357` etc. render "Pengusaha Muslim"), but `template_gallery.py:435` still says "use Halal badge prominently" — an inconsistency to clean up, and there is no automated output check for the forbidden string.

### Other prompts in the flow

| Prompt | Location | Role |
|---|---|---|
| Copywriter JSON (template path) | `ai_service.py:4088–4135` | Fixed-schema JSON content poured into `{{placeholders}}` |
| Truncation/repair retries | `ai_service.py:5051–5057`, `5317–5323` | Low-temp re-ask |
| Food image prompts (Stability) | `ai_service.py:1507–1547`, `1882–1891` | Malaysian-cuisine image prompt writer |
| Menu/category name extraction | `ai_service.py:2137`, `2245` | "EXACTLY {n} names" extractors |

## 1.4 V2 component-recipe audit: reusable vs ceiling

### What's genuinely reusable (keep, this is the foundation)

- **The two-schema contract** (`DesignBrief` → `PageRecipe`) is exactly the right seam: LLM creativity on one side, deterministic guarantees on the other. Pydantic validation, WhatsApp number normalization, image-key resolution, and hero+footer invariants already exist.
- **The 13 Style DNAs** are hand-tuned, Malaysia-native (teh_tarik_warm, pasar_malam_neon, kopitiam_nostalgia, kampung_serene, fine_dining_obsidian…) with full token sets — colors, fonts + CDN URLs, radii, shadows, component-level Tailwind strings, and **matching animation personalities** (`animation_tokens.py`: fine-dining 1000 ms deliberate easing vs streetfood 350 ms bouncy). This is design capital most competitors don't have.
- **The renderer's quality floor**: verified output (`docs/previews/test_pasar_malam_neon.html`) uses CSS custom properties, a custom IntersectionObserver reveal system (AOS removed), entrance choreography, per-DNA Google Fonts loading. Deterministic = never truncated, never unbalanced, md5-stable.
- **Existing tests**: `test_recipe_schemas.py`, `test_assembler_e2e.py` (brief → recipe → valid HTML).

### What's a ceiling (fix or accept)

- **Closed set of 13 DNAs, no interpolation.** A user's brand color can't be honored; `color_mode` is the only knob. → fixable (M3: palette derivation layered onto a DNA).
- **Declared-but-unimplemented variants silently render as `<!-- Unknown component -->`** (`html_renderer.py:286–288`): `hero:video/minimal/slider`, `about:minimal`, `menu:cards`, `gallery:lightbox`, `testimonial:grid/minimal`, `footer:simple/cta` are in `VALID_VARIANTS` but have no renderer. An LLM told the full variant list would emit briefs that render holes. → must fix before wiring Stage 1.
- **Fixed vertical rhythm**: hardcoded `padding_map` per section, fixed 1280 px max width, fixed 72 px nav spacer. Every site has the same skeleton silhouette. → medium fix (layout tokens per DNA).
- **Tailwind Play CDN at runtime** — a prototyping tool in production output (the renderer even hides the Tailwind "Play" badge). Works, but adds ~100 KB JS, FOUC risk, and an external dependency on every published site. → medium fix (build-time CSS or vanilla CSS emission).
- **Section order comes from the brief, nav from a fixed label table** — no compositional variety beyond variant choice.

### Is the recipe approach itself the limit?

**No — for this product, it's the right approach; the recipes and the missing LLM stage are the limit.** Lovable-class tools feel bespoke because an LLM makes *many small design decisions* (composition, palette, copy voice, imagery pairing) inside a strong design system — not because the LLM writes every line of CSS. BinaApp's live pipeline has the LLM writing every line of CSS (unreliable), and the V2 pipeline has the LLM making zero decisions (unbuilt). The upgrade is to meet in the middle: LLM decides *within a widened, validated decision space*; the assembler guarantees the floor. The one place raw-LLM-HTML genuinely beats recipes — a truly bespoke hero composition — can be added later as a sandboxed "island" (M4) without giving up the floor.

## 1.5 Output-quality gaps vs Lovable-tier

| Dimension | Live pipeline today | V2 assembler today | Lovable-tier target |
|---|---|---|---|
| **Typography scale** | Prompt asks for 5-step scale; adherence unverified, drifts | Per-DNA fonts + weights, consistent | Distinctive display/body pairing per brand, fluid `clamp()` scale, optical alignment |
| **Spacing system** | Prompt asks for 8px grid; unverified | Hardcoded uniform section padding | Tokenized rhythm that *varies by DNA* (dense streetfood vs airy fine-dining) |
| **Color palette** | 9 canned palettes by business bucket; adjectives ignored | 13 fixed DNAs, no brand-color input | Derived palette: user words + optional brand color → validated (contrast-checked) ramp on a DNA base |
| **Layout variety** | Fixed `LAYOUT_TEMPLATES` order per bucket; LLM freelances the rest | Section order from brief; same skeleton rhythm | Composed variety: hero/menu/gallery variants chosen for the *story* ("since 1985" → heritage timeline), asymmetry, overlap, full-bleed moments |
| **Responsive quality** | LLM-written, inconsistent; mobile breakage possible | Coarse but reliable md:/lg: breakpoints | Mobile-first verified at 375/768/1280; no horizontal scroll, thumb-reachable CTAs |
| **Imagery** | Stability per-dish + Unsplash residue replacement; fusion dishes lack pool coverage | 14 curated pools, seeded deterministic pick | Art-directed images per DNA (lighting/plating style matches mood); duotone/overlay treatments; correct aspect handling |
| **Micro-interactions** | AOS-style attributes, LLM-dependent | Custom reveal system + per-DNA choreography (genuinely good) | Keep V2's system; add hover states, sticky nav w/ backdrop blur, reduced-motion respect (partially present) |
| **Section composition** | Whatever the LLM writes that day | 31 solid but same-y variants | Editorial-tier variants (the 9/10-rated `contact_card_overlay`, `reviews_pull_quote` show the bar); texture accents (subtle geometric/batik patterns), varied section transitions |

**Cross-cutting gap:** no automated design QA anywhere — nothing measures whether output followed the type scale, contrast, spacing, language, or wording rules.

## 1.6 DO-NOT-BREAK zones (explicit)

Any generation change must leave all of the following byte-for-byte untouched in behavior:

### Billing / subscription
- `backend/app/services/subscription_service.py` — `TIER_PRICES`/`ADDON_PRICES`/`TIER_LIMITS` (:20–62), `check_limit` (:533), `increment_usage` (:642), addon overflow/credits (:724–943)
- `backend/app/services/plan_features.py` — `get_plan_features` (:28), `can_publish_subdomain` (:72)
- `backend/app/middleware/subscription_guard.py` — route middleware + DI guards
- `backend/app/services/toyyibpay_service.py`, `payment_service.py`, `api/v1/endpoints/payments.py` (incl. draft promotion `_promote_pending_draft_for_user` :767–1050), `api/v1/endpoints/subscription.py`
- Tables: `subscriptions`, `subscription_plans`, `addon_purchases`

### Quota
- `usage_tracking` table writes; AI-usage increments after success (`websites.py:438–452`, `max_ai_images` budget cap :405–423); website-slot increment at publish (`main.py:3447–3452`)
- The `pending_payment` exclusion in `get_actual_resource_counts` (:262–289) — drafts must not consume slots

### Publish
- `main.py::publish_website` @3103 — all gates in order: `repair_html`/`is_html_balanced` (422), email verification, draft promotion via embedded `data-website-id`, `check_limit`, `can_publish_subdomain`, widget injection, `websites` upsert, Storage upload `websites/{subdomain}/index.html`, usage increment
- `simple/publish.py` (imported helpers: `inject_delivery_widget_if_needed` :739, `inject_chat_widget_if_needed` :786, `fix_website_id_in_html` :697, subdomain blocklist/validators)
- Draft-promotion path in `payments.py` (ToyyibPay callback)

### Serving
- `backend/app/middleware/subdomain.py` — the whole middleware: subdomain parse, reserved list, `/order/*` redirect, 60 s lookup + HTML caches, lock check (never cached), free-tier gate (fails closed), Storage fetch + legacy key fallback, tombstone guard, orphan auto-recovery, `_inject_widgets` @287, `apply_layout_safety_guard`, Cache-Control headers
- `backend/app/services/website_lock_checker.py`, `storage_service.py` (tombstones!)

### The output contract a new generator MUST honor
1. Emit **one complete, balanced HTML document string** (passes `is_html_balanced`; unbalanced output → 422 at publish).
2. Embed `data-website-id="<uuid>"` (+ `const WEBSITE_ID`, `websiteId:`, `/delivery/<uuid>` patterns) — draft promotion and widget targeting re-extract and rewrite these.
3. Contain a `</body>` tag — serve-time and publish-time widget injectors splice before it.
4. Not carry its own copies of `delivery-widget.js` / `chat-widget.js` / `binaapp-widget-container` in conflicting form — the serve-time injector strips and re-adds these markers (`subdomain.py:310–331`).
5. Land in **both** `websites.html_content` (DB) and Storage `{subdomain}/index.html` — serving reads Storage; dashboard reads DB.
6. Never scrape menu items from HTML — menu comes from the `menu_items` table / user uploads.
7. Never flip a live site's `status`, never resurrect tombstoned (`.deleted`) subdomains.

### Existing published sites
Serving reads Storage; nothing in this plan regenerates or rewrites stored HTML. The dangerous surfaces that *do* touch existing sites — admin bulk republish (`simple/publish.py:820–916`), AI rebuild (`website_rebuild.py`), bulk HTML fixers (`websites.py:1029–1407`) — are explicitly **out of scope** for every milestone below.

---

# PHASE 2 — GAP ANALYSIS

## 2.1 Gap classification

| # | Gap | Class | LLM-quality limit or pipeline limit? |
|---|---|---|---|
| G1 | User adjectives/mood dropped by business-type bucketing | **Prompt-engineering (cheap)** | Pipeline — the code discards intent before the LLM sees it |
| G2 | Palette can't reflect user words or brand color | **Prompt + small module (cheap→medium)** | Pipeline (canned palettes) |
| G3 | Design rules unverified (type scale, spacing, contrast, wording) | **Cheap** — output lint, no LLM change | Pipeline |
| G4 | Truncation/imbalance failures from 24k-token one-shot | **Architecture (expensive if kept monolithic; free once recipes carry structure)** | LLM limit *in the monolithic shape* — no prompt fixes this reliably |
| G5 | Same-y layouts, fixed section skeleton | **Recipe/component upgrade (medium)** | Pipeline |
| G6 | V2 variant catalog holes (declared but unimplemented → HTML comments) | **Medium** | Pipeline bug |
| G7 | No LLM design decisions in V2 path (Stage 1 missing) | **Architecture (the big one, but the seam exists)** | Pipeline |
| G8 | Closed 13-DNA set, no brand-color/mood interpolation | **Medium** | Pipeline |
| G9 | Imagery not art-directed per mood; fusion-dish pool gaps | **Medium** (data + prompt work) | Pipeline/data |
| G10 | Tailwind Play CDN in production output | **Medium** | Pipeline |
| G11 | Bespoke hero compositions beyond variant catalog | **Expensive** (sandboxed LLM islands) | Genuine LLM-quality frontier — DeepSeek/Qwen writing raw creative CSS is the least reliable part; scope tightly |
| G12 | "Halal" wording rule not enforced globally (template_gallery inconsistency, no output check) | **Cheap** | Pipeline |
| G13 | Copy is functional but flat (BM voice, hooks, storytelling) | **Prompt-engineering (cheap)** — dedicated copy pass with voice guidance per DNA | Mostly prompt; partially LLM ceiling for BM nuance (DeepSeek's BM is serviceable; worth A/B-ing Qwen for BM copy) |

**Honest read on LLM-quality vs pipeline limits:** roughly 80% of the visible quality gap is pipeline-inflicted (intent bucketing, canned palettes, missing Stage 1, no design QA). The genuine LLM ceilings are: (a) one-shot 24k-token HTML reliability — unfixable by prompting, sidestepped by recipes; (b) bespoke creative CSS (G11) — real but deferrable; (c) BM copy nuance (G13) — mitigable with voice-primed prompts and model A/B.

## 2.2 Benchmark: what "Lovable-tier" means for a mamak site

**Test prompt (BM):** *"Saya nak website untuk Restoran Mamak Bintang, mamak 24 jam di Bangi. Famous dengan roti canai garing dan teh tarik. Suasana meriah, ramai student lepak malam-malam. Nak gaya retro neon sikit."*

### What we produce today (live pipeline)

- Bucketed to `food` → fixed section order (hero → menu → about → gallery → contact → footer), one of 9 canned "food" palettes (warm orange family), hero variant from a fixed list. **"Retro neon" and "student lepak malam" are discarded** — nothing maps mood words to design decisions.
- One DeepSeek shot writes the whole page: typography usually follows the prompt's scale but drifts (ad-hoc sizes appear); spacing roughly 8px-ish but inconsistent between sections; occasional truncation → retry → sometimes `needs_manual_review`.
- Stability generates competent dish photos; hero is typically centered-text-over-dark-overlay — the most generic composition on the web.
- BM copy is grammatical but flat: "Selamat Datang ke Restoran Mamak Bintang. Kami menyediakan makanan yang lazat."
- Animations: basic fade-ups if the LLM remembered them.
- Net: a **6/10 template-feel site**. Functional, mobile-OK, WhatsApp button works — but visibly AI-generated and interchangeable with every other food site we emit.

### What Lovable-tier looks like for the same prompt

- **First viewport sells the vibe:** `pasar_malam_neon` DNA base — near-black plum background, neon pink/teal accents, Bebas Neue display type; asymmetric hero with a full-bleed night-market-lit roti canai shot, subtle grain overlay, "24 Jam · Pengusaha Muslim" badge, glowing "Pesan Sekarang" WhatsApp CTA. The "retro neon" request is *visible in 0.5 seconds*.
- **Typography with intent:** display font at clamp(2.5rem→4.5rem) tight leading; menu items in an editorial list with dotted price leaders; caption type for "Sejak 1998".
- **Palette derived, not canned:** neon DNA base + teh-tarik cream secondary pulled from the user's own words, every pair contrast-checked.
- **Composition tells the story:** hours section leads with "Buka Sekarang · Tutup 6 pagi" (today-focus variant — already built!); testimonial pull-quote from a student; gallery as a masonry of night shots; menu features "Roti Canai Garing" as chef's pick with a bigger card.
- **Motion matches mood:** 400 ms snappy staggered reveals (already in `animation_tokens.py` for this DNA), hover lifts on menu cards, sticky translucent nav.
- **BM copy with voice:** "Port lepak paling happening di Bangi. Roti canai garing sampai pagi." — colloquial register matched to a student mamak, not brochure-speak.
- Net: a **9/10 designer-feel site**. Every element of this description is achievable with the V2 assembler + a good Stage-1 brief + the M3 upgrades below. Nothing requires the LLM to write raw HTML.

---

# PHASE 3 — MILESTONE PLAN

## Guiding rules (all milestones)

- **Zero changes** to billing, quota, publish, or serving logic (§1.6). All flag branches live inside `AIService.generate_website()` or new modules — `main.py`'s job/publish handlers, middleware, and subscription code are untouched in every milestone.
- New pipeline output honors the **same contract** (§1.6): one balanced HTML string with embedded `data-website-id`, `</body>`, widget-compatible markers.
- Old pipeline stays **default**; every milestone independently ships and independently rolls back by flag flip or revert of additive files.
- Existing published sites: untouched (no regeneration surfaces in scope).
- BM/EN preserved; "Pengusaha Muslim" wording enforced and now machine-checked.

## M0 — Quality harness + golden set (foundation, ~3 days)

*You can't claim "Lovable-tier" without a way to see and gate quality.*

- **New files only:**
  - `backend/scripts/golden_prompts.py` — 12 fixed briefs: mamak, kopitiam, modern cafe, catering, warung, fine dining × BM/EN × light/dark samples
  - `backend/scripts/generate_golden_set.py` — runs any pipeline over the golden set → `docs/previews/golden/{pipeline}/{prompt}.html`
  - `backend/scripts/screenshot_golden.py` — Playwright screenshots at 375/768/1440 px
  - `backend/tests/test_output_lint.py` — **design lint** run on any generated HTML: forbidden strings ("Halal Certified", "Sijil Halal", "JAKIM"), language check (BM output contains no stray EN nav labels and vice versa), `data-website-id` present, `</body>` present, balanced HTML, no `font-family: Inter/Roboto`, WCAG AA contrast on token pairs
- **Files touched:** none in production. **Test plan:** lint suite green on current previews. **Visual QA:** screenshot gallery reviewed by Yassir — this becomes the approval artifact for every later milestone. **Rollback:** delete scripts. **Risk: none.**
- **Ops note (not code):** `deepseek-chat`/`deepseek-reasoner` model IDs are deprecated **2026-07-24** (route to V4 Flash after). Set `DEEPSEEK_MODEL`/`DEEPSEEK_MODEL_PRO` env pins explicitly before that date and re-run the golden set to catch behavior drift. This is an env change on Render, no code.

## M1 — Intent extraction + prompt V3 for the live pipeline (cheap win, ~1 week)

*Stop discarding the user's design intent; ship a visibly better monolithic prompt while the recipe path matures.*

- **New files:** `backend/app/services/intent_extractor.py` (one cheap `deepseek-chat` call: description → structured mood/adjectives/era/brand-color/audience JSON), `backend/app/services/prompt_v3.py` (rewritten strict prompt consuming intent JSON: mood-mapped palette guidance, expanded voice/copy direction per register, negative-space and composition instructions, self-check checklist footer).
- **Files touched:** `ai_service.py` only — a flag branch at the top of the prompt-build step: `if AI_PROMPT_V3_ENABLED and user allowlisted: use prompt_v3`. `design_system.py` untouched (v3 carries its own token data). Fix `template_gallery.py:435` Halal wording (one string).
- **Flag:** `AI_PROMPT_V3_ENABLED` (env, default false) + `AI_V3_USER_ALLOWLIST` (comma-separated user IDs/emails — founder first).
- **Test plan:** unit tests for intent extractor (fixed fixtures), golden set generated both pipelines, output lint green.
- **Visual QA checklist:** side-by-side golden gallery; verify mood words visibly change output; type scale sampled on 3 sites; mobile 375 px pass; BM copy register check.
- **Rollback:** flag off (instant); revert = delete 2 files + one branch in `ai_service.py`.
- **Risk: low.** Cost: +1 small LLM call (see §5).

## M2 — Stage 1 brief generator: wire the V2 pipeline end-to-end (the unlock, ~2 weeks)

- **New files:** `backend/app/services/brief_generator.py` — the missing Stage 1: intent JSON + description + features + images → `DesignBrief` (JSON mode, `deepseek-chat`), Pydantic-validated with one retry-on-validation-error; DNA selection rubric (mood → DNA mapping table); copy written into section content slots with per-DNA voice guidance. `backend/app/services/recipe_pipeline.py` — orchestrator: brief → `build_recipe` → `render_html` → post-process to meet the output contract (embed `data-website-id`, integration markers) → return through the same `WebsiteGenerationResponse` shape (`html_content`, `ai_images_count`, `meta_*`).
- **Files touched:** `ai_service.py` (flag branch inside `generate_website()`: `GENERATION_RECIPE_PIPELINE_ENABLED` + allowlist → `recipe_pipeline`, with **automatic fallback to the old pipeline on any exception**); `html_renderer.py` + `recipe.py` (close G6: implement the ~8 missing variant renderers *or* remove them from `VALID_VARIANTS`, and make unknown-component a hard error in tests); `recipe_builder.py` (accept uploaded-image URLs in `image_map` — already supported by schema).
- **Explicitly NOT touched:** `main.py`, middleware, subscription/publish/storage services.
- **Test plan:** brief-generator unit tests with recorded LLM fixtures; property test — any valid `DesignBrief` renders balanced HTML with zero `<!-- Unknown component -->`; e2e assembler tests extended; output lint on golden set; verify draft-promotion contract by asserting `data-website-id` embed matches the old pipeline's patterns.
- **Visual QA checklist:** all 13 DNAs exercised across golden set; nav labels correct BM/EN; WhatsApp CTA resolves; images load; animations fire; reduced-motion respected; 375/768/1440 px screenshots.
- **Rollback:** flag off; fallback-on-exception means a broken recipe path degrades to today's behavior, not an outage.
- **Risk: medium** (new code path end-to-end) — mitigated by allowlist + auto-fallback + the deterministic assembler being un-truncatable.

## M3 — Design-system deepening: palette derivation, layout tokens, editorial variants (~2–3 weeks, parallelizable after M2)

- **New files:** `backend/app/services/palette_deriver.py` (DNA base + user mood/brand color → interpolated, WCAG-validated `ColorTokens`; pure Python color math, no LLM, deterministic); `backend/app/data/layout_tokens.py` (per-DNA rhythm: section padding scale, max-width, density — kills the uniform skeleton); ~8–10 new editorial-tier variant renderers (hero diagonal-split, hero neon-marquee, menu chef's-pick feature card, about heritage-timeline-photo, texture/pattern accent partials).
- **Files touched:** `style_dna.py` (add fields, defaults preserve current values → md5-stable for old briefs), `html_renderer.py` (consume layout tokens; new renderers additive), `recipe_builder.py` (thread palette override), `brief_generator.py` (expose new variants + palette intent).
- **Also:** replace Tailwind Play CDN with emitted vanilla CSS *for the recipe path only* (old pipeline untouched) — removes external dependency and FOUC (G10).
- **Test plan:** snapshot determinism for unchanged briefs; contrast property tests on 1,000 random palette derivations; lint suite.
- **Visual QA checklist:** golden gallery re-review — the "same-y skeleton" complaint specifically re-scored; per-DNA density visibly differs; brand-color prompt honored.
- **Rollback:** recipe pipeline flag still gates everything; within it, `PALETTE_DERIVATION_ENABLED` sub-flag defaults to DNA-exact colors.
- **Risk: low-medium** (pure-deterministic additions behind two flags).

## M4 — Bespoke hero islands + art-direction pass (the last 10%, ~2 weeks, optional)

- **New files:** `backend/app/services/hero_island.py` — one tightly-scoped LLM call may write a bespoke hero *section only*, sandboxed: output validated as a fragment (no `<script>`, no external assets, scoped `<style>` under a namespaced class, token-only colors), rejected → fall back to catalog variant. `backend/app/services/art_director.py` — a cheap review call: screenshot-free, reviews the *brief* (not HTML) for composition quality and suggests variant swaps before rendering.
- **Files touched:** `recipe_pipeline.py` only.
- **Test plan:** adversarial fixtures (script injection, external fonts, unbalanced fragments → all rejected); fallback rate logged.
- **Visual QA:** hero-only gallery; approve/reject per DNA.
- **Rollback:** `HERO_ISLAND_ENABLED` sub-flag, default off.
- **Risk: medium** — this is the only milestone that reintroduces LLM-written HTML, hence the sandbox and fragment validation. Ship last, judge by data.

## M5 — Imagery art direction + multi-variant preview (~1–2 weeks)

- **New files:** `backend/app/data/image_art_direction.py` (per-DNA Stability prompt modifiers: lighting, plating, palette echo); fusion-dish pool additions (data-only, closes the documented gap in `docs/V2_PROGRESS_NOTES.md`).
- **Files touched:** `recipe_pipeline.py` (generate 2–3 briefs per request — cheap at ~$0.001 each — return as `variants[]`, which the frontend and `generation_jobs` **already support**: `get_generation_status` @956 already wraps HTML into a variants array); `stability_service.py` prompt-side only.
- **Test plan:** variants array shape matches existing frontend contract; job-status polling unchanged.
- **Visual QA:** pick-your-style gallery of 3 per golden prompt.
- **Rollback:** variant count env `RECIPE_VARIANT_COUNT=1`.
- **Risk: low.**

### Sequencing & independence

M0 → M1 → M2 → M3 → M5, with M4 optional after M3. Each milestone ships value alone: M1 improves today's default-adjacent path; M2 stands alone behind its flag even if M3–M5 never happen; M3/M5 are additive to M2. Any single milestone can be reverted without touching the others (flags are independent; files are additive).

## 4. Feature-flag strategy

- **Master flags (env, read in `ai_service.py`/new modules only):** `AI_PROMPT_V3_ENABLED`, `GENERATION_RECIPE_PIPELINE_ENABLED` — both default **false**. Old pipeline remains the default for all users until you flip them.
- **Allowlist:** `AI_V3_USER_ALLOWLIST` / `RECIPE_PIPELINE_USER_ALLOWLIST` (user IDs or emails) — lets you dogfood on your own account in production while every real user stays on the old path. Matches the existing env-flag idiom (`AI_QWEN_CSS_REFINE_ENABLED`).
- **Sub-flags:** `PALETTE_DERIVATION_ENABLED`, `HERO_ISLAND_ENABLED`, `RECIPE_VARIANT_COUNT`.
- **Auto-fallback:** any exception in the new path logs + falls back to the old pipeline within the same request — a broken flag never becomes a user-facing outage.
- **Existing published sites:** flags only affect *new generation requests*. Serving reads stored HTML from Storage; no milestone writes to existing sites' storage keys or DB rows. Bulk-republish/rebuild surfaces are out of scope. **100% untouched by construction.**
- **Cutover:** flip default only after golden-set visual approval + ≥2 weeks of allowlisted usage with fallback rate <2%.

### Old-pipeline kill criteria (we will not maintain two pipelines forever)

The legacy monolithic-prompt pipeline gets **deleted** (not just disabled) when ALL of the following hold:

1. **Volume:** ≥200 production generations have run through the recipe pipeline (flag on, `RECIPE_PIPELINE_USER_ALLOWLIST=*`), covering both languages and at least 4 of the 6 golden scenarios' business types.
2. **Fallback rate:** <2% of those generations fell back to the legacy pipeline (measured from the `🧪 recipe pipeline failed` log lines / `step_timings` presence on `generation_jobs`), sustained over the most recent 30 days.
3. **Compliance:** zero forbidden-wording or unbalanced-HTML lint failures in production output over the same window (the lint report is written into each golden run's meta.json; production spot-checks via `generation_jobs.html`).
4. **Visual sign-off:** Yassir has reviewed a full golden-set `review.html` (all 12 prompts, desktop + mobile, OLD vs NEW) and signed off in writing that NEW ≥ OLD on every prompt — no exceptions carried.
5. **Support signal:** no open user complaints attributable to recipe-pipeline output.

Deletion scope when criteria are met: `_build_strict_prompt` and the legacy generation branch of `generate_website` in `ai_service.py`, plus the then-dead prompt-support blocks in `design_system.py`. The publish/serving/quota surfaces are untouched by the deletion (they never knew which pipeline produced the HTML). Until every criterion is met, the legacy pipeline stays as the automatic fallback target.

## 5. LLM cost impact per generation

Verified pricing (July 2026): DeepSeek V4 Flash $0.14/M input (cache miss) / $0.28/M output; V4 Pro $0.435/M in / $0.87/M out ([DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing)). Qwen-Plus intl $0.40/M in / $1.20/M out ([Alibaba Model Studio](https://www.alibabacloud.com/help/en/model-studio/model-pricing)). Stability image costs are unchanged by this plan and excluded (they dominate total cost at ~$0.03/image × ~5 but are orthogonal).

**Today (text LLM, per generation):**

| Call | Model | Tokens (in/out, typical) | Cost |
|---|---|---|---|
| Menu-name extraction | deepseek-chat | 0.5k / 0.2k | ~$0.0002 |
| Main HTML | deepseek-reasoner (Pro pricing) | ~7k / ~15k (+ reasoning tokens billed as output) | ~$0.016–0.022 |
| Truncation retry (~20% of runs) | same | ~7k / ~15k | +~$0.004 expected |
| Qwen copy refine | qwen-plus | ~15k / ~8k | ~$0.016 when it runs |
| **Total** | | | **≈ $0.025–0.045** (~RM 0.11–0.20) |

**After M2 (recipe path):**

| Call | Model | Tokens | Cost |
|---|---|---|---|
| Intent extraction | deepseek-chat (V4 Flash) | 1k / 0.3k | ~$0.0002 |
| Brief generation (copy included) | deepseek-chat (V4 Flash) | 3k / 3k | ~$0.0013 |
| Validation retry (~15%) | same | | +~$0.0002 expected |
| Assembly | deterministic | 0 | $0 |
| **Total** | | | **≈ $0.002 (~RM 0.01) — a ~93% reduction** |

**Add-ons:** M1 prompt V3 on the old path: +$0.0002 (intent call) and ~+10% main-call input ≈ **+$0.001**. M4 hero island: +~$0.002/run. M5 three variants: 3 × brief ≈ **$0.005 total — still 8–10× cheaper than one generation today**. Margins improve at every milestone; the only scenario that raises cost is running *both* pipelines for the same request (A/B), which is a deliberate, temporary testing choice.

## 6. Constraints compliance

- **"Pengusaha Muslim" only:** already enforced in `design_system.py` and the V2 renderer; M0 adds a hard lint (forbidden: "Halal Certified", "Sijil Halal", "JAKIM") run in CI on golden output; M1 fixes the stale `template_gallery.py:435` instruction; brief-generator prompt (M2) carries the rule explicitly.
- **Bilingual BM/EN:** the recipe path inherits `recipe_builder.NAV_LABELS` (BM/EN table) and `DesignBrief.language`; brief-generator writes copy in the requested language with register guidance; M0 lint checks language purity.
- **Malaysian F&B aesthetic:** the 13 Style DNAs are already Malaysia-native and are the *core* of this plan, not a casualty of it — the upgrade widens expression around them (palette derivation, layout rhythm, imagery art direction) rather than importing Silicon-Valley SaaS defaults. The prompt V3 explicitly keeps the existing anti-"generic SaaS" bans.

---

## Honest Verdict

**Yes — the current architecture can reach Lovable-tier for BinaApp's domain, and it does not need a pipeline rebuild; it needs the pipeline you already half-built to be finished and fed.** The live monolithic-prompt path is a dead end for reliability (no prompt makes a 15k-token one-shot HTML emission consistently designer-grade — the truncation retries and repair gates in your own code are the evidence), but the V2 recipe system is precisely the architecture Lovable-class tools use in spirit: an LLM making bounded creative decisions inside a hand-tuned, deterministic design system. Its missing Stage-1 brief generator is roughly two weeks of work, the design capital (13 Malaysia-native Style DNAs, animation choreography, 31 variants) already exists, and the upgrade is *cheaper* per generation than today by ~93%, not more expensive. The honest caveats: the fixed variant catalog caps the top end — the last 10% of "bespoke" feel needs the sandboxed LLM hero-islands of M4, which is the only genuinely risky piece and is deferrable; DeepSeek/Qwen BM copy voice needs A/B validation; and the deprecation of `deepseek-chat`/`deepseek-reasoner` model IDs on 2026-07-24 is an unrelated ops risk to handle this month regardless. Rebuild: no. Finish, widen, and gate what exists: yes.
