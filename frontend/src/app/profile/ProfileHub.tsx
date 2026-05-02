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
import { DisputeCard, type Dispute } from './components/DisputeCard'
import { Toast, type ToastTone } from './components/primitives/Toast'
import { RiderFormModal } from '@/components/riders/RiderFormModal'
import type { RiderFormRider, RiderFormWebsite } from '@/components/riders/RiderForm'
import type { VehicleType } from '@/components/riders/useRiderMutations'

interface ProfileHubProps {
  user: User
  initial: ProfileCardData
  loading?: boolean
  onSaveProfile: (next: ProfileCardData) => Promise<void>
  onLogout: () => void | Promise<void>
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
  name?: string | null
  business_name?: string | null
  subdomain?: string | null
}

interface RawRider {
  id: string
  name?: string | null
  phone?: string | null
  email?: string | null
  vehicle_type?: string | null
  vehicle_plate?: string | null
  vehicle_model?: string | null
  is_active?: boolean | null
  is_online?: boolean | null
  total_deliveries?: number | null
}

interface RawDispute {
  id: string
  dispute_number?: string | null
  order_id?: string | null
  customer_name?: string | null
  description?: string | null
  order_amount?: number | string | null
  disputed_amount?: number | string | null
  status?: string | null
  created_at?: string | null
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

function mapDispute(raw: RawDispute): Dispute | null {
  if (!raw.id || !raw.created_at) return null
  const displayId = raw.dispute_number?.trim() || raw.order_id?.trim() || raw.id
  const amountRaw = raw.disputed_amount ?? raw.order_amount ?? null
  const amountNum =
    amountRaw === null || amountRaw === undefined
      ? null
      : Number.isFinite(Number(amountRaw))
        ? Number(amountRaw)
        : null
  return {
    id: raw.id,
    displayId,
    customerName: (raw.customer_name ?? '').trim(),
    reason: (raw.description ?? '').trim() || 'Tiada keterangan',
    amount: amountNum,
    createdAt: raw.created_at,
  }
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
  onLogout,
}: ProfileHubProps) {
  const router = useRouter()
  const [toast, setToast] = useState<{ msg: string; tone: ToastTone } | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { usage: subscriptionData, plan, loading: subLoading } = useSubscription()
  const [invoices, setInvoices] = useState<Invoice[] | null>(null)
  const [riders, setRiders] = useState<Rider[] | null>(null)
  const [rawRiders, setRawRiders] = useState<Map<string, RawRider>>(new Map())
  const [websites, setWebsites] = useState<RawWebsite[]>([])
  const [disputes, setDisputes] = useState<Dispute[] | null>(null)
  const [openDisputeCount, setOpenDisputeCount] = useState(0)
  const [riderModal, setRiderModal] = useState<
    | { mode: 'closed' }
    | { mode: 'add' }
    | { mode: 'edit'; rider: RiderFormRider }
  >({ mode: 'closed' })

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

  const loadRiders = useCallback(async () => {
    const token = getStoredToken()
    if (!token) {
      setRiders([])
      setRawRiders(new Map())
      return
    }
    const headers = {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
    try {
      const websitesRes = await fetch(`${API_URL}/api/v1/websites/`, { headers })
      if (!websitesRes.ok) {
        setWebsites([])
        setRiders([])
        setRawRiders(new Map())
        return
      }
      const websitesData: RawWebsite[] = await websitesRes.json()
      const websiteList = Array.isArray(websitesData) ? websitesData : []
      setWebsites(websiteList)

      if (websiteList.length === 0) {
        setRiders([])
        setRawRiders(new Map())
        return
      }

      const results = await Promise.all(
        websiteList.map(async (w) => {
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
      setRiders(mapped)
      setRawRiders(dedupedById)
    } catch (err) {
      console.warn('[Profile] Failed to load riders:', err)
      setRiders([])
      setRawRiders(new Map())
    }
  }, [])

  useEffect(() => {
    void loadRiders()
  }, [loadRiders])

  useEffect(() => {
    let cancelled = false

    async function loadDisputes() {
      const token = getStoredToken()
      if (!token) {
        if (!cancelled) {
          setDisputes([])
          setOpenDisputeCount(0)
        }
        return
      }
      try {
        const res = await fetch(
          `${API_URL}/api/v1/disputes/owner/list?status=open&per_page=1`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          },
        )
        if (!res.ok) {
          if (!cancelled) {
            setDisputes([])
            setOpenDisputeCount(0)
          }
          return
        }
        const data: { disputes?: RawDispute[]; total?: number } = await res.json()
        const mapped = (data.disputes ?? [])
          .map(mapDispute)
          .filter((d): d is Dispute => d !== null)
        if (!cancelled) {
          setDisputes(mapped)
          setOpenDisputeCount(typeof data.total === 'number' ? data.total : mapped.length)
        }
      } catch (err) {
        console.warn('[Profile] Failed to load disputes:', err)
        if (!cancelled) {
          setDisputes([])
          setOpenDisputeCount(0)
        }
      }
    }

    loadDisputes()
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

  const handleAddRider = useCallback(() => {
    setRiderModal({ mode: 'add' })
  }, [])

  const handleManageRider = useCallback(
    (rider: Rider) => {
      const raw = rawRiders.get(rider.id)
      const editRider: RiderFormRider = {
        id: rider.id,
        name: rider.name || raw?.name || null,
        phone: rider.phone ?? raw?.phone ?? null,
        email: raw?.email ?? null,
        vehicle_type: (raw?.vehicle_type as VehicleType | undefined) ?? null,
        vehicle_plate: rider.vehiclePlate ?? raw?.vehicle_plate ?? null,
        vehicle_model: raw?.vehicle_model ?? null,
        is_active: raw?.is_active ?? null,
      }
      setRiderModal({ mode: 'edit', rider: editRider })
    },
    [rawRiders],
  )

  const closeRiderModal = useCallback(() => setRiderModal({ mode: 'closed' }), [])

  const handleViewAllDisputes = useCallback(() => {
    router.push('/disputes')
  }, [router])

  const handleRespondDispute = useCallback(() => {
    router.push('/disputes')
  }, [router])

  return (
    <div className="profile-hub profile-hub-page" style={{ minHeight: '100vh', padding: '40px 20px 80px' }}>
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
          onAdd={handleAddRider}
          onManage={handleManageRider}
        />

        <DisputeCard
          disputes={disputes}
          totalOpen={openDisputeCount}
          onViewAll={handleViewAllDisputes}
          onRespond={handleRespondDispute}
        />

        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
          <button
            type="button"
            onClick={() => onLogout()}
            className="profile-logout"
            style={{
              fontFamily: 'inherit',
              fontSize: 13,
              fontWeight: 500,
              color: '#dc2626',
              border: '0.5px solid var(--border-strong)',
              borderRadius: 'var(--r-input)',
              padding: '8px 18px',
              minHeight: 36,
              background: 'transparent',
              cursor: 'pointer',
              transition: 'background 120ms',
              letterSpacing: 'inherit',
            }}
          >
            Log keluar
          </button>
        </div>
      </main>

      <Toast msg={toast?.msg ?? null} tone={toast?.tone} />

      <RiderFormModal
        open={riderModal.mode !== 'closed'}
        mode={riderModal.mode === 'edit' ? 'edit' : 'add'}
        rider={riderModal.mode === 'edit' ? riderModal.rider : undefined}
        websites={websites}
        initialWebsiteId={websites[0]?.id ?? null}
        onClose={closeRiderModal}
        onSaved={() => { void loadRiders() }}
        onDeleted={() => {
          void loadRiders()
          closeRiderModal()
        }}
        onShowToast={(msg, tone) => showToast(msg, tone)}
      />
    </div>
  )
}
