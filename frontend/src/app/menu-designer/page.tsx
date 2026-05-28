'use client'

import { useMemo, useState, type FormEvent } from 'react'
import { Trash2, Check, Plus, FileDown, Loader2 } from 'lucide-react'
import { API_BASE_URL } from '@/lib/env'

type CategoryId = 'makanan-berat' | 'minuman' | 'roti-snack' | 'pencuci-mulut'

interface MenuItem {
  id: string
  name: string
  price: string
  description: string
  cat: CategoryId
}

interface CategoryDef {
  id: CategoryId
  label: string
  dot: string
}

const CATEGORIES: CategoryDef[] = [
  { id: 'makanan-berat', label: 'Makanan Berat', dot: 'bg-orange-500' },
  { id: 'minuman', label: 'Minuman', dot: 'bg-sky-500' },
  { id: 'roti-snack', label: 'Roti & Snack', dot: 'bg-amber-500' },
  { id: 'pencuci-mulut', label: 'Pencuci Mulut', dot: 'bg-pink-500' },
]

type SizeId = 'A4' | 'A5' | 'Letter' | 'Banner'

const SIZES: { id: SizeId; label: string; sub: string }[] = [
  { id: 'A4', label: 'A4', sub: '210×297' },
  { id: 'A5', label: 'A5', sub: '148×210' },
  { id: 'Letter', label: 'Letter', sub: '8.5×11"' },
  { id: 'Banner', label: 'Banner', sub: '3×2 ft' },
]

type ThemeId = 'classic' | 'warm' | 'modern' | 'forest' | 'ocean' | 'rose'

interface ThemeDef {
  id: ThemeId
  name: string
  paper: string
  ink: string
  accent: string
  font: string
}

const THEMES: ThemeDef[] = [
  { id: 'classic', name: 'Classic', paper: '#FAF7F0', ink: '#2B2A29', accent: '#B5894E', font: '"Geist", "Times New Roman", serif' },
  { id: 'warm',    name: 'Warm',    paper: '#F5E9D6', ink: '#5B3A1E', accent: '#D96B2A', font: '"Geist", Georgia, serif' },
  { id: 'modern',  name: 'Modern',  paper: '#FFFFFF', ink: '#0B0B15', accent: '#4F3DFF', font: '"Geist", system-ui, sans-serif' },
  { id: 'forest',  name: 'Forest',  paper: '#F4F1E8', ink: '#1F3D2B', accent: '#2E7D4F', font: '"Geist", Georgia, serif' },
  { id: 'ocean',   name: 'Ocean',   paper: '#F2F7FB', ink: '#0A2540', accent: '#1196EA', font: '"Geist", system-ui, sans-serif' },
  { id: 'rose',    name: 'Rose',    paper: '#FBF1F3', ink: '#4A1F2E', accent: '#C2185B', font: '"Geist", Georgia, serif' },
]

function uid() {
  return Math.random().toString(36).slice(2, 10)
}

function fmtPrice(p: string) {
  const n = parseFloat(p.replace(',', '.'))
  return isNaN(n) ? `RM${p}` : `RM${n.toFixed(2)}`
}

function catLabel(id: CategoryId) {
  return CATEGORIES.find(c => c.id === id)?.label ?? ''
}

export default function MenuDesigner() {
  const [businessName, setBusinessName] = useState('')
  const [subtitle, setSubtitle] = useState('')
  const [size, setSize] = useState<SizeId>('A4')
  const [themeId, setThemeId] = useState<ThemeId>('modern')
  const [items, setItems] = useState<MenuItem[]>([])
  const [activeTab, setActiveTab] = useState<'all' | CategoryId>('all')
  const [loading, setLoading] = useState(false)
  const [pdfUrl, setPdfUrl] = useState('')

  // form state
  const [formName, setFormName] = useState('')
  const [formCat, setFormCat] = useState<CategoryId>('makanan-berat')
  const [formPrice, setFormPrice] = useState('')
  const [formDesc, setFormDesc] = useState('')

  const theme = THEMES.find(t => t.id === themeId)!

  const counts = useMemo(() => {
    const base: Record<string, number> = { all: items.length }
    for (const c of CATEGORIES) base[c.id] = 0
    for (const it of items) base[it.cat] = (base[it.cat] ?? 0) + 1
    return base
  }, [items])

  const filtered = activeTab === 'all' ? items : items.filter(i => i.cat === activeTab)

  const stats = useMemo(() => {
    const total = items.length
    const cats = new Set(items.map(i => i.cat)).size
    const prices = items.map(i => parseFloat(i.price)).filter(n => !isNaN(n))
    const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : 0
    return { total, cats, avg }
  }, [items])

  function addItem(e: FormEvent) {
    e.preventDefault()
    const name = formName.trim()
    const price = formPrice.trim()
    if (!name || !price) return
    setItems(prev => [...prev, { id: uid(), name, price, description: formDesc.trim(), cat: formCat }])
    setFormName('')
    setFormPrice('')
    setFormDesc('')
  }

  function removeItem(id: string) {
    setItems(prev => prev.filter(i => i.id !== id))
  }

  async function generateMenu() {
    if (!businessName.trim()) {
      alert('Sila isi nama perniagaan dahulu.')
      return
    }
    if (items.length === 0) {
      alert('Sila tambah sekurang-kurangnya satu item menu.')
      return
    }

    setLoading(true)
    setPdfUrl('')
    try {
      const backendSize = size === 'Banner' ? 'banner' : size

      const payload = {
        business_name: businessName,
        subtitle,
        items: items.map(({ name, price, description, cat }) => ({
          name,
          price,
          description,
          cat,
        })),
        size: backendSize,
        style: themeId,
      }

      const res = await fetch(`${API_BASE_URL}/api/generate-menu`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()

      if (data.success) {
        setPdfUrl(data.pdf_url)
      } else {
        alert('Menu generation failed: ' + (data.error || data.detail || 'unknown'))
      }
    } catch (err) {
      console.error(err)
      alert('Failed to generate menu')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-ink-050" style={{ fontFamily: '"Geist", system-ui, -apple-system, sans-serif' }}>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">Menu Designer</h1>
          <p className="mt-2 text-sm text-ink-500">
            Reka menu cetak profesional untuk restoran anda — pratonton langsung, eksport ke PDF.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* LEFT — editor */}
          <section className="lg:col-span-7 space-y-6">
            {/* Business name + size */}
            <div className="rounded-2xl border border-ink-100 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <label htmlFor="biz" className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-ink-500">
                    Nama Perniagaan
                  </label>
                  <input
                    id="biz"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    placeholder="Contoh: Kedai Nasi Kandar Khulafa"
                    className="w-full rounded-lg border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                  />
                </div>
                <div className="sm:max-w-xs">
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-ink-500">
                    Saiz
                  </label>
                  <div className="inline-flex rounded-lg bg-ink-100 p-1">
                    {SIZES.map(s => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => setSize(s.id)}
                        className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                          size === s.id
                            ? 'bg-white text-ink-900 shadow-sm'
                            : 'text-ink-500 hover:text-ink-700'
                        }`}
                        title={s.sub}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <label htmlFor="subtitle" className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-ink-500">
                  Subtajuk (pilihan)
                </label>
                <input
                  id="subtitle"
                  value={subtitle}
                  onChange={(e) => setSubtitle(e.target.value)}
                  placeholder="Contoh: Menu Hari Ini, Cawangan Sungai Petani…"
                  className="w-full rounded-lg border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                />
              </div>
            </div>

            {/* Theme cards */}
            <div className="rounded-2xl border border-ink-100 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-ink-900">Tema</h2>
                <span className="text-xs text-ink-400">Pratonton sahaja buat masa ini</span>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {THEMES.map(t => {
                  const active = t.id === themeId
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setThemeId(t.id)}
                      className={`group relative rounded-xl border p-3 text-left transition ${
                        active
                          ? 'border-brand-500 ring-2 ring-brand-100'
                          : 'border-ink-200 hover:border-ink-300'
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="h-5 w-5 rounded-full ring-1 ring-black/5" style={{ background: t.paper }} />
                        <span className="h-5 w-5 rounded-full ring-1 ring-black/5" style={{ background: t.ink }} />
                        <span className="h-5 w-5 rounded-full ring-1 ring-black/5" style={{ background: t.accent }} />
                        {active && (
                          <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full bg-brand-500 text-white">
                            <Check className="h-3 w-3" />
                          </span>
                        )}
                      </div>
                      <div className="mt-2 text-sm font-medium text-ink-900">{t.name}</div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Category tabs + items */}
            <div className="rounded-2xl border border-ink-100 bg-white p-5 shadow-sm">
              <div className="mb-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('all')}
                  className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                    activeTab === 'all'
                      ? 'border-ink-900 bg-ink-900 text-white'
                      : 'border-ink-200 bg-white text-ink-700 hover:border-ink-300'
                  }`}
                >
                  <span className="h-2 w-2 rounded-full bg-ink-400" />
                  Semua
                  <span className={`rounded-full px-1.5 text-[10px] font-semibold ${activeTab === 'all' ? 'bg-white/20 text-white' : 'bg-ink-100 text-ink-600'}`}>
                    {counts.all ?? 0}
                  </span>
                </button>
                {CATEGORIES.map(c => {
                  const active = activeTab === c.id
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => setActiveTab(c.id)}
                      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                        active
                          ? 'border-ink-900 bg-ink-900 text-white'
                          : 'border-ink-200 bg-white text-ink-700 hover:border-ink-300'
                      }`}
                    >
                      <span className={`h-2 w-2 rounded-full ${c.dot}`} />
                      {c.label}
                      <span className={`rounded-full px-1.5 text-[10px] font-semibold ${active ? 'bg-white/20 text-white' : 'bg-ink-100 text-ink-600'}`}>
                        {counts[c.id] ?? 0}
                      </span>
                    </button>
                  )
                })}
              </div>

              {filtered.length === 0 ? (
                <div className="rounded-xl border border-dashed border-ink-200 px-4 py-10 text-center text-sm text-ink-400">
                  {items.length === 0
                    ? 'Belum ada item. Tambah item pertama anda di bawah.'
                    : 'Tiada item dalam kategori ini.'}
                </div>
              ) : (
                <ul className="space-y-2">
                  {filtered.map(item => (
                    <li
                      key={item.id}
                      className="group flex items-start gap-3 rounded-xl border border-ink-100 bg-white p-3 transition hover:border-ink-200 hover:shadow-sm"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="truncate text-sm font-semibold text-ink-900">{item.name}</span>
                          <span className="rounded-md bg-ink-100 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-ink-600">
                            {catLabel(item.cat)}
                          </span>
                        </div>
                        {item.description && (
                          <p className="mt-1 line-clamp-2 text-xs text-ink-500">{item.description}</p>
                        )}
                      </div>
                      <div className="shrink-0 text-right">
                        <div className="font-mono text-sm font-semibold text-ink-900">{fmtPrice(item.price)}</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeItem(item.id)}
                        aria-label="Buang item"
                        className="shrink-0 rounded-md p-1.5 text-ink-400 transition hover:bg-err-400/10 hover:text-err-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {/* Add item form (dark surface) */}
              <form
                onSubmit={addItem}
                className="mt-5 rounded-xl bg-ink-900 p-4 text-white"
              >
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_auto]">
                  <input
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="Nama item (cth: Nasi Ayam)"
                    className="rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-white placeholder:text-ink-400 focus:border-volt-400 focus:outline-none"
                    required
                  />
                  <select
                    value={formCat}
                    onChange={(e) => setFormCat(e.target.value as CategoryId)}
                    className="rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-white focus:border-volt-400 focus:outline-none"
                  >
                    {CATEGORIES.map(c => (
                      <option key={c.id} value={c.id}>{c.label}</option>
                    ))}
                  </select>
                  <div className="flex items-stretch overflow-hidden rounded-md border border-ink-700 bg-ink-800">
                    <span className="flex items-center px-2.5 font-mono text-xs text-ink-400">RM</span>
                    <input
                      value={formPrice}
                      onChange={(e) => setFormPrice(e.target.value)}
                      inputMode="decimal"
                      placeholder="0.00"
                      className="w-24 bg-transparent px-1 py-2 text-sm text-white placeholder:text-ink-500 focus:outline-none"
                      required
                    />
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
                  <input
                    value={formDesc}
                    onChange={(e) => setFormDesc(e.target.value)}
                    placeholder="Penerangan (pilihan)"
                    className="rounded-md border border-ink-700 bg-ink-800 px-3 py-2 text-sm text-white placeholder:text-ink-400 focus:border-volt-400 focus:outline-none"
                  />
                  <button
                    type="submit"
                    className="inline-flex items-center justify-center gap-1.5 rounded-md bg-volt-400 px-4 py-2 text-sm font-semibold text-ink-900 transition hover:bg-volt-300 active:scale-[0.98]"
                  >
                    <Plus className="h-4 w-4" />
                    Tambah
                  </button>
                </div>
              </form>
            </div>

            {/* Generate CTA */}
            <button
              type="button"
              onClick={generateMenu}
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-500 px-6 py-4 text-base font-semibold text-white shadow-lg shadow-brand-500/20 transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Menjana PDF…
                </>
              ) : (
                <>
                  <FileDown className="h-5 w-5" />
                  Generate Menu PDF
                </>
              )}
            </button>

            {pdfUrl && (
              <div className="rounded-xl border border-ok-400/30 bg-ok-400/5 p-4">
                <p className="text-sm font-semibold text-ok-500">PDF berjaya dijana.</p>
                <a
                  href={pdfUrl}
                  download
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 underline-offset-2 hover:underline"
                >
                  <FileDown className="h-4 w-4" /> Muat turun PDF
                </a>
              </div>
            )}
          </section>

          {/* RIGHT — sticky stats + preview */}
          <aside className="lg:col-span-5">
            <div className="lg:sticky lg:top-6 space-y-4">
              {/* Stat cards */}
              <div className="grid grid-cols-3 gap-3">
                <StatCard label="Jumlah Item" value={String(stats.total)} />
                <StatCard label="Kategori" value={String(stats.cats)} />
                <StatCard label="Harga Purata" value={stats.avg ? `RM${stats.avg.toFixed(2)}` : '—'} />
              </div>

              {/* Live preview */}
              <div className="rounded-2xl border border-ink-100 bg-white p-4 shadow-sm">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">Pratonton Langsung</span>
                  <span className="font-mono text-[10px] text-ink-400">{size} · {theme.name}</span>
                </div>
                <MenuPreview
                  theme={theme}
                  businessName={businessName || 'Nama Perniagaan'}
                  subtitle={subtitle}
                  items={items}
                />
                <p className="mt-3 text-center text-[11px] text-ink-400">Dibina dengan binaapp.</p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink-100 bg-white p-3 shadow-sm">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-ink-400">{label}</div>
      <div className="mt-1 font-mono text-xl font-bold text-ink-900">{value}</div>
    </div>
  )
}

function MenuPreview({
  theme,
  businessName,
  subtitle,
  items,
}: {
  theme: ThemeDef
  businessName: string
  subtitle: string
  items: MenuItem[]
}) {
  const grouped = CATEGORIES
    .map(c => ({ cat: c, list: items.filter(i => i.cat === c.id) }))
    .filter(g => g.list.length > 0)

  return (
    <div
      className="relative w-full overflow-hidden rounded-lg ring-1 ring-black/5"
      style={{
        aspectRatio: '1 / 1.414',
        background: theme.paper,
        color: theme.ink,
        fontFamily: theme.font,
      }}
    >
      <div className="absolute inset-0 overflow-auto px-[6%] py-[7%]">
        <div className="text-center">
          <div
            className="text-[clamp(14px,2.8vw,28px)] font-bold leading-tight tracking-tight"
            style={{ color: theme.ink }}
          >
            {businessName}
          </div>
          {subtitle && (
            <div
              className="mt-1 text-[clamp(9px,1.4vw,12px)] uppercase tracking-[0.18em]"
              style={{ color: theme.accent }}
            >
              {subtitle}
            </div>
          )}
          <div
            className="mx-auto mt-3 h-[2px] w-16"
            style={{ background: theme.accent }}
          />
        </div>

        {grouped.length === 0 ? (
          <div
            className="mt-10 text-center text-[clamp(9px,1.4vw,12px)] italic"
            style={{ color: theme.ink, opacity: 0.5 }}
          >
            Tambah item untuk lihat pratonton…
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            {grouped.map(({ cat, list }) => (
              <div key={cat.id}>
                <div
                  className="mb-1.5 text-[clamp(9px,1.4vw,12px)] font-semibold uppercase tracking-[0.18em]"
                  style={{ color: theme.accent }}
                >
                  {cat.label}
                </div>
                <ul className="space-y-1.5">
                  {list.map(item => (
                    <li key={item.id} className="flex items-baseline gap-2">
                      <span
                        className="text-[clamp(10px,1.6vw,14px)] font-semibold"
                        style={{ color: theme.ink }}
                      >
                        {item.name}
                      </span>
                      <span
                        className="flex-1 self-end border-b border-dotted"
                        style={{ borderColor: theme.ink, opacity: 0.25 }}
                      />
                      <span
                        className="text-[clamp(10px,1.6vw,14px)] font-semibold tabular-nums"
                        style={{ color: theme.accent }}
                      >
                        {fmtPrice(item.price)}
                      </span>
                    </li>
                  ))}
                  {list.some(i => i.description) && (
                    <li className="pt-0.5">
                      {list
                        .filter(i => i.description)
                        .map(i => (
                          <p
                            key={i.id + '-desc'}
                            className="text-[clamp(8px,1.2vw,10px)] italic leading-snug"
                            style={{ color: theme.ink, opacity: 0.65 }}
                          >
                            {i.name}: {i.description}
                          </p>
                        ))}
                    </li>
                  )}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
