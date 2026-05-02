'use client'

import { useCallback, useRef, useState } from 'react'
import type { User } from '@supabase/supabase-js'
import { ProfileCard, type ProfileCardData } from './components/ProfileCard'
import { Toast, type ToastTone } from './components/primitives/Toast'

interface ProfileHubProps {
  user: User
  initial: ProfileCardData
  loading?: boolean
  planLabel?: string
  onSaveProfile: (next: ProfileCardData) => Promise<void>
}

const TOAST_TIMEOUT = 2200

export function ProfileHub({
  user,
  initial,
  loading = false,
  planLabel,
  onSaveProfile,
}: ProfileHubProps) {
  const [toast, setToast] = useState<{ msg: string; tone: ToastTone } | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showToast = useCallback((msg: string, tone: ToastTone = 'success') => {
    setToast({ msg, tone })
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setToast(null), TOAST_TIMEOUT)
  }, [])

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
      </main>

      <Toast msg={toast?.msg ?? null} tone={toast?.tone} />
    </div>
  )
}
