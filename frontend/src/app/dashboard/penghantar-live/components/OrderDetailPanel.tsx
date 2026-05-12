'use client';

// OrderDetailPanel — right-side slide-in showing a single order's details.
//
// Action buttons render here but the actual modal openings (Re-assign,
// Batalkan) are wired in commit 6. tel: / wa.me anchors are live now.

import { Bike, MapPin, Package, Phone, X } from 'lucide-react';
import type { ActiveOrder } from '../lib/types';
import StatusPill from './StatusPill';

function formatCurrency(n: number): string {
  return `RM ${n.toFixed(2)}`;
}

function formatBigEta(etaAt: string | null): { primary: string; secondary: string; tone: 'normal' | 'late' } {
  if (!etaAt) return { primary: '—', secondary: 'ETA tiada', tone: 'normal' };
  const diffMs = new Date(etaAt).getTime() - Date.now();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 0) {
    const m = Math.abs(minutes);
    return {
      primary: m < 60 ? `${m} min` : `${(m / 60).toFixed(1)} jam`,
      secondary: 'Lewat dari anggaran',
      tone: 'late',
    };
  }
  if (minutes < 60) {
    return { primary: `${minutes} min`, secondary: 'Sehingga sampai', tone: 'normal' };
  }
  return {
    primary: `${(minutes / 60).toFixed(1)} jam`,
    secondary: 'Sehingga sampai',
    tone: 'normal',
  };
}

function cleanPhone(raw: string | null | undefined): string {
  if (!raw) return '';
  // Strip everything except digits; wa.me wants no leading +.
  return raw.replace(/\D/g, '');
}

export default function OrderDetailPanel({
  order,
  variant = 'desktop',
  onClose,
  onReassignClick,
  onCancelClick,
}: {
  order: ActiveOrder;
  variant?: 'desktop' | 'mobile';
  onClose: () => void;
  onReassignClick: () => void;
  onCancelClick: () => void;
}) {
  const eta = formatBigEta(order.eta_at);
  const customerTel = cleanPhone(order.customer_phone);
  const riderTel = cleanPhone(order.rider_phone);
  const waMsg = `Hai ${order.rider_name ?? ''}, pasal pesanan ${order.order_number}…`;
  const waHref = riderTel
    ? `https://wa.me/${riderTel}?text=${encodeURIComponent(waMsg)}`
    : null;

  return (
    <aside
      className={
        variant === 'mobile'
          ? 'phl-mobile-modal fixed inset-0 z-[1500] flex flex-col bg-[#0a0e1a]'
          : 'phl-detail-panel flex flex-col h-full w-[360px] shrink-0 border-l border-white/[0.08] bg-[#0a0e1a]'
      }
      aria-label="Maklumat pesanan"
    >
      <div className="flex items-start justify-between gap-3 px-4 pt-4 pb-3 border-b border-white/[0.06]">
        <div className="min-w-0">
          <div className="font-mono text-[11px] tracking-wider text-white/50 uppercase">
            {order.order_number}
          </div>
          <div className="mt-1 flex items-center gap-2">
            <StatusPill status={order.status} size="md" />
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Tutup"
          className="h-10 w-10 -mr-2 -mt-1 flex items-center justify-center rounded-lg text-white/60 hover:text-white hover:bg-white/[0.06] transition"
        >
          <X size={18} strokeWidth={1.5} />
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Big ETA */}
        <div className="px-4 py-4 border-b border-white/[0.06]">
          <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
            ETA
          </div>
          <div
            className={`mt-1 font-mono font-semibold text-3xl ${
              eta.tone === 'late' ? 'text-red-300' : 'text-white'
            }`}
          >
            {eta.primary}
          </div>
          <div className="text-xs text-white/50 font-geist mt-0.5">
            {eta.secondary}
          </div>
        </div>

        {/* Customer */}
        <section className="px-4 py-4 border-b border-white/[0.06] space-y-2">
          <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
            Pelanggan
          </div>
          <div className="text-sm text-white font-geist font-medium">
            {order.customer_name}
          </div>
          {customerTel && (
            <a
              href={`tel:${customerTel}`}
              className="inline-flex items-center gap-1.5 text-[13px] text-white/70 hover:text-white"
            >
              <Phone size={13} strokeWidth={1.5} />
              {order.customer_phone}
            </a>
          )}
          <div className="flex items-start gap-1.5 text-[12px] text-white/60">
            <MapPin size={13} strokeWidth={1.5} className="shrink-0 mt-0.5" />
            <span>{order.delivery_address}</span>
          </div>
        </section>

        {/* Items */}
        <section className="px-4 py-4 border-b border-white/[0.06]">
          <div className="flex items-center justify-between mb-2">
            <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
              Item
            </div>
            <span className="font-mono text-[11px] text-white/40">
              {order.items.length}
            </span>
          </div>
          {order.items.length === 0 ? (
            <div className="flex flex-col items-center text-white/40 py-3">
              <Package size={16} strokeWidth={1.5} />
              <span className="mt-1 text-xs">Tiada item direkodkan</span>
            </div>
          ) : (
            <ul className="space-y-1.5">
              {order.items.map((it, idx) => (
                <li
                  key={it.id ?? `${idx}-${it.item_name}`}
                  className="flex items-start justify-between gap-3 text-[13px]"
                >
                  <div className="min-w-0">
                    <span className="font-mono text-white/50 mr-1.5">
                      {it.quantity}×
                    </span>
                    <span className="text-white">{it.item_name}</span>
                  </div>
                  <div className="font-mono text-white/70 shrink-0">
                    {formatCurrency(it.total_price)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Totals */}
        <section className="px-4 py-4 border-b border-white/[0.06] space-y-1">
          <Row label="Subtotal" value={formatCurrency(order.subtotal)} />
          <Row label="Yuran penghantaran" value={formatCurrency(order.delivery_fee)} />
          <div className="pt-2 mt-1 border-t border-white/[0.06]">
            <Row
              label="Jumlah"
              value={formatCurrency(order.total_amount)}
              strong
            />
          </div>
        </section>

        {/* Rider info */}
        <section className="px-4 py-4 space-y-2">
          <div className="font-mono text-[10px] uppercase tracking-wider text-white/50">
            Rider
          </div>
          {order.rider_id ? (
            <>
              <div className="text-sm text-white font-geist font-medium">
                {order.rider_name ?? 'Rider'}
              </div>
              <div className="flex flex-wrap items-center gap-3 text-[12px] text-white/60">
                {order.rider_vehicle_plate && (
                  <span className="font-mono">{order.rider_vehicle_plate}</span>
                )}
                {riderTel && (
                  <a
                    href={`tel:${riderTel}`}
                    className="inline-flex items-center gap-1 hover:text-white"
                  >
                    <Phone size={12} strokeWidth={1.5} />
                    {order.rider_phone}
                  </a>
                )}
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2 text-[13px] text-white/50">
              <Bike size={14} strokeWidth={1.5} />
              Belum ada rider ditugaskan
            </div>
          )}
        </section>
      </div>

      {/* Action footer (sticky) */}
      <div className="border-t border-white/[0.08] bg-[#0a0e1a] px-3 py-3 space-y-2">
        {customerTel && (
          <ActionLink href={`tel:${customerTel}`} variant="default">
            Hubungi pelanggan
          </ActionLink>
        )}
        {riderTel && (
          <ActionLink href={`tel:${riderTel}`} variant="default">
            Hubungi rider
          </ActionLink>
        )}
        {waHref && (
          <ActionLink
            href={waHref}
            variant="default"
            target="_blank"
            rel="noopener noreferrer"
          >
            Mesej rider (WhatsApp)
          </ActionLink>
        )}
        <ActionButton onClick={onReassignClick} variant="default">
          Tukar rider
        </ActionButton>
        <ActionButton onClick={onCancelClick} variant="danger">
          Batalkan pesanan
        </ActionButton>
      </div>
    </aside>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between text-[13px]">
      <span className={strong ? 'text-white font-geist font-medium' : 'text-white/60 font-geist'}>
        {label}
      </span>
      <span
        className={`font-mono ${
          strong ? 'text-white font-semibold' : 'text-white/70'
        }`}
      >
        {value}
      </span>
    </div>
  );
}

const BTN_BASE =
  'w-full inline-flex items-center justify-center h-11 px-3 rounded-lg text-sm font-geist font-medium transition';

function ActionButton({
  onClick,
  variant,
  children,
}: {
  onClick: () => void;
  variant: 'default' | 'danger';
  children: React.ReactNode;
}) {
  const tone =
    variant === 'danger'
      ? 'bg-red-400/10 text-red-300 hover:bg-red-400/15 ring-1 ring-red-400/20'
      : 'bg-white/[0.06] text-white hover:bg-white/[0.10] ring-1 ring-white/[0.08]';
  return (
    <button type="button" onClick={onClick} className={`${BTN_BASE} ${tone}`}>
      {children}
    </button>
  );
}

function ActionLink({
  href,
  variant,
  target,
  rel,
  children,
}: {
  href: string;
  variant: 'default' | 'danger';
  target?: string;
  rel?: string;
  children: React.ReactNode;
}) {
  const tone =
    variant === 'danger'
      ? 'bg-red-400/10 text-red-300 hover:bg-red-400/15 ring-1 ring-red-400/20'
      : 'bg-white/[0.06] text-white hover:bg-white/[0.10] ring-1 ring-white/[0.08]';
  return (
    <a href={href} target={target} rel={rel} className={`${BTN_BASE} ${tone}`}>
      {children}
    </a>
  );
}
