'use client';

import { Settings, Trash2 } from 'lucide-react';
import type { Zone } from '../lib/types';
import { formatKm2, polygonAreaM2 } from '../lib/polygon';

const DAY_SHORT: Array<{ key: keyof Zone['schedule_json']; label: string }> = [
  { key: 'mon', label: 'I' },
  { key: 'tue', label: 'S' },
  { key: 'wed', label: 'R' },
  { key: 'thu', label: 'K' },
  { key: 'fri', label: 'J' },
  { key: 'sat', label: 'S' },
  { key: 'sun', label: 'A' },
];

export default function ZoneCard({
  zone,
  onHover,
  onEdit,
  onDelete,
  onToggleActive,
}: {
  zone: Zone;
  onHover: (id: string | null) => void;
  onEdit: (zone: Zone) => void;
  onDelete: (zone: Zone) => void;
  onToggleActive: (zone: Zone, active: boolean) => void;
}) {
  const km2 = formatKm2(zone.area_m2 ?? polygonAreaM2(zone.polygon));
  const fee = (zone.fee_cents / 100).toFixed(2);
  const minOrder = (zone.min_order_cents / 100).toFixed(0);

  return (
    <div
      onMouseEnter={() => onHover(zone.id)}
      onMouseLeave={() => onHover(null)}
      className="group rounded-xl bg-[#161623] border border-white/[0.08] hover:border-white/[0.16] transition px-4 py-3.5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <span
            aria-hidden
            className="mt-1 inline-block h-3 w-3 rounded-sm shrink-0"
            style={{
              backgroundColor: zone.color,
              opacity: zone.active ? 1 : 0.35,
            }}
          />
          <div className="min-w-0">
            <div className="font-geist font-semibold text-sm text-white truncate">
              {zone.name}
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-white/50 font-mono">
              <span>{km2} km²</span>
              <span aria-hidden>·</span>
              <span>RM {fee}</span>
              <span aria-hidden>·</span>
              <span>min RM {minOrder}</span>
            </div>
          </div>
        </div>
        <label className="relative inline-flex items-center cursor-pointer shrink-0">
          <input
            type="checkbox"
            className="sr-only peer"
            checked={zone.active}
            onChange={(e) => onToggleActive(zone, e.target.checked)}
          />
          <div className="w-9 h-5 bg-white/10 rounded-full peer peer-checked:bg-[#C7FF3D] transition" />
          <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition peer-checked:translate-x-4" />
        </label>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-1">
          {DAY_SHORT.map(({ key, label }) => {
            const day = zone.schedule_json?.[key];
            const active = day?.active ?? false;
            return (
              <span
                key={key}
                className={`inline-flex items-center justify-center h-5 w-5 rounded text-[10px] font-mono ${
                  active
                    ? 'bg-white/[0.08] text-white'
                    : 'bg-white/[0.02] text-white/30'
                }`}
                title={`${key}: ${day?.open ?? '—'}–${day?.close ?? '—'}`}
              >
                {label}
              </span>
            );
          })}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onEdit(zone)}
            className="p-1.5 rounded-md text-white/60 hover:text-white hover:bg-white/[0.06] transition"
            title="Tetapan"
            aria-label={`Edit zon ${zone.name}`}
          >
            <Settings size={15} strokeWidth={1.5} />
          </button>
          <button
            type="button"
            onClick={() => onDelete(zone)}
            className="p-1.5 rounded-md text-white/60 hover:text-red-400 hover:bg-red-500/10 transition"
            title="Padam"
            aria-label={`Padam zon ${zone.name}`}
          >
            <Trash2 size={15} strokeWidth={1.5} />
          </button>
        </div>
      </div>
    </div>
  );
}
