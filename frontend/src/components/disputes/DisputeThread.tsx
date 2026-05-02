'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { GhostButton } from '@/app/profile/components/primitives/GhostButton'
import { Pill } from '@/app/profile/components/primitives/Pill'
import { PrimaryButton } from '@/app/profile/components/primitives/PrimaryButton'
import type { Dispute, DisputeMessage } from '@/types'
import { DisputeModalShell } from './DisputeModalShell'
import { categoryFor } from './constants'
import {
  loadDisputeMessages,
  useDisputeMutations,
  ACTIVE_STATUSES,
} from './useDisputeMutations'

interface DisputeThreadProps {
  open: boolean
  dispute: Dispute | null
  onClose: () => void
  onRequestResolve: () => void
  onShowToast: (msg: string, tone: 'success' | 'error') => void
}

const TYPING_MIN_MS = 1500
const POLL_INTERVAL_MS = 2000
const MAX_POLL_ATTEMPTS = 8

interface PendingMessage {
  id: string
  text: string
}

function formatRelative(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'baru-baru ini'
  const diffMs = Date.now() - d.getTime()
  if (diffMs < 60_000) return 'baru sekarang'
  const minutes = Math.floor(diffMs / 60_000)
  if (minutes < 60) return `${minutes} minit lepas`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} jam lepas`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} hari lepas`
  return d.toLocaleDateString('en-MY', { day: 'numeric', month: 'short', year: 'numeric' })
}

function statusPill(status: string) {
  if (ACTIVE_STATUSES.has(status as never)) {
    return <Pill tone="amber">{status.replace(/_/g, ' ')}</Pill>
  }
  if (status === 'resolved') return <Pill tone="green">Selesai</Pill>
  if (status === 'closed') return <Pill tone="gray">Tutup</Pill>
  if (status === 'rejected') return <Pill tone="red">Ditolak</Pill>
  return <Pill tone="gray">{status.replace(/_/g, ' ')}</Pill>
}

export function DisputeThread({
  open,
  dispute,
  onClose,
  onRequestResolve,
  onShowToast,
}: DisputeThreadProps) {
  const [messages, setMessages] = useState<DisputeMessage[] | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [reply, setReply] = useState('')
  const [pending, setPending] = useState<PendingMessage[]>([])
  const [aiTyping, setAiTyping] = useState(false)
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const { sendReply } = useDisputeMutations()

  const isClosed = dispute
    ? !ACTIVE_STATUSES.has(dispute.status as never)
    : false

  const refresh = useCallback(async () => {
    if (!dispute) return [] as DisputeMessage[]
    try {
      const next = await loadDisputeMessages(dispute.id)
      setMessages(next)
      return next
    } catch (err) {
      console.warn('[Dispute] Failed to load messages:', err)
      return null
    }
  }, [dispute])

  useEffect(() => {
    if (!open || !dispute) return
    setMessages(null)
    setReply('')
    setPending([])
    setAiTyping(false)
    setLoadingMessages(true)
    refresh().finally(() => setLoadingMessages(false))
  }, [open, dispute, refresh])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages, pending, aiTyping])

  async function handleSend() {
    const trimmed = reply.trim()
    if (!trimmed || !dispute || sending) return

    const tempId = `pending-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    const optimistic: PendingMessage = { id: tempId, text: trimmed }
    setPending((p) => [...p, optimistic])
    setReply('')
    setSending(true)
    setAiTyping(true)

    const startedAt = Date.now()

    try {
      await sendReply(dispute.id, trimmed)
      // Snapshot existing message count to detect AI follow-up arrival
      const beforeCount = messages?.length ?? 0
      // Always wait for the typing-indicator minimum
      await new Promise((r) => setTimeout(r, Math.max(0, TYPING_MIN_MS - (Date.now() - startedAt))))

      let attempts = 0
      let aiArrived = false
      while (attempts < MAX_POLL_ATTEMPTS) {
        const next = await refresh()
        if (next) {
          // Owner's own message will show up; AI reply means count grew by >=2
          if (next.length >= beforeCount + 2 || next.some((m) => m.sender_type === 'ai' && new Date(m.created_at).getTime() > startedAt)) {
            aiArrived = true
            break
          }
        }
        attempts += 1
        if (attempts < MAX_POLL_ATTEMPTS) {
          await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
        }
      }

      // Drop the optimistic bubble — owner's message is now in `messages`
      setPending((p) => p.filter((m) => m.id !== tempId))
      if (!aiArrived) {
        // Final refresh just in case
        await refresh()
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Gagal hantar mesej'
      onShowToast(msg, 'error')
      // Roll back optimistic message and restore the textarea contents
      setPending((p) => p.filter((m) => m.id !== tempId))
      setReply(trimmed)
    } finally {
      setSending(false)
      setAiTyping(false)
    }
  }

  if (!dispute) return null

  const cat = categoryFor(dispute.category)
  const subtitle = `${cat ? `${cat.icon} ${cat.label}` : dispute.category} · ${formatRelative(dispute.created_at)}`

  return (
    <DisputeModalShell
      open={open}
      onClose={onClose}
      title={`Aduan #${dispute.dispute_number}`}
      subtitle={subtitle}
      maxWidth={600}
      fill
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, height: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
          {statusPill(dispute.status)}
          {!isClosed && (
            <GhostButton onClick={onRequestResolve}>Tutup aduan</GhostButton>
          )}
        </div>

        <div
          ref={scrollRef}
          style={{
            flex: 1,
            minHeight: 240,
            maxHeight: '50vh',
            overflowY: 'auto',
            background: '#f7f7f8',
            border: '0.5px solid var(--border)',
            borderRadius: 'var(--r-input)',
            padding: 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          {loadingMessages && messages === null && (
            <div style={{ padding: 20, textAlign: 'center', fontSize: 13, color: 'var(--ink-3)' }}>Memuatkan mesej…</div>
          )}

          {messages !== null && messages.length === 0 && pending.length === 0 && !aiTyping && (
            <div style={{ padding: 20, textAlign: 'center', fontSize: 13, color: 'var(--ink-3)' }}>
              Belum ada mesej. Hantar mesej untuk mulakan perbualan.
            </div>
          )}

          {messages?.map((m) => <MessageBubble key={m.id} message={m} />)}
          {pending.map((p) => (
            <Bubble key={p.id} side="right" tone="owner" muted>
              <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{p.text}</div>
              <div style={{ fontSize: 10, color: 'var(--ink-3)', marginTop: 4 }}>menghantar…</div>
            </Bubble>
          ))}
          {aiTyping && <TypingBubble />}
        </div>

        {isClosed ? (
          <div
            style={{
              fontSize: 13,
              color: 'var(--ink-3)',
              textAlign: 'center',
              padding: '10px 0',
            }}
          >
            Aduan ini sudah ditutup. Tiada lagi mesej boleh dihantar.
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void handleSend()
            }}
            style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}
          >
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void handleSend()
                }
              }}
              placeholder="Taip mesej…"
              rows={1}
              style={{
                flex: 1,
                background: '#fff',
                border: '0.5px solid var(--border-strong)',
                borderRadius: 'var(--r-input)',
                padding: '10px 12px',
                fontFamily: 'inherit',
                fontSize: 14,
                resize: 'none',
                color: 'var(--ink-1)',
                letterSpacing: 'inherit',
                outline: 'none',
                minHeight: 38,
                maxHeight: 120,
              }}
            />
            <PrimaryButton type="submit" disabled={sending || !reply.trim()}>
              {sending ? 'Menghantar…' : 'Hantar'}
            </PrimaryButton>
          </form>
        )}
      </div>
    </DisputeModalShell>
  )
}

function MessageBubble({ message }: { message: DisputeMessage }) {
  const { sender_type, message: text, sender_name, created_at } = message
  if (sender_type === 'system') {
    return (
      <div style={{ alignSelf: 'center', fontSize: 11, color: 'var(--ink-3)', fontStyle: 'italic', textAlign: 'center', maxWidth: '80%' }}>
        {text}
      </div>
    )
  }
  if (sender_type === 'owner') {
    return (
      <Bubble side="right" tone="owner" timestamp={created_at}>
        <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{text}</div>
      </Bubble>
    )
  }
  if (sender_type === 'ai') {
    return (
      <Bubble side="left" tone="ai" label="BinaApp Support" labelGlyph="✨" timestamp={created_at}>
        <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{text}</div>
      </Bubble>
    )
  }
  // customer or admin
  const label = sender_name?.trim() || (sender_type === 'admin' ? 'BinaApp Admin' : 'Pelanggan')
  return (
    <Bubble side="left" tone="neutral" label={label} timestamp={created_at}>
      <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{text}</div>
    </Bubble>
  )
}

function TypingBubble() {
  return (
    <Bubble side="left" tone="ai" label="BinaApp Support" labelGlyph="✨">
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 0' }}>
        <Dot delay={0} />
        <Dot delay={150} />
        <Dot delay={300} />
      </div>
      <style jsx>{`
        @keyframes dot-pulse {
          0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
          30% { opacity: 1; transform: translateY(-2px); }
        }
      `}</style>
    </Bubble>
  )
}

function Dot({ delay }: { delay: number }) {
  return (
    <span
      style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: 'var(--ink-3)',
        animation: 'dot-pulse 1.2s ease-in-out infinite',
        animationDelay: `${delay}ms`,
        display: 'inline-block',
      }}
    />
  )
}

interface BubbleProps {
  side: 'left' | 'right'
  tone: 'owner' | 'ai' | 'neutral'
  label?: string
  labelGlyph?: string
  timestamp?: string
  muted?: boolean
  children: React.ReactNode
}

function Bubble({ side, tone, label, labelGlyph, timestamp, muted, children }: BubbleProps) {
  const isRight = side === 'right'
  const bg = tone === 'owner' ? '#fff5ed' : tone === 'ai' ? '#f0f1f4' : '#fff'
  const fg = tone === 'owner' ? '#9a3412' : 'var(--ink-1)'
  const border = tone === 'neutral' ? '0.5px solid var(--border)' : 'none'

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isRight ? 'flex-end' : 'flex-start',
        gap: 2,
        maxWidth: '80%',
        alignSelf: isRight ? 'flex-end' : 'flex-start',
      }}
    >
      {label && (
        <div style={{ fontSize: 10, color: 'var(--ink-3)', display: 'inline-flex', alignItems: 'center', gap: 4, paddingLeft: 4 }}>
          {labelGlyph && <span aria-hidden>{labelGlyph}</span>}
          {label}
        </div>
      )}
      <div
        style={{
          background: bg,
          color: fg,
          border,
          padding: '8px 12px',
          borderRadius: 12,
          fontSize: 13,
          lineHeight: 1.45,
          opacity: muted ? 0.7 : 1,
        }}
      >
        {children}
      </div>
      {timestamp && (
        <div style={{ fontSize: 10, color: 'var(--ink-4)', paddingLeft: isRight ? 0 : 4, paddingRight: isRight ? 4 : 0 }}>
          {formatRelative(timestamp)}
        </div>
      )}
    </div>
  )
}
