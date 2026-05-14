// /rider — localStorage helpers.
// CRITICAL: the key names below are a PWA contract. Riders already have these
// set on installed devices — renaming them logs everyone out. Do not change
// 'rider_data', 'rider_phone', or 'rider_cached_orders'.

import type { Rider, RiderOrder } from './types';

const KEY_RIDER_DATA = 'rider_data';
const KEY_RIDER_PHONE = 'rider_phone';
const KEY_CACHED_ORDERS = 'rider_cached_orders';

// Guards against SSR (Next.js renders this module on the server too).
function hasWindow(): boolean {
  return typeof window !== 'undefined';
}

export function loadRider(): Rider | null {
  if (!hasWindow()) return null;
  const raw = localStorage.getItem(KEY_RIDER_DATA);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Rider;
  } catch {
    localStorage.removeItem(KEY_RIDER_DATA);
    return null;
  }
}

export function saveRider(rider: Rider): void {
  if (!hasWindow()) return;
  localStorage.setItem(KEY_RIDER_DATA, JSON.stringify(rider));
}

export function clearRider(): void {
  if (!hasWindow()) return;
  localStorage.removeItem(KEY_RIDER_DATA);
  localStorage.removeItem(KEY_CACHED_ORDERS);
}

export function loadRiderPhone(): string | null {
  if (!hasWindow()) return null;
  return localStorage.getItem(KEY_RIDER_PHONE);
}

export function saveRiderPhone(phone: string): void {
  if (!hasWindow()) return;
  localStorage.setItem(KEY_RIDER_PHONE, phone);
}

export function clearRiderPhone(): void {
  if (!hasWindow()) return;
  localStorage.removeItem(KEY_RIDER_PHONE);
}

export function loadCachedOrders(): RiderOrder[] | null {
  if (!hasWindow()) return null;
  const raw = localStorage.getItem(KEY_CACHED_ORDERS);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as RiderOrder[];
  } catch {
    localStorage.removeItem(KEY_CACHED_ORDERS);
    return null;
  }
}

export function saveCachedOrders(orders: RiderOrder[]): void {
  if (!hasWindow()) return;
  localStorage.setItem(KEY_CACHED_ORDERS, JSON.stringify(orders));
}
