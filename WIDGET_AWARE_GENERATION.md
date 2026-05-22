# Widget-aware AI generation + regenerate flow

This doc covers two extensions to the AI website generation pipeline:

1. **Widget-aware generation** — the AI is told upfront which widgets
   (WhatsApp, chat, delivery/pesanan, maps, contact form) will be
   stitched onto the page after generation, so it can leave room and
   pick a complementary palette instead of designing in a vacuum.
2. **Persisted description + regenerate** — the natural-language prompt
   the user originally typed is saved on the website row, and the
   `PATCH /api/v1/websites/{id}/regenerate` endpoint can re-run AI
   generation in place without re-collecting subdomain / business
   name / integrations.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  backend/app/services/widget_catalogue.py                            │
│    • WIDGETS — frozen dataclass dict, source of truth                │
│    • widgets_for_request() — pick the right set for a generation     │
│    • build_prompt_context_block() — render the prompt's              │
│      "INJECTED WIDGETS — DESIGN AROUND THESE" block                  │
└────────────┬───────────────────────────────────┬─────────────────────┘
             │                                   │
             ▼                                   ▼
┌──────────────────────────┐         ┌──────────────────────────┐
│ ai_service.py            │         │ templates.py             │
│   _build_strict_prompt() │         │   _find_widget_slot()    │
│     ↳ prepends widget    │         │   _inject_into_slot()    │
│       context block      │         │   inject_*() now accept  │
│     ↳ instructs AI to    │         │     theme_tokens=…       │
│       emit optional      │         │     and prefer slots     │
│       slot divs          │         │     over floating /      │
│   extract_theme_tokens() │         │     fixed appending      │
│     ↳ pulls primary/     │         └──────────────────────────┘
│       accent/surface     │
│       hex from HTML      │
└──────────────────────────┘
             │                                   ▲
             └─── theme_tokens flow ─────────────┘
```

### widget_catalogue.py

Every injectable widget is described in one place. Each `WidgetSpec`
carries:

- `id` and computed `slot_id` (`binaapp-<id>-slot`) — the canonical id
  the AI is told to emit in placeholder divs.
- `aliases` — alternative ids the injector also matches (e.g. the AI
  occasionally emits `binaapp-pesanan` instead of `binaapp-pesanan-slot`;
  we accept both).
- `default_position` and `legacy_position` — describes the legacy
  floating/fixed placement used when the AI didn't emit a slot.
- `default_colors` — paint defaults if no theme tokens are available.
- `recommended_placement` and `prompt_description` — the strings that
  end up verbatim in the AI prompt.

Adding a new widget = appending one entry to `WIDGETS`. Both the prompt
builder and the injection layer pick it up.

### Designated slots (backward compatible)

The prompt's widget block tells the AI:

> For inline widgets (maps, contact form, qr, pesanan), you MAY emit an
> empty placeholder div with the listed id, e.g.
> `<div id="binaapp-pesanan-slot"></div>`. The injection layer will
> replace the inner contents with the live widget. If you don't emit a
> slot div, the widget is appended at the end of the body (legacy
> behaviour, still works).

Inject helpers (`inject_google_maps`, `inject_contact_form`, etc.) do:

1. Look for the canonical slot id + aliases via `_find_widget_slot`.
2. If found, call `_inject_into_slot` to swap the inner HTML — preserves
   the AI's semantic placement.
3. If not found, fall back to the old "append before `</body>`" path.

This means **every existing generated site still renders identically.**

### Theme token extraction

`extract_theme_tokens(html)` scans the generated HTML for:

- `--primary-color: #...;`, `--primary: #...;`, or `primary: "#..."`
  (Tailwind config form). First match wins.
- Same logic for `--accent-color` / `--accent`.
- `--surface-color` or `--bg-color` for surface.

The result is passed into every widget injector as `theme_tokens=`:

- **Delivery widget**: overrides `data-primary-color` so the floating
  button's pill colour matches the site.
- **Chat widget**: emits a `<style>:root { --binaapp-chat-primary: … }</style>`
  block before the script tag so future chat-widget.js revs can inherit
  the theme without a redeploy.
- **Contact form**: themes the submit button gradient.
- **Maps**: themes the section heading colour.
- **WhatsApp**: kept on brand green (#25D366) — colour change reduces
  recognition / conversions. The hook is wired but no-op for now.

---

## Database changes

Migration `039_websites_description_and_generation_count.sql`:

```sql
ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS generation_count INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS idx_websites_generation_count
  ON public.websites(generation_count);
```

- `description` — nullable so legacy rows aren't broken; the
  regenerate endpoint rejects requests where neither stored nor body
  description is present.
- `generation_count` — 0 default for legacy rows. The create endpoint
  sets it to 1; regenerate increments by 1.

---

## Regenerate endpoint

`PATCH /api/v1/websites/{website_id}/regenerate`

### Request body

```json
{ "description": "optional override prompt" }
```

Omit `description` to reuse the stored value.

### Response

`200 OK` immediately with a `WebsiteResponse` showing `status: "generating"`.
The frontend polls `GET /api/v1/websites/{id}` every 3 s until status
flips to `draft` or `failed`.

### Access control / quota

In order, the endpoint enforces:

1. **Auth** — JWT required (FastAPI `Depends(get_current_user)`).
2. **Ownership** — `website.user_id == sub` else `403`.
3. **Conflict** — if status is already `generating`, `409` so concurrent
   regenerate buttons don't double-bill.
4. **Description present** — explicit body or stored row else `400`.
5. **Quota** — `subscription_service.check_limit("generate_ai_hero")`
   else `403` (same path as create; respects plan limit + addon credits).

Important: quota check happens **after** the ownership check, so we
don't waste a quota check on a forbidden request and don't leak the
row's existence to non-owners.

### Background pipeline

The endpoint reconstructs a `WebsiteGenerationRequest` from the saved
row + new description and hands it to the same `generate_website_content`
background task the create flow uses. This keeps the AI pipeline
single-sourced — improvements (widget catalogue, theme tokens, etc.)
apply to regenerate too with zero extra work.

---

## Frontend

`frontend/src/app/editor/[id]/page.tsx` adds a regenerate panel:

- Shows the currently-stored description (read-only context).
- Textarea to edit; empty means "reuse stored".
- Button opens a confirm modal that warns existing HTML will be
  replaced.
- During regeneration, the textarea is disabled, the button shows
  `⏳ Regenerating…`, and a poll loop watches `GET /:id` for status
  change.
- Generation count is shown as `(sudah regenerate Nx)`.

The panel is gated on the custom BinaApp token — Supabase-session-only
users see the existing UI without the regenerate panel (their saved
description still flows through `/api/v1/websites/generate` create
flow).

---

## Sample before/after of widget-aware AI output

### Before

AI generates a hero with a giant floating "WhatsApp Order Now" CTA in
the bottom-right. The delivery widget then injects its own pill in the
same corner — they stack and the bottom button is unreachable on mobile.
The hero's primary colour is electric green, clashing with the WhatsApp
brand green.

### After

The prompt block tells the AI:

```
INJECTED WIDGETS — DESIGN AROUND THESE
- WhatsApp Floating Button (id=binaapp-whatsapp-slot)
    placement: Floating action button in the bottom-right corner.
    Leave a ~80px clear zone there
- Delivery / Ordering Widget (id=binaapp-delivery-slot)
    placement: Stacked above the WhatsApp button on the bottom-right.
    The hero CTA should complement an ordering flow (e.g. 'Lihat Menu'
    or 'Pesan Sekarang') and link to #menu
RULES:
1. Do NOT add your own floating WhatsApp / chat / delivery buttons
2. For inline widgets you MAY emit <div id="binaapp-pesanan-slot"></div>
```

The AI now:

- Drops the redundant floating CTA.
- Places a hero "Lihat Menu" button that scrolls to `#menu`.
- Emits `<div id="binaapp-pesanan-slot"></div>` between menu and
  contact, which the inline ordering UI fills in semantically.
- Picks a warm orange `--primary-color` that doesn't clash with the
  WhatsApp green — and `extract_theme_tokens` reads that, so the
  delivery widget pill also flips to warm orange.

---

## Tests

- `backend/tests/test_widget_catalogue.py` — 24 tests covering the
  catalogue, request → widgets mapping, prompt block, theme token
  extractor, and the slot-aware injection helpers.
- `backend/tests/test_websites_regenerate.py` — 11 tests covering the
  regenerate endpoint: schema validation, 404, 403 ownership, 409
  in-flight, 400 missing description, 403 quota, owner success path,
  stored-description reuse.

Run with:

```
cd backend && python -m pytest tests/test_widget_catalogue.py tests/test_websites_regenerate.py
```
