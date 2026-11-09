# Quality system for generated sites

A week of one-off fixes on agp.binaapp.my (mustard prices on a red brand, a
spice strip covering the hero CTA, map buttons clipped out of sight, a
call link rendered as bare text, three full-width level blocks on a phone)
had one cause: the model writes the layout, and every layout bug is found
by a human looking at a screenshot. This document is the plan to replace
that with a system: code owns layout, a gate owns "does it render right",
a golden suite owns "did we regress", and the create page owns "did the
merchant give us what a good site needs".

## Stage 1 — Deterministic sections (`app/services/sections/`)

**What.** Every structural section is rendered by code from the merchant's
data: nav, hero (photo or solid), options strip (spice levels), info
banners (free refill, charges), menu slot (filled by the existing
`menu_fidelity` block), coming soon, about, location (address card + the
`binaapp-maps-slot` the worker fills), contact (CTAs + `binaapp-contact-slot`),
footer. The model contributes exactly two things:

- **Theme** — through the existing design plan (Pass 1): palette, display
  and body fonts, and a style variant (`soft`, `outline`, `editorial`)
  derived from the plan's direction or the merchant's style chip.
  `sections/theme.py` repairs every token for contrast once (text and the
  primary read on both surfaces, `on_primary` reads on the primary) and
  emits one stylesheet. The primary is the plan's accent, never the
  darkened secondary.
- **Copy** — one small JSON call (`sections/copy.py`): kicker, headline,
  sub-headline, menu lead, about title + 1–3 paragraphs, tagline, contact
  lead. Hard length caps, tags stripped, and any field that carries a fact
  the brief does not (an RM amount, a phone number, a founding year, a
  rating) falls back to deterministic copy built from the merchant's own
  sentences.

**Flag.** `BINAAPP_PAGE_MODE=deterministic` (default) composes;
`BINAAPP_PAGE_MODE=freeform` runs the previous model-writes-everything
pipeline with all its guards, untouched. Multi-style previews are composed
too: one copy call, then each plan's theme on the same sections, so the
preview the merchant picks is what the final build renders.

**What it removes.** For composed pages none of the layout guards run
(hero-strip docking, spice-level compaction, call-link styling, map-slot
unclipping, w-full margin fixes, hierarchy repairs, nav-contrast JS):
there is no model-written layout to repair. The validator still runs
(validate only, never a model "repair" rewrite); brief-fact, branding,
SEO and quality-floor passes still run as safety nets.

**Modules.** `spec.py` (SiteSpec from the request + brief facts),
`theme.py` (tokens + CSS), `copy.py` (prompt, parse, fallback),
`render.py` (section renderers; every CTA is icon + label), `compose.py`
(document assembly, section order per vertical). Wired in
`ai_service.generate_website` (`_generate_composed`) and
`generate_plan_variants`.

## Stage 2 — Visual QA gate (`app/services/visual_gate.py`)

**What.** Before a page reaches the merchant, render it in Playwright at
390 px and 1280 px with the floating WhatsApp button and widgets injected
(the gate sees the page the customer sees), screenshot both, and check:

- no horizontal overflow (`scrollWidth > innerWidth`) at either width;
- no element overlapping the hero CTAs, and nothing overlapping the
  floating WhatsApp button (viewport rects at scroll 0 and at the CTA);
- no clipped text (`scrollWidth > clientWidth` on text elements with
  `overflow: hidden`, or text wider than its box);
- contrast ≥ 4.5:1 on every text node (computed colour vs. the effective
  background, images counted as dark);
- every `<img>` loads. The page is walked a screen at a time, every image
  is made eager, awaited (up to `VISUAL_GATE_IMAGE_WAIT_MS`) and
  **decoded** before the screenshot: the first live agp screenshot showed
  every menu card as an empty box, because a `decoding="async"` image had
  loaded but not been drawn. A download that failed is broken (dropped);
  one still arriving is slow (`images_drawn`, soft — never dropped);
- every CTA button has an icon and a label;
- the map iframe is visible with both buttons when an address was given.

Then `qwen3-vl-plus` answers three questions at once:

1. **The page**, as overlapping slices of the mobile screenshot (1400 px
   tall, 250 px shared with the next, up to 10 slices — a 10,000 px page is
   covered to the end): overlapping, tilted, cut-off or unreadable elements.
   A cut-off fails the gate only when the browser measured clipping or
   overflow too. Back-to-back slices cut mamak's menu cards in two and the
   model failed a good page for "cut off at the bottom edge".
2. **Each menu card's own photo** (one crop per card, after its name)
   against its own name. A mismatch drops that photo. On the full page the
   model blamed agp's burger hero on all seven cards ("same burger photo
   used") and seven good photos were dropped.
3. **The hero photo against the business** (name, type, brief, items). A
   mismatch swaps in the photo-free hero (`bs-hero-solid` for a composed
   page; a freeform hero loses its photo and takes the primary colour).

A deterministic check always wins over the model's opinion where they
disagree.

**On failure.** Auto-fix through the existing guards (contrast guard,
broken-image fix, overflow fixes, strip docking) and re-render once; if
still failing, regenerate once — with the first build's images
(`generate_website(reuse_images=response.image_bundle)`: a composed page
redoes only plan, copy and composition, ~20 s instead of the 4–5 minute
image phase), its progress reported in the 93–98 % band; if still failing, the job fails with a merchant-facing
"Sila cuba lagi" and a `VISUAL_GATE_FAIL` log line carrying the check
names. `VISUAL_GATE_MODE=enforce|warn|off` (default `enforce`; `warn` for
sandboxes with no network). Never ship a page that fails the gate.

**Outputs.** Gate report on `generation_jobs.validation.visual_gate`; the
mobile screenshot uploaded (Cloudinary) and its URL on the job row, for
the create page's preview step (stage 4) and the golden suite (stage 3).

## Stage 3 — Golden suite (`backend/tests/golden/`, `scripts/golden_run.py`)

Five fixture merchants: ayam gepuk (agp), mamak, kek, salon, kedai
telefon. `golden_run.py` generates each end to end (job worker semantics:
compose/generate → widgets → gate), writes `site.html`, both screenshots,
the gate report and the `verify_site_menu` checks, and diffs the mobile
screenshot against the stored baseline (pixel diff image kept as a CI
artifact; the diff is for eyes, the gate and the structural checks are
pass/fail, because copy varies between runs).

Workflow `.github/workflows/golden.yml`: nightly (full, with model keys
from secrets) and on every PR that touches `backend/app/services/**`,
`backend/scripts/**`, `backend/tests/golden/**` (offline: no keys, library
theme + fallback copy — still the exact composed layout, still the full
gate). A failing golden job blocks merge once `golden` is added to the
branch protection's required checks (a repo setting, not code).

## Stage 4 — Create-page guards (`frontend/src/app/create/`)

- Multi-line paste into the business-name box routes to the bulk menu
  parser (the name box keeps the first line only when it is not a menu).
- Subdomain auto-suggested from the business name (slug), checked live
  against `GET /api/subdomain/check/{sub}`, with the existing typo warning.
- Hero upload that looks like a poster or menu board (portrait, or the
  server's text-heavy check via a new `POST /api/image/role`) gets a
  warning and a one-tap "use as menu board instead".
- Generate is blocked, not confirmed, for Restoran/Bakeri with 0 named
  menu items (inline message + scroll to the menu rows).
- "Preview before publish": the publish modal shows the mobile screenshot
  from the gate (job row) and the gate summary before the Publish button
  enables.

## How the stages catch this week's agp bugs

| Bug (commit) | Caught by |
|---|---|
| Mustard `--primary-color` from the darkened secondary (78b3e48) | S1 theme (primary = plan accent, contrast-repaired); S2 contrast check; S3 golden agp |
| Spice strip pinned over the hero CTA on mobile (78b3e48) | S1 options strip is in flow; S2 CTA-overlap check |
| Three full-width level blocks on a phone (260ae5f) | S1 chips row; S2 vision review ("unreadable/cut-off") |
| Map slot clipped, both buttons hidden (4f42ee5) | S1 map box never clips; S2 map-visible check; S3 verify_map |
| Call button rendered as bare text (78b3e48, d2fb3fa) | S1 contact CTA is a styled button; S2 icon+label check |
| Footer "Telefon" on a stray line with a dot (5205a6e) | S1 footer renders contact list deterministically |
| Mobile CTA `w-full ml-4` overflow (65cc5c8) | S1 CSS; S2 overflow check; S3 |
| Brand palette locked to yellow from a descriptive mention (4a37803) | S1 theme from plan only; S3 golden agp baseline colours |
| Outline detection missed near-black borders (dd5659a) | S1 variant is chosen, not detected |
| Brief facts (levels, refill, caj, coming soon) dropped with the menu slot (bf3d72e) | S1 renders them as sections; S3 golden checks |
| Menu photo reused in Tentang Kami (4078b4d) | S1 about photo excludes item photos |
| Missing "Gambar hiasan" label (4078b4d) | S1 hero/about label; S2 vision review |
| Set-meal photo as a whole roast chicken / live roosters (3fa99a3, db0c0ee) | S2 vision review photo-vs-name rubric (removes the photo) |
| Signature card without a badge (3b0554d) | S1 (menu block, unchanged); S3 golden agp |
| Image text check silently "pass (unchecked)" on a 404 model (e941c0e) | S2 logs a model failure as a gate warning; S3 nightly fails if the vision step never answers |
| Burger-and-fries hero on agp (first live build, Standard) | hero prompt from the merchant's dishes, not the direction's example; S2 hero-vs-business check → photo-free hero; S3 `hero_prompt_on_subject` + the burger-hero browser test |
| Seven good agp card photos dropped for the hero's burger | S2 judges each card's own crop against its own name |
| mamak failed for menu cards "cut off" at slice edges | S2 overlapping slices; a cut-off needs the measurements to agree |
| Card photos blank in the gate screenshot | S2 waits for every image to load and decode; slow ≠ broken |
| Place name used as the map address (6dd0e9a) | S1 spec uses the resolved address; S3 golden checks the full address |
| Interrupted job left hanging (bff1081) | not a design bug; out of scope |

## Build time

Live agp build on Standard, 2026-11-08 (`TIMING BREAKDOWN`): 362 s of
generation, of which **352 s were images** (8 Z.ai images, one at a time,
~40 s each, the last one cut over to Stability by the 300 s budget), 6 s the
plan, 3 s the copy, 0.01 s the composition; then 47 s in the gate (two
renders and two reviews). mamak: 242 s + a gate regeneration that redid the
whole image phase (304 s). The progress bar's drop from 93 % to 25 % during
that regeneration looked like a worker restart; the logs show one instance,
no restart, memory flat at 185–231 MB of 2 GB.

| step | before | now |
|---|---|---|
| images (8) | 250–352 s (Z.ai serial) | ~80–100 s: two on Z.ai, the rest on Stability in parallel (`IMAGE_PHASE_TARGET_SECONDS`) |
| image checks | ~2 s each, one after another | in parallel (~3 s) |
| plan + copy + compose | ~10 s | ~10 s |
| gate | 30–80 s | ~30–60 s (three reviews at once) |
| gate regeneration | full rebuild, 270–300 s | images reused: plan + copy + compose + gate, ~40–60 s |
| **total** | **7–10 min** | **~2.5–3.5 min** |

## Effort

| Stage | Size | Notes |
|---|---|---|
| 1 Deterministic sections | ~2 days | done in this PR; theme/copy/renderers/compose + wiring + 23 tests |
| 2 Visual gate | ~2 days | Playwright measurement JS, vision call, auto-fix loop, job persistence |
| 3 Golden suite | ~1 day | fixtures, runner, workflow, baselines |
| 4 Create-page guards | ~1.5 days | five guards + preview step + tests |

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `BINAAPP_PAGE_MODE` | `deterministic` | `deterministic` composes pages from data; `freeform` runs the model-writes-everything pipeline and its guards |
| `AI_COPY_TIMEOUT_SECONDS` / `AI_COPY_MAX_TOKENS` / `AI_COPY_TEMPERATURE` | `45` / `900` / `0.7` | the copy call (DeepSeek flash → GLM → Qwen); on timeout the fallback copy ships |
| `VISUAL_GATE_MODE` | `enforce` | `enforce`: a failing page never ships (auto-fix → regenerate once → fail the job); `warn`: report only; `off`: no browser |
| `VISUAL_GATE_VISION_MODEL` | `qwen3-vl-plus` | the reviewer on DashScope (`QWEN_API_KEY`); GLM-4.5V on Z.ai is the fallback |
| `VISUAL_GATE_RENDER_TIMEOUT_SECONDS` / `VISUAL_GATE_VISION_TIMEOUT_SECONDS` | `40` / `60` | per-render and per-review caps |
| `VISUAL_GATE_VISION_TILES` | `10` | how many slices of the mobile screenshot the reviewer sees |
| `VISUAL_GATE_TILE_HEIGHT` / `VISUAL_GATE_TILE_OVERLAP` | `1400` / `250` | slice height and the part each slice shares with the next |
| `VISUAL_GATE_CARD_PHOTOS` | `16` | menu cards whose photo is judged on its own |
| `VISUAL_GATE_IMAGE_WAIT_MS` | `15000` | how long one image may take to arrive before the screenshot |
| `IMAGE_PHASE_TARGET_SECONDS` | `100` | the image phase's target: an image whose turn in the one-at-a-time Z.ai queue would end later goes to Stability at once (parallel, ~5–10 s). `0` = every image waits for Z.ai (the old behaviour; agp's 8 images took 352 s) |
| `ZAI_IMAGE_EXPECTED_SECONDS` | `40` | first guess at one Z.ai image; the build's own measured mean replaces it |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_ALERT_CHAT_ID` | unset | operator alerts (`services/ops_alerts.py`): a build the gate blocked, a start refused with the location question, and a Monday 08:23 MYT weekly summary. Unset = alerts are only logged (`OPS_ALERT …`) |
| `OPS_ALERT_IGNORE_USERS` | unset | comma-separated user ids / emails left out of alerts and the weekly summary (test accounts) |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE` | unset | a Chromium binary for the gate when Playwright's own download is unavailable |
| `PLAYWRIGHT_BROWSERS_PATH` | Render: `/opt/render/project/src/backend/.playwright-browsers` | where `build.sh` installs the Chromium headless shell. It must be inside the project folder: Render discards anything else between the build and the running service |
| `BROWSER_MIN_FREE_MB` | `450` | free container memory required before Chromium is launched; below it the gate is skipped (`VISUAL_GATE_SKIPPED_MEMORY`) instead of risking an out-of-memory restart |
| `VISUAL_GATE_CHROMIUM_ARGS` | unset | extra Chromium flags, appended to the low-memory set |

**Memory.** The Playwright driver plus the Chromium headless shell peak at
roughly 340–410 MB on the agp page (measured as PSS; the desktop capture is
viewport-only in production, the mobile capture full-page for the vision
review). The Render backend's Starter instance has 512 MB and the app uses
160–255 MB of it, so on Starter the guard skips the gate. Every build logs
`GATE_SELFTEST chromium=… gate=… peak_mb=…` (one gate run on the agp page on
Render's build machine) and every boot logs `VISUAL_GATE_BOOT … -> gate WILL
RUN | will be SKIPPED`.

The gate's verdict lives on `generation_jobs.validation.visual_gate` (checks,
vision verdict, fixes, attempt, `preview_mobile_url` of the mobile
screenshot on Cloudinary) and is returned by `GET /api/generate/status/{job}`
as `visual_gate` + `preview_mobile_url`. A `VISUAL_GATE_FAIL` log line
carries the failing check names; `VISUAL_GATE_UNAVAILABLE` means no browser
could render (the page ships, loudly).
