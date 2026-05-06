'use client'

import { MapPin } from 'lucide-react'
import { nameInitials } from '../phone'

export interface ReturningCustomerCardProps {
  name: string
  /** Saved delivery address. May be empty for customers who only have an order history but no saved address. */
  address: string
}

/**
 * "Selamat kembali" card — shown when a phone number matches an
 * existing `website_customers` row. Mirrors `.returning-card` from
 * the design.
 */
export function ReturningCustomerCard({ name, address }: ReturningCustomerCardProps) {
  return (
    <div className="returning-card fade-up" role="region" aria-label="Pelanggan kembali">
      <div className="returning-avatar" aria-hidden="true">
        {nameInitials(name) || '·'}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="lbl">Selamat kembali</div>
        <h3 className="name">{name || 'Pelanggan'}</h3>
        {address && (
          <div className="addr">
            <MapPin className="addr-icon" size={14} aria-hidden="true" />
            <span>{address}</span>
          </div>
        )}
      </div>
    </div>
  )
}
