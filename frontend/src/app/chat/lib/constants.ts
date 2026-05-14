// /chat — UI constants.
// TABS order: Semua → Belum Dibaca → Aktif → Pesanan → Sokongan → Ditutup.
// Each tab carries its own match() predicate so filter logic stays declarative.

import type { Conversation, TabKey } from './types';

export interface TabDef {
  id: TabKey;
  label: string;
  match: (c: Conversation) => boolean;
}

export const TABS: TabDef[] = [
  { id: 'all', label: 'Semua', match: () => true },
  {
    id: 'unread',
    label: 'Belum Dibaca',
    match: (c) => (c.unread_owner ?? 0) > 0,
  },
  { id: 'active', label: 'Aktif', match: (c) => c.status === 'active' },
  { id: 'order', label: 'Pesanan', match: (c) => !!c.order_id },
  { id: 'support', label: 'Sokongan', match: (c) => !c.order_id },
  { id: 'closed', label: 'Ditutup', match: (c) => c.status === 'closed' },
];

export const POLL_INTERVAL_MS = 30_000;
export const SEARCH_DEBOUNCE_MS = 300;
