'use client'

import { useCallback, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import type { User } from '@supabase/supabase-js'
import useSubscription from '@/hooks/useSubscription'
import { ProfileCard, type ProfileCardData } from './components/ProfileCard'
import {
  PlanCard,
  type PlanStatus,
  type PlanTier,
  type PlanUsage,
} from './components/PlanCard'
import { Toast, type ToastTone } from './components/primitives/Toast'

interface ProfileHubProps {
  user: User
  initial: ProfileCardData
  loading?: boolean
  onSaveProfile: (next: ProfileCardData) => Promise<void>
}

const TOAST_TIMEOUT = 2200
const VALID_TIERS: PlanTier[] = ['starter', 'basic', 'pro']
const VALID_STATUSES: PlanStatus[] = ['active', 'expired', 'cancelled']

function normalizeTier(name: string | undefined): PlanTier {
  const lower = (name ?? '').toLowerCase() as PlanTier
  return VALID_TIERS.includes(lower) ? lower : 'starter'
}

function normalizeStatus(status: string | undefined): PlanStatus {
  const lower = (status ?? '').toLowerCase() as PlanStatus
  return VALID_STATUSES.includes(lower) ? lower : 'active'
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

  const showToast = useCallback((msg: string, tone: ToastTone = 'success') => {
    setToast({ msg, tone })
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setToast(null), TOAST_TIMEOUT)
  }, [])

  const tier = normalizeTier(plan?.name)
  const planLabel = tier.toUpperCase()
  const status = normalizeStatus(plan?.status)
  const isExpired = plan?.is_expired ?? false
  const endDate = plan?.end_date ?? null
  const planUsage: PlanUsage | null = subscriptionData?.usage ?? null

  const handleUpgrade = useCallback(() => {
    router.push('/dashboard/billing')
  }, [router])

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
      </main>

      <Toast msg={toast?.msg ?? null} tone={toast?.tone} />
    </div>
  )
}
