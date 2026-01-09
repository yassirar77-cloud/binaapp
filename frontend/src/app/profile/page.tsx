'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'

export default function ProfilePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState({ full_name: '', business_name: '', phone: '' })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [websites, setWebsites] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [riders, setRiders] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<'websites' | 'orders'>('websites')
  const [loadingOrders, setLoadingOrders] = useState(false)

  useEffect(() => {
    loadUserData()
  }, [])

  useEffect(() => {
    if (user && websites.length > 0) {
      loadOrders()
      loadRiders()
    }
  }, [user, websites])

  async function loadUserData() {
    if (!supabase) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)

      // EXACT SAME METHOD AS MY-PROJECTS PAGE
      const { data: { user } } = await supabase.auth.getUser()

      if (!user) {
        router.push('/login')
        return
      }

      setUser(user)

      // Load profile
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user.id)
        .maybeSingle()

      if (profileData) {
        setProfile({
          full_name: profileData.full_name || '',
          business_name: profileData.business_name || '',
          phone: profileData.phone || ''
        })
      }

      // Load websites
      const { data: websitesData } = await supabase
        .from('websites')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })

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
    if (!supabase) return
    await supabase.auth.signOut()
    router.push('/')
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
      } else {
        setOrders(data || [])
      }
    } catch (error) {
      console.error('Error loading orders:', error)
    } finally {
      setLoadingOrders(false)
    }
  }

  async function loadRiders() {
    if (!supabase || websites.length === 0) return

    try {
      const websiteIds = websites.map(w => w.id)

      const { data, error } = await supabase
        .from('riders')
        .select('*')
        .or(`website_id.in.(${websiteIds.join(',')}),website_id.is.null`)
        .eq('is_active', true)
        .order('name')

      if (error) {
        console.error('Error loading riders:', error)
      } else {
        setRiders(data || [])
      }
    } catch (error) {
      console.error('Error loading riders:', error)
    }
  }

  async function confirmOrder(orderId: string) {
    if (!supabase) return

    try {
      const { error } = await supabase
        .from('delivery_orders')
        .update({
          status: 'confirmed',
          confirmed_at: new Date().toISOString()
        })
        .eq('id', orderId)

      if (error) {
        console.error('Error confirming order:', error)
        alert('❌ Gagal mengesahkan pesanan')
      } else {
        alert('✅ Pesanan disahkan!')
        loadOrders()
      }
    } catch (error) {
      console.error('Error confirming order:', error)
      alert('❌ Gagal mengesahkan pesanan')
    }
  }

  async function rejectOrder(orderId: string) {
    if (!supabase) return

    const reason = prompt('Sebab menolak pesanan:')
    if (!reason) return

    try {
      const { error } = await supabase
        .from('delivery_orders')
        .update({
          status: 'cancelled',
          cancelled_at: new Date().toISOString()
        })
        .eq('id', orderId)

      if (error) {
        console.error('Error rejecting order:', error)
        alert('❌ Gagal menolak pesanan')
      } else {
        alert('✅ Pesanan ditolak')
        loadOrders()
      }
    } catch (error) {
      console.error('Error rejecting order:', error)
      alert('❌ Gagal menolak pesanan')
    }
  }

  async function assignRider(orderId: string, riderId: string) {
    if (!supabase) return

    try {
      const { error } = await supabase
        .from('delivery_orders')
        .update({
          status: 'assigned',
          rider_id: riderId
        })
        .eq('id', orderId)

      if (error) {
        console.error('Error assigning rider:', error)
        alert('❌ Gagal assign rider')
      } else {
        alert('✅ Rider ditetapkan!')
        loadOrders()
      }
    } catch (error) {
      console.error('Error assigning rider:', error)
      alert('❌ Gagal assign rider')
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">Sila Log Masuk</h1>
          <Link href="/login" className="text-blue-500 hover:underline">
            Log Masuk
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header - SAME AS MY-PROJECTS */}
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
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
        </nav>
      </header>

      <div className="py-12">
        <div className="max-w-4xl mx-auto px-4">
          {/* Profile Section */}
          <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
            <h1 className="text-3xl font-bold mb-6">👤 Profil Saya</h1>
            {msg && (
              <div className={`p-4 rounded-lg mb-6 ${msg.includes('✅') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {msg}
              </div>
            )}
            <form onSubmit={saveProfile} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                <input type="email" value={user.email || ''} disabled className="w-full p-3 bg-gray-100 rounded-lg border" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nama Penuh</label>
                <input
                  type="text"
                  value={profile.full_name}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  placeholder="Nama anda"
                  className="w-full p-3 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nama Perniagaan</label>
                <input
                  type="text"
                  value={profile.business_name}
                  onChange={(e) => setProfile({ ...profile, business_name: e.target.value })}
                  placeholder="Nama perniagaan"
                  className="w-full p-3 border rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nombor Telefon</label>
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  placeholder="01X-XXX XXXX"
                  className="w-full p-3 border rounded-lg"
                />
              </div>
              <button type="submit" disabled={saving} className="w-full py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium disabled:opacity-50">
                {saving ? 'Menyimpan...' : '💾 Simpan Profil'}
              </button>
            </form>
          </div>

          {/* Tabs Navigation */}
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="flex gap-2 mb-6 border-b">
              <button
                onClick={() => setActiveTab('websites')}
                className={`px-6 py-3 font-medium transition-colors ${
                  activeTab === 'websites'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                🌐 Website Saya ({websites.length})
              </button>
              <button
                onClick={() => setActiveTab('orders')}
                className={`px-6 py-3 font-medium transition-colors ${
                  activeTab === 'orders'
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                📦 Pesanan ({orders.filter(o => o.status === 'pending').length} baru)
              </button>
            </div>

            {/* Websites Tab */}
            {activeTab === 'websites' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold">🌐 Website Saya</h2>
                  <Link href="/create" className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 text-sm font-medium">
                    + Bina Website Baru
                  </Link>
                </div>

                {websites.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">🌐</div>
                    <p className="text-gray-500 mb-6">Tiada website lagi</p>
                    <Link href="/create" className="inline-block bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600">
                      ✨ Bina Website Sekarang
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {websites.map((site) => (
                      <div key={site.id} className="border rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <h3 className="font-semibold text-lg">{site.name}</h3>
                            {site.subdomain && (
                              <a href={`https://${site.subdomain}.binaapp.my`} target="_blank" className="text-blue-500 hover:underline text-sm">
                                {site.subdomain}.binaapp.my ↗
                              </a>
                            )}
                            <p className="text-xs text-gray-500 mt-1">Dibuat: {new Date(site.created_at).toLocaleDateString('ms-MY')}</p>
                          </div>
                          <div className="flex gap-2">
                            {site.published_url && (
                              <a href={site.published_url} target="_blank" className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 text-sm">
                                👁 Lihat
                              </a>
                            )}
                            <Link href={`/editor/${site.id}`} className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 text-sm">
                              ✏️ Edit
                            </Link>
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
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold">📦 Pesanan</h2>
                  <button
                    onClick={loadOrders}
                    disabled={loadingOrders}
                    className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 text-sm font-medium disabled:opacity-50"
                  >
                    {loadingOrders ? '⏳ Loading...' : '🔄 Refresh'}
                  </button>
                </div>

                {loadingOrders ? (
                  <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                    <p className="text-gray-500 mt-4">Loading orders...</p>
                  </div>
                ) : orders.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">📦</div>
                    <p className="text-gray-500">Tiada pesanan lagi</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {orders.map((order) => {
                      const riderInfo = riders.find(r => r.id === order.rider_id)
                      return (
                        <div key={order.id} className="border rounded-lg p-6 bg-white shadow-sm">
                          {/* Order Header */}
                          <div className="flex justify-between items-start mb-4">
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
                            <p className="text-sm">
                              <span className="font-medium">👤 Pelanggan:</span> {order.customer_name}
                            </p>
                            <p className="text-sm">
                              <span className="font-medium">📱 Telefon:</span> {order.customer_phone}
                            </p>
                            <p className="text-sm">
                              <span className="font-medium">📍 Alamat:</span> {order.delivery_address}
                            </p>
                            {order.delivery_notes && (
                              <p className="text-sm">
                                <span className="font-medium">📝 Nota:</span> {order.delivery_notes}
                              </p>
                            )}
                          </div>

                          {/* Order Items */}
                          <div className="mb-4">
                            <p className="font-medium text-sm mb-2">🍽️ Item Pesanan:</p>
                            <div className="space-y-1">
                              {order.order_items?.map((item: any) => (
                                <div key={item.id} className="flex justify-between text-sm">
                                  <span>{item.quantity}x {item.item_name}</span>
                                  <span className="font-medium">RM{item.total_price.toFixed(2)}</span>
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
                              <p className="text-sm">
                                <span className="font-medium">🛵 Rider:</span> {riderInfo.name}
                              </p>
                              <p className="text-sm">
                                <span className="font-medium">📱 Telefon Rider:</span> {riderInfo.phone}
                              </p>
                              {riderInfo.vehicle_plate && (
                                <p className="text-sm">
                                  <span className="font-medium">🏍️ No Plat:</span> {riderInfo.vehicle_plate}
                                </p>
                              )}
                            </div>
                          )}

                          {/* Action Buttons */}
                          <div className="flex gap-2 mt-4">
                            {order.status === 'pending' && (
                              <>
                                <button
                                  onClick={() => confirmOrder(order.id)}
                                  className="flex-1 bg-green-500 text-white px-4 py-3 rounded-lg hover:bg-green-600 font-medium"
                                >
                                  ✅ TERIMA PESANAN
                                </button>
                                <button
                                  onClick={() => rejectOrder(order.id)}
                                  className="flex-1 bg-red-500 text-white px-4 py-3 rounded-lg hover:bg-red-600 font-medium"
                                >
                                  ❌ TOLAK
                                </button>
                              </>
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
                                    className="w-full border rounded-lg px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                              <div className="flex-1 text-center py-3 bg-blue-50 rounded-lg">
                                <p className="text-sm text-blue-700 font-medium">
                                  ✓ Pesanan sedang diproses
                                </p>
                              </div>
                            )}

                            {['delivered', 'completed'].includes(order.status) && (
                              <div className="flex-1 text-center py-3 bg-green-50 rounded-lg">
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
          </div>
        </div>
      </div>
    </div>
  )
}
