'use client'

import { useEffect, useState } from 'react'
import { Avatar } from './primitives/Avatar'
import { Card } from './primitives/Card'
import { Divider } from './primitives/Divider'
import { Field } from './primitives/Field'
import { Pill } from './primitives/Pill'
import { PrimaryButton } from './primitives/PrimaryButton'

const BM_MONTHS = [
  'Januari', 'Februari', 'Mac', 'April', 'Mei', 'Jun',
  'Julai', 'Ogos', 'September', 'Oktober', 'November', 'Disember',
]

function formatMemberSince(createdAt?: string | null): string {
  if (!createdAt) return 'Ahli BinaApp'
  const d = new Date(createdAt)
  if (Number.isNaN(d.getTime())) return 'Ahli BinaApp'
  return `ahli sejak ${BM_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

function getInitials(name: string, email: string): string {
  const n = name.trim()
  if (n) {
    const parts = n.split(/\s+/)
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
    return parts[0].slice(0, 2).toUpperCase()
  }
  const local = email.split('@')[0] || ''
  return local.slice(0, 2).toUpperCase() || 'YA'
}

export interface ProfileCardData {
  fullName: string
  businessName: string
  phone: string
}

interface ProfileCardProps {
  email: string
  createdAt?: string | null
  planLabel?: string
  initial: ProfileCardData
  loading?: boolean
  onSave: (next: ProfileCardData) => Promise<void>
  onSuccess: (msg: string) => void
  onError: (msg: string) => void
}

export function ProfileCard({
  email,
  createdAt,
  planLabel = 'PRO',
  initial,
  loading = false,
  onSave,
  onSuccess,
  onError,
}: ProfileCardProps) {
  const [fullName, setFullName] = useState(initial.fullName)
  const [businessName, setBusinessName] = useState(initial.businessName)
  const [phone, setPhone] = useState(initial.phone)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setFullName(initial.fullName)
    setBusinessName(initial.businessName)
    setPhone(initial.phone)
    setDirty(false)
  }, [initial.fullName, initial.businessName, initial.phone])

  const initials = getInitials(fullName || initial.fullName, email)
  const memberSince = formatMemberSince(createdAt)
  const subtitleBiz = (businessName || initial.businessName || '').trim()

  const handleSave = async () => {
    if (!dirty || saving) return
    setSaving(true)
    try {
      await onSave({ fullName, businessName, phone })
      setDirty(false)
      onSuccess('Perubahan disimpan')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Gagal simpan perubahan'
      onError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Avatar initials={initials} tone="purple" size={56} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: 15,
                fontWeight: 500,
                color: 'var(--ink-1)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                minWidth: 0,
              }}
            >
              {email}
            </span>
            <Pill tone="purple">{planLabel}</Pill>
          </div>
          <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 2 }}>
            {subtitleBiz ? `${subtitleBiz} · ${memberSince}` : memberSince}
          </div>
        </div>
      </div>

      <Divider style={{ margin: '20px 0' }} />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16,
        }}
      >
        <Field
          label="Nama penuh"
          value={fullName}
          onChange={(v) => { setFullName(v); setDirty(true) }}
          placeholder="Masukkan nama penuh"
          disabled={loading}
          autoComplete="name"
        />
        <Field
          label="Nombor telefon"
          value={phone}
          onChange={(v) => { setPhone(v); setDirty(true) }}
          type="tel"
          placeholder="012-345 6789"
          disabled={loading}
          autoComplete="tel"
        />
        <Field
          label="Nama perniagaan"
          value={businessName}
          onChange={(v) => { setBusinessName(v); setDirty(true) }}
          placeholder="Masukkan nama perniagaan"
          full
          disabled={loading}
          autoComplete="organization"
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
        <PrimaryButton onClick={handleSave} disabled={!dirty || saving || loading}>
          {saving ? 'Menyimpan…' : 'Simpan perubahan'}
        </PrimaryButton>
      </div>
    </Card>
  )
}
