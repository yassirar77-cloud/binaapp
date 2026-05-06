'use client'

import { AlertCircle, Send } from 'lucide-react'
import { Button } from '../primitives'

interface SubmitButtonProps {
  disabled: boolean
  loading: boolean
  uploading: boolean
  error: string | null
  onSubmit: () => void
}

/**
 * Sticky bottom button. Three states:
 *   - uploading photos in flight → "Menunggu gambar siap…"
 *   - submission in flight       → spinner + "Menghantar aduan…"
 *   - idle                       → "Hantar aduan" + send icon
 *
 * Inline error appears above the button when the create-dispute call
 * fails. Form data is preserved on error so the customer can retry.
 */
export function SubmitButton({
  disabled,
  loading,
  uploading,
  error,
  onSubmit,
}: SubmitButtonProps) {
  return (
    <div className="submit-bar">
      {error && (
        <div className="submit-error" role="alert">
          <AlertCircle size={14} strokeWidth={2} aria-hidden="true" style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{error}</span>
        </div>
      )}
      <Button
        loading={loading || uploading}
        disabled={disabled || loading}
        onClick={onSubmit}
      >
        {uploading
          ? 'Menunggu gambar siap…'
          : loading
            ? 'Menghantar aduan…'
            : (
              <>
                Hantar aduan
                <Send size={16} strokeWidth={2} aria-hidden="true" />
              </>
            )}
      </Button>
    </div>
  )
}
