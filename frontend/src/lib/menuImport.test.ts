/**
 * menuImport — the pure rules behind the "Import menu" panel.
 *
 * What must hold: an import never duplicates a row the merchant already
 * typed, fills the blank placeholder row instead of leaving it, keeps an
 * unpriced row unticked, and reads the backend's error shape.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  cleanPriceInput,
  describeImport,
  detectFileKind,
  extractMenu,
  groupByCategory,
  mergeImportedRows,
  overPlanBy,
  toReviewRows,
  validateImportFile,
  type ImportedMenuItem,
  type MenuRow,
} from './menuImport'

vi.mock('@/lib/supabase', () => ({ getApiAuthToken: vi.fn(async () => 'tok') }))

function item(overrides: Partial<ImportedMenuItem> & { name: string }): ImportedMenuItem {
  return {
    price: '10.00',
    description: null,
    category: null,
    is_signature: false,
    confidence: 1,
    price_raw: null,
    source_line: null,
    ...overrides,
  }
}

describe('detectFileKind / validateImportFile', () => {
  it('reads the extension first and the MIME type second', () => {
    expect(detectFileKind('Menu.PDF')).toBe('pdf')
    expect(detectFileKind('menu.docx')).toBe('docx')
    expect(detectFileKind('upload', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')).toBe('xlsx')
    expect(detectFileKind('IMG_0001.jpeg', '')).toBe('image')
    expect(detectFileKind('blob', 'image/webp')).toBe('image')
    expect(detectFileKind('menu.pptx', 'application/octet-stream')).toBeNull()
  })

  it('rejects unsupported, empty and oversized files with a reason', () => {
    expect(validateImportFile({ name: 'menu.pdf', size: 1000 })).toBeNull()
    expect(validateImportFile({ name: 'deck.pptx', size: 1000 })).toMatch(/Format tidak disokong/)
    expect(validateImportFile({ name: 'menu.pdf', size: 0 })).toMatch(/kosong/)
    expect(validateImportFile({ name: 'menu.pdf', size: 11 * 1024 * 1024 })).toMatch(/10MB/)
  })
})

describe('toReviewRows', () => {
  it('pre-ticks priced rows and leaves unpriced rows for the merchant', () => {
    const rows = toReviewRows([item({ name: 'Set A' }), item({ name: 'Ikan Bakar', price: null, price_raw: 'ikut saiz' })])
    expect(rows.map(r => r.selected)).toEqual([true, false])
    expect(rows[0].key).toBe('0-Set A')
  })
})

describe('mergeImportedRows', () => {
  const imported = toReviewRows([
    item({ name: 'Set Panglima', price: '15.90', category: 'Set Ayam', is_signature: true, description: 'Nasi, ayam' }),
    item({ name: 'Set A', price: '12.50', category: 'Set Ayam' }),
    item({ name: 'teh o ice', price: '3.00' }),
  ])

  it('fills the blank placeholder row instead of leaving it above the items', () => {
    const existing: MenuRow[] = [{ url: '', name: '', price: '' }]
    const { gallery, added } = mergeImportedRows(existing, imported)
    expect(added).toBe(3)
    expect(gallery.map(r => r.name)).toEqual(['Set Panglima', 'Set A', 'teh o ice'])
  })

  it('never duplicates a row the merchant already typed', () => {
    const existing: MenuRow[] = [{ url: 'https://img/x.jpg', name: 'Teh O Ice', price: '3.50' }]
    const { gallery, added, skipped } = mergeImportedRows(existing, imported)
    expect(added).toBe(2)
    expect(skipped).toEqual(['teh o ice'])
    // The merchant's own row (with its photo and price) is untouched.
    expect(gallery[0]).toEqual({ url: 'https://img/x.jpg', name: 'Teh O Ice', price: '3.50' })
  })

  it('carries description, category and the signature flag onto the row', () => {
    const { gallery } = mergeImportedRows([], imported)
    expect(gallery[0]).toEqual({
      url: '', name: 'Set Panglima', price: '15.90', description: 'Nasi, ayam', category: 'Set Ayam', isSignature: true,
    })
    // Nothing optional is set when the import had nothing — the manual shape.
    expect(gallery[2]).toEqual({ url: '', name: 'teh o ice', price: '3.00', description: undefined, category: undefined, isSignature: undefined })
  })

  it('skips unticked rows and brings a ticked unpriced row through with an empty price', () => {
    const rows = toReviewRows([item({ name: 'Set A' }), item({ name: 'Ikan Bakar', price: null })])
    rows[0].selected = false
    rows[1].selected = true
    const { gallery } = mergeImportedRows([], rows)
    expect(gallery).toEqual([{ url: '', name: 'Ikan Bakar', price: '', description: undefined, category: undefined, isSignature: undefined }])
  })

  it('re-importing the same file is a no-op', () => {
    const first = mergeImportedRows([], imported)
    const second = mergeImportedRows(first.gallery, imported)
    expect(second.added).toBe(0)
    expect(second.gallery).toEqual(first.gallery)
  })
})

describe('small helpers', () => {
  it('cleanPriceInput mirrors the manual row rule', () => {
    expect(cleanPriceInput('RM12,505')).toBe('12.50')
    expect(cleanPriceInput('1.2.3')).toBe('1.23')
    expect(cleanPriceInput('abc')).toBe('')
  })

  it('groupByCategory keeps first-seen order and puts uncategorised rows last', () => {
    const rows = toReviewRows([
      item({ name: 'Teh', category: 'Minuman' }),
      item({ name: 'Keropok' }),
      item({ name: 'Set A', category: 'Set Ayam' }),
      item({ name: 'Kopi', category: 'Minuman' }),
    ])
    const groups = groupByCategory(rows)
    expect(groups.map(g => g.category)).toEqual(['Minuman', 'Set Ayam', ''])
    expect(groups[0].rows.map(r => r.name)).toEqual(['Teh', 'Kopi'])
  })

  it('describeImport reports the selection and the engine', () => {
    const base = { items: toReviewRows([item({ name: 'A' })]), source: { kind: 'pdf', pages: 1, chars: 10, images: 0 } }
    expect(describeImport({ ...base, engine: 'ai-text', total_found: 14 })).toBe('1 daripada 14 item dipilih · AI baca teks')
    expect(describeImport({ ...base, engine: 'heuristic', total_found: 1 }, 'en')).toBe('1 items found · parsed automatically')
  })

  it('overPlanBy counts only what exceeds the plan', () => {
    expect(overPlanBy(34, { menu_items_limit: 20, menu_items_used: 3, remaining: 17, unlimited: false, allowed: true, requires_renewal: false })).toBe(17)
    expect(overPlanBy(34, { menu_items_limit: null, menu_items_used: 3, remaining: null, unlimited: true, allowed: true, requires_renewal: false })).toBe(0)
    expect(overPlanBy(34, null)).toBe(0)
  })
})

describe('extractMenu', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts multipart with the mode and instruction and returns the draft', async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ items: [], engine: 'heuristic' }) }))
    vi.stubGlobal('fetch', fetchMock)
    const result = await extractMenu({ text: 'Nasi Lemak RM 8.50', mode: 'custom', instruction: '5 killer menu', language: 'en', businessType: 'food' })
    expect(result.engine).toBe('heuristic')
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/v1\/menu\/import\/extract$/)
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok')
    const form = init.body as FormData
    expect(form.get('mode')).toBe('custom')
    expect(form.get('instruction')).toBe('5 killer menu')
    expect(form.get('text')).toBe('Nasi Lemak RM 8.50')
    expect(form.get('language')).toBe('en')
    expect(form.get('business_type')).toBe('food')
  })

  it('surfaces the backend error code and message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: false, status: 415, json: async () => ({ detail: { error: 'unsupported_type', message: 'Format tidak disokong.' } }),
    })))
    await expect(extractMenu({ text: 'x', mode: 'all' })).rejects.toMatchObject({ code: 'unsupported_type', status: 415, message: 'Format tidak disokong.' })
  })

  it('turns a network failure into a readable error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    await expect(extractMenu({ text: 'x', mode: 'all' })).rejects.toMatchObject({ code: 'network' })
  })
})
