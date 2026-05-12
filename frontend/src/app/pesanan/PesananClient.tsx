'use client';

// /pesanan — main client wrapper.
// Mirrors penghantar-live's pattern: own the data + filter state, render the
// chrome (TopBar / TabBar / FilterBar) and a content surface that the order
// cards + detail panel will plug into in Phase 5+.
//
// For this scaffold commit the content surface is a placeholder; cards and
// detail panel land in subsequent phases.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { getOrders, getRidersForWebsites, getWebsites } from './lib/api';
import type {
  DateRange,
  Order,
  Rider,
  TabKey,
  Website,
} from './lib/types';
import { POLL_INTERVAL_MS } from './lib/constants';
import TopBar from './components/TopBar';
import TabBar from './components/TabBar';
import FilterBar from './components/FilterBar';

export default function PesananClient() {
  // ----- Data -----
  const [orders, setOrders] = useState<Order[]>([]);
  const [websites, setWebsites] = useState<Website[]>([]);
  // Riders are fetched but not consumed by the chrome; the picker will read
  // from this state in Phase 7.
  const [, setRiders] = useState<Rider[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  // ----- Filter state -----
  const [selectedWebsiteId, setSelectedWebsiteId] = useState<string | 'all'>('all');
  const [tab, setTab] = useState<TabKey>('semua');
  const [searchQuery, setSearchQuery] = useState('');
  const [dateRange, setDateRange] = useState<DateRange>('today');

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

  // ----- Derived counts (shared across chrome) -----

  const pendingCount = useMemo(
    () => orders.filter((o) => o.status === 'pending').length,
    [orders],
  );

  // ----- Manual refresh from buttons -----
  const handleRefresh = useCallback(async () => {
    await refreshOrders();
  }, [refreshOrders]);

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e1a] text-white">
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

      {/* Content surface — cards + detail panel arrive in Phase 5+. */}
      <main className="flex-1 min-h-0 px-4 lg:px-6 py-6">
        {loading && orders.length === 0 ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/40" />
          </div>
        ) : (
          <div className="max-w-4xl mx-auto text-center py-20 text-white/40 font-mono text-xs tracking-wide">
            <p>Senarai pesanan akan dipaparkan di sini (Fasa 5).</p>
            <p className="mt-2 text-white/30">
              {orders.length} pesanan dimuatkan · {websites.length} outlet
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
