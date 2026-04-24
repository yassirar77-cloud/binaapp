'use client'

import { ReactElement } from 'react'
import { UsageWidget } from '@/components/UsageWidget'

interface DashboardUsageWidgetProps {
  onUpgradeClick: () => void
  onRenewClick: () => void
}

export default function DashboardUsageWidget({
  onUpgradeClick,
  onRenewClick,
}: DashboardUsageWidgetProps): ReactElement {
  return (
    <>
      {/* Desktop: floating bottom-right */}
      <div className="hidden lg:block fixed bottom-6 right-6 w-72 z-30">
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
