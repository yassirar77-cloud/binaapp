// /pesanan — status metadata + timeline definitions.
// The pages /dashboard/penghantaran and /dashboard/penghantar-live keep their
// own status maps; this one is local so label/color tweaks here don't ripple.

import type { OrderStatus, TabKey } from './types';

export interface StatusMeta {
  /** Long Malay label used in the detail panel. */
  label: string;
  /** Short Malay label used inside pills on dense cards. */
  short: string;
  /** Pill color (hex). */
  color: string;
  /** Which tab this status groups under. */
  tab: TabKey;
}

export const STATUS_META: Record<OrderStatus, StatusMeta> = {
  pending:    { label: 'Menunggu Pengesahan', short: 'Menunggu',  color: '#f59e0b', tab: 'baru' },
  confirmed:  { label: 'Disahkan',            short: 'Disahkan',  color: '#3b82f6', tab: 'aktif' },
  preparing:  { label: 'Sedang Disiapkan',    short: 'Disiapkan', color: '#a855f7', tab: 'aktif' },
  ready:      { label: 'Sedia Diambil',       short: 'Sedia',     color: '#06b6d4', tab: 'aktif' },
  picked_up:  { label: 'Dipickup Rider',      short: 'Dipickup',  color: '#6366f1', tab: 'aktif' },
  delivering: { label: 'Sedang Dihantar',     short: 'Dihantar',  color: '#6366f1', tab: 'aktif' },
  delivered:  { label: 'Telah Dihantar',      short: 'Dihantar',  color: '#10b981', tab: 'selesai' },
  completed:  { label: 'Selesai',             short: 'Selesai',   color: '#10b981', tab: 'selesai' },
  cancelled:  { label: 'Dibatalkan',          short: 'Batal',     color: '#ef4444', tab: 'batal' },
  rejected:   { label: 'Ditolak',             short: 'Tolak',     color: '#ef4444', tab: 'batal' },
};

/** Neutral fallback for unknown / legacy enum values (e.g. the dead 'assigned'). */
export const STATUS_META_FALLBACK: StatusMeta = {
  label: 'Status tidak diketahui',
  short: 'N/A',
  color: '#6b7280',
  tab: 'aktif',
};

export function statusMeta(status: string): StatusMeta {
  return (STATUS_META as Record<string, StatusMeta>)[status] ?? STATUS_META_FALLBACK;
}

export interface TimelineStep {
  key: string;
  label: string;
  /** Statuses for which this step is rendered as completed. */
  matches: ReadonlyArray<OrderStatus>;
}

export const TIMELINE_STEPS: ReadonlyArray<TimelineStep> = [
  { key: 'pending',    label: 'Diterima',  matches: ['pending','confirmed','preparing','ready','picked_up','delivering','delivered','completed'] },
  { key: 'confirmed',  label: 'Disahkan',  matches: ['confirmed','preparing','ready','picked_up','delivering','delivered','completed'] },
  { key: 'preparing',  label: 'Disiapkan', matches: ['preparing','ready','picked_up','delivering','delivered','completed'] },
  { key: 'ready',      label: 'Sedia',     matches: ['ready','picked_up','delivering','delivered','completed'] },
  { key: 'delivering', label: 'Dihantar',  matches: ['picked_up','delivering','delivered','completed'] },
  { key: 'completed',  label: 'Selesai',   matches: ['delivered','completed'] },
];

/** Tab definitions in display order. */
export const TABS: ReadonlyArray<{ key: TabKey; label: string }> = [
  { key: 'semua',   label: 'Semua' },
  { key: 'baru',    label: 'Baru' },
  { key: 'aktif',   label: 'Aktif' },
  { key: 'selesai', label: 'Selesai' },
  { key: 'batal',   label: 'Batal' },
];

export const DATE_RANGE_LABELS: Record<string, string> = {
  today:     'Hari ini',
  yesterday: 'Semalam',
  '7days':   '7 hari',
  '30days':  '30 hari',
  custom:    'Tarikh khas',
};

/** Auto-refresh cadence for the orders polling loop. */
export const POLL_INTERVAL_MS = 30_000;
