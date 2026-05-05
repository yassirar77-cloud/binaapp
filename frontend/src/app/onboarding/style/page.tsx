'use client'

import { useRouter } from 'next/navigation'
import { ArrowLeft, Check } from 'lucide-react'
import ProgressBar from '../ProgressBar'
import { useOnboardingState } from '@/hooks/useOnboardingState'

interface StyleOption {
  key: string
  name: string
  tagline: string
  vibe: string
  fonts: { heading: string; body: string }
  colors: { primary: string; secondary: string; accent: string }
}

const STYLES: StyleOption[] = [
  {
    key: 'teh_tarik_warm',
    name: 'Teh Tarik Warm',
    tagline: 'Hangat, mesra keluarga',
    vibe: 'Suasana kedai mamak yang mesra dan selesa',
    fonts: { heading: 'Playfair Display', body: 'Lato' },
    colors: { primary: '#C17817', secondary: '#F5E6D3', accent: '#8B4513' },
  },
  {
    key: 'pasar_malam_neon',
    name: 'Pasar Malam Neon',
    tagline: 'Vibrant, urban, malam',
    vibe: 'Tenaga pasar malam dengan cahaya neon yang meriah',
    fonts: { heading: 'Poppins', body: 'Inter' },
    colors: { primary: '#FF6B9D', secondary: '#1A1A2E', accent: '#00D4FF' },
  },
  {
    key: 'kampung_serene',
    name: 'Kampung Serene',
    tagline: 'Tradisional, tenang, warisan',
    vibe: 'Ketenangan kampung dengan sentuhan warisan Melayu',
    fonts: { heading: 'Merriweather', body: 'Source Sans Pro' },
    colors: { primary: '#2D5F2D', secondary: '#F5F0E8', accent: '#8B7355' },
  },
  {
    key: 'kopitiam_nostalgia',
    name: 'Kopitiam Nostalgia',
    tagline: 'Klasik, kopitiam, nostalgia',
    vibe: 'Suasana kopitiam lama yang klasik dan nostalgia',
    fonts: { heading: 'Roboto Slab', body: 'Roboto' },
    colors: { primary: '#4A3728', secondary: '#FDF6EC', accent: '#D4A574' },
  },
  {
    key: 'streetfood_bold',
    name: 'Streetfood Bold',
    tagline: 'Berani, food truck, anak muda',
    vibe: 'Tenaga jalanan yang berani untuk generasi muda',
    fonts: { heading: 'Montserrat', body: 'Open Sans' },
    colors: { primary: '#FF4500', secondary: '#FFF8F0', accent: '#FFD700' },
  },
  {
    key: 'fine_dining_obsidian',
    name: 'Fine Dining Obsidian',
    tagline: 'Premium, eksklusif, fine dining',
    vibe: 'Kemewahan dan keanggunan untuk restoran premium',
    fonts: { heading: 'Cormorant Garamond', body: 'Nunito Sans' },
    colors: { primary: '#1A1A1A', secondary: '#F8F4F0', accent: '#C9A96E' },
  },
]

export default function StylePage() {
  const router = useRouter()
  const { state, setStyleDna } = useOnboardingState()

  function selectStyle(key: string) {
    setStyleDna(key)
    router.push('/onboarding/generate')
  }

  return (
    <>
      <ProgressBar currentStep={3} />

      <div className="text-center mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
          Pilih Gaya Laman Web
        </h1>
        <p className="text-gray-600">
          Pilih satu gaya yang sesuai dengan restoran anda.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mb-8">
        {STYLES.map(style => {
          const isSelected = state.styleDna === style.key

          return (
            <button
              key={style.key}
              onClick={() => selectStyle(style.key)}
              className={`relative text-left p-5 rounded-xl border-2 transition-all hover:shadow-lg ${
                isSelected
                  ? 'border-orange-500 shadow-md ring-2 ring-orange-200'
                  : 'border-gray-200 hover:border-orange-300'
              }`}
            >
              {isSelected && (
                <div className="absolute top-3 right-3 bg-orange-500 text-white rounded-full p-1">
                  <Check size={14} />
                </div>
              )}

              {/* Color swatches */}
              <div className="flex gap-2 mb-3">
                <div
                  className="w-8 h-8 rounded-full border border-gray-200"
                  style={{ backgroundColor: style.colors.primary }}
                  title="Primary"
                />
                <div
                  className="w-8 h-8 rounded-full border border-gray-200"
                  style={{ backgroundColor: style.colors.secondary }}
                  title="Secondary"
                />
                <div
                  className="w-8 h-8 rounded-full border border-gray-200"
                  style={{ backgroundColor: style.colors.accent }}
                  title="Accent"
                />
              </div>

              {/* Font preview */}
              <div className="mb-3 p-3 bg-gray-50 rounded-lg">
                <p
                  className="text-lg font-bold text-gray-900"
                  style={{ fontFamily: style.fonts.heading }}
                >
                  Aa Bb Cc 123
                </p>
                <p
                  className="text-sm text-gray-600"
                  style={{ fontFamily: style.fonts.body }}
                >
                  Restoran Malaysia
                </p>
              </div>

              {/* Info */}
              <h3 className="font-semibold text-gray-900 mb-1">{style.name}</h3>
              <p className="text-sm font-medium text-orange-600 mb-1">{style.tagline}</p>
              <p className="text-xs text-gray-500">{style.vibe}</p>

              <div className="mt-3 text-center">
                <span className="inline-block px-4 py-1.5 bg-orange-100 text-orange-700 text-sm font-medium rounded-full">
                  Pilih
                </span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => router.push('/onboarding/dishes')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          <ArrowLeft size={18} />
          Kembali
        </button>
      </div>
    </>
  )
}
