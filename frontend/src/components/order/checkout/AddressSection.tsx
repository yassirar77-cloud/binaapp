'use client'

import { Check, Home, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Customer } from '../types'
import { GeolocationHelper } from './GeolocationHelper'

export type AddressChoice = 'saved' | 'new'

interface AddressSectionProps {
  customer: Customer
  choice: AddressChoice
  onChoiceChange: (choice: AddressChoice) => void
  newAddressText: string
  onNewAddressChange: (text: string) => void
  onGeolocated?: (data: { address: string; latitude: number; longitude: number }) => void
  /** Display number for the section header. */
  step?: number
}

/**
 * Section 2 — pick a saved address or type a new one. Backed by the
 * Customer schema's single `address` field (one saved address per
 * customer per restaurant). For new customers (empty `customer.address`)
 * the section auto-collapses into just the new-address textarea.
 *
 * TODO(geocoding): Consider Google Places autocomplete for better
 *                  address quality once an API key budget is available.
 */
export function AddressSection({
  customer,
  choice,
  onChoiceChange,
  newAddressText,
  onNewAddressChange,
  onGeolocated,
  step = 2,
}: AddressSectionProps) {
  const hasSaved = !!customer.address?.trim()

  const filled =
    (choice === 'saved' && hasSaved) ||
    (choice === 'new' && newAddressText.trim().length >= 8)

  return (
    <div className="co-sec fade-up" style={{ animationDelay: '40ms' }}>
      <div className="co-sec-head">
        <h2>
          <span className={cn('num', filled && 'done')}>{step}</span>
          Alamat penghantaran
        </h2>
      </div>

      {hasSaved && (
        <button
          type="button"
          className={cn('saved-addr', choice === 'saved' && 'active')}
          onClick={() => onChoiceChange('saved')}
        >
          <Home className="ic" size={18} strokeWidth={2} aria-hidden="true" />
          <div className="body">
            <div className="nm">Alamat tersimpan</div>
            <div className="ad">{customer.address}</div>
          </div>
          <div className="check">
            {choice === 'saved' && (
              <Check size={12} strokeWidth={3} aria-hidden="true" />
            )}
          </div>
        </button>
      )}

      <button
        type="button"
        className={cn('saved-addr', choice === 'new' && 'active')}
        onClick={() => onChoiceChange('new')}
        style={{
          borderStyle: hasSaved && choice !== 'new' ? 'dashed' : 'solid',
        }}
      >
        <Plus className="ic" size={18} strokeWidth={2} aria-hidden="true" />
        <div className="body">
          <div className="nm">{hasSaved ? 'Tambah alamat baru' : 'Masukkan alamat'}</div>
        </div>
      </button>

      {choice === 'new' && (
        <div style={{ marginTop: 12 }} className="fade-up">
          <textarea
            className="addr-textarea"
            placeholder="No. unit, jalan, taman, poskod, bandar…"
            value={newAddressText}
            onChange={(e) => onNewAddressChange(e.target.value)}
            aria-label="Alamat penghantaran"
          />
          {onGeolocated && <GeolocationHelper onResolved={onGeolocated} />}
        </div>
      )}
    </div>
  )
}
