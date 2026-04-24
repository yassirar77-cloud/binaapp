'use client'

import { ReactElement } from 'react'
import { ExternalLink, Edit2, Trash2, Globe } from 'lucide-react'

export type WebsiteStatus = 'published' | 'draft' | 'paused'

interface WebsiteCardProps {
  /** Website name */
  name: string
  /** Subdomain, e.g. "mamakabc.binaapp.my" */
  subdomain: string
  /** Publishing status */
  status: WebsiteStatus
  /** Template preview image URL (optional) */
  templateImage?: string
  /** Total orders count */
  orders: number
  /** Total views display string */
  views: string
  /** Delete in-progress (shows confirm state) */
  isDeleteConfirm?: boolean
  /** Currently deleting */
  isDeleting?: boolean
  /** Callbacks */
  onView?: () => void
  onEdit?: () => void
  onDelete?: () => void
  onDeleteConfirm?: () => void
  onDeleteCancel?: () => void
}

const STATUS_CONFIG: Record<
  WebsiteStatus,
  { label: string; color: string; glow: boolean }
> = {
  published: { label: 'Hidup', color: '#22C08F', glow: true },
  draft: { label: 'Draf', color: '#86869A', glow: false },
  paused: { label: 'Dipadam', color: '#FF5A5F', glow: true },
}

export default function WebsiteCard({
  name,
  subdomain,
  status,
  templateImage,
  orders,
  views,
  isDeleteConfirm = false,
  isDeleting = false,
  onView,
  onEdit,
  onDelete,
  onDeleteConfirm,
  onDeleteCancel,
}: WebsiteCardProps): ReactElement {
  const isDraft = status === 'draft'
  const statusCfg = STATUS_CONFIG[status]

  return (
    <div className="dash-surface-flat overflow-hidden flex flex-col">
      {/* Template preview */}
      <div className="relative aspect-[16/10] overflow-hidden border-b border-white/[0.05]">
        {templateImage ? (
          <img
            src={templateImage}
            alt={name}
            className={`w-full h-full object-cover block ${
              isDraft ? 'grayscale-[0.6] brightness-[0.7]' : ''
            }`}
          />
        ) : (
          <div
            className={`w-full h-full bg-gradient-to-br from-brand-500/20 to-brand-700/20 grid place-items-center ${
              isDraft ? 'opacity-50' : ''
            }`}
          >
            <Globe className="w-12 h-12 text-brand-300 opacity-50" />
          </div>
        )}
        {/* Status badge */}
        <div
          className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full backdrop-blur-lg"
          style={{
            background: 'rgba(11,11,21,0.85)',
            border: `1px solid ${statusCfg.color}${statusCfg.glow ? '59' : '24'}`,
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: statusCfg.color,
              boxShadow: statusCfg.glow
                ? `0 0 8px ${statusCfg.color}`
                : 'none',
            }}
          />
          <span
            className="font-geist-mono text-[10px] tracking-[0.1em] uppercase font-semibold"
            style={{ color: statusCfg.color }}
          >
            {statusCfg.label}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-[18px] flex flex-col gap-3.5 flex-1">
        {/* Name + subdomain */}
        <div>
          <h3 className="font-geist font-semibold text-base text-white tracking-[-0.02em] mb-1">
            {name}
          </h3>
          <div className="font-geist-mono text-[11.5px] text-ink-400 flex items-center gap-1.5">
            <Globe size={11} strokeWidth={1.8} /> {subdomain}
          </div>
        </div>

        {/* Stats row */}
        <div className="flex gap-5 py-2.5 border-t border-b border-white/[0.05]">
          <div>
            <div className="dash-eyebrow text-[9px] mb-0.5">Pesanan</div>
            <div
              className="font-geist font-semibold text-[15px] dash-tnum"
              style={{ color: isDraft ? '#6E6E80' : '#fff' }}
            >
              {orders}
            </div>
          </div>
          <div>
            <div className="dash-eyebrow text-[9px] mb-0.5">Lawatan</div>
            <div
              className="font-geist font-semibold text-[15px] dash-tnum"
              style={{ color: isDraft ? '#6E6E80' : '#fff' }}
            >
              {views}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-1.5">
          <button
            onClick={onView}
            className="flex-1 flex items-center justify-center gap-1.5 bg-white/[0.04] text-white border border-white/[0.08] font-geist text-[12.5px] py-2 px-2.5 rounded-[9px] cursor-pointer font-medium hover:bg-white/[0.08] transition-colors"
          >
            <ExternalLink size={12} /> Lihat
          </button>
          <button
            onClick={onEdit}
            className="flex-1 flex items-center justify-center gap-1.5 bg-brand-500/[0.14] text-brand-200 border border-brand-300/25 font-geist text-[12.5px] py-2 px-2.5 rounded-[9px] cursor-pointer font-medium hover:bg-brand-500/20 transition-colors"
          >
            <Edit2 size={12} /> Ubah
          </button>
          {isDeleteConfirm ? (
            <button
              onClick={onDeleteConfirm}
              disabled={isDeleting}
              className="flex-1 flex items-center justify-center bg-err-400 hover:bg-err-500 text-white font-geist text-[12.5px] py-2 px-2.5 rounded-[9px] cursor-pointer font-medium transition-colors disabled:opacity-50"
            >
              {isDeleting ? '...' : 'Pasti?'}
            </button>
          ) : (
            <button
              onClick={onDelete}
              className="bg-white/[0.04] text-ink-400 border border-white/[0.08] py-2 px-2.5 rounded-[9px] cursor-pointer grid place-items-center hover:bg-white/[0.08] hover:text-err-400 transition-colors"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>

        {/* Cancel delete */}
        {isDeleteConfirm && (
          <button
            onClick={onDeleteCancel}
            className="w-full text-xs text-ink-400 hover:text-ink-300 transition-colors"
          >
            Batal
          </button>
        )}
      </div>
    </div>
  )
}
