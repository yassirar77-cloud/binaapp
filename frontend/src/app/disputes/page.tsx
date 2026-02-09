'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { getStoredToken } from '@/lib/supabase'
import { Dispute, DisputeMessage, DisputeSummary, DisputeCategory, DisputeResolutionType } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

// Category labels & icons
const CATEGORY_INFO: Record<DisputeCategory, { label: string; icon: string }> = {
  wrong_items: { label: 'Wrong Items', icon: 'swap_horiz' },
  missing_items: { label: 'Missing Items', icon: 'remove_shopping_cart' },
  quality_issue: { label: 'Quality Issue', icon: 'thumb_down' },
  late_delivery: { label: 'Late Delivery', icon: 'schedule' },
  damaged_items: { label: 'Damaged Items', icon: 'broken_image' },
  overcharged: { label: 'Overcharged', icon: 'attach_money' },
  never_delivered: { label: 'Never Delivered', icon: 'cancel' },
  rider_issue: { label: 'Rider Issue', icon: 'person_off' },
  other: { label: 'Other', icon: 'help_outline' },
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-yellow-100 text-yellow-800',
  under_review: 'bg-blue-100 text-blue-800',
  awaiting_response: 'bg-purple-100 text-purple-800',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-800',
  escalated: 'bg-red-100 text-red-800',
  rejected: 'bg-red-100 text-red-800',
}

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-gray-100 text-gray-600',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-orange-100 text-orange-700',
  urgent: 'bg-red-100 text-red-700',
}

const RESOLUTION_LABELS: Record<string, string> = {
  full_refund: 'Full Refund',
  partial_refund: 'Partial Refund',
  replacement: 'Replacement Order',
  credit: 'Store Credit',
  apology: 'Apology',
  rejected: 'Rejected',
  escalated: 'Escalated',
}

// Subscriber dispute categories (complaints against BinaApp)
const SUBSCRIBER_CATEGORIES = [
  { key: 'poor_design', icon: '\uD83C\uDFA8', label: 'Reka Bentuk Buruk', desc: 'Laman web yang dijana tidak memuaskan' },
  { key: 'website_bug', icon: '\uD83C\uDF10', label: 'Masalah Laman Web', desc: 'Laman web tidak berfungsi dengan betul' },
  { key: 'service_outage', icon: '\u26A1', label: 'Gangguan Perkhidmatan', desc: 'Platform BinaApp tidak boleh diakses' },
  { key: 'payment_issue', icon: '\uD83D\uDCB3', label: 'Masalah Pembayaran', desc: 'Caj salah atau pembayaran gagal' },
  { key: 'technical_problem', icon: '\uD83D\uDC1B', label: 'Masalah Teknikal', desc: 'Fungsi tidak berjalan seperti sepatutnya' },
  { key: 'order_system', icon: '\uD83D\uDCF1', label: 'Masalah Pesanan', desc: 'Sistem pesanan atau penghantaran bermasalah' },
  { key: 'chat_issue', icon: '\uD83D\uDCAC', label: 'Masalah Chat', desc: 'Chat widget tidak berfungsi' },
  { key: 'other', icon: '\u2753', label: 'Lain-lain', desc: 'Masalah lain yang tidak disenaraikan' },
] as const

export default function DisputesPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [disputes, setDisputes] = useState<Dispute[]>([])
  const [summary, setSummary] = useState<DisputeSummary | null>(null)
  const [selectedDispute, setSelectedDispute] = useState<Dispute | null>(null)
  const [messages, setMessages] = useState<DisputeMessage[]>([])
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [activeTab, setActiveTab] = useState<'all' | 'open' | 'resolved'>('all')
  const [showResolveModal, setShowResolveModal] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [sendingReply, setSendingReply] = useState(false)

  // Resolve form state
  const [resolveType, setResolveType] = useState<DisputeResolutionType>('partial_refund')
  const [resolveNotes, setResolveNotes] = useState('')
  const [refundAmount, setRefundAmount] = useState('')
  const [resolving, setResolving] = useState(false)

  // Create subscriber dispute state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createStep, setCreateStep] = useState<'form' | 'submitting' | 'result'>('form')
  const [createCategory, setCreateCategory] = useState('')
  const [createDescription, setCreateDescription] = useState('')
  const [createWebsiteId, setCreateWebsiteId] = useState('')
  const [createEvidence, setCreateEvidence] = useState<string[]>([])
  const [createResult, setCreateResult] = useState<{ status: string; message: string; amount?: number } | null>(null)
  const [websites, setWebsites] = useState<{ id: string; name: string }[]>([])

  useEffect(() => {
    loadDisputes()
    loadSummary()
    loadWebsites()
  }, [activeTab])

  async function loadDisputes() {
    const token = getStoredToken()
    if (!token) {
      router.push('/login?redirect=/disputes')
      return
    }

    setLoading(true)
    try {
      let url = `${API_BASE}/api/v1/disputes/owner/list?per_page=50`
      if (activeTab === 'open') url += '&status=open'
      else if (activeTab === 'resolved') url += '&status=resolved'

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        const data = await res.json()
        setDisputes(data.disputes || [])
      } else if (res.status === 401) {
        router.push('/login?error=session_expired&redirect=/disputes')
      }
    } catch (error) {
      console.error('[Disputes] Error loading:', error)
    } finally {
      setLoading(false)
    }
  }

  async function loadSummary() {
    const token = getStoredToken()
    if (!token) return

    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/owner/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        const data = await res.json()
        setSummary(data)
      }
    } catch (error) {
      console.error('[Disputes] Error loading summary:', error)
    }
  }

  async function loadMessages(disputeId: string) {
    const token = getStoredToken()
    if (!token) return

    setLoadingMessages(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/owner/${disputeId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
      }
    } catch (error) {
      console.error('[Disputes] Error loading messages:', error)
    } finally {
      setLoadingMessages(false)
    }
  }

  async function sendReply() {
    if (!replyText.trim() || !selectedDispute) return

    const token = getStoredToken()
    if (!token) return

    setSendingReply(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/owner/${selectedDispute.id}/message`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: replyText,
          sender_type: 'owner',
          sender_name: 'Business Owner',
        }),
      })

      if (res.ok) {
        setReplyText('')
        loadMessages(selectedDispute.id)
      }
    } catch (error) {
      console.error('[Disputes] Error sending reply:', error)
    } finally {
      setSendingReply(false)
    }
  }

  async function resolveDispute() {
    if (!selectedDispute) return

    const token = getStoredToken()
    if (!token) return

    setResolving(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/owner/${selectedDispute.id}/resolve`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resolution_type: resolveType,
          resolution_notes: resolveNotes,
          refund_amount: refundAmount ? parseFloat(refundAmount) : null,
        }),
      })

      if (res.ok) {
        setShowResolveModal(false)
        setSelectedDispute(null)
        loadDisputes()
        loadSummary()
      }
    } catch (error) {
      console.error('[Disputes] Error resolving:', error)
    } finally {
      setResolving(false)
    }
  }

  async function escalateDispute(disputeId: string) {
    const token = getStoredToken()
    if (!token) return

    if (!confirm('Are you sure you want to escalate this dispute to the BinaApp team?')) return

    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/owner/${disputeId}/escalate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        loadDisputes()
        loadSummary()
        if (selectedDispute?.id === disputeId) {
          setSelectedDispute(null)
        }
      }
    } catch (error) {
      console.error('[Disputes] Error escalating:', error)
    }
  }

  function selectDispute(dispute: Dispute) {
    setSelectedDispute(dispute)
    loadMessages(dispute.id)
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString('en-MY', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  async function loadWebsites() {
    const token = getStoredToken()
    if (!token) return
    try {
      const res = await fetch(`${API_BASE}/api/v1/websites/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setWebsites((data.websites || data || []).map((w: any) => ({ id: w.id, name: w.name || w.business_name || w.domain || 'Website' })))
      }
    } catch (error) {
      console.error('[Disputes] Error loading websites:', error)
    }
  }

  function handleEvidenceUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files) return
    const remaining = 5 - createEvidence.length
    const toProcess = Array.from(files).slice(0, remaining)
    toProcess.forEach((file) => {
      const reader = new FileReader()
      reader.onload = () => {
        setCreateEvidence((prev) => {
          if (prev.length >= 5) return prev
          return [...prev, reader.result as string]
        })
      }
      reader.readAsDataURL(file)
    })
    e.target.value = ''
  }

  function removeEvidence(index: number) {
    setCreateEvidence((prev) => prev.filter((_, i) => i !== index))
  }

  function openCreateModal() {
    setCreateStep('form')
    setCreateCategory('')
    setCreateDescription('')
    setCreateWebsiteId('')
    setCreateEvidence([])
    setCreateResult(null)
    setShowCreateModal(true)
  }

  function closeCreateModal() {
    setShowCreateModal(false)
    if (createResult) {
      loadDisputes()
      loadSummary()
    }
  }

  async function submitSubscriberDispute() {
    if (!createCategory || createDescription.length < 10) return

    const token = getStoredToken()
    if (!token) return

    setCreateStep('submitting')
    try {
      const severity =
        createCategory === 'service_outage' || createCategory === 'payment_issue'
          ? 'high'
          : createCategory === 'technical_problem' || createCategory === 'order_system'
          ? 'medium'
          : 'low'

      const res = await fetch(`${API_BASE}/api/v1/disputes/create`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          category: createCategory,
          description: createDescription,
          website_id: createWebsiteId || undefined,
          evidence_urls: createEvidence.length > 0 ? createEvidence : undefined,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        const status = data.status || data.ai_decision || 'under_review'
        if (status === 'approved' || status === 'resolved') {
          setCreateResult({
            status: 'approved',
            message: `BinaCredit RM${(data.refund_amount || data.credit_amount || 0).toFixed(2)} telah ditambah ke akaun anda`,
            amount: data.refund_amount || data.credit_amount,
          })
        } else if (status === 'rejected') {
          setCreateResult({
            status: 'rejected',
            message: 'Aduan tidak dapat disahkan. Anda boleh mengemukakan bukti tambahan.',
          })
        } else {
          setCreateResult({
            status: 'under_review',
            message: 'Aduan anda telah dihantar untuk semakan lanjut',
          })
        }
      } else {
        setCreateResult({
          status: 'under_review',
          message: 'Aduan anda telah dihantar untuk semakan lanjut',
        })
      }
      setCreateStep('result')
    } catch (error) {
      console.error('[Disputes] Error creating subscriber dispute:', error)
      setCreateResult({
        status: 'under_review',
        message: 'Aduan anda telah dihantar. Kami akan menyemak secepat mungkin.',
      })
      setCreateStep('result')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/profile" className="text-gray-500 hover:text-gray-700">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Dispute Resolution</h1>
              <p className="text-sm text-gray-500">AI-powered dispute management</p>
            </div>
          </div>
          <button
            onClick={openCreateModal}
            className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 flex items-center gap-2 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Buat Aduan Baru
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <p className="text-sm text-gray-500">Total Disputes</p>
              <p className="text-2xl font-bold text-gray-900">{summary.total_disputes}</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-yellow-200 bg-yellow-50">
              <p className="text-sm text-yellow-600">Open</p>
              <p className="text-2xl font-bold text-yellow-700">{summary.open_disputes}</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-green-200 bg-green-50">
              <p className="text-sm text-green-600">Resolved</p>
              <p className="text-2xl font-bold text-green-700">{summary.resolved_disputes}</p>
            </div>
            <div className="bg-white rounded-xl p-4 border border-gray-200">
              <p className="text-sm text-gray-500">Resolution Rate</p>
              <p className="text-2xl font-bold text-gray-900">{summary.resolution_rate}%</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {(['all', 'open', 'resolved'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => { setActiveTab(tab); setSelectedDispute(null) }}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {tab === 'all' ? 'All Disputes' : tab === 'open' ? 'Open' : 'Resolved'}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Dispute List */}
          <div className="lg:col-span-1">
            {loading ? (
              <div className="bg-white rounded-xl p-8 text-center border border-gray-200">
                <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-gray-500">Loading disputes...</p>
              </div>
            ) : disputes.length === 0 ? (
              <div className="bg-white rounded-xl p-8 text-center border border-gray-200">
                <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-gray-500 font-medium">No disputes found</p>
                <p className="text-gray-400 text-sm mt-1">All clear! No customer disputes to handle.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {disputes.map((dispute) => (
                  <button
                    key={dispute.id}
                    onClick={() => selectDispute(dispute)}
                    className={`w-full text-left bg-white rounded-xl p-4 border transition-all hover:shadow-md ${
                      selectedDispute?.id === dispute.id
                        ? 'border-indigo-500 ring-2 ring-indigo-100'
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-sm font-mono font-medium text-gray-900">
                        #{dispute.dispute_number}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[dispute.status] || 'bg-gray-100 text-gray-600'}`}>
                        {dispute.status.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-800 mb-1">
                      {CATEGORY_INFO[dispute.category]?.label || dispute.category}
                    </p>
                    <p className="text-xs text-gray-500 line-clamp-2 mb-2">{dispute.description}</p>
                    <div className="flex items-center justify-between text-xs text-gray-400">
                      <span>{dispute.customer_name}</span>
                      <span>RM{dispute.order_amount?.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`px-2 py-0.5 rounded text-xs ${PRIORITY_COLORS[dispute.priority] || 'bg-gray-100 text-gray-600'}`}>
                        {dispute.priority}
                      </span>
                      {dispute.ai_severity_score && (
                        <span className="text-xs text-gray-400">
                          Severity: {dispute.ai_severity_score}/10
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Dispute Detail */}
          <div className="lg:col-span-2">
            {selectedDispute ? (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Detail Header */}
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-lg font-bold text-gray-900">
                        Dispute #{selectedDispute.dispute_number}
                      </h2>
                      <p className="text-sm text-gray-500">{formatDate(selectedDispute.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[selectedDispute.status]}`}>
                        {selectedDispute.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">Category</p>
                      <p className="font-medium">{CATEGORY_INFO[selectedDispute.category]?.label}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Customer</p>
                      <p className="font-medium">{selectedDispute.customer_name}</p>
                      {selectedDispute.customer_phone && (
                        <p className="text-xs text-gray-400">{selectedDispute.customer_phone}</p>
                      )}
                    </div>
                    <div>
                      <p className="text-gray-500">Order Amount</p>
                      <p className="font-medium">RM{selectedDispute.order_amount?.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Priority</p>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_COLORS[selectedDispute.priority]}`}>
                        {selectedDispute.priority.toUpperCase()}
                      </span>
                    </div>
                    {selectedDispute.disputed_amount && (
                      <div>
                        <p className="text-gray-500">Disputed Amount</p>
                        <p className="font-medium text-red-600">RM{selectedDispute.disputed_amount?.toFixed(2)}</p>
                      </div>
                    )}
                    {selectedDispute.resolution_type && (
                      <div>
                        <p className="text-gray-500">Resolution</p>
                        <p className="font-medium text-green-600">{RESOLUTION_LABELS[selectedDispute.resolution_type]}</p>
                      </div>
                    )}
                  </div>

                  <div className="mt-4">
                    <p className="text-gray-500 text-sm mb-1">Description</p>
                    <p className="text-gray-800 text-sm bg-gray-50 rounded-lg p-3">{selectedDispute.description}</p>
                  </div>
                </div>

                {/* AI Analysis Section */}
                {selectedDispute.ai_analysis && (
                  <div className="p-6 border-b border-gray-100 bg-indigo-50/50">
                    <h3 className="text-sm font-semibold text-indigo-800 mb-3 flex items-center gap-2">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      AI Analysis
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                      <div className="bg-white rounded-lg p-2.5">
                        <p className="text-xs text-gray-500">Confidence</p>
                        <p className="font-bold text-indigo-700">
                          {((selectedDispute.ai_analysis.category_confidence || 0) * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div className="bg-white rounded-lg p-2.5">
                        <p className="text-xs text-gray-500">Severity</p>
                        <p className="font-bold text-indigo-700">{selectedDispute.ai_analysis.severity_score}/10</p>
                      </div>
                      <div className="bg-white rounded-lg p-2.5">
                        <p className="text-xs text-gray-500">Recommendation</p>
                        <p className="font-bold text-indigo-700 text-xs">
                          {RESOLUTION_LABELS[selectedDispute.ai_analysis.recommended_resolution] || selectedDispute.ai_analysis.recommended_resolution}
                        </p>
                      </div>
                      {selectedDispute.ai_analysis.recommended_refund_percentage !== undefined && (
                        <div className="bg-white rounded-lg p-2.5">
                          <p className="text-xs text-gray-500">Refund %</p>
                          <p className="font-bold text-indigo-700">{selectedDispute.ai_analysis.recommended_refund_percentage}%</p>
                        </div>
                      )}
                    </div>
                    {selectedDispute.ai_analysis.reasoning && (
                      <p className="text-sm text-indigo-700 bg-white rounded-lg p-3">
                        {selectedDispute.ai_analysis.reasoning}
                      </p>
                    )}
                    {selectedDispute.ai_analysis.risk_flags && selectedDispute.ai_analysis.risk_flags.length > 0 && (
                      <div className="flex gap-2 mt-2">
                        {selectedDispute.ai_analysis.risk_flags.map((flag, i) => (
                          <span key={i} className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">
                            {flag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Messages */}
                <div className="p-6 border-b border-gray-100">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">Messages</h3>
                  {loadingMessages ? (
                    <div className="text-center py-4">
                      <div className="animate-spin w-6 h-6 border-3 border-indigo-600 border-t-transparent rounded-full mx-auto" />
                    </div>
                  ) : messages.length === 0 ? (
                    <p className="text-gray-400 text-sm text-center py-4">No messages yet</p>
                  ) : (
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {messages.map((msg) => (
                        <div
                          key={msg.id}
                          className={`rounded-lg p-3 ${
                            msg.sender_type === 'system'
                              ? 'bg-gray-50 text-gray-500 text-center text-xs'
                              : msg.sender_type === 'ai'
                              ? 'bg-indigo-50 border-l-4 border-indigo-400'
                              : msg.sender_type === 'owner'
                              ? 'bg-blue-50 border-l-4 border-blue-400'
                              : 'bg-white border border-gray-200'
                          } ${msg.is_internal ? 'border-l-4 border-orange-300 bg-orange-50' : ''}`}
                        >
                          {msg.sender_type !== 'system' && (
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs font-medium text-gray-600">
                                {msg.sender_name || msg.sender_type}
                                {msg.is_internal && <span className="ml-1 text-orange-500">(Internal)</span>}
                              </span>
                              <span className="text-xs text-gray-400">
                                {formatDate(msg.created_at)}
                              </span>
                            </div>
                          )}
                          <p className={`text-sm ${msg.sender_type === 'system' ? '' : 'text-gray-800'}`}>
                            {msg.message}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Reply & Actions */}
                {selectedDispute.status !== 'closed' && selectedDispute.status !== 'resolved' && (
                  <div className="p-6">
                    <div className="flex gap-2 mb-4">
                      <input
                        type="text"
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendReply()}
                        placeholder="Type your response to the customer..."
                        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                      <button
                        onClick={sendReply}
                        disabled={!replyText.trim() || sendingReply}
                        className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {sendingReply ? 'Sending...' : 'Send'}
                      </button>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setShowResolveModal(true)}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                      >
                        Resolve Dispute
                      </button>
                      <button
                        onClick={() => escalateDispute(selectedDispute.id)}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
                      >
                        Escalate
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <svg className="w-16 h-16 text-gray-200 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <p className="text-gray-400 font-medium">Select a dispute to view details</p>
                <p className="text-gray-300 text-sm mt-1">Click on any dispute from the list to see AI analysis and manage resolution</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Subscriber Dispute Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white rounded-t-2xl border-b border-gray-100 px-6 py-4 flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">
                {createStep === 'form' ? 'Buat Aduan Baru' : createStep === 'submitting' ? 'Menghantar Aduan...' : 'Keputusan Aduan'}
              </h3>
              <button onClick={closeCreateModal} className="text-gray-400 hover:text-gray-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Form Step */}
            {createStep === 'form' && (
              <div className="p-6 space-y-5">
                {/* Category Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Kategori Aduan</label>
                  <div className="grid grid-cols-2 gap-2">
                    {SUBSCRIBER_CATEGORIES.map((cat) => (
                      <button
                        key={cat.key}
                        onClick={() => setCreateCategory(cat.key)}
                        className={`text-left p-3 rounded-xl border-2 transition-all ${
                          createCategory === cat.key
                            ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-200'
                            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        <span className="text-xl">{cat.icon}</span>
                        <p className="text-sm font-medium text-gray-800 mt-1">{cat.label}</p>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{cat.desc}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Terangkan masalah anda secara terperinci
                  </label>
                  <textarea
                    value={createDescription}
                    onChange={(e) => setCreateDescription(e.target.value)}
                    placeholder="Sila terangkan masalah yang anda hadapi dengan BinaApp... (minimum 10 aksara)"
                    rows={4}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                  />
                  <p className="text-xs text-gray-400 mt-1">{createDescription.length}/500 aksara</p>
                </div>

                {/* Related Website */}
                {websites.length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Laman Web Berkaitan <span className="text-gray-400">(Pilihan)</span>
                    </label>
                    <select
                      value={createWebsiteId}
                      onChange={(e) => setCreateWebsiteId(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="">-- Pilih laman web --</option>
                      {websites.map((w) => (
                        <option key={w.id} value={w.id}>{w.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Evidence Upload */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Bukti <span className="text-gray-400">(Pilihan, maks 5 gambar)</span>
                  </label>
                  <p className="text-xs text-gray-400 mb-2">Tangkap layar masalah, rekod pembayaran, dsb.</p>

                  {/* Image Previews */}
                  {createEvidence.length > 0 && (
                    <div className="flex gap-2 mb-3 flex-wrap">
                      {createEvidence.map((img, i) => (
                        <div key={i} className="relative w-16 h-16 rounded-lg overflow-hidden border border-gray-200 group">
                          <img src={img} alt={`Bukti ${i + 1}`} className="w-full h-full object-cover" />
                          <button
                            onClick={() => removeEvidence(i)}
                            className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {createEvidence.length < 5 && (
                    <label className="flex items-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/50 transition-colors">
                      <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span className="text-sm text-gray-500">Muat naik gambar ({createEvidence.length}/5)</span>
                      <input
                        type="file"
                        accept="image/*"
                        multiple
                        onChange={handleEvidenceUpload}
                        className="hidden"
                      />
                    </label>
                  )}
                </div>

                {/* Submit Button */}
                <button
                  onClick={submitSubscriberDispute}
                  disabled={!createCategory || createDescription.length < 10}
                  className="w-full px-6 py-3 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Hantar Aduan
                </button>
              </div>
            )}

            {/* Submitting Step */}
            {createStep === 'submitting' && (
              <div className="p-12 text-center">
                <div className="animate-spin w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-gray-700 font-medium">AI sedang menganalisis...</p>
                <p className="text-gray-400 text-sm mt-1">Sila tunggu sebentar</p>
              </div>
            )}

            {/* Result Step */}
            {createStep === 'result' && createResult && (
              <div className="p-8 text-center">
                {createResult.status === 'approved' && (
                  <>
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <h4 className="text-lg font-bold text-green-700 mb-2">Diluluskan</h4>
                    <p className="text-sm text-gray-600">{createResult.message}</p>
                  </>
                )}
                {createResult.status === 'rejected' && (
                  <>
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </div>
                    <h4 className="text-lg font-bold text-red-700 mb-2">Ditolak</h4>
                    <p className="text-sm text-gray-600">{createResult.message}</p>
                  </>
                )}
                {createResult.status === 'under_review' && (
                  <>
                    <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <h4 className="text-lg font-bold text-yellow-700 mb-2">Dalam Semakan</h4>
                    <p className="text-sm text-gray-600">{createResult.message}</p>
                  </>
                )}

                <button
                  onClick={closeCreateModal}
                  className="mt-6 px-6 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
                >
                  Tutup
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Resolve Modal */}
      {showResolveModal && selectedDispute && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Resolve Dispute</h3>
            <p className="text-sm text-gray-500 mb-4">
              #{selectedDispute.dispute_number} - {selectedDispute.customer_name}
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Resolution Type</label>
                <select
                  value={resolveType}
                  onChange={(e) => setResolveType(e.target.value as DisputeResolutionType)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="full_refund">Full Refund</option>
                  <option value="partial_refund">Partial Refund</option>
                  <option value="replacement">Replacement Order</option>
                  <option value="credit">Store Credit</option>
                  <option value="apology">Apology (No Compensation)</option>
                  <option value="rejected">Reject Dispute</option>
                </select>
              </div>

              {(resolveType === 'full_refund' || resolveType === 'partial_refund' || resolveType === 'credit') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Refund Amount (RM)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={refundAmount}
                    onChange={(e) => setRefundAmount(e.target.value)}
                    placeholder={`Max: ${selectedDispute.order_amount?.toFixed(2)}`}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  />
                  {selectedDispute.ai_analysis?.recommended_refund_percentage !== undefined && (
                    <p className="text-xs text-indigo-500 mt-1">
                      AI suggests: {selectedDispute.ai_analysis.recommended_refund_percentage}% (RM
                      {((selectedDispute.order_amount * selectedDispute.ai_analysis.recommended_refund_percentage) / 100).toFixed(2)})
                    </p>
                  )}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  value={resolveNotes}
                  onChange={(e) => setResolveNotes(e.target.value)}
                  placeholder="Add resolution notes..."
                  rows={3}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowResolveModal(false)}
                className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={resolveDispute}
                disabled={resolving}
                className="flex-1 px-4 py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {resolving ? 'Resolving...' : 'Confirm Resolution'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
