'use client'

import { Textarea } from '../primitives'
import { cn } from '@/lib/utils'

const MAX_LENGTH = 500
const MIN_LENGTH = 10

interface DescriptionInputProps {
  value: string
  onChange: (next: string) => void
}

/**
 * Required free-text description with min-10 / max-500 char counter.
 * Matches the design's "Ceritakan apa yang berlaku" block including
 * the inline error/info hint that flips red below 10 chars.
 */
export function DescriptionInput({ value, onChange }: DescriptionInputProps) {
  const trimmedLength = value.trim().length
  const tooShort = trimmedLength > 0 && trimmedLength < MIN_LENGTH

  return (
    <div className="dp-sec">
      <h3>
        Ceritakan apa yang berlaku<span className="req">*</span>
      </h3>
      <Textarea
        rows={4}
        placeholder="cth: Saya pesan nasi kandar tapi yang sampai nasi briyani. Sayur pun lain dari yang saya pilih…"
        value={value}
        onChange={(e) => {
          // Hard-cap at MAX_LENGTH so we don't have to re-validate on submit.
          const next = e.target.value.slice(0, MAX_LENGTH)
          onChange(next)
        }}
        aria-label="Penerangan masalah"
      />
      <div className={cn('desc-counter', tooShort && 'short')}>
        <span>
          {trimmedLength < MIN_LENGTH
            ? `Minimum ${MIN_LENGTH} aksara (${trimmedLength})`
            : 'Cukup terperinci'}
        </span>
        <span>{value.length} / {MAX_LENGTH}</span>
      </div>
    </div>
  )
}

export const DESCRIPTION_MIN_LENGTH = MIN_LENGTH
