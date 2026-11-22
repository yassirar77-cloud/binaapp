/**
 * Mascot Video client — a merchant's own clip with a cartoon mascot added.
 *
 * Backend: `api/v1/endpoints/mascot_videos.py`. Rendering is asynchronous:
 * `createMascotVideo` returns a job at once and the page polls
 * `fetchMascotVideo` until it is `ready`, `rejected` or `failed`.
 *
 * Flag-gated server-side (MASCOT_VIDEO_ENABLED). With the flag off every
 * route 404s; `fetchMascotVideoConfig` turns that into `null` so the page can
 * say the feature is not available.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

const BASE = `${API_BASE}/api/v1/mascot-videos`

export type MascotVideoStatus =
  | 'queued'
  | 'moderating'
  | 'processing'
  | 'ready'
  | 'rejected'
  | 'failed'

export interface MascotVideoJob {
  id: string
  status: MascotVideoStatus
  prompt: string
  clip_url: string | null
  mascot_url: string | null
  result_url: string | null
  clip_seconds: number
  error: string | null
  ai_generated: boolean
  created_at: string
  finished_at: string | null
}

export interface MascotVideoDaily {
  /** Renders that count against the cap (a render with no mascot does not). */
  used: number
  limit: number
  remaining: number
  /** Everything that reached the video model today, counted or not. */
  attempts?: number
  attempt_limit?: number
}

export interface MascotVideoConfig {
  enabled: boolean
  /** False when the video provider is not configured on the server. */
  available: boolean
  min_clip_seconds: number
  max_clip_seconds: number
  max_clip_mb: number
  max_mascot_mb: number
  prompt_max: number
  mascot_description_max: number
  poll_interval_seconds: number
  daily: MascotVideoDaily
}

export interface MascotPreset {
  key: string
  label: string
  src: string
}

/** Ready-made mascots, served from /public/mascots. */
export const MASCOT_PRESETS: readonly MascotPreset[] = [
  { key: 'pakcik-teh-tarik', label: 'Pakcik Teh Tarik', src: '/mascots/pakcik-teh-tarik.png' },
  { key: 'ayam-ceria', label: 'Ayam Ceria', src: '/mascots/ayam-ceria.png' },
]

export const ACTIVE_STATUSES: readonly MascotVideoStatus[] = ['queued', 'moderating', 'processing']

export function isActive(status: MascotVideoStatus): boolean {
  return ACTIVE_STATUSES.includes(status)
}

export const STATUS_LABEL: Record<MascotVideoStatus, string> = {
  queued: 'Dalam giliran',
  moderating: 'Menyemak kandungan klip',
  processing: 'Menjana video (3–5 minit)',
  ready: 'Siap',
  rejected: 'Ditolak',
  failed: 'Gagal',
}

export class MascotVideoError extends Error {
  code: string
  status: number
  constructor(message: string, code: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

async function toError(res: Response): Promise<MascotVideoError> {
  let code = 'error'
  let message = 'Ralat berlaku. Sila cuba lagi.'
  try {
    const body = await res.json()
    const detail = body?.detail
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      code = detail.error || code
      message = detail.message || message
    } else if (typeof detail === 'string') {
      message = detail
    }
  } catch {
    // not JSON — keep the generic message
  }
  return new MascotVideoError(message, code, res.status)
}

function auth(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` }
}

/** `null` when the feature flag is off. */
export async function fetchMascotVideoConfig(token: string): Promise<MascotVideoConfig | null> {
  const res = await fetch(`${BASE}/config`, { headers: auth(token) })
  if (res.status === 404) return null
  if (!res.ok) throw await toError(res)
  return res.json()
}

export async function fetchMascotVideos(
  token: string
): Promise<{ jobs: MascotVideoJob[]; daily: MascotVideoDaily }> {
  const res = await fetch(`${BASE}/jobs`, { headers: auth(token) })
  if (!res.ok) throw await toError(res)
  return res.json()
}

export async function fetchMascotVideo(token: string, jobId: string): Promise<MascotVideoJob> {
  const res = await fetch(`${BASE}/jobs/${jobId}`, { headers: auth(token) })
  if (!res.ok) throw await toError(res)
  return (await res.json()).job
}

/** A mascot is either an image file or the URL `generateMascot` returned. */
export type MascotChoice = { file: Blob; name: string } | { url: string }

export async function createMascotVideo(
  token: string,
  params: { clip: File; mascot: MascotChoice; prompt: string; consent: boolean }
): Promise<MascotVideoJob> {
  const form = new FormData()
  form.append('clip', params.clip)
  form.append('prompt', params.prompt)
  form.append('consent', params.consent ? 'true' : 'false')
  if ('url' in params.mascot) form.append('mascot_url', params.mascot.url)
  else form.append('mascot', params.mascot.file, params.mascot.name)
  const res = await fetch(`${BASE}/jobs`, { method: 'POST', headers: auth(token), body: form })
  if (!res.ok) throw await toError(res)
  return (await res.json()).job
}

export async function generateMascot(token: string, description: string): Promise<string> {
  const res = await fetch(`${BASE}/mascots/generate`, {
    method: 'POST',
    headers: { ...auth(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  })
  if (!res.ok) throw await toError(res)
  return (await res.json()).mascot_url
}

export async function applyMascotVideoToHero(
  token: string,
  jobId: string,
  websiteId: string
): Promise<{ message: string; live_site_updated: boolean; warning?: string }> {
  const res = await fetch(`${BASE}/jobs/${jobId}/use-as-hero`, {
    method: 'POST',
    headers: { ...auth(token), 'Content-Type': 'application/json' },
    body: JSON.stringify({ website_id: websiteId }),
  })
  if (!res.ok) throw await toError(res)
  return res.json()
}

/** Duration of a local video file in seconds, read by the browser. */
export function readClipSeconds(file: File): Promise<number | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    const done = (value: number | null) => {
      URL.revokeObjectURL(url)
      resolve(value)
    }
    video.preload = 'metadata'
    video.onloadedmetadata = () => done(Number.isFinite(video.duration) ? video.duration : null)
    video.onerror = () => done(null)
    video.src = url
  })
}

/**
 * Why a clip cannot be used, or `null` when it can. The server checks again;
 * this only saves the merchant an upload that would be refused.
 */
export function clipProblem(
  file: { type: string; size: number },
  seconds: number | null,
  config: Pick<MascotVideoConfig, 'min_clip_seconds' | 'max_clip_seconds' | 'max_clip_mb'>
): string | null {
  if (!['video/mp4', 'video/quicktime'].includes(file.type)) {
    return 'Klip mesti dalam format MP4 atau MOV.'
  }
  if (file.size > config.max_clip_mb * 1024 * 1024) {
    return `Klip terlalu besar. Maksimum ${config.max_clip_mb} MB.`
  }
  if (seconds !== null && seconds < config.min_clip_seconds) {
    return `Klip terlalu pendek. Minimum ${config.min_clip_seconds} saat.`
  }
  if (seconds !== null && seconds > config.max_clip_seconds + 0.5) {
    return `Klip terlalu panjang (${Math.round(seconds)} saat). Maksimum ${config.max_clip_seconds} saat.`
  }
  return null
}
