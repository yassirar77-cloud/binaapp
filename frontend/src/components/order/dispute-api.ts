/**
 * API client for the customer-facing dispute flow.
 *
 * Two write paths:
 *   1. Upload an evidence image to Supabase Storage (`assets` bucket,
 *      namespaced under `disputes/{orderNumber}/`).
 *      → TODO(storage): move to a dedicated `customer-disputes`
 *        bucket with a 90-day lifecycle policy.
 *   2. POST /api/v1/disputes/customer-create with the dispute payload.
 *
 * Image upload uses the public `supabase` client (anon key) — the
 * `assets` bucket is already configured for public-write in production.
 * The dispute-create call is plain `fetch` since the customer flow
 * has no JWT.
 */

import { supabase } from '@/lib/supabase'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

/* ----- Categories + resolutions (mirror backend enums) ------------------ */

export type DisputeCategoryId =
  | 'wrong_items'
  | 'quality_issue'
  | 'never_delivered'
  | 'late_delivery'
  | 'damaged_items'
  | 'overcharged'
  | 'rider_issue'
  | 'other'

export interface DisputeCategoryOption {
  id: DisputeCategoryId
  emoji: string
  label: string
}

export const DISPUTE_CATEGORIES: DisputeCategoryOption[] = [
  { id: 'wrong_items', emoji: '🍽️', label: 'Makanan tak betul' },
  { id: 'quality_issue', emoji: '❄️', label: 'Makanan sejuk' },
  { id: 'never_delivered', emoji: '🚫', label: 'Makanan tak sampai' },
  { id: 'late_delivery', emoji: '⏰', label: 'Lambat sampai' },
  { id: 'damaged_items', emoji: '💔', label: 'Makanan rosak / pecah' },
  { id: 'overcharged', emoji: '💰', label: 'Caj salah' },
  { id: 'rider_issue', emoji: '🛵', label: 'Masalah dengan rider' },
  { id: 'other', emoji: '❓', label: 'Lain-lain' },
]

/**
 * Customer's preferred resolution. The backend doesn't currently store
 * this as a structured field — we append it to the `description` so the
 * owner sees it. TODO(disputes): add a dedicated column once the dispute
 * resolution workflow grows a customer-side preference field.
 */
export type DisputeResolutionId =
  | 'refund_full'
  | 'refund_partial'
  | 'redeliver'
  | 'apology'

export interface DisputeResolutionOption {
  id: DisputeResolutionId
  label: string
  hint: string
}

export const DISPUTE_RESOLUTIONS: DisputeResolutionOption[] = [
  {
    id: 'refund_full',
    label: 'Refund penuh',
    hint: 'Pulang semua wang yang dibayar',
  },
  {
    id: 'refund_partial',
    label: 'Refund sebahagian',
    hint: 'Pulang untuk item bermasalah sahaja',
  },
  {
    id: 'redeliver',
    label: 'Hantar semula pesanan',
    hint: 'Restoran hantar pesanan baru',
  },
  {
    id: 'apology',
    label: 'Apologize sahaja',
    hint: 'Saya cuma nak luahkan, terima kasih',
  },
]

/* ----- Photo upload ----------------------------------------------------- */

const STORAGE_BUCKET = 'assets'

export class PhotoUploadError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'PhotoUploadError'
  }
}

/**
 * Upload a compressed photo blob to Supabase Storage and return the
 * public URL. The blob path is namespaced under
 * `disputes/{orderNumber}/{timestamp}_{rand}.jpg` so the owner-side
 * dispute view can group images per order.
 */
export async function uploadDisputePhoto(
  blob: Blob,
  orderNumber: string
): Promise<string> {
  if (!supabase) {
    throw new PhotoUploadError('Supabase tidak dikonfigurasi')
  }

  const safeOrder = orderNumber.replace(/[^a-zA-Z0-9_-]/g, '')
  const rand = Math.random().toString(36).slice(2, 9)
  const path = `disputes/${safeOrder}/${Date.now()}_${rand}.jpg`

  const { error } = await supabase.storage.from(STORAGE_BUCKET).upload(path, blob, {
    contentType: 'image/jpeg',
    cacheControl: '3600',
    upsert: false,
  })

  if (error) {
    throw new PhotoUploadError(error.message || 'Muat naik gagal')
  }

  const { data } = supabase.storage.from(STORAGE_BUCKET).getPublicUrl(path)
  if (!data?.publicUrl) {
    throw new PhotoUploadError('URL gambar tidak dapat dijana')
  }
  return data.publicUrl
}

/* ----- Dispute creation ------------------------------------------------- */

export interface CreateDisputePayload {
  /** Order UUID (NOT order_number — the backend keys disputes on UUID). */
  orderId: string
  category: DisputeCategoryId
  description: string
  evidenceUrls: string[]
  customerName?: string
  customerPhone?: string
  customerEmail?: string
}

export interface CreatedDispute {
  id: string
  disputeNumber: string
  status: string
  category: string
  description: string
  evidenceUrls: string[]
  createdAt: string
}

export class CreateDisputeError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message)
    this.name = 'CreateDisputeError'
  }
}

export async function createDispute(payload: CreateDisputePayload): Promise<CreatedDispute> {
  const url = `${API_BASE}/api/v1/disputes/customer-create`
  const body = {
    order_id: payload.orderId,
    category: payload.category,
    description: payload.description,
    evidence_urls: payload.evidenceUrls,
    customer_name: payload.customerName,
    customer_phone: payload.customerPhone,
    customer_email: payload.customerEmail,
  }

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = ''
    let code: string | undefined
    try {
      const json = await res.json()
      const d = json?.detail
      if (typeof d === 'string') detail = d
      else if (d && typeof d === 'object') {
        detail = d.message || ''
        code = d.error
      }
    } catch {
      // not JSON
    }
    throw new CreateDisputeError(
      detail || `Aduan gagal dihantar (${res.status})`,
      res.status,
      code
    )
  }

  const raw = await res.json()
  return {
    id: raw.id,
    disputeNumber: raw.dispute_number,
    status: raw.status,
    category: raw.category,
    description: raw.description,
    evidenceUrls: raw.evidence_urls ?? [],
    createdAt: raw.created_at,
  }
}
