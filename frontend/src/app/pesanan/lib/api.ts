// /pesanan — API client.
// Mirrors the auth + authFetch pattern from
// /dashboard/penghantar-live/lib/api.ts: backend token first
// (ensureValidToken handles refresh), Supabase session as fallback. Surfaces
// Malay error text from the API `detail` field when present.

import { supabase, ensureValidToken } from '@/lib/supabase';
import type { Order, OrderStatus, Rider, Website } from './types';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

async function getToken(): Promise<string> {
  const validToken = await ensureValidToken();
  if (validToken) return validToken;
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) return data.session.access_token;
  }
  throw new Error('Tidak log masuk');
}

async function authFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(opts.headers || {}),
    },
  });

  if (res.status === 204) {
    return null as unknown as T;
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }

  return (await res.json()) as T;
}

// ----- Public API -----

interface OrdersMyResponse {
  orders: Order[];
  total: number;
  limit: number;
  offset: number;
}

/** GET /api/v1/delivery/orders/my returns `{orders, total, limit, offset}`;
 *  we unwrap to `Order[]` so callers don't have to. */
export async function getOrders(): Promise<Order[]> {
  const res = await authFetch<OrdersMyResponse>('/api/v1/delivery/orders/my');
  return res?.orders ?? [];
}

/** GET /api/v1/websites/ returns an array with `business_name`; we normalize
 *  by populating `.name` so the UI can read a single field. */
export async function getWebsites(): Promise<Website[]> {
  const raw = await authFetch<Array<Website & { business_name?: string }>>(
    '/api/v1/websites/',
  );
  return (raw ?? []).map((w) => ({
    ...w,
    name: w.name ?? w.business_name,
  }));
}

export function getRiders(websiteId: string): Promise<Rider[]> {
  return authFetch<Rider[]>(
    `/api/v1/delivery/admin/websites/${websiteId}/riders`,
  );
}

/** Fetch riders across multiple outlets, dedup by id. Sequential to keep the
 *  load light on small fleets; switch to Promise.all if outlet count grows. */
export async function getRidersForWebsites(
  websiteIds: string[],
): Promise<Rider[]> {
  const seen = new Set<string>();
  const out: Rider[] = [];
  for (const id of websiteIds) {
    try {
      const list = await getRiders(id);
      for (const r of list ?? []) {
        if (!seen.has(r.id)) {
          seen.add(r.id);
          out.push(r);
        }
      }
    } catch {
      // One outlet's rider call failing shouldn't blank the whole list.
    }
  }
  return out;
}

export function updateOrderStatus(
  orderId: string,
  status: OrderStatus,
  notes?: string,
): Promise<Order> {
  return authFetch<Order>(`/api/v1/delivery/orders/${orderId}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status, notes }),
  });
}

export function assignRider(
  orderId: string,
  riderId: string,
): Promise<Order> {
  return authFetch<Order>(`/api/v1/delivery/orders/${orderId}/assign-rider`, {
    method: 'PUT',
    body: JSON.stringify({ rider_id: riderId }),
  });
}
