'use client'

import { useState, useEffect, useMemo } from 'react'
import { supabase } from '@/lib/supabase'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

// ─── Types ───────────────────────────────────────────────────────
interface DashboardTabProps {
  websites: { id: string; name?: string; business_name?: string; subdomain?: string; created_at?: string }[]
  userId: string
}

interface OrderRow {
  id: string
  status: string
  total_amount: number
  delivery_fee: number
  subtotal: number
  created_at: string
  rider_id: string | null
  website_id: string
  order_type?: string
}

interface OrderItemRow {
  menu_item_id: string
  quantity: number
  price: number
  order_id: string
}

interface RiderRow {
  id: string
  name: string
  phone: string
  vehicle_type: string
  vehicle_plate: string
  is_active: boolean
  is_online: boolean
  total_deliveries: number
  rating: number
  total_ratings: number
  status: string
  created_at: string
}

interface MenuItemRow {
  id: string
  name: string
  price: number
  category_id: string | null
}

interface CategoryRow {
  id: string
  name: string
}

interface ConversationRow {
  id: string
  website_id: string
  customer_name: string
  customer_phone: string
  status: string
  unread_owner: number
  created_at: string
  updated_at: string
}

interface MessageRow {
  id: string
  conversation_id: string
  sender_type: string
  created_at: string
  is_read: boolean
}

type SubTab = 'overview' | 'orders' | 'riders' | 'menu' | 'chat'

// ─── Colours ─────────────────────────────────────────────────────
const STATUS_COLORS: Record<string, string> = {
  pending: '#F59E0B',
  confirmed: '#3B82F6',
  assigned: '#8B5CF6',
  preparing: '#F97316',
  ready: '#14B8A6',
  picked_up: '#6366F1',
  delivering: '#2563EB',
  delivered: '#10B981',
  completed: '#059669',
  cancelled: '#EF4444',
}

const PIE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#F97316', '#14B8A6', '#6366F1', '#EC4899', '#06B6D4']

const STATUS_LABELS: Record<string, string> = {
  pending: 'Menunggu Pengesahan',
  confirmed: 'Disahkan',
  assigned: 'Rider Ditetapkan',
  preparing: 'Sedang Disediakan',
  ready: 'Sedia untuk Pickup',
  picked_up: 'Dipickup',
  delivering: 'Dalam Penghantaran',
  delivered: 'Telah Dihantar',
  completed: 'Selesai',
  cancelled: 'Dibatalkan',
}

// ─── Helpers ─────────────────────────────────────────────────────
function fmtRM(v: number) {
  return `RM ${v.toLocaleString('ms-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function dayLabel(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('ms-MY', { day: 'numeric', month: 'short' })
}

// ─── Component ───────────────────────────────────────────────────
export default function DashboardTab({ websites, userId }: DashboardTabProps) {
  const [subTab, setSubTab] = useState<SubTab>('overview')
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState(30) // days

  // Data state
  const [orders, setOrders] = useState<OrderRow[]>([])
  const [orderItems, setOrderItems] = useState<OrderItemRow[]>([])
  const [riders, setRiders] = useState<RiderRow[]>([])
  const [menuItems, setMenuItems] = useState<MenuItemRow[]>([])
  const [categories, setCategories] = useState<CategoryRow[]>([])
  const [conversations, setConversations] = useState<ConversationRow[]>([])
  const [messages, setMessages] = useState<MessageRow[]>([])

  const websiteIds = useMemo(() => websites.map(w => w.id), [websites])

  // ── Fetch all data ────────────────────────────────────────────
  useEffect(() => {
    if (!supabase || websiteIds.length === 0) {
      setLoading(false)
      return
    }

    let cancelled = false
    async function fetchAll() {
      setLoading(true)
      const since = new Date()
      since.setDate(since.getDate() - dateRange)
      const sinceISO = since.toISOString()

      try {
        // Fetch orders
        const { data: ordersData } = await supabase!
          .from('delivery_orders')
          .select('id, status, total_amount, delivery_fee, subtotal, created_at, rider_id, website_id, order_type')
          .in('website_id', websiteIds)
          .gte('created_at', sinceISO)
          .order('created_at', { ascending: false })

        if (cancelled) return
        const ordersList = ordersData || []
        setOrders(ordersList)

        // Fetch order items
        const orderIds = ordersList.map(o => o.id)
        if (orderIds.length > 0) {
          // Supabase .in() has a limit, batch if needed
          const batchSize = 200
          const allItems: OrderItemRow[] = []
          for (let i = 0; i < orderIds.length; i += batchSize) {
            const batch = orderIds.slice(i, i + batchSize)
            const { data: itemsData } = await supabase!
              .from('order_items')
              .select('menu_item_id, quantity, price, order_id')
              .in('order_id', batch)
            if (cancelled) return
            if (itemsData) allItems.push(...itemsData)
          }
          setOrderItems(allItems)
        } else {
          setOrderItems([])
        }

        // Fetch riders
        const { data: ridersData } = await supabase!
          .from('riders')
          .select('id, name, phone, vehicle_type, vehicle_plate, is_active, is_online, total_deliveries, rating, total_ratings, status, created_at')
          .in('website_id', websiteIds)

        if (cancelled) return
        setRiders(ridersData || [])

        // Fetch menu items
        const { data: menuData } = await supabase!
          .from('menu_items')
          .select('id, name, price, category_id')
          .in('website_id', websiteIds)

        if (cancelled) return
        setMenuItems(menuData || [])

        // Fetch categories
        const { data: catData } = await supabase!
          .from('menu_categories')
          .select('id, name')
          .in('website_id', websiteIds)

        if (cancelled) return
        setCategories(catData || [])

        // Fetch conversations
        const { data: convData } = await supabase!
          .from('chat_conversations')
          .select('id, website_id, customer_name, customer_phone, status, unread_owner, created_at, updated_at')
          .in('website_id', websiteIds)
          .order('updated_at', { ascending: false })

        if (cancelled) return
        const convList = convData || []
        setConversations(convList)

        // Fetch messages
        const convIds = convList.map(c => c.id)
        if (convIds.length > 0) {
          const batchSize = 200
          const allMsgs: MessageRow[] = []
          for (let i = 0; i < convIds.length; i += batchSize) {
            const batch = convIds.slice(i, i + batchSize)
            const { data: msgData } = await supabase!
              .from('chat_messages')
              .select('id, conversation_id, sender_type, created_at, is_read')
              .in('conversation_id', batch)
              .gte('created_at', sinceISO)
            if (cancelled) return
            if (msgData) allMsgs.push(...msgData)
          }
          setMessages(allMsgs)
        } else {
          setMessages([])
        }
      } catch (err) {
        console.error('[Dashboard] Error fetching data:', err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchAll()
    return () => { cancelled = true }
  }, [websiteIds, dateRange])

  // ── Computed data ─────────────────────────────────────────────
  const stats = useMemo(() => {
    const totalOrders = orders.length
    const totalDelivered = orders.filter(o => o.status === 'delivered' || o.status === 'completed').length
    const totalCancelled = orders.filter(o => o.status === 'cancelled').length
    const totalRevenue = orders
      .filter(o => o.status !== 'cancelled')
      .reduce((sum, o) => sum + (o.total_amount || 0), 0)
    const activeRiders = riders.filter(r => r.is_online).length
    const avgDeliveryRating = riders.length > 0
      ? riders.reduce((sum, r) => sum + (r.rating || 0), 0) / riders.length
      : 0

    return { totalOrders, totalDelivered, totalCancelled, totalRevenue, activeRiders, avgDeliveryRating }
  }, [orders, riders])

  // Daily revenue chart data
  const dailyRevenue = useMemo(() => {
    const map: Record<string, number> = {}
    orders
      .filter(o => o.status !== 'cancelled')
      .forEach(o => {
        const day = dayLabel(o.created_at)
        map[day] = (map[day] || 0) + (o.total_amount || 0)
      })
    return Object.entries(map)
      .map(([day, revenue]) => ({ day, revenue: Math.round(revenue * 100) / 100 }))
      .reverse()
  }, [orders])

  // Order status breakdown
  const statusBreakdown = useMemo(() => {
    const map: Record<string, number> = {}
    orders.forEach(o => {
      map[o.status] = (map[o.status] || 0) + 1
    })
    return Object.entries(map).map(([status, count]) => ({
      name: STATUS_LABELS[status] || status,
      value: count,
      color: STATUS_COLORS[status] || '#9CA3AF',
    }))
  }, [orders])

  // Hourly order distribution
  const hourlyOrders = useMemo(() => {
    const hours = Array.from({ length: 24 }, (_, i) => ({
      hour: `${i.toString().padStart(2, '0')}:00`,
      count: 0,
    }))
    orders.forEach(o => {
      const h = new Date(o.created_at).getHours()
      hours[h].count++
    })
    return hours
  }, [orders])

  // Customer flow (by order_type or approximate)
  const customerFlow = useMemo(() => {
    const map: Record<string, { dinein: number; online: number }> = {}
    orders.forEach(o => {
      const day = dayLabel(o.created_at)
      if (!map[day]) map[day] = { dinein: 0, online: 0 }
      if (o.order_type === 'dine_in' || o.order_type === 'dine-in') {
        map[day].dinein++
      } else {
        map[day].online++
      }
    })
    return Object.entries(map)
      .map(([day, v]) => ({ day, 'Dine-in': v.dinein, Online: v.online }))
      .reverse()
  }, [orders])

  // Top selling menu items
  const topMenu = useMemo(() => {
    const menuMap: Record<string, { qty: number; revenue: number }> = {}
    orderItems.forEach(item => {
      const key = item.menu_item_id
      if (!menuMap[key]) menuMap[key] = { qty: 0, revenue: 0 }
      menuMap[key].qty += item.quantity || 0
      menuMap[key].revenue += (item.quantity || 0) * (item.price || 0)
    })

    const menuLookup = new Map(menuItems.map(m => [m.id, m]))

    return Object.entries(menuMap)
      .map(([id, data]) => {
        const mi = menuLookup.get(id)
        return {
          id,
          name: mi?.name || 'Item tidak dikenali',
          qty: data.qty,
          revenue: data.revenue,
        }
      })
      .sort((a, b) => b.qty - a.qty)
      .slice(0, 10)
  }, [orderItems, menuItems])

  const topMenuMax = topMenu.length > 0 ? topMenu[0].qty : 1

  // Menu revenue pie data
  const menuRevenuePie = useMemo(() => {
    return topMenu.slice(0, 6).map(m => ({
      name: m.name.length > 18 ? m.name.substring(0, 18) + '...' : m.name,
      value: Math.round(m.revenue * 100) / 100,
    }))
  }, [topMenu])

  // Chat stats
  const chatStats = useMemo(() => {
    const totalConversations = conversations.length
    const activeChats = conversations.filter(c => c.status === 'active').length
    const unreadMessages = conversations.reduce((sum, c) => sum + (c.unread_owner || 0), 0)
    const totalMessages = messages.length

    return { totalConversations, activeChats, unreadMessages, totalMessages }
  }, [conversations, messages])

  // Messages per day
  const messagesByDay = useMemo(() => {
    const map: Record<string, number> = {}
    messages.forEach(m => {
      const day = dayLabel(m.created_at)
      map[day] = (map[day] || 0) + 1
    })
    return Object.entries(map)
      .map(([day, count]) => ({ day, count }))
      .reverse()
  }, [messages])

  // Recent activity
  const recentActivity = useMemo(() => {
    return orders.slice(0, 8).map(o => ({
      id: o.id,
      type: o.status,
      label: STATUS_LABELS[o.status] || o.status,
      amount: o.total_amount,
      time: new Date(o.created_at).toLocaleString('ms-MY', {
        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
      }),
    }))
  }, [orders])

  // Recent conversations
  const recentConversations = useMemo(() => {
    return conversations.slice(0, 8)
  }, [conversations])

  // ── Loading ───────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
        <p className="text-gray-500 text-sm">Memuatkan dashboard...</p>
      </div>
    )
  }

  if (!supabase) {
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-4">⚠️</div>
        <p className="text-gray-500">Sambungan pangkalan data tidak tersedia</p>
      </div>
    )
  }

  if (websiteIds.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="text-4xl mb-4">🌐</div>
        <p className="text-gray-500 mb-2">Tiada website untuk dipaparkan</p>
        <p className="text-gray-400 text-sm">Bina website terlebih dahulu untuk melihat dashboard</p>
      </div>
    )
  }

  // ── Sub-tab navigation ────────────────────────────────────────
  const subTabs: { key: SubTab; icon: string; label: string }[] = [
    { key: 'overview', icon: '📊', label: 'Gambaran' },
    { key: 'orders', icon: '📦', label: 'Pesanan' },
    { key: 'riders', icon: '🏍️', label: 'Rider' },
    { key: 'menu', icon: '🍽️', label: 'Menu' },
    { key: 'chat', icon: '💬', label: 'Chat' },
  ]

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-3">
        <h2 className="text-xl md:text-2xl font-bold">📊 Dashboard</h2>
        <select
          value={dateRange}
          onChange={e => setDateRange(Number(e.target.value))}
          className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={7}>7 hari lepas</option>
          <option value={30}>30 hari lepas</option>
          <option value={90}>90 hari lepas</option>
        </select>
      </div>

      {/* Sub-tab navigation */}
      <div className="flex gap-1 mb-6 overflow-x-auto scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0">
        {subTabs.map(t => (
          <button
            key={t.key}
            onClick={() => setSubTab(t.key)}
            className={`px-3 md:px-4 py-2 rounded-lg font-medium text-xs md:text-sm whitespace-nowrap transition-colors min-h-[36px] ${
              subTab === t.key
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ━━━ OVERVIEW ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {subTab === 'overview' && (
        <div className="space-y-6">
          {/* Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
            <StatCard label="Jumlah Pesanan" value={stats.totalOrders} icon="📦" color="bg-blue-50 text-blue-700" />
            <StatCard label="Telah Dihantar" value={stats.totalDelivered} icon="✅" color="bg-green-50 text-green-700" />
            <StatCard label="Dibatalkan" value={stats.totalCancelled} icon="❌" color="bg-red-50 text-red-700" />
            <StatCard label="Jumlah Hasil" value={fmtRM(stats.totalRevenue)} icon="💰" color="bg-yellow-50 text-yellow-700" />
          </div>

          {/* Daily Revenue Chart */}
          {dailyRevenue.length > 0 ? (
            <ChartCard title="Hasil Harian">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={dailyRevenue}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `RM${v}`} />
                  <Tooltip formatter={(v: number) => [fmtRM(v), 'Hasil']} />
                  <Line type="monotone" dataKey="revenue" stroke="#3B82F6" strokeWidth={2} dot={{ fill: '#3B82F6', r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          ) : (
            <EmptyChart message="Belum ada data hasil harian" />
          )}

          {/* Customer Flow + Status Pie */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {customerFlow.length > 0 ? (
              <ChartCard title="Aliran Pelanggan">
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={customerFlow}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="Online" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Dine-in" fill="#10B981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            ) : (
              <EmptyChart message="Belum ada data aliran pelanggan" />
            )}

            {statusBreakdown.length > 0 ? (
              <ChartCard title="Status Pesanan">
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={statusBreakdown}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                      label={({ name, value }) => `${name}: ${value}`}
                    >
                      {statusBreakdown.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </ChartCard>
            ) : (
              <EmptyChart message="Belum ada data status pesanan" />
            )}
          </div>

          {/* Recent Activity */}
          <ChartCard title="Aktiviti Terkini">
            {recentActivity.length > 0 ? (
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {recentActivity.map(a => (
                  <div key={a.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div className="flex items-center gap-3">
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: STATUS_COLORS[a.type] || '#9CA3AF' }}
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-800">{a.label}</p>
                        <p className="text-xs text-gray-400">{a.time}</p>
                      </div>
                    </div>
                    <span className="text-sm font-semibold text-gray-700">{fmtRM(a.amount)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm text-center py-6">Tiada aktiviti terkini</p>
            )}
          </ChartCard>

          {/* Bottom info cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
            <GradientCard icon="👥" label="Sesi Pelanggan" value={stats.totalOrders} gradient="from-blue-500 to-cyan-400" />
            <GradientCard icon="🏍️" label="Rider Aktif" value={stats.activeRiders} gradient="from-green-500 to-emerald-400" />
            <GradientCard icon="⏱️" label="Purata Hantar" value={riders.length > 0 ? `${Math.round(stats.avgDeliveryRating * 10) / 10}★` : '-'} gradient="from-orange-500 to-amber-400" />
            <GradientCard icon="⭐" label="Rating" value={riders.length > 0 ? `${(stats.avgDeliveryRating).toFixed(1)}/5` : '-'} gradient="from-purple-500 to-pink-400" />
          </div>
        </div>
      )}

      {/* ━━━ ORDERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {subTab === 'orders' && (
        <div className="space-y-6">
          {hourlyOrders.some(h => h.count > 0) ? (
            <ChartCard title="Pesanan Mengikut Jam">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={hourlyOrders}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="hour" tick={{ fontSize: 10 }} interval={1} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3B82F6" radius={[4, 4, 0, 0]} name="Pesanan" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          ) : (
            <EmptyChart message="Belum ada data pesanan mengikut jam" />
          )}

          {/* Status breakdown cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            {Object.entries(STATUS_LABELS).map(([key, label]) => {
              const count = orders.filter(o => o.status === key).length
              return (
                <div
                  key={key}
                  className="rounded-lg p-3 border text-center"
                  style={{ borderColor: STATUS_COLORS[key] || '#E5E7EB' }}
                >
                  <p className="text-2xl font-bold" style={{ color: STATUS_COLORS[key] }}>{count}</p>
                  <p className="text-xs text-gray-600 mt-1">{label}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ━━━ RIDERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {subTab === 'riders' && (
        <div className="space-y-6">
          <ChartCard title="Prestasi Rider">
            {riders.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-500">
                      <th className="py-2 pr-4">Nama</th>
                      <th className="py-2 pr-4">Penghantaran</th>
                      <th className="py-2 pr-4">Rating</th>
                      <th className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {riders.map(r => (
                      <tr key={r.id} className="border-b border-gray-100 last:border-0">
                        <td className="py-3 pr-4">
                          <p className="font-medium text-gray-800">{r.name}</p>
                          <p className="text-xs text-gray-400">{r.vehicle_plate}</p>
                        </td>
                        <td className="py-3 pr-4 font-semibold">{r.total_deliveries || 0}</td>
                        <td className="py-3 pr-4">
                          <span className="text-yellow-500">{'★'.repeat(Math.round(r.rating || 0))}</span>
                          <span className="text-gray-300">{'★'.repeat(5 - Math.round(r.rating || 0))}</span>
                          <span className="text-xs text-gray-400 ml-1">({(r.rating || 0).toFixed(1)})</span>
                        </td>
                        <td className="py-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                            r.is_online ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                          }`}>
                            {r.is_online ? '🟢 Online' : '⚫ Offline'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-400 text-sm text-center py-6">Belum ada rider</p>
            )}
          </ChartCard>
        </div>
      )}

      {/* ━━━ MENU ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {subTab === 'menu' && (
        <div className="space-y-6">
          <ChartCard title="Menu Paling Laris">
            {topMenu.length > 0 ? (
              <div className="space-y-3">
                {topMenu.map((item, idx) => (
                  <div key={item.id} className="flex items-center gap-3">
                    <span className="text-sm font-bold text-gray-400 w-6 text-right">#{idx + 1}</span>
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-1">
                        <p className="text-sm font-medium text-gray-800 truncate max-w-[200px]">{item.name}</p>
                        <div className="text-right flex-shrink-0">
                          <span className="text-xs text-gray-500">{item.qty} unit</span>
                          <span className="text-xs text-gray-400 mx-1">•</span>
                          <span className="text-xs font-semibold text-green-600">{fmtRM(item.revenue)}</span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all"
                          style={{ width: `${(item.qty / topMenuMax) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm text-center py-6">Tambah menu untuk melihat analitik</p>
            )}
          </ChartCard>

          {menuRevenuePie.length > 0 && (
            <ChartCard title="Pecahan Hasil Menu">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={menuRevenuePie}
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${fmtRM(value)}`}
                  >
                    {menuRevenuePie.map((_, idx) => (
                      <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmtRM(v)} />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
          )}
        </div>
      )}

      {/* ━━━ CHAT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */}
      {subTab === 'chat' && (
        <div className="space-y-6">
          {/* Chat stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
            <StatCard label="Jumlah Perbualan" value={chatStats.totalConversations} icon="💬" color="bg-blue-50 text-blue-700" />
            <StatCard label="Chat Aktif" value={chatStats.activeChats} icon="🟢" color="bg-green-50 text-green-700" />
            <StatCard label="Belum Dibaca" value={chatStats.unreadMessages} icon="📩" color="bg-red-50 text-red-700" />
            <StatCard label="Jumlah Mesej" value={chatStats.totalMessages} icon="📨" color="bg-purple-50 text-purple-700" />
          </div>

          {/* Messages per day chart */}
          {messagesByDay.length > 0 ? (
            <ChartCard title="Mesej Mengikut Hari">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={messagesByDay}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8B5CF6" radius={[4, 4, 0, 0]} name="Mesej" />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          ) : (
            <EmptyChart message="Belum ada data mesej" />
          )}

          {/* Recent conversations */}
          <ChartCard title="Perbualan Terkini">
            {recentConversations.length > 0 ? (
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {recentConversations.map(c => (
                  <div key={c.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{c.customer_name || 'Pelanggan'}</p>
                      <p className="text-xs text-gray-400">
                        {c.customer_phone || '-'} • {new Date(c.updated_at).toLocaleString('ms-MY', {
                          day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                        })}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {(c.unread_owner || 0) > 0 && (
                        <span className="bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                          {c.unread_owner}
                        </span>
                      )}
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        c.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {c.status === 'active' ? 'Aktif' : 'Tamat'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm text-center py-6">Tiada perbualan terkini</p>
            )}
          </ChartCard>
        </div>
      )}
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────
function StatCard({ label, value, icon, color }: { label: string; value: string | number; icon: string; color: string }) {
  return (
    <div className={`rounded-xl p-4 ${color}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
        <span className="text-xs font-medium opacity-80">{label}</span>
      </div>
      <p className="text-xl md:text-2xl font-bold">{value}</p>
    </div>
  )
}

function GradientCard({ icon, label, value, gradient }: { icon: string; label: string; value: string | number; gradient: string }) {
  return (
    <div className={`rounded-xl p-4 bg-gradient-to-br ${gradient} text-white`}>
      <span className="text-2xl">{icon}</span>
      <p className="text-xs mt-2 opacity-90">{label}</p>
      <p className="text-lg md:text-xl font-bold mt-1">{value}</p>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 md:p-6">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{title}</h3>
      {children}
    </div>
  )
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
      <div className="text-3xl mb-2">📉</div>
      <p className="text-gray-400 text-sm">{message}</p>
    </div>
  )
}
