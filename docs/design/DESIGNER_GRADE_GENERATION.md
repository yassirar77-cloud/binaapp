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
