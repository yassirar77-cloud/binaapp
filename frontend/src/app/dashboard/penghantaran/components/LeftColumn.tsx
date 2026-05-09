'use client';

import { Plus } from 'lucide-react';
import type { Zone } from '../lib/types';
import ZoneCard from './ZoneCard';
import EmptyState from './EmptyState';
import PostcodeTest, { type PostcodeTestState } from './PostcodeTest';

export default function LeftColumn({
  zones,
  loading,
  isDrawing,
  onAddZone,
  onHoverZone,
  onEditZone,
  onDeleteZone,
  onToggleActive,
  postcodeState,
  postcodeLoading,
  onPostcodeSubmit,
}: {
  zones: Zone[];
  loading: boolean;
  isDrawing: boolean;
  onAddZone: () => void;
  onHoverZone: (id: string | null) => void;
  onEditZone: (zone: Zone) => void;
  onDeleteZone: (zone: Zone) => void;
  onToggleActive: (zone: Zone, active: boolean) => void;
  postcodeState: PostcodeTestState;
  postcodeLoading: boolean;
  onPostcodeSubmit: (postcode: string) => void;
}) {
  return (
    <aside className="flex flex-col h-full overflow-hidden bg-[#0a0e1a]">
      <div className="flex items-center justify-between px-4 lg:px-6 pt-5 pb-3">
        <div>
          <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
            Zon Penghantaran
          </div>
          <div className="font-geist font-semibold text-base text-white">
            {zones.length} zon
          </div>
        </div>
        <button
          type="button"
          onClick={onAddZone}
          disabled={isDrawing}
          className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-[#4F3DFF] text-white font-geist font-medium text-sm hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          <Plus size={14} strokeWidth={2} />
          Zon Baru
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 lg:px-6 pb-4 space-y-2.5">
        {loading ? (
          <div className="space-y-2.5">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-[88px] rounded-xl bg-white/[0.04] animate-pulse"
              />
            ))}
          </div>
        ) : zones.length === 0 ? (
          <EmptyState onAddZone={onAddZone} disabled={isDrawing} />
        ) : (
          zones.map((z) => (
            <ZoneCard
              key={z.id}
              zone={z}
              onHover={onHoverZone}
              onEdit={onEditZone}
              onDelete={onDeleteZone}
              onToggleActive={onToggleActive}
            />
          ))
        )}
      </div>

      <div className="px-4 lg:px-6 pb-5 pt-2 border-t border-white/[0.08]">
        <PostcodeTest
          onSubmit={onPostcodeSubmit}
          state={postcodeState}
          loading={postcodeLoading}
        />
      </div>
    </aside>
  );
}
