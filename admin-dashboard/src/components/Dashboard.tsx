'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/auth-context'
import { HomePage } from './pages/HomePage'
import { UsersPage } from './pages/UsersPage'
import { RevenuePage } from './pages/RevenuePage'
import { WebsitesPage } from './pages/WebsitesPage'
import { ErrorsPage } from './pages/ErrorsPage'
import { ActivityPage } from './pages/ActivityPage'

type Tab = 'home' | 'users' | 'revenue' | 'websites' | 'errors'

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'users', label: 'Users', icon: 'users' },
  { id: 'revenue', label: 'Money', icon: 'money' },
  { id: 'websites', label: 'Sites', icon: 'globe' },
  { id: 'errors', label: 'Bugs', icon: 'bug' },
]

function TabIcon({ name, active }: { name: string; active: boolean }) {
  const color = active ? '#ea580c' : '#6b7280'
  switch (name) {
    case 'home':
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      )
    case 'users':
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      )
    case 'money':
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="1" x2="12" y2="23" />
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      )
    case 'globe':
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="2" y1="12" x2="22" y2="12" />
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
        </svg>
      )
    case 'bug':
      return (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      )
    default:
      return null
  }
}

export function Dashboard() {
  const { user, signOut } = useAuth()
  const [activeTab, setActiveTab] = useState<Tab>('home')
  const [showActivity, setShowActivity] = useState(false)
  const [errorCount, setErrorCount] = useState(0)

  const fetchErrorCount = useCallback(async () => {
    try {
      const today = new Date().toISOString().split('T')[0] + 'T00:00:00.000Z'
      const res = await fetch(`/api/errors?since=${today}&count_only=true`)
      const data = await res.json()
      setErrorCount(data.count ?? 0)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchErrorCount()
    const interval = setInterval(fetchErrorCount, 30000)
    return () => clearInterval(interval)
  }, [fetchErrorCount])

  if (showActivity) {
    return (
      <div className="min-h-screen bg-gray-950 pb-20">
        <header className="sticky top-0 z-40 bg-gray-950/95 backdrop-blur border-b border-gray-800 px-4 py-3 flex items-center justify-between">
          <button onClick={() => setShowActivity(false)} className="text-gray-400 hover:text-white p-1">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-lg font-semibold text-white">Live Activity</h1>
          <div className="w-8" />
        </header>
        <ActivityPage />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 pb-20">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-gray-950/95 backdrop-blur border-b border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-orange rounded-lg flex items-center justify-center">
            <span className="text-sm font-bold text-white">BA</span>
          </div>
          <h1 className="text-lg font-semibold text-white">BinaApp Admin</h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowActivity(true)}
            className="relative flex items-center gap-1.5 bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg px-3 py-1.5 transition-colors"
          >
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs font-medium text-green-400">Live</span>
          </button>
          <button
            onClick={signOut}
            className="text-gray-500 hover:text-gray-300 p-1"
            title="Sign out"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        </div>
      </header>

      {/* Page Content */}
      <main className="px-4 py-4">
        {activeTab === 'home' && <HomePage />}
        {activeTab === 'users' && <UsersPage />}
        {activeTab === 'revenue' && <RevenuePage />}
        {activeTab === 'websites' && <WebsitesPage />}
        {activeTab === 'errors' && <ErrorsPage />}
      </main>

      {/* Bottom Tab Bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 bg-gray-950/95 backdrop-blur border-t border-gray-800 safe-area-pb">
        <div className="flex items-center justify-around px-2 py-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl transition-colors min-w-[56px] ${
                activeTab === tab.id ? 'text-brand-orange' : 'text-gray-500'
              }`}
            >
              <div className="relative">
                <TabIcon name={tab.icon} active={activeTab === tab.id} />
                {tab.id === 'errors' && errorCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                    {errorCount > 9 ? '9+' : errorCount}
                  </span>
                )}
              </div>
              <span className={`text-[10px] font-medium ${activeTab === tab.id ? 'text-brand-orange' : 'text-gray-500'}`}>
                {tab.label}
              </span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  )
}
