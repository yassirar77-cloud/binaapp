'use client';

// Full-width page chrome under DashboardHeader. Title + LIVE indicator with
// last-refresh time + manual refresh button. Outlet picking moved to the
// pills row inside the list panel (see WebsiteFilterPills.tsx).

import { Bell, RefreshCw } from 'lucide-react';

interface Props {
  unreadTotal: number;
  loading: boolean;
  lastRefresh: Date | null;
  onRefresh: () => void;
}

function formatTime(d: Date | null): string {
  if (!d) return '—';
  return d.toLocaleTimeString('ms-MY', { hour: '2-digit', minute: '2-digit' });
}

export default function TopBar({
  unreadTotal,
  loading,
  lastRefresh,
  onRefresh,
}: Props) {
  return (
    <div className="w-full px-4 lg:px-6 py-3 sm:py-4 border-b border-white/[0.08]">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <h1 className="font-geist font-semibold text-base sm:text-xl text-white tracking-[-0.02em] shrink-0">
            Chat
          </h1>
          <span className="inline-flex items-center gap-1.5 h-6 px-2 rounded-full bg-emerald-400/10 ring-1 ring-emerald-400/20">
            <span className="chat-live-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="font-mono text-[10px] tracking-wider uppercase text-emerald-300">
              Live
            </span>
          </span>
          <span className="hidden sm:inline font-mono text-[10px] tracking-wide text-white/40">
            {formatTime(lastRefresh)}
          </span>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Unread chip — always shown so '0' reads as a stable state. */}
          <span
            className={`inline-flex items-center gap-1 h-6 px-2 rounded-full font-mono text-[10px] tracking-wide ring-1 ${
              unreadTotal > 0
                ? 'text-[#C7FF3D] bg-[#C7FF3D]/10 ring-[#C7FF3D]/20'
                : 'text-white/50 bg-white/[0.04] ring-white/[0.08]'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                unreadTotal > 0 ? 'bg-[#C7FF3D]' : 'bg-white/40'
              }`}
            />
            {unreadTotal} belum dibaca
          </span>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              aria-label="Notifikasi"
              className="relative inline-flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors"
            >
              <Bell size={14} strokeWidth={1.5} className="sm:hidden" />
              <Bell size={16} strokeWidth={1.5} className="hidden sm:block" />
              {unreadTotal > 0 && (
                <span className="absolute top-1 right-1 sm:top-1.5 sm:right-1.5 h-2 w-2 rounded-full bg-[#C7FF3D] ring-2 ring-[#0a0e1a]" />
              )}
            </button>
            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              aria-label="Muat semula"
              className="inline-flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors disabled:opacity-50"
            >
              <RefreshCw
                size={14}
                strokeWidth={1.5}
                className={`sm:hidden ${loading ? 'animate-spin' : ''}`}
              />
              <RefreshCw
                size={16}
                strokeWidth={1.5}
                className={`hidden sm:block ${loading ? 'animate-spin' : ''}`}
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
