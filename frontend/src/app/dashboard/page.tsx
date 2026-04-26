/**
 * Dashboard Page - Project Management
 * Redesigned with new dark-theme dashboard components (B1–B5)
 */

'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Sparkles, Truck, MapPin } from 'lucide-react'
import { API_BASE_URL } from '@/lib/env'
import { supabase, getStoredToken, getCurrentUser } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { SubscriptionExpiredBanner } from '@/components/SubscriptionExpiredBanner'
import { LimitReachedModal } from '@/components/LimitReachedModal'
// New dashboard components
import DashboardHeader from '@/components/dashboard-new/DashboardHeader'
import DashboardGreeting from '@/components/dashboard-new/DashboardGreeting'
import DashboardFooter from '@/components/dashboard-new/DashboardFooter'
import HeroStats, {
  type SalesData,
  type OrdersData,
  type CommissionData,
} from '@/components/dashboard-new/HeroStats'
import PrimaryActions, { type ActionItem } from '@/components/dashboard-new/PrimaryActions'
import WebsitesSection, { type WebsiteItem } from '@/components/dashboard-new/WebsitesSection'
import ActivityFeed, { type ActivityEvent } from '@/components/dashboard-new/ActivityFeed'
import DashboardUsageWidget from '@/components/dashboard-new/DashboardUsageWidget'
import MobileDashboard, { type MobileStat } from '@/components/dashboard-new/MobileDashboard'
import '@/components/dashboard-new/dashboard.css'

interface Project {
  id: string
  name: string
  subdomain: string
  url: string
  created_at: string
  published_at?: string
  published_url?: string
}

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [showLimitModal, setShowLimitModal] = useState(false)
  const [limitModalData, setLimitModalData] = useState({
    resourceType: 'website' as 'website' | 'menu_item' | 'ai_hero' | 'ai_image' | 'zone' | 'rider',
    currentUsage: 0,
    limit: 0,
    canBuyAddon: false,
    addonPrice: 0
  })
  const [planLimit, setPlanLimit] = useState(1)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    if (!supabase) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError('')

    try {
      // Auth check — aligned with /my-projects pattern
      const token = getStoredToken()
      const currentUser = await getCurrentUser()

      if (!token || !currentUser) {
        router.push('/login')
        return
      }

      setUser(currentUser as User)

      // Fetch projects directly from Supabase
      const { data, error: supabaseError } = await supabase
        .from('websites')
        .select('*')
        .eq('user_id', currentUser.id)
        .order('created_at', { ascending: false })

      if (supabaseError) {
        console.error('Error fetching projects:', supabaseError)
        throw new Error('Failed to load projects')
      }

      // Transform to Project interface
      const transformedProjects: Project[] = (data || []).map((website: any) => ({
        id: website.id,
        name: website.name || 'Untitled Project',
        subdomain: website.subdomain || '',
        url: website.published_url || `https://${website.subdomain}.binaapp.my`,
        created_at: website.created_at,
        published_at: website.updated_at,
        published_url: website.published_url
      }))

      setProjects(transformedProjects)

      // Fetch plan limit for dashboard display (non-critical)
      try {
        const { data: planData } = await supabase
          .from('subscriptions')
          .select('subscription_plans(websites_limit)')
          .eq('user_id', currentUser.id)
          .eq('status', 'active')
          .order('created_at', { ascending: false })
          .limit(1)
          .single()

        if (planData?.subscription_plans) {
          const sp = planData.subscription_plans as any
          const wl = Array.isArray(sp) ? sp[0]?.websites_limit : sp?.websites_limit
          if (typeof wl === 'number') setPlanLimit(wl)
        }
      } catch {
        // Non-critical — planLimit stays at default
      }
    } catch (err: any) {
      console.error('Load projects error:', err)
      setError(err.message || 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (projectId: string) => {
    if (!confirm('Are you sure you want to delete this project?')) return
    if (!supabase) return

    setDeleting(projectId)
    setError('')

    try {
      const { error: deleteError } = await supabase
        .from('websites')
        .delete()
        .eq('id', projectId)

      if (deleteError) throw deleteError

      // Remove from list
      setProjects(projects.filter(p => p.id !== projectId))
      setDeleteConfirm(null)
    } catch (err: any) {
      console.error('Delete error:', err)
      setError(err.message || 'Failed to delete project')
    } finally {
      setDeleting(null)
    }
  }

  const handleLogout = async () => {
    if (!supabase) return
    try {
      await supabase.auth.signOut()
      setUser(null)
      router.push('/')
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  const handleCreateWebsiteClick = async () => {
    if (!supabase || !user) {
      router.push('/create')
      return
    }

    try {
      // Count actual websites (source of truth)
      const { count: actualCount } = await supabase
        .from('websites')
        .select('id', { count: 'exact', head: true })
        .eq('user_id', user.id)

      // Get plan limit
      const { data: subData } = await supabase
        .from('subscriptions')
        .select('subscription_plans(websites_limit)')
        .eq('user_id', user.id)
        .eq('status', 'active')
        .order('created_at', { ascending: false })
        .limit(1)
        .single()

      const limit = subData?.subscription_plans?.websites_limit ?? 1

      // Unlimited plan
      if (limit === null) {
        router.push('/create')
        return
      }

      // Get addon credits
      const { data: addons } = await supabase
        .from('addon_purchases')
        .select('quantity_remaining')
        .eq('user_id', user.id)
        .eq('addon_type', 'website')
        .eq('status', 'active')
        .gt('quantity_remaining', 0)

      const addonCredits = (addons || []).reduce((sum: number, a: any) => sum + a.quantity_remaining, 0)
      const totalAllowed = limit + addonCredits

      if ((actualCount ?? 0) >= totalAllowed) {
        setLimitModalData({
          resourceType: 'website',
          currentUsage: actualCount ?? 0,
          limit: limit,
          canBuyAddon: true,
          addonPrice: 5
        })
        setShowLimitModal(true)
        return // DO NOT navigate to /create
      }

      // Safe to proceed
      router.push('/create')
    } catch (err) {
      console.error('Limit check failed:', err)
      router.push('/create') // Fail open (backend will still block)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-MY', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    } catch {
      return 'Unknown'
    }
  }

  // ── Data mapping for new dashboard components ──

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Pengguna'
  const businessName = projects[0]?.name || 'Perniagaan Anda'

  // Map projects → WebsiteItem for new components
  const websiteItems: WebsiteItem[] = projects.map((p) => ({
    id: p.id,
    name: p.name,
    subdomain: `${p.subdomain}.binaapp.my`,
    status: p.published_at ? 'published' : 'draft',
    orders: 0,   // TODO: wire real order counts per website
    views: '—',  // TODO: wire real analytics per website
  }))

  // TODO: Replace mock data below with real Supabase queries
  const mockSales: SalesData = {
    amount: '0',
    currencyPrefix: 'RM',
    deltaPercent: '0%',
    deltaDirection: 'up',
    barPoints: [0, 0, 0, 0, 0, 0, 0].map((v) => ({ value: v })),
    dayLabels: ['I', 'S', 'R', 'K', 'J', 'S', 'A'],
  }

  const mockOrders: OrdersData = {
    count: 0,
    statusBreakdown: [
      { label: 'Masak', count: 0, color: '#F59E0B' },
      { label: 'Hantar', count: 0, color: '#3B82F6' },
      { label: 'Siap', count: 0, color: '#22C08F' },
    ],
  }

  const mockCommission: CommissionData = {
    amount: '0',
    currencyPrefix: 'RM',
    subtitle: 'berbanding platform lain',
    calcLine1: '0% komisen · RM 0 jimat',
    calcLine2: 'vs 30% di platform lain',
    ytdLabel: 'Tahun ini',
    ytdAmount: 'RM 0',
  }

  const mockActions: ActionItem[] = [
    {
      icon: <Truck size={20} />,
      title: 'Urus Penghantaran',
      description: 'Tetapkan zon, harga, dan jadual penghantaran.',
      meta: { dotColor: '#3B82F6', label: '0 zon aktif' },
      hue: '#3B82F6',
      href: '/delivery',
    },
    {
      icon: <MapPin size={20} />,
      title: 'Penghantar Live',
      description: 'Pantau lokasi penghantar secara real-time.',
      meta: { dotColor: '#22C08F', label: '0 penghantar', pulse: true },
      hue: '#22C08F',
      href: '/riders',
    },
    {
      icon: <Sparkles size={20} />,
      title: 'Reka Menu AI',
      description: 'Jana menu cantik secara automatik dengan AI.',
      meta: { dotColor: '#C7FF3D', label: 'AI sedia' },
      hue: '#C7FF3D',
      href: '/create',
      featured: true,
    },
  ]

  // TODO: Wire real activity events from order/website tables
  const mockActivityEvents: ActivityEvent[] = []

  const mobileStats: [MobileStat, MobileStat, MobileStat, MobileStat] = [
    { label: 'Jualan Hari Ini', value: 'RM 0', delta: { text: '0%', color: '#C7FF3D', icon: 'up' } },
    { label: 'Pesanan Baru', value: '0', pulse: true },
    { label: 'Komisen Dijimatkan', value: 'RM 0', featured: true },
    { label: 'Website Aktif', value: String(projects.length) },
  ]

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">Please Log In</h1>
          <Link href="/login" className="text-primary-600 hover:underline">
            Log In
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="dash-bg min-h-screen relative">
      {/* Ambient background effects */}
      <div className="dash-dotgrid" />
      <div className="dash-glow-top" />
      <div className="dash-glow-accent" />

      {/* Subscription Expired Banner — preserved */}
      <SubscriptionExpiredBanner />

      {/* New dark header */}
      <DashboardHeader
        userName={displayName}
        newOrdersCount={0}
        notificationCount={0}
        onLogout={handleLogout}
      />

      {/* Error message — preserved */}
      {error && (
        <div className="relative z-10 mx-auto max-w-7xl px-4 lg:px-6 mt-4">
          <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-red-400 text-sm">
            {error}
          </div>
        </div>
      )}

      {/* ── Mobile layout (below md breakpoint) ── */}
      <MobileDashboard
        userName={displayName}
        businessName={businessName}
        ordersCount={0}
        stats={mobileStats}
        actions={mockActions}
        websites={websiteItems}
        activityEvents={mockActivityEvents}
        deleteConfirmId={deleteConfirm}
        deletingId={deleting}
        onCreateNew={handleCreateWebsiteClick}
        onView={(w) => window.open(`https://${w.subdomain}`, '_blank')}
        onEdit={(w) => router.push(`/edit/${w.id}`)}
        onDelete={(id) => setDeleteConfirm(id)}
        onDeleteConfirm={(id) => handleDelete(id)}
        onDeleteCancel={() => setDeleteConfirm(null)}
        onUpgradeClick={() => router.push('/dashboard/billing')}
        onRenewClick={() => router.push('/dashboard/billing')}
        onLogout={handleLogout}
      />

      {/* ── Desktop layout (md and up) ── */}
      <main className="hidden md:block relative z-10 mx-auto max-w-7xl px-6 pb-12">
        <DashboardGreeting userName={displayName} businessName={businessName} />

        <HeroStats
          sales={mockSales}
          orders={mockOrders}
          commission={mockCommission}
          websites={{
            active: projects.length,
            limit: planLimit,
            planName: 'Semasa',
            onCreateNew: handleCreateWebsiteClick,
            onUpgradePlan: () => router.push('/dashboard/billing'),
          }}
        />

        <PrimaryActions actions={mockActions} />

        <WebsitesSection
          websites={websiteItems}
          planLimit={planLimit}
          deleteConfirmId={deleteConfirm}
          deletingId={deleting}
          onCreateNew={handleCreateWebsiteClick}
          onView={(w) => window.open(`https://${w.subdomain}`, '_blank')}
          onEdit={(w) => router.push(`/edit/${w.id}`)}
          onDelete={(id) => setDeleteConfirm(id)}
          onDeleteConfirm={(id) => handleDelete(id)}
          onDeleteCancel={() => setDeleteConfirm(null)}
        />

        {/* TODO: Wire real activity events */}
        {mockActivityEvents.length > 0 && (
          <section className="mb-10">
            <h2 className="font-geist font-semibold text-lg text-white tracking-[-0.02em] mb-4">
              Aktiviti terkini
            </h2>
            <ActivityFeed events={mockActivityEvents} />
          </section>
        )}

        <DashboardFooter />
      </main>

      {/* Usage widget — desktop only (mobile has its own inline copy in MobileDashboard) */}
      <div className="hidden md:block">
        <DashboardUsageWidget
          onUpgradeClick={() => router.push('/dashboard/billing')}
          onRenewClick={() => router.push('/dashboard/billing')}
        />
      </div>

      {/* Limit Reached Modal — preserved verbatim */}
      <LimitReachedModal
        show={showLimitModal}
        onClose={() => setShowLimitModal(false)}
        resourceType={limitModalData.resourceType}
        currentUsage={limitModalData.currentUsage}
        limit={limitModalData.limit}
        canBuyAddon={limitModalData.canBuyAddon}
        addonPrice={limitModalData.addonPrice}
      />
    </div>
  )
}
