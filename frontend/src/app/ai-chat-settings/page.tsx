'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { API_BASE_URL } from '@/lib/env'
import { getStoredToken } from '@/lib/supabase'

interface ChatSettings {
  website_id: string
  is_enabled: boolean
  delay_seconds: number
  custom_greeting: string
  personality: string
  auto_respond_hours: { start: number; end: number }
}

interface AIResponse {
  id: string
  customer_message: string
  ai_response: string
  model_used: string
  response_time_ms: number
  created_at: string
}

export default function AIChatSettingsPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const websiteId = searchParams.get('website_id') || ''

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState<ChatSettings>({
    website_id: websiteId,
    is_enabled: false,
    delay_seconds: 120,
    custom_greeting: 'Salam! Saya BinaBot, pembantu AI kedai ini. Ada apa yang boleh saya bantu?',
    personality: 'friendly',
    auto_respond_hours: { start: 0, end: 24 }
  })
  const [responses, setResponses] = useState<AIResponse[]>([])
  const [activeTab, setActiveTab] = useState<'settings' | 'log'>('settings')
  const [websites, setWebsites] = useState<Array<{ id: string; business_name: string }>>([])
  const [selectedWebsite, setSelectedWebsite] = useState(websiteId)

  useEffect(() => {
    loadWebsites()
  }, [])

  useEffect(() => {
    if (selectedWebsite) {
      loadSettings()
      loadResponses()
    }
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
      console.error('Error loading websites:', err)
    }
  }

  const loadSettings = async () => {
    try {
      setLoading(true)
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/ai-chat-settings/${selectedWebsite}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const d = await response.json()
        setSettings(d.data)
      }
    } catch (err) {
      console.error('Error loading settings:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadResponses = async () => {
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/ai-chat-settings/${selectedWebsite}/responses`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const d = await response.json()
        setResponses(d.data || [])
      }
    } catch (err) {
      console.error('Error loading responses:', err)
    }
  }

  const saveSettings = async () => {
    setSaving(true)
    try {
      const token = getStoredToken()
      const response = await fetch(`${API_BASE_URL}/api/v1/ai-chat-settings/${selectedWebsite}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          is_enabled: settings.is_enabled,
          delay_seconds: settings.delay_seconds,
          custom_greeting: settings.custom_greeting,
          personality: settings.personality,
          auto_respond_hours: settings.auto_respond_hours
        })
      })
      if (response.ok) {
        alert('Tetapan berjaya disimpan!')
      }
    } catch (err) {
      console.error('Error saving:', err)
    } finally {
      setSaving(false)
    }
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
        <div className="mb-6">
          <button onClick={() => router.push('/profile')} className="text-blue-600 text-sm mb-2 hover:underline">&larr; Kembali ke Profil</button>
          <h1 className="text-2xl font-bold text-gray-900">Tetapan Chat AI</h1>
          <p className="text-gray-600 text-sm mt-1">Konfigurasi BinaBot untuk balas pelanggan secara automatik</p>
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

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('settings')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${activeTab === 'settings' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'}`}
          >Tetapan</button>
          <button
            onClick={() => setActiveTab('log')}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${activeTab === 'log' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'}`}
          >Log Respons AI</button>
        </div>

        {activeTab === 'settings' && (
          <div className="bg-white rounded-lg shadow p-6 space-y-6">
            {/* Enable Toggle */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Aktifkan BinaBot</h3>
                <p className="text-sm text-gray-500">AI akan balas pelanggan apabila anda offline</p>
              </div>
              <button
                onClick={() => setSettings({ ...settings, is_enabled: !settings.is_enabled })}
                className={`relative w-14 h-7 rounded-full transition-colors ${settings.is_enabled ? 'bg-blue-600' : 'bg-gray-300'}`}
              >
                <span className={`absolute top-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform ${settings.is_enabled ? 'translate-x-7' : 'translate-x-0.5'}`} />
              </button>
            </div>

            {/* Delay */}
            <div>
              <label className="block font-semibold mb-1">Masa Tunggu Sebelum Balas</label>
              <p className="text-sm text-gray-500 mb-2">AI hanya balas jika pemilik tidak balas dalam masa ini</p>
              <input
                type="range"
                min="30"
                max="600"
                step="30"
                value={settings.delay_seconds}
                onChange={(e) => setSettings({ ...settings, delay_seconds: parseInt(e.target.value) })}
                className="w-full"
              />
              <p className="text-sm text-gray-600 mt-1">{Math.floor(settings.delay_seconds / 60)} minit {settings.delay_seconds % 60} saat</p>
            </div>

            {/* Greeting */}
            <div>
              <label className="block font-semibold mb-1">Ucapan Tersuai</label>
              <textarea
                value={settings.custom_greeting}
                onChange={(e) => setSettings({ ...settings, custom_greeting: e.target.value })}
                rows={3}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Personality */}
            <div>
              <label className="block font-semibold mb-1">Personaliti Bot</label>
              <div className="grid grid-cols-3 gap-3">
                {(['friendly', 'professional', 'casual'] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setSettings({ ...settings, personality: p })}
                    className={`p-3 rounded-lg border-2 text-center transition-colors ${settings.personality === p ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                  >
                    <p className="font-medium capitalize">{p === 'friendly' ? 'Mesra' : p === 'professional' ? 'Profesional' : 'Santai'}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Save */}
            <button
              onClick={saveSettings}
              disabled={saving}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50 transition-colors"
            >
              {saving ? 'Menyimpan...' : 'Simpan Tetapan'}
            </button>
          </div>
        )}

        {activeTab === 'log' && (
          <div className="bg-white rounded-lg shadow">
            {responses.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                Belum ada respons AI. BinaBot akan mula membalas apabila diaktifkan.
              </div>
            ) : (
              <div className="divide-y">
                {responses.map((r) => (
                  <div key={r.id} className="p-4">
                    <div className="bg-gray-50 rounded-lg p-3 mb-2">
                      <p className="text-xs text-gray-500 mb-1">Pelanggan:</p>
                      <p className="text-sm">{r.customer_message}</p>
                    </div>
                    <div className="bg-blue-50 rounded-lg p-3">
                      <p className="text-xs text-blue-500 mb-1">BinaBot:</p>
                      <p className="text-sm">{r.ai_response}</p>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                      {r.model_used} | {r.response_time_ms}ms | {new Date(r.created_at).toLocaleString('ms-MY')}
                    </p>
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
