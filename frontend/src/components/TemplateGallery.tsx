'use client'

import { useState, useEffect } from 'react'
import { DIRECT_BACKEND_URL } from '@/lib/env'

interface TemplateColors {
  primary: string
  secondary: string
  accent: string
  background: string
  surface: string
  text: string
  text_muted: string
}

interface TemplateItem {
  id: string
  name: string
  name_ms: string
  description: string
  description_ms: string
  preview_image: string
  category: string
  best_for: string[]
  color_mode: string
  colors: TemplateColors
  recommended?: boolean
}

interface TemplateGalleryProps {
  language: 'ms' | 'en'
  businessType?: string
  onSelect: (templateId: string | null) => void
  onSkip: () => void
  selectedTemplateId: string | null
}

function TemplatePreviewCard({
  template,
  colors,
}: {
  template: TemplateItem
  colors: TemplateColors
}) {
  const isDark = template.color_mode === 'dark'
  return (
    <div
      className="w-full h-full rounded-lg overflow-hidden relative"
      style={{ backgroundColor: colors.background }}
    >
      {/* Mini header bar */}
      <div
        className="h-6 flex items-center px-2 gap-1"
        style={{ backgroundColor: isDark ? colors.surface : colors.accent }}
      >
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colors.primary }} />
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colors.secondary }} />
        <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colors.text_muted }} />
      </div>

      {/* Mini hero section */}
      <div
        className="h-16 flex items-center justify-center relative"
        style={{
          background: isDark
            ? `linear-gradient(135deg, ${colors.surface} 0%, ${colors.background} 100%)`
            : `linear-gradient(135deg, ${colors.accent} 0%, ${colors.background} 100%)`,
        }}
      >
        <div className="text-center px-2">
          <div
            className="h-2 w-16 rounded-full mx-auto mb-1"
            style={{ backgroundColor: colors.text }}
          />
          <div
            className="h-1.5 w-10 rounded-full mx-auto"
            style={{ backgroundColor: colors.text_muted }}
          />
        </div>
      </div>

      {/* Mini content cards */}
      <div className="px-2 py-2 space-y-1.5">
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="flex-1 h-10 rounded"
              style={{
                backgroundColor: isDark ? colors.surface : colors.surface,
                border: `1px solid ${isDark ? `${colors.primary}20` : `${colors.text}10`}`,
              }}
            >
              <div
                className="h-1.5 w-5 rounded-full mx-auto mt-2"
                style={{ backgroundColor: colors.primary }}
              />
              <div
                className="h-1 w-8 rounded-full mx-auto mt-1"
                style={{ backgroundColor: colors.text_muted }}
              />
            </div>
          ))}
        </div>

        {/* Mini CTA button */}
        <div className="flex justify-center pt-1">
          <div
            className="h-3 w-14 rounded-full"
            style={{ backgroundColor: colors.primary }}
          />
        </div>
      </div>
    </div>
  )
}

export default function TemplateGallery({
  language,
  businessType,
  onSelect,
  onSkip,
  selectedTemplateId,
}: TemplateGalleryProps) {
  const [templates, setTemplates] = useState<TemplateItem[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')

  const isMalay = language === 'ms'

  useEffect(() => {
    fetchTemplates()
  }, [businessType])

  async function fetchTemplates() {
    try {
      setLoading(true)
      const endpoint = businessType
        ? `${DIRECT_BACKEND_URL}/api/v1/templates/gallery/recommended/${businessType}`
        : `${DIRECT_BACKEND_URL}/api/v1/templates/gallery`
      const res = await fetch(endpoint)
      if (res.ok) {
        const data = await res.json()
        setTemplates(data.templates || [])
      }
    } catch (err) {
      console.error('Failed to fetch templates:', err)
      // Fallback: use hardcoded template list
      setTemplates([])
    } finally {
      setLoading(false)
    }
  }

  const categories = [
    { id: 'all', label: isMalay ? 'Semua' : 'All' },
    { id: 'light', label: isMalay ? 'Cerah' : 'Light' },
    { id: 'dark', label: isMalay ? 'Gelap' : 'Dark' },
  ]

  const filteredTemplates =
    filter === 'all'
      ? templates
      : templates.filter((t) =>
          filter === 'light' ? t.color_mode === 'light' : t.color_mode === 'dark'
        )

  if (loading) {
    return (
      <div className="py-12 text-center">
        <div className="inline-block w-8 h-8 border-4 border-orange-200 border-t-orange-500 rounded-full animate-spin" />
        <p className="mt-3 text-gray-500 text-sm">
          {isMalay ? 'Memuatkan templat...' : 'Loading templates...'}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">
          {isMalay ? 'Pilih Gaya Reka Bentuk' : 'Choose a Design Style'}
        </h2>
        <p className="mt-2 text-gray-500 text-sm max-w-md mx-auto">
          {isMalay
            ? 'Pilih templat untuk gaya website anda, atau langkau untuk gaya lalai.'
            : 'Pick a template for your website style, or skip for the default style.'}
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex justify-center gap-2">
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setFilter(cat.id)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
              filter === cat.id
                ? 'bg-orange-500 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {filteredTemplates.map((template) => {
          const isSelected = selectedTemplateId === template.id
          return (
            <button
              key={template.id}
              onClick={() => onSelect(isSelected ? null : template.id)}
              className={`group relative rounded-xl overflow-hidden border-2 transition-all duration-200 text-left ${
                isSelected
                  ? 'border-orange-500 ring-2 ring-orange-200 shadow-lg scale-[1.02]'
                  : 'border-gray-200 hover:border-orange-300 hover:shadow-md'
              }`}
            >
              {/* Recommended badge */}
              {template.recommended && (
                <div className="absolute top-2 left-2 z-10 bg-orange-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm">
                  {isMalay ? 'Disyorkan' : 'Recommended'}
                </div>
              )}

              {/* Color mode badge */}
              <div
                className={`absolute top-2 right-2 z-10 text-[10px] font-medium px-2 py-0.5 rounded-full ${
                  template.color_mode === 'dark'
                    ? 'bg-gray-800 text-gray-200'
                    : 'bg-white text-gray-600 border border-gray-200'
                }`}
              >
                {template.color_mode === 'dark' ? 'Dark' : 'Light'}
              </div>

              {/* Selected checkmark */}
              {isSelected && (
                <div className="absolute top-2 right-2 z-20 bg-orange-500 text-white w-6 h-6 rounded-full flex items-center justify-center shadow-sm">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}

              {/* Preview */}
              <div className="aspect-[3/4] bg-gray-50">
                <TemplatePreviewCard template={template} colors={template.colors} />
              </div>

              {/* Info */}
              <div className="p-3 bg-white">
                <h3 className="font-semibold text-sm text-gray-900 truncate">
                  {isMalay ? template.name_ms : template.name}
                </h3>
                <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-2">
                  {isMalay ? template.description_ms : template.description}
                </p>

                {/* Color swatches */}
                <div className="flex gap-1 mt-2">
                  {[
                    template.colors.primary,
                    template.colors.secondary,
                    template.colors.background,
                    template.colors.text,
                  ].map((color, i) => (
                    <div
                      key={i}
                      className="w-4 h-4 rounded-full border border-gray-200"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </button>
          )
        })}
      </div>

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
        <button
          onClick={onSkip}
          className="px-6 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
        >
          {isMalay ? 'Langkau (Guna Gaya Lalai)' : 'Skip (Use Default Style)'}
        </button>

        {selectedTemplateId && (
          <button
            onClick={() => onSkip()}
            className="px-6 py-2.5 text-sm font-semibold text-white bg-orange-500 hover:bg-orange-600 rounded-xl transition-colors shadow-sm"
          >
            {isMalay ? 'Teruskan dengan Templat Ini' : 'Continue with This Template'}
          </button>
        )}
      </div>
    </div>
  )
}
