/**
 * Menu Import client — the merchant's existing menu read into rows.
 *
 * Backend: `api/v1/endpoints/menu_import.py` (service `menu_import.py`).
 *
 *   POST /api/v1/menu/import/extract   file or text → DRAFT rows (nothing saved)
 *
 * The create page shows the draft in a review table; what the merchant ticks
 * is merged into the same `uploadedImages.gallery` rows the manual form
 * fills, so generation and publish see no difference between a typed item
 * and an imported one. Pure helpers live here so the merge rules are
 * unit-testable without React.
 */

import { API_BASE_URL } from '@/lib/env'
import { getApiAuthToken } from '@/lib/supabase'

export type MenuImportMode = 'all' | 'signature' | 'custom'

/** One row as the backend returns it, before review. */
export interface ImportedMenuItem {
  name: string
  /** Canonical "12.50", or null when the source had no usable price. */
  price: string | null
  description: string | null
  category: string | null
  is_signature: boolean
  /** 1 = read off a priced line; lower = inferred (section price, lowest of several). */
  confidence: number
  /** The price text when it could not be reduced to one number ("RM5 - RM8"). */
  price_raw: string | null
  source_line: string | null
}

export interface MenuImportPlan {
  menu_items_limit: number | null
  menu_items_used: number
  remaining: number | null
  unlimited: boolean
  allowed: boolean
  requires_renewal: boolean
}

export interface MenuImportResult {
  items: ImportedMenuItem[]
  categories: string[]
  warnings: string[]
  engine: 'ai-text' | 'ai-vision' | 'heuristic'
  mode: MenuImportMode
  source: { kind: string; pages: number; chars: number; images: number }
  total_found: number
  truncated: boolean
  skipped: string[]
  plan: MenuImportPlan | null
}

/** The create page's menu row. `description`/`category`/`isSignature` are
 *  new, optional, and only ever set by an import — the manual form leaves
 *  them undefined, which is what the backend saw before this feature. */
export interface MenuRow {
  url: string
  name: string
  price: string
  description?: string
  category?: string
  isSignature?: boolean
}

/** A draft row in the review table: the import plus the merchant's edits. */
export interface ReviewRow extends ImportedMenuItem {
  key: string
  selected: boolean
}

export const MENU_IMPORT_ACCEPT =
  '.pdf,.docx,.xlsx,.csv,.txt,.md,image/png,image/jpeg,image/webp,application/pdf,' +
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document,' +
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv,text/plain'

export const MENU_IMPORT_MAX_BYTES = 10 * 1024 * 1024

export type MenuImportFileKind = 'pdf' | 'docx' | 'xlsx' | 'csv' | 'text' | 'image' | null

/** What kind of file this is, from its name first and its MIME type second
 *  (phones often upload with a generic type). null = not something we read. */
export function detectFileKind(name: string, type?: string): MenuImportFileKind {
  const ext = (name.toLowerCase().match(/\.([a-z0-9]+)$/) || [])[1] || ''
  const mime = (type || '').toLowerCase()
  if (ext === 'pdf' || mime === 'application/pdf') return 'pdf'
  if (ext === 'docx' || mime.includes('wordprocessingml')) return 'docx'
  if (ext === 'xlsx' || mime.includes('spreadsheetml')) return 'xlsx'
  if (ext === 'csv' || mime === 'text/csv') return 'csv'
  if (ext === 'txt' || ext === 'md' || mime === 'text/plain' || mime === 'text/markdown') return 'text'
  if (['png', 'jpg', 'jpeg', 'webp'].includes(ext) || /^image\/(png|jpe?g|webp)$/.test(mime)) return 'image'
  return null
}

/** A one-line reason the file cannot be imported, or null when it can. */
export function validateImportFile(file: { name: string; type?: string; size: number }): string | null {
  if (!detectFileKind(file.name, file.type)) {
    return 'Format tidak disokong. Guna PDF, Word (.docx), Excel (.xlsx), CSV, teks atau gambar (JPG/PNG/WebP).'
  }
  if (file.size > MENU_IMPORT_MAX_BYTES) return 'Fail melebihi 10MB. Kecilkan fail atau ambil gambar setiap muka surat.'
  if (file.size === 0) return 'Fail kosong.'
  return null
}

export class MenuImportError extends Error {
  code: string
  status: number
  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = 'MenuImportError'
    this.code = code
    this.status = status
  }
}

export interface ExtractOptions {
  file?: File | null
  text?: string
  mode: MenuImportMode
  instruction?: string
  maxItems?: number
  language?: 'ms' | 'en'
  businessType?: string
  signal?: AbortSignal
}

function readErrorDetail(body: unknown, status: number): { code: string; message: string } {
  const detail = (body as { detail?: unknown })?.detail
  if (detail && typeof detail === 'object') {
    const d = detail as { error?: string; message?: string }
    return { code: d.error || `http_${status}`, message: d.message || 'Import gagal.' }
  }
  if (typeof detail === 'string') return { code: `http_${status}`, message: detail }
  return { code: `http_${status}`, message: status === 401 ? 'Sila log masuk semula.' : 'Import gagal. Cuba lagi.' }
}

/** Upload the file (or pasted text) and get the draft rows back. */
export async function extractMenu(opts: ExtractOptions): Promise<MenuImportResult> {
  const token = await getApiAuthToken()
  if (!token) throw new MenuImportError('unauthenticated', 'Sila log masuk untuk guna import menu.', 401)

  const form = new FormData()
  if (opts.file) form.append('file', opts.file, opts.file.name)
  if (opts.text && opts.text.trim()) form.append('text', opts.text.trim())
  form.append('mode', opts.mode)
  if (opts.instruction?.trim()) form.append('instruction', opts.instruction.trim())
  if (opts.maxItems) form.append('max_items', String(opts.maxItems))
  form.append('language', opts.language || 'ms')
  if (opts.businessType && opts.businessType !== 'auto') form.append('business_type', opts.businessType)

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}/api/v1/menu/import/extract`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
      signal: opts.signal,
    })
  } catch (err) {
    if ((err as Error)?.name === 'AbortError') throw err
    throw new MenuImportError('network', 'Tidak dapat sambung ke pelayan. Semak internet dan cuba lagi.', 0)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    const { code, message } = readErrorDetail(body, res.status)
    throw new MenuImportError(code, message, res.status)
  }
  return body as MenuImportResult
}

/** Draft rows → review rows: everything with a price is pre-ticked; a row
 *  with no price is shown unticked so the merchant fills it in on purpose. */
export function toReviewRows(items: ImportedMenuItem[]): ReviewRow[] {
  return items.map((item, index) => ({
    ...item,
    key: `${index}-${item.name}`,
    selected: item.price !== null,
  }))
}

export function normalizeName(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9À-ɏ]+/g, ' ').trim()
}

export interface MergeResult {
  gallery: MenuRow[]
  added: number
  /** Names skipped because an identical row already exists. */
  skipped: string[]
}

/**
 * Merge ticked review rows into the create page's gallery rows.
 *
 * - An empty placeholder row (no name, price or photo) is filled first, so
 *   the import does not leave a blank row above the real items.
 * - A name already on the list (case/space-insensitive) is skipped, never
 *   duplicated — re-importing the same PDF is a no-op.
 * - A ticked row with no price still comes through with `price: ''`; the
 *   manual field then shows it empty and the generator treats it as an item
 *   without a price (allowed) rather than inventing one.
 */
export function mergeImportedRows(existing: MenuRow[], rows: ReviewRow[]): MergeResult {
  const kept = existing.filter(r => (r.name || '').trim() || (r.price || '').trim() || r.url)
  const seen = new Set(kept.map(r => normalizeName(r.name)).filter(Boolean))
  const additions: MenuRow[] = []
  const skipped: string[] = []
  for (const row of rows) {
    if (!row.selected) continue
    const name = row.name.trim()
    if (!name) continue
    const key = normalizeName(name)
    if (seen.has(key)) {
      skipped.push(name)
      continue
    }
    seen.add(key)
    additions.push({
      url: '',
      name,
      price: row.price || '',
      description: row.description || undefined,
      category: row.category || undefined,
      isSignature: row.is_signature || undefined,
    })
  }
  return { gallery: [...kept, ...additions], added: additions.length, skipped }
}

/** Keep a typed price to digits and at most two decimals (same rule as the
 *  manual row's onChange). */
export function cleanPriceInput(raw: string): string {
  return raw
    .replace(/,/g, '.')
    .replace(/[^0-9.]/g, '')
    .replace(/(\..*)\./g, '$1')
    .replace(/^(\d*\.\d{0,2}).*$/, '$1')
}

/** Group review rows by category, preserving first-seen order; rows with
 *  no category go under the empty string key last. */
export function groupByCategory(rows: ReviewRow[]): Array<{ category: string; rows: ReviewRow[] }> {
  const order: string[] = []
  const buckets = new Map<string, ReviewRow[]>()
  for (const row of rows) {
    const cat = row.category || ''
    if (!buckets.has(cat)) {
      buckets.set(cat, [])
      if (cat) order.push(cat)
    }
    buckets.get(cat)!.push(row)
  }
  const out = order.map(category => ({ category, rows: buckets.get(category)! }))
  if (buckets.has('')) out.push({ category: '', rows: buckets.get('')! })
  return out
}

/** A short line for the summary strip above the review table. */
export function describeImport(result: Pick<MenuImportResult, 'engine' | 'total_found' | 'items' | 'source'>, language: 'ms' | 'en' = 'ms'): string {
  const n = result.items.length
  const found = result.total_found
  const engine =
    result.engine === 'ai-vision' ? (language === 'ms' ? 'AI baca gambar' : 'AI read the image')
    : result.engine === 'ai-text' ? (language === 'ms' ? 'AI baca teks' : 'AI read the text')
    : (language === 'ms' ? 'dibaca automatik' : 'parsed automatically')
  if (language === 'ms') {
    return found > n ? `${n} daripada ${found} item dipilih · ${engine}` : `${n} item dijumpai · ${engine}`
  }
  return found > n ? `${n} of ${found} items selected · ${engine}` : `${n} items found · ${engine}`
}

/** How many ticked rows exceed what the plan still allows (0 = fine). */
export function overPlanBy(selectedCount: number, plan: MenuImportPlan | null | undefined): number {
  if (!plan || plan.unlimited || plan.remaining === null) return 0
  return Math.max(0, selectedCount - plan.remaining)
}
