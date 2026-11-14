// /pesanan — dine-in (table QR) orders.
//
// A dine-in order has no delivery leg, so the rider steps do not apply:
//   pending → confirmed → preparing → ready → completed
// The backend enforces the same table (DINE_IN_ORDER_TRANSITIONS in
// api/v1/endpoints/delivery.py); this file only decides which single
// button the kitchen sees next.

import type { Order, OrderStatus } from './types';

export function isDineIn(order: Pick<Order, 'order_type'>): boolean {
  return order.order_type === 'dine_in';
}

export interface DineInStep {
  /** Status the button moves the order to. */
  next: OrderStatus;
  /** Button label. */
  label: string;
  /** Toast shown after it succeeds. */
  done: string;
}

/** The kitchen's next action for a dine-in order, or null when there is none. */
export function dineInNextStep(status: string): DineInStep | null {
  switch (status) {
    case 'confirmed':
      return { next: 'preparing', label: 'Mula Sediakan', done: 'sedang disediakan' };
    case 'preparing':
      return { next: 'ready', label: 'Sedia Dihidang', done: 'sedia dihidang' };
    case 'ready':
      return { next: 'completed', label: 'Selesai', done: 'selesai' };
    default:
      return null;
  }
}

/** Voucher + loyalty discount on an order, in RM. */
export function orderDiscount(
  order: Pick<Order, 'discount_amount' | 'loyalty_discount'>,
): number {
  return (Number(order.discount_amount) || 0) + (Number(order.loyalty_discount) || 0);
}
