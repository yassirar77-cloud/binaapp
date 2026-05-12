// Stuck-order detection for /dashboard/penghantar-live.
//
// Definition: an order is "stuck" when the rider has the order in hand
// (status picked_up or delivering) AND the eta_at is in the past AND the
// rider's GPS hasn't pinged in STUCK_THRESHOLD_MIN. Pure client-side
// computation — no DB column, no backend cron.

import type { ActiveOrder, LiveRider } from './types';

export const STUCK_THRESHOLD_MIN = 12;

const ACTIVE_DELIVERY_STATUSES = new Set(['picked_up', 'delivering']);

export function computeStuckOrder(
  order: ActiveOrder,
  rider: LiveRider | null,
): boolean {
  if (!ACTIVE_DELIVERY_STATUSES.has(order.status)) return false;
  if (!order.eta_at) return false;
  if (!rider || !rider.last_location_update) return false;

  const now = Date.now();
  const etaPassed = new Date(order.eta_at).getTime() < now;
  if (!etaPassed) return false;

  const minutesSincePing =
    (now - new Date(rider.last_location_update).getTime()) / 60_000;
  return minutesSincePing >= STUCK_THRESHOLD_MIN;
}

/** Computes the set of stuck order ids given current orders + riders. */
export function computeStuckOrderIds(
  orders: ActiveOrder[],
  riders: LiveRider[],
): ReadonlySet<string> {
  const riderById = new Map(riders.map((r) => [r.id, r]));
  const stuck = new Set<string>();
  for (const o of orders) {
    if (!o.rider_id) continue;
    if (computeStuckOrder(o, riderById.get(o.rider_id) ?? null)) {
      stuck.add(o.id);
    }
  }
  return stuck;
}
