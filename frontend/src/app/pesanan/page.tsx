'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getStoredToken, getCurrentUser } from '@/lib/supabase'
import DashboardHeader from '@/components/dashboard-new/DashboardHeader'
import DashboardFooter from '@/components/dashboard-new/DashboardFooter'
import '@/components/dashboard-new/dashboard.css'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface OrderItem {
  name: string
  price: number
  quantity: number
}

interface Order {
  id: string
  order_number: string
  website_id: string
  customer_name: string
  customer_phone: string
  delivery_address: string
  delivery_notes: string | null
  delivery_fee: number
  subtotal: number
  total_amount: number
  payment_method: string
  status: string
  created_at: string
  confirmed_at: string | null
  rider_id: string | null
  items: OrderItem[]
  notes: string
}

interface Website {
  id: string
  name?: string
  business_name?: string
  subdomain?: string
}

interface Rider {
  id: string
  name: string
  phone: string
  vehicle_plate?: string
  is_online?: boolean
  website_id: string
}

export default function PesananPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [orders, setOrders] = useState<Order[]>([])
  const [websites, setWebsites] = useState<Website[]>([])
  const [riders, setRiders] = useState<Rider[]>([])
  const [userName, setUserName] = useState('Pengguna')
  const [loadingOrders, setLoadingOrders] = useState(false)

  useEffect(() => {
    init()
  }, [])

  async function init() {
    const token = getStoredToken()
    const user = await getCurrentUser()

    if (!token || !user) {
      router.push('/login')
      return
    }

    setUserName(
      (user as any).user_metadata?.full_name ||
        (user as any).email?.split('@')[0] ||
        'Pengguna',
    )

    // Load websites first (needed for riders fetch + WhatsApp context)
    const loadedWebsites = await fetchWebsites(token)
    setWebsites(loadedWebsites)

    // Load orders and riders in parallel
    await Promise.all([fetchOrders(token), fetchRiders(token, loadedWebsites)])

    setLoading(false)
  }

  // ── Data fetching ──────────────────────────────────────

  async function fetchOrders(token: string) {
    setLoadingOrders(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/delivery/orders/my`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) {
        if (res.status === 401) {
          router.push('/login')
          return
        }
        console.error('[Pesanan] Failed to fetch orders:', res.status)
        return
      }
      const data = await res.json()
      setOrders(data.orders || [])
    } catch (err) {
      console.error('[Pesanan] Error fetching orders:', err)
    } finally {
      setLoadingOrders(false)
    }
  }

  async function fetchWebsites(token: string): Promise<Website[]> {
    try {
      const res = await fetch(`${API_BASE}/api/v1/websites/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (!res.ok) return []
      const data = await res.json()
      return (data || []).map((w: any) => ({
        ...w,
        name: w.business_name,
      }))
    } catch {
      return []
    }
  }

  async function fetchRiders(token: string, sites: Website[]) {
    if (sites.length === 0) return
    const allRiders: Rider[] = []
    for (const site of sites) {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/delivery/admin/websites/${site.id}/riders`,
          { headers: { Authorization: `Bearer ${token}` } },
        )
        if (!res.ok) continue
        const data = await res.json()
        for (const rider of data || []) {
          if (!allRiders.find((r) => r.id === rider.id)) {
            allRiders.push(rider)
          }
        }
      } catch {
        // continue to next website
      }
    }
    setRiders(allRiders)
  }

  // ── Order actions ──────────────────────────────────────

  async function confirmOrder(orderId: string) {
    const token = getStoredToken()
    if (!token) {
      alert('Sila log masuk semula')
      router.push('/login')
      return
    }
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/delivery/orders/${orderId}/status`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            status: 'confirmed',
            notes: 'Pesanan disahkan oleh pemilik',
          }),
        },
      )
      if (!res.ok) {
        if (res.status === 401) {
          alert('Sesi tamat tempoh. Sila log masuk semula.')
          router.push('/login')
          return
        }
        const err = await res.json().catch(() => ({}))
        alert(`Gagal mengesahkan pesanan\n\n${err.detail || res.statusText}`)
        return
      }
      alert('Pesanan disahkan!')
      fetchOrders(token)
    } catch (err: any) {
      alert(`Gagal mengesahkan pesanan\n\n${err?.message || 'Network error'}`)
    }
  }

  async function rejectOrder(orderId: string) {
    const reason = prompt('Sebab menolak pesanan:')
    if (!reason) return

    const token = getStoredToken()
    if (!token) {
      alert('Sila log masuk semula')
      router.push('/login')
      return
    }
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/delivery/orders/${orderId}/status`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            status: 'cancelled',
            notes: `Pesanan ditolak: ${reason}`,
          }),
        },
      )
      if (!res.ok) {
        if (res.status === 401) {
          alert('Sesi tamat tempoh. Sila log masuk semula.')
          router.push('/login')
          return
        }
        const err = await res.json().catch(() => ({}))
        alert(`Gagal menolak pesanan\n\n${err.detail || res.statusText}`)
        return
      }
      alert('Pesanan ditolak')
      fetchOrders(token)
    } catch (err: any) {
      alert(`Gagal menolak pesanan\n\n${err?.message || 'Network error'}`)
    }
  }

  async function assignRider(orderId: string, riderId: string) {
    const token = getStoredToken()
    if (!token) {
      alert('Sila log masuk semula')
      router.push('/login')
      return
    }
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/delivery/orders/${orderId}/assign-rider`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ rider_id: riderId }),
        },
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert(`Gagal menetapkan rider\n\n${err.detail || res.statusText}`)
        return
      }
      alert('Rider ditetapkan!')
      fetchOrders(token)
    } catch (err: any) {
      alert(`Gagal menetapkan rider\n\n${err?.message || 'Network error'}`)
    }
  }

  // ── Helpers ────────────────────────────────────────────

  function getStatusBadge(status: string) {
    const badges: Record<string, { label: string; bg: string; text: string }> = {
      pending: { label: 'Menunggu Pengesahan', bg: 'bg-yellow-500/15', text: 'text-yellow-400' },
      confirmed: { label: 'Disahkan', bg: 'bg-blue-500/15', text: 'text-blue-400' },
      assigned: { label: 'Rider Ditetapkan', bg: 'bg-purple-500/15', text: 'text-purple-400' },
      preparing: { label: 'Sedang Disediakan', bg: 'bg-orange-500/15', text: 'text-orange-400' },
      ready: { label: 'Sedia untuk Pickup', bg: 'bg-teal-500/15', text: 'text-teal-400' },
      picked_up: { label: 'Dipickup Rider', bg: 'bg-indigo-500/15', text: 'text-indigo-400' },
      delivering: { label: 'Sedang Dihantar', bg: 'bg-blue-500/15', text: 'text-blue-400' },
      delivered: { label: 'Telah Dihantar', bg: 'bg-green-500/15', text: 'text-green-400' },
      completed: { label: 'Selesai', bg: 'bg-green-500/15', text: 'text-green-400' },
      cancelled: { label: 'Dibatalkan', bg: 'bg-red-500/15', text: 'text-red-400' },
    }
    const badge = badges[status] || {
      label: status,
      bg: 'bg-white/10',
      text: 'text-white/60',
    }
    return (
      <span
        className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}
      >
        {badge.label}
      </span>
    )
  }

  function waCustomerUrl(order: Order) {
    const site = websites.find((w) => w.id === order.website_id)
    const shopName = site?.name || site?.business_name || 'kedai'
    const phone = order.customer_phone.replace(/^0/, '60')
    return `https://wa.me/${phone}?text=Hi%20${encodeURIComponent(order.customer_name)},%20ini%20dari%20${encodeURIComponent(shopName)}%20mengenai%20pesanan%20${order.order_number}`
  }

  function waRiderUrl(order: Order, rider: Rider) {
    const phone = rider.phone.replace(/^0/, '60')
    return `https://wa.me/${phone}?text=Hi%20${encodeURIComponent(rider.name)},%20mengenai%20order%20${order.order_number}`
  }

  function handleLogout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('binaapp_token')
      localStorage.removeItem('binaapp_user')
    }
    router.push('/')
  }

  // ── Render ─────────────────────────────────────────────

  if (loading) {
    return (
      <div className="dash-bg min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#C7FF3D]" />
      </div>
    )
  }

  const pendingCount = orders.filter((o) => o.status === 'pending').length

  return (
    <div className="dash-bg min-h-screen relative">
      <div className="dash-dotgrid" />
      <div className="dash-glow-top" />
      <div className="dash-glow-accent" />

      <DashboardHeader
        userName={userName}
        newOrdersCount={pendingCount}
        onLogout={handleLogout}
      />

      <main className="relative z-10 mx-auto max-w-4xl px-4 lg:px-6 py-8">
        {/* Page header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-white">Pesanan</h1>
            <p className="text-sm text-white/40 mt-1">
              {orders.length} pesanan &middot; {pendingCount} menunggu pengesahan
            </p>
          </div>
          <button
            onClick={() => {
              const token = getStoredToken()
              if (token) fetchOrders(token)
            }}
            disabled={loadingOrders}
            className="px-4 py-2 rounded-lg bg-white/[0.08] border border-white/[0.1] text-sm text-white/70 hover:text-white hover:bg-white/[0.12] transition-colors disabled:opacity-50"
          >
            {loadingOrders ? 'Loading...' : 'Refresh'}
          </button>
        </div>

        {/* Loading state */}
        {loadingOrders && orders.length === 0 && (
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#C7FF3D] mx-auto" />
            <p className="text-white/40 mt-4 text-sm">Memuatkan pesanan...</p>
          </div>
        )}

        {/* Empty state */}
        {!loadingOrders && orders.length === 0 && (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📦</div>
            <p className="text-white/40 text-sm">Tiada pesanan lagi</p>
          </div>
        )}

        {/* Order cards */}
        <div className="space-y-4">
          {orders.map((order) => {
            const riderInfo = riders.find((r) => r.id === order.rider_id)
            const orderWebsite = websites.find((w) => w.id === order.website_id)

            return (
              <div
                key={order.id}
                className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-4 md:p-6"
              >
                {/* Order header */}
                <div className="flex flex-col sm:flex-row justify-between items-start gap-2 mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white">
                      #{order.order_number}
                    </h3>
                    <p className="text-xs text-white/40">
                      {new Date(order.created_at).toLocaleString('ms-MY', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      {orderWebsite && (
                        <span className="ml-2 text-white/30">
                          &middot; {orderWebsite.name || orderWebsite.business_name}
                        </span>
                      )}
                    </p>
                  </div>
                  {getStatusBadge(order.status)}
                </div>

                {/* Customer info */}
                <div className="mb-4 p-3 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                  <p className="text-xs md:text-sm text-white/70 break-words">
                    <span className="font-medium text-white/90">Pelanggan:</span>{' '}
                    {order.customer_name}
                  </p>
                  <p className="text-xs md:text-sm text-white/70">
                    <span className="font-medium text-white/90">Telefon:</span>{' '}
                    <a
                      href={`tel:${order.customer_phone}`}
                      className="text-[#C7FF3D]/80 hover:text-[#C7FF3D]"
                    >
                      {order.customer_phone}
                    </a>
                  </p>
                  <p className="text-xs md:text-sm text-white/70 break-words">
                    <span className="font-medium text-white/90">Alamat:</span>{' '}
                    {order.delivery_address}
                  </p>
                  {order.delivery_notes && (
                    <p className="text-xs md:text-sm text-white/70 break-words">
                      <span className="font-medium text-white/90">Nota:</span>{' '}
                      {order.delivery_notes}
                    </p>
                  )}
                </div>

                {/* Order items */}
                <div className="mb-4">
                  <p className="font-medium text-xs md:text-sm text-white/90 mb-2">
                    Item Pesanan:
                  </p>
                  <div className="space-y-1">
                    {(order.items || []).map((item, idx) => (
                      <div
                        key={idx}
                        className="flex justify-between text-xs md:text-sm gap-2"
                      >
                        <span className="flex-1 text-white/70 break-words">
                          {item.quantity}x {item.name}
                        </span>
                        <span className="font-medium text-white/90 whitespace-nowrap">
                          RM{(item.price * item.quantity).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Pricing */}
                <div className="mb-4 pt-3 border-t border-white/[0.06]">
                  <div className="flex justify-between text-sm text-white/60 mb-1">
                    <span>Subtotal:</span>
                    <span>RM{order.subtotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-white/60 mb-1">
                    <span>Delivery Fee:</span>
                    <span>RM{order.delivery_fee.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-lg text-[#C7FF3D]">
                    <span>Total:</span>
                    <span>RM{order.total_amount.toFixed(2)}</span>
                  </div>
                  <p className="text-xs text-white/30 mt-1">
                    Bayaran: {order.payment_method.toUpperCase()}
                  </p>
                </div>

                {/* Rider info */}
                {order.rider_id && riderInfo && (
                  <div className="mb-4 p-3 rounded-xl bg-blue-500/[0.08] border border-blue-500/[0.15]">
                    <p className="text-xs md:text-sm text-white/70">
                      <span className="font-medium text-white/90">Rider:</span>{' '}
                      {riderInfo.name}
                    </p>
                    <p className="text-xs md:text-sm text-white/70">
                      <span className="font-medium text-white/90">
                        Telefon Rider:
                      </span>{' '}
                      <a
                        href={`tel:${riderInfo.phone}`}
                        className="text-[#C7FF3D]/80 hover:text-[#C7FF3D]"
                      >
                        {riderInfo.phone}
                      </a>
                    </p>
                    {riderInfo.vehicle_plate && (
                      <p className="text-xs md:text-sm text-white/70">
                        <span className="font-medium text-white/90">
                          No Plat:
                        </span>{' '}
                        {riderInfo.vehicle_plate}
                      </p>
                    )}
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex flex-col sm:flex-row gap-2 mt-4">
                  {order.status === 'pending' && (
                    <>
                      <button
                        onClick={() => confirmOrder(order.id)}
                        className="flex-1 bg-green-600 text-white px-4 py-3 min-h-[44px] rounded-xl hover:bg-green-500 active:bg-green-700 font-medium text-sm transition-colors"
                      >
                        TERIMA PESANAN
                      </button>
                      <button
                        onClick={() => rejectOrder(order.id)}
                        className="flex-1 bg-red-600/80 text-white px-4 py-3 min-h-[44px] rounded-xl hover:bg-red-500 active:bg-red-700 font-medium text-sm transition-colors"
                      >
                        TOLAK
                      </button>
                    </>
                  )}

                  {order.customer_phone && (
                    <a
                      href={waCustomerUrl(order)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 bg-green-700/60 text-white px-4 py-3 min-h-[44px] rounded-xl hover:bg-green-600/60 font-medium text-sm text-center flex items-center justify-center gap-2 transition-colors"
                    >
                      WhatsApp Customer
                    </a>
                  )}

                  {riderInfo?.phone && (
                    <a
                      href={waRiderUrl(order, riderInfo)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 bg-orange-600/60 text-white px-4 py-3 min-h-[44px] rounded-xl hover:bg-orange-500/60 font-medium text-sm text-center flex items-center justify-center gap-2 transition-colors"
                    >
                      WhatsApp Rider
                    </a>
                  )}

                  {order.status === 'confirmed' && (
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-white/70 mb-2">
                        Pilih Rider untuk Hantar
                      </label>
                      {riders.length === 0 ? (
                        <p className="text-sm text-red-400">
                          Tiada rider tersedia. Sila tambah rider dahulu.
                        </p>
                      ) : (
                        <select
                          onChange={(e) => {
                            if (e.target.value) {
                              assignRider(order.id, e.target.value)
                            }
                          }}
                          className="w-full rounded-xl px-4 py-3 min-h-[44px] text-sm bg-white/[0.06] border border-white/[0.1] text-white focus:outline-none focus:ring-2 focus:ring-[#C7FF3D]/40"
                          defaultValue=""
                        >
                          <option value="" className="bg-[#161623]">
                            -- Pilih Rider --
                          </option>
                          {riders.map((rider) => (
                            <option
                              key={rider.id}
                              value={rider.id}
                              className="bg-[#161623]"
                            >
                              {rider.name} - {rider.phone}{' '}
                              {rider.is_online ? 'Online' : 'Offline'}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  )}

                  {[
                    'assigned',
                    'preparing',
                    'ready',
                    'picked_up',
                    'delivering',
                  ].includes(order.status) && (
                    <div className="flex-1 text-center py-3 min-h-[44px] bg-blue-500/10 rounded-xl flex items-center justify-center">
                      <p className="text-sm text-blue-400 font-medium">
                        Pesanan sedang diproses
                      </p>
                    </div>
                  )}

                  {['delivered', 'completed'].includes(order.status) && (
                    <div className="flex-1 text-center py-3 min-h-[44px] bg-green-500/10 rounded-xl flex items-center justify-center">
                      <p className="text-sm text-green-400 font-medium">
                        Pesanan selesai
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </main>

      <div className="relative z-10 mx-auto max-w-4xl px-4 lg:px-6 pb-8">
        <DashboardFooter />
      </div>
    </div>
  )
}
