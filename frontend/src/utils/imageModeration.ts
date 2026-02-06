/**
 * Image Moderation Utility for BinaApp
 *
 * Checks images before upload using the moderation API.
 * Does NOT modify any existing UI - just provides helper functions
 * that are called before uploads proceed.
 */

const MODERATION_API_URL =
  'https://binaapp-backend.onrender.com/api/v1/moderation/check-image'

export interface ModerationResult {
  allowed: boolean
  message: string
}

/**
 * Check if an image file is safe to upload.
 * @param file - The image file to check
 * @returns Whether the image is allowed and a message
 */
export async function checkImageSafety(file: File): Promise<ModerationResult> {
  try {
    // Skip non-image files
    if (!file.type.startsWith('image/')) {
      return { allowed: true, message: 'Not an image, skipping moderation' }
    }

    // Skip very small files (likely icons/thumbnails)
    if (file.size < 1000) {
      return { allowed: true, message: 'Small file, skipping moderation' }
    }

    console.log('[BinaApp Moderation] Checking image:', file.name)

    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(MODERATION_API_URL, {
      method: 'POST',
      body: formData,
    })

    const data = await response.json()

    if (response.ok && (data.allowed || data.success)) {
      console.log('[BinaApp Moderation] Image approved')
      return { allowed: true, message: data.message || 'Gambar diluluskan' }
    } else {
      console.log(
        '[BinaApp Moderation] Image rejected:',
        data.detail || data.message
      )
      return {
        allowed: false,
        message:
          data.detail ||
          data.message ||
          'Gambar ditolak: Kandungan tidak sesuai',
      }
    }
  } catch (error) {
    console.error('[BinaApp Moderation] Error:', error)
    // Fail open - allow upload if moderation service is down
    return { allowed: true, message: 'Moderation check failed, allowing upload' }
  }
}

/**
 * Check multiple files sequentially. Stops at the first rejected file.
 * @param files - Array of files to check
 * @returns Whether all files are safe plus per-file results
 */
export async function checkMultipleImages(
  files: File[]
): Promise<{ allSafe: boolean; results: (ModerationResult & { fileName: string })[]; failedFile?: string }> {
  const results: (ModerationResult & { fileName: string })[] = []

  for (const file of files) {
    const result = await checkImageSafety(file)
    results.push({ fileName: file.name, ...result })

    if (!result.allowed) {
      return { allSafe: false, results, failedFile: file.name }
    }
  }

  return { allSafe: true, results }
}
