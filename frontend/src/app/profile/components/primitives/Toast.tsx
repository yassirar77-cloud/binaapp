import { Check, X } from 'lucide-react'

export type ToastTone = 'success' | 'error'

interface ToastProps {
  msg: string | null
  tone?: ToastTone
}

export function Toast({ msg, tone = 'success' }: ToastProps) {
  if (!msg) return null
  const Icon = tone === 'error' ? X : Check
  const iconColor = tone === 'error' ? '#f87171' : '#10b981'
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      aria-live={tone === 'error' ? 'assertive' : 'polite'}
      style={{
        position: 'fixed',
        bottom: 28,
        left: '50%',
        transform: 'translateX(-50%)',
        background: 'var(--ink-1)',
        color: '#fff',
        fontSize: 13,
        fontWeight: 500,
        padding: '10px 16px',
        borderRadius: 'var(--r-input)',
        animation: 'profileToastIn 220ms cubic-bezier(.25,1,.5,1)',
        boxShadow: '0 8px 24px rgba(0,0,0,.18)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}
    >
      <Icon size={14} strokeWidth={2} color={iconColor} />
      {msg}
    </div>
  )
}
