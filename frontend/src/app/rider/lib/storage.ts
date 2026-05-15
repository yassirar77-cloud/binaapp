// /rider — localStorage helpers.
// CRITICAL: the key names below are a PWA contract. Riders already have these
// set on installed devices — renaming them logs everyone out. Do not change
// 'rider_data', 'rider_phone', or 'rider_cached_orders'.

import type { Rider, RiderOrder } from './types';

const KEY_RIDER_DATA = 'rider_data';
const KEY_RIDER_PHONE = 'rider_phone';
const KEY_CACHED_ORDERS = 'rider_cached_orders';

// Phase-9 additions. Local-only flags surfaced through the profile
// screen. Prefixed with `rider_pref_` to avoid colliding with other
// `rider_*` keys that are part of the PWA contract.
const KEY_PREF_ONLINE = 'rider_pref_online';
const KEY_PREF_SOUND = 'rider_pref_sound';
const KEY_PREF_BATTERY_SAVER = 'rider_pref_battery_saver';

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

// Boolean preferences with explicit defaults. Each helper falls back to
// the default when localStorage is missing or unparseable so the UI
// never sees `undefined`.

function loadBool(key: string, fallback: boolean): boolean {
  if (!hasWindow()) return fallback;
  const raw = localStorage.getItem(key);
  if (raw === null) return fallback;
  return raw === '1' || raw === 'true';
}

function saveBool(key: string, value: boolean): void {
  if (!hasWindow()) return;
  localStorage.setItem(key, value ? '1' : '0');
}

export const loadOnlinePref = () => loadBool(KEY_PREF_ONLINE, true);
export const saveOnlinePref = (v: boolean) => saveBool(KEY_PREF_ONLINE, v);

export const loadSoundPref = () => loadBool(KEY_PREF_SOUND, true);
export const saveSoundPref = (v: boolean) => saveBool(KEY_PREF_SOUND, v);

export const loadBatterySaverPref = () =>
  loadBool(KEY_PREF_BATTERY_SAVER, false);
export const saveBatterySaverPref = (v: boolean) =>
  saveBool(KEY_PREF_BATTERY_SAVER, v);

// Tracks whether we've shown the Phase-10 notification permission
// prompt at least once. The decision (granted vs dismissed) is owned
// by the browser's Notification.permission state, not this flag — we
// just don't want to re-prompt every login.
const KEY_NOTIFICATIONS_ASKED = 'rider_notifications_asked';
export const wasNotificationAsked = () =>
  loadBool(KEY_NOTIFICATIONS_ASKED, false);
export const markNotificationAsked = () =>
  saveBool(KEY_NOTIFICATIONS_ASKED, true);
