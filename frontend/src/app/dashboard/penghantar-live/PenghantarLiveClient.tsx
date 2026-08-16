'use client';

// Penghantar Live — main client wrapper.
// Desktop layout: TopBar (sticky) + 320px left column (Orders top, Riders bottom)
// + MapView fills the rest. Under md the aside is replaced by MobileBottomSheet.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { getCurrentUser } from '@/lib/supabase';
import DashboardHeader from '@/components/dashboard-new/DashboardHeader';
import { getActiveOrders, getRiders, getZones, setRiderPresence } from './lib/api';
import {
  loadSoundPref,
  playNewOrderChime,
  playStuckAlert,
  saveSoundPref,
} from './lib/sound';
import type { ActiveOrder, LiteZone, LiveRider, Outlet } from './lib/types';
import TopBar from './components/TopBar';
import SearchBox from './components/SearchBox';
import OrdersPanel from './components/OrdersPanel';
import RidersPanel from './components/RidersPanel';
import MapView, { type MapViewHandle } from './components/MapView';
import OrderDetailPanel from './components/OrderDetailPanel';
import RiderDetailPanel from './components/RiderDetailPanel';
import MapControls from './components/MapControls';
import MapLegend from './components/MapLegend';
import StuckBanner from './components/StuckBanner';
import ReassignModal from './components/ReassignModal';
import CancelModal from './components/CancelModal';
import { computeStuckOrderIds } from './lib/stuck';
import { subscribeToLive } from './lib/realtime';
import { useIsMobile } from './lib/useIsMobile';
import MobileBottomSheet from './components/MobileBottomSheet';

interface Props {
  outlets: Outlet[];
}

const POLL_INTERVAL_MS = 15_000;
// While realtime is up we still poll, just slower — a safety net so a new
// order can never sit unseen if a realtime event is missed or dropped.
const SAFETY_POLL_INTERVAL_MS = 60_000;
// Relative times (ETA, "GPS x min lalu") and the stuck set otherwise only
// change on a refetch; a 30s wall-clock tick keeps them honest in between.
const CLOCK_TICK_MS = 30_000;

const OUTLET_STORAGE_KEY = 'phl_selected_outlet';

export default function PenghantarLiveClient({ outlets }: Props) {
  const router = useRouter();
  const [userName, setUserName] = useState('Pengguna');
  const [selectedOutletId, setSelectedOutletId] = useState<string | null>(() => {
    // Restore the last-viewed outlet so a refresh doesn't snap back to the
    // first one. Falls back to the first outlet when the stored id is gone.
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(OUTLET_STORAGE_KEY);
        if (stored && outlets.some((o) => o.id === stored)) return stored;
      } catch {
        /* ignore */
      }
    }
    return outlets[0]?.id ?? null;
  });
  const [orders, setOrders] = useState<ActiveOrder[]>([]);
  const [riders, setRiders] = useState<LiveRider[]>([]);
  const [zones, setZones] = useState<LiteZone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Mutually-exclusive selection
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedRiderId, setSelectedRiderId] = useState<string | null>(null);
  const [hoveredOrderId, setHoveredOrderId] = useState<string | null>(null);
  const [hoveredRiderId, setHoveredRiderId] = useState<string | null>(null);

  // Visibility toggles (wired via MapControls).
  const [showZones, setShowZones] = useState(true);
  const [showOfflineRiders, setShowOfflineRiders] = useState(false);

  // Imperative handle to MapView for zoom + center buttons.
  const mapApi = useRef<MapViewHandle>(null);

  // Modal state — only one open at a time, both keyed to selectedOrder.
  const [reassignOpen, setReassignOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

  // Realtime channel up-state. When true we pause polling (Supabase pushes
  // rider updates directly); when false we fall back to setInterval.
  const [realtimeUp, setRealtimeUp] = useState(false);

  // Feed freshness + manual refresh state (surfaced in TopBar).
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Sound alerts (new order / stuck) — preference persisted per browser.
  const [soundEnabled, setSoundEnabled] = useState(false);
  useEffect(() => {
    setSoundEnabled(loadSoundPref());
  }, []);
  const toggleSound = useCallback(() => {
    setSoundEnabled((v) => {
      saveSoundPref(!v);
      return !v;
    });
  }, []);

  // Search across orders (number / customer / address) and riders (name /
  // plate / phone). Filters the list panels only — the map keeps everything.
  const [searchQuery, setSearchQuery] = useState('');

  // 30s wall-clock tick — see CLOCK_TICK_MS.
  const [nowTick, setNowTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setNowTick((t) => t + 1), CLOCK_TICK_MS);
    return () => window.clearInterval(id);
  }, []);

  // Debounce burst-rate realtime events (rider apps ping ~every 5s). Collapse
  // any cluster within 800ms into one refetch.
  const debouncedRefetchTimer = useRef<number | null>(null);

  const isMobile = useIsMobile();

  // Resolve display name for DashboardHeader once on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const user = await getCurrentUser();
        if (cancelled || !user) return;
        const u = user as {
          user_metadata?: { full_name?: string };
          email?: string;
        };
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

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Orders + riders refetch — runs on outlet change and every 15s.
  const refetchLive = useCallback(async (websiteId: string) => {
    try {
      const [o, r] = await Promise.all([
        getActiveOrders(websiteId),
        getRiders(websiteId),
      ]);
      if (!mountedRef.current) return;
      setOrders(o);
      setRiders(r);
      setError(null);
      setLastUpdatedAt(new Date());
    } catch (e) {
      if (!mountedRef.current) return;
      setError(e instanceof Error ? e.message : 'Ralat tidak diketahui');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  // Zones change rarely — fetch once per outlet, not in the poll loop.
  // TODO v2: refetch zones on owner edit signal (websocket or focus listener).
  const refetchZones = useCallback(async (websiteId: string) => {
    try {
      const z = await getZones(websiteId);
      if (mountedRef.current) setZones(z);
    } catch {
      // Zone overlay is non-critical; failing to load it shouldn't blow up
      // the page. The error toast for live data covers the broader UX.
      if (mountedRef.current) setZones([]);
    }
  }, []);

  useEffect(() => {
    if (!selectedOutletId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    refetchLive(selectedOutletId);
    refetchZones(selectedOutletId);
  }, [selectedOutletId, refetchLive, refetchZones]);

  // Realtime subscription — flips realtimeUp; debounced refetch on change.
  useEffect(() => {
    if (!selectedOutletId) return;
    const fire = () => {
      if (debouncedRefetchTimer.current) {
        window.clearTimeout(debouncedRefetchTimer.current);
      }
      debouncedRefetchTimer.current = window.setTimeout(() => {
        refetchLive(selectedOutletId);
      }, 800);
    };
    const handle = subscribeToLive(selectedOutletId, fire, (status) => {
      setRealtimeUp(status === 'subscribed');
    });
    return () => {
      handle.unsubscribe();
      if (debouncedRefetchTimer.current) {
        window.clearTimeout(debouncedRefetchTimer.current);
        debouncedRefetchTimer.current = null;
      }
      setRealtimeUp(false);
    };
  }, [selectedOutletId, refetchLive]);

  // Polling — 15s when realtime is down (primary), 60s when it's up (safety
  // net). We never fully pause: realtime events can be missed or dropped, and
  // a newly-placed order must not sit unseen waiting for the socket.
  useEffect(() => {
    if (!selectedOutletId) return;
    const interval = realtimeUp ? SAFETY_POLL_INTERVAL_MS : POLL_INTERVAL_MS;
    const id = window.setInterval(
      () => refetchLive(selectedOutletId),
      interval,
    );
    return () => window.clearInterval(id);
  }, [selectedOutletId, refetchLive, realtimeUp]);

  // Reset selection on outlet change + remember the choice.
  useEffect(() => {
    setSelectedOrderId(null);
    setSelectedRiderId(null);
    if (selectedOutletId) {
      try {
        localStorage.setItem(OUTLET_STORAGE_KEY, selectedOutletId);
      } catch {
        /* ignore */
      }
    }
  }, [selectedOutletId]);

  // Manual refresh — spins the TopBar icon while both lists reload.
  const handleManualRefresh = useCallback(async () => {
    if (!selectedOutletId || refreshing) return;
    setRefreshing(true);
    try {
      await refetchLive(selectedOutletId);
    } finally {
      if (mountedRef.current) setRefreshing(false);
    }
  }, [selectedOutletId, refreshing, refetchLive]);

  // Owner force-offline for a rider (RiderDetailPanel action).
  const handleSetRiderOffline = useCallback(
    async (riderId: string) => {
      try {
        await setRiderPresence(riderId, false);
        toast.success('Rider ditetapkan offline');
        if (selectedOutletId) await refetchLive(selectedOutletId);
      } catch (e) {
        toast.error(
          e instanceof Error ? e.message : 'Gagal menetapkan rider offline',
        );
      }
    },
    [selectedOutletId, refetchLive],
  );

  const handleOrderSelect = useCallback((id: string) => {
    setSelectedOrderId((prev) => (prev === id ? null : id));
    setSelectedRiderId(null);
  }, []);
  const handleRiderSelect = useCallback((id: string) => {
    setSelectedRiderId((prev) => (prev === id ? null : id));
    setSelectedOrderId(null);
  }, []);

  // Selected outlet as an Outlet object for MapView.
  const selectedOutlet = useMemo(
    () => outlets.find((o) => o.id === selectedOutletId) ?? null,
    [outlets, selectedOutletId],
  );

  // Resolved selection objects for the detail panels.
  const selectedOrder = useMemo(
    () => (selectedOrderId ? orders.find((o) => o.id === selectedOrderId) ?? null : null),
    [orders, selectedOrderId],
  );
  const selectedRider = useMemo(
    () => (selectedRiderId ? riders.find((r) => r.id === selectedRiderId) ?? null : null),
    [riders, selectedRiderId],
  );

  // If a selected order/rider disappears from the live feed (delivered or went
  // offline beyond stale threshold), drop the selection automatically so the
  // panel doesn't hang showing stale snapshot data.
  useEffect(() => {
    if (selectedOrderId && !selectedOrder) setSelectedOrderId(null);
  }, [selectedOrderId, selectedOrder]);
  useEffect(() => {
    if (selectedRiderId && !selectedRider) setSelectedRiderId(null);
  }, [selectedRiderId, selectedRider]);

  // Stuck order set — pure function over orders + riders. nowTick makes it
  // re-evaluate every 30s so an order crossing the threshold between polls
  // is flagged without waiting for the next refetch.
  const stuckOrderIds = useMemo(
    () => computeStuckOrderIds(orders, riders),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [orders, riders, nowTick],
  );
  // The banner should jump to the MOST overdue stuck order, not the newest.
  const firstStuckOrderId = useMemo(() => {
    if (stuckOrderIds.size === 0) return null;
    let worst: string | null = null;
    let worstEta = Infinity;
    for (const o of orders) {
      if (!stuckOrderIds.has(o.id)) continue;
      const eta = o.eta_at ? new Date(o.eta_at).getTime() : Infinity;
      if (eta < worstEta) {
        worstEta = eta;
        worst = o.id;
      }
    }
    return worst ?? stuckOrderIds.values().next().value ?? null;
  }, [stuckOrderIds, orders]);

  // ---- Sound alerts ----
  // New order chime: any order id not present in the previous snapshot.
  // Stuck alert: any id newly entering the stuck set. Both are suppressed on
  // the first load per outlet (prev === null) so opening the page is silent.
  const prevOrderIdsRef = useRef<Set<string> | null>(null);
  const prevStuckIdsRef = useRef<ReadonlySet<string> | null>(null);
  useEffect(() => {
    prevOrderIdsRef.current = null;
    prevStuckIdsRef.current = null;
  }, [selectedOutletId]);
  useEffect(() => {
    const prev = prevOrderIdsRef.current;
    const current = new Set(orders.map((o) => o.id));
    if (prev && soundEnabled) {
      let hasNew = false;
      for (const id of current) {
        if (!prev.has(id)) {
          hasNew = true;
          break;
        }
      }
      if (hasNew) playNewOrderChime();
    }
    prevOrderIdsRef.current = current;
  }, [orders, soundEnabled]);
  useEffect(() => {
    const prev = prevStuckIdsRef.current;
    if (prev && soundEnabled) {
      let hasNewStuck = false;
      for (const id of stuckOrderIds) {
        if (!prev.has(id)) {
          hasNewStuck = true;
          break;
        }
      }
      if (hasNewStuck) playStuckAlert();
    }
    prevStuckIdsRef.current = stuckOrderIds;
  }, [stuckOrderIds, soundEnabled]);

  // ---- Search filtering (list panels only; the map shows everything) ----
  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filteredOrders = useMemo(() => {
    if (!normalizedQuery) return orders;
    return orders.filter((o) =>
      [o.order_number, o.customer_name, o.delivery_address, o.rider_name ?? '']
        .join(' ')
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [orders, normalizedQuery]);
  const filteredRiders = useMemo(() => {
    if (!normalizedQuery) return riders;
    return riders.filter((r) =>
      [r.name, r.phone, r.vehicle_plate ?? '']
        .join(' ')
        .toLowerCase()
        .includes(normalizedQuery),
    );
  }, [riders, normalizedQuery]);

  if (outlets.length === 0) {
    return (
      <div className="min-h-screen flex flex-col bg-[#0a0e1a] text-white">
        <DashboardHeader userName={userName} onLogout={handleLogout} />
        <div className="flex-1 p-8">
          <h1 className="text-xl font-semibold">Tiada outlet</h1>
          <p className="mt-2 text-white/60">
            Daftarkan outlet anda dahulu sebelum menggunakan halaman ini.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#0a0e1a]">
      <DashboardHeader userName={userName} onLogout={handleLogout} />
      <TopBar
        outlets={outlets}
        selectedOutletId={selectedOutletId}
        onOutletChange={setSelectedOutletId}
        orders={orders}
        riders={riders}
        stuckCount={stuckOrderIds.size}
        realtimeUp={realtimeUp}
        lastUpdatedAt={lastUpdatedAt}
        refreshing={refreshing}
        onRefresh={handleManualRefresh}
        soundEnabled={soundEnabled}
        onToggleSound={toggleSound}
      />

      <div className="flex-1 min-h-0 flex">
        {/* Desktop left column — 320px; replaced by MobileBottomSheet under md. */}
        <aside className="hidden md:flex w-[320px] shrink-0 flex-col border-r border-white/[0.06]">
          <SearchBox value={searchQuery} onChange={setSearchQuery} />
          <div className="flex-1 min-h-0">
            <OrdersPanel
              orders={filteredOrders}
              totalCount={orders.length}
              selectedId={selectedOrderId}
              stuckOrderIds={stuckOrderIds}
              onSelect={handleOrderSelect}
              onHover={setHoveredOrderId}
            />
          </div>
          <div className="flex-1 min-h-0">
            <RidersPanel
              riders={filteredRiders}
              totalCount={riders.length}
              selectedId={selectedRiderId}
              showOffline={showOfflineRiders}
              onSelect={handleRiderSelect}
              onHover={setHoveredRiderId}
            />
          </div>
        </aside>

        <main className="flex-1 min-w-0 relative bg-[#0a0e1a]">
          <MapView
            ref={mapApi}
            outlet={selectedOutlet}
            orders={orders}
            riders={riders}
            zones={zones}
            showZones={showZones}
            showOfflineRiders={showOfflineRiders}
            stuckOrderIds={stuckOrderIds}
            selectedOrderId={selectedOrderId}
            selectedRiderId={selectedRiderId}
            hoveredOrderId={hoveredOrderId}
            hoveredRiderId={hoveredRiderId}
            onOrderSelect={handleOrderSelect}
            onRiderSelect={handleRiderSelect}
          />

          <StuckBanner
            count={stuckOrderIds.size}
            firstStuckOrderId={firstStuckOrderId}
            onSelectStuck={handleOrderSelect}
          />

          <MapLegend />

          <MapControls
            showZones={showZones}
            showOfflineRiders={showOfflineRiders}
            onZoomIn={() => mapApi.current?.zoomIn()}
            onZoomOut={() => mapApi.current?.zoomOut()}
            onCenterOnOutlet={() => mapApi.current?.centerOnOutlet()}
            onToggleZones={() => setShowZones((v) => !v)}
            onToggleOfflineRiders={() => setShowOfflineRiders((v) => !v)}
          />

          {/* Non-blocking status overlays */}
          {loading && (
            <div className="absolute top-3 left-3 z-[1000] px-3 py-1.5 rounded-lg bg-[#0a0e1a]/90 border border-white/[0.08] text-xs font-mono text-white/60">
              Memuatkan…
            </div>
          )}
          {error && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] px-3 py-1.5 rounded-lg bg-red-400/10 border border-red-400/30 text-xs font-geist text-red-300">
              {error}
            </div>
          )}
        </main>

        {/* Right detail panel — slides in when an order or rider is selected. */}
        {selectedOrder && (
          <OrderDetailPanel
            order={selectedOrder}
            variant={isMobile ? 'mobile' : 'desktop'}
            onClose={() => setSelectedOrderId(null)}
            onReassignClick={() => setReassignOpen(true)}
            onCancelClick={() => setCancelOpen(true)}
          />
        )}
        {selectedRider && !selectedOrder && (
          <RiderDetailPanel
            rider={selectedRider}
            variant={isMobile ? 'mobile' : 'desktop'}
            onClose={() => setSelectedRiderId(null)}
            onActiveOrderClick={(orderId) => handleOrderSelect(orderId)}
            onSetOffline={handleSetRiderOffline}
          />
        )}
      </div>

      {/* Mobile-only bottom sheet — hidden when a detail modal is open so it
          doesn't poke through under the full-screen panel. */}
      {isMobile && !selectedOrder && !selectedRider && (
        <MobileBottomSheet
          orders={orders}
          riders={riders}
          selectedOrderId={selectedOrderId}
          selectedRiderId={selectedRiderId}
          stuckOrderIds={stuckOrderIds}
          showOffline={showOfflineRiders}
          onSelectOrder={handleOrderSelect}
          onSelectRider={handleRiderSelect}
        />
      )}

      {selectedOrder && reassignOpen && (
        <ReassignModal
          order={selectedOrder}
          riders={riders}
          onClose={() => setReassignOpen(false)}
          onSuccess={() => {
            setReassignOpen(false);
            if (selectedOutletId) refetchLive(selectedOutletId);
          }}
        />
      )}
      {selectedOrder && cancelOpen && (
        <CancelModal
          order={selectedOrder}
          onClose={() => setCancelOpen(false)}
          onSuccess={() => {
            setCancelOpen(false);
            setSelectedOrderId(null); // order leaves the active list
            if (selectedOutletId) refetchLive(selectedOutletId);
          }}
        />
      )}
    </div>
  );
}
