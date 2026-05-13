'use client';

// Six-tab status row inside the list panel. Counts derived from each tab's
// match() predicate so a tab definition is self-contained.

import type { Conversation, TabKey } from '../lib/types';
import { TABS } from '../lib/constants';

interface Props {
  tab: TabKey;
  onTabChange: (next: TabKey) => void;
  conversations: Conversation[];
}

function countForTab(convs: Conversation[], key: TabKey): number {
  const def = TABS.find((t) => t.id === key);
  if (!def) return 0;
  let n = 0;
  for (const c of convs) if (def.match(c)) n++;
  return n;
}

export default function TabBar({ tab, onTabChange, conversations }: Props) {
  return (
    <div className="w-full border-b border-white/[0.06]">
      <div
        className="chat-hscroll flex items-center gap-1 overflow-x-auto -mb-px px-2"
        role="tablist"
      >
        {TABS.map(({ id, label }) => {
          const active = tab === id;
          const count = countForTab(conversations, id);
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onTabChange(id)}
              className={[
                'shrink-0 inline-flex items-center gap-2 px-3 h-10',
                'border-b-2 font-geist text-xs sm:text-sm transition-colors',
                active
                  ? 'border-[#C7FF3D] text-white'
                  : 'border-transparent text-white/55 hover:text-white/80',
              ].join(' ')}
            >
              <span>{label}</span>
              {count > 0 && (
                <span
                  className={[
                    'inline-flex items-center justify-center min-w-[18px] h-[18px] px-1.5',
                    'rounded-full font-mono text-[10px] tracking-wide',
                    active
                      ? 'bg-[#C7FF3D]/15 text-[#C7FF3D] ring-1 ring-[#C7FF3D]/30'
                      : 'bg-white/[0.06] text-white/60 ring-1 ring-white/10',
                  ].join(' ')}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
