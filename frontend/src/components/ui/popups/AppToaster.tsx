'use client'

import { useEffect, useState } from 'react'
import { Toaster } from 'react-hot-toast'

/**
 * Global toast theming — dark navy panel + lime/red semantic icons, matching
 * the dashboard design language. Top-center on phones (clear of FABs and
 * bottom bars), top-right on desktop.
 */
export function AppToaster() {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 640px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  return (
    <Toaster
      position={isMobile ? 'top-center' : 'top-right'}
      toastOptions={{
        duration: 4000,
        style: {
          background: '#161623',
          color: '#F7F7FA',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '12px',
          boxShadow: '0 12px 32px rgba(0,0,0,0.45)',
          fontFamily: "'Geist', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
          fontSize: '14px',
          maxWidth: 'min(420px, calc(100vw - 32px))',
        },
        success: {
          iconTheme: { primary: '#C7FF3D', secondary: '#0B0B15' },
        },
        error: {
          duration: 5000,
          iconTheme: { primary: '#FF5A5F', secondary: '#FFFFFF' },
        },
        loading: {
          iconTheme: { primary: '#C7FF3D', secondary: 'rgba(255,255,255,0.2)' },
        },
      }}
    />
  )
}
