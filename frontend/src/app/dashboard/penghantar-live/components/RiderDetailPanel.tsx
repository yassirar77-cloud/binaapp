'use client';

// RiderDetailPanel — right-side slide-in for a single rider's details.
//
// The "Set offline" action would call PUT /api/v1/delivery/riders/{id}/status,
// which exists but is owned by the legacy delivery router. Out of scope for
// this PR; rendered disabled with a TODO.

import { Bike, Hash, Package, Phone, X } from 'lucide-react';
import type { LiveRider } from '../lib/types';
import { computeRiderPresence } from '../lib/types';

function relativeTime(iso: string | null): string {
  if (!iso) return '—';
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return 'baru sekarang';
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return 'baru sekarang';
  if (minutes < 60) return `${minutes} min lalu`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} jam lalu`;
  const days = Math.floor(hours / 24);
  return `${days} hari lalu`;
}

function cleanPhone(raw: string | null | undefined): string {
  if (!raw) return '';
  return raw.replace(/\D/g, '');
}

const PRESENCE_LABEL = {
  online: { label: 'Online', dot: 'bg-emerald-400', tone: 'text-emerald-300' },
  online_stale_gps: { label: 'Online (GPS lapuk)', dot: 'bg-amber-400', tone: 'text-amber-300' },
  offline: { label: 'Offline', dot: 'bg-white/30', tone: 'text-white/40' },
} as const;

export default function RiderDetailPanel({
  rider,
  onClose,
  onActiveOrderClick,
}: {
  rider: LiveRider;
  onClose: () => void;
  onActiveOrderClick: (orderId: string) => void;
}) {
  const presence = computeRiderPresence(rider);
  const tone = PRESENCE_LABEL[presence];
  const tel = cleanPhone(rider.phone);
  const waMsg = `Hai ${rider.name}, dari outlet…`;
  const waHref = tel ? `https://wa.me/${tel}?text=${encodeURIComponent(waMsg)}` : null;

  return (
    <aside
      className="phl-detail-panel flex flex-col h-full w-[360px] shrink-0 border-l border-white/[0.08] bg-[#0a0e1a]"
      aria-label="Maklumat rider"
    >
      <div className="flex items-start justify-between gap-3 px-4 pt-4 pb-3 border-b border-white/[0.06]">
        <div className="min-w-0">
          <div className="text-base font-geist font-semibold text-white truncate">
            {rider.name}
          </div>
          <div className="mt-1">
            <span
              className={`inline-flex items-center gap-1.5 h-5 px-2 rounded-full font-mono text-[10px] tracking-wide ${tone.tone} bg-white/[0.04] ring-1 ring-white/[0.06]`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
              {tone.label}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Tutup"
          className="h-10 w-10 -mr-2 -mt-1 flex items-center justify-center rounded-lg text-white/60 hover:text-white hover:bg-white/[0.06] transition"
        >
          <X size={18} strokeWidth={1.5} />
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Vehicle */}
        <section className="px-4 py-4 border-b border-white/[0.06] space-y-2">
          <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
            Kenderaan
          </div>
          {rider.vehicle_plate && (
            <div className="flex items-center gap-1.5 text-sm font-mono text-white">
              <Hash size={13} strokeWidth={1.5} className="text-white/50" />
              {rider.vehicle_plate}
            </div>
          )}
          <div className="text-[12px] text-white/60 font-geist">
            {[rider.vehicle_type, rider.vehicle_model].filter(Boolean).join(' · ') ||
              'Tiada maklumat'}
          </div>
          {tel && (
            <a
              href={`tel:${tel}`}
              className="inline-flex items-center gap-1.5 text-[13px] text-white/70 hover:text-white"
            >
              <Phone size={13} strokeWidth={1.5} />
              {rider.phone}
            </a>
          )}
        </section>

        {/* Today stats */}
        <section className="px-4 py-4 border-b border-white/[0.06]">
          <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
            Hari ini
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <Stat
              label="Hantaran"
              value={String(rider.today_deliveries)}
              icon={<Package size={14} strokeWidth={1.5} />}
            />
            <Stat
              label="GPS terakhir"
              value={relativeTime(rider.last_location_update)}
            />
          </div>
        </section>

        {/* Current delivery */}
        <section className="px-4 py-4">
          <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
            Hantaran semasa
          </div>
          {rider.active_order_id ? (
            <button
              type="button"
              onClick={() => onActiveOrderClick(rider.active_order_id!)}
              className="mt-2 w-full text-left rounded-lg bg-[#161623] border border-white/[0.06] hover:border-white/[0.12] px-3 py-3 transition"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] tracking-wider text-white/50 uppercase">
                  {rider.active_order_number}
                </span>
                <span className="text-[11px] text-white/40 font-geist">
                  Lihat pesanan →
                </span>
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[12px] text-white/60">
                <Bike size={12} strokeWidth={1.5} />
                <span className="capitalize">{rider.active_order_status}</span>
              </div>
            </button>
          ) : (
            <div className="mt-2 flex items-center gap-2 text-[13px] text-white/50">
              <Bike size={14} strokeWidth={1.5} />
              Idle — tiada hantaran aktif
            </div>
          )}
        </section>
      </div>

      <div className="border-t border-white/[0.08] bg-[#0a0e1a] px-3 py-3 space-y-2">
        {tel && (
          <ActionLink href={`tel:${tel}`}>Hubungi rider</ActionLink>
        )}
        {waHref && (
          <ActionLink href={waHref} target="_blank" rel="noopener noreferrer">
            Mesej rider (WhatsApp)
          </ActionLink>
        )}
        {/* TODO: wire to PUT /api/v1/delivery/riders/{id}/status when add to lib/api.ts */}
        <button
          type="button"
          disabled
          title="Belum tersedia di halaman ini"
          className="w-full inline-flex items-center justify-center h-11 px-3 rounded-lg text-sm font-geist font-medium bg-white/[0.03] text-white/30 ring-1 ring-white/[0.06] cursor-not-allowed"
        >
          Tetapkan offline
        </button>
      </div>
    </aside>
  );
}

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg bg-[#161623] border border-white/[0.06] px-3 py-2.5">
      <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
        {label}
      </div>
      <div className="mt-1 flex items-center gap-1.5 text-sm font-mono text-white">
        {icon}
        {value}
      </div>
    </div>
  );
}

function ActionLink({
  href,
  target,
  rel,
  children,
}: {
  href: string;
  target?: string;
  rel?: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target={target}
      rel={rel}
      className="w-full inline-flex items-center justify-center h-11 px-3 rounded-lg text-sm font-geist font-medium bg-white/[0.06] text-white hover:bg-white/[0.10] ring-1 ring-white/[0.08] transition"
    >
      {children}
    </a>
  );
}
