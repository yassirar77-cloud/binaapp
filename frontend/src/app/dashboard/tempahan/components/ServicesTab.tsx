'use client'

import { useEffect, useState } from 'react'

import {
  createService,
  deleteService,
  fetchServices,
  formatDuration,
  formatPrice,
  updateService,
  type BookingService,
  type ServiceInput,
} from '@/lib/booking'

import { Button, Field, Notice, TextInput, errorText, inputClass } from './ui'

interface Draft {
  id: string | null
  name: string
  description: string
  duration_min: string
  price: string
  active: boolean
}

const EMPTY: Draft = { id: null, name: '', description: '', duration_min: '30', price: '', active: true }

function toInput(draft: Draft, sortOrder: number): ServiceInput | string {
  const name = draft.name.trim()
  if (!name) return 'Nama servis diperlukan'
  const duration = Number(draft.duration_min)
  if (!Number.isInteger(duration) || duration < 5 || duration > 600) {
    return 'Tempoh mesti antara 5 hingga 600 minit'
  }
  let price: number | null = null
  if (draft.price.trim()) {
    price = Number(draft.price)
    if (Number.isNaN(price) || price < 0) return 'Harga tidak sah'
  }
  return {
    name,
    description: draft.description.trim(),
    duration_min: duration,
    price,
    active: draft.active,
    sort_order: sortOrder,
  }
}

export default function ServicesTab({ websiteId }: { websiteId: string }) {
  const [services, setServices] = useState<BookingService[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState<Draft | null>(null)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      setServices(await fetchServices(websiteId))
      setError('')
    } catch (err) {
      setError(errorText(err, 'Gagal memuatkan servis.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [websiteId])

  const save = async () => {
    if (!draft) return
    const existing = services.find((s) => s.id === draft.id)
    const input = toInput(draft, existing?.sort_order ?? services.length)
    if (typeof input === 'string') {
      setError(input)
      return
    }
    setSaving(true)
    setError('')
    try {
      if (draft.id) await updateService(websiteId, draft.id, input)
      else await createService(websiteId, input)
      setDraft(null)
      await load()
    } catch (err) {
      setError(errorText(err, 'Gagal menyimpan servis.'))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (service: BookingService) => {
    if (!window.confirm(`Padam servis "${service.name}"? Tempahan sedia ada tidak terjejas.`)) return
    setError('')
    try {
      await deleteService(websiteId, service.id)
      await load()
    } catch (err) {
      setError(errorText(err, 'Gagal memadam servis.'))
    }
  }

  const toggle = async (service: BookingService) => {
    setError('')
    try {
      await updateService(websiteId, service.id, {
        name: service.name,
        description: service.description,
        duration_min: service.duration_min,
        price: service.price,
        active: !service.active,
        sort_order: service.sort_order ?? 0,
      })
      await load()
    } catch (err) {
      setError(errorText(err, 'Gagal mengemas kini servis.'))
    }
  }

  return (
    <div className="space-y-4">
      {error && <Notice tone="error">{error}</Notice>}

      {draft ? (
        <div className="dash-surface p-5 space-y-4">
          <h2 className="text-sm font-semibold text-white">{draft.id ? 'Edit servis' : 'Servis baru'}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Nama servis">
              <TextInput
                value={draft.name}
                maxLength={120}
                placeholder="cth. Potong Rambut"
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tempoh (minit)">
                <TextInput
                  type="number"
                  min={5}
                  max={600}
                  step={5}
                  value={draft.duration_min}
                  onChange={(e) => setDraft({ ...draft, duration_min: e.target.value })}
                />
              </Field>
              <Field label="Harga (RM)" hint="Kosongkan jika tidak mahu papar">
                <TextInput
                  type="number"
                  min={0}
                  step="0.01"
                  inputMode="decimal"
                  value={draft.price}
                  onChange={(e) => setDraft({ ...draft, price: e.target.value })}
                />
              </Field>
            </div>
          </div>
          <Field label="Penerangan (pilihan)">
            <textarea
              rows={2}
              maxLength={500}
              value={draft.description}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              className={inputClass}
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-white/70">
            <input
              type="checkbox"
              checked={draft.active}
              onChange={(e) => setDraft({ ...draft, active: e.target.checked })}
              className="accent-[#C7FF3D]"
            />
            Boleh ditempah oleh pelanggan
          </label>
          <div className="flex gap-2">
            <Button variant="primary" onClick={save} disabled={saving}>
              {saving ? 'Menyimpan…' : 'Simpan'}
            </Button>
            <Button onClick={() => { setDraft(null); setError('') }} disabled={saving}>
              Batal
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="primary" onClick={() => setDraft(EMPTY)}>
          + Tambah servis
        </Button>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
        </div>
      ) : services.length === 0 ? (
        <div className="dash-surface p-10 text-center">
          <p className="text-white font-medium">Belum ada servis</p>
          <p className="text-[13px] text-white/40 mt-1">
            Tambah sekurang-kurangnya satu servis sebelum membuka tempahan.
          </p>
        </div>
      ) : (
        <ul className="dash-surface divide-y divide-white/[0.06]">
          {services.map((s) => (
            <li key={s.id} className="p-4 flex flex-wrap items-center gap-3">
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-medium ${s.active ? 'text-white' : 'text-white/40'}`}>
                  {s.name}
                  {!s.active && <span className="ml-2 text-[11px] font-normal">(disembunyikan)</span>}
                </p>
                <p className="text-[12px] text-white/50">
                  {formatDuration(s.duration_min)}
                  {s.price !== null ? ` · ${formatPrice(s.price)}` : ''}
                </p>
                {s.description && <p className="text-[12px] text-white/40 mt-0.5">{s.description}</p>}
              </div>
              <Button onClick={() => toggle(s)}>{s.active ? 'Sembunyi' : 'Aktifkan'}</Button>
              <Button
                onClick={() =>
                  setDraft({
                    id: s.id,
                    name: s.name,
                    description: s.description,
                    duration_min: String(s.duration_min),
                    price: s.price === null ? '' : String(s.price),
                    active: s.active ?? true,
                  })
                }
              >
                Edit
              </Button>
              <Button variant="danger" onClick={() => remove(s)}>
                Padam
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
