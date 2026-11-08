/**
 * Create-page guards (quality system, stage 4): the merchant mistakes the
 * product must prevent before credit is spent.
 *
 * Pure helpers so each rule has a unit test; the page wires them in.
 */

/** "Nasi Lemak 5.50", "Set A – RM12.50", "Teh O | 2.00", "Roti: 1.50" */
const PRICED_LINE = /(?:[-–—|:]\s*)?(?:RM\s*)?\d{1,5}(?:[.,]\d{1,2})?\s*$/i

/**
 * A paste into the business-name box that is really a menu: several lines,
 * most of them priced (or a long list). The name box keeps nothing of it;
 * the bulk parser gets all of it.
 */
export function looksLikeMenuPaste(text: string): boolean {
  const lines = String(text ?? '').split(/\r?\n/).map(l => l.trim()).filter(Boolean)
  if (lines.length < 2) return false
  const priced = lines.filter(l => PRICED_LINE.test(l) || l.includes('|')).length
  if (priced >= 2) return true
  return lines.length >= 4
}

/** The first line of a paste, for the name box when it is not a menu. */
export function firstLineOf(text: string): string {
  return String(text ?? '').split(/\r?\n/).map(l => l.trim()).find(Boolean) ?? ''
}

/**
 * A subdomain suggested from the business name: lower-case words joined
 * with hyphens, 3–30 characters, no leading/trailing hyphen. "Restoran" /
 * "Kedai" style prefixes are kept — the merchant can shorten it; the point
 * is that the slug is never a typo of the name.
 */
export function suggestSubdomain(businessName: string): string {
  const words = String(businessName ?? '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9\s-]/g, ' ')
    .split(/[\s-]+/)
    .filter(Boolean)
  let slug = words.join('-')
  if (slug.length > 30) {
    slug = slug.slice(0, 30)
    const cut = slug.lastIndexOf('-')
    if (cut >= 3) slug = slug.slice(0, cut)
  }
  slug = slug.replace(/^-+|-+$/g, '')
  return slug.length >= 3 ? slug : ''
}

export type ImageRole = { poster: boolean; portrait: boolean; text_heavy: boolean; width?: number; height?: number }

/** Portrait ratio from which an upload counts as a poster (matches the backend). */
export const POSTER_RATIO = 1.2

/** Client-side poster guess from the image's own pixels (no network). */
export function portraitPoster(width: number, height: number): boolean {
  return width > 0 && height >= width * POSTER_RATIO
}

/** The warning under a hero upload that looks like a poster or menu board. */
export function posterWarning(role: ImageRole): string | null {
  if (!role.poster) return null
  if (role.text_heavy) {
    return 'Gambar ini nampak macam papan menu atau poster (banyak tulisan). Sebagai gambar hero ia akan dipotong dan tulisannya tak boleh dibaca. Guna gambar makanan/kedai yang melintang untuk hero, dan letak papan menu di langkah 06 supaya item boleh dibaca.'
  }
  return 'Gambar ini menegak (portrait). Hero akan memotongnya di atas dan bawah pada telefon dan komputer. Gambar melintang (landscape) paling sesuai untuk hero; papan menu atau poster letak di langkah 06.'
}

/**
 * Why Generate is blocked: a restaurant/bakery with no named menu item.
 * Returns the message, or null when generation may proceed.
 */
export function generateBlockedReason(namedItems: number, businessType: string, description: string): string | null {
  if (namedItems > 0) return null
  const foodish = businessType === 'food' || businessType === 'bakery'
    || (businessType === 'auto' && /\b(menu|restoran|restaurant|kafe|cafe|warung|kedai makan|gerai|nasi|ayam|mee|roti|kuih|bakeri|bakery|makan|minuman)\b/i.test(description))
  if (!foodish) return null
  return 'Restoran perlu sekurang-kurangnya satu item menu sebelum dijana — tanpa menu, laman akan dicipta tanpa senarai makanan dan harga anda. Tambah item di langkah 06, tampal senarai menu, atau muat naik papan menu dan tekan "Baca menu dari gambar".'
}

export type GatePreview = {
  url: string | null
  passed: boolean | null
  summary: string | null
  failedChecks: string[]
  fixes: string[]
}

/** The preview-before-publish block, from the job status response. */
export function gatePreviewFromStatus(status: any): GatePreview | null {
  if (!status || typeof status !== 'object') return null
  const vg = status.visual_gate
  const url: string | null = status.preview_mobile_url || vg?.preview_mobile_url || null
  if (!vg && !url) return null
  return {
    url,
    passed: typeof vg?.passed === 'boolean' ? vg.passed : null,
    summary: vg?.summary ?? null,
    failedChecks: Array.isArray(vg?.failed_checks) ? vg.failed_checks : [],
    fixes: Array.isArray(vg?.fixes) ? vg.fixes : [],
  }
}

export function gatePreviewLine(p: GatePreview | null): string {
  if (!p || p.passed === null) return 'Semakan visual automatik tidak dijalankan untuk laman ini.'
  if (p.passed) return p.fixes.length ? `Semakan visual lulus selepas pembetulan automatik (${p.fixes.join(', ')}).` : 'Semakan visual lulus: tiada elemen bertindih, terpotong atau sukar dibaca pada telefon.'
  return `Semakan visual mendapati masalah: ${p.failedChecks.join(', ') || p.summary}. Semak pratonton sebelum terbit.`
}
