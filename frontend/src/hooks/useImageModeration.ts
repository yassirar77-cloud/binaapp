/**
 * React Hook for Image Moderation
 *
 * Provides a stateful wrapper around the image moderation utility
 * for use in components that handle image uploads.
 */

import { useState } from 'react'
import { alertDialog } from '@/components/ui/popups'
import { checkImageSafety, type ModerationResult } from '@/utils/imageModeration'

export function useImageModeration() {
  const [isChecking, setIsChecking] = useState(false)
  const [moderationResult, setModerationResult] = useState<ModerationResult | null>(null)

  const checkImage = async (file: File): Promise<ModerationResult> => {
    setIsChecking(true)
    try {
      const result = await checkImageSafety(file)
      setModerationResult(result)
      return result
    } finally {
      setIsChecking(false)
    }
  }

  const checkAndProceed = async (
    file: File,
    onApproved?: (file: File) => void,
    onRejected?: (message: string) => void
  ): Promise<ModerationResult> => {
    const result = await checkImage(file)

    if (result.allowed) {
      onApproved?.(file)
    } else {
      onRejected ? onRejected(result.message) : void alertDialog({ title: 'Imej ditolak', message: result.message, variant: 'warning' })
    }

    return result
  }

  return {
    checkImage,
    checkAndProceed,
    isChecking,
    moderationResult,
  }
}
