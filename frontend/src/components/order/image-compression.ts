/**
 * Image compression for the dispute photo uploads.
 *
 * Resizes the image down to a max width via canvas and re-encodes as
 * JPEG so we don't ship 8MB phone-camera originals to Supabase Storage.
 * Falls back to lower quality when the first pass still exceeds the
 * 2MB target.
 */

const MAX_WIDTH_PX = 1280
const FIRST_PASS_QUALITY = 0.8
const SECOND_PASS_QUALITY = 0.6
const SIZE_BUDGET_BYTES = 2 * 1024 * 1024 // 2 MB

export interface CompressedImage {
  blob: Blob
  width: number
  height: number
}

/**
 * Resize-and-encode a user-selected image. Always returns JPEG so the
 * bucket sees a single content type. Throws on decode failure.
 */
export async function compressImage(file: File): Promise<CompressedImage> {
  const bitmap = await loadBitmap(file)
  const scale = Math.min(MAX_WIDTH_PX / bitmap.width, 1)
  const width = Math.round(bitmap.width * scale)
  const height = Math.round(bitmap.height * scale)

  const blob = await renderToBlob(bitmap, width, height, FIRST_PASS_QUALITY)

  // Already small enough — done.
  if (blob.size <= SIZE_BUDGET_BYTES) {
    return { blob, width, height }
  }

  // One retry at lower quality.
  const second = await renderToBlob(bitmap, width, height, SECOND_PASS_QUALITY)
  return { blob: second, width, height }
}

async function loadBitmap(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Tidak dapat membaca fail gambar'))
    }
    img.src = url
  })
}

function renderToBlob(
  img: HTMLImageElement,
  width: number,
  height: number,
  quality: number
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      reject(new Error('Canvas tidak disokong oleh pelayar'))
      return
    }
    ctx.drawImage(img, 0, 0, width, height)
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('Gagal mampatkan gambar'))
      },
      'image/jpeg',
      quality
    )
  })
}
