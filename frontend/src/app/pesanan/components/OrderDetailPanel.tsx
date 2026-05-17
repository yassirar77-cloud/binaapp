'use client';

// Right-side detail panel for a selected order. Slides in via the
// `pesanan-slide-in` keyframe defined in pesanan.css. Close handlers (ESC,
// click-outside) live in PesananClient — this component only renders chrome +
// fires onClose when the X is clicked.
//
// Sticky action footer reflects the order's status:
//   pending              → Terima + Tolak
//   confirmed            → Pilih Rider
//   preparing | ready    → muted disabled state
//   picked_up|delivering → muted disabled state
//   delivered            → Tandakan selesai
//   completed            → no actions
//   cancelled|rejected   → no actions (cancellation_reason shown above)

import { X } from 'lucide-react';
import type { Order, Rider } from '../lib/types';
import { statusMeta } from '../lib/constants';
import StatusPill from './StatusPill';
import Timeline from './Timeline';
import CustomerInfoCard from './CustomerInfoCard';
import RiderInfoCard from './RiderInfoCard';
import RiderPickerDropdown from './RiderPickerDropdown';

interface Props {
  order: Order;
  rider: Rider | null;
  acceptingId: string | null;
  completingId: string | null;
  pickerOpen: boolean;
  allRiders: Rider[];
  /** desktop = inline flex item, slide-in from right.
   *  mobile  = fixed overlay + backdrop, slide-up from bottom. */
  variant: 'desktop' | 'mobile';
  onClose: () => void;
  onAccept: (order: Order) => void;
  onReject: (order: Order) => void;
  onPickRider: (order: Order) => void;
  onMarkCompleted: (order: Order) => void;
  onClosePicker: () => void;
  onAssignRider: (orderId: string, rider: Rider) => Promise<boolean>;
}

const LIME = '#C7FF3D';

/** Pull the cancellation reason out of `notes`. Legacy backend stores it as
 *  "Pesanan ditolak: <reason>"; surface just the human part when present. */
function extractCancellationReason(notes: string | null | undefined): string | null {
  if (!notes) return null;
  const m = /Pesanan ditolak:\s*(.+)$/i.exec(notes);
  return m ? m[1].trim() : notes;
}

export default function OrderDetailPanel({
  order,
  rider,
  acceptingId,
  completingId,
  pickerOpen,
  allRiders,
  variant,
  onClose,
  onAccept,
  onReject,
  onPickRider,
  onMarkCompleted,
  onClosePicker,
  onAssignRider,
}: Props) {
  const meta = statusMeta(order.status);
  const accepting = acceptingId === order.id;
  const completing = completingId === order.id;
  const cancellationReason =
    order.status === 'cancelled' || order.status === 'rejected'
      ? extractCancellationReason(order.notes)
      : null;

  // Wrapper differs by variant; the inner header / body / footer JSX is the
  // same, so we build it once below and inject into the right wrapper.
  const isMobile = variant === 'mobile';

  const panelClasses = isMobile
    ? 'pesanan-slide-up absolute inset-x-0 bottom-0 top-14 bg-[#0d1120] rounded-t-2xl shadow-2xl shadow-black/50 flex flex-col min-h-0'
    : 'pesanan-slide-in w-[420px] shrink-0 flex flex-col bg-[#0d1120] border-l border-white/[0.08] min-h-0';

  const panel = (
    <aside
      className={panelClasses}
      role="dialog"
      aria-label={`Butiran pesanan ${order.order_number}`}
      // On mobile the wrapper backdrop closes on click; stop propagation so
      // clicks inside the panel itself don't close it.
      onMouseDown={isMobile ? (e) => e.stopPropagation() : undefined}
    >
      {/* Header */}
      <div className="shrink-0 px-5 pt-3 sm:pt-5 pb-4 border-b border-white/[0.06]">
        {isMobile ? (
          <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-white/15" />
        ) : null}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-mono font-bold text-lg text-white tracking-tight truncate">
              #{order.order_number}
            </div>
            <div className="mt-2">
              <StatusPill status={order.status} size="md" />
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="shrink-0 inline-flex items-center justify-center w-9 h-9 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-white/60 hover:text-white ring-1 ring-white/[0.06] transition-colors"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5">
        <section>
          <h3 className="font-mono text-[10px] uppercase tracking-wider text-white/40 mb-3">
            Status Pesanan
          </h3>
          <Timeline order={order} />
        </section>

        <CustomerInfoCard order={order} />

        {/* Items */}
        <section>
          <h3 className="font-mono text-[10px] uppercase tracking-wider text-white/40 mb-2">
            Item Pesanan
          </h3>
          <div className="rounded-xl bg-white/[0.03] ring-1 ring-white/[0.06] divide-y divide-white/[0.06]">
            {(order.items?.length ?? 0) === 0 ? (
              <div className="px-3 py-3 text-xs text-white/40 font-geist">
                Tiada item.
              </div>
            ) : (
              (order.items ?? []).map((it, idx) => (
                <div
                  key={`${it.name}-${idx}`}
                  className="flex items-start justify-between gap-3 px-3 py-2.5"
                >
                  <div className="flex items-start gap-2 min-w-0">
                    <span className="font-mono text-xs text-white/50 shrink-0">
                      {it.quantity}×
                    </span>
                    <span className="font-geist text-xs text-white/85 truncate">
                      {it.name}
                    </span>
                  </div>
                  <span className="font-mono text-xs text-white/85 shrink-0">
                    RM {(it.price * it.quantity).toFixed(2)}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Totals */}
        <section className="rounded-xl bg-white/[0.03] ring-1 ring-white/[0.06] p-3">
          <div className="flex items-center justify-between text-xs font-geist text-white/55 py-1">
            <span>Subtotal</span>
            <span className="font-mono text-white/80">
              RM {order.subtotal.toFixed(2)}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs font-geist text-white/55 py-1">
            <span>Yuran Penghantaran</span>
            <span className="font-mono text-white/80">
              RM {order.delivery_fee.toFixed(2)}
            </span>
          </div>
          <div className="border-t border-white/[0.06] mt-2 pt-2 flex items-center justify-between">
            <span className="font-geist text-sm font-semibold text-white">
              Jumlah
            </span>
            <span className="font-mono text-base font-bold" style={{ color: LIME }}>
              RM {order.total_amount.toFixed(2)}
            </span>
          </div>
          {order.payment_method ? (
            <div className="mt-1 text-[10px] uppercase tracking-wider font-mono text-white/35">
              Bayaran: {order.payment_method}
            </div>
          ) : null}
        </section>

        {/* Rider (conditional) */}
        {order.rider_id && rider ? <RiderInfoCard rider={rider} /> : null}

        {/* Cancellation reason (conditional) */}
        {cancellationReason ? (
          <section className="rounded-xl bg-red-400/[0.06] ring-1 ring-red-400/[0.2] p-3">
            <div className="font-mono text-[10px] uppercase tracking-wider text-red-300 mb-1">
              Sebab {meta.label}
            </div>
            <div className="font-geist text-xs text-white/80 whitespace-pre-wrap">
              {cancellationReason}
            </div>
          </section>
        ) : null}
      </div>

      {/* Sticky action footer */}
      <div className="shrink-0 border-t border-white/[0.06] px-5 py-4 bg-[#0d1120]">
        {order.status === 'pending' && (
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              disabled={accepting}
              onClick={() => onAccept(order)}
              className="inline-flex items-center justify-center h-11 px-3 rounded-lg bg-[#C7FF3D] hover:bg-[#d8ff6b] active:bg-[#b5e633] text-[#0B0B15] font-geist text-sm font-semibold transition-colors disabled:opacity-60"
            >
              {accepting ? 'Memproses…' : 'Terima'}
            </button>
            <button
              type="button"
              disabled={accepting}
              onClick={() => onReject(order)}
              className="inline-flex items-center justify-center h-11 px-3 rounded-lg bg-white/[0.04] hover:bg-red-500/15 active:bg-red-500/25 text-white/80 hover:text-red-300 ring-1 ring-white/[0.08] hover:ring-red-400/30 font-geist text-sm font-medium transition-colors"
            >
              Tolak
            </button>
          </div>
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
              className="w-full inline-flex items-center justify-center h-11 px-3 rounded-lg bg-[#C7FF3D] hover:bg-[#d8ff6b] active:bg-[#b5e633] text-[#0B0B15] font-geist text-sm font-semibold transition-colors"
            >
              Pilih Rider
            </button>
            {pickerOpen ? (
              <RiderPickerDropdown
                orderId={order.id}
                allRiders={allRiders}
                placement="above"
                align="right"
                onClose={onClosePicker}
                onAssign={onAssignRider}
              />
            ) : null}
          </div>
        )}

        {(order.status === 'preparing' ||
          order.status === 'ready' ||
          order.status === 'picked_up' ||
          order.status === 'delivering') && (
          <div className="w-full inline-flex items-center justify-center h-11 px-3 rounded-lg bg-white/[0.04] ring-1 ring-white/[0.06] font-geist text-sm text-white/55">
            {meta.label}
          </div>
        )}

        {order.status === 'delivered' && (
          <button
            type="button"
            disabled={completing}
            onClick={() => onMarkCompleted(order)}
            className="w-full inline-flex items-center justify-center h-11 px-3 rounded-lg bg-[#C7FF3D] hover:bg-[#d8ff6b] active:bg-[#b5e633] text-[#0B0B15] font-geist text-sm font-semibold transition-colors disabled:opacity-60"
          >
            {completing ? 'Memproses…' : 'Tandakan selesai'}
          </button>
        )}

        {(order.status === 'completed' ||
          order.status === 'cancelled' ||
          order.status === 'rejected') && (
          <div className="w-full inline-flex items-center justify-center h-11 px-3 rounded-lg bg-white/[0.03] ring-1 ring-white/[0.04] font-geist text-sm text-white/45">
            Tiada tindakan
          </div>
        )}
      </div>
    </aside>
  );

  // Mobile wraps the panel in a fixed backdrop overlay so it floats on top of
  // the cards list (which stays mounted underneath). Backdrop click closes.
  if (isMobile) {
    return (
      <div
        className="pesanan-fade-in fixed inset-0 z-[55] bg-black/55 backdrop-blur-sm"
        role="presentation"
        onMouseDown={onClose}
      >
        {panel}
      </div>
    );
  }
  return panel;
}
