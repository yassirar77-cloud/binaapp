/**
 * Template Gallery Page
 *
 * Step 1 of the enhanced creation flow: user browses animated design
 * templates and picks one (or skips). Then navigates to /create with
 * the template_id as a query parameter.
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Sparkles, Palette } from 'lucide-react'
import { supabase, getCurrentUser, getStoredToken } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import TemplateGallery from '@/components/TemplateGallery'

export default function TemplateGalleryPage() {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [language, setLanguage] = useState<'ms' | 'en'>('ms')
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)

  useEffect(() => {
    checkUser()
  }, [])

  async function checkUser() {
    try {
      const customToken = getStoredToken()
      const customUser = await getCurrentUser()

      if (customToken && customUser) {
        setUser(customUser as any)
        setAuthLoading(false)
        return
      }

      const { data } = await supabase.auth.getSession()
      if (data.session?.user) {
        setUser(data.session.user)
      }
    } catch (err) {
      console.error('Auth check failed:', err)
    } finally {
      setAuthLoading(false)
    }
  }

  function handleSelectTemplate(templateId: string | null) {
    setSelectedTemplate(templateId)
  }

  function handleContinue() {
    if (selectedTemplate) {
      router.push(`/create?template=${selectedTemplate}`)
    } else {
      router.push('/create')
    }
  }

  function handleSkip() {
    router.push('/create')
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#0a0a0f' }}>
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-orange-900 border-t-orange-500 rounded-full animate-spin mx-auto" />
          <p className="mt-3 text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={{ background: '#0a0a0f' }}>
      {/* Header */}
      <header
        className="sticky top-0 z-50"
        style={{
          background: 'rgba(10,10,15,0.85)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link
            href="/create"
            className="flex items-center gap-2 text-sm transition-colors"
            style={{ color: 'rgba(255,255,255,0.5)' }}
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">
              {language === 'ms' ? 'Kembali' : 'Back'}
            </span>
          </Link>

          <div className="flex items-center gap-2">
            <Palette className="w-5 h-5" style={{ color: '#ff6b35' }} />
            <span className="font-bold text-white">
              {language === 'ms' ? 'Galeri Templat' : 'Template Gallery'}
            </span>
          </div>

          {/* Language toggle */}
          <div
            className="flex items-center gap-1 rounded-full p-0.5"
            style={{ background: 'rgba(255,255,255,0.06)' }}
          >
            <button
              onClick={() => setLanguage('ms')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                language === 'ms'
                  ? 'bg-white/10 text-white shadow-sm'
                  : 'text-white/40 hover:text-white/60'
              }`}
            >
              BM
            </button>
            <button
              onClick={() => setLanguage('en')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                language === 'en'
                  ? 'bg-white/10 text-white shadow-sm'
                  : 'text-white/40 hover:text-white/60'
              }`}
            >
              EN
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Step badge */}
        <div className="text-center mb-8">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium"
            style={{ background: 'rgba(255,107,53,0.1)', color: '#ff6b35' }}
          >
            <Sparkles className="w-4 h-4" />
            {language === 'ms' ? 'Langkah 1 daripada 2' : 'Step 1 of 2'}
          </div>
        </div>

        <TemplateGallery
          language={language}
          onSelect={handleSelectTemplate}
          onSkip={handleSkip}
          selectedTemplateId={selectedTemplate}
        />

        {/* Selected template bottom bar */}
        {selectedTemplate && (
          <div
            className="fixed bottom-0 left-0 right-0 p-4 z-50"
            style={{
              background: 'rgba(18,18,26,0.95)',
              backdropFilter: 'blur(12px)',
              borderTop: '1px solid rgba(255,255,255,0.06)',
              boxShadow: '0 -4px 20px rgba(0,0,0,0.4)',
            }}
          >
            <div className="max-w-6xl mx-auto flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: 'rgba(255,107,53,0.15)' }}
                >
                  <Palette className="w-4 h-4" style={{ color: '#ff6b35' }} />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">
                    {language === 'ms' ? 'Templat dipilih' : 'Template selected'}
                  </p>
                  <p className="text-xs" style={{ color: 'rgba(255,255,255,0.4)' }}>
                    {selectedTemplate.replace(/-/g, ' ')}
                  </p>
                </div>
              </div>
              <button
                onClick={handleContinue}
                className="px-6 py-2.5 text-sm font-semibold rounded-xl transition-all duration-200"
                style={{
                  background: '#ff6b35',
                  color: '#fff',
                  boxShadow: '0 2px 10px rgba(255,107,53,0.3)',
                }}
              >
                {language === 'ms' ? 'Teruskan ke Borang' : 'Continue to Form'}
                <span className="ml-1">&rarr;</span>
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Global keyframe for card entrance animation */}
      <style jsx global>{`
        @keyframes fadeUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  )
}
