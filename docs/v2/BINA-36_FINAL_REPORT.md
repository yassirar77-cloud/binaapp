# BINA-36 Design Quality Sprint — Final Report

**Date:** 2026-05-16  
**Sprint:** 4-week Design Quality Sprint (3 workstreams)  
**Goal:** Visual variety, animation polish, and photo-first onboarding

---

## Status Overview

| Workstream | Branch | Status | Merged |
|-----------|--------|--------|--------|
| A — Typography Variety | `feat/bina36-typography` | ✅ Complete | `9739929` into `feat/chat-nav-link` |
| B — Animation Choreography | `feat/bina36-animation` | ✅ Complete | `f85333a` into `feat/chat-nav-link` |
| C — Photo Upload UX | `feat/bina36-photo-upload-ux` | ✅ Complete | Awaiting Yassir review (BINA-37) |

---

## Workstream A — Typography Variety (5 New Style DNAs)

**Branch:** `feat/bina36-typography`  
**Commits:** 4 commits (64a6f98 → dd33edd)  
**Files changed:** 9 files, +2,258 lines

### New Style DNAs Added

| Key | Display Font | Body Font | Personality |
|-----|-------------|-----------|-------------|
| `pasar_malam_neon` | Bebas Neue 700 | Inter 400/500/700 | Bold, urban, vibrant — mamak/late-night |
| `kampung_serene` | Cormorant Garamond 400/500/600i | Noto Serif 400/600 | Elegant, traditional — warung/heritage |
| `kopitiam_nostalgia` | Playfair Display 400/700 | Source Serif Pro 400/600 | Classical, warm sepia — kopitiam |
| `streetfood_bold` | Anton 400 | DM Sans 400/500/700 | Impact, contrast, fast — food truck |
| `fine_dining_obsidian` | Fraunces 400/700 | Inter 400/500 | Fine dining, gold accents, deep contrast |

### Verification

**md5sum determinism check:**
```
7f3ffb690f487a89790ca19fcfdca199  docs/previews/test_pasar_malam_neon.html
49cc72852032e7fc02088e424d9d9d99  docs/previews/test_kampung_serene.html
ea6720ff886ed18535e2c1027b30e0cd  docs/previews/test_kopitiam_nostalgia.html
4086a77228b90063b9df1e0266cd77cc  docs/previews/test_streetfood_bold.html
94d1f217413876a3b10e1240f712cbf3  docs/previews/test_fine_dining_obsidian.html
```

**Tests:** 21/21 recipe schema tests passing (updated style_dna count from 8 → 13)

**Preview files:** `docs/previews/test_{style_dna_key}.html` — all visually distinct from `teh_tarik_warm` baseline

### Self-audit
- ✅ Full theme tokens (colors, spacing, shadows) per style DNA — not just fonts
- ✅ `_head_links()` dynamically loads only fonts needed for active style DNA
- ✅ CSS variables `--font-heading` / `--font-body` referenced correctly
- ✅ Commit messages formatted `(BINA-36-A)`
- ⚠️ Reviewer note: Font loading relies on Google Fonts CDN — offline/firewall environments will fall back to system fonts

---

## Workstream B — Animation Choreography

**Branch:** `feat/bina36-animation`  
**Commits:** 4 commits (c32227b → 082bc7f)  
**Files changed:** 30+ files, significant changes to `html_renderer.py`

### What Was Built

1. **`backend/app/data/animation_tokens.py`** — New file defining per-style-DNA animation personality:
   - `teh_tarik_warm`: 700ms, soft easing `cubic-bezier(0.22, 1, 0.36, 1)`, stagger 100ms
   - `pasar_malam_neon`: 400ms, snappy `cubic-bezier(0.34, 1.56, 0.64, 1)`, stagger 60ms
   - `kampung_serene`: 900ms, dignified `cubic-bezier(0.4, 0, 0.2, 1)`, stagger 150ms
   - `kopitiam_nostalgia`: 800ms, graceful `cubic-bezier(0.25, 0.46, 0.45, 0.94)`, stagger 120ms
   - `streetfood_bold`: 350ms, bouncy `cubic-bezier(0.68, -0.55, 0.265, 1.55)`, stagger 50ms
   - `fine_dining_obsidian`: 1000ms, deliberate `cubic-bezier(0.165, 0.84, 0.44, 1)`, stagger 200ms

2. **AOS replaced** with custom `IntersectionObserver` — removed CDN dependency, replaced all `data-aos="fade-up"` with `data-reveal`

3. **Page entrance choreography:**
   - Nav fades down from -20px (delay 0ms)
   - Hero text fades up from +30px (delay 200ms, duration × 1.2)
   - Hero image scales from 0.95 (delay 300ms, duration × 1.4)
   - CTA buttons stagger up (delay 400ms + stagger)
   - Scroll-triggered IO reveals thereafter

4. **All 20+ existing variant previews regenerated** with new animation system

### Verification
- **Manual test plan:** `docs/v2/animation_test_plan.md` — browser-by-browser checklist for Yassir
- **Screen recordings:** Not captured programmatically (headless env limitation) — test plan covers all animation checkpoints
- ✅ All variant previews regenerated without build errors

### Self-audit
- ✅ Animation tokens cover all 6 style DNAs including new ones from Workstream A
- ✅ AOS CDN dependency removed — no external animation library
- ✅ Commit messages formatted `(BINA-36-B)`
- ⚠️ Reviewer note: Animation verification requires a browser — static HTML inspection alone won't confirm timing. Use `docs/v2/animation_test_plan.md`.

---

## Workstream C — Photo Upload Onboarding UX

**Branch:** `feat/bina36-photo-upload-ux` (tracked from `feat/chat-nav-link`)  
**Issue:** [BINA-37](/BINA/issues/BINA-37)  
**Commits:** 4 commits (6a0bab7 → 3564049)  
**Files changed:** 11 new files, all in `frontend/src/` — zero backend changes

### What Was Built

4-step onboarding wizard at `/onboarding`:

| Step | Route | File |
|------|-------|------|
| 1 — Photo Upload | `/onboarding/upload` | `app/onboarding/upload/page.tsx` |
| 2 — AI Dish Names | `/onboarding/dishes` | `app/onboarding/dishes/page.tsx` |
| 3 — Style DNA | `/onboarding/style` | `app/onboarding/style/page.tsx` |
| 4 — Generate | `/onboarding/generate` | `app/onboarding/generate/page.tsx` |

**Supporting files:**
- `hooks/useOnboardingState.ts` — localStorage-persisted state (survives browser back)
- `app/onboarding/ProgressBar.tsx` — "1 of 4 — Foto" progress indicator
- `app/api/dish-suggest/route.ts` — Next.js API route proxying Claude Haiku vision

**Photo slots:** Hero (1) + Menu (4) + Interior (1, optional)  
**Validation:** JPG/PNG only, max 5MB, min 800×600  
**Storage:** Supabase Storage bucket `restaurant-photos/{user_id}/{slot}.jpg`  
**AI suggestions:** Claude Haiku with image URL — JSON output: `{name, description, suggested_price_rm}`  
**Fallback:** All failures degrade gracefully — manual entry available at every step

### Verification

- ✅ `npx next build` → compiled successfully (no new errors)
- ✅ `git diff feat/chat-nav-link -- backend/` → empty (backend untouched)
- ✅ Dependencies added: `react-dropzone`, `@anthropic-ai/sdk`
- ✅ Mobile-responsive: single-column layout, tap-to-select on mobile

### Self-audit
- ✅ No Halal Certified claims
- ✅ Legal compliance copy untouched
- ✅ Commit messages formatted `(BINA-36-C)`
- ⚠️ **Blocker for full E2E:** Supabase Storage bucket `restaurant-photos` must exist — wizard falls back to local preview URLs if bucket is absent
- ⚠️ **Blocker for AI suggestions:** `ANTHROPIC_API_KEY` must be set in Vercel env vars — empty form fields with manual entry if absent

---

## What's Incomplete or Rough

| Item | Status | Notes |
|------|--------|-------|
| Animation screen recordings | ❌ Not captured | Headless env — manual test plan provided instead |
| Workstream C font loading in style cards | ⚠️ CSS only | Google Fonts not bundled via `next/font` — visual approximation only |
| Supabase bucket provisioning | ⚠️ Manual step | Board must create `restaurant-photos` bucket in Supabase dashboard |
| `ANTHROPIC_API_KEY` in Vercel | ⚠️ Manual step | Board must add env var for dish suggestions to work in production |
| Workstream C PR merge | ⏳ Pending review | `feat/bina36-photo-upload-ux` awaiting Yassir approval |

---

## PR References

- **Workstream A:** PR #611 — "BINA-36-A: Typography variety (5 new style DNAs)" → merged `9739929`
- **Workstream B:** Merged as `f85333a` into `feat/chat-nav-link`
- **Workstream C:** `feat/bina36-photo-upload-ux` → PR to be opened against `feat/chat-nav-link`

---

*Report authored by BinaApp CTO agent. Sprint duration: ~2 weeks wall-clock (A+B sequential, C parallel).*
