'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import type { User } from '@supabase/supabase-js'
import useSubscription from '@/hooks/useSubscription'
import { getStoredToken } from '@/lib/supabase'
import { ProfileCard, type ProfileCardData } from './components/ProfileCard'
import {
  PlanCard,
  type PlanStatus,
  type PlanTier,
  type PlanUsage,
} from './components/PlanCard'
import {
  BillingCard,
  type Invoice,
  type InvoiceStatus,
} from './components/BillingCard'
import { Toast, type ToastTone } from './components/primitives/Toast'

interface ProfileHubProps {
  user: User
  initial: ProfileCardData
  loading?: boolean
  onSaveProfile: (next: ProfileCardData) => Promise<void>
}

interface RawTransaction {
  transaction_id: string
  transaction_type?: string
  item_description?: string
  amount?: number | string | null
  payment_status?: string
  created_at?: string
  toyyibpay_bill_code?: string | null
  invoice_number?: string | null
}

const TOAST_TIMEOUT = 2200
const VALID_TIERS: PlanTier[] = ['starter', 'basic', 'pro']
const VALID_STATUSES: PlanStatus[] = ['active', 'expired', 'cancelled']
const API_URL = process.env.NEXT_PUBLIC_API_URL || ''
const TOYYIBPAY_BILL_BASE = 'https://toyyibpay.com'

const BM_MONTHS = [
  'Januari', 'Februari', 'Mac', 'April', 'Mei', 'Jun',
  'Julai', 'Ogos', 'September', 'Oktober', 'November', 'Disember',
]

function normalizeTier(name: string | undefined): PlanTier {
  const lower = (name ?? '').toLowerCase() as PlanTier
  return VALID_TIERS.includes(lower) ? lower : 'starter'
}

function normalizeStatus(status: string | undefined): PlanStatus {
  const lower = (status ?? '').toLowerCase() as PlanStatus
  return VALID_STATUSES.includes(lower) ? lower : 'active'
}

function normalizeInvoiceStatus(status: string | undefined): InvoiceStatus {
  const lower = (status ?? '').toLowerCase()
  if (lower === 'success' || lower === 'paid' || lower === 'completed') return 'success'
  if (lower === 'pending' || lower === 'processing') return 'pending'
  return 'failed'
}

function formatBmDate(iso: string | null): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return `${d.getDate()} ${BM_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

function formatInvoiceLabel(iso: string | null): string {
  if (!iso) return 'Invois'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'Invois'
  return `Invois ${BM_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

function toAmount(raw: number | string | null | undefined): number | null {
  if (raw === null || raw === undefined) return null
  const n = typeof raw === 'string' ? Number(raw) : raw
  return Number.isFinite(n) ? n : null
}

function mapTransaction(t: RawTransaction): Invoice | null {
  const created = t.created_at ?? null
  const date = formatBmDate(created)
  if (!date) return null
  return {
    id: t.transaction_id,
    invoiceNumber: t.invoice_number ?? null,
    label: formatInvoiceLabel(created),
    date,
    amount: toAmount(t.amount),
    status: normalizeInvoiceStatus(t.payment_status),
    toyyibpayBillCode: t.toyyibpay_bill_code ?? null,
  }
}

export function ProfileHub({
  user,
  initial,
  loading = false,
  onSaveProfile,
}: ProfileHubProps) {
  const router = useRouter()
  const [toast, setToast] = useState<{ msg: string; tone: ToastTone } | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { usage: subscriptionData, plan, loading: subLoading } = useSubscription()
  const [invoices, setInvoices] = useState<Invoice[] | null>(null)

  const showToast = useCallback((msg: string, tone: ToastTone = 'success') => {
    setToast({ msg, tone })
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setToast(null), TOAST_TIMEOUT)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadInvoices() {
      const token = getStoredToken()
      if (!token) {
        if (!cancelled) setInvoices([])
        return
      }
      try {
        const res = await fetch(`${API_URL}/api/v1/subscription/transactions?limit=3`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        })
        if (!res.ok) {
          if (!cancelled) setInvoices([])
          return
        }
        const data: { transactions?: RawTransaction[] } = await res.json()
        const mapped = (data.transactions ?? [])
          .map(mapTransaction)
          .filter((inv): inv is Invoice => inv !== null)
        if (!cancelled) setInvoices(mapped)
      } catch (err) {
        console.warn('[Profile] Failed to load transactions:', err)
        if (!cancelled) setInvoices([])
      }
    }

    loadInvoices()
    return () => { cancelled = true }
  }, [])

  const tier = normalizeTier(plan?.name)
  const planLabel = tier.toUpperCase()
  const status = normalizeStatus(plan?.status)
  const isExpired = plan?.is_expired ?? false
  const endDate = plan?.end_date ?? null
  const planUsage: PlanUsage | null = subscriptionData?.usage ?? null

  const hasActiveBilling = endDate !== null
  const nextChargeDate = formatBmDate(endDate)

  const handleUpgrade = useCallback(() => {
    router.push('/dashboard/billing')
  }, [router])

  const handleViewAllInvoices = useCallback(() => {
    router.push('/dashboard/transactions')
  }, [router])

  const handleChangePayment = useCallback(() => {
    router.push('/dashboard/billing')
  }, [router])

  const handleDownloadReceipt = useCallback((invoice: Invoice) => {
    if (!invoice.toyyibpayBillCode) {
      showToast('Resit tidak tersedia untuk transaksi ini', 'error')
      return
    }
    window.open(`${TOYYIBPAY_BILL_BASE}/${invoice.toyyibpayBillCode}`, '_blank', 'noopener,noreferrer')
  }, [showToast])

  return (
    <div className="profile-hub" style={{ minHeight: '100vh', padding: '40px 20px 80px' }}>
      <main
        style={{
          maxWidth: 720,
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
      >
        <header style={{ marginBottom: 8 }}>
          <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: '-0.015em' }}>Tetapan</h1>
          <p style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 2 }}>
            Urus akaun, langganan dan operasi
          </p>
        </header>

        <ProfileCard
          email={user.email ?? ''}
          createdAt={user.created_at}
          planLabel={planLabel}
          initial={initial}
          loading={loading}
          onSave={onSaveProfile}
          onSuccess={(msg) => showToast(msg, 'success')}
          onError={(msg) => showToast(msg, 'error')}
        />

        <PlanCard
          tier={tier}
          status={status}
          endDate={endDate}
          isExpired={isExpired}
          usage={planUsage}
          loading={subLoading}
          onUpgrade={handleUpgrade}
        />

        <BillingCard
          invoices={invoices}
          hasActiveBilling={hasActiveBilling}
          nextChargeDate={nextChargeDate}
          onViewAll={handleViewAllInvoices}
          onChangePayment={handleChangePayment}
          onDownloadReceipt={handleDownloadReceipt}
        />
      </main>

      <Toast msg={toast?.msg ?? null} tone={toast?.tone} />
    </div>
  )
}
