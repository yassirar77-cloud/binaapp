'use client';

// TopBar — sticky 56px header on the orders + profile screens.
// Left: rider greeting. Center: GPS status dot + last update time.
// Right: bell (with optional unread dot) + refresh.

import { Bell, RefreshCw } from 'lucide-react';

import type { GpsStatus } from '../lib/types';

interface TopBarProps {
  riderName: string;
  gpsStatus: GpsStatus;
  lastGpsUpdate: Date | null;
  hasNewOrder: boolean;
  refreshing: boolean;
  onRefresh: () => void;
  onBellClick?: () => void;
}

const GPS_DOT_COLOR: Record<GpsStatus, string> = {
  active: '#C7FF3D',
  inactive: '#6b7280',
  error: '#FFB020',
  permission_denied: '#FF5A5F',
};

const GPS_DOT_LABEL: Record<GpsStatus, string> = {
  active: 'GPS aktif',
  inactive: 'GPS tidak aktif',
  error: 'GPS ralat',
  permission_denied: 'GPS ditolak',
};

function fmtTime(d: Date | null): string {
  if (!d) return '—';
  return d.toLocaleTimeString('en-MY', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

export default function TopBar({
  riderName,
  gpsStatus,
  lastGpsUpdate,
  hasNewOrder,
  refreshing,
  onRefresh,
  onBellClick,
}: TopBarProps) {
  const dotColor = GPS_DOT_COLOR[gpsStatus];

  return (
    <header className="sticky top-0 z-30 h-14 px-4 flex items-center gap-3 bg-[var(--rider-bg)]/85 backdrop-blur-md border-b border-[var(--rider-border)]">
      <div className="flex-1 min-w-0">
        <p className="text-[15px] font-medium text-white truncate">
          Hi, <span className="text-[var(--rider-lime)]">{riderName}</span>
        </p>
      </div>

      <div
        className="flex items-center gap-1.5 text-[11px] text-[var(--rider-text-2)]"
        title={GPS_DOT_LABEL[gpsStatus]}
        aria-label={GPS_DOT_LABEL[gpsStatus]}
      >
        <span
          className={`w-2 h-2 rounded-full ${gpsStatus === 'active' ? 'rider-live-dot' : ''}`}
          style={{ backgroundColor: dotColor }}
        />
        <span className="font-mono">GPS {fmtTime(lastGpsUpdate)}</span>
      </div>

      <button
        type="button"
        onClick={onBellClick}
        className="relative w-9 h-9 rounded-full flex items-center justify-center text-[var(--rider-text-2)] hover:text-white hover:bg-[var(--rider-surface)] transition-colors"
        aria-label="Notifikasi"
      >
        <Bell className="w-[18px] h-[18px]" />
        {hasNewOrder && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--rider-red)] rider-live-dot" />
        )}
      </button>

      <button
        type="button"
        onClick={onRefresh}
        disabled={refreshing}
        className="w-9 h-9 rounded-full flex items-center justify-center text-[var(--rider-text-2)] hover:text-white hover:bg-[var(--rider-surface)] transition-colors disabled:opacity-50"
        aria-label="Muat semula"
      >
        <RefreshCw
          className={`w-[18px] h-[18px] ${refreshing ? 'animate-spin' : ''}`}
        />
      </button>
    </header>
  );
}
