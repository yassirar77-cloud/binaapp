# Designer-grade site generation

Every site a merchant generates should look like a designer made it for
*that* restaurant or shop — not the same template with a new colour. This
document describes the pipeline that replaced single-shot HTML generation:
a design **plan** first, HTML built against it second, a critique gate in
between, and a learning loop that records what merchants did with each
direction.

## Why

All output had converged on one look: cream background, serif display, one
gold/terracotta accent, an italic word in every headline, an ALL-CAPS
eyebrow above every heading, identical rounded cards, fade-up on every
section. Customers could tell. Prompt rules alone did not fix it — the
model drifted back — so the fix is structural: a catalogue of visibly
different directions, deterministic validation and lint, a rotation rule,
and a screenshot critique.

An earlier upgrade was rejected as "too dark, no happy feeling". Malaysian
F&B sites are therefore **bright by default**: dark directions exist only
for merchants who pick *Gelap* or whose brief asks for a dark / night
concept (steakhouse, lounge, cocktail bar).

## Pipeline

```
create form ──► PlanBrief (§0 mapping) ──► Pass 1: design plan (JSON, small model, validated)
                                                 │  fallback: deterministic library plan
                                                 ▼
                     Pass 2: HTML built against the plan (binding spec + anti-template rules
                             + section standards + string table + typography contract)
                                                 │
                     anti-template lint (repairs + failures) ──► screenshot critique (8 criteria)
                                                 │  score < 7 or lint fail → regenerate Pass 2 with the notes, max 2 retries
                                                 ▼
                     best attempt served ──► existing sanitizer / validator / widgets ──► quality floor
                                                 │
                     design_plans row (plan, scores, html hash) ──► outcome (published / edited / regenerated)
```

### Modules

| Module | Role |
|---|---|
| `backend/app/services/design_directions.py` | The direction library (26 directions with `styles` tags, bright/dark theme, palette family, type pairing, hero treatment, signature device), the curated font allowlist and pairing rule, per-vertical section sets. |
| `backend/app/services/design_plan.py` | Pass 1: `PlanBrief` (the create form mapped), the plan prompt, `parse_plans` validation/repair, `fallback_plan`, completeness + listening questions, the Pass 2 binding-spec block. |
| `backend/app/services/design_plan_store.py` | Rolling direction history per category (last 3) and the learning-loop rows (migration 057). Best-effort; mirrors history in-process. |
| `backend/app/services/designer_prompt_blocks.py` | Pass 2 blocks: anti-template rules (§2), typography contract (§4), Malaysian F&B section standards + feature rules (§0/§5), quality floor rules (§8), HEAD contract without AOS. |
| `backend/app/services/site_strings.py` | UI string table keyed by `<html lang>` (ms / en). |
| `backend/app/services/anti_template_lint.py` | Server-side lint: data-aos count, eyebrow count, decorated headlines, arrow CTAs, middle-dot meta, inline heading font-size, fake map cards, placeholder copy, invented hours. Repairs what it can. |
| `backend/app/services/design_critique.py` | Playwright screenshots (1280 + 390), the 8-criterion rubric, vision call, parsing, measured overrides (mobile overflow, hero size), the ≥ 7 / no-score-< 5 gate. |
| `backend/app/services/quality_floor.py` | lang, viewport, reduced-motion, focus-visible, lazy-load + width/height, Tailwind CDN swap when precompiled CSS exists. |
| `backend/app/services/image_intelligence.py` | Hero quality gate, dominant colours, Cloudinary section crops, dish-specific hero prompt cue. |
| `backend/app/cron/design_stats_cron.py` | Weekly `docs/design/direction-stats.md`. |

The wiring lives in `AIService.generate_website` (`_plan_brief_for`,
`_direct_design_plan`, `_run_plan_gate`, `_regenerate_pass2`,
`record_last_plan`) and `AIService.generate_plan_variants` (multi-style).

## §0 — the create form is law

| /create control | Wire key | Plan effect |
|---|---|---|
| Bahasa website | `language` | `<html lang>`, string table, copy language |
| Color theme Cerah / Gelap | `color_mode` | Cerah → bright directions only; Gelap → dark only. The written brief overrides the toggle and the plan's notes say so. |
| Gaya design | `design_style` | Auto → whole library; a pick → directions tagged with that style |
| Arahan untuk designer AI | `design_brief` | Highest priority; the plan quotes the sentences it honoured in `brief_quotes` and `why` |
| Designer bebas / Ikut sistem | `design_freedom` | bebas → custom direction allowed; ikut sistem → library only |
| Apa jenis kedai | `business_type` | Section set + direction subset; Auto → classifier on name + story |
| Multi-style preview + thumbnails | `multi_style` | Three plans, three low-fidelity previews; the pick is refined (`/api/generate/refine`) |
| Nama kedai + Cerita | `business_name`, `description` | Copy source; only facts in the story reach the page |
| Brief completeness < 40% | `/api/generate/listen` | Follow-up questions before planning (no model call) |
| Hero image / prompt | `images`, `hero_image_prompt` | Upload/stock → colour extraction; AI → prompt written from the plan merged with the merchant's words |
| Video latar hero | `hero_video` | Hero forced to photo-full-bleed with `data-binaapp-hero-video`; the video is the load moment |
| Menu items / image source | `menu_items`, `image_choice` | No photos → typographic tiles, never placeholder icons |
| Features | `features.*` | ON = section exists, OFF = it does not. Maps off → address text only. Borang off → no form slot. |
| Nombor WhatsApp | `whatsapp_number` | Empty → no WhatsApp buttons anywhere |
| Cara terima bayaran | `payment.cod/qr` | Footer payment badges and checkout copy only |

## Environment

| Variable | Default | Effect |
|---|---|---|
| `AI_DESIGN_PLAN_ENABLED` | `true` | Two-pass generation. `false` restores the older concept step. |
| `AI_DESIGN_PLAN_TIMEOUT_SECONDS` | `60` | Cap on the plan call; timeout = library plan |
| `DESIGN_CRITIQUE_ENABLED` | `true` | Screenshot + vision critique (needs `ZAI_API_KEY` or `QWEN_API_KEY`) |
| `DESIGN_CRITIQUE_MODEL` | `glm-4.5v` | Vision model on Z.ai; `DESIGN_CRITIQUE_QWEN_MODEL` (`qwen-vl-max`) is the fallback |
| `DESIGN_GATE_MAX_RETRIES` | `2` | Pass 2 regenerations after a failed gate |
| `DESIGN_CRITIQUE_SCREENSHOT_TIMEOUT_SECONDS` | `25` | Playwright render cap; no browser = text-mode critique |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE` | unset | Point Playwright at a system Chromium when the bundled one is missing |
| `DESIGN_PLAN_STORE_ENABLED` | `true` | design_plans reads/writes (needs migration 057) |
| `TAILWIND_PRECOMPILE` | `false` | Replace the Tailwind Play CDN with compiled CSS at publish (needs node + `npx tailwindcss`) |

## Operations

- Apply `backend/migrations/057_design_plans_learning_loop.sql` to Supabase.
- Weekly Render cron: `python cron_runner.py design-stats` → `docs/design/direction-stats.md`.
- Acceptance harness: `python scripts/designer_grade_acceptance.py` (offline checks always; add `--live` with API keys to generate, lint, critique and screenshot ten briefs into `docs/design/screenshots/`).

## Observability

Log lines: `🎨 Plan step`, `🎨 Plan: {...}`, `🎨 Plan adjusted during validation`,
`🧹 Anti-template lint`, `🧑‍⚖️ Critique`, `🔁 Plan gate failed … regenerating`,
`🎯 Plan gate result`, `🧱 Quality floor applied`, `📊 Direction stats`.
`AIService._last_design_plan` and `_last_plan_gate` hold the last plan and gate result.

## Round 2 — after the Dobi Layan Diri test

Reference site: bebe.binaapp.my (Servis, Cerah). Structure was right; the
images, the data and the type hierarchy were not. Each fix has a
regression test that uses the Dobi brief as its fixture.

| Area | What changed | Module |
|---|---|---|
| Images | Every non-F&B prompt starts with a category subject clause (dobi → laundromat and front-load machines; salon → chair, mirror, tools; pakaian → flat-lay/mannequin), F&B wording is scrubbed, and the universal negative rides on every provider: no text, no letters, no logo, no watermark, no people's faces. | `image_subjects.py` |
| Vision check | Each generated image is shown to Qwen-VL (GLM-4.5V fallback): rendered text / food / face / matches category. Fail → one stricter regeneration → drop the image (typographic tile). Rejections are logged with the reason. `IMAGE_CHECK_ENABLED`, `IMAGE_CHECK_QWEN_MODEL`. | `image_vision_check.py`, `AIService._vision_gate_image` |
| Location | Story vs address place tokens (Seksyen N, Taman X, city). `/api/generate/listen` returns `location_conflicts`; `/api/generate/start` answers 409 until `location_resolution` says which side is right; the loser is rewritten before Pass 1 and scrubbed from the page. | `data_consistency.py` |
| Hours | `is_24h` from 00:00–23:59 / every day / "24 jam"; badge says "Buka 24 jam"; JSON-LD hours come from the structured field only; "tutup 23:59" is rewritten. | `data_consistency.normalize_hours`, `subdomain._OPEN_BADGE_SCRIPT` |
| Prices | Decimals through one formatter (`RM6.00`, `RM18.00/pax`); the form only accepts digits; start refuses typos (400); validator fails `RM\d+\.[^\d]`; publish never invents a price. | `data_consistency.format_price` |
| Address | Title-cased, `l7/l` → `L7/1`; map heading is the business name, address is body text. | `data_consistency.normalize_address`, `templates.inject_google_maps` |
| Invented sections | Facts (times, numbers with units, prices, counts) not in the brief strip the section (or the element, in essential sections). | `fact_guard.py` |
| Type hierarchy | H1 largest (≥ 2× body), H2 ≥ 1.6× body — static Tailwind repairs plus measured repairs by CSS path from the critique render. | `page_hierarchy.py` |
| Hero | Text background sampled on the screenshot; < 4.5:1 gets a panel. One hero image only. | `page_hierarchy.hero_readability_repair` |
| CTAs | Nav = primary, hero = primary + secondary, no third repeat. | `page_hierarchy.dedupe_ctas` |
| QR / floats | QR inside the footer container; chat bubble, WhatsApp float, order button and open badge stacked so nothing overlaps at 390px. | `subdomain.insert_in_footer`, `binaapp-float-stack` CSS |
| Logo badge | Single-letter mark takes the plan accent and display font. | `page_hierarchy.restyle_logo_badge` |

`python scripts/designer_grade_acceptance.py` now includes the Dobi offline
checks; `--live` regenerates the brief and writes screenshots.
