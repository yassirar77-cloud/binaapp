'use client'

import { ReactElement, useState } from 'react'
import { BarChart3, X } from 'lucide-react'
import { UsageWidget } from '@/components/UsageWidget'

interface DashboardUsageWidgetProps {
  onUpgradeClick: () => void
  onRenewClick: () => void
}

export default function DashboardUsageWidget({
  onUpgradeClick,
  onRenewClick,
}: DashboardUsageWidgetProps): ReactElement {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      {/* Desktop: collapsible floating widget — bottom-right */}
      <div className="hidden lg:block fixed bottom-6 right-6 z-30">
        {expanded ? (
          <div className="w-72 relative">
            <button
              onClick={() => setExpanded(false)}
              className="absolute -top-2 -right-2 z-40 w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
              aria-label="Tutup widget"
            >
              <X size={14} className="text-white/70" />
            </button>
            <div
              className="rounded-2xl p-0.5 overflow-hidden"
              style={{
                background: 'rgba(11,11,21,0.85)',
                backdropFilter: 'blur(16px)',
                WebkitBackdropFilter: 'blur(16px)',
                border: '1px solid rgba(255,255,255,0.1)',
                boxShadow: '0 20px 40px rgba(0,0,0,0.45)',
              }}
            >
              <UsageWidget
                onUpgradeClick={onUpgradeClick}
                onRenewClick={onRenewClick}
              />
            </div>
          </div>
        ) : (
          <button
            onClick={() => setExpanded(true)}
            className="w-12 h-12 rounded-full flex items-center justify-center transition-all hover:scale-105"
            style={{
              background: 'rgba(11,11,21,0.85)',
              backdropFilter: 'blur(16px)',
              WebkitBackdropFilter: 'blur(16px)',
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: '0 20px 40px rgba(0,0,0,0.45)',
            }}
            aria-label="Lihat penggunaan"
          >
            <BarChart3 size={20} className="text-white/70" />
          </button>
        )}
      </div>

      {/* Mobile: inline within page flow */}
      <div className="lg:hidden mb-6">
        <UsageWidget
          onUpgradeClick={onUpgradeClick}
          onRenewClick={onRenewClick}
          compact
        />
      </div>
    </>
  )
}
