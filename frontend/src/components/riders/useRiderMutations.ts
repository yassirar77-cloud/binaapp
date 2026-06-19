'use client'

import { useCallback, useState } from 'react'
import { getStoredToken } from '@/lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || ''
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

export type VehicleType = 'motorcycle' | 'car' | 'bicycle' | 'scooter'

export interface RiderPayload {
  name: string
  phone: string
  email?: string
  password?: string
  vehicle_type: VehicleType
  vehicle_plate?: string
  vehicle_model?: string
  is_active?: boolean
}

export function isValidUUID(str: string | null | undefined): boolean {
  if (!str) return false
  return UUID_RE.test(str)
}

class RiderApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'RiderApiError'
    this.status = status
  }
}

/** Structured detail returned by SubscriptionGuard.check_limit("add_rider"). */
export interface RiderLimitInfo {
  message: string
  canBuyAddon: boolean
  addonType: string
  addonPrice?: number
  currentUsage?: number
  limit?: number
}

class RiderLimitError extends RiderApiError {
  info: RiderLimitInfo
  constructor(info: RiderLimitInfo, status: number) {
    super(info.message, status)
    this.name = 'RiderLimitError'
    this.info = info
  }
}

// Turn a non-OK response into a typed error. A 403 carrying the structured
// limit-reached payload becomes a RiderLimitError (so the UI can open the
// buy-slot modal); everything else becomes a RiderApiError with the best human
// message we can extract — crucially, never a bare "Ralat 403" when the API
// actually sent a `detail` object (the old parseError collapsed those).
async function toRiderError(res: Response): Promise<RiderApiError> {
  let detail: unknown
  try {
    detail = (await res.json())?.detail
  } catch {
    /* ignore JSON parse errors */
  }

  if (
    res.status === 403 &&
    detail &&
    typeof detail === 'object' &&
    !Array.isArray(detail) &&
    ((detail as Record<string, unknown>).error === 'limit_reached' ||
      (detail as Record<string, unknown>).can_buy_addon !== undefined)
  ) {
    const d = detail as Record<string, unknown>
    return new RiderLimitError(
      {
        message:
          typeof d.message === 'string'
            ? (d.message as string)
            : 'Had rider pelan anda telah dicapai. / You’ve reached your plan’s rider limit.',
        canBuyAddon: !!d.can_buy_addon,
        addonType: typeof d.addon_type === 'string' ? (d.addon_type as string) : 'rider',
        addonPrice: typeof d.addon_price === 'number' ? (d.addon_price as number) : undefined,
        currentUsage: typeof d.current_usage === 'number' ? (d.current_usage as number) : undefined,
        limit: typeof d.limit === 'number' ? (d.limit as number) : undefined,
      },
      res.status,
    )
  }

  let message = `Ralat ${res.status}`
  if (typeof detail === 'string') {
    message = detail
  } else if (Array.isArray(detail) && (detail[0] as Record<string, unknown>)?.msg) {
    message = String((detail[0] as Record<string, unknown>).msg)
  } else if (
    detail &&
    typeof detail === 'object' &&
    typeof (detail as Record<string, unknown>).message === 'string'
  ) {
    message = (detail as Record<string, unknown>).message as string
  }
  return new RiderApiError(message, res.status)
}

export function useRiderMutations() {
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const authHeaders = useCallback((): HeadersInit => {
    const token = getStoredToken()
    if (!token) throw new RiderApiError('Sesi tamat. Sila log masuk semula.', 401)
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  }, [])

  const createRider = useCallback(
    async (websiteId: string, payload: RiderPayload) => {
      if (!isValidUUID(websiteId)) {
        throw new RiderApiError('Sila pilih website terlebih dahulu', 400)
      }
      setSubmitting(true)
      try {
        const res = await fetch(
          `${API_URL}/api/v1/delivery/admin/websites/${websiteId}/riders`,
          {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(payload),
          },
        )
        if (!res.ok) throw await toRiderError(res)
        return await res.json()
      } finally {
        setSubmitting(false)
      }
    },
    [authHeaders],
  )

  const updateRider = useCallback(
    async (riderId: string, payload: RiderPayload) => {
      setSubmitting(true)
      try {
        const body: Partial<RiderPayload> = { ...payload }
        if (!body.password) delete body.password
        const res = await fetch(`${API_URL}/api/v1/delivery/riders/${riderId}`, {
          method: 'PUT',
          headers: authHeaders(),
          body: JSON.stringify(body),
        })
        if (!res.ok) throw await toRiderError(res)
        return await res.json()
      } finally {
        setSubmitting(false)
      }
    },
    [authHeaders],
  )

  const deleteRider = useCallback(
    async (riderId: string) => {
      setDeleting(true)
      try {
        const res = await fetch(`${API_URL}/api/v1/delivery/riders/${riderId}`, {
          method: 'DELETE',
          headers: authHeaders(),
        })
        if (!res.ok) throw await toRiderError(res)
      } finally {
        setDeleting(false)
      }
    },
    [authHeaders],
  )

  return { createRider, updateRider, deleteRider, submitting, deleting }
}

export { RiderApiError, RiderLimitError }
