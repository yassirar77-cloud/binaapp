// Penghantar Live — API client.
// Mirrors the auth + authFetch pattern from /dashboard/penghantaran/lib/api.ts:
// backend token first, Supabase session as fallback. Returns Malay error text
// from the API when available.

import { supabase, ensureValidToken } from '@/lib/supabase';
import type { ActiveOrder, LiteZone, LiveRider } from './types';

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

export function getActiveOrders(websiteId: string): Promise<ActiveOrder[]> {
  return authFetch<ActiveOrder[]>(`/api/v1/live/website/${websiteId}/orders`);
}

export function getRiders(websiteId: string): Promise<LiveRider[]> {
  return authFetch<LiveRider[]>(`/api/v1/live/website/${websiteId}/riders`);
}

/** Fetch delivery zones for overlay rendering. Reuses the /zones endpoint
 *  owned by /dashboard/penghantaran — we only consume the subset of fields
 *  declared in LiteZone. */
export function getZones(websiteId: string): Promise<LiteZone[]> {
  return authFetch<LiteZone[]>(`/api/v1/zones/website/${websiteId}`);
}

/** Reassign or unassign (newRiderId=null) the rider on an order. 204 No Content. */
export async function reassignRider(
  orderId: string,
  newRiderId: string | null,
): Promise<void> {
  await authFetch<null>(`/api/v1/live/orders/${orderId}/rider`, {
    method: 'PATCH',
    body: JSON.stringify({ new_rider_id: newRiderId }),
  });
}

/** Cancel an order (status change only). Reason must be 10+ chars after strip. */
export async function cancelOrder(
  orderId: string,
  reason: string,
): Promise<void> {
  await authFetch<null>(`/api/v1/live/orders/${orderId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}
