'use client'

import { useState } from 'react'
import { Field } from '@/app/profile/components/primitives/Field'
import { GhostButton } from '@/app/profile/components/primitives/GhostButton'
import { PrimaryButton } from '@/app/profile/components/primitives/PrimaryButton'
import {
  RiderApiError,
  isValidUUID,
  useRiderMutations,
  type RiderPayload,
  type VehicleType,
} from './useRiderMutations'

export interface RiderFormWebsite {
  id: string
  name?: string | null
  business_name?: string | null
  subdomain?: string | null
}

export interface RiderFormRider {
  id: string
  name: string | null
  phone: string | null
  email?: string | null
  vehicle_type?: VehicleType | null
  vehicle_plate: string | null
  vehicle_model?: string | null
  is_active?: boolean | null
}

type Mode = 'add' | 'edit'

interface RiderFormProps {
  mode: Mode
  rider?: RiderFormRider
  websites: RiderFormWebsite[]
  selectedWebsiteId: string | null
  onWebsiteChange: (id: string) => void
  onSuccess: (msg: string) => void
  onError: (msg: string) => void
  onCancel: () => void
  onDeleted?: () => void
}

const VEHICLE_OPTIONS: ReadonlyArray<{ value: VehicleType; label: string }> = [
  { value: 'motorcycle', label: 'Motosikal' },
  { value: 'car', label: 'Kereta' },
  { value: 'bicycle', label: 'Basikal' },
  { value: 'scooter', label: 'Skuter' },
]

interface FormState {
  name: string
  phone: string
  email: string
  password: string
  vehicle_type: VehicleType
  vehicle_plate: string
  vehicle_model: string
  is_active: boolean
}

function initialState(rider?: RiderFormRider): FormState {
  return {
    name: rider?.name ?? '',
    phone: rider?.phone ?? '',
    email: rider?.email ?? '',
    password: '',
    vehicle_type: (rider?.vehicle_type as VehicleType | null | undefined) ?? 'motorcycle',
    vehicle_plate: rider?.vehicle_plate ?? '',
    vehicle_model: rider?.vehicle_model ?? '',
    is_active: rider?.is_active !== false,
  }
}

function websiteLabel(w: RiderFormWebsite): string {
  const base = (w.name || w.business_name || w.subdomain || 'Website tanpa nama').trim()
  if (w.subdomain && base !== w.subdomain) return `${base} (${w.subdomain}.binaapp.my)`
  return base
}

export function RiderForm({
  mode,
  rider,
  websites,
  selectedWebsiteId,
  onWebsiteChange,
  onSuccess,
  onError,
  onCancel,
  onDeleted,
}: RiderFormProps) {
  const [form, setForm] = useState<FormState>(() => initialState(rider))
  const [error, setError] = useState<string | null>(null)
  const { createRider, updateRider, deleteRider, submitting, deleting } = useRiderMutations()

  const isEdit = mode === 'edit'
  const showWebsiteSelector = !isEdit && websites.length > 1

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function buildPayload(): RiderPayload {
    return {
      name: form.name.trim(),
      phone: form.phone.trim(),
      email: form.email.trim() || undefined,
      password: form.password || undefined,
      vehicle_type: form.vehicle_type,
      vehicle_plate: form.vehicle_plate.trim() || undefined,
      vehicle_model: form.vehicle_model.trim() || undefined,
      is_active: form.is_active,
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!form.name.trim() || !form.phone.trim()) {
      setError('Nama dan nombor telefon diperlukan')
      return
    }
    if (!isEdit && !form.password) {
      setError('Kata laluan diperlukan untuk rider baru')
      return
    }
    if (!isEdit && !isValidUUID(selectedWebsiteId)) {
      setError('Sila pilih website terlebih dahulu')
      return
    }

    try {
      if (isEdit && rider) {
        await updateRider(rider.id, buildPayload())
        onSuccess('Rider dikemaskini')
      } else {
        await createRider(selectedWebsiteId as string, buildPayload())
        onSuccess('Rider ditambah')
      }
    } catch (err) {
      const msg = err instanceof RiderApiError ? err.message : 'Ralat sistem. Sila cuba lagi.'
      setError(msg)
      onError(msg)
    }
  }

  async function handleDelete() {
    if (!rider) return
    const ok = window.confirm(`Padam rider "${rider.name || 'tanpa nama'}"? Tindakan ini tidak boleh dibatalkan.`)
    if (!ok) return
    try {
      await deleteRider(rider.id)
      onSuccess('Rider dipadam')
      onDeleted?.()
    } catch (err) {
      const msg = err instanceof RiderApiError ? err.message : 'Ralat sistem. Sila cuba lagi.'
      setError(msg)
      onError(msg)
    }
  }

  const busy = submitting || deleting

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {showWebsiteSelector && (
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>Website *</span>
          <select
            value={selectedWebsiteId ?? ''}
            onChange={(e) => onWebsiteChange(e.target.value)}
            required
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
            <option value="">— Pilih website —</option>
            {websites.map((w) => (
              <option key={w.id} value={w.id}>{websiteLabel(w)}</option>
            ))}
          </select>
        </label>
      )}

      {!isEdit && websites.length === 1 && (
        <div
          style={{
            fontSize: 12,
            color: 'var(--ink-3)',
            background: '#f7f7f8',
            padding: '8px 10px',
            borderRadius: 'var(--r-input)',
          }}
        >
          Website: {websiteLabel(websites[0])}
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 12,
        }}
      >
        <Field label="Nama penuh *" value={form.name} onChange={(v) => update('name', v)} placeholder="Ahmad bin Ali" />
        <Field label="No. telefon *" value={form.phone} onChange={(v) => update('phone', v)} type="tel" placeholder="0123456789" />
        <Field label="E-mel" value={form.email} onChange={(v) => update('email', v)} type="email" placeholder="rider@example.com" />
        <Field
          label={isEdit ? 'Kata laluan baru (kosongkan jika tiada)' : 'Kata laluan *'}
          value={form.password}
          onChange={(v) => update('password', v)}
          type="password"
          placeholder={isEdit ? 'Min 6 aksara' : 'Min 6 aksara'}
        />

        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: 12, color: 'var(--ink-2)' }}>Jenis kenderaan</span>
          <select
            value={form.vehicle_type}
            onChange={(e) => update('vehicle_type', e.target.value as VehicleType)}
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
            {VEHICLE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>

        <Field
          label="No. plat"
          value={form.vehicle_plate}
          onChange={(v) => update('vehicle_plate', v.toUpperCase())}
          placeholder="ABC1234"
        />
        <Field
          label="Model kenderaan"
          value={form.vehicle_model}
          onChange={(v) => update('vehicle_model', v)}
          placeholder="Honda Wave 125"
        />
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--ink-2)' }}>
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(e) => update('is_active', e.target.checked)}
          style={{ width: 16, height: 16, accentColor: 'var(--orange)' }}
        />
        Rider boleh terima pesanan
      </label>

      {error && (
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
          {error}
        </div>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          marginTop: 4,
          flexWrap: 'wrap',
        }}
      >
        <div>
          {isEdit && (
            <button
              type="button"
              onClick={handleDelete}
              disabled={busy}
              style={{
                background: 'transparent',
                color: '#dc2626',
                border: '0.5px solid #fecaca',
                fontFamily: 'inherit',
                fontSize: 13,
                fontWeight: 500,
                padding: '7px 12px',
                minHeight: 36,
                borderRadius: 'var(--r-input)',
                cursor: busy ? 'not-allowed' : 'pointer',
                opacity: busy ? 0.6 : 1,
              }}
            >
              {deleting ? 'Memadam…' : 'Padam rider'}
            </button>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <GhostButton onClick={onCancel} type="button">Batal</GhostButton>
          <PrimaryButton type="submit" disabled={busy}>
            {submitting ? 'Menyimpan…' : isEdit ? 'Simpan' : 'Tambah rider'}
          </PrimaryButton>
        </div>
      </div>
    </form>
  )
}
