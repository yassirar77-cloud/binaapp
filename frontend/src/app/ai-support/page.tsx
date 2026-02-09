'use client'

import React from 'react'
import Link from 'next/link'

export default function AISupportPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-800">Bantuan AI</h1>
            <p className="text-xs text-gray-500">Pilih cara untuk mendapatkan bantuan</p>
          </div>
          <Link href="/profil" className="text-sm text-blue-600 hover:underline">
            Kembali ke Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Bagaimana kami boleh membantu?</h2>
          <p className="text-gray-500">Pilih salah satu pilihan di bawah</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {/* Option A: Chat with AI */}
          <Link
            href="/ai-support/chat"
            className="block border-2 border-blue-200 bg-white rounded-2xl p-8 text-center hover:border-blue-400 hover:shadow-lg transition-all group"
          >
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-blue-200 transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-800 mb-2">Chat dengan AI</h3>
            <p className="text-sm text-gray-500">
              Berbual terus dengan AI untuk selesaikan masalah anda. Boleh hantar gambar!
            </p>
            <div className="mt-4 inline-flex items-center gap-1 text-sm text-blue-600 font-medium">
              Mula berbual
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
          </Link>

          {/* Option B: Dispute Form */}
          <Link
            href="/disputes"
            className="block border-2 border-purple-200 bg-white rounded-2xl p-8 text-center hover:border-purple-400 hover:shadow-lg transition-all group"
          >
            <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:bg-purple-200 transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-600">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
            </div>
            <h3 className="text-lg font-bold text-gray-800 mb-2">Borang Aduan</h3>
            <p className="text-sm text-gray-500">
              Isi borang dan muat naik bukti untuk aduan rasmi
            </p>
            <div className="mt-4 inline-flex items-center gap-1 text-sm text-purple-600 font-medium">
              Isi borang
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
          </Link>
        </div>
      </main>
    </div>
  )
}
