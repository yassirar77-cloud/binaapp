/**
 * Root Layout Component
 */

import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import { Suspense } from 'react'
import './globals.css'
import { Toaster } from 'react-hot-toast'
import { PWAInstallPrompt } from '@/components/PWAInstallPrompt'
import { ServiceWorkerRegister } from '@/components/ServiceWorkerRegister'
import ChatWidget from '@/components/ChatWidget'
import { AuthProvider } from '@/components/AuthProvider'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  // Production origin — drives absolute URL generation for Metadata
  // fields like canonical and alternates.languages on child routes.
  // Without this Next.js emits relative URLs in <link rel="canonical">
  // and <link rel="alternate" hreflang> tags, which work but are a
  // weaker SEO signal than absolute URLs.
  metadataBase: new URL('https://binaapp.my'),
  title: 'BinaApp - AI Website Builder Malaysia',
  description: 'Bina website perniagaan dengan AI dalam 60 saat',
  manifest: '/manifest.json',
  icons: {
    apple: '/icons/icon-192x192.png',
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'BinaApp',
  },
  formatDetection: {
    telephone: false,
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'msapplication-TileColor': '#3b82f6',
    'msapplication-tap-highlight': 'no',
  },
  openGraph: {
    type: 'website',
    siteName: 'BinaApp',
    title: 'BinaApp - AI Website Builder',
    description: 'Bina website perniagaan dengan AI',
  },
}

export const viewport: Viewport = {
  themeColor: '#3b82f6',
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
        {/* PWA tags emitted via `metadata` so /rider can override them — a hardcoded <link rel="manifest"> here would shadow the rider manifest in document order. */}
        {/* Early PWA install prompt capture - must run before React mounts */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              window.__pwaInstallPrompt = null;
              window.__pwaInstallPromptCaptured = false;
              window.addEventListener('beforeinstallprompt', function(e) {
                e.preventDefault();
                window.__pwaInstallPrompt = e;
                window.__pwaInstallPromptCaptured = true;
                console.log('[PWA] Install prompt captured early (before React mount)');
                window.dispatchEvent(new CustomEvent('pwa-prompt-ready'));
              });
            `,
          }}
        />
      </head>
      <body className={inter.className}>
        <Suspense fallback={null}>
          <AuthProvider>
            {children}
          </AuthProvider>
        </Suspense>
        <ServiceWorkerRegister swPath="/sw.js" />
        <PWAInstallPrompt />
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
