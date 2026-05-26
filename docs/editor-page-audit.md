# Editor Page Audit — `/editor/[id]`

> Read-only inventory taken before any redesign work. **No code was changed.**
> Source of truth: `frontend/src/app/editor/[id]/page.tsx` (read end-to-end),
> plus its child `AIEditor.tsx`, the Next route `api/edit-website/route.ts`,
> and the `lib/regenerate*` helpers. Date: 2026-05-26.

---

## 1. File inventory

**Main file:** `frontend/src/app/editor/[id]/page.tsx` — **750 lines**, `'use client'`.

### Components defined in this file

| Component | Role |
|---|---|
| `EditorPage` (default export) | Top-level page. Owns all data + regenerate state. |
| `StyleChipRow` | Horizontal radio-group of style chips above the regenerate textarea. |
| `RegenerateConfirmModal` | Confirm dialog before regenerate; image-aware warning + acknowledge checkbox. |

### Components imported

| Import | From | Notes |
|---|---|---|
| `AIEditor` | `./AIEditor` | Separate incremental "AI Editor" panel (chat-style). |
| `supabase`, `getCurrentUser`, `getStoredToken` | `@/lib/supabase` | Auth + DB fallback. |
| `buildRegenerateWarning` | `@/lib/regenerateWarning` | Pure warning-text builder. |
| `STYLE_CHIPS`, `applyStyleChip`, `chipIsStillApplied`, `type StyleChipId` | `@/lib/regenerateStyleChips` | Style-chip catalogue + text composition. |

### Panels (visual sections, top → bottom)

1. **Header bar** — title (`business_name`/`name`), subdomain line, `← Kembali`, `💾 Simpan`.
2. **Regenerate dengan AI** card — current-description context box, style-chip row, "Penerangan baru" textarea, error box, `🪄 Regenerate Website` button.
3. **RegenerateConfirmModal** — conditional overlay (only when `showRegenerateConfirm`).
4. **AI Editor** (`<AIEditor>`) — chat history, prompt input + `Ubah`, 4 quick-fill chips.
5. **Code Editor + Preview grid** — left: HTML `<textarea>`; right: live `<iframe srcDoc>`.
6. **Mobile notice** — landscape recommendation banner (`lg:hidden`).
7. **Floating chat bubble** — *not in this file*; injected globally by `layout.tsx`.

### State variables — `EditorPage` (12 `useState`)

| # | State | Init | Purpose |
|---|---|---|---|
| 1 | `loading` | `true` | Initial load spinner. |
| 2 | `saving` | `false` | Simpan button busy. |
| 3 | `website` | `null` | Fetched `Website` record. |
| 4 | `html` | `''` | The HTML buffer (editor + preview + save source). |
| 5 | `error` | `null` | Fatal load error → redirect screen. |
| 6 | `pendingDescription` | `''` | Editable regenerate prompt; **source of truth** for what is sent. |
| 7 | `regenerating` | `false` | True while regenerate job runs + polls. |
| 8 | `showRegenerateConfirm` | `false` | Confirm modal visibility. |
| 9 | `regenerateError` | `null` | Regenerate-flow error text. |
| 10 | `uploadedImageCount` | `0` | Drives strong vs soft warning in modal. |
| 11 | `acknowledgeReplace` | `false` | Modal checkbox tick. |
| 12 | `selectedChipId` | `null` | Active style chip (UI helper only). |

`AIEditor.tsx` owns 3 more `useState`: `prompt`, `loading`, `history`.

### Hooks

- `useState` × 12 (page) + 3 (AIEditor).
- `useEffect` × 1 (page, line 64 — runs `loadWebsite()` + `loadUploadedImageCount()` on `id`). AIEditor: 0.
- `useMemo` × 1 (`RegenerateConfirmModal`, memoises `buildRegenerateWarning`).
- **No custom hooks.**

---

## 2. Wired vs unwired audit (each visible UI element)

| Element | Wired? | Target / behaviour |
|---|---|---|
| **Kembali** button | ✅ | `router.push('/dashboard')` (page.tsx:381). No save prompt. |
| **Simpan** button | ✅ | Custom-auth: `PUT ${API_BASE}/api/v1/websites/{id}` with `{ html_content }`. Fallback: Supabase `websites.update` + (if subdomain) Storage upload to `${subdomain}/index.html`. |
| **Regenerate dengan AI** panel | ✅ | `PATCH ${API_BASE}/api/v1/websites/{id}/regenerate` body `{ description? }`. Then **polls** `GET .../websites/{id}` every **3s**, cap **100 attempts (≈5 min)**, stops when `status` ≠ `'generating'`. |
| **Style chips (6)** | ✅ | Read from `STYLE_CHIPS` in `regenerateStyleChips.ts`. Single-select; re-tap clears. They **mutate the textarea text** via `applyStyleChip`; they are **not** sent as a separate field — the textarea is what gets POSTed. |
| **AI Editor textarea + `Ubah`** | ✅ | `POST /api/edit-website` (Next route) → proxies to backend `POST ${API_URL}/api/edit-html`. Returns `{ success, html }`; updates `html` **in memory only** (does not save). |
| **Quick chips** (Tukar warna / Tambah telefon / Tukar alamat / Tambah harga) | ⚠️ semi-static | Inside `AIEditor`. They only `setPrompt('<canned text>')`; user must still click `Ubah`. Pure prompt pre-fills, not direct API calls. |
| **HTML Editor** | ✅ editable | Plain `<textarea>` two-way bound to `html`. **No editor library** (no CodeMirror/Monaco), no syntax highlighting, `spellCheck={false}`. |
| **Preview iframe** | ✅ | `srcDoc={html}` — renders live from the `html` state. `sandbox="allow-scripts allow-same-origin allow-forms"`. |
| **Floating chat bubble** (blue, bottom-right) | ✅ (global) | `ChatWidget` ("BinaBot" support chat) rendered in `layout.tsx:93`. **Not** part of the editor; appears on every route except `/delivery`. |

---

## 3. Recent PR overlay (which PRs touched this page)

| PR | Touched `editor/[id]/page.tsx`? | What it added |
|---|---|---|
| **#665** (`a18b7eb`, widget-aware + regenerate UI) | ✅ +232 lines | Regenerate panel, confirm modal (original soft version), regenerate endpoint call, **the entire polling loop incl. the 5-min cap**. |
| **#666** (`3b177ad`, modal warning + style chips) | ✅ ±310 lines | `StyleChipRow`, `selectedChipId` state, image-aware `RegenerateConfirmModal`. **Created** `regenerateStyleChips.ts` (+ test) and `regenerateWarning.ts` (+ test). |
| **#670** (`5a84970`, heartbeat / stuck-status safety net) | ❌ | Backend-only; no editor-page changes (confirmed). |
| **Poll timeout fix** (#669 `e605c96`, "timeout retry + counter-on-success") | ❌ | Did **not** touch the editor page. The poll cap (`maxAttempts=100`) was already introduced in #665 — `git blame` attributes all poll lines to `a18b7eb`. |
| **DeepSeek-only** (#671 `92db834`) | ❌ | Backend generation refactor only; no editor-page changes. |

Net: only **#665 and #666** modified this page. #667/#668/#669/#670/#671 are backend/create-flow/safety work.

---

## 4. Dependency map (`lib/*` imports)

| Module | Imported? | Used for |
|---|---|---|
| `lib/regenerateStyleChips.ts` | ✅ | `STYLE_CHIPS`, `applyStyleChip`, `chipIsStillApplied`, `StyleChipId`. |
| `lib/regenerateWarning.ts` | ✅ | `buildRegenerateWarning` (modal copy + acknowledge gating). |
| `lib/regeneratePollMessages.ts` | ❌ **DOES NOT EXIST** | No such file anywhere in `frontend/src`. Poll status strings are **hardcoded inline** in `regenerateWebsite()`. |
| `lib/supabase.ts` | ✅ | `supabase`, `getCurrentUser`, `getStoredToken`. |

Both helper modules ship with companion tests (`regenerateStyleChips.test.ts`, `regenerateWarning.test.ts`). No other `lib/*` helper is imported by this page. `AIEditor.tsx` imports nothing from `lib`.

---

## 5. State complexity / where data flow gets hard to follow

- **12 `useState` + 1 `useEffect` + 1 `useMemo`** in the page; **2 distinct AI subsystems** with separate state.
- **`html` is edited from 4 places**: initial load, HTML textarea, regenerate poll result, and AIEditor's `onHtmlChange`. No single reducer — easy to lose track of which write wins.
- **`pendingDescription` ↔ `selectedChipId` coupling** (lines 437–477) is the trickiest logic: chip selection mutates the textarea via string `includes`/`split`, and editing the textarea de-highlights the chip. Works, but the "effective previous" computation is subtle.
- **Two regenerate-error channels** (`error` for fatal load, `regenerateError` for the regen flow) plus AIEditor's own in-component `history` error strings — three independent error surfaces.

---

## 6. What's broken / weird (observation only — nothing fixed)

1. **Missing module referenced in the brief:** `regeneratePollMessages.ts` does not exist. Poll/status copy is inline literals.
2. **Two parallel AI editing systems** with inconsistent contracts:
   - "Regenerate dengan AI" → authed `PATCH .../regenerate`, persisted server-side, async + polled.
   - "AI Editor" (`Ubah`) → `POST /api/edit-website` → backend `/api/edit-html`, **sends NO auth header at all** (neither the Next route nor `AIEditor` attaches `getStoredToken()`), and the result is **in-memory only** (not saved until Simpan).
3. **Polling has no cleanup.** `setInterval` in `regenerateWebsite()` is never cleared on unmount (no `useEffect` cleanup / ref). Navigating away mid-regenerate leaves the interval running and can call `setState` on an unmounted component.
4. **AI Editor edits can be silently lost** — `onHtmlChange` updates `html` but there is no autosave; if the user leaves without Simpan, the change is gone (Kembali doesn't warn).
5. **Silently swallowed errors:**
   - `loadUploadedImageCount` catch → `console.warn` only (intentional: falls back to soft warning).
   - poll `catch (pollErr)` → `console.warn` only.
   - `saveWebsite` Storage-upload errors → logged and ignored by design (save still "succeeds").
6. **Loading-state desync risk:** if a poll `statusResp` is non-OK it `return`s without resetting `regenerating`; it keeps retrying until the 5-min cap. Combined with #3, `regenerating` can get stuck if the component unmounts.
7. **Modal warning IS still wired.** `RegenerateConfirmModal` renders whenever `showRegenerateConfirm` is true and is gated by `buildRegenerateWarning`. The screenshot shows the AI Editor with chips but no modal simply because **the modal belongs to the *Regenerate* panel** and only appears after clicking `🪄 Regenerate Website` — it is a different flow from the AI Editor. So: not broken, just not visible in that screenshot state.
8. **No `TODO`/`FIXME`/`HACK`/`deprecated` markers** in `page.tsx`, `AIEditor.tsx`, or `api/edit-website/route.ts`.
9. **No dead state found** — all 12 page states and all 3 AIEditor states are read somewhere. No unused functions.
10. **Plain-textarea HTML editor** (no library) means large HTML is hard to edit; no formatting/validation in the UI.

---

## 7. User flows currently supported

| Action | What happens |
|---|---|
| **Clicks `Regenerate Website`** | Validates (needs stored description OR ≥10 chars typed) → opens `RegenerateConfirmModal` (resets acknowledge). On `Ya, regenerate`: `PATCH .../regenerate` with optional `{ description }` → sets `regenerating` → polls every 3s until `status≠generating` → replaces `website`+`html`, clears textarea. On `failed`/timeout → sets `regenerateError`. |
| **Picks a style chip, then regenerates** | Chip appends its English modifier to the textarea (`applyStyleChip`); re-tap or text edit removes it. The **textarea text** (incl. the appended modifier) is what's sent as `description`. The chip id itself is never transmitted. |
| **Types in AI Editor → `Ubah`** | `POST /api/edit-website {html, instruction}` → backend `/api/edit-html`. On `{success, html}` updates the `html` buffer + appends "Perubahan berjaya!" to chat history. **In-memory only — not persisted.** Errors are mapped to Malay strings in the chat. |
| **Edits HTML directly in HTML Editor** | Two-way bound to `html`; preview updates live. **Does NOT auto-save** — only persists on Simpan. |
| **Clicks `Simpan`** | Saves **only `html_content`** (= current `html` buffer): `PUT .../websites/{id}` for custom-auth users, or Supabase `websites.update` (+ Storage upload if published with subdomain) for legacy users. Description/chips/AI-editor metadata are **not** saved here. |

---

## Summary

- **Total lines** in `editor/[id]/page.tsx`: **750**.
- **Components/panels/state:** 3 components in-file (+1 imported child `AIEditor`); ~6 visible panels; **12 `useState`** + 1 `useEffect` + 1 `useMemo` in the page (AIEditor adds 3 more state hooks).
- **API endpoints called (page):**
  - `GET  ${API_BASE}/api/v1/websites/{id}/menu-items` (image count)
  - `GET  ${API_BASE}/api/v1/websites/{id}` (load + poll)
  - `PUT  ${API_BASE}/api/v1/websites/{id}` (save)
  - `PATCH ${API_BASE}/api/v1/websites/{id}/regenerate` (regenerate)
  - Supabase fallbacks: `websites.select`, `websites.update`, Storage `websites` upload
  - **AI Editor (child):** `POST /api/edit-website` → backend `POST ${API_URL}/api/edit-html`
- **Helper modules imported:** `@/lib/supabase`, `@/lib/regenerateWarning`, `@/lib/regenerateStyleChips`, `./AIEditor`. (`regeneratePollMessages.ts` does **not** exist.)
- **Audit doc path:** `docs/editor-page-audit.md` (this file).

### 3 most important findings

1. **Two disconnected AI subsystems with inconsistent auth & persistence.** "Regenerate" is authed, server-persisted, and polled; "AI Editor" (`Ubah`) sends **no auth token** and is **in-memory only** until Simpan. This is the biggest source of user confusion and a likely auth gap to resolve in the redesign.
2. **The regenerate polling `setInterval` is never cleaned up on unmount**, and a non-OK poll response doesn't reset `regenerating` — so leaving the page mid-regenerate can leak the timer and strand the busy state.
3. **`regeneratePollMessages.ts` doesn't exist** (poll copy is hardcoded inline), and the **HTML editor is a plain `<textarea>` with no editor library** — both are concrete, easily-verified facts for scoping the redesign. (Separately: the modal warning **is** still wired; it just belongs to the Regenerate flow, not the AI Editor shown in the screenshot.)
