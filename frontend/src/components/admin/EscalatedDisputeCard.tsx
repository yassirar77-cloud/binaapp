'use client'

import React, { useState } from 'react'

interface EscalatedDisputeCardProps {
  dispute: {
    id: string
    order_id?: string
    user_id?: string
    category?: string
    description?: string
    status: string
    ai_reasoning?: string
    confidence_score?: number
    recommended_action?: string
    credit_amount?: number
    created_at?: string
    evidence_urls?: string[]
  }
  onApprove: (disputeId: string, notes: string) => Promise<void>
  onOverride: (disputeId: string, resolution: string, notes: string, creditAmount?: number) => Promise<void>
  onReject: (disputeId: string, notes: string) => Promise<void>
}

const CATEGORY_LABELS: Record<string, string> = {
  wrong_items: 'Item Salah',
  missing_items: 'Item Hilang',
  quality_issue: 'Isu Kualiti',
  late_delivery: 'Penghantaran Lewat',
  damaged_items: 'Item Rosak',
  overcharged: 'Caj Berlebihan',
  never_delivered: 'Tidak Dihantar',
  rider_issue: 'Isu Rider',
  other: 'Lain-lain',
}

export default function EscalatedDisputeCard({
  dispute,
  onApprove,
  onOverride,
  onReject,
}: EscalatedDisputeCardProps) {
  const [notes, setNotes] = useState('')
  const [creditAmount, setCreditAmount] = useState(String(dispute.credit_amount || ''))
  const [resolution, setResolution] = useState('full_refund')
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const handleAction = async (action: () => Promise<void>) => {
    setLoading(true)
    try {
      await action()
    } finally {
      setLoading(false)
    }
  }

  const confidence = dispute.confidence_score || 0

  return (
    <div className="border rounded-xl bg-white overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-gray-800">
                Aduan #{dispute.id.slice(0, 8)}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                Eskalasi
              </span>
              {dispute.category && (
                <span className="text-xs text-gray-500">
                  {CATEGORY_LABELS[dispute.category] || dispute.category}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600 line-clamp-2">{dispute.description}</p>
          </div>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </div>

        {/* Confidence bar */}
        {confidence > 0 && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs text-gray-500 mb-0.5">
              <span>Keyakinan AI</span>
              <span>{Math.round(confidence * 100)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full"
                style={{
                  width: `${confidence * 100}%`,
                  backgroundColor: confidence > 0.7 ? '#22c55e' : confidence > 0.4 ? '#eab308' : '#ef4444',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="p-4 space-y-4">
          {/* AI Reasoning */}
          {dispute.ai_reasoning && (
            <div className="bg-blue-50 rounded-lg p-3">
              <p className="text-xs font-medium text-blue-700 mb-1">Analisis AI:</p>
              <p className="text-sm text-blue-800">{dispute.ai_reasoning}</p>
            </div>
          )}

          {/* Recommended action */}
          {dispute.recommended_action && (
            <div className="bg-green-50 rounded-lg p-3">
              <p className="text-xs font-medium text-green-700 mb-1">Cadangan:</p>
              <p className="text-sm text-green-800">{dispute.recommended_action}</p>
            </div>
          )}

          {/* Evidence thumbnails */}
          {dispute.evidence_urls && dispute.evidence_urls.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Bukti:</p>
              <div className="flex gap-2 flex-wrap">
                {dispute.evidence_urls.map((url, i) => (
                  <a key={i} href={url} target="_blank" rel="noopener noreferrer">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={url}
                      alt={`Bukti ${i + 1}`}
                      className="w-20 h-20 object-cover rounded border hover:opacity-80"
                    />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Admin notes */}
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">Nota Admin:</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Tambah nota..."
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-blue-400"
              rows={2}
            />
          </div>

          {/* Override resolution type */}
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs font-medium text-gray-500 block mb-1">Jenis Penyelesaian:</label>
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
              >
                <option value="full_refund">Bayaran Balik Penuh</option>
                <option value="partial_refund">Bayaran Balik Separa</option>
                <option value="credit">Kredit Kedai</option>
                <option value="replacement">Ganti</option>
                <option value="rejected">Tolak</option>
              </select>
            </div>
            <div className="w-32">
              <label className="text-xs font-medium text-gray-500 block mb-1">Kredit (RM):</label>
              <input
                type="number"
                value={creditAmount}
                onChange={(e) => setCreditAmount(e.target.value)}
                placeholder="0.00"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                min="0"
                step="0.50"
              />
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 pt-2 border-t">
            <button
              onClick={() => handleAction(() => onApprove(dispute.id, notes))}
              disabled={loading}
              className="flex-1 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              Terima AI
            </button>
            <button
              onClick={() =>
                handleAction(() =>
                  onOverride(dispute.id, resolution, notes, creditAmount ? parseFloat(creditAmount) : undefined)
                )
              }
              disabled={loading}
              className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              Override
            </button>
            <button
              onClick={() => handleAction(() => onReject(dispute.id, notes))}
              disabled={loading}
              className="flex-1 px-4 py-2 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200 disabled:opacity-50 transition-colors"
            >
              Tolak
            </button>
          </div>
        </div>
      )}

      {/* Footer info */}
      <div className="px-4 py-2 bg-gray-50 border-t text-xs text-gray-400 flex justify-between">
        <span>User: {dispute.user_id?.slice(0, 8)}...</span>
        {dispute.created_at && (
          <span>{new Date(dispute.created_at).toLocaleString('ms-MY')}</span>
        )}
      </div>
    </div>
  )
}
