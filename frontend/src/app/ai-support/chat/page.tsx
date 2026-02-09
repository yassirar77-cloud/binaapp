'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getStoredToken } from '@/lib/supabase'
import ChatBubble from '@/components/ai-chat/ChatBubble'
import ChatInput from '@/components/ai-chat/ChatInput'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  image_urls?: string[]
  image_analysis?: unknown
  action_taken?: string
  action_data?: Record<string, unknown>
  created_at?: string
}

interface Chat {
  id: string
  title?: string
  status: string
  category?: string
  messages_count: number
  credit_awarded?: number
  created_at?: string
  updated_at?: string
}

export default function AIChatPage() {
  const router = useRouter()
  const [chats, setChats] = useState<Chat[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showSidebar, setShowSidebar] = useState(false)
  const [showRating, setShowRating] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  const getHeaders = useCallback((): Record<string, string> | null => {
    const token = getStoredToken()
    if (!token) {
      router.push('/login?redirect=/ai-support/chat')
      return null
    }
    return {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  }, [router])

  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    const headers = getHeaders()
    if (!headers) throw new Error('Not authenticated')
    const res = await fetch(`${API_BASE}${path}`, { headers, ...options })
    if (res.status === 401) {
      router.push('/login?redirect=/ai-support/chat')
      throw new Error('Session expired')
    }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Request failed')
    }
    return res.json()
  }, [getHeaders, router])

  // Load active chats on mount
  useEffect(() => {
    async function loadChats() {
      try {
        const data = await apiFetch('/api/v1/ai-chat/active')
        setChats(data.chats || [])
      } catch (err) {
        console.error('Failed to load chats:', err)
      } finally {
        setLoading(false)
      }
    }
    loadChats()
  }, [apiFetch])

  const startNewChat = async () => {
    try {
      const data = await apiFetch('/api/v1/ai-chat/start', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      setActiveChatId(data.chat_id)
      // Load messages for the new chat
      const msgsData = await apiFetch(`/api/v1/ai-chat/${data.chat_id}/messages`)
      setMessages(msgsData.messages || [])
      setChats((prev) => [{ id: data.chat_id, status: 'active', messages_count: 1 }, ...prev])
    } catch (err) {
      console.error('Failed to start chat:', err)
    }
  }

  const loadChatMessages = async (chatId: string) => {
    setActiveChatId(chatId)
    setShowSidebar(false)
    try {
      const data = await apiFetch(`/api/v1/ai-chat/${chatId}/messages`)
      setMessages(data.messages || [])
    } catch (err) {
      console.error('Failed to load messages:', err)
    }
  }

  const sendMessage = async (text: string, imageUrls: string[]) => {
    if (!activeChatId) return

    // Optimistic: add user message
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      image_urls: imageUrls.length > 0 ? imageUrls : undefined,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setIsTyping(true)

    try {
      const data = await apiFetch(`/api/v1/ai-chat/${activeChatId}/message`, {
        method: 'POST',
        body: JSON.stringify({
          message: text,
          image_urls: imageUrls.length > 0 ? imageUrls : null,
        }),
      })

      // Replace temp message and add AI response
      const aiMsg: Message = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        content: data.message,
        action_taken: data.action?.toLowerCase() || null,
        action_data: data.action_result,
        created_at: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, aiMsg])
    } catch (err) {
      console.error('Failed to send message:', err)
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: 'Maaf, terdapat masalah teknikal. Sila cuba lagi.',
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsTyping(false)
    }
  }

  const uploadImage = async (file: File): Promise<string> => {
    if (!activeChatId) throw new Error('No active chat')
    const token = getStoredToken()
    if (!token) throw new Error('Not authenticated')

    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(`${API_BASE}/api/v1/ai-chat/${activeChatId}/upload-image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })

    if (!res.ok) throw new Error('Upload failed')
    const data = await res.json()
    return data.url
  }

  const closeChat = async () => {
    if (!activeChatId) return
    try {
      await apiFetch(`/api/v1/ai-chat/${activeChatId}/close`, { method: 'POST' })
      setShowRating(true)
    } catch (err) {
      console.error('Failed to close chat:', err)
    }
  }

  const rateChat = async (rating: number) => {
    if (!activeChatId) return
    try {
      await apiFetch(`/api/v1/ai-chat/${activeChatId}/rate`, {
        method: 'POST',
        body: JSON.stringify({ rating }),
      })
      setShowRating(false)
      setActiveChatId(null)
      setMessages([])
      // Refresh chat list
      const data = await apiFetch('/api/v1/ai-chat/active')
      setChats(data.chats || [])
    } catch (err) {
      console.error('Failed to rate:', err)
    }
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
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-20">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="md:hidden p-1.5 rounded-lg hover:bg-gray-100"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-bold text-gray-800">BinaBot</h1>
              <p className="text-xs text-gray-500">Pembantu AI anda</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {activeChatId && (
              <button
                onClick={closeChat}
                className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Tutup Chat
              </button>
            )}
            <Link href="/ai-support" className="text-sm text-blue-600 hover:underline">
              Kembali
            </Link>
          </div>
        </div>
      </header>

      <div className="flex-1 flex max-w-4xl mx-auto w-full">
        {/* Sidebar */}
        <aside className={`${showSidebar ? 'block' : 'hidden'} md:block w-64 bg-white border-r flex-shrink-0`}>
          <div className="p-3">
            <button
              onClick={startNewChat}
              className="w-full px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
            >
              + Chat Baru
            </button>
          </div>
          <div className="overflow-y-auto max-h-[calc(100vh-140px)]">
            {chats.map((chat) => (
              <button
                key={chat.id}
                onClick={() => loadChatMessages(chat.id)}
                className={`w-full text-left px-4 py-3 border-b text-sm hover:bg-gray-50 transition-colors ${
                  activeChatId === chat.id ? 'bg-blue-50 border-l-2 border-l-blue-600' : ''
                }`}
              >
                <p className="font-medium text-gray-700 truncate">
                  {chat.title || `Chat #${chat.id.slice(0, 6)}`}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    chat.status === 'active' ? 'bg-green-500' :
                    chat.status === 'escalated' ? 'bg-red-500' :
                    'bg-gray-400'
                  }`} />
                  <span className="text-xs text-gray-400">{chat.status}</span>
                  {chat.credit_awarded ? (
                    <span className="text-xs text-green-600">+RM{chat.credit_awarded}</span>
                  ) : null}
                </div>
              </button>
            ))}
            {chats.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-6">Tiada chat aktif</p>
            )}
          </div>
        </aside>

        {/* Chat area */}
        <div className="flex-1 flex flex-col bg-white">
          {!activeChatId ? (
            <div className="flex-1 flex items-center justify-center text-center p-8">
              <div>
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-blue-600">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-gray-700 mb-2">Selamat datang ke BinaBot</h2>
                <p className="text-sm text-gray-500 mb-4">
                  Mulakan chat baru untuk mendapatkan bantuan AI
                </p>
                <button
                  onClick={startNewChat}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  Mulakan Chat Baru
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4">
                {messages.map((msg) => (
                  <ChatBubble
                    key={msg.id}
                    role={msg.role}
                    content={msg.content}
                    imageUrls={msg.image_urls}
                    actionTaken={msg.action_taken}
                    actionData={msg.action_data}
                    timestamp={msg.created_at}
                  />
                ))}
                {isTyping && <ChatBubble role="assistant" content="" isTyping />}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <ChatInput
                onSend={sendMessage}
                onUploadImage={uploadImage}
                disabled={isTyping}
                placeholder="Taip mesej anda..."
              />
            </>
          )}

          {/* Rating modal */}
          {showRating && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
              <div className="bg-white rounded-2xl p-6 max-w-sm mx-4 text-center">
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Bagaimana pengalaman anda?</h3>
                <p className="text-sm text-gray-500 mb-4">Sila berikan penilaian</p>
                <div className="flex justify-center gap-3 mb-4">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => rateChat(star)}
                      className="text-3xl hover:scale-110 transition-transform"
                    >
                      {star <= 3 ? (star === 1 ? '😞' : star === 2 ? '😐' : '🙂') : star === 4 ? '😊' : '🤩'}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => { setShowRating(false); setActiveChatId(null); setMessages([]) }}
                  className="text-sm text-gray-400 hover:underline"
                >
                  Langkau
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
