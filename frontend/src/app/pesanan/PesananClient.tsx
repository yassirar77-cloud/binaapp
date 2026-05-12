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

  // ----- Refresh logic -----

  const refreshOrders = useCallback(async (): Promise<Order[] | null> => {
    try {
      const o = await getOrders();
      if (!mountedRef.current) return null;
      setOrders(o);
      setLastRefresh(new Date());
      return o;
    } catch (e) {
      if (!mountedRef.current) return null;
      toast.error(
        e instanceof Error && e.message
          ? e.message
          : 'Gagal hubungi backend. Sila refresh halaman.',
      );
      return null;
    }
  }, []);

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
        toast.error(
          e instanceof Error && e.message
            ? e.message
            : 'Gagal hubungi backend. Sila refresh halaman.',
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Polling — 30s after the initial load completes.
  useEffect(() => {
    const id = window.setInterval(() => {
      void refreshOrders();
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
        toast.success(`Pesanan #${order.order_number} diterima`);
        await refreshOrders();
      } catch (e) {
        toast.error(
          e instanceof Error && e.message
            ? e.message
            : 'Gagal kemaskini status. Sila cuba lagi.',
        );
      } finally {
        if (mountedRef.current) setAcceptingId(null);
      }
    },
    [refreshOrders],
  );

  const handleRejectOrder = useCallback((order: Order) => {
    // TODO(Phase 8): open RejectModal with reason textarea + validation.
    console.log('[Pesanan] TODO: open RejectModal (Phase 8)', order.id);
  }, []);

  const handlePickRider = useCallback((order: Order) => {
    // TODO(Phase 7): open RiderPickerDropdown anchored to this button.
    console.log('[Pesanan] TODO: open RiderPickerDropdown (Phase 7)', order.id);
  }, []);

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

      {/* Content surface — order cards. Detail panel arrives in Phase 6. */}
      <main className="flex-1 min-h-0 px-4 lg:px-6 py-6">
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
                  onSelect={handleSelectOrder}
                  onAccept={handleAcceptOrder}
                  onReject={handleRejectOrder}
                  onPickRider={handlePickRider}
                />
              ))}
            </div>
          )}
        </div>
      </main>
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
