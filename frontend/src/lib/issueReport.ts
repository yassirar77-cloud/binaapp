/**
 * "Report Issue" client for generated websites.
 *
 * Backend: POST /api/v1/websites/{website_id}/report-issue (owner-only,
 * flag-gated behind ISSUE_REPORT_ENABLED — a 404 means the feature is off
 * and the UI must hide itself gracefully).
 *
 * Within the per-site cap the backend auto-grants ONE free regeneration
 * (status "regen_granted"); beyond it the report escalates to the admin
 * queue (status "escalated"). After a grant, the merchant's next normal
 * regenerate of that site is automatically free — no special parameter.
 */
import { getApiAuthToken } from '@/lib/supabase'
import { API_BASE_URL } from '@/lib/env'

export const ISSUE_CATEGORIES = [
  { id: 'images_wrong', label: 'Gambar tak kena', emoji: '🖼️' },
  { id: 'text_wrong', label: 'Teks tak betul', emoji: '📝' },
  { id: 'page_broken', label: 'Page rosak', emoji: '🛠️' },
  { id: 'sensitive_content', label: 'Kandungan sensitif', emoji: '🚫' },
  { id: 'other', label: 'Lain-lain', emoji: '💬' },
] as const

export type IssueCategory = (typeof ISSUE_CATEGORIES)[number]['id']

export const ISSUE_DESCRIPTION_MAX = 500

/** Session flag so the button hides everywhere after one "feature off" 404. */
const DISABLED_STORAGE_KEY = 'binaapp_issue_report_disabled'

export function isIssueReportKnownDisabled(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return sessionStorage.getItem(DISABLED_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function markIssueReportDisabled(): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(DISABLED_STORAGE_KEY, '1')
  } catch {
    /* private mode etc. — non-fatal */
  }
}

export type ReportOutcome =
  | { kind: 'regen_granted'; regensRemaining: number | null; duplicate: boolean; message: string }
  | { kind: 'escalated'; duplicate: boolean; message: string }
  | { kind: 'feature_disabled'; message: string }
  | { kind: 'error'; message: string }

/**
 * Map an HTTP status + parsed body to a user-facing outcome. Pure —
 * unit-tested without a browser.
 */
export function mapReportResponse(status: number, body: any): ReportOutcome {
  if (status === 200 && body?.status === 'regen_granted') {
    return {
      kind: 'regen_granted',
      regensRemaining:
        typeof body.regens_remaining === 'number' ? body.regens_remaining : null,
      duplicate: Boolean(body.duplicate),
      message:
        'Kami dah bagi regenerate percuma! Klik regenerate untuk cuba semula.',
    }
  }
  if (status === 200) {
    // "escalated" (or any other open status the backend returns for a
    // duplicate) — the report is in the admin queue.
    return {
      kind: 'escalated',
      duplicate: Boolean(body?.duplicate),
      message:
        'Kami dah terima report anda. Team kami akan semak dan hubungi anda.',
    }
  }
  if (status === 404) {
    // Feature flag off (ISSUE_REPORT_ENABLED=false) — hide the UI.
    return {
      kind: 'feature_disabled',
      message: 'Ciri report belum tersedia buat masa ini.',
    }
  }
  if (status === 429) {
    return {
      kind: 'error',
      message: 'Anda dah report terlalu banyak kali hari ni. Cuba lagi esok.',
    }
  }
  if (status === 403) {
    return {
      kind: 'error',
      message: 'Anda tidak dibenarkan untuk report website ini.',
    }
  }
  if (status === 400 && body?.detail?.error === 'no_completed_generation') {
    return {
      kind: 'error',
      message: 'Website ini belum siap dijana — tiada apa untuk direport lagi.',
    }
  }
  return {
    kind: 'error',
    message: 'Maaf, report tak dapat dihantar. Sila cuba lagi sekejap.',
  }
}

export async function submitIssueReport(
  websiteId: string,
  category: IssueCategory,
  description: string,
): Promise<ReportOutcome> {
  const token = await getApiAuthToken()
  if (!token) {
    return { kind: 'error', message: 'Sila log masuk semula untuk report.' }
  }

  let response: Response
  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/websites/${websiteId}/report-issue`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          category,
          description: description.trim()
            ? description.trim().slice(0, ISSUE_DESCRIPTION_MAX)
            : undefined,
        }),
      },
    )
  } catch {
    return {
      kind: 'error',
      message: 'Tiada sambungan internet. Sila cuba lagi.',
    }
  }

  let body: any = null
  try {
    body = await response.json()
  } catch {
    /* non-JSON error body — mapReportResponse handles null */
  }

  const outcome = mapReportResponse(response.status, body)
  if (outcome.kind === 'feature_disabled') {
    markIssueReportDisabled()
  }
  return outcome
}
