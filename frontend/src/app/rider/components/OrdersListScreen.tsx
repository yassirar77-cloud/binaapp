'use client';

// OrdersListScreen — TopBar + filter tabs + (optional) new-order banner +
// scrollable order list + empty state per tab. Parent owns the data; this
// component is presentational over a filtered slice.

import { Inbox } from 'lucide-react';

import { STATUS_META, TABS } from '../lib/constants';
import type { GpsStatus, OrderStatus, Rider, RiderOrder, Tab } from '../lib/types';
import NewOrderBanner from './NewOrderBanner';
import OrderRow from './OrderRow';
import TopBar from './TopBar';

interface OrdersListScreenProps {
  rider: Rider;
  orders: RiderOrder[];
  newOrder: RiderOrder | null;
  tab: Tab;
  pendingOrderId: string | null;
  refreshing: boolean;
  gpsStatus: GpsStatus;
  lastGpsUpdate: Date | null;
  onTab: (tab: Tab) => void;
  onRefresh: () => void;
  onOpen: (order: RiderOrder) => void;
  onAdvance: (order: RiderOrder, next: OrderStatus) => void;
  onAcceptNew: (order: RiderOrder) => void;
  onRejectNew: (order: RiderOrder) => void;
}

const EMPTY_STATE: Record<Tab, string> = {
  aktif:   'Tiada pesanan aktif. Tunggu pesanan baru.',
  baru:    'Tiada pesanan baru.',
  selesai: 'Belum siap pesanan hari ini.',
};

// Returns ISO timestamp at UTC midnight today — used to scope the
// `selesai` (today) tab.
function utcDayStartIso(): string {
  const d = new Date();
  d.setUTCHours(0, 0, 0, 0);
  return d.toISOString();
}

function filterByTab(orders: RiderOrder[], tab: Tab): RiderOrder[] {
  const meta = TABS.find((t) => t.id === tab);
  if (!meta) return orders;
  const allowed = new Set<OrderStatus>(meta.statuses);
  const todayStart = tab === 'selesai' ? utcDayStartIso() : null;

  return orders
    .filter((o) => {
      if (!allowed.has(o.status)) return false;
      if (todayStart) {
        // Use delivered_at when available, fall back to created_at so a
        // stale row without delivered_at doesn't disappear forever.
        const ts = o.delivered_at || o.created_at;
        return ts >= todayStart;
      }
      return true;
    })
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
}

export default function OrdersListScreen({
  rider,
  orders,
  newOrder,
  tab,
  pendingOrderId,
  refreshing,
  gpsStatus,
  lastGpsUpdate,
  onTab,
  onRefresh,
  onOpen,
  onAdvance,
  onAcceptNew,
  onRejectNew,
}: OrdersListScreenProps) {
  const visible = filterByTab(orders, tab);

  // Precompute counts per tab once so badges don't allocate on every render.
  const counts = {
    aktif: filterByTab(orders, 'aktif').length,
    baru: filterByTab(orders, 'baru').length,
    selesai: filterByTab(orders, 'selesai').length,
  } as Record<Tab, number>;

  return (
    <div className="min-h-[100dvh] pb-20">
      <TopBar
        riderName={rider.name}
        gpsStatus={gpsStatus}
        lastGpsUpdate={lastGpsUpdate}
        hasNewOrder={!!newOrder}
        refreshing={refreshing}
        onRefresh={onRefresh}
      />

      {/* Filter tabs */}
      <div className="px-4 pt-3 flex gap-2 overflow-x-auto rider-hscroll">
        {TABS.map((t) => {
          const isActive = t.id === tab;
          const count = counts[t.id];
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onTab(t.id)}
              className={`shrink-0 h-9 px-3.5 rounded-full text-[13px] font-medium border transition-colors flex items-center gap-1.5 ${
                isActive
                  ? 'bg-[var(--rider-lime)] border-[var(--rider-lime)] text-black'
                  : 'bg-[var(--rider-surface)] border-[var(--rider-border)] text-[var(--rider-text-2)] hover:text-white'
              }`}
            >
              {t.label}
              {count > 0 && (
                <span
                  className={`min-w-[20px] h-5 px-1.5 rounded-full text-[10px] font-semibold flex items-center justify-center ${
                    isActive
                      ? 'bg-black/10 text-black'
                      : 'bg-[var(--rider-surface-2)] text-[var(--rider-text-2)]'
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {newOrder && (
        <NewOrderBanner
          order={newOrder}
          onAccept={onAcceptNew}
          onReject={onRejectNew}
        />
      )}

      {/* List */}
      <div className="pt-1 pb-4">
        {visible.length === 0 ? (
          <div className="mx-4 mt-8 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] py-12 px-6 flex flex-col items-center text-center rider-fade-in">
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center mb-3"
              style={{ backgroundColor: STATUS_META.ready.bg }}
            >
              <Inbox
                className="w-6 h-6"
                style={{ color: STATUS_META.ready.color }}
              />
            </div>
            <p className="text-sm text-[var(--rider-text-2)]">
              {EMPTY_STATE[tab]}
            </p>
          </div>
        ) : (
          visible.map((o) => (
            <OrderRow
              key={o.id}
              order={o}
              pending={pendingOrderId === o.id}
              onOpen={onOpen}
              onAdvance={onAdvance}
            />
          ))
        )}
      </div>
    </div>
  );
}
