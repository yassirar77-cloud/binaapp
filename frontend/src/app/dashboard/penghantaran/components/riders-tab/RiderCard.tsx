'use client';

import { Pencil, Trash2 } from 'lucide-react';
import type { Rider } from '../../lib/types';
import { vehicleTypeLabel } from './vehicle';

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export default function RiderCard({
  rider,
  onEdit,
  onDelete,
}: {
  rider: Rider;
  onEdit: (rider: Rider) => void;
  onDelete: (rider: Rider) => void;
}) {
  return (
    <div className="group rounded-xl bg-[#161623] border border-white/[0.08] hover:border-white/[0.16] transition px-4 py-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div
            aria-hidden
            className={`h-10 w-10 rounded-full shrink-0 flex items-center justify-center font-geist font-semibold text-sm ${
              rider.is_active
                ? 'bg-[#4F3DFF]/20 text-[#b3a8ff]'
                : 'bg-white/[0.06] text-white/40'
            }`}
          >
            {initials(rider.name)}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-geist font-semibold text-sm text-white truncate">
                {rider.name}
              </span>
              {rider.is_online ? (
                <span className="inline-flex items-center gap-1 shrink-0 px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-mono text-[10px] tracking-wider uppercase">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  Online
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 shrink-0 px-1.5 py-0.5 rounded-full bg-white/[0.06] text-zinc-400 font-mono text-[10px] tracking-wider uppercase">
                  <span className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
                  Offline
                </span>
              )}
              {!rider.is_active && (
                <span className="shrink-0 px-1.5 py-0.5 rounded-full bg-white/[0.04] text-white/40 font-mono text-[10px] tracking-wider uppercase">
                  Tidak aktif
                </span>
              )}
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[11px] text-white/50">
              <span className="font-mono">{rider.phone}</span>
              {rider.vehicle_plate && (
                <>
                  <span aria-hidden>·</span>
                  <span className="font-mono">{rider.vehicle_plate}</span>
                </>
              )}
              <span aria-hidden>·</span>
              <span>{vehicleTypeLabel(rider.vehicle_type)}</span>
              <span aria-hidden>·</span>
              <span>
                <span className="font-mono text-white/70">
                  {rider.total_deliveries ?? 0}
                </span>{' '}
                hantaran
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => onEdit(rider)}
            className="p-1.5 rounded-md text-white/60 hover:text-white hover:bg-white/[0.06] transition"
            title="Edit"
            aria-label={`Edit rider ${rider.name}`}
          >
            <Pencil size={15} strokeWidth={1.5} />
          </button>
          <button
            type="button"
            onClick={() => onDelete(rider)}
            className="p-1.5 rounded-md text-white/60 hover:text-red-400 hover:bg-red-500/10 transition"
            title="Padam"
            aria-label={`Padam rider ${rider.name}`}
          >
            <Trash2 size={15} strokeWidth={1.5} />
          </button>
        </div>
      </div>
    </div>
  );
}
