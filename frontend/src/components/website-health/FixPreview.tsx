'use client'

import React, { useState } from 'react'

interface FixPreviewProps {
  fixId: string
  issueType: string
  issueDescription: string
  severity: string
  codeBefore?: string
  codeAfter?: string
  fixDescription?: string
  status: string
  onApply: (fixId: string) => Promise<void>
  onReject: (fixId: string) => Promise<void>
  onRevert?: (fixId: string) => Promise<void>
  onGenerate?: (fixId: string) => Promise<void>
  loading?: boolean
}

const SEVERITY_COLORS: Record<string, string> = {
  minor: 'bg-gray-100 text-gray-700',
  medium: 'bg-yellow-100 text-yellow-700',
  major: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
}

const SEVERITY_LABELS: Record<string, string> = {
  minor: 'Kecil',
  medium: 'Sederhana',
  major: 'Besar',
  critical: 'Kritikal',
}

export default function FixPreview({
  fixId,
  issueType,
  issueDescription,
  severity,
  codeBefore,
  codeAfter,
  fixDescription,
  status,
  onApply,
  onReject,
  onRevert,
  onGenerate,
  loading = false,
}: FixPreviewProps) {
  const [viewMode, setViewMode] = useState<'split' | 'before' | 'after'>('split')
  const [actionLoading, setActionLoading] = useState(false)

  const handleAction = async (action: (id: string) => Promise<void>) => {
    setActionLoading(true)
    try {
      await action(fixId)
    } finally {
      setActionLoading(false)
    }
  }

  const isLoading = loading || actionLoading

  return (
    <div className="border rounded-lg bg-white overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SEVERITY_COLORS[severity] || SEVERITY_COLORS.medium}`}>
                {SEVERITY_LABELS[severity] || severity}
              </span>
              <span className="text-xs text-gray-500 font-mono">{issueType}</span>
              {status === 'applied' && (
                <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                  Diterapkan
                </span>
              )}
              {status === 'rejected' && (
                <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                  Ditolak
                </span>
              )}
              {status === 'reverted' && (
                <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                  Dikembalikan
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700">{issueDescription}</p>
            {fixDescription && (
              <p className="text-xs text-gray-500 mt-1">{fixDescription}</p>
            )}
          </div>
        </div>
      </div>

      {/* Code preview */}
      {(codeBefore || codeAfter) && (
        <div>
          {/* View mode toggle */}
          <div className="flex border-b bg-gray-50 px-4 py-1.5 gap-1">
            {(['split', 'before', 'after'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  viewMode === mode
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:bg-gray-200'
                }`}
              >
                {mode === 'split' ? 'Perbandingan' : mode === 'before' ? 'Sebelum' : 'Selepas'}
              </button>
            ))}
          </div>

          <div className={`${viewMode === 'split' ? 'grid grid-cols-2' : ''}`}>
            {(viewMode === 'split' || viewMode === 'before') && codeBefore && (
              <div className={viewMode === 'split' ? 'border-r' : ''}>
                <div className="bg-red-50 px-3 py-1 text-xs font-medium text-red-700 border-b">
                  Sebelum
                </div>
                <pre className="p-3 text-xs overflow-x-auto max-h-60 bg-gray-50 text-gray-700 whitespace-pre-wrap break-all">
                  {codeBefore.slice(0, 1500)}
                  {codeBefore.length > 1500 && '\n... (truncated)'}
                </pre>
              </div>
            )}
            {(viewMode === 'split' || viewMode === 'after') && codeAfter && (
              <div>
                <div className="bg-green-50 px-3 py-1 text-xs font-medium text-green-700 border-b">
                  Selepas
                </div>
                <pre className="p-3 text-xs overflow-x-auto max-h-60 bg-gray-50 text-gray-700 whitespace-pre-wrap break-all">
                  {codeAfter.slice(0, 1500)}
                  {codeAfter.length > 1500 && '\n... (truncated)'}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="p-3 border-t bg-gray-50 flex items-center gap-2">
        {status === 'pending' && !codeBefore && !codeAfter && onGenerate && (
          <button
            onClick={() => handleAction(onGenerate)}
            disabled={isLoading}
            className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Menjana...' : 'Jana Pembetulan'}
          </button>
        )}
        {status === 'pending' && (codeBefore || codeAfter) && (
          <>
            <button
              onClick={() => handleAction(onApply)}
              disabled={isLoading}
              className="px-4 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {isLoading ? 'Menerapkan...' : 'Terima'}
            </button>
            <button
              onClick={() => handleAction(onReject)}
              disabled={isLoading}
              className="px-4 py-1.5 text-sm bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50 transition-colors"
            >
              Tolak
            </button>
          </>
        )}
        {status === 'applied' && onRevert && (
          <button
            onClick={() => handleAction(onRevert)}
            disabled={isLoading}
            className="px-4 py-1.5 text-sm bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 disabled:opacity-50 transition-colors"
          >
            {isLoading ? 'Mengembalikan...' : 'Kembalikan'}
          </button>
        )}
      </div>
    </div>
  )
}
