'use client';

// Anchored rider-picker popover. Rendered conditionally next to a "Pilih
// Rider" trigger (OrderCard action area OR OrderDetailPanel footer). The
// parent owns the open/close state; this component handles ESC + outside
// click + sorting + per-row assigning state.
//
// Placement is fixed by parent classes via the `align` + `placement` props,
// not measured from JS — keeps the popover behavior predictable across
// scroll positions and viewport sizes.

import { Bike, Phone } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { Rider } from '../lib/types';

interface Props {
  orderId: string;
  websiteId: string;
  allRiders: Rider[];
  /** Above the trigger (panel footer) or below it (card action area). */
  placement: 'above' | 'below';
  /** Horizontal alignment relative to the wrapper. */
  align: 'left' | 'right';
  onClose: () => void;
  /** Returns once the API call resolves (success or failure). The picker
   *  closes itself on success; on failure stays open and unsets the row
   *  loading state. */
  onAssign: (orderId: string, rider: Rider) => Promise<boolean>;
}

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .map((p) => p[0] ?? '')
    .join('')
    .slice(0, 2)
    .toUpperCase() || '?';
}

/** Stable rider sort: online first (alpha asc), then offline (alpha asc). */
function sortRiders(riders: Rider[]): Rider[] {
  const onl = riders.filter((r) => r.is_online);
  const off = riders.filter((r) => !r.is_online);
  const byName = (a: Rider, b: Rider) =>
    a.name.localeCompare(b.name, 'ms-MY', { sensitivity: 'base' });
  onl.sort(byName);
  off.sort(byName);
  return [...onl, ...off];
}

export default function RiderPickerDropdown({
  orderId,
  websiteId,
  allRiders,
  placement,
  align,
  onClose,
  onAssign,
}: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [assigningId, setAssigningId] = useState<string | null>(null);

  // Filter to riders owned by the order's outlet, then sort.
  const riders = useMemo(
    () => sortRiders(allRiders.filter((r) => r.website_id === websiteId)),
    [allRiders, websiteId],
  );

  // ESC + outside click. mousedown (not click) so we close before a card
  // body click handler fires under the popover.
  useEffect(() => {
    const onDocMouse = (e: MouseEvent) => {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', onDocMouse);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocMouse);
      document.removeEventListener('keydown', onKey);
    };
  }, [onClose]);

  const handlePick = async (rider: Rider) => {
    if (assigningId) return; // ignore double-clicks while one is in flight
    setAssigningId(rider.id);
    const ok = await onAssign(orderId, rider);
    if (!ok) {
      // Failure: stay open so user can retry / pick another rider.
      setAssigningId(null);
    }
    // Success: parent unmounts the picker; no need to clear state.
  };

  const posClasses = [
    'absolute z-30 w-[300px] max-w-[90vw]',
    placement === 'above' ? 'bottom-full mb-2' : 'top-full mt-2',
    align === 'right' ? 'right-0' : 'left-0',
  ].join(' ');

  return (
    <div
      ref={ref}
      role="dialog"
      aria-label="Pilih rider"
      className={`${posClasses} pesanan-fade-in rounded-xl bg-[#11152a] ring-1 ring-white/[0.1] shadow-2xl shadow-black/40 overflow-hidden`}
      // Stop bubbling so the parent card / cards-container doesn't treat this
      // as a select / close-panel click.
      onClick={(e) => e.stopPropagation()}
    >
      <div className="px-3 py-2.5 border-b border-white/[0.06] flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-white/50">
          Pilih Rider
        </span>
        <span className="font-mono text-[10px] text-white/35">
          {riders.length}
        </span>
      </div>

      {riders.length === 0 ? (
        <div className="px-3 py-6 text-center">
          <div className="font-geist text-xs text-white/65">
            Tiada rider aktif.
          </div>
          <div className="mt-1 font-geist text-[11px] text-white/40">
            Tambah rider di halaman Penghantar.
          </div>
        </div>
      ) : (
        <ul className="max-h-[320px] overflow-y-auto py-1">
          {riders.map((r) => {
            const busy = assigningId === r.id;
            const disabled = !!assigningId && !busy;
            return (
              <li key={r.id}>
                <button
                  type="button"
                  disabled={disabled || busy}
                  onClick={() => handlePick(r)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                    busy
                      ? 'bg-[#C7FF3D]/10'
                      : 'hover:bg-white/[0.04] disabled:opacity-40'
                  }`}
                >
                  <div
                    className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center font-geist font-semibold text-[11px] ring-1 ${
                      r.is_online
                        ? 'bg-[#C7FF3D]/15 ring-[#C7FF3D]/25 text-[#C7FF3D]'
                        : 'bg-white/[0.05] ring-white/[0.08] text-white/50'
                    }`}
                  >
                    {initials(r.name)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="font-geist font-medium text-sm text-white truncate">
                        {r.name}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 h-4 px-1.5 rounded-full font-mono text-[9px] tracking-wider shrink-0 ${
                          r.is_online
                            ? 'bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/20'
                            : 'bg-white/[0.04] text-white/40 ring-1 ring-white/10'
                        }`}
                      >
                        <span
                          className={`h-1 w-1 rounded-full ${
                            r.is_online ? 'bg-emerald-400' : 'bg-white/40'
                          }`}
                        />
                        {r.is_online ? 'Online' : 'Offline'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 text-[11px] text-white/50 font-mono">
                      {r.vehicle_plate ? (
                        <span className="inline-flex items-center gap-1">
                          <Bike size={10} strokeWidth={1.5} />
                          {r.vehicle_plate}
                        </span>
                      ) : null}
                      <span className="inline-flex items-center gap-1">
                        <Phone size={10} strokeWidth={1.5} />
                        {r.phone}
                      </span>
                    </div>
                  </div>
                  {busy ? (
                    <span className="shrink-0 font-mono text-[10px] text-[#C7FF3D] tracking-wide">
                      …
                    </span>
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
