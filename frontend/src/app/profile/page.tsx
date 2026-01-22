'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase, getCurrentUser, getStoredToken, signOut as customSignOut } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import dynamic from 'next/dynamic'

// Dynamically import chat dashboard to avoid SSR issues
const OwnerChatDashboard = dynamic(() => import('@/components/OwnerChatDashboard'), { ssr: false })

// Backend API URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

export default function ProfilePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [authChecking, setAuthChecking] = useState(true) // NEW: Separate auth checking state
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState({ full_name: '', business_name: '', phone: '' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [websites, setWebsites] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [riders, setRiders] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'websites' | 'orders' | 'riders' | 'chat'>('websites')
  const [loadingOrders, setLoadingOrders] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [chatEnabled, setChatEnabled] = useState(true) // Default to true - API is working
  const [chatLoading, setChatLoading] = useState(true)
  const [showAddRider, setShowAddRider] = useState(false)
  const [editingRider, setEditingRider] = useState<any>(null)
  const [deletingWebsite, setDeletingWebsite] = useState<string | null>(null)

  // Helper function to load data using custom BinaApp token
  async function loadDataWithCustomToken(token: string, userId: string) {
    try {
      // Load websites from backend API
      const websitesResponse = await fetch(`${API_BASE}/api/v1/websites/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (websitesResponse.ok) {
        const websitesData = await websitesResponse.json()
        // Map API response to expected format
        const mappedWebsites = websitesData.map((w: any) => ({
          ...w,
          name: w.business_name // Map business_name to name for compatibility
        }))
        setWebsites(mappedWebsites || [])
        console.log('[Profile] ✅ Loaded websites via API:', mappedWebsites?.length)
      } else {
        console.error('[Profile] Failed to load websites:', websitesResponse.status)
        setWebsites([])
      }

      // Try to load profile from Supabase if available (for profile form)
      if (supabase) {
        try {
          const { data: profileData } = await supabase
            .from('profiles')
            .select('*')
            .eq('id', userId)
            .maybeSingle()

          if (profileData) {
            setProfile({
              full_name: profileData.full_name || '',
              business_name: profileData.business_name || '',
              phone: profileData.phone || ''
            })
          }
        } catch (e) {
          console.log('[Profile] Could not load profile from Supabase:', e)
        }
      }
    } catch (error) {
      console.error('[Profile] Error loading data with custom token:', error)
    }
  }

  // Load Eruda console for mobile debugging
  useEffect(() => {
    if (typeof window !== 'undefined' && /mobile/i.test(navigator.userAgent)) {
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/eruda'
      document.body.appendChild(script)
      script.onload = () => {
        (window as any).eruda.init()
        console.log('[Eruda] Mobile console initialized! Tap the floating button in bottom-right corner.')
      }
    }
  }, [])

  useEffect(() => {
    loadUserData()
  }, [])

  // Set up auth state listener for mobile browsers
  // NOTE: Only listen for Supabase events, don't auto-redirect on SIGNED_OUT
  // because we use custom BinaApp token which Supabase doesn't know about
  useEffect(() => {
    if (!supabase) return

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('[Profile] Auth event:', event, 'Has session:', !!session)

        // Don't redirect on SIGNED_OUT - check custom token first
        if (event === 'SIGNED_OUT') {
          // Check if we have a custom BinaApp token
          const customToken = getStoredToken()
          if (!customToken) {
            setAuthChecking(false)
            setUser(null)
            router.push('/login')
          }
          // If we have custom token, don't redirect
        } else if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
          if (session?.user) {
            setUser(session.user)
            setAuthChecking(false) // Auth successful!
            // Reload data after sign in
            loadUserData()
          }
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [supabase, router])

  useEffect(() => {
    if (user && websites.length > 0) {
      loadOrders()
      loadRiders()
    }
  }, [user, websites])

  // Check if chat API is working when chat tab is active
  useEffect(() => {
    if (activeTab === 'chat' && websites.length > 0) {
      checkChatApi()
    }
  }, [activeTab, websites])

  async function checkChatApi() {
    try {
      setChatLoading(true)
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'
      const session = supabase ? await supabase.auth.getSession() : null
      const accessToken = session?.data.session?.access_token

      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`
      }

      const response = await fetch(`${apiUrl}/api/v1/chat/conversations`, { headers })

      if (response.ok) {
        setChatEnabled(true) // API works = chat enabled
        console.log('[Chat] API is working ✅')
      } else {
        setChatEnabled(false)
        console.log('[Chat] API returned error:', response.status)
      }
    } catch (error) {
      console.error('[Chat] API check failed:', error)
      setChatEnabled(false)
    } finally {
      setChatLoading(false)
    }
  }

  async function loadUserData() {
    try {
      setLoading(true)
      setAuthChecking(true)

      console.log('[Profile] Loading user data...')

      // First check for custom BinaApp token
      const customToken = getStoredToken()
      const customUser = await getCurrentUser()

      console.log('[Profile] Custom auth check:', {
        hasToken: !!customToken,
        hasUser: !!customUser
      })

      // If we have custom token + user, use that
      if (customToken && customUser) {
        console.log('[Profile] ✅ Using custom BinaApp auth')
        // Create a mock user object compatible with Supabase User type
        const mockUser = {
          id: customUser.id,
          email: customUser.email,
          user_metadata: { full_name: customUser.full_name }
        } as User
        setUser(mockUser)
        setAuthChecking(false)

        // Load profile and websites using custom token via backend API
        await loadDataWithCustomToken(customToken, customUser.id)
        setLoading(false)
        return
      }

      // Fallback to Supabase session
      if (!supabase) {
        console.log('[Profile] No Supabase client and no custom token')
        setAuthChecking(false)
        setLoading(false)
        router.push('/login')
        return
      }

      // Small delay to ensure session is hydrated (especially on mobile)
      await new Promise(resolve => setTimeout(resolve, 300))

      const { data: { session }, error: sessionError } = await supabase.auth.getSession()

      console.log('[Profile] Supabase session check:', {
        hasSession: !!session,
        email: session?.user?.email,
        error: sessionError?.message
      })

      if (sessionError) {
        console.error('[Profile] Session error:', sessionError)
        setAuthChecking(false)
        setLoading(false)
        router.push('/login')
        return
      }

      if (!session?.user) {
        console.log('[Profile] No session found, redirecting to login')
        setAuthChecking(false)
        setLoading(false)
        router.push('/login')
        return
      }

      // SUCCESS: We have a valid Supabase session
      console.log('[Profile] ✅ Supabase session valid:', session.user.email)
      setUser(session.user)
      setAuthChecking(false)

      const currentUser = session?.user
      if (!currentUser) {
        console.log('[Profile] ERROR: currentUser is null after session check!')
        setLoading(false)
        return
      }

      console.log('[Profile] Loading data for user:', currentUser.email)

      // Load profile
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', currentUser.id)
        .maybeSingle()

      if (profileData) {
        setProfile({
          full_name: profileData.full_name || '',
          business_name: profileData.business_name || '',
          phone: profileData.phone || ''
        })
      }

      // Load websites
      console.log('[DEBUG] Current user ID:', currentUser.id)
      const { data: websitesData } = await supabase
        .from('websites')
        .select('*')
        .eq('user_id', currentUser.id)
        .order('created_at', { ascending: false })

      console.log('[DEBUG] Loaded websites:', websitesData?.map(w => ({
        id: w.id,
        name: w.name || w.business_name,
        subdomain: w.subdomain,
        user_id: w.user_id
      })))

      setWebsites(websitesData || [])
    } catch (error) {
      console.error('Error loading user data:', error)
    } finally {
      setLoading(false)
    }
  }

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault()
    if (!supabase || !user) return

    setSaving(true)
    try {
      await supabase.from('profiles').upsert({
        id: user.id,
        email: user.email,
        ...profile,
        updated_at: new Date().toISOString()
      })
      setMsg('✅ Disimpan!')
      setTimeout(() => setMsg(''), 3000)
    } catch (error) {
      console.error('Error saving profile:', error)
      setMsg('❌ Gagal simpan')
    } finally {
      setSaving(false)
    }
  }

  async function handleLogout() {
    // Clear custom BinaApp token
    await customSignOut()
    // Also clear Supabase session if available
    if (supabase) {
      await supabase.auth.signOut()
    }
    router.push('/')
  }

  async function handleDeleteWebsite(websiteId: string, websiteName: string) {
    // First confirmation
    const confirmed = window.confirm(
      `AMARAN: Adakah anda pasti mahu memadam "${websiteName}"?\n\n` +
      `Tindakan ini akan MEMADAM KEKAL:\n` +
      `- Website dan semua kandungan\n` +
      `- Semua menu items\n` +
      `- Semua riders\n` +
      `- Semua delivery zones & settings\n` +
      `- Semua pesanan dan chat\n\n` +
      `TINDAKAN INI TIDAK BOLEH DIBATALKAN!`
    )

    if (!confirmed) return

    // Double confirmation - type DELETE
    const confirmText = prompt(`Taip "DELETE" untuk mengesahkan pemadaman "${websiteName}":`)
    if (confirmText !== 'DELETE') {
      alert('Dibatalkan. Website tidak dipadam.')
      return
    }

    try {
      setDeletingWebsite(websiteId)

      // Get session token
      const { data: { session } } = await supabase.auth.getSession()

      if (!session) {
        alert('Sesi tamat. Sila log masuk semula.')
        router.push('/login')
        return
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/websites/${websiteId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          }
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Gagal memadam website')
      }

      const result = await response.json()

      // Success!
      alert(`Website "${websiteName}" berjaya dipadam!`)

      // Reload websites list
      setWebsites(websites.filter(w => w.id !== websiteId))

    } catch (error: any) {
      console.error('[Delete Website] Error:', error)
      alert(`Ralat memadam website: ${error.message}\n\nSila cuba lagi atau hubungi sokongan.`)
    } finally {
      setDeletingWebsite(null)
    }
  }

  async function loadOrders() {
    if (!supabase || websites.length === 0) return

    setLoadingOrders(true)
    try {
      const websiteIds = websites.map(w => w.id)

      const { data, error } = await supabase
        .from('delivery_orders')
        .select(`
          *,
          order_items (
            id,
            item_name,
            quantity,
            unit_price,
            total_price
          )
        `)
        .in('website_id', websiteIds)
        .order('created_at', { ascending: false })

      if (error) {
        console.error('Error loading orders:', error)
        // Check if it's an auth error
        if (error.message?.includes('JWT') || error.message?.includes('token')) {
          console.error('Auth token expired, redirecting to login...')
          await supabase.auth.signOut()
          router.push('/login')
          return
        }
      } else {
        setOrders(data || [])
        console.log(`✅ Loaded ${data?.length || 0} orders`)
      }
    } catch (error) {
      console.error('Error loading orders:', error)
    } finally {
      setLoadingOrders(false)
    }
  }

  async function loadRiders() {
    if (!supabase || websites.length === 0) {
      console.log('[DEBUG] loadRiders SKIPPED - supabase:', !!supabase, 'websites.length:', websites.length)
      return
    }

    try {
      console.log('=== LOADING RIDERS DEBUG START ===')

      // DEBUG: Log all websites
      console.log('[DEBUG] All websites:', websites.map(w => ({
        id: w.id,
        name: w.name || w.business_name,
        subdomain: w.subdomain
      })))

      // Get the session token for authentication
      const { data: { session } } = await supabase.auth.getSession()

      if (!session) {
        console.error('[Riders] No session available')
        return
      }

      console.log('[DEBUG] Session user:', session.user?.email)

      // FIX: Load riders for ALL websites, not just the first one
      // This fixes the bug where riders weren't showing if the user had multiple websites
      const allRiders: any[] = []

      for (const website of websites) {
        const apiUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/delivery/admin/websites/${website.id}/riders`
        console.log(`[DEBUG] Fetching riders for website_id: ${website.id}`)
        console.log(`[DEBUG] Website name: ${website.name || website.business_name}`)
        console.log(`[DEBUG] API URL: ${apiUrl}`)

        const response = await fetch(
          apiUrl,
          {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
              'Content-Type': 'application/json'
            }
          }
        )

        console.log(`[DEBUG] Response status for website ${website.id}:`, response.status)

        if (response.ok) {
          const data = await response.json()
          console.log(`[DEBUG] Response data for website ${website.id}:`, data)
          console.log(`✅ Loaded ${data?.length || 0} riders for website ${website.name || website.business_name}`)

          if (data && data.length > 0) {
            console.log(`[DEBUG] Riders from website ${website.id}:`, data.map((r: any) => ({
              id: r.id,
              name: r.name,
              website_id: r.website_id
            })))

            // Add riders to the list, avoiding duplicates
            for (const rider of data) {
              if (!allRiders.find(r => r.id === rider.id)) {
                allRiders.push(rider)
                console.log(`[DEBUG] Added rider: ${rider.name} (ID: ${rider.id})`)
              } else {
                console.log(`[DEBUG] Skipped duplicate rider: ${rider.name}`)
              }
            }
          } else {
            console.log(`[DEBUG] No riders found for website ${website.id}`)
          }
        } else {
          const errorText = await response.text()
          console.error(`❌ Error loading riders for website ${website.id}:`, response.status, errorText)
        }
      }

      console.log(`[DEBUG] Setting riders state with ${allRiders.length} riders`)
      setRiders(allRiders)
      console.log(`✅ Total riders loaded: ${allRiders.length}`)
      console.log('[DEBUG] Final rider details:', allRiders.map(r => ({
        id: r.id,
        name: r.name,
        website_id: r.website_id
      })))
      console.log('=== LOADING RIDERS DEBUG END ===')
    } catch (error) {
      console.error('❌ Error loading riders:', error)
      console.error('[DEBUG] Error stack:', error instanceof Error ? error.stack : 'No stack trace')
    }
  }

  async function confirmOrder(orderId: string) {
    if (!supabase) return

    try {
      const { data, error } = await supabase
        .from('delivery_orders')
        .update({
          status: 'confirmed',
          confirmed_at: new Date().toISOString()
        })
        .eq('id', orderId)
        .select()

      if (error) {
        console.error('Error confirming order:', error)
        console.error('Error details:', JSON.stringify(error, null, 2))
        alert(`❌ Gagal mengesahkan pesanan\n\nError: ${error.message}\n\nCode: ${error.code}\n\nSila check console untuk details.`)

        // Check if it's an RLS/permission error
        if (error.code === 'PGRST301' || error.message?.includes('policy')) {
          alert('⚠️ RLS Policy Issue: Sila run migration 006_fix_owner_orders_access.sql di Supabase SQL Editor')
        }
      } else {
        console.log('✅ Order confirmed successfully:', data)
        alert('✅ Pesanan disahkan!')
        loadOrders()
      }
    } catch (error: any) {
      console.error('Error confirming order:', error)
      alert(`❌ Gagal mengesahkan pesanan\n\nError: ${error?.message || 'Unknown error'}\n\nSila check console.`)
    }
  }

  async function rejectOrder(orderId: string) {
    if (!supabase) return

    const reason = prompt('Sebab menolak pesanan:')
    if (!reason) return

    try {
      const { data, error } = await supabase
        .from('delivery_orders')
        .update({
          status: 'cancelled',
          cancelled_at: new Date().toISOString()
        })
        .eq('id', orderId)
        .select()

      if (error) {
        console.error('Error rejecting order:', error)
        console.error('Error details:', JSON.stringify(error, null, 2))
        alert(`❌ Gagal menolak pesanan\n\nError: ${error.message}`)
      } else {
        console.log('✅ Order rejected successfully:', data)
        alert('✅ Pesanan ditolak')
        loadOrders()
      }
    } catch (error: any) {
      console.error('Error rejecting order:', error)
      alert(`❌ Gagal menolak pesanan\n\nError: ${error?.message || 'Unknown error'}`)
    }
  }

  async function assignRider(orderId: string, riderId: string) {
    if (!supabase) return

    try {
      const { data, error } = await supabase
        .from('delivery_orders')
        .update({
          status: 'assigned',
          rider_id: riderId
        })
        .eq('id', orderId)
        .select()

      if (error) {
        console.error('Error assigning rider:', error)
        console.error('Error details:', JSON.stringify(error, null, 2))
        alert(`❌ Gagal assign rider\n\nError: ${error.message}`)
      } else {
        console.log('✅ Rider assigned successfully:', data)
        alert('✅ Rider ditetapkan!')
        loadOrders()
      }
    } catch (error: any) {
      console.error('Error assigning rider:', error)
      alert(`❌ Gagal assign rider\n\nError: ${error?.message || 'Unknown error'}`)
    }
  }

  function getStatusBadge(status: string) {
    const badges: { [key: string]: { label: string; color: string } } = {
      pending: { label: 'Menunggu Pengesahan', color: 'bg-yellow-100 text-yellow-800' },
      confirmed: { label: 'Disahkan', color: 'bg-blue-100 text-blue-800' },
      assigned: { label: 'Rider Ditetapkan', color: 'bg-purple-100 text-purple-800' },
      preparing: { label: 'Sedang Disediakan', color: 'bg-orange-100 text-orange-800' },
      ready: { label: 'Sedia untuk Pickup', color: 'bg-teal-100 text-teal-800' },
      picked_up: { label: 'Dipickup Rider', color: 'bg-indigo-100 text-indigo-800' },
      delivering: { label: 'Sedang Dihantar', color: 'bg-blue-100 text-blue-800' },
      delivered: { label: 'Telah Dihantar', color: 'bg-green-100 text-green-800' },
      completed: { label: 'Selesai', color: 'bg-green-100 text-green-800' },
      cancelled: { label: 'Dibatalkan', color: 'bg-red-100 text-red-800' }
    }
    const badge = badges[status] || { label: status, color: 'bg-gray-100 text-gray-800' }
    return <span className={`px-3 py-1 rounded-full text-xs font-medium ${badge.color}`}>{badge.label}</span>
  }

  // Rider Form Component
  function AddRiderForm({ websiteId, editData, onSuccess, onCancel }: any) {
    const [formData, setFormData] = useState(editData || {
      name: '',
      email: '',
      phone: '',
      password: '',
      vehicle_type: 'motorcycle',
      vehicle_plate: '',
      vehicle_model: '',
      is_active: true
    })
    const [loading, setLoading] = useState(false)

    async function handleSubmit(e: React.FormEvent) {
      e.preventDefault()
      setLoading(true)

      try {
        // Get the session token for authentication
        const { data: { session } } = await supabase.auth.getSession()

        if (!session) {
          alert('Sila log masuk semula')
          return
        }

        const url = editData
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1/delivery/riders/${editData.id}`
          : `${process.env.NEXT_PUBLIC_API_URL}/api/v1/delivery/admin/websites/${websiteId}/riders`

        const method = editData ? 'PUT' : 'POST'

        // Filter out empty password when editing (only include if user wants to change it)
        const submitData = editData && !formData.password
          ? { ...formData, password: undefined }
          : formData

        const response = await fetch(url, {
          method,
          headers: {
            'Authorization': `Bearer ${(await supabase?.auth.getSession())?.data.session?.access_token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(submitData)
        })

        if (response.ok) {
          alert(editData ? 'Rider dikemaskini!' : 'Rider berjaya ditambah!')
          onSuccess()
        } else {
          const error = await response.json()
          alert('Gagal: ' + (error.detail || 'Sila cuba lagi'))
        }
      } catch (error) {
        console.error('Error:', error)
        alert('Ralat sistem. Sila cuba lagi.')
      } finally {
        setLoading(false)
      }
    }

    return (
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-lg p-6 space-y-4">
        <h3 className="text-xl font-bold text-gray-900 mb-4">
          {editData ? '✏️ Edit Rider' : '➕ Tambah Rider Baru'}
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nama Penuh *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="Ahmad bin Ali"
            />
          </div>

          {/* Phone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              No. Telefon *
            </label>
            <input
              type="tel"
              required
              value={formData.phone}
              onChange={(e) => setFormData({...formData, phone: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="0123456789"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email (pilihan)
            </label>
            <input
              type="email"
              value={formData.email || ''}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="rider@example.com"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Kata Laluan {editData ? '(kosongkan jika tidak mahu tukar)' : '*'}
            </label>
            <input
              type="password"
              required={!editData}
              value={formData.password || ''}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder={editData ? "Masukkan kata laluan baru" : "Min 6 aksara"}
              minLength={6}
            />
            <p className="mt-1 text-xs text-gray-500">
              Rider akan guna kata laluan ini untuk login di binaapp.my/rider
            </p>
          </div>

          {/* Vehicle Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Jenis Kenderaan *
            </label>
            <select
              required
              value={formData.vehicle_type}
              onChange={(e) => setFormData({...formData, vehicle_type: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="motorcycle">🏍️ Motosikal</option>
              <option value="car">🚗 Kereta</option>
              <option value="bicycle">🚲 Basikal</option>
              <option value="scooter">🛴 Skuter</option>
            </select>
          </div>

          {/* Vehicle Plate */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              No. Plat Kenderaan *
            </label>
            <input
              type="text"
              required
              value={formData.vehicle_plate}
              onChange={(e) => setFormData({...formData, vehicle_plate: e.target.value.toUpperCase()})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="ABC1234"
            />
          </div>

          {/* Vehicle Model */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Model Kenderaan (pilihan)
            </label>
            <input
              type="text"
              value={formData.vehicle_model || ''}
              onChange={(e) => setFormData({...formData, vehicle_model: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              placeholder="Honda Wave 125"
            />
          </div>

          {/* Active Status */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
              className="w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500"
            />
            <label htmlFor="is_active" className="ml-2 text-sm font-medium text-gray-700">
              Aktif (boleh terima pesanan)
            </label>
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 bg-orange-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-orange-700 disabled:opacity-50 min-h-[44px]"
          >
            {loading ? 'Menyimpan...' : (editData ? 'Kemaskini' : 'Tambah Rider')}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50 min-h-[44px]"
          >
            Batal
          </button>
        </div>
      </form>
    )
  }

  // Show loading while checking authentication
  if (loading || authChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600 text-sm font-medium">
            {authChecking ? 'Memeriksa pengesahan...' : 'Memuatkan data...'}
          </p>
          <p className="text-gray-400 text-xs mt-2">Sila tunggu sebentar</p>
        </div>
      </div>
    )
  }

  // Only show "Sila Log Masuk" if auth check is complete AND no user
  // Note: Middleware should have already redirected, but this is a fallback
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="text-6xl mb-4">🔒</div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Sesi Tamat</h1>
          <p className="text-gray-600 text-sm mb-6">Sila log masuk semula untuk teruskan</p>
          <Link
            href="/login"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium min-h-[44px] transition-colors"
          >
            Log Masuk
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header - Mobile Responsive */}
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <span className="text-xl font-bold">BinaApp</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-4">
            <Link href="/my-projects" className="text-sm text-gray-600 hover:text-gray-900">
              Website Saya
            </Link>
            <Link href="/create" className="text-sm text-gray-600 hover:text-gray-900">
              Bina Website
            </Link>
            <button onClick={handleLogout} className="text-sm text-red-500 hover:text-red-600">
              Log Keluar
            </button>
          </div>

          {/* Mobile Hamburger Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-gray-600 hover:text-gray-900 focus:outline-none"
            aria-label="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {mobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </nav>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t bg-white">
            <div className="flex flex-col py-2">
              <Link
                href="/my-projects"
                className="px-4 py-3 text-sm text-gray-600 hover:bg-gray-50 active:bg-gray-100"
                onClick={() => setMobileMenuOpen(false)}
              >
                Website Saya
              </Link>
              <Link
                href="/create"
                className="px-4 py-3 text-sm text-gray-600 hover:bg-gray-50 active:bg-gray-100"
                onClick={() => setMobileMenuOpen(false)}
              >
                Bina Website
              </Link>
              <button
                onClick={() => {
                  setMobileMenuOpen(false)
                  handleLogout()
                }}
                className="px-4 py-3 text-sm text-red-500 hover:bg-gray-50 active:bg-gray-100 text-left"
              >
                Log Keluar
              </button>
            </div>
          </div>
        )}
      </header>

      <div className="py-6 md:py-12">
        <div className="max-w-4xl mx-auto px-4">
          {/* Profile Section */}
          <div className="bg-white rounded-xl shadow-lg p-4 md:p-8 mb-6 md:mb-8">
            <h1 className="text-2xl md:text-3xl font-bold mb-4 md:mb-6">👤 Profil Saya</h1>
            {msg && (
              <div className={`p-4 rounded-lg mb-6 ${msg.includes('✅') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {msg}
              </div>
            )}
            <form onSubmit={saveProfile} className="space-y-4 md:space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input type="email" value={user.email || ''} disabled className="w-full p-3 bg-gray-100 rounded-lg border text-sm md:text-base" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nama Penuh</label>
                <input
                  type="text"
                  value={profile.full_name}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  placeholder="Nama anda"
                  className="w-full p-3 border rounded-lg text-sm md:text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nama Perniagaan</label>
                <input
                  type="text"
                  value={profile.business_name}
                  onChange={(e) => setProfile({ ...profile, business_name: e.target.value })}
                  placeholder="Nama perniagaan"
                  className="w-full p-3 border rounded-lg text-sm md:text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nombor Telefon</label>
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  placeholder="01X-XXX XXXX"
                  className="w-full p-3 border rounded-lg text-sm md:text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button type="submit" disabled={saving} className="w-full py-3 md:py-3 min-h-[44px] bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium disabled:opacity-50 active:bg-blue-700 transition-colors">
                {saving ? 'Menyimpan...' : '💾 Simpan Profil'}
              </button>
            </form>
          </div>

          {/* Tabs Navigation */}
          <div className="bg-white rounded-xl shadow-lg p-4 md:p-8">
            {/* Mobile-friendly scrollable tabs */}
            <div className="flex gap-2 mb-6 border-b overflow-x-auto scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0">
              <button
                onClick={() => setActiveTab('websites')}
                className={`px-4 md:px-6 py-3 font-medium transition-colors whitespace-nowrap text-sm md:text-base min-h-[44px] ${
                  activeTab === 'websites'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                🌐 <span className="hidden sm:inline">Website Saya </span>({websites.length})
              </button>
              <button
                onClick={() => setActiveTab('orders')}
                className={`px-4 md:px-6 py-3 font-medium transition-colors whitespace-nowrap text-sm md:text-base min-h-[44px] ${
                  activeTab === 'orders'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                📦 <span className="hidden sm:inline">Pesanan </span>({orders.filter(o => o.status === 'pending').length})
              </button>
              <button
                onClick={() => setActiveTab('riders')}
                className={`px-4 md:px-6 py-3 font-medium transition-colors whitespace-nowrap text-sm md:text-base min-h-[44px] ${
                  activeTab === 'riders'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                🛵 <span className="hidden sm:inline">Rider </span>({riders.length})
              </button>
              <button
                onClick={() => setActiveTab('chat')}
                className={`px-4 md:px-6 py-3 font-medium transition-colors whitespace-nowrap text-sm md:text-base min-h-[44px] ${
                  activeTab === 'chat'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                💬 Chat
              </button>
            </div>

            {/* Websites Tab */}
            {activeTab === 'websites' && (
              <div>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-3">
                  <h2 className="text-xl md:text-2xl font-bold">🌐 Website Saya</h2>
                  <Link href="/create" className="w-full sm:w-auto bg-blue-500 text-white px-4 py-2.5 min-h-[44px] rounded-lg hover:bg-blue-600 active:bg-blue-700 text-sm font-medium text-center flex items-center justify-center">
                    + Bina Website Baru
                  </Link>
                </div>

                {websites.length === 0 ? (
                  <div className="text-center py-12 px-4">
                    <div className="text-4xl md:text-6xl mb-4">🌐</div>
                    <p className="text-gray-500 mb-6 text-sm md:text-base">Tiada website lagi</p>
                    <Link href="/create" className="inline-block bg-blue-500 text-white px-6 py-3 min-h-[44px] rounded-lg hover:bg-blue-600 active:bg-blue-700 text-sm md:text-base">
                      ✨ Bina Website Sekarang
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {websites.map((site) => (
                      <div key={site.id} className="border rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50 transition-colors">
                        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                          <div className="flex-1 w-full sm:w-auto">
                            <h3 className="font-semibold text-lg">{site.name}</h3>
                            {site.subdomain && (
                              <a href={`https://${site.subdomain}.binaapp.my`} target="_blank" className="text-blue-500 hover:underline text-sm">
                                {site.subdomain}.binaapp.my ↗
                              </a>
                            )}
                            <p className="text-xs text-gray-500 mt-1">Dibuat: {new Date(site.created_at).toLocaleDateString('ms-MY')}</p>
                          </div>
                          <div className="flex flex-col sm:flex-row gap-2 mt-3 sm:mt-0">
                            {site.published_url && (
                              <a href={site.published_url} target="_blank" className="bg-green-500 text-white px-4 py-2 min-h-[44px] rounded-lg hover:bg-green-600 active:bg-green-700 text-sm flex items-center justify-center">
                                👁 Lihat
                              </a>
                            )}
                            <Link href={`/editor/${site.id}`} className="bg-blue-500 text-white px-4 py-2 min-h-[44px] rounded-lg hover:bg-blue-600 active:bg-blue-700 text-sm flex items-center justify-center">
                              ✏️ Edit
                            </Link>
                            <button
                              onClick={() => handleDeleteWebsite(site.id, site.name || site.business_name)}
                              disabled={deletingWebsite === site.id}
                              className="bg-red-500 text-white px-4 py-2 min-h-[44px] rounded-lg hover:bg-red-600 active:bg-red-700 text-sm flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {deletingWebsite === site.id ? '⏳ Memadam...' : '🗑️ Padam'}
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Orders Tab */}
            {activeTab === 'orders' && (
              <div>
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-3">
                  <h2 className="text-xl md:text-2xl font-bold">📦 Pesanan</h2>
                  <button
                    onClick={loadOrders}
                    disabled={loadingOrders}
                    className="w-full sm:w-auto bg-blue-500 text-white px-4 py-2.5 min-h-[44px] rounded-lg hover:bg-blue-600 active:bg-blue-700 text-sm font-medium disabled:opacity-50"
                  >
                    {loadingOrders ? '⏳ Loading...' : '🔄 Refresh'}
                  </button>
                </div>

                {loadingOrders ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                    <p className="text-gray-500 mt-4 text-sm md:text-base">Loading orders...</p>
                  </div>
                ) : orders.length === 0 ? (
                  <div className="text-center py-12 px-4">
                    <div className="text-4xl md:text-6xl mb-4">📦</div>
                    <p className="text-gray-500 text-sm md:text-base">Tiada pesanan lagi</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {orders.map((order) => {
                      const riderInfo = riders.find(r => r.id === order.rider_id)
                      const orderWebsite = websites.find(w => w.id === order.website_id)
                      return (
                        <div key={order.id} className="border rounded-lg p-4 md:p-6 bg-white shadow-sm">
                          {/* Order Header */}
                          <div className="flex flex-col sm:flex-row justify-between items-start gap-2 mb-4">
                            <div>
                              <h3 className="text-xl font-bold text-gray-900">#{order.order_number}</h3>
                              <p className="text-sm text-gray-500">
                                {new Date(order.created_at).toLocaleString('ms-MY', {
                                  day: 'numeric',
                                  month: 'short',
                                  year: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </p>
                            </div>
                            {getStatusBadge(order.status)}
                          </div>

                          {/* Customer Info */}
                          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                            <p className="text-xs md:text-sm break-words">
                              <span className="font-medium">👤 Pelanggan:</span> {order.customer_name}
                            </p>
                            <p className="text-xs md:text-sm">
                              <span className="font-medium">📱 Telefon:</span> <a href={`tel:${order.customer_phone}`} className="text-blue-500 hover:underline">{order.customer_phone}</a>
                            </p>
                            <p className="text-xs md:text-sm break-words">
                              <span className="font-medium">📍 Alamat:</span> {order.delivery_address}
                            </p>
                            {order.delivery_notes && (
                              <p className="text-xs md:text-sm break-words">
                                <span className="font-medium">📝 Nota:</span> {order.delivery_notes}
                              </p>
                            )}
                          </div>

                          {/* Order Items */}
                          <div className="mb-4">
                            <p className="font-medium text-xs md:text-sm mb-2">🍽️ Item Pesanan:</p>
                            <div className="space-y-1">
                              {order.order_items?.map((item: any) => (
                                <div key={item.id} className="flex justify-between text-xs md:text-sm gap-2">
                                  <span className="flex-1 break-words">{item.quantity}x {item.item_name}</span>
                                  <span className="font-medium whitespace-nowrap">RM{item.total_price.toFixed(2)}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Pricing */}
                          <div className="mb-4 pt-3 border-t">
                            <div className="flex justify-between text-sm mb-1">
                              <span>Subtotal:</span>
                              <span>RM{order.subtotal.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between text-sm mb-1">
                              <span>Delivery Fee:</span>
                              <span>RM{order.delivery_fee.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between font-bold text-lg text-orange-600">
                              <span>Total:</span>
                              <span>RM{order.total_amount.toFixed(2)}</span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">Bayaran: {order.payment_method.toUpperCase()}</p>
                          </div>

                          {/* Rider Info */}
                          {order.rider_id && riderInfo && (
                            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
                              <p className="text-xs md:text-sm">
                                <span className="font-medium">🛵 Rider:</span> {riderInfo.name}
                              </p>
                              <p className="text-xs md:text-sm">
                                <span className="font-medium">📱 Telefon Rider:</span> <a href={`tel:${riderInfo.phone}`} className="text-blue-500 hover:underline">{riderInfo.phone}</a>
                              </p>
                              {riderInfo.vehicle_plate && (
                                <p className="text-xs md:text-sm">
                                  <span className="font-medium">🏍️ No Plat:</span> {riderInfo.vehicle_plate}
                                </p>
                              )}
                            </div>
                          )}

                          {/* Action Buttons */}
                          <div className="flex flex-col sm:flex-row gap-2 mt-4">
                            {order.status === 'pending' && (
                              <>
                                <button
                                  onClick={() => confirmOrder(order.id)}
                                  className="flex-1 bg-green-500 text-white px-4 py-3 min-h-[44px] rounded-lg hover:bg-green-600 active:bg-green-700 font-medium text-sm md:text-base"
                                >
                                  ✅ TERIMA PESANAN
                                </button>
                                <button
                                  onClick={() => rejectOrder(order.id)}
                                  className="flex-1 bg-red-500 text-white px-4 py-3 min-h-[44px] rounded-lg hover:bg-red-600 active:bg-red-700 font-medium text-sm md:text-base"
                                >
                                  ❌ TOLAK
                                </button>
                              </>
                            )}

                            {/* WhatsApp Quick Actions */}
                            {order.customer_phone && (
                              <a
                                href={`https://wa.me/${order.customer_phone.replace(/^0/, '60')}?text=Hi%20${encodeURIComponent(order.customer_name)},%20ini%20dari%20${encodeURIComponent(orderWebsite?.name || websites[0]?.name || 'kedai')}%20mengenai%20pesanan%20${order.order_number}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 bg-green-600 text-white px-4 py-3 min-h-[44px] rounded-lg hover:bg-green-700 active:bg-green-800 font-medium text-sm md:text-base text-center flex items-center justify-center gap-2"
                              >
                                💬 WhatsApp Customer
                              </a>
                            )}

                            {riderInfo && riderInfo.phone && (
                              <a
                                href={`https://wa.me/${riderInfo.phone.replace(/^0/, '60')}?text=Hi%20${encodeURIComponent(riderInfo.name)},%20mengenai%20order%20${order.order_number}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 bg-orange-600 text-white px-4 py-3 min-h-[44px] rounded-lg hover:bg-orange-700 active:bg-orange-800 font-medium text-sm md:text-base text-center flex items-center justify-center gap-2"
                              >
                                🛵 WhatsApp Rider
                              </a>
                            )}

                            {order.status === 'confirmed' && (
                              <div className="flex-1">
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                  🛵 Pilih Rider untuk Hantar
                                </label>
                                {riders.length === 0 ? (
                                  <p className="text-sm text-red-500">Tiada rider tersedia. Sila tambah rider dahulu.</p>
                                ) : (
                                  <select
                                    onChange={(e) => {
                                      if (e.target.value) {
                                        assignRider(order.id, e.target.value)
                                      }
                                    }}
                                    className="w-full border rounded-lg px-4 py-3 min-h-[44px] text-sm md:text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    defaultValue=""
                                  >
                                    <option value="">-- Pilih Rider --</option>
                                    {riders.map((rider) => (
                                      <option key={rider.id} value={rider.id}>
                                        {rider.name} - {rider.phone} {rider.is_online ? '🟢 Online' : '⚫ Offline'}
                                      </option>
                                    ))}
                                  </select>
                                )}
                              </div>
                            )}

                            {['assigned', 'preparing', 'ready', 'picked_up', 'delivering'].includes(order.status) && (
                              <div className="flex-1 text-center py-3 min-h-[44px] bg-blue-50 rounded-lg flex items-center justify-center">
                                <p className="text-sm text-blue-700 font-medium">
                                  ✓ Pesanan sedang diproses
                                </p>
                              </div>
                            )}

                            {['delivered', 'completed'].includes(order.status) && (
                              <div className="flex-1 text-center py-3 min-h-[44px] bg-green-50 rounded-lg flex items-center justify-center">
                                <p className="text-sm text-green-700 font-medium">
                                  ✓ Pesanan selesai
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Riders Tab */}
            {activeTab === 'riders' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">🛵 Pengurusan Rider</h2>
                    <p className="text-gray-600 mt-1">
                      Urus rider untuk penghantaran pesanan
                    </p>
                  </div>

                  {!showAddRider && !editingRider && (
                    <button
                      onClick={() => setShowAddRider(true)}
                      className="bg-orange-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-orange-700 flex items-center gap-2 min-h-[44px]"
                    >
                      ➕ Tambah Rider
                    </button>
                  )}
                </div>

                {/* Add/Edit Form */}
                {(showAddRider || editingRider) && (
                  <AddRiderForm
                    websiteId={websites[0]?.id}
                    editData={editingRider}
                    onSuccess={() => {
                      setShowAddRider(false)
                      setEditingRider(null)
                      loadRiders()
                    }}
                    onCancel={() => {
                      setShowAddRider(false)
                      setEditingRider(null)
                    }}
                  />
                )}

                {/* Riders List */}
                {!showAddRider && !editingRider && (
                  <>
                    {riders.length === 0 ? (
                      <div className="text-center py-12 bg-gray-50 rounded-lg">
                        <div className="text-6xl mb-4">🛵</div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">
                          Tiada Rider Lagi
                        </h3>
                        <p className="text-gray-600 mb-6">
                          Tambah rider pertama anda untuk mula mengurus penghantaran
                        </p>
                        <button
                          onClick={() => setShowAddRider(true)}
                          className="bg-orange-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-orange-700 inline-flex items-center gap-2 min-h-[44px]"
                        >
                          ➕ Tambah Rider Pertama
                        </button>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {riders.map((rider) => (
                          <div
                            key={rider.id}
                            className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow"
                          >
                            {/* Rider Header */}
                            <div className="flex items-start justify-between mb-4">
                              <div>
                                <h3 className="text-lg font-bold text-gray-900">{rider.name}</h3>
                                <div className="flex items-center gap-2 mt-1">
                                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                    rider.is_online
                                      ? 'bg-green-100 text-green-800'
                                      : rider.is_active
                                      ? 'bg-gray-100 text-gray-800'
                                      : 'bg-red-100 text-red-800'
                                  }`}>
                                    {rider.is_online ? '🟢 Online' : rider.is_active ? '⚪ Offline' : '🔴 Tidak Aktif'}
                                  </span>
                                </div>
                              </div>

                              <div className="flex gap-2">
                                <button
                                  onClick={() => setEditingRider(rider)}
                                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg min-h-[44px] min-w-[44px]"
                                  title="Edit"
                                >
                                  ✏️
                                </button>
                                {rider.is_active !== false ? (
                                  <button
                                    onClick={async () => {
                                      if (confirm(`Nyahaktifkan ${rider.name}?`)) {
                                        try {
                                          const response = await fetch(
                                            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/delivery/riders/${rider.id}/status`,
                                            {
                                              method: 'PUT',
                                              headers: { 'Content-Type': 'application/json' },
                                              body: JSON.stringify({ status: 'inactive' })
                                            }
                                          )
                                          if (response.ok) {
                                            alert('Rider dinyahaktifkan')
                                            loadRiders()
                                          } else {
                                            const error = await response.json()
                                            alert('Gagal menyahaktifkan rider: ' + (error.detail || 'Unknown error'))
                                          }
                                        } catch (error) {
                                          console.error('Error:', error)
                                          alert('Ralat sistem')
                                        }
                                      }
                                    }}
                                    className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg min-h-[44px] min-w-[44px]"
                                    title="Nyahaktif"
                                  >
                                    ⏸️
                                  </button>
                                ) : (
                                  <button
                                    onClick={async () => {
                                      if (confirm(`Aktifkan semula ${rider.name}?`)) {
                                        try {
                                          const response = await fetch(
                                            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/delivery/riders/${rider.id}/status`,
                                            {
                                              method: 'PUT',
                                              headers: { 'Content-Type': 'application/json' },
                                              body: JSON.stringify({ status: 'active' })
                                            }
                                          )
                                          if (response.ok) {
                                            alert('Rider diaktifkan semula')
                                            loadRiders()
                                          } else {
                                            const error = await response.json()
                                            alert('Gagal mengaktifkan rider: ' + (error.detail || 'Unknown error'))
                                          }
                                        } catch (error) {
                                          console.error('Error:', error)
                                          alert('Ralat sistem')
                                        }
                                      }
                                    }}
                                    className="p-2 text-green-600 hover:bg-green-50 rounded-lg min-h-[44px] min-w-[44px]"
                                    title="Aktifkan Semula"
                                  >
                                    ▶️
                                  </button>
                                )}
                                <button
                                  onClick={async () => {
                                    if (confirm(`PADAM ${rider.name}? Tindakan ini tidak boleh dibatalkan.`)) {
                                      try {
                                        const response = await fetch(
                                          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/delivery/riders/${rider.id}`,
                                          {
                                            method: 'DELETE',
                                            headers: { 'Content-Type': 'application/json' }
                                          }
                                        )
                                        if (response.ok) {
                                          alert('Rider berjaya dipadam')
                                          loadRiders()
                                        } else {
                                          const error = await response.json()
                                          alert('Gagal memadam rider: ' + (error.detail || 'Unknown error'))
                                        }
                                      } catch (error) {
                                        console.error('Error:', error)
                                        alert('Ralat sistem')
                                      }
                                    }
                                  }}
                                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg min-h-[44px] min-w-[44px]"
                                  title="Padam"
                                >
                                  🗑️
                                </button>
                              </div>
                            </div>

                            {/* Rider Info */}
                            <div className="space-y-2 text-sm">
                              <div className="flex items-center gap-2 text-gray-700">
                                <span>📱</span>
                                <a href={`tel:${rider.phone}`} className="hover:text-orange-600">
                                  {rider.phone}
                                </a>
                              </div>

                              {rider.email && (
                                <div className="flex items-center gap-2 text-gray-700">
                                  <span>📧</span>
                                  <span className="truncate">{rider.email}</span>
                                </div>
                              )}

                              <div className="flex items-center gap-2 text-gray-700">
                                <span>
                                  {rider.vehicle_type === 'motorcycle' ? '🏍️' :
                                   rider.vehicle_type === 'car' ? '🚗' :
                                   rider.vehicle_type === 'bicycle' ? '🚲' : '🛴'}
                                </span>
                                <span className="font-semibold">{rider.vehicle_plate}</span>
                                {rider.vehicle_model && (
                                  <span className="text-gray-500">• {rider.vehicle_model}</span>
                                )}
                              </div>

                              <div className="flex items-center gap-2 text-gray-700 pt-2 border-t">
                                <span>📊</span>
                                <span><strong>{rider.total_deliveries || 0}</strong> penghantaran selesai</span>
                              </div>
                            </div>

                            {/* Quick Actions */}
                            <div className="flex gap-2 mt-4 pt-4 border-t">
                              <a
                                href={`tel:${rider.phone}`}
                                className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg text-center text-sm font-semibold hover:bg-blue-700 min-h-[44px] flex items-center justify-center"
                              >
                                📞 Call
                              </a>
                              <a
                                href={`https://wa.me/${rider.phone.replace(/^0/, '60')}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg text-center text-sm font-semibold hover:bg-green-700 min-h-[44px] flex items-center justify-center"
                              >
                                💬 WhatsApp
                              </a>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Chat Tab */}
            {activeTab === 'chat' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl md:text-2xl font-bold">💬 Chat Pelanggan</h2>
                </div>

                {/* Loading indicator while checking chat API */}
                {chatLoading && (
                  <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-orange-500"></div>
                      <span className="text-gray-600">Menyemak sistem chat...</span>
                    </div>
                  </div>
                )}

                {/* Error Banner - Only show if API check failed */}
                {!chatEnabled && !chatLoading && (
                  <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">⚠️</span>
                      <div className="flex-1">
                        <h3 className="font-bold text-red-900 mb-1">Chat Tidak Dapat Dihubungi</h3>
                        <p className="text-sm text-red-800 mb-2">
                          Sistem chat tidak dapat dihubungi. Sila cuba semula atau hubungi sokongan.
                        </p>
                        <button
                          onClick={() => checkChatApi()}
                          className="text-sm bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded"
                        >
                          Cuba Semula
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {websites.length === 0 ? (
                  <div className="text-center py-12 px-4">
                    <div className="text-4xl md:text-6xl mb-4">🌐</div>
                    <p className="text-gray-500 mb-4 text-sm md:text-base">Tiada website untuk chat</p>
                    <Link href="/create" className="inline-block bg-blue-500 text-white px-6 py-3 min-h-[44px] rounded-lg hover:bg-blue-600 active:bg-blue-700 text-sm md:text-base">
                      ✨ Bina Website Sekarang
                    </Link>
                  </div>
                ) : chatEnabled ? (
                  <OwnerChatDashboard
                    websites={websites}
                    ownerName={profile.business_name || profile.full_name || 'Pemilik Kedai'}
                  />
                ) : null}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
