'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import type { User } from '@supabase/supabase-js'
import { supabase, getCurrentUser } from '@/lib/supabase'
import { ProfileHub } from './ProfileHub'
import type { ProfileCardData } from './components/ProfileCard'
import './tokens.css'

const EMPTY_PROFILE: ProfileCardData = { fullName: '', businessName: '', phone: '' }

export default function ProfilePage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<ProfileCardData>(EMPTY_PROFILE)
  const [loading, setLoading] = useState(true)
  const [authChecking, setAuthChecking] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function init() {
      const currentUser = await getCurrentUser()
      if (cancelled) return

      if (!currentUser) {
        router.push('/')
        return
      }

      setUser(currentUser as User)
      setAuthChecking(false)

      if (supabase) {
        try {
          const { data } = await supabase
            .from('profiles')
            .select('full_name, business_name, phone')
            .eq('id', currentUser.id)
            .maybeSingle()

          if (!cancelled && data) {
            setProfile({
              fullName: data.full_name ?? '',
              businessName: data.business_name ?? '',
              phone: data.phone ?? '',
            })
          }
        } catch (err) {
          console.warn('[Profile] Could not load profile:', err)
        }
      }

      if (!cancelled) setLoading(false)
    }

    init()
    return () => { cancelled = true }
  }, [router])

  const handleSaveProfile = useCallback(
    async (next: ProfileCardData) => {
      if (!supabase || !user) {
        throw new Error('Sesi tidak sah. Sila log masuk semula.')
      }
      const { error } = await supabase.from('profiles').upsert({
        id: user.id,
        email: user.email,
        full_name: next.fullName,
        business_name: next.businessName,
        phone: next.phone,
        updated_at: new Date().toISOString(),
      })
      if (error) throw new Error(error.message || 'Gagal simpan perubahan')
      setProfile(next)
    },
    [user],
  )

  if (authChecking || !user) {
    return (
      <div
        className="profile-hub"
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--ink-3)',
          fontSize: 13,
        }}
      >
        Memuatkan…
      </div>
    )
  }

  return (
    <ProfileHub
      user={user}
      initial={profile}
      loading={loading}
      onSaveProfile={handleSaveProfile}
    />
  )
}

