'use client';

// Penghantar Live — main client wrapper.
// Desktop layout: TopBar (sticky) + 320px left column (Orders top, Riders bottom)
// + map fills the rest. Mobile bottom-sheet variant lands in a later commit.

import { useCallback, useEffect, useRef, useState } from 'react';
import { getActiveOrders, getRiders } from './lib/api';
import type { ActiveOrder, LiveRider, Outlet } from './lib/types';
import TopBar from './components/TopBar';
import OrdersPanel from './components/OrdersPanel';
import RidersPanel from './components/RidersPanel';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Mutually-exclusive selection: picking an order clears rider selection
  // and vice versa. Hover state powers the map↔panel highlight.
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedRiderId, setSelectedRiderId] = useState<string | null>(null);
  const [hoveredOrderId, setHoveredOrderId] = useState<string | null>(null);
  const [hoveredRiderId, setHoveredRiderId] = useState<string | null>(null);

  // Visibility toggles wired in commit 5 (MapControls). Defaults: zones on,
  // offline riders hidden.
  const [showOfflineRiders] = useState(false);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refetch = useCallback(async (websiteId: string) => {
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

  useEffect(() => {
    if (!selectedOutletId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    refetch(selectedOutletId);
    const id = window.setInterval(
      () => refetch(selectedOutletId),
      POLL_INTERVAL_MS,
    );
    return () => window.clearInterval(id);
  }, [selectedOutletId, refetch]);

  // Reset selection on outlet change to avoid pointing at a stale order/rider.
  useEffect(() => {
    setSelectedOrderId(null);
    setSelectedRiderId(null);
  }, [selectedOutletId]);

  const handleOrderSelect = (id: string) => {
    setSelectedOrderId((prev) => (prev === id ? null : id));
    setSelectedRiderId(null);
  };
  const handleRiderSelect = (id: string) => {
    setSelectedRiderId((prev) => (prev === id ? null : id));
    setSelectedOrderId(null);
  };

  // Stuck order set lands in commit 5 (lib/stuck.ts). Empty for now so the
  // TopBar shows "Tersangkut: 0" and OrderCard never shows the red ring.
  const stuckOrderIds: ReadonlySet<string> = new Set();

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
        {/* Left column — 320px on desktop, hidden under sm */}
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

        {/* Map area — placeholder until commit 3 lands MapView */}
        <main className="flex-1 min-w-0 relative bg-[#0a0e1a] flex items-center justify-center">
          {loading ? (
            <p className="text-white/40 text-sm font-geist">Memuatkan…</p>
          ) : error ? (
            <p className="text-red-400 text-sm font-geist">{error}</p>
          ) : (
            <p className="text-white/30 text-xs font-mono uppercase tracking-wider">
              Peta dipasang dalam commit seterusnya
              {hoveredOrderId ? ` · order ${hoveredOrderId.slice(0, 6)}` : ''}
              {hoveredRiderId ? ` · rider ${hoveredRiderId.slice(0, 6)}` : ''}
            </p>
          )}
        </main>
      </div>
    </div>
  );
}
