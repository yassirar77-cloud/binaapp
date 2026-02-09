'use client'

import React, { useState } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  image_urls?: string[]
  action_taken?: string
  action_data?: Record<string, unknown>
  created_at?: string
}

interface ChatViewerProps {
  chatId: string
  messages: Message[]
  chatStatus?: string
  onAdminRespond: (chatId: string, message: string) => Promise<void>
  onResolve?: (chatId: string) => Promise<void>
}

export default function ChatViewer({
  chatId,
  messages,
  chatStatus,
  onAdminRespond,
  onResolve,
}: ChatViewerProps) {
  const [adminMessage, setAdminMessage] = useState('')
  const [sending, setSending] = useState(false)

  const handleSend = async () => {
    if (!adminMessage.trim() || sending) return
    setSending(true)
    try {
      await onAdminRespond(chatId, adminMessage.trim())
      setAdminMessage('')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="border rounded-xl bg-white overflow-hidden flex flex-col max-h-[600px]">
      {/* Header */}
      <div className="p-3 border-b bg-gray-50 flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold text-gray-700">Chat #{chatId.slice(0, 8)}</span>
          {chatStatus && (
            <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
              chatStatus === 'escalated' ? 'bg-red-100 text-red-700' :
              chatStatus === 'active' ? 'bg-green-100 text-green-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {chatStatus}
            </span>
          )}
        </div>
        {onResolve && chatStatus !== 'closed' && chatStatus !== 'resolved' && (
          <button
            onClick={() => onResolve(chatId)}
            className="text-xs px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Selesai
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => {
          const isUser = msg.role === 'user'
          const isSystem = msg.role === 'system'

          return (
            <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] ${isSystem ? 'w-full' : ''}`}>
                {/* Role label */}
                <p className={`text-[10px] mb-0.5 ${isUser ? 'text-right' : 'text-left'} text-gray-400`}>
                  {isUser ? 'Pengguna' : isSystem ? 'Admin' : 'AI'}
                </p>

                {/* Images */}
                {msg.image_urls && msg.image_urls.length > 0 && (
                  <div className={`flex gap-1 mb-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
                    {msg.image_urls.map((url, i) => (
                      <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={url} alt={`Img ${i + 1}`} className="w-24 h-24 object-cover rounded border" />
                      </a>
                    ))}
                  </div>
                )}

                <div
                  className={`rounded-xl px-3 py-2 text-sm ${
                    isUser
                      ? 'bg-blue-600 text-white'
                      : isSystem
                        ? 'bg-amber-50 text-amber-800 border border-amber-200'
                        : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                </div>

                {/* Action indicator */}
                {msg.action_taken && (
                  <p className="text-[10px] text-purple-600 mt-0.5">
                    Tindakan: {msg.action_taken}
                  </p>
                )}

                {/* Timestamp */}
                {msg.created_at && (
                  <p className={`text-[10px] mt-0.5 text-gray-400 ${isUser ? 'text-right' : ''}`}>
                    {new Date(msg.created_at).toLocaleString('ms-MY')}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Admin input */}
      <div className="border-t p-3 bg-gray-50">
        <div className="flex gap-2">
          <input
            type="text"
            value={adminMessage}
            onChange={(e) => setAdminMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Balas sebagai admin..."
            className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={!adminMessage.trim() || sending}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {sending ? '...' : 'Hantar'}
          </button>
        </div>
      </div>
    </div>
  )
}
