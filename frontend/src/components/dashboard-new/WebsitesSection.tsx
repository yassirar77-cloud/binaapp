'use client'

import { ReactElement } from 'react'
import { Plus, Sparkles } from 'lucide-react'
import WebsiteCard, { WebsiteStatus } from './WebsiteCard'

export interface WebsiteItem {
  id: string
  name: string
  subdomain: string
  status: WebsiteStatus
  templateImage?: string
  orders: number
  views: string
}

interface WebsitesSectionProps {
  websites: WebsiteItem[]
  /** Total allowed by plan */
  planLimit?: number
  /** Which website ID is in delete-confirm state */
  deleteConfirmId: string | null
  /** Which website ID is currently being deleted */
  deletingId: string | null
  /** MUST call existing handleCreateWebsiteClick (with limit check) */
  onCreateNew: () => void
  onView: (website: WebsiteItem) => void
  onEdit: (website: WebsiteItem) => void
  onDelete: (websiteId: string) => void
  onDeleteConfirm: (websiteId: string) => void
  onDeleteCancel: () => void
}

export default function WebsitesSection({
  websites,
  planLimit,
  deleteConfirmId,
  deletingId,
  onCreateNew,
  onView,
  onEdit,
  onDelete,
  onDeleteConfirm,
  onDeleteCancel,
}: WebsitesSectionProps): ReactElement {
  return (
    <section className="mb-10">
      {/* Section header */}
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="font-geist font-semibold text-lg text-white tracking-[-0.02em] m-0">
            Website Saya
          </h2>
          {planLimit != null && (
            <p className="font-geist text-[13px] text-ink-400 mt-0.5 mb-0">
              {websites.length} daripada {planLimit} dibenarkan
            </p>
          )}
        </div>
        <button
          onClick={onCreateNew}
          className="flex items-center gap-1.5 bg-volt-400 text-ink-900 border-0 font-geist font-bold text-[13px] py-2.5 px-4 rounded-[10px] cursor-pointer tracking-[-0.005em] hover:brightness-110 transition-all"
          style={{
            boxShadow:
              '0 0 0 1px #A8E81C, 0 6px 16px rgba(199,255,61,0.3)',
          }}
        >
          <Plus size={14} strokeWidth={2.4} /> Bina baru
        </button>
      </div>

      {/* Grid or empty state */}
      {websites.length === 0 ? (
        <EmptyState onCreateNew={onCreateNew} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {websites.map((site) => (
            <WebsiteCard
              key={site.id}
              name={site.name}
              subdomain={site.subdomain}
              status={site.status}
              templateImage={site.templateImage}
              orders={site.orders}
              views={site.views}
              isDeleteConfirm={deleteConfirmId === site.id}
              isDeleting={deletingId === site.id}
              onView={() => onView(site)}
              onEdit={() => onEdit(site)}
              onDelete={() => onDelete(site.id)}
              onDeleteConfirm={() => onDeleteConfirm(site.id)}
              onDeleteCancel={onDeleteCancel}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function EmptyState({
  onCreateNew,
}: {
  onCreateNew: () => void
}): ReactElement {
  return (
    <div className="dash-surface-flat text-center py-20 px-6">
      <div className="w-16 h-16 rounded-2xl bg-brand-500/[0.15] border border-brand-300/25 grid place-items-center mx-auto mb-5">
        <Sparkles size={28} className="text-brand-300" />
      </div>
      <h3 className="font-geist font-semibold text-xl text-white tracking-[-0.02em] mb-2">
        Belum ada website
      </h3>
      <p className="font-geist text-sm text-ink-400 mb-6 max-w-xs mx-auto">
        Mula dengan AI — upload menu atau taip maklumat kedai anda.
      </p>
      <button
        onClick={onCreateNew}
        className="inline-flex items-center gap-2 bg-volt-400 text-ink-900 border-0 font-geist font-bold text-sm py-3 px-6 rounded-xl cursor-pointer hover:brightness-110 transition-all"
        style={{
          boxShadow:
            '0 0 0 1px #A8E81C, 0 6px 16px rgba(199,255,61,0.3)',
        }}
      >
        <Plus size={16} strokeWidth={2.4} /> Bina Website Pertama
      </button>
    </div>
  )
}
