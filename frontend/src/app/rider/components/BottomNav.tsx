'use client';

// BottomNav — 2-tab bar fixed to the bottom of the orders + profile
// screens. Hidden on /login + /detail (those screens manage their own
// nav). Safe-area aware for iOS home indicator.

import { List, User } from 'lucide-react';

interface BottomNavProps {
  active: 'orders' | 'profile';
  onSelect: (tab: 'orders' | 'profile') => void;
}

const TABS: Array<{ id: 'orders' | 'profile'; label: string; Icon: typeof List }> = [
  { id: 'orders',  label: 'Pesanan', Icon: List },
  { id: 'profile', label: 'Saya',    Icon: User },
];

export default function BottomNav({ active, onSelect }: BottomNavProps) {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-30 bg-[var(--rider-bg)]/95 backdrop-blur-md border-t border-[var(--rider-border)] rider-safe-pb"
      role="tablist"
    >
      <div className="h-16 flex items-stretch">
        {TABS.map(({ id, label, Icon }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onSelect(id)}
              className="flex-1 flex flex-col items-center justify-center gap-0.5 transition-colors"
            >
              <Icon
                className={`w-[22px] h-[22px] ${isActive ? 'text-[var(--rider-lime)]' : 'text-[var(--rider-text-2)]'}`}
                strokeWidth={isActive ? 2.5 : 2}
              />
              <span
                className={`text-[11px] font-medium ${isActive ? 'text-[var(--rider-lime)]' : 'text-[var(--rider-text-2)]'}`}
              >
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
