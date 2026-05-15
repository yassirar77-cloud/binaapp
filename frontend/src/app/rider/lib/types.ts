// /rider — shared types.
// Mirrors the data shapes returned by /api/v1/delivery rider endpoints.
// Keep field names aligned with the backend; the rider PWA does not
// transform server payloads outside the api.ts wrappers.

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

export type PaymentMethod = 'cod' | 'online';

// Bottom-nav tabs. Order-list filter pills use the same union — see TABS in
// constants.ts.
export type Tab = 'aktif' | 'baru' | 'selesai';

export type GpsStatus = 'inactive' | 'active' | 'error' | 'permission_denied';

export type Route = 'login' | 'orders' | 'detail' | 'profile';

export interface Rider {
  id: string;
  name: string;
  phone: string;
  vehicle_type?: string;
  vehicle_plate?: string;
  photo_url?: string;
  website_id?: string;
  is_online?: boolean;
}

export interface OrderItem {
  qty: number;
  name: string;
  price: string;
}

export interface RiderOrder {
  id: string;
  order_number: string;
  customer_name: string;
  customer_phone: string;
  delivery_address: string;
  delivery_notes?: string;
  delivery_latitude?: number | null;
  delivery_longitude?: number | null;
  status: OrderStatus;
  payment_method: PaymentMethod;
  payment_received?: boolean | null;
  total: string;
  subtotal: string;
  delivery_fee: string;
  items?: OrderItem[];
  distance_km?: string;
  eta_minutes?: number;
  created_at: string;
  picked_up_at?: string;
  delivered_at?: string;
}

export interface TodayStats {
  count: number;
  earnings: string;
}
