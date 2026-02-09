'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Dispute, DisputeMessage, DisputeCategory } from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

const CATEGORY_LABELS: Record<string, string> = {
  wrong_items: 'Wrong Items',
  missing_items: 'Missing Items',
  quality_issue: 'Quality Issue',
  late_delivery: 'Late Delivery',
  damaged_items: 'Damaged Items',
  overcharged: 'Overcharged',
  never_delivered: 'Never Delivered',
  rider_issue: 'Rider Issue',
  other: 'Other',
}

const STATUS_STEPS = [
  { key: 'open', label: 'Filed' },
  { key: 'under_review', label: 'Under Review' },
  { key: 'awaiting_response', label: 'Awaiting Response' },
  { key: 'resolved', label: 'Resolved' },
]

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-yellow-100 text-yellow-800',
  under_review: 'bg-blue-100 text-blue-800',
  awaiting_response: 'bg-purple-100 text-purple-800',
  resolved: 'bg-green-100 text-green-800',
  closed: 'bg-gray-100 text-gray-800',
  escalated: 'bg-red-100 text-red-800',
  rejected: 'bg-red-100 text-red-800',
}

export default function TrackDisputePage() {
  const searchParams = useSearchParams()
  const [disputeNumber, setDisputeNumber] = useState(searchParams.get('id') || '')
  const [dispute, setDispute] = useState<Dispute | null>(null)
  const [messages, setMessages] = useState<DisputeMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [newMessage, setNewMessage] = useState('')
  const [sendingMessage, setSendingMessage] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(!!searchParams.get('order_id'))

  // Create dispute form state
  const [orderId, setOrderId] = useState(searchParams.get('order_id') || '')
  const [category, setCategory] = useState<DisputeCategory>('quality_issue')
  const [description, setDescription] = useState('')
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  useEffect(() => {
    if (disputeNumber) {
      trackDispute()
    }
  }, [])

  async function trackDispute() {
    if (!disputeNumber.trim()) return

    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/track/${disputeNumber}`)
      if (res.ok) {
        const data = await res.json()
        setDispute(data)
        loadMessages(disputeNumber)
      } else if (res.status === 404) {
        setError('Dispute not found. Please check the dispute number.')
        setDispute(null)
      } else {
        setError('Failed to load dispute. Please try again.')
      }
    } catch (err) {
      setError('Connection error. Please check your internet and try again.')
    } finally {
      setLoading(false)
    }
  }

  async function loadMessages(dspNumber: string) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/track/${dspNumber}/messages`)
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
      }
    } catch (err) {
      console.error('Error loading messages:', err)
    }
  }

  async function sendMessage() {
    if (!newMessage.trim() || !dispute) return

    setSendingMessage(true)
    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/track/${dispute.dispute_number}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: newMessage,
          sender_type: 'customer',
          sender_name: dispute.customer_name,
        }),
      })

      if (res.ok) {
        setNewMessage('')
        loadMessages(dispute.dispute_number)
      }
    } catch (err) {
      console.error('Error sending message:', err)
    } finally {
      setSendingMessage(false)
    }
  }

  async function createDispute() {
    if (!orderId || !description || !customerName) {
      setCreateError('Please fill in all required fields.')
      return
    }

    setCreating(true)
    setCreateError('')
    try {
      const res = await fetch(`${API_BASE}/api/v1/disputes/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: orderId,
          category,
          description,
          customer_name: customerName,
          customer_phone: customerPhone || null,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        setDispute(data)
        setDisputeNumber(data.dispute_number)
        setShowCreateForm(false)
        loadMessages(data.dispute_number)
      } else {
        const errData = await res.json().catch(() => ({}))
        setCreateError(errData.detail || 'Failed to create dispute. Please try again.')
      }
    } catch (err) {
      setCreateError('Connection error. Please try again.')
    } finally {
      setCreating(false)
    }
  }

  function getStatusStep(statusKey: string): number {
    if (statusKey === 'escalated') return 2
    if (statusKey === 'rejected') return 3
    if (statusKey === 'closed') return 4
    return STATUS_STEPS.findIndex(s => s.key === statusKey)
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString('en-MY', {
      day: 'numeric', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-xl font-bold text-gray-900">Dispute Center</h1>
          <p className="text-sm text-gray-500">File or track your dispute</p>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* Toggle between track and create */}
        {!dispute && (
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => setShowCreateForm(false)}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                !showCreateForm ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200'
              }`}
            >
              Track Dispute
            </button>
            <button
              onClick={() => setShowCreateForm(true)}
              className={`px-4 py-2 rounded-lg text-sm font-medium ${
                showCreateForm ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200'
              }`}
            >
              File New Dispute
            </button>
          </div>
        )}

        {/* Track Form */}
        {!showCreateForm && !dispute && (
          <div className="bg-white rounded-xl p-6 border border-gray-200 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Track Your Dispute</h2>
            <div className="flex gap-2">
              <input
                type="text"
                value={disputeNumber}
                onChange={(e) => setDisputeNumber(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && trackDispute()}
                placeholder="Enter dispute number (e.g. DSP-20260209-0001)"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              <button
                onClick={trackDispute}
                disabled={loading || !disputeNumber.trim()}
                className="px-6 py-3 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Track'}
              </button>
            </div>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          </div>
        )}

        {/* Create Dispute Form */}
        {showCreateForm && !dispute && (
          <div className="bg-white rounded-xl p-6 border border-gray-200 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">File a New Dispute</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Order ID *</label>
                <input
                  type="text"
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                  placeholder="Your order ID"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Name *</label>
                <input
                  type="text"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="Enter your name"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                <input
                  type="tel"
                  value={customerPhone}
                  onChange={(e) => setCustomerPhone(e.target.value)}
                  placeholder="e.g. 0123456789"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Issue Category *</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as DisputeCategory)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                >
                  {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Describe the Issue *</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Please describe what happened in detail (minimum 10 characters)..."
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {createError && <p className="text-red-500 text-sm">{createError}</p>}

              <button
                onClick={createDispute}
                disabled={creating || !orderId || !customerName || description.length < 10}
                className="w-full px-6 py-3 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating ? 'Submitting...' : 'Submit Dispute'}
              </button>
            </div>
          </div>
        )}

        {/* Dispute Detail */}
        {dispute && (
          <div className="space-y-6">
            {/* Status Banner */}
            <div className="bg-white rounded-xl p-6 border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">#{dispute.dispute_number}</h2>
                  <p className="text-sm text-gray-500">Filed {formatDate(dispute.created_at)}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[dispute.status]}`}>
                  {dispute.status.replace('_', ' ')}
                </span>
              </div>

              {/* Progress Steps */}
              <div className="flex items-center gap-1 mb-6">
                {STATUS_STEPS.map((step, i) => {
                  const currentStep = getStatusStep(dispute.status)
                  const isCompleted = i <= currentStep
                  const isCurrent = i === currentStep
                  return (
                    <div key={step.key} className="flex-1">
                      <div className={`h-2 rounded-full ${isCompleted ? 'bg-indigo-500' : 'bg-gray-200'}`} />
                      <p className={`text-xs mt-1 ${isCurrent ? 'font-semibold text-indigo-600' : 'text-gray-400'}`}>
                        {step.label}
                      </p>
                    </div>
                  )
                })}
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Category</p>
                  <p className="font-medium">{CATEGORY_LABELS[dispute.category]}</p>
                </div>
                <div>
                  <p className="text-gray-500">Order Amount</p>
                  <p className="font-medium">RM{dispute.order_amount?.toFixed(2)}</p>
                </div>
                {dispute.resolution_type && (
                  <div>
                    <p className="text-gray-500">Resolution</p>
                    <p className="font-medium text-green-600">
                      {dispute.resolution_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </p>
                  </div>
                )}
                {dispute.refund_amount && dispute.refund_amount > 0 && (
                  <div>
                    <p className="text-gray-500">Refund Amount</p>
                    <p className="font-medium text-green-600">RM{dispute.refund_amount.toFixed(2)}</p>
                  </div>
                )}
              </div>

              <div className="mt-4">
                <p className="text-gray-500 text-sm mb-1">Your Description</p>
                <p className="text-gray-800 text-sm bg-gray-50 rounded-lg p-3">{dispute.description}</p>
              </div>
            </div>

            {/* Messages */}
            <div className="bg-white rounded-xl p-6 border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Messages</h3>

              {messages.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-4">No messages yet. We&apos;ll respond shortly.</p>
              ) : (
                <div className="space-y-3 mb-4">
                  {messages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`rounded-lg p-3 ${
                        msg.sender_type === 'system'
                          ? 'bg-gray-50 text-gray-500 text-center text-xs'
                          : msg.sender_type === 'ai'
                          ? 'bg-indigo-50 border-l-4 border-indigo-400'
                          : msg.sender_type === 'customer'
                          ? 'bg-white border border-gray-200 ml-8'
                          : 'bg-blue-50 border-l-4 border-blue-400 mr-8'
                      }`}
                    >
                      {msg.sender_type !== 'system' && (
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-gray-600">
                            {msg.sender_type === 'ai' ? 'AI Assistant' : msg.sender_name || msg.sender_type}
                          </span>
                          <span className="text-xs text-gray-400">{formatDate(msg.created_at)}</span>
                        </div>
                      )}
                      <p className={`text-sm ${msg.sender_type === 'system' ? '' : 'text-gray-800'}`}>
                        {msg.message}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* Reply box */}
              {dispute.status !== 'closed' && dispute.status !== 'resolved' && dispute.status !== 'rejected' && (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Send a message..."
                    className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!newMessage.trim() || sendingMessage}
                    className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {sendingMessage ? '...' : 'Send'}
                  </button>
                </div>
              )}
            </div>

            {/* Back link */}
            <div className="text-center">
              <button
                onClick={() => { setDispute(null); setMessages([]) }}
                className="text-indigo-600 text-sm hover:underline"
              >
                Track another dispute
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
