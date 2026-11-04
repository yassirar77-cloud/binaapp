'use client'

/**
 * MenuImportPanel — "Import menu (AI)" on the create page.
 *
 * Three steps, one card:
 *   1. INPUT   drop a PDF / Word / Excel / photo (or paste the text) and pick
 *              what to take: every item, signature items only, or a free
 *              instruction ("5 killer menu sahaja").
 *   2. READING the backend extracts (AI when reachable, the deterministic
 *              parser otherwise) and returns a DRAFT — nothing is saved.
 *   3. REVIEW  a table the merchant ticks and fixes (name, price, ★) before
 *              pressing "Tambah". Only ticked rows reach `onImport`.
 *
 * The panel owns no menu state: the page merges the ticked rows into the
 * same gallery rows the manual form fills (see lib/menuImport.ts).
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { FileText, Image as ImageIcon, Sparkles, Star, Upload, X as XIcon } from 'lucide-react'
import {
  MENU_IMPORT_ACCEPT,
  cleanPriceInput,
  describeImport,
  detectFileKind,
  extractMenu,
  groupByCategory,
  overPlanBy,
  toReviewRows,
  validateImportFile,
  type MenuImportMode,
  type MenuImportResult,
  type ReviewRow,
} from '@/lib/menuImport'

export interface MenuImportPanelProps {
  language: 'ms' | 'en'
  businessType: string
  /** Merge the ticked rows into the page's menu rows; return what happened. */
  onImport: (rows: ReviewRow[]) => { added: number; skipped: string[] }
  /** Back to the manual rows. */
  onClose: () => void
}

type Step = 'input' | 'reading' | 'review'

const T = {
  ms: {
    dropTitle: 'Drop menu anda di sini',
    dropSub: 'PDF, Word, Excel, CSV atau gambar papan menu · maks 10MB',
    orPaste: 'Atau tampal teks menu',
    pastePlaceholder: 'Tampal menu dari WhatsApp / nota, contoh:\nSet A  RM 12.50\nSet B  RM 13.50\nTeh O Ais  RM 2.50',
    hidePaste: 'Tutup teks',
    whichItems: 'Item mana nak diambil?',
    modeAll: 'Semua item',
    modeAllSub: 'Setiap item & harga dalam menu',
    modeSig: 'Signature sahaja',
    modeSigSub: 'Item bertanda signature / best seller',
    modeCustom: 'Ikut arahan saya',
    modeCustomSub: 'Cth: "5 killer menu sahaja"',
    instructionPlaceholder: 'Cth: 5 killer menu sahaja · set ayam dan minuman, kecuali add-on',
    examples: ['5 killer menu sahaja', 'set sahaja, tanpa minuman', 'minuman & dessert'],
    read: 'Baca menu dengan AI',
    reading: 'AI sedang baca menu anda…',
    readingSub: 'Draf dahulu — anda semak sebelum ditambah ke menu.',
    cancel: 'Batal',
    back: 'Kembali ke tulis sendiri',
    another: 'Import fail lain',
    selectAll: 'Pilih semua',
    selectNone: 'Nyahpilih semua',
    selected: (n: number) => `${n} dipilih`,
    addN: (n: number) => (n === 0 ? 'Pilih item dahulu' : `Tambah ${n} item ke menu`),
    noPrice: 'Tiada harga — isi dahulu',
    lowConfidence: 'Harga disimpulkan — semak',
    signature: 'Signature',
    onlySignature: 'Tunjuk signature sahaja',
    uncategorised: 'Tanpa kategori',
    overPlan: (n: number, remaining: number) =>
      `Pelan anda membenarkan ${remaining} lagi item menu — ${n} item yang dipilih melebihi had. Nyahpilih beberapa atau naik taraf.`,
    nothingFound: 'Tiada item dijumpai. Cuba fail lain, gambar yang lebih jelas, atau tampal teks menu.',
    skippedLabel: 'Dilangkau',
  },
  en: {
    dropTitle: 'Drop your menu here',
    dropSub: 'PDF, Word, Excel, CSV or a photo of the menu board · max 10MB',
    orPaste: 'Or paste the menu text',
    pastePlaceholder: 'Paste from WhatsApp / notes, e.g.\nSet A  RM 12.50\nSet B  RM 13.50\nIced Tea  RM 2.50',
    hidePaste: 'Hide text',
    whichItems: 'Which items should we take?',
    modeAll: 'Every item',
    modeAllSub: 'Each item & price on the menu',
    modeSig: 'Signature only',
    modeSigSub: 'Items marked signature / best seller',
    modeCustom: 'Follow my instruction',
    modeCustomSub: 'e.g. "5 killer menu only"',
    instructionPlaceholder: 'e.g. 5 killer menu only · sets and drinks, except add-ons',
    examples: ['5 killer menu only', 'sets only, no drinks', 'drinks & desserts'],
    read: 'Read menu with AI',
    reading: 'AI is reading your menu…',
    readingSub: 'Draft first — you review before anything is added.',
    cancel: 'Cancel',
    back: 'Back to manual entry',
    another: 'Import another file',
    selectAll: 'Select all',
    selectNone: 'Deselect all',
    selected: (n: number) => `${n} selected`,
    addN: (n: number) => (n === 0 ? 'Select items first' : `Add ${n} items to menu`),
    noPrice: 'No price — fill in first',
    lowConfidence: 'Price inferred — check',
    signature: 'Signature',
    onlySignature: 'Show signature only',
    uncategorised: 'No category',
    overPlan: (n: number, remaining: number) =>
      `Your plan allows ${remaining} more menu items — ${n} selected items exceed it. Untick some or upgrade.`,
    nothingFound: 'No items found. Try another file, a clearer photo, or paste the menu text.',
    skippedLabel: 'Skipped',
  },
} as const

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

const KIND_LABEL: Record<string, string> = { pdf: 'PDF', docx: 'Word', xlsx: 'Excel', csv: 'CSV', text: 'Teks', image: 'Gambar' }

export default function MenuImportPanel({ language, businessType, onImport, onClose }: MenuImportPanelProps) {
  const t = T[language]
  const [step, setStep] = useState<Step>('input')
  const [file, setFile] = useState<File | null>(null)
  const [pasteOpen, setPasteOpen] = useState(false)
  const [text, setText] = useState('')
  const [mode, setMode] = useState<MenuImportMode>('all')
  const [instruction, setInstruction] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [result, setResult] = useState<MenuImportResult | null>(null)
  const [rows, setRows] = useState<ReviewRow[]>([])
  const [onlySignature, setOnlySignature] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const canRead = Boolean(file) || text.trim().length > 0
  const fileKind = file ? detectFileKind(file.name, file.type) : null

  const pickFile = (candidate: File | null | undefined) => {
    if (!candidate) return
    const problem = validateImportFile(candidate)
    if (problem) { setError(problem); return }
    setError(null)
    setFile(candidate)
  }

  const read = async () => {
    if (!canRead) return
    if (mode === 'custom' && !instruction.trim()) {
      setError(language === 'ms' ? 'Tulis arahan anda dahulu, atau pilih "Semua item".' : 'Write your instruction first, or pick "Every item".')
      return
    }
    setError(null)
    setStep('reading')
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const res = await extractMenu({ file, text, mode, instruction, language, businessType, signal: controller.signal })
      setResult(res)
      setRows(toReviewRows(res.items))
      setOnlySignature(false)
      setStep('review')
    } catch (err) {
      if ((err as Error)?.name === 'AbortError') { setStep('input'); return }
      setError((err as Error)?.message || (language === 'ms' ? 'Import gagal. Cuba lagi.' : 'Import failed. Try again.'))
      setStep('input')
    } finally {
      abortRef.current = null
    }
  }

  const cancelRead = () => { abortRef.current?.abort() }

  const resetToInput = () => {
    setResult(null)
    setRows([])
    setFile(null)
    setText('')
    setError(null)
    setStep('input')
  }

  const updateRow = (key: string, patch: Partial<ReviewRow>) =>
    setRows(prev => prev.map(r => (r.key === key ? { ...r, ...patch } : r)))

  const visibleRows = useMemo(() => (onlySignature ? rows.filter(r => r.is_signature) : rows), [rows, onlySignature])
  const groups = useMemo(() => groupByCategory(visibleRows), [visibleRows])
  const selectedCount = rows.filter(r => r.selected && r.name.trim()).length
  const over = overPlanBy(selectedCount, result?.plan)
  const setAll = (selected: boolean) =>
    setRows(prev => prev.map(r => (visibleRows.some(v => v.key === r.key) ? { ...r, selected } : r)))

  const commit = () => {
    const ticked = rows.filter(r => r.selected && r.name.trim())
    if (!ticked.length) return
    onImport(ticked)
    resetToInput()
    onClose()
  }

  // ---------------------------------------------------------------- READING
  if (step === 'reading') {
    return (
      <div className="float-in" style={{ padding: '36px 20px', textAlign: 'center' }}>
        <div style={{ width: 44, height: 44, margin: '0 auto 14px', borderRadius: 14, background: 'rgba(79,61,255,.12)', border: '1px solid rgba(107,92,255,.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: 18, height: 18, border: '2px solid rgba(255,255,255,.2)', borderTopColor: '#C7FF3D', borderRadius: '50%', animation: 'spin .8s linear infinite' }} />
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: '#F5F5FA' }}>{t.reading}</div>
        <div style={{ fontSize: 12, color: '#86869A', marginTop: 6 }}>
          {file ? `${KIND_LABEL[fileKind || 'text']} · ${file.name}` : (language === 'ms' ? 'Teks yang ditampal' : 'Pasted text')} · {t.readingSub}
        </div>
        <button type="button" className="cr-btn cr-btn-ghost" onClick={cancelRead} style={{ marginTop: 18, padding: '8px 14px', fontSize: 13 }}>{t.cancel}</button>
      </div>
    )
  }

  // ----------------------------------------------------------------- REVIEW
  if (step === 'review' && result) {
    return (
      <div className="float-in" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
            <span className="pill pill-volt" style={{ padding: '3px 8px', fontSize: 9 }}>
              <span className="led" /> {result.engine === 'heuristic' ? 'AUTO' : 'AI'}
            </span>
            <span style={{ fontSize: 13, color: '#B8B8C8' }}>{describeImport(result, language)}</span>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {rows.some(r => r.is_signature) && (
              <button type="button" className={'chip' + (onlySignature ? ' chip-on' : '')} onClick={() => setOnlySignature(v => !v)} style={{ fontSize: 12, cursor: 'pointer' }}>
                <Star size={12} fill={onlySignature ? '#C7FF3D' : 'none'} color={onlySignature ? '#C7FF3D' : '#B8B8C8'} /> {t.onlySignature}
              </button>
            )}
            <button type="button" className="chip" onClick={() => setAll(true)} style={{ fontSize: 12, cursor: 'pointer' }}>{t.selectAll}</button>
            <button type="button" className="chip" onClick={() => setAll(false)} style={{ fontSize: 12, cursor: 'pointer' }}>{t.selectNone}</button>
          </div>
        </div>

        {(result.warnings.length > 0 || over > 0) && (
          <div className="banner-accent" style={{ margin: 0, background: 'linear-gradient(90deg, rgba(255,176,32,.06), transparent)', border: '1px solid rgba(255,176,32,.22)', flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
            <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#FFB020' }} />
            {over > 0 && result.plan && result.plan.remaining !== null && (
              <span style={{ fontSize: 13, color: '#FFB020', fontWeight: 600 }}>{t.overPlan(selectedCount, result.plan.remaining)}</span>
            )}
            {result.warnings.map((w, i) => (
              <span key={i} style={{ fontSize: 12, color: '#FFB020' }}>{w}</span>
            ))}
          </div>
        )}

        {rows.length === 0 ? (
          <div style={{ padding: '22px 12px', textAlign: 'center', color: '#86869A', fontSize: 13 }}>{t.nothingFound}</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 520, overflowY: 'auto', paddingRight: 2 }}>
            {groups.map(group => (
              <div key={group.category || '__none'}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '2px 0 6px' }}>
                  <span className="eyebrow" style={{ color: group.category ? '#B8B8C8' : '#5A5A6E' }}>{group.category || t.uncategorised}</span>
                  <span className="num" style={{ fontSize: 10, color: '#5A5A6E' }}>{group.rows.length}</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {group.rows.map(row => (
                    <div
                      key={row.key}
                      className="mi-row"
                      style={{
                        display: 'grid', gridTemplateColumns: '24px 28px minmax(0,1fr) 104px', gap: 8, alignItems: 'center',
                        padding: '8px 10px', borderRadius: 12,
                        background: row.selected ? '#0F0F1A' : 'rgba(15,15,26,.5)',
                        border: `1px solid ${row.selected ? 'rgba(255,255,255,.08)' : 'rgba(255,255,255,.04)'}`,
                        opacity: row.selected ? 1 : 0.6,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={row.selected}
                        onChange={e => updateRow(row.key, { selected: e.target.checked })}
                        aria-label={row.name}
                        style={{ width: 16, height: 16, accentColor: '#C7FF3D', cursor: 'pointer' }}
                      />
                      <button
                        type="button"
                        onClick={() => updateRow(row.key, { is_signature: !row.is_signature })}
                        title={t.signature}
                        aria-pressed={row.is_signature}
                        style={{ width: 28, height: 28, border: 0, background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      >
                        <Star size={15} fill={row.is_signature ? '#C7FF3D' : 'none'} color={row.is_signature ? '#C7FF3D' : '#5A5A6E'} />
                      </button>
                      <div style={{ minWidth: 0 }}>
                        <input
                          className="cr-input"
                          value={row.name}
                          onChange={e => updateRow(row.key, { name: e.target.value })}
                          style={{ background: 'transparent', border: '1px solid rgba(255,255,255,.04)', height: 36, padding: '0 10px', width: '100%', minWidth: 0 }}
                        />
                        {(row.description || row.price_raw || row.confidence < 1) && (
                          <div style={{ fontSize: 11, color: '#5A5A6E', marginTop: 3, paddingLeft: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {row.price === null && <span style={{ color: '#FFB020' }}>{t.noPrice}{row.price_raw ? ` (${row.price_raw})` : ''} · </span>}
                            {row.price !== null && row.confidence < 1 && <span style={{ color: '#FFB020' }}>{t.lowConfidence} · </span>}
                            {row.description}
                          </div>
                        )}
                      </div>
                      <div className="mi-row-price" style={{ position: 'relative', minWidth: 0 }}>
                        <span className="num" style={{ position: 'absolute', left: 10, top: 18, transform: 'translateY(-50%)', fontSize: 11, color: '#5A5A6E', pointerEvents: 'none' }}>RM</span>
                        <input
                          className="cr-input"
                          placeholder="0.00"
                          inputMode="decimal"
                          value={row.price ?? ''}
                          onChange={e => {
                            const cleaned = cleanPriceInput(e.target.value)
                            updateRow(row.key, { price: cleaned ? cleaned : null, confidence: 1 })
                          }}
                          style={{ background: 'transparent', border: `1px solid ${row.price === null && row.selected ? 'rgba(255,176,32,.5)' : 'rgba(255,255,255,.04)'}`, height: 36, padding: '0 10px 0 32px', fontFamily: "'Geist Mono', monospace", width: '100%', minWidth: 0 }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {result.skipped.length > 0 && (
          <div style={{ fontSize: 11, color: '#5A5A6E' }}>{t.skippedLabel}: {result.skipped.slice(0, 8).join(', ')}{result.skipped.length > 8 ? ' …' : ''}</div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', paddingTop: 6, borderTop: '1px solid rgba(255,255,255,.06)' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="cr-btn cr-btn-ghost" onClick={resetToInput} style={{ padding: '9px 14px', fontSize: 13 }}>{t.another}</button>
            <button type="button" className="cr-btn cr-btn-ghost" onClick={onClose} style={{ padding: '9px 14px', fontSize: 13 }}>{t.cancel}</button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="num" style={{ fontSize: 11, color: '#86869A' }}>{t.selected(selectedCount)}</span>
            <button
              type="button"
              className="cr-btn"
              onClick={commit}
              disabled={selectedCount === 0}
              style={{ padding: '10px 16px', fontSize: 13, background: selectedCount ? 'linear-gradient(180deg, #D4FF5C, #C7FF3D)' : 'rgba(255,255,255,.06)', color: selectedCount ? '#05050C' : '#5A5A6E', cursor: selectedCount ? 'pointer' : 'not-allowed' }}
            >
              {t.addN(selectedCount)}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ------------------------------------------------------------------ INPUT
  return (
    <div className="float-in" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); pickFile(e.dataTransfer.files?.[0]) }}
        role="button"
        tabIndex={0}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
        style={{
          border: `1.5px dashed ${dragOver ? 'rgba(199,255,61,.6)' : file ? 'rgba(199,255,61,.35)' : 'rgba(255,255,255,.14)'}`,
          borderRadius: 14, padding: file ? 14 : '22px 16px', cursor: 'pointer',
          background: dragOver ? 'rgba(199,255,61,.04)' : 'rgba(255,255,255,.015)', transition: 'all 200ms',
          display: 'flex', alignItems: 'center', gap: 14, justifyContent: file ? 'flex-start' : 'center', flexDirection: file ? 'row' : 'column', textAlign: 'center',
        }}
      >
        <input ref={inputRef} type="file" accept={MENU_IMPORT_ACCEPT} onChange={e => { pickFile(e.target.files?.[0]); e.target.value = '' }} style={{ display: 'none' }} />
        {file ? (
          <>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(199,255,61,.1)', border: '1px solid rgba(199,255,61,.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#C7FF3D', flexShrink: 0 }}>
              {fileKind === 'image' ? <ImageIcon size={18} /> : <FileText size={18} />}
            </div>
            <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#F5F5FA', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.name}</div>
              <div className="num" style={{ fontSize: 11, color: '#86869A' }}>{KIND_LABEL[fileKind || 'text']} · {formatBytes(file.size)}</div>
            </div>
            <button type="button" aria-label="Buang fail" onClick={e => { e.stopPropagation(); setFile(null) }} className="cr-btn-icon" style={{ width: 30, height: 30 }}><XIcon size={13} /></button>
          </>
        ) : (
          <>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(79,61,255,.1)', border: '1px solid rgba(107,92,255,.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#BAB0FF' }}>
              <Upload size={18} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#F5F5FA' }}>{t.dropTitle}</div>
              <div style={{ fontSize: 12, color: '#86869A', marginTop: 4 }}>{t.dropSub}</div>
            </div>
          </>
        )}
      </div>

      <div>
        <button type="button" onClick={() => setPasteOpen(v => !v)} style={{ background: 'transparent', border: 0, color: '#86869A', fontSize: 12, cursor: 'pointer', padding: 0, textDecoration: 'underline dotted' }}>
          {pasteOpen ? t.hidePaste : t.orPaste}
        </button>
        {pasteOpen && (
          <textarea
            className="cr-input float-in"
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder={t.pastePlaceholder}
            rows={5}
            style={{ marginTop: 8, resize: 'vertical', fontFamily: "'Geist Mono', monospace", fontSize: 13, lineHeight: 1.5 }}
          />
        )}
      </div>

      <div>
        <div className="eyebrow" style={{ marginBottom: 8 }}>{t.whichItems}</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8 }}>
          {([
            { id: 'all' as const, l: t.modeAll, s: t.modeAllSub, icon: <FileText size={15} /> },
            { id: 'signature' as const, l: t.modeSig, s: t.modeSigSub, icon: <Star size={15} /> },
            { id: 'custom' as const, l: t.modeCustom, s: t.modeCustomSub, icon: <Sparkles size={15} /> },
          ]).map(m => (
            <div
              key={m.id}
              role="radio"
              aria-checked={mode === m.id}
              tabIndex={0}
              className={'opt ' + (mode === m.id ? 'selected' : '')}
              onClick={() => setMode(m.id)}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setMode(m.id) } }}
              style={{ padding: '11px 12px', display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}
            >
              <div style={{ width: 30, height: 30, borderRadius: 8, background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#B8B8C8', flexShrink: 0 }}>{m.icon}</div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{m.l}</div>
                <div style={{ fontSize: 11, color: '#86869A', marginTop: 1 }}>{m.s}</div>
              </div>
            </div>
          ))}
        </div>
        {mode === 'custom' && (
          <div className="float-in" style={{ marginTop: 10 }}>
            <input
              className="cr-input"
              value={instruction}
              onChange={e => setInstruction(e.target.value)}
              placeholder={t.instructionPlaceholder}
              maxLength={400}
            />
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
              {t.examples.map(ex => (
                <button key={ex} type="button" className="chip" onClick={() => setInstruction(ex)} style={{ fontSize: 12, cursor: 'pointer' }}>{ex}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="banner-accent" style={{ margin: 0, background: 'linear-gradient(90deg, rgba(255,90,95,.08), transparent)', border: '1px solid rgba(255,90,95,.25)' }}>
          <div style={{ position: 'absolute', top: 0, bottom: 0, left: 0, width: 3, background: '#FF5A5F' }} />
          <span style={{ fontSize: 13, color: '#FF8A8E' }}>{error}</span>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
        <button type="button" className="cr-btn cr-btn-ghost" onClick={onClose} style={{ padding: '9px 14px', fontSize: 13 }}>{t.back}</button>
        <button
          type="button"
          className="cr-btn"
          onClick={read}
          disabled={!canRead}
          style={{ padding: '10px 18px', fontSize: 13, background: canRead ? 'linear-gradient(180deg, #6B5CFF, #4F3DFF)' : 'rgba(255,255,255,.06)', color: canRead ? '#fff' : '#5A5A6E', cursor: canRead ? 'pointer' : 'not-allowed', boxShadow: canRead ? '0 0 0 1px rgba(107,92,255,.5), 0 8px 24px rgba(79,61,255,.3)' : 'none' }}
        >
          <Sparkles size={15} /> {t.read}
        </button>
      </div>
    </div>
  )
}
