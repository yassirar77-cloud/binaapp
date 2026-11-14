'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

// Recharts is heavy — load the chart module lazily so it doesn't block first paint
const chartLoading = () => <div className="h-[250px] animate-pulse bg-gray-700/50 rounded-lg" />
const PlanPieChart = dynamic(() => import('./FounderCharts').then(m => m.PlanPieChart), { ssr: false, loading: chartLoading })
const ValueBarChart = dynamic(() => import('./FounderCharts').then(m => m.ValueBarChart), { ssr: false, loading: chartLoading })
const UserGrowthChart = dynamic(() => import('./FounderCharts').then(m => m.UserGrowthChart), { ssr: false, loading: chartLoading })

interface Overview {
  total_users: number
  total_websites: number
  active_websites: number
  mrr: number
  active_subscriptions: number
  subscriptions_by_plan: Record<string, number>
  orders_today: number
  total_disputes: number
  total_health_scans: number
  total_credits_circulation: number
  trust_distribution: Record<string, number>
}

interface Revenue {
  total_mrr: number
  arr: number
  revenue_by_plan: Record<string, number>
  total_subscribers: number
}

interface Users {
  total_users: number
  monthly_signups: Record<string, number>
}

interface AIPerf {
  total_health_scans: number
  total_ai_chat_responses: number
  total_order_verifications: number
  total_website_rebuilds: number
}

interface MarketingSource {
  source: string
  visits: number
  signups: number
  paid: number
  signup_rate: number | null
}

interface Marketing {
  days: number
  total_visits: number
  total_signups: number
  sources: MarketingSource[]
  campaigns: { source: string; campaign: string; visits: number }[]
  daily: { date: string; visits: number }[]
}

interface Credits {
  total_in_circulation: number
  total_wallets: number
  total_earned: number
  total_spent: number
  by_transaction_type: Record<string, number>
}


export default function FounderDashboard() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'revenue' | 'users' | 'marketing' | 'ai' | 'credits'>('overview')
  const [overview, setOverview] = useState<Overview | null>(null)
  const [revenue, setRevenue] = useState<Revenue | null>(null)
  const [users, setUsers] = useState<Users | null>(null)
  const [aiPerf, setAiPerf] = useState<AIPerf | null>(null)
  const [credits, setCredits] = useState<Credits | null>(null)
  const [marketing, setMarketing] = useState<Marketing | null>(null)
  const [marketingDays, setMarketingDays] = useState(30)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const token = getStoredToken()
      if (!token) { router.push('/auth/login'); return }
      const headers = { 'Authorization': `Bearer ${token}` }

      const [ovResp, revResp, usrResp, aiResp, credResp] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/founder/overview`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/founder/revenue`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/founder/users`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/founder/ai-performance`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/founder/credits`, { headers })
      ])

      if (ovResp.status === 403) {
        setError('Akses ditolak. Halaman ini hanya untuk pengasas BinaApp.')
        return
      }

      if (ovResp.ok) { const d = await ovResp.json(); setOverview(d.data) }
      if (revResp.ok) { const d = await revResp.json(); setRevenue(d.data) }
      if (usrResp.ok) { const d = await usrResp.json(); setUsers(d.data) }
      if (aiResp.ok) { const d = await aiResp.json(); setAiPerf(d.data) }
      if (credResp.ok) { const d = await credResp.json(); setCredits(d.data) }
    } catch (err) {
      console.error('Error:', err)
      setError('Gagal memuatkan data')
    } finally {
      setLoading(false)
    }
  }

  // Loaded separately from the rest: it has its own period switch, and a
  // failure here (e.g. migration 067 not applied yet) must not blank the page.
  useEffect(() => {
    const token = getStoredToken()
    if (!token) return
    let cancelled = false
    fetch(`${API_BASE_URL}/api/v1/marketing/summary?days=${marketingDays}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (!cancelled) setMarketing(d ? d.data : null) })
      .catch(() => { if (!cancelled) setMarketing(null) })
    return () => { cancelled = true }
  }, [marketingDays])

  const exportCSV = async (type: string) => {
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/founder/export/${type}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `binaapp_${type}.csv`
        a.click()
      }
    } catch (err) {
      console.error('Export error:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-gray-800 rounded-lg p-8 text-center">
          <p className="text-red-400 text-lg">{error}</p>
          <button onClick={() => router.push('/profile')} className="mt-4 text-blue-400 hover:underline">Kembali</button>
        </div>
      </div>
    )
  }

  const planPieData = overview ? Object.entries(overview.subscriptions_by_plan).map(([name, value]) => ({ name, value })) : []
  const userGrowthData = users ? Object.entries(users.monthly_signups).sort().slice(-12).map(([month, count]) => ({ month: month.slice(5), users: count })) : []
  const trustPieData = overview ? Object.entries(overview.trust_distribution).map(([name, value]) => ({ name, value })) : []
  const revPlanData = revenue ? Object.entries(revenue.revenue_by_plan).map(([name, value]) => ({ name, value })) : []

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <button onClick={() => router.push('/profile')} className="text-blue-400 text-sm mb-2 hover:underline">&larr; Kembali</button>
            <h1 className="text-3xl font-bold">Founder Dashboard</h1>
            <p className="text-gray-400">BinaApp Business Intelligence</p>
          </div>
          <div className="flex gap-2">
            {['users', 'subscriptions', 'credits', 'trust_scores'].map(type => (
              <button
                key={type}
                onClick={() => exportCSV(type)}
                className="bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded text-xs transition-colors"
              >
                Export {type}
              </button>
            ))}
          </div>
        </div>

        {/* Key Metrics */}
        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            <div className="bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs">MRR</p>
              <p className="text-2xl font-bold text-green-400">RM{overview.mrr.toLocaleString()}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs">Pengguna</p>
              <p className="text-2xl font-bold text-blue-400">{overview.total_users}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs">Laman Web</p>
              <p className="text-2xl font-bold text-purple-400">{overview.active_websites}/{overview.total_websites}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs">Kredit Edaran</p>
              <p className="text-2xl font-bold text-yellow-400">RM{overview.total_credits_circulation.toFixed(0)}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs">Pesanan Hari Ini</p>
              <p className="text-2xl font-bold text-orange-400">{overview.orders_today}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {[
            { key: 'overview', label: 'Ringkasan' },
            { key: 'revenue', label: 'Hasil' },
            { key: 'users', label: 'Pengguna' },
            { key: 'marketing', label: 'Marketing' },
            { key: 'ai', label: 'Prestasi AI' },
            { key: 'credits', label: 'Kredit' }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`px-4 py-2 rounded-lg text-sm whitespace-nowrap ${activeTab === tab.key ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
            >{tab.label}</button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && overview && (
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Langganan Mengikut Pelan</h3>
              <PlanPieChart data={planPieData} />
            </div>
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Taburan Skor Kepercayaan</h3>
              <ValueBarChart data={trustPieData} fill="#8B5CF6" />
            </div>
          </div>
        )}

        {/* Revenue Tab */}
        {activeTab === 'revenue' && revenue && (
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-2">Ringkasan Hasil</h3>
              <div className="space-y-4 mt-4">
                <div className="flex justify-between"><span className="text-gray-400">MRR</span><span className="text-green-400 font-bold">RM{revenue.total_mrr}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">ARR</span><span className="text-green-400 font-bold">RM{revenue.arr}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Jumlah Pelanggan</span><span className="font-bold">{revenue.total_subscribers}</span></div>
              </div>
            </div>
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Hasil Mengikut Pelan</h3>
              <ValueBarChart data={revPlanData} fill="#10B981" />
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && users && (
          <div className="bg-gray-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Pertumbuhan Pengguna (12 Bulan)</h3>
            <UserGrowthChart data={userGrowthData} />
          </div>
        )}

        {/* Marketing Tab — where visitors and signups come from */}
        {activeTab === 'marketing' && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-gray-400 text-sm">
                Pelawat ke binaapp.my dan pendaftaran mengikut sumber. Dikira sejak penjejakan dipasang.
              </p>
              <div className="flex gap-2">
                {[7, 30, 90].map(d => (
                  <button
                    key={d}
                    onClick={() => setMarketingDays(d)}
                    className={`px-3 py-1 rounded text-xs ${marketingDays === d ? 'bg-blue-600' : 'bg-gray-800 hover:bg-gray-700'}`}
                  >{d} hari</button>
                ))}
              </div>
            </div>

            {!marketing ? (
              <div className="bg-gray-800 rounded-xl p-6 text-gray-400 text-sm">
                Tiada data marketing lagi.
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="bg-gray-800 rounded-xl p-4">
                    <p className="text-gray-400 text-xs">Pelawat</p>
                    <p className="text-2xl font-bold text-blue-400">{marketing.total_visits}</p>
                  </div>
                  <div className="bg-gray-800 rounded-xl p-4">
                    <p className="text-gray-400 text-xs">Pendaftaran</p>
                    <p className="text-2xl font-bold text-green-400">{marketing.total_signups}</p>
                  </div>
                  <div className="bg-gray-800 rounded-xl p-4 col-span-2 md:col-span-1">
                    <p className="text-gray-400 text-xs">Kadar daftar</p>
                    <p className="text-2xl font-bold text-yellow-400">
                      {marketing.total_visits
                        ? `${((marketing.total_signups / marketing.total_visits) * 100).toFixed(1)}%`
                        : '—'}
                    </p>
                  </div>
                </div>

                <div className="bg-gray-800 rounded-xl p-6 overflow-x-auto">
                  <h3 className="text-lg font-semibold mb-4">Mengikut Sumber</h3>
                  {marketing.sources.length === 0 ? (
                    <p className="text-gray-400 text-sm">Belum ada pelawat direkodkan dalam tempoh ini.</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-400 border-b border-gray-700">
                          <th className="py-2 pr-4 font-medium">Sumber</th>
                          <th className="py-2 pr-4 font-medium text-right">Pelawat</th>
                          <th className="py-2 pr-4 font-medium text-right">Daftar</th>
                          <th className="py-2 pr-4 font-medium text-right">Bayar</th>
                          <th className="py-2 font-medium text-right">Kadar daftar</th>
                        </tr>
                      </thead>
                      <tbody>
                        {marketing.sources.map(s => (
                          <tr key={s.source} className="border-b border-gray-700/50">
                            <td className="py-2 pr-4">{s.source}</td>
                            <td className="py-2 pr-4 text-right tabular-nums">{s.visits}</td>
                            <td className="py-2 pr-4 text-right tabular-nums">{s.signups}</td>
                            <td className="py-2 pr-4 text-right tabular-nums">{s.paid}</td>
                            <td className="py-2 text-right tabular-nums">
                              {s.signup_rate === null ? '—' : `${s.signup_rate}%`}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                {marketing.campaigns.length > 0 && (
                  <div className="bg-gray-800 rounded-xl p-6 overflow-x-auto">
                    <h3 className="text-lg font-semibold mb-4">Kempen Teratas</h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-400 border-b border-gray-700">
                          <th className="py-2 pr-4 font-medium">Kempen</th>
                          <th className="py-2 pr-4 font-medium">Sumber</th>
                          <th className="py-2 font-medium text-right">Pelawat</th>
                        </tr>
                      </thead>
                      <tbody>
                        {marketing.campaigns.map(c => (
                          <tr key={`${c.source}/${c.campaign}`} className="border-b border-gray-700/50">
                            <td className="py-2 pr-4">{c.campaign}</td>
                            <td className="py-2 pr-4 text-gray-400">{c.source}</td>
                            <td className="py-2 text-right tabular-nums">{c.visits}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* AI Performance Tab */}
        {activeTab === 'ai' && aiPerf && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <p className="text-3xl font-bold text-blue-400">{aiPerf.total_health_scans}</p>
              <p className="text-gray-400 text-sm mt-1">Imbasan Kesihatan</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <p className="text-3xl font-bold text-green-400">{aiPerf.total_ai_chat_responses}</p>
              <p className="text-gray-400 text-sm mt-1">Respons Chat AI</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <p className="text-3xl font-bold text-yellow-400">{aiPerf.total_order_verifications}</p>
              <p className="text-gray-400 text-sm mt-1">Pengesahan Pesanan</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-6 text-center">
              <p className="text-3xl font-bold text-purple-400">{aiPerf.total_website_rebuilds}</p>
              <p className="text-gray-400 text-sm mt-1">Bina Semula Web</p>
            </div>
          </div>
        )}

        {/* Credits Tab */}
        {activeTab === 'credits' && credits && (
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Ekonomi BinaCredit</h3>
              <div className="space-y-4">
                <div className="flex justify-between"><span className="text-gray-400">Jumlah Edaran</span><span className="text-yellow-400 font-bold">RM{credits.total_in_circulation.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Jumlah Dompet</span><span className="font-bold">{credits.total_wallets}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Jumlah Diperoleh</span><span className="text-green-400 font-bold">RM{credits.total_earned.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Jumlah Dibelanja</span><span className="text-red-400 font-bold">RM{credits.total_spent.toFixed(2)}</span></div>
              </div>
            </div>
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-lg font-semibold mb-4">Mengikut Jenis Transaksi</h3>
              <div className="space-y-2">
                {Object.entries(credits.by_transaction_type).map(([type, amount]) => (
                  <div key={type} className="flex justify-between items-center">
                    <span className="text-gray-400 text-sm">{type}</span>
                    <span className={`font-medium ${Number(amount) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      RM{Math.abs(Number(amount)).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
