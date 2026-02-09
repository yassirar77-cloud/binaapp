'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getStoredToken } from '@/lib/supabase'
import HealthScoreCard from '@/components/website-health/HealthScoreCard'
import FixPreview from '@/components/website-health/FixPreview'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface Website {
  id: string
  business_name: string
  subdomain: string
}

interface Scan {
  id: string
  website_id: string
  overall_score: number
  design_score: number
  performance_score: number
  content_score: number
  mobile_score: number
  total_issues: number
  critical_issues: number
  auto_fixable_issues: number
  ai_summary: string
  ai_recommendations: string | string[]
  issues: string | Array<{ type: string; severity: string; description: string; auto_fixable: boolean }>
  status: string
  created_at: string
}

interface Fix {
  id: string
  issue_type: string
  issue_description: string
  severity: string
  fix_type: string
  fix_description: string
  code_before: string
  code_after: string
  status: string
}

export default function WebsiteHealthPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [websites, setWebsites] = useState<Website[]>([])
  const [selectedWebsite, setSelectedWebsite] = useState<string | null>(null)
  const [scans, setScans] = useState<Scan[]>([])
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null)
  const [fixes, setFixes] = useState<Fix[]>([])
  const [scanning, setScanning] = useState(false)
  const [autoFixing, setAutoFixing] = useState(false)
  const [latestScans, setLatestScans] = useState<Record<string, Scan>>({})

  const authHeaders = useCallback(() => {
    const token = getStoredToken()
    if (!token) {
      router.push('/login?redirect=/website-health')
      return null
    }
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  }, [router])

  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    const headers = authHeaders()
    if (!headers) throw new Error('Not authenticated')
    const res = await fetch(`${API_BASE}${path}`, { headers, ...options })
    if (res.status === 401) {
      router.push('/login?redirect=/website-health')
      throw new Error('Session expired')
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Request failed')
    }
    return res.json()
  }, [authHeaders, router])

  // Load user websites
  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch('/api/v1/websites')
        const sites = data.websites || data || []
        setWebsites(Array.isArray(sites) ? sites : [])

        // Load latest scan for each website
        const scanMap: Record<string, Scan> = {}
        for (const site of (Array.isArray(sites) ? sites : [])) {
          try {
            const scanData = await apiFetch(`/api/v1/website-health/scans/${site.id}`)
            const siteScans = scanData.scans || []
            if (siteScans.length > 0) {
              scanMap[site.id] = siteScans[0]
            }
          } catch {
            // No scans yet
          }
        }
        setLatestScans(scanMap)
      } catch (err) {
        console.error('Failed to load websites:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [apiFetch])

  const handleSelectWebsite = async (websiteId: string) => {
    setSelectedWebsite(websiteId)
    setSelectedScan(null)
    setFixes([])
    try {
      const data = await apiFetch(`/api/v1/website-health/scans/${websiteId}`)
      setScans(data.scans || [])
    } catch (err) {
      console.error('Failed to load scans:', err)
    }
  }

  const handleScan = async () => {
    if (!selectedWebsite || scanning) return
    setScanning(true)
    try {
      const data = await apiFetch(`/api/v1/website-health/scan/${selectedWebsite}`, { method: 'POST' })
      // Refresh scans
      const scansData = await apiFetch(`/api/v1/website-health/scans/${selectedWebsite}`)
      setScans(scansData.scans || [])
      if (data.scan_id) {
        const scanDetail = await apiFetch(`/api/v1/website-health/scan/${data.scan_id}`)
        setSelectedScan(scanDetail)
      }
    } catch (err) {
      console.error('Scan failed:', err)
    } finally {
      setScanning(false)
    }
  }

  const handleSelectScan = async (scan: Scan) => {
    setSelectedScan(scan)
    try {
      const data = await apiFetch(`/api/v1/website-health/fixes/${scan.id}`)
      setFixes(data.fixes || [])
    } catch (err) {
      console.error('Failed to load fixes:', err)
    }
  }

  const handleApplyFix = async (fixId: string) => {
    await apiFetch(`/api/v1/website-health/fix/${fixId}/apply`, { method: 'POST' })
    // Refresh fixes
    if (selectedScan) {
      const data = await apiFetch(`/api/v1/website-health/fixes/${selectedScan.id}`)
      setFixes(data.fixes || [])
    }
  }

  const handleRejectFix = async (fixId: string) => {
    await apiFetch(`/api/v1/website-health/fix/${fixId}/reject`, { method: 'POST' })
    if (selectedScan) {
      const data = await apiFetch(`/api/v1/website-health/fixes/${selectedScan.id}`)
      setFixes(data.fixes || [])
    }
  }

  const handleRevertFix = async (fixId: string) => {
    await apiFetch(`/api/v1/website-health/fix/${fixId}/revert`, { method: 'POST' })
    if (selectedScan) {
      const data = await apiFetch(`/api/v1/website-health/fixes/${selectedScan.id}`)
      setFixes(data.fixes || [])
    }
  }

  const handleGenerateFix = async (fixId: string) => {
    await apiFetch(`/api/v1/website-health/fix/${fixId}/generate`, { method: 'POST' })
    if (selectedScan) {
      const data = await apiFetch(`/api/v1/website-health/fixes/${selectedScan.id}`)
      setFixes(data.fixes || [])
    }
  }

  const handleAutoFix = async () => {
    if (!selectedScan || autoFixing) return
    setAutoFixing(true)
    try {
      await apiFetch(`/api/v1/website-health/auto-fix/${selectedScan.id}`, { method: 'POST' })
      const data = await apiFetch(`/api/v1/website-health/fixes/${selectedScan.id}`)
      setFixes(data.fixes || [])
    } catch (err) {
      console.error('Auto-fix failed:', err)
    } finally {
      setAutoFixing(false)
    }
  }

  const parseIssues = (issues: Scan['issues']) => {
    if (typeof issues === 'string') {
      try { return JSON.parse(issues) } catch { return [] }
    }
    return issues || []
  }

  const parseRecommendations = (recs: Scan['ai_recommendations']) => {
    if (typeof recs === 'string') {
      try { return JSON.parse(recs) } catch { return [] }
    }
    return recs || []
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Memuatkan...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-800">Kesihatan Laman Web</h1>
            <p className="text-xs text-gray-500">AI Auto-Fix &amp; Monitoring</p>
          </div>
          <Link href="/profil" className="text-sm text-blue-600 hover:underline">
            Kembali ke Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Website list with health scores */}
        {!selectedWebsite && (
          <div>
            <h2 className="text-base font-semibold text-gray-700 mb-4">Laman Web Anda</h2>
            {websites.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <p>Tiada laman web ditemui.</p>
                <Link href="/create" className="text-blue-600 hover:underline text-sm mt-2 inline-block">
                  Cipta laman web baru
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {websites.map((site) => {
                  const scan = latestScans[site.id]
                  return (
                    <HealthScoreCard
                      key={site.id}
                      websiteName={site.business_name}
                      overallScore={scan?.overall_score ?? 0}
                      designScore={scan?.design_score ?? 0}
                      performanceScore={scan?.performance_score ?? 0}
                      contentScore={scan?.content_score ?? 0}
                      mobileScore={scan?.mobile_score ?? 0}
                      totalIssues={scan?.total_issues ?? 0}
                      lastScan={scan?.created_at}
                      onClick={() => handleSelectWebsite(site.id)}
                    />
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Selected website view */}
        {selectedWebsite && (
          <div>
            <button
              onClick={() => { setSelectedWebsite(null); setSelectedScan(null); setFixes([]) }}
              className="text-sm text-blue-600 hover:underline mb-4 inline-flex items-center gap-1"
            >
              &larr; Kembali ke senarai
            </button>

            <div className="flex items-center gap-3 mb-4">
              <h2 className="text-base font-semibold text-gray-700">
                {websites.find((w) => w.id === selectedWebsite)?.business_name || 'Laman Web'}
              </h2>
              <button
                onClick={handleScan}
                disabled={scanning}
                className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {scanning ? 'Mengimbas...' : 'Scan Sekarang'}
              </button>
            </div>

            {/* Scan history */}
            {scans.length > 0 && !selectedScan && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-600">Sejarah Imbasan</h3>
                {scans.map((scan) => (
                  <div
                    key={scan.id}
                    onClick={() => handleSelectScan(scan)}
                    className="border rounded-lg bg-white p-4 cursor-pointer hover:shadow-sm transition-shadow"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span
                          className={`text-2xl font-bold ${
                            scan.overall_score >= 80 ? 'text-green-600' :
                            scan.overall_score >= 50 ? 'text-yellow-600' : 'text-red-600'
                          }`}
                        >
                          {scan.overall_score}
                        </span>
                        <div>
                          <p className="text-sm text-gray-700">{scan.total_issues} isu ditemui</p>
                          <p className="text-xs text-gray-400">
                            {new Date(scan.created_at).toLocaleString('ms-MY')}
                          </p>
                        </div>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        scan.status === 'fixed' ? 'bg-green-100 text-green-700' :
                        scan.status === 'completed' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {scan.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {scans.length === 0 && !scanning && (
              <div className="text-center py-12 text-gray-400">
                <p>Tiada imbasan lagi. Tekan &quot;Scan Sekarang&quot; untuk memulakan.</p>
              </div>
            )}

            {/* Scan details */}
            {selectedScan && (
              <div className="space-y-6">
                <button
                  onClick={() => { setSelectedScan(null); setFixes([]) }}
                  className="text-sm text-blue-600 hover:underline inline-flex items-center gap-1"
                >
                  &larr; Kembali ke sejarah
                </button>

                {/* Score summary */}
                <HealthScoreCard
                  overallScore={selectedScan.overall_score}
                  designScore={selectedScan.design_score}
                  performanceScore={selectedScan.performance_score}
                  contentScore={selectedScan.content_score}
                  mobileScore={selectedScan.mobile_score}
                  totalIssues={selectedScan.total_issues}
                  lastScan={selectedScan.created_at}
                />

                {/* AI Summary */}
                {selectedScan.ai_summary && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-blue-700 mb-1">Ringkasan AI</h3>
                    <p className="text-sm text-blue-800">{selectedScan.ai_summary}</p>
                  </div>
                )}

                {/* Recommendations */}
                {parseRecommendations(selectedScan.ai_recommendations).length > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-green-700 mb-2">Cadangan</h3>
                    <ul className="space-y-1">
                      {parseRecommendations(selectedScan.ai_recommendations).map((rec: string, i: number) => (
                        <li key={i} className="text-sm text-green-800 flex items-start gap-2">
                          <span className="text-green-500 mt-0.5">-</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Auto-fix button */}
                {selectedScan.auto_fixable_issues > 0 && (
                  <button
                    onClick={handleAutoFix}
                    disabled={autoFixing}
                    className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors text-sm font-medium"
                  >
                    {autoFixing
                      ? 'Sedang membaiki...'
                      : `Auto-Fix Semua (${selectedScan.auto_fixable_issues} isu selamat)`}
                  </button>
                )}

                {/* Fixes list */}
                {fixes.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-semibold text-gray-700">
                      Pembetulan ({fixes.length})
                    </h3>
                    {fixes.map((fix) => (
                      <FixPreview
                        key={fix.id}
                        fixId={fix.id}
                        issueType={fix.issue_type}
                        issueDescription={fix.issue_description}
                        severity={fix.severity}
                        codeBefore={fix.code_before}
                        codeAfter={fix.code_after}
                        fixDescription={fix.fix_description}
                        status={fix.status}
                        onApply={handleApplyFix}
                        onReject={handleRejectFix}
                        onRevert={handleRevertFix}
                        onGenerate={handleGenerateFix}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
