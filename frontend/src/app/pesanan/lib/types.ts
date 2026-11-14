// /pesanan — shared types.
// Backend contract: backend/app/api/v1/endpoints/delivery.py
// We preserve snake_case from the API response (no rename layer) so the wire
// format is trivially debuggable in the network panel.

export type OrderStatus =
  | 'pending'
  | 'confirmed'
  | 'preparing'
  | 'ready'
  | 'picked_up'
  | 'delivering'
  | 'delivered'
  | 'completed'
  | 'cancelled'
  | 'rejected';

// 'assigned' exists in the legacy backend enum but is no longer produced by
// the workflow. We render unknown statuses through STATUS_META_FALLBACK rather
// than adding the dead value here.

export interface OrderItem {
  name: string;
  price: number;
  quantity: number;
}

export interface Order {
  id: string;
  order_number: string;
  website_id: string;
  customer_name: string;
  customer_phone: string;
  delivery_address: string;
  delivery_notes: string | null;
  delivery_fee: number;
  subtotal: number;
  total_amount: number;
  payment_method: string;
  status: OrderStatus | string;
  created_at: string;
  confirmed_at: string | null;
  rider_id: string | null;
  items: OrderItem[];
  notes: string;
  /** 'dine_in' = ordered from a table QR (no delivery leg). Absent on
   *  rows created before migration 064, which are all delivery. */
  order_type?: 'delivery' | 'dine_in' | string;
  table_number?: string | null;
  /** Voucher discount in RM, already subtracted from total_amount. */
  discount_amount?: number | null;
  voucher_code?: string | null;
  loyalty_points_redeemed?: number | null;
  /** Loyalty-points discount in RM, already subtracted from total_amount. */
  loyalty_discount?: number | null;
}

export interface Website {
  id: string;
  name?: string;
  business_name?: string;
  subdomain?: string;
}

export interface Rider {
  id: string;
  name: string;
  phone: string;
  vehicle_plate?: string;
  is_online?: boolean;
  website_id: string;
}

export type TabKey = 'semua' | 'baru' | 'aktif' | 'selesai' | 'batal';

export type DateRange = 'today' | 'yesterday' | '7days' | '30days' | 'custom';
