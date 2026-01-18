'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import BinaChat from '@/components/BinaChat'
import { supabase } from '@/lib/supabase'

interface Website {
  id: string
  business_name?: string
  name?: string
  subdomain?: string
}

interface ChatMessage {
  id: string
  message?: string
  content?: string
  message_text?: string
  sender_type?: string
  created_at?: string
}

interface Conversation {
  id: string
  order_id?: string
  website_id: string
  website_name?: string
  customer_name?: string
  customer_phone?: string
  status?: 'active' | 'closed' | 'archived'
  unread_owner?: number
  updated_at?: string
  chat_messages?: ChatMessage[]
}

interface OwnerChatDashboardProps {
  websites: Website[]
  ownerName?: string
  className?: string
}

const getWebsiteLabel = (website: Website) =>
  website.business_name || website.name || 'Website'

const formatTime = (dateString?: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Baru'
  if (diffMins < 60) return `${diffMins}m`
  if (diffHours < 24) return `${diffHours}j`
  if (diffDays < 7) return `${diffDays}h`

  return date.toLocaleDateString('ms-MY', {
    day: 'numeric',
    month: 'short'
  })
}

export default function OwnerChatDashboard({
  websites,
  ownerName,
  className = ''
}: OwnerChatDashboardProps) {
  const [activeWebsiteId, setActiveWebsiteId] = useState<string>('all')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isMobileView, setIsMobileView] = useState(false)
  const [showChatList, setShowChatList] = useState(true)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

  const websiteNameById = useMemo(() => {
    return websites.reduce<Record<string, string>>((acc, site) => {
      acc[site.id] = getWebsiteLabel(site)
      return acc
    }, {})
  }, [websites])

  const selectedConversation = useMemo(() => {
    return conversations.find(conv => conv.id === selectedConversationId) || null
  }, [conversations, selectedConversationId])

  useEffect(() => {
    const checkMobile = () => setIsMobileView(window.innerWidth < 768)
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  useEffect(() => {
    if (websites.length === 1 && activeWebsiteId === 'all') {
      setActiveWebsiteId(websites[0].id)
    }
  }, [websites, activeWebsiteId])

  const loadConversations = useCallback(async () => {
    if (websites.length === 0) {
      setConversations([])
      setIsLoading(false)
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      const session = supabase ? await supabase.auth.getSession() : null
      const accessToken = session?.data.session?.access_token

      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`
      }

      const params = new URLSearchParams()
      if (activeWebsiteId !== 'all') {
        params.set('website_ids', activeWebsiteId)
      }

      const url = params.toString()
        ? `${API_URL}/api/v1/chat/conversations?${params.toString()}`
        : `${API_URL}/api/v1/chat/conversations`

      const res = await fetch(url, { headers })
      if (!res.ok) {
        throw new Error(`Failed to load conversations (${res.status})`)
      }

      const data = await res.json()
      const conversationsData = Array.isArray(data)
        ? data
        : data.conversations || []
      setConversations(conversationsData)
    } catch (err) {
      console.error('[OwnerChatDashboard] Failed to load conversations:', err)
      setError('Gagal memuatkan perbualan. Sila cuba lagi.')
    } finally {
      setIsLoading(false)
    }
  }, [API_URL, activeWebsiteId, websites.length])

  useEffect(() => {
    loadConversations()
    const interval = setInterval(loadConversations, 30000)
    return () => clearInterval(interval)
  }, [loadConversations])

  const handleSelectConversation = (conversationId: string) => {
    setSelectedConversationId(conversationId)
    if (isMobileView) {
      setShowChatList(false)
    }
  }

  const renderConversationItem = (conv: Conversation) => {
    const isSelected = conv.id === selectedConversationId
    const lastMessage = conv.chat_messages?.[conv.chat_messages.length - 1]
    const lastMessageText =
      lastMessage?.message_text || lastMessage?.content || lastMessage?.message || 'Tiada mesej'
    const unreadCount = conv.unread_owner || 0
    const hasUnread = unreadCount > 0
    const websiteLabel =
      conv.website_name || websiteNameById[conv.website_id] || 'Website'

    return (
      <div
        key={conv.id}
        onClick={() => handleSelectConversation(conv.id)}
        className={`p-3 border-b cursor-pointer transition-colors ${
          isSelected
            ? 'bg-orange-50 border-l-4 border-l-orange-500'
            : 'hover:bg-gray-50 border-l-4 border-l-transparent'
        }`}
      >
        <div className="flex items-start gap-3">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold ${
              hasUnread ? 'bg-orange-500' : 'bg-gray-400'
            }`}
          >
            {conv.customer_name?.charAt(0).toUpperCase() || '?'}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-0.5">
              <div className="font-medium text-sm truncate">
                {conv.customer_name || 'Pelanggan'}
              </div>
              <div className="text-xs text-gray-400 flex-shrink-0 ml-2">
                {formatTime(conv.updated_at)}
              </div>
            </div>

            {conv.customer_phone && (
              <div className="text-xs text-gray-500 flex items-center gap-1">
                <span>📱</span>
                <span className="truncate">{conv.customer_phone}</span>
              </div>
            )}

            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                🌐 {websiteLabel}
              </span>
              {conv.status === 'closed' && (
                <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                  Ditutup
                </span>
              )}
            </div>

            <div className="text-xs text-gray-500 truncate mt-1">
              {lastMessage?.sender_type === 'owner' && (
                <span className="text-gray-400">Anda: </span>
              )}
              {lastMessageText}
            </div>
          </div>

          {hasUnread && (
            <span className="bg-orange-500 text-white text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex flex-wrap gap-2">
        {websites.length > 1 && (
          <button
            onClick={() => setActiveWebsiteId('all')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeWebsiteId === 'all'
                ? 'bg-orange-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Semua
          </button>
        )}
        {websites.map(site => (
          <button
            key={site.id}
            onClick={() => setActiveWebsiteId(site.id)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeWebsiteId === site.id
                ? 'bg-orange-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {getWebsiteLabel(site)}
          </button>
        ))}
      </div>

      <div className="flex flex-col md:flex-row h-[calc(100vh-320px)] md:h-[640px] max-h-[800px] border rounded-lg overflow-hidden bg-white">
        {isMobileView && (
          <div className="md:hidden bg-gray-50 p-2 border-b">
            <button
              onClick={() => setShowChatList(!showChatList)}
              className="w-full py-2 px-4 bg-orange-500 text-white rounded-lg font-medium text-sm flex items-center justify-center gap-2 min-h-[44px]"
            >
              {showChatList ? 'Lihat Chat' : 'Senarai Chat'}
            </button>
          </div>
        )}

        <div className={`${showChatList ? 'flex' : 'hidden'} md:flex w-full md:w-96 border-r bg-white flex-shrink-0`}>
          <div className="flex flex-col h-full w-full">
            <div className="flex items-center justify-between px-4 py-3 border-b bg-gradient-to-r from-orange-500 to-orange-600 text-white">
              <div className="font-semibold text-sm">Senarai Perbualan</div>
              <button
                onClick={loadConversations}
                className="p-1.5 hover:bg-white/20 rounded-full transition-colors"
                title="Muat semula"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin w-6 h-6 border-3 border-orange-500 border-t-transparent rounded-full" />
                </div>
              ) : error ? (
                <div className="p-4 text-center text-red-500 text-sm">
                  {error}
                  <button
                    onClick={loadConversations}
                    className="block mx-auto mt-2 text-orange-500 underline"
                  >
                    Cuba lagi
                  </button>
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <div className="text-4xl mb-2">💬</div>
                  <div className="text-sm font-medium">Tiada perbualan lagi</div>
                  <div className="text-xs text-gray-400 mt-2">
                    Pelanggan boleh chat melalui butang di website anda
                  </div>
                </div>
              ) : (
                conversations.map(renderConversationItem)
              )}
            </div>

            <div className="p-3 border-t bg-gray-50 text-xs text-gray-500 flex items-center justify-between">
              <span>{conversations.length} perbualan</span>
              <span>
                {conversations.reduce((sum, c) => sum + (c.unread_owner || 0), 0)} belum dibaca
              </span>
            </div>
          </div>
        </div>

        <div className={`${!showChatList ? 'flex' : 'hidden'} md:flex flex-1 bg-white`}>
          {selectedConversation ? (
            <BinaChat
              conversationId={selectedConversation.id}
              userType="owner"
              userId={selectedConversation.website_id}
              userName={
                selectedConversation.website_name ||
                websiteNameById[selectedConversation.website_id] ||
                ownerName ||
                'Pemilik Kedai'
              }
              orderId={selectedConversation.order_id}
              showMap={true}
              className="h-full w-full"
            />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500 w-full">
              <div className="text-center p-4 max-w-md">
                <div className="text-4xl md:text-6xl mb-4">💬</div>
                <p className="text-sm md:text-lg font-medium mb-2">
                  Pilih perbualan untuk mula chat
                </p>
                <p className="text-xs md:text-sm text-gray-400">
                  Pelanggan boleh bertanya soalan melalui butang chat di website anda
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
