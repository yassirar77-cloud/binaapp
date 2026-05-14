// /rider — API client.
// The rider PWA does NOT use Supabase auth — it logs in directly against
// /api/v1/delivery/riders/login (bcrypt) and stores the rider record in
// localStorage. All subsequent endpoints are public (rider_id in the path
// is the only identifier). Do not switch this to authFetch.

import type { OrderStatus, Rider, RiderOrder, TodayStats } from './types';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

/** Thrown by riderFetch with the HTTP status attached. status === 0 means
 *  the fetch call itself threw (network failure / offline). */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function riderFetch<T>(
  path: string,
  opts: RequestInit = {},
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(opts.headers || {}),
      },
    });
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : 'Network error',
      0,
    );
  }

  if (res.status === 204) {
    return null as unknown as T;
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail || body?.message || detail;
    } catch {
      /* ignore — body may not be JSON */
    }
    throw new ApiError(detail || `HTTP ${res.status}`, res.status);
  }

  return (await res.json()) as T;
}

// ----- Public API -----

interface LoginResponse {
  success: boolean;
  rider: Rider;
}

/** POST /api/v1/delivery/riders/login — bcrypt password check on the server.
 *  Strips whitespace from the phone before sending (the input field allows
 *  spaces for readability). */
export async function loginRider(
  phone: string,
  password: string,
): Promise<Rider> {
  const res = await riderFetch<LoginResponse>(
    '/api/v1/delivery/riders/login',
    {
      method: 'POST',
      body: JSON.stringify({
        phone: phone.replace(/\s/g, ''),
        password,
      }),
    },
  );
  if (!res?.success || !res?.rider) {
    throw new ApiError('Login gagal. Sila cuba lagi.', 401);
  }
  return res.rider;
}

interface OrdersResponse {
  orders?: RiderOrder[];
}

/** GET /api/v1/delivery/riders/{rider_id}/orders — returns {orders: [...]}
 *  on the server; we unwrap to the array. Returns [] on missing key so the
 *  UI never has to null-check. */
export async function fetchRiderOrders(
  riderId: string,
): Promise<RiderOrder[]> {
  const res = await riderFetch<OrdersResponse>(
    `/api/v1/delivery/riders/${riderId}/orders`,
  );
  return res?.orders ?? [];
}

/** PUT /api/v1/delivery/riders/{rider_id}/orders/{order_id}/status — accepts
 *  optional `payment_received` (Phase 4 backend change). Pass it on the
 *  `delivering → delivered` transition for COD orders. */
export async function updateOrderStatus(
  riderId: string,
  orderId: string,
  status: OrderStatus,
  options?: { notes?: string; payment_received?: boolean | null },
): Promise<void> {
  await riderFetch<void>(
    `/api/v1/delivery/riders/${riderId}/orders/${orderId}/status`,
    {
      method: 'PUT',
      body: JSON.stringify({
        status,
        notes: options?.notes,
        payment_received: options?.payment_received,
      }),
    },
  );
}

/** PUT /api/v1/delivery/riders/{rider_id}/location — the periodic GPS ping
 *  (every 15s via useGeolocation). The optional order_id lets the backend
 *  associate the fix with an active delivery. */
export async function updateRiderLocation(
  riderId: string,
  lat: number,
  lng: number,
  orderId?: string,
): Promise<void> {
  await riderFetch<void>(
    `/api/v1/delivery/riders/${riderId}/location`,
    {
      method: 'PUT',
      body: JSON.stringify({
        latitude: lat,
        longitude: lng,
        timestamp: new Date().toISOString(),
        order_id: orderId,
      }),
    },
  );
}

/** GET /api/v1/delivery/riders/{rider_id}/today — Phase 4 endpoint. Falls
 *  back to zeros if the endpoint is not yet deployed. */
export async function fetchTodayStats(
  riderId: string,
): Promise<TodayStats> {
  try {
    return await riderFetch<TodayStats>(
      `/api/v1/delivery/riders/${riderId}/today`,
    );
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      return { count: 0, earnings: '0.00' };
    }
    throw e;
  }
}
