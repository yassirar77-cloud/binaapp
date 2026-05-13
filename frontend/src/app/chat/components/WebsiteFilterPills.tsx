'use client';

// Outlet filter pills. Renders nothing when the user owns just one website
// (no choice to make). 'Semua' is the all-outlets value 'all'.

import type { Website } from '../lib/types';

interface Props {
  websites: Website[];
  selectedWebsiteId: string | 'all';
  onChange: (id: string | 'all') => void;
}

const getLabel = (w: Website) => w.name || w.business_name || 'Outlet';

export default function WebsiteFilterPills({
  websites,
  selectedWebsiteId,
  onChange,
}: Props) {
  if (websites.length <= 1) return null;

  return (
    <div className="px-3 py-2 border-b border-white/[0.06]">
      <div className="chat-hscroll flex items-center gap-1.5 overflow-x-auto">
        <PillButton
          active={selectedWebsiteId === 'all'}
          onClick={() => onChange('all')}
          label="Semua"
        />
        {websites.map((w) => (
          <PillButton
            key={w.id}
            active={selectedWebsiteId === w.id}
            onClick={() => onChange(w.id)}
            label={getLabel(w)}
          />
        ))}
      </div>
    </div>
  );
}

function PillButton({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'shrink-0 inline-flex items-center h-7 px-3 rounded-full',
        'font-geist text-xs whitespace-nowrap transition-colors',
        active
          ? 'bg-[#C7FF3D] text-[#0a0e1a]'
          : 'bg-white/[0.04] text-white/70 ring-1 ring-white/[0.08] hover:bg-white/[0.08]',
      ].join(' ')}
    >
      {label}
    </button>
  );
}
