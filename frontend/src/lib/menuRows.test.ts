import { describe, it, expect } from 'vitest'
import {
  categoriesOf, clearMenuRows, loadMenuRows, menuRowsWarning, parseMenuPaste,
  rowsForRequest, saveMenuRows, slugMismatchWarning, slugifyBusinessName,
} from './menuRows'

const PANGLIMA_PASTE = `Set Ayam: Set A – Ayam Gepuk 12.50 | Set B – Ayam Gepuk Tauhu Tempe 13.50 | Set C – Ayam Gepuk Kubis Goreng 14.50 | Set Panglima Krispy – Ayam Krispy 14.90 | Set Panglima Signature – Ayam Gepuk Telur Mata 15.90
Set Seafood Krispy: Set Sotong Krispy 20.90 | Set Udang Krispy 22.90
Tambahan: Ayam Gepuk Ori 7.00 | Sotong Krispy 15.00 | Udang Krispy 16.00 | Pedal Ayam Goreng (3 pcs) 3.00 | Tauhu Goreng (3 pcs) 3.00 | Tempe Goreng (3 pcs) 3.00 | Telur Mata 2.00 | Kubis Goreng 3.70 | Enoki Mushroom Goreng 4.50 | Nasi Putih 2.50 | Sambal Extra 3.00 | Sambal Gajus Extra 3.50 | Keropok 2.00 | Sup 1.00
Minuman: Teh O Ice 3.00 | Teh O Ice Limau 3.50 | Sirap Limau Ice 3.50 | Limau Ice 3.50 | Air Mineral 500ml 2.00 | Air Mineral 1.5L 3.50
Special Drink: Bali Blues 5.00 | Es Jeruk 5.00
Kid's Menu: Fries 5.00 | Fries + Tender Chicken (3 pcs) 9.90 | Fries + Nugget (5 pcs) 7.90`

describe('parseMenuPaste', () => {
  it('reads the Ayam Gepuk Panglima menu: 32 items, prices and sections intact', () => {
    const rows = parseMenuPaste(PANGLIMA_PASTE)
    expect(rows).toHaveLength(32)
    expect(rows[0]).toEqual({ url: '', name: 'Set A – Ayam Gepuk', price: '12.50', category: 'Set Ayam' })
    expect(rows.find(r => r.name === 'Air Mineral 1.5L')?.price).toBe('3.50')
    expect(rows.find(r => r.name === 'Fries + Nugget (5 pcs)')).toEqual({ url: '', name: 'Fries + Nugget (5 pcs)', price: '7.90', category: "Kid's Menu" })
    expect(categoriesOf(rows)).toEqual(['Set Ayam', 'Set Seafood Krispy', 'Tambahan', 'Minuman', 'Special Drink', "Kid's Menu"])
  })

  it('treats a short unpriced line followed by priced lines as a section label', () => {
    const rows = parseMenuPaste('Minuman\nTeh O Ice RM3.00\nLimau Ice - RM 3.50\nKid\'s Menu:\nFries 5')
    expect(rows).toEqual([
      { url: '', name: 'Teh O Ice', price: '3.00', category: 'Minuman' },
      { url: '', name: 'Limau Ice', price: '3.50', category: 'Minuman' },
      { url: '', name: 'Fries', price: '5', category: "Kid's Menu" },
    ])
  })

  it('keeps an unpriced item as an item when nothing marks it as a label', () => {
    expect(parseMenuPaste('Nasi Lemak Istimewa')).toEqual([{ url: '', name: 'Nasi Lemak Istimewa', price: '', category: '' }])
  })

  it('does not read a size in the name as the price', () => {
    expect(parseMenuPaste('Air Mineral 500ml 2.00')[0]).toMatchObject({ name: 'Air Mineral 500ml', price: '2.00' })
  })
})

describe('rowsForRequest', () => {
  it('sends every named row, with category and photo when present, and drops blanks', () => {
    const out = rowsForRequest([
      { url: '', name: ' Sup ', price: '1.00', category: 'Tambahan' },
      { url: 'https://cdn/x.jpg', name: 'Set A', price: '', category: '' },
      { url: '', name: '', price: '9.00' },
    ])
    expect(out).toEqual([
      { name: 'Sup', price: '1.00', category: 'Tambahan', image_url: undefined },
      { name: 'Set A', price: '', category: undefined, image_url: 'https://cdn/x.jpg' },
    ])
  })
})

describe('menuRowsWarning', () => {
  it('warns a food business that is about to generate with no items', () => {
    expect(menuRowsWarning([{ url: '', name: '', price: '' }], 'food', '')).toMatch(/Tiada item menu/)
    expect(menuRowsWarning([], 'auto', 'Restoran ayam gepuk di Klang')).toMatch(/Tiada item menu/)
  })
  it('stays quiet when items exist or the business is not food', () => {
    expect(menuRowsWarning([{ url: '', name: 'Set A', price: '12.50' }], 'food', '')).toBeNull()
    expect(menuRowsWarning([], 'salon', 'Salon rambut di Shah Alam')).toBeNull()
  })
})

describe('menu row draft storage', () => {
  const mem = () => {
    const m = new Map<string, string>()
    return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => { m.set(k, v) }, removeItem: (k: string) => { m.delete(k) } }
  }
  it('round-trips rows and clears them', () => {
    const store = mem()
    saveMenuRows([{ url: '', name: 'Sup', price: '1.00', category: 'Tambahan' }, { url: '', name: '', price: '' }], store)
    expect(loadMenuRows(store)).toEqual([{ url: '', name: 'Sup', price: '1.00', category: 'Tambahan' }])
    clearMenuRows(store)
    expect(loadMenuRows(store)).toEqual([])
  })
  it('ignores corrupt storage', () => {
    const store = mem()
    store.setItem('binaapp:create:menuRows:v1', '{not json')
    expect(loadMenuRows(store)).toEqual([])
  })
})

describe('slugMismatchWarning', () => {
  it('flags ayamgepukpaglima as a misspelling of Ayam Gepuk Panglima', () => {
    expect(slugifyBusinessName('Ayam Gepuk Panglima')).toBe('ayamgepukpanglima')
    const w = slugMismatchWarning('ayamgepukpaglima', 'Ayam Gepuk Panglima')
    expect(w?.suggestion).toBe('ayamgepukpanglima')
    expect(w?.message).toMatch(/salah eja/)
  })
  it('is silent for the exact slug and for a deliberately different one', () => {
    expect(slugMismatchWarning('ayamgepukpanglima', 'Ayam Gepuk Panglima')).toBeNull()
    expect(slugMismatchWarning('ayam-gepuk-panglima', 'Ayam Gepuk Panglima')).toBeNull()
    expect(slugMismatchWarning('panglima-klang', 'Ayam Gepuk Panglima')).toBeNull()
    expect(slugMismatchWarning('kedai', 'Ayam Gepuk Panglima')).toBeNull()
  })
})
