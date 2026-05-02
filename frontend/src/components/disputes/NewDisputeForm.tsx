'use client'

import { useState, type ChangeEvent } from 'react'
import { GhostButton } from '@/app/profile/components/primitives/GhostButton'
import { PrimaryButton } from '@/app/profile/components/primitives/PrimaryButton'
import { DisputeModalShell } from './DisputeModalShell'
import { SUBSCRIBER_CATEGORIES } from './constants'
import {
  useDisputeMutations,
  type CreateDisputeResult,
  type SubscriberCategoryKey,
} from './useDisputeMutations'
import {
  MAX_EVIDENCE_IMAGES,
  POST_COMPRESSION_MAX_BYTES,
  PRE_COMPRESSION_WARN_BYTES,
  compressImage,
  formatBytes,
  type CompressedImage,
} from './imageCompression'

interface NewDisputeFormProps {
  open: boolean
  onClose: () => void
  websites: Array<{ id: string; label: string }>
  onSubmitted: () => void
  onShowToast: (msg: string, tone: 'success' | 'error') => void
}

type Step = 'form' | 'submitting' | 'result'

const MIN_DESCRIPTION = 10
const MAX_DESCRIPTION = 500

export function NewDisputeForm({
  open,
  onClose,
  websites,
  onSubmitted,
  onShowToast,
}: NewDisputeFormProps) {
  const [step, setStep] = useState<Step>('form')
  const [category, setCategory] = useState<SubscriberCategoryKey | null>(null)
  const [description, setDescription] = useState('')
  const [websiteId, setWebsiteId] = useState('')
  const [evidence, setEvidence] = useState<CompressedImage[]>([])
  const [imageError, setImageError] = useState<string | null>(null)
  const [imageProcessing, setImageProcessing] = useState(false)
  const [result, setResult] = useState<CreateDisputeResult | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const { createDispute, submitting } = useDisputeMutations()

  function reset() {
    setStep('form')
    setCategory(null)
    setDescription('')
    setWebsiteId('')
    setEvidence([])
    setImageError(null)
    setImageProcessing(false)
    setResult(null)
    setFormError(null)
  }

  function handleClose() {
    const wasResult = step === 'result'
    onClose()
    // Reset after a tick so the closing transition still shows the result text
    setTimeout(reset, 50)
    if (wasResult) onSubmitted()
  }

  async function handleEvidenceUpload(e: ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files || files.length === 0) return
    setImageError(null)
    setImageProcessing(true)
    try {
      const remaining = MAX_EVIDENCE_IMAGES - evidence.length
      const toProcess = Array.from(files).slice(0, remaining)
      const next: CompressedImage[] = []
      for (const file of toProcess) {
        if (file.size > PRE_COMPRESSION_WARN_BYTES) {
          setImageError(
            `"${file.name}" terlalu besar (${formatBytes(file.size)}). Cuba pilih gambar di bawah ${formatBytes(PRE_COMPRESSION_WARN_BYTES)}.`,
          )
          continue
        }
        try {
          const compressed = await compressImage(file)
          next.push(compressed)
        } catch (err) {
          setImageError(err instanceof Error ? err.message : 'Gagal proses gambar')
        }
      }
      if (next.length > 0) setEvidence((prev) => [...prev, ...next])
    } finally {
      setImageProcessing(false)
      // Reset input so the same file can be re-picked
      e.target.value = ''
    }
  }

  function removeEvidence(index: number) {
    setEvidence((prev) => prev.filter((_, i) => i !== index))
  }

  async function handleSubmit() {
    setFormError(null)
    if (!category) {
      setFormError('Sila pilih kategori aduan')
      return
    }
    if (description.trim().length < MIN_DESCRIPTION) {
      setFormError(`Sila terangkan masalah anda (minimum ${MIN_DESCRIPTION} aksara)`)
      return
    }

    setStep('submitting')
    try {
      const res = await createDispute({
        category,
        description: description.trim(),
        website_id: websiteId || undefined,
        evidence_urls: evidence.length > 0 ? evidence.map((e) => e.dataUrl) : undefined,
      })
      setResult(res)
      setStep('result')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ralat sistem. Sila cuba lagi.'
      onShowToast(msg, 'error')
      setStep('form')
      setFormError(msg)
    }
  }

  const title =
    step === 'submitting'
      ? 'Menghantar aduan…'
      : step === 'result'
        ? 'Keputusan aduan'
        : 'Buat aduan baru'

  const subtitle = step === 'form' ? 'Beritahu kami masalah yang anda hadapi dengan BinaApp' : undefined

  const submitDisabled =
    !category || description.trim().length < MIN_DESCRIPTION || submitting || imageProcessing

  return (
    <DisputeModalShell open={open} onClose={handleClose} title={title} subtitle={subtitle} maxWidth={560}>
      {step === 'form' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <section>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-2)', marginBottom: 8 }}>
              Kategori aduan
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))',
                gap: 8,
              }}
            >
              {SUBSCRIBER_CATEGORIES.map((cat) => {
                const selected = category === cat.key
                return (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => setCategory(cat.key)}
                    aria-pressed={selected}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                      padding: '12px 8px',
                      minHeight: 80,
                      background: selected ? '#fff5ed' : '#fff',
                      border: selected ? '1px solid var(--orange)' : '0.5px solid var(--border-strong)',
                      boxShadow: selected ? '0 0 0 3px rgba(249,115,22,0.12)' : 'none',
                      borderRadius: 'var(--r-input)',
                      cursor: 'pointer',
                      transition: 'background 120ms, border-color 120ms',
                      fontFamily: 'inherit',
                      letterSpacing: 'inherit',
                    }}
                    title={cat.desc}
                  >
                    <span style={{ fontSize: 22, lineHeight: 1 }}>{cat.icon}</span>
                    <span style={{ fontSize: 11, color: 'var(--ink-1)', fontWeight: 500, textAlign: 'center', lineHeight: 1.2 }}>
                      {cat.label}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>

          <section>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-2)' }}>
                Terangkan masalah anda secara terperinci
              </span>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, MAX_DESCRIPTION))}
                placeholder="Sila terangkan masalah yang anda hadapi…"
                rows={4}
                style={{
                  background: '#fff',
                  border: '0.5px solid var(--border-strong)',
                  borderRadius: 'var(--r-input)',
                  padding: '10px 12px',
                  fontFamily: 'inherit',
                  fontSize: 14,
                  resize: 'vertical',
                  color: 'var(--ink-1)',
                  letterSpacing: 'inherit',
                  outline: 'none',
                }}
              />
              <span style={{ fontSize: 11, color: 'var(--ink-3)', alignSelf: 'flex-end' }}>
                {description.length}/{MAX_DESCRIPTION}
              </span>
            </label>
          </section>

          {websites.length > 0 && (
            <section>
              <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-2)' }}>
                  Laman web berkaitan <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>(pilihan)</span>
                </span>
                <select
                  value={websiteId}
                  onChange={(e) => setWebsiteId(e.target.value)}
                  style={{
                    background: '#fff',
                    border: '0.5px solid var(--border-strong)',
                    borderRadius: 'var(--r-input)',
                    padding: '10px 12px',
                    fontFamily: 'inherit',
                    fontSize: 14,
                    color: 'var(--ink-1)',
                  }}
                >
                  <option value="">— Tiada (umum) —</option>
                  {websites.map((w) => (
                    <option key={w.id} value={w.id}>{w.label}</option>
                  ))}
                </select>
              </label>
            </section>
          )}

          <section>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink-2)', marginBottom: 6 }}>
              Bukti{' '}
              <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>
                (pilihan, maks {MAX_EVIDENCE_IMAGES} gambar, {formatBytes(POST_COMPRESSION_MAX_BYTES)} sekeping)
              </span>
            </div>

            {evidence.length > 0 && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                {evidence.map((img, i) => (
                  <div
                    key={i}
                    style={{
                      position: 'relative',
                      width: 72,
                      height: 72,
                      borderRadius: 'var(--r-input)',
                      overflow: 'hidden',
                      border: '0.5px solid var(--border-strong)',
                    }}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={img.dataUrl}
                      alt={`Bukti ${i + 1}`}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                    <button
                      type="button"
                      onClick={() => removeEvidence(i)}
                      aria-label={`Buang bukti ${i + 1}`}
                      style={{
                        position: 'absolute',
                        top: 2,
                        right: 2,
                        background: 'rgba(15,17,26,0.7)',
                        color: '#fff',
                        border: 0,
                        width: 20,
                        height: 20,
                        borderRadius: '50%',
                        cursor: 'pointer',
                        fontSize: 12,
                        lineHeight: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      ×
                    </button>
                    <span
                      style={{
                        position: 'absolute',
                        bottom: 0,
                        left: 0,
                        right: 0,
                        background: 'rgba(15,17,26,0.55)',
                        color: '#fff',
                        fontSize: 9,
                        textAlign: 'center',
                        padding: '1px 0',
                      }}
                    >
                      {formatBytes(img.bytes)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {evidence.length < MAX_EVIDENCE_IMAGES && (
              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  padding: '10px 12px',
                  border: '1px dashed var(--border-strong)',
                  borderRadius: 'var(--r-input)',
                  cursor: imageProcessing ? 'wait' : 'pointer',
                  fontSize: 13,
                  color: 'var(--ink-2)',
                  background: '#fff',
                }}
              >
                {imageProcessing
                  ? 'Memproses gambar…'
                  : `+ Tambah gambar (${evidence.length}/${MAX_EVIDENCE_IMAGES})`}
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleEvidenceUpload}
                  disabled={imageProcessing}
                  style={{ display: 'none' }}
                />
              </label>
            )}

            {imageError && (
              <div
                role="alert"
                style={{
                  marginTop: 8,
                  fontSize: 12,
                  color: 'var(--pill-amber-fg)',
                  background: 'var(--pill-amber-bg)',
                  padding: '6px 10px',
                  borderRadius: 'var(--r-input)',
                }}
              >
                {imageError}
              </div>
            )}
          </section>

          {formError && (
            <div
              role="alert"
              style={{
                fontSize: 13,
                color: 'var(--pill-red-fg)',
                background: 'var(--pill-red-bg)',
                padding: '8px 12px',
                borderRadius: 'var(--r-input)',
              }}
            >
              {formError}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 4 }}>
            <GhostButton onClick={handleClose}>Batal</GhostButton>
            <PrimaryButton onClick={handleSubmit} disabled={submitDisabled}>
              {submitting ? 'Menghantar…' : 'Hantar aduan'}
            </PrimaryButton>
          </div>
        </div>
      )}

      {step === 'submitting' && (
        <div style={{ padding: '32px 0', textAlign: 'center' }}>
          <div
            style={{
              width: 36,
              height: 36,
              border: '3px solid var(--border)',
              borderTopColor: 'var(--orange)',
              borderRadius: '50%',
              margin: '0 auto 14px',
              animation: 'profile-spin 800ms linear infinite',
            }}
          />
          <div style={{ fontSize: 14, color: 'var(--ink-1)', fontWeight: 500 }}>AI sedang menganalisis…</div>
          <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 4 }}>Sila tunggu sebentar</div>
          <style jsx>{`
            @keyframes profile-spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      )}

      {step === 'result' && result && (
        <div style={{ padding: '8px 0', textAlign: 'center' }}>
          <ResultIcon status={result.status} />
          <h3 style={{ fontSize: 16, fontWeight: 500, margin: '12px 0 6px', color: 'var(--ink-1)' }}>
            {result.status === 'approved'
              ? 'Diluluskan'
              : result.status === 'rejected'
                ? 'Ditolak'
                : 'Dalam semakan'}
          </h3>
          <p style={{ fontSize: 13, color: 'var(--ink-2)', margin: 0 }}>{result.message}</p>
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: 18 }}>
            <PrimaryButton onClick={handleClose}>Tutup</PrimaryButton>
          </div>
        </div>
      )}
    </DisputeModalShell>
  )
}

function ResultIcon({ status }: { status: CreateDisputeResult['status'] }) {
  const config =
    status === 'approved'
      ? { bg: 'var(--pill-green-bg)', fg: 'var(--pill-green-fg)', glyph: '✓' }
      : status === 'rejected'
        ? { bg: 'var(--pill-red-bg)', fg: 'var(--pill-red-fg)', glyph: '×' }
        : { bg: 'var(--pill-amber-bg)', fg: 'var(--pill-amber-fg)', glyph: '!' }
  return (
    <div
      style={{
        width: 56,
        height: 56,
        borderRadius: '50%',
        background: config.bg,
        color: config.fg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 26,
        fontWeight: 600,
        margin: '0 auto',
      }}
    >
      {config.glyph}
    </div>
  )
}
