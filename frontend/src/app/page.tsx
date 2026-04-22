/**
 * Landing Page
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { signOut, getCurrentUser, getStoredToken } from '@/lib/supabase'
import { UpgradeModal } from '@/components/UpgradeModal'
import LandingNav from '@/components/landing/LandingNav'
import LandingHero from '@/components/landing/LandingHero'
import LandingFeatures from '@/components/landing/LandingFeatures'
import LandingPricing from '@/components/landing/LandingPricing'
import LandingFooter from '@/components/landing/LandingFooter'

function LandingPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [targetTier, setTargetTier] = useState<'starter' | 'basic' | 'pro'>('starter')

  useEffect(() => {
    checkUser()
  }, [])

  // Handle tier parameter from redirect after login
  useEffect(() => {
    if (!loading && user) {
      const tier = searchParams.get('tier') as 'starter' | 'basic' | 'pro' | null
      if (tier && ['starter', 'basic', 'pro'].includes(tier)) {
        // Clear the URL parameter
        router.replace('/', { scroll: false })
        // Open the upgrade modal or redirect
        handleSelectPlan(tier)
      }
    }
  }, [loading, user, searchParams])

  async function checkUser() {
    try {
      // Check for stored auth token first (custom backend auth)
      const token = getStoredToken()
      if (token) {
        const currentUser = await getCurrentUser()
        setUser(currentUser)
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Error checking user:', error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleLogout() {
    try {
      await signOut()
      setUser(null)
      router.refresh()
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  function handleSelectPlan(tier: 'starter' | 'basic' | 'pro') {
    if (!user) {
      // Not logged in - redirect to login with return URL
      router.push(`/login?redirect=/?tier=${tier}`)
      return
    }

    // User is logged in - show upgrade/subscribe modal for ALL plans
    // Users must pay before they can create websites
    setTargetTier(tier)
    setShowUpgradeModal(true)
  }

  return (
    <div className="min-h-screen">
      <LandingNav user={user} loading={loading} onLogout={handleLogout} />
      <LandingHero />
      <LandingFeatures />
      <LandingPricing onSelectPlan={handleSelectPlan} />
      <LandingFooter />

      {/* Upgrade Modal */}
      {user && (
        <UpgradeModal
          show={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
          currentTier="starter"
          targetTier={targetTier}
        />
      )}
    </div>
  )
}

export default function LandingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <LandingPageContent />
    </Suspense>
  )
}
