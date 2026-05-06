'use client'

import { Phone, User } from 'lucide-react'
import { useState } from 'react'
import { Input } from '../primitives'
import { fromStorageFormat, formatPhoneDisplay, toStorageFormat } from '../phone'
import type { Customer } from '../types'

interface CustomerInfoSectionProps {
  customer: Customer
  onUpdate: (patch: Partial<Customer>) => void
}

/**
 * Section 1 — read-only display of phone + name with an Edit toggle.
 * Phone is the customer's identity (set during PR 2 / identify) — the
 * input shown when editing strips the leading 0 because the +60 prefix
 * is implied by the display formatter.
 */
export function CustomerInfoSection({ customer, onUpdate }: CustomerInfoSectionProps) {
  const [editing, setEditing] = useState(!customer.name?.trim())
  const [draftName, setDraftName] = useState(customer.name || '')
  const [draftPhone, setDraftPhone] = useState(fromStorageFormat(customer.phone))

  const save = () => {
    const next: Partial<Customer> = {}
    const trimmedName = draftName.trim()
    if (trimmedName !== customer.name) next.name = trimmedName
    const nextPhone = toStorageFormat(draftPhone)
    if (nextPhone !== customer.phone) next.phone = nextPhone
    if (Object.keys(next).length > 0) onUpdate(next)
    setEditing(false)
  }

  const phoneDone = customer.name?.trim() && customer.phone?.length >= 9

  return (
    <div className="co-sec fade-up">
      <div className="co-sec-head">
        <h2>
          <span className={`num${phoneDone ? ' done' : ''}`}>1</span>
          Maklumat pelanggan
        </h2>
        {editing ? (
          <button type="button" className="edit" onClick={save}>
            Simpan
          </button>
        ) : (
          <button type="button" className="edit" onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
      </div>

      <div className="info-row">
        <div className="ic">
          <Phone size={16} aria-hidden="true" />
        </div>
        <div style={{ flex: 1 }}>
          <div className="lbl">Nombor telefon</div>
          {editing ? (
            <Input
              style={{ height: 36, marginTop: 4 }}
              value={formatPhoneDisplay(draftPhone)}
              onChange={(e) => setDraftPhone(e.target.value)}
              type="tel"
              inputMode="numeric"
              aria-label="Nombor telefon"
            />
          ) : (
            <div className="val">+60 {formatPhoneDisplay(fromStorageFormat(customer.phone))}</div>
          )}
        </div>
      </div>

      <div className="info-row">
        <div className="ic">
          <User size={16} aria-hidden="true" />
        </div>
        <div style={{ flex: 1 }}>
          <div className="lbl">Nama</div>
          {editing ? (
            <Input
              style={{ height: 36, marginTop: 4 }}
              value={draftName}
              onChange={(e) => setDraftName(e.target.value)}
              placeholder="Nama anda"
              aria-label="Nama"
            />
          ) : (
            <div className="val">{customer.name || '—'}</div>
          )}
        </div>
      </div>
    </div>
  )
}
