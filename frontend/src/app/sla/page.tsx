'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface SLADefinition {
  plan_name: string
  max_response_time_hours: number
  max_downtime_minutes: number
  max_build_time_minutes: number
  uptime_guarantee_percent: number
  credit_compensation_amount: number
  description: string
}

interface SLABreach {
  id: string
  breach_type: string
  expected_value: number
  actual_value: number
  credit_awarded: number
  description: string
  month_year: string
  auto_compensated: boolean
  created_at: string
}

interface ComplianceReport {
  month: string
  sla_definition: SLADefinition | null
  compliance_rate: number
  total_breaches: number
  breaches_by_type: Record<string, number>
  total_credits_awarded: number
  breaches: SLABreach[]
}

export default function SLAPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [sla, setSla] = useState<SLADefinition | null>(null)
  const [compliance, setCompliance] = useState<ComplianceReport | null>(null)
  const [breaches, setBreaches] = useState<SLABreach[]>([])
  const [activeTab, setActiveTab] = useState<'overview' | 'breaches'>('overview')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const token = getStoredToken()
      if (!token) { router.push('/auth/login'); return }

      const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }

      const [slaResp, compResp, breachResp] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/sla/my-sla`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/sla/compliance`, { headers }),
        fetch(`${API_BASE_URL}/api/v1/sla/breaches`, { headers })
      ])

      if (slaResp.ok) {
        const d = await slaResp.json()
        setSla(d.data)
      }
      if (compResp.ok) {
        const d = await compResp.json()
        setCompliance(d.data)
      }
      if (breachResp.ok) {
        const d = await breachResp.json()
        setBreaches(d.data || [])
      }
    } catch (err) {
      console.error('Error loading SLA data:', err)
    } finally {
      setLoading(false)
    }
  }

  const breachTypeLabel: Record<string, string> = {
    response_time: 'Masa Respons',
    downtime: 'Masa Henti',
    build_time: 'Masa Bina',
    uptime: 'Uptime'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <button onClick={() => router.push('/profile')} className="text-blue-600 text-sm mb-2 hover:underline">&larr; Kembali ke Profil</button>
            <h1 className="text-2xl font-bold text-gray-900">Jaminan Perkhidmatan (SLA)</h1>
            <p className="text-gray-600 text-sm mt-1">Pantau tahap perkhidmatan dan pampasan automatik</p>
          </div>
        </div>

        {/* Plan Badge */}
        {sla && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm text-gray-500">Pelan Semasa</span>
                <h2 className="text-xl font-bold text-gray-900 capitalize">{sla.plan_name}</h2>
                <p className="text-gray-600 text-sm">{sla.description}</p>
              </div>
              {sla.plan_name !== 'free' && (
                <div className="text-right">
                  <span className="text-sm text-gray-500">Pampasan Per Pelanggaran</span>
                  <p className="text-xl font-bold text-green-600">RM{sla.credit_compensation_amount?.toFixed(2)}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Compliance Overview */}
        {compliance && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-3xl font-bold text-blue-600">{compliance.compliance_rate}%</p>
              <p className="text-sm text-gray-500">Pematuhan</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-3xl font-bold text-orange-600">{compliance.total_breaches}</p>
              <p className="text-sm text-gray-500">Pelanggaran</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-3xl font-bold text-green-600">RM{compliance.total_credits_awarded?.toFixed(2)}</p>
              <p className="text-sm text-gray-500">Kredit Diterima</p>
            </div>
            <div className="bg-white rounded-lg shadow p-4 text-center">
              <p className="text-3xl font-bold text-gray-700">{compliance.month}</p>
              <p className="text-sm text-gray-500">Bulan</p>
            </div>
          </div>
        )}

        {/* SLA Metrics */}
        {sla && sla.plan_name !== 'free' && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Jaminan SLA Anda</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="border rounded-lg p-4">
                <p className="text-sm text-gray-500">Masa Respons Maksimum</p>
                <p className="text-xl font-bold">{sla.max_response_time_hours} jam</p>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-gray-500">Masa Henti Maksimum</p>
                <p className="text-xl font-bold">{sla.max_downtime_minutes} minit</p>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-gray-500">Masa Bina Maksimum</p>
                <p className="text-xl font-bold">{sla.max_build_time_minutes} minit</p>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-gray-500">Jaminan Uptime</p>
                <p className="text-xl font-bold">{sla.uptime_guarantee_percent}%</p>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${activeTab === 'overview' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
          >Ringkasan</button>
          <button
            onClick={() => setActiveTab('breaches')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${activeTab === 'breaches' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
          >Sejarah Pelanggaran</button>
        </div>

        {/* Breach History */}
        {activeTab === 'breaches' && (
          <div className="bg-white rounded-lg shadow">
            {breaches.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                Tiada pelanggaran SLA. Perkhidmatan berjalan lancar!
              </div>
            ) : (
              <div className="divide-y">
                {breaches.map((breach) => (
                  <div key={breach.id} className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="inline-block px-2 py-1 text-xs rounded bg-red-100 text-red-700 mr-2">
                          {breachTypeLabel[breach.breach_type] || breach.breach_type}
                        </span>
                        <span className="text-sm text-gray-600">{breach.description}</span>
                      </div>
                      {breach.auto_compensated && (
                        <span className="text-green-600 font-semibold text-sm">
                          +RM{breach.credit_awarded?.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Dijangka: {breach.expected_value} | Sebenar: {breach.actual_value} |{' '}
                      {new Date(breach.created_at).toLocaleDateString('ms-MY')}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'overview' && compliance && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Pecahan Pelanggaran Bulan Ini</h3>
            {Object.keys(compliance.breaches_by_type).length === 0 ? (
              <p className="text-gray-500 text-center py-4">Tiada pelanggaran bulan ini</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(compliance.breaches_by_type).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="font-medium">{breachTypeLabel[type] || type}</span>
                    <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
