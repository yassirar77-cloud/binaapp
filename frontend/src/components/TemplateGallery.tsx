'use client'

import { useState, useMemo } from 'react'
import TemplateCard, { AnimatedTemplate } from '@/components/templates/TemplateCard'

const ANIMATED_TEMPLATES: AnimatedTemplate[] = [
  {
    id: 'particle-globe',
    styleKey: 'particle-globe',
    name: 'Particle Globe',
    nameMy: 'Glob Zarah',
    categories: ['premium', 'gelap'],
    tag: 'Premium',
  },
  {
    id: 'gradient-wave',
    styleKey: 'gradient-wave',
    name: 'Gradient Wave',
    nameMy: 'Gelombang Gradien',
    categories: ['gelap', 'ceria'],
    tag: 'Vibrant',
  },
  {
    id: 'floating-food',
    styleKey: 'floating-food',
    name: 'Floating Food',
    nameMy: 'Makanan Terapung',
    categories: ['gelap', 'ceria'],
    tag: 'Vibrant',
  },
  {
    id: 'neon-grid',
    styleKey: 'neon-grid',
    name: 'Neon Grid',
    nameMy: 'Grid Neon',
    categories: ['gelap', 'premium'],
    tag: 'Dark',
  },
  {
    id: 'morphing-blob',
    styleKey: 'morphing-blob',
    name: 'Morphing Blob',
    nameMy: 'Blob Berubah',
    categories: ['gelap', 'minimal'],
    tag: 'Minimal',
  },
  {
    id: 'matrix-code',
    styleKey: 'matrix-code',
    name: 'Matrix Code',
    nameMy: 'Kod Matrix',
    categories: ['gelap'],
    tag: 'Dark',
  },
  {
    id: 'aurora',
    styleKey: 'aurora',
    name: 'Aurora Borealis',
    nameMy: 'Aurora',
    categories: ['premium', 'gelap', 'ceria'],
    tag: 'Premium',
  },
  {
    id: 'spotlight',
    styleKey: 'spotlight',
    name: 'Spotlight',
    nameMy: 'Sorotan',
    categories: ['gelap', 'minimal'],
    tag: 'Minimal',
  },
  {
    id: 'parallax-layers',
    styleKey: 'parallax-layers',
    name: 'Parallax Layers',
    nameMy: 'Lapisan Paralaks',
    categories: ['premium', 'ceria'],
    tag: 'Premium',
  },
  {
    id: 'word-explosion',
    styleKey: 'word-explosion',
    name: 'Word Explosion',
    nameMy: 'Letupan Kata',
    categories: ['ceria', 'premium'],
    tag: 'New',
    isNew: true,
  },
  {
    id: 'ghost-restaurant',
    styleKey: 'ghost-restaurant',
    name: 'Ghost Restaurant',
    nameMy: 'Restoran Hantu',
    categories: ['gelap', 'premium'],
    tag: 'New',
    isNew: true,
  },
]

interface TemplateGalleryProps {
  language: 'ms' | 'en'
  businessType?: string
  onSelect: (templateId: string | null) => void
  onSkip: () => void
  selectedTemplateId: string | null
}

const FILTERS = [
  { id: 'semua', labelMs: 'Semua', labelEn: 'All' },
  { id: 'gelap', labelMs: 'Gelap', labelEn: 'Dark' },
  { id: 'cerah', labelMs: 'Cerah', labelEn: 'Light' },
  { id: 'ceria', labelMs: 'Ceria', labelEn: 'Vibrant' },
  { id: 'minimal', labelMs: 'Minimal', labelEn: 'Minimal' },
  { id: 'premium', labelMs: 'Premium', labelEn: 'Premium' },
]

export default function TemplateGallery({
  language,
  onSelect,
  onSkip,
  selectedTemplateId,
}: TemplateGalleryProps) {
  const [filter, setFilter] = useState('semua')
  const isMalay = language === 'ms'

  const filtered = useMemo(() => {
    if (filter === 'semua') return ANIMATED_TEMPLATES
    return ANIMATED_TEMPLATES.filter((t) => t.categories.includes(filter))
  }, [filter])

  function handleSelect(id: string) {
    onSelect(selectedTemplateId === id ? null : id)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white">
          {isMalay ? 'Pilih Gaya Reka Bentuk' : 'Choose a Design Style'}
        </h2>
        <p className="mt-2 text-sm max-w-md mx-auto" style={{ color: 'rgba(255,255,255,0.5)' }}>
          {isMalay
            ? 'Pilih gaya animasi untuk hero section website anda, atau langkau untuk gaya lalai.'
            : 'Pick an animated style for your website hero, or skip for the default.'}
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex flex-wrap justify-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className="px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200"
            style={{
              background: filter === f.id ? '#ff6b35' : 'rgba(255,255,255,0.06)',
              color: filter === f.id ? '#fff' : 'rgba(255,255,255,0.5)',
              boxShadow: filter === f.id ? '0 2px 10px rgba(255,107,53,0.3)' : 'none',
            }}
          >
            {isMalay ? f.labelMs : f.labelEn}
          </button>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((template, i) => (
          <TemplateCard
            key={template.id}
            template={template}
            isSelected={selectedTemplateId === template.id}
            onSelect={handleSelect}
            language={language}
            index={i}
          />
        ))}
      </div>

      {/* No results */}
      {filtered.length === 0 && (
        <div className="text-center py-12">
          <p className="text-sm" style={{ color: 'rgba(255,255,255,0.4)' }}>
            {isMalay ? 'Tiada templat dalam kategori ini.' : 'No templates in this category.'}
          </p>
        </div>
      )}

      {/* Skip link */}
      <div className="flex justify-center pt-2">
        <button
          onClick={onSkip}
          className="px-6 py-2.5 text-sm font-medium rounded-xl transition-all duration-200"
          style={{
            background: 'rgba(255,255,255,0.06)',
            color: 'rgba(255,255,255,0.5)',
          }}
        >
          {isMalay ? 'Langkau — Guna Gaya Lalai' : 'Skip — Use Default Style'}
        </button>
      </div>
    </div>
  )
}
