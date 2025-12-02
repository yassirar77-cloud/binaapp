/**
 * Root Layout Component
 */

import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Toaster } from 'react-hot-toast'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'BinaApp - AI Website Builder untuk SME Malaysia',
  description: 'Cipta website perniagaan anda dalam masa minit dengan AI. Untuk SME Malaysia.',
  keywords: ['website builder', 'AI', 'Malaysia', 'SME', 'no-code'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ms">
      <body className={inter.className}>
        {children}
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
