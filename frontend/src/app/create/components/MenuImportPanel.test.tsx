// @vitest-environment jsdom
/**
 * MenuImportPanel — the three steps a merchant walks through.
 *
 * What must hold: the "read" button stays off until there is a file or
 * text; a custom mode needs an instruction; the review table pre-ticks
 * priced rows; untick, re-price and ★ edits reach `onImport`; the panel
 * returns to the manual rows afterwards.
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import MenuImportPanel from './MenuImportPanel'
import type { MenuImportResult, ReviewRow } from '@/lib/menuImport'

const extractMenu = vi.fn()

vi.mock('@/lib/menuImport', async () => {
  const actual = await vi.importActual<typeof import('@/lib/menuImport')>('@/lib/menuImport')
  return { ...actual, extractMenu: (...args: unknown[]) => extractMenu(...args) }
})

function result(overrides: Partial<MenuImportResult> = {}): MenuImportResult {
  return {
    items: [
      { name: 'Set Panglima', price: '15.90', description: 'Nasi, ayam', category: 'Set Ayam', is_signature: true, confidence: 1, price_raw: null, source_line: null },
      { name: 'Set A', price: '12.50', description: null, category: 'Set Ayam', is_signature: false, confidence: 1, price_raw: null, source_line: null },
      { name: 'Ikan Bakar', price: null, description: null, category: 'Lauk', is_signature: false, confidence: 0.5, price_raw: 'RM15 - RM25', source_line: null },
    ],
    categories: ['Set Ayam', 'Lauk'],
    warnings: ['1 item tiada harga — isi sebelum tambah ke menu.'],
    engine: 'ai-text',
    mode: 'all',
    source: { kind: 'docx', pages: 1, chars: 1200, images: 0 },
    total_found: 3,
    truncated: false,
    skipped: ['Bakso Daging'],
    plan: { menu_items_limit: 20, menu_items_used: 19, remaining: 1, unlimited: false, allowed: true, requires_renewal: false },
    ...overrides,
  }
}

describe('MenuImportPanel', () => {
  const onImport = vi.fn((_rows: ReviewRow[]) => ({ added: 2, skipped: [] as string[] }))
  const onClose = vi.fn()

  beforeEach(() => {
    extractMenu.mockReset()
    onImport.mockClear()
    onClose.mockClear()
  })
  afterEach(cleanup)

  function mount() {
    return render(<MenuImportPanel language="ms" businessType="food" onImport={onImport} onClose={onClose} />)
  }

  it('keeps the read button off until there is something to read', () => {
    mount()
    const read = screen.getByRole('button', { name: /Baca menu dengan AI/ })
    expect((read as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByText('Atau tampal teks menu'))
    fireEvent.change(screen.getByPlaceholderText(/Tampal menu/), { target: { value: 'Nasi Lemak RM 8.50' } })
    expect((read as HTMLButtonElement).disabled).toBe(false)
  })

  it('custom mode needs an instruction before it calls the backend', () => {
    mount()
    fireEvent.click(screen.getByText('Atau tampal teks menu'))
    fireEvent.change(screen.getByPlaceholderText(/Tampal menu/), { target: { value: 'Nasi Lemak RM 8.50' } })
    fireEvent.click(screen.getByText('Ikut arahan saya'))
    fireEvent.click(screen.getByRole('button', { name: /Baca menu dengan AI/ }))
    expect(extractMenu).not.toHaveBeenCalled()
    expect(screen.getByText(/Tulis arahan anda dahulu/)).toBeTruthy()
    // An example chip fills the instruction.
    fireEvent.click(screen.getByText('5 killer menu sahaja'))
    fireEvent.click(screen.getByRole('button', { name: /Baca menu dengan AI/ }))
    expect(extractMenu).toHaveBeenCalledWith(expect.objectContaining({ mode: 'custom', instruction: '5 killer menu sahaja', text: 'Nasi Lemak RM 8.50', businessType: 'food', language: 'ms' }))
  })

  it('rejects an unsupported file with a reason and never uploads it', () => {
    mount()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['x'], 'deck.pptx', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [file] } })
    expect(screen.getByText(/Format tidak disokong/)).toBeTruthy()
    expect((screen.getByRole('button', { name: /Baca menu dengan AI/ }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('shows the draft, pre-ticks priced rows, and sends edits to onImport', async () => {
    extractMenu.mockResolvedValue(result())
    mount()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [new File(['x'], 'menu.docx', { type: '' })] } })
    expect(screen.getByText('menu.docx')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Baca menu dengan AI/ }))

    await waitFor(() => expect(screen.getByText(/3 item dijumpai · AI baca teks/)).toBeTruthy())
    // Categories are shown as group headings; the warning and the skipped list are visible.
    expect(screen.getByText('Set Ayam')).toBeTruthy()
    expect(screen.getByText(/tiada harga — isi sebelum/)).toBeTruthy()
    expect(screen.getByText(/Dilangkau: Bakso Daging/)).toBeTruthy()
    // 2 priced rows ticked, the unpriced one not; the plan allows only 1 → warning.
    expect(screen.getByText('2 dipilih')).toBeTruthy()
    expect(screen.getByText(/membenarkan 1 lagi item menu/)).toBeTruthy()

    // Untick Set A, give Ikan Bakar a price and tick it, un-star Set Panglima.
    fireEvent.click(screen.getByRole('checkbox', { name: 'Set A' }))
    const priceInputs = screen.getAllByPlaceholderText('0.00')
    fireEvent.change(priceInputs[2], { target: { value: 'RM18,5' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Ikan Bakar' }))
    fireEvent.click(screen.getAllByTitle('Signature')[0])
    expect(screen.getByText('2 dipilih')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Tambah 2 item ke menu/ }))
    expect(onImport).toHaveBeenCalledTimes(1)
    const rows = onImport.mock.calls[0][0]
    expect(rows.map(r => [r.name, r.price, r.is_signature])).toEqual([
      ['Set Panglima', '15.90', false],
      ['Ikan Bakar', '18.5', false],
    ])
    expect(onClose).toHaveBeenCalled()
  })

  it('shows the backend error and returns to the input step', async () => {
    extractMenu.mockRejectedValue(Object.assign(new Error('Fail ini tidak dapat dibaca.'), { code: 'unreadable' }))
    mount()
    fireEvent.click(screen.getByText('Atau tampal teks menu'))
    fireEvent.change(screen.getByPlaceholderText(/Tampal menu/), { target: { value: 'x RM 1.00' } })
    fireEvent.click(screen.getByRole('button', { name: /Baca menu dengan AI/ }))
    await waitFor(() => expect(screen.getByText('Fail ini tidak dapat dibaca.')).toBeTruthy())
    expect(screen.getByRole('button', { name: /Baca menu dengan AI/ })).toBeTruthy()
  })

  it('"Kembali" hands control back to the manual rows', () => {
    mount()
    fireEvent.click(screen.getByRole('button', { name: /Kembali ke tulis sendiri/ }))
    expect(onClose).toHaveBeenCalled()
  })
})
