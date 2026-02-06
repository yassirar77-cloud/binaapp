/**
 * React Hook for Image Moderation
 *
 * Provides a stateful wrapper around the image moderation utility
 * for use in components that handle image uploads.
 */

import { useState } from 'react'
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
      onRejected ? onRejected(result.message) : alert(result.message)
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
