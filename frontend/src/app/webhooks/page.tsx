'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface WebhookEndpoint {
  id: string
  url: string
  events: string[] | string
  is_active: boolean
  failure_count: number
  last_triggered_at: string | null
  description: string
  created_at: string
}

interface DeliveryLog {
  id: string
  event_type: string
  response_status: number | null
  delivered: boolean
  attempt_count: number
  error_message: string | null
  created_at: string
}

const ALL_EVENTS = [
  'dispute.created', 'dispute.resolved',
  'credit.awarded', 'credit.spent',
  'order.delivered', 'order.issue_detected',
  'website.scanned', 'website.rebuilt',
  'sla.breach', 'penalty.created',
  'subscription.created', 'subscription.expired'
]

export default function WebhooksPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [endpoints, setEndpoints] = useState<WebhookEndpoint[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [newUrl, setNewUrl] = useState('')
  const [newEvents, setNewEvents] = useState<string[]>([])
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [newSecret, setNewSecret] = useState('')
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null)
  const [logs, setLogs] = useState<DeliveryLog[]>([])

  useEffect(() => {
    loadEndpoints()
  }, [])

  const loadEndpoints = async () => {
    try {
      const token = getStoredToken()
      if (!token) { router.push('/auth/login'); return }

      const response = await fetch(`${API_BASE_URL}/api/v1/webhooks`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const d = await response.json()
        setEndpoints(d.data || [])
      }
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const createEndpoint = async () => {
    if (!newUrl || newEvents.length === 0) return
    setCreating(true)

    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/webhooks`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: newUrl, events: newEvents, description: newDesc })
      })

      if (response.ok) {
        const d = await response.json()
        setNewSecret(d.secret || '')
        setShowCreate(false)
        setNewUrl('')
        setNewEvents([])
        setNewDesc('')
        loadEndpoints()
      } else {
        const err = await response.json()
        alert(err.detail || 'Gagal mencipta webhook')
      }
    } catch (err) {
      console.error('Error:', err)
    } finally {
      setCreating(false)
    }
  }

  const deleteEndpoint = async (id: string) => {
    if (!confirm('Padam webhook ini?')) return

    try {
      const token = getStoredToken()
      await fetch(`${API_BASE_URL}/api/v1/webhooks/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      loadEndpoints()
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const testEndpoint = async (id: string) => {
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/webhooks/${id}/test`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        alert('Webhook ujian dihantar!')
      }
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const loadLogs = async (endpointId: string) => {
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/webhooks/${endpointId}/logs`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const d = await response.json()
        setLogs(d.data || [])
        setSelectedEndpoint(endpointId)
      }
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const toggleEvent = (event: string) => {
    setNewEvents(prev =>
      prev.includes(event) ? prev.filter(e => e !== event) : [...prev, event]
    )
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <button onClick={() => router.push('/profile')} className="text-blue-600 text-sm mb-2 hover:underline">&larr; Kembali ke Profil</button>
            <h1 className="text-2xl font-bold text-gray-900">Webhook API</h1>
            <p className="text-gray-600 text-sm mt-1">Terima pemberitahuan event melalui HTTP webhook</p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            + Tambah Webhook
          </button>
        </div>

        {/* Secret Display */}
        {newSecret && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <p className="text-green-800 font-medium mb-1">Webhook berjaya dicipta!</p>
            <p className="text-sm text-green-700 mb-2">Simpan secret ini - ia tidak akan dipaparkan lagi:</p>
            <code className="bg-green-100 px-3 py-2 rounded block text-sm break-all">{newSecret}</code>
            <button onClick={() => { navigator.clipboard.writeText(newSecret); }} className="mt-2 text-green-600 text-sm hover:underline">Salin secret</button>
          </div>
        )}

        {/* Create Form */}
        {showCreate && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Cipta Webhook Baharu</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL Endpoint</label>
                <input
                  type="url"
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="https://your-server.com/webhook"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Keterangan (pilihan)</label>
                <input
                  type="text"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Penerangan webhook"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Events</label>
                <div className="grid grid-cols-2 gap-2">
                  {ALL_EVENTS.map(event => (
                    <label key={event} className="flex items-center gap-2 p-2 rounded hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newEvents.includes(event)}
                        onChange={() => toggleEvent(event)}
                        className="rounded border-gray-300"
                      />
                      <span className="text-sm">{event}</span>
                    </label>
                  ))}
                </div>
              </div>

              <button
                onClick={createEndpoint}
                disabled={creating || !newUrl || newEvents.length === 0}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-medium disabled:opacity-50 transition-colors"
              >
                {creating ? 'Mencipta...' : 'Cipta Webhook'}
              </button>
            </div>
          </div>
        )}

        {/* Endpoints List */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="p-4 border-b">
            <h3 className="text-lg font-semibold">Webhook Endpoints</h3>
          </div>
          {endpoints.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              Tiada webhook. Cipta satu untuk mula menerima event.
            </div>
          ) : (
            <div className="divide-y">
              {endpoints.map((ep) => {
                const events = typeof ep.events === 'string' ? JSON.parse(ep.events) : ep.events
                return (
                  <div key={ep.id} className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`w-2 h-2 rounded-full ${ep.is_active ? 'bg-green-500' : 'bg-red-500'}`}></span>
                          <span className="font-medium text-sm break-all">{ep.url}</span>
                        </div>
                        {ep.description && <p className="text-xs text-gray-500 mb-2">{ep.description}</p>}
                        <div className="flex flex-wrap gap-1">
                          {(events || []).map((e: string) => (
                            <span key={e} className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs">{e}</span>
                          ))}
                        </div>
                        {ep.failure_count > 0 && (
                          <p className="text-xs text-red-500 mt-1">Kegagalan: {ep.failure_count}</p>
                        )}
                      </div>
                      <div className="flex gap-2 ml-3">
                        <button onClick={() => testEndpoint(ep.id)} className="text-blue-600 text-xs hover:underline">Uji</button>
                        <button onClick={() => loadLogs(ep.id)} className="text-gray-600 text-xs hover:underline">Log</button>
                        <button onClick={() => deleteEndpoint(ep.id)} className="text-red-600 text-xs hover:underline">Padam</button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Delivery Logs */}
        {selectedEndpoint && (
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="text-lg font-semibold">Log Penghantaran</h3>
              <button onClick={() => setSelectedEndpoint(null)} className="text-gray-400 text-sm hover:underline">Tutup</button>
            </div>
            {logs.length === 0 ? (
              <div className="p-8 text-center text-gray-500">Tiada log penghantaran</div>
            ) : (
              <div className="divide-y">
                {logs.map((log) => (
                  <div key={log.id} className="p-4 flex items-center justify-between">
                    <div>
                      <span className={`inline-block px-2 py-0.5 rounded text-xs mr-2 ${log.delivered ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {log.delivered ? 'Berjaya' : 'Gagal'}
                      </span>
                      <span className="text-sm">{log.event_type}</span>
                      {log.error_message && <p className="text-xs text-red-500 mt-1">{log.error_message}</p>}
                    </div>
                    <div className="text-right text-xs text-gray-400">
                      <p>HTTP {log.response_status || '-'}</p>
                      <p>{new Date(log.created_at).toLocaleString('ms-MY')}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Payload Format Documentation */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-3">Format Payload</h3>
          <p className="text-sm text-gray-600 mb-3">Setiap webhook dihantar sebagai POST request dengan payload JSON dan header berikut:</p>
          <div className="bg-gray-900 text-green-400 rounded-lg p-4 text-sm font-mono overflow-x-auto">
            <pre>{`Headers:
  Content-Type: application/json
  X-BinaApp-Signature: <HMAC-SHA256>
  X-BinaApp-Event: <event_type>

Body:
{
  "event": "dispute.created",
  "timestamp": "2024-01-01T00:00:00",
  "data": {
    // Event-specific data
  }
}`}</pre>
          </div>
          <p className="text-xs text-gray-500 mt-3">Signature dikira menggunakan HMAC-SHA256 dengan secret anda sebagai kunci dan payload JSON sebagai mesej.</p>
        </div>
      </div>
    </div>
  )
}
