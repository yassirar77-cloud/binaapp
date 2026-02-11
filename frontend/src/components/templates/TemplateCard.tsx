'use client'

import { useRef, useEffect, useState } from 'react'
import TemplatePreview from './TemplatePreview'

export interface AnimatedTemplate {
  id: string
  styleKey: string
  name: string
  nameMy: string
  categories: string[]
  tag: string
  isNew?: boolean
}

interface TemplateCardProps {
  template: AnimatedTemplate
  isSelected: boolean
  onSelect: (id: string) => void
  language: 'ms' | 'en'
  index: number
}

export default function TemplateCard({
  template,
  isSelected,
  onSelect,
  language,
  index,
}: TemplateCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const el = cardRef.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting)
      },
      { threshold: 0.1 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const isMalay = language === 'ms'
  const displayName = isMalay ? template.nameMy : template.name

  return (
    <div
      ref={cardRef}
      data-category={template.categories.join(',')}
      className="group relative rounded-xl overflow-hidden transition-all duration-300 cursor-pointer"
      style={{
        background: '#12121a',
        border: isSelected ? '2px solid #ff6b35' : '2px solid rgba(255,255,255,0.06)',
        boxShadow: isSelected ? '0 0 20px rgba(255,107,53,0.2)' : 'none',
        animation: `fadeUp 0.5s ease-out ${index * 0.06}s both`,
      }}
      onClick={() => onSelect(template.id)}
    >
      {/* Preview area */}
      <div className="relative" style={{ height: '240px' }}>
        <TemplatePreview styleKey={template.styleKey} isVisible={isVisible} />

        {/* Hover overlay with button */}
        <div
          className="absolute inset-0 flex items-end justify-center pb-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{ background: 'linear-gradient(transparent 40%, rgba(0,0,0,0.7) 100%)' }}
        >
          <span
            className="px-4 py-1.5 rounded-full text-xs font-semibold transition-transform duration-300 group-hover:translate-y-0 translate-y-2"
            style={{
              background: '#ff6b35',
              color: '#fff',
            }}
          >
            {isMalay ? 'Guna Templat Ini' : 'Use This Template'}
          </span>
        </div>

        {/* NEW badge */}
        {template.isNew && (
          <div
            className="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider z-20"
            style={{
              background: 'linear-gradient(135deg, #00E5A0, #00B8D4)',
              color: '#0D0D0D',
              boxShadow: '0 2px 8px rgba(0,229,160,0.4)',
            }}
          >
            NEW
          </div>
        )}

        {/* Selected checkmark */}
        {isSelected && (
          <div
            className="absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center z-20"
            style={{ background: '#ff6b35' }}
          >
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </div>

      {/* Info bar */}
      <div className="px-3 py-2.5 flex items-center justify-between" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <span className="text-sm font-semibold text-white/90 truncate">{displayName}</span>
        <span
          className="text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0 ml-2"
          style={{
            background: 'rgba(255,107,53,0.1)',
            color: '#ff6b35',
          }}
        >
          {template.tag}
        </span>
      </div>
    </div>
  )
}
