'use client';

// OrderDetailScreen — full-screen detail view for a single order.
//
// Layout (top to bottom):
//   1. custom top bar (back / order number / status pill)
//   2. OrderHero
//   3. ActionQuad
//   4. RouteMap (collapsible)
//   5. Address card (with optional delivery notes)
//   6. ItemList
//   7. BottomActionBar (fixed)
//
// The screen is presentational; status mutations + CODModal trigger live
// in the parent RiderApp.

import { ArrowLeft, MapPin, StickyNote } from 'lucide-react';

import type { OrderStatus, RiderOrder } from '../lib/types';
import ActionQuad from './ActionQuad';
import BottomActionBar from './BottomActionBar';
import ItemList from './ItemList';
import OrderHero from './OrderHero';
import RouteMap from './RouteMap';
import StatusPill from './StatusPill';

interface OrderDetailScreenProps {
  order: RiderOrder;
  pending: boolean;
  riderLocation: { lat: number; lng: number } | null;
  onBack: () => void;
  onAdvance: (order: RiderOrder, next: OrderStatus) => void;
}

export default function OrderDetailScreen({
  order,
  pending,
  riderLocation,
  onBack,
  onAdvance,
}: OrderDetailScreenProps) {
  return (
    <div className="min-h-[100dvh] pb-32 rider-fade-in">
      {/* Custom top bar — replaces the orders-screen TopBar for this route */}
      <header className="sticky top-0 z-30 h-14 px-2 flex items-center gap-2 bg-[var(--rider-bg)]/90 backdrop-blur-md border-b border-[var(--rider-border)]">
        <button
          type="button"
          onClick={onBack}
          className="w-10 h-10 rounded-full flex items-center justify-center text-white hover:bg-[var(--rider-surface)] transition-colors"
          aria-label="Kembali"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="flex-1 font-mono text-[14px] text-white truncate">
          #{order.order_number}
        </h1>
        <div className="pr-2">
          <StatusPill status={order.status} />
        </div>
      </header>

      <OrderHero order={order} />
      <ActionQuad order={order} />
      <RouteMap
        riderLocation={riderLocation}
        customerLat={order.delivery_latitude ?? null}
        customerLng={order.delivery_longitude ?? null}
      />

      {/* Address + delivery notes */}
      <section className="mx-4 mt-3 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] p-4">
        <div className="flex items-start gap-2.5">
          <MapPin className="w-4 h-4 mt-0.5 text-[var(--rider-lime)] shrink-0" />
          <div className="flex-1 min-w-0">
            <h3 className="text-[12px] font-semibold text-[var(--rider-text-2)] uppercase tracking-wide">
              Alamat Hantar
            </h3>
            <p className="mt-1 text-[14px] text-white leading-relaxed">
              {order.delivery_address}
            </p>
          </div>
        </div>
        {order.delivery_notes && (
          <div className="mt-3 pt-3 border-t border-[var(--rider-border)] flex items-start gap-2.5">
            <StickyNote className="w-4 h-4 mt-0.5 text-[var(--rider-amber)] shrink-0" />
            <div className="flex-1 min-w-0">
              <h3 className="text-[12px] font-semibold text-[var(--rider-text-2)] uppercase tracking-wide">
                Nota Pelanggan
              </h3>
              <p className="mt-1 text-[13px] text-[var(--rider-text-2)] leading-relaxed">
                {order.delivery_notes}
              </p>
            </div>
          </div>
        )}
      </section>

      <ItemList order={order} />

      <BottomActionBar order={order} pending={pending} onAdvance={onAdvance} />
    </div>
  );
}
