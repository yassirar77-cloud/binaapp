import type { DisputeResolutionType } from '@/types'
import type { SubscriberCategoryKey } from './useDisputeMutations'

export interface SubscriberCategoryDef {
  key: SubscriberCategoryKey
  icon: string
  label: string
  desc: string
}

export const SUBSCRIBER_CATEGORIES: ReadonlyArray<SubscriberCategoryDef> = [
  { key: 'poor_design', icon: '🎨', label: 'Reka Bentuk Buruk', desc: 'Laman web yang dijana tidak memuaskan' },
  { key: 'website_bug', icon: '🌐', label: 'Masalah Laman Web', desc: 'Laman web tidak berfungsi dengan betul' },
  { key: 'service_outage', icon: '⚡', label: 'Gangguan Perkhidmatan', desc: 'Platform BinaApp tidak boleh diakses' },
  { key: 'payment_issue', icon: '💳', label: 'Masalah Pembayaran', desc: 'Caj salah atau pembayaran gagal' },
  { key: 'technical_problem', icon: '🐛', label: 'Masalah Teknikal', desc: 'Fungsi tidak berjalan seperti sepatutnya' },
  { key: 'order_system', icon: '📱', label: 'Masalah Pesanan', desc: 'Sistem pesanan atau penghantaran bermasalah' },
  { key: 'chat_issue', icon: '💬', label: 'Masalah Chat', desc: 'Chat widget tidak berfungsi' },
  { key: 'other', icon: '❓', label: 'Lain-lain', desc: 'Masalah lain yang tidak disenaraikan' },
]

export interface ResolutionOption {
  key: DisputeResolutionType
  icon: string
  label: string
  desc: string
}

export const RESOLUTION_OPTIONS: ReadonlyArray<ResolutionOption> = [
  { key: 'issue_resolved', icon: '✅', label: 'Masalah Selesai', desc: 'BinaApp telah selesaikan masalah' },
  { key: 'self_resolved', icon: '🔧', label: 'Selesai Sendiri', desc: 'Saya jumpa penyelesaian sendiri' },
  { key: 'no_longer_needed', icon: '🚫', label: 'Tidak Perlu Lagi', desc: 'Masalah tidak lagi relevan' },
  { key: 'accepted_explanation', icon: '💬', label: 'Terima Penjelasan', desc: 'Terima penjelasan BinaApp' },
  { key: 'still_unsatisfied', icon: '😐', label: 'Masih Tidak Puas Hati', desc: 'Tutup tetapi masih tidak puas hati' },
  { key: 'withdraw_complaint', icon: '↩️', label: 'Tarik Balik Aduan', desc: 'Batalkan aduan ini sepenuhnya' },
]

export const RESOLUTION_LABELS: Record<string, string> = Object.fromEntries(
  RESOLUTION_OPTIONS.map((o) => [o.key, o.label]),
)

export function categoryFor(key: string | null | undefined): SubscriberCategoryDef | null {
  if (!key) return null
  return SUBSCRIBER_CATEGORIES.find((c) => c.key === key) ?? null
}
