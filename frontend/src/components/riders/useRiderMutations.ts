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

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return String(body.detail[0].msg)
  } catch {
    /* ignore JSON parse errors */
  }
  return `Ralat ${res.status}`
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
        if (!res.ok) throw new RiderApiError(await parseError(res), res.status)
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
        if (!res.ok) throw new RiderApiError(await parseError(res), res.status)
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
        if (!res.ok) throw new RiderApiError(await parseError(res), res.status)
      } finally {
        setDeleting(false)
      }
    },
    [authHeaders],
  )

  return { createRider, updateRider, deleteRider, submitting, deleting }
}

export { RiderApiError }
