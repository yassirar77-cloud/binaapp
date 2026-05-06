'use client'

import { forwardRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { cn } from '@/lib/utils'
import { digitsOnly, formatPhoneDisplay } from '../phone'

export interface PhoneInputProps {
  /** The digits the user has typed (no leading 0, no formatting). */
  value: string
  /** Receives the cleaned digits-only string (max 9, leading 0 not included). */
  onChange: (digits: string) => void
  /** Disables the input (e.g. while submitting). */
  disabled?: boolean
  className?: string
  autoFocus?: boolean
}

/**
 * Phone-number input with a locked `+60` prefix on the left and live
 * formatting (`12-345 6789`) on the right. Maxes out at 9 digits — the
 * leading `0` is implicit (added at storage time by `toStorageFormat`).
 *
 * Visually mirrors the `.phone-input-wrap` block from the design's
 * phone-identification.html.
 */
export const PhoneInput = forwardRef<HTMLInputElement, PhoneInputProps>(
  function PhoneInput({ value, onChange, disabled, className, autoFocus }, ref) {
    const [focused, setFocused] = useState(false)

    const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
      // Always normalize via digitsOnly + cap at 9 — this protects
      // against pasted formatted numbers, country codes, etc.
      const cleaned = digitsOnly(e.target.value).slice(0, 9)
      onChange(cleaned)
    }

    return (
      <div className={cn('phone-input-wrap', focused && 'focused', className)}>
        <div className="phone-prefix">
          <div className="flag" aria-hidden="true" />
          <span>+60</span>
        </div>
        <input
          ref={ref}
          className="phone-input"
          type="tel"
          inputMode="numeric"
          autoComplete="tel"
          autoFocus={autoFocus}
          placeholder="12-345 6789"
          value={formatPhoneDisplay(value)}
          onChange={handleChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          aria-label="Nombor telefon"
        />
      </div>
    )
  }
)
