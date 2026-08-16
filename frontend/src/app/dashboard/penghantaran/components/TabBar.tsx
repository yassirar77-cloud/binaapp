'use client';

import { Bike, CircleDot, Settings2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type DeliveryTab = 'ring' | 'rider' | 'tetapan';

const TABS: Array<{ key: DeliveryTab; label: string; icon: LucideIcon }> = [
  { key: 'ring', label: 'Ring', icon: CircleDot },
  { key: 'rider', label: 'Rider', icon: Bike },
  { key: 'tetapan', label: 'Tetapan', icon: Settings2 },
];

export default function TabBar({
  activeTab,
  onChange,
  ringCount,
}: {
  activeTab: DeliveryTab;
  onChange: (tab: DeliveryTab) => void;
  ringCount?: number;
}) {
  return (
    <div className="px-4 lg:px-6 border-b border-white/[0.08] bg-[#0a0e1a] shrink-0">
      <div
        role="tablist"
        aria-label="Bahagian penghantaran"
        className="flex gap-1 overflow-x-auto scrollbar-hide -mb-px"
      >
        {TABS.map(({ key, label, icon: Icon }) => {
          const active = activeTab === key;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onChange(key)}
              className={`inline-flex items-center gap-1.5 px-4 py-3 font-geist font-medium text-sm whitespace-nowrap transition border-b-2 ${
                active
                  ? 'text-white border-[#C7FF3D]'
                  : 'text-white/50 border-transparent hover:text-white/80'
              }`}
            >
              <Icon size={14} strokeWidth={1.5} />
              {label}
              {key === 'ring' && ringCount != null && ringCount > 0 && (
                <span
                  className={`font-mono text-[10px] px-1.5 py-0.5 rounded-full ${
                    active
                      ? 'bg-[#C7FF3D]/15 text-[#C7FF3D]'
                      : 'bg-white/[0.06] text-white/40'
                  }`}
                >
                  {ringCount}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
