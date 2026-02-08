/**
 * Template Gallery Page
 *
 * Step 1 of the enhanced creation flow: user browses design templates
 * and picks one (or skips). Then navigates to /create with the
 * template_id as a query parameter.
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
    if (selectedTemplate) {
      router.push(`/create?template=${selectedTemplate}`)
    } else {
      router.push('/create')
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-orange-200 border-t-orange-500 rounded-full animate-spin mx-auto" />
          <p className="mt-3 text-gray-500 text-sm">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link
            href="/create"
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">
              {language === 'ms' ? 'Kembali' : 'Back'}
            </span>
          </Link>

          <div className="flex items-center gap-2">
            <Palette className="w-5 h-5 text-orange-500" />
            <span className="font-bold text-gray-900">
              {language === 'ms' ? 'Galeri Templat' : 'Template Gallery'}
            </span>
          </div>

          {/* Language toggle */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-full p-0.5">
            <button
              onClick={() => setLanguage('ms')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                language === 'ms'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              BM
            </button>
            <button
              onClick={() => setLanguage('en')}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                language === 'en'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              EN
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Intro section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 bg-orange-50 text-orange-600 px-4 py-2 rounded-full text-sm font-medium mb-4">
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

        {/* Selected template indicator */}
        {selectedTemplate && (
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 z-50 shadow-lg">
            <div className="max-w-6xl mx-auto flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center">
                  <Palette className="w-4 h-4 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    {language === 'ms' ? 'Templat dipilih' : 'Template selected'}
                  </p>
                  <p className="text-xs text-gray-500">{selectedTemplate.replace(/_/g, ' ')}</p>
                </div>
              </div>
              <button
                onClick={handleContinue}
                className="px-6 py-2.5 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-xl transition-colors shadow-sm"
              >
                {language === 'ms' ? 'Teruskan ke Borang' : 'Continue to Form'}
                <span className="ml-1">&rarr;</span>
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
