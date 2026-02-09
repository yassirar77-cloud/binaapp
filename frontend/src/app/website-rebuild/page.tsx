'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { API_BASE_URL, DIRECT_BACKEND_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface Rebuild {
  id: string
  trigger_reason: string
  old_health_score: number | null
  new_health_score: number | null
  status: string
  changes_summary: Array<{ type: string; description: string }>
  created_at: string
  approved_at: string | null
  applied_at: string | null
}

interface RebuildPreview {
  id: string
  old_html: string
  new_html: string
  old_health_score: number | null
  new_health_score: number | null
  changes_summary: Array<{ type: string; description: string }>
  status: string
}

export default function WebsiteRebuildPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const websiteId = searchParams.get('website_id') || ''

  const [loading, setLoading] = useState(true)
  const [rebuilding, setRebuilding] = useState(false)
  const [history, setHistory] = useState<Rebuild[]>([])
  const [preview, setPreview] = useState<RebuildPreview | null>(null)
  const [previewTab, setPreviewTab] = useState<'old' | 'new'>('new')
  const [websites, setWebsites] = useState<Array<{ id: string; business_name: string }>>([])
  const [selectedWebsite, setSelectedWebsite] = useState(websiteId)

  useEffect(() => {
    loadWebsites()
  }, [])

  useEffect(() => {
    if (selectedWebsite) loadHistory()
  }, [selectedWebsite])

  const loadWebsites = async () => {
    try {
      const token = getStoredToken()
      if (!token) { router.push('/auth/login'); return }

      const response = await fetch(`${API_BASE_URL}/api/v1/websites`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        const sites = data.websites || data.data || []
        setWebsites(sites)
        if (!selectedWebsite && sites.length > 0) {
          setSelectedWebsite(sites[0].id)
        }
      }
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/website-rebuild/${selectedWebsite}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const d = await response.json()
        setHistory(d.data || [])
      }
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const triggerRebuild = async () => {
    if (!selectedWebsite) return
    setRebuilding(true)

    try {
      const token = getStoredToken()
      const response = await fetch(`${DIRECT_BACKEND_URL}/api/v1/website-rebuild/${selectedWebsite}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
      })

      if (response.ok) {
        const d = await response.json()
        alert('Bina semula berjaya! Sila semak pratonton.')
        loadHistory()
        if (d.data?.id && d.data?.status === 'preview_ready') {
          loadPreview(d.data.id)
        }
      } else {
        const err = await response.json()
        alert(err.detail || 'Gagal membina semula')
      }
    } catch (err) {
      console.error('Error:', err)
      alert('Ralat rangkaian')
    } finally {
      setRebuilding(false)
    }
  }

  const loadPreview = async (rebuildId: string) => {
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/website-rebuild/preview/${rebuildId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const d = await response.json()
        setPreview(d.data)
      }
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const approveRebuild = async (rebuildId: string) => {
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/website-rebuild/${rebuildId}/approve`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        alert('Laman web berjaya dikemas kini!')
        setPreview(null)
        loadHistory()
      }
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const rejectRebuild = async (rebuildId: string) => {
    try {
      const token = getStoredToken()
      await fetch(`${API_BASE_URL}/api/v1/website-rebuild/${rebuildId}/reject`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Tidak berminat' })
      })
      setPreview(null)
      loadHistory()
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const statusLabels: Record<string, { text: string; color: string }> = {
    pending: { text: 'Menunggu', color: 'bg-gray-100 text-gray-700' },
    generating: { text: 'Menjana...', color: 'bg-yellow-100 text-yellow-700' },
    preview_ready: { text: 'Sedia Disemak', color: 'bg-blue-100 text-blue-700' },
    approved: { text: 'Diluluskan', color: 'bg-green-100 text-green-700' },
    applied: { text: 'Diterapkan', color: 'bg-green-100 text-green-700' },
    rejected: { text: 'Ditolak', color: 'bg-red-100 text-red-700' },
    failed: { text: 'Gagal', color: 'bg-red-100 text-red-700' }
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
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="mb-6">
          <button onClick={() => router.push('/profile')} className="text-blue-600 text-sm mb-2 hover:underline">&larr; Kembali ke Profil</button>
          <h1 className="text-2xl font-bold text-gray-900">Bina Semula Laman Web</h1>
          <p className="text-gray-600 text-sm mt-1">AI akan bina semula laman web anda dengan reka bentuk baharu</p>
        </div>

        {/* Website Selector */}
        {websites.length > 1 && (
          <div className="mb-4">
            <select
              value={selectedWebsite}
              onChange={(e) => setSelectedWebsite(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-4 py-2"
            >
              {websites.map(w => (
                <option key={w.id} value={w.id}>{w.business_name}</option>
              ))}
            </select>
          </div>
        )}

        {/* Trigger Button */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-2">Bina Semula Sekarang</h3>
          <p className="text-gray-600 text-sm mb-4">AI akan menjana reka bentuk baharu berdasarkan maklumat perniagaan anda. Anda perlu meluluskan sebelum ia diterapkan.</p>
          <button
            onClick={triggerRebuild}
            disabled={rebuilding || !selectedWebsite}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium disabled:opacity-50 transition-colors"
          >
            {rebuilding ? 'Sedang menjana...' : 'Mula Bina Semula'}
          </button>
        </div>

        {/* Preview */}
        {preview && preview.status === 'preview_ready' && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Pratonton Bina Semula</h3>

            {/* Changes Summary */}
            {preview.changes_summary && preview.changes_summary.length > 0 && (
              <div className="mb-4">
                <h4 className="font-medium text-sm text-gray-700 mb-2">Perubahan:</h4>
                <div className="flex flex-wrap gap-2">
                  {preview.changes_summary.map((change, i) => (
                    <span key={i} className="bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-xs">
                      {change.description}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Side by side tabs */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setPreviewTab('old')}
                className={`px-4 py-2 rounded text-sm ${previewTab === 'old' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}
              >Lama</button>
              <button
                onClick={() => setPreviewTab('new')}
                className={`px-4 py-2 rounded text-sm ${previewTab === 'new' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}
              >Baharu</button>
            </div>

            <div className="border rounded-lg overflow-hidden" style={{ height: '400px' }}>
              <iframe
                srcDoc={previewTab === 'old' ? preview.old_html : preview.new_html}
                className="w-full h-full"
                title={`Preview ${previewTab}`}
                sandbox="allow-scripts"
              />
            </div>

            <div className="flex gap-3 mt-4">
              <button
                onClick={() => approveRebuild(preview.id)}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-medium transition-colors"
              >
                Luluskan &amp; Terapkan
              </button>
              <button
                onClick={() => rejectRebuild(preview.id)}
                className="flex-1 bg-red-100 hover:bg-red-200 text-red-700 py-3 rounded-lg font-medium transition-colors"
              >
                Tolak
              </button>
            </div>
          </div>
        )}

        {/* History */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h3 className="text-lg font-semibold">Sejarah Bina Semula</h3>
          </div>
          {history.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              Belum ada sejarah bina semula
            </div>
          ) : (
            <div className="divide-y">
              {history.map((h) => (
                <div key={h.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className={`inline-block px-2 py-1 rounded text-xs ${statusLabels[h.status]?.color || 'bg-gray-100'}`}>
                        {statusLabels[h.status]?.text || h.status}
                      </span>
                      <span className="text-sm text-gray-600 ml-2">
                        {h.trigger_reason === 'manual' ? 'Manual' : h.trigger_reason === 'low_health_score' ? 'Skor Kesihatan Rendah' : h.trigger_reason}
                      </span>
                    </div>
                    {h.status === 'preview_ready' && (
                      <button
                        onClick={() => loadPreview(h.id)}
                        className="text-blue-600 text-sm hover:underline"
                      >Lihat Pratonton</button>
                    )}
                  </div>
                  {h.old_health_score !== null && (
                    <p className="text-xs text-gray-400 mt-1">
                      Skor: {h.old_health_score} {h.new_health_score ? `→ ${h.new_health_score}` : ''}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(h.created_at).toLocaleString('ms-MY')}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
