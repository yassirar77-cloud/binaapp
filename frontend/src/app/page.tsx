/**
 * Landing Page
 */

'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { signOut, getCurrentUser, getStoredToken } from '@/lib/supabase'
import { UpgradeModal } from '@/components/UpgradeModal'
import LandingNav from '@/components/landing/LandingNav'
import LandingHero from '@/components/landing/LandingHero'
import LandingFeatures from '@/components/landing/LandingFeatures'
import LandingShowcase from '@/components/landing/LandingShowcase'
import LandingPricing from '@/components/landing/LandingPricing'
import LandingFooter from '@/components/landing/LandingFooter'
import DownloadAppCard from '@/components/pwa/DownloadAppCard'

function LandingPageContent() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [targetTier, setTargetTier] = useState<'starter' | 'pro'>('starter')

  useEffect(() => {
    checkUser()
  }, [])

  // Handle tier parameter from redirect after login.
  //
  // Read from window.location, NOT useSearchParams(): that hook suspends the
  // component during the static build, so the server-rendered home page was
  // only the Suspense fallback ("Loading...") — no headline, no copy, nothing
  // for a crawler or a link preview to read.
  useEffect(() => {
    if (!loading && user) {
      const tier = new URLSearchParams(window.location.search).get('tier')
      if (tier === 'starter' || tier === 'pro') {
        // Clear the URL parameter
        router.replace('/', { scroll: false })
        // Open the upgrade modal or redirect
        handleSelectPlan(tier)
      }
    }
  }, [loading, user])

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

  function handleSelectPlan(tier: 'starter' | 'pro') {
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
      <LandingShowcase />
      <LandingPricing onSelectPlan={handleSelectPlan} />
      <DownloadAppCard
        appName="BinaApp"
        tagline="Urus order & delivery terus dari phone"
        iconSrc="/icons/icon-192x192.png"
      />
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
  return <LandingPageContent />
}
