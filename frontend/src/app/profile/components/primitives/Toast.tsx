import { Check } from 'lucide-react'

interface ToastProps {
  msg: string | null
}

export function Toast({ msg }: ToastProps) {
  if (!msg) return null
  return (
    <div
      role="status"
      aria-live="polite"
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
      <Check size={14} strokeWidth={2} color="#10b981" />
      {msg}
    </div>
  )
}
