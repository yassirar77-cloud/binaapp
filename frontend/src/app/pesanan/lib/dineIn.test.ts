import { describe, expect, it } from 'vitest';
import { dineInNextStep, isDineIn, orderDiscount } from './dineIn';

describe('dine-in orders', () => {
  it('only orders marked dine_in are dine-in (older rows have no order_type)', () => {
    expect(isDineIn({ order_type: 'dine_in' })).toBe(true);
    expect(isDineIn({ order_type: 'delivery' })).toBe(false);
    expect(isDineIn({})).toBe(false);
  });

  it('walks the kitchen through preparing → ready → completed, never a rider step', () => {
    const seen: string[] = [];
    let status = 'confirmed';
    for (let i = 0; i < 5; i++) {
      const step = dineInNextStep(status);
      if (!step) break;
      seen.push(step.next);
      status = step.next;
    }
    expect(seen).toEqual(['preparing', 'ready', 'completed']);
  });

  it('offers nothing before acceptance or after the end', () => {
    for (const status of ['pending', 'completed', 'cancelled', 'rejected', 'delivering']) {
      expect(dineInNextStep(status)).toBeNull();
    }
  });

  it('adds voucher and points discounts, tolerating rows without the columns', () => {
    expect(orderDiscount({ discount_amount: 3, loyalty_discount: 5 })).toBe(8);
    expect(orderDiscount({})).toBe(0);
  });
});
