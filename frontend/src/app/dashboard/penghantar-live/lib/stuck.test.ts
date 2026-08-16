import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { computeStuckOrder, computeStuckOrderIds, STUCK_THRESHOLD_MIN } from './stuck';
import type { ActiveOrder, LiveRider } from './types';

const NOW = new Date('2026-08-16T12:00:00Z').getTime();

function minutesAgo(min: number): string {
  return new Date(NOW - min * 60_000).toISOString();
}

function makeOrder(overrides: Partial<ActiveOrder> = {}): ActiveOrder {
  return {
    id: 'o1',
    order_number: 'D-1001',
    customer_name: 'Aisyah',
    customer_phone: '0123456789',
    delivery_address: 'Jalan Ampang',
    delivery_latitude: 3.15,
    delivery_longitude: 101.7,
    items: [],
    subtotal: 20,
    delivery_fee: 5,
    total_amount: 25,
    status: 'delivering',
    created_at: minutesAgo(60),
    picked_up_at: minutesAgo(30),
    estimated_delivery_time: 30,
    eta_at: minutesAgo(10),
    rider_id: 'r1',
    rider_name: 'Ali',
    rider_phone: '0198765432',
    rider_vehicle_plate: 'WXY 1234',
    rider_current_latitude: 3.14,
    rider_current_longitude: 101.69,
    rider_last_location_update: minutesAgo(STUCK_THRESHOLD_MIN + 1),
    rider_is_online: true,
    delivery_zone_id: null,
    zone_name: null,
    zone_color: null,
    zone_outer_radius_m: null,
    ...overrides,
  } as ActiveOrder;
}

function makeRider(overrides: Partial<LiveRider> = {}): LiveRider {
  return {
    id: 'r1',
    name: 'Ali',
    phone: '0198765432',
    vehicle_plate: 'WXY 1234',
    vehicle_type: 'motorcycle',
    vehicle_model: null,
    is_active: true,
    is_online: true,
    current_latitude: 3.14,
    current_longitude: 101.69,
    last_location_update: minutesAgo(STUCK_THRESHOLD_MIN + 1),
    active_order_id: 'o1',
    active_order_number: 'D-1001',
    active_order_eta_at: minutesAgo(10),
    active_order_status: 'delivering',
    today_deliveries: 3,
    ...overrides,
  } as LiveRider;
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('computeStuckOrder', () => {
  it('flags a late order whose rider GPS has gone silent', () => {
    expect(computeStuckOrder(makeOrder(), makeRider())).toBe(true);
  });

  it('ignores orders not yet picked up', () => {
    expect(
      computeStuckOrder(makeOrder({ status: 'pending' }), makeRider()),
    ).toBe(false);
    expect(
      computeStuckOrder(makeOrder({ status: 'preparing' }), makeRider()),
    ).toBe(false);
  });

  it('ignores orders whose ETA has not passed', () => {
    const future = new Date(NOW + 10 * 60_000).toISOString();
    expect(
      computeStuckOrder(makeOrder({ eta_at: future }), makeRider()),
    ).toBe(false);
  });

  it('ignores orders with no ETA at all', () => {
    expect(computeStuckOrder(makeOrder({ eta_at: null }), makeRider())).toBe(
      false,
    );
  });

  it('does not flag when the rider is still pinging', () => {
    expect(
      computeStuckOrder(
        makeOrder(),
        makeRider({ last_location_update: minutesAgo(1) }),
      ),
    ).toBe(false);
  });

  it('does not flag riders that never sent GPS', () => {
    expect(
      computeStuckOrder(
        makeOrder(),
        makeRider({ last_location_update: null }),
      ),
    ).toBe(false);
    expect(computeStuckOrder(makeOrder(), null)).toBe(false);
  });
});

describe('computeStuckOrderIds', () => {
  it('collects only stuck orders, skipping unassigned ones', () => {
    const stuckOrder = makeOrder();
    const unassigned = makeOrder({ id: 'o2', rider_id: null, status: 'pending' });
    const healthy = makeOrder({
      id: 'o3',
      rider_id: 'r2',
      eta_at: new Date(NOW + 5 * 60_000).toISOString(),
    });
    const riders = [
      makeRider(),
      makeRider({ id: 'r2', last_location_update: minutesAgo(1) }),
    ];
    const result = computeStuckOrderIds([stuckOrder, unassigned, healthy], riders);
    expect([...result]).toEqual(['o1']);
  });
});
