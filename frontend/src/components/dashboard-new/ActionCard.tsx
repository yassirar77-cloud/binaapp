'use client'

import { ReactElement, ReactNode } from 'react'
import { ArrowRight } from 'lucide-react'

interface ActionCardMeta {
  dotColor: string
  label: string
  pulse?: boolean
}

interface ActionCardProps {
  /** Icon element (lucide-react) */
  icon: ReactNode
  /** Card title, e.g. "Urus Penghantaran" */
  title: string
  /** Description text */
  description: string
  /** Status meta line at bottom */
  meta: ActionCardMeta
  /** Accent hue for icon background */
  hue: string
  /** Link destination */
  href?: string
  /** Featured card (volt glow) */
  featured?: boolean
  /** Click handler */
  onClick?: () => void
}

export default function ActionCard({
  icon,
  title,
  description,
  meta,
  hue,
  href,
  featured = false,
  onClick,
}: ActionCardProps): ReactElement {
  const Tag = href ? 'a' : 'div'

  return (
    <Tag
      href={href}
      onClick={onClick}
      className={`
        block no-underline cursor-pointer relative overflow-hidden
        rounded-[18px] p-[22px]
        transition-transform duration-200 ease-[cubic-bezier(.25,1,.5,1)]
        hover:scale-[1.01] hover:border-white/10
        ${featured
          ? 'bg-gradient-to-b from-ink-800 to-[#0F0F1F] border border-volt-400/[0.18]'
          : 'bg-ink-800 border border-white/[0.07]'
        }
      `}
    >
      {/* Featured accent glow */}
      {featured && (
        <div
          className="absolute -top-[30px] -right-[30px] w-[140px] h-[140px] rounded-full pointer-events-none"
          style={{
            background: `radial-gradient(circle, ${hue}22, transparent 70%)`,
          }}
        />
      )}

      {/* Top row: icon + arrow */}
      <div className="flex justify-between items-start mb-7">
        <div
          className="w-11 h-11 rounded-xl grid place-items-center"
          style={
            featured
              ? {
                  background: 'linear-gradient(135deg, #C7FF3D, #A8E81C)',
                  color: '#0B0B15',
                  boxShadow: '0 8px 24px rgba(199,255,61,0.25)',
                }
              : {
                  background: `${hue}1F`,
                  border: `1px solid ${hue}33`,
                  color: hue,
                }
          }
        >
          {icon}
        </div>
        <div className="w-8 h-8 rounded-full bg-white/[0.04] border border-white/[0.06] grid place-items-center text-ink-400">
          <ArrowRight size={14} strokeWidth={2} />
        </div>
      </div>

      {/* Title + description */}
      <h3 className="font-geist font-semibold text-[19px] text-white tracking-[-0.025em] mb-1.5">
        {title}
      </h3>
      <p className="font-geist text-[13.5px] text-ink-400 leading-relaxed tracking-[-0.005em] mb-5">
        {description}
      </p>

      {/* Meta line */}
      <div className="dash-divider pt-3.5 flex items-center gap-2">
        <StatusDot color={meta.dotColor} pulse={meta.pulse} />
        <span className="font-geist-mono text-[11px] text-ink-300 tracking-[-0.005em]">
          {meta.label}
        </span>
      </div>
    </Tag>
  )
}

function StatusDot({
  color,
  pulse,
}: {
  color: string
  pulse?: boolean
}): ReactElement {
  return (
    <span className="relative inline-block w-[7px] h-[7px]">
      {pulse && (
        <span
          className="absolute -inset-0.5 rounded-full opacity-30 animate-pulse-red"
          style={{ background: color }}
        />
      )}
      <span
        className="absolute inset-0 rounded-full"
        style={{
          background: color,
          boxShadow: `0 0 8px ${color}80`,
        }}
      />
    </span>
  )
}
