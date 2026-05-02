'use client'

import { useCallback, useState } from 'react'
import { getStoredToken } from '@/lib/supabase'
import type {
  Dispute,
  DisputeMessage,
  DisputeResolutionType,
  DisputeStatus,
} from '@/types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || ''

export type SubscriberCategoryKey =
  | 'poor_design'
  | 'website_bug'
  | 'service_outage'
  | 'payment_issue'
  | 'technical_problem'
  | 'order_system'
  | 'chat_issue'
  | 'other'

export interface CreateDisputePayload {
  category: SubscriberCategoryKey
  description: string
  website_id?: string
  evidence_urls?: string[]
}

export interface CreateDisputeResult {
  status: 'approved' | 'rejected' | 'under_review'
  message: string
  amount?: number
}

class DisputeApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'DisputeApiError'
    this.status = status
  }
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return body.detail
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return String(body.detail[0].msg)
  } catch {
    /* ignore */
  }
  return `Ralat ${res.status}`
}

function authHeaders(): HeadersInit {
  const token = getStoredToken()
  if (!token) throw new DisputeApiError('Sesi tamat. Sila log masuk semula.', 401)
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
}

export function useDisputeMutations() {
  const [submitting, setSubmitting] = useState(false)

  const createDispute = useCallback(
    async (payload: CreateDisputePayload): Promise<CreateDisputeResult> => {
      setSubmitting(true)
      try {
        const res = await fetch(`${API_URL}/api/v1/disputes/create`, {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify(payload),
        })
        if (!res.ok) {
          // Treat backend non-OK as still under_review per legacy behavior
          return {
            status: 'under_review',
            message: 'Aduan anda telah dihantar untuk semakan lanjut',
          }
        }
        const data = await res.json()
        const status = data.status || data.ai_decision || 'under_review'
        if (status === 'approved' || status === 'resolved') {
          const amount = data.refund_amount ?? data.credit_amount ?? 0
          return {
            status: 'approved',
            message: `BinaCredit RM${Number(amount).toFixed(2)} telah ditambah ke akaun anda`,
            amount: Number(amount),
          }
        }
        if (status === 'rejected') {
          return {
            status: 'rejected',
            message: 'Aduan tidak dapat disahkan. Anda boleh mengemukakan bukti tambahan.',
          }
        }
        return {
          status: 'under_review',
          message: 'Aduan anda telah dihantar untuk semakan lanjut',
        }
      } finally {
        setSubmitting(false)
      }
    },
    [],
  )

  const resolveDispute = useCallback(
    async (disputeId: string, resolutionType: DisputeResolutionType, notes: string) => {
      setSubmitting(true)
      try {
        const res = await fetch(`${API_URL}/api/v1/disputes/owner/${disputeId}/resolve`, {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({
            resolution_type: resolutionType,
            resolution_notes: notes,
          }),
        })
        if (!res.ok) throw new DisputeApiError(await parseError(res), res.status)
      } finally {
        setSubmitting(false)
      }
    },
    [],
  )

  const sendReply = useCallback(async (disputeId: string, message: string) => {
    const res = await fetch(`${API_URL}/api/v1/disputes/owner/${disputeId}/message`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        message,
        sender_type: 'owner',
        sender_name: 'Business Owner',
      }),
    })
    if (!res.ok) throw new DisputeApiError(await parseError(res), res.status)
  }, [])

  return { createDispute, resolveDispute, sendReply, submitting }
}

export async function loadDisputeMessages(disputeId: string): Promise<DisputeMessage[]> {
  const res = await fetch(`${API_URL}/api/v1/disputes/owner/${disputeId}/messages`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new DisputeApiError(await parseError(res), res.status)
  const data = await res.json()
  return Array.isArray(data?.messages) ? (data.messages as DisputeMessage[]) : []
}

export async function loadDisputesList(perPage = 50): Promise<Dispute[]> {
  const res = await fetch(`${API_URL}/api/v1/disputes/owner/list?per_page=${perPage}`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new DisputeApiError(await parseError(res), res.status)
  const data = await res.json()
  return Array.isArray(data?.disputes) ? (data.disputes as Dispute[]) : []
}

export const ACTIVE_STATUSES: ReadonlySet<DisputeStatus> = new Set([
  'open',
  'under_review',
  'awaiting_response',
])

export const CLOSED_STATUSES: ReadonlySet<DisputeStatus> = new Set([
  'resolved',
  'closed',
  'rejected',
  'escalated',
])

export { DisputeApiError }
