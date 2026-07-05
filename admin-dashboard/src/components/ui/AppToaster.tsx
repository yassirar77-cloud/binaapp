'use client'

import { Toaster } from 'react-hot-toast'

/**
 * Global toast theming for the admin dashboard — same dark navy + volt/red
 * treatment as the main BinaApp dashboard. Top-center suits the mobile-first
 * PWA layout (clear of the bottom tab bar).
 */
export function AppToaster() {
  return (
    <Toaster
      position="top-center"
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
      }}
    />
  )
}
