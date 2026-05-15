'use client';

// ActionQuad — 4 deep-link tiles: Call, WhatsApp, Waze, Google Maps.
// Waze prefers a coordinate URL when the order has GPS; otherwise it
// falls back to an address search. All links open in a new tab so the
// PWA install state survives.

import { Map, MessageCircle, Navigation, Phone } from 'lucide-react';

import { formatPhoneForWA } from '../lib/phone';
import type { RiderOrder } from '../lib/types';

interface ActionQuadProps {
  order: RiderOrder;
}

const WA_TEMPLATE =
  'Hi, saya penghantar BinaApp untuk pesanan anda. Saya sedang dalam perjalanan ke alamat anda.';

function buildWazeHref(order: RiderOrder): string {
  if (order.delivery_latitude && order.delivery_longitude) {
    return `https://waze.com/ul?ll=${order.delivery_latitude},${order.delivery_longitude}&navigate=yes`;
  }
  return `https://waze.com/ul?q=${encodeURIComponent(order.delivery_address)}`;
}

function buildGMapsHref(order: RiderOrder): string {
  const dest =
    order.delivery_latitude && order.delivery_longitude
      ? `${order.delivery_latitude},${order.delivery_longitude}`
      : order.delivery_address;
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(dest)}`;
}

interface TileProps {
  label: string;
  href: string;
  external?: boolean;
  Icon: typeof Phone;
  accent: string;
}

function Tile({ label, href, external, Icon, accent }: TileProps) {
  return (
    <a
      href={href}
      target={external ? '_blank' : undefined}
      rel={external ? 'noreferrer noopener' : undefined}
      className="flex flex-col items-center justify-center gap-1 h-16 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] hover:border-[var(--rider-border-2)] active:bg-[var(--rider-surface-2)] transition-colors"
    >
      <Icon className="w-5 h-5" style={{ color: accent }} />
      <span className="text-[11px] font-medium text-[var(--rider-text-2)]">
        {label}
      </span>
    </a>
  );
}

export default function ActionQuad({ order }: ActionQuadProps) {
  const waHref = `https://wa.me/${formatPhoneForWA(order.customer_phone)}?text=${encodeURIComponent(WA_TEMPLATE)}`;

  return (
    <section className="mx-4 mt-3 grid grid-cols-4 gap-2">
      <Tile
        label="Hubungi"
        href={`tel:${order.customer_phone}`}
        Icon={Phone}
        accent="#C7FF3D"
      />
      <Tile
        label="WhatsApp"
        href={waHref}
        external
        Icon={MessageCircle}
        accent="#25D366"
      />
      <Tile
        label="Waze"
        href={buildWazeHref(order)}
        external
        Icon={Navigation}
        accent="#33CCFF"
      />
      <Tile
        label="Peta"
        href={buildGMapsHref(order)}
        external
        Icon={Map}
        accent="#FF5A5F"
      />
    </section>
  );
}
