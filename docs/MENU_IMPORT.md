# Menu Import — the menu you already have, read by AI

Typing a 40-line menu one row at a time was the slowest step of the create
page. Most merchants already have the menu somewhere: a PDF from the printer,
the Word file they sent the printer, an Excel sheet, a photo of the menu
board, a WhatsApp message. **Menu Import** turns any of those into the same
`name · price · photo` rows the manual form collects — and lets the merchant
say *which* items to take.

| Surface | What it is |
|---|---|
| Create page → 06 Menu items → **Import menu (AI)** | drop a file or paste text, pick "every item / signature only / my instruction", review, add |
| `POST /api/v1/menu/import/extract` | file or text → **draft** rows (nothing saved) |
| `POST /api/v1/menu/websites/{id}/menu-items/bulk` | reviewed rows → `menu_items` (+ categories) for a site that already exists |

The manual "Tulis sendiri" tab is unchanged: one row per item, name, price,
optional photo, "Add item".

---

## 1. What the merchant does

```
06 — MENU ITEMS
[ Tulis sendiri ]  [ Import menu (AI)  BARU ]

┌ Drop menu anda di sini ─────────────────────────┐
│ PDF, Word, Excel, CSV atau gambar papan menu     │
└──────────────────────────────────────────────────┘
Atau tampal teks menu

Item mana nak diambil?
( Semua item )  ( Signature sahaja )  ( Ikut arahan saya: "5 killer menu sahaja" )

                                  [ ✦ Baca menu dengan AI ]
```

The AI returns a **draft**. The merchant sees it grouped by the menu's own
sections, every priced row pre-ticked, every unpriced row unticked with the
reason ("Tiada harga — isi dahulu (RM15 - RM25)"), a ★ on signature items,
and the printed ingredient line under each name. They untick, fix a price,
toggle a ★, then **Tambah N item ke menu**. The rows land in the same list
the manual form fills; duplicates by name are skipped, so re-importing the
same PDF is a no-op.

Nothing the AI read is on the site until the merchant has looked at it.

### Selection modes

| Mode | Prompt to the model | Deterministic safety net |
|---|---|---|
| `all` | return every orderable item | — |
| `signature` | only items the menu marks (SIGNATURE, BEST SELLER, ★, 🔥…); if none are marked, the 5–8 most representative mains | flagged rows only; nothing flagged → all rows + a warning to pick by hand |
| `custom` | follow the merchant's words exactly | `interpret_instruction`: a count ("5", "lima"), signature intent ("killer", "terlaris", "best"), include words, and words after *kecuali / except / tanpa / without* to exclude |

"5 killer menu sahaja" → signature items, at most 5. "set ayam dan minuman,
kecuali add-on" → rows whose name/section matches *set*, *ayam* or *minuman*,
minus anything matching *add-on*.

---

## 2. Pipeline (`backend/app/services/menu_import.py`)

```
file bytes ──extract_source──▶ text (and/or page images)
            │
            ├── AI reachable ──▶ extract_with_ai ──▶ items   (engine: ai-text | ai-vision)
            └── otherwise / model failed ──▶ parse_menu_text ──▶ items   (engine: heuristic)
            │
            ▼
   apply_selection (all / signature / custom) ──▶ normalise_items ──▶ MenuImportResult
```

**Extraction** is pure (no network):

| Input | How |
|---|---|
| PDF | `pypdf` text layer, first 12 pages. Fewer than ~40 chars/page → treated as a **scan**: pages are rasterised with `pypdfium2` (pure wheels, no poppler) and sent to the vision model |
| Word `.docx` | stdlib zip + XML; a tab in a paragraph stays a tab, a table row becomes one tab-separated line (so `name \| price` cells stay together) |
| Excel `.xlsx` | stdlib zip + XML, shared strings resolved, one tab-separated line per row, every sheet |
| CSV / TXT / MD | decoded (utf-8-sig, cp1252 fallback); CSV dialect sniffed |
| JPG / PNG / WebP | passed to the vision model (downscaled to 1600px JPEG inline) |

**The heuristic parser** is the no-API fallback *and* the offline test
target, so it has to be good on real Malaysian menus. On the Ayam Gepuk
Panglima sample it finds all 32 items in 6 sections with no model at all:

- `Set A ········ RM 12.50`, `Set A\tRM 12.50`, `Teh Tarik 2.50`, `Set A RM 12.50 (nasi, ayam)` — all one item
- a bare trailing integer (`Nugget 5`) is **not** a price — a price needs `RM`, decimals, or a dotted leader
- ALL-CAPS short lines are section headings → Title Case categories (`KID'S MENU` → `Kid's Menu`); headings with no items (the shop name, the tagline, "MENU") are dropped
- the line right under an item that reads like ingredients (`Nasi, ayam, kubis…`) is its description; an ALL-CAPS note (`PERCUMA tambah sambal…`) is not
- `RM 5.00 — semua jenis` is a **section price** applied to the unpriced names under it (confidence 0.7, shown as "harga disimpulkan")
- `SIGNATURE`, `BEST SELLER`, `★`, `🔥` are stripped from the name and set `is_signature`
- `RM15 - RM25` is kept as `price_raw`, never reduced to one number; `S RM2.50 L RM3.50` takes the lowest and warns
- everything under `COMING SOON` / `AKAN DATANG` / `SOLD OUT` is skipped and listed in a warning
- phone numbers and opening hours never become items

**AI extraction** asks for strict JSON (`items[]`, `categories[]`,
`skipped[]`, `notes[]`) with the rules spelled out: prices as `"12.50"`
strings, never invented; one item per size; markers stripped into
`is_signature`; headings/notes/hours/phones skipped. Text goes to DeepSeek
(JSON mode) → GLM → Qwen; images go through `ai_service._call_vision_model`
(GLM-4.5V → Qwen-VL), the same chain as the design critique. The model
callers are injected, so tests never touch the network.

**Normalisation** dedupes case-insensitively (merging a missing price or
description), canonicalises prices, applies the same
`is_valid_menu_item_name` gate the generator applies — so nothing imported
here silently vanishes at generation — caps the list, and explains every
drop in `warnings`.

---

## 3. API

### `POST /api/v1/menu/import/extract`  (owner, multipart)

| Field | |
|---|---|
| `file` | optional — PDF / docx / xlsx / csv / txt / md / png / jpg / webp, ≤ 10 MB |
| `text` | optional — pasted menu text (≤ 60 000 chars); either `file` or `text` is required |
| `mode` | `all` (default) · `signature` · `custom` |
| `instruction` | ≤ 400 chars, used with `custom` |
| `max_items` | default 60, hard cap 150 |
| `language` | `ms` (default) · `en` — language of the notes |
| `business_type` | hint for the model |

```json
{
  "items": [{"name": "Set Panglima", "price": "15.90", "description": "Nasi, ayam, …",
             "category": "Set Ayam", "is_signature": true, "confidence": 1.0,
             "price_raw": null, "source_line": "Set Panglima   SIGNATURE \tRM 15.90"}],
  "categories": ["Set Ayam", "Set Seafood Krispy", "Tambahan (Add On)", "Minuman"],
  "warnings": ["Dilangkau (coming soon / tidak tersedia): Bakso Daging, Nasi Lemak"],
  "engine": "ai-text",
  "mode": "all",
  "source": {"kind": "docx", "pages": 1, "chars": 1494, "images": 0},
  "total_found": 32, "truncated": false, "skipped": ["Bakso Daging", "Nasi Lemak"],
  "plan": {"menu_items_limit": 20, "menu_items_used": 3, "remaining": 17, "unlimited": false,
           "allowed": true, "requires_renewal": false}
}
```

Errors carry `{"detail": {"error": <code>, "message": <Malay text>}}`:
`no_input` 400 · `bad_mode` 400 · `file_too_large` / `text_too_long` 413 ·
`unsupported_type` 415 · `unreadable` / `no_content` / `vision_unavailable` 422 ·
`rate_limited` 429.

**Writes nothing. Touches no usage counter.** `plan` is a read of the
plan's menu-item limit so the UI can warn before the merchant ticks 34
items on a 20-item plan.

### `POST /api/v1/menu/websites/{website_id}/menu-items/bulk`  (owner, JSON)

```json
{"items": [{"name": "Set Panglima", "price": "15.90", "description": "…", "category": "Set Ayam",
            "image_url": null, "is_signature": true, "is_available": true}],
 "skip_duplicates": true, "default_description": null}
```

One quota check (`add_menu_item`) for the whole batch: over the plan's
remaining count → `409 {"error": "menu_item_limit", "remaining", "limit",
"requested"}`, nothing inserted. Categories are found or created **by name**
(case-insensitive). Rows without a readable price, duplicates within the
request, and names already on the site are reported in `skipped` with a
reason. `menu_items_count` is incremented by the rows actually inserted.
Response: `{"created", "skipped", "categories_created", "items"}`.

### Publish (`POST /api/publish`)

The create page now sends **every named row with a price** as a menu item —
a photo is optional. Before this, only rows *with* a photo reached the
ordering menu, so a 30-item menu typed without pictures never showed up in
the ordering widget. Rows also carry `category` and `is_popular`; publish
groups them into `menu_categories` by name (`plan_publish_menu_rows`) and the
default "Menu" category is only used for rows without a section.

---

## 4. Cost and safety guards

| Guard | Where | Default |
|---|---|---|
| `MENU_IMPORT_ENABLED` | both endpoints 404 when off | `true` |
| `MENU_IMPORT_MAX_PER_HOUR` | per-user, in-memory, `extract` only | `30` |
| `MENU_IMPORT_AI_TIMEOUT_SECONDS` | one model call | `90` |
| `MENU_IMPORT_TEXT_MODEL` | override the DeepSeek model for extraction | `DEEPSEEK_MODEL` |
| upload size / PDF pages / vision images | service constants | 10 MB / 12 / 6 |

`extract` is the only AI call and the parser answers when no model is
reachable, so a merchant with a plain PDF is never blocked on an outage.
`bulk` never calls a model.

---

## 5. Tests

- `backend/tests/test_menu_import.py` — the real menu through the parser
  (every item, section, description, ★, section price, skipped list), line
  parser edge cases, docx/xlsx/csv/pdf extraction (fixtures built in-test),
  AI JSON tolerance, instruction interpretation, selection modes,
  normalisation, both endpoints (auth, errors, rate limit, feature flag,
  quota 409, category creation, usage count), the publish helper.
- `frontend/src/lib/menuImport.test.ts` — merge/dedupe into gallery rows,
  file kind detection, request shape, error shape.
- `frontend/src/app/create/components/MenuImportPanel.test.tsx` — the
  three steps: disabled until input, custom needs an instruction, review
  pre-ticks priced rows, edits reach `onImport`, errors return to input.

## 6. Next

- A **Import menu** button on the dashboard's menu manager for sites that
  already exist, calling `bulk` — the endpoint is ready; only the panel
  placement is missing.
- Variant rows (`Teh Tarik (S)` / `(L)`) as `menu_item_options` instead of
  separate items once the ordering widget renders options.
