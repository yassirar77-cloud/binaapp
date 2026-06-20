'use client';

import { Plus } from 'lucide-react';
import type { Zone } from '../lib/types';
import RingCard from './RingCard';
import OutletLocationCard from './OutletLocationCard';
import PostcodeTest, { type PostcodeTestState } from './PostcodeTest';

export default function LeftColumn({
  zones,
  loading,
  hasOutletLocation,
  outletAddress,
  outletPickerMode,
  onToggleOutletPicker,
  onAddRing,
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
  hasOutletLocation: boolean;
  outletAddress: string | null;
  outletPickerMode: boolean;
  onToggleOutletPicker: () => void;
  onAddRing: () => void;
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
      <div className="px-4 lg:px-6 pt-5 pb-3">
        <OutletLocationCard
          address={outletAddress}
          hasLocation={hasOutletLocation}
          picking={outletPickerMode}
          onTogglePick={onToggleOutletPicker}
        />
      </div>

      <div className="flex items-center justify-between px-4 lg:px-6 pb-3">
        <div>
          <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
            Ring Penghantaran
          </div>
          <div className="font-geist font-semibold text-base text-white">
            {zones.length} ring
          </div>
        </div>
        <button
          type="button"
          onClick={onAddRing}
          disabled={!hasOutletLocation}
          title={hasOutletLocation ? 'Tambah ring' : 'Tetapkan lokasi kedai dahulu'}
          className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-[#4F3DFF] text-white font-geist font-medium text-sm hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          <Plus size={14} strokeWidth={2} />
          Ring Baru
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 lg:px-6 pb-4 space-y-2.5">
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
          <div className="flex flex-col items-center justify-center text-center px-6 py-10 rounded-xl bg-white/[0.02] border border-white/[0.06]">
            <div className="text-3xl mb-2">🍱</div>
            <h3 className="font-geist font-semibold text-base text-white">
              Belum ada ring
            </h3>
            <p className="mt-1 text-sm text-white/60 max-w-xs">
              {hasOutletLocation
                ? 'Tambah ring pertama untuk mula menerima pesanan delivery dalam radius tertentu.'
                : 'Tetapkan lokasi kedai dahulu, kemudian tambah ring.'}
            </p>
            {hasOutletLocation && (
              <button
                type="button"
                onClick={onAddRing}
                className="mt-5 inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-[#C7FF3D] text-black font-geist font-semibold text-sm hover:brightness-110 transition"
              >
                <Plus size={16} strokeWidth={2} />
                Tambah Ring Pertama
              </button>
            )}
          </div>
        ) : (
          zones.map((z) => (
            <RingCard
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
