export const MAX_EVIDENCE_IMAGES = 3
export const PRE_COMPRESSION_WARN_BYTES = 5 * 1024 * 1024
export const POST_COMPRESSION_MAX_BYTES = 2 * 1024 * 1024
const MAX_WIDTH = 1280
const JPEG_QUALITY = 0.8

export interface CompressedImage {
  dataUrl: string
  bytes: number
}

function dataUrlBytes(dataUrl: string): number {
  const comma = dataUrl.indexOf(',')
  const base64 = comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl
  return Math.floor((base64.length * 3) / 4)
}

export async function compressImage(file: File): Promise<CompressedImage> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(new Error('Gagal baca fail'))
    reader.readAsDataURL(file)
  })

  const img = await new Promise<HTMLImageElement>((resolve, reject) => {
    const el = new Image()
    el.onload = () => resolve(el)
    el.onerror = () => reject(new Error('Gagal muat gambar'))
    el.src = dataUrl
  })

  const ratio = img.width > 0 ? img.height / img.width : 1
  const targetWidth = Math.min(MAX_WIDTH, img.width || MAX_WIDTH)
  const targetHeight = Math.max(1, Math.round(targetWidth * ratio))

  const canvas = document.createElement('canvas')
  canvas.width = targetWidth
  canvas.height = targetHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Pelayar tidak menyokong canvas')
  ctx.drawImage(img, 0, 0, targetWidth, targetHeight)

  let quality = JPEG_QUALITY
  let compressed = canvas.toDataURL('image/jpeg', quality)
  let bytes = dataUrlBytes(compressed)
  // Try one more pass at lower quality if still over budget
  if (bytes > POST_COMPRESSION_MAX_BYTES && quality > 0.4) {
    quality = 0.6
    compressed = canvas.toDataURL('image/jpeg', quality)
    bytes = dataUrlBytes(compressed)
  }

  if (bytes > POST_COMPRESSION_MAX_BYTES) {
    throw new Error('Gambar terlalu besar selepas mampatan (>2MB). Cuba gambar lain.')
  }

  return { dataUrl: compressed, bytes }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
