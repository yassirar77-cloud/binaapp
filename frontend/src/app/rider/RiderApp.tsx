'use client';

// /rider — main state container.
//
// Owns: route, tab, active order, fetched orders, online flag, rider.
// Children read from props; status mutations + API calls happen here so the
// state machine stays in one file. Mirrors the pattern used by
// /chat/ChatClient.tsx and /pesanan/PesananClient.tsx.

import { useCallback, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';

import BottomNav from './components/BottomNav';
import LoginScreen from './components/LoginScreen';
import OrderDetailScreen from './components/OrderDetailScreen';
import OrdersListScreen from './components/OrdersListScreen';
import {
  ApiError,
  fetchRiderOrders,
  updateOrderStatus as apiUpdateStatus,
} from './lib/api';
import { FETCH_INTERVAL_MS } from './lib/constants';
import {
  clearRider,
  loadCachedOrders,
  loadRider,
  saveCachedOrders,
  saveRider,
  saveRiderPhone,
} from './lib/storage';
import { useIsOnline } from './lib/useIsOnline';
import type {
  GpsStatus,
  OrderStatus,
  Rider,
  RiderOrder,
  Route,
  Tab,
} from './lib/types';

import './rider.css';

// Mock data for the ?demo=1 preview URL. Three orders covering the three
// action states so the row CTA can be reviewed without seeded backend
// data.
function buildDemoOrders(): RiderOrder[] {
  const now = Date.now();
  const iso = (msAgo: number) => new Date(now - msAgo).toISOString();
  return [
    {
      id: 'demo-1',
      order_number: 'D-1024',
      customer_name: 'Aiman Hakim',
      customer_phone: '0123456789',
      delivery_address: 'No 12, Jalan SS 2/24, Petaling Jaya, Selangor',
      delivery_notes: 'Rumah pagar putih, sebelah kedai runcit.',
      delivery_latitude: 3.1156,
      delivery_longitude: 101.6231,
      status: 'ready',
      payment_method: 'cod',
      total: '38.50',
      subtotal: '32.00',
      delivery_fee: '6.50',
      distance_km: '2.3',
      eta_minutes: 8,
      created_at: iso(2 * 60_000),
      items: [
        { qty: 2, name: 'Nasi Lemak Special',  price: '12.00' },
        { qty: 1, name: 'Teh Tarik Ais',        price: '4.00' },
        { qty: 1, name: 'Roti Canai (Sapingen)', price: '4.00' },
      ],
    },
    {
      id: 'demo-2',
      order_number: 'D-1023',
      customer_name: 'Nurul Aina',
      customer_phone: '0198765432',
      delivery_address: 'Apartment Damai, Block B-12-3, Ampang',
      delivery_latitude: 3.1478,
      delivery_longitude: 101.7616,
      status: 'picked_up',
      payment_method: 'online',
      total: '64.20',
      subtotal: '58.20',
      delivery_fee: '6.00',
      distance_km: '4.1',
      eta_minutes: 14,
      created_at: iso(8 * 60_000),
      picked_up_at: iso(1 * 60_000),
      items: [
        { qty: 1, name: 'Burger Set Beef',  price: '24.20' },
        { qty: 1, name: 'Burger Set Chicken', price: '22.00' },
        { qty: 2, name: 'Sprite (Can)',     price: '6.00' },
      ],
    },
    {
      id: 'demo-3',
      order_number: 'D-1022',
      customer_name: 'Lim Wei Ming',
      customer_phone: '0167778888',
      delivery_address: 'No 5, Lorong Mawar 3, Taman Bunga Raya, Kajang',
      delivery_notes: 'Tolong ketuk pintu, loceng rosak.',
      delivery_latitude: 2.9931,
      delivery_longitude: 101.7872,
      status: 'delivering',
      payment_method: 'cod',
      total: '52.00',
      subtotal: '46.00',
      delivery_fee: '6.00',
      distance_km: '5.6',
      eta_minutes: 18,
      created_at: iso(22 * 60_000),
      picked_up_at: iso(15 * 60_000),
      items: [
        { qty: 1, name: 'Pizza Pepperoni Large', price: '38.00' },
        { qty: 1, name: 'Garlic Bread',           price: '8.00' },
      ],
    },
  ];
}

export default function RiderApp() {
  const [route, setRoute] = useState<Route>('login');
  const [rider, setRider] = useState<Rider | null>(null);
  const [tab, setTab] = useState<Tab>('aktif');
  const [activeOrderId, setActiveOrderId] = useState<string | null>(null);
  const [orders, setOrders] = useState<RiderOrder[]>([]);
  const [newOrder, setNewOrder] = useState<RiderOrder | null>(null);
  const [pendingOrderId, setPendingOrderId] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const online = useIsOnline();

  // GPS state is filled by Phase 10 (useGeolocation). For now show the
  // header dot as "inactive" — the layout is already wired.
  const [gpsStatus] = useState<GpsStatus>('inactive');
  const [lastGpsUpdate] = useState<Date | null>(null);

  // Ref to the latest rider so the polling interval avoids re-binding on
  // every render.
  const riderRef = useRef<Rider | null>(null);
  useEffect(() => {
    riderRef.current = rider;
  }, [rider]);

  // Hydrate rider session + cached orders from localStorage on mount.
  // Also flip into demo mode if the URL has ?demo=1 so reviewers can
  // see the list without a real account.
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('demo') === '1') {
        setDemoMode(true);
        setOrders(buildDemoOrders());
        setRider({
          id: 'demo-rider',
          name: 'Demo Penghantar',
          phone: '0123456789',
          vehicle_type: 'motorcycle',
          vehicle_plate: 'ABC 1234',
        });
        setRoute('orders');
        return;
      }
    }

    const saved = loadRider();
    if (saved) {
      setRider(saved);
      setRoute('orders');
      const cached = loadCachedOrders();
      if (cached?.length) setOrders(cached);
    } else {
      setRoute('login');
    }
  }, []);

  // Fetch + 30s poll while logged in. Demo mode skips the network entirely.
  const refreshOrders = useCallback(
    async (silent: boolean): Promise<void> => {
      const r = riderRef.current;
      if (!r || demoMode) return;
      if (!silent) setRefreshing(true);
      try {
        const list = await fetchRiderOrders(r.id);
        setOrders(list);
        saveCachedOrders(list);
      } catch (e) {
        // Keep cached orders on network failure — the offline banner is
        // surfaced by useIsOnline at the screen level.
        if (e instanceof ApiError && e.status !== 0 && !silent) {
          toast.error(e.message || 'Gagal muat pesanan.');
        }
      } finally {
        if (!silent) setRefreshing(false);
      }
    },
    [demoMode],
  );

  useEffect(() => {
    if (route === 'login' || !rider) return;
    void refreshOrders(true);
    const id = setInterval(() => void refreshOrders(true), FETCH_INTERVAL_MS);
    return () => clearInterval(id);
  }, [route, rider, refreshOrders]);

  const handleLoginSuccess = (
    loggedIn: Rider,
    rememberPhone: string | null,
  ) => {
    saveRider(loggedIn);
    if (rememberPhone) saveRiderPhone(rememberPhone);
    setRider(loggedIn);
    setRoute('orders');
  };

  // Core advance: optimistic flip, network call, rollback + toast on
  // failure. paymentReceived is opt-in (only set on COD `delivered`
  // transitions, threaded through from CODModal once Phase 8 lands).
  const advanceStatus = useCallback(
    async (
      order: RiderOrder,
      next: OrderStatus,
      paymentReceived?: boolean | null,
    ) => {
      const prev = order.status;
      setPendingOrderId(order.id);
      setOrders((list) =>
        list.map((o) =>
          o.id === order.id
            ? {
                ...o,
                status: next,
                ...(paymentReceived !== undefined
                  ? { payment_received: paymentReceived }
                  : {}),
              }
            : o,
        ),
      );

      if (demoMode) {
        setTimeout(() => setPendingOrderId(null), 250);
        toast.success(`Pesanan #${order.order_number} dikemas kini.`);
        return;
      }

      const r = riderRef.current;
      if (!r) return;
      try {
        await apiUpdateStatus(r.id, order.id, next, {
          payment_received:
            paymentReceived === undefined ? null : paymentReceived,
        });
        toast.success(`Pesanan #${order.order_number} dikemas kini.`);
        void refreshOrders(true);
      } catch (e) {
        setOrders((list) =>
          list.map((o) => (o.id === order.id ? { ...o, status: prev } : o)),
        );
        const msg =
          e instanceof ApiError ? e.message : 'Gagal kemas kini status.';
        toast.error(msg);
      } finally {
        setPendingOrderId(null);
      }
    },
    [demoMode, refreshOrders],
  );

  // Wrapper called by row pills and the detail-screen CTA. For COD
  // orders on the `delivering → delivered` step we'll route through the
  // CODModal in Phase 8; for now we surface a clear toast and complete
  // the transition so riders can still ship. The intercept hook is
  // marked below — Phase 8 only needs to open the modal here and call
  // advanceStatus(order, 'delivered', received) from the modal.
  const handleAdvance = useCallback(
    (order: RiderOrder, next: OrderStatus) => {
      if (
        next === 'delivered' &&
        order.status === 'delivering' &&
        order.payment_method === 'cod'
      ) {
        // TODO(phase-8): replace this with `setCodModalOrder(order)` and
        // let the modal confirm + call advanceStatus(order, 'delivered',
        // <bool>) on submit.
        toast('Pengesahan tunai akan dipasang dalam Phase 8.', { icon: '💵' });
      }
      void advanceStatus(order, next);
    },
    [advanceStatus],
  );

  const handleOpen = useCallback((order: RiderOrder) => {
    setActiveOrderId(order.id);
    setRoute('detail');
  }, []);

  const handleAcceptNew = (order: RiderOrder) => {
    // Wired in a followup PR. For now drop the banner and surface a toast.
    setNewOrder(null);
    toast.success(`Pesanan #${order.order_number} diterima.`);
  };

  const handleRejectNew = (order: RiderOrder) => {
    setNewOrder(null);
    toast(`Pesanan #${order.order_number} ditolak.`);
  };

  const handleLogout = useCallback(() => {
    clearRider();
    setRider(null);
    setOrders([]);
    setNewOrder(null);
    setActiveOrderId(null);
    setRoute('login');
  }, []);

  const navTab: 'orders' | 'profile' =
    route === 'profile' ? 'profile' : 'orders';

  // Resolve the active order from id on every render so optimistic
  // status mutations (which rewrite the orders array) propagate into
  // the detail screen without stale prop snapshots.
  const activeOrder = activeOrderId
    ? orders.find((o) => o.id === activeOrderId) ?? null
    : null;

  // If the rider returns to detail after the order vanished (eg. server
  // refetch dropped it), bounce back to the list rather than render an
  // empty screen.
  useEffect(() => {
    if (route === 'detail' && !activeOrder) setRoute('orders');
  }, [route, activeOrder]);

  return (
    <div className="rider-app">
      {!online && route !== 'login' && (
        <div className="px-4 py-2 bg-[var(--rider-amber)]/15 border-b border-[var(--rider-amber)]/30 text-[12px] text-[var(--rider-amber)] text-center">
          Mod luar talian — paparan dari cache.
        </div>
      )}

      {route === 'login' && <LoginScreen onLogin={handleLoginSuccess} />}

      {route === 'orders' && rider && (
        <OrdersListScreen
          rider={rider}
          orders={orders}
          newOrder={newOrder}
          tab={tab}
          pendingOrderId={pendingOrderId}
          refreshing={refreshing}
          gpsStatus={gpsStatus}
          lastGpsUpdate={lastGpsUpdate}
          onTab={setTab}
          onRefresh={() => void refreshOrders(false)}
          onOpen={handleOpen}
          onAdvance={handleAdvance}
          onAcceptNew={handleAcceptNew}
          onRejectNew={handleRejectNew}
        />
      )}

      {route === 'detail' && rider && activeOrder && (
        <OrderDetailScreen
          order={activeOrder}
          pending={pendingOrderId === activeOrder.id}
          riderLocation={null}
          onBack={() => setRoute('orders')}
          onAdvance={handleAdvance}
        />
      )}

      {route === 'profile' && rider && (
        <div className="min-h-[100dvh] pb-20 px-5 py-8 text-[var(--rider-text-2)] rider-fade-in">
          <p className="text-sm">
            Skrin profil akan dipasang dalam Phase 9.
          </p>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-6 h-11 px-4 rounded-xl bg-[var(--rider-surface)] border border-[var(--rider-border)] text-[var(--rider-red)] text-sm"
          >
            Log Keluar
          </button>
        </div>
      )}

      {rider && (route === 'orders' || route === 'profile') && (
        <BottomNav
          active={navTab}
          onSelect={(t) => setRoute(t === 'profile' ? 'profile' : 'orders')}
        />
      )}
    </div>
  );
}
