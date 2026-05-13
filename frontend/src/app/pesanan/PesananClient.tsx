'use client';

// /pesanan — main client wrapper.
// Owns data + filter state, renders the chrome (DashboardHeader / TopBar /
// TabBar / FilterBar) and the card list. The detail panel lands in Phase 6.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { getCurrentUser } from '@/lib/supabase';
import DashboardHeader from '@/components/dashboard-new/DashboardHeader';
import {
  ApiError,
  assignRider,
  getOrders,
  getRidersForWebsites,
  getWebsites,
  updateOrderStatus,
} from './lib/api';
import type {
  DateRange,
  Order,
  Rider,
  TabKey,
  Website,
} from './lib/types';
import { POLL_INTERVAL_MS, statusMeta } from './lib/constants';
import TopBar from './components/TopBar';
import TabBar from './components/TabBar';
import FilterBar from './components/FilterBar';
import OrderCard from './components/OrderCard';
import EmptyState from './components/EmptyState';
import OrderDetailPanel from './components/OrderDetailPanel';
import RejectModal from './components/RejectModal';

export default function PesananClient() {
  const router = useRouter();

  // ----- Data -----
  const [orders, setOrders] = useState<Order[]>([]);
  const [websites, setWebsites] = useState<Website[]>([]);
  // Riders are fetched but not consumed by the chrome; the picker will read
  // from this state in Phase 7.
  const [riders, setRiders] = useState<Rider[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [userName, setUserName] = useState('Pengguna');

  // ----- Filter state -----
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string | 'all'>('all');
  const [tab, setTab] = useState<TabKey>('semua');
  const [searchQuery, setSearchQuery] = useState('');
  /** Debounced (300ms) mirror of searchQuery; used for the actual filter so
   *  typing doesn't recompute the list on every keystroke. */
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [dateRange, setDateRange] = useState<DateRange>('today');

  // ----- Selection state -----
  /** Selected card; detail panel plugs into this in Phase 6. */
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  /** Order id currently being accepted via API (to disable buttons inline). */
  const [acceptingId, setAcceptingId] = useState<string | null>(null);
  /** Order id currently being marked completed via API. */
  const [completingId, setCompletingId] = useState<string | null>(null);
  /** Order id whose RiderPickerDropdown is open. At most one open at a time;
   *  consumers (OrderCard / OrderDetailPanel) decide where to anchor. */
  const [ridersPickerOpenFor, setRidersPickerOpenFor] = useState<string | null>(
    null,
  );
  /** Order whose RejectModal is open. Stored as the full Order object so the
   *  modal can render even if the order momentarily disappears mid-refetch. */
  const [rejectModalFor, setRejectModalFor] = useState<Order | null>(null);

  // ----- Bookkeeping -----
  const mountedRef = useRef(true);
  /** True until the first non-empty orders fetch resolves; used to land on the
   *  right default tab without overriding user choice afterwards. */
  const defaultTabAppliedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // ----- Toast + error helpers -----
  //
  // Centralized so all toast calls go through one duration policy + 401 +
  // network-failure handling. Success: 3s. Error: 5s. 401 → /login.
  // Network failures map to a friendly Malay message regardless of the
  // upstream throw text.

  const reportSuccess = useCallback((msg: string) => {
    toast.success(msg, { duration: 3000 });
  }, []);

  /** Toast an error and, on 401, kick to /login. `silent` suppresses the toast
   *  but still triggers the 401 redirect — used by background polling so we
   *  don't spam users while their network is flaky. */
  const reportError = useCallback(
    (e: unknown, fallback: string, opts: { silent?: boolean } = {}) => {
      if (e instanceof ApiError && e.status === 401) {
        router.push('/login');
        return;
      }
      if (opts.silent) return;
      const msg =
        e instanceof ApiError && e.status === 0
          ? 'Tiada sambungan. Periksa internet anda.'
          : e instanceof Error && e.message
            ? e.message
            : fallback;
      toast.error(msg, { duration: 5000 });
    },
    [router],
  );

  // ----- Refresh logic -----

  const refreshOrders = useCallback(
    async (refreshOpts: { silent?: boolean } = {}): Promise<Order[] | null> => {
      try {
        const o = await getOrders();
        if (!mountedRef.current) return null;
        setOrders(o);
        setLastRefresh(new Date());
        return o;
      } catch (e) {
        if (!mountedRef.current) return null;
        reportError(e, 'Gagal muat semula pesanan. Sila cuba lagi.', {
          silent: refreshOpts.silent,
        });
        return null;
      }
    },
    [reportError],
  );

  // Resolve display name for DashboardHeader once on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await getCurrentUser();
        if (cancelled || !user) return;
        const u = user as { user_metadata?: { full_name?: string }; email?: string };
        setUserName(
          u.user_metadata?.full_name || u.email?.split('@')[0] || 'Pengguna',
        );
      } catch {
        // Silent: header just keeps the default name.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('binaapp_token');
      localStorage.removeItem('binaapp_user');
    }
    router.push('/');
  }, [router]);

  // Initial load — websites + orders + riders.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const ws = await getWebsites();
        if (cancelled) return;
        setWebsites(ws);
        const ids = ws.map((w) => w.id);
        const [o, r] = await Promise.all([
          getOrders(),
          ids.length > 0 ? getRidersForWebsites(ids) : Promise.resolve([] as Rider[]),
        ]);
        if (cancelled) return;
        setOrders(o);
        setRiders(r);
        setLastRefresh(new Date());
      } catch (e) {
        if (cancelled) return;
        reportError(e, 'Gagal muat pesanan. Sila refresh halaman.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reportError]);

  // Background polling — 30s. Silent on toast (no spam during flaky network)
  // but 401 still redirects so a dead session forces re-auth.
  useEffect(() => {
    const id = window.setInterval(() => {
      void refreshOrders({ silent: true });
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [refreshOrders]);

  // Default tab landing: once the first order list arrives, if there are
  // pending orders we land on 'baru'. Only runs once so it doesn't fight the
  // user's later tab choices.
  useEffect(() => {
    if (defaultTabAppliedRef.current) return;
    if (loading) return;
    defaultTabAppliedRef.current = true;
    const hasPending = orders.some((o) => o.status === 'pending');
    if (hasPending) setTab('baru');
  }, [loading, orders]);

  // Search debounce — collapses keystroke bursts inside a 300ms window.
  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => window.clearTimeout(t);
  }, [searchQuery]);

  // ----- Derived counts (shared across chrome) -----

  const pendingCount = useMemo(
    () => orders.filter((o) => o.status === 'pending').length,
    [orders],
  );

  // ----- Filter + sort -----

  const filteredOrders = useMemo(() => {
    const bounds = dateRangeBounds(dateRange, Date.now());
    const q = debouncedSearch.trim().toLowerCase();

    const matches = orders.filter((o) => {
      if (selectedWebsiteId !== 'all' && o.website_id !== selectedWebsiteId) {
        return false;
      }
      if (tab !== 'semua' && statusMeta(o.status).tab !== tab) {
        return false;
      }
      const ts = new Date(o.created_at).getTime();
      if (ts < bounds.start || ts >= bounds.end) return false;
      if (q) {
        const hay = `${o.order_number} ${o.customer_name} ${o.customer_phone}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    // Newest first.
    matches.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    return matches;
  }, [orders, selectedWebsiteId, tab, debouncedSearch, dateRange]);

  /** Distinguish "no orders at all" (empty state A) from "filter mismatch"
   *  (empty state B). Determined off raw `orders`, not filtered. */
  const hasAnyOrders = orders.length > 0;

  // ----- Selection helpers + action handlers -----

  const websiteById = useMemo(() => {
    const m = new Map<string, Website>();
    for (const w of websites) m.set(w.id, w);
    return m;
  }, [websites]);

  const riderById = useMemo(() => {
    const m = new Map<string, Rider>();
    for (const r of riders) m.set(r.id, r);
    return m;
  }, [riders]);

  const handleSelectOrder = useCallback((order: Order) => {
    setSelectedOrderId((prev) => (prev === order.id ? null : order.id));
  }, []);

  const handleAcceptOrder = useCallback(
    async (order: Order) => {
      setAcceptingId(order.id);
      try {
        await updateOrderStatus(order.id, 'confirmed', 'Pesanan disahkan oleh pemilik');
        reportSuccess(`Pesanan #${order.order_number} diterima`);
        await refreshOrders();
      } catch (e) {
        reportError(
          e,
          `Gagal terima pesanan #${order.order_number}. Sila cuba lagi.`,
        );
      } finally {
        if (mountedRef.current) setAcceptingId(null);
      }
    },
    [refreshOrders, reportSuccess, reportError],
  );

  const handleRejectOrder = useCallback((order: Order) => {
    setRejectModalFor(order);
  }, []);

  const handleCloseRejectModal = useCallback(() => {
    setRejectModalFor(null);
  }, []);

  /** Returns true on success so the modal closes itself, false on failure
   *  so it stays open + clears its submitting state. */
  const handleConfirmReject = useCallback(
    async (order: Order, reason: string): Promise<boolean> => {
      try {
        await updateOrderStatus(
          order.id,
          'cancelled',
          `Pesanan ditolak: ${reason}`,
        );
        reportSuccess(`Pesanan #${order.order_number} ditolak`);
        setRejectModalFor(null);
        await refreshOrders();
        return true;
      } catch (e) {
        reportError(
          e,
          `Gagal tolak pesanan #${order.order_number}. Sila cuba lagi.`,
        );
        return false;
      }
    },
    [refreshOrders, reportSuccess, reportError],
  );

  const handlePickRider = useCallback((order: Order) => {
    setRidersPickerOpenFor((prev) => (prev === order.id ? null : order.id));
  }, []);

  const handleClosePicker = useCallback(() => {
    setRidersPickerOpenFor(null);
  }, []);

  /** Returns true on success so the picker can decide whether to clear its
   *  per-row spinner. On success we close the picker + toast + refetch. */
  const handleAssignRider = useCallback(
    async (orderId: string, rider: Rider): Promise<boolean> => {
      const order = orders.find((o) => o.id === orderId);
      const orderNumber = order?.order_number ?? '';
      try {
        await assignRider(orderId, rider.id);
        setRidersPickerOpenFor(null);
        reportSuccess(
          orderNumber
            ? `Rider ${rider.name} ditugaskan ke pesanan #${orderNumber}`
            : `Rider ${rider.name} ditugaskan`,
        );
        await refreshOrders();
        return true;
      } catch (e) {
        reportError(
          e,
          orderNumber
            ? `Gagal tetapkan rider untuk pesanan #${orderNumber}. Sila cuba lagi.`
            : 'Gagal tetapkan rider. Sila cuba lagi.',
        );
        return false;
      }
    },
    [orders, refreshOrders, reportSuccess, reportError],
  );

  const handleMarkCompleted = useCallback(
    async (order: Order) => {
      setCompletingId(order.id);
      try {
        await updateOrderStatus(order.id, 'completed');
        reportSuccess(`Pesanan #${order.order_number} ditandakan selesai`);
        await refreshOrders();
      } catch (e) {
        reportError(
          e,
          `Gagal kemaskini pesanan #${order.order_number}. Sila cuba lagi.`,
        );
      } finally {
        if (mountedRef.current) setCompletingId(null);
      }
    },
    [refreshOrders, reportSuccess, reportError],
  );

  const handleClosePanel = useCallback(() => setSelectedOrderId(null), []);

  // Selected order object — null when no selection or when the selected order
  // disappears from the feed (e.g. status filtered out by a tab change is OK,
  // but a deleted/missing order should drop selection so the panel doesn't
  // hang showing stale data).
  const selectedOrder = useMemo(
    () =>
      selectedOrderId
        ? orders.find((o) => o.id === selectedOrderId) ?? null
        : null,
    [orders, selectedOrderId],
  );
  const selectedRider = useMemo(
    () =>
      selectedOrder?.rider_id
        ? riderById.get(selectedOrder.rider_id) ?? null
        : null,
    [selectedOrder, riderById],
  );

  // Drop stale selection when the underlying order vanishes from refetch.
  useEffect(() => {
    if (selectedOrderId && !selectedOrder) {
      setSelectedOrderId(null);
    }
  }, [selectedOrderId, selectedOrder]);

  // Drop stale picker when the picker's order vanishes OR leaves 'confirmed'.
  useEffect(() => {
    if (!ridersPickerOpenFor) return;
    const o = orders.find((x) => x.id === ridersPickerOpenFor);
    if (!o || o.status !== 'confirmed') {
      setRidersPickerOpenFor(null);
    }
  }, [orders, ridersPickerOpenFor]);

  // ESC closes the panel.
  useEffect(() => {
    if (!selectedOrderId) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSelectedOrderId(null);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [selectedOrderId]);

  // ----- Manual refresh from buttons -----
  const handleRefresh = useCallback(async () => {
    await refreshOrders();
  }, [refreshOrders]);

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e1a] text-white">
      <DashboardHeader
        userName={userName}
        newOrdersCount={pendingCount}
        onLogout={handleLogout}
      />
      <TopBar
        websites={websites}
        selectedWebsiteId={selectedWebsiteId}
        onWebsiteChange={setSelectedWebsiteId}
        orders={orders}
        pendingCount={pendingCount}
        loading={loading}
        onRefresh={handleRefresh}
      />
      <TabBar
        tab={tab}
        onTabChange={setTab}
        orders={orders}
        lastRefresh={lastRefresh}
      />
      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        dateRange={dateRange}
        onDateRangeChange={setDateRange}
        websites={websites}
        selectedWebsiteId={selectedWebsiteId}
        onWebsiteChange={setSelectedWebsiteId}
        loading={loading}
        onRefresh={handleRefresh}
      />

      {/* Content surface — cards left, detail panel right (when an order is
          selected). Mobile-polish for the panel ships in Phase 10; for now the
          cards column hides on small viewports while the panel is open so we
          don't end up with two competing scroll surfaces. */}
      <main className="flex-1 min-h-0 flex">
        <div
          className={[
            'flex-1 min-w-0 overflow-y-auto px-4 lg:px-6 py-6',
            selectedOrder ? 'hidden md:block' : '',
          ].join(' ')}
          // Click on empty cards-area background (not bubbled from a card)
          // closes the detail panel.
          onClick={(e) => {
            if (e.target === e.currentTarget && selectedOrder) {
              handleClosePanel();
            }
          }}
        >
          <div className="max-w-4xl mx-auto">
            {loading && orders.length === 0 ? (
              <div className="flex items-center justify-center py-20">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/40" />
              </div>
            ) : filteredOrders.length === 0 ? (
              <EmptyState variant={hasAnyOrders ? 'no-match' : 'no-orders'} />
            ) : (
              <div className="space-y-2">
                {filteredOrders.map((o) => (
                  <OrderCard
                    key={o.id}
                    order={o}
                    website={websiteById.get(o.website_id) ?? null}
                    riderPhone={
                      o.rider_id ? riderById.get(o.rider_id)?.phone ?? null : null
                    }
                    selected={selectedOrderId === o.id}
                    acceptingId={acceptingId}
                    pickerOpen={ridersPickerOpenFor === o.id}
                    allRiders={riders}
                    onSelect={handleSelectOrder}
                    onAccept={handleAcceptOrder}
                    onReject={handleRejectOrder}
                    onPickRider={handlePickRider}
                    onClosePicker={handleClosePicker}
                    onAssignRider={handleAssignRider}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {selectedOrder ? (
          <OrderDetailPanel
            order={selectedOrder}
            rider={selectedRider}
            acceptingId={acceptingId}
            completingId={completingId}
            pickerOpen={ridersPickerOpenFor === selectedOrder.id}
            allRiders={riders}
            onClose={handleClosePanel}
            onAccept={handleAcceptOrder}
            onReject={handleRejectOrder}
            onPickRider={handlePickRider}
            onMarkCompleted={handleMarkCompleted}
            onClosePicker={handleClosePicker}
            onAssignRider={handleAssignRider}
          />
        ) : null}
      </main>

      {rejectModalFor ? (
        <RejectModal
          order={rejectModalFor}
          onClose={handleCloseRejectModal}
          onConfirm={handleConfirmReject}
        />
      ) : null}
    </div>
  );
}

/** Inclusive start, exclusive end. Used by the date-range filter.
 *  - today      : midnight today → +∞
 *  - yesterday  : midnight yesterday → midnight today (24h window)
 *  - 7days      : now − 7d → +∞
 *  - 30days     : now − 30d → +∞
 *  - custom     : open range (no custom picker yet — Phase 12 follow-up). */
function dateRangeBounds(
  range: DateRange,
  now: number,
): { start: number; end: number } {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  const startOfToday = d.getTime();
  const DAY = 86_400_000;
  switch (range) {
    case 'today':
      return { start: startOfToday, end: Number.POSITIVE_INFINITY };
    case 'yesterday':
      return { start: startOfToday - DAY, end: startOfToday };
    case '7days':
      return { start: now - 7 * DAY, end: Number.POSITIVE_INFINITY };
    case '30days':
      return { start: now - 30 * DAY, end: Number.POSITIVE_INFINITY };
    case 'custom':
    default:
      return {
        start: Number.NEGATIVE_INFINITY,
        end: Number.POSITIVE_INFINITY,
      };
  }
}
