# Senior Designer mode

Website generation used to be a template-filler: the design system picked the
fonts, the palette, the hero HTML and a numbered section list, and the prompt
told the model "MUST FOLLOW". Sites came out consistent, but the AI had no
room to design, and a merchant who wrote *"I want it to feel like a Tokyo
listening bar, dark, one gold accent"* got the same seeded look as everyone
else.

Senior Designer mode reframes the AI as the senior designer on a real client
project. It owns the visual design; the pipeline owns the facts and the
technical contract.

## What changed

| Before | After (designer mode) |
| --- | --- |
| Design system picks fonts + palette from seeded pools | The AI writes a **design concept** (mood, palette, Google Fonts pairing, hero idea, page plan, signature details); the pipeline validates it and wires it into `tailwind.config` and the Google Fonts `<link>` |
| Hero is a fixed HTML blueprint with placeholder tokens | The AI composes the hero from its concept (blueprint only survives as an optional reference when there is no concept) |
| "LAYOUT STRUCTURE — MUST FOLLOW" numbered list | The concept's own page plan, with the house layout as reference material and a short *required content* list (hero, offerings, about, contact, footer) |
| "ART DIRECTION (NON-NEGOTIABLE)" | "STUDIO STANDARDS (house defaults — depart from them deliberately)" |
| No way to say how you want the site to look | A free-text **design brief** from the create page (and the editor's regenerate form) is the highest-priority design input, in both the concept step and the HTML prompt |
| One system prompt: "follow constraints exactly" | A senior-designer system prompt for the HTML call; the GLM prompt keeps its GOAL → HARD RULES → FREEDOM core and gains a role preface + precedence ladder |

What did **not** change: every fact and technical rule. Real data only, no
invented numbers/claims, exact image URLs, WhatsApp digit rules, mobile
hamburger nav, free Font Awesome icons only, fonts loaded in the HEAD only,
the language lock, the menu-data source-of-truth block, the sensitive-claim
sanitizer, the post-generation validator and the layout guards all run
exactly as before, in both modes.

## Precedence

When instructions conflict, the prompt states the ladder explicitly:

1. **Non-negotiable** rules — facts, URLs, WhatsApp, language, mobile, icons, fonts in HEAD.
2. **The merchant's explicit picks** — design brief, colour theme, light/dark, chosen style.
3. **The AI's design concept.**
4. **House defaults** — type scale, 8px spacing, card patterns, animation defaults.

## The concept step

`backend/app/services/design_director.py` is pure and side-effect free.
`ai_service._direct_design_concept()` calls the fast DeepSeek tier (GLM as
fallback when enabled) with `build_concept_prompt()`, then `parse_concept()`
validates the JSON:

- every hex colour is checked (3-digit expanded, invalid replaced from the
  seeded palette);
- text/background contrast is repaired to ≥ 4.5:1 (muted ≥ 3:1), primary must
  be visible against the background;
- the merchant's **light/dark** choice is enforced — a concept that flips it
  has its neutrals reset;
- merchant **brand colours** override the concept's primary/secondary/accent;
- fonts are resolved against a curated Google Fonts catalogue with per-font
  weight strings (an unknown font silently falls back to system-ui; a wrong
  weight 400s the whole stylesheet), display faces are never used for body
  copy;
- required content sections are added if missing; hero is forced first and
  footer last; sections are capped.

A failed, slow or unparseable concept means "no concept": the seeded design
system fills in and the prompt still runs in designer framing. The step is
bounded by `AI_DESIGN_CONCEPT_TIMEOUT_SECONDS` and never raises.

The doodle style is the one look that keeps its own fonts and drawing
directives with a concept present — it is an explicit merchant pick.

Gallery templates (`template_id`) always run **guided**: the merchant chose
that exact look.

## Request fields

`POST /api/generate/start`, `POST /api/v1/websites/generate` and
`PATCH /api/v1/websites/{id}/regenerate` accept:

| Field | Type | Meaning |
| --- | --- | --- |
| `design_brief` | string ≤ 1500 | Free-text design direction. Trimmed, whitespace-collapsed; blank = none |
| `design_freedom` | `"designer"` \| `"guided"` | Override of the server default. Unknown values mean "server default" (never a 422) |

`design_style` (doodle / elegant / minimal / playful / bold / classic) still
works and is passed to the concept step as a constraint.

## Environment

| Variable | Default | Effect |
| --- | --- | --- |
| `AI_DESIGN_FREEDOM_DEFAULT` | `designer` | Site-wide default mode. Set `guided` for an instant rollback to the pre-upgrade prompt without a deploy |
| `AI_DESIGN_CONCEPT_ENABLED` | `true` | Run the concept step in designer mode. `false` keeps designer framing but uses the seeded fonts/palette |
| `AI_DESIGN_CONCEPT_TIMEOUT_SECONDS` | `75` | Hard cap on the concept call |
| `AI_DESIGN_CONCEPT_MAX_TOKENS` | `2200` | Output cap for the concept JSON |
| `AI_DESIGN_CONCEPT_TEMPERATURE` | `0.8` | Creativity of the concept step (the HTML step stays at 0.2) |

## Observability

- `step_timings.design_concept` on the generation response.
- Log lines: `🎨 Design freedom: … | brief: … | concept: …`, the full validated
  concept as JSON, and `🎨 Concept adjusted during validation: …` listing every
  repair (bad hex, contrast, mode mismatch, unknown font, missing section).
- `AIService._last_design_concept` holds the last validated concept dict.
- With `PREMIUM_DESIGN_LOOP=true`, the DeepSeek reviewer also checks that the
  page visibly delivers the merchant's brief.

## Frontend

- Create page, section 02: an **"Arahan untuk designer AI"** card with the
  brief textarea, example chips (Malay/English) and the freedom picker
  (*Designer bebas* / *Ikut sistem*). The summary panel shows both.
- Editor page: an optional **"Arahan design untuk jana semula"** field under
  the assistant prompt, sent as `design_brief` with a full regenerate.
- Helpers and tests: `frontend/src/lib/designBrief.ts`.
