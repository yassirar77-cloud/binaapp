/**
 * Root Layout Component
 */

import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import PWAProvider from '@/components/PWAProvider'
import ChatWidget from '@/components/ChatWidget'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'BinaApp - AI Website Builder untuk SME Malaysia',
  description: 'Cipta website perniagaan anda dalam masa minit dengan AI. Untuk SME Malaysia.',
  keywords: ['website builder', 'AI', 'Malaysia', 'SME', 'no-code'],
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'BinaApp',
  },
  formatDetection: {
    telephone: false,
  },
}

export const viewport: Viewport = {
  themeColor: '#0ea5e9',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ms">
      <head>
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
        <link rel="apple-touch-icon" sizes="152x152" href="/icons/icon-152x152.png" />
        <link rel="apple-touch-icon" sizes="180x180" href="/icons/icon-192x192.png" />
        <link rel="apple-touch-icon" sizes="167x167" href="/icons/icon-192x192.png" />

        {/* Eruda Mobile Console - Only show in development */}
        {process.env.NODE_ENV === 'development' && (
          <script
            dangerouslySetInnerHTML={{
              __html: `
                (function() {
                  var script = document.createElement('script');
                  script.src = 'https://cdn.jsdelivr.net/npm/eruda';
                  document.body.appendChild(script);
                  script.onload = function() {
                    eruda.init();
                    console.log('[Eruda] Mobile debugging console loaded! Tap the button in bottom-right corner.');
                  }
                })();
              `
            }}
          />
        )}
      </head>
      <body className={inter.className}>
        <PWAProvider>
          {children}
        </PWAProvider>
        <ChatWidget />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
          }}
        />
      </body>
    </html>
  )
}
