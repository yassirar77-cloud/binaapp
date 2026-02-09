'use client'

import React from 'react'

interface ChatBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  imageUrls?: string[]
  actionTaken?: string | null
  actionData?: Record<string, unknown> | null
  timestamp?: string
  isTyping?: boolean
}

const ACTION_DISPLAY: Record<string, { icon: string; color: string; label: string }> = {
  award_credit: { icon: '✅', color: 'bg-green-50 border-green-200 text-green-700', label: 'BinaCredit Ditambah' },
  create_dispute: { icon: '📋', color: 'bg-blue-50 border-blue-200 text-blue-700', label: 'Aduan Dicipta' },
  scan_website: { icon: '🔍', color: 'bg-purple-50 border-purple-200 text-purple-700', label: 'Mengimbas Laman Web' },
  check_order: { icon: '📦', color: 'bg-yellow-50 border-yellow-200 text-yellow-700', label: 'Semakan Pesanan' },
  check_website: { icon: '🌐', color: 'bg-indigo-50 border-indigo-200 text-indigo-700', label: 'Semakan Laman Web' },
  escalate: { icon: '⚠️', color: 'bg-red-50 border-red-200 text-red-700', label: 'Dihantar ke Admin' },
  admin_response: { icon: '👤', color: 'bg-gray-50 border-gray-300 text-gray-700', label: 'Respons Admin' },
}

export default function ChatBubble({
  role,
  content,
  imageUrls,
  actionTaken,
  actionData,
  timestamp,
  isTyping = false,
}: ChatBubbleProps) {
  const isUser = role === 'user'
  const isSystem = role === 'system'

  if (isTyping) {
    return (
      <div className="flex justify-start mb-3">
        <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%]">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-xs text-gray-400 mt-1 block">AI sedang menaip...</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[80%] ${isSystem ? 'w-full' : ''}`}>
        {/* Images */}
        {imageUrls && imageUrls.length > 0 && (
          <div className={`flex gap-2 mb-1 ${isUser ? 'justify-end' : 'justify-start'} flex-wrap`}>
            {imageUrls.map((url, i) => (
              <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={url}
                  alt={`Gambar ${i + 1}`}
                  className="w-32 h-32 object-cover rounded-lg border cursor-pointer hover:opacity-90 transition-opacity"
                />
              </a>
            ))}
          </div>
        )}

        {/* Message bubble */}
        <div
          className={`rounded-2xl px-4 py-2.5 ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : isSystem
                ? 'bg-amber-50 text-amber-800 border border-amber-200 rounded-lg'
                : 'bg-gray-100 text-gray-800 rounded-bl-sm'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
        </div>

        {/* Action card */}
        {actionTaken && ACTION_DISPLAY[actionTaken] && (
          <div className={`mt-1.5 border rounded-lg px-3 py-2 ${ACTION_DISPLAY[actionTaken].color}`}>
            <div className="flex items-center gap-2 text-sm font-medium">
              <span>{ACTION_DISPLAY[actionTaken].icon}</span>
              <span>{ACTION_DISPLAY[actionTaken].label}</span>
            </div>
            {actionData && (
              <div className="mt-1 text-xs opacity-80">
                {actionTaken === 'award_credit' && actionData.credited && (
                  <span>+RM{String(actionData.credited)} telah ditambah ke dompet anda</span>
                )}
                {actionTaken === 'create_dispute' && actionData.dispute_id && (
                  <span>Aduan #{String(actionData.dispute_id).slice(0, 8)} telah dicipta</span>
                )}
                {actionTaken === 'check_order' && actionData.status && (
                  <span>Status: {String(actionData.status)}</span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        {timestamp && (
          <p className={`text-[10px] mt-1 ${isUser ? 'text-right' : 'text-left'} text-gray-400`}>
            {new Date(timestamp).toLocaleTimeString('ms-MY', { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  )
}
