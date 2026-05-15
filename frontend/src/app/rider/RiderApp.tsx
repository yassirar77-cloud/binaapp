'use client';

// /rider — main state container.
//
// Owns: route, tab, active order, fetched orders, online flag, rider.
// Children read from props; status mutations + API calls happen here so the
// state machine stays in one file. Mirrors the pattern used by
// /chat/ChatClient.tsx and /pesanan/PesananClient.tsx.

import { useEffect, useState } from 'react';

import LoginScreen from './components/LoginScreen';
import { loadRider, saveRider, saveRiderPhone } from './lib/storage';
import { useIsOnline } from './lib/useIsOnline';
import type { Rider, RiderOrder, Route, Tab } from './lib/types';

import './rider.css';

export default function RiderApp() {
  const [route, setRoute] = useState<Route>('login');
  const [rider, setRider] = useState<Rider | null>(null);
  // Tab / active order / orders / newOrder / loading are wired into the
  // shell here but only read by the Phase-6+ screens; keep them in this
  // file so the state machine has one home.
  const [tab, setTab] = useState<Tab>('aktif');
  const [activeOrderId, setActiveOrderId] = useState<string | null>(null);
  const [orders, setOrders] = useState<RiderOrder[]>([]);
  const [newOrder, setNewOrder] = useState<RiderOrder | null>(null);
  const [loading, setLoading] = useState(false);
  const online = useIsOnline();

  // Hydrate rider session from localStorage on mount. Routes straight to
  // the orders screen if we already have a rider record; otherwise show
  // the login form.
  useEffect(() => {
    const saved = loadRider();
    if (saved) {
      setRider(saved);
      setRoute('orders');
    } else {
      setRoute('login');
    }
  }, []);

  const handleLoginSuccess = (
    loggedIn: Rider,
    rememberPhone: string | null,
  ) => {
    saveRider(loggedIn);
    if (rememberPhone) saveRiderPhone(rememberPhone);
    setRider(loggedIn);
    setRoute('orders');
  };

  return (
    <div className="rider-app">
      {route === 'login' && <LoginScreen onLogin={handleLoginSuccess} />}
      {route !== 'login' && rider && (
        <div className="px-5 py-8 text-[var(--rider-text-2)] rider-fade-in">
          <p className="text-sm">
            Selamat datang,{' '}
            <span className="text-white font-semibold">{rider.name}</span>.
          </p>
          <p className="mt-2 text-xs">
            Skrin pesanan akan dipasang dalam Phase 6. Status:{' '}
            <span className="text-[var(--rider-lime)]">
              {online ? 'Online' : 'Offline'}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
