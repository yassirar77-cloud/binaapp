'use client'

import { useEffect, useState } from 'react'

import {
  createVoucher,
  deleteVoucher,
  EMPTY_VOUCHER_FORM,
  fetchVouchers,
  normalizeVoucherCode,
  setVoucherActive,
  usageText,
  VOUCHER_STATE_LABEL,
  voucherFormProblem,
  voucherState,
  type Voucher,
  type VoucherForm,
  type VoucherState,
} from '@/lib/promotions'

import { Button, Field, Notice, TextInput, errorText, inputClass } from '../../tempahan/components/ui'

const STATE_TONE: Record<VoucherState, string> = {
  active: 'bg-[#C7FF3D]/15 text-[#C7FF3D]',
  paused: 'bg-white/[0.08] text-white/60',
  scheduled: 'bg-sky-400/15 text-sky-300',
  expired: 'bg-[#FF5A5F]/15 text-[#FF9A9D]',
  used_up: 'bg-amber-400/15 text-amber-300',
}

function formatExpiry(iso: string | null): string {
  if (!iso) return 'Tiada tarikh tamat'
  try {
    return `Tamat ${new Date(iso).toLocaleDateString('ms-MY', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'Asia/Kuala_Lumpur',
    })}`
  } catch {
    return ''
  }
}

export default function VouchersTab({ websiteId }: { websiteId: string }) {
  const [vouchers, setVouchers] = useState<Voucher[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState<VoucherForm | null>(null)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      setVouchers(await fetchVouchers(websiteId))
      setError('')
    } catch (err) {
      setError(errorText(err, 'Gagal memuatkan baucar.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [websiteId])

  const set = <K extends keyof VoucherForm>(key: K, value: VoucherForm[K]) => {
    setFormError('')
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  const submit = async () => {
    if (!form) return
    const problem = voucherFormProblem(form)
    if (problem) {
      setFormError(problem)
      return
    }
    setSaving(true)
    try {
      const created = await createVoucher(websiteId, form)
      setVouchers((prev) => [created, ...prev])
      setForm(null)
      setFormError('')
    } catch (err) {
      setFormError(errorText(err, 'Gagal menyimpan baucar.'))
    } finally {
      setSaving(false)
    }
  }

  const toggle = async (voucher: Voucher) => {
    setBusyId(voucher.id)
    try {
      const updated = await setVoucherActive(voucher.id, !voucher.is_active)
      setVouchers((prev) => prev.map((v) => (v.id === updated.id ? updated : v)))
      setError('')
    } catch (err) {
      setError(errorText(err, 'Gagal mengemas kini baucar.'))
    } finally {
      setBusyId(null)
    }
  }

  const remove = async (voucher: Voucher) => {
    setBusyId(voucher.id)
    try {
      await deleteVoucher(voucher.id)
      setVouchers((prev) => prev.filter((v) => v.id !== voucher.id))
      setError('')
    } catch (err) {
      setError(errorText(err, 'Gagal memadam baucar.'))
    } finally {
      setBusyId(null)
      setConfirmDeleteId(null)
    }
  }

  const copy = async (voucher: Voucher) => {
    try {
      await navigator.clipboard.writeText(voucher.code)
      setCopiedId(voucher.id)
      setTimeout(() => setCopiedId((id) => (id === voucher.id ? null : id)), 1800)
    } catch {
      window.prompt('Salin kod baucar:', voucher.code)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13px] text-white/50 max-w-xl">
          Pelanggan masukkan kod di troli semasa membuat pesanan. Diskaun ditolak daripada harga
          makanan sahaja — yuran penghantaran tidak berubah.
        </p>
        {!form && (
          <Button variant="primary" onClick={() => setForm({ ...EMPTY_VOUCHER_FORM })}>
            + Baucar baharu
          </Button>
        )}
      </div>

      {error && <Notice tone="error">{error}</Notice>}

      {form && (
        <form
          className="dash-surface p-5 space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            void submit()
          }}
        >
          <h2 className="text-sm font-semibold text-white">Baucar baharu</h2>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Kod" hint="3–20 huruf atau nombor. Kod tidak boleh diubah selepas disimpan.">
              <TextInput
                value={form.code}
                onChange={(e) => set('code', normalizeVoucherCode(e.target.value))}
                placeholder="cth: RAYA15"
                maxLength={20}
                autoCapitalize="characters"
                autoCorrect="off"
                spellCheck={false}
                className="font-mono tracking-wider"
              />
            </Field>
            <Field label="Catatan (pilihan)" hint="Untuk rujukan anda sahaja.">
              <TextInput
                value={form.description}
                onChange={(e) => set('description', e.target.value)}
                placeholder="cth: Promosi Hari Raya"
                maxLength={200}
              />
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Jenis diskaun">
              <select
                value={form.discount_type}
                onChange={(e) => set('discount_type', e.target.value === 'fixed' ? 'fixed' : 'percent')}
                className={inputClass}
              >
                <option value="percent" className="bg-[#161623]">Peratus (%)</option>
                <option value="fixed" className="bg-[#161623]">Jumlah tetap (RM)</option>
              </select>
            </Field>
            <Field label={form.discount_type === 'percent' ? 'Diskaun (%)' : 'Diskaun (RM)'}>
              <TextInput
                value={form.discount_value}
                onChange={(e) => set('discount_value', e.target.value)}
                inputMode="decimal"
                placeholder={form.discount_type === 'percent' ? '10' : '5.00'}
              />
            </Field>
            {form.discount_type === 'percent' ? (
              <Field label="Had maksimum (RM, pilihan)" hint="cth: 10% tetapi tidak lebih RM5.">
                <TextInput
                  value={form.max_discount}
                  onChange={(e) => set('max_discount', e.target.value)}
                  inputMode="decimal"
                  placeholder="Tiada had"
                />
              </Field>
            ) : (
              <div className="hidden sm:block" />
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Pesanan minimum (RM, pilihan)">
              <TextInput
                value={form.min_order}
                onChange={(e) => set('min_order', e.target.value)}
                inputMode="decimal"
                placeholder="Tiada minimum"
              />
            </Field>
            <Field label="Tarikh tamat (pilihan)" hint="Sah sehingga hujung hari ini.">
              <TextInput
                type="date"
                value={form.expires_on}
                onChange={(e) => set('expires_on', e.target.value)}
              />
            </Field>
            <Field label="Had penggunaan (pilihan)" hint="Jumlah tebusan untuk semua pelanggan.">
              <TextInput
                value={form.usage_limit}
                onChange={(e) => set('usage_limit', e.target.value)}
                inputMode="numeric"
                placeholder="Tiada had"
              />
            </Field>
          </div>

          <label className="flex items-center gap-2.5 text-[13px] text-white/75 cursor-pointer w-fit">
            <input
              type="checkbox"
              checked={form.once_per_customer}
              onChange={(e) => set('once_per_customer', e.target.checked)}
              className="h-4 w-4 accent-[#C7FF3D]"
            />
            Sekali sahaja bagi setiap pelanggan (ikut nombor telefon)
          </label>

          {formError && <Notice tone="error">{formError}</Notice>}

          <div className="flex gap-2">
            <Button variant="primary" type="submit" disabled={saving}>
              {saving ? 'Menyimpan…' : 'Simpan baucar'}
            </Button>
            <Button
              disabled={saving}
              onClick={() => {
                setForm(null)
                setFormError('')
              }}
            >
              Batal
            </Button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
        </div>
      ) : vouchers.length === 0 ? (
        !form && (
          <div className="dash-surface p-10 text-center">
            <p className="text-white font-medium">Belum ada baucar</p>
            <p className="text-[13px] text-white/40 mt-1">
              Cipta kod pertama anda dan kongsi di WhatsApp atau media sosial.
            </p>
          </div>
        )
      ) : (
        <ul className="space-y-2">
          {vouchers.map((v) => {
            const state = voucherState(v)
            const busy = busyId === v.id
            return (
              <li key={v.id} className="dash-surface p-4 flex flex-wrap items-center gap-x-4 gap-y-3">
                <div className="min-w-0 flex-1 basis-56">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-semibold tracking-wider text-white">{v.code}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${STATE_TONE[state]}`}>
                      {VOUCHER_STATE_LABEL[state]}
                    </span>
                  </div>
                  <p className="text-[13px] text-white/75 mt-1">{v.summary}</p>
                  <p className="text-[11px] text-white/40 mt-0.5">
                    {usageText(v)} · {formatExpiry(v.expires_at)}
                    {v.per_customer_limit === 1 ? ' · sekali setiap pelanggan' : ''}
                    {v.description ? ` · ${v.description}` : ''}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {confirmDeleteId === v.id ? (
                    <>
                      <span className="text-xs text-white/60">Padam {v.code}?</span>
                      <Button variant="danger" disabled={busy} onClick={() => remove(v)}>
                        {busy ? 'Memadam…' : 'Ya, padam'}
                      </Button>
                      <Button disabled={busy} onClick={() => setConfirmDeleteId(null)}>
                        Tidak
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button onClick={() => copy(v)}>{copiedId === v.id ? 'Disalin ✓' : 'Salin kod'}</Button>
                      <Button disabled={busy} onClick={() => toggle(v)}>
                        {busy ? '…' : v.is_active ? 'Jeda' : 'Aktifkan'}
                      </Button>
                      <Button variant="danger" disabled={busy} onClick={() => setConfirmDeleteId(v.id)}>
                        Padam
                      </Button>
                    </>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
