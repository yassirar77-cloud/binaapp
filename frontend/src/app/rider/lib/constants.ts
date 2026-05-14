// /rider — constants.
// Colors picked from the dark-navy + lime design family. STATUS_META is the
// single source of truth for status colors; do not inline hex values in
// components.

import type { OrderStatus, Tab } from './types';

export const STATUS_META: Record<
  OrderStatus,
  { label: string; color: string; bg: string; border: string }
> = {
  pending:    { label: 'Menunggu',      color: '#86869A', bg: 'rgba(134,134,154,0.10)', border: 'rgba(134,134,154,0.25)' },
  confirmed:  { label: 'Disahkan',      color: '#8F80FF', bg: 'rgba(143,128,255,0.10)', border: 'rgba(143,128,255,0.25)' },
  preparing:  { label: 'Sedia',         color: '#8F80FF', bg: 'rgba(143,128,255,0.10)', border: 'rgba(143,128,255,0.25)' },
  ready:      { label: 'Bersedia',      color: '#FFB020', bg: 'rgba(255,176,32,0.10)',  border: 'rgba(255,176,32,0.30)' },
  picked_up:  { label: 'Diambil',       color: '#C7FF3D', bg: 'rgba(199,255,61,0.10)',  border: 'rgba(199,255,61,0.30)' },
  delivering: { label: 'Sedang Hantar', color: '#C7FF3D', bg: 'rgba(199,255,61,0.10)',  border: 'rgba(199,255,61,0.30)' },
  delivered:  { label: 'Dihantar',      color: '#22C08F', bg: 'rgba(34,192,143,0.10)',  border: 'rgba(34,192,143,0.30)' },
  completed:  { label: 'Selesai',       color: '#22C08F', bg: 'rgba(34,192,143,0.10)',  border: 'rgba(34,192,143,0.30)' },
  cancelled:  { label: 'Dibatalkan',    color: '#FF5A5F', bg: 'rgba(255,90,95,0.10)',   border: 'rgba(255,90,95,0.30)' },
  rejected:   { label: 'Ditolak',       color: '#FF5A5F', bg: 'rgba(255,90,95,0.10)',   border: 'rgba(255,90,95,0.30)' },
};

// Status → next-step action shown on order rows and bottom CTA. Mirrors
// the backend state machine in delivery.update_order_status_by_rider.
export const ACTION_LABELS: Partial<
  Record<OrderStatus, { label: string; nextStatus: OrderStatus }>
> = {
  ready:      { label: 'Mula Ambil',  nextStatus: 'picked_up'  },
  picked_up:  { label: 'Mula Hantar', nextStatus: 'delivering' },
  delivering: { label: 'Selesai',    nextStatus: 'delivered'  },
};

// Order-list filter pills. `selesai` is filtered to today only by the
// component; this list just declares the status set.
export const TABS: Array<{ id: Tab; label: string; statuses: OrderStatus[] }> = [
  { id: 'aktif',   label: 'Aktif',            statuses: ['ready', 'picked_up', 'delivering'] },
  { id: 'baru',    label: 'Baru',             statuses: ['confirmed', 'preparing'] },
  { id: 'selesai', label: 'Selesai Hari Ini', statuses: ['delivered', 'completed'] },
];

// GPS upload cadence — must stay at 15s to match the backend rate limits
// and keep parity with the pre-redesign behavior.
export const GPS_INTERVAL_MS = 15000;

// Poll orders this often while logged in.
export const FETCH_INTERVAL_MS = 30000;
