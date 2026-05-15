'use client';

// OrderHero — top of the detail screen: customer name, copyable phone,
// distance/ETA pill (when known), and a WhatsApp shortcut.

import toast from 'react-hot-toast';
import { Copy, MessageCircle } from 'lucide-react';

import { formatPhoneForWA } from '../lib/phone';
import type { RiderOrder } from '../lib/types';

interface OrderHeroProps {
  order: RiderOrder;
}

const WA_TEMPLATE =
  'Hi, saya penghantar BinaApp untuk pesanan anda. Saya sedang dalam perjalanan ke alamat anda.';

export default function OrderHero({ order }: OrderHeroProps) {
  const handleCopyPhone = async () => {
    try {
      await navigator.clipboard.writeText(order.customer_phone);
      toast.success('Nombor disalin.');
    } catch {
      toast.error('Gagal salin nombor.');
    }
  };

  const waHref = `https://wa.me/${formatPhoneForWA(order.customer_phone)}?text=${encodeURIComponent(WA_TEMPLATE)}`;

  const distanceLine =
    order.distance_km || order.eta_minutes
      ? [
          order.distance_km ? `${order.distance_km} km` : null,
          order.eta_minutes ? `~${order.eta_minutes} min` : null,
        ]
          .filter(Boolean)
          .join(' · ')
      : null;

  return (
    <section className="mx-4 mt-3 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] p-4">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <h2 className="text-[18px] font-bold text-white truncate">
            {order.customer_name}
          </h2>
          <button
            type="button"
            onClick={handleCopyPhone}
            className="mt-1 inline-flex items-center gap-1.5 text-[13px] font-mono text-[var(--rider-text-2)] hover:text-white transition-colors"
          >
            <span>{order.customer_phone}</span>
            <Copy className="w-3.5 h-3.5" />
          </button>
          {distanceLine && (
            <p className="mt-1.5 text-[12px] text-[var(--rider-muted)]">
              {distanceLine}
            </p>
          )}
        </div>
        <a
          href={waHref}
          target="_blank"
          rel="noreferrer noopener"
          className="shrink-0 h-10 px-3 rounded-full bg-[#25D366]/15 border border-[#25D366]/40 text-[#25D366] text-[12px] font-semibold flex items-center gap-1.5 hover:bg-[#25D366]/25 transition-colors"
          aria-label="WhatsApp pelanggan"
        >
          <MessageCircle className="w-4 h-4" />
          WhatsApp
        </a>
      </div>
    </section>
  );
}
