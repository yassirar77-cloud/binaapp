'use client';

// Penghantar Live — main client wrapper.
// Desktop layout: TopBar (sticky) + 320px left column (Orders top, Riders bottom)
// + MapView fills the rest. Mobile bottom-sheet variant lands in a later commit.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getActiveOrders, getRiders, getZones } from './lib/api';
import type { ActiveOrder, LiteZone, LiveRider, Outlet } from './lib/types';
import TopBar from './components/TopBar';
import OrdersPanel from './components/OrdersPanel';
import RidersPanel from './components/RidersPanel';
import MapView, { type MapViewHandle } from './components/MapView';
import OrderDetailPanel from './components/OrderDetailPanel';
import RiderDetailPanel from './components/RiderDetailPanel';
import MapControls from './components/MapControls';
import MapLegend from './components/MapLegend';
import StuckBanner from './components/StuckBanner';
import { computeStuckOrderIds } from './lib/stuck';

interface Props {
  outlets: Outlet[];
}

const POLL_INTERVAL_MS = 15_000;

export default function PenghantarLiveClient({ outlets }: Props) {
  const [selectedOutletId, setSelectedOutletId] = useState<string | null>(
    outlets[0]?.id ?? null,
  );
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
    const id = window.setInterval(
      () => refetchLive(selectedOutletId),
      POLL_INTERVAL_MS,
    );
    return () => window.clearInterval(id);
  }, [selectedOutletId, refetchLive, refetchZones]);

  // Reset selection on outlet change.
  useEffect(() => {
    setSelectedOrderId(null);
    setSelectedRiderId(null);
  }, [selectedOutletId]);

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

  // Stuck order set — recomputed each render so it reacts to time passing
  // on the next poll/realtime tick. (Pure function over orders + riders.)
  const stuckOrderIds = useMemo(
    () => computeStuckOrderIds(orders, riders),
    [orders, riders],
  );
  const firstStuckOrderId = useMemo(
    () => (stuckOrderIds.size > 0 ? stuckOrderIds.values().next().value ?? null : null),
    [stuckOrderIds],
  );

  if (outlets.length === 0) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] text-white p-8">
        <h1 className="text-xl font-semibold">Tiada outlet</h1>
        <p className="mt-2 text-white/60">
          Daftarkan outlet anda dahulu sebelum menggunakan halaman ini.
        </p>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#0a0e1a]">
      <TopBar
        outlets={outlets}
        selectedOutletId={selectedOutletId}
        onOutletChange={setSelectedOutletId}
        orders={orders}
        riders={riders}
        stuckCount={stuckOrderIds.size}
      />

      <div className="flex-1 min-h-0 flex">
        {/* Left column — 320px on desktop, hidden under md (mobile UI in commit 8) */}
        <aside className="hidden md:flex w-[320px] shrink-0 flex-col border-r border-white/[0.06]">
          <div className="flex-1 min-h-0">
            <OrdersPanel
              orders={orders}
              selectedId={selectedOrderId}
              stuckOrderIds={stuckOrderIds}
              onSelect={handleOrderSelect}
              onHover={setHoveredOrderId}
            />
          </div>
          <div className="flex-1 min-h-0">
            <RidersPanel
              riders={riders}
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

        {/* Right detail panel — slides in when an order or rider is selected.
            Modal openings are wired in commit 6; placeholders for now. */}
        {selectedOrder && (
          <OrderDetailPanel
            order={selectedOrder}
            onClose={() => setSelectedOrderId(null)}
            onReassignClick={() => {
              /* TODO: open ReassignModal — wired in commit 6 */
            }}
            onCancelClick={() => {
              /* TODO: open CancelModal — wired in commit 6 */
            }}
          />
        )}
        {selectedRider && !selectedOrder && (
          <RiderDetailPanel
            rider={selectedRider}
            onClose={() => setSelectedRiderId(null)}
            onActiveOrderClick={(orderId) => handleOrderSelect(orderId)}
          />
        )}
      </div>
    </div>
  );
}
