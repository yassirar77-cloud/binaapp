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
import { RiderCard, type Rider } from './components/RiderCard'
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

interface RawWebsite {
  id: string
}

interface RawRider {
  id: string
  name?: string | null
  phone?: string | null
  vehicle_plate?: string | null
  is_online?: boolean | null
  total_deliveries?: number | null
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

function mapRider(raw: RawRider): Rider {
  return {
    id: raw.id,
    name: (raw.name ?? '').trim(),
    phone: raw.phone ?? null,
    vehiclePlate: raw.vehicle_plate ?? null,
    isOnline: raw.is_online === true,
    totalDeliveries: typeof raw.total_deliveries === 'number' ? raw.total_deliveries : 0,
  }
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
  const [riders, setRiders] = useState<Rider[] | null>(null)

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

  useEffect(() => {
    let cancelled = false

    async function loadRiders() {
      const token = getStoredToken()
      if (!token) {
        if (!cancelled) setRiders([])
        return
      }
      const headers = {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      }
      try {
        const websitesRes = await fetch(`${API_URL}/api/v1/websites/`, { headers })
        if (!websitesRes.ok) {
          if (!cancelled) setRiders([])
          return
        }
        const websites: RawWebsite[] = await websitesRes.json()
        if (!Array.isArray(websites) || websites.length === 0) {
          if (!cancelled) setRiders([])
          return
        }

        const results = await Promise.all(
          websites.map(async (w) => {
            try {
              const res = await fetch(
                `${API_URL}/api/v1/delivery/admin/websites/${w.id}/riders`,
                { headers },
              )
              if (!res.ok) return [] as RawRider[]
              const data = await res.json()
              return Array.isArray(data) ? (data as RawRider[]) : []
            } catch (err) {
              console.warn(`[Profile] Failed to load riders for website ${w.id}:`, err)
              return [] as RawRider[]
            }
          }),
        )

        const dedupedById = new Map<string, RawRider>()
        for (const list of results) {
          for (const r of list) {
            if (r?.id && !dedupedById.has(r.id)) dedupedById.set(r.id, r)
          }
        }
        const mapped = Array.from(dedupedById.values()).map(mapRider)
        if (!cancelled) setRiders(mapped)
      } catch (err) {
        console.warn('[Profile] Failed to load riders:', err)
        if (!cancelled) setRiders([])
      }
    }

    loadRiders()
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

  const handleRiderUnavailable = useCallback(() => {
    showToast('Pengurusan rider akan datang tidak lama lagi')
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

        <RiderCard
          riders={riders}
          onAdd={handleRiderUnavailable}
          onManage={handleRiderUnavailable}
        />
      </main>

      <Toast msg={toast?.msg ?? null} tone={toast?.tone} />
    </div>
  )
}
