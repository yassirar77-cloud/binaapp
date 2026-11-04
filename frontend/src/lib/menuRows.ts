/**
 * The create page's menu rows (step 06) — the merchant's items with prices
 * and section labels — and the small rules around them.
 *
 * Ayam Gepuk Panglima typed 32 items and the generation request carried
 * `menu_items: []`: the rows never left the browser. Three things here make
 * that loss hard to repeat:
 *
 *   - `parseMenuPaste`: a whole menu pasted in one go ("Set Ayam: Set A –
 *     Ayam Gepuk 12.50 | Set B – ... 13.50") becomes rows with categories,
 *     instead of 32 separate Add-item clicks.
 *   - `saveMenuRows` / `loadMenuRows`: the rows survive a reload, a tab the
 *     phone discarded, or an auth bounce — the form has no other draft.
 *   - `menuRowsWarning`: a food business about to generate with no items is
 *     told so before credit is spent.
 *
 * Pure module so every rule is unit-testable.
 */

export interface MenuRow {
  url: string
  name: string
  price: string
  category?: string
}

export const MENU_ROWS_STORAGE_KEY = 'binaapp:create:menuRows:v1'

const PRICE_TAIL = /(?:[-–—|:]\s*)?(?:RM\s*)?(\d{1,5}(?:[.,]\d{1,2})?)\s*$/i

function cleanName(s: string): string {
  return s.replace(/[\s\-–—|:]+$/g, '').replace(/^[\s\-–—•*·]+/, '').trim()
}

/** One "Name 12.50" / "Name – RM12.50" / "Name | 12.50" chunk → row, or null. */
function parseItemChunk(chunk: string, category: string): MenuRow | null {
  const text = chunk.trim()
  if (!text) return null
  const m = PRICE_TAIL.exec(text)
  if (m && m.index > 0) {
    const name = cleanName(text.slice(0, m.index))
    if (name) return { url: '', name, price: m[1].replace(',', '.'), category }
  }
  const name = cleanName(text)
  if (!name) return null
  return { url: '', name, price: '', category }
}

/**
 * A pasted menu → rows. Lines are items; a line (or a leading "Label:" on a
 * line) that carries no price names the section for what follows. Items on
 * one line may be separated with "|". A line without a price that is short
 * and followed by priced items is a section label, not an unpriced item.
 */
export function parseMenuPaste(text: string): MenuRow[] {
  const rows: MenuRow[] = []
  let category = ''
  const lines = String(text ?? '').split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]
    // "Set Ayam: Set A – Ayam Gepuk 12.50 | ..." → label + items on one line.
    const labelled = /^([^|]{2,40}?):\s*(.+)$/.exec(line)
    if (labelled && !PRICE_TAIL.test(labelled[1]) && !/\d/.test(labelled[1])) {
      category = labelled[1].trim()
      line = labelled[2]
    }
    const chunks = line.split('|').map(c => c.trim()).filter(Boolean)
    const parsed = chunks.map(c => parseItemChunk(c, category)).filter((r): r is MenuRow => !!r)
    const unpricedShort = parsed.length === 1 && !parsed[0].price && parsed[0].name.length <= 40
    const nextIsPriced = i + 1 < lines.length && PRICE_TAIL.test(lines[i + 1].split('|')[0])
    if (unpricedShort && (line.endsWith(':') || nextIsPriced) && !labelled) {
      category = parsed[0].name.replace(/:$/, '')
      continue
    }
    rows.push(...parsed)
  }
  return rows
}

/** The rows the generation and publish requests carry: every named row. */
export function rowsForRequest(rows: MenuRow[]): { name: string; price: string; category?: string; image_url?: string }[] {
  return rows
    .map(r => ({
      name: (r.name || '').trim(),
      price: (r.price || '').trim(),
      category: (r.category || '').trim() || undefined,
      image_url: (r.url || '').trim() || undefined,
    }))
    .filter(r => r.name.length > 0)
}

/** Distinct section labels in first-seen order, for the datalist. */
export function categoriesOf(rows: MenuRow[]): string[] {
  const out: string[] = []
  for (const r of rows) {
    const c = (r.category || '').trim()
    if (c && !out.includes(c)) out.push(c)
  }
  return out
}

/**
 * Why generating now would lose the menu, or null. A food business (chosen
 * or auto-detected from the story) with no named item gets a page built
 * from the prose — which is where invented dishes come from.
 */
export function menuRowsWarning(rows: MenuRow[], businessType: string, description: string): string | null {
  const named = rows.filter(r => (r.name || '').trim()).length
  if (named > 0) return null
  const foodish = businessType === 'food' || businessType === 'bakery'
    || (businessType === 'auto' && /\b(menu|restoran|restaurant|kafe|cafe|warung|kedai makan|gerai|nasi|ayam|mee|roti|kuih|bakeri|bakery|makan|minuman)\b/i.test(description))
  if (!foodish) return null
  return 'Tiada item menu dimasukkan di langkah 06 — laman akan dijana TANPA senarai menu dan harga anda. Tambah item (atau tampal menu) dahulu jika anda mahu menu di laman.'
}

type StorageLike = { getItem(k: string): string | null; setItem(k: string, v: string): void; removeItem(k: string): void }

function storage(): StorageLike | null {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return null
    return window.localStorage
  } catch {
    return null
  }
}

export function saveMenuRows(rows: MenuRow[], store: StorageLike | null = storage()): void {
  if (!store) return
  try {
    const kept = rows.filter(r => (r.name || '').trim() || (r.price || '').trim() || (r.url || '').trim())
    if (kept.length === 0) store.removeItem(MENU_ROWS_STORAGE_KEY)
    else store.setItem(MENU_ROWS_STORAGE_KEY, JSON.stringify({ rows: kept, savedAt: Date.now() }))
  } catch { /* storage full / private mode — the form still works */ }
}

export function loadMenuRows(store: StorageLike | null = storage()): MenuRow[] {
  if (!store) return []
  try {
    const raw = store.getItem(MENU_ROWS_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as { rows?: unknown }
    if (!parsed || !Array.isArray(parsed.rows)) return []
    return parsed.rows
      .filter((r): r is Record<string, unknown> => !!r && typeof r === 'object')
      .map(r => ({
        url: typeof r.url === 'string' ? r.url : '',
        name: typeof r.name === 'string' ? r.name : '',
        price: typeof r.price === 'string' ? r.price : '',
        category: typeof r.category === 'string' ? r.category : '',
      }))
  } catch {
    return []
  }
}

export function clearMenuRows(store: StorageLike | null = storage()): void {
  try { store?.removeItem(MENU_ROWS_STORAGE_KEY) } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Subdomain vs business name
// ---------------------------------------------------------------------------

/** The subdomain a business name slugifies to ("Ayam Gepuk Panglima" → "ayamgepukpanglima"). */
export function slugifyBusinessName(name: string): string {
  return String(name ?? '').toLowerCase().normalize('NFKD').replace(/[^a-z0-9]/g, '').slice(0, 30)
}

function editDistance(a: string, b: string): number {
  const dp: number[] = Array.from({ length: b.length + 1 }, (_, j) => j)
  for (let i = 1; i <= a.length; i++) {
    let prev = dp[0]
    dp[0] = i
    for (let j = 1; j <= b.length; j++) {
      const tmp = dp[j]
      dp[j] = Math.min(dp[j] + 1, dp[j - 1] + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1))
      prev = tmp
    }
  }
  return dp[b.length]
}

/**
 * A soft warning when the typed subdomain looks like a misspelling of the
 * business name: close to the slugified name but not equal (1–3 edits on a
 * name of 8+ characters). "ayamgepukpaglima" for "Ayam Gepuk Panglima" is
 * one dropped letter — the kind of slug that goes live and stays wrong. A
 * deliberately different slug ("panglima-klang") is left alone.
 */
export function slugMismatchWarning(subdomain: string, businessName: string): { suggestion: string; message: string } | null {
  const typed = String(subdomain ?? '').toLowerCase().replace(/[^a-z0-9]/g, '')
  const expected = slugifyBusinessName(businessName)
  if (!typed || expected.length < 8 || typed === expected) return null
  const distance = editDistance(typed, expected)
  if (distance < 1 || distance > 3) return null
  return {
    suggestion: expected,
    message: `Subdomain "${subdomain}" nampak seperti salah eja nama kedai anda — cadangan: ${expected}. Alamat ini kekal selepas publish.`,
  }
}
