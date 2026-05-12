'use client';

// Penghantar Live — main client wrapper.
// Scaffold only: fetches orders + riders for the selected outlet on mount and
// every 15 seconds. UI subcomponents (TopBar, OrdersPanel, MapView, etc.)
// land in subsequent commits per the phase plan.

import { useCallback, useEffect, useRef, useState } from 'react';
import { getActiveOrders, getRiders } from './lib/api';
import type { ActiveOrder, LiveRider, Outlet } from './lib/types';

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

  // Scaffold view — UI lands in next commits.
  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white p-8">
      <h1 className="text-xl font-semibold">Penghantar Live</h1>
      <p className="mt-2 text-white/60 text-sm">
        Outlet:{' '}
        <select
          className="bg-white/10 rounded px-2 py-1 text-white"
          value={selectedOutletId ?? ''}
          onChange={(e) => setSelectedOutletId(e.target.value)}
        >
          {outlets.map((o) => (
            <option key={o.id} value={o.id} className="bg-[#0a0e1a]">
              {o.name}
            </option>
          ))}
        </select>
      </p>
      {loading ? (
        <p className="mt-4 text-white/40 text-sm">Memuatkan…</p>
      ) : error ? (
        <p className="mt-4 text-red-400 text-sm">{error}</p>
      ) : (
        <p className="mt-4 text-white/40 text-sm">
          {orders.length} pesanan aktif · {riders.length} rider
        </p>
      )}
    </div>
  );
}
