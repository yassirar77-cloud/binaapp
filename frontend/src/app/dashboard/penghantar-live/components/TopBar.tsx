'use client';

import { ChevronDown, RefreshCw, Store, Volume2, VolumeX } from 'lucide-react';
import type { ActiveOrder, LiveRider, Outlet } from '../lib/types';
import { computeRiderPresence } from '../lib/types';

const IN_PROGRESS_STATUSES = new Set(['picked_up', 'delivering']);

function formatClock(d: Date | null): string {
  if (!d) return '—';
  return d.toLocaleTimeString('ms-MY', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

export default function TopBar({
  outlets,
  selectedOutletId,
  onOutletChange,
  orders,
  riders,
  stuckCount,
  realtimeUp,
  lastUpdatedAt,
  refreshing,
  onRefresh,
  soundEnabled,
  onToggleSound,
}: {
  outlets: Outlet[];
  selectedOutletId: string | null;
  onOutletChange: (id: string) => void;
  orders: ActiveOrder[];
  riders: LiveRider[];
  stuckCount: number;
  realtimeUp: boolean;
  lastUpdatedAt: Date | null;
  refreshing: boolean;
  onRefresh: () => void;
  soundEnabled: boolean;
  onToggleSound: () => void;
}) {
  const inProgress = orders.filter((o) => IN_PROGRESS_STATUSES.has(o.status)).length;
  const onlineRiders = riders.filter(
    (r) => computeRiderPresence(r) !== 'offline',
  ).length;

  const stats: Array<{ label: string; value: string; tone: 'normal' | 'alert' }> = [
    { label: 'Dalam Perjalanan', value: String(inProgress), tone: 'normal' },
    { label: 'Rider Online', value: `${onlineRiders}/${riders.length}`, tone: 'normal' },
    { label: 'Tersangkut', value: String(stuckCount), tone: stuckCount > 0 ? 'alert' : 'normal' },
  ];

  return (
    <div className="w-full px-4 lg:px-6 py-4 border-b border-white/[0.08] bg-[#0a0e1a]/95 backdrop-blur-sm sticky top-0 z-20">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="font-geist font-semibold text-lg sm:text-xl text-white tracking-[-0.02em] shrink-0">
            Penghantar Live
          </h1>
          {outlets.length > 0 && (
            <div className="relative shrink min-w-0">
              <Store
                size={14}
                strokeWidth={1.5}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
              <select
                value={selectedOutletId ?? ''}
                onChange={(e) => onOutletChange(e.target.value)}
                className="appearance-none h-10 pl-9 pr-9 max-w-[240px] truncate rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist focus:outline-none focus:border-white/[0.16]"
              >
                {outlets.map((o) => (
                  <option key={o.id} value={o.id} className="bg-[#161623]">
                    {o.name}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={14}
                strokeWidth={1.5}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none"
              />
            </div>
          )}

          {/* Feed health: realtime vs polling + last successful refetch. */}
          <div
            className="hidden sm:flex items-center gap-2 shrink-0"
            title={
              realtimeUp
                ? 'Sambungan masa nyata aktif'
                : 'Mod tinjauan — data disegarkan setiap 15 saat'
            }
          >
            <span
              className={`inline-flex items-center gap-1.5 h-6 px-2 rounded-full font-mono text-[10px] tracking-wider uppercase ring-1 ${
                realtimeUp
                  ? 'text-emerald-300 bg-emerald-400/10 ring-emerald-400/20'
                  : 'text-amber-300 bg-amber-400/10 ring-amber-400/20'
              }`}
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  realtimeUp ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
              {realtimeUp ? 'Live' : 'Tinjauan'}
            </span>
            <span className="font-mono text-[10px] text-white/40">
              {formatClock(lastUpdatedAt)}
            </span>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing}
              aria-label="Segarkan data"
              title="Segarkan data"
              className="h-9 w-9 flex items-center justify-center rounded-lg text-white/60 hover:text-white hover:bg-white/[0.06] transition disabled:opacity-50"
            >
              <RefreshCw
                size={15}
                strokeWidth={1.5}
                className={refreshing ? 'animate-spin' : ''}
              />
            </button>
            <button
              type="button"
              onClick={onToggleSound}
              aria-label={
                soundEnabled ? 'Matikan bunyi amaran' : 'Hidupkan bunyi amaran'
              }
              title={
                soundEnabled
                  ? 'Bunyi amaran: hidup (pesanan baru & tersangkut)'
                  : 'Bunyi amaran: mati'
              }
              className={`h-9 w-9 flex items-center justify-center rounded-lg transition ${
                soundEnabled
                  ? 'text-[#C7FF3D] hover:bg-white/[0.06]'
                  : 'text-white/40 hover:text-white hover:bg-white/[0.06]'
              }`}
            >
              {soundEnabled ? (
                <Volume2 size={15} strokeWidth={1.5} />
              ) : (
                <VolumeX size={15} strokeWidth={1.5} />
              )}
            </button>
          </div>
        </div>

        {/* Compact mobile stat: single line, hides on md+. */}
        <div className="md:hidden flex items-center gap-2">
          <span className="font-mono text-[11px] tracking-wide text-white/50">
            {inProgress} dalam perjalanan
          </span>
          {stuckCount > 0 && (
            <span className="inline-flex items-center gap-1 h-5 px-2 rounded-full font-mono text-[10px] tracking-wide text-red-300 bg-red-400/10 ring-1 ring-red-400/20">
              <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
              {stuckCount}
            </span>
          )}
        </div>

        <div className="hidden md:grid grid-cols-3 gap-3 sm:gap-6">
          {stats.map((s) => (
            <div key={s.label} className="text-right">
              <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
                {s.label}
              </div>
              <div
                className={`font-mono font-semibold text-base sm:text-lg ${
                  s.tone === 'alert' ? 'text-red-300' : 'text-white'
                }`}
              >
                {s.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
