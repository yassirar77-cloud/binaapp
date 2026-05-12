'use client';

// Compact 84px order card. Body click opens the detail panel; inner action
// buttons stop propagation so their clicks don't double-fire as a select.
//
// Action area is status-driven:
//   pending              → Terima + Tolak
//   confirmed            → Pilih Rider
//   preparing | ready    → muted text + WA customer
//   picked_up|delivering → muted text + WA rider + WA customer
//   delivered|completed  → "Lihat" link
//   cancelled|rejected   → muted text + "Lihat" link

import { ChevronRight, MessageCircle } from 'lucide-react';
import type { KeyboardEvent, MouseEvent } from 'react';
import type { Order, Rider, Website } from '../lib/types';
import { statusMeta } from '../lib/constants';
import { relTime } from '../lib/relTime';
import StatusDot from './StatusDot';
import RiderPickerDropdown from './RiderPickerDropdown';

interface Props {
  order: Order;
  website: Website | null;
  /** When the order has a rider assigned, parent should pass phone for WA. */
  riderPhone?: string | null;
  selected: boolean;
  acceptingId: string | null;
  pickerOpen: boolean;
  allRiders: Rider[];
  onSelect: (order: Order) => void;
  onAccept: (order: Order) => void;
  onReject: (order: Order) => void;
  onPickRider: (order: Order) => void;
  onClosePicker: () => void;
  onAssignRider: (orderId: string, rider: Rider) => Promise<boolean>;
}

function waUrl(phone: string, name: string, shop: string, orderNumber: string) {
  const cleaned = phone.replace(/^0/, '60').replace(/[^0-9]/g, '');
  const text = `Hi ${name}, ini dari ${shop} mengenai pesanan ${orderNumber}`;
  return `https://wa.me/${cleaned}?text=${encodeURIComponent(text)}`;
}

/** Tiny helper so inner button/link clicks don't bubble to card-select. */
function stop(e: MouseEvent) {
  e.stopPropagation();
}

export default function OrderCard({
  order,
  website,
  riderPhone,
  selected,
  acceptingId,
  pickerOpen,
  allRiders,
  onSelect,
  onAccept,
  onReject,
  onPickRider,
  onClosePicker,
  onAssignRider,
}: Props) {
  const meta = statusMeta(order.status);
  const itemCount = order.items?.length ?? 0;
  const shopName =
    website?.name || website?.business_name || 'kedai';
  const accepting = acceptingId === order.id;

  const handleKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(order);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      onClick={() => onSelect(order)}
      onKeyDown={handleKey}
      className={[
        'group relative w-full min-h-[84px] flex items-center gap-3 px-4 py-3',
        'rounded-xl border transition-colors cursor-pointer',
        selected
          ? 'border-[#C7FF3D]/30 bg-[#C7FF3D]/[0.04]'
          : 'border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.05]',
      ].join(' ')}
    >
      <StatusDot color={meta.color} size={12} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-mono font-bold text-sm text-white truncate">
            #{order.order_number}
          </span>
          <span
            className="font-mono text-[10px] uppercase tracking-wider shrink-0"
            style={{ color: meta.color }}
          >
            {meta.short}
          </span>
        </div>
        <div className="text-xs text-white/60 truncate font-geist">
          {order.customer_name}
          <span className="text-white/30"> · </span>
          {relTime(order.created_at)}
        </div>
      </div>

      {/* Item count + total — hides under sm to keep the card compact on
          phones (action buttons get priority on small screens). */}
      <div className="hidden sm:flex flex-col items-end shrink-0 mr-1">
        <span className="font-mono text-[10px] text-white/40 tracking-wide">
          {itemCount} item
        </span>
        <span className="font-mono text-sm font-semibold text-[#C7FF3D] leading-tight">
          RM {order.total_amount.toFixed(2)}
        </span>
      </div>

      {/* Status-driven action area */}
      <div className="shrink-0 flex items-center gap-1.5" onClick={stop}>
        {order.status === 'pending' && (
          <>
            <button
              type="button"
              disabled={accepting}
              onClick={() => onAccept(order)}
              className="inline-flex items-center justify-center h-9 min-w-[44px] px-3 rounded-lg bg-[#C7FF3D] hover:bg-[#d8ff6b] active:bg-[#b5e633] text-[#0B0B15] font-geist text-xs font-semibold transition-colors disabled:opacity-60"
            >
              {accepting ? 'Memproses…' : 'Terima'}
            </button>
            <button
              type="button"
              disabled={accepting}
              onClick={() => onReject(order)}
              className="inline-flex items-center justify-center h-9 min-w-[44px] px-3 rounded-lg bg-white/[0.04] hover:bg-red-500/15 active:bg-red-500/25 text-white/70 hover:text-red-300 ring-1 ring-white/[0.08] hover:ring-red-400/30 font-geist text-xs font-medium transition-colors"
            >
              Tolak
            </button>
          </>
        )}

        {order.status === 'confirmed' && (
          <div className="relative">
            <button
              type="button"
              // Stop the picker's document-level mousedown outside-click
              // handler from firing on the same gesture that opens it.
              onMouseDown={(e) => e.stopPropagation()}
              onClick={() => onPickRider(order)}
              aria-haspopup="dialog"
              aria-expanded={pickerOpen}
              className="inline-flex items-center justify-center h-9 min-h-[44px] sm:min-h-0 px-3 rounded-lg bg-[#C7FF3D] hover:bg-[#d8ff6b] active:bg-[#b5e633] text-[#0B0B15] font-geist text-xs font-semibold transition-colors"
            >
              Pilih Rider
            </button>
            {pickerOpen ? (
              <RiderPickerDropdown
                orderId={order.id}
                websiteId={order.website_id}
                allRiders={allRiders}
                placement="below"
                align="right"
                onClose={onClosePicker}
                onAssign={onAssignRider}
              />
            ) : null}
          </div>
        )}

        {(order.status === 'preparing' || order.status === 'ready') && (
          <>
            <span className="hidden sm:inline font-geist text-[11px] text-white/50">
              Sedang diproses
            </span>
            <a
              href={waUrl(order.customer_phone, order.customer_name, shopName, order.order_number)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={stop}
              aria-label="WhatsApp pelanggan"
              className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-emerald-400/10 hover:bg-emerald-400/20 ring-1 ring-emerald-400/20 text-emerald-300 transition-colors"
            >
              <MessageCircle size={14} strokeWidth={1.5} />
            </a>
          </>
        )}

        {(order.status === 'picked_up' || order.status === 'delivering') && (
          <>
            <span className="hidden sm:inline font-geist text-[11px] text-white/50">
              Dalam perjalanan
            </span>
            {riderPhone && (
              <a
                href={waUrl(order.customer_phone, order.customer_name, shopName, order.order_number).replace(
                  /wa\.me\/\d+/,
                  `wa.me/${riderPhone.replace(/^0/, '60').replace(/[^0-9]/g, '')}`,
                )}
                target="_blank"
                rel="noopener noreferrer"
                onClick={stop}
                aria-label="WhatsApp rider"
                className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-indigo-400/10 hover:bg-indigo-400/20 ring-1 ring-indigo-400/20 text-indigo-300 transition-colors"
              >
                <MessageCircle size={14} strokeWidth={1.5} />
              </a>
            )}
            <a
              href={waUrl(order.customer_phone, order.customer_name, shopName, order.order_number)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={stop}
              aria-label="WhatsApp pelanggan"
              className="inline-flex items-center justify-center w-9 h-9 rounded-lg bg-emerald-400/10 hover:bg-emerald-400/20 ring-1 ring-emerald-400/20 text-emerald-300 transition-colors"
            >
              <MessageCircle size={14} strokeWidth={1.5} />
            </a>
          </>
        )}

        {(order.status === 'delivered' || order.status === 'completed') && (
          <span className="font-geist text-xs text-white/60 group-hover:text-white transition-colors">
            Lihat
          </span>
        )}

        {(order.status === 'cancelled' || order.status === 'rejected') && (
          <>
            <span className="hidden sm:inline font-geist text-[11px] text-white/40">
              {meta.label}
            </span>
            <span className="font-geist text-xs text-white/60 group-hover:text-white transition-colors">
              Lihat
            </span>
          </>
        )}
      </div>

      <ChevronRight
        size={16}
        strokeWidth={1.5}
        className="text-white/30 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
      />
    </div>
  );
}
