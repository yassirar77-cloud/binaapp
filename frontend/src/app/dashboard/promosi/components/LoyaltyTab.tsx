'use client'

import { useEffect, useState } from 'react'

import {
  adjustLoyaltyPoints,
  fetchLoyalty,
  fetchLoyaltyMembers,
  loyaltySummary,
  saveLoyalty,
  type LoyaltyMember,
  type LoyaltySettings,
} from '@/lib/promotions'

import { Button, Field, Notice, TextInput, errorText } from '../../tempahan/components/ui'

interface Draft {
  enabled: boolean
  points_per_rm: string
  redeem_points: string
  redeem_value: string
}

const toDraft = (s: LoyaltySettings): Draft => ({
  enabled: s.enabled,
  points_per_rm: String(s.points_per_rm),
  redeem_points: String(s.redeem_points),
  redeem_value: String(s.redeem_value),
})

/** Parsed settings, or a Malay message describing what is wrong. */
function parseDraft(d: Draft): LoyaltySettings | string {
  const perRm = Number(d.points_per_rm.replace(',', '.'))
  const points = Number(d.redeem_points)
  const value = Number(d.redeem_value.replace(',', '.'))
  if (!(perRm > 0) || perRm > 100) return 'Mata bagi setiap RM1 mesti antara 0.01 hingga 100.'
  if (!Number.isInteger(points) || points < 1) return 'Mata untuk tebusan mesti nombor bulat, sekurang-kurangnya 1.'
  if (!(value > 0)) return 'Nilai tebusan (RM) mesti lebih daripada 0.'
  return { enabled: d.enabled, points_per_rm: perRm, redeem_points: points, redeem_value: value }
}

export default function LoyaltyTab({ websiteId }: { websiteId: string }) {
  const [draft, setDraft] = useState<Draft | null>(null)
  const [members, setMembers] = useState<LoyaltyMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [formError, setFormError] = useState('')

  const [adjustPhone, setAdjustPhone] = useState('')
  const [adjustPoints, setAdjustPoints] = useState('')
  const [adjusting, setAdjusting] = useState(false)
  const [adjustNote, setAdjustNote] = useState<{ tone: 'error' | 'success'; text: string } | null>(null)

  const loadMembers = async () => {
    try {
      setMembers(await fetchLoyaltyMembers(websiteId))
    } catch {
      // The list is secondary; a failure here must not hide the settings.
      setMembers([])
    }
  }

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      try {
        const settings = await fetchLoyalty(websiteId)
        if (!active) return
        setDraft(toDraft(settings))
        setError('')
      } catch (err) {
        if (active) setError(errorText(err, 'Gagal memuatkan tetapan mata ganjaran.'))
      } finally {
        if (active) setLoading(false)
      }
      await loadMembers()
    }
    load()
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [websiteId])

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => {
    setSaved(false)
    setFormError('')
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  const save = async () => {
    if (!draft) return
    const parsed = parseDraft(draft)
    if (typeof parsed === 'string') {
      setFormError(parsed)
      return
    }
    setSaving(true)
    try {
      setDraft(toDraft(await saveLoyalty(websiteId, parsed)))
      setSaved(true)
      setFormError('')
    } catch (err) {
      setFormError(errorText(err, 'Gagal menyimpan tetapan.'))
    } finally {
      setSaving(false)
    }
  }

  const adjust = async () => {
    const points = Number(adjustPoints)
    if (adjustPhone.trim().length < 9) {
      setAdjustNote({ tone: 'error', text: 'Masukkan nombor telefon pelanggan.' })
      return
    }
    if (!Number.isInteger(points) || points === 0) {
      setAdjustNote({ tone: 'error', text: 'Masukkan bilangan mata (nombor bulat, negatif untuk tolak).' })
      return
    }
    setAdjusting(true)
    try {
      const result = await adjustLoyaltyPoints(websiteId, adjustPhone.trim(), points)
      setAdjustNote({
        tone: 'success',
        text: `Baki ${result.customer_phone} kini ${result.balance} mata.`,
      })
      setAdjustPoints('')
      await loadMembers()
    } catch (err) {
      setAdjustNote({ tone: 'error', text: errorText(err, 'Gagal melaras mata.') })
    } finally {
      setAdjusting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
      </div>
    )
  }
  if (error || !draft) {
    return <Notice tone="error">{error || 'Gagal memuatkan tetapan.'}</Notice>
  }

  const preview = parseDraft(draft)

  return (
    <div className="space-y-4">
      <form
        className="dash-surface p-5 space-y-4"
        onSubmit={(e) => {
          e.preventDefault()
          void save()
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-white">Program mata ganjaran</h2>
            <p className="text-[13px] text-white/45 mt-0.5 max-w-xl">
              Pelanggan kumpul mata apabila pesanan selesai, dan tebus sebagai diskaun pada pesanan
              seterusnya. Mata dikira ikut nombor telefon.
            </p>
          </div>
          <label className="flex items-center gap-2.5 text-[13px] text-white/80 cursor-pointer">
            <input
              type="checkbox"
              role="switch"
              checked={draft.enabled}
              onChange={(e) => set('enabled', e.target.checked)}
              className="h-4 w-4 accent-[#C7FF3D]"
            />
            {draft.enabled ? 'Dihidupkan' : 'Dimatikan'}
          </label>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Mata bagi setiap RM1" hint="Dikira atas harga makanan selepas diskaun.">
            <TextInput
              value={draft.points_per_rm}
              onChange={(e) => set('points_per_rm', e.target.value)}
              inputMode="decimal"
            />
          </Field>
          <Field label="Mata untuk satu tebusan">
            <TextInput
              value={draft.redeem_points}
              onChange={(e) => set('redeem_points', e.target.value)}
              inputMode="numeric"
            />
          </Field>
          <Field label="Nilai satu tebusan (RM)">
            <TextInput
              value={draft.redeem_value}
              onChange={(e) => set('redeem_value', e.target.value)}
              inputMode="decimal"
            />
          </Field>
        </div>

        {typeof preview !== 'string' && <Notice tone="info">{loyaltySummary(preview)}</Notice>}
        {formError && <Notice tone="error">{formError}</Notice>}
        {saved && <Notice tone="success">Tetapan disimpan.</Notice>}

        <Button variant="primary" type="submit" disabled={saving}>
          {saving ? 'Menyimpan…' : 'Simpan tetapan'}
        </Button>
      </form>

      <div className="dash-surface p-5 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Laras mata pelanggan</h2>
          <p className="text-[13px] text-white/45 mt-0.5">
            Beri mata tambahan sebagai tanda terima kasih, atau betulkan baki. Guna nombor negatif
            untuk menolak.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-[1fr_160px_auto] sm:items-end">
          <Field label="Nombor telefon pelanggan">
            <TextInput
              value={adjustPhone}
              onChange={(e) => {
                setAdjustPhone(e.target.value)
                setAdjustNote(null)
              }}
              inputMode="tel"
              placeholder="cth: 0123456789"
            />
          </Field>
          <Field label="Mata">
            <TextInput
              value={adjustPoints}
              onChange={(e) => {
                setAdjustPoints(e.target.value)
                setAdjustNote(null)
              }}
              inputMode="numeric"
              placeholder="cth: 50"
            />
          </Field>
          <Button onClick={adjust} disabled={adjusting} className="h-[38px]">
            {adjusting ? 'Melaras…' : 'Laras'}
          </Button>
        </div>
        {adjustNote && <Notice tone={adjustNote.tone}>{adjustNote.text}</Notice>}
      </div>

      <div className="dash-surface p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Ahli ({members.length})</h2>
        {members.length === 0 ? (
          <p className="text-[13px] text-white/40">
            Belum ada pelanggan dengan mata. Mata direkod apabila pesanan pertama selesai.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="text-[11px] uppercase tracking-wider text-white/40">
                  <th className="font-medium pb-2 pr-4">Telefon</th>
                  <th className="font-medium pb-2 pr-4 text-right">Baki</th>
                  <th className="font-medium pb-2 text-right">Jumlah dikumpul</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.06]">
                {members.map((m) => (
                  <tr key={m.customer_phone}>
                    <td className="py-2 pr-4 font-mono text-white/80">{m.customer_phone}</td>
                    <td className="py-2 pr-4 text-right font-mono text-[#C7FF3D]">{m.balance}</td>
                    <td className="py-2 text-right font-mono text-white/55">{m.lifetime_earned ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
